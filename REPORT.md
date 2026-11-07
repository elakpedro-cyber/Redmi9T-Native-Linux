# Исследование и границы проверки

Исторический отчёт v1. Продолжение с разбором конкретных блокеров и экспериментальным образом v2: `DTBO_COMPATIBILITY.md`, `BOOTLOADER_RESEARCH.md`, `FIRST_BOOT.md`, `RECOVERY_PLAN.md`, `STATUS.md`.

Дата: 5 ноября 2026. Устройство подтверждено через работающий root ADB в TWRP: Redmi_9T_NFC, lemon, 4 GiB RAM; текущий recovery kernel — 4.19.252. Перезагрузок и записей разделов не выполнялось.

## Device Tree и исходники

Последняя найденная версия августовской серии Adam Skladowski — [v5 от 21 августа](https://patchew.org/linux/20260821-next-patches-v5-0-ec81cee63e09@gmail.com/). [Bjorn Andersson сообщил о принятии 1 октября](https://lists.openwall.net/linux-kernel/2026/10/01/1795): коммит lemon `76fbf547548ccd1a650c096836d8cf01f3ce3ce6`. Текст коммита сохранён в `reports/lemon-upstream.patch`.

DTS присутствует [в mainline дереве Torvalds](https://github.com/torvalds/linux/blob/05441d697f7f9a927264f4058cbbc6a03dfcac9d/arch/arm64/boot/dts/qcom/sm6115-xiaomi-lemon.dts). Для сборки выбрана зафиксированная ревизия `05441d697f7f9a927264f4058cbbc6a03dfcac9d`, версия 7.4-rc1; патч не переносился на старое ядро. Это development/RC версия, выбранная ради уже включённого lemon. Более поздний, ещё обсуждаемый рефакторинг общих DTS Poco M3/lime не используется.

Upstream описывает simple framebuffer, GPU, питание, кнопки, UFS/SD, USB и сопроцессоры. Это заявленные возможности порта, а не результаты теста нашего образа. Драйвер панели и варианты подсветки не завершены; backlight в DTS отключён. Поддержка NFC из названия телефона не следует: NFC, Wi-Fi, звук и мобильная связь здесь не реализуются.

Использован ARM64 defconfig с отключением остальных платформ и модульных драйверов, затем применён `config/bringup.fragment`. Все необходимые для начального запуска драйверы встроены: Qualcomm clock/pinctrl/SPMI/RPM/interconnect, QUSB2/QMP USB PHY, DWC3, configfs ACM, simpledrm, devtmpfs, gzip initrd, pstore/ramoops. Накопители, сеть и загрузка ADSP/CDSP/MPSS отключены. Rootfs работает в памяти; proprietary firmware не добавлялась.

Upstream DTB сохранён отдельно. В копию для boot image добавлены `qcom,msm-id` и `qcom,board-id` из live DTB телефона. В ней принудительно задан `dr_mode=peripheral` и удалён `usb-role-switch`, чтобы первый эксперимент не зависел от переключения роли Type-C. Это экспериментальная настройка USB, а не подтверждённое решение. AVB не изменялся.

## Сохранённый boot.img

Анализ выполнен неизменённым [AOSP unpack_bootimg.py](https://android.googlesource.com/platform/system/tools/mkbootimg/+/refs/heads/main/unpack_bootimg.py). Полный вывод: `reports/boot-header.txt`, воспроизводимые аргументы: `reports/boot-mkbootimg.txt`.

| Поле | Значение |
|---|---|
| Размер резервной копии раздела | 134217728 байт |
| Magic / header | ANDROID! / v2 |
| Header size / page size | 1660 / 4096 |
| Kernel payload | 13033162 байта, gzip |
| Распакованный ARM64 Image | 29358592 байта, ARM64 magic корректен |
| Ramdisk | 1057620 байт |
| Second / recovery DTBO | отсутствуют |
| DTB | отдельное поле, 302880 байт, один FDT |
| Kernel / ramdisk address в header | 0x00008000 / 0x01000000 |
| Tags / DTB address в header | 0x00000100 / 0x01f00000 |
| OS metadata | 11.0.0 / 2023-03 |

В тестовом образе воспроизведён именно этот layout: gzip kernel, gzip newc initramfs, отдельный DTB, header v2, page 4096. `--base 0` служит для точного воспроизведения полей адресов; настоящий исторический параметр base из header восстановить нельзя. DTB к ядру не приписывается. Stock dtbo.img не изменяется и не включается вслепую.

Офлайн-проверка AVB: в последних 64 байтах boot.img нет footer AVBf; у recovery.img он есть (embedded vbmeta 2432 байта). В сохранённом vbmeta.img flags=0, algorithm_type=1 (SHA256_RSA2048). Это не проверка подписи или цепочки доверия. В тестовый образ footer/подпись не добавлялись; принятие образа загрузчиком не подтверждено. Исходные AVB-файлы и флаги не менялись. Поля сохранены в `reports/avb-readonly.json`.

Эти адреса — значения header, не доказанные физические адреса размещения mainline. В текущем TWRP `/proc/iomem` показывает kernel code по 0x40080000, live DT — initrd 0x43c34000..0x456fea7f. Загрузчик выполняет собственное размещение. Для mainline действительный результат требует теста.

У текущего recovery тоже header v2 и те же адресные поля, но ядро/ramdisk другие, есть встроенный recovery DTBO 233654 байта, DTB 303431 байт. Поля OS 127.0.0/2099-12 принадлежат сохранённому recovery и не копируются в тестовый Linux образ.

Старая строка cmdline содержит downstream ttyMSM0 и GENI earlycon; причём boot и recovery расходятся в адресе UART. Она не переносилась: для mainline использованы `rdinit=/init console=tty0`, подробный printk и сохранение включённых clocks/power domains. Непроверенный адрес UART не назначался. Полный cmdline — `config/cmdline.txt`.

## Загрузчик, DTBO и временная загрузка

Из телефона только прочитан раздел ABL, затем офлайн извлечён его UEFI PE-образ. Его fastboot-таблица имеет 26 строк с обработчиками по адресам 0xbce28..0xbcfb8; среди них нет `boot`. Таблица сохранена в `reports/abl-command-table.txt`. По этому статическому свидетельству временная загрузка, вероятно, отключена в установленной сборке. Сам телефон в fastboot не переводился; окончательного протокольного подтверждения нет.

В ABL также есть путь выбора DTB, применения DTBO и сообщение об exact match, при котором поиск DTBO не нужен. Наличие этой строки не доказывает, что наш DTB попадёт именно в этот путь. Плата из live DT имеет `qcom,board-id=<0x22 0>`, stock base DTB — `<0 0>`. Экспериментальная копия использует идентификаторы устройства, но алгоритм выбора полностью не восстановлен.

`scripts/check-dtbo.py` извлекает сохранённые DTBO и отдельно пробует overlay #0, выбранный текущим recovery, на stock base и на mainline. Результат в `reports/dtbo-compatibility.json` необходимо учитывать перед тестом. Даже успех libfdt не гарантирует совместимость семантики vendor overlay с mainline. При ошибке нельзя автоматически стирать DTBO или менять ABL/AVB.

Получен конкретный результат: в dtbo.img один overlay; на stock base он применяется успешно, на mainline — `FDT_ERR_NOTFOUND`. Поэтому тест Linux заблокирован до выяснения, пропустит ли ABL overlay при точном выборе полного DTB, либо до разработки отдельно согласованного решения. Образ имеет корректную структуру, но не объявляется совместимым с установленным bootloader/DTBO.

Загрузка без записи пока не подтверждена. План остановки и альтернативы: `BOOT.md`. Никаких boot/flash/erase команд на устройстве при подготовке не выполнялось.

## USB и журнал

В DTS контроллер USB, QUSB2 и QMP PHY включены, максимальная скорость high-speed. BusyBox init пытается создать gadget ACM через configfs и запустить shell на ttyGS0. На ПК требуется проверить новое USB-устройство и реально получить вывод. USB networking не настроен; работающий ADB TWRP не считается проверкой mainline.

Текущий upstream framebuffer расположен по 0x5c000000, размер 1080×2340×4; simpledrm опирается на состояние дисплея, оставленное загрузчиком. Настоящего панельного драйвера в этом эксперименте нет. Отсутствие картинки возможно даже при работающем ядре.

Для раннего сбоя доступны только предполагаемый ramoops и дальнейшее аппаратное исследование UART. Совпадение конфигурации pstore recovery и сохранность RAM после reset пока не подтверждены.

## Офлайн-проверки

Проверяются: ARM64 Image header и gzip, статический ARM64 ELF BusyBox и выполнение под qemu-user, синтаксис init целевой оболочкой, newc cpio и `/dev/console`, DTB и идентификаторы, размер образа меньше 128 MiB, повторная распаковка AOSP с побайтовым сравнением всех payload, фактические kernel config зависимости и исходные SHA-256 резервных копий.

Это не эмуляция SM6115 и не проверка запуска ядра. Итоговые результаты и размеры нужно читать в `reports/offline-validation.json`, `reports/artifact-manifest.json` и `reports/final-checks.txt`. Готовность к загрузке, дисплей, USB и поведение AVB остаются непроверенными на устройстве.

Итог: Linux `7.4.0-rc1-lemon-bringup`; Image.gz 8469072 байта, initramfs 573526 байт, upstream DTB 62956 байт, boot DTB 63050 байт, тестовый boot image 9117696 байт. AOSP round-trip сохранил все payload побайтово. BusyBox статический ARM64, выполняется под qemu-user, init проверен его ash, `/dev/console` имеет major:minor 5:1. SHA-256 всех четырёх исходных резервных копий до и после работы совпали. Телефон остался в recovery.

В собранном Image ARM64 `text_offset=0`, `image_size=28311552`; файл занимает 27693568 байт. Это нормальные отдельные поля (image_size включает область памяти), но соответствие размещению старого ABL не проверено. Header адрес 0x8000 не подменяет требований ARM64 boot protocol.
