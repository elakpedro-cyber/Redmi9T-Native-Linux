> Отчёт подготовки до аппаратного испытания. Текущий аппаратный результат: [V7_HARDWARE_RESULTS.md](V7_HARDWARE_RESULTS.md).

# Итог офлайн-подготовки v7

2026-11-05. **Готов к согласованному первому испытанию; на телефоне v7 не запускалась.**
Телефон остаётся в v6. Ни flash, ни reboot, ни GPU/display/touch probe в этой
сессии не выполнялись. Сборка продолжает v6 и её bootshim, не заменяет проект.

## Артефакты

| Файл | Байты | Назначение |
|---|---:|---|
| artifacts/boot-linux-test-v7.img | 24428544 | Android-compatible boot v2, минимальная RAM Alpine |
| artifacts/Image-v7 | 31844864 | ARM64 Linux 7.4.0-rc1-lemon-bringup-v7 |
| artifacts/sm6115-xiaomi-lemon-v7.dtb | 63100 | Native DT; новый только ZAP firmware-name |
| artifacts/initramfs-v7.cpio.gz | 13807761 | Alpine/OpenRC, ACM/NCM, SSH, modules, firmware |
| artifacts/bootshim-v7.Image | 31922924 | прежний переходник с новым embedded payload |
| artifacts/gpu-userspace-v7.tar.gz | 85770796 | Mesa 26.1.6, libdrm/EGL/GLES/GBM, evtest, shader probe |
| artifacts/gpu-render-v7 | 75080 | ARM64 headless GLES2 shader/readback test |

Финальный boot SHA256:
`0ae797dbf092aaeb6fee4cb7a6d646a296f27c9f44ca9ead80fa57785f370746`.
Addon SHA256:
`b81dcac42177033382803779dd0ef1450a42e096a76b22fb260737bac6297620`.
Полный список файлов/размеров/SHA — `reports/v7-final-manifest.json`.

## Boot header и память

AOSP mkbootimg/unpack_bootimg: header v2, page4096, header size1660;
kernel offset0x8000, ramdisk0x01000000, tags0x100, DTB0x01f00000,
stock OS fields11.0.0/2023-03 сохранены как поля контейнера, не версия Linux.
Сжатый wrapper10308687, stock header DTB302880 байт. Unpack сверяет компоненты
байт-в-байт; образ меньше boot=128 MiB. Отчёт `reports/v7-header.txt`.

ABL-facing DTB остался точным оригиналом Android. Оригинальный DTBO entry0
применён fdtoverlay успешно; dtbo.img не меняется. Native DT находится внутри
wrapper. Нельзя пытаться применить stock overlay непосредственно к native DT.

