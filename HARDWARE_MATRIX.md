# Аппаратная матрица — v4 на устройстве, v5 только офлайн

| Компонент | Реальное v4 | v5 офлайн | Осталось / отсутствует |
|---|---|---|---|
| ARM64 bootshim | EL1, base40080000, DAIF3c0, M/C off | 15 сценариев, источники сохранены | Новая сборка на телефоне |
| Linux /init | 7.4-rc1-v4, marker V4 | v5 kernel и marker упакованы | Marker V5 на железе |
| RAM | Около 3.5 GiB | Rootfs ~33 MiB, initramfs ~13.4 MB | Реальное потребление v5 |
| UFS HBA/PHY | ufshcd-qcom и QMP UFS привязаны | Все v4 builtins и DTB сохранены | Регрессия v5, PM и длительная стабильность |
| UFS media | Micron MT064GASAO2U21, FW0605, sda–sdf | SCSI/SD/GPT включены | Не выполнялись записи и полный surface test |
| Сектора/GPT | 4096; header CRC шести LUN корректны | Сектор4096 в deviceinfo | Сохранение содержимого после теста |
| USB ACM | COM3 shell работает | Прежний gadget/getty, static rescue v4 | Реальный v5 enumeration/login |
| USB ECM/NCM/RNDIS | Не проверено | Встроены, default off | NIC/Windows driver, трафик и ACM вместе |
| SSH | Нет | Dropbear ARM64 запускает -V | Ключи, сеть и сеанс SSH |
| SimpleDRM/fb | 1080×2340, simpledrmdrmfb | Сохранено | Регрессия v5 |
| Native DSI/panel | Не работает в текущем DT | MDSS/DSI disabled | Правильный panel driver/вариант панели |
| GPU acceleration | Нет render node, GPU driver отсутствует | Adreno610 DT okay, DRM_MSM=n | MSM+firmware+Mesa и аппаратный тест |
| Touchscreen | Нет touch input; только три устройства кнопок | Нет подходящего узла/включённого touch driver | Идентификация контроллера/варианта и DT/driver |
| Кнопки | pm8941_pwrkey, pm8941_resin, gpio-keys зарегистрированы | INPUT_EVDEV сохранён | События отдельных кнопок здесь не проверялись |
| Alpine/OpenRC | В v4 отсутствует | Настоящие ARM64 пакеты, версии/синтаксис проверены | PID1/default runlevel на lemon |
| apk и диагностика | v4 rescue BusyBox | 67 Alpine packages, lsblk/blkid/ip/curl/strace | Работа после загрузки v5 |
| Wi-Fi/Bluetooth/audio/модем/камера | Не подтверждено | Не настраивались | За пределами этого этапа |
| Pstore | Настройки v4 сохранены | Совместимый ramoops | Retention после reset не доказан |

## Графика и touch: что говорит источник

Pinned mainline sm6115-xiaomi-lemon.dts включает GPU и оставляет dispcc/MDSS
выключенными до реализации панели; комментарий прямо объясняет сохранение simplefb.
В sm6115.dtsi GPU находится по **0x05900000**, не по 0x05000000.
В live DTB GPU okay, но у 5900000.gpu нет driver link. DRM_MSM отключён,
Mesa/firmware в rootfs не добавлялись; наличие framebuffer не означает ускорение.
В a6xx_catalog.c pinned ядра имеется Adreno610 и указание a610_zap.mdt. Это
поддержка в исходниках, а не доказательство наличия нужной firmware и запуска GPU
на данной плате. Дальнейшая работа должна проверить firmware/OPP/speedbin/SMMU
и затем render node/Mesa; в v5 GPU не включался, чтобы сохранить framebuffer.

Touch-контроллер по прочитанным данным не идентифицирован. В native DT нет
touchscreen node, соответствующие Goodix/Novatek/EDT опции отключены. Ни три
устройства кнопок, ни разрешение экрана не подтверждают сенсор. Не выполнялись
I2C scans, reset, загрузка touch firmware или записи в GPIO/sysfs.

Доказательства: logs/v4-live-diagnostics/*-graphics-input.txt и *-gpu-driver.txt,
reports/hardware-v5-dt-audit.json, config/linux-v5.config и pinned исходники
arch/arm64/boot/dts/qcom/sm6115*. Фактический touch/panel вариант пока неизвестен.
