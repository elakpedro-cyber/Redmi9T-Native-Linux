# v7 — дисплей и DSI

## Определение профиля конкретного экземпляра

В сохранённом **живом TWRP FDT** `reports/live.dtb`, `/chosen/bootargs`:

```
msm_drm.dsi_display0=qcom,mdss_dsi_td4330_truly_v2_video:
msm_drm.dsi_wp=305318
androidboot.dtbo_idx=0 androidboot.dtb_idx=0
androidboot.product.hardware.sku=lemon
```

Серийный номер совпадает с текущим телефоном. Тот же bootarg сохранён в
`reports/twrp-readonly.txt` и `reports/v2-device-metadata.txt`.
Следовательно, выбран **TD4330 Truly v2 video profile**, а не случайный
кандидат из DTBO. Это доказательство выбора загрузчиком и работавшего recovery;
оно ещё не является чтением DDIC ID или точного номера LCD-модуля.

Исходник Xiaomi `lime-q-oss`, commit
`02ca1a919564a9b176a79cce09c40977f833e9ac`:
[dsi-panel-td4330-truly-v2-singlemipi-fhd-vid.dtsi](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/02ca1a919564a9b176a79cce09c40977f833e9ac/arch/arm64/boot/dts/vendor/qcom/dsi-panel-td4330-truly-v2-singlemipi-fhd-vid.dtsi).

Скомпилирован отдельно и сравнен с выбранным узлом TWRP:
**58 свойств совпали, 0 различий**, в том числе init/off DCS sequences.
Доказательства: `reports/v7-panel-comparison.{json,log}`,
`reports/v7-panel-touch-details.json`, pinned исходник в downloads/v7-xiaomi-source.
Обозначение TD4330 в имени нельзя без дополнительного чтения ID автоматически
заменить на NT36672A-compatible. Другие панели NT36672D/FT8719 в том же DTBO
не выбраны на этом экземпляре.

## Извлечённые параметры

| Параметр | Значение |
|---|---|
| Интерфейс | DSI0, PHY0, VC0, 4 lanes 0–3, RGB888 |
| Режим | video, non-burst sync-event, LP11 init |
| Активная область | 1080×2340, 60 Hz |
| Horizontal | front 60, sync 8, back 60; total 1208 |
| Vertical | front 26, sync 4, back 24; total 2394 |
| Расчётный pixel clock | 173517120 Hz по totals×60; не измерен на линии |
| Reset | TLMM GPIO85; raw levels 1/10 ms, 0/10 ms, 1/20 ms |
| Backlight enable | TLMM GPIO99 |
| Panel vddio | pm6125_l9, panel supply entry строго 1.8 V, post-on 20 ms |
| Bias | PMI632 LCDB LDO/NCP, downstream имена lab/ibb, диапазон 4.6–6.0 V в supply entries |
| Host/PHY analog | upstream mdss_dsi0 vdda=pm6125_l18; остальные карты питания из SM6115 DTSI |
| Backlight profile | bl_ctrl_pwm, период 100 µs, диапазон 1–4095 |

Диапазон bias — ограничение downstream, **не разрешение выбрать любое напряжение**.
У LCDB provider в сохранённом DT более широкий диапазон 4–6 V; требуется перенос
реального LCDB sequencing, а не замена фиктивным fixed-regulator.
Содержимое команд разобрано на DSI packets с типами и задержками в JSON.
Например, sleep-out имеет задержку 85 ms; команды vendor pages сохраняются
точно, без сокращения до стандартных sleep-out/display-on.

## Что уже есть в mainline

SM6115 содержит MDSS/DPU, DSI host, DSI PHY и display clock controller.
Существуют MSM DPU catalog для SM6115 и драйверы DSI/PHY; board DTS задаёт
часть питания и lanes. Августовская [серия v5](https://marc.info/?l=devicetree&m=178731515251507&w=1)
явно оставляет MDSS выключенным из-за отсутствия панели.

В upstream board DTS также есть **TI LM36923@0x36** на i2c1 и led-backlight,
оба выключены с замечанием о различиях между панелями. GPIO99 совпадает с
downstream enable, но это не доказывает, что установлен именно LM36923.
Нельзя автоматически заменить downstream PWM-подсветку этим I2C-драйвером.
На v6 `/sys/class/backlight` пуст; I2C backlight не проверен.

Mainline qcom-labibb-regulator соответствует PMI8998 LAB/IBB, не PMI632 LCDB.
В выбранном ядре не найден готовый совместимый PMI632 LCDB regulator driver.
Нельзя подставлять pmi8998-compatible только из-за сходства названий bias rails.

## Блокеры и реализация следующего этапа

1. Перенести и проверить PMI632 LCDB register layout, включение LDO/NCP,
   ограничение напряжений, discharge и задержки из downstream. Сверить с
   исходниками PMIC и имеющимися upstream bindings; сначала отдельный review.
2. Уточнить контроллер подсветки по downstream I2C node/драйверу и доступным
   recovery-логам. При новом разрешённом сеансе TWRP читать уже bound driver
   и input/backlight sysfs; не выполнять i2cdetect или bus probing сейчас.
3. Подготовить отдельный panel binding/driver только для подтверждённого
   профиля. Перенести все 697 байт on-command и off-command с типами/delays,
   reset и supply sequence; не применять случайный существующий compatible.
4. Проверить совместное использование vddio/bias сенсором, regulator refcounts,
   suspend/unprepare и отсутствие преждевременного отключения LCD firmware.
5. Лишь затем включать dispcc, MDSS, DSI/PHY, graph endpoints и KMS в отдельном
   образе. Задокументировать handover от SimpleDRM и отключение firmware fb.
6. Первый разрешённый modeset: один статический pattern без compositor,
   с параллельными COM/SSH и ограниченной яркостью после проверки backlight.
   Успех — корректный KMS connector/mode и видимое тестовое изображение.
7. После стабильного KMS — Weston DRM backend с seat/permissions и проверенным
   render node. Headless Weston проверяет compositor, но не DSI/panel.

В текущем **v7 GPU preparation** MDSS/DSI/dispcc остаются disabled, SimpleDRM
сохраняется. Panel-compatible, reset, bias и backlight не добавлялись.
Дисплейные аппаратные эксперименты не выполнялись.
