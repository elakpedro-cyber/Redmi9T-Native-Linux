# Актуально: первый live Touchscreen preflight остановлен до SPI

После разрешения владельца проверены текущие v8b/SSH/NCM/COM4 и readback boot: SHA совпал с резервной v8b. Live L9 сообщил cached state=disabled,uV=1800000,num_users0. Физическое VDDIO не измерено; из-за риска I/O back-power при возможном отсутствии питания остановлено до GENI/module load/CS0 child/SPI. Касаний нет, fw/PID не читались. Показание cache не объявляется доказательством физического выключения. Пользователь подтвердил консоль на LCD; dmesg идентичен, UFS write/discard неизменны, GPU suspended. Перезагрузки/прошивки не было. [Живой результат](TOUCHSCREEN_FIRST_LIVE_RESULTS.md). Требуется подтверждение существующего VDDIO без переключения общих rails, а не ещё одна офлайн-матрица.

---

# Актуально: Touchscreen Stage1 Final — runtime CS0, активный тест NO-GO

7 ноября 2026: найдено и проверено важное исправление: Novatek stock DT child@1 переопределяется драйвером на CS0. В сохранённом TWRP Image подтверждён zero-store в byte chip_select перед spi_setup. Старые CS1-модуль и DTB63732байта сохранены, но отозваны для активного применения. Отдельно собраны r2 CS0-модуль и GENI с запретом auto firmware upload. В saved recovery найдены generic/Tianma metadata5 и Truly metadata6; payload hash TWRP fallback неизвестен, причина runtime5 ещё не доказана. Все3touch supplies общие с LCD. Проверенный rollback GENI/pinctrl без MODULE_UNLOAD/reboot отсутствует; active runner отказывает с78 до device access. Телефон не опрашивался/не изменялся, GNOME v2.1 и v8b сохранены. [Окончательный план](TOUCHSCREEN_STAGE1_FINAL.md). Не выполнять старый unbind/CS1 план.

---

# Актуально: Touchscreen v1 — подготовлен офлайн, аппаратно не запускался

После отдельного разрешения собран disabled DTB-кандидат63732байта, SHA256 `3b0f9e4281cabcd2a1e6120f6373250e7881866d51743d2075235af98a8605d4`. Exact delta, memory reservations, полные schemas и5negative checks прошли. Сохранены все display/power/UFS properties и контрольные v8b/GNOME SHA. Обычный dtc roundtrip был отклонён из-за изменения L15 property; финальная сборка использует бинарный fdtoverlay. Файлы и детали: `touchscreen-v1/DTB_REVIEW.md`. На телефоне никаких действий, активный Stage1 по-прежнему NO-GO.

2026-11-07: приоритет переключён на встроенный Novatek. Read-only SSH подтвердил отсутствие touch input, GENI SPI master и touch child в текущем DT; сам SPI2/SE2 включён, но CONFIG_SPI_QCOM_GENI выключен. Архивные trim/PID5940/FW5 и stock pins/supplies сопоставлены с исходниками. Подготовлены внешние ARM64-модули handoff-only NT36672A и GENI с raw-delay patch, отдельный FreeRDP pointer fallback и private input integration. QEMU evdev/Type-B, реальные FreeRDP callbacks, calibration и full offline GNOME/RDP regression прошли. На телефон ничего не загружалось; новый DTB/boot не собирался.

Firmware blob из vendor/recovery имеет metadata6, архивный runtime FW5: связь не установлена, upload запрещён. Текущий VDDIO/SRAM handoff не подтверждён. CONFIG_MODULE_UNLOAD=n исключает rmmod rollback. Активный Touch Stage1 пока NO-GO до согласования этих gates и способа SPI child registration. GNOME v2.1 сохранена отдельно: snapshot79файлов, SHA проверены. Шесть UFS stats и dmesg до/после диагностики совпали, GPU suspended/MDSS hold. GJS shutdown warning оставлен известной проблемой по указанию владельца. [Отчёт](TOUCHSCREEN_V1_RESULTS.md) · [Этапы испытания](TOUCHSCREEN_STAGE1.md) · [Исходники](touchscreen-v1/README.md).

---

# Актуально: GNOME Physical LCD v2.1 проверена на LCD

2026-11-07: после отдельно разрешённого GPU restore проведён один C-сеанс с watchdog60s. Владелец подтвердил GNOME/Console/Activities и возврат tty1. FD610 подтверждён Mutter, exit0, VT2 освобождена без EBUSY, rootfs RAM удалена, GPU suspended, SSH/NCM/COM4 доступны, все UFS stat неизменны. PSS886.91MiB против891.44MiB v2 — один sampled run, не доказательство оптимизации.

