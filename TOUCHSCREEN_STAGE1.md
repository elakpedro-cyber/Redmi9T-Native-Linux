# Touchscreen Stage 1 — план отдельного аппаратного испытания

**Исторический план.** Его предположение runtime CS1 и предложение unbind не действуют. Следовать `TOUCHSCREEN_STAGE1_FINAL.md`: runtime CS0 подтверждён отдельно; unbind/rmmod не являются проверенным recovery, активный этап NO-GO.

**Сейчас аппаратный GO не выдан.** Разрешённая этим заданием read-only диагностика выполнена; загрузки модулей/новых DTB, GPIO, SPI-команд и firmware не было. Все нижеследующие активные действия требуют нового конкретного разрешения.

## Перед активным этапом

1. Сохранить v8b/GNOMEv2.1, сверить snapshot/MANIFEST и known_hosts через COM при новой загрузке. Проверить SSH/NCM/COM4, tty1, SimpleDRM1080×2340, FD610/MDSS hold, mounts/swap, dmesg и6UFS stats.
2. Убедиться, что выбран именно этот Novatek: исторические trim/PID/FW доказательства приложены. Не использовать Focaltech@0, I2C Novatek или global GPIO1270/1260.
3. Подтвердить существующее питание VDDIO и допустимость перевода GPIO6/7/71/80 в SPI mode без новых supply votes. Наличие LCD не является измерением всех touch-сигналов. Не включать/выключать LAB/IBB и не запрашивать resetGPIO103.
4. Принять отдельно способ появления SPI child: текущий DT включает SPI2, но child отсутствует. По новому разрешению собран только офлайн disabled DTB-кандидат, прошедший exact-delta/schema/negative checks (touchscreen-v1/DTB_REVIEW.md). Новый boot.img не создавался. Применение DTB или runtime registration на телефоне не разрешены. Нужен отдельный review выбранного механизма, без замены boot/recovery автоматически.
5. Проверить GENI module version lemon-touch-v1 и SHA. Его probe включает собственные clocks/pinctrl и может запросить firmware последовательного GENI engine: это уже аппаратные действия, даже без touch child. QCOM_GPI_DMA в v8b выключен; FIFO допустим только при подтверждённой штатной конфигурации. При defer/invalid protocol/unsupported GPI остановиться, не форсировать режим или MMIO.
6. Проверить stock raw delay200/interword0; частный provider patch не переводит их в ns или SCK cycles. GPI DMA с этими свойствами отклоняется. IRQ TLMM93 rising; resetTLMM103 не управляется. Mode0,CS1,9600000Hz. Шина Linux может называться не spi1 и не spi2 — выбирать по OF path/адресу4a88000.
7. Принять ограничение CONFIG_MODULE_UNLOAD=n. rmmod не является откатом. Для sensor stop подготовлено закрытие input readers и targeted driver unbind/devres teardown без power/reset, но аппаратный unbind ещё не испытан. Не выгружать MSM или чужие драйверы. Если для аварии потребуется reboot, это отдельное разрешение, а не автоматическая мера.

## Активный Stage1A: controller/handoff identification

После выполнения условий и отдельного разрешения — один контролируемый probe. Предел процедуры заранее ограничить watchdog, параллельные SSH/COM. Записывать каждое действие в RAM/на ПК.

- Зарегистрировать только проверенный GENI SPI controller и один CS1 Novatek child согласованным способом. Не создавать Focaltech child. Никаких I2C scan.
- Вход драйвера требует stage1_authorized и xiaomi,validated-touch-handoff. Эти флаги — явное согласование, **не аппаратное доказательство**. Core/pinctrl может менять состояние ещё до probe, поэтому flags не заменяют предыдущие gates.
- Единственные touch writes — стандартная команда выбора event-buffer page. Далее чтение FWINFO и PID. Это **не read-only диагностика текущего этапа**: page command разрешается только отдельно.
- Ожидаются живые PID5940,FW5,1080×2340 и версия/inverse checksum. Нет валидного ответа — немедленный отказ. Не выполнять reset, firmware upload, cold recovery или повторную попытку автоматически.
- Stock event map21c00 подтверждён trim-таблицей. Не читать произвольные регистры. Архивный trim в Stage1 повторно не читается, поскольку исходный trim-probe использует reset.

Текущий firmware blob имеет metadata version6, архивы TWRP — runtimeFW5. До установления происхождения именно поданного TWRP blob нельзя превращать найденный файл в автоматический loader. Handoff driver не зависит от файла и не умеет загружать firmware.

## Активный Stage1B: evdev, сначала без GNOME

Только при успешном handoff и отдельном разрешении открыть конкретный verified event node на10s:

```text
touch-events /dev/input/eventN 10 --ack-input-open
```

Перед открытием: verify name/phys/driver, direct touchscreen, MT slots/position/tracking IDs. Первые3s — без касаний, затем один палец в центр/четыре угла, drag и release. Сохранять только touch/SYN события в /tmp и передать на ПК. Не угадывать eventN, axes или invert.

Ошибки checksum/I/O приводят к release slots;3последовательные ошибки защёлкивают fault и отключают IRQ. Никаких автоматических ESD reset/firmware recovery. Любой fault, USB loss, unexpected display state, SYN_DROPPED или UFS activity — стоп и логи. Тайм-аут процесса не является доказательством физического отключения/разряда цепей или гарантией отмены зависшего аппаратного I/O.

## Stage1C: интеграция в GNOME, только следующим отдельным допуском

После verified evdev и измеренной матрицы: один C-сеанс <=60s, ранее проверенный watchdog/VT2->tty1. Один private input inode и udev metadata, patched wlf client+pointer fallback. Проверить tap,drag,Activities,Settings/Console focus; scroll только в явно выбранном режиме. Не заявлять multitouch/OSK как результат mouse fallback. Без изменений физических timings/питания/MDSS.

После: закрыть readers, освободить slots/IRQ, остановить GUI/GRD/Weston, вернуть tty1, проверить GPU suspended, SSH/NCM/COM4, dmesg/6LUN. Удалить только RAM-файлы после подтверждения освобождения ресурсов. Не обещать unload модулей, запрещённый config.

Откат GUI — неизменённая GNOMEv2.1 C без Touch overlay; source/session-touch не заменяет baseline. При неизвестном состоянии hardware не выполнять reset/PMIC/LCDB/REFGEN и не переходить к следующему этапу.
