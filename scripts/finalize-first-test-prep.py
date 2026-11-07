from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'reports/artifact-manifest-v5.json').read_text())
image=manifest['boot-linux-test-v5.img'];ramdisk=manifest['initramfs-v5.cpio.gz']['bytes']
old_sha='e26f9da760c05f80d88a978675c70b0b1d0fffa9af1f64ef2a83ae797308a60d'
for path in root.glob('*.md'):
    old=path.read_text(encoding='utf-8-sig')
    text=old.replace(old_sha,image['sha256']).replace('13397696',str(ramdisk))
    if text!=old:path.write_text(text,encoding='utf-8',newline='\n')
path=root/'FIRST_BOOT.md';text=path.read_text(encoding='utf-8')
text+='''
## Подготовка COM-сбора и аварийная shell

Текущий v5 усилен статической USB-shell с баннером USB_RESCUE_SHELL_V5.
Она запускается до OpenRC и не требует Alpine loader или /etc/profile.
OpenRC failure не считается успешной загрузкой Alpine: сохранить логи и
использовать shell только для диагностики, не для записи UFS.
Три теста отказа OpenRC, свежие v4 логи и автоматический сбор описаны в
FIRST_TEST_PREPARATION.md. Во время разрешённого теста, когда телефон уже в TWRP,
можно заранее запустить на ПК collect-first-test.py --expect v5 --port COM3 --wait 120.
Он только ожидает COM и читает данные; reboot/flash не выполняет.
После сбора выполнить analyze-first-test.py --version v5 и разобрать raw/dmesg.
'''
path.write_text(text,encoding='utf-8',newline='\n')
path=root/'V5_VALIDATION.md';text=path.read_text(encoding='utf-8')
text+='''
## Дополнительная подготовка первого теста

USB login helper переведён на статический BusyBox v4; профиль и Alpine libraries
ему не требуются. Missing/failed/hung OpenRC isolation tests прошли на ПК.
До OpenRC сохраняется /run/ufs-stat-initial.txt. Startup files повторно проверены
на virtual-only mounts, пустой fstab/runlevels и отсутствие swap/raw-write команд.
Ядро, переходник и оба DTB не изменялись; повторены 15 emulation cases с новым
initramfs, AOSP unpack и DTBO validation. Текущий комплект:
reports/v5-first-test-manifest.json. Старый v5-delivery-manifest относится к архиву
snapshots/v5-before-first-test-prep. Аппаратный тест v5 по-прежнему не выполнен.
'''
path.write_text(text,encoding='utf-8',newline='\n')
previous=json.loads((root/'snapshots/v5-before-first-test-prep/artifact-manifest-v5.json').read_text())
preserved=['Image-v5','Image-v5.gz','bootshim-v5.elf','bootshim-v5.Image','bootshim-v5.Image.gz','sm6115-xiaomi-lemon-v2.dtb']
for name in preserved:
    assert hashlib.sha256((root/'artifacts'/name).read_bytes()).hexdigest()==previous[name]['sha256'],name
files=list(root.glob('*.md'))
for directory in ['config','scripts','bootshim','pmaports','logs/first-test-v4']:
    files.extend(p for p in (root/directory).rglob('*') if '__pycache__' not in p.parts)
files.extend(p for p in (root/'artifacts').iterdir() if 'v5' in p.name or p.name=='boot-linux-test-v4.img')
files.extend(p for p in (root/'reports').iterdir() if 'v5' in p.name or p.name=='first-test-v4-assessment.json')
files=[p for p in files if p.is_file() and p.name not in ['v5-first-test-manifest.json']]
data={p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(set(files))}
(root/'reports/v5-first-test-manifest.json').write_text(json.dumps({'image':image,'kernel_shim_unchanged':preserved,'phone_reboot_or_flash_run':False,'files':data},indent=2)+'\n')
for name,info in data.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==info['sha256'],name
print('Current v5:',image,';',len(data),'delivery files verified')
