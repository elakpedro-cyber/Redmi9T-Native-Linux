# Linux v7 — результаты аппаратного испытания

Дата: 2026-11-05. Redmi 9T NFC lemon, SM6115 / Adreno 610.
**Короткий аппаратный headless-тест GPU и Mesa Freedreno прошёл. Телефон оставлен в v7.**
Это один shader/readback test, не стресс-тест и не подтверждение полной стабильности всех GPU функций.

## Выполненные действия и безопасность

Свежая рабочая v6 проверена через COM4, затем через SSH. После предыдущего reboot
Windows потеряла ActiveStore USB IPv4, а RAM v6 — тестовый public key. Восстановлены
только адрес USB NIC72 и уже разрешённый public key в RAM. Приватный ключ остался на ПК.
Новый host key v6 проверен через физический COM; проверка SSH не отключалась.
Логи: logs/v7-authorized/v6-ssh-*, v6-live.dtb, v6-config.gz;
дополнительно logs/first-test-v6/20261105T192639Z-*.

Образ v6 и все356 файлов контрольного snapshot проверены до испытания и после него.
Оригинальные boot/recovery/dtbo/vbmeta backups проверены до записи.
V7: **24428544 байта**, SHA256 `0ae797dbf092aaeb6fee4cb7a6d646a296f27c9f44ca9ead80fa57785f370746`.
AOSP unpack подтвердил header v2/page4096 и точные kernel/initramfs/stock DTB.
Артефакт v7 после проверки не пересобирался и не изменялся.

Пользователь аппаратно вошёл в отдельный TWRP. Root ADB, lemon, recovery kernel
4.19.252-sucksguuji-45543a51f5f8, заряд80%, boot=sde49/128 MiB, recovery=sda9.
Первый guard с точным uname без suffix отказал до любых действий; после чтения
фактического uname использована корректная проверка prefix4.19.252.

**TWRP автоматически смонтировал /data (f2fs) и /cache (vfat) RW.** Они штатно
отмонтированы до передачи и записи образа. Нельзя утверждать, что до этого
TWRP не выполнил фоновых metadata/discard writes. При последующих native Linux
проверках таких записей не обнаружено; это отдельные области доказательств.

Выполнена **одна намеренная запись только boot**, без erase/форматирования/GPT changes.
Прочитан обратно точный префикс24428544 байта: SHA совпал. Recovery/dtbo/vbmeta
SHA до и после записи совпали с оригиналами. Затем выполнена одна загрузка v7.
Доказательства: logs/v7-authorized/boot-write-journal.json и adb-write-commands.txt.

## Базовая система до и после GPU

| Проверка | Фактический результат |
|---|---|
| Linux | 7.4.0-rc1-lemon-bringup-v7 |
| /init | LEMON_INIT_V7_REACHED |
| OpenRC | LEMON_OPENRC_V7_REACHED; health/net/sshd started |
| Alpine / apk | 3.24.4 / apk-tools3.0.9-r0 |
| Bootshim | EL1, DAIF=0x3c0, реальная база0x40080000, end0x41ef5af0 |
| USB ACM | COM4, shell работает;12 serial heartbeats параллельно GPU |
| USB NCM | UsbNcm Host Device, ifIndex72, MAC02:00:00:00:77:01 |
| Адреса | Windows192.168.77.1/30 ↔ Linux192.168.77.2/30 |
| Ping | До и после GPU:3/3 ответов,0% loss, <1ms |
| SSH | Ключ из v7 initramfs принят без добавления ключа после boot; строгий COM pin |
| SCP/SFTP | До и после GPU:1024 байта в /tmp и обратно, SHA совпали |
| UFS | sda–sdf; write/discard/flush counters0, ioerr_cnt0x3 без роста |
| Storage policy | Только rootfs/виртуальные mounts, swap отсутствует |
| Домашняя сеть | 192.168.0.49/ifIndex7 не изменена; network snapshots совпали |

После re-enumeration v7 Windows снова потеряла временный USB IPv4. Он повторно
назначен только проверенному USB NIC; домашние Ethernet/Wi-Fi/DNS/routes не менялись.
Host key v7: `SHA256:hETyisXByiPBy5U5Bw04VEFKDjKFvx60dvaLW7CBd/8`, получен через COM4.
Это новый ключ данной RAM-сессии, не старый ключ v6 и не отключённая host verification.

До GPU: logs/hardware-v7/20261105T223116400.
После GPU: logs/hardware-v7/20261105T223610698.
Полный первый serial snapshot: logs/first-test-v7/20261105T193016Z-*.

## Шесть разных уровней подтверждения GPU

| Уровень | Результат и доказательство |
|---|---|
| Драйвер зарегистрирован | PASS: modprobe exit0, dmesg Initialized msm1.13.0 for5900000.gpu |
| Firmware загружена | SQE PASS: dmesg loaded qcom/a630_sqe.fw. ZAP MDT/b00/b01/b02 SHA проверены в RAM |
| GPU инициализирован | PASS для данного workload: CP/GLES job завершился, glFinish/readback прошли |
| Render node | PASS: /dev/dri/renderD128, platform driver adreno; отдельный card1, SimpleDRM card0 сохранён |
| Mesa распознаёт GPU | PASS: EGL1.5, OpenGL ES3.2 Mesa26.1.6, rendererFD610 |
| Реальный hardware render | PASS: compiled shaders, triangle into surfaceless RGBA FBO16×16, все256 pixels совпали |

