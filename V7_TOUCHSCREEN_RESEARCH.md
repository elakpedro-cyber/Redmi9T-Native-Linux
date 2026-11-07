# v7 — сенсорный экран

## Определение по дереву реального устройства

В живом TWRP DT присутствуют два SPI-кандидата:

| Узел | Compatible | Panel phandles |
|---|---|---|
| /soc/spi@4a88000/novatek@1 | novatek,NVT-ts-spi | TD4330 Truly v2, NT36672D Tianma/Xinli |
| /soc/spi@4a88000/focaltech@0 | focaltech,fts | FT8719 Truly v2 |

Выбранная загрузчиком **TD4330 Truly v2** входит только в список Novatek.
Это сильная идентификация семейства **Novatek NVT SPI** на этом экземпляре,
а не произвольный выбор по наличию двух узлов. Два сохранённых лога TWRP содержат аппаратно прочитанный trim `0A 00 00 72 66 03`, project ID `0x5940` и FW 5. Trim соответствует таблице NT36672A Xiaomi. [Проверка архивов](REDMI9T_DISPLAY_HARDWARE_MAP.md#идентичность-и-варианты). Отчёт: `reports/v7-panel-comparison.json`.

## Разводка downstream

SPI GENI @0x4a88000 (QUPv3 SE2); DT child reg=1 — логический chip-select 1.
Не следует выводить физический CS только из имени узла: pinctrl/CS routing
GENI надо переносить отдельно. У Novatek reset TLMM GPIO103, IRQ GPIO93,
raw irq-gpio flags=0x2001. IRQ flags требуют сопоставления с downstream GPIO
и irq API; переносить 0x2001 в mainline blindly нельзя.

Питание общее с дисплеем: touch_vddio=pm6125_l9, touch_lab=PMI632 LCDB LDO,
touch_ibb=LCDB NCP. Поэтому «просто включить SPI» небезопасно: driver probe
может перезапустить touch, загрузить firmware и повлиять на общие bias rails.
Focaltech использует те же reset/IRQ, но другую панель и protocol.

## Драйвер и firmware

В официальном Xiaomi `lime-q-oss` commit
`02ca1a919564a9b176a79cce09c40977f833e9ac` найден
[NT36672A/nt36xxx.c](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/02ca1a919564a9b176a79cce09c40977f833e9ac/drivers/input/touchscreen/NT36672A/nt36xxx.c).
Несмотря на имя каталога, это **SPI** driver: CTP_SPI_READ/WRITE, spi_sync,
drm panel selection и firmware updater. Сохранены C/H, memory map и updater.
В нём есть Android-зависимые notifier/feature paths: это не готовый mainline port.

Из vendor filesystem на ПК видны `nt33672a_truly_novatek_ts_fw.bin`,
Tianma-вариант, NT33672D Tianma/Xinli и MP-прошивки. Наличие файлов подтверждено
в `reports/v7-vendor-firmware-list.txt`; ни один не загружался в сенсор.
MP manufacturing image не подходит для обычного input теста. Выбор normal
firmware должен следовать подтверждённому PID/memory map, а не только имени LCD.
Firmware из устройства не получает автоматически лицензию на распространение.

Mainline `drivers/input/touchscreen/novatek-nvt-ts.c` поддерживает
novatek,nt11205-ts и novatek,nt36672a-ts через **I2C**, а не нужный NVT SPI
protocol и загрузку runtime firmware. Совпадение NT36672A в имени не делает
этот driver совместимым с SPI-узлом. EDT FT5x06 также не является заменой
SPI Focaltech. В v7 неподтверждённых compatibles нет.

## План порта и критерий успеха

1. При отдельно разрешённом recovery-сеансе снять уже существующие input name,
   bound SPI driver и диагностический PID/FW из штатного интерфейса, если его
   чтение не запускает updater/reset. Не читать произвольные регистры сейчас.
2. Разобрать chip-ID table/memory-map и RAM firmware download downstream.
   Исключить flash/update-пути во внутреннюю память контроллера; перед тестом
   доказать, что выбранный updater пишет только volatile touch RAM.
3. Подготовить binding и mainline input driver с regulator sequencing,
   reset/IRQ, multitouch slots, 1080×2340 координатами и корректным suspend.
   Согласовать общие LCD/touch regulators и panel lifecycle.
4. Проверить код и DT schemas офлайн. Затем отдельное разрешение на probe,
   параллельные SSH/COM, stop-condition при reset loop/USB потере.
5. Тест `evtest /dev/input/eventN`: идентификация именно touch device,
   ABS_MT_POSITION_X/Y, tracking IDs, несколько касаний, отпускания, края,
   ориентация; без записи в UFS. evtest подготовлен в GPU userspace addon.

На работающей v6 input содержит кнопки; touch events не подтверждены.
Ни SPI, ни touch regulators/reset в этой работе на телефоне не включались.
