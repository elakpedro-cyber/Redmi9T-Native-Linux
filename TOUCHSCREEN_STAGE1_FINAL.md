# Touchscreen Stage 1 — окончательная подготовка

7 ноября 2026. Все действия этого этапа выполнены на ПК/WSL. Телефон не опрашивался, модули не загружались, DTB не применялся, питание/GPIO/SPI не изменялись.

**Решение: NO-GO для активного теста.** Найдена и исправлена важная ошибка в предположении о CS. Подготовлены отдельные ARM64-модули r2. Но безопасный возврат аппаратного состояния после GENI probe без rmmod/reboot пока не доказан; текущие питание и SRAM firmware также не подтверждены. Скрипт не превращает эти UNKNOWN в разрешение.

## 1. Подтверждённые параметры

| Параметр | Факт и источник | Статус для активного теста |
|---|---|---|
| Контроллер | Исторический trim `0A 00 00 72 66 03`, PID5940, runtimeFW5; TWRP v7/v8 dmesg | Исторически подтверждён; текущая SRAM неизвестна |
| Шина | Stock `/soc/spi@4a88000`, mainline `/soc@0/geniqup@4ac0000/spi@4a88000`; GENI SE2 | Подтверждено DT; Linux bus number динамический |
| Chip select | DT содержит `novatek@1`, но Xiaomi probe делает `client->chip_select = 0`; это подтверждается сохранённым TWRP Image | **Runtime CS0. Старый вывод CS1 отозван** |
| SPI mode / word / speed | Mode0,8bit,MSB-first, max9600000Hz: stock probe, header и реальные TWRP логи | Подтверждены настройки; реальная частота на проводе не измерялась |
| CS polarity | SPI_MODE_0 без SPI_CS_HIGH; stock GENI очищает inversion и выбирает chip_select | Активный low по настройке; текущий уровень неизвестен |
| CS delay | Stock raw200, interword0 | Подтверждены поля; не переведены в выдуманные ns |
| Data/clock pins | TLMM6/7/71 qup2,6mA,pull-down | Stock default pinctrl, не измерение уровней |
| CS pin | TLMM80 qup2,6mA,pull-up, группа `qupv3_se2_spi_cs0_active` | Согласуется с runtime CS0 |
| Sleep pins | TLMM6/7/71 gpio,6mA,pull-down; TLMM80 gpio,6mA,pull-up в stock sleep groups | Это штатная конфигурация, не доказанный безопасный откат текущей v8b |
| IRQ | TLMM93; GPIOF_IN в stock, trigger1/rising и IRQF_ONESHOT; raw DT flags0x2001 | Номер/trigger подтверждены; электрические idle/pull не установлены |
| Reset | TLMM103; stock request GPIOF_OUT_INIT_LOW, затем eng-reset и вывод1 | Активный reset используется stock; handoff без него не доказан |
| VDDIO | `touch_vddio` → PM6125 L9; stock driver запрашивает1800000uV | Provider подтверждён, фактическое напряжение неизвестно |
| LAB | `touch_lab` → PMI632 LCDB LDO | Общий с LCD; новые votes запрещены |
| IBB | `touch_ibb` → PMI632 LCDB NCP | Общий с LCD; новые votes запрещены |
| Координаты | Stock1080×2340,10contacts; input ABI X0..1079,Y0..2339 | Геометрия подтверждена; физическая калибровка ещё нет |

Точные пути, phandle resolution **внутри каждого** stock blob, ссылки consumer→provider и номера строк исходников сохранены в `logs/touchscreen-stage1-final/stock-comparison.json` и `logs/touchscreen-v1/stock-topology.json`. Это доказательство программного описания платы, не измерение разводки/напряжения.

## 2. Исправление CS: DT-адрес не равен фактическому demux

Исходник `touchscreen-v1/sources/xiaomi/NT36672A/nt36xxx.c` принудительно меняет chip_select до spi_setup. Stock GENI использует это изменённое поле для demux. Поэтому имя устройства `spi1.1` сохраняет DT-адрес, но не подтверждает CS1 во время обмена.

