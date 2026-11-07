# v8b Stage B — результаты аппаратного испытания

Испытание Redmi 9T NFC lemon 5 ноября 2026 года. Один переход в TWRP, одна запись boot и одна загрузка v8b. Система стабильна и оставлена на v8b.

## Подготовка и запись

- По SSH сохранён [исходный снимок v8](logs/v8b-authorized/v8-baseline.txt). Образ отката [v8](artifacts/boot-linux-test-v8.img) имеет 24 698 880 байт и SHA-256 `563296819c9e22da2ffcc38918b0761ca3d18eed7ae181123796fd6fb1033a29`.
- У [v8b](artifacts/boot-linux-test-v8b.img) подтверждены 24 707 072 байта, Android boot header v2, страницы 4096 байт и побайтное совпадение трёх распакованных компонентов с эталоном. Повторная офлайн-проверка подтвердила native DT, отчёт схемы и 15 сценариев bootshim. В initramfs отсутствуют модули панели, LCDB и Novatek, MSM и DISPCC исключены из автозагрузки по alias. [Заголовок](logs/v8b-authorized/boot-header.txt) · [Компоненты](logs/v8b-authorized/boot-components.txt) · [Проверки](logs/v8b-authorized/offline-validation.txt) · [Initramfs](logs/v8b-authorized/initramfs-gates.txt).
- После подтверждённого физического входа в TWRP проверены root ADB, lemon, отдельный recovery и boot на `/dev/block/sde49`. TWRP уже смонтировал `/data` и `/cache` в RW. Оба отмонтированы до записи и проверены повторно. Возможные записи при раннем старте TWRP или отмонтировании исключить нельзя.
- Префикс boot совпал с v8 до записи. Образ передан в RAM `/tmp` и записан только в boot. SHA-256 обратного чтения 24 707 072 байт совпал с файлом `9ce181e8a6170ce8773a923f03dd10f5edb405d1990fa09b4f4bc12f2e59a610`. Полные SHA recovery, dtbo и vbmeta совпали до и после. [ADB](logs/v8b-authorized/adb-write-commands.txt) · [Журнал записи](logs/v8b-authorized/boot-write-journal.json).

## Результаты

| Проверка | Наблюдение |
|---|---|
| Базовая система | `7.4.0-rc1-lemon-bringup-v8b`, маркеры init и OpenRC, Alpine 3.24.4, apk 3.0.9, службы health, net и sshd запущены. |
| ACM и NCM | COM4 выполнил команды. Во время DISPCC/MDSS получены 12 из 12 ответов COM4. NCM поднялся на 192.168.77.1/30 ↔ 192.168.77.2/30, ping 3/3. Настройка Windows затронула только USB NCM. |
| SSH и файлы | SSH по ключу с проверкой host key, полученного по COM4. SCP/SFTP через RAM `/tmp` с совпавшим SHA. SSH остался доступен после привязки MDSS и проверки хоста. |
| UFS | Видны sda–sdf. В Linux дисковые mounts и swap отсутствовали, записи, discard и flush по счётчикам LUN нулевые. |
| GPU | До активации дисплейного тракта `renderD128`, MSM 1.13.0, Mesa 26.1.6 FD610. GLES шейдер отрисовал 256 проверенных RGBA-пикселей, SHA `ebec48648edef1e298a2e12473d1c837bfc6ce99151088606b4cda794434b9cb`. После DSI узел и привязка Adreno сохранились, новых GPU/IOMMU faults нет. Повторный рендеринг после DSI не выполнялся. |
| DISPCC и MDSS | `5f00000.clock-controller` привязан к `dispcc-sm6115`, `5e00000.display-subsystem` к `msm-mdss`. |
| DSI Host | Да. `5e94000.dsi` привязан к `msm_dsi`, отдельный read-only lookup ядра вывел `lemon-stage-b: DSI0 host registered`. |
| DSI PHY | Да, probe и регистрация clock provider. `5e94400.phy` привязан к `msm_dsi_phy`, зарегистрированы VCO, byte и pixel clocks. Физическая передача по DSI не проверялась. |
| Display PLL | DISPCC PLL0 показал 768 МГц и `hardware enable=Y`. Для `clk_alpha_pll_ops` этот флаг читается из `PLL_LOCK_DET`. Захват отдельного DSI PHY PLL не подтверждён. Его VCO отображался с нулевыми счётчиками, а `Y` для 14-нм VCO без `.is_enabled` подставляется ядром. |
| Состояние дисплейного тракта | MDSS, Host и PHY runtime suspended, `mdss_gdsc` off. SimpleDRM сохранился. MIPI DSI bus пуст, DSI connector и backlight class отсутствуют, зарегистрированы только кнопки. Команды панели, изменение GPIO и управление LCDB не выполнялись. Физические уровни питания не измерялись. |

## Привязка и предупреждения

Чтобы проверить Adreno первым, перед `modprobe msm separate_gpu_kms=1` в RAM установили временный `driver_override` только для MDSS. Дочерние DSI/PHY platform devices отсутствовали до и после теста рендеринга. После штатного probe DISPCC и проверки live DT override снят и один раз вызван штатный bind MDSS. Очередь deferred probe при финальном чтении пуста. Новых probe errors, таймаутов или IOMMU faults нет.

Новое предупреждение `msm_dsi 5e94000.dsi: supply refgen not found, using dummy regulator`. Оно не помешало регистрации хоста, но требует сверки питания с downstream SM6115 перед любым modeset. При старте также были сообщения об исправленных циклах DT-зависимостей и ожидании sync_state. Для Adreno повторились прежние предупреждения о dummy vdd/vddcx. Диагностический модуль пометил ядро как tainted из-за сборки вне дерева.

Офлайн-подготовку Stage C можно продолжить. До аппаратного включения остаётся проверить REFGEN, последовательность LCDB и подсветки и критерий захвата DSI PHY PLL. [Разбор питания](V8_DISPLAY_FOLLOWUP.md) · [Upstream REFGEN](https://www.spinics.net/lists/kernel/msg5852534.html).

[COM4 при загрузке](logs/first-test-v8/20261105T203336Z-identity.txt) · [NCM и SCP/SFTP](logs/hardware-v8/20261105T233411758) · [COM4 при probe](logs/v8b-authorized/gpu-com-monitor-result.json) · [Рендер](logs/v8b-authorized/gpu-render-once.stdout) · [DSI и clocks](logs/v8b-authorized/host-clock-deferred.txt) · [Конечное состояние и dmesg](logs/v8b-authorized/post-bind-state.txt) · [Финальная проверка](logs/v8b-authorized/final-status.txt).
