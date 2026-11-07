# v6: CDC ACM + CDC NCM и SSH

Образ: artifacts/boot-linux-test-v6.img, **23670784 байта**.
SHA-256: `1eade4d8208905703286d01883e76b71728cc36b301f28563b58a0e53d4c8d63`.
Это подготовленная сборка; на устройстве v6 ещё не запускался.

## Что сохранено

Живая COM3 диагностика повторно подтвердила v5, /init, OpenRC default/lemon-health,
Alpine3.24.4, apk3.0.9, шесть UFS LUN и разделы. UFS mounts и swap отсутствуют,
block writes0, ioerr3 без роста. Логи: logs/first-test-v5/20261105T153608Z*;
оценка reports/first-test-v5-assessment.json. COM3 закрыт после чтения.

Контроль v5 сохранён в snapshots/v5-known-good с MANIFEST.json (193 файла),
исходниками переходника/конфигами/скриптами/артефактами/отчётами/live-логами.
Bootshim, DTB и Linux Image сохранены побайтово; базовые Alpine APK v5 сохранены,
для SCP дополнительно установлен openssh-sftp-server.
Поэтому **uname в v6 остаётся 7.4.0-rc1-lemon-bringup-v5**: v6 меняет initramfs,
а не проверенное ядро. Marker нового образа — LEMON_INIT_V6_REACHED и
LEMON_OPENRC_V6_REACHED. Bootshim trace остаётся LEMON_BOOTSHIM_V3.

## Выбор NCM

