from pathlib import Path
root=Path(__file__).resolve().parents[1]
t=(root/'scripts/collect-first-test.py').read_text()
t=t.replace('Read-only v4/v5 serial diagnostics','Read-only v6 serial diagnostics')
t=t.replace("choices=['v4','v5']","choices=['v6']").replace("if args.expect=='v5':","if args.expect=='v6':")
t=t.replace("('startup-logs','cat /run/ufs-stat-initial.txt; cat /run/usb-setup.log; cat /run/lemon-diagnostics.log; cat /var/log/rc.log'),", "('startup-logs','cat /run/ufs-stat-initial.txt; cat /run/usb-setup.log; cat /run/lemon-diagnostics.log; cat /var/log/rc.log'),\n    ('network-ssh','/sbin/ip address show; /sbin/ip route show; cat /sys/class/net/usb0/address /sys/class/net/usb0/carrier; ls -l /run/openrc/started; cat /run/ssh-hostkey.txt /run/dropbear.log; ls -l /root/.ssh/authorized_keys; cat /sys/kernel/config/usb_gadget/lemon/UDC; ls -l /sys/kernel/config/usb_gadget/lemon/configs/c.1'),")
t=t.replace("('lemon-bringup-'+args.expect).encode()", "b'lemon-bringup-v5'")
t=t.replace("if name=='identity' and b'lemon-bringup-v5' not in output:", "if name=='identity' and (b'lemon-bringup-v5' not in output or b'LEMON_INIT_V6_REACHED' not in output):")
t=t.replace("('ufs-after',", "('network-ssh-after','/sbin/ip address show; /sbin/ip route show; cat /run/ssh-hostkey.txt /run/dropbear.log; ls -l /run/openrc/started'),\n('ufs-after',")
(root/'scripts/collect-v6.py').write_text(t,newline='\n')
