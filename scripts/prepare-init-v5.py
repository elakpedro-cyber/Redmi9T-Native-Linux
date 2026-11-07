from pathlib import Path
root=Path(__file__).resolve().parents[1]
t=(root/'config/init-v4').read_text()
t=t.replace('#!/bin/sh','#!/rescue/busybox sh',1)
t=t.replace('export PATH=/bin:/sbin','export PATH=/rescue:/sbin:/bin:/usr/sbin:/usr/bin')
t=t.replace('LEMON_INIT_V4_REACHED','LEMON_INIT_V5_REACHED')
t=t.replace('mount -t devpts devpts /dev/pts', '''mount -t devpts devpts /dev/pts
{
    for d in /sys/block/sd*; do
        echo "$d"
        cat "$d/stat" "$d/device/ioerr_cnt"
    done
    cat /proc/mounts /proc/swaps
} > /run/ufs-stat-initial.txt''')
t=t.replace('    n=0\n', '''    # Optional composite mode is selected before binding; default remains ACM-only.
    usbnet=$(cat /etc/lemon/usbnet-mode 2>/dev/null)
    for arg in $(cat /proc/cmdline); do
        case "$arg" in lemon.usbnet=*) usbnet=${arg#lemon.usbnet=} ;; esac
    done
    case "$usbnet" in
        ecm|ncm|rndis)
            if mkdir -p "functions/$usbnet.usb0"; then
                echo 0x0105 > idProduct
                echo 0xef > bDeviceClass
                echo 0x02 > bDeviceSubClass
                echo 0x01 > bDeviceProtocol
                echo 02:00:00:00:77:02 > "functions/$usbnet.usb0/dev_addr"
                echo 02:00:00:00:77:01 > "functions/$usbnet.usb0/host_addr"
                ln -s "functions/$usbnet.usb0" "configs/c.1/$usbnet.usb0"
            else
                echo "Optional USB $usbnet unavailable; retaining ACM" > /dev/kmsg
                usbnet=
            fi
            ;;
        *) usbnet= ;;
    esac
    n=0
''')
t=t.replace('    dmesg > /run/boot-dmesg.txt', '''    if [ -n "$usbnet" ]; then
        /sbin/ip address add 192.168.77.2/30 dev usb0
        /sbin/ip link set usb0 up
    fi
    dmesg > /run/boot-dmesg.txt''')
t=t.replace('/bin/getty -L -n -l /bin/sh','/rescue/getty -L -n -l /usr/local/sbin/lemon-root-shell')
t=t.replace('/sbin/ufs-diagnostics >/run/ufs-diagnostics.log 2>&1 &','')
start=t.index("echo 'RAM-only system.")
t=t[:start]+'''export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
echo 'Starting Alpine BusyBox init and OpenRC in RAM'
exec /sbin/init
'''
(root/'config/init-v5').write_text(t,newline='\n')
