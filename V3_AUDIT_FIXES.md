# v3: исправления после независимого аудита

## Результат и граница доказательств

Подготовлен `artifacts/boot-linux-test-v3.img`: 9379840 байт, SHA-256:

```text
2f90a2e9f07577f80245f70dec671f1e2b4c5a3bd79655d67c3413e6ffec24f7
```

Исправления выполнены в существующем переходнике. Linux Image, конфигурация ядра, mainline DTB и схема работы со stock DTBO не менялись. `/init-v3` получил отдельный marker и вывод runtime-данных переходника. v1/v2 binaries и резервные копии сохранили свои SHA-256.

Это результат офлайн-проверок, **не доказательство первого запуска на телефоне**. Нет разрешения на запись или запуск. Команды телефона в ходе подготовки v3 не выполнялись.

## 1. DAIF

В v2 состояние D/A/I/F наследовалось от ABL. Это было недостаточно явно и исправлено.

В `bootshim/start.S` первая инструкция после ARM64 header branch — `msr daifset, #0xf`, затем `isb`. EL и SCTLR проверяются до назначения стека и входа в C. Перед `br` в ядро маски устанавливаются повторно. Exception level не переключается: поддерживаются исходные EL1 и EL2.

Эмуляция начинает выполнение с DAIF=0 либо частично установленными масками. На границе entry проверяется `(PSTATE & 0x3c0)==0x3c0`, сохранение исходного EL и x0/x1/x2/x3. Для EL1 получено PSTATE 0x600003c5, для EL2 — 0x600003c9; старшие NZCV bits не являются частью требования DAIF.

## 2. Cache coherency

