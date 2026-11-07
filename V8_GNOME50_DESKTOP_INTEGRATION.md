# GNOME 50 Desktop для Redmi 9T NFC

## Сборка и запуск

Контрольные `boot-linux-test-v8b.img` и `lemon-gnome50-rdp-v8b-aarch64.squashfs` сохранены с прежними SHA-256. Отдельный desktop SquashFS содержит подписанные Alpine 3.24 aarch64 Nautilus 50.1-r0 и GNOME Text Editor 50.1-r0, Console и Settings. Установлены зависимости и выполнены apk triggers. Shell 50.3, защищённый Mutter 50.2 и GRD совпали побайтово с контрольным пакетом. [APK-лог](logs/v8b-gnome50-desktop/stage.txt) · [Сборка](logs/v8b-gnome50-desktop/package.sh) · [SHA-256](logs/v8b-gnome50-desktop/sha256.txt)

Windows launcher `scripts/Start-LemonGnomeRdp.ps1` без аргументов проверяет NCM и клиент. `-Start` после отдельного согласования проверяет хеши и строгий SSH, применяет RAM-only staging, запускает сессию и локальный FreeRDP WSLg. `-StopRun <каталог сессии>` или закрытие клиента завершает сессию. Предельное время — 120 с, потеря heartbeat останавливает namespace. Профиль 480×720 выбран по умолчанию. 720×1280 и 720×1600 доступны как профили клиента для отдельной проверки, без динамического изменения в текущем протоколе.

Телефон стартовал с датой Unix epoch. В конфигурации v8b есть `RTC_HCTOSYS`, но PM8xxx RTC driver выключен и rtc0 не обнаружен. Перед TLS launcher сверяет системное UTC через закреплённый SSH с часами Windows и при существенном расхождении меняет Linux wall clock. Проверено повторным чтением. В RTC ничего не записывается, после перезагрузки сверка повторяется. [Сверка](logs/v8b-gnome50-desktop/hardware-1/clock.txt)

