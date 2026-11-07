# Touchscreen v1 — результаты, 7 ноября 2026

**Последующее исправление:** stock DT child@1 не означает runtime CS1. Source и saved TWRP Image подтверждают принудительный CS0; прежние CS1-модуль/DTB остаются только историческими structural fixtures. Итоговый источник решения — `TOUCHSCREEN_STAGE1_FINAL.md`; активный test NO-GO до подтверждения питания/handoff и recovery. Полные CS0 r2 module sources собраны отдельно, основной v8b не изменялся.

**Сенсор в работающем v8b не зарегистрирован.** Подготовлены ARM64-модули и отдельная интеграция ввода в проверенную графическую цепочку. Касания на телефоне ещё не испытаны. Рабочая GNOME Physical LCD v2.1 не изменена; GJS critical `ShellWindowTracker::notify` при завершении оставлен известной проблемой.

**Дополнение по отдельному разрешению:** собран офлайн disabled DTB-кандидат63732байта. Полные Linux+local fixture schemas, exact delta и5негативных тестов прошли. DTB не передавался на телефон; boot/kernel не пересобирались. Подробности и хеши: `touchscreen-v1/DTB_REVIEW.md`. Ниже сохранены результаты исходного этапа до этого разрешения.

## 1. Что установлено на телефоне

Read-only SSH-снимки: `logs/touchscreen-v1/20261107T132908Z` и `20261107T142712Z`. Первый неполный DT-снимок `132708Z` сохранён отдельно; выводы основаны на исправленном обходе `/sys/firmware/devicetree/base`.

- Linux `7.4.0-rc1-lemon-bringup-v8b`, tty1. В input subsystem только pm8941_pwrkey, pm8941_resin и gpio-keys; event0–2, без touchscreen/EV_ABS.
- `/sys/class/spi_master` и SPI devices пусты. Драйвера Novatek нет.
- SPI2 `/soc@0/geniqup@4ac0000/spi@4a88000` и wrapper уже имеют `status=okay`, но touchscreen child отсутствует. Альтернативный I2C по тому же адресу выключен. Номер Linux `spiN` нельзя вывести из имени SE2.
- В конфигурации v8b `CONFIG_SPI_QCOM_GENI` выключен. `CONFIG_SPI_QUP=y` — другой драйвер, его наличия недостаточно. GENI SE, SPI, evdev и input touchscreen включены; GPI DMA выключен.
- `CONFIG_MODULE_UNLOAD=n`: выгрузка модулей не может служить планом отката.

Диагностический скрипт `touchscreen-v1/diagnose.py` не открывает event/SPI/I2C devices, не пишет в sysfs и не монтирует файловые системы. Сравнение до/после: все17 полей статистики шести UFS LUN неизменны, dmesg идентичен, GPU suspended, MDSS hold сохранён. Новые модули не загружались. Это проверка наблюдаемых счётчиков, не независимое электрическое измерение.

## 2. Подтверждённая топология

Основание: сохранённые DT `reports/live.dtb` из TWRP и `reports/stock-overlay-result.dtb`, stock DTS `reports/stock-merged.dts`, журналы TWRP v7/v8, Xiaomi lime-q-oss commit `02ca1a919564a9b176a79cce09c40977f833e9ac`. `stock-audit.py` разрешает phandle внутри каждого DT отдельно; значения phandle между образами различаются.

| Параметр | Доказательство | Ограничение |
|---|---|---|
| Novatek NT36672A | Архивный trim `0A 00 00 72 66 03` и маска таблицы Xiaomi | В этой загрузке контроллер не опрашивался |
| Project ID `0x5940`, runtime FW `0x05` | Реальные архивные TWRP dmesg | Текущее содержимое SRAM неизвестно |
| Transport | GENI SE2, MMIO `0x4a88000`, stock child `novatek@1`, CS1, mode0,9,6MHz | Это SPI, не I2C; имя spi1.1 из stock не переносится автоматически |
| SPI pins | TLMM6/7/71 qup2,6mA,pull-down; TLMM80 qup2,6mA,pull-up | Stock-имя группы содержит cs0, child при этом CS1; сохранены оба факта, не назначен другой GPIO |
| IRQ | TLMM93; Xiaomi `IRQ_TYPE_EDGE_RISING` | Raw stock flags `0x2001` не перенесены как mainline IRQ flags |
| Reset | TLMM103, stock raw flags0 | Логическая assertion polarity и допустимость reset отдельно не доказаны; драйвер GPIO не запрашивает |
| VDDIO | PM6125 L9 | Текущее электрическое состояние не измерено |
| LAB/IBB | PMI632 LCDB LDO/NCP, shared LCD supplies | Не включались, не отключались и не добавлены новые votes |
| Event map | NT36672A trim table: `0x21c00`, FWINFO+0x78, PID+0x9a | Другие Novatek maps не подставлялись |
| Геометрия | Stock FWINFO/driver defaults1080×2340,10 контактов | Физическая калибровка ещё не выполнена |

