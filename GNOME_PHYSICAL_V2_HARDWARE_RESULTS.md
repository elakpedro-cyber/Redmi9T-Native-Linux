# GNOME Physical LCD v2 — аппаратный тест C

**7 ноября 2026: выполнена ровно одна разрешённая попытка на Redmi 9T NFC, Linux v8b. GNOME Shell 50.3 с FD610 показан на встроенном LCD, введённая команда выполнена в Console. Возврат tty1 и освобождение VT2 прошли без EBUSY.** Пользователь подтвердил: «Да, GNOME виден; затем вернулась консоль».

## Образ и процедура

Использован подготовленный v2 C, профиль baseline, TestActions. Root archives и runtime payload прошли SHA-256 preflight на ПК; архивы после передачи проверены в RAM. Пакет: `artifacts/lemon-gnome-physical-lcd-v2-aarch64.tar.gz`, 549 080 249 байт, SHA-256 `88b81bbad652a7ef146031541f849a1e6520a324f671600528646d6c5fd3fedc`.

Boot/kernel/DTB не менялись. Сохранён маршрут:

`GNOME/FD610 → PipeWire → GRD TLS/NLA → local FreeRDP → Weston/Pixman → SimpleDRM → LCD`.

Запуск — существующий `Start-GNOME-Physical.ps1 -Mode C -Seconds 60 -Profile baseline -TestActions`. Аппаратный watchdog имел жёсткий предел 60 с. Отдельный наблюдатель запросил Stop на **45,94 с**. После остановки, включая сбор основных журналов, на отметке 52,70 с от запуска watchdog уже зафиксирована tty1. Жёсткий deadline не понадобился; `SESSION_EXIT=0`.

Один доверенный `weston-screenshooter` снял реальный кадр compositor output, дополнительного графического сеанса не было. Для измерений подключён штатный Weston timeline reader. Оба диагностических клиента запускались внутри PID/mount/network namespace теста и имели собственные timeout. Никакие процессы захвата не оставлены.

## Фактический результат

| Проверка | Результат |
|---|---|
| v8b, NCM, SSH, COM4 | PASS до и после. SSH с прежним проверенным host key; COM4 эксклюзивно открыт и закрыт без отправки команд. Windows IP не изменялся. |
| FD610 | `LEMON_FD610_EGL_VERIFIED node=/dev/dri/renderD128 renderer=FD610`, создан GBM renderer; software fallback не обнаружен. |
| GNOME Session lifecycle | `SHELL_COMPONENT_REGISTERED pid=242`; настоящий Shell запущен. Длиннее 90 с этот аппаратный тест не шёл; устранение прежнего registration timeout проверено отдельно офлайн. |
| Физический LCD | PASS, пользователь подтвердил. Сохранён PNG 1080×2340 с верхней панелью и Console. |
| Выполнение команды | На захваченном кадре видны `echo GNOME_LCD_INPUT_OK` и ответ `GNOME_LCD_INPUT_OK`. Это ввод в настоящий терминал, не заранее подготовленное изображение. |
| Activities, app grid, Settings, Alt+Tab | Команды переданы через приватную Mutter input-сессию; запуск Settings виден в журнале/процессах. Отдельный снимок Settings не делался, все эти экраны пользователь по отдельности не подтверждал. |
| Указатель | Команда относительного виртуального движения принята. Физическая мышь и touchscreen не тестировались. |
| VT cleanup | `TTY1_RESTORED`, `VT2_RELEASED deferred_checks=0`; EBUSY не возник. Живые владельцы и изолированные монтирования после теста отсутствуют. |
| GPU после завершения | `suspended`; MSM не выгружался и не перепривязывался. |
| Ошибки ядра | Между полными снимками dmesg нет новых строк; новых GPU/IOMMU faults нет. |
| UFS | Все шесть LUN сохранены, mounts/swap отсутствуют. Write/discard/flush counters совпали и остались нулевыми. Это доказательство по наблюдаемым счётчикам, не утверждение о внутренних служебных операциях контроллера. |
| Изоляция | MDSS override сохранён; MDSS и DISPCC unbound, DSI не активировался. Права системного `/run` и исходного render node не менялись. |
| RAM cleanup | Весь временный v2 tree удалён только после проверки отсутствия владельцев/mounts. Root cache и приватные RDP credentials на телефоне не оставлены. |
| Контрольная v1 | Все 77 файлов повторно сверены по SHA-256, несовпадений нет. |

## Измерения

Это короткий сценарий запуска/ввода с периодами idle, **не benchmark максимального FPS**.