Сеанс без GDM использует отдельного пользователя, приватные D-Bus, runtime и сетевой namespace, GNOME Session 48 с проверенным non-systemd startup. GNOME Screen Shield в этой схеме сообщает об отключённой блокировке. Для временного доступа закрытие клиента завершает весь сеанс. Для постоянной сессии блокировка через интеграцию display manager/seat остаётся отдельной задачей. [GNOME Shell 50.3 Screen Shield](https://github.com/GNOME/gnome-shell/blob/50.3/js/ui/screenShield.js)

## Офлайн-проверки

- ARM64 QEMU прошёл privilege-drop preflight из финального SquashFS, включая ELF-зависимости четырёх приложений. Ошибочные runtime/TLS/device права и активный SIT были отклонены. Получены RDP-кадр, реакция мыши и сетка приложений. Приложения запустились как процессы. QEMU не дал достаточного визуального подтверждения их окон в первом коротком захвате. [Аудит](logs/v8b-gnome50-desktop/audit-final.txt) · [RDP](logs/v8b-gnome50-desktop/qemu-apps/rdp-client-controller.txt)
- ARM64 watchdog собран с `-Wall -Wextra -Werror`. Нативная сборка того же исходника в WSL проверена на предел 120 с, убийство PID namespace по deadline и разрыв heartbeat. QEMU user-mode не поддержал clone с этими namespace flags. ARM64 код отдельно запущен на телефоне. [Watchdog](logs/v8b-gnome50-desktop/watchdog-native-test.txt)
- Компиляция ARM64 LCDB-модуля прошла. Модель C-драйвера прошла 70 одиночных, 12 вложенных отказов и 128 конкурентных сценариев. TD4330 транспорт прошёл 158 инъекций ошибок. Disabled LCDB fixture проверен по DT schemas, KMS review fixture проверен отдельно и отклонён после искусственного включения DSI. [Дисплей и KMS](V8_GNOME50_PHYSICAL_DISPLAY.md)
- Проект OpenRC service для заранее подготовленного RAM staging сохранён в `userspace/gnome50-v8b/lemon-gnome.openrc`. Проверен синтаксис. Рабочий удалённый launcher управляет watchdog напрямую; проект службы не установлен.

## Аппаратные результаты

Первая попытка повторно получила реальный кадр GNOME через FD610 за 2,308 с от запуска RDP-клиента. Контроллер прервал сеанс, когда расширенный сбор метрик не вернулся по SSH за 5 с. Это ошибка мониторинга; состояние GPU и дисплейные guards проверены после остановки, новых сообщений ядра нет. Watchdog завершил процессы по разрыву heartbeat. В исправлении обязательные guards, температура, память и dmesg отделены от опциональной выборки PSS/DRM, которая ограничена двумя секундами. Имитация зависшего сборщика в ARM64 BusyBox завершилась вовремя. [Попытка 1](logs/v8b-gnome50-desktop/hardware-1) · [Регрессия мониторинга](logs/v8b-gnome50-desktop/test-telemetry.txt)

### Вторая попытка — четыре окна на физическом Redmi 9T

| Проверка | Результат |
|---|---|
| GPU и графика | Mutter 50.2, `LEMON_FD610_EGL_VERIFIED`, аппаратный GBM через renderD128. GNOME Shell 50.3 и виртуальный монитор 480×720. |
| Мышь, клавиатура | Клик по Activities открыл Overview. Super+A открыл сетку. В Console по RDP введена и выполнена команда `echo LEMON_RDP_KEYBOARD_OK`. Alt+Tab сменил активное окно на Files. |
| Приложения | На одном кадре одновременно видны Console, Settings, Files и Text Editor. Тест запустил их контролируемым helper от имени lemon через окружение сессии. Запуск самих приложений кликом из Activities не проверен. Settings открыл Network, но показывает отсутствие NetworkManager в приватном namespace. Files открывает RAM Home, индексатор отказывается извлекать содержимое без Landlock. |
| Задержка | GRD готов через 11,09 с от начала watchdog. Первый кадр через 2,722 с от запуска RDP-клиента. Одиночные переходы до первого изменения кадра: мышь 215 мс, клавиатура 381 мс. Два замеченных обновления после Super+A разделены 124 мс. Эти наблюдения включают приложение, сеть, клиент и дискретизацию захвата, устойчивый FPS и распределение frametime не установлены. |
| CPU/RAM | 41 контрольный сэмпл, 7 выборок расширенных метрик прерваны бюджетом. Пик общей загрузки CPU между сэмплами 45,61%. Минимальный MemAvailable 1 878 644 КиБ. Пик суммарного PSS наблюдавшихся процессов 486 031 КиБ (475 МиБ), без учёта всего tmpfs rootfs и прочих затрат ядра. |
| PSS / RSS | Shell/Mutter 140 397 / 206 828 КиБ, GRD 64 868 / 114 536 КиБ, Console 114 969 / 171 020 КиБ, Settings 99 979 / 177 092 КиБ, Files 63 524 / 136 132 КиБ, Editor 52 970 / 122 408 КиБ. Индивидуальные пики получены в разное время и не суммируются. |
| DRM | Максимум одного наблюдавшегося DRM-клиента — total 74 272 КиБ, resident 61 888 КиБ. Повторяющиеся fdinfo не суммировались. Счётчик двигателя до 331 мс, температура GPU 43,5–46,4 °C. |
| Завершение | Watchdog вернул 124 на 120 с, RAM очищена. SSH, COM4 и USB NCM работают. Ping <1 мс, MDSS по-прежнему заблокирован, GPU `suspended`, dmesg без новых сообщений, счётчики всех шести UFS LUN совпали. |

[Четыре окна](logs/v8b-gnome50-desktop/hardware-2/desktop-windows.png) · [Команда в Console](logs/v8b-gnome50-desktop/hardware-2/desktop-console.png) · [Сетка](logs/v8b-gnome50-desktop/hardware-2/desktop-app-grid.png) · [Mutter](logs/v8b-gnome50-desktop/hardware-2/gnome.txt) · [Сэмплы](logs/v8b-gnome50-desktop/hardware-2/samples.txt) · [Очистка](logs/v8b-gnome50-desktop/hardware-2/cleanup.txt)

### Разрешения виртуального экрана

| Профиль | Один XRGB8888 буфер | Доказательства |
|---|---:|---|
| 480×720 | 1,32 МиБ | Полный аппаратный тест; профиль по умолчанию. |
| 720×1280 | 3,52 МиБ | QEMU получил кадр с точным размером, 8,727 с от запуска клиента. Измерений на FD610 нет. |
| 720×1600 | 4,39 МиБ | Подготовлена настройка клиента. Буфер рассчитан без stride, выравнивания, дополнительного рендера и кодировщика. |

Сеансы ограничены по времени. Утечки и длительная отзывчивость не оценены. Доступ с Windows подтверждён автоматизированным FreeRDP внутри WSL; интерактивный запуск через WSLg подготовлен, его отдельный GUI-тест не выполнялся. [QEMU 720](logs/v8b-gnome50-desktop/qemu-720/rdp-client-controller.txt)

Физический экран остаётся заблокирован. [План KMS](V8_GNOME50_PHYSICAL_DISPLAY.md)

