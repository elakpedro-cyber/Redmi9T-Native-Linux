# Labwc на Redmi 9T v8b

## Пакет

Архив `artifacts/lemon-labwc-v8b-aarch64.tar.gz` собран из пакетов Alpine 3.24 aarch64. Внутри Labwc 0.20.0, wlroots 0.20.2, Mesa 26.1.6, Waybar 0.15.0, foot 1.27.0, wayvnc 0.10.0, приватный D-Bus, шрифты, меню и скрипт сессии. Размер архива 175 374 381 байт, распакованные файлы занимают около 458 MiB. SHA-256:

```
8a81b729bbb55fc245272ba09e9cff015a6a3d3f7133fea77db4a6a021942884
```

Исходники и конфигурация лежат в `userspace/labwc-v8b/`. Скрипты `setup.sh` и `package.sh` готовят пакет на ПК, `test-offline.sh` и `test-rfb.py` проверяют его. Сессия стартует через `runtime/session.sh`.

## Офлайн-проверки

В WSL с ARM64 QEMU проверены распакованные бинарники, виртуальный экран 480×720, панель с часами, два окна foot, выполнение команды с VNC-клавиатуры, меню приложений, перетаскивание и изменение размеров мышью, переключение окон. Журнал Labwc подтвердил действия Move, Resize и NextWindow. Кадры получены через wayvnc по RFB и локальному stdio-ретранслятору. PNG закодированы на ПК из этих кадров. Журналы и снимки находятся в `logs/v8b-labwc-offline/`. Офлайн-сессия явно использовала Pixman.

Первый локальный кадр получен за 115 мс, следующие за 10–17 мс. Эти числа относятся к WSL без USB. Полный кадр RGBA 480×720 занимает 1,38 МБ. Верхняя оценка при 10 полных несжатых кадрах в секунду составляет 13,8 МБ/с до накладных расходов протокола. wayvnc ограничен 10 кадрами/с. Клиент может использовать сжатие и обновление изменившихся областей. Отдельные RSS в QEMU составляли примерно 97 MiB для Labwc, 98 MiB для Waybar, 57 MiB для wayvnc и 29–32 MiB на окно foot. Значения включают общие страницы. RAM, FPS и задержку на телефоне предстоит измерить.

## Путь FD610

Аппаратный режим использует `WLR_BACKENDS=headless`, `WLR_RENDERER=gles2` и `WLR_RENDER_DRM_DEVICE=/dev/dri/renderD128`. wlroots 0.20.2 открывает указанный render node и требует поддержку EGL DMA-BUF import для GLES2. Успешный аппаратный Weston на v8b уже подтвердил FD610 и EGL DMA-BUF для своего стека. Совместимость Labwc с новым комплектом Mesa должна быть подтверждена на телефоне. Скрипт требует строку GL renderer FD610, открытый дескриптор renderD128 и отсутствие открытого DRM primary node у Labwc. Программный GL завершает запуск ошибкой. Pixman доступен в отдельном режиме офлайн-проверки. [wlroots renderer](https://gitlab.freedesktop.org/wlroots/wlroots/-/blob/0.20.2/render/wlr_renderer.c), [wlroots EGL](https://gitlab.freedesktop.org/wlroots/wlroots/-/blob/0.20.2/render/egl.c), [wlroots GLES2](https://gitlab.freedesktop.org/wlroots/wlroots/-/blob/0.20.2/render/gles2/renderer.c)

## Windows

wayvnc принимает соединение через Unix-сокет в каталоге с правами 0700. У штатного Dropbear v8b отключён проброс портов, поэтому мост передаёт RFB через SSH stdin/stdout. На Windows он принимает одного клиента на loopback. Используй локальный SSH-ключ и known_hosts, сверенный с ключом текущей загрузки через COM4. [wayvnc FAQ](https://github.com/any1/wayvnc/blob/master/FAQ.md)

```powershell
python .\userspace\labwc-v8b\vnc-ssh.py --identity "C:\path\to\key" --known-hosts "C:\path\to\verified_known_hosts"
```

Адрес для TigerVNC — `127.0.0.1::5905`. Super+Return открывает foot, Super+Space открывает меню, Super+перетаскивание правой кнопкой меняет размер окна, Alt+Tab переключает окна. Терминал работает с правами текущей SSH-сессии root.

## Одно аппаратное испытание после разрешения

1. Снять исходные dmesg, UFS-счётчики, mounts и swap, проверить COM4, SSH с закреплённым ключом, MSM и раздельный GPU/KMS, блокировку привязки MDSS и отсутствие активных DSI и подсветки. Проверить свободные 800 MiB в `/tmp` и запас доступной RAM.
2. Проверить `/dev/shm`. POSIX shared memory нужна wlroots для раскладки клавиатуры. Если каталога нет, создать его с режимом 0700 только в уже смонтированном RAM-backed devtmpfs и проверить тип файловой системы. При несовпадении остановиться. [wlroots shared memory](https://gitlab.freedesktop.org/wlroots/wlroots/-/blob/0.20.2/util/shm.c)
3. Передать архив по SFTP в новый приватный каталог `/tmp/lemon-labwc-v8b`, сверить SHA-256, распаковать в этот каталог. Запустить один сеанс на 90 секунд.

```sh
/bin/busybox timeout -s TERM -k 5 90 /bin/sh /tmp/lemon-labwc-v8b/runtime/session.sh start gles2
```

4. С Windows получить кадр, открыть два окна, проверить мышь, клавиатуру и терминал. Сохранить EGL/GL renderer, дескрипторы DRM, время первого кадра и RSS. При проблеме GL сохранить журналы и завершить тест.
5. Завершить сессию через меню Close desktop или таймаут. Убедиться, что процессы теста остановлены, скачать логи и удалить выделенный каталог в `/tmp`. Если на шаге 2 был создан `/dev/shm`, удалить его через `rmdir`, когда он пуст. Сравнить доступность SSH/COM4, UFS-счётчики, mounts и swap, GPU runtime PM, dmesg и состояние дисплейного тракта с исходным снимком. Эта очистка восстанавливает исходное состояние v8b.

Stage C/B остаётся NO-GO. В этой подготовке использовался только ПК.

## После Labwc

После успешного теста собрать отдельный RAM-пакет Qt/KWin/Plasma Mobile. Сначала проверить вложенный сеанс KWin под Labwc на ПК, включая EGL, ввод и расход памяти. Для Windows оставить проверенный захват внешнего сеанса Labwc через wayvnc, пока отдельный путь захвата KWin не подтверждён. На телефоне проверить вложенный сеанс отдельным испытанием.
