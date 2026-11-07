# v8 — идентификация панели lemon

Для этого экземпляра подтверждён **профиль TD4330 Truly v2 video**. Точный номер LCD-модуля и ревизия DDIC остаются открытыми.

| Источник | Наблюдение |
|---|---|
| Архивный TWRP FDT `reports/live.dtb` | ABL выбрал `qcom,mdss_dsi_td4330_truly_v2_video` в `/chosen/bootargs`. |
| Архивный TWRP dmesg | Downstream DRM сообщил об успешной привязке того же профиля. Драйвер сенсора отдельно определил Truly LCD/TP. [Привязка](logs/v7-authorized/twrp-dmesg-before.txt#L877), [сенсор](logs/v7-authorized/twrp-dmesg-before.txt#L1565). |
| Stock boot DTB + stock DTBO entry 0 | Восстановленный узел `timing@0` совпал с TWRP FDT и скомпилированным исходником Xiaomi по всем свойствам vendor timing. |
| Свежая v7 через SSH | Работают firmware framebuffer и отдельный MSM GPU render node. Нативный DSI и Linux backlight отсутствуют. [Инвентаризация](logs/v8-research/identity.txt). |

Запись о привязке DRM подтверждает использование профиля драйвером. Она зависит от выбора ABL. Данные сенсора, связанные с парой Truly/Truly, получены из отдельного downstream probe, а строка производителя берётся из таблицы драйвера. Для точной ревизии нужны маркировка модуля, BOM или поддерживаемое этим DDIC чтение ID с отдельно проверенным протоколом.

Другие профили lemon включают NT36672D Tianma/Xinli и FT8719 Truly. Даже TD4330 Truly v2 **cmd** в исходнике Xiaomi задаёт 1080×2280 и отдельные пакеты. Выбранный video профиль задаёт 1080×2340 при 60 Гц. Его параметры инициализации сравниваются побайтно в `scripts/extract-display-v8.py`. [Исходник Xiaomi](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/02ca1a919564a9b176a79cce09c40977f833e9ac/arch/arm64/boot/dts/vendor/qcom/dsi-panel-td4330-truly-v2-singlemipi-fhd-vid.dtsi).
