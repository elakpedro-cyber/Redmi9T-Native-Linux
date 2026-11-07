from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
data=json.loads((root/'reports/artifact-manifest-v6.json').read_text())
size=data['boot-linux-test-v6.img']['bytes'];digest=data['boot-linux-test-v6.img']['sha256']
for path in root.glob('*.md'):
    old=path.read_text(encoding='utf-8-sig')
    new=old.replace('beb9e336d8b25a7c6e6952c4c6e7feac591ea0384c74c375ae0103a7c6895762',digest)
    if path.name in ['README.md','STATUS.md','V6_VALIDATION.md','V6_USB_SSH.md']:
        new=new.replace('23609344',str(size)).replace('13398010',str(data['initramfs-v6.cpio.gz']['bytes']))
    if path.name=='V6_FIRST_BOOT.md':
        new=new.replace('Образ v6: 23609344 байта',f'Образ v6: {size} байта')
        mark="dd if=/tmp/boot-linux-test-v6.img"
        before,after=new.split(mark,1)
        after=after.replace('head -c 23609344',f'head -c {size}',1)
        new=before+mark+after
    if new!=old:path.write_text(new,encoding='utf-8',newline='\n')
path=root/'V6_VALIDATION.md';t=path.read_text(encoding='utf-8')
t+='\n## Подготовка текущего аппаратного теста\n\nДобавлен официальный openssh-sftp-server (68 Alpine packages). Настоящий scp/SFTP round-trip прошёл под ARM64 QEMU-user, всего7 функциональных случаев. Полный новый Windows тест — scripts/Test-LemonHardwareV6.ps1. Он проверяет ping/SSH/rc-status/SCP и сохраняет host/serial failure logs, защищает домашний192.168.0.x интерфейс. Подробнее V6_HARDWARE_PREPARATION.md.\n'
path.write_text(t,encoding='utf-8',newline='\n')
path=root/'V6_USB_SSH.md';t=path.read_text(encoding='utf-8')
t=t.replace('Передача файлов отдельно не проверялась.','SCP через SFTP проверен на ПК; через настоящий USB ещё не испытывался.')
t+='\n## Полный аппаратный тест с SCP\n\nИспользовать scripts/Test-LemonHardwareV6.ps1 с -ConfigureIPv4 -TestSsh -TestScp и проверенным через COM -ExpectedHostFingerprint. Он сохраняет старые защиты Test-LemonUsbV6.ps1 и добавляет ping, uname -a, rc-status, /tmp tmpfs check, SCP round-trip с SHA256 и автоматические failure logs. Протокол и границы разрешения: V6_HARDWARE_PREPARATION.md.\n'
path.write_text(t,encoding='utf-8',newline='\n')
path=root/'V6_FIRST_BOOT.md';t=path.read_text(encoding='utf-8')
t+='\n## Текущий протокол Windows и RAM SCP\n\nДля нового финального образа с SFTP использовать V6_HARDWARE_PREPARATION.md и Test-LemonHardwareV6.ps1. Разрешение на полный тест должно включать USB-only IPv4 Windows и1024-byte SCP в проверенный /tmp tmpfs с последующим удалением. Единственные разрешаемые записи UFS — boot для одного теста и boot при согласованном возврате v5; другие разделы не затрагиваются. Предыдущий v6 сохранён в snapshots/v6-before-scp.\n'
path.write_text(t,encoding='utf-8',newline='\n')
print('Current v6',size,digest)
