# Redmi9T-Native-Linux — v6 работает на телефоне

Физически подтверждены Alpine3.24.4/OpenRC/apk, ACM(COM4), CDC NCM, key-only SSH,
SCP в /tmp RAM и внутренний UFS без mounts/swap/write/discard в Linux.
Windows USB192.168.77.1/30 ↔ телефон192.168.77.2/30. Домашняя сеть не менялась.

- [Фактические результаты, ошибки, логи и команда подключения](V6_HARDWARE_RESULTS.md)
- [Текущий статус](STATUS.md)
- [Восстановление рабочего v5](V6_RECOVERY.md)
- [Матрица графики](V7_GRAPHICS_MATRIX.md) и [офлайн-план v7](V7_TECHNICAL_PLAN.md)

Испытанный образ artifacts/boot-linux-test-v6.img:23670784 байта.
SHA256: `1eade4d8208905703286d01883e76b71728cc36b301f28563b58a0e53d4c8d63`.
Linux uname остаётся -lemon-bringup-v5: ядро и bootshim сохранены.

SSH сейчас использует отдельный тестовый ключ. Его public часть добавлена только
в RAM и исчезнет после reboot; private часть осталась на ПК вне проекта.
Точная команда и пути — в отчёте. Не перезагружать ради v7 без нового разрешения.

При входе в TWRP были обнаружены его автоматические /data/cache rw mounts;
они отмонтированы до flash. Абсолютное отсутствие фоновых записей recovery не
заявляется. Проверенные protected hashes и нулевые Linux block writes описаны в отчёте.
