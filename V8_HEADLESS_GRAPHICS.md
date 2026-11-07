# Headless Wayland и Freedreno для v8b

Архив [lemon-headless-v8b-aarch64.tar.gz](artifacts/lemon-headless-v8b-aarch64.tar.gz) содержит изолированный Alpine ARM64 runtime. В нём Weston 14.0.2, Wayland 1.25.0, Mesa 26.1.6, `weston-simple-shm`, `weston-screenshooter`, скрипт запуска и ранее проверенный `gpu-render-v7`. Размер 116 580 073 байта, SHA-256 `e0a95b172aab151c991ece0f8561a86614def458d8405cf0295b60113502ba5c`. В архиве отсутствуют ключи устройства, boot, kernel modules и настройки SSH. Runtime распаковывается отдельно от системы. [Weston](https://wayland.pages.freedesktop.org/weston/toc/running-weston.html) · [Проверка архива](logs/v8-blocker-resolution/headless-bundle-test.txt).

На ПК из повторно распакованного архива в ARM64 chroot запустились headless backend и клиент. Screenshooter сохранил PNG 320×240 с видимым кадром клиента. Weston использовал Pixman. Загрузчик разрешил зависимости отдельного GPU probe, который штатно отказался без render node. [PNG](logs/v8-blocker-resolution/lemon-headless.png) · [Журнал Weston](logs/v8-blocker-resolution/weston-test.log).

## Будущий тест телефона

Только после согласования. Подтвердить v8b, COM4, pinned SSH, отсутствие дисковых mounts, swap и достаточную свободную RAM. На ПК и после SFTP в приватный каталог под RAM `/tmp` сверить SHA. Распаковать туда же и запускать внутри этого runtime, не накладывая файлы на `/`. Создать необходимые null/random/urandom nodes в RAM chroot, затем выполнить `timeout 18 chroot <runtime> /bin/sh /run-wayland.sh`. Скрипт запускает Weston с приватным socket и debug extension только для screenshot, затем завершает клиент и Weston. Забрать PNG и журнал по SFTP и сверить SHA PNG.

Отдельный ограниченный GPU-прогон допускается только при уже доступном Adreno render node. Проверить привязку по sysfs, передать в RAM chroot только этот character device с подтверждёнными major/minor, без card nodes, и один раз запустить `gpu-render-v7` с таймаутом. Критерии — DRM MSM, GLES renderer `FD610`, 256 проверенных пикселей и эталон SHA `ebec48648edef1e298a2e12473d1c837bfc6ce99151088606b4cda794434b9cb`. `llvmpipe` и `softpipe` считаются отказом GPU-прогона. После каждого теста проверить SSH, COM и отсутствие GPU/IOMMU faults, удалить только собственный RAM-каталог. При отсутствии нужного render node завершить GPU-часть без подгрузки модуля.

PNG Weston подтверждает Wayland и compositor readback. Тест FD610 подтверждает отдельный рендеринг в RAM. Ускорение самого Weston и физический KMS/DSI этим сценарием не проверяются. Новый графический тест на телефоне ещё не запускался.

Финальная проверка по COM4 подтвердила работающую v8b. SSH при этой проверке завершился по таймауту, а адрес ПК 192.168.77.1 не был обнаружен. Настройки сети не менялись. Перед headless-тестом доступ по NCM/SSH нужно подтвердить заново. [COM4](logs/v8-blocker-resolution/device-com4.txt).

## Архив для отдельного GPU-испытания

[lemon-headless-gpu-v8b-aarch64.tar.gz](artifacts/lemon-headless-gpu-v8b-aarch64.tar.gz), 116 573 498 байт. SHA-256 `724868f97a2e541c0f23e8f16c265651617ea0f4a18fcdb4f9bb6d9c415eb2ad`.

| Сценарий | Статус |
|---|---|
| `/run-wayland.sh pixman` | Проверен на ПК из распакованного архива. PNG 320×240. |
| `/run-freedreno.sh` | Использует только renderD128, проверяет DRM MSM, Adreno 610, 256 пикселей и SHA. Офлайн отказ при отсутствии узла подтверждён; текущий телефон пока не тестировался. |
| `/run-wayland.sh gl` | Weston 14 headless запрашивает Mesa surfaceless EGL. Mesa 26.1.6 умеет выбирать DRM render node, затем может перейти на программный fallback. Скрипт требует hardware renderer в логе Weston до запуска клиента и захвата PNG. Принудительный llvmpipe на ПК был отклонён. Поддержка на физическом Adreno в изолированном runtime ещё не подтверждена. |

После отдельного разрешения запускать режимы по одному и с таймаутом из приватного RAM-каталога. Путь к renderD128 и major/minor сверить с Adreno в sysfs. Выдать только существующий render node, без primary card, DRM backend и input devices. Проверить фактический GL renderer и PNG отдельно. Если изоляция не даёт Mesa обнаружить устройство, остановить проверку Weston GL; самостоятельный GBM/FD610 shader остаётся независимым тестом. Не добавлять mounts или переключения драйверов в ходе проверки. Изображение и логи забирать через SFTP из `/tmp`. [Тест распакованного архива](logs/v8b-usb-recovery/headless-gpu-test.txt) · [Weston 14](https://gitlab.freedesktop.org/wayland/weston/-/blob/14.0.2/libweston/backend-headless/headless.c) · [Mesa 26.1.6](https://gitlab.freedesktop.org/mesa/mesa/-/blob/mesa-26.1.6/src/egl/drivers/dri2/platform_surfaceless.c).
