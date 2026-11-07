# Возврат в TWRP

При временной загрузке разделы не меняются. Основной путь возврата — перезапуск в сохранённое recovery.

1. Если работает USB-оболочка Linux: `reboot -f`. Для принудительного возврата удерживать Power; при перезапуске удерживать Power + Volume Up для TWRP. Конкретный момент отпускания Power может потребовать повторной попытки.
2. Из bootloader fastboot можно вручную выполнить:

```powershell
.\platform-tools\fastboot.exe reboot recovery
```

3. Если команда не поддерживается — использовать аппаратные кнопки. Power + Volume Down обычно возвращает в bootloader fastboot. Не использовать unlock/lock/erase.
4. Если `fastboot boot` ранее действительно заработал, сохранённый `recovery.img` можно временно загрузить им. Этот способ не предполагается рабочим на текущем ABL без проверки.

Проверка возвращения:

```powershell
.\platform-tools\adb.exe devices -l
.\platform-tools\adb.exe shell uname -a
```

Ожидаются режим recovery, `lemon` и прежнее ядро TWRP 4.19.252.

## Только при фактическом повреждении recovery

Это ручная запись раздела, а не часть теста. Выполнять лишь с отдельным разрешением, после проверки устройства и SHA-256:

```powershell
Get-FileHash .\platform-tools\Redmi9T_Backup\recovery.img -Algorithm SHA256
# Ожидается 1737005c5d9452d3238fcd0a2430956e7232937b35e9df427edc114f0dacd2eb
.\platform-tools\fastboot.exe flash recovery .\platform-tools\Redmi9T_Backup\recovery.img
.\platform-tools\fastboot.exe reboot recovery
```

При отсутствии доступа и к recovery, и к bootloader остановиться. Не переходить автоматически к EDL, сбросу данных или перепрошивке прошивки целиком.
Для выполненной подготовки восстановление не требуется: телефон оставлен в TWRP, записи разделов не выполнялись.
