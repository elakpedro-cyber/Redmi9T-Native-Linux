from pathlib import Path
import json,re
root=Path(__file__).resolve().parents[1]
raw=Path('C:/Windows/INF/usbncm.inf').read_bytes()
inf=raw.decode('utf-16') if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else raw.decode('utf-8-sig',errors='replace')
gadget=(root/'config/lemon-usb-gadget-v6').read_text()
evidence=(root/'reports/v6-usb-descriptor-evidence.txt').read_text()
symbols=(root/'reports/System-v5.map').read_text()
checks={
    'Windows_inbox_NCM_match':'USB\\Class_02&SubClass_0d&Prot_00'.lower() in inf.lower(),
    'NCM_source_control_class':'bInterfaceClass =\tUSB_CLASS_COMM' in evidence,
    'NCM_source_subclass':'USB_CDC_SUBCLASS_NCM' in evidence,
    'NCM_source_protocol':'USB_CDC_PROTO_NONE' in evidence,
    'NCM_IAD_two_interfaces':'bInterfaceCount =\t2' in evidence,
    'compiled_NCM_bind':re.search(r'\bncm_bind$',symbols,re.M) is not None,
    'compiled_ACM_bind':re.search(r'\bacm_bind$',symbols,re.M) is not None,
    'ACM_link_before_NCM':gadget.index('ln -s functions/acm.usb0')<gadget.index('ln -s functions/ncm.usb0'),
    'composite_IAD_device_class':all(s in gadget for s in ['echo 0xef > bDeviceClass','echo 0x02 > bDeviceSubClass','echo 0x01 > bDeviceProtocol']),
    'no_live_unbind':re.search(r'echo\s+[\'\"]{2}\s*>\s*UDC',gadget) is None,
}
assert all(checks.values()),checks
(root/'reports/v6-descriptor-check.json').write_text(json.dumps({'status':'PASS_SOURCE_AND_HOST_INF_ONLY','checks':checks,'expected_interfaces':['0 ACM control','1 ACM data','2 NCM control (02/0d/00)','3 NCM data'],'actual_bus_descriptors_captured':False,'limits':'Interface numbers are inferred from configfs link order; physical descriptors, endpoint allocation and Windows binding still require v6 boot.'},indent=2)+'\n')
print(json.dumps(checks,indent=2))
