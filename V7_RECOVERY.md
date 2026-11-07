# Восстановление v6 после согласованного испытания v7

Сейчас восстановление не требуется: телефон остался в v6.
Этот план не разрешает запись сам по себе. Запись recovery/dtbo/vbmeta/super,
wipe, GPT changes, fastboot erase и unlock не входят в процедуру.

## Контрольный образ

`artifacts/boot-linux-test-v6.img` и отдельная копия
`snapshots/v6-hardware-validated/artifacts/boot-linux-test-v6.img`:

- 23670784 байта.
- SHA256 `1eade4d8208905703286d01883e76b71728cc36b301f28563b58a0e53d4c8d63`.
- Snapshot MANIFEST проверяется офлайн; v6 файлы и сохранённые Android backups
  этой работой не изменены.

## Сначала логи

Если доступен COM — collect-v7.py; если доступен SSH — dmesg, mounts, swaps,
блоковые counters, /run/boot-dmesg.txt, /run/dropbear.log, /run/usb-setup.log,
/run/lemon-diagnostics.log, /run/ssh-hostkey.txt. Сохранять на ПК.
При полном зависании — только в разрешённом восстановлении Power reset,
Power+Volume Up в отдельный TWRP. Не запускать recovery install/wipe.

Root TWRP должен быть 4.19.252, device=lemon, serial=35a1d5bf0221.
Проверить by-name boot=sde49, recovery=sda9; размер обоих 134217728.
Проверить mounts: TWRP способен автоматически монтировать /data,/cache RW.
Отключить disk mounts перед записью; нельзя задним числом гарантировать отсутствие
ранних фоновых записей самого recovery. /tmp должен быть RAM filesystem.

Снять pstore и TWRP dmesg на ПК. Pstore может быть пустым; не удалять записи,
не путать старые init markers со следами последнего теста.

## Восстановить только boot

Команды из каталога platform-tools_r37.0.1-windows, только после проверки
локального SHA и разрешения на восстановление:

```powershell
Get-FileHash .\Redmi9T-Native-Linux\artifacts\boot-linux-test-v6.img -Algorithm SHA256
.\platform-tools\adb.exe -s 35a1d5bf0221 push .\Redmi9T-Native-Linux\artifacts\boot-linux-test-v6.img /tmp/boot-linux-test-v6.img
.\platform-tools\adb.exe -s 35a1d5bf0221 shell 'wc -c /tmp/boot-linux-test-v6.img; sha256sum /tmp/boot-linux-test-v6.img'
# Сверить размер/SHA, root/device/partition/mount preconditions, затем:
.\platform-tools\adb.exe -s 35a1d5bf0221 shell 'dd if=/tmp/boot-linux-test-v6.img of=/dev/block/bootdevice/by-name/boot bs=4194304 conv=fsync'
.\platform-tools\adb.exe -s 35a1d5bf0221 shell 'head -c 23670784 /dev/block/bootdevice/by-name/boot | sha256sum'
.\platform-tools\adb.exe -s 35a1d5bf0221 shell 'sha256sum /dev/block/bootdevice/by-name/recovery /dev/block/bootdevice/by-name/dtbo /dev/block/bootdevice/by-name/vbmeta'
```

Ожидаются prefix SHA v6 и неизменные:

| Раздел | SHA256 |
|---|---|
| recovery | 1737005c5d9452d3238fcd0a2430956e7232937b35e9df427edc114f0dacd2eb |
| dtbo | 6fd8b752c9a64bc77ccb43a43834b38a2a61e0499c44de01c6d1a349d73ce9a6 |
| vbmeta | e1bd96f8e0ffe1a71cf41074aa46d3786fda7831b7395efa6205d166b1506ad5 |

Все exit codes должны быть 0. Полный hash boot-раздела не равен hash короткого
образа: проверяется точный префикс. Хвост boot не стирать и не занулять.
При ошибке не reboot; оставаться в TWRP. После успешной сверки — один normal
boot в рамках согласованного восстановления.

## Подтверждение возврата

Ждать ACM/NCM, сверить LEMON_INIT_V6_REACHED, LEMON_OPENRC_V6_REACHED,
ядро `7.4.0-rc1-lemon-bringup-v5`, Alpine, шесть UFS LUN, пустые swap/mounts.
Сохранённая v6 **не содержит временного тестового public key**, он раньше
добавлялся только в RAM. Поэтому после возврата основной канал восстановления —
COM4. Через него можно повторно добавить публичную часть сохранённого PC ключа
в RAM /root/.ssh/authorized_keys (700/600); приватный ключ остаётся на ПК.
Не менять контрольный v6 boot ради ключа. Его persistence исправлена в v7.

Host key после reboot тоже новый: прочитать full host public key/fingerprint
по физическому COM и закрепить в отдельном known_hosts. Не удалять проверку
подлинности SSH. Старый IP не доказывает идентичность нового SSH-сервера.

Если отдельный recovery не доступен, остановиться и согласовать дальнейший
план. EDL, прошивка загрузчика/AVB и запись иных разделов автоматически не допускаются.
