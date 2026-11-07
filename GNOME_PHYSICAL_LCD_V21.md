# GNOME Physical LCD v2.1

Рабочая аппаратная контрольная версия — **v2**, проверенная владельцем на LCD. **v2.1 подготовлена и проверена офлайн; на телефоне ещё не запускалась.** Новый запуск требует отдельного разрешения.

Сохраняется путь C: GNOME50.3/Mutter50.2/FD610 -> PipeWire/локальный GRD TLS/NLA -> wlfreerdp3 -> Weston14/Pixman -> SimpleDRM1080×2340. Software renderer допускается только в явно обозначенном ARM64 QEMU тесте; аппаратный launcher сохраняет строгий FD610 guard.

## Что изменено

- Исправлены logout Shell/Session48 и порядок завершения компонентов.
- Устранены подтверждённые zero-size WindowPreview и callback-after-destroy случаи.
- Собран GRD50.1 с исправлением fd initialization при отказе EGL.
- Пара TLS paths применяется атомарно до grdctl.
- Cleanup проверяет владельцев root/exe/cwd/fd, namespace inode references и parent mountinfo; удаляет приватные socket файлы только после освобождения владельцев. VT helper остаётся проверенным из v2.
- Stop проверяет boot ID, путь watchdog и process start ticks; повторная остановка не ищет процессы по имени. Новый boot не получает сигналы по старому state.
- После успешного controller postflight и сохранения логов обе распакованные RAM-root удаляются. При ошибке/неподтверждённом освобождении дерево сохраняется для анализа: не удалять его принудительно.
- Добавлены одновременный учёт памяти и опциональная трасса rectangle copy/scale/NSC decode.
- Неожиданное завершение RDP/PipeWire/WirePlumber или локального клиента прекращает сессию и вызывает cleanup.

## Файлы

Архив `artifacts/lemon-gnome-physical-lcd-v2.1-aarch64.tar.gz`: immutable ARM64 roots, новые scripts/helpers/GRD, патчи/исходники, логи и manifest. SHA и размер находятся в `artifacts/gnome-physical-v2.1/release.json`. Нет новой прошивки, автозапуска или установки на UFS.

v2 backup: `snapshots/gnome-physical-lcd-v2/MANIFEST.json` и исходный `artifacts/lemon-gnome-physical-lcd-v2-aarch64.tar.gz`. В snapshot83файла; старые userspace/v2 и binary bundle не изменены. v1 также сохранена.

## Одна команда запуска / остановки

Из корня проекта, после отдельного разрешения на аппаратный сеанс:

```powershell
& .\scripts\Start-GNOME-Physical.ps1 -CheckOnly
& .\scripts\Start-GNOME-Physical.ps1 -Seconds 60
```

Остановка из второго PowerShell:

```powershell
& .\scripts\Stop-GNOME-Physical.ps1
```

Статус: `& .\scripts\Stop-GNOME-Physical.ps1 -Status`. Для baseline v2 к обеим командам добавить `-Version v2`. `-Measure` включает дополнительную трассу только v2.1; `-TestActions` запускает прежние программные проверки Console/Activities/Settings и требует включения в разрешённый сценарий. Ничего не запускается при чтении этого документа.

При запрете PowerShell scripts не менять глобальную ExecutionPolicy автоматически. Ранее одобренный запуск отдельного процесса с `-ExecutionPolicy Bypass -File` не устанавливает policy постоянно; выполнять его может сам владелец при необходимости.

Preflight находит только ранее подтверждённые NCM и COM4, проверяет IP, SSH host pin, hashes, v8b, tty1, SimpleDRM/current-mode, FD610, MDSS hold, unbound DISPCC/DSI, RAM и mounts/swap. Он не восстанавливает IP, не загружает MSM и не меняет дисплейное питание. Отсутствие GPU или changed SSH host key — остановка с причиной.

C доступен после офлайн-регрессии. B и A в v2.1 блокированы: их нельзя незаметно подставить вместо C; baseline v2 сохранена отдельно.

## Watchdog и возврат tty1

Ограничение60s действует с начала изолированной сессии, включая старт. За5s до hard deadline запрашивается штатный выход. По hard deadline завершается PID1 только приватного PID namespace и его потомки. Изолированы mount/pid/net, сеть RDP доступна только через private loopback; внешнего RDP listener нет.

Штатно: SessionManager.Logout -> Shell ACK/exit -> GRD -> WirePlumber -> PipeWire -> local client -> Weston/seatd -> bus. Затем helper возвращает tty1, закрывает проверочные VT references, освобождает VT2. EBUSY не обходится принудительным VT_DISALLOCATE чужого ресурса.

Если launcher не завершился: используйте Stop той же Version, сохраните логи. Если ownership check/VT helper отказывает, RAM не удалять, не запускать вторую сессию, не применять killall, не unload MSM. SSH/COM служат диагностикой. Не менять boot или перезагружать телефон для решения userspace cleanup без отдельного разрешения.

## Следующее аппаратное испытание (ещё не разрешено)

Один C-сеанс до60s, без firmware/module/power changes: preflight; RAM prepare; GNOME/локальный RDP/Weston в текущем режиме; Console/Activities/Settings при доступном времени; monitor faults/RAM/thermal; logout и VT recovery; выгрузка логов на ПК; сравнение шести UFS write/discard/flush counters; удаление RAM roots только при полном postflight success. Пользователь подтверждает видимый LCD и возврат текста.

Не запускать, если нет SimpleDRM текущего режима, renderD128/MDSS hold, verified host pin, COM4 или достаточно RAM. При fault/low memory/неожиданном display state сразу Stop, без автоматической повторной попытки. Stage C/B остаётся NO-GO для повторной аппаратной инициализации.

Отчёты: `GNOME_PHYSICAL_V21_WARNINGS.md`, `GNOME_PHYSICAL_V21_MEMORY_PERFORMANCE.md`, `GNOME_PHYSICAL_V21_TOUCH.md`, `GNOME_PHYSICAL_V21_VALIDATION.md`. Оставшиеся Glycin sandbox/системные службы явно перечислены; полноценная повседневная phone-сессия ещё не заявляется.
