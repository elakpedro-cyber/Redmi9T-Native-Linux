> Историческая предварительная заметка после v6. Текущие результаты: V7_VALIDATION.md и V7_HARDWARE_MATRIX.md.

# План v7 после стабильного v6

Аппаратные работы ниже **не выполнялись**. Гейт Windows NCM/SSH/SCP + ACM пройден
на настоящем телефоне. Начато только офлайн-чтение сохранённых mainline-исходников:
Adreno610 firmware entries и DPU6.3 SM6115 подтверждены. V7 kernel не собирался,
rootfs телефона не менялся, драйверы не загружались. Полный результат v6 —
V6_HARDWARE_RESULTS.md; дальнейшие аппаратные действия требуют нового согласования.

## Гейт v6

Требуются реальный UsbNcm binding, адреса .77.1/.77.2, ping, key-only SSH,
uname/Alpine/OpenRC, SCP в tmpfs с совпавшим SHA, одновременно работающий ACM,
шесть UFS LUN без mounts/swap и ненулевых block write/discard counters.
Сохранить рабочий v6 image, rootfs, DTS/configs, SHA и логи Windows/COM/SSH.
Короткий тест не равен длительной стабильности: дополнительно согласовать более
длительную сессию с повторными SSH командами и контролем USB/UFS ошибок.

## 1. Read-only инвентаризация

Через стабильный SSH и резервный ACM собрать DRM/input/backlight sysfs, dmesg,
процессы, modules/config и live DTB. Сравнить с pinned source и последней доступной
mainline версией; изменения upstream проверять по первичным источникам после гейта.
Определить фактические binds: simpledrm, MSM, DPU/DSI/PHY и touch, различая
зарегистрированный platform device и успешно проброшенный драйвер.
Сверить clocks/regulators/reset/IOMMU/OPP и статус deferred probing чтением.
Не сканировать I2C и не писать GPIO/reset/clock/regulator/debugfs автоматически.

## 2. Идентификация панели и сенсора

Сначала искать фактический panel selection в сохранённых boot/DTBO/ABL/TWRP
логах, live chosen и доступных метаданных конкретного SKU. Все найденные panel
nodes считать кандидатами, пока не доказан выбранный вариант.
Если программных данных недостаточно, потребуется отдельное решение о безопасном
способе определения аппаратных ID; доступ к DSI/I2C может изменить состояние экрана
или сенсора и требует разрешения. Не подбирать драйвер случайным перебором.

Для установленного panel/touch составить схему supplies, GPIO, IRQ, reset timing,
DSI lanes/format/mode, backlight path и pinctrl. Точная модель сейчас неизвестна.

## 3. GPU отдельно от панели

Проверить pinned DRM/MSM Adreno610 и GMU-wrapper путь, firmware names/availability,
speedbin nvmem, OPP, SMMU и питания. Пользоваться mainline драйверами и DT bindings;
не заменять проверенное ядро случайным downstream GPU кодом.
Подготовить отдельную ветку kernel config с MSM и необходимыми зависимостями,
сохранить simpledrm/NCM/ACM/UFS. Сначала compile, DT/schema, phandle checks и
bootshim emulation; аппаратный kernel test — только по отдельному разрешению.

**Проверить адресное окно:** текущий Image memory_size31522816; DTB по0x82000000,
окно ядра от0x80000000 —33554432 байта, запас2031616. DRM/MSM может не поместиться.
Не отключать guards или рабочие подсистемы ради размера. При превышении лимита
сначала отдельный аудит новой RAM раскладки/reservations/initrd/PoC, затем новый
bootshim и эмуляции. Самовольное перемещение DTB исключено.

После разрешённого теста GPU подтвердить bound MSM и render node, отсутствие
IOMMU/firmware faults; затем добавить минимальный Mesa Freedreno в RAM rootfs.
Проверить реальный renderer/EGL/GLES, не принимая llvmpipe/software за Adreno.
Наличие GPU render node ещё не подтверждает native DSI scanout.

## 4. Native display/backlight

Только после точной идентификации panel и проверки bindings подготовить отдельный
DT patch для MDSS/DPU/DSI/PHY/panel/backlight. Проверить regulator voltage limits,
clock/reset dependencies, modes и reserved framebuffer. Сохранить рабочий образ
с firmware framebuffer как возврат. Изменения, способные погасить дисплей,
испытывать отдельно с уже работающими SSH и ACM, после разрешения.
Критерий — нативный DRM driver, connector/modes, корректный modeset/scanout и
управление подсветкой, а не прежняя картинка ABL.

## 5. Touch и Wayland

После установления модели touch включить только подходящий mainline driver/DT,
проверить IRQ и evdev events, диапазоны координат/ориентацию и кнопки. Event node
без событий не считать работой сенсора.
Собрать минимальный Weston в отдельной RAM rootfs. Можно сначала проверить
программный вывод через SimpleDRM, явно пометив отсутствие GPU ускорения.
Полноценный этап — Weston на native DRM с аппаратным renderer, проверенными
touch coordinates и стабильным управлением. Headless Weston не доказывает
дисплей; SimpleDRM/Pixman не доказывает ускорение.

Каждый шаг оформлять отдельными source/config/DT diffs, image SHA, offline logs,
матрицей «исходник / сборка / реальное устройство» и известным откатом v6.
Rootfs/firmware/runtime keys остаются в RAM; установки на UFS этот план не включает.
