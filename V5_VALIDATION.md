# v5 — собранные артефакты и проверки

**На телефоне оставлен работающий v4. v5 не прошивался и не запускался.**

Образ `artifacts/boot-linux-test-v5.img`: **23609344 байта**.
SHA-256: `ad15b45a3d60217711333fe1e07a30ede1e8b66d0195fcc3ecc00dda81586195`.
Полные размеры/хеши — reports/artifact-manifest-v5.json.

| Компонент / проверка | Результат |
|---|---|
| Kernel | ARM64 Linux 7.4.0-rc1-lemon-bringup-v5, Image 30859776 байт |
| Native Image memory_size | 31522816 байт < 33554432; до DTB остаётся 2031616 байт |
| Rootfs | Alpine3.24.4, OpenRC0.63.2, musl, apk3.0.9; около33 MiB распаковано |
| Initramfs | 13396858 байт gzip; весь корень RAM, нет root=UFS |
| Android image | v2, header1660, page4096, прежние offsets, меньше128 MiB |
| AOSP unpack | Kernel/ramdisk/stock DTB побайтово совпадают с исходными payload |
| DTBO | Оригинальный overlay #0 применяется к точному stock DTB; dtbo не изменён |
| Native DTB | Проверенный v4 DTB сохранён; dtc/provider references проходят |
| Bootshim | start.S/bridge.c/link.ld/fdt_check.c сохранены; ELF без relocations |
| ARM64 эмуляция | 15 PASS: 8 entry и7 guarded failures; DAIF masked, cache ranges |
| Большой initrd | 3 дополнительных случая используют live-v4 DTB и ABL адреса; все байты сохранены |
| ABL layout | Реальные инструкции0x16508..0x16694; fallback и2 modeled UEFI layouts без перекрытий |
| Userspace | ARM64 BusyBox/OpenRC/apk/ip/lsblk/curl/Dropbear выполнялись под QEMU-user |
| Initramfs safety | Нет block device nodes; fstab пуст; только lemon-health в runlevels |
| USB | Базовый режим off для сети: ACM-only; static BusyBox v4 есть в /rescue |
| SSH | Не запущен, ключей/пароля для сети не добавлено |
| Device package | Schema, parser и upstream devicepkg helpers PASS; APK build не выполнялся |
| Контроль v4 | Все прежние artifacts и332 файла frozen snapshot сохранили SHA |
| Backups | boot/recovery/dtbo/vbmeta на ПК сохранили SHA |

В gzip wrapper kernel_size=9901432, ramdisk_size=13396858, stock DTB=302880.
Значения Android offsets не являются доказательством физических адресов ABL.
Считанные live-v4 initrd start/end: 0x45670000/0x456fecfe. Сопоставление с
расчётами ABL согласуется с base40000000/KernelSize05700000, но переменные UEFI
не читались напрямую и для v5 остаются моделью. В трёх моделях большой initrd
находится ниже прежнего: например start44a38000, DTB44837000 при base40000000.
Bootshim дополнительно проверяет runtime RAM/overlap/reservations и откажется
переходить при неподходящем размещении.

Эмуляция завершает работу у Linux entry 0x80000000, x0=0x82000000, x1–x3=0.
Она проверяет инструкции/порядок cache maintenance, а не реальные cache contents,
PoC, firmware coherency или периферию. QEMU-user тестирует ARM64 userspace
на ядре WSL, а не полноценный boot /sbin/init/OpenRC на SM6115.

Источники результатов: reports/v5-validation.txt, bootshim-v5-emulation.json,
abl-v5-placement-emulation.json, rootfs-v5-execution.txt, pmaports-v5-check.json,
v5-header.txt, v5-abl-merged.dts, emulated-mainline-v5*.dtb.
Dtc warnings сохранены; полная dt-schema валидация не заявляется.
Логи сборки имеют имена kernel-v5-build.log, rootfs-v5-*.log, shim-v5-build.log.

Для повторной проверки после сборки: scripts/emulate-abl-placement-v5.py,
scripts/make-large-initrd-fixtures-v5.py (WSL/fdtput), scripts/emulate-shim-v5.py
(Windows Python с tools/uefi-deps), scripts/validate-v5.py (WSL).
Если prepare-shim-v5.py регенерирует базовый эмулятор, затем выполнить
extend-emulation-v5.py ровно один раз. Изменение initramfs требует повторить
package, расчёт размещения, fixtures, эмуляцию и validation.

Успех /init v5, OpenRC default, UFS и прежнего ACM на устройстве ещё не подтверждён.
Следующий этап — только отдельно разрешённый boot-only тест по FIRST_BOOT.md.

## Дополнительная подготовка первого теста

USB login helper переведён на статический BusyBox v4; профиль и Alpine libraries
ему не требуются. Missing/failed/hung OpenRC isolation tests прошли на ПК.
До OpenRC сохраняется /run/ufs-stat-initial.txt. Startup files повторно проверены
на virtual-only mounts, пустой fstab/runlevels и отсутствие swap/raw-write команд.
Ядро, переходник и оба DTB не изменялись; повторены 15 emulation cases с новым
initramfs, AOSP unpack и DTBO validation. Текущий комплект:
reports/v5-first-test-manifest.json. Старый v5-delivery-manifest относится к архиву
snapshots/v5-before-first-test-prep. Аппаратный тест v5 по-прежнему не выполнен.