Нормативная основа: [официальный ARM64 boot protocol](https://docs.kernel.org/arch/arm64/booting.html). Требуются masked DAIF, допустимый EL, выключенная MMU, отсутствие старых инструкций в I-cache и очистка Image до PoC. I-cache может оставаться включённым. v3 не ограничивается прежним `ic iallu`.

Новые helpers `prepare_range_poc` и `clean_range_poc` находятся в `start.S`. Размер строки вычисляется из CTR_EL0.DminLine как `4 << DminLine`; начало округляется вниз. Обрабатываются полные диапазоны Image memory size 28311552 байта по 0x80000000 и DTB workspace 0x20000 байт по 0x82000000.

Порядок:

1. После проверки всех адресов выполняются `dsb sy`, `dc civac` по каждой строке destination, `dsb sy`. Это очищает и инвалидирует возможные прежние линии **до** записи новых данных.
2. Создаётся mainline DTB, копируется Image, обнуляется хвост до image_size.
3. Для обоих диапазонов выполняются `dsb sy`, `dc cvac` по каждой строке, `dsb sy` — явная очистка до PoC по адресам, а не set/way.
4. После возврата из C: повторное DAIFSet, ISB, подготовка x1/x2/x3, `dsb sy; ic iallu; dsb sy; isb; br x9`.

Назначение CVAC подтверждается [описанием Arm](https://support.arm.com/documentation/111107/2026-09/AArch64-Instructions/DC-CVAC--Data-or-unified-Cache-line-Clean-by-VA-to-PoC); подход с обслуживанием диапазона и барьерами также сопоставлен с [Linux arm64 cache.S](https://github.com/torvalds/linux/blob/master/arch/arm64/mm/cache.S). C-код не включает MMU/cache и не переключает EL.

При SCTLR текущего EL с M=1 либо C=1 переходник останавливается **до использования своего стека**. Поддержка включённого D-cache с произвольными таблицами трансляции намеренно не добавлена: для неё потребовалась бы отдельная корректная процедура выключения и обслуживания всех задействованных отображений. Состояние I=1 допускается, оно отдельно протестировано.

### Что эмуляция доказывает

Unicorn исполнил скомпилированные инструкции EL1/EL2. Hooks проверили адрес **каждой** обслуженной строки, полный охват обоих диапазонов, завершение CIVAC до CVAC и завершающую последовательность DSB/IC/DSB/ISB. В модели CTR даёт 64 байта: по 444416 CIVAC и 444416 CVAC на каждый успешный случай. Image в destination совпал побайтово; хвост BSS нулевой.

### Чего эмуляция не доказывает

Unicorn не моделирует реальные dirty lines, system cache, PoC, interconnect и других coherent masters. Поэтому он не подтверждает аппаратную cache coherency. Дополнительные требования к firmware остаются: корректный boot environment от ABL/EL3/EL2, разрешённые либо корректно обслуживаемые VA maintenance/CTR accesses, согласованная адресация RAM/IPA и отсутствие продолжающегося DMA в используемые диапазоны. Неархитектурные system caches требуют корректной настройки firmware. Эти условия нельзя объявить проверенными по офлайн-прогону.

При EL1 код не пытается читать или менять недоступные HCR_EL2/EL3 registers. При EL2 использует SCTLR_EL2; при EL1 — SCTLR_EL1. Таймеры, GIC, security state и конфигурация остальных CPU наследуются от стандартного ABL Linux handoff и физически ещё не проверены. Открытый аналог `PreparePlatformHardware` выключает interrupts/cache/MMU после обслуживания кэшей; он сохранён как справочный `reports/reference-abl/ShutdownServices.c`, но не выдаётся за исходник установленного Xiaomi firmware.

## 3. Фактическое размещение ABL

Прежний прогон по 0x40080000 был моделью и не доказывал адрес при нормальной загрузке. Теперь это ограничение явно снято с утверждений, но не с проверки аппаратного теста.

В сохранённом ABL найдены реальные обращения к UEFI variables `KernelBaseAddr` и `KernelSize` по 0x16508..0x16578. В успешной ветке по 0x1662c..0x1664c 64-bit load address получается как KernelBaseAddr+0x80000. В fallback-ветке base memory объединяется с PCD kernel offset 0x80000; kernel region end задаётся PCD 0x05600000. Поля Android header kernel_addr сами по себе не доказывают физического размещения.

`scripts/emulate-abl-placement.py` исполнил эти инструкции со смоделированными UEFI responses:

| Сценарий | Kernel | Region end | Initrd | Входной DTB |
|---|---|---|---|---|
| Нет обеих UEFI variables, base memory 0x40000000 | 0x40080000 | 0x45600000 | 0x45572000 | 0x45371000 |
| Variables: base 0x40000000, size 0x05700000 | 0x40080000 | 0x45700000 | 0x45672000 | 0x45471000 |
| Variables: base 0x40200000, size 0x05700000 | 0x40280000 | 0x45900000 | 0x45872000 | 0x45671000 |

Это проверка **логики** с подставленными значениями. Реальные значения UEFI variables при нормальном запуске не прочитаны. Данные TWRP по 0x40080000 относятся к уже запущенному recovery и не заменяют normal-boot trace.

v3 не использует 0x40080000 как адрес собственных symbols. PC-relative code и payload работают с runtime base. Требуется 4 KiB alignment, проверяемое до ADRP стека. C дополнительно проверяет весь runtime диапазон `_start..wrapper_end`: нахождение в объявленной RAM, отсутствие пересечения с входным FDT, initrd, firmware reservations и destinations. При пересечении либо неподдерживаемом адресе — halt, без попытки копировать kernel поверх источника.

У wrapper ARM64 header text_offset=0x80000, image_size=27787952; размер файла 27771562. Runtime size включает 16 KiB стека и выравнивание. Для сравнения: сохранённый stock kernel header требует 35557376 байт; новый wrapper меньше. Это полезная проверка габаритов, но не доказательство выбора firmware-ветки. В ABL есть собственная проверка runtime ImageSize против промежутка до DTB.

Runtime guards не могут отменить ошибочное размещение, которое firmware выполнила **до** передачи управления. Сохраняется исходное требование: ABL должна выделить корректный диапазон с учётом ImageSize, включая стек.

Для будущего доказательства реального адреса добавлено строковое свойство `/chosen/xiaomi,bootshim-info`. Оно содержит runtime base/end, EL, SCTLR и DAIF. `/init-v3` выводит его в kmsg; его также можно прочитать из shell. Только этот вывод с аппаратного запуска позволит снять неопределённость адреса. Наличие строки в файле образа не является доказательством исполнения.

## 4. Матрица офлайн-тестов

12 случаев в `reports/bootshim-v3-emulation.json`:

- Успех EL1 по 0x40080000 с DAIF=0.
- Успех EL1 по 0x40280000 с частичными масками.
- Успех EL1 по 0x41080000 с другими частичными масками.
- Успех EL2 по 0x40480000 с DAIF=0.
- Успех EL1 по 0x40880000 с SCTLR.I=1.
- Защитные остановки: неверный FDT, initrd/destination overlap, source/FDT overlap, source/kernel-destination overlap, source alignment.
- Остановки M=1/C=1 проверены подменой значения чтения SCTLR: реальная MMU эмулятора оставалась выключенной, чтобы проверить guard, а не создавать несуществующие page tables.

Во всех пяти успешных случаях конечный entry=0x80000000, x0=0x82000000, x1=x2=x3=0, DAIF masked, EL сохранён. Kernel entry используется как граница остановки: **ядро в этих тестах не исполняется**.

## 5. Повторная проверка образа и DTBO

`scripts/validate-v3.py`: 48 успешных проверок. Android header v2, page 4096, header length 1660, DTB address field 0x01f00000. Stock DTB в boot image побайтово прежний; stock overlay #0 успешно применяется. Dtc читает оба итоговых дерева, warnings сохранены. Проверены 466 стандартных phandle/provider references, 17 входных reserved ranges и 13 no-map ranges, статический initramfs/ash syntax, ELF без relocations/GOT и размеры.

AOSP round-trip kernel/ramdisk/DTB выполнен при упаковке. Manifest: `reports/artifact-manifest-v3.json`. Результаты: `v3-validation.txt`, `bootshim-v3-emulation.json`, `abl-v3-placement-emulation.json`, `abl-v3-load-address-disassembly.txt`, `bootshim-v3-disassembly.txt`.

Для воспроизведения:

```powershell
wsl -d Ubuntu-24.04 -- bash /mnt/c/Users/HadirPC/Downloads/platform-tools_r37.0.1-windows/Redmi9T-Native-Linux/scripts/build-shim-v3.sh
python .\Redmi9T-Native-Linux\scripts\emulate-abl-placement.py
python .\Redmi9T-Native-Linux\scripts\emulate-shim-v3.py
wsl -d Ubuntu-24.04 -- python3 /mnt/c/Users/HadirPC/Downloads/platform-tools_r37.0.1-windows/Redmi9T-Native-Linux/scripts/validate-v3.py
```

v2 sources сохранены в `bootshim/v2/`, исторический `build-shim.sh` закреплён на них. Существующий `Redmi9T-Boot-Audit.zip` относится к v2 и не обновлялся.

Актуальный предлагаемый аппаратный сценарий — `FIRST_BOOT.md`; возврат — `RECOVERY_PLAN.md`. Доказательство успеха остаётся marker `LEMON_INIT_V3_REACHED` из реально выполняемого `/init`, а не логотип или завершение переходника.
