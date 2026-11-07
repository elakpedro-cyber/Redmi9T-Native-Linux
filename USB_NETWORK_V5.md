# USB-сеть и SSH: подготовлено, на устройстве не испытано

Базовый v5 оставляет **только ACM**, VID:PID 1d6b:0104. На текущем телефоне USB
конфигурация не менялась. Сеть и SSH не считаются работающими.

Ядро v5 включает NET/UNIX/INET/PACKET и configfs ECM/NCM/RNDIS встроенно;
ACM/DWC3/PHY и все остальные v4 builtins сохранены. CONFIG_DIFF_V4_V5.md содержит
полный diff. Изменения нужны также для нормальных Unix/IP sockets пользовательской среды.

Исходники протоколов проверены в drivers/usb/gadget/Kconfig и functions/.
ECM обычно подходит Linux-хосту; для Windows следует отдельно проверить NCM или
RNDIS и доступный драйвер конкретной версии ОС. Наличие функции в ядре не
доказывает host enumeration, драйвер Windows, передачу пакетов или сохранение ACM.
Официальная механика: [Linux configfs gadget](https://docs.kernel.org/usb/gadget_configfs.html).

## Отдельный будущий вариант, не первый тест v5

На ПК поменять config/usbnet-mode-v5 с off на ecm, ncm или rndis и пересобрать
initramfs/boot image в отдельный файл, сохранив базовый ACM-only образ. Потребуются
новые hash, проверки размещения initrd и отдельное разрешение на тест.
Не делать unbind/rebind UDC через действующую COM-консоль.

Выбор происходит до единственного bind. ACM сохраняется первым; добавляется
сетевой function, VID:PID становится 1d6b:0105, класс composite EF/02/01.
Device MAC 02:00:00:00:77:02, host MAC 02:00:00:00:77:01.
Device IPv4 192.168.77.2/30; хосту потребуется 192.168.77.1/30 без gateway/DNS.
Маршрутизация, DHCP, NAT и доступ в интернет автоматически не настраиваются.
RNDIS OS descriptors/драйвер Windows специально не обходились; при отсутствии
enumeration сначала собрать логи с host, не менять VID/драйвер вслепую.

Bootshim сохраняет жёстко заданную bootargs v3, поэтому просто добавить параметр
к Android header cmdline недостаточно. Рабочая точка выбора в этой реализации —
файл /etc/lemon/usbnet-mode внутри будущего initramfs. В базовом образе он off.

После отдельного успешного теста сети: подтвердить ACM shell, ip link/address,
ping в обе стороны и передачу файла с одинаковым SHA. Пока эти тесты не выполнены.

## SSH

Dropbear установлен, но не запущен и не включён в runlevel. В образе нет общих
host private keys, пароля SSH или authorized public keys. После проверки сети
можно передать свой публичный ключ через COM в /root/.ssh/authorized_keys (RAM),
права700 каталогу и600 файлу, и отдельно запустить:

```sh
dropbear -R -E -s -p 22
```

Это будущая операция в RAM, не выполненная сейчас. -s запрещает password login,
-R создаёт необходимые host keys в RAM. Подтвердить fingerprint по COM перед SSH.
Ключи и изменения пропадут после reboot. Нельзя заявлять рабочий SSH только на
основании наличия executable или появления USB NIC.
