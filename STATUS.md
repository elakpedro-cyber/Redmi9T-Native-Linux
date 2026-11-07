# v7 — аппаратный headless GPU тест пройден

2026-11-05: один boot-only flash с readback SHA, одна загрузка v7, один modprobe MSM и один shader/readback тест. Mesa26.1.6 определила FD610; все256 RGBA pixels совпали. USB ACM COM4, NCM, SSH/SFTP и UFS сохранились. Телефон оставлен в v7.

Итог: [V7_HARDWARE_RESULTS.md](V7_HARDWARE_RESULTS.md), reports/v7-hardware-result.json. DSI/backlight/touch не включались; v8 не прошивалась. V6 snapshot сохранён. TWRP ранее автомонтировал data/cache RW; их отключили до flash, ранние записи recovery исключить нельзя.

Ниже — историческое состояние подготовки.

---

# v7 — подготовлена, аппаратно не испытана

2026-11-05: собраны Linux 7.4.0-rc1-lemon-bringup-v7, GPU-only MSM module,
device-owned firmware и компактный RAM boot. MSM autoload запрещён; для ручного
headless probe задан separate_gpu_kms=1. Mesa/FBO shader test — отдельный RAM addon.
Публичные SSH keys включены в initramfs; private PC key вне образа, host key
проверяется заново через COM после reboot. MDSS/DSI/touch не активировались.

Телефон остался в работающей v6. Нет reboot/flash/GPU workload. v6 snapshot
и исходные backups сохранены. Новое аппаратное испытание требует разрешения.

Текущие документы: V7_VALIDATION.md, V7_HARDWARE_MATRIX.md, V7_GPU_RESEARCH.md,
V7_DISPLAY_RESEARCH.md, V7_TOUCHSCREEN_RESEARCH.md, V7_FIRST_BOOT.md, V7_RECOVERY.md.
Хеши: reports/v7-final-manifest.json. Ниже — предыдущее состояние v6.

---

# Текущий статус — v6 испытан на физическом Redmi9T

**PASS: v6 работает; откат v5 не потребовался.**
Одна согласованная запись только boot и один normal boot. SHA прочитанного
boot совпал до и после загрузки; recovery/dtbo/vbmeta SHA остались исходными.

| Проверка | Фактический результат |
|---|---|
| /init / OpenRC | V6 markers, health/net/sshd started |
| Linux | 7.4.0-rc1-lemon-bringup-v5, ядро v5 сохранено |
| Alpine/apk | 3.24.4 / 3.0.9 |
| ACM | COM4, работает параллельно SSH |
| NCM | UsbNcm Host Device, ifIndex72, Up |
| IP/ping | .77.1/30 ↔ .77.2/30, 0% loss, <1ms |
| SSH | Key login, uname -a/rc-status выполнены; password не предлагается |
| SCP | 1024 bytes в /tmp tmpfs и обратно, SHA совпал, RAM файл удалён |
| UFS | Шесть LUN, no mounts/swap, writes/discards0, ioerr3 без роста |
| Домашняя сеть | ifIndex7/192.168.0.49 и snapshots DHCP/DNS/gateway сохранены |
| Auth key | Отдельный разрешённый тестовый public key добавлен только в RAM |
| TWRP caveat | Автоматически монтировал /data/cache rw до нашего штатного unmount; фоновые metadata writes recovery исключить нельзя |
| v7 | Только офлайн-анализ источников, никаких сборок/прошивок/драйверов на телефоне |

Результаты, ошибки и команда SSH: V6_HARDWARE_RESULTS.md.
Машинный результат: reports/v6-hardware-result.json.
Резерв v5: snapshots/v5-known-good. Снимок v6: snapshots/v6-hardware-validated.
Исходное разрешение на один v6 boot использовано; новые reboot/flash требуют нового согласования.
