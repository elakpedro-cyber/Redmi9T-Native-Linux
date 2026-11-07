# Первое испытание v7 — только после нового разрешения

В этой сессии телефон не перезагружался, boot не записывался, GPU не включался.
Прошлое разрешение относилось только к v6. Порядок ниже — план.

## Область предлагаемого испытания

Один переход v6 → TWRP, одна запись **только boot**, проверка readback,
одна загрузка компактной v7. Сначала USB/Alpine/UFS, затем, если это отдельно
включено в разрешение, ручной headless GPU test. Ни panel reset, ни touch probe,
ни управление LCD bias/backlight не входят в этот тест.
При неработоспособной v7 — восстановление сохранённой v6 через отдельный recovery.

## Фиксированные образы

- v7 `artifacts/boot-linux-test-v7.img`: **24428544 байта**,
  SHA256 `0ae797dbf092aaeb6fee4cb7a6d646a296f27c9f44ca9ead80fa57785f370746`.
- v6 `artifacts/boot-linux-test-v6.img`: **23670784 байта**,
  SHA256 `1eade4d8208905703286d01883e76b71728cc36b301f28563b58a0e53d4c8d63`.
- Контрольная v6: `snapshots/v6-hardware-validated/artifacts/boot-linux-test-v6.img`.
- GPU addon: `artifacts/gpu-userspace-v7.tar.gz`, **85770796 байт**,
  SHA256 `b81dcac42177033382803779dd0ef1450a42e096a76b22fb260737bac6297620`.

До начала проверить эти три SHA на ПК и доступность аппаратного Power+Volume Up.
Не использовать старый authorized-v6-write.py для v7. Fastboot boot на этом
ABL ранее не поддерживался; повторные неподтверждённые способы загрузки не нужны.

## 1. Сохранить v6 и войти в recovery

Снять SSH dmesg/config/DT и UFS counters; закрыть serial terminal перед pyserial.
Проверить питание/заряд, USB, исходный recovery backup и v6 snapshot.
Только после разрешения перейти аппаратными кнопками в TWRP, без wipe/app install.

TWRP ранее автоматически монтировал /data и /cache RW. Сначала проверить
`cat /proc/mounts`, отключить эти mounts и не продолжать при дисковых mounts.
Это ограничивает дальнейшие записи; строго доказать отсутствие самых ранних
фоновых записей самого TWRP нельзя. Не запускать recovery, если такой риск
не принят пользователем в разрешении аппаратного испытания.

## 2. Проверки в TWRP до единственной записи

Все команды ADB с `-s 35a1d5bf0221`, из исходного каталога platform-tools.
Проверить uid=0, ro.product.device=lemon, kernel 4.19.252, tmpfs `/tmp`.
Проверить by-name, не полагаться только на старые номера:

```
/dev/block/bootdevice/by-name/boot     -> /dev/block/sde49, 134217728 байт
/dev/block/bootdevice/by-name/recovery -> /dev/block/sda9, 134217728 байт
```

Recovery SHA:
`1737005c5d9452d3238fcd0a2430956e7232937b35e9df427edc114f0dacd2eb`.
DTBO SHA:
`6fd8b752c9a64bc77ccb43a43834b38a2a61e0499c44de01c6d1a349d73ce9a6`.
Vbmeta SHA:
`e1bd96f8e0ffe1a71cf41074aa46d3786fda7831b7395efa6205d166b1506ad5`.
Проверить SHA текущего boot **префикса 23670784 байта**, он должен совпасть с v6.
Снять pstore/dmesg на ПК, ничего в pstore не удалять.

Передать v7 в `/tmp/boot-linux-test-v7.img`, повторить `wc -c` и SHA на телефоне.
При любом несоответствии остановиться без записи и без reboot.

## 3. Единственная запись, только в разрешённом тесте

Следующий блок **не выполнялся**. Проверки выше обязательны; это не автономный flasher.

```powershell
.\platform-tools\adb.exe -s 35a1d5bf0221 push .\Redmi9T-Native-Linux\artifacts\boot-linux-test-v7.img /tmp/boot-linux-test-v7.img
.\platform-tools\adb.exe -s 35a1d5bf0221 shell 'wc -c /tmp/boot-linux-test-v7.img; sha256sum /tmp/boot-linux-test-v7.img'
# После ручной сверки размера, SHA и всех preconditions:
.\platform-tools\adb.exe -s 35a1d5bf0221 shell 'dd if=/tmp/boot-linux-test-v7.img of=/dev/block/bootdevice/by-name/boot bs=4194304 conv=fsync'
.\platform-tools\adb.exe -s 35a1d5bf0221 shell 'head -c 24428544 /dev/block/bootdevice/by-name/boot | sha256sum'
```

