# GNOME 50 на Alpine ARM64

## Обновление после Labwc r2

Собран ARM64 образ для офлайн-проверок `artifacts/lemon-gnome50-v8b-aarch64-offline.squashfs`. Это read-only SquashFS/gzip размером 317 833 216 байт, SHA-256 `a7267ececa24727fceb450379fe4d3143b73a88d803a85bdf681f3767e903f95`. Включает пакетный Shell 50.3, Mutter 50.2, Console, Settings, GNOME Session 48 и GRD 50.1. Каталоги runtime, тестовые сокеты и machine-id исключены. Launcher в образе ограничен офлайн-режимом.

GNOME Session 48 запустил Shell 50.3 через отдельный профиль headless с исходной фазой DisplayServer и без systemd. Журнал подтвердил fallback менеджера сессии к non-systemd startup и сообщение `GNOME Shell started`. Проверка относится к связке Session/Shell в минимальном профиле. Штатный профиль GNOME с полным набором Settings Daemon, вход через GDM и интеграция elogind остаются отдельными проверками. Обновление GNOME Session для минимального профиля сейчас не требуется.

Пиковое измеренное суммарное PSS процессов ARM64 chroot в прогоне Session 48 составило 994 310 KiB (971 MiB) при секундном опросе `smaps_rollup`. Это максимум выборки под QEMU без аппаратного GL и RDP. PSS не включает объём образа в tmpfs, а также будущий расход на GPU-буферы и RDP-кодирование. Начальный порог перед аппаратным тестом остаётся 2 GiB MemAvailable. Предпочтительный формат для телефона после допуска — образ gzip SquashFS в RAM, чтобы не держать весь распакованный rootfs в tmpfs.

В `userspace/gnome50-v8b/require-render-node.patch` подготовлено opt-in изменение Mutter 50.2. При `LEMON_REQUIRE_RENDER_NODE=/dev/dri/renderD128` оно требует native headless и аппаратный GBM на указанном узле, возвращает ошибку при отсутствии GPU и исключает ветвь GPU-less surfaceless. Проверено применение патча к upstream 50.2 в dry-run. Патч ещё не собран, официальный Mutter в офлайн-образе работает без него. Перед аппаратным допуском собрать Alpine-пакет Mutter, проверить отрицательный сценарий без render node и подтвердить EGL/GL renderer FD610 на первой ограниченной сессии. После этого допускается отдельная проверка интерактивного RDP. На телефоне GNOME пока не запускался.

Распаковка SquashFS в чистый тестовый каталог повторно подтвердила запуск Shell через Session 48. На одной сессионной шине обнаружены `org.gnome.SessionManager` и `org.gnome.Mutter.RemoteDesktop`. В отдельной network namespace с единственным loopback `grdctl --headless rdp set-tls-key` завершился SIGSEGV под QEMU. Прямая запись путей TLS через GSettings прошла, после чего SIGSEGV воспроизвёлся на `grdctl --headless rdp set-credentials`. Причина пока не установлена. RDP-демон в этом прогоне не дошёл до запуска, поэтому передача кадра и ввод из Windows остаются открытыми. Лог `image-smoke-rdp-gsettings.txt`.

## Пакеты и размер

