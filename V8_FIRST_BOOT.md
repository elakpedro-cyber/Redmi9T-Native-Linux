# v8 — поэтапное испытание

Первое согласование касается только **этапа A**. Образ `artifacts/boot-linux-test-v8.img` содержит отключённый дисплейный тракт. Размер 24 698 880 байт. SHA-256 `563296819c9e22da2ffcc38918b0761ca3d18eed7ae181123796fd6fb1033a29`.

| Этап | Действие и критерий успеха | Когда остановиться |
|---|---|---|
| A. Загрузка и инвентаризация | Одна запись только boot через TWRP с обратной проверкой SHA. Один запуск v8. Проверить маркеры init/OpenRC, COM, NCM, SSH/SFTP, 6 LUN, DT-зависимости и SimpleDRM. Дисплейные platform devices и panel connector отсутствуют. | Неверный hash/раздел, сбой USB, mount UFS, swap, прирост write/discard или I/O errors. |
| B. Host/PHY | Отдельный образ и согласование после A. Статический DT для dispcc/MDSS/DSI/PHY с отключённым DPU и без panel child. Сверить регистрацию host и PHY, ресурсы и отсутствие DCS transfers. Проверить порядок probe и гарантии сохранения SimpleDRM ещё до сборки этого образа. | Deferred probe без разрешимого поставщика, неожиданный KMS handoff, DSI traffic, ошибка clocks/IRQ/PHY или пропажа USB. |
| C. Питание | Офлайн review LCDB, backlight и panel lifecycle. Для аппаратного шага отдельно согласовать измерение rails, reset и порядка отключения. Критерий — воспроизводимая последовательность с контролем общего LCDB и rollback. | Неопределённый PWM/IC, другой voltage selector, VREG_OK timeout, short-circuit, неполный откат. |
| D. Инициализация | После C короткий сеанс с проверенным panel driver. Снять этапы prepare, передачу LP пакетов и выключение. Критерий — полный согласованный проход и сохранение COM/SSH. | Ошибка передачи, unexpected reset, timeout или отсутствие подтверждения безопасного отключения. |
| E. KMS | Проверить отдельный MSM display card, connector, режим 1080×2340@60 и atomic TEST_ONLY. Сначала подготовить переход от SimpleDRM. | Неверный connector/режим, IOMMU fault или потеря rescue. |
| F. Кадр | Один ограниченный atomic commit с тестовым рисунком. Записать vblank и encoder CRC, если доступны. Для зачёта изображения требуется увидеть рисунок на телефоне или получить его через внешнюю камеру. | DSI errors, нет vblank, рисунок отсутствует или наблюдать его невозможно. |
| G. Flips и выключение | Небольшое фиксированное число flips двух буферов с событиями и различимым CRC, затем atomic disable и штатный off. Сверить USB, runtime state и питание. | Flip timeout, underflow, зависание, неожиданное удержание rails. |

Этапы B–G требуют отдельных условий и согласования. Доступ по SSH, connector status, CRC и vblank показывают состояние цифрового тракта. Для вывода о свечении панели нужна внешняя визуальная проверка.

## Этап A

1. Проверить оба образа по SHA. Подготовить физический доступ к Power + Volume Up и исходному TWRP. При недоступности оператора оставить телефон в текущей системе.
2. В TWRP подтвердить root ADB, serial `35a1d5bf0221`, lemon, recovery kernel prefix `4.19.252`, boot `sde49` 128 MiB, отдельный recovery `sda9`. Проверить SHA recovery/dtbo/vbmeta по [исходным копиям](reports/backup-sha256-before.json) и SHA текущего boot-префикса длиной 24 428 544 байта по [отчёту v7](V7_HARDWARE_RESULTS.md).
3. Снять mounts и pstore, отмонтировать /data и /cache, убедиться в отсутствии дисковых mounts и в RAM /tmp. Ранние фоновые записи TWRP при автомонтировании исключить нельзя. Передать v8 в /tmp, сверить SHA и размер, записать только boot один раз. Считать точный префикс 24 698 880 байт обратно, повторно сверить защищённые разделы. При несовпадении остаться в TWRP.
4. Выполнить один normal boot. Использовать `scripts/collect-v8.py --expect v8 --port COM4 --wait 120` после сверки фактического номера COM. Для SSH взять новый публичный ключ сервера из этого COM-лога через `scripts/pin-host-key-v8.py`. Проверить `Test-LemonHardwareV8.ps1` с параметрами `-TestScp`, `-IdentityFile`, `-ExpectedHostFingerprint`, `-HostPublicKeyPath`. Если Windows сбросила адрес, `-ConfigureIPv4` затрагивает только проверенный NCM-адаптер. Доступ к SSH использует прежний клиентский ключ, приватная часть хранится на ПК.
5. Передать `scripts/display-inventory-v8.sh` по stdin в `sh -s` через SSH с `StrictHostKeyChecking=yes` и свежим known_hosts. Сопоставить sysfs и dmesg со списком отключённых узлов из [проверки](V8_VALIDATION.md). Для аварии предусмотрен [откат](V8_RECOVERY.md).
