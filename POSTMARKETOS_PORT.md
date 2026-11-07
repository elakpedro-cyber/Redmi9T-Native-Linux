# Начальный порт postmarketOS / Alpine v5

Собранная среда — **Alpine Linux 3.24.4 aarch64 с OpenRC в RAM**.
Это первый этап порта: пакет postmarketos-base, штатный postmarketos-mkinitfs и UI
в образ не включены. Нельзя считать этот образ завершённой сборкой postmarketOS
или официально поддержанным портом lemon.

## Изученная инфраструктура

Официальные источники:

- [pmbootstrap: установка и ограничения WSL](https://docs.postmarketos.org/pmbootstrap/installation.html)
- [pmbootstrap: назначение](https://docs.postmarketos.org/pmbootstrap/)
- [pmaports](https://gitlab.postmarketos.org/postmarketOS/pmaports)
- [deviceinfo_schema.toml](https://gitlab.postmarketos.org/postmarketOS/pmaports/-/blob/main/deviceinfo_schema.toml)
- [Alpine: OpenRC и порядок runlevels](https://wiki.alpinelinux.org/wiki/OpenRC)
- [Alpine ARM64 release metadata](https://dl-cdn.alpinelinux.org/alpine/v3.24/releases/aarch64/latest-releases.yaml)

Официальные Git URLs при клонировании перенаправились на gitlab.nura.eco;
редирект и исходные URL сохранены в reports/v5-infrastructure-download.log.
Ничего не переименовывалось по предположению. Использованы полученные официальные
исходники, а не сторонний device fork:

| Инструмент | Версия / commit |
|---|---|
| pmbootstrap | 3.12.1 / e0dfe2cda7f3a0b70cdcc96f3060100839322aa4 |
| pmaports | c3a9afb479a904663460792ac186b23274c33d7f |
| deviceinfo schema | 0.1 |
| Linux | 7.4-rc1 / 05441d697f7f9a927264f4058cbbc6a03dfcac9d |

Pmbootstrap создаёт Alpine chroots, разрешает зависимости pmaports и собирает APK.
Device package предоставляет метаданные/настройки, kernel package — ядро/DTB;
postmarketos-mkinitfs затем собирает загрузочные компоненты.
`pmbootstrap install` без физического target создаёт локальную rootfs, а flasher,
sideload и target disk options относятся к отдельным операциям записи.
В этой работе pmbootstrap install/flasher/sideload не запускались.

## Подготовленные aports

`pmaports/device/testing/device-xiaomi-lemon/`: APKBUILD, deviceinfo, kernel-cmdline.conf.
`pmaports/device/testing/linux-xiaomi-lemon/`: pinned source APKBUILD,
config-xiaomi-lemon.aarch64 и полный lemon-runtime.dts проверенного DTB v4.
Рецепт ядра использует mainline, не Android kernel. SHA-512 источников записаны.

Deviceinfo: aarch64, handset, DTB qcom/sm6115-xiaomi-lemon, сектор4096,
DRM=true означает только наличие DRM API (SimpleDRM), не GPU acceleration.
flash_method=none и generate_bootimg=false оставлены намеренно: обычный pmOS
bootimg с непосредственным mainline DTB несовместим со stock DTBO. Нужен существующий
переходник с двумя DTB и внешний scripts/package-v5.py. Поля firmware/vbmeta/rootfs
flash targets не добавлены.

Формат проверен по настоящей схеме, Deviceinfo разобран настоящим parser
pmbootstrap; изолирован только lookup вариантов ядра, которых в этом пакете нет.
Штатные devicepkg_build.sh/devicepkg_package.sh успешно создали staging metadata.
Результат — reports/pmaports-v5-check.json. Подписанные APK этих двух локальных
пакетов не собирались, pmbootstrap integration build ещё не выполнен.
В rootfs установлены их deviceinfo metadata, а не фиктивная запись в apk DB.

Для завершения порта нужны интеграция dual-DTB bootshim в mkinitfs hooks,
пакетирование/сборка через pmbootstrap и отдельные аппаратные испытания. Текущие
системные APK настоящие и установлены штатным apk из подписанных Alpine репозиториев.

## RAM rootfs и сборка

Исходный minirootfs проверен по опубликованному SHA-256. Добавлены alpine-base,
OpenRC, iproute2/iputils, lsblk, blkid, strace, curl/CA и Dropbear.
Полные версии: config/rootfs-v5-packages.lock и reports/rootfs-v5-apk-installed.txt.
Первичная ARM64 apk установка под QEMU-user не сохранила права двух privileged
файлов. Оба пакета переустановлены native x86_64 apk.static с --arch aarch64;
успех записан в rootfs-v5-native-repair.log. Скрипт сборки исправлен на native apk.

В WSL из каталога проекта, root только для rootfs/mknod/chroot:

```sh
bash scripts/build-kernel-v5.sh
sudo bash scripts/build-rootfs-v5.sh
python3 scripts/prepare-init-v5.py
sudo bash scripts/configure-rootfs-v5.sh
bash scripts/build-shim-v5.sh
```

Rootfs создаётся в отдельном WSL rootfs-v5/root; скрипт отказывается заменять
существующее дерево. Для уже подготовленного дерева повторяется только configure.
Версии apk зафиксированы отчётом; повторная online установка из v3.24 со временем
может выбрать обновления. Побайтовая воспроизводимость между версиями gcc/zlib/apk
не заявляется; зафиксированы SHA готовых файлов.

`/init` использует статический rescue BusyBox v4, сохраняет его ACM gadget и getty,
монтирует только виртуальные FS и передаёт PID1 Alpine /sbin/init. Затем inittab
запускает OpenRC sysinit → boot → default. Единственный включённый сервис —
lemon-health: marker и диагностика в /run. Fstab пуст; localmount, swap, fsck,
hwclock, automount, сетевые службы и SSH автоматически не запускаются.

Корень initramfs, /run, /tmp и /var/log находятся в RAM; UFS не является rootfs.
Изменения и установленное через apk ПО пропадают после выключения.
Артефакты: initramfs-v5.cpio.gz и alpine-rootfs-v5.tar.gz.
Образ помещается в boot; альтернативная архитектура сейчас не нужна. Если будущая
GUI rootfs превысит лимит, сначала использовать отдельную RAM rootfs с передачей
по проверенной сети или внешний носитель после нового согласования, без записи UFS.