Проверить exit codes, readback SHA=v7, неизменность recovery/dtbo/vbmeta SHA.
Не очищать хвост boot и не выполнять erase. Лишь после успешной сверки разрешён
один normal reboot. Если запись/readback не прошли — оставаться в TWRP.

## 4. Базовая проверка v7 без GPU

Ожидаются `7.4.0-rc1-lemon-bringup-v7`, LEMON_INIT_V7_REACHED,
LEMON_OPENRC_V7_REACHED, Alpine 3.24.4, health/net/sshd started.
ACM остаётся: ожидается COM4, но проверять PnP, не угадывать номер.
Не открывать COM одновременно двумя программами.

```
python Redmi9T-Native-Linux/scripts/collect-v7.py --expect v7 --port COM4 --wait 120
```

Проверить 6 LUN, 4096-byte logical blocks, только виртуальные mounts, пустой swap,
нулевые write/discard counters; `lsmod` не должен содержать msm.
Самопроизвольное появление MSM/render node — отклонение от плана, собрать логи.

SSH host key новый после каждого reboot. Из **нового физического COM-лога**
`*-network-ssh.txt` получить pin:

```
python Redmi9T-Native-Linux/scripts/pin-host-key-v7.py --serial-log <новый_COM_лог>
```

Он создаёт host-ed25519.pub, known_hosts и pin.json. Проверить fingerprint,
затем Windows test с этим host public key и ExpectedHostFingerprint:

```powershell
$project = Join-Path (Get-Location) 'Redmi9T-Native-Linux'
$identity = (Get-Content "$project\logs\v6-authorized\test-client-identity.json" -Raw | ConvertFrom-Json).private_key_path
# $pinDir — каталог, напечатанный pin-host-key-v7.py для текущей загрузки.
$pin = Get-Content "$pinDir\pin.json" -Raw | ConvertFrom-Json
& "$project\scripts\Test-LemonHardwareV7.ps1" -SerialPort COM4 -TestScp -IdentityFile $identity -HostPublicKeyPath "$pinDir\host-ed25519.pub" -ExpectedHostFingerprint $pin.fingerprint
```

При необходимости `-ConfigureIPv4` задаёт .77.1/30 **только** USB adapter,
проверенный VID/PID/MAC; домашние .0.x, DNS и default route не меняются.
Никогда не ставить StrictHostKeyChecking=no и не принимать IP-key без COM pin.
При отказе OpenRC статическая getty/shell запущена раньше и не зависит от NCM.

## 5. Отдельно разрешённый GPU этап

Только после устойчивых USB/SSH и согласия на GPU workload. Проверить /tmp=tmpfs,
root=rootfs, достаточно RAM (не менее 500 MiB свободно для addon и распаковки).
Передать addon по SCP в /tmp, сверить **точный SHA выше**. Не писать на UFS.
Распаковать проверенный addon в RAM rootfs:

```
tar xpf /tmp/gpu-userspace-v7.tar.gz -C /
```

Снять dmesg/UFS stats, открыть параллельный COM logger. Явно загрузить `modprobe msm separate_gpu_kms=1`.
Blacklist блокирует autoload, но не прямой modprobe. Не менять clocks/regulators,
не запускать modetest modeset/Weston/DSI и не повторять modprobe/reset при зависании.
Проверить dmesg, `/sys/class/drm/renderD*/device/driver`, `/dev/dri`, lsmod.

Найти render node с DRM driver msm; номер renderD128 не считать постоянным.
На нём выполнить один тест:

```
MESA_SHADER_CACHE_DISABLE=true /usr/local/bin/gpu-render-v7 /dev/dri/renderD128
sha256sum /tmp/gpu-render-v7.rgba
```

Успех: LEMON_GPU_V7_RENDER_PASS, renderer610, все пиксели, отсутствие fault/hang,
SSH и COM продолжают работать. Один render node без workload успехом не является.
Сохранить stdout/dmesg/UFS stats на ПК. При firmware/PAS/SMMU failure остановить
GPU этап; не обходить подпись и не подставлять ZAP другой платы.

## 6. Stop conditions

Потеря обоих USB каналов, kernel panic, нестабильность UFS, ненулевые неожиданные
write/discard counters, ошибочный образ/раздел/hash: никаких повторных экспериментов.
Сначала доступные логи, затем согласованный возврат v6 по V7_RECOVERY.md.
v7 не считается новой контрольной сборкой до полного аппаратного протокола.
