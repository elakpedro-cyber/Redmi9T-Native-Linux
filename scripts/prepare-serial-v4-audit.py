from pathlib import Path
root=Path(__file__).resolve().parents[1]
t=(root/'scripts/serial-readonly-v3.py').read_text()
a=t.index('groups={');b=t.index("group=sys.argv",a)
t=t[:a]+'''groups={'audit':[
('identity','uname -a; cat /run/init-reached; cat /sys/firmware/devicetree/base/chosen/xiaomi,bootshim-info; cat /proc/uptime; cat /proc/mounts'),
('storage','cat /proc/partitions; ls -l /sys/class/scsi_host /sys/class/scsi_disk; readlink /sys/bus/platform/devices/4804000.ufshc/driver; readlink /sys/bus/platform/devices/4807000.phy/driver; for d in /sys/block/sd*; do echo "$d"; cat "$d/device/vendor" "$d/device/model" "$d/device/rev" "$d/size" "$d/queue/logical_block_size" "$d/queue/physical_block_size" "$d/ro" "$d/stat" "$d/device/ioerr_cnt" "$d/device/state"; done'),
('dmesg-before','dmesg'),
('graphics-input','cat /proc/fb; ls -l /dev/dri /sys/class/drm; cat /proc/bus/input/devices; ls -l /sys/class/input; for p in /sys/firmware/devicetree/base/soc@0/gpu@5000000 /sys/firmware/devicetree/base/soc@0/display-subsystem@5e00000; do echo "$p"; cat "$p/compatible" "$p/status"; done'),
('reads-a','for d in sda sdb sdc sdd sde sdf; do echo "BEGIN_READ_$d"; head -c 16384 /dev/$d | base64; echo "END_READ_$d"; done'),
('interval','sleep 20; cat /proc/uptime'),
('reads-b','for d in sda sdb sdc sdd sde sdf; do echo "BEGIN_READ_$d"; head -c 16384 /dev/$d | base64; echo "END_READ_$d"; done'),
('storage-after','for d in /sys/block/sd*; do echo "$d"; cat "$d/stat" "$d/device/ioerr_cnt" "$d/device/state"; done; dmesg'),
]}
''' +t[b:]
t=t.replace("else 'initial'","else 'audit'").replace("logs/v3-live-diagnostics","logs/v4-live-diagnostics")
(root/'scripts/serial-readonly-v4.py').write_text(t,encoding='utf-8',newline='\n')
