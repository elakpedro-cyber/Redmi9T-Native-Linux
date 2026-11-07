# Stage C/A — диагностика v8b только чтением

Телефон ответил на SSH по NCM `192.168.77.2` с ранее закреплённым через COM4 ключом сервера. Ядро `7.4.0-rc1-lemon-bringup-v8b` подтверждено до и после. COM4 для этого сбора не понадобился. Команды передавались в stdin, результаты писались на ПК. Приватные ключи, содержимое каталогов SSH и сырые свойства /chosen не собирались. [Полный лог](logs/v8-stage-c-a/hardware.txt) · [Команды](logs/v8-stage-c-a/read-only.sh) · [Сравнение](logs/v8-stage-c-a/comparison.txt).

## Display clocks и PLL

- Из уже смонтированного debugfs считаны программные счётчики и сохранённые parent links 27 clocks DSI/DISPCC. У всех `enable_count=0`. Только `disp_cc_mdss_ahb_clk` и его source имеют `prepare_count=1`. Prepare reference не равен аппаратному enable.
- Цепочки byte/pixel идут через `dsi0pllbyte` и `dsi0pll` к 14-нм `dsi0vco_clk`, чей parent — `bi_tcxo`. MDP и LUT получают clock от `disp_cc_mdss_mdp_clk_src → disp_cc_pll0_out_main → disp_cc_pll0`. AHB, ESC, ROT и VSYNC в снимке восходят к `bi_tcxo`, sleep clock к `sleep-clk`. Список links и счётчики сохранены полностью.
- **DISPCC PLL0** зарегистрирован, enable/prepare 0/0 в обоих снимках. 768 МГц и признак `PLL_LOCK_DET` относятся к чтению Stage B. Текущий аппаратный lock неизвестен. Нулевые счётчики Linux не доказывают состояние, оставленное firmware.
- **DSI PHY PLL** зарегистрировал VCO, byte и pixel providers, счётчики 0/0. PHY runtime suspended. Захват и состояние lanes не проверены. Оценка частоты VCO и индикатор Y из Stage B не подтверждают lock этого 14-нм PLL.

Глобальные `clk_summary` и `clk_dump` пропущены после проверки исходников сборки. Они вызывают `clk_pm_runtime_get_all()` и могут временно разбудить контроллеры. Отдельный `clk_rate` также пропущен, поскольку он пересчитывает rate через driver callback. Считанные `clk_parent`, `clk_flags` и счётчики используют сохранённые поля ядра. Поэтому отчёт различает программные ссылки и физическую активность.

## Регуляторы, REFGEN и LCDB

| Объект | Что подтверждено |
|---|---|
| Регуляторы v8b | 28 зарегистрированных объектов. 25 RPM-регуляторов `s6–s8`, `l1`, `l4–l24`, ещё `vph_pwr`, `usb_vbus` и общий программный `regulator-dummy`. Полные имена, пути и constraints в логе. Наличие объекта не измеряет напряжение. |
| DSI VDDA | Свойство live DT `vdda-supply=<0x4d>` разрешается в PM6125 L18. У L18 ограничение 1 232 000 мкВ, `num_users=0` в снимке. Stock DT отдельно описывает `vdda-1p2` с 1,232 В и enable load 21,8 мА. |
| LCD VDDIO | Android phandle ведёт к PM6125 L9. Профиль панели задаёт 1,8 В. L9 зарегистрирован в v8b, `num_users=0`, ограничения провайдера 1,8–2,0 В. Это не текущее измерение напряжения. |
| REFGEN | Live DT не содержит `refgen-supply` у DSI host, отдельный provider не обнаружен, `CONFIG_REGULATOR_QCOM_REFGEN` выключен. DSI v2.4 bulk-запросил `refgen` и framework подставил общий dummy, что подтверждено dmesg. Dummy также использован другими потребителями, его общие `use_count=8` и `open_count=28` нельзя приписать одному DSI. |
| LCDB | PMI632 SID 3 есть в live DT. Узла `0xec00`, LCDB-драйвера и LDO/NCP regulator devices в v8b нет. Android DTB с применённым DTBO содержит PMI632 LCDB, IRQ `<3 0xec 1 1>` и ссылки LAB/IBB на LDO/NCP. Архивный TWRP сообщал о bias +5,5/−5,5 В и boost 5,65 В. Физическое состояние LCDB в текущей загрузке неизвестно. |

В stock DT `refgen` присутствует в списке core supplies с нулевыми значениями напряжения и нагрузки, без ссылки на provider. Это объясняет разницу между описанием потребителя и отсутствием привязки в Linux, но не определяет владельца физического REFGEN. [Stock DT](reports/stock-merged.dts#L15418) · [Исследование REFGEN](V8_REFGEN_RESEARCH.md) · [LCDB v2](https://lkml.rescloud.iu.edu/2610.2/06632.html).

Из debugfs regulator прочитаны программные счётчики и `supply_map`, который оказался пуст. Полный `regulator_summary` и sysfs `microvolts/state/status` не читались. Они вызывают driver callbacks, безопасность которых для всех провайдеров не была установлена. Данных о физических напряжениях в этом отчёте нет.

## Power domains и сравнение снимков

`5e00000.display-subsystem` привязан к `msm-mdss`, его `mdss_gdsc` показывает `off-0`. Host `5e94000.dsi` привязан к `msm_dsi` и относится к RPM `cx`, который показывает `off-0`. DPU с той же DT-зависимостью отключён. PHY `5e94400.phy` привязан к `msm_dsi_phy`, отдельного `power-domains` в его узле нет. DT связывает его с DISPCC AHB и RPM XO. MDSS использует GCC AHB/AXI, DISPCC, interconnects и SMMU streams `0x420/0x421`. RT и NRT MM-SNoC MMU TBU votes видны как on. GPU GX/CX off в покое, USB и UFS domains on.

MDSS, Host и PHY оставались runtime suspended. Накопленное active time не изменилось — 66/0/19 мс. Совпали 77 сравниваемых полей, включая clock counts, UFS I/O, runtime status и active time. Очередь deferred probe пуста. UFS sda–sdf обнаружены, записи/discard/flush по счётчикам нулевые, дисковых mounts и swap нет. DSI bus пуст, DPU и подсветка disabled, framebuffer остался SimpleDRM. Показатели учитывают только наблюдаемые поля двух снимков.

## Перед Stage C/B

1. Подтвердить владельца и реализацию REFGEN на SM6115 из документации или downstream исходников. Текущий dummy нельзя считать доказательством питания.
2. Для LCDB закрыть offline проверки cold start и handoff, общего enable, частичных записей, ошибки выключения, SC и разряда. До подачи питания нужны подтверждённые пределы и способ независимо измерить обе bias-шины. Linux отсутствие LCDB-узла не устанавливает исходный физический уровень.
3. Определить неразрушаемый критерий lock DSI PHY PLL и место LP11 до reset. Это отдельный этап после проверки питания. До активации подсветки подтвердить модель и начальное состояние.
4. Согласовать отдельный Stage C/B по [плану A–G](V8_STAGE_C_FIRST_BOOT.md). Новых оснований для активного DT, LCDB probe или образа v8c эти данные не дали.

Телефон оставлен на v8b. Диагностика не включала прошивку, перезагрузку, монтирование или изменение clocks, regulators, GPIO и I²C.
