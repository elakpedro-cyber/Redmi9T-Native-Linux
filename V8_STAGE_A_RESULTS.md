# v8 — аппаратный результат Stage A

5 ноября 2026, Redmi 9T NFC lemon. **Stage A пройден. Телефон оставлен в работающей v8.**

Сохранены свежие логи v7 по SSH. Резервная v7 в `snapshots/v7-hardware-validated` имеет 24 428 544 байта и SHA-256 `0ae797dbf092aaeb6fee4cb7a6d646a296f27c9f44ca9ead80fa57785f370746`. Перед прошивкой сверены размеры и SHA двух образов, проверены отключённые узлы и отсутствие прототипов в initramfs.

TWRP автоматически смонтировал /data и /cache в RW. Оба раздела отмонтированы до передачи образа и записи. Ранние записи TWRP исключить нельзя. Выполнена одна намеренная запись в boot (`sde49`) и одна загрузка. SHA-256 прочитанного префикса 24 698 880 байт совпал с образом v8 `563296819c9e22da2ffcc38918b0761ca3d18eed7ae181123796fd6fb1033a29`. SHA recovery, dtbo и vbmeta совпали до и после записи. [Журнал записи](logs/v8-authorized/boot-write-journal.json).

| Проверка | Фактический результат |
|---|---|
| Linux | `7.4.0-rc1-lemon-bringup-v8`, маркер `LEMON_INIT_V8_REACHED`. Bootshim EL1, база `0x40080000`, DAIF `0x3c0`. |
| Alpine и OpenRC | Alpine 3.24.4, apk-tools 3.0.9-r0, маркер `LEMON_OPENRC_V8_REACHED`, health/net/sshd запущены. |
| USB ACM | COM4 и аварийная shell доступны. Во время GPU проверки получены 12 serial heartbeat. |
| USB NCM | Windows UsbNcm Host Device, ifIndex 72. После переопределения USB восстановлен временный адрес 192.168.77.1/30 только на NCM. Ping на 192.168.77.2/30 без потерь. |
| SSH/SFTP | Принят сохранённый ключ клиента. Новый серверный ключ закреплён через COM, fingerprint `SHA256:NKpArzg8M3YwjqueFCBSGEqDe922Mh4gi+H1XaMNIPk`. Roundtrip 1024 байт в /tmp прошёл. GPU readback дополнительно скачан через SFTP после теста. |
| UFS | Все шесть LUN sda–sdf. Только виртуальные mounts, swap отсутствует. Write, discard и flush равны нулю, ioerr_cnt `0x3` на каждом LUN до и после теста. |
| DRM/MSM | Однократно загружен `msm` с `separate_gpu_kms=1`. DRM 1.13.0, Adreno renderD128, SimpleDRM сохранён. |
| Freedreno | Mesa 26.1.6, EGL 1.5, OpenGL ES 3.2, renderer FD610. Один короткий shader draw завершился до лимита 20 с. Все 256 RGBA-пикселей совпали с эталоном и повторно проверены на ПК. |
| DSI и сенсор | Живой DT до и после GPU подтвердил семь отключённых узлов, включая MDSS/DPU/DSI/PHY/dispcc и подсветку. Дисплейные platform bindings отсутствовали. Узлов TD4330, LCDB и Novatek нет. Физическое изображение через DSI на этом этапе не проверялось. |

SHA-256 1024-байтного shader readback `ebec48648edef1e298a2e12473d1c837bfc6ce99151088606b4cda794434b9cb` совпадает с v7. Температура GPU в точечных замерах составила 42,0 °C до и 42,3 °C после теста. GPU вернулся в runtime suspend.

Сравнение dmesg с сохранённой v7 после нормализации времени не выявило новых сообщений об ошибках GPU, IOMMU, clocks и regulators. Повторились прежние предупреждения legacy supplies `vdd` и `vddcx` от GPU с переходом на dummy regulators. Dmesg подтвердил загрузку SQE. Аппаратный результат относится к одной короткой нагрузке.

- [COM и первый запуск](logs/first-test-v8/20261105T201234Z.json)
- [USB, SSH и SFTP](logs/hardware-v8/20261105T231319350/result.json)
- [Вывод GPU](logs/v8-authorized/gpu-render-once.stdout) · [Сохранённые пиксели](logs/v8-authorized/gpu-render-v8.rgba)
- [Живые DT и UFS проверки после GPU](logs/v8-authorized/after-gpu-gates.json) · [Dmesg](logs/v8-authorized/after-gpu-dmesg.txt)
