# Один тест v6 — только после отдельного разрешения

Сейчас работает v5. Не перезагружать и не писать boot до отдельного согласования.
Предлагаемый объём: вход в TWRP, одна запись только boot, один normal boot v6,
чтение логов и при неуспехе восстановление v5. Host IPv4 настройка выполняется
вручную отдельным флагом PowerShell-скрипта, а не во время подготовки проекта.

Образ v6: 23670784 байта,
`1eade4d8208905703286d01883e76b71728cc36b301f28563b58a0e53d4c8d63`.
Рабочий v5: 23609344 байта,
`ad15b45a3d60217711333fe1e07a30ede1e8b66d0195fcc3ecc00dda81586195`.
Оба доступны в artifacts, v5 также в snapshots/v5-known-good/artifacts.

## 1. Согласованный переход в отдельный TWRP

Проверить заряд, кабель, наличие обоих образов и V6_RECOVERY.md. Закрыть COM-клиент.
Аппаратно войти Power/Volume Up в TWRP. При невозможности входа остановиться.
Не использовать fastboot boot как путь спасения: в исследованном ABL нет обработчика.

PowerShell из C:\Users\HadirPC\Downloads\platform-tools_r37.0.1-windows:

```powershell
.\platform-tools\adb.exe devices -l
.\platform-tools\adb.exe shell id
.\platform-tools\adb.exe shell uname -r
.\platform-tools\adb.exe shell readlink -f /dev/block/bootdevice/by-name/boot
.\platform-tools\adb.exe shell readlink -f /dev/block/bootdevice/by-name/recovery
.\platform-tools\adb.exe shell blockdev --getsize64 /dev/block/bootdevice/by-name/boot
.\platform-tools\adb.exe shell blockdev --getsize64 /dev/block/bootdevice/by-name/recovery
.\platform-tools\adb.exe shell sha256sum /dev/block/bootdevice/by-name/recovery
.\platform-tools\adb.exe shell 'head -c 23609344 /dev/block/bootdevice/by-name/boot | sha256sum'
```

Нужны root TWRP4.19.252, boot=sde49 и recovery=sda9, по134217728 байт;
prefix boot SHA равен v5 выше. Recovery SHA:
1737005c5d9452d3238fcd0a2430956e7232937b35e9df427edc114f0dacd2eb.
Пути ранее проверены; заново подтвердить. При несовпадении не писать.
До следующего reboot сохранить существующий pstore по V6_RECOVERY.md.

## 2. Только boot, в пределах разрешения

```powershell
Get-FileHash .\Redmi9T-Native-Linux\artifacts\boot-linux-test-v6.img -Algorithm SHA256
Get-FileHash .\Redmi9T-Native-Linux\artifacts\boot-linux-test-v5.img -Algorithm SHA256
.\platform-tools\adb.exe push .\Redmi9T-Native-Linux\artifacts\boot-linux-test-v6.img /tmp/boot-linux-test-v6.img
.\platform-tools\adb.exe shell wc -c /tmp/boot-linux-test-v6.img
.\platform-tools\adb.exe shell sha256sum /tmp/boot-linux-test-v6.img
```

Сверить точные размер/SHA. Затем, только после согласования:

```powershell
.\platform-tools\adb.exe shell 'dd if=/tmp/boot-linux-test-v6.img of=/dev/block/bootdevice/by-name/boot bs=4194304 conv=fsync'
.\platform-tools\adb.exe shell 'head -c 23670784 /dev/block/bootdevice/by-name/boot | sha256sum'
.\platform-tools\adb.exe shell sha256sum /dev/block/bootdevice/by-name/recovery
```

Exit code каждого шага должен быть0, prefix SHA=v6, recovery прежний.
Полный hash 128MiB boot не равен hash короткого образа. При ошибке не reboot.
Не писать другие разделы, не делать erase/wipe/AVB обходы и не менять GPT.
После успешного readback допустим один согласованный `adb.exe reboot`.
Если BCB вернул TWRP, сохранить обстоятельства и не менять misc автоматически.

## 3. Сначала ACM, затем сеть

Подождать до60 секунд и найти **фактический COM-номер**. Сначала подтвердить shell,
V6 markers, шесть LUN, отсутствие disk mounts и swap. Uname намеренно остаётся -v5.
Собрать collect-v6.py с правильным --port, закрыв другие serial-программы.
Он читает и сохраняет данные, сам не делает reboot/flash или IP changes.

Затем по V6_USB_SSH.md прочитать host fingerprint через COM, настроить только
целевой Windows NCM IPv4 и проверить pinned-key SSH. Не отключать ACM и не
перепривязывать UDC при сетевой ошибке. Отсутствие NCM при работающем ACM —
диагностируемый частичный результат, а не повод повторять прошивку.

Успех — одновременные ACM и SSH, V6 init/OpenRC markers, Alpine/apk, UFS и
нулевые block write counters/пустой swap/отсутствие UFS mounts. Подтверждение
только ядра или NIC недостаточно. При сетевой ошибке сохранить COM-логи и остаться
в текущем состоянии до разбора. При panic/отсутствии USB вернуться в TWRP и
восстановить v5 в рамках разрешения. Автоматического отката или повторной прошивки нет.

## Текущий протокол Windows и RAM SCP

Для нового финального образа с SFTP использовать V6_HARDWARE_PREPARATION.md и Test-LemonHardwareV6.ps1. Разрешение на полный тест должно включать USB-only IPv4 Windows и1024-byte SCP в проверенный /tmp tmpfs с последующим удалением. Единственные разрешаемые записи UFS — boot для одного теста и boot при согласованном возврате v5; другие разделы не затрагиваются. Предыдущий v6 сохранён в snapshots/v6-before-scp.
