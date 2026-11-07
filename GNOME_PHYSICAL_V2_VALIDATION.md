# GNOME Physical LCD v2 — валидация

Этот документ описывает офлайн-подготовку. После неё выполнен один разрешённый аппаратный тест C: [отдельный отчёт](GNOME_PHYSICAL_V2_HARDWARE_RESULTS.md). Пакет, испытанный на телефоне, сохранён с первоначальным SHA-256; новые результаты хранятся отдельно.

Все новые графические проверки выполнены **на ПК**, ARM64 программы — через QEMU user, VT/watchdog — через QEMU system с Image v8b. Software renderer в PC-тестах включён явно. Новые физические тесты не выполнялись.

| Проверка | Результат и лог |
|---|---|
| Контрольная копия v1 | 77 файлов; повторная сверка всех размеров/SHA при упаковке; `checkpoint-verification.json` |
| ARM64 build | static watchdog, vt-cleanup, drm-probe; musl frame-trace.so и dbus-trace.so; `build.txt`, `build-sha256.txt` |
| VT EBUSY | Старый close→disallocate воспроизводит EBUSY; новый алгоритм ждёт, отказывает живому владельцу, возвращает tty1 из ownerless graphics VT и проходит повторный cleanup; `vt-v8b-vm.txt` |
| Watchdog | Graceful deadline, внешний TERM, hard deadline и уничтожение stubborn descendants, изоляция mounts; тот же VM log |
| ABI instrumentation | 12 integer + 12 double, регистры и stack varargs, `trace-abi.txt` |
| C, GNOME/RDP/окна | `offline-C-session/`, 120 с PC watchdog, Shell component зарегистрирован, GNOME/Console/Settings и ввод; нет прежнего 90-секундного registration failure |
| C, итоговый Stop | `offline-C-release/`, запрос Stop на 60 с PC теста: USER_STOP для GRD, session, WP, PW; Weston/system bus завершены; namespace cleanup PASS |
| B без RDP | `offline-B-headless-final/`: официальный Devkit, PipeWire streaming, screen damage, настоящий кадр GNOME и приложения поверх Weston headless; cleanup PASS |
| Touch mapping | Синтетические края/offset и отказы недопустимых координат; `touch-map.txt`; аппаратный ввод НЕ проверен |
| Windows | Parse AST обоих PS1 без запуска графики; Python compile; mode A отказывает до SSH |
| Живой check-only | USB PnP/MAC и IP, COM4 exclusive open без команд, strict SSH pin и v8b/DRM isolation; `windows-preflight.txt`; графика не запускалась |
| Телефон | Только чтение по SSH: v8b, tty1, GPU suspended, USB, шесть LUN, нулевые writes/discards/flushes; `read-only.txt`, `final-readonly.txt` |

## Известные ограничения

- При остановке C после исчезновения GRD virtual monitor остаются Mutter warnings о logical monitor и timeout отдельного session client. В итоговом тесте они не оставили процессов/mounts и не сорвали Stop. Это userspace shutdown warnings, не утверждение о GPU/IOMMU fault на телефоне.
- В B headless parent не имеет физического input seat; GTK предупреждает `GDK_IS_SEAT`. Несмотря на это, после исправления GNOME Session lifecycle получены реальные кадры. Физический touch и input forwarding B требуют отдельной проверки.
- В PC/QEMU namespace supervisor собран нативно для WSL: QEMU user не поддерживает clone namespace flags. ARM64 версию watchdog отдельно проверяет QEMU system с тем же BusyBox и Image v8b. Таким образом ограничение QEMU user не выдано за свойство телефона.
- Оптимизация `quiet` и отключение постоянных PNG не имеют пока измеренного аппаратного выигрыша. FPS GNOME/FD610, RDP encode/decode и input-to-photon на LCD не измерены.
- Renderer guard и исходный Mutter бинарник сохранены. Путь A не запущен; fake software fallback, fake KMS device и dummy regulator не используются.
- После выключения/перезагрузки RAM-cache и ключи исчезают; новая загрузка требует COM-проверки host key и, при отсутствии GPU, отдельного разрешения на его восстановление. Launcher не загружает MSM.

Подробности запуска, остановки и следующего согласуемого теста: [GNOME_PHYSICAL_LCD_V2.md](GNOME_PHYSICAL_LCD_V2.md).
