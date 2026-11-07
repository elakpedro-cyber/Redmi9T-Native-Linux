# Redmi 9T NFC — финальная проверка framebuffer на v8b

Позднее живой вывод подтверждён визуально по новой строке TTY и рабочему столу Weston. [Результаты аппаратного теста](V8_PHYSICAL_WESTON_RESULTS.md)

**B. Framebuffer существует, физический scanout не подтверждён. Тест кадра не допущен. Stage C/B — NO-GO.**

## Свежие данные с телефона

| Проверка | Результат |
|---|---|
| `/proc/fb` и `/sys/class/graphics` | `0 simpledrmdrmfb`. `fb0` принадлежит `5c000000.framebuffer`, platform driver `simple-framebuffer` (SimpleDRM). |
| Источник параметров | Живой `/chosen/framebuffer@5c000000` и встроенный native DTB v8b совпадают по адресу, размеру, формату, ширине, высоте, stride и clock. Разрешение 1080×2340, 32 bpp, stride 4320, формат `a8r8g8b8`. |
| Память | DT описывает `0x5c000000–0x5c9a3f7f` включительно, 10 108 800 байт. `/proc/iomem` помечает охватывающий диапазон `0x5c000000–0x5cffffff` как reserved. SimpleDRM сообщает `could not acquire memory region`, затем регистрируется. По коду он может использовать исходный ресурс и отобразить его в память после такого предупреждения. Резервация и отображение ресурса не устанавливают, откуда DPU считывает кадры. |
| DRM connector | Единственный connector `card0-Unknown-1`: `connected`, `enabled`, 1080×2340. SimpleDRM создаёт connector типа `Unknown` без callback обнаружения. Общий DRM helper в этом случае возвращает `connected`. `enabled` отражает назначение software encoder. DSI connector отсутствует. `card1` и `renderD128` относятся к Adreno. |
| DPU, MDSS, DSI и DISPCC | DPU `5e01000` disabled в DT и отсутствует в platform bus. MDSS `5e00000` unbound с `lemon-stage-b-hold`, DISPCC `5f00000` unbound. DSI Host `5e94000` и PHY `5e94400` описаны как okay, но их platform devices отсутствуют. MIPI DSI bus пуста, sysfs backlight отсутствует. Это состояние драйверов Linux. Физическое состояние, оставленное ABL, оно не измеряет. |
| Такты и питание | В framebuffer DT только `GCC_DISP_HF_AXI_CLK`. Свойств `display`, `power-domains` и supplies на этом узле нет. Debugfs не смонтирован. Состояние display PLL, GDSC, DPU scanout и напряжения панели безопасными доступными интерфейсами не подтверждены. |

[Свежий SSH-снимок](logs/v8b-framebuffer-final/live.txt) · [Сверка DT и счётчиков](logs/v8b-framebuffer-final/verification.txt) · [Проверенные строки ядра](logs/v8b-framebuffer-final/kernel-source.txt) · [Linux SimpleDRM](https://github.com/torvalds/linux/blob/05441d697f7f9a927264f4058cbbc6a03dfcac9d/drivers/gpu/drm/sysfb/simpledrm.c)

## Что ABL передал

В исходном stock DTB и архивном живом TWRP FDT есть резерв `cont_splash_region@5c000000` размером `0x00f00000`. Узла `simple-framebuffer` там нет. В v8b его описывает mainline DTS, встроенный в bootshim. Bootshim берёт native DTB как основу, сохраняет резервации входного дерева и переносит выбранные свойства `/chosen`. Параметры fb0 в этой загрузке приходят из native DTB. [Сверка](logs/v8b-framebuffer-final/verification.txt) · [Bootshim](bootshim/bridge.c#L181) · [Upstream DTS](https://github.com/torvalds/linux/commit/76fbf547548ccd1a650c096836d8cf01f3ce3ce6)

Архив TWRP для этого телефона фиксирует привязку TD4330 Truly v2 и `cont_splash enabled in 1 of 1 display(s)` в другой загрузке. Это доказательство исторического пути handoff, связь текущего буфера с активным TD4330 и сохранение continuous splash после перехода в v8b остаются неизвестными. [TWRP](logs/v8b-authorized/adb-write-commands.txt#L951) · [Continuous splash](logs/v8b-authorized/adb-write-commands.txt#L1036)

## Почему тест остановлен

Для обновления изображения запись в буфер должна встретить действующий DMA scanout DPU из этого адреса, активные display clocks и DSI Host/PHY с работающим link, а также уже запитанную и настроенную TD4330 с видимой подсветкой. Единственный clock в узле simplefb описывает доступ к дисплейной шине. Он не подтверждает DPU timing, DSI PHY PLL, REFGEN, VDD_MX или состояние VDDIO, LCD_VSP/LCD_VSN и HWEN. Если тракт не унаследован активным, эти зависимости пришлось бы настраивать и включать отдельно. [Binding simple-framebuffer](https://github.com/torvalds/linux/blob/05441d697f7f9a927264f4058cbbc6a03dfcac9d/Documentation/devicetree/bindings/display/simple-framebuffer.yaml) · [Карта питания](REDMI9T_DISPLAY_HARDWARE_MAP.md)

Сбор через SSH с закреплённым host key завершился успешно. NCM в Windows Up с `192.168.77.1/30`, телефон сохранил `192.168.77.2/30`. Windows видит COM4 со статусом OK, порт не открывался. Счётчики записи всех шести UFS LUN совпали до и после. Запись кадра, KMS commit, чтение через `/dev/mem`, изменения питания, прошивка и сборка нового boot.img не выполнялись. [Windows](logs/v8b-framebuffer-final/windows.txt) · [Метод сбора](logs/v8b-framebuffer-final/read-only.sh)
