# GNOME Physical LCD v2 — 7 ноября 2026

**Обновление после подготовки:** один разрешённый аппаратный тест v2 C выполнен, пользователь подтвердил GNOME/Console на LCD и возврат tty1; VT2 освобождена без EBUSY. Есть shutdown warnings GNOME/GRD. [Фактические результаты и измерения](GNOME_PHYSICAL_V2_HARDWARE_RESULTS.md). Разрешение этой попытки использовано.

Ниже сохранено описание офлайн-подготовки пакета. Путь B испытан только на ПК. Телефон оставлен на v8b с tty1, GPU suspended; дальнейшие аппаратные запуски требуют отдельного согласования.

## Сохранённая версия v1

Полная контрольная копия: `snapshots/gnome-physical-lcd-v1/`, 77 файлов, 884 686 279 байт. `MANIFEST.json` содержит размер и SHA-256 каждого файла. Сохранены оба ARM64 userspace-архива, исходный GNOME SquashFS, boot v8b, DTB/config, launcher, watchdog, RDP, Weston, helper, журналы, снимки LCD и подтверждения пользователя. Секреты сеансов в копию не включены.

GNOME SquashFS: `d990fd141a24423b170e9db0e28837273f8fc0b18f2cb759611e29e5b3672d23`.
Boot v8b: `9ce181e8a6170ce8773a923f03dd10f5edb405d1990fa09b4f4bc12f2e59a610`.

Исходники v1 не переписаны. Новая реализация находится в `userspace/gnome-physical-v2/`. Полный запускной пакет v2 включает готовые GNOME/Weston root archives и собранные ARM64 helpers; новое ядро, DTB или boot.img не нужны.

## Рабочие маршруты

| Режим | Цепочка | Доказательство | Ограничение |
|---|---|---|---|
| C, основной | GNOME/FD610 → PipeWire → GRD TLS/NLA → local FreeRDP → Weston/Pixman → SimpleDRM/LCD | v1 — физический телефон; v2 — ARM64/QEMU, настоящие окна и ввод | v2 на FD610 ещё не запускалась |
| B, экспериментальный | GNOME → PipeWire raw frames → Mutter Devkit GTK presenter → Wayland → Weston/Pixman | Офлайн GNOME, Console, Settings и кадры без RDP | GPU и LCD в B ещё не проверены на телефоне |
| A, заблокирован | Mutter native → SimpleDRM, отдельный FD610 renderer | Анализ точной версии Mutter и сохранённые DRM caps | Нужны render-only/KMS-only topology и seat; существующий guard запрещает этот режим |

