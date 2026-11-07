# v8 — возврат к аппаратно проверенной v7

Резерв находится в `snapshots/v7-hardware-validated/artifacts/boot-linux-test-v7.img`. Проверены 416 файлов снимка, на копии выставлен атрибут read-only.

- Образ v7 имеет 24 428 544 байта.
- SHA-256 `0ae797dbf092aaeb6fee4cb7a6d646a296f27c9f44ca9ead80fa57785f370746`.

При сбое сначала сохранить COM/SSH/pstore, если доступны. Для согласованного восстановления войти в TWRP аппаратно. Подтвердить root ADB, serial, модель, recovery kernel и пути разделов из [плана A](V8_FIRST_BOOT.md). Отмонтировать /data и /cache, проверить tmpfs /tmp. Сверить recovery/dtbo/vbmeta с [исходными SHA](reports/backup-sha256-before.json).

Передать v7 в `/tmp/boot-linux-test-v7.img`, повторно сверить длину и SHA на телефоне. Для записи использовать только by-name boot, разрешив путь в `/dev/block/sde49` до запуска команды:

```sh
dd if=/tmp/boot-linux-test-v7.img of=/dev/block/bootdevice/by-name/boot bs=4194304 conv=fsync
head -c 24428544 /dev/block/bootdevice/by-name/boot | sha256sum
```

При успешном readback повторно сверить SHA recovery/dtbo/vbmeta, затем загрузить v7. Проверить COM, маркеры v7, пустой swap, виртуальные mounts и UFS counters. Заново закрепить SSH host key по физическому COM. Для GPU отдельный RAM addon v7 лежит в снимке и загружается по ранее согласованному протоколу.
