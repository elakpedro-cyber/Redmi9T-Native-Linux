# v6 — офлайн-проверки

boot-linux-test-v6.img: **23670784 байта**,
SHA-256 `1eade4d8208905703286d01883e76b71728cc36b301f28563b58a0e53d4c8d63`.
Телефон оставлен в рабочем v5; v6 не загружался и не прошивался.

| Проверка | Результат |
|---|---|
| Контроль v5 | Live COM3, Alpine/OpenRC/apk/UFS; snapshot193 файла, SHA проверены |
| Ядро/переходник | Image и wrapper побайтово v5; uname остаётся -v5 |
| Kernel config | В v5 уже встроены NET/INET/UNIX, NCM и ACM; не пересобирался |
| Native DTB / stock DTB | Не изменены, dual-DTB схема сохранена |
| Android header | v2, header1660/page4096, прежние offsets |
| Payload sizes | kernel9901432, initramfs13457855, stockDTB302880 |
| Размер boot | 23670784 < 134217728 |
| AOSP unpack | Payload совпадают побайтово |
| DTBO | Original overlay0 применяется к точному stock DTB, dtbo не менялся |
| ARM64 emulation | 15 PASS, 8 entry; DAIF/cache guards/reservations сохранены |
| Большой initrd | 3 ABL-modeled layouts, содержимое initrd не повреждено |
| NCM normal setup model | ACM link остаётся первым, NCM link создан, bind выполняется |
| NCM creation failure model | ACM сохранён, fallback PID0104, bind ACM-only |
| Emergency shell | Выполняет команды без сети/OpenRC/Alpine loader |
| SSH positive | Реальный ARM64 Dropbear под QEMU-user, ключевой login и Alpine commands |
| SSH negative | Неверный ключ отвергается; password authentication не предлагается |
| OpenRC configuration | Health + lemon-net + lemon-sshd; SSH needs lemon-net |
| Windows preflight | Build28000, UsbNcm.inf/DriverStore, Class02/0d/00 match |
| PowerShell | AST parse PASS; адреса/драйверы Windows не изменялись |
| UFS safety | Пустой fstab, no swap/localmount/partition writes, rootfs в RAM |
| Backups/старые артефакты | v1–v5 и boot/recovery/dtbo/vbmeta прежние по SHA |

Полные логи: reports/v6-validation.txt, v6-functional-tests.json,
v6-offline-sshd.log, bootshim-v6-emulation.json, abl-v6-placement-emulation.json,
v6-header.txt, v6-windows-preflight.json, v6-powershell-parse.txt.
Текущие размеры/хеши: reports/artifact-manifest-v6.json.

SSH offline test использовал отдельный disposable chroot, loopback ПК
127.0.0.1:22266 и временные тестовые client/host keys. Ключи удалены вместе с
temporary directory; в реальном rootfs остался только публичный ключ пользователя.
Сеть WSL и QEMU-user не моделируют USB. NCM configfs model использует обычные
файлы и не проверяет реальные descriptors/endpoint allocation/Windows enumeration.
Успешная эмуляция handoff не означает исполнения ядра внутри эмулятора.

## Что ещё требует физического испытания

- Composite enumeration Windows11: Usbser + UsbNcm одновременно, фактический COM.
- Настоящий NCM link/IP, TCP22, fingerprint и SSH key login через USB.
- Сохранение ACM при неработающем IP/SSH; не вызывать аппаратные сбои автоматически.
- UFS/Alpine/OpenRC/display regression и отсутствие block writes по снимкам.

Фиксированный номер COM3 не гарантируется из-за нового composite PID; ручное
назначение номера при необходимости описано в V6_USB_SSH.md. Ни появление NIC,
ни offline SSH test не считаются завершённым аппаратным успехом.

## Повторная сборка

Исходники v6 — config/*-v6, scripts/prepare-v6.py и build-rootfs-v6.sh.
prepare-v6.py копирует проверенные kernel/shim под v6 именами и создаёт /init.
build-rootfs-v6.sh извлекает сохранённый Alpine v5 tar в отдельное WSL дерево,
устанавливает helper/services/public key. Существующий v6 root не заменяется.

После подготовки нового дерева и `test-v6-offline.py`:

```sh
sudo bash scripts/package-rootfs-v6.sh
```

На Windows: package-v6.py, emulate-abl-placement-v6.py; в WSL:
make-large-initrd-fixtures-v6.py; затем Windows emulate-shim-v6.py и WSL validate-v6.py.
Манифесты привязаны к готовым файлам; byte reproducibility между версиями tar/gzip
не заявляется. Не использовать prepare-v6.py для прошивки — операций с телефоном в нём нет.

## Подготовка текущего аппаратного теста

Добавлен официальный openssh-sftp-server (68 Alpine packages). Настоящий scp/SFTP round-trip прошёл под ARM64 QEMU-user, всего7 функциональных случаев. Полный новый Windows тест — scripts/Test-LemonHardwareV6.ps1. Он проверяет ping/SSH/rc-status/SCP и сохраняет host/serial failure logs, защищает домашний192.168.0.x интерфейс. Подробнее V6_HARDWARE_PREPARATION.md.
