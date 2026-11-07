# Фактическое аппаратное испытание v6 — 2026-11-05

**Итог: PASS. Телефон оставлен в работающем v6; восстановление v5 не потребовалось.**
Была одна запись v6 только в boot и один normal boot v6. Повторной прошивки,
AVB-патчей, format/wipe, изменения GPT или загрузки v7 не было.

Испытанный boot-linux-test-v6.img:23670784 байта,
SHA256 `1eade4d8208905703286d01883e76b71728cc36b301f28563b58a0e53d4c8d63`.
Рабочий v5 сохранён: artifacts/boot-linux-test-v5.img и snapshots/v5-known-good,
SHA256 `ad15b45a3d60217711333fe1e07a30ede1e8b66d0195fcc3ecc00dda81586195`.

## Реальные результаты

| Проверка | На физическом телефоне / Windows |
|---|---|
| TWRP перед записью | Root ADB, lemon, kernel4.19.252, boot=sde49/recovery=sda9, по128MiB |
| Образ до записи | Размер/SHA на ПК и в /tmp TWRP совпали |
| Boot write/readback | Одна dd запись только boot, fsync; SHA точного префикса совпал |
| Проверка после normal boot | Boot prefix SHA вновь совпал через SSH, после аппаратной загрузки |
| Защищённые разделы | Recovery/dtbo/vbmeta SHA совпали до/после записи и после Linux boot |
| Ядро | 7.4.0-rc1-lemon-bringup-v5: сохранённое ядро, это ожидаемо для v6 |
| Bootshim | EL1, base40080000, end41e052b0, DAIF3c0, SCTLRc00808 |
| /init/OpenRC | LEMON_INIT_V6_REACHED и LEMON_OPENRC_V6_REACHED |
| Alpine/apk | Alpine3.24.4; apk-tools3.0.9 |
| OpenRC | default: lemon-health, lemon-net, lemon-sshd started |
| ACM | USB Serial Device COM4, interface MI00; static rescue shell выполняет команды |
| NCM | UsbNcm Host Device, interface MI02, Status OK/Up, Ethernet2/ifIndex72 |
| IPv4 | Windows192.168.77.1/30 ↔ phone192.168.77.2/30 |
| Ping | 3/3, потерь0%, время<1ms; дополнительные2/2 также без потерь |
| SSH | Настоящие команды uname -a, Alpine release, rc-status, IP, mounts/stats выполнены |
| SSH auth | Успешная подпись отдельным тестовым Ed25519; password-only probe отвергнут, предлагается только publickey |
| SCP/SFTP | 1024-byte upload и download в /tmp tmpfs; SHA совпал, GUID-файл удалён |
| SHA тестового файла | dde81dbcaf32bc88d134fc0f68f393ecf563a01e109429c7fb0bd3e38ff2691b |
| ACM + SSH вместе | Serial collector и SSH команды работали параллельно; после SCP COM доступен |
| UFS | Micron, sda–sdf и разделы сохранены; mounts отсутствуют |
| No writes в v6 | Write/sectors-written/discard counters0; ioerr3 без роста, swap пуст |
| Домашняя сеть | ifIndex7,192.168.0.49/24 сохранён; DNS/DHCP/gateway snapshots в Windows test одинаковы |
| Откат | Не потребовался: v6 пригоден для дальнейшей работы через ACM/SSH |

## Ошибки и их устранение

1. Windows назначил ACM **COM4**, не COM3. Это новая нумерация для PID0106,
   а не потеря консоли. Registry/назначение COM не менялись.
2. Первый elevated USB-IP helper остановился до изменений из-за зарезервированного
   имени $HOME. Исправлен на protectedHomeIndexes. Повторный helper изменил только
   NCM ifIndex72; домашний ifIndex7 не затрагивался. ssh-agent не запускался.
