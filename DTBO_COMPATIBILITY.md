# DTBO: причина несовместимости и решение v2

Схема DTBO сохраняется во v3 без изменений. Обновления CPU handoff, cache coherency и проверки размещения — `V3_AUDIT_FIXES.md`; текущий образ и аппаратный план указаны в `FIRST_BOOT.md`.

## Итог

Собран `artifacts/boot-linux-test-v2.img`. Он использует **два настоящих дерева для разных этапов**: сохранённый Android DTB для ABL и отдельный mainline DTB для Linux. Между ними работает небольшой ARM64 переходник из `bootshim/`. Исходный `dtbo.img` не меняется. Фиктивных аппаратных узлов нет.

Это экспериментальная сборка, проверенная офлайн. Выполнение ядра и `/init` на телефоне ещё не подтверждено. Сценарий согласуемого теста — `FIRST_BOOT.md`.

## Какие исходные файлы разобраны

`platform-tools/Redmi9T_Backup/boot.img`: header v2, page 4096, kernel gzip, отдельный DTB 302880 байт, recovery_dtbo_size=0. В поле DTB находится один FDT, не набор нескольких DTB. Его root `qcom,msm-id=<0x1a1 0x10000 0x1bc 0x10000>`, `qcom,board-id=<0 0>`.

`dtbo.img`: раздел 16777216 байт, полезная DT table 233583 байта, header version 0, page 4096. **Ровно одна entry**: index 0, offset 64, size 233519, id=0, rev=0, custom[4]=0. Root overlay имеет `qcom,board-id=<0x22 0>` и те же две пары msm-id. Нет других entries, с которыми можно было перепутать результат.

Распаковка: официальный AOSP `tools/unpack_bootimg.py`; DT table разобрана как big-endian header/entries с проверкой границ в `scripts/check-dtbo.py`. Исходные файлы и их SHA-256 сохранены.

## Почему ABL должен выбирать entry 0

| Метаданные телефона | Прочитанное значение | Значение overlay |
|---|---|---|
| SoC ID | 444 = 0x1bc, SM_KAMORTA_H | среди msm-id есть 0x1bc |
| SoC revision | 1.0 = 0x10000 | 0x10000 |
| Foundry | 2 | 0: допустимое общее соответствие |
| Platform type | 34 = 0x22, IDP | 0x22 |
| Platform version | 0x10000: major 1, minor 0 | major 0, minor 0: более ранняя допустимая ревизия |
| Platform subtype | 0 | 0 |
| PMIC | socinfo сообщает две; dmesg: PM6125 v1.1 и PMI632 v2.0 | PMIC selector отсутствует |
| DT table id/rev/custom | не являются основным аппаратным selector в исследованном коде GetBoardDtb | все нули |

`reports/soc-metadata.txt`, `pmic-dmesg.txt`, `v2-device-metadata.txt` содержат исходные чтения. `androidboot.dtbo_idx=0` текущего TWRP дополнительно подтверждает индекс, **но относится к recovery**: recovery имеет собственный embedded DTBO, немного отличающийся от отдельного dtbo-раздела.

Для нормального boot более сильная проверка — выполнение сохранённого машинного кода ABL `ReadDtbFindMatch` с root свойствами именно partition overlay #0 и прочитанными метаданными. Результат `selected=true` с selection_bit=52 (VARIANT_MATCH); других entries нет. См. `reports/abl-match-emulation.json`. Вызовы UEFI заменялись данными TWRP; это офлайн-модель, не протокольная трасса работающего ABL.

## Точная причина FDT_ERR_NOTFOUND

Overlay содержит 45 fragments, 156 внешних symbols, 375 внешних fixup-ссылок и 56 local fixup-ссылок. Все 375 внешних ссылок найдены в stock `__symbols__`, каждый соответствующий phandle существует, все 56 local references разрешаются внутри overlay.

Первоначальный mainline DTB вообще не содержит `/__symbols__`. Поэтому разрешение внешних fixups невозможно уже на этом уровне. Для исключения простой ошибки сборки DTB отдельно пересобран с `DTC_FLAGS=-@`: появились 295 symbols, но **145 из 156 требуемых symbols по-прежнему отсутствуют**. Простого добавления `-@` недостаточно.

Полная точная таблица каждой ссылки: `reports/dtbo-references.tsv`. Столбцы: symbol, stock path, исходный phandle, mainline symbol path, наличие старого пути, overlay node, property, byte offset. Полный JSON, включая fragments и списки отсутствующих symbols: `reports/dtbo-reference-audit.json`. Это не выборка из первого сообщения libfdt, а разбор всех ссылок.

| Symbol | Stock target / phandle | Аппаратное назначение и отличие mainline |
|---|---|---|
| bolero | `/soc/qcom,msm-audio-apr/qcom,q6core-audio/bolero-cdc`, 0x311 | Downstream аудиокодек/макросы LPASS; такого provider нет в текущем mainline DTS |
| L9A | `/soc/qcom,rpm-smd/rpm-regulator-ldoa9/regulator-l9`, 0x12 | Физический LDO9; mainline описывает его как `pm6125_l9` в RPM regulators, с другим binding |
| qupv3_se1_i2c | `/soc/i2c@4a84000`, 0x271 | Тот же serial engine mainline находится в `/soc@0/geniqup@4ac0000/i2c@4a84000`; vendor children нельзя переносить без проверки bindings |
| soc | `/soc`, 0x188 | Mainline `/soc@0`; отличаются также форматы адресации дочерних reg |
| tlmm | `/soc/pinctrl@400000`, 0x11 | Mainline `/soc@0/pinctrl@500000`; структура контроллера и pin states отличаются |
| usb0 | `/soc/ssusb@4e00000`, 0x1f1 | Vendor `qcom,dwc-usb3-msm`; mainline использует отдельный glue `usb@4ef8800` и snps DWC3 `usb@4e00000` |
| ufshc_mem | `/soc/ufshc@4804000`, 0x1b2 | Mainline `ufs_mem_hc` расположен в `/soc@0/ufshc@4804000`; питание и clocks описаны иначе |

