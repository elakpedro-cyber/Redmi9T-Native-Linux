# v8 — проверка образа этапа A

| Артефакт | Результат |
|---|---|
| boot-linux-test-v8.img | 24 698 880 байт, SHA-256 `563296819c9e22da2ffcc38918b0761ca3d18eed7ae181123796fd6fb1033a29` |
| ARM64 Image | 31 844 864 байта, memory_size 32 505 856 байт, укладывается в окно 32 MiB |
| Initramfs | 14 023 739 байт, Alpine 3.24.4, OpenRC, прежние USB/SSH службы, модули с vermagic v8 |
| Android boot | Header v2, page 4096, stock DTB 302 880 байт. AOSP распаковал и побайтно сверил три компонента |
| Kernel / DT | ARM64 DPU/DSI/14nm PHY в msm.ko, dispcc и SimpleDRM встроены. Сохранены встроенные опции v7. Для lemon выполнен CHECK_DTBS=y. Отдельный dt-validate финального DTB без диагностик |
| DT dependencies | Проверено 466 ссылок в handoff FDT. Сравнение v7→v8 выявило одно изменение: явный disabled DPU. LCDB и touch child отсутствуют |
| Bootshim | 3 ABL-модели placement и 15 Unicorn случаев, включая 8 входов в Linux, guard failures и сохранение полного initramfs. Linker сообщает прежний RWX LOAD wrapper. Эмуляция проверяет инструкции и handoff |
| USB и SSH | 7 офлайн тестов, включая модель NCM failure→ACM, статическую shell, ARM64 Dropbear по ключу и SCP/SFTP roundtrip в WSL. PowerShell parser прошёл |
| GPU addon | Прежний addon v7 распакован поверх v8 и проверен ARM64 loader. Render probe ожидаемо отказал без render node. Firmware совпала по байтам, сохранён separate_gpu_kms=1 |
| Display code | ARM64 сборка td4330-profile.o и LCDB .ko с modpost отдельно от boot root. Сверены 77 on и 2 off packets |
| DT fixture этапа B | Отдельное дерево для проверки host/PHY на ПК. От v8 отличается только четырьмя status полями, dt-validate без диагностик |
| Контроль v7 | 416 файлов скопированы, сверены и помечены read-only. Проверка сравнила SHA снимка с текущими исходниками и артефактами v7 |

Сборка выполнена на том же pinned Linux 7.4-rc1. В boot root сохранены публичные клиентские ключи. Новый серверный Ed25519 генерируется в RAM после старта, а первый SSH требует pin из COM.

Воспроизводимый порядок на ПК: `build-kernel-v8.sh`, `extract-display-v8.py` с stock-merged DTB, `dtc` и `fdtoverlay` с `config/display-safe-v8.dts`, `build-boot-rootfs-v8.sh` (WSL root), `build-shim-v8.sh`, placement/fixture/shim emulation, `check-dt-v8.sh`, `test-v8-offline.py` (WSL root), `validate-v8.py`. Внешние прототипы собирает `build-display-prototypes-v8.sh`. Исходная ссылка LCDB зафиксирована в [отчёте о питании](V8_POWER_SEQUENCE.md).

Основные логи: [ядро](reports/kernel-v8-build.log), [DT schemas](reports/v8-dtbs-check.log), [bootshim](reports/bootshim-v8-emulation.json), [rootfs](reports/v8-functional-tests.json), [проверка](reports/v8-validation.txt). Аппаратные результаты относятся к v7. На устройстве выполнено только чтение диагностики через SSH. 