Первоисточники: [Xiaomi NT36672A](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/tree/02ca1a919564a9b176a79cce09c40977f833e9ac/drivers/input/touchscreen/NT36672A), [stock GENI SPI](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/02ca1a919564a9b176a79cce09c40977f833e9ac/drivers/spi/spi-geni-qcom.c). Локальные excerpts, SHA и независимое разрешение supplies/pinctrl: `logs/touchscreen-v1/stock-topology.json`.

## 3. Firmware: обнаружено расхождение, загрузка запрещена

Из сохранённого vendor и recovery на ПК извлечён один и тот же normal Truly blob `nt33672a_truly_novatek_ts_fw.bin`:118784байта, SHA256 `36dccc95785b40bb5bc0cc4764bc80dc066ce358dd7fb3c1afebaca670b9276f`. Структура содержит NVT end marker, write size110592 и metadata version6; архивный runtime сообщает FW5. Почему эти версии различаются и какой именно blob фактически подал прежний TWRP userspace, не установлено. Файл не объявляется доказанно совместимым или несовместимым по одному различию версий.

Парсер проверяет границы заголовков/секций и version complement. Его additive checksum **не является подтверждением hardware CRC, подписи, SRAM allowlist или безопасности загрузки**. Firmware не отправлялась контроллеру. Бинарники из личных backups не включены в распространяемый пакет.

Выбран ограниченный handoff-only драйвер: принимает только уже работающую FW5/PID5940 с валидной геометрией. Если firmware не сохранилась после загрузки, он откажет. Cold boot, reset и firmware upload этим этапом не решены.

## 4. Подготовленный код

- `nvt-spi.c` + `nvt-frame.c/.h`: настоящий Linux SPI/input driver, IRQ-thread,10 direct Type-B slots, EV_ABS/MT positions и tracking IDs. Перед публикацией проверяется целый пакет. Corrupt/I/O frame освобождает касания;3 последовательные ошибки защёлкивают fault и отключают IRQ без reset/retry. Close/suspend синхронизируют IRQ вне mutex; resume повторно проверяет identity. Есть read-only fault attribute.
- Два opt-in: module parameter `stage1_authorized` и property `xiaomi,validated-touch-handoff`. Они предотвращают SPI-запросы драйвера без допуска, но не делают core/pinctrl probe аппаратно пассивным. Единственные writes после допуска — штатный выбор event-buffer page; прошивка, reset, power switching и произвольные register APIs отсутствуют.
- `spi-geni-qcom.ko`: отдельно собранный штатный GENI с локальным patch raw CS delay200/interword0. Поля записываются в существующем powered FIFO/SE-DMA пути с сохранением reserved bits. Непроверенный GPI DMA с opt-in отклоняется. Значение200 не переименовано в наносекунды. Это private property/patch, не upstream binding.
- Оба модуля имеют vermagic текущего v8b. Собраны внешними модулями, kernel Image/config SHA не изменились. `touch-handoff-review.dtsi` — только исходник для review, child disabled, authorization property отсутствует. **Новый DTB, Image и boot.img не создавались.**

## 5. Ввод Weston → RDP → GNOME

