# GNOME 50 на LCD Redmi 9T NFC

7 ноября 2026 года выполнены два разрешённых сеанса, ограниченные watchdog на 30 и 60 секунд. **Настоящий GNOME Shell 50.3 с Mutter 50.2 и рендерингом FD610 отображён на встроенном LCD.** Пользователь подтвердил GNOME с верхней панелью и Console после первого сеанса, а после второго — смену экранов и возврат текстовой консоли.

## Рабочий путь C

`GNOME/FD610 → PipeWire/GRD → локальный RDP TLS/NLA → wlfreerdp → Wayland → Weston/Pixman → SimpleDRM card0 → LCD`.

GNOME использует подготовленный Desktop SquashFS, распакованный на ПК без изменения содержимого и переданный в RAM телефона. Weston работает как полноэкранная kiosk-сессия с текущим KMS-режимом 1080×2340 на временной VT2. GNOME остаётся headless, его кадры транслируются локальному клиенту. Скриншоты сняты с вывода Weston, который в этих испытаниях обслуживал LCD. Это программные захваты вывода, фотографии камеры не делались. Видимость на физическом LCD подтверждена пользователем.

Сеть RDP ограничена отдельным network namespace без USB/home интерфейсов. Клиент использует NLA и точный SHA-256 fingerprint автоматически созданного сертификата. Пароль случаен, передаётся клиенту через stdin. Приватный TLS-ключ и пароль создаются в RAM, в журналы не выводятся и удалены с временным окружением. SSH сохраняет проверку host key, свёрку новой загрузки выполнили через COM4.

## Фактические результаты

| Проверка | Результат |
|---|---|
| GNOME Shell, верхняя панель и LCD | PASS, пользователь подтвердил оба сеанса. [Первый кадр с Console](logs/v8b-physical-gnome/hardware-30/wayland-screenshot-1970-01-01_00-11-25.png) |
| FD610 | В обоих журналах `LEMON_FD610_EGL_VERIFIED node=/dev/dri/renderD128 renderer=FD610`, создан GBM renderer. Software fallback не обнаружен. [Журнал второго запуска](logs/v8b-physical-gnome/hardware-60/shell.log) |
| Виртуальная клавиатура | Через отдельную Mutter RemoteDesktop input-сессию введена команда `echo GNOME_LCD_INPUT_OK`, ответ виден в Console. [Кадр с результатом](logs/v8b-physical-gnome/hardware-60/wayland-screenshot-1970-01-01_00-14-38.png) |
| Activities и обзор приложений | Отправлены Super и Super+A, получены соответствующие кадры. [Обзор приложений](logs/v8b-physical-gnome/hardware-60/wayland-screenshot-1970-01-01_00-14-43.png) |
| Несколько окон и переключение | Открыты Console и Settings, отправлен Alt+Tab. [Два окна](logs/v8b-physical-gnome/hardware-60/wayland-screenshot-1970-01-01_00-14-48.png) · [Журнал действий](logs/v8b-physical-gnome/hardware-60/input.log) |
| Указатель | Принята команда виртуального относительного движения. Физическая мышь и сенсор не испытаны. |
| Ресурсы | Минимум MemAvailable по выборкам — 1 397 736 KiB в первом и 1 267 896 KiB во втором сеансе. Максимальная прочитанная температура — 47,3 °C и 53,2 °C. Это выборки, CPU/PSS, FPS и задержка целиком не измерялись. |
| Восстановление | Watchdog остановил пространства процессов на 30/60 секундах. VT1 восстановлена, GNOME/Weston/seatd/GRD отсутствуют, GPU в suspended. При втором освобождении временной VT2 получен EBUSY после успешного возврата VT1. Helper исправлен: эта дополнительная операция сообщает состояние отдельно от обязательного восстановления KD_TEXT/VT_AUTO. Повторного графического запуска не было. |
| Сохранность | Счётчики write/discard/flush шести UFS LUN совпали и остались нулевыми. Новых GPU/IOMMU fault-сообщений нет. v8b и оба контрольных GNOME SquashFS совпали по SHA-256. [Проверка результатов](logs/v8b-physical-gnome/results.json) |