3. Windows ssh-keyscan выбрал sntrup761x25519-sha512@openssh.com и завершился
   с unsupported KEX. Это соответствует [известной проблеме Win32-OpenSSH](https://github.com/PowerShell/Win32-OpenSSH/issues/2140).
   Полный server public key взят через COM, fingerprint сверён; strict host checking
   сохранён. Для команд указан совместимый curve25519-sha256, без правок sshd/UDC.
4. Существующий личный public key сервер принимал, но клиент в BatchMode не
   отправлял подпись; agent отсутствовал. Пароль не подбирался и не читался.
   После отдельного согласования создан тестовый ключ на ПК, его public часть
   добавлена в RAM authorized_keys с сохранением прежнего ключа. Новый ключ
   успешно подписал аутентификацию. Парольный вход не включался.

## Важная граница сохранности UFS

При ручном входе TWRP автоматически смонтировал /data и /cache rw.
Оба штатно отмонтированы до push/write/reboot; затем оставались только virtual FS.
Мы не записывали туда файлы, но **нельзя утверждать абсолютное отсутствие
метаданных/фоновых записей самим recovery**. Нулевые TWRP whole-disk stats также
не используются как доказательство: они оставались0 даже при чтении разделов.
В отличие от этого, работающий v6 имеет реальные read counters и нулевые
write/discard counters; состояние подтверждено до/после SCP.
Единственная намеренная запись раздела — согласованный boot.

## Как подключиться сейчас

Адрес: root@192.168.77.2, порт22, COM4. На Windows задан только USB IPv4.
Текущий host fingerprint:
`SHA256:jdEY9bOPwMk914MUMhGGbn4BHj2CdM4XrEIoMvGrmBU`.
Host key создан в RAM и изменится при новом boot.

Тестовый private key остался только на ПК:
`C:\Users\HadirPC\.ssh\redmi9t_v6_test_20261105T163939Z`.
Его public часть добавлена только в текущую RAM-сессию и **исчезнет после reboot**;
исходный прошитый образ по-прежнему содержит прежний public key.
Не считать новый runtime key постоянной настройкой boot image.

Из каталога проекта:

```powershell
ssh -i "$env:USERPROFILE\.ssh\redmi9t_v6_test_20261105T163939Z" -o IdentitiesOnly=yes -o KexAlgorithms=curve25519-sha256 -o StrictHostKeyChecking=yes -o UserKnownHostsFile=logs/hardware-v6/20261105T193940984/usb/known_hosts root@192.168.77.2
```

Не присылать/не включать private key в архивы проекта. Для следующей сборки
можно отдельно выбрать постоянный public key; новый image/flash в этой сессии
не выполнялся. Windows IPv4 находится в ActiveStore: после перезапуска ПК
проверить его заново только на USB adapter.

## Логи и границы результата

- logs/v6-authorized/boot-write-journal.json и adb-write-commands.txt: ровно одна запись и readback.
- reports/v6-twrp-prewrite.txt, v6-twrp-unmount.txt, v6-ram-image-checks.txt.
- reports/v6-native-postboot-hashes.txt: boot/recovery/dtbo/vbmeta после загрузки.
- logs/first-test-v6/: raw COM transcripts, identity/OpenRC/UFS/SSH logs.
- logs/hardware-v6/20261105T193940984/: успешные ping, SSH, SCP, SHA и home snapshots.
- reports/v6-ssh-parallel-acm.txt и v6-real-password-denied.stderr.
- reports/first-test-v6-assessment.json и v6-hardware-result.json: машинные результаты.
- Неудачные host attempts193115427/193349834 оставлены для анализа ошибок.

Это один успешный boot и ограниченные проверки, не длительный endurance,
suspend/resume или cable-replug qualification. Инъекцией аппаратных ошибок NCM
не занимались; доказано одновременное выполнение ACM/SSH и сохранение консоли
при клиентских SSH ошибках. В логах Dropbear дата Jan01: синхронизация часов
в рамках теста не настраивалась.

## Дальше

V6 hardware gate пройден для офлайн-подготовки v7. Начат read-only анализ
сохранённых исходников: Adreno610 требует a630_sqe.fw и a610_zap.mdt, DPU каталог
SM6115 имеет версию6.3. Mesa документирует Freedreno для семейства Adreno6xx,
но на этом телефоне GPU acceleration пока не проверен. Panel/touch модели
не определены. V7 не собран, не загружен и не прошит. Новые изменения состояния
телефона и следующая прошивка требуют нового согласования.
