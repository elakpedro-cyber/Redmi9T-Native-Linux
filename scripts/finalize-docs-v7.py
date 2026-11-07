from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
image=root/'artifacts/boot-linux-test-v7.img';addon=json.loads((root/'reports/gpu-userspace-v7.json').read_text())
bootsha=hashlib.sha256(image.read_bytes()).hexdigest()
for name in ['V7_FIRST_BOOT.md','V7_VALIDATION.md']:
    p=root/name;text=p.read_text(encoding='utf-8')
    text=text.replace('d666314c8a356d0153e066f5081802a6d20117e69db0ec0f265c0749f2daee55',bootsha)
    text=text.replace('0f1cd0b4c6d8b689554cac9be975a9e47d1077715aa852dbbb9c393d1c5c0bf4',bootsha)
    text=text.replace('bfeb9f0e12eaf92548b60e9ff83ef2b04aa2c0ee3e6dd078290ef764b19bee74',addon['sha256'])
    text=text.replace('85770437',str(addon['bytes'])).replace('| 74896 |','| 75080 |')
    text=text.replace('24481792',str(image.stat().st_size))
    text=text.replace('10363248',str((root/'artifacts/bootshim-v7.Image.gz').stat().st_size))
    assert bootsha in text and str(image.stat().st_size) in text
    p.write_text(text,encoding='utf-8',newline='\n')
status='''# v7 — подготовлена, аппаратно не испытана

2026-11-05: собраны Linux 7.4.0-rc1-lemon-bringup-v7, GPU-only MSM module,
device-owned firmware и компактный RAM boot. MSM autoload запрещён; для ручного
headless probe задан separate_gpu_kms=1. Mesa/FBO shader test — отдельный RAM addon.
Публичные SSH keys включены в initramfs; private PC key вне образа, host key
проверяется заново через COM после reboot. MDSS/DSI/touch не активировались.

Телефон остался в работающей v6. Нет reboot/flash/GPU workload. v6 snapshot
и исходные backups сохранены. Новое аппаратное испытание требует разрешения.

Текущие документы: V7_VALIDATION.md, V7_HARDWARE_MATRIX.md, V7_GPU_RESEARCH.md,
V7_DISPLAY_RESEARCH.md, V7_TOUCHSCREEN_RESEARCH.md, V7_FIRST_BOOT.md, V7_RECOVERY.md.
Хеши: reports/v7-final-manifest.json. Ниже — предыдущее состояние v6.

---

'''
p=root/'STATUS.md';text=p.read_text(encoding='utf-8')
if not text.startswith('# v7 — подготовлена'):p.write_text(status+text,encoding='utf-8',newline='\n')
for name in ['V7_GRAPHICS_MATRIX.md','V7_TECHNICAL_PLAN.md']:
    p=root/name;text=p.read_text(encoding='utf-8')
    note='> Историческая предварительная заметка после v6. Текущие результаты: V7_VALIDATION.md и V7_HARDWARE_MATRIX.md.\n\n'
    if not text.startswith('> Историческая'):p.write_text(note+text,encoding='utf-8',newline='\n')
print('Final v7 boot SHA256:',bootsha)
print('Final GPU addon SHA256:',addon['sha256'])
