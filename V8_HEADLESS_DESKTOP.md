# v8b — Headless Desktop Prototype

## Сборка и результат

[ARM64 RAM-only архив](artifacts/lemon-desktop-v8b-aarch64.tar.gz) содержит Weston 14.0.2, Mesa 26.1.6 с Freedreno, Wayland, desktop shell, ресурсы и собственный клиент Lemon Desktop. Размер 121 840 791 байт, SHA-256 `ab14a15aea7fb007fb54f19f5956e6b3dfb8a8899b4021801ab1a2c9e3ac3326`. Распакованные обычные файлы занимают 349 708 821 байт. В архиве нет boot image, модулей ядра или SSH ключей. [Проверка архива](logs/v8b-desktop-offline/archive-validation.txt).

[Клиент](userspace/desktop-v8b/desktop.c) — C/Cairo, Wayland xdg-shell и два wl_shm буфера, 360×800. Он рисует текст и элементы управления в CPU-буфер, меняет тему и курсор, принимает ASCII и Backspace, читает release, CPU, MemAvailable, NCM carrier и слушающий порт SSH. Индикатор FD610 зависит от подтверждения рендерера Weston в launcher. Короткая анимация запускается по нажатию. Клавиши и координаты адресуются только этому приложению через приватный Unix datagram socket. Системного ввода и touch нет.

[Launcher](userspace/desktop-v8b/desktop.sh) передаёт библиотечные пути, GBM/DRI backend, fonts, XKB и модули Weston через окружение процесса. Это сохраняет доступ Mesa к реальному sysfs без chroot на телефоне. `start gl` требует v8b, RAM /tmp, пустой swap, действующий renderD128 Adreno, separate_gpu_kms=1 и уже установленную блокировку MDSS. Проверяются отсутствие DISPCC, DSI devices и подсветки, затем идентичность FD610 и открытый Weston render FD. При отказе launcher завершается. Явный `start pixman` предназначен для отдельной software-проверки. Код загрузки модулей отсутствует.

