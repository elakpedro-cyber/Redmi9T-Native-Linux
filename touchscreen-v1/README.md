# Redmi9T Touchscreen v1 — offline preparation

**Superseded hardware interpretation:** `TOUCHSCREEN_STAGE1_FINAL.md` установил runtime CS0 по Xiaomi source и сохранённому TWRP Image. Старые CS1 driver/DTB ниже — архивные structural fixtures, не использовать для hardware probe. Отдельные CS0 r2 sources/modules находятся в stage1-r2 и artifacts/touchscreen-stage1-final. Активный runner пока намеренно возвращает NO-GO: обратимый GENI lifecycle и электрический handoff не доказаны.

Экспериментальная подготовка, **не загружать модули на телефон без отдельного разрешения**. GNOME Physical LCD v2.1 остаётся неизменной. Физические касания в Linux ещё не работают.

После отдельного разрешения собран офлайн disabled DTB-кандидат. Delta/schema/negative checks прошли; он не прошивался и не применялся. Источник, хеши и объяснение отказа от lossy roundtrip: [DTB_REVIEW.md](DTB_REVIEW.md). Дополнительная прошивка для текущего этапа не нужна. Новый пакет и манифест: artifacts/touchscreen-v1/release-dtb-review.json и MANIFEST-dtb-review.json; исходный review archive сохранён.

Артефакты ARM64: lemon_nt36672a.ko, spi-geni-qcom.ko (private raw-delay patch), wlfreerdp3-touch, libuwac0.so.0, touch-pointer.so, touch-events. Полные выводы: TOUCHSCREEN_V1_RESULTS.md; процедура: TOUCHSCREEN_STAGE1.md. Хеши: artifacts/touchscreen-v1/MANIFEST.json и release.json.

На ПК/WSL:

```sh
bash touchscreen-v1/build.sh
bash touchscreen-v1/build-geni.sh
bash touchscreen-v1/build-input.sh
bash touchscreen-v1/build-client.sh
python3 touchscreen-v1/test-software.py
python3 touchscreen-v1/test-frames.py
python3 touchscreen-v1/test-delay.py
bash touchscreen-v1/build-dtb.sh
bash touchscreen-v1/test-vm.sh
bash touchscreen-v1/test-wlf.sh
LEMON_OFFLINE_SECONDS=60 bash touchscreen-v1/tests/test-graph.sh C pointer-graph
```

Используются существующие kernel source/out v8b и Alpine ARM64 SDK. build-client требует SDK cmake/patchelf и development dependencies; SDK находится на ПК. Полные kernel/toolchain/SDK/rootfs и personal firmware в этот архив не включены. FreeRDP source archive и источники Novatek/GENI приложены для воспроизводимости.

Безопасная текущая диагностика с Windows:

```powershell
python -X utf8 .\touchscreen-v1\diagnose.py --known-hosts ПУТЬ_К_COM_ПРОВЕРЕННОМУ_known_hosts
```

Она не открывает evdev, SPI/I2C и не монтирует debugfs. Запись событий требует отдельного разрешения: даже O_RDONLY open evdev может вызвать input.open и включить IRQ. Поэтому touch-events требует --ack-input-open, проверяет конкретное имя устройства и ограничен30s. Он не применяет EVIOCGRAB и не создаёт uinput.

session-touch.sh и session-touch.patch — отдельный вариант исходника, не замена рабочему v2.1. Для будущего разрешённого сеанса нужны LEMON_TOUCH_EVENT=eventN, LEMON_TOUCH_STAGE1_VALIDATED=1 и измеренная LEMON_TOUCH_MATRIX (шесть значений). Внутри namespace передаётся сохранённый parent mount ID; prepare-private-input.sh создаёт только приватный device inode и udev metadata для проверенного touchscreen. Системные /dev/input, /run/udev и permissions не меняются.

Одиночный fallback включается только в RDP-клиенте через LD_PRELOAD touch-pointer.so и LEMON_TOUCH_POINTER=drag или scroll. drag даёт мышиные tap/drag; scroll — явный отдельный режим wheel. Это **не remote multitouch**, не автоматическое распознавание swipe и не подтверждение экранной клавиатуры. Второй контакт игнорируется. Native multitouch/жесты пока не допускаются; новый Wayland-клиент используется для touch только вместе с fallback.

Никакие команды старта, insmod, DT apply, firmware update или reboot этим README не выполняются. Stage C/B для повторной инициализации LCD остаётся NO-GO.
