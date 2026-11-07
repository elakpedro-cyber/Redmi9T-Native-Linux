> Отчёт подготовки до аппаратного испытания. Текущий аппаратный результат: [V7_HARDWARE_RESULTS.md](V7_HARDWARE_RESULTS.md).

# v7 — Adreno 610

Дата: 2026-11-05. Экспериментальная подготовка, не аппаратное подтверждение GPU.

## Что обнаружено на телефоне

По SSH собраны `/sys/class/drm`, graphics, backlight, input, platform, I2C/SPI,
`/dev/dri`, dmesg, живой FDT и `/proc/config.gz`. Начальный срез:
`logs/v7-research/20261105T165437Z`; заключительный:
`logs/v7-research/20261105T174503Z`. Все команды сохранены в `commands.json`.

У работающей v6 есть только SimpleDRM/card0, framebuffer 1080×2340×32.
Render node отсутствует, DRM_MSM не собран, GPU firmware в RAM отсутствовала.
Наличие GPU-узла DT со status=okay не обеспечивало привязку драйвера.
Произвольные регистры, regulators, clocks и GPU reset не трогались.

## Upstream и исходники

Августовская серия Adam Skladowski дошла до **v5 от 21 августа 2026**;
v4 не является последней найденной ревизией. v5 декларирует GPU, USB, UFS,
кнопки и SimpleDRM; MDSS оставлен выключенным до поддержки панели.
[Патч v5 7/7](https://marc.info/?l=devicetree&m=178731515251507&w=1),
[полная серия](https://patchew.org/linux/20260821-next-patches-v5-0-ec81cee63e09%40gmail.com/).

Есть сообщение о принятии 1 октября и включение lemon в DT pull для 7.4:
[ответ сопровождающего](https://lists.openwall.net/linux-kernel/2026/10/01/1795),
[pull 7.4](https://lists.openwall.net/linux-kernel/2026/10/22/700).
В используемом дереве Linux 7.4-rc1 файл уже существует: заново применять
августовскую серию не нужно. Основа сохранена:
`linux-05441d697f7f9a927264f4058cbbc6a03dfcac9d`.

Существенные исходники: `arch/arm64/boot/dts/qcom/sm6115{,-xiaomi-lemon}.dts*`,
`drivers/gpu/drm/msm/adreno/{a6xx_catalog.c,a6xx_gpu.c,a6xx_gmu.c,adreno_gpu.c}`,
`drivers/clk/qcom/gpucc-sm6115.c`, ARM SMMU Qualcomm и `drivers/soc/qcom/mdt_loader.c`.
Выдержки сохранены в `reports/v7-gpu-source-excerpts.txt`.

## Аппаратная цепочка

| Часть | Конкретное описание в используемом DT/драйвере |
|---|---|
| GPU | qcom,adreno-610.0 / qcom,adreno; chip ID 0x06010000 |
| MMIO | 0x05900000/0x40000, CX 0x0599e000/0x1000, debug 0x05961000/0x800 |
| IRQ | GIC SPI 177, level high |
| Clocks | GPU_CC_GX_GFX3D, GPU_CC_AHB, GCC_BIMC_GPU_AXI, GCC_GPU_MEMNOC_GFX, GPU_CC_CX_GMU, GPU_CC_CXO |
| Power | RPM SM6115_VDDCX; GMU-wrapper domains GPUCC CX/GX |
| GMU | wrapper@0x596a000; полноценной отдельной GMU у A610 нет |
| IOMMU | Adreno SMMU@0x59a0000, iommus stream 0 / mask 1 |
| OPP | 320–980 MHz; speed-bin masks ограничивают допустимый набор |
| Speed bin | nvmem gpu_speed_bin; драйвер содержит таблицу именно Bengal |
| ZAP RAM | pil_gpu_mem 0xfa400000, 8192 байта, no-map |

Не менялись частоты, напряжения, speed-bin masks и sequence upstream-драйвера.
Успешность runtime-PM, SMMU translation и SCM/PAS требует аппаратного испытания.
Предупреждение старого [патча A610](https://www.mail-archive.com/freedreno%40lists.freedesktop.org/msg25391.html)
о специфике reset — дополнительная причина не экспериментировать с reset через sysfs.

## Прошивки: найден источник именно на этом устройстве

Чтение modem/sde52 не нашло GPU firmware. Затем **без монтирования** прочитана
LP metadata super/sda10: проверены SHA256 geometry, header и tables.
Две metadata-копии описывают разные extents, их нельзя путать с A/B телефона.
Vendor по metadata slot0 не содержит пригодного filesystem; slot1 содержит
читаемый ext4. Это не доказывает, какая metadata-копия была бы выбрана Android.
Устройство работает без Android, поэтому обе карты рассматривались только как
источники данных для офлайн-разбора. Они не изменялись и не активировались.

Из `/firmware` vendor-slot1 извлечены через **debugfs без -w**, на ПК:

| Файл | Байты | SHA-256 |
|---|---:|---|
| a630_sqe.fw | 32264 | 57eece0d8032b0ab2467d856c304ce22f502ae8d4b2f8169b9d1ca890ceb463c |
| a610_zap.mdt | 6860 | 75e47ff4eed9bc862ade8634df221493064d4bc3b8041db07893c070f7d5d4f5 |
| a610_zap.b00 | 148 | 422ed7993d7cd924ba3200b1acd18c120b0a40f4357b55362eddcbe4a0c8e019 |
| a610_zap.b01 | 6712 | 3372c6d06398460ca3ccd0f9f06fdbde0644947f2c0a125ccdd24c0b459cba96 |
| a610_zap.b02 | 2096 | 84c657996f3ec60a90d0c7223faad9b0700074fe00dc55596e0d3ba69b914d33 |

Полный ELF тоже сохранён для сравнения. MDT содержит согласованные header/hash;
PT_LOAD flags=0x08000007 означают **relocatable**, paddr=0x5000 — не адрес
записи в физическую RAM. Расчёт loader даёт 4096 байт, что помещается в 8192.
Метаданные и сегменты сверены с ELF. Подпись **не признана проверенной**:
SCM/PAS должен принять её на реальном телефоне. Версия SQE также требует
runtime-проверки с этим ядром.

В v7 ZAP находится в `lib/firmware/qcom/sm6115/xiaomi/lemon/`, SQE —
`lib/firmware/qcom/a630_sqe.fw`. Единственное изменение native DT — явный
firmware-name у zap-shader. Никаких патчей подписи/secure world не сделано.

Это извлечение из принадлежащего пользователю устройства для его локального
испытания; оно не даёт автоматически права распространять vendor blobs.
Полные modem/vendor readbacks остаются в `downloads/v7-personal`, вне
компактных поставок проекта. Для свободно распространяемой SQE есть
[linux-firmware WHENCE](https://gitlab.com/kernel-firmware/linux-firmware/-/raw/main/WHENCE)
и лицензия Qualcomm; ZAP другой платы qrb4210 не подставляется вместо lemon.

## Сборка v7 и разделение этапов

`CONFIG_DRM_MSM=m`, MODULES=y; MSM MDP4/MDP5/DPU выключены, DSI не включён.
Все встроенные возможности v6 сохранены. `Image` занимает 31844864 байта;
проверяется также image_size с BSS <=32 MiB. Перенос DTB с 0x82000000 не нужен.
Модули и firmware включены в компактный boot.img; `msm` внесён в blacklist
автозагрузки. Для headless bind задан `options msm separate_gpu_kms=1`:
автоматический выбор при одном GPU и выключенном MDSS иначе оставляет GPU
component без отдельного DRM master. Init/OpenRC не запускают modprobe,
mdev, udev или GPU-тест.
Явный `modprobe msm` возможен только на отдельно разрешённом этапе.

Прямое включение GPU в init сделало бы первую проверку сразу проверкой питания
GPU. В v7 сначала проверяются базовая загрузка и USB, затем отдельно GPU.

Mesa 26.1.6, EGL/GLES/GBM/libdrm и evtest собраны в **gpu-userspace-v7.tar.gz**.
Контрольная упаковка полной graphics build-root дала initramfs 101955561 байт
(с оставшимися dev headers); его размещение ABL конфликтовало бы с wrapper
в RAM. Поэтому boot содержит
минимальную Alpine, а Mesa передаётся после загрузки по SSH в `/tmp` и
распаковывается в RAM rootfs. Layout, bootshim и память не обходят проверками.

Freedreno поддерживает семейство Adreno 6xx в исходном коде:
[официальная документация Mesa](https://docs.mesa3d.org/drivers/freedreno.html).
Это не сертификат работы A610 именно на этом телефоне.

## Доказательство реального рендеринга

`userspace/gpu-render-v7.c` и ARM64 `artifacts/gpu-render-v7`:

1. Открывает только указанный renderD*, проверяет DRM driver=msm.
2. Создаёт GBM/EGL GLES2 surfaceless context и RGBA texture/FBO 16×16 без
   KMS/modeset и панели. Не требует PBUFFER_BIT, которого GBM может не предоставлять.
3. Требует renderer с 610, исключает llvmpipe/softpipe.
4. Компилирует shaders, рисует треугольник, ждёт завершения и читает 256 RGBA
   пикселей. Каждый канал сверяется с 64/128/191/255 с допуском 1.
5. Сохраняет результат только в `/tmp/gpu-render-v7.rgba` для SHA-256.

Офлайн проверены сборка, ARM64 dependencies и отказ при отсутствии render node.
**GPU workload на телефоне не запускался.** Аппаратный успех требует одновременно
renderer, корректных пикселей, отсутствия GPU/SMMU faults и живых SSH+ACM.
Weston пока не включён: сначала headless GPU, затем безопасный KMS/panel port.