`capture` вызывает штатный Weston 14 screenshooter и возвращает PNG с виртуального output. PNG никогда не формируется в приложении. При неизменном счётчике коммитов возвращается последний захваченный PNG без нового readback. Debug capture доступен только через Wayland socket в приватном каталоге 0700. Никакой Wayland или HTTP порт на телефоне не слушает. [Weston headless](https://wayland.pages.freedesktop.org/weston/toc/running-weston.html).

[Windows viewer](userspace/desktop-v8b/viewer.py) запускается на 127.0.0.1, проверяет локальный token, Host и Origin, отправляет фиксированные команды через SSH со строгой проверкой host key. Мышь отображается в приложении и передаётся по желанию, click переключает элементы, клавиатура редактирует app-only поле. По умолчанию кадры запрашиваются вручную или после действия. Опционально до 1 FPS, с кэшем и ограничением входящих событий. На телефон ничего не публикуется.

## Офлайн-проверки

- Архив заново распакован в ARM64 chroot на ПК. Weston/Pixman запущен, Wayland-клиент виден на двух реальных кадрах 360×800. Клик сменил тему, клавиша A появилась в поле, маркер указателя переместился. Неверная координата отклонена, stop закрыл сессию и удалил приватный runtime. Повторный idle capture вернул тот же PNG.
- Windows loopback HTTP тест использовал захваченный PNG и подставной SSH-адаптер. Проверены выдача PNG, частотный кэш, click/key, запрет команд без token и с посторонним Origin, отклонение invalid input и ограничение частоты. Живой SSH в этом испытании не вызывался.
- GL запуск на ПК остановился на проверке среды. В новом пакете GPU-режим на телефоне ещё не проверен. Аппаратное доказательство FD610 относится к предшествующему тесту Weston 14.0.2. [Аппаратный эталон](V8_HEADLESS_GPU_RESULTS.md).
- Готовая v8b сохранила прежний SHA-256. Телефон в этом сеансе не подключался к тестовым программам.

[Журнал прогона](logs/v8b-desktop-offline/test.txt) · [Журнал Windows viewer](logs/v8b-desktop-offline/viewer-test.txt) · [Кадр после ввода](logs/v8b-desktop-offline/after-input.png).

## Ресурсы

На ПК с WSL/QEMU-user и Pixman измерено 231 мс на один вызов capture с запуском клиента захвата, без SSH. Два PNG занимают 32 737 и 30 884 байта. При постоянном обновлении 1 FPS это около 31–33 кБ/с полезной нагрузки плюс SSH. Размер двух клиентских буферов 2 304 000 байт. RSS процессов Weston и клиента в WSL около 25,6 и 22,5 МиБ соответственно. Общий RSS нельзя суммировать как точное потребление из-за общих страниц. GPU, CPU, задержка USB и фактическая RAM на телефоне для нового desktop не измерялись. Клиент перерисовывается по событиям и раз в минуту для часов/статуса, анимация ограничена шестью шагами.

## Воспроизведение на ПК

Из корня проекта, в WSL Ubuntu-24.04 с QEMU ARM64 и существующим headless staging, выполнить с root `bash userspace/desktop-v8b/setup-build.sh`, затем `bash userspace/desktop-v8b/build.sh` и `bash userspace/desktop-v8b/test-offline.sh`. Запустить `python userspace/desktop-v8b/test-viewer.py` на Windows. Точный архив закреплён SHA, повторная загрузка Alpine build-пакетов зависит от состояния репозитория.

## Отдельное короткое аппаратное испытание и возврат

1. Только после согласования проверить SSH с pin, COM4 и NCM, baseline dmesg, UFS counters, RAM /tmp и отсутствие swap. Если renderD128 отсутствует или MDSS уже привязан, остановиться. Этот тест не даёт разрешения на загрузку MSM или unbind. Проверить минимум 600 МиБ свободных в /tmp и доступную RAM.
2. Создать приватный новый каталог `/tmp/lemon-desktop-v8b`, передать архив по SFTP туда, сверить SHA и распаковать в этот каталог. Не распаковывать поверх системы.
3. В одном SSH-окне запустить `/bin/busybox timeout -s TERM -k 3 45 /bin/sh /tmp/lemon-desktop-v8b/runtime/desktop.sh start gl`. В Windows открыть `python userspace/desktop-v8b/viewer.py --identity <локальный-ключ> --known-hosts <сверенный-по-COM4-файл>`. Проверить FD610 и renderD128 в журнале. Захватить кадр, нажать Theme, ввести один символ, захватить второй кадр. При отказе GL или новом аппаратном fault закончить прогон без смены backend.
4. Команда `/bin/sh /tmp/lemon-desktop-v8b/runtime/desktop.sh stop` завершает приложение и Weston. Закрыть Windows viewer, скачать журналы, проверить отсутствие тестовых процессов и удалить только каталог данного запуска. Сверить COM4, SSH, display bindings, dmesg и UFS counters до/после. v8b, модули и guard остаются в исходном состоянии. Прошивка и откат через TWRP этому испытанию не нужны. Stage C/B **NO-GO**.

## Аппаратный результат 6 ноября 2026

**PASS.** Windows USB NCM восстановлен на 192.168.77.1/30 только по проверенному PnP/MAC. Host key текущего запуска сверён через COM4. После подтверждения отсутствия привязки MDSS установлен guard, штатный MSM загружен один раз с `separate_gpu_kms=1`. DISPCC не загружался.

Проверенный архив передан в tmpfs по SFTP. Один запуск с лимитом 45 секунд занял около 5 секунд по журналу Weston. Weston подтвердил EGL Mesa Project, GL FD610 и renderD128. Windows loopback viewer через реальный SSH получил два PNG 360×800 и передал клики, клавишу A и координаты указателя. На итоговом кадре подтверждены светлая тема, A и маркер указателя. [Кадр](logs/v8-desktop-hardware/after-input.png) · [Viewer/SSH](logs/v8-desktop-hardware/run.txt) · [Weston](logs/v8-desktop-hardware/weston.log).

Штатная остановка и удаление RAM-каталога прошли. Weston при TERM повторил предупреждение о layer с views. SSH, COM4 и NCM сохранились, GPU вернулся в runtime suspend. Новых GPU/IOMMU faults нет, UFS counters и mounts не изменились, swap отсутствует. MDSS остался заблокирован, DSI/PHY не появились. Телефон оставлен на v8b с загруженным MSM. Stage C/B **NO-GO**. [Сравнение](logs/v8-desktop-hardware/comparison.txt).