В реальном [FreeRDP3.32.2 Wayland input code](https://github.com/FreeRDP/FreeRDP/blob/3.32.2/client/Wayland/wlf_input.c) обнаружена передача contact ID в аргумент pressure при motion. В отдельной сборке исправлен порядок аргументов, добавлена обработка touch cancel. Собраны `wlfreerdp3-touch` и необходимая `libuwac0.so.0` с сохранением TLS/NLA.

`touch-pointer.so` реализует явный одноточечный fallback: `drag` даёт tap/drag мышью; `scroll` — отдельно выбранный режим wheel. Второй контакт игнорируется, up/cancel освобождает кнопку. Это не remote multitouch, не автоматическое распознавание жестов и не подтверждение GNOME OSK.

`session-touch.sh` — отдельная копия с небольшим patch к v2.1. В согласованном будущем сеансе один проверенный event device и его udev metadata появляются только в private Weston root/namespace. Глобальные /dev/input, /run/udev и права не меняются; uinput не используется. Полная цепочка с реальным libinput touchscreen ещё не проверена. Исправление callback и синтетический evdev тестировались отдельно.

## 6. Офлайн-проверки

| Проверка | Результат и границы |
|---|---|
| ARM64 сборка двух модулей, W=1 | PASS; ABI v8b; Image/config SHA совпали |
| Native SPI/IRQ/PM lifecycle | Сборка и source review; реальный probe, unbind, suspend/resume и аппаратная fault injection ещё не испытаны |
| checkpatch sensor/GENI patch |0 errors/0 warnings; это style check, не аппаратное подтверждение |
| NVT parser в ARM64 QEMU | PASS checksum, bounds, duplicate ID, watchdog/service frames, release |
| Настоящий evdev в QEMU с v8b Image | PASS Type-B slots, tracking IDs,2контакта, motion/release,1080×2340; test module запрещает запуск на телефоне |
| Raw GENI delay helper ARM64 | PASS200/0, reserved bits, граница1023, отказ1024 без изменения output |
| FreeRDP actual Wayland callbacks ARM64 | PASS down/motion/up с ID4, second contact, cancel, scroll |
| GNOME/GRD/Weston с новым клиентом и fallback | PASS офлайн software QEMU/X11; Console/Activities/Settings, реальные кадры, cleanup0 и namespace clear. Не новая проверка FD610 или physical touch |
| Калибровка | PASS16комбинаций rotation/inversion, offsets и invalid points; synthetic identity candidate не установлен |
| Firmware parser negatives | PASS5повреждений на synthetic fixture; hardware CRC не проверен |
| Финальная read-only диагностика | UFS all17fields unchanged,0новых dmesg,модули не загружены |

В сборке input helpers остались deprecation warnings из публичных FreeRDP headers; ошибки компиляции не подавлялись. Логи находятся в `logs/touchscreen-v1/`.

Калибровка должна измеряться пальцем по центру/четырём углам, drag/release и периоду без касаний. Кандидат0..1079/0..2339 соответствует stock input ABI, но orientation/offset/phantom touches ещё не измерены. `calibration.py` формирует матрицу и проверяет границы без изменения режима LCD.

## 7. Следующее испытание и блокеры

Подробный поэтапный план: `TOUCHSCREEN_STAGE1.md`. Сейчас **NO-GO для активного сенсорного probe**: не подтверждено текущее VDDIO/SRAM handoff, не согласован способ регистрации SPI child, не испытано безопасное прекращение GENI/sensor при CONFIG_MODULE_UNLOAD=n. Локальный драйвер намеренно не устраняет это включением общих LCDB supplies или reset.

Первый аппаратный этап должен ограничиться identity/handoff, затем отдельный10s evdev; GNOME-touch — только после verified events и калибровки. Неизвестное питание, неверные FW/PID, отсутствие ответа, ошибки SPI/IRQ или изменение LCD — отказ без автоматического reset, загрузки firmware и повторной попытки. Нельзя обещать, что watchdog процесса отменит зависший hardware transfer.

Отдельно разрешённая офлайн-сборка DTB уже выполнена; это не разрешение на аппаратную активацию. Питание/SRAM handoff и способ применения дерева остаются gates следующего этапа.

## 8. Сохранность и поставка

Snapshot `snapshots/gnome-physical-lcd-v2.1`:79файлов, все SHA проверены. В нём исходники, архив, логи и восстановление tty1. Исходные v2.1 scripts и ARM64 archive не изменены. Stage C/B для повторного включения LCD остаётся NO-GO.

`artifacts/lemon-touchscreen-v1-aarch64-review.tar.gz` — дополнение к существующей v2.1, не загрузочный образ и не автоматически запускаемый installer. Содержит исходники, ARM64 binaries, тесты, доказательства и манифест. Полные kernel/SDK/rootfs, личные firmware и SSH-ключи исключены. SHA/размер архива — `artifacts/touchscreen-v1/release.json`.