Старые lifecycle/TLS/fd0/WindowPreview ошибки не повторились, но появился GJS GC-critical ShellWindowTracker::notify при выходе. Следующая работа — офлайн-анализ этого дефекта; без нового аппаратного запуска. Проверенная v2 сохранена. Полный отчёт: GNOME_PHYSICAL_V21_HARDWARE_RESULTS.md. Stage C/B NO-GO сохраняется.

---

# Последний аппаратный preflight v2.1 — остановлен до старта

2026-11-07: владелец восстановил Windows USB IP, SSH и COM4 работают. В текущей загрузке v8b нет MSM/renderD128 и override MDSS. GNOME v2.1 НЕ запускалась; GPU не восстанавливался. Счётчики записи шести UFS LUN неизменны, новых GPU/IOMMU faults нет. Для продолжения необходимо отдельное разрешение на проверенное GPU-only восстановление. Подробности: `GNOME_PHYSICAL_V21_HARDWARE_RESULTS.md`. v2 и пакет v2.1 остаются неизменёнными.

---

# Актуальная контрольная точка — GNOME Physical LCD v2.1 (offline)

2026-11-07: v2 сохранена неизменяемой в `snapshots/gnome-physical-lcd-v2` (83 файла, проверка SHA/size). v2.1 — отдельная userspace/RAM-only сборка: исправления Session/Shell logout, GRD fd cleanup, атомарная TLS конфигурация, ownership check, memory/copy instrumentation. На телефоне v2.1 не запускалась. Стабильной аппаратной точкой остаётся подтверждённая v2 C, v8b не изменён.

Архив/хеши: `artifacts/gnome-physical-v2.1/release.json`. Начать с `GNOME_PHYSICAL_LCD_V21.md` и отчётов WARNINGS, VALIDATION, MEMORY_PERFORMANCE, TOUCH. Есть оставшийся Glycin sandbox warning и неполные desktop services: не объявлять все предупреждения исправленными или систему готовой к повседневному использованию. Новые аппаратные FPS/latency не измерены.

Следующий шаг — только после отдельного разрешения один C-тест до60s. Не загружать MSM автоматически. Stage C/B NO-GO для повторной инициализации дисплейного питания; никакой прошивки/UFS/PMIC/DSI. Touchscreen пока без работающего input device.

---

# Redmi9T-Native-Linux — контрольная точка

**Аппаратное обновление v2 C, 7 ноября.** Выполнен один согласованный сеанс с watchdog 60 с, Stop запрошен на 45,94 с. Пользователь подтвердил GNOME/Console на LCD и возврат консоли; PNG содержит ответ команды GNOME_LCD_INPUT_OK. FD610 подтверждён, VT2 освобождена без EBUSY, UFS counters неизменны, новых kernel/GPU faults нет. Полный RAM tree удалён; v8b оставлен на tty1, GPU suspended. Есть userspace shutdown warnings после исчезновения GRD virtual monitor — следующий шаг их офлайн-исправление. B остаётся только офлайн. [Аппаратный отчёт](GNOME_PHYSICAL_V2_HARDWARE_RESULTS.md).

**Обновление 7 ноября: GNOME Physical LCD v1/v2.** Пользователь подтвердил GNOME на LCD в двух сеансах. Путь: GNOME/FD610 → local RDP → Weston/Pixman → SimpleDRM. Неизменяемая копия v1 — `snapshots/gnome-physical-lcd-v1/` с SHA-256. Подготовлена отдельная v2: безопасный VT cleanup, start/stop из Windows, lifecycle adapter Session 48/Shell 50, frame counters и экспериментальный Devkit без RDP. Новые проверки v2 выполнены только на ПК. Touchscreen в v8b input subsystem отсутствует; native KMS A заблокирован. Следующее действие — отдельно согласованный короткий тест v2 C. [Состояние v2](GNOME_PHYSICAL_LCD_V2.md) · [Офлайн-валидация](GNOME_PHYSICAL_V2_VALIDATION.md).

**Последняя контрольная точка.** v8b и исходный аппаратно проверенный GNOME SquashFS сохранены. Отдельный Desktop SquashFS с GNOME 50.3 и Mutter 50.2 проверен на физическом Redmi 9T через FD610 и RDP. Console, Settings, Files и Text Editor открывались одновременно. Мышь, клавиатура и смена окна подтверждены. Телефон оставлен работающим на v8b, GPU suspended, SSH/NCM/COM4 доступны. Stage C/B остаётся NO-GO. [Desktop и хеши](V8_GNOME50_DESKTOP_INTEGRATION.md) · [Физический KMS](V8_GNOME50_PHYSICAL_DISPLAY.md)

