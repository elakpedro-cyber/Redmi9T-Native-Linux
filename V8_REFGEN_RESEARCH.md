# REFGEN на SM6115

## Подтверждено

В [stock DT](reports/stock-merged.dts#L15418) host DSI0 имеет `refgen` в `qcom,core-supply-entries`. Min/max и enable/disable load равны нулю. `refgen-supply`, отдельного узла провайдера и его MMIO-адреса в дереве нет. Отдельная линия `vdda-1p2` имеет явный phandle и заявленные 1,232 В / 21,8 мА. В mainline lemon аналоговая линия host описана через PM6125 L18.

В `drivers/gpu/drm/msm/dsi/dsi_cfg.c` Linux 7.4-rc1 общая конфигурация DSI v2.4 для SDM845/SDM670 и host по адресу `0x5e94000` запрашивает `vdda` и `refgen` через bulk regulator API. При отсутствии описанного провайдера core вернул dummy. На v8b host и 14-нм PHY привязались. [Аппаратный журнал](logs/v8b-authorized/host-clock-deferred.txt).

Серия Qualcomm добавляет реальные MMIO-провайдеры и ссылки из DSI для SC7180, SDM845, SDM670, SM6375 и других SoC. В binding есть варианты SC7180 и SM6375 с fallback SDM845. В проверенном binding и серии отсутствует SM6115. Патчи описывают внутреннее опорное питание DSI. [Серия Qualcomm](https://patchew.org/linux/20250921-refgen-v1-0-9d93e64133ea%40oss.qualcomm.com/) · [Binding](https://code.googlesource.com/linux/torvalds/linux/+/7acf90feab8b009fde7def08ff2c622d0f10e99f/Documentation/devicetree/bindings/regulator/qcom%2Csdm845-refgen-regulator.yaml).

## Гипотезы и неизвестное

REFGEN на SM6115 может быть доступен как внутренний управляемый блок либо оставаться включённым другой частью платформы. Запись downstream без phandle допускает обе интерпретации. Совпадение поколения host и адреса DSI между SoC не устанавливает адрес REFGEN. Отдельный регулятор, его статус после cold boot и нужность изменения DSI config остаются открытыми. Dummy warning сохраняется.

Для будущего link-теста нужны доказанная схема REFGEN, корректные host VDDA, VDDCX/OPP, MDSS GDSC, AHB и XO PHY, выходы byte/pixel PLL, а также подтверждённое состояние LP11. Нужен исходник или документация Bengal с адресом и семантикой enable либо подтверждение штатного управления REFGEN на SM6115. Не добавлен фиксированный источник и не заимствованы регистры соседней SoC. [SM6115 lemon v5](https://lore-kernel.gnuweeb.org/lkml/20260821-next-patches-v5-5-ec81cee63e09%40gmail.com/T/).

## Уточнение Stage C/B

[Downstream Qualcomm Bengal](https://android.googlesource.com/kernel/msm-extra/devicetree/+/refs/heads/android-msm-redbull-4.19-android12/qcom/bengal-sde.dtsi) независимо подтверждает DSI core supply с именем `refgen` без provider phandle. Архивы TWRP этого lemon дважды показывают dummy REFGEN даже у stock DSI при успешной привязке выбранного профиля TD4330. Это сильнее подтверждает отсутствие Linux-управляемого провайдера в штатной конфигурации. Успешная привязка панели не указывает, как запитан REFGEN при холодном старте. [Bengal, сохранённый DTS](logs/v8-stage-c-b-preflight/bengal-sde.dtsi) · [TWRP](logs/v8-authorized/twrp-dmesg-before.txt#L859).

[Mainline qcom-refgen-regulator](https://code.googlesource.com/linux/torvalds/linux/+/7acf90feab8b009fde7def08ff2c622d0f10e99f/drivers/regulator/qcom-refgen-regulator.c) имеет разные схемы управления. SC7180/SDM845 используют семейство с BIAS_EN и BG_CTRL, SM6375 использует fallback SM8250 с PWRDWN_CTRL5. Физический адрес, compatible и способ управления для SM6115 не установлены. При доказанном provider существующий binding задаёт `refgen-supply` на **DSI controller**, который запрашивает питание; перенос свойства на PHY не поддерживается проверенным consumer path. Сначала нужен SM6115-специфичный документ или downstream provider с адресом, layout и описанием взаимодействия с firmware. [Bindings REFGEN](https://linux.googlesource.com/linux/kernel/git/torvalds/linux/+/7acf90feab8b009fde7def08ff2c622d0f10e99f/Documentation/devicetree/bindings/regulator/qcom,sdm845-refgen-regulator.yaml) · [Binding DSI](https://gbmc.googlesource.com/linux/+/7c1a9408ce5f34ded5a85db81cf80e0975901685/Documentation/devicetree/bindings/display/msm/dsi-controller-main.yaml).

## Обязательность зависимости

DSI v2.4 запрашивает REFGEN через обычный bulk regulator API. Поэтому из одного предупреждения нельзя вывести, что ресурс необязателен для SM6115. Dummy в штатном TWRP и в v8b подтверждает отсутствие provider в обоих деревьях. Штатная привязка TD4330 совместима с гипотезой о firmware ownership, но не показывает, что произойдёт при cold start или изменении состояния PHY. Нужны SM6115-специфичный register map либо документация о встроенном или firmware-controlled REFGEN. Решение остаётся блокером. [Downstream Bengal](https://android.googlesource.com/kernel/msm-extra/devicetree/+/refs/heads/android-msm-redbull-4.19-android12/qcom/bengal-sde.dtsi) · [Mainline REFGEN binding](https://linux.googlesource.com/linux/kernel/git/torvalds/linux/+/7acf90feab8b009fde7def08ff2c622d0f10e99f/Documentation/devicetree/bindings/regulator/qcom,sdm845-refgen-regulator.yaml).

Офлайн-патч и проверки отсутствующего, отключённого и ещё не зарегистрированного провайдера описаны в [отчёте bring-up](V8_DISPLAY_TOUCH_BRINGUP.md#refgen-и-pll). Владелец REFGEN остаётся неподтверждённым.

См. [итоговое заключение](REFGEN_SM6115_FINAL_ANALYSIS.md) с цепочкой вызовов Xiaomi и отдельным disabled DTB для VDD_MX.