Официальные индексы Alpine v3.24 aarch64 и установка с проверкой подписей в отдельный WSL rootfs подтвердили GNOME Shell 50.3-r0, Mutter 50.2-r1, Settings 50.3-r0, Console 50.0-r0, GTK4 `gtk4.0` 4.22.4-r0, Libadwaita 1.9.2-r0 и GNOME Remote Desktop 50.1-r0. Alpine предоставляет GNOME Session и gnome-shell-session версии 48.0-r3, а GDM версии 48.0-r6. Этот набор действительно смешанный по версиям. Испытана прямая загрузка Shell. Совместимость полного запуска через Session 48 с Shell 50 ещё не установлена. [Индекс community Alpine](https://dl-cdn.alpinelinux.org/alpine/v3.24/community/aarch64/APKINDEX.tar.gz), [Индекс main Alpine](https://dl-cdn.alpinelinux.org/alpine/v3.24/main/aarch64/APKINDEX.tar.gz)

После добавления GDM и polkit APK показал 549 пакетов и 848,8 MiB. Размер файлового дерева составил 893 169 423 байта до QA-артефактов. Один снимок WSL/QEMU дал GNOME Shell 418 780 KiB RSS и PipeWire 16 700 KiB RSS. В цифрах присутствуют накладные расходы эмуляции и общие страницы. Нативный RSS и пиковый расход RAM телефона неизвестны. Для первого теста с распаковкой предусмотреть минимум 2 GiB MemAvailable до передачи и не менее 1,4 GiB свободного tmpfs, затем проверить объём по фактическому архиву. Для снижения расхода можно подготовить read-only SquashFS с gzip, передать образ в RAM по USB и оставить изменяемые каталоги в tmpfs. В конфигурации v8b включены loop, SquashFS и zlib. Такой mount потребует отдельного согласования.

## Что запустилось офлайн

Скрипты `userspace/gnome50-v8b/start-shell.sh` и `offline-smoke.sh` запускают пакетный GNOME Shell в изолированном ARM64 chroot на ПК с отдельной сетевой и mount namespace. Подтверждены Mutter 50.2, виртуальный монитор 480×720, Wayland socket, запуск сервисов Shell на сессионной D-Bus и сообщение `GNOME Shell started`. Shell дошёл до штатного завершения по таймауту. Это GPU-less тест, Mutter сообщил `Created surfaceless renderer without GPU`. Доступность Activities, нескольких окон GNOME Console, Settings и RDP-клиента ещё не подтверждена.

В первом запуске отсутствовал `Gdm-1.0.typelib`, после установки GDM проявилось отсутствие typelib Polkit. Установка пакетов решила обе ошибки. Shell затем завершался в `TimeLimitsManager`, когда отсутствовала системная D-Bus. С отдельной системной шиной Shell продолжил работать, но сообщил об отсутствии `org.gnome.SessionManager` и о проблеме загрузки иконок. Тестовый rootfs ставился с `--no-scripts`. Для пакета нужно штатно сформировать MIME, icon и pixbuf caches и повторить проверку Session. Подготовленный chroot и launcher предназначены для ПК. Готовый к запуску на телефоне пакет пока не выпущен.

## OpenRC, D-Bus и GNOME Session

Alpine поставляет elogind 255.24 и Mutter связан с libelogind. Стандартный GNOME Alpine использует OpenRC, D-Bus, eudev, PipeWire и GDM. Для v8b кандидат состоит из отдельной пользовательской сессии с RAM HOME и XDG_RUNTIME_DIR, системной и сессионной D-Bus, Alpine elogind/polkit по необходимости и PipeWire. WirePlumber доступен как 0.5.15. GDM в офлайн-прогоне предоставил typelib, его демон не запускался. Прямой запуск Shell полезен для проверки Mutter, а дальнейший тест должен поднять SessionManager, Settings Daemon и проверить авторизацию пользователя без изменения штатного OpenRC. [GNOME на Alpine](https://wiki.alpinelinux.org/wiki/GNOME), [elogind на Alpine](https://wiki.alpinelinux.org/wiki/Elogind)

## FD610 и аппаратный допуск

В Mutter 50.2 native headless перечисляет DRM render nodes через udev и устанавливает флаг `META_KMS_FLAG_NO_MODE_SETTING`. GBM-путь проверяет аппаратное ускорение. Это совместимо по архитектуре с GPU-only DRM на lemon, но офлайн не доказано, что udev в v8b обнаружит `renderD128` и Mutter выберет его. Mutter способен перейти в surfaceless-режим без GPU. Требуется fail-closed проверка рендерера и файловых дескрипторов, прежде чем подключать RDP. `WLR_RENDER_DRM_DEVICE` относится к wlroots, поэтому конфигурация Labwc здесь не переносится. [Mutter native backend 50.2](https://github.com/GNOME/mutter/blob/50.2/src/backends/native/meta-backend-native.c)

Перед первым аппаратным запуском проверить v8b, закреплённый SSH host key и COM4, свободную RAM, renderD128, блокировку MDSS, отсутствие DISPCC/DSI и mounts/swap. Затем с отдельного разрешения стартовать только headless Shell в ограниченном сеансе. Успех требует активного FD610, виртуального монитора и отсутствия GPU/IOMMU faults. После этого отдельно проверить PipeWire/RDP, Activities, Settings, Console и клавиатуру с Windows. Stage C/B остаётся NO-GO.

### Протокол первого аппаратного теста

1. Допуск после пересборки Mutter и воспроизводимого теста, который отвергает запуск при скрытом render node. Проверить SHA-256 готового образа, SSH, COM4, 2 GiB MemAvailable, v8b, штатный MSM, существующий renderD128, hold MDSS, отсутствие DSI, DISPCC и подсветки. Снять UFS-счётчики и dmesg. 
2. Передать образ в tmpfs, сверить хеш и смонтировать его read-only внутри отдельной mount namespace. Создать временные HOME и runtime в RAM. Пробросить только необходимые виртуальные файловые системы и GPU render node. Оставить DRM primary nodes, физические input devices и UFS за пределами окружения. 
3. Запустить один headless Shell/Mutter на 480×720 до 60 секунд с `LEMON_REQUIRE_RENDER_NODE=/dev/dri/renderD128`. Проверить FD610, аппаратный EGL и открытый render node, отсутствие llvmpipe/softpipe и GPU/IOMMU faults. Собрать интервальный PSS и минимум MemAvailable. Прервать при ошибках GPU, снижении запаса памяти ниже 512 MiB, изменении дисплейного тракта или потере связи.
4. Завершить процесс, размонтировать только тестовый образ, удалить тестовые файлы из RAM и сверить COM4, SSH, состояние питания GPU и UFS-счётчики. После подтверждения графического этапа проверять 720×1280 и RDP с вводом в отдельном испытании.

## RDP через SSH

В пакетном ARM64 бинарнике проверены `gnome-remote-desktop-daemon --headless` и команды `grdctl --headless` для настройки TLS, учётных данных и порта. Режим single-user работает с уже существующей headless-сессией, использует PipeWire и API Mutter. Upstream описывает запуск через systemd user unit. Здесь кандидат для OpenRC — ручной запуск демона в той же сессионной D-Bus и XDG_RUNTIME_DIR. Отдельно надо проверить старт, ввод и TLS. `CONFIG_FUSE_FS` отсутствует в v8b, поэтому не рассчитываем на файловый clipboard FUSE. Основной RDP-путь остаётся непроверенным. [GNOME Remote Desktop 50.1](https://github.com/GNOME/gnome-remote-desktop/blob/50.1/README.md)

Upstream bind использует `g_socket_listener_add_inet_port`. Запуск на основной сети телефона открыл бы RDP на доступных интерфейсах. План — выделенная network namespace с единственным loopback, без veth и маршрутов. v8b имеет CONFIG_NET_NS. После проверки изоляции положить PID supervisor в закрытый каталог, `rdp-stream.sh` подключит SSH stdin/stdout к loopback этой namespace. Проектный мост Windows поддерживает один локальный RDP-клиент с сохранением строгой проверки SSH host key. Путь требует отдельного офлайн-прогона и ещё не развёрнут на телефоне. [Код привязки сокета GRD](https://github.com/GNOME/gnome-remote-desktop/blob/50.1/src/grd-utils.c)

```powershell
python .\userspace\labwc-v8b\vnc-ssh.py --gnome-rdp --identity "C:\path\to\key" --known-hosts "C:\path\to\verified_known_hosts"
mstsc.exe /v:127.0.0.1:13389
```

Для теста использовать временный пароль RDP, вводимый через stdin, и сертификат, сверенный вне RDP. Все настройки и ключи теста хранятся в RAM. Удалить тестовые процессы, namespace и каталог после проверки, затем сверить dmesg, питание GPU, UFS, SSH и COM4.

Журналы находятся в `logs/v8b-gnome50-offline/`. Ключевые файлы — `stage.txt`, `add-gdm-polkit.txt`, `smoke-private-bus.txt` и `grd-help.txt`.