| Версия | Что достигнуто |
|---|---|
| v1 | Разбор AOSP boot header v2, page 4096 и stock DTB. Минимальные ARM64 Linux и BusyBox, анализ ABL и плана восстановления. Временный fastboot boot для установленного ABL не принят как рабочий путь. [Загрузка](BOOT.md) · [ABL](BOOTLOADER_RESEARCH.md). |
| v2 | Stock DTBO содержит одну entry. Несовместимость с mainline решена двумя деревьями: stock для ABL, mainline для Linux, между ними bootshim. Офлайн проверены DTBO и boot image. [DTBO](DTBO_COMPATIBILITY.md). |
| v3 | Исправлены DAIF и cache handoff, проверены EL1/EL2 в эмуляции. На телефоне подтверждены /init, COM3, SimpleDRM, RAM и адрес bootshim 0x40080000. UFS ещё не работал. [Аудит](V3_AUDIT_FIXES.md) · [Живая диагностика](V3_LIVE_DIAGNOSTICS.md). |
| v4 | Штатный Qualcomm UFS, Micron и шесть LUN sda–sdf с логическим сектором 4096 байт. Сохранены рабочий образ и контрольные логи. [v4](V4_CONTROL.md). |
| v5 | Alpine 3.24.4, apk и OpenRC в RAM, аварийная ACM shell и UFS без монтирования разделов. [Валидация](V5_VALIDATION.md). |
| v6 | Составной ACM/NCM, COM4, Windows 192.168.77.1/30 и телефон .77.2/30, Dropbear по ключу, передача SCP/SFTP с SHA. [Аппаратный результат](V6_HARDWARE_RESULTS.md). |
| v7 | Adreno 610, MSM render node, Freedreno FD610, 256 пикселей с проверенным readback. Дисплей оставался на SimpleDRM. [GPU](V7_HARDWARE_RESULTS.md). |
| v8 Stage A | Проверены базовая система и GPU с добавленной дисплейной подготовкой. Нативный дисплейный тракт не активировался. [Stage A](V8_STAGE_A_RESULTS.md). |
| v8b Stage B | Зарегистрированы DSI Host, PHY и его clock provider. DISPCC PLL0 показал 768 МГц и lock bit. Lock отдельного DSI PHY PLL не проверен. Панель, bias, подсветка и сенсор не запускались. [Stage B](V8_STAGE_B_RESULTS.md). |
| v8b Stage C/A и preflight | Сняты read-only clocks/regulator/genpd данные. Разобраны TD4330 Truly v2, PMI632 LCDB, REFGEN и вариант подсветки. LCDB safety variant собран ARM64, прошли 70 одиночных, 12 вложенных инъекций и 128 конкурентных сценариев на mock. [Stage C/A](V8_STAGE_C_A_RESULTS.md) · [LCDB](V8_LCDB_FAULT_INJECTION.md). |
| v8b headless | Восстановлен Windows NCM после потери ActiveStore адреса. На телефоне подтверждены Weston/Pixman и аппаратный Weston 14.0.2 GL/Mesa 26.1.6 FD610 через renderD128. Кадр Wayland 320×240 передан с проверкой SHA. [USB](V8_USB_NETWORK_DIAGNOSIS.md) · [Weston GL](V8_HEADLESS_GPU_RESULTS.md). |

## Перед выключением

Снимок SSH и COM4 подтверждает Alpine 3.24.4, apk 3.0.9, OpenRC default (health/net/sshd), NCM, ACM и шесть UFS LUN. Дисковых mounts и swap нет. MSM загружен с `separate_gpu_kms=1`, Adreno runtime suspended, MDSS удерживается override, DISPCC и DSI Host/PHY не привязаны. В /tmp пусто, Weston и shader-процессов нет. Этот снимок описывает RAM-состояние текущей загрузки. [Логи](logs/project-checkpoint/).

