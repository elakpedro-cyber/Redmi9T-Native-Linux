# GNOME Physical LCD v2.1 — офлайн-проверки

Дата:2026-11-07. Все проверки этой версии выполнены на Windows/WSL/QEMU. Телефон не использовался для новых графических испытаний; syscall/driver/питание устройства в этой работе не менялись.

| Проверка | Доказательство | Результат |
|---|---|---|
| ARM64 сборка helpers и traces | `logs/gnome-physical-v2.1/build.txt`, `build-sha256.txt` | ELF aarch64, GCC Wall/Wextra/Werror, pixel-copy result unchanged |
| GRD50.1 source + minimal fd patch | `grd-build.txt`, `grd-loader.txt`, `grd-build-stage.txt` | Собран, зависимости разрешены, реально работает в C QEMU |
| Forced EGL failure old/fixed | `grd-egl-negative.txt` | Старый исходник воспроизводит EBADF/stdin closed; новый stdin intact |
| Настоящие ARM64 GNOME/GRD/RDP/Weston | `offline-final-term`, `offline-final-int`, `offline-release-deadline` | Logout/TERM/INT/deadline, exit0, не осталось namespace mounts/owners |
| Частичный старт до GRD install | `offline-partial-start` | Инъекция missing binary, ожидаемый exit1, cleanup pass |
| Частичный отказ RDP после старта Shell | `offline-partial-rdp` | Инъекция exit23; USER_COMPONENT_EXIT, штатный logout и namespace cleanup pass |
| VT helper на настоящем ядре v8b в QEMU system | `vt-v8b-vm.txt` | ALL_VT_TESTS_PASS, VT_VM_RESULT=0; repeated release/EBUSY/owner cases |
| Watchdog на ARM64 kernel v8b/BusyBox | тот же VM log | soft deadline, TERM, INT, partial exit17, hard kill namespace, ALL_WATCHDOG_TESTS_PASS |
| ARM64 variadic trace ABI | `trace-abi.txt` | PASS, реальные аргументы не повреждены |
| Resource ownership | `scope-tests.txt` | File descriptor и сохранённый mount namespace fd блокируют clean; после close repeat check pass |
| Simultaneous memory cohort | `accounting-test.txt` | Не суммируются независимые пики |
| Windows control guards | `controller-tests.txt` | stale boot не получает signal; repeated stop; exe+starttime guard. Это mock regression, не аппаратная проверка Windows controller |
| PowerShell AST | `windows-parse.txt` | Оба файла разобраны Windows PowerShell без выполнения сетевых команд |
| Touch mapping/sequence | `touch-tests.txt` | synthetic bounds/invalid cases, два контакта/cancel/release; никаких input devices |
| Stable snapshots | `checkpoint-verification.json` | SHA/size всех файлов v1 и v2; mismatch0 |
| Bundle members | `artifacts/gnome-physical-v2.1/release.json`, `BUNDLE_MANIFEST.json` | Размеры и SHA каждого файла проверены после упаковки |

В QEMU software rendering включён явно `LEMON_GNOME_OFFLINE=1` и `LIBGL_ALWAYS_SOFTWARE=1`; эти логи не доказывают аппаратный FD610 или производительность телефона. Hardware branch по-прежнему не выставляет эти переменные и требует существующий renderD128 плюс строгую защиту Mutter. На телефоне v2.1 FD610, VT cleanup, показатели памяти/FPS и visual regressions ещё не проверены.

Successful C logs не содержат прежних ClientPrivate timeout, disposed/inf WindowPreview, g_close(fd0) или BIO_new. Служебные предупреждения остаются видимыми. Негативный old-GRD тест намеренно содержит прежний CRITICAL: это ожидаемое воспроизведение, не новая ошибка готовой сборки.

`test-offline.sh` замораживает свою копию перед запуском, чтобы правки harness во время долгого теста не портили чтение Bash. Существуют промежуточные failed-development логи (`cleanup-*`, `lifecycle-*`, `offline-final-deadline`): они сохранены как история причин, а не считаются успешной регрессией. При проверке fd ownership найден и исправлен ложный захват собственным outer launcher script fd; чужие fd не исключаются.

В VM тесте дочерний PID namespace проверяется по namespace inode, не по PID из другого namespace. Перед выключением QEMU оставлена1s для вывода UART; это относится только к VM, не к телефону.

Для повторения: `build.sh`, `build-grd.sh`, `test-grd-egl-failure.sh`, `test-trace.sh`, `test-vt-vm.sh`, `test-scope.py`, `test-offline.sh C TAG`, Python tests, затем `pack.py`. Пути SDK/roots указаны в существующих скриптах; toolchains/полные kernel sources не включаются в bundle. Никакая из этих команд не прошивает телефон.
