# v6 — подготовка аппаратного испытания

**Текущее состояние:** телефон по-прежнему работает в v5. В этой сессии были
только serial-команды чтения и локальные операции. Ни reboot, ни flash, ни
изменения USB/IP/драйверов на телефоне или Windows не выполнялись.

## Контроль v5

Свежие логи: logs/first-test-v5/20261105T160004Z*, raw transcript и JSON команд.
Подтверждены kernel-v5, оба marker V5, Alpine3.24.4, apk, OpenRC default и
lemon-health, шесть LUN, UFS/PHY drivers и ACM configured. В /proc/mounts только
виртуальные FS, /proc/swaps пуст. Writes/sectors written0, ioerr3 без роста.
Результат: reports/first-test-v5-assessment.json — PASS_OBSERVED_CHECKS.

Рабочий образ v5 и snapshot сохранены; его SHA:
`ad15b45a3d60217711333fe1e07a30ede1e8b66d0195fcc3ecc00dda81586195`,
размер23609344. Он не заменялся новой сборкой.

## Исправление найденного блокера SCP

Предыдущий v6 поддерживал SSH, но не содержал SFTP server. Современный scp
использует SFTP по умолчанию ([OpenSSH manual](https://man.openbsd.org/scp.1)).
В локальный v6 добавлен официальный Alpine openssh-sftp-server10.3_p1-r2,
ровно один пакет; kernel/shim/DTB и Dropbear не менялись. Его путь совпадает с
/usr/lib/ssh/sftp-server, скомпилированным в Dropbear.
Старый v6 сохранён в snapshots/v6-before-scp.

**Использовать новый финальный образ:** artifacts/boot-linux-test-v6.img.
Размер **23670784 байта**, SHA256:
`1eade4d8208905703286d01883e76b71728cc36b301f28563b58a0e53d4c8d63`.
Старый SHA beb9… больше не относится к этому файлу.
Корень остаётся целиком в RAM; не добавлены mount/swap/partition services.

## Что проверено

| Проверка | Доказательство / граница |
|---|---|
| AOSP header2/page4096 и payload round-trip | reports/v6-header.txt, v6-validation.txt |
| Stock DTBO и mainline references | fdtoverlay/dtc PASS; dtbo не менялся |
| ARM64 handoff | 15 случаев PASS, включая новый большой initrd; ядро в эмуляторе не исполняется |
| Ядро и wrapper | Побайтово рабочий v5; uname остаётся -v5, markers V6 |
| Windows NCM | Inbox UsbNcm.inf совпадает с02/0d/00; Microsoft поддерживает Windows11 |
| Source descriptors | IAD EF/02/01; ACM первым, NCM control02/0d/00; ожидаются4 интерфейса |
| Compiled functions | acm_bind/ncm_bind присутствуют в System-v5.map |
| Configfs setup/failure model | ACM остаётся при отказе создания NCM; реальный USB не эмулируется |
| Static emergency shell | Работает в PC chroot без сети/OpenRC/Alpine libraries |
| Dropbear/keys | Root public key600, directory700; private host key отсутствует в image |
| SSH auth | Настоящий ARM64 Dropbear: valid-key PASS, wrong-key rejected, password не предлагается |
| SCP | Реальный scp/SFTP upload/download2082 bytes в disposable /tmp, SHA совпал |
| Windows safety guards | 3 mock rejection cases: absent adapter, wrong MAC, protected192.168.0.x; mutations0 |
| PowerShell | Все новые/изменённые скрипты проверены parser, не выполнялись против телефона |

Логи: v6-functional-tests.json (7 cases), v6-offline-sshd.log,
v6-network-guard-tests.json, v6-descriptor-check.json, v6-usb-descriptor-evidence.txt,
artifact-manifest-v6.json и v6-validation.txt в reports.
SSH/SCP PC тест шёл через loopback WSL с временными ключами в disposable chroot,
а не через USB/Windows. Модель gadget не доказывает endpoint allocation.

На настоящем v6 ещё не проверены bus descriptors, UsbNcm binding, номер COM,
ping/SSH/SCP и одновременная стабильность ACM/UFS. Это проверяется только после
разрешения на аппаратный запуск. COM-номер может измениться при новом PID0106.

## Автоматизированный тест Windows ↔ телефон

Сначала применить V6_FIRST_BOOT.md и V6_RECOVERY.md в согласованном сценарии.
После появления ACM прочитать текущий host fingerprint через COM:

```sh
cat /run/ssh-hostkey.txt
```

На ПК из каталога проекта, повышенный PowerShell только для USB IPv4:

```powershell
.\scripts\Test-LemonHardwareV6.ps1 -ConfigureIPv4 -TestSsh -TestScp -ExpectedHostFingerprint 'SHA256:ИЗ_COM' -SerialPort COM3
```

Указать фактический COM. Для локального passphrase зашифрованного клиентского ключа
есть -InteractiveKey; пароль на телефон остаётся отключён. Приватный ключ не
копируется. Host key сверяется через COM для каждого boot, затем StrictHostKeyChecking=yes.

Сценарий:

1. Найти ACM и единственный USB NCM по VID/PID и MAC, отказать при неоднозначности.
2. Не выбирать домашний192.168.0.x интерфейс даже при неожиданном совпадении идентичности.
3. При явном -ConfigureIPv4 добавить .77.1/30 только целевому USB ifIndex в ActiveStore,
   без gateway/DNS/firewall и без удаления адресов других интерфейсов.
4. Проверить source route через USB, TCP22, ping с source .77.1, host fingerprint и key SSH.
5. Выполнить uname -a, Alpine release, rc-status, SSH service status и проверить .77.2/30.
6. Убедиться в шести block devices, только virtual mounts, no swap и нулевых
   block write/discard counters. Отдельно сверить ioerr до/после по COM/SSH логам.
7. До SCP убедиться, что именно /tmp — tmpfs; передать1024-byte случайный файл,
   проверить remote SHA и download SHA, удалить только этот GUID-файл из RAM.
8. Повторить storage safety check и сравнить snapshot адресов/DHCP/DNS/gateway
   домашнего192.168.0.x интерфейса. Любое отличие — failure, без автоматического отката настроек.

Без -TestScp файл не передаётся. Этот флаг используется только внутри разрешённого
аппаратного теста: это запись в RAM, не в UFS. До разрешения скрипт не запускать
с подключением к телефону. Без флага -ConfigureIPv4 Windows IP не меняется.

## Логи и неисправности

logs/hardware-v6/<timestamp>/ содержит результат, ping/SSH/SCP/SHA, snapshots
домашней сети и вложенный usb/ с adapter/IP/route/TCP/known_hosts.
При ошибке автоматически собираются PnP nodes/properties (hardware/compatible IDs,
driver/problem fields), найденные USB adapters и ping; затем read-only collect-v6.py
по указанному COM. Занятый порт не отбирается и чужие процессы не закрываются.
В таком случае закрыть свой терминал и отдельно повторить serial collector.

Если NCM отсутствует: проверить composite parent и interface2 в PnP properties,
их compatible ID02/0d/00 и UsbNcm driver/problem code; сверить ожидаемую структуру
с source evidence. В COM прочитать /run/usb-setup.log, dmesg, ip link и configfs
links. При необходимости получить реальные bus descriptors после запуска;
по исходнику нельзя утверждать, какие байты реально принял Windows.
Не отключать ACM, не unbind UDC, не подменять драйвер WinUSB и не устанавливать
случайный INF ради сети.

Если link/ping работает, а SSH нет: проверить lemon-net/lemon-sshd started,
192.168.77.2, /run/dropbear.log, host fingerprint, authorized public key и agent.
Не включать парольную auth. При SCP failure проверить /tmp tmpfs и SFTP binary.

Ни один из Windows-скриптов не содержит flash/reboot. Полный host тест ещё не
выполнен, результаты mock/chroot не выдаются за аппаратный успех.

## Следующий разрешаемый шаг

Точный объём отдельного разрешения: войти из v5 в TWRP, перепроверить v5/backup
и текущий новый v6 SHA, записать один раз только boot, readback, один запуск v6,
настроить только USB IPv4 Windows и проверить SSH/SCP в RAM. При неуспехе —
сбор pstore/логов и восстановление только boot рабочим v5. Сам boot физически
находится на UFS: его согласованная запись является единственным исключением,
другие разделы не монтируются и не изменяются.

## Графика v7

Гейт стабильного физического v6 ещё не пройден. V7_GRAPHICS_MATRIX.md переносит
имеющиеся факты с разделением source/offline/device; V7_TECHNICAL_PLAN.md задаёт
будущие шаги. Новое аппаратное исследование и graphics kernel не запускались.