Загрузка выполнена один раз командой с лимитом15s:
`timeout -s TERM -k 3 15 modprobe msm separate_gpu_kms=1`.
Параметр — **параметр модуля msm**, задан также в /etc/modprobe.d/lemon-gpu-manual.conf;
фактический /sys/module/msm/parameters/separate_gpu_kms равен1.
Для одного GPU без активного MDSS default auto-policy недостаточна, поэтому
явный separate_gpu_kms=1 необходим для отдельного GPU DRM master.

После стабильного bind выполнен **один** renderer process под timeout20s,
без повторов и бенчмарков. Время команды с SSH overhead примерно0.587s;
это не измерение чистого GPU времени. Timeout не сработал, exit0.
Вывод:

```
DRM=msm 1.13.0
EGL=1.5 GLES=OpenGL ES 3.2 Mesa 26.1.6 renderer=FD610
LEMON_GPU_V7_RENDER_PASS: GLES shader draw and 256 RGBA pixels verified
```

llvmpipe/softpipe исключены проверкой renderer; DRM fd обязан быть msm.
Probe использует конкретный render node через GBM, surfaceless context и FBO,
не KMS modeset и не framebuffer software output.

Сохранённый output1024 байта скачан на ПК, **все байты** дополнительно совпали
с256 повторами RGBA(64,128,191,255). SHA256:
`ebec48648edef1e298a2e12473d1c837bfc6ce99151088606b4cda794434b9cb`.
Файл: logs/v7-authorized/gpu-render-v7.rgba; вывод: gpu-render-once.stdout.

Отдельного trace вызова SCM/PAS для ZAP не включали. По коду a6xx_hw_init
успешный workload без сообщения `Zap shader not enabled`/ошибки авторизации
означает прохождение штатной ZAP ветки. Это вывод по коду и наблюдаемому
результату, а не самостоятельный cryptographic/PAS trace. Никаких bypass/патчей
подписи или SECVID register writes от оператора не выполнялось.

## Ошибки, температура и питание

Новые сообщения GPU сохранены отдельно: gpu-dmesg-delta.txt.
В delta нет GPU fault, SMMU/IOMMU fault, hang, timeout или reset loop.
Есть **два предупреждения**: supply vdd/vddcx not found, using dummy regulator.
В msm_gpu.c запрашиваются legacy vdd/vddcx handles; SM6115 описывает питание
через RPM/GMU-wrapper power domains. Рендеринг прошёл, но warnings не надо
скрывать или исправлять выдуманными regulator supplies. Перед автоматическим
GPU enable/v8 требуется отдельный review этой power-domain цепочки.

Boot-time sync_state pending для неиспользуемых peripherals присутствовали до
загрузки GPU; они не появились как следствие workload. Серьёзной нестабильности
не обнаружено. Существующий UFS ioerr_cnt0x3 не равен нулевой истории ошибок,
но во время теста не вырос.

GPU-thermal samples: до40.7°C,
после bind40.7°C,
после render41.1°C,
финально40.7°C.
Это точечные замеры, не гарантированный температурный peak.
После теста GPU devfreq сообщает320MHz, runtime_status=suspended.
Это reported selected frequency, не доказательство активной работы на320MHz
во время suspend. USB power_supply сообщает5V, current_now/current_max0;
эти поля не дают достоверного измерения мощности GPU. Rail voltage/current
не менялись принудительно и не измерялись внешним прибором.

## Вывод и следующий этап

- **Adreno610 работает в коротком аппаратном GLES shader/readback тесте.**
- **Mesa Freedreno с аппаратным ускорением работает для проверенного workload.**
- Это не проверка Vulkan, всех GLES функций, длительного DVFS, системного
  suspend/resume, устойчивости под нагрузкой или полного graphics stack.
- Можно переходить к **офлайн-порту DSI**. Аппаратно включать DSI ещё рано:
  нужны PMI632 LCDB bias driver/sequencing, точная подсветка и panel driver
  для подтверждённого TD4330 Truly v2 профиля. SimpleDRM не заменяет KMS/DSI.
- Перед v8: review dummy-regulator warnings и power domains, убрать зависимость
  Windows USB IPv4 от временного ActiveStore состояния безопасным USB-only
  механизмом, решить размещение Mesa runtime, затем закончить panel/backlight
  и отдельно Novatek SPI touch. Не включать всё сразу в одном hardware тесте.

Телефон **оставлен в работающей v7**, msm после теста runtime-suspended.
Mesa addon находится только в RAM; при reboot его надо передать заново,
автозагрузка msm остаётся запрещённой. Публичные SSH client keys уже в boot;
host key после reboot обязательно закреплять снова через физический COM.
Откат v6 не понадобился, но проверенный образ и отдельный TWRP сохранены.
DSI/backlight/touch не включались. Прошивки v8 и дальнейших опытов не было.

Машинный результат: reports/v7-hardware-result.json. Основные логи:
logs/v7-authorized, logs/hardware-v7, logs/first-test-v7.
