# Актуально: GNOME Physical LCD v2.1 проверена на LCD

2026-11-07: после отдельно разрешённого GPU restore проведён один C-сеанс с watchdog60s. Владелец подтвердил GNOME/Console/Activities и возврат tty1. FD610 подтверждён Mutter, exit0, VT2 освобождена без EBUSY, rootfs RAM удалена, GPU suspended, SSH/NCM/COM4 доступны, все UFS stat неизменны. PSS886.91MiB против891.44MiB v2 — один sampled run, не доказательство оптимизации.

Старые lifecycle/TLS/fd0/WindowPreview ошибки не повторились, но появился GJS GC-critical ShellWindowTracker::notify при выходе. Следующая работа — офлайн-анализ этого дефекта; без нового аппаратного запуска. Проверенная v2 сохранена. Полный отчёт: GNOME_PHYSICAL_V21_HARDWARE_RESULTS.md. Stage C/B NO-GO сохраняется.

---

# Продолжение с GNOME Physical LCD v2.1

Сначала прочитать `GNOME_PHYSICAL_LCD_V21.md`, `GNOME_PHYSICAL_V21_VALIDATION.md`, `GNOME_PHYSICAL_V21_WARNINGS.md`, `GNOME_PHYSICAL_V21_MEMORY_PERFORMANCE.md`, `GNOME_PHYSICAL_V21_TOUCH.md`. Актуальный исходник `userspace/gnome-physical-v2.1`, artifacts/logs той же версии. Аппаратно подтверждена v2 C; v2.1 проверена только офлайн. Не повторять порт GNOME и не возвращаться к исследованию питания для уже работающего SimpleDRM вывода.

Проверить `release.json` и `BUNDLE_MANIFEST.json`; baseline v2 находится в `snapshots/gnome-physical-lcd-v2` и `userspace/gnome-physical-v2`. Новые Start/Stop PowerShell имеют явный `-Version v2` для fallback, default v2.1. Это не разрешение на их аппаратный запуск.

До отдельного разрешения — только офлайн/разрешённое чтение. При следующем C-тесте: strict SSH host pin, идентификация USB NIC/COM4, FD610 и MDSS hold, current-mode SimpleDRM, RAM/mounts/swap/UFS baseline; deadline60s; collect/cleanup/VT1/postflight. Если GPU отсутствует, не modprobe; если IP/host key изменились, не обходить проверки. Нет автоматического нового теста, reboot, flash или DSI/LCDB/REFGEN. Измеренный v2 PSS891MiB — общий одновременный peak; QEMU metrics не являются native benchmark.

---

# Возобновление Redmi9T-Native-Linux в новом сеансе

**Последнее фактическое состояние:** прочитать `GNOME_PHYSICAL_V2_HARDWARE_RESULTS.md`. Один аппаратный тест v2 C выполнен успешно: GNOME/FD610/Console на LCD, tty1/VT2 cleanup без EBUSY; пользователь подтвердил. RAM tree удалён, v8b работает, GPU suspended. Разрешение этой попытки использовано. Следующая работа — офлайн устранить GNOME/GRD monitor teardown warnings; B и последующие аппаратные запуски отдельно согласовать.

**Сначала читать GNOME_PHYSICAL_LCD_V2.md и GNOME_PHYSICAL_V2_VALIDATION.md.** Физический GNOME v1 подтверждён пользователем; контрольная копия `snapshots/gnome-physical-lcd-v1`. v2 находится отдельно, проверена офлайн, на телефоне ещё не запускалась. Рабочий путь C сохранён, B/Devkit получил кадры без RDP в ARM64 QEMU, A/native заблокирован. Новый сеанс v2 C/B требует отдельного разрешения. Не повторять исследования питания ради уже работающего SimpleDRM; Stage C/B NO-GO относится к повторной аппаратной инициализации. Touchscreen input device в v8b отсутствует. Скрипты — `scripts/Start-GNOME-Physical.ps1` и `Stop-GNOME-Physical.ps1`; `-CheckOnly` не запускает графику.

Актуальная точка продолжения — [GNOME Desktop](V8_GNOME50_DESKTOP_INTEGRATION.md) и [план физического KMS](V8_GNOME50_PHYSICAL_DISPLAY.md). В последнем сеансе телефон оставлен на v8b после RAM-only теста Desktop, все временные ресурсы очищены. Сначала проверить живые SSH, NCM и COM4 и сверить хеши Desktop и контрольного boot. `scripts/Start-LemonGnomeRdp.ps1` без параметров выполняет проверку NCM/клиента. `-Start` использовать только после нового разрешения на аппаратный запуск. Проект OpenRC service подготовлен, не установлен. Физические gates REFGEN, LCDB, board revision и discharge открыты для исследования, подача питания остаётся NO-GO.

