# Идентификация подсветки lemon

## Подтверждено

Архивный DT описывает клиентов `qcom,sgm37603a_bl` и `ti,lm36923` на I²C GENI `4a84000` по адресу `0x36`. В TWRP второй client на этом адресе получил `-16`. GPIO99 — активная высоким уровнем линия enable. Профиль описывает PWM 100 мкс через PM6125 LPG `0xb300`, но в downstream ветке PWM обновление яркости закомментировано и вызывается `lcd_bl_set_led_brightness`. [Stock DT](reports/stock-merged.dts) · [TWRP](logs/v8-authorized/twrp-dmesg-before.txt) · [Xiaomi panel](downloads/v8-xiaomi-source/techpack/display/msm/dsi/dsi_panel.c#L749).

При профиле TD4330 код не выбирает ветку `ft8719`. Он печатает `ti_lm36823` по условию, затем пишет `0x07` в `0x10`. Записи яркости идут в `0x18/0x19`, с обеими величинами ноль для выключения яркости. Для LM36923 значение `0x07` включает chip/LED1/LED2, `0x18/0x19` — 11 бит яркости. Напечатанное имя не получено из регистра. Нулевой brightness и снятие enable — отдельные шаги. [Xiaomi I²C](downloads/v8-xiaomi-source/drivers/video/backlight/sgm37603a.c#L315) · [TI](https://www.ti.com/lit/ds/symlink/lm36923.pdf).

## Гипотезы и неизвестное

LM36923 — наиболее обоснованный кандидат. LM36923H имеет сходную карту и адрес. Точная микросхема, ревизия, режим регистра `0x11`, число физических цепочек LED и уровень PWM на плате не установлены. Номер в `0x00` для LM36923 обозначен как ревизия. Нужны маркировка, BOM или достоверная таблица идентификации. Серия KTD3136 для ginkgo годится как пример backlight API. Аппаратная применимость к lemon не подтверждена. [TI LM36923H](https://www.ti.com/product/LM36923H) · [KTD3136 RFC](https://go.mail-archive.com/dri-devel%40lists.freedesktop.org/msg634892.html).

Mainline `leds-lm3692x` поддерживает `ti,lm36923` через LED class и может подать питание уже в probe. Для DRM нужны один подтверждённый I²C consumer и явный backlight provider либо проверенный LED-to-backlight bridge. Для раздельного кадра и подсветки первый modeset обязан оставить backlight gated, независимо от обычного автоматического включения `drm_panel_of_backlight`. Начальное состояние должно оставаться выключенным. Драйвер, DT consumer и GPIO99 не активированы.

## Схема платы J19S

На листе 27 схемы Huaqin J19S_MB_V1 Rev 1.0 у U2732 указан **LM36923YFFR**. Видны APPS_I2C, HWEN от GPIO_LCM_LED_EN и две линии LED cathode. Это аппаратное свидетельство для проекта платы, независимо от Android драйвера. На том же листе есть таблица альтернативных обозначений LM3697/KTD3136 с тем же `0x36` и варианты PWM/CABC с незапаянными позициями. Выбор компонента на конкретной NFC-плате всё ещё требует совпадения ревизии и BOM/маркировки U2732. Один адрес, код ревизии или строка dmesg не позволяют подтвердить установленный вариант. До этой проверки `ti,lm36923` остаётся отключённым. [Схема, лист 27](https://www.scribd.com/document/613010966/Xiaomi-Redmi-9T-Schematic-pcb) · [TI LM36923](https://www.ti.com/lit/ds/symlink/lm36923.pdf).

TI указывает маркировку `36923` для LM36923YFFR и LM36923YFFR.A. Макрофото читаемой маркировки U2732 вместе с идентификацией ревизии платы или заводской BOM может подтвердить семейство для данного аппарата без обращения к I²C. Для определения точного заказного суффикса нужна BOM. [TI, Package Option Addendum](https://www.ti.com/lit/ds/symlink/lm36923.pdf#page=42).

## Сверка для NFC

Xiaomi указала одинаковый PCB layout у M2010J19SL и NFC M2010J19SY. Это помогает сопоставить семейство платы, но не связывает серийный аппарат с конкретной ревизией схемы или BOM. [Заявление Xiaomi](https://fcc.report/FCC-ID/2AFZZJ19SY/5086250.pdf).

| Категория | Данные |
|---|---|
| Подтверждено схемой | J19S Rev 1.0, лист 27, U2732 LM36923YFFR. Вход от VPH_PWR, выход `LCD_BL_LED_A`, два cathode nets, HWEN от GPIO_LCM_LED_EN, APPS_I2C и вариантные цепи PWM/CABC. |
| Подтверждено Device Tree | GENI `4a84000`, `0x36`, GPIO99. Два альтернативных I²C-описания на одном адресе. PWM 100 мкс указан для выбранного профиля. |
| Подтверждено исходниками | Xiaomi для TD4330 использует I²C brightness 0x18/0x19 и таблицу преобразования вместо вызова PWM. Mainline `leds-lm3692x` знает `ti,lm36923`, управляет LED class, выбирает строки и поднимает enable при инициализации. Для DRM нужен отдельный согласованный backlight provider/bridge и удержание выключенного состояния до разрешённого теста. |
| Требует физической проверки | Ревизия PCB и состав монтажа U2732, маркировка `36923`, варианты PWM/CABC, режим яркости и подтверждение безопасного минимума. |

[Схема](https://www.scribd.com/document/613010966/Xiaomi-Redmi-9T-Schematic-pcb) · [Mainline LED driver](https://linux.googlesource.com/linux/kernel/git/torvalds/linux/+/077ab8985ee278c3d8618182d335b0f0cd919e16/drivers/leds/leds-lm3692x.c) · [Осмотр](BOARD_VERIFICATION_GUIDE.md).
