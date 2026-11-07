# Живая диагностика v3 — 2026-11-05

Через COM3 действительно выполнены команды чтения на работающем телефоне.
Клиент: `scripts/serial-readonly-v3.py`, локальный pyserial, 115200, без flow control.
Сеансы закрыты; перезагрузок, загрузки v4, записи разделов, sysfs/debugfs не было.
Полные команды, ответы, raw-транскрипты и результаты framing находятся в
`logs/v3-live-diagnostics/`: группы initial, hardware, verification.

## Подтверждено

| Проверка | Реальный результат |
|---|---|
| Ядро | `7.4.0-rc1-lemon-bringup`, ARM64 |
| Выполнение /init | `/run/init-reached` = `LEMON_INIT_V3_REACHED` |
| USB ACM | Интерактивные команды через COM3; UDC `configured` |
| Экран | fb0 `simpledrmdrmfb`, 1080×2340 |
| RAM | MemTotal 3706100 kB; MemAvailable 3577244 kB в снимке |
| Bootshim | base `0x40080000`, end `0x41b002b0`, EL1 |
| CPU handoff trace | SCTLR `0xc00808`: M/C выключены, I включён; DAIF `0x3c0` |
| Накопители | Только loop; `/proc/partitions` без дисков; `scsi_host` отсутствует |
| UFS HBA | `4804000.ufshc` существует, `/driver` отсутствует |
| UFS PHY | `4807000.phy` существует, `/driver` отсутствует |
| DT HBA | `qcom,sm6115-ufshc`, `qcom,ufshc`, `jedec,ufs-2.0`; `okay` |
| DT PHY | `qcom,sm6115-qmp-ufs-phy`; `okay` |
| Провайдеры | GCC связан с gcc-sm6115; SMMU связан с arm-smmu |

Эта трасса подтверждает реальный адрес переходника для данного запуска v3.
Она не определяет все внутренние значения UEFI и не является измерением cache coherency.

## Питание, clocks, resets, deferred probe

В live supplier links GCC, SMMU и RPM/glink имеют `available`; взаимные
зависимости UFS/PHY — `dormant`. Dmesg содержит регистрацию SMMU, IOMMU group
для HBA и ожидание GCC sync_state для UFS/PHY. Попыток probe ufshcd нет.
Сообщения `Fixed dependency cycle(s)` сами по себе не означают неисправность.

L11/L18/L24 выключены, users=0; L4/L12 включены и уже используются USB.
При отсутствующем драйвере UFS выключенные его питания ожидаемы; это не
доказательство неправильных напряжений. Питания вручную не включались.
`runtime_status=unsupported` у непривязанных устройств не доказывает отказ железа.

Debugfs не смонтирован. Поэтому devices_deferred, clk_summary и regulator_summary
не удалось прочитать; debugfs намеренно не монтировался. Реальное состояние reset
линий и частоты UFS clocks не измерены. Разрешение DT-ссылок проверено офлайн:
`reports/ufs-v4-dt-dependencies.json`. Полное live DTB не выгружалось; сравнение
живого дерева ограничено прочитанными compatible/status и зависимостями sysfs.

## Происхождение конфигурации

В v3 BusyBox отсутствуют zcat/gunzip/base64/od/hexdump. Использована разрешённая
альтернатива: IKCONFIG извлечён на ПК из сохранённого v3 `artifacts/Image`.
Он побайтово совпадает с `config/linux.config`, SHA-256:
`1abed5e8dbd7f59401ad1b131c06809cd7c6563f0c6f720891693f10d8fc267b`.
Сжатый блок — 36002 байта, как размер live `/proc/config.gz`.
Это не выгрузка live config через serial. Данные и метод сохранены в
`logs/v3-live-diagnostics/config-provenance.json`.

Отрицательные grep по kallsyms и отсутствующие sysfs файлы имеют ненулевой exit
status; они сохранены как диагностические результаты, а не скрыты как успех.
В минимальном ash нет `command`; ошибка `command -v` не использовалась как
доказательство отсутствия applet. Список applets получен через BusyBox --list.
