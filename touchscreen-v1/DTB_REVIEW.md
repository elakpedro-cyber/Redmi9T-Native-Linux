# Touchscreen v1 — отдельный DTB, только офлайн

**Аппаратный допуск отозван для этого CS1-кандидата.** Последующий binary/source audit доказал runtime CS0, несмотря на stock DT child@1. См. `../TOUCHSCREEN_STAGE1_FINAL.md`. Успех schema/exact-delta ниже означает структурную проверку, не правильность выбора фактического CS. Файл63732байта сохранён неизменным как история; не применять на телефоне.

Разрешение владельца: собрать отдельный кандидат и проверить на ПК. Прошивка, загрузка DTB на телефон, SPI probe и изменение питания не разрешались и не выполнялись.

## Артефакты

В `artifacts/touchscreen-v1/dtb-review/`:

- `touchscreen-handoff-review.dtb` — полное кандидатное дерево на основе неизменённого v8b DTB;
- `touchscreen-handoff-review.dtbo` — минимальный overlay;
- `touchscreen-handoff-review-overlay.dts` — воспроизводимый источник overlay.

Base SHA256: `a752c54ee87e525c69b5c13086e700f5ac19cf39a843c3263e08e5906414569e`.
Candidate:63732байта, SHA256 `3b0f9e4281cabcd2a1e6120f6373250e7881866d51743d2075235af98a8605d4`.
Итоговый manifest/размер следует сверять с `logs/touchscreen-v1/dtb-review/delta.json` и `artifacts/touchscreen-v1/release-dtb-review.json`.

Это **disabled review candidate**, не образ для испытания касаний: Novatek child выключен, property `xiaomi,validated-touch-handoff` отсутствует. Он не исправляет отсутствие драйверов в работающем v8b и не подтверждает питание/firmware handoff. Отдельный boot.img или kernel не собирался.

## Точный delta

Из существующих свойств изменяются только `num-cs` и `pinctrl-0` SPI2. Добавлены child `touchscreen@1` и две stock pinctrl-группы. Chip select1, mode0,9,6MHz, IRQ TLMM93 rising, raw delay200/0,геометрия1080×2340. Новых supply/reset consumers и разрешения на probe нет.

Проверяется полное равенство остальных node/property bytes, включая все существующие phandle, regulators, framebuffer, clocks, MDSS/DSI, GPU, UFS, memory/chosen. Memory reserve map и boot CPU сохраняются. Новые pinctrl phandle и IRQ phandle разрешаются внутри итогового дерева, не копируются из Android DTB.

## Почему не используется DTB → DTS → DTB

При первой офлайн-попытке установленный dtc экспортировал PM6125 L15 `regulator-max-microvolt` как неоднозначную строку `"\01Q"`. Повторная компиляция изменила исходные4байта `00 31 51 00` на3байта `01 51 00`. Exact-delta check отклонил результат. Эта ошибка не переносилась на телефон.

Сборка теперь работает с исходным бинарным DTB через fdtoverlay. Единственный временный symbol tlmm добавляется в копию base для разрешения существующего phandle; SPI target задаётся абсолютным путём, поскольку его base node не имеет собственного phandle. После merge временная symbol table удаляется. Исходный base не меняется.

Отвергнутые материалы изолированы в `logs/touchscreen-v1/dtb-review/rejected-roundtrip/`. `*-inspection.dts` — только экспорты для чтения; их нельзя использовать как build source. Собирать следует из overlay source и исходного бинарного base.

## Проверки и воспроизведение

На существующем WSL:

```sh
bash touchscreen-v1/build-dtb.sh
```

Скрипт не обращается к телефону. Он собирает overlay, применяет его к PC-копии DTB, проверяет точный delta и негативные случаи, затем проверяет схемы с существующим Linux tree и локальным fixture binding. Binding частный, не принят upstream; зарезервированный адрес `.invalid` в его metadata — явно не настоящий maintainer.

- DTC overlay: без предупреждений. Merged DT:12старых предупреждений, совпадающих с v8b; новых нет. Среди исходных предупреждений — альтернативные I2C/SPI unit-address и placeholder clock SimpleDRM, не изменения сенсора.
- Пять негативных тестов отвергают status=okay, неправильные CS/IRQ, наличие authorization property и изменение постороннего напряжения.
- Полные выводы схем и статусы находятся в `logs/touchscreen-v1/dtb-review/`. PASS следует считать подтверждённым только при `result.txt=OFFLINE_TOUCH_DTB_BUILD_AND_SCHEMA_PASS` и пустом `candidate-schema.txt`; schema check не является аппаратным допуском.
- Контрольные v8b DTB, Image, boot.img, архив GNOME v2.1 и session.sh проверяются по SHA до/после. Новый kernel или boot image не строятся.

## Нужна ли ещё прошивка

Для этой работы — нет. Уже есть оригинальные DTB/DTBO, сохранённые vendor/recovery и Xiaomi kernel sources с Novatek SPI-драйвером. Драйвер изучается по исходникам, а не восстанавливается из случайной прошивки сходной модели.

Если позже понадобится cold firmware loading, потребуется точно сопоставить stock MIUI/recovery build и реально поданный сенсору файл: найденный personal blob имеет metadata6, исторические логи — runtimeFW5. Это не основание прошивать сенсор или брать firmware другой ревизии. Пока handoff-only драйвер ничего не загружает.

Следующий аппаратный этап остаётся закрыт до подтверждения существующего питания/SRAM handoff и отдельного согласования регистрации SPI child и GENI probe. Stage C/B для повторной инициализации LCD остаётся NO-GO. Рабочий v8b/GNOME v2.1 сохранён.
