# TD4330 Truly v2 video и последовательность питания

## Подтверждено

ABL выбрал `qcom,mdss_dsi_td4330_truly_v2_video`, TWRP DRM привязал этот же профиль. Вариант — `td4330 v2 video mode dsi truly panel`, DSI0/PHY0, VC0, RGB888, четыре lanes 0–3, non-burst sync-event, LP11 init, BLLP/EOF power mode и EoT append. 1080×2340 при 60 Гц, размер 65×129 мм. H front/sync/back 60/8/60, V 26/4/24. Mode totals 1208×2394, pixel clock 173517 кГц. Профили cmd и другие панели lemon исключены из прототипа. [Идентификация](V8_PANEL_IDENTIFICATION.md) · [Исходник Xiaomi](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/02ca1a919564a9b176a79cce09c40977f833e9ac/arch/arm64/boot/dts/vendor/qcom/dsi-panel-td4330-truly-v2-singlemipi-fhd-vid.dtsi).

Reset — GPIO85, физические уровни high 10 мс → low 10 мс → high 20 мс. Downstream display использует `panel_active` и `panel_suspend`, каждый с DSI и TE группами TLMM. Backlight enable — GPIO99. VDDIO 1,8 В PM6125 L9, bias — LDO/NCP PMI632 LCDB. При включении VDDIO → LAB → IBB, 20 мс после VDDIO и IBB. [Stock DT и TWRP](V8_POWER_SEQUENCE.md).

Полная последовательность — [77 on и 2 off пакета](reports/v8-panel-packets.json), побайтно сверенных по TWRP, stock DTB+DTBO и Xiaomi source. VC0, LP, wire types 0x05 и 0x39. Sleep-out `11 00` ждёт 85 мс, display-on `29 00` ждёт 2 мс. При выключении `28 00` + 20 мс, `10 00` + 120 мс. [Транспортный прототип](display-v8/td4330-profile.c).

## Проект перехода к DRM

Downstream с lp11-init откладывает подачу питания до prepare. Mainline нужен проверенный bridge order, в том числе `prepare_prev_first`, и подтверждение физического LP11 до reset. Затем prepare приобретает питание и переводит pinctrl/reset в подтверждённое состояние. Enable отправляет последовательность DCS, сохраняя подсветку выключенной. Disable сначала убирает подсветку, при доступном link посылает off/sleep-in и выдерживает задержки. Unprepare возвращает pinctrl/reset в безопасное состояние, освобождает IBB → LAB → VDDIO и снимает link в порядке, согласованном с bridge. Отказ должен останавливать дальнейшие передачи, отпускать только приобретённые ресурсы и сохранять первый код ошибки и все ошибки выключения. При ошибке отключения повторный enable запрещён.

## Неизвестное

Номер LCD-модуля и физическая ревизия DDIC не установлены. Нет измерений холодного старта, подтверждённого порядка LP11 в MSM и соответствия BLLP/EoT для этой панели. Нет доказанной цепи REFGEN и точной модели подсветки. Поэтому прототип содержит режим и транспорт без probe, DSI attach, `drm_panel` callbacks или автоматического питания. Конечные node/graph/compatible будут определяться по подтверждённой схеме.