Дата 1970 года в именах аппаратных скриншотов отражает часы телефона после новой загрузки. Дату испытания задаёт время ПК. Во время сеанса Settings показали отсутствие NetworkManager, GNOME предупредил об отсутствии GDM для блокировки экрана. В журналах остаются предупреждения GRD/FreeRDP о TPM, RT scheduling, Kerberos realm, FUSE и `g_close(fd:0)`. Они не прервали показ. Полноценная пользовательская сессия с блокировкой, сетевыми настройками и физическим вводом требует дальнейшей интеграции.

## Почему выбрана трансляция

**A, native KMS.** У SimpleDRM есть KMS, у render-only MSM вызов GETRESOURCES возвращает EOPNOTSUPP. Mutter 50.2 в native-режиме перечисляет card-устройства и пытается построить для каждого KMS backend. Действующий проектный FD610 guard также допускает только headless. Нужны раздельное назначение render-only GPU и KMS-only выхода, ограниченный аппаратный renderer guard и активная пользовательская seat-сессия. В upstream есть CPU-copy в dumb buffer, но этот путь сам не добавляет render-only устройство в native-топологию. Рабочий headless патч сохранён. [Подтверждённая топология](logs/v8b-physical-weston/mutter-topology.txt) · [Mutter native](https://github.com/GNOME/mutter/blob/50.2/src/backends/native/meta-backend-native.c) · [CPU-copy](https://github.com/GNOME/mutter/blob/50.2/src/backends/native/meta-onscreen-native.c)

**B, Devkit.** В GNOME 50 для nested используется `--devkit`. Проверены установленный бинарник и ARM64-запуск поверх Weston на ПК. Shell запустился, но Devkit не получил кадр и сообщил timeout при создании RemoteDesktop-сеанса. У headless Weston также отсутствовала input seat, которую Devkit запрашивает. Сохранены исходники и журналы. Путь B не объявляется несовместимым с телефоном, аппаратные попытки на него не расходовали. [Документация Mutter 50.2](https://github.com/GNOME/mutter/blob/50.2/doc/building-and-running.md) · [Офлайн-журнал](logs/v8b-physical-gnome/offline-gnome.log)

**C, локальный RDP.** На ПК получен кадр GNOME через FreeRDP в Weston, затем выполнены два описанных аппаратных теста с FD610. Этот путь достиг цели отображения GNOME на LCD без управления DSI/LCDB/REFGEN.

## Запуск и остановка

Скрипты сохранены в проекте. Новые аппаратные сеансы требуют нового разрешения, текущие две попытки использованы.

- [Контроллер Windows](userspace/gnome50-v8b/physical-devkit-host.py) имеет команды `stage`, `run --limit 30`, `run --limit 60`, `stop`, `reset` и `clean`. Каталоги `hardware-30` и `hardware-60` защищают от случайного повтора этого испытания. Для следующего согласованного цикла назначить новую директорию журналов.
- [RAM-сессия и возврат VT1](userspace/gnome50-v8b/run-physical-devkit.sh), [DRM/VT helper](userspace/headless-v8/probe-simpledrm.c) и [виртуальный ввод](userspace/gnome50-v8b/physical-input.js).
- [Watchdog](userspace/gnome50-v8b/namespace-watchdog.c) ограничивает PID/mount/network namespace. Его завершение уничтожает потомков. `stop` посылает TERM только PID, исполняющему watchdog из известной RAM-директории.

После сохранения логов выполнен `clean`. RAM-окружение удалено, телефон оставлен на v8b с текстовой VT1 и работающей USB-связью. Прошивок, перезагрузок и новых операций с питанием дисплея не выполнялось. Stage C/B сохраняет NO-GO для повторной аппаратной инициализации.
