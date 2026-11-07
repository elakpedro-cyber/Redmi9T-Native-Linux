# v4 — результаты офлайн-проверок

Образ собран, на телефон не загружался. Текущий телефон оставлен в v3.

`artifacts/boot-linux-test-v4.img`: **9576448 байт**.
SHA-256: `4cf10f2a9c6d7298e46aec7afdcc64421b532705d29bbbf7b703ae2c90bffa45`.
Манифест всех артефактов: `reports/artifact-manifest-v4.json`.

| Проверка | Результат |
|---|---|
| Ядро ARM64 | 7.4.0-rc1-lemon-bringup-v4; Image 28166656 байт |
| Image memory_size с BSS | 28770304 < 33554432; DTB по 0x82000000 не перекрыт |
| Конфигурация | Все v3 =y сохранены, UFS/SCSI/SD/QMP UFS =y |
| ARM64 handoff | Все 12 сценариев прошли, 5 достигают entry 0x80000000 |
| CPU/cache | EL1/EL2, DAIF masked, CIVAC/CVAC ranges, DSB/IC/ISB проверены эмулятором |
| Защиты | Недопустимые FDT, перекрытия, выравнивание, M/C включены — отказ |
| Bootshim | Исходники v3 сохранены; новый payload; ELF без relocations |
| Android header | v2, 1660, page4096; offsets как v3; AOSP round-trip точный |
| Kernel/ramdisk/DTB размеры | 8680164 / 584958 / 302880 байт в Android header |
| ABL-facing DTB | Точный stock DTB, stock overlay #0 применяется fdtoverlay |
| Mainline DTB | Прежний v3; dtc читает объединённые деревья; 466 ссылок разрешены |
| UFS DT | HBA/PHY okay, driver compatibles и зависимости проверены |
| BusyBox | Статический ARM64; все v3 features сохранены; zcat/base64 round-trip |
| Initramfs | /init и diagnostic executable, console char 5:1, все applet links |
| /init | v3 поведение сохранено; изменены только marker и запуск RAM-диагностики |
| Оригиналы | SHA всех прежних artifacts v1/v2/v3 и четырёх backups неизменны |

Подробности: `reports/v4-validation.txt`, `reports/bootshim-v4-emulation.json`,
`reports/emulate-shim-v4.log`, `reports/v4-header.txt`, `reports/v4-abl-merged.dts`,
`reports/emulated-mainline-v4.dts`, соответствующие dtc warnings.
Dtc warnings сохранены; успешная декомпиляция не означает полную dt-schema проверку.
Эмулятор проверяет переходник до entry; ядро Linux в нём не исполняется.
Реальное содержимое caches, PoC и firmware coherency эмулятор не моделирует.
Требования протокола: [официальная документация ARM64 Linux](https://cdn.kernel.org/doc/html/latest/arch/arm64/booting.html).

## Изменения относительно v3

Новые файлы ядра и конфига имеют суффикс v4; прежние Image/linux.config не заменены.
Bootshim start.S/bridge.c/link.ld/fdt_check.c не менялись. Trace по-прежнему
называется LEMON_BOOTSHIM_V3: это версия переходника. Новый Linux различается
uname `-v4` и marker `LEMON_INIT_V4_REACHED`.

Init сохраняет ACM gadget, console shell, pstore, параметры framebuffer.
После запуска USB-фонового процесса добавляется отдельный процесс диагностики.
Он делает три снимка с интервалами 5 и 10 секунд и пишет только
`/run/ufs-diagnostics.log` (tmpfs). Sysfs/debugfs только читаются, debugfs не
монтируется. В init не добавлено монтирование накопителей, fsck, swap, mass storage
или команды записи дисков. Обычный UFS probe управляет PHY/питанием при будущем
запуске; режим аппаратной write protection не настроен и не заявляется.

BusyBox дополнен gunzip/zcat/base64/od/hexdump для последующей диагностики.

## Повторная сборка

WSL Ubuntu-24.04, aarch64-linux-gnu GCC 13.3, тот же pinned source. Из каталога проекта:

```sh
bash scripts/build-kernel-v4.sh
bash scripts/build-userspace-v4.sh
bash scripts/build-shim-v4.sh
```

Последний скрипт вызывает package-v4.py с официальными AOSP mkbootimg/unpack_bootimg.
Эмулятор запускается Windows Python с имеющимися tools/uefi-deps:

```powershell
python .\scripts\emulate-shim-v4.py
```

Затем в WSL: `python3 scripts/validate-v4.py`; на ПК: `python scripts/audit-ufs-v4.py`.
Логи сборки: reports/kernel-v4-build.log, userspace-v4-build.log, shim-v4-build.log.
Конфиги: config/linux-v4.config, ufs-v4.fragment, busybox-v4.config.

## Граница подтверждений

На устройстве подтверждена только v3: Linux, /init, COM3, simpledrm и runtime trace.
Для v4 пока не проверены ABL acceptance нового размера, загрузка ядра, /init,
реальная UFS связь/разделы, USB/экран и pstore retention. Требуется отдельное
разрешение по FIRST_BOOT.md. Успехом UFS будет вывод настоящих SCSI дисков и
разделов без монтирования/изменения их содержимого.
