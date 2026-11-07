from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1]
t=(root/'config/init-v5').read_text().replace('V5','V6')
a=t.index('(\n    g=');b=t.index(') >/run/usb-setup.log 2>&1 &',a)
t=t[:a]+'''(
    /usr/local/sbin/lemon-usb-gadget || { echo 'USB gadget setup failed'; exit 1; }
    dmesg > /run/boot-dmesg.txt
    while :; do
        /rescue/getty -L -n -l /usr/local/sbin/lemon-root-shell 115200 ttyGS0 vt100
        sleep 1
    done
''' +t[b:]
(root/'config/init-v6').write_text(t,newline='\n')
for old,new in [('lemon-root-shell-v5','lemon-root-shell-v6'),('lemon-health-v5','lemon-health-v6'),('lemon-diagnostics-v5','lemon-diagnostics-v6')]:
    t=(root/'config'/old).read_text().replace('V5','V6').replace('v5','v6')
    (root/'config'/new).write_text(t,newline='\n')
shutil.copyfile(root/'config/inittab-v5',root/'config/inittab-v6')
shutil.copyfile(root/'config/linux-v5.config',root/'config/linux-v6.config')
for name in ['Image','Image.gz','bootshim-v5.elf','bootshim-v5.Image','bootshim-v5.Image.gz']:
    source=('Image-v5'+name[len('Image'):]) if name.startswith('Image') else name
    target=source.replace('v5','v6')
    shutil.copyfile(root/'artifacts'/source,root/'artifacts'/target)
for kind in ['symbols','relocations','disassembly']:
    shutil.copyfile(root/f'reports/bootshim-v5-{kind}.txt',root/f'reports/bootshim-v6-{kind}.txt')
for filename in ['package-v5.py','emulate-shim-v5.py','emulate-abl-placement-v5.py','make-large-initrd-fixtures-v5.py']:
    text=(root/'scripts'/filename).read_text().replace('v5','v6')
    # The live-v4 DTB remains a valid firmware handoff fixture; no new live-v6 DTB exists.
    (root/'scripts'/filename.replace('v5','v6')).write_text(text,newline='\n')
