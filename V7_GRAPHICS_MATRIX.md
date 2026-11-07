> Историческая предварительная заметка после v6. Текущие результаты: V7_VALIDATION.md и V7_HARDWARE_MATRIX.md.

# v7 — предварительная матрица графики

**Гейт v6 пройден:** физические NCM/SSH/SCP и ACM подтверждены (V6_HARDWARE_RESULTS.md).
Начато только офлайн-исследование сохранённого mainline-кода. Нового graphics kernel
и аппаратных изменений не было. Неизвестные panel/touch модели не выдумываются.

| Узел | Поддержка в имеющемся исходном коде/DT | Сборка/офлайн | Подтверждение на данном Redmi9T |
|---|---|---|---|
| Adreno610 | sm6115.dtsi: adreno-610.0, GPU/GMU wrapper/SMMU/OPP; a6xx catalog | DT okay, но DRM_MSM=n; Mesa не установлен | GPU driver/render node/ускорение не подтверждены |
| SimpleDRM | Simple framebuffer от ABL | Драйвер встроен, конфигурация сохранена v6 | Работал в v4/v5, 1080×2340; это framebuffer, не GPU |
| MDSS/DPU | Подтверждён каталог dpu_6_3_sm6115.h, core6.3 | Native MDSS/DSI disabled в текущем DTB | Нативные modeset/scanout не подтверждены |
| DSI PHY/panel | Связи/питания частично описаны, полного panel path нет | Linux panel driver не выбран | Точная модель и ревизия панели неизвестны |
| Backlight | В lemon DTS есть ti,lm36923, disabled из-за вариантов панели | Драйвер этой платы не активирован | Подсветка от firmware не доказывает Linux backlight driver |
| Touch | Потенциальные mainline драйверы существуют, контроллер платы не определён | Touch node отсутствует, подходящий driver не включён | Touch input не зарегистрирован |
| Кнопки | pm8941_pwrkey/resin и gpio-keys | EVDEV и драйверы сохранены | Устройства зарегистрированы; все реальные нажатия отдельно не тестировались |
| Clocks/regulators/PHY | Зависимости SoC/питания есть в DTS | Их наличие не доказывает нужные частоты/состояния для графики | UFS/USB работают; это не верификация graphics rails/PHY |
| Mesa Freedreno | Пользовательский стек для Adreno; matching kernel/firmware нужен отдельно | В образе отсутствует, сборка не проводилась | EGL/GLES/hardware renderer не проверены |
| Weston/Wayland | Возможны программный и DRM backend как отдельные этапы | В rootfs отсутствует | Ни compositor, ни touch integration не проверены |

Предыдущие доказательства: HARDWARE_MATRIX.md, reports/hardware-v5-dt-audit.json,
логи graphics-input/gpu-driver в logs/v4-live-diagnostics, config/linux-v5.config,
сохранённые mainline DTS. Их датировка и статус не повышаются из-за переноса в v7.
Принятие точной панели/сенсора по невыбранному Android DT-узлу недопустимо.
Для новых выводов нужны данные именно установленного экземпляра платы.

После v6 офлайн подтверждены в pinned a6xx_catalog.c: Adreno610/GMU-wrapper,
SQE firmware a630_sqe.fw, ZAP a610_zap.mdt и таблица SM6115 speedbins.
Фактическая доступность и пригодность firmware для этой платы не проверены.
[Официальная Mesa документация](https://docs.mesa3d.org/drivers/freedreno.html)
описывает Freedreno для Adreno2xx–6xx; это поддержка семейства в исходном стеке,
не проверенный renderer на данном устройстве. Снимок source evidence:
reports/v7-post-v6-source-notes.txt. Ни Mesa, ни firmware на телефон не устанавливались.
