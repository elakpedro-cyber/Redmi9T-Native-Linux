"""Offline stock/mainline supply comparison and line-addressed evidence index."""
from pathlib import Path
import hashlib,json,sys

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'scripts'))
from fdt_audit import Fdt

stock=Fdt(root/'reports/live.dtb');base=Fdt(root/'artifacts/sm6115-xiaomi-lemon-v8b.dtb')
touch='/soc/spi@4a88000/novatek@1'
supplies={}
for key in ['touch_vddio-supply','touch_lab-supply','touch_ibb-supply']:
    value=stock.nodes[touch][key]
    suppliers=stock.phandles[stock.cells(value)[0]]
    consumers=[]
    for path,props in stock.nodes.items():
        for prop,data in props.items():
            if prop.endswith('-supply') and data==value:consumers.append({'node':path,'property':prop})
    supplies[key]={'provider':suppliers,'consumers':consumers}
assert all(any(c['node']=='/soc/qcom,dsi-display-primary' for c in supplies[key]['consumers']) for key in supplies)
v8_l9=base.nodes['/remoteproc/glink-edge/rpm-requests/regulators-0/l9']
assert base.cells(v8_l9['regulator-min-microvolt'])==[1800000]
active_spi=[p for p,ps in base.nodes.items() if b'qcom,geni-spi' in ps.get('compatible',b'') and ps.get('status',b'okay\0') in [b'okay\0',b'ok\0']]
assert active_spi==['/soc@0/geniqup@4ac0000/spi@4a88000']
queries={
 'touchscreen-v1/sources/xiaomi/NT36672A/nt36xxx.c':['client->chip_select = 0','regulator_get(&ts->client->dev, "touch_vddio")','regulator_get(&ts->client->dev, "touch_lab")','regulator_get(&ts->client->dev, "touch_ibb")','GPIOF_OUT_INIT_LOW','gpio_set_value(ts->reset_gpio, 1)','msecs_to_jiffies(14000)','nvt_eng_reset();','nvt_ts_enable_regulator(false)'],
 'touchscreen-v1/sources/xiaomi/NT36672A/nt36xxx.h':['NVT_TOUCH_SUPPORT_HW_RST 1','BOOT_UPDATE_FIRMWARE_NAME','INT_TRIGGER_TYPE'],
 'touchscreen-v1/sources/xiaomi/NT36672A/nt36xxx_fw_update.c':['request_firmware(','FW_BIN_VER_OFFSET','nvt_download_firmware(void)','nvt_write_firmware(','nvt_get_fw_info();'],
 'touchscreen-v1/sources/xiaomi/spi-geni-qcom.c':['demux_sel = spi_slv->chip_select','demux_output_inv = 0'],
 'touchscreen-v1/sources/linux/spi-geni-qcom.c':['static int spi_geni_init','geni_load_se_firmware','static struct platform_driver spi_geni_driver','spi_geni_runtime_suspend'],
 'logs/v7-authorized/twrp-dmesg-before.txt':['mode=0, max_speed_hz=9600000','int_trigger_type=1','Linked as a consumer to regulator.31','filename is nt33672a_truly','Update firmware success','fw_ver = 0x05','PID=5940'],
 'logs/v8-stage-c-a/hardware.txt':['/sys/class/regulator/regulator.11/name=l9','regulator.11/num_users=0'],
}
anchors={}
for name,needles in queries.items():
    data=(root/name).read_bytes();lines=data.decode('utf-8',errors='replace').splitlines()
    anchors[name]={'sha256':hashlib.sha256(data).hexdigest(),'matches':[
        {'line':i,'text':line.strip()} for i,line in enumerate(lines,1) if any(n in line for n in needles)]}
result={'supplies_shared_with_display':supplies,'v8b_l9_limits_uv':[1800000,2000000],
        'lcdb_provider_present_in_v8b':any('regulator@ec00' in p for p in base.nodes),
        'enabled_geni_spi_nodes':active_spi,'source_anchors':anchors,
        'decision':'NO-GO: electrical handoff, runtime rollback and CS0 registration unresolved'}
out=root/'logs/touchscreen-stage1-final/stock-comparison.json'
out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('STOCK_SUPPLY_AND_CS_SOURCE_AUDIT_PASS; all three touch supplies also feed LCD')
