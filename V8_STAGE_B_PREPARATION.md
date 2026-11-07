# v8b — отдельный тест регистрации DSI0

Кандидат `artifacts/boot-linux-test-v8b.img` проверен на ПК. Размер **24 707 072 байта**, SHA-256 `9ce181e8a6170ce8773a923f03dd10f5edb405d1990fa09b4f4bc12f2e59a610`. Рабочий откат для этого этапа — проверенная Stage A v8, 24 698 880 байт, SHA-256 `563296819c9e22da2ffcc38918b0761ca3d18eed7ae181123796fd6fb1033a29`. Резерв v7 также доступен.

DT включает dispcc, MDSS, DSI0 и PHY, а DPU и backlight остаются disabled. У DSI0 нет panel child. Свойство `resets` удалено только у MDSS, поскольку текущий MSM выполняет reset на 20 мс в `msm_mdss_init` до создания дочерних устройств. Отсутствие optional reset позволяет пропустить этот путь. LCDB, Novatek и прототип транспорта TD4330 отсутствуют в загрузочном тракте.

В v8b dispcc собран отдельным модулем и добавлен в blacklist автоматической загрузки. MSM также остаётся ручным. После загрузки базовая проверка идёт через COM/SSH до любых bind. Ручной probe dispcc всё же программирует PLL, а probe DSI/PHY обращается к clocks и display power domains. Это часть предлагаемого Stage B и может нарушить унаследованный scanout, даже если SimpleDRM остаётся зарегистрирован. Нужен оператор у телефона для аварийного TWRP.

Проверки на ПК прошли. Финальный DT отличается от A только четырьмя status и удалением MDSS reset, dt-validate чист, AOSP unpack сверил компоненты, 3 модели ABL placement и 15 сценариев bootshim прошли. Сравнение rootfs подтвердило прежние userspace файлы, разрешённые отличия ограничены модулями и blacklist dispcc. Отдельный `dsi-host-check.ko` собран с modpost, он проверяет присутствие DSI0 в списке зарегистрированных MIPI DSI hosts ядра и печатает маркер.

## Предлагаемое ограниченное испытание

1. При доступном операторе сохранить логи A, сверить SHA обоих образов. Через TWRP записать один раз только boot и сверить точный readback, как в Stage A. При потере связи восстановить Stage A v8 через аппаратный вход в TWRP.
2. Один раз загрузить v8b. Подтвердить release `7.4.0-rc1-lemon-bringup-v8b`, COM, NCM, pin серверного SSH, OpenRC, отсутствие дисковых mounts/swap и записи UFS. Маркеры init/OpenRC по-прежнему содержат V8. Убедиться, что SimpleDRM доступен и модули dispcc и msm ещё не загружены.
3. С параллельным мониторингом COM один раз вручную загрузить `dispcc-sm6115` с таймаутом. Проверить, что USB и SimpleDRM доступны, и просмотреть новые сообщения clocks/regulators. Только при успехе один раз вручную загрузить `msm separate_gpu_kms=1` с таймаутом.
4. Проверить driver bindings MDSS, DSI и PHY, отдельно выполнить `modprobe dsi-host-check` и получить маркер `lemon-stage-b: DSI0 host registered`. Повторно сверить отсутствие panel child, DSI connector, touch/backlight bindings и изменений UFS. Критерий успеха — зарегистрированы host и PHY, сохранены COM/SSH и SimpleDRM, нет новых ошибок.
5. При timeout, fault, clock/regulator error, потере SimpleDRM или USB прекратить probe и сохранить доступные логи. Для восстановления использовать Stage A v8, readback ровно 24 698 880 байт. Успешная регистрация host не включает тест DCS, LCDB, подсветки, сенсора или modeset.
