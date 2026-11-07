from pathlib import Path
import datetime,gzip,hashlib,json,re,shutil,subprocess
root=Path(__file__).resolve().parents[1];log=root/'logs/v7-authorized'
key=json.loads((root/'logs/v6-authorized/test-client-identity.json').read_text())['private_key_path']
ssh=['ssh.exe','-i',key,'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','KexAlgorithms=curve25519-sha256','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(root/'logs/v7-host-pin/20261105T193103Z/known_hosts'),'root@192.168.77.2']
for name,remote in [('v7-live.dtb','/sys/firmware/fdt'),('v7-config.gz','/proc/config.gz')]:
    p=subprocess.run(ssh+['cat '+remote],capture_output=True,timeout=20);p.check_returncode();(log/name).write_bytes(p.stdout)
(log/'v7-live.config').write_bytes(gzip.decompress((log/'v7-config.gz').read_bytes()))
def text(name):return (log/name).read_text(encoding='utf-8',errors='replace')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
render=text('gpu-render-once.stdout')
assert 'renderer=FD610' in render and 'LEMON_GPU_V7_RENDER_PASS' in render and 'DRM=msm 1.13.0' in render
assert json.loads(text('gpu-render-once.json'))=={'returncode':0,'timed_out':False}
pixels=(log/'gpu-render-v7.rgba').read_bytes();assert pixels==bytes([64,128,191,255])*256
before=text('gpu-pre-dmesg.stdout');after=text('gpu-final-dmesg.stdout')
delta='\n'.join(line for line in after.splitlines() if line not in set(before.splitlines()))+'\n'
(log/'gpu-dmesg-delta.txt').write_text(delta,encoding='utf-8',newline='\n')
assert 'loaded qcom/a630_sqe.fw' in delta
assert 'Zap shader not enabled' not in after and 'Unable to authorize' not in after
assert not re.search(r'fault|hang|timed out|failed|Unable to',delta,re.I),delta
temps={}
for stage in ['pre','after-load','after-render','final']:
    content=text('gpu-'+stage+'-diagnostic.stdout')
    temps[stage]={name:int(value)/1000 for name,value in re.findall(r'/sys/class/thermal/thermal_zone\d+\n([^\n]+)\n(-?\d+)\n',content)}
storage={}
content=text('gpu-final-diagnostic.stdout')
for disk,row,errors in re.findall(r'/sys/block/(sd[a-f])\n([0-9 \t]+)\n(0x[0-9a-f]+)',content):
    fields=list(map(int,row.split()));assert len(fields)>=17
    assert all(fields[i]==0 for i in [4,6,11,13,15]),(disk,fields)
    storage[disk]={'writes':fields[4],'write_sectors':fields[6],'discards':fields[11],'discard_sectors':fields[13],'flushes':fields[15],'ioerr_cnt':errors}
assert len(storage)==6
network=[]
for folder in sorted((root/'logs/hardware-v7').iterdir()):
    p=folder/'result.json'
    if not p.exists():continue
    data=json.loads(p.read_text());assert data['Status']=='NETWORK_SSH_SCP_COMMANDS_PASSED_REVIEW_STORAGE_LOGS' and data['HomeNetworkUnchanged']
    network.append({'folder':folder.relative_to(root).as_posix(),**data})
assert len(network)==2
monitor=json.loads(text('gpu-com-monitor-result.json'));assert monitor['completed'] and monitor['heartbeats']==12
commands=[json.loads(line) for line in text('gpu-commands.jsonl').splitlines()]
start=next(p['time'] for p in commands if p['name']=='gpu-render-once');finish=next(p['time'] for p in commands if p['name']=='gpu-render-output-sha')
bootsha='0ae797dbf092aaeb6fee4cb7a6d646a296f27c9f44ca9ead80fa57785f370746'
assert sha(root/'artifacts/boot-linux-test-v7.img')==bootsha
assert sha(root/'artifacts/boot-linux-test-v6.img')=='1eade4d8208905703286d01883e76b71728cc36b301f28563b58a0e53d4c8d63'
for name,info in json.loads((root/'snapshots/v6-hardware-validated/MANIFEST.json').read_text()).items():
    assert sha(root/'snapshots/v6-hardware-validated'/name.replace('\\','/'))==info['sha256'],name
result={'status':'V7_HARDWARE_HEADLESS_ADRENO610_PASS','time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'phone_left_running':'v7','boot_bytes':24428544,'boot_sha256':bootsha,'boot_write_count':1,'v7_boot_count':1,'gpu_module_load_count':1,'gpu_render_attempt_count':1,'render_limit_seconds':20,'render_command_wall_seconds_including_ssh':finish-start,'drm':'msm 1.13.0','render_node':'/dev/dri/renderD128','mesa':'26.1.6','renderer':'FD610','egl':'1.5','gles':'OpenGL ES 3.2','pixel_bytes':len(pixels),'pixel_rgba':[64,128,191,255],'pixel_sha256':sha(log/'gpu-render-v7.rgba'),'sqe_firmware':'loaded; explicit dmesg','zap_authentication':'inferred from successful a6xx hw_init/render and absence of fallback/error; no separate PAS trace recorded','separate_gpu_kms':1,'gpu_runtime_state_after':'suspended','gpu_reported_frequency_after_hz':320000000,'temperatures_c':temps,'ufs':storage,'network_tests':network,'com_monitor':monitor,'protected_partition_hashes':'recovery/dtbo/vbmeta matched original before and after boot write','twrp_caveat':'data/cache auto-mounted RW, unmounted before flashing; earlier TWRP writes cannot be excluded','warnings':['legacy vdd/vddcx dummy regulator warnings','boot-time sync_state pending for unused disabled peripherals'],'gpu_iommu_faults_in_test_delta':False,'stress_test_run':False,'dsi_backlight_touch_activated':False,'recovery_performed':False,'v8_flash_performed':False}
(root/'reports/v7-hardware-result.json').write_text(json.dumps(result,indent=2)+'\n')
report=f'''# Linux v7 — результаты аппаратного испытания

Дата: 2026-11-05. Redmi 9T NFC lemon, SM6115 / Adreno 610.
**Короткий аппаратный headless-тест GPU и Mesa Freedreno прошёл. Телефон оставлен в v7.**
Это один shader/readback test, не стресс-тест и не подтверждение полной стабильности всех GPU функций.

## Выполненные действия и безопасность

Свежая рабочая v6 проверена через COM4, затем через SSH. После предыдущего reboot
Windows потеряла ActiveStore USB IPv4, а RAM v6 — тестовый public key. Восстановлены
только адрес USB NIC72 и уже разрешённый public key в RAM. Приватный ключ остался на ПК.
Новый host key v6 проверен через физический COM; проверка SSH не отключалась.
Логи: logs/v7-authorized/v6-ssh-*, v6-live.dtb, v6-config.gz;
дополнительно logs/first-test-v6/20261105T192639Z-*.

Образ v6 и все356 файлов контрольного snapshot проверены до испытания и после него.
Оригинальные boot/recovery/dtbo/vbmeta backups проверены до записи.
V7: **24428544 байта**, SHA256 `{bootsha}`.
AOSP unpack подтвердил header v2/page4096 и точные kernel/initramfs/stock DTB.
Артефакт v7 после проверки не пересобирался и не изменялся.

Пользователь аппаратно вошёл в отдельный TWRP. Root ADB, lemon, recovery kernel
4.19.252-sucksguuji-45543a51f5f8, заряд80%, boot=sde49/128 MiB, recovery=sda9.
Первый guard с точным uname без suffix отказал до любых действий; после чтения
фактического uname использована корректная проверка prefix4.19.252.

**TWRP автоматически смонтировал /data (f2fs) и /cache (vfat) RW.** Они штатно
отмонтированы до передачи и записи образа. Нельзя утверждать, что до этого
TWRP не выполнил фоновых metadata/discard writes. При последующих native Linux
проверках таких записей не обнаружено; это отдельные области доказательств.

Выполнена **одна намеренная запись только boot**, без erase/форматирования/GPT changes.
Прочитан обратно точный префикс24428544 байта: SHA совпал. Recovery/dtbo/vbmeta
SHA до и после записи совпали с оригиналами. Затем выполнена одна загрузка v7.
Доказательства: logs/v7-authorized/boot-write-journal.json и adb-write-commands.txt.

## Базовая система до и после GPU

| Проверка | Фактический результат |
|---|---|
| Linux | 7.4.0-rc1-lemon-bringup-v7 |
| /init | LEMON_INIT_V7_REACHED |
| OpenRC | LEMON_OPENRC_V7_REACHED; health/net/sshd started |
| Alpine / apk | 3.24.4 / apk-tools3.0.9-r0 |
| Bootshim | EL1, DAIF=0x3c0, реальная база0x40080000, end0x41ef5af0 |
| USB ACM | COM4, shell работает;12 serial heartbeats параллельно GPU |
| USB NCM | UsbNcm Host Device, ifIndex72, MAC02:00:00:00:77:01 |
| Адреса | Windows192.168.77.1/30 ↔ Linux192.168.77.2/30 |
| Ping | До и после GPU:3/3 ответов,0% loss, <1ms |
| SSH | Ключ из v7 initramfs принят без добавления ключа после boot; строгий COM pin |
| SCP/SFTP | До и после GPU:1024 байта в /tmp и обратно, SHA совпали |
| UFS | sda–sdf; write/discard/flush counters0, ioerr_cnt0x3 без роста |
| Storage policy | Только rootfs/виртуальные mounts, swap отсутствует |
| Домашняя сеть | 192.168.0.49/ifIndex7 не изменена; network snapshots совпали |

После re-enumeration v7 Windows снова потеряла временный USB IPv4. Он повторно
назначен только проверенному USB NIC; домашние Ethernet/Wi-Fi/DNS/routes не менялись.
Host key v7: `SHA256:hETyisXByiPBy5U5Bw04VEFKDjKFvx60dvaLW7CBd/8`, получен через COM4.
Это новый ключ данной RAM-сессии, не старый ключ v6 и не отключённая host verification.

До GPU: logs/hardware-v7/20261105T223116400.
После GPU: logs/hardware-v7/20261105T223610698.
Полный первый serial snapshot: logs/first-test-v7/20261105T193016Z-*.

## Шесть разных уровней подтверждения GPU

| Уровень | Результат и доказательство |
|---|---|
| Драйвер зарегистрирован | PASS: modprobe exit0, dmesg Initialized msm1.13.0 for5900000.gpu |
| Firmware загружена | SQE PASS: dmesg loaded qcom/a630_sqe.fw. ZAP MDT/b00/b01/b02 SHA проверены в RAM |
| GPU инициализирован | PASS для данного workload: CP/GLES job завершился, glFinish/readback прошли |
| Render node | PASS: /dev/dri/renderD128, platform driver adreno; отдельный card1, SimpleDRM card0 сохранён |
| Mesa распознаёт GPU | PASS: EGL1.5, OpenGL ES3.2 Mesa26.1.6, rendererFD610 |
| Реальный hardware render | PASS: compiled shaders, triangle into surfaceless RGBA FBO16×16, все256 pixels совпали |

Загрузка выполнена один раз командой с лимитом15s:
`timeout -s TERM -k 3 15 modprobe msm separate_gpu_kms=1`.
Параметр — **параметр модуля msm**, задан также в /etc/modprobe.d/lemon-gpu-manual.conf;
фактический /sys/module/msm/parameters/separate_gpu_kms равен1.
Для одного GPU без активного MDSS default auto-policy недостаточна, поэтому
явный separate_gpu_kms=1 необходим для отдельного GPU DRM master.

После стабильного bind выполнен **один** renderer process под timeout20s,
без повторов и бенчмарков. Время команды с SSH overhead примерно{finish-start:.3f}s;
это не измерение чистого GPU времени. Timeout не сработал, exit0.
Вывод:

```
DRM=msm 1.13.0
EGL=1.5 GLES=OpenGL ES 3.2 Mesa 26.1.6 renderer=FD610
LEMON_GPU_V7_RENDER_PASS: GLES shader draw and 256 RGBA pixels verified
```

llvmpipe/softpipe исключены проверкой renderer; DRM fd обязан быть msm.
Probe использует конкретный render node через GBM, surfaceless context и FBO,
не KMS modeset и не framebuffer software output.

Сохранённый output1024 байта скачан на ПК, **все байты** дополнительно совпали
с256 повторами RGBA(64,128,191,255). SHA256:
`{sha(log/'gpu-render-v7.rgba')}`.
Файл: logs/v7-authorized/gpu-render-v7.rgba; вывод: gpu-render-once.stdout.

Отдельного trace вызова SCM/PAS для ZAP не включали. По коду a6xx_hw_init
успешный workload без сообщения `Zap shader not enabled`/ошибки авторизации
означает прохождение штатной ZAP ветки. Это вывод по коду и наблюдаемому
результату, а не самостоятельный cryptographic/PAS trace. Никаких bypass/патчей
подписи или SECVID register writes от оператора не выполнялось.

## Ошибки, температура и питание

Новые сообщения GPU сохранены отдельно: gpu-dmesg-delta.txt.
В delta нет GPU fault, SMMU/IOMMU fault, hang, timeout или reset loop.
Есть **два предупреждения**: supply vdd/vddcx not found, using dummy regulator.
В msm_gpu.c запрашиваются legacy vdd/vddcx handles; SM6115 описывает питание
через RPM/GMU-wrapper power domains. Рендеринг прошёл, но warnings не надо
скрывать или исправлять выдуманными regulator supplies. Перед автоматическим
GPU enable/v8 требуется отдельный review этой power-domain цепочки.

Boot-time sync_state pending для неиспользуемых peripherals присутствовали до
загрузки GPU; они не появились как следствие workload. Серьёзной нестабильности
не обнаружено. Существующий UFS ioerr_cnt0x3 не равен нулевой истории ошибок,
но во время теста не вырос.

GPU-thermal samples: до{temps['pre']['gpu-thermal']:.1f}°C,
после bind{temps['after-load']['gpu-thermal']:.1f}°C,
после render{temps['after-render']['gpu-thermal']:.1f}°C,
финально{temps['final']['gpu-thermal']:.1f}°C.
Это точечные замеры, не гарантированный температурный peak.
После теста GPU devfreq сообщает320MHz, runtime_status=suspended.
Это reported selected frequency, не доказательство активной работы на320MHz
во время suspend. USB power_supply сообщает5V, current_now/current_max0;
эти поля не дают достоверного измерения мощности GPU. Rail voltage/current
не менялись принудительно и не измерялись внешним прибором.

## Вывод и следующий этап

- **Adreno610 работает в коротком аппаратном GLES shader/readback тесте.**
- **Mesa Freedreno с аппаратным ускорением работает для проверенного workload.**
- Это не проверка Vulkan, всех GLES функций, длительного DVFS, системного
  suspend/resume, устойчивости под нагрузкой или полного graphics stack.
- Можно переходить к **офлайн-порту DSI**. Аппаратно включать DSI ещё рано:
  нужны PMI632 LCDB bias driver/sequencing, точная подсветка и panel driver
  для подтверждённого TD4330 Truly v2 профиля. SimpleDRM не заменяет KMS/DSI.
- Перед v8: review dummy-regulator warnings и power domains, убрать зависимость
  Windows USB IPv4 от временного ActiveStore состояния безопасным USB-only
  механизмом, решить размещение Mesa runtime, затем закончить panel/backlight
  и отдельно Novatek SPI touch. Не включать всё сразу в одном hardware тесте.

Телефон **оставлен в работающей v7**, msm после теста runtime-suspended.
Mesa addon находится только в RAM; при reboot его надо передать заново,
автозагрузка msm остаётся запрещённой. Публичные SSH client keys уже в boot;
host key после reboot обязательно закреплять снова через физический COM.
Откат v6 не понадобился, но проверенный образ и отдельный TWRP сохранены.
DSI/backlight/touch не включались. Прошивки v8 и дальнейших опытов не было.

Машинный результат: reports/v7-hardware-result.json. Основные логи:
logs/v7-authorized, logs/hardware-v7, logs/first-test-v7.
'''
(root/'V7_HARDWARE_RESULTS.md').write_text(report,encoding='utf-8',newline='\n')
print('PASS: hardware results written; exact pixels, no new faults, six zero-write UFS disks, v6 snapshot unchanged')