Рабочий образ `artifacts/boot-linux-test-v8b.img`, 24 707 072 байта, SHA-256 `9ce181e8a6170ce8773a923f03dd10f5edb405d1990fa09b4f4bc12f2e59a610`. Контрольная копия и [манифест](snapshots/v8b-hardware-validated/manifest.json) на ПК. Исходные Android backups остаются в `../platform-tools/Redmi9T_Backup`. [Восстановление v8b](V8_STAGE_C_FIRST_BOOT.md#recovery-после-будущего-испытания).

## Блокеры и дальнейшая работа

**Stage C/B NO-GO.** Для TD4330 остаются неизвестными REFGEN SM6115, фактические bias и разряд PMI632 LCDB, DSI PHY PLL/LP11, точная ревизия платы и установленный U2732. Следующий безопасный шаг после возобновления — офлайн упаковка проверенного Weston GL launcher и пассивная сверка платы специалистом. [GO / NO-GO](V8_STAGE_C_SAFETY_REVIEW.md) · [Проверка платы](BOARD_VERIFICATION_GUIDE.md) · [Продолжение](RESUME_INSTRUCTIONS.md).

## Завершение сеанса

Сохранён и проверен [архив контрольной точки](snapshots/project-checkpoint-20261106.zip), 347 файлов и внутренний манифест. SHA-256 архива `43221a581d978cfc6f44ec45c22d567cc1c9af022e42d81bdfef8d4898291e9d`. Это снимок до выключения. Финальные журналы выключения сохранены рядом в рабочем проекте.

6 ноября выполнена одна штатная команда `/sbin/poweroff` через COM4 после проверки версии. Маркер выполнения получен, NCM исчез первым, затем COM4 и родительское composite устройство. Независимого измерения питания или визуального подтверждения нет. Повторных попыток, перезагрузки или перехода в TWRP не было. [Транскрипт COM4](logs/project-checkpoint/poweroff-com4.raw) · [Наблюдение Windows](logs/project-checkpoint/usb-after-poweroff.json).

## Дисплей и сенсор после Desktop

Stage C/B остаётся NO-GO. Добавлены офлайн-патчи REFGEN guard, PHY PLL rollback и LM36923, доработаны LCDB и TD4330, собран декодер/MT Novatek. Ветку физического KMS продолжать с подтверждения ревизии NFC-платы и источника REFGEN. В рабочий boot и Desktop SquashFS изменения не внесены. [Инженерный отчёт](V8_DISPLAY_TOUCH_BRINGUP.md) · [План A–I](V8_DISPLAY_TOUCH_FIRST_LIGHT.md) · [Хеши](logs/v8-display-touch/control-sha256.txt)

Итоговый допуск обновлён после повторной сверки оригинальных образов. Архивы подтвердили trim/PID Novatek NT36672A и отдельный stock DSI PHY VDD_MX vote. Физическая ревизия, реальный REFGEN, VDD_MX lifecycle и разряд bias остаются открытыми. [Электрическая карта](REDMI9T_DISPLAY_HARDWARE_MAP.md) · [Окончательный checklist](DISPLAY_FIRST_LIGHT_GO_NO_GO.md).

REFGEN остаётся UNKNOWN. Stock PHY NOM 256 перенесён в отдельный disabled review DTB через genpd/OPP. Эквивалентность off/RETENTION открыта. [Итоговый анализ](REFGEN_SM6115_FINAL_ANALYSIS.md) · [Checklist](DISPLAY_FIRST_LIGHT_GO_NO_GO.md).

Подготовлен [инженерный пакет для физической проверки](artifacts/Redmi9T-Display-Hardware-Verification.zip). Аудит подтвердил различие stock RETENTION и снятия vote в genpd, без доказательства электрического эффекта. Следующий шаг — пассивная сверка конкретной платы специалистом. Измерения под питанием и first light требуют отдельных допусков. Stage C/B остаётся NO-GO. [Рабочие документы](display-verification/README.md) · [Хеши v8b и GNOME](logs/display-verification-package/control-sha256.txt).

Собран [отдельный диагностический boot](artifacts/first-light-diagnostic/boot-linux-v8b-first-light-diagnostic.img) с ядром и initramfs v8b, новым отключённым DTB и проверенным ARM64 handoff. В живом v8b read-only подтверждён framebuffer, физический scanout не установлен. Панель не активировалась. [Результаты первого этапа](V8_FIRST_LIGHT_EXPERIMENT.md)

7 ноября 2026 подтверждён настоящий GNOME Shell 50.3/Mutter 50.2 на физическом LCD через FD610 → локальный RDP → Weston/Pixman → SimpleDRM. Пользователь подтвердил два ограниченных сеанса, Console, смену экранов и возврат VT1. Проверены ввод команды, обзор приложений и два окна. Журналы и кадры сохранены на ПК, RAM-пакет телефона удалён. Native KMS GNOME пока не реализован. [Аппаратный отчёт](V8_GNOME50_PHYSICAL_LCD_RESULTS.md)