Image memory_size **32505856** с BSS, меньше окна32 MiB до DTB@0x82000000;
Image переносится на0x80000000. ELF bootshim без relocations, start.S сохраняет
DAIF masked и проверки MMU/D-cache EL1/EL2. Cache maintenance к PoC и I-cache
sequence остались прежними; исходный код переходника не патчился в v7.
Официальные требования: [ARM64 boot protocol](https://kernel.org/doc/html/v5.17/arm64/booting.html).

Эмуляция исполняет настоящий код ABL для трёх моделей UEFI placement и настоящий
ARM64 shim: **15 cases, 8 достижений native entry и 7 guarded failures**.
Проверены EL1/EL2, разные базы, DAIF, x0/DTB и x1–x3=0, Image/BSS, runtime
memory/reservations и сохранность полного нового initramfs в трёх layout.
Это не исполнение Linux и не физическая модель кэша/SCM/внешних DMA masters.
Фактические адреса ABL v7 ещё должны попасть в trace на реальном устройстве.

## DT и GPU-only режим

`make CHECK_DTBS=y ... qcom/sm6115-xiaomi-lemon.dtb` прошёл, dtschema2026.9.
Для фактического native DT отдельно выполнен dt-validate по processed schema
из **5957 entries**: baseline и v7 без diagnostics. Отдельный GPU-filter также
без diagnostics. Стандартные provider/phandle references проверены валидатором.
Dtc структурно читает stock merged, native и emulated handoff tree; сохранены
предупреждения duplicate-unit-address у альтернативных отключённых QUP SPI/I2C,
graph/addr-size. «Читается dtc» не подменяет schema check, а schema pass не
доказывает электрическую совместимость.

`CONFIG_DRM_MSM=m`; v6 builtins, UFS и USB сохранены. DPU/MDSS/DSI не включены.
Важное условие headless: auto policy `msm_separate_gpu_kms_auto()` не включает
отдельный GPU при одном GPU и отсутствии активного display subsystem.
Поэтому modprobe config содержит **options msm separate_gpu_kms=1**.
Blacklist msm и отсутствие autoload services не позволяют включить GPU самим
фактом загрузки v7. Явный modprobe — только отдельный разрешённый шаг.

Firmware MDT/segments проверены на формат, согласованность, relocatable bit
и размер в reserved RAM. Это **не** проверка подписи SCM на телефоне.
Валидация графики: `reports/v7-graphics-validation.json`.

## Initramfs, сеть и SSH

Проверены executable /init, V7 markers, Alpine/OpenRC/apk, точное содержимое
USB helper и Dropbear service относительно v6, права public keys700/600,
ранний независимый static getty и известный BusyBox-v4 rescue.
Fstab пуст, только три службы health/net/sshd; нет disk mounts, swapon,
partition tools/startup writes, module autoload или panel reset.

**7 функциональных тестов** QEMU-user: normal NCM model, injected NCM failure
с сохранённым ACM, rescue без Alpine/OpenRC/network, правильный ключ и ARM64
команды, SFTP roundtrip+SHA, wrong key rejected, password не предлагается.
Тестовый SSH использует WSL loopback и одноразовые offline identities,
а не реальную USB-сеть. На аппаратуре проверка SSH host key остаётся строгой.

В образе два public keys: исходный пользовательский и уже разрешённый
device/test key, проверенный на v6. Приватный PC key и общие host private keys
в образ не включены. Host key создаётся заново в RAM, full public key и fingerprint
считываются через COM и закрепляются для текущего boot. Скрипты:
`collect-v7.py`, `pin-host-key-v7.py`, `Test-Lemon{Usb,Hardware}V7.ps1`.

## Почему Mesa отдельно

Контрольная упаковка полной graphics build-root дала initramfs **101955561 байт**
(`reports/v7-full-initramfs-bytecount.txt`; этот root также содержит оставшиеся
dev headers). Даже собственно готовый runtime addon имеет85.8 MB.
Такой initrd не проходит существующее размещение ABL относительно32 MB wrapper,
независимо от того, помещается ли файл boot в128 MiB раздел.
Небезопасный большой boot.img не выпускается, placement guards не отключаются.

Вместо этого addon394 файлов распаковывается через SSH только в RAM после
первой проверки v7. Manifest каждого файла/ссылки проверен. Отдельно проверена
распаковка поверх точного boot-root, разрешение ARM64 dynamic dependencies
libdrm/GBM/EGL/GLES и Gallium/LLVM. Probe корректно отказывает без render node.
Вызовы GPU на телефоне не выполнялись. Код действительно рисует shaders и
сверяет pixels; наличие DRM node само по себе не даёт PASS.

## Сохранение v6 и ограничения

Валидатор проверяет исходные backups, прежние артефакты и все356 файлов
`snapshots/v6-hardware-validated/MANIFEST.json`. Рабочий v6 сохранён без изменений.
Первые и последние SSH срезы этой сессии показывают v6 markers и прежний kernel,
UFS write/discard/flush counters0, отсутствие дисковых mounts/swap.
ioerr_cnt уже был0x3, не вырос. Чтение modem/vendor увеличило только read counters.

Не проверены на физическом v7: загрузка нового kernel, COM number, USB regression,
module bind, GPU/SMMU/runtime-PM, SCM signature, реальный shader render.
DSI driver/LCDB/backlight и точный touchscreen chip ID остаются блокерами
полноценной графики. Они описаны в исследовательских отчётах, не замаскированы
случайными compatibles. Запуск разрешается только по V7_FIRST_BOOT.md,
откат — V7_RECOVERY.md.

## Повторение сборки в существующем окружении

Использовать отдельные v7 directories; scripts отказываются затирать root при
первичном создании. Linux source и cross compiler существующие, kernel source
не заменялся. Команды ниже **только на ПК**, не для телефона:

1. Windows Python `scripts/prepare-v7.py` — public keys, конфигурации и v7 tests.
2. WSL hadirpc: `scripts/build-kernel-v7.sh`.
3. WSL root: `build-rootfs-v7.sh`, `finish-rootfs-v7.sh`, `build-gpu-test-v7.sh`,
   затем `build-boot-rootfs-v7.sh`, `package-rootfs-v7.sh`.
4. WSL hadirpc: `build-shim-v7.sh`; WSL root: `package-gpu-userspace-v7.py`.
5. `check-dt-v7.sh`, `check-native-dt-v7.sh`, placement emulator, fixture generator,
   shim emulator, `test-v7-offline.py`, `test-addon-v7.sh`, `validate-v7.py`,
   `validate-graphics-v7.py`; в конце `seal-v7.py`.

Точные apk версии/installed database сохранены. Репозиторий Alpine обновляемый:
повторная сетевая сборка спустя время не обещает побитового совпадения.
Контрольными являются сохранённые artifacts и их финальный manifest.
