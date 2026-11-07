# Возврат рабочего v5 после разрешённого теста v6

Здесь только план, команды не выполнялись. Тест должен менять только boot;
отдельный TWRP recovery сохраняется. Разрешение на подготовку не является
разрешением на reset, flash или восстановление.

Контрольный v5: artifacts/boot-linux-test-v5.img, **23609344 байта**,
SHA256 `ad15b45a3d60217711333fe1e07a30ede1e8b66d0195fcc3ecc00dda81586195`.
Вторая копия: snapshots/v5-known-good/artifacts/boot-linux-test-v5.img.

## 1. В согласованном восстановлении войти в TWRP

При зависании — аппаратный reset Power и вход Power/Volume Up в отдельный recovery.
При отсутствии recovery остановиться; не использовать wipe/EDL/unlock/прошивку
других разделов. Пока phone не в TWRP, команды ADB ниже не применять.

Из исходного каталога platform-tools_r37.0.1-windows:

```powershell
.\platform-tools\adb.exe devices -l
.\platform-tools\adb.exe shell id
.\platform-tools\adb.exe shell uname -r
.\platform-tools\adb.exe shell readlink -f /dev/block/bootdevice/by-name/boot
.\platform-tools\adb.exe shell readlink -f /dev/block/bootdevice/by-name/recovery
.\platform-tools\adb.exe shell blockdev --getsize64 /dev/block/bootdevice/by-name/boot
.\platform-tools\adb.exe shell blockdev --getsize64 /dev/block/bootdevice/by-name/recovery
.\platform-tools\adb.exe shell sha256sum /dev/block/bootdevice/by-name/recovery
New-Item -ItemType Directory -Force .\Redmi9T-Native-Linux\logs\v6-recovery | Out-Null
.\platform-tools\adb.exe pull /sys/fs/pstore .\Redmi9T-Native-Linux\logs\v6-recovery\pstore
.\platform-tools\adb.exe shell dmesg > .\Redmi9T-Native-Linux\logs\v6-recovery\twrp-dmesg.txt
```

Root TWRP4.19.252; boot=sde49, recovery=sda9, оба128MiB.
Recovery SHA должен остаться
1737005c5d9452d3238fcd0a2430956e7232937b35e9df427edc114f0dacd2eb.
При расхождении остановиться. Pstore может быть пустым; не удалять файлы,
retention после reset не гарантирован. Отличать старый V5 marker от нового V6.

## 2. Проверить v5 в RAM, затем восстановить только boot

```powershell
Get-FileHash .\Redmi9T-Native-Linux\artifacts\boot-linux-test-v5.img -Algorithm SHA256
.\platform-tools\adb.exe push .\Redmi9T-Native-Linux\artifacts\boot-linux-test-v5.img /tmp/boot-linux-test-v5.img
.\platform-tools\adb.exe shell wc -c /tmp/boot-linux-test-v5.img
.\platform-tools\adb.exe shell sha256sum /tmp/boot-linux-test-v5.img
```

Сначала сверить точные размер/SHA. Только в разрешённом восстановлении:

```powershell
.\platform-tools\adb.exe shell 'dd if=/tmp/boot-linux-test-v5.img of=/dev/block/bootdevice/by-name/boot bs=4194304 conv=fsync'
.\platform-tools\adb.exe shell 'head -c 23609344 /dev/block/bootdevice/by-name/boot | sha256sum'
.\platform-tools\adb.exe shell sha256sum /dev/block/bootdevice/by-name/recovery
```

Требуются exit codes0, prefix SHA=v5 выше и исходный recovery SHA. Проверять
префикс, не полный hash более длинного boot-раздела. При ошибке записи не reboot,
оставаться в TWRP для разбора. Не использовать conv=noerror.
После успеха можно остаться в TWRP; normal boot v5 — только в рамках разрешения.
В v5 вернутся прежний ACM-only PID0104, статическая shell, Alpine/OpenRC и UFS;
новые RAM host keys/IP настройки v6 исчезнут. Windows ActiveStore USB IPv4 на
отключённом composite adapter не мешает v5; другие сетевые адаптеры не изменялись.

Оригинальные boot/recovery/dtbo/vbmeta backups также сохранены и проверены на ПК,
но для этого отката нужен рабочий v5, а не восстановление отсутствующего Android.
Recovery/dtbo/vbmeta/super/userdata/persist/modem/ABL не прошивать.
