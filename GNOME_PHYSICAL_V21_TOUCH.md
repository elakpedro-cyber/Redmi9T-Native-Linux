# GNOME Physical LCD v2.1 — подготовка touchscreen

Физический LCD уже подтверждён через SimpleDRM. Это не подтверждение touch transport или его питания.

Подтверждение экземпляра из сохранённых TWRP данных: Novatek NT36672A, trim `0A 00 00 72 66 03`, project0x5940, FW5. Stock SPI1.1/CS1, IRQ GPIO93, resetGPIO103. Источники: `V7_TOUCHSCREEN_RESEARCH.md`, `V8_DISPLAY_TOUCH_BRINGUP.md`, `GNOME_PHYSICAL_V2_TOUCH_AND_KMS.md`. Не переносить I2C-драйвер или похожий firmware по имени.

Последний read-only snapshot v2: только input pm8941_pwrkey, pm8941_resin, gpio-keys; SPI devices пусты. В этой работе телефон не опрашивался заново: утверждение о текущем event node без нового чтения не делается.

Не хватает проверенного kernel SPI driver, firmware identity/hash и доказанной RAM-only политики upload, IRQ/reset/power sequencing без сброса общей LCD/TP цепи. В vendor списке имя `nt33672a_truly_novatek_ts_fw.bin` (33672a) — не опечатка, которую можно автоматически исправить на36672a. Наличие списка не доказывает наличие нужного файла.

## Готовая программная часть

- Сохранён `display-v8/novatek-lemon-frame.c`: checksum/packet validation и Type B slots, только офлайн parser/report helper; не работающий SPI driver.
- `touch-map.py`: координаты из измеренных ABS min/max в выбранный output; rejects invalid bounds/out-of-range. Реальная rotation/inversion пока неизвестны.
- `touch-sequence.py`: validator down/motion/up/cancel, unique contact IDs и обязательный release при disconnect. Тесты двух пальцев/cancel и отрицательные последовательности выполняются на ПК. Никакого `/dev/uinput`, hardware injection или открытия input node.

Будущая интеграция C: SPI input MT Type B -> libinput seat Weston -> wl_touch -> FreeRDP touch channel -> GRD/Mutter RemoteDesktop -> GNOME. [Используемый Wayland client FreeRDP](https://github.com/FreeRDP/FreeRDP/blob/3.32.2/client/Wayland/wlf_input.c) содержит touch callbacks; negotiation и поведение конкретной версии из ARM64 root должны быть проверены отдельно. Mouse emulation нельзя засчитывать как multitouch.

Порядок после разрешённого безопасного driver bring-up: идентифицировать один event node по driver/phys/ABS/MT, измерить bounds, проверить libinput classification; разрешить только этот node в приватном Weston root; trace contact IDs/down/motion/up/cancel; проверить два пальца, ориентацию, release после disconnect, прокрутку и фокус GNOME. Текущий launcher по-прежнему не выдаёт `/dev/input`. Нельзя реализовать реальный touch одной заменой userspace-скриптов при отсутствии input device.

Stage C/B NO-GO сохраняется для повторной аппаратной инициализации дисплейного питания. Эта подготовка не разрешает питание/reset/firmware команды контроллеру.
