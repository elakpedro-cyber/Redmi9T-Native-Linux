# Подготовка первого аппаратного теста Alpine v5

Телефон оставлен в Linux v4. В этой подготовке не было reboot, flash, записи
разделов, sysfs/debugfs, включения сети или переключения UDC.

## Свежая контрольная диагностика v4

Через COM3/115200 собраны uname, /init marker, bootshim trace, mounts/swaps,
UFS/PHY driver links, partitions, SCSI, framebuffer, USB state и два dmesg.
Два набора block counters разделены 15 секундами. COM3 закрыт после сбора;
чужие процессы не завершались.

Логи: logs/first-test-v4/20261105T151623Z*, включая raw transcript и список команд.
Оценка: reports/first-test-v4-assessment.json — PASS_OBSERVED_CHECKS.
Подтверждены v4, marker V4, шесть LUN и разделы, UDC configured, только виртуальные
mounts и пустой /proc/swaps. На всех LUN writes_completed/sectors_written равны0
до и после, ioerr_cnt=3 без роста. Это отсутствие наблюдаемых OS block writes
в данных снимках, а не гарантия отсутствия любых внутренних firmware записей.

Рабочий возврат: artifacts/boot-linux-test-v4.img, 9576448 байт,
SHA256 4cf10f2a9c6d7298e46aec7afdcc64421b532705d29bbbf7b703ae2c90bffa45.
Контрольные snapshots/v4-known-good и v4-live-supplement не менялись.

## Усиление аварийной shell

USB gadget и цикл /rescue/getty запускаются отдельным процессом из /init **до**
exec Alpine /sbin/init. От OpenRC сервисов USB не зависит. Ранее login helper
использовал Alpine /bin/ash и динамический loader. Теперь и его shebang, и
интерактивная shell — статический BusyBox v4 из /rescue; /etc/profile не читается.
Баннер: `USB_RESCUE_SHELL_V5`. Команды Alpine доступны по обычному PATH.
Для обычного Alpine ash после проверки библиотек можно вручную выполнить /bin/ash -l.

На ПК в отдельном QEMU-user/chroot, без /bin/sh и Alpine libraries, проверены:

| Сценарий | Результат |
|---|---|
| OpenRC отсутствует | Static shell принимает и выполняет команду |
| OpenRC завершился с кодом1 | Static shell принимает и выполняет команду |
| OpenRC завис | Параллельная static shell принимает и выполняет команду |

Доказательства: scripts/test-usb-rescue-v5.py и reports/v5-rescue-failure-tests.json.
Это тест зависимостей shell на ПК, не эмуляция USB/getty или полного PID1 boot.
На телефоне доступ всё равно требует работающих ядра, UDC и ACM. Panic/отказ USB
невозможно исправить shell, которая недоступна; для этого сохранён TWRP/v4.

## Отсутствие автоматической установки на UFS

- /init монтирует только devtmpfs/proc/sysfs/tmpfs/devpts/configfs/pstore.
- Весь Alpine rootfs находится в initramfs; switch_root на диск отсутствует.
- Fstab пуст; OpenRC runlevels включают только lemon-health.
- Нет запуска localmount, fsck, swap, automount, partition tools или raw writes.
- USB gadget только ACM; сеть off, mass storage не создаётся, SSH не запускается.
- Начальные счётчики дисков и mounts/swaps сохраняются до OpenRC в
  /run/ufs-stat-initial.txt. Последующие логи пишутся в /run и /var/log в RAM.

Наличие утилит в rootfs не делает диск аппаратно read-only. Поэтому первый тест
ограничен командами чтения; не выполнять apk add, mount дисков, swap или ручной
bind/reset. Автоматическая проверка стартовых файлов включена в validate-v5.py.

## Образ и разрешённая граница

После изменения shell пересобраны initramfs/boot.img; ядро, bootshim и DTB не менялись.
Предыдущий v5 сохранён в snapshots/v5-before-first-test-prep.
Использовать **только текущий SHA** из FIRST_BOOT.md и reports/artifact-manifest-v5.json.
Манифест reports/v5-delivery-manifest.json относится к предыдущему v5; новый
комплект описан reports/v5-first-test-manifest.json.

Переход по FIRST_BOOT.md начинается только после отдельного разрешения:
закрыть COM-клиент, аппаратно войти в TWRP, проверить root/kernel/boot/recovery
by-name и размеры, recovery hash и префикс рабочего v4. Только затем push в /tmp,
проверка SHA и одна запись **только boot**, readback префикса и recovery hash.
После успешного readback — один согласованный normal boot. Нет автоматических
повторов, AVB обходов или записи других разделов. При ошибке записи оставаться
в TWRP; не reboot. Возврат v4 подробно описан в RECOVERY_PLAN.md.

## Автоматический сбор после будущей загрузки

Не запускать ожидающий v5 collector на текущем v4: он сохранит identity и остановится
из-за несовпадения версии. Во время разрешённого теста, когда телефон уже в TWRP,
закрыть другие serial-программы и запустить в отдельном PowerShell на ПК:

```powershell
Set-Location 'C:\Users\HadirPC\Downloads\platform-tools_r37.0.1-windows'
python .\Redmi9T-Native-Linux\scripts\collect-first-test.py --expect v5 --port COM3 --wait 120
```

Скрипт сам ничего не загружает и не перезагружает. Он ждёт отсутствующий COM-порт,
но при занятом порте сразу завершается без завершения чужих процессов.
Если Windows назначит другой COM, указать его явно. После появления root shell
собираются identity, Alpine/OpenRC/apk versions, PID1/processes/runlevel state,
начальные и текущие counters, mounts/swaps, разделы, drivers, dmesg и RAM logs.
Спустя15 секунд сохраняется второй снимок. Вывод идёт на ПК в logs/first-test-v5/.
Ошибки OpenRC/утилит сохраняются в логах, не препятствуя сбору остального.

После завершения:

```powershell
python .\Redmi9T-Native-Linux\scripts\analyze-first-test.py --version v5
```

Успех: kernel-v5, ранний marker V5, Alpine3.24.4, apk version, marker OpenRC,
runlevel default и started lemon-health, выполняемые через USB команды, шесть LUN
и разделы. Не должно быть swap, UFS mounts, ненулевых/растущих block write counters
или роста ioerr. Дополнительно вручную проверить early counters и весь dmesg:
автоматическая оценка не заменяет разбор ошибок и не объявляет успех по логотипу.

Если /init marker есть, но OpenRC marker отсутствует, результат — частичная загрузка.
Static COM-shell должна оставаться доступной при работоспособном USB; собрать
/var/log/rc.log, /run/usb-setup.log, ps и dmesg. Ничего не чинить на UFS.
Если USB недоступен, вернуться в TWRP в рамках согласованного восстановления,
сохранить pstore и вернуть v4. Retention RAM/pstore после reset не гарантирован.
