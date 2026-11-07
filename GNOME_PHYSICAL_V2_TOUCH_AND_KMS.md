# Physical LCD v2 — touchscreen и native KMS

## Фактический ввод

Read-only SSH: `logs/gnome-physical-v2/read-only.txt`. В текущем v8b зарегистрированы только pm8941_pwrkey/event0, pm8941_resin/event1 и gpio-keys/event2. SPI bus devices пусты. Touchscreen evdev отсутствует, поэтому libinput не может получить касания. Никакой probe, firmware upload, GPIO/reset, питания или input injection на телефоне в этой работе не выполнялось.

Идентификация экземпляра сохраняется из двух TWRP-архивов: SPI trim `0A 00 00 72 66 03`, downstream mask NT36672A Xiaomi, project ID `0x5940`, firmware version 5. Stock DT: `spi1.1`, CS1, reset GPIO103, IRQ GPIO93. Это не доказывает готовность mainline-драйвера или безопасность повторного питания. [Предыдущие доказательства](V7_TOUCHSCREEN_RESEARCH.md) · [Локальный разбор](V8_DISPLAY_TOUCH_BRINGUP.md).

В сохранённом перечне vendor firmware указан `nt33672a_truly_novatek_ts_fw.bin` — написание именно **33672a**, его нельзя незаметно заменить похожим именем 36672a. Наличие списка не равно проверенной загрузке firmware в RAM контроллера. В текущем Linux нужный файл не подтверждён.

## Подготовленный программный путь

После отдельного безопасного SPI bring-up ожидаемая цепь:

`NT36672A SPI → MT Type B evdev → libinput/Weston seat → Wayland wl_touch → FreeRDP touch channel → Mutter RemoteDesktop → GNOME` для C.

У FreeRDP 3.32.2 Wayland client есть обработчики down/up/motion, перевод координат и передача touch events. Это подтверждение исходного кода, не аппаратный тест multitouch. При будущей проверке нужно отдельно подтвердить согласование RDP touch channel и приём GRD; mouse emulation не считать multitouch. [wlf_input.c](https://github.com/FreeRDP/FreeRDP/blob/3.32.2/client/Wayland/wlf_input.c#L388).

В B вход идёт от Weston seat через GTK/Devkit и libei в GNOME, без RDP. При отсутствии host seat GTK выдавал предупреждение `GDK_IS_SEAT`, однако исправленный полный GNOME session смог получить кадры в офлайн headless backend. Физические касания этим не подтверждены.

Текущий production launcher намеренно не пробрасывает `/dev/input` в Weston root. Автоматического включения touch нет. После подтверждённого kernel input device потребуется отдельный allowlist конкретного event node, его identity/ABS/MT/IRQ и существующей seat. `/dev/uinput` не используется.

`userspace/gnome-physical-v2/touch-map.py` выполняет только офлайн-проверку координат по **измеренным** ABS bounds. Проверены края, смещённый диапазон и отказ вне диапазона. 1080×2340/rotation 0 — геометрия существующего LCD; ориентация сенсора, axis inversion и реальные min/max пока не измерены. Поэтому calibration matrix на телефоне не устанавливалась. Существующий `display-v8/novatek-lemon-frame.c` остаётся офлайн MT decoder, не полноценным SPI-драйвером.

## Конкретные блокеры touch

| Блокер | Что требуется | Что запрещено подменять |
|---|---|---|
| Нет SPI/input binding | Проверенный SPI driver, DT, IRQ polarity, reset и transport | I²C-драйвером Novatek |
| Firmware/flash policy | Проверенный vendor файл, hash, project/version; доказанный RAM-only upload | Записью во flash контроллера |
| Общие LCD/TP bias и I/O | Отдельно подтверждённое исходное питание и допустимая последовательность без его сброса | Видимым изображением LCD как доказательством безопасности reset TP |
| Нет libinput touchscreen | Реальный event node, MT slots/tracking, ABS bounds и libinput classification | Программным вводом через Mutter |
| Не проверена передача C/B | Contacts, down/motion/up/cancel, два пальца, ориентация и release после disconnect | Одним курсором мыши |

Первый touch hardware test требует отдельного согласования. Повторную инициализацию общих bias-цепей это разрешение не включает.

## Native KMS A

Сохранённая реальная топология (`logs/v8b-physical-weston/mutter-topology.txt`): SimpleDRM card0 имеет один CRTC/connector/encoder; card1 MSM возвращает EOPNOTSUPP на GETRESOURCES; renderD128 — render-only MSM. PRIME import/export caps сообщают 1, но это **не доказательство совместимости конкретных buffers, modifiers, fences и CPU mapping**.

Mutter 50.2 native перечисляет card devices и создаёт KMS device для каждого. Имеющийся FD610 guard допускает только headless; снимать его ради native нельзя. В исходниках существует CPU-copy в dumb buffer, но отдельно требуется включить render-only GPU в renderer topology и обеспечить валидный native seat. [Перечисление GPU](https://github.com/GNOME/mutter/blob/50.2/src/backends/native/meta-backend-native.c) · [CPU-copy](https://github.com/GNOME/mutter/blob/50.2/src/backends/native/meta-onscreen-native.c).

Безопасный дальнейший план A: отдельная userspace ветка Mutter; mock проверки раздельных KMS/render devices и строгого FD610 guard; ошибки import/map/copy/fence; OpenRC seat lifecycle и освобождение DRM master; затем отдельный короткий тест существующего SimpleDRM режима. Ядро/MDSS для этой работы менять не нужно. Native renderer не объявляется готовым, `-Mode A` блокируется с причиной. Проверенный C остаётся доступен независимо от результата B/A.