Например, `/fragment@0:target:0` требует bolero. `/fragment@0/__overlay__/wcd937x-codec:cdc-vdd-rxtx-supply:0` требует L9A. До применения на их местах находится 0xffffffff. Полная таблица показывает и повторные ссылки на тот же provider.

Многие остальные отсутствующие symbols относятся к camera GPIO/pinctrl, downstream charger/thermal, display PLL/панелям и аудио. Переименование labels не переводит номера clock/reset, GPIO states, reg и API драйверов. Добавлять пустые nodes, копировать numeric phandles или смешивать оба набора bindings нельзя.

## Отвергнутый путь: exact-match selector

ABL содержит штатную ветку пропуска DTBO, но в сохранённом бинарнике её условие требует mask `0x35555555550000`. В нём есть exact-model bits для **16 PMIC slots**. При этом две PMIC arrays в промежуточной структуре имеют по **15 элементов**: second array начинается через 0x3c, match flags находятся через 0x78.

При 15 slots последний необходимый bit не выставляется. При попытке задать 16 slots обработка последнего элемента пересекается с полем flags. Офлайн-эмуляция настоящего кода с обычными нулевыми отсутствующими slots не включает skip flag. Это подтверждается source-relative disassembly, а не только строкой сообщения. Открытый аналог Qualcomm также содержит `MAX_PMIC_IDX=0xF`, но вывод о данном устройстве опирается на его бинарник.

Вариант metadata-only отвергнут. Его исследовательские файлы находятся только в `reports/rejected-lemon-abl-metadata.dtso` и `reports/lemon-exact-match-candidate.dtb`; **они не входят в v2 и не должны загружаться**. Эксплуатация пересечения полей для подделки flags не применяется.

## Как работает v2

1. ABL видит исходный Android DTB, совпадающий побайтово с DTB из сохранённого boot.img.
2. ABL выбирает обычный stock overlay #0 и выполняет штатное объединение. Именно эта пара прошла `fdtoverlay`.
3. Вместо непосредственного запуска Linux ABL передаёт управление ARM64 Image-переходнику с обычным 64-байтным ARM64 header. Внутри находятся неизменённый Linux Image и отдельный mainline DTB.
4. Переходник проверяет входной FDT, EL1/EL2, выключенные MMU/data cache, реальную карту DRAM, отсутствие пересечений destination с initrd, firmware reservations и самим переходником.
5. В mainline DTB переносятся фактические memory/reg и initrd pointers; при наличии — rng/kaslr seed. Firmware reserved ranges сохраняются как memreserve entries без копирования vendor drivers. Для исходных no-map ranges, ещё не покрытых mainline no-map region, добавляется настоящее описание резервирования RAM с reg/no-map. Это защита реально зарезервированной памяти, а не фиктивный device node. В прочитанном дереве дополнительно сохраняется старый GPU reservation 0x55a15000/0x2000, который upstream перенёс в другое место; GPU в сборке отключён. Bootargs задаются подготовленной строкой Linux.
6. Linux копируется по 0x80000000, mainline DTB — по 0x82000000. Адреса предварительно проверяются по входной карте памяти и обоим деревьям. Они подходят для прочитанной конфигурации, но не заявляются универсальными для всех вариантов Redmi 9T.
7. После барьеров и инвалидации instruction cache выполняется переход к Linux: x0=0x82000000, x1=x2=x3=0. Переходник не меняет exception level и не обращается к накопителям.

Основа перехода — [документированный ARM64 boot protocol](https://docs.kernel.org/arch/arm64/booting.html). Это наш экспериментальный загрузочный код, а не готовый подтверждённый порт U-Boot для lemon. Его работа на реальном ABL ещё требует испытания.

У mainline ramoops удалён `ecc-size=16`: у текущего recovery ECC не настроен. Физический регион 0x64000000/4 MiB и record/console/pmsg sizes совпадают. USB peripheral-настройка v1 сохранена; её работа на устройстве не подтверждена.

## Выполненные проверки

- `fdtoverlay(stock, overlay#0)`: успех; `fdtoverlay(mainline, overlay#0)`: ожидаемый FDT_ERR_NOTFOUND. Во v2 используется первая пара.
- AOSP unpack round-trip v2: kernel, ramdisk, ABL DTB совпадают с входными файлами побайтово.
- `dtc`: читает stock merged и выходное mainline дерево. Предупреждения сохранены; это не полный dt-schema validation. У vendor tree есть существующие legacy binding warnings, у mainline — в том числе альтернативные GENI nodes с общими unit addresses.
- Проверены 466 стандартных mainline phandle/provider references: clocks, supplies, GPIO, resets, power domains, phys, interconnects, endpoints и другие перечисленные в `scripts/validate-v2.py` свойства.
- ARM64 Unicorn исполнил **скомпилированный переходник**, включая копирование Image, перенос RAM/initrd и 17 firmware reserved ranges; сохранено покрытие всех 13 исходных no-map ranges. Получен переход по 0x80000000 с правильными регистрами. Linux-инструкции после этой границы не выполнялись.
- Неверный FDT останавливает переходник с reason 13; пересечение initrd с destination — с reason 10. ELF не содержит relocations, linker запрещает GOT.
- Все исходные v1 артефакты и четыре backup-файла сохранили SHA-256.

Результаты: `reports/v2-validation.txt`, `bootshim-emulation.json`, `v2-status.json`. Физический запуск и `/init` остаются отдельным испытанием.
