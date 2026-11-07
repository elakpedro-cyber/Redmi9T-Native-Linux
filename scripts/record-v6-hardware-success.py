from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
windows_path=root/'logs/hardware-v6/20261105T193940984/result.json'
windows=json.loads(windows_path.read_text(encoding='utf-8-sig'))
serial=json.loads((root/'reports/first-test-v6-assessment.json').read_text())
journal=json.loads((root/'logs/v6-authorized/boot-write-journal.json').read_text())
hashes=(root/'reports/v6-native-postboot-hashes.txt').read_text().splitlines()
expected=['1eade4d8208905703286d01883e76b71728cc36b301f28563b58a0e53d4c8d63','1737005c5d9452d3238fcd0a2430956e7232937b35e9df427edc114f0dacd2eb','6fd8b752c9a64bc77ccb43a43834b38a2a61e0499c44de01c6d1a349d73ce9a6','e1bd96f8e0ffe1a71cf41074aa46d3786fda7831b7395efa6205d166b1506ad5']
assert [line.split()[0] for line in hashes]==expected
assert windows['Checks']['ScpTmpfsRoundtrip']['Status']=='PASS' and windows['HomeNetworkUnchanged']
assert serial['status']=='PASS_OBSERVED_CHECKS'
assert sum(e['stage']=='single_boot_write_started' for e in journal)==1
assert journal[-1]['stage']=='readback_and_protected_hashes_verified'
assert 'Authentications that can continue: publickey' in (root/'reports/v6-real-password-denied.stderr').read_text()
report={'status':'PASS_PHYSICAL_V6_TRIAL','boot_image_bytes':23670784,'boot_image_sha256':expected[0],'v6_boot_writes':1,'v6_normal_boot_requests':1,'rollback_performed':False,'current_phone_state':'v6 running; COM4 and NCM/SSH available','kernel_release':'7.4.0-rc1-lemon-bringup-v5 (unchanged kernel, V6 init/OpenRC markers)','windows_ncm_interface_index':72,'windows_ip':'192.168.77.1/30','phone_ip':'192.168.77.2/30','acm_port':'COM4','password_authentication_offered':False,'scp_roundtrip':windows['Checks']['ScpTmpfsRoundtrip'],'serial_checks':serial['checks'],'home_network_unchanged':True,'protected_partition_hashes_after_boot_unchanged':True,'runtime_client_key':json.loads((root/'logs/v6-authorized/test-client-identity.json').read_text()),'important_limit':'TWRP automatically mounted /data and /cache rw before flashing. They were normally unmounted; metadata writes by recovery cannot be excluded. Linux v6 block write/discard counters remained zero. No deliberate write targeted any partition except boot.','scope':'One boot and bounded checks, not long-term/suspend/cable-replug qualification.'}
(root/'reports/v6-hardware-result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k in ['status','v6_boot_writes','v6_normal_boot_requests','rollback_performed','acm_port','scp_roundtrip']},indent=2))
