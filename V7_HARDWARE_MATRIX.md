> Отчёт подготовки до аппаратного испытания. Текущий аппаратный результат: [V7_HARDWARE_RESULTS.md](V7_HARDWARE_RESULTS.md).

# Матрица v7

Состояние на 2026-11-05. Телефон остался в работающей **v6**;
ядро v6 имеет release `7.4.0-rc1-lemon-bringup-v5`, это не признак отката userspace.

| Компонент | Поддержка исходниками | Проверено офлайн v7 | На физическом Redmi 9T |
|---|---|---|---|
| ARM64 bootshim | существующие start.S/bridge.c/link.ld | 15 handoff/guard cases, ABL 3 layouts, DAIF/cache instruction checks | работает в v6; новый payload v7 не загружался |
| Alpine 3.24.4, OpenRC, apk | сохранена существующая RAM-среда | /init, V7 markers, services, ARM64 SSH tests | подтверждено в v6 |
| USB ACM + emergency shell | прежний v6 helper и static BusyBox | normal/failure NCM model, shell без Alpine loader/OpenRC | COM4 работает в v6; номер после v7 не гарантирован |
| USB NCM + SSH/SFTP | прежние gadget и Dropbear -s | SSH правильным ключом, отказ wrong key/password, SFTP SHA | подтверждено в v6, адреса .77.1/.77.2 |
| Клиентские SSH public keys | два public keys в v7 initramfs | public-only, права 700/600, содержимое проверено | новый ключ проверен в RAM v6; persistence v7 ещё не испытана |
| SSH host identity | новый Ed25519 key в RAM каждого boot | COM pin helper; Windows strict host checking сохранён | старый ключ v6 проверен; будущий v7 надо закрепить заново |
| UFS/SCSI | все v6 builtins сохранены | config, init без disk mounts/swap | 6 LUN sda–sdf, чтение vendor/modem; записи/discards 0 |
| Adreno 610 DRM/MSM | mainline a6xx + gmu-wrapper, SM6115 GPUCC/SMMU/OPP | msm.ko, ABI, firmware/DT/provider checks | driver не загружался, render node отсутствует в v6 |
| SQE + signed ZAP | firmware loader SCM/PAS | same-device extraction, ELF/MDT/segments/relocation/bounds | подпись и SQE совместимость ещё не проверены |
| Mesa Freedreno | семейство A610/6xx поддерживается | Mesa 26.1.6 addon, ARM64 dependencies, GLES shader probe | аппаратное ускорение не подтверждено |
| SimpleDRM | включён, firmware framebuffer | сохранён | 1080×2340×32 в v6 |
| MDSS/DPU/DSI/PHY | SM6115 host/DPU/PHY есть | узлы/питание изучены; оставлены disabled | полноценный KMS/DSI не подтверждён |
| Панель | выбран TD4330 Truly v2 video downstream profile | 58 свойств совпали с Xiaomi source, DCS разобраны | подтверждён выбор профиля TWRP; DDIC ID не читался |
| LCD bias | downstream PMI632 LCDB | обнаружен пробел mainline driver, схема проанализирована | не управляется v7, электрические тесты не выполнялись |
| Backlight | upstream кандидат LM36923 + downstream PWM | вариативность сохранена, не включён | контроллер конкретной ревизии не подтверждён |
| Touch | Novatek NVT SPI выбран panel phandles | SPI/GPIO/supplies/driver изучены; evtest в addon | точный chip ID/PID/FW и события не подтверждены |
| Кнопки | GPIO/PMIC input | сохранена config/DT | input devices зарегистрированы в v6; новые нажатия не тестировались |
| Weston | дальнейший этап после GPU/KMS | не добавлялся и не запускался | не проверен |

У UFS `ioerr_cnt=0x3` уже присутствовал в начальном снимке и не вырос;
это нельзя выдавать за нулевое число ошибок за всё время работы контроллера.
В начале и конце этой сессии write/discard/flush counters всех LUN равны нулю,
дисковых mounts/swap нет. Доказательства — два набора read-only SSH логов.

Полное описание: V7_GPU_RESEARCH.md, V7_DISPLAY_RESEARCH.md,
V7_TOUCHSCREEN_RESEARCH.md. Планы испытания и отката: V7_FIRST_BOOT.md,
V7_RECOVERY.md. Образ v7 подготовлен, но не записан.
