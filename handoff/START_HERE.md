# Передача Claude Code — 7 ноября 2026

## Что уже работает

Xiaomi Redmi 9T NFC, codename lemon, SM6115/Snapdragon662, ARM64, unlocked bootloader, TWRP, non-A/B. Нативный Linux v8b `7.4.0-rc1-lemon-bringup-v8b`, Alpine3.24.4/OpenRC, rootfs в RAM. Шесть UFS LUN sda–sdf, без дисковых mounts/swap. USB ACM COM4, NCM Windows192.168.77.1/30 ↔ Linux192.168.77.2/30, Dropbear SSH по ключу.

Adreno610/FD610 с Mesa Freedreno работает аппаратно. MSM `separate_gpu_kms=1`, MDSS удерживается override `lemon-stage-b-hold`.

**На физическом LCD уже показан настоящий GNOME50.3/Mutter50.2:** FD610 → headless GNOME → local RDP TLS/NLA → Weston14/Pixman → SimpleDRM → LCD1080×2340. Владелец подтвердил GNOME, Console, Activities и возврат tty1. GNOME Physical LCD v2.1: VT2 освобождается без EBUSY, GPU возвращается suspended, PSS около887MiB, UFS writes не изменились. GJS GC-critical `ShellWindowTracker::notify` при shutdown остаётся известной проблемой; не делать его главным приоритетом.

Это не native MDSS/DSI bring-up: LCD использует уже работающий унаследованный тракт. Stage C/B для повторной инициализации питания LCD остаётся NO-GO.

## Последняя задача: touchscreen

Исторические TWRP logs: NT36672A, trim `0A 00 00 72 66 03`, PID0x5940, runtimeFW5. GENI SE2 at0x4a88000. Stock DT child `novatek@1` обманчив: stock probe принудительно делает chip_select=0. Это подтверждено disassembly сохранённого TWRP Image. **Нужен runtime CS0. Старые CS1 driver/DTB не применять.** Mode0,8bit,9,6MHz. IRQ TLMM93 rising, reset TLMM103. Stock SPI pads6/7/71/80. Все три supplies shared с LCD: PM6125L9 VDDIO, PMI632LCDB LAB/IBB.

Подготовлен отдельный `touchscreen-v1/stage1-r2/`: IRQ-driven input MT driver с10slots, fail-closed liveFW5/PID5940/1080×2340, без reset/power votes/firmware upload. GENI r2 отказывает при отсутствии SPI engine firmware вместо auto-upload. `recording_authorized` defaultfalse запрещает input.open до отдельного допуска; это не emergency-stop для уже открытого reader. ARM64 modules с точным vermagic v8b находятся в `artifacts/touchscreen-stage1-final/`.

В saved recovery generic/Tianma normal blob имеет metadata5, Truly blob — metadata6. Лог TWRP содержит request Truly, sysfs firmware fallback и runtime5, но не hash фактически доставленного payload. Причина различия не доказана. Не подменять Truly файлом Tianma и не загружать FW6 по догадке.

**Первая live-проверка остановилась до SPI**. SSH/NCM/COM4, boot readback SHA и tty1 проверены. L9 framework сообщил disabled/1800000uV/num_users0. Оба значения cached: mainline qcom_smd-regulator возвращает `vreg->is_enabled` и `vreg->uV`. Это не физическое измерение и не доказательство выключенной шины. Агент остановился из-за риска I/O back-power при неподтверждённом VDDIO. GENI/Novatek не загружены, child не создан, FW/PID не прочитаны, ABS_MT событий нет. Пользователь подтвердил прежнюю консоль на LCD. Dmesg до/после идентичен, UFS write/discard не изменились. Reboot не выполнялся.

Следует независимо и предметно разобраться с подтверждением существующего VDDIO и минимальной CS0 runtime registration. MODULE_UNLOAD=n: rmmod не является rollback. Последнее согласование владельца допускало восстановительную перезагрузку, но новый агент не должен автоматически запускать hardware tests без уточнения актуального состояния/разрешения владельца.

## Где смотреть

- `TOUCHSCREEN_STAGE1_FINAL.md`: stock/binary evidence, supplies, firmware5/6, side effects, recovery constraints.
- `TOUCHSCREEN_FIRST_LIVE_RESULTS.md`: точный последний live preflight; логи в `logs/touchscreen-first-live/20261107T180106Z/`.
- `logs/touchscreen-stage1-final/`: binary xrefs, source line index, сборка r2, offline tests, preservation checks.
- `touchscreen-v1/`: драйверы, codec/evdev tests, calibration, corrected FreeRDP pointer fallback, read-only diagnostic script, separate session overlay. `stage1-test.py --run` намеренно отказывает; активная registration пока не реализована.
- `userspace/gnome-physical-v2.1/`: рабочая graphics session и контроль с Windows. `GNOME_PHYSICAL_V21_HARDWARE_RESULTS.md`: подтверждения владельца и метрики.
- `config/`, `scripts/`, `bootshim/`: kernel/initramfs/USB/SSH/boot image build; некоторые старые scripts пишут boot — не запускать автоматически.
- `display-v8/`, `display-verification/`: драйверы и исследования display power, не разрешение активировать их.

## Исходный ПК и WSL

Основная Windows-папка:
`C:\Users\HadirPC\Downloads\platform-tools_r37.0.1-windows\Redmi9T-Native-Linux`

WSL workspace:
`/home/hadirpc/Redmi9T-Native-Linux`

Kernel tree:
`linux-05441d697f7f9a927264f4058cbbc6a03dfcac9d`, out `kernel-out-v8b`.

ARM64 Alpine SDK и изменённые исходники Mutter/GRD:
`gnome50-build.hT7bPE/build/`.

Локальные дополнительные source snapshots подготовлены в соседней Windows-папке `Redmi9T-GitHub-Transfer/wsl-sources/`; в компактный GitHub-репозиторий они не загружены.

Крупные проверенные boot/rootfs архивы остаются на ПК, см. JSON с путями/хешами. Нет смысла собирать всё заново, если Claude Code работает на том же ПК. На другой машине сначала получить нужные большие артефакты у владельца или восстановить сборку по scripts.

SSH private key и GitHub credentials не включены. Доступ к SSH использовал локальный key path из `logs/v6-authorized/test-client-identity.json` оригинального проекта и COM-verified host pin. Не отключать StrictHostKeyChecking. После reboot host key может измениться: сверять через COM.

## Как продолжить

1. Прочитать перечисленные отчёты и подтвердить текущую задачу владельца.
2. Не повторять весь GNOME/ядро порт и офлайн-матрицу без новой причины.
3. Сохранять различие source support / offline build / physical validation.
4. Не объявлять касания рабочими до сохранённых evdev down/move/up.
5. Когда evdev заработает, подготовленный путь: touch → libinput/Weston → local RDP client → GNOME. Первая интеграция pointer-emulation, не полноценный multitouch. Физическая калибровка ещё не выполнена.
