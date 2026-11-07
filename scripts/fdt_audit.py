from pathlib import Path
import json
import struct

class Fdt:
    def __init__(self, path):
        self.data = Path(path).read_bytes()
        magic,total,off,strings,_,version,_,_,_,length = struct.unpack_from('>10I',self.data)
        assert magic == 0xd00dfeed and total <= len(self.data)
        self.nodes = {}
        stack = []
        end = off + length
        while off < end:
            token = struct.unpack_from('>I',self.data,off)[0]; off += 4
            if token == 1:
                stop = self.data.index(0,off)
                stack.append(self.data[off:stop].decode())
                self.nodes['/'+'/'.join(stack[1:])] = {}
                off = (stop+4)&~3
            elif token == 2:
                stack.pop()
            elif token == 3:
                size,nameoff = struct.unpack_from('>II',self.data,off); off += 8
                nameend=self.data.index(0,strings+nameoff)
                name=self.data[strings+nameoff:nameend].decode()
                self.nodes['/'+'/'.join(stack[1:])][name]=self.data[off:off+size]
                off=(off+size+3)&~3
            elif token == 9:
                break
            else:
                assert token == 4
        self.symbols={k:v.rstrip(b'\0').decode() for k,v in self.nodes.get('/__symbols__',{}).items()}
        self.phandles={self.cells(v['phandle'])[0]:k for k,v in self.nodes.items() if 'phandle' in v}

    @staticmethod
    def cells(value):
        return list(struct.unpack('>'+str(len(value)//4)+'I',value))

    @staticmethod
    def strings(value):
        return [s.decode() for s in value.rstrip(b'\0').split(b'\0')]

if __name__ == '__main__':
    root=Path(__file__).resolve().parents[1]
    stock=Fdt(root/'reports/stock-boot/dtb')
    main=Fdt(root/'artifacts/sm6115-xiaomi-lemon.dtb')
    symbols_path=root/'reports/mainline-symbols.dtb'
    labels=Fdt(symbols_path) if symbols_path.exists() else main
    ov=Fdt(root/'reports/stock-overlay-0.dtbo')
    fixups=ov.nodes['/__fixups__']
    rows=[]
    for symbol,data in fixups.items():
        target=stock.symbols.get(symbol)
        assert target in stock.nodes, symbol
        phandle=stock.cells(stock.nodes[target]['phandle'])[0]
        for location in ov.strings(data):
            node,prop,offset=location.rsplit(':',2); offset=int(offset)
            placeholder=struct.unpack_from('>I',ov.nodes[node][prop],offset)[0]
            assert placeholder == 0xffffffff,location
            rows.append({'symbol':symbol,'stock_path':target,'stock_phandle':hex(phandle),'mainline_symbol_path':labels.symbols.get(symbol),'same_path_in_mainline':target in main.nodes,'overlay_node':node,'property':prop,'byte_offset':offset,'placeholder':hex(placeholder),'stock_compatible':stock.strings(stock.nodes[target].get('compatible',b''))})
    local_count=0
    for path,props in ov.nodes.items():
        if path.startswith('/__local_fixups__/'):
            original=path[len('/__local_fixups__'):]
            for prop,data in props.items():
                for off in ov.cells(data):
                    ref=struct.unpack_from('>I',ov.nodes[original][prop],off)[0]
                    assert ref in ov.phandles,(path,prop,off,ref)
                    local_count+=1
    fragments=[]
    target_symbols={row['overlay_node']:row['symbol'] for row in rows if row['property']=='target'}
    for path,props in ov.nodes.items():
        if path.count('/')==1 and path.startswith('/fragment@'):
            fragments.append({'fragment':path,'target_symbol':target_symbols.get(path),'target_path':ov.strings(props['target-path']) if 'target-path' in props else None,'overlay_properties':list(ov.nodes.get(path+'/__overlay__',{}))})
    report={'stock_nodes':len(stock.nodes),'mainline_nodes':len(main.nodes),'stock_symbols':len(stock.symbols),'mainline_symbols_original':len(main.symbols),'mainline_symbols_rebuilt':len(labels.symbols),'external_symbols':len(fixups),'external_references':len(rows),'missing_symbols_original':sorted(set(fixups)-set(main.symbols)),'missing_symbols_with_labels':sorted(set(fixups)-set(labels.symbols)),'local_references_validated':local_count,'fragments':fragments,'references':rows}
    (root/'reports/dtbo-reference-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    header='symbol\tstock_path\tstock_phandle\tmainline_symbol_path\tsame_path_in_mainline\toverlay_node\tproperty\tbyte_offset\n'
    (root/'reports/dtbo-references.tsv').write_text(header+'\n'.join('\t'.join(str(row[k]) for k in ['symbol','stock_path','stock_phandle','mainline_symbol_path','same_path_in_mainline','overlay_node','property','byte_offset']) for row in rows)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['references','fragments','missing_symbols_original','missing_symbols_with_labels']},indent=2))
    print('Missing after -@:',','.join(report['missing_symbols_with_labels']))