## Справочные шаги

1. Открыть существующий проект `C:\Users\HadirPC\Downloads\platform-tools_r37.0.1-windows\Redmi9T-Native-Linux`. Прочитать [контрольную точку](PROJECT_CHECKPOINT.md), [отчёт Weston GL](V8_HEADLESS_GPU_RESULTS.md) и [таблицу допуска](V8_STAGE_C_SAFETY_REVIEW.md). Любой старт телефона или аппаратный тест выполняется только по новому указанию владельца.
2. Сверить `Get-FileHash artifacts/boot-linux-test-v8b.img` с SHA-256 `9ce181e8a6170ce8773a923f03dd10f5edb405d1990fa09b4f4bc12f2e59a610` и размером 24 707 072 байта. Контрольный образ в `snapshots/v8b-hardware-validated/artifacts`. Исходники, скрипты и конфиги находятся в `bootshim`, `config`, `display-v8`, `scripts`, `userspace` и `pmaports`. Linux исходники и outputs находятся в WSL Ubuntu-24.04, `/home/hadirpc/Redmi9T-Native-Linux`. [Проверка v8b](scripts/validate-stage-b-v8.py).
3. После разрешённого включения сначала проверить release и ACM через единственный клиент COM. COM4 был текущим портом. Через Windows определить NCM по VID/PID/MI и MAC с `./scripts/Restore-LemonV8bUsbIp.ps1`. Только с разрешением на изменение IP использовать `-Apply`, когда адрес отсутствует. Старые ifIndex не использовать.
4. После новой загрузки прочитать только публичный SSH host key из `/run/ssh-hostkey.txt` через COM и заново закрепить его для 192.168.77.2. SSH выполнять с `StrictHostKeyChecking=yes`. Существующий тестовый ключ ПК указан в локальном `logs/v6-authorized/test-client-identity.json`. Приватный ключ на телефоне и в образах отсутствует. [USB и SSH](V8_USB_NETWORK_DIAGNOSIS.md).
5. RAM-процессы, `driver_override` и загруженные модули после выключения теряются. При новой загрузке v8b MSM по умолчанию не загружается. Для будущего отдельно разрешённого GPU-only теста проверить unbound MDSS, отсутствие DSI/PHY и DISPCC, затем применить прежнюю изоляцию MDSS и штатный MSM с `separate_gpu_kms=1`. Сценарий не должен включать DSI, LCDB, REFGEN, подсветку или сенсор. [Успешная процедура](V8_HEADLESS_GPU_RESULTS.md).
6. Для офлайн работы использовать `artifacts/lemon-headless-gpu-v8b-aarch64.tar.gz` и проверенный launcher `logs/v8-headless-gpu/weston-gl.sh`. Учесть пути GBM/DRI и Weston libs. Обычный chroot без sysfs не дал Mesa определить устройство. До следующего разрешения ограничиться упаковкой/офлайн тестами или пассивной подготовкой документации. [Headless](V8_HEADLESS_GRAPHICS.md).
7. Если потребуется восстановление и владелец его отдельно разрешит, использовать аппаратный TWRP и [план возврата v8b](V8_STAGE_C_FIRST_BOOT.md#recovery-после-будущего-испытания). Проверять правильный boot, tmpfs, SHA до записи и readback после. Защищённые разделы сохраняются. TWRP может успеть смонтировать /data и /cache в RW при входе.

Историческая запись — после одной штатной команды poweroff NCM, COM4 и composite исчезли. Полное отключение питания независимо не подтверждалось. [Итог выключения](PROJECT_CHECKPOINT.md#завершение-сеанса).


Для физического дисплея начать с [актуального отчёта](V8_DISPLAY_TOUCH_BRINGUP.md), [плана A–I](V8_DISPLAY_TOUCH_FIRST_LIGHT.md) и [ARM64 сборки](scripts/build-display-touch-review.sh). Рабочий v8b и headless Desktop служат контрольными образами. DT fixture disabled и патчи существуют только для review. Следующий аппаратный шаг требует отдельно согласованной пассивной сверки платы.

Перед обсуждением физического включения проверить [карту](REDMI9T_DISPLAY_HARDWARE_MAP.md) и [окончательный checklist](DISPLAY_FIRST_LIGHT_GO_NO_GO.md). Использовать найденные архивные ID Novatek и учитывать отдельное питание PHY VDD_MX. Следующий возможный аппаратный шаг — отдельно согласованная сверка полностью обесточенной платы.