У B Devkit — официальный механизм nested в Mutter 50.2. Это не прямой EGL Wayland backend: вместо RDP-кодека используется PipeWire. Devkit presenter явно использует Cairo/wl_shm, Weston явно использует Pixman. На телефоне сам GNOME обязан использовать FD610; эти отдельные CPU-этапы не выдаются за GPU renderer. [Mutter Devkit](https://github.com/GNOME/mutter/blob/50.2/doc/building-and-running.md) · [Raw frame consumer](https://github.com/GNOME/mutter/blob/50.2/mdk/mdk-stream.c).

Mutter RemoteDesktop/ScreenCast D-Bus API в B используется для PipeWire/libei и не является RDP-соединением: GRD, TCP listener и RDP client в B не запускаются. В офлайн B Console приняла ввод, но на захваченном кадре часть начала тестовой команды потеряна; полную корректность набора команды и фокус нельзя считать подтверждёнными только по успешным D-Bus вызовам.

В эмуляции software rendering включается **явно**, только аргументом `offline`. Аппаратный launcher сохраняет `LEMON_REQUIRE_RENDER_NODE=/dev/dri/renderD128`, проверенный FD610 guard и проверку строки EGL renderer. Отказ GL не переключает режим автоматически.

## VT2: причина и исправление

В v1 helper открывал tty2 даже после выхода Weston, закрывал её и сразу выполнял `VT_DISALLOCATE(2)`. Последний close может ещё держать ссылку `vc->port.kref` до deferred `release_one_tty()` / `con_cleanup()`. `vt_busy()` тогда возвращает EBUSY. Этот сценарий воспроизведён в QEMU system ARM64 **с ядром v8b**; результаты находятся в `logs/gnome-physical-v2/vt-v8b-vm.txt`.

Это доказанная гонка старого алгоритма. Исторические аппаратные логи не содержат kref/FD снимка ровно в момент EBUSY, поэтому исключить для того отдельного события дополнительного владельца задним числом нельзя.

Новый `vt-cleanup`:

1. Проверяет controlling TTY и открытые FD всех процессов; живые владельцы tty2 или card0 вызывают отказ, без сигналов этим процессам.
2. Не открывает tty2, если уже активна tty1. Для оставшейся активной ownerless tty2 восстанавливает KD_TEXT/VT_AUTO и переключает tty1.
3. Проверяет текстовый режим tty1. Ждёт исчезновения ссылки через `VT_GETSTATE` до 2,5 с, затем просит ядро освободить только VT2.
4. Учитывает уже удалённую `/sys/class/vc/vcs2`: на исследованном ядре повторный ioctl может получить EBUSY из-за сравнения двух NULL в `vc_is_sel()`. Отсутствующая VC не создаётся заново ради cleanup.
5. При реальном EBUSY оставляет ресурс на месте и возвращает ошибку. Принудительного disallocate нет.

Порядок остановки: local RDP client → GRD и GNOME user session → Weston/seatd → system bus → оставшиеся процессы частного PID namespace → восстановление VT1. Пользовательская сессия получает stop marker и завершает дочерние процессы; её D-Bus не убивается раньше cleanup. Независимый watchdog начинает мягкое завершение за 5 с до жёсткого лимита. В пределе уничтожается только собственный PID namespace; чужие процессы, MSM и оборудование не выгружаются.

[vt_busy / VT_GETSTATE](https://github.com/torvalds/linux/blob/05441d697f7f9a927264f4058cbbc6a03dfcac9d/drivers/tty/vt/vt_ioctl.c) · [deferred TTY release](https://github.com/torvalds/linux/blob/05441d697f7f9a927264f4058cbbc6a03dfcac9d/drivers/tty/tty_io.c).

## Сессия GNOME 50 и GNOME Session 48

Длинный офлайн-тест выявил ошибку, невидимую в прежних 30/60-секундных сеансах: через 90 с legacy session manager выдавал `failed to register before timeout`, хотя настоящий Shell работал. Увеличение timeout это не исправляет. `X-GNOME-Autostart-Notify=false` в исследованном Session 48 проблему не решает и не используется как обход.

Добавлен `session-component.js`: он запускает настоящий Shell, проверяет PID владельца `org.gnome.Shell`, регистрирует собственный компонент с исходным startup ID, обрабатывает QueryEndSession/EndSession/Stop и отслеживает реальный выход дочернего Shell. Это lifecycle launcher, не подмена GNOME или его D-Bus сервисов. Незапланированный отказ Shell остаётся ошибкой. После исправления выполнен 120-секундный тест без registration timeout. [Session 48 startup tracking](https://github.com/GNOME/gnome-session/blob/48.0/gnome-session/gsm-manager.c).

Предупреждения об отсутствии GDM, NetworkManager, Polkit/GeoClue и colord пока остаются. Settings открываются, но сетевыми настройками телефона из GNOME управлять нельзя. Полноценная блокировка/аутентификация desktop-сессии ещё не завершена. Система пока не объявляется готовым повседневным телефоном.

## Измерения и оптимизация

`frame-trace.so` записывает monotonic timestamps непустых PipeWire buffers и Wayland surface commits. AArch64 variadic trampoline проверен передачей 12 integer и 12 double аргументов, включая stack arguments. Он не меняет framebuffer или режим дисплея.

`weston-debug timeline` доступен только в диагностическом прогоне с capture; фиксируются repaint begin/posted. Его события не равны физическому photon timing. Default launcher не делает постоянных PNG-захватов. Профиль `quiet` выключает анимации в приватном dconf в RAM; `baseline` сохраняет поведение v1. TLS/NLA, certificate pin и SSH host-key checking не ослаблены. Разрешение физического KMS остаётся текущим 1080×2340, `--current-mode`.

Сводки: `logs/gnome-physical-v2/offline-C-session/metrics.json` и `offline-C-release/metrics.json`. Для первого 120-секундного исправленного сеанса в QEMU: 32 непустых PW buffers, 32 commits RDP-клиента; средние update rates 0,441 и 0,397/с включают idle. Это **не FPS FD610 и не 60 Гц LCD**. Максимальный sampled aggregate PSS — 2 078 678 KiB с памятью QEMU. Median D-Bus input dispatch RTT — 2,441 ms, p95 — 549,86 ms; input-to-photon не измерялся. Median Weston repaint begin→posted — 2,753 ms, p95 — 3,323 ms, только PC software backend.

Точное время encode/decode, потери кадров, аппаратные FPS, CPU/PSS и input-to-LCD latency ещё требуют согласованного аппаратного теста. Нельзя вычитать counts PW/commits как точное число потерянных кадров: имеются initial commits, cursor updates и coalescing. Измеренного ускорения v2 на телефоне пока нет.

## Запуск после отдельного разрешения

Из PowerShell в каталоге проекта:

```powershell
.\scripts\Start-GNOME-Physical.ps1 -CheckOnly
.\scripts\Start-GNOME-Physical.ps1 -Mode C -Seconds 60 -Profile baseline -TestActions
# Из второго окна:
.\scripts\Stop-GNOME-Physical.ps1
.\scripts\Stop-GNOME-Physical.ps1 -Status
```

`-Mode B` выбирает Devkit явно, `-Mode A` выдаёт объяснение блокера. Прозрачного переключения B→C или hardware→software нет. Скрипты не меняют ExecutionPolicy и Windows IP. Они проверяют USB PnP/MAC, .77.1/30 и COM4. Контроллер открывает COM4 эксклюзивно на короткую проверку, не посылая команд; занятый порт — отказ, чужой терминал не закрывается.

SSH использует ключ из существующей локальной identity-конфигурации и COM-проверенный known_hosts. При новой загрузке несовпадение host key требует новой сверки через COM; `accept-new`/`StrictHostKeyChecking=no` не используются.

Root archives проверяются по SHA-256 до передачи и в RAM. Повторный запуск может использовать уже распакованный RAM-cache только той же загрузки, при отсутствии владельцев и монтирований. Режимы, источники и бинарники связаны с release manifest. При ошибке остановки RAM tree сохраняется для диагностики; никто не удаляет занятые mounts.

`Stop` оставляет неактивный RAM-cache для следующего старта, но временные credentials и TLS private keys удаляются. Для полного удаления после успешной остановки: `python userspace/gnome-physical-v2/control.py clean`. Эта команда ограничена записанным `/tmp/lemon-gnome-v2.XXXXXX` и отказывается при живых владельцах.

## Следующий аппаратный тест — ещё НЕ разрешён

Один сеанс **C, 60 с максимум**: read-only preflight SSH/NCM/COM4, FD610/MDSS isolation, RAM, отсутствие mounts/swap; baseline UFS/GPU. Только RAM staging, DRM master SimpleDRM card0, временная VT2, существующий режим. Console → короткая команда → Activities → Settings. Сбор CPU/PSS/температур и границ кадров. На 45-й секунде запрос Stop, жёсткий независимый deadline остаётся 60 с. Возврат tty1, отсутствие процессов, проверка GPU suspended и неизменности write/discard/flush всех LUN. При любой новой аппаратной ошибке — Stop; без повторов и без выгрузки MSM.

После успешного C можно отдельно согласовать такой же тест B и сравнить задержку на одинаковом сценарии. В этом этапе нет прошивки, reboot, новых драйверов, PMIC, GPIO или повторного включения MDSS/DSI/LCDB/REFGEN. Stage C/B для питания остаётся **NO-GO**.

## Восстановление

Основной путь: Stop → собственный watchdog → `vt-cleanup 1 2` → tty1. При остаточных владельцах helper сообщает PID/FD и ничего не отбирает. Сначала дождаться завершения конкретной сессии и сохранить логи. Не применять `killall`, `deallocvt --all` или отключение MSM.

Поскольку boot/kernel v8b не меняются, откат userspace — удаление только остановленного v2 RAM tree и использование сохранённого v1. Запуск v1 — тоже отдельный аппаратный сеанс, автоматически не выполняется. Boot v8b и старые TWRP-инструкции сохранены на случай отдельно разрешённого восстановления; текущая задача не требует TWRP.

Сенсор и native KMS: [отдельный отчёт](GNOME_PHYSICAL_V2_TOUCH_AND_KMS.md). Офлайн-проверки: [валидация](GNOME_PHYSICAL_V2_VALIDATION.md).
