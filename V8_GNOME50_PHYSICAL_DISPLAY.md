# GNOME 50 на встроенном экране lemon — подготовка KMS

## Состояние

**Stage C/B — NO-GO.** Дисплейный тест Stage B подтвердил probe MDSS, DSI Host и 14-нм PHY. На DISPCC PLL0 был прочитан признак lock. Захват PLL PHY и состояние LP11 отдельно не подтверждены. DPU, панель, подсветка и сенсор в этом тесте не работали. [Stage B](V8_STAGE_B_RESULTS.md) · [Stage C/A](V8_STAGE_C_A_RESULTS.md)

| Участок | Подтверждено | Что требуется |
|---|---|---|
| SM6115 | DPU/DSI endpoints взаимны, PHY связан через phandle. MDSS использует DISPCC GDSC, GCC AHB/AXI и SMMU; DSI Host зависит от VDDA PM6125 L18 и RPM CX. | Отдельно проверить PLL/LP11 и runtime PM после допуска к link-тесту. [SM6115 DPU binding](https://android.googlesource.com/kernel/common/+/68a00586559f5fce3bb163f4618f1b71ef05b4e7/Documentation/devicetree/bindings/display/msm/qcom,sm6115-dpu.yaml) |
| REFGEN | Stock Bengal перечисляет ресурс без supply phandle. В stock TWRP и v8b используется dummy. | Нужен документ SM6115 с адресом, семантикой и владельцем либо подтверждение штатного firmware handoff. Привязку от соседнего SoC не переносить. [Qualcomm Bengal](https://android.googlesource.com/kernel/msm-extra/devicetree/+/refs/heads/android-msm-redbull-4.19-android12/qcom/bengal-sde.dtsi) · [REFGEN](V8_REFGEN_RESEARCH.md) |
| LCD и bias | Downstream выбирает TD4330 Truly v2. Профиль 1080×2340, четыре lanes, RGB888, 60 Гц, pixel clock 173517 кГц. VDDIO PM6125 L9, LAB/IBB PMI632. Reset GPIO85. | Сверить ревизию, polarity и pinctrl с платой, подтвердить LP11 до reset и измерить обе bias-шины, rollback и off. [Последовательность](V8_PANEL_POWER_SEQUENCE.md) |
| Подсветка | LM36923YFFR указан как U2732 в схеме J19S. Stock указывает I²C 0x36, enable GPIO99. | Сверить BOM/маркировку U2732 именно на NFC. Подсветка должна быть отдельно gated при первом modeset. [Сверка](V8_BACKLIGHT_IDENTIFICATION.md) |
| Сенсор | Выбор TD4330 сопоставляет аппарат с Novatek NVT SPI. DT описывает SPI CS1, reset GPIO103 и IRQ GPIO93; bias общие с LCD. | В архивах TWRP подтверждены trim NT36672A, project ID 0x5940 и FW 5. Остаются проверка пригодности firmware к RAM-only загрузке и mainline SPI probe. Mainline I²C-драйвер не подходит к SPI-ветке. Нужен подтверждённый SPI-порт без записи во flash контроллера. [Сенсор](V7_TOUCHSCREEN_RESEARCH.md) |

`display-v8/gnome-kms-review.dts` — отдельный офлайн overlay поверх существующего disabled LCDB fixture. В итоговом DTB принудительно отключены DISPCC, MDSS, DPU, DSI Host/PHY, LCDB и подсветка. Panel endpoint и touch consumer отсутствуют. Audit проверяет взаимные phandle, PHY и четыре lanes и отклоняет fixture с включённым DSI. Сборщик boot эти файлы не использует. [DTS](display-v8/gnome-kms-review.dts) · [DTB](logs/v8b-gnome50-desktop/gnome-kms-review.dtb) · [Audit](logs/v8b-gnome50-desktop/kms-review.txt)

## Последовательность проверки

1. На обесточенной плате специалист сверяет PCB и маркировку панели/U2732. По boardview и CN2701 определяет pin 1, VSP, VSN и reference. Номера контактов для данного экземпляра пока не подтверждены.
2. До подачи питания установить пределы модуля для VDDIO/VSP/VSN, допустимые ramp, overshoot, ripple, интервал разряда и порог off. С отдельным разрешением измерять обе bias-шины независимо осциллографом и высокоомным interposer. Нужны холодный handoff, один штатный цикл и наблюдение безопасного разряда. Код состояния LCDB фиксирует результат управления, физические уровни подтверждаются отдельно. [План измерений](V8_BIAS_MEASUREMENT_PLAN.md)
3. После допуска к DSI отдельно подтвердить PLL lock, LP11, порядок bridge pre-enable, reset и DCS, а затем fixed frame с аппаратным backlight gate. Проверить rollback при ошибке и suspend/resume. При неопределённом состоянии bias блокировать повторный enable. [Ворота допуска](V8_STAGE_C_SAFETY_REVIEW.md)
4. Проверить атомарный DRM/KMS commit через `modetest` или минимальный libdrm клиент. Зафиксировать DSI connector, native mode, CRTC/plane и поддерживаемые форматы/модификаторы. При отдельных GPU/KMS устройствах проверить PRIME/DMA-BUF экспорт FD610 → импорт DPU, fence и отсутствие software blit. Проверять render и scanout независимо.
5. Для физического Mutter нужен активный seat с `org.freedesktop.login1` и передачей KMS/input fd. На OpenRC кандидат — elogind и корректная PAM-сессия. Текущий патч `LEMON_REQUIRE_RENDER_NODE` намеренно отказывает в режиме с физическим выходом. Его оставить для headless. Отдельная физическая проверка должна подтвердить аппаратный FD610 и доступ именно к проверенному KMS connector. Сначала проверить seat и KMS через VKMS в отдельной VM, затем только после допуска через DSI. [Native backend Mutter 50.2](https://github.com/GNOME/mutter/blob/50.2/src/backends/native/meta-backend-native.c)
6. Получить идентичность connector от Mutter DisplayConfig до создания `monitors.xml`. Начать с нативного портретного 1080×2340 и логического масштаба 200% как кандидата. Подтвердить compositor transform, привязку сенсора к output, min/max ABS, углы, мультитач и корректность масштаба на физическом образце. Не вводить поворот GPIO или input-оси по предположению.

Образ с включённым дисплеем требует закрытия этих ворот. Прототип панели по-прежнему содержит режим и DSI-транспорт без аппаратного probe.