[Microsoft документирует встроенный UsbNcm.sys/UsbNcm.inf для Windows11 и
рекомендует NCM вместо RNDIS](https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/supported-usb-classes).
На этом ПК обнаружены Windows build28000, UsbNcm.inf и DriverStore package;
INF сопоставляет USB Class02/SubClass0d/Prot00. Это соответствует CDC NCM Linux.
Источники: reports/v6-windows-preflight.json и [Linux configfs gadget](https://docs.kernel.org/usb/gadget_configfs.html).
Сторонние INF, unsigned drivers, OS descriptor обходы и RNDIS здесь не нужны.
Реальное связывание Windows с телефоном ещё требует испытания.

config/lemon-usb-gadget-v6 создаёт одну конфигурацию:

| Параметр | Значение |
|---|---|
| VID:PID | 1d6b:0106, новый ID для составного тестового устройства |
| Composite class | EF/02/01, IAD |
| Первые интерфейсы | acm.usb0, ttyGS0, контрольный интерфейс0 |
| Следующая функция | ncm.usb0, usb0 |
| MAC Linux / Windows | 02:00:00:00:77:02 / 02:00:00:00:77:01 |
| IPv4 Linux / Windows | 192.168.77.2/30 / 192.168.77.1/30 |
| DHCP / gateway / DNS / NAT | Не настраиваются |

Скрипт выполняется один раз до bind UDC. При ошибке создания NCM оставляется
ACM-only с прежним PID0104. При отказе самого composite bind допускается одна
попытка ACM-only, только если UDC ещё пуст. Уже связанный gadget автоматически
не отключается и не перепривязывается. Не запускать helper повторно вручную.

**Номер COM3 назначает Windows.** Новый PID/состав интерфейсов может дать COM4/COM5.
ACM остаётся первым, но сохранение именно номера3 офлайн не доказуемо. Проверить
Ports в Device Manager или PowerShell; при необходимости вручную назначить ACM
номер COM3 в свойствах порта после освобождения старого назначения. Скрипты проекта
не правят registry и не удаляют старые устройства ради номера порта.

## Независимость консоли

USB-getty запускается /init до Alpine init/OpenRC. Сетевая адресация вынесена в
отдельную OpenRC службу lemon-net; Dropbear зависит от неё. Ошибки IP/SSH не
останавливают getty и не делают unbind UDC. Static rescue shell остаётся из BusyBox
v4, без Alpine loader/profile; баннер USB_RESCUE_SHELL_V6.

Офлайн модель проверяет создание составного gadget и отказ создания NCM с
сохранением ACM. Static shell проверена без сети, OpenRC и Alpine libraries.
Эта модель использует обычные файлы, не реальный configfs/Windows/USB endpoint
allocation. При panic/отказе самого USB-контроллера COM также недоступен — нужен TWRP.

## SSH

Dropbear уже имелся в v5. В v6 добавлена OpenRC служба lemon-sshd с need lemon-net.
Она создаёт уникальный Ed25519 host key в /run/dropbear, публикует его public key
и fingerprint в /run/ssh-hostkey.txt и слушает **только 192.168.77.2:22**.
Параметр -s отключает password logins; -j/-k отключают forwarding. Root login по
ключу разрешён. SSH-сервер запускается автоматически после успешной адресации.

В authorized_keys установлен только существующий публичный ключ
C:\Users\HadirPC\.ssh\id_ed25519.pub. Его fingerprint сохранён в v6-windows-preflight.json.
Приватный пользовательский ключ не читался и не копировался. Смена разрешённого
ключа требует обновить config/ssh-authorized-keys-v6 и пересобрать initramfs.
Все host keys/служебные логи/authorized_keys на телефоне находятся в RAM rootfs,
после reboot пропадают. Shared host private key в образ не включён.

## Подключение Windows после отдельного разрешённого теста

1. Сначала подтвердить доступную ACM-shell, marker V6, UFS, отсутствие mounts/swap.
2. Через COM прочитать `cat /run/ssh-hostkey.txt`; сохранить SHA256 fingerprint
   именно этого boot. Если файла нет, читать /var/log/rc.log, /run/dropbear.log,
   `ip address show` и состояние /run/openrc/started. Не перепривязывать UDC.
3. Открыть повышенный PowerShell из каталога проекта. Сначала можно запустить
   scripts/Test-LemonUsbV6.ps1 без флагов: он только диагностирует, адреса не меняет.
4. Для настройки **только распознанного NCM-адаптера** и проверки SSH:

```powershell
.\scripts\Test-LemonUsbV6.ps1 -ConfigureIPv4 -TestSsh -ExpectedHostFingerprint 'SHA256:С_КОНСОЛИ'
```

Скрипт проверяет VID/PID и MAC, сохраняет логи, добавляет только 192.168.77.1/30
в ActiveStore, без gateway/DNS и изменения других адаптеров/firewall. Неверный
адаптер/конфликт адреса останавливает настройку. Он проверяет путь через USB,
TCP22, сопоставляет ssh-keyscan с fingerprint из COM и только затем аутентифицируется.
Глобальный known_hosts не изменяется, для каждого boot используется отдельный
проверенный файл в logs/windows-v6. Он не стирает старые ключи и не отключает
StrictHostKeyChecking. При несовпадении fingerprint остановиться.

По умолчанию SSH BatchMode=yes: зашифрованный пользовательский ключ должен быть
разблокирован в вашем agent. Либо добавить -InteractiveKey для локального запроса
его passphrase; парольный вход на телефон при этом остаётся запрещённым.
Серверный host key меняется при каждом reboot: каждый раз сверять его через COM.

Успех — прошедшая команда SSH с V6 markers, Alpine/apk output, одновременной
работой ACM и шестью UFS LUN без дисковых mounts/записей. Одно появление NIC или
открытый TCP22 этого не доказывают. SCP через SFTP проверен на ПК; через настоящий USB ещё не испытывался.

## Живая диагностика v6

Только после разрешённого запуска, при закрытом другом COM-клиенте:

```powershell
python .\scripts\collect-v6.py --expect v6 --port COM3 --wait 120
```

Указать фактический COM-номер. Сбор только читает kernel/markers, mounts/swaps,
UFS counters/partitions, IP/routes/carrier, OpenRC started, host public key и
RAM-логи Dropbear/USB. Приватный host key не считывает. Reboot/flash/IP change
через COM не выполняет. Логи — logs/first-test-v6. При занятом порте завершится,
не закрывая чужую программу. При ошибке сети сохранить COM и сначала разобрать логи.

## Полный аппаратный тест с SCP

Использовать scripts/Test-LemonHardwareV6.ps1 с -ConfigureIPv4 -TestSsh -TestScp и проверенным через COM -ExpectedHostFingerprint. Он сохраняет старые защиты Test-LemonUsbV6.ps1 и добавляет ping, uname -a, rc-status, /tmp tmpfs check, SCP round-trip с SHA256 и автоматические failure logs. Протокол и границы разрешения: V6_HARDWARE_PREPARATION.md.
