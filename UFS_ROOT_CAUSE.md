# Причина отсутствия UFS в v3

Подтверждённый блокер — исключённые из v3 драйверы. `CONFIG_SCSI=n` и
`CONFIG_PHY_QCOM_QMP_UFS=n`; BLK_DEV_SD/UFSHCD/UFS_QCOM недоступны по зависимостям.
`CONFIG_SCSI_MOD=y` не включает SCSI. В live v3 нет регистрации UFS-драйверов,
привязки HBA/PHY, SCSI hosts и попыток ufshcd probe. При этом оба DT-устройства
присутствуют и включены. Это объясняет наблюдаемое отсутствие дисков до какого-либо
аппаратного probe. Последующие аппаратные блокеры пока не исключены.

## Исправление

| Реальное имя Kconfig | v3 | v4 |
|---|---|---|
| CONFIG_SCSI | n | y |
| CONFIG_SCSI_DMA | n | y |
| CONFIG_BLK_DEV_SD | n | y |
| CONFIG_SCSI_UFSHCD | n | y |
| CONFIG_SCSI_UFSHCD_PLATFORM | n | y |
| CONFIG_SCSI_UFS_QCOM | n | y |
| CONFIG_PHY_QCOM_QMP_UFS | n | y |

Полный список различий, включая автоматические зависимости:
`CONFIG_DIFF_V3_V4.md`. Сохранены все встроенные возможности v3. Разделы GPT и
MSDOS поддерживаются прежними CONFIG_EFI_PARTITION/CONFIG_MSDOS_PARTITION=y.
MODULES=n сохранён; установка модулей не нужна.

Проверен именно исходный commit Linux
`05441d697f7f9a927264f4058cbbc6a03dfcac9d`, 7.4-rc1:
`drivers/ufs/Kconfig`, `drivers/ufs/host/Kconfig`,
`drivers/phy/qualcomm/Kconfig`, `drivers/ufs/host/ufs-qcom.c`,
`drivers/phy/qualcomm/phy-qcom-qmp-ufs.c`.
Выдержки — `reports/ufs-v4-source-evidence.txt`.
UFSHCD требует SCSI и SCSI_DMA; Qualcomm HBA также требует platform UFS,
ARCH_QCOM, GENERIC_MSI_IRQ, RESET_CONTROLLER. Olddefconfig и проверка итоговой
конфигурации подтвердили зависимости, System-v4.map — скомпилированные probe.

## Device Tree

DTB оставлен проверенным v3: `sm6115-xiaomi-lemon-v2.dtb`.
HBA совпадает с `qcom,ufshc` из ufs-qcom; PHY имеет точное совпадение
`qcom,sm6115-qmp-ufs-phy`, для которого драйвер содержит собственные таблицы SM6115.
Разрешены ссылки PHY, GCC clocks/reset/GDSC, RPM reference clock, SMMU и питаний.

HBA: vcc=L24, vccq2=L11, vdd-hba=L18. PHY: vdda-phy=L4, vdda-pll=L12.
Reset PHY предоставляется HBA; reset HBA — GCC. Это описанная аппаратная
зависимость, а не повод добавлять фиктивный узел. Полная расшифровка handles и
аргументов — `reports/ufs-v4-dt-dependencies.json`. Никаких DT-подмен для UFS нет.

## Что ещё требует устройства

После разрешённого запуска v4: привязка обоих драйверов, питание/clock/reset,
link training, LUN discovery, SCSI disk/GPT scan, отсутствие IOMMU ошибок и
сохранение работающих USB/экрана. `/dev/sda` и разделы пока не подтверждены.
В зависимости от порядка UFS LUN разделы могут оказаться на sdb/sdc и далее.
Если probe откладывается, сначала сохранить автоматический журнал и dmesg;
не включать питания или reset через sysfs вручную.
