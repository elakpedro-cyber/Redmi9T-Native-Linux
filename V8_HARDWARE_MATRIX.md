# v8 — статус компонентов

| Компонент | Доказательства на телефоне | Статус v8 |
|---|---|---|
| Alpine, OpenRC, USB ACM/NCM, SSH/SFTP, UFS | Пройдены на v7 | Rootfs и опции сохранены, офлайн тесты прошли |
| Adreno 610 / Freedreno | v7, FD610 и 256/256 RGBA pixels | MSM v8 собран, прежние firmware и addon проверены, аппаратный регрессионный тест впереди |
| SimpleDRM | Firmware framebuffer v7 | Встроен и сохранён в DT |
| MDSS/DPU / display clocks / SMMU | Адреса и зависимости описаны в SM6115 DT | Собраны и проверены по схемам, probe отключён |
| DSI0 и PHY 14 нм | Выбранный downstream профиль и stock DT | Собраны, probe отключён |
| TD4330 Truly v2 video | ABL и привязка TWRP | Сверены параметры и пакеты, собран прототип транспорта. Точная ревизия LCD не установлена |
| LCD bias | PMI632 LCDB, исходное состояние TWRP 5,5/5,5 В | Внешний модуль компилируется, power lifecycle на этой плате ещё не проверен |
| Подсветка | GPIO99 и PWM в профиле, неоднозначный I²C probe 0x36 | Отключена, требуется сверка bound driver и LPG |
| Novatek NT36672A | Trim ID, PID 5940 и FW5 в TWRP | Отдельный план SPI, отсутствует touch child |
| Видимый кадр / page flips | В v7 проверялся headless GPU | Запланированы отдельные этапы с наблюдением экрана |
