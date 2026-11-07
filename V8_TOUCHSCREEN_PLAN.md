# v8 — отдельный порт сенсора

Архивный downstream probe прочитал trim ID `0a 00 00 72 66 03`. С маской таблицы Xiaomi он выбирает NT36672A memory map. Далее recovery зарегистрировал `NVTCapacitiveTouchScreen`, сообщил FW v5 и PID `5940` после загрузки `nt33672a_truly_novatek_ts_fw.bin`. Имя файла воспроизведено буквально. При первых кадрах после обновления в логе есть ошибки checksum. [Probe](logs/v7-authorized/twrp-dmesg-before.txt#L1204) · [PID и firmware](logs/v7-authorized/twrp-dmesg-before.txt#L1560).

Топология: GENI SPI `4a88000`, логический CS1, SPI mode 0, 9,6 МГц, reset TLMM103 и IRQ TLMM93. Downstream использует IRQ rising edge по логу и дополнительные GPIO flags в DT. При переносе сверить физический pinmux/CS и преобразование IRQ flags. Питание VDDIO, LAB и IBB совместно с дисплеем. Mainline `novatek-nvt-ts.c` работает через I²C, поэтому понадобится SPI transport и разбор RAM firmware загрузчика Xiaomi.

Отдельный патч должен сначала проверить trim ID и memory map, валидировать firmware partitions и checksum, затем реализовать input MT type B, координаты/ориентацию, release всех слотов при остановке и безопасную работу IRQ. Использовать только подтверждённые volatile RAM operations. Тестировать `evtest` и `libinput debug-events` отдельным сеансом после валидации питания. В текущем v8 отсутствует touch child в DT. 
