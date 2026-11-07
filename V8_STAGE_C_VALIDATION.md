# Stage C — проверки на ПК

| Проверка | Результат и границы |
|---|---|
| Native DT и проверка схемы ядра | `CHECK_DTBS=y` для цели lemon. Переизданные схемы LCDB v2 и MFD проверены в отдельной временной копии с исходным v8b DT и disabled fixture. [Сборка](logs/v8-stage-c/build-review.txt) · [Схемы](logs/v8-stage-c/fixture-schema.txt). |
| Сохранение зависимостей | Байтовые значения всех свойств v8b сохранены. Fixture добавляет три узла, disabled LCDB и LDO/NCP, проверены SID/IRQ и ограничения. Panel/backlight binding под новый compatible не проверялся, поскольку активных новых узлов нет. [Валидатор](scripts/validate-stage-c-v8.py). |
| LCDB и панель | AArch64 LCDB v2 собран через modpost. TD4330 transport object собран без регистрации драйвера. Режим и пакеты сверены по трём источникам. Две полные последовательности, 158 инъекций timeout/short transfer во всех пакетах и отказ неправильного VC прошли на mock host. Проверены остановка отправки и применение задержек только для принятых пакетов. [Тест](scripts/test-stage-c-transport.py) · [Лог](logs/v8-stage-c/transport-check.txt). |
| Ошибки питания | Проанализированы prepare/rollback, штатное выключение, частичная запись и short-circuit. Тестов реального LCDB lifecycle и KMS atomic отказов пока нет. Исходный LCDB v2 остаётся непригодным для активации по результату ревью. |
| USB и SSH | Семь сценариев на rootfs v8b. Модель ACM+NCM, ACM fallback при ошибке NCM, аварийная shell, SSH pin, SCP/SFTP round trip, отказ неверного ключа и отсутствие пароля. QEMU-user и WSL loopback не эмулируют USB физически. [Результаты](logs/v8-stage-c/functional-tests.json). |
| Bootshim, GPU и образ | SHA v8b повторно совпал. Сверены отчёты 15 сценариев bootshim и итоговый DT после handoff, без повторной эмуляции. Рабочий kernel, initramfs и GPU не менялись. Аппаратный эталон Freedreno и USB взят из Stage B. [Манифест](snapshots/v8b-hardware-validated/manifest.json). |

Проверки подтверждают отключённый fixture и корректное поведение транспортного прототипа на подставном хосте. Реальная последовательность LCDB/REFGEN, PLL и подсветки остаётся вне этой валидации.