| Показатель | Измерено |
|---|---|
| Shell constructor → первый непустой PipeWire buffer | 8,851 с по CLOCK_MONOTONIC в trace; это не время первого физического photon на LCD. |
| Выход GNOME/PipeWire | 73 непустых buffers за 31,031 с; средний update rate 2,32/с, максимум 13 событий в секундном bin. |
| RDP client → Weston | 62 surface commits за 32,423 с; средний update rate 1,881/с, максимум 12 в секундном bin. Initial commits, cursor updates и coalescing не позволяют объявлять разность counts потерянными кадрами. |
| Weston | 63 repaint submissions; begin→posted median 0,568 ms, p95 12,134 ms. Это длительность отправки repaint, не LCD scanout timing. |
| Ввод | 65 Notify-вызовов; D-Bus dispatch RTT median 10,993 ms, p95 108,915 ms, max 154,226 ms. Полная input-to-photon latency не измерена. |
| Пиковый sampled aggregate PSS | 912 835 KiB, около 891,4 MiB. Выборки могут пропускать короткие пики; это не вся занятая RAM с rootfs и kernel buffers. |
| Минимум MemAvailable | 1 256 284 KiB, около 1,20 GiB. |
| CPU, sampled aggregate peak | 190,20%, где один логический CPU = 100%; у SoC восемь CPU. Это примерно 1,9 CPU в самом занятом интервале выборки. |
| Отдельные process CPU peaks | Console 137,82%; Shell 109,15%; Settings 104,23%; FreeRDP 55,74%; GRD 45,57%; Weston 3,05%. Пики разных процессов приходятся на разные интервалы. |
| Температура | Максимум среди прочитанных thermal nodes — 57,6 °C. |

60 Гц текущего режима не выданы за 60 FPS GNOME. Время отдельных encode/decode стадий, точный GPU utilization и задержка физического LCD не измерены. PipeWire и Wayland counters показывают реальные границы передачи, а не точное число уникальных предъявленных панелью кадров. Ускорение относительно v1 не объявляется: сопоставимого аппаратного baseline v1 нет.

## Ошибки, которые остаются

После запроса Stop и удаления GRD virtual monitor появились userspace сообщения GNOME: обращение к disposed WindowPreview, Clutter sibling assertion, logical monitor/work area assertions и timeout ответа одного session client. Они находятся в фазе завершения, после Stop, и не сопровождались новыми kernel/GPU faults. Shell затем сообщил shutdown, все USER_STOP стадии прошли, tty1/VT2 очищены.

Это не следует скрывать: текущий порядок отключает RDP display до завершения Shell, и shutdown lifecycle ещё нуждается в улучшении. Следующая офлайн-задача — проверить порядок завершения Shell/GRD с сохранением monitor до закрытия UI, затем fault/timeout cleanup. Повторный аппаратный запуск автоматически не выполнялся.

Сохраняются известные предупреждения об отсутствии GDM/Polkit/NetworkManager, IBus и устаревших стилях Adwaita. Settings не могут управлять NetworkManager, которого нет. Touchscreen input device отсутствует. Поэтому подтверждён успешный короткий desktop-сеанс, а не готовый повседневный Linux phone.

## Доказательства и текущее состояние

- [Кадр с выполненной командой](logs/gnome-physical-v2/20261107T053802561073Z/wayland-screenshot-1970-01-01_01-21-45.png), SHA-256 `e5512297986790958f3a627251784d084a43c8cfc5acd093eee91ab3c2209a2b`. Дата 1970 в имени — RTC телефона; дата испытания определяется ПК.
- [Session/VT log](logs/gnome-physical-v2/20261107T053802561073Z/session.txt), [Shell](logs/gnome-physical-v2/20261107T053802561073Z/shell.log), [input](logs/gnome-physical-v2/20261107T053802561073Z/input.log).
- [Метрики](logs/gnome-physical-v2/20261107T053802561073Z/metrics.json), [CPU](logs/gnome-physical-v2/20261107T053802561073Z/cpu-analysis.json), [аппаратный анализ](logs/gnome-physical-v2/20261107T053802561073Z/hardware-analysis.json).
- [Контроллер](logs/gnome-physical-v2/hardware-C-approved/controller.txt), [observer/Stop](logs/gnome-physical-v2/hardware-C-approved/observer.txt), [postflight](logs/gnome-physical-v2/hardware-C-approved/postflight.txt), [подтверждение пользователя](logs/gnome-physical-v2/hardware-C-approved/user-confirmation.txt).

Телефон оставлен на **v8b, tty1, GPU suspended**, SSH/NCM/COM4 доступны. Прошивок, reboot, изменений USB gadget, UFS и питания дисплейного тракта не было. Stage C/B остаётся **NO-GO**. Путь B на телефоне не запускался; для него и любых следующих аппаратных сеансов нужно новое разрешение.