Проверен именно сохранённый TWRP Image30978064байта, SHA256 `4e9946d0160031469fe1d664e75d1e282539ca92dddd21349bd34188154ccdba`. По единственному xref строки `mode=%d, max_speed_hz=%d` найден контекст probe:

```text
file+0x7f98b4  strb wzr, [x23, #0x35c]   chip_select = 0
file+0x7f98d4  mov  w10, #8
file+0x7f98d8  strb w10, [x9, #0x35d]    bits_per_word = 8
file+0x7f98e0  strh wzr, [x9, #0x35e]    mode = 0
file+0x7f9958  ldrh w4, [x8, #0x35e]    mode для diagnostic print
file+0x7f995c  ldr  w5, [x8, #0x358]     max_speed_hz для того же print
```

Атрибуция полей основана на совпадающем source sequence и порядке u32/u8/u8/u16 в [stock spi_device header](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/02ca1a919564a9b176a79cce09c40977f833e9ac/include/linux/spi/spi.h). Это статический binary audit, не измерение CS осциллографом. Файлы: `stock-binary.json`, `probe-string-xrefs.txt`; воспроизведение: `python touchscreen-v1/audit-stock-binary.py`.

Попытка извлечь kallsyms через [vmlinux-to-elf1.2.2](https://github.com/marin-m/vmlinux-to-elf) не дала symbol table; ошибка сохранена. После неё использован локальный ARM64 string-xref/disassembly, ядро не исполнялось и не изменялось.

**Прежний DTB63732байта и старый CS1-модуль остаются архивными материалами. Они проходили структурные проверки, но более не считаются пригодными для аппаратного теста.** Их SHA/файлы не подменены. В r2 подготовлен disabled source `stage1-r2/touch-handoff-stage1-r2.dtsi` с CS0; нового DTB/boot на этом этапе не строили.

## 3. Питание: что совпадает с v8b

Stock Novatek и `qcom,dsi-display-primary` ссылаются на **одни и те же три provider**: L9/vddio, LCDB/ldo/lab и LCDB/ncp/ibb. Общие не только bias-шины, но и VDDIO. Следовательно, включение/отключение touch supplies нельзя считать изолированным от LCD.

В v8b реальный RPM-regulator L9 существует с constraints1,8–2,0V. В старом сохранённом Stage C/A sysfs он имеет имя l9 и num_users0. В последнем touch dmesg есть `l9: Bringing 0uV into 1800000-1800000uV`: это сообщение framework, не независимое измерение питания. Current use_count, constraints или факт работы LCD не доказывают напряжение на touch pad.

В основном v8b DT отсутствует LCDB provider subtree. Наличие унаследованного работающего LCD не означает, что mainline умеет корректно включать/выключать его bias. Handoff-only драйвер не запрашивает suppliers и ничего не меняет в PMIC. Dummy regulator не используется как доказательство питания.

Stock source и TWRP binary не полностью одинаковы: например, опубликованный source вызывает в конце probe `nvt_ts_enable_regulator(false)`, а реальные TWRP логи сообщают enable. Поэтому копировать такую последовательность как точную и безопасную для этой загрузки нельзя. Исторические consumer links к трём регуляторам подтверждены отдельно логами.

## 4. Reset, firmware и сохранность handoff

В stock путь включает reset GPIO, engineering/bootloader reset и firmware download. Queue boot-update ставится после probe с задержкой14s; комментарий требует учитывать display RESX sequence. В реальных логах TWRP FW5/PID5940 получены **после** `Update firmware success` примерно на15,95s. Это не доказательство, что bootloader передал рабочую FW5 без reset/upload.

В SRAM текущего v8b пока ничего не читалось. Нельзя ни утверждать, что reset обязателен для уже живой firmware, ни обещать успешный первый сеанс без reset. Выбранное поведение — отказ при отсутствии валидного handoff, без попытки его создавать.

В сохранённом recovery действительно присутствуют разные normal binaries:

| Файл | Metadata version | SHA256 |
|---|---:|---|
| `novatek_ts_fw.bin` |5|`aa62ec8f23094177537e121153a826ffa69f425901a4245e01051248c21edeaa`|
| `nt33672a_tianma_novatek_ts_fw.bin` |5|тот же SHA|
| `nt33672a_truly_novatek_ts_fw.bin` |6|`36dccc95785b40bb5bc0cc4764bc80dc066ce358dd7fb3c1afebaca670b9276f`|

Truly blob в saved vendor имеет тот же SHA, что в saved recovery. Однако TWRP журналирует request имени Truly, sysfs firmware fallback и затем runtime5, **не хеш фактически доставленного payload**. Generic/Tianma5 — новый конкретный источник возможного расхождения, но не доказательство, что загружен именно он. Другой путь userspace fallback/mounted vendor или несовпадение сохранённого firmware package с загрузкой остаются гипотезами. Metadata version и runtime byte также нельзя автоматически объявлять взаимозаменяемыми.

Таким образом, **точная причина5/6 не установлена**. Нельзя подменять Truly файлом Tianma, выбирать firmware только по числу5 или считать версия6 совместимой. Парсер не проверяет hardware CRC/signature. Все файлы анализировались в RAM ПК; ничего не отправлялось сенсору.

Fail-closed r2 требует live version5 и complement, PID5940,1080×2340, CS0 и явные opt-in properties. Любое несовпадение — отказ без reset/upload/retry. Исторический trim подтверждает выбранную event map0x21c00; активный trim-probe с reset в тест не включён.

## 5. GENI probe не является пассивной регистрацией

В v8b только SE2 SPI node enabled. Его probe/default pinctrl меняют mux GPIO6/7/71/80. GENI resources_activate включает clocks/interconnect resources; init читает protocol и пишет FIFO/IRQ/packing configuration. SPI setup выбирает demux/polarity/delay. Возможны indirect core power votes через framework. Прямых запросов LCDB/REFGEN или touch regulators в этом пути не найдено; это не доказывает безопасность переключения SPI pads при неизвестном VDDIO.

Оригинальный GENI при invalid protocol может автоматически вызвать `geni_load_se_firmware`. В отдельном модуле r2 эта ветка заменена отказом EOPNOTSUPP. Touch firmware и GENI firmware — разные вещи; автоматическая загрузка обеих не разрешается данным планом.

**r2 собран внешними модулями под точный vermagic v8b**, без kernel/config/boot rebuild. Файлы:

```text
artifacts/touchscreen-stage1-final/lemon_nt36672a_stage1_r2.ko
artifacts/touchscreen-stage1-final/spi-geni-qcom-stage1-r2.ko
touchscreen-v1/stage1-r2/                         полные источники
```

R2 не загружался на телефон. Предыдущие modules/DTB оставлены с исходными SHA. Даже r2 может менять состояние GENI до отказа — запрет upload не делает probe пассивным.

В r2 добавлен отдельный root-only parameter `recording_authorized`, defaultfalse. Input open до него возвращает EPERM **до SPI и enable IRQ**. Это важно: IRQF_NO_AUTOEN сам по себе не гарантирует тишину после input_register_device — input handlers могут открыть устройство автоматически. Выдавать recording permission можно только отдельным разрешённым шагом после identity. Это не аварийный stop: возврат flag=false не закрывает уже открытые readers и не заменяет их завершение. Lifecycle этого нового gate проверен статически/сборкой, не аппаратно.

## 6. Команды диагностики и побочные эффекты

Подготовлен `touchscreen-v1/stage1-readonly.sh`: только stdout, чтение framework metadata; не монтирует debugfs, не запрашивает GPIO, не открывает evdev/SPI/I2C, не вызывает gpioget, не читает /dev/mem. На этом этапе он проверен только в offline fixture, не запускался на телефоне.

Примеры включённых команд для будущего отдельно разрешённого сбора:

```sh
cat /proc/bus/input/devices /proc/interrupts /proc/modules
cat /proc/mounts /proc/swaps /proc/fb
cat /sys/class/tty/tty0/active
readlink /sys/bus/platform/devices/4a88000.spi/driver
cat /sys/class/regulator/regulator.11/name
cat /sys/class/regulator/regulator.11/num_users
```

Номер regulator.11 — исторический пример: выбирать по имени и of_node, не полагаться на номер после reboot. Уже доступный `pinmux-pins` показывает owner, **не уровень/напряжение**. Для неизвестных электрических параметров скрипт печатает UNKNOWN. Не применять GPIO request/export или переключение direction ради чтения.

Разрешаемые после открытия gates SPI-операции имеют эффекты:

| Операция | Что меняет / ограничение |
|---|---|
| Page select `FF 04 38` | Меняет адресную страницу на0x21c00; это write, не read-only |
| FWINFO offset78,16data bytes | Формирует SPI clocks/CS; отсутствие побочных read effects документально не гарантировано |
| PID page `FF 04 39`, offset1a,2data bytes | Меняет страницу на0x21c80; затем штатный restore0x21c00 |
| Неуспех передачи | Нельзя считать адресную страницу восстановленной или принудительно повторять обмен |
| evdev open | Вызывает identity checks и enable IRQ; даже O_RDONLY не пассивен |
| IRQ report read | Читает event packet, может обслуживать/снимать controller report condition; не нейтральный dump SRAM |
| evdev close | Disable/synchronize IRQ и release MT slots; не восстанавливает GENI/pinctrl/firmware page до точного исходного состояния |

## 7. Конкретный сценарий после открытия gates

Сейчас исполняемый gate runner:

```sh
python3 touchscreen-v1/stage1-test.py --check-only
```

Он возвращает **78/NO-GO** с причинами. `--run` также отказывает **до любого device access**. Это намеренно заблокированный runner подготовки, не утверждение о готовом активном тесте. Проверено, что команд загрузки модулей/registration/reset/unbind в нём нет.

Предлагаемый единственный активный сеанс после отдельного согласования:

1. Владелец рядом с телефоном; COM и SSH проверены. Сохранить tty1, binds, mux ownership, GPU/IOMMU,6UFS stats, mounts/swap. Не запускать GNOME и input consumers.
2. Подтвердить допустимость существующего VDDIO/reset-high handoff и отсутствие новых votes. Для физического напряжения недостаточно cached sysfs. Не включать shared rails.
3. Принять отдельно способ создания **CS0** child без прошивки текущего boot. В основном DT child отсутствует; source-фрагмент сам по себе не создаёт устройство. Runtime registration/новый boot здесь не реализованы и не разрешены автоматически.
4. Только при проверенном механизме rollback — одна GENI registration. Немедленный стоп при invalid protocol, probe defer, FIFO/DMA error или неожиданном mux/display change. Не загружать firmware и не принуждать режим.
5. Одна sensor identity/probe с r2: FW5/complement,PID5940,1080×2340. IRQ NO_AUTOEN и recording_authorized=false: даже auto-open input handler должен получить EPERM до SPI/IRQ. Ни reset, ни trim commands, ни firmware update.
6. Если всё валидно — отдельный допуск на recording_authorized и10s evdev, предварительно исключив другие readers. Первые3s без касаний, затем один tap, drag,release. Использовать существующий `touch-events /dev/input/eventN 10 --ack-input-open` после проверки exact device name/capabilities. Не угадывать eventN и не использовать EVIOCGRAB/uinput.
7. Сохранить SYN/ABS/BTN_TOUCH, tracking ID и all-slot release. По окончании закрыть только свой reader, проверить fault/IRQ count и отсутствие фоновых consumers. Собрать post state и сравнить6UFS stats/GPU/IOMMU/display. Повторной попытки нет.

Watchdog должен находиться вне reader process. Внутренний10s recorder deadline и внешний timeout ограничивают userspace, но **не гарантируют прерывание зависшего SPI open/close/synchronize_irq или kernel I/O**. Пока не доказан безопасный stop таких операций, шаг3–6 остаются NO-GO. В скрипт не добавлена фиктивная гарантия тайм-аутом.

Stop conditions: плохие FW/PID/geometry, SPI timeout/checksum fault, неожиданная IRQ storm, SYN_DROPPED, потеря USB/SSH/COM, изменение дисплея, новые GPU/IOMMU faults, UFS write/discard activity, критическая память. Снять доступные логи; не делать reset, regulator disable, firmware retry, rmmod или forced unbind.

## 8. Возврат в рабочую v8b: что реально возможно

`CONFIG_MODULE_UNLOAD=n`: module exit нельзя вызвать rmmod. Закрытие evdev оставляет загруженные модули, SPI controller, новый mux и возможные core resource votes. Наличие `.shutdown` не означает, что оно вызывается при close или гарантирует полное восстановление. `devm` teardown/unbind для этой конфигурации аппаратно не испытаны. В исходном GENI нет отдельного `.remove`, который можно принять за проверенный restore; новый handler ради обхода не добавлен.

Поэтому гарантированного возврата к **дотестовому аппаратному состоянию без reboot** сейчас нет. Принудительный unbind запрещён. Будущий альтернативный recovery — отдельно разрешённая штатная перезагрузка в уже сохранённую v8b, без записи boot и других разделов, при физически доступном владельце. Она очистит RAM-модули, но сохранность SRAM touch firmware после неё не обещается. Это резервная процедура, не автоматическое действие и не доказанный recovery от kernel hang.

Рабочие v8b/GNOMEv2.1, исходные63,732-byte DTB и старые архивы сохранены. На данном этапе откатывать телефон не требуется: он не изменялся. GNOME/tty1 restoration из v2.1 не менялся.

## 9. GO / NO-GO

| Gate | Решение | Недостающее доказательство |
|---|---|---|
| SE2,mode0,8bit,9,6MHz,IRQ93 | PASS как stock configuration | Не заменяет измерения current state |
| Runtime CS | PASS:CS0, прежнийCS1 отозван | CS0 registration и соответствующий кандидат ещё не применялись |
| Shared supply map | PASS:все3общие с LCD | Текущее напряжение/retention UNKNOWN |
| Live FW5 handoff без reset/upload | UNKNOWN | Историческая FW5 получена после download |
| r2 firmware safety | PASS source/build guards | Runtime test не проводился |
| Только штатный GENI без panel votes | Частично:нет direct LCD regulator API | Probe всё равно активен; pin/clock/ICC rollback не доказан |
| Полное восстановление без unload/reboot | UNKNOWN, критический | Проверенный reversible lifecycle отсутствует |
| Hardware activation permission | Не выдано этим заданием | Нужна конкретная процедура после закрытия критических gates |
| Итог | **NO-GO** | Не обходить неизвестное питание и recovery |

Офлайн результаты: ARM64 r2 module build W=1, точный vermagic, kernel Image/config SHA unchanged; fail-closed runner check/run, source guards, неизменяющий metadata fixture; ARM64/QEMU frame parser regression. Pinctrl/GENI runtime и реальные касания этим не подтверждены. Логи — `logs/touchscreen-stage1-final/`, хеши — `artifacts/touchscreen-stage1-final/MANIFEST.json`.

Следующий шаг не очередное исследование GNOME: решить **CS0 child registration + reversible GENI lifecycle** и подтвердить существующее touch питание/handoff. Пока это не решено, разрешение просто «загрузить модули» не делает тест безопасно обратимым. Stage C/B для повторной инициализации LCD остаётся NO-GO.
