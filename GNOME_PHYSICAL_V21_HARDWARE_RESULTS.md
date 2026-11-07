# GNOME Physical LCD v2.1 — аппаратные результаты

2026-11-07. **Один разрешённый C-сеанс выполнен успешно по функциональности и cleanup.** GNOME50.3/Mutter50.2 с FD610 показан на встроенном LCD. Пользователь ответил **«да всё есть»** на вопрос о GNOME, Console с GNOME_LCD_INPUT_OK, Activities и возврате tty1.

**Открытый дефект:** при выходе возник один новый GJS critical о callback ShellWindowTracker::notify во время GC. Поэтому завершение не объявляется полностью свободным от ошибок. Второго аппаратного теста не было.

Логи сеанса: `logs/gnome-physical-v2.1/20261107T130858618151Z`.
Подготовка/GPU restore/postflight/сравнение: `logs/gnome-physical-v2.1/hardware-C-run-20261107T130647Z`.
Данные: comparison.json, metrics.json, memory-accounting.json, ufs-live-monitor.jsonl.

## Подготовка

Первый read-only preflight остановился до GNOME: Windows потеряла USB IP, MSM/renderD128 отсутствовали. Он сохранён в previous-preflight-report.md; графических процессов тогда не запускали.

Владелец восстановил192.168.77.1/30 и отдельно разрешил GPU restore с последующим одним C-тестом. По COM4 сверены v8b, tty1 и публичный SSH host key. StrictHostKeyChecking=yes сохранён. Приватные SSH-ключи не собирались.

На непривязанном MDSS установлен временный override lemon-stage-b-hold; **однократно** загружен штатный MSM с separate_gpu_kms=1. RenderD128226:128 привязан к adreno. MDSS/DISPCC/DSI остались непривязаны. Второго modprobe, force-unbind, ручных clocks/regulators или питания не было. gpu-restore-attempt.json фиксирует команду.

Новый check-only прошёл: SHA roots/17payload-файлов, SSH/NCM/COM4, v8b, tty1, текущий SimpleDRM1080×2340, FD610, MDSS hold, RAM, mounts/swap. COM4 открывался только одним клиентом и закрывался после диагностики.

MemAvailable перед переносом3505456KiB (~3.34GiB), непосредственно перед графикой после распаковки2129692KiB (~2.03GiB). Rootfs и временные данные только в RAM.

## Реальный графический путь

`FD610 -> GNOME50.3/Mutter50.2 -> PipeWire/local GRD TLS+NLA -> wlfreerdp3 -> Weston14/Pixman -> SimpleDRM -> LCD1080×2340`.

Фактический shell.log:

```text
LEMON_FD610_EGL_VERIFIED node=/dev/dri/renderD128 renderer=FD610
Added device '/dev/dri/renderD128' (msm) using no mode setting.
Created gbm renderer for '/dev/dri/renderD128'
GNOME Shell started
```

Software fallback у Shell не включался. Weston/Pixman является намеренным software presenter, не заменой FD610 у GNOME. Optional EGL path GRD всё ещё выдаёт ошибки; аппаратное кодирование RDP не доказано.

Weston использовал current-mode1080×2340/XR24 и shadow framebuffer. Физический mode/timings/питание не изменялись. RDP был доступен только на private loopback в отдельном net namespace; TLS/NLA и certificate pin сохранены, внешнего RDP listener не создавали.

input.log подтверждает65 Notify calls, ввод echo GNOME_LCD_INPUT_OK, Super/Activities, Super+A, pointer motion, Settings и Alt+Tab. Console/Activities и возврат текста подтверждены пользователем указанным ответом. Settings также присутствовал в memory samples; отдельного детального ответа о нём не запрашивали. Скриншот/фото этой сессии не снимался.

## Лимит и остановка

Независимый ARM64 watchdog имеет hard limit60s с private PID/mount/net namespaces и запросом logout на55s. Сработал **graceful deadline**, SESSION_EXIT=0; hard kill не потребовался. По Weston log output был активен примерно54.7s; от начала инициализации Mutter до удаления virtual monitor прошло около51.2s. GUI завершился до hard deadline.

Окно before.txt -> after.txt67.64s включает read-only контроль и сбор журналов **после остановки GUI**; это не длительность активной графической сессии.

```text
WATCHDOG graceful deadline
LEMON_SESSION_ACK QueryEndSession
LEMON_SESSION_ACK EndSession
USER_GNOME_SESSION_REAPED
TTY1_RESTORED
VT2_RELEASED deferred_checks=1
SCOPE_CLEAR
PRIVATE_SOCKETS_AND_HOME_REMOVED
SESSION_EXIT=0
SESSION_RAM_ROOTS_REMOVED
```

Порядок: logout Shell/Session -> GRD -> WirePlumber/PipeWire -> client -> Weston/seatd -> system bus. VT helper дождался отложенного освобождения references. **EBUSY нет**, VT2 освобождена, tty1 восстановлена. Проверены root/exe/cwd/fd/namespace owners и parent mountinfo. После сохранения логов/postflight обе RAM-root удалены, state base пуст. В post ps нет GNOME/Mutter/GRD/Weston/FreeRDP/PipeWire/WirePlumber/session D-Bus процессов.

## Предупреждения v2 и v2.1

| Ошибка v2 | Результат этого v2.1 |
|---|---|
| ClientPrivate reply timeout | Не повторился, оба ACK получены |
| GLib.unix_signal_add deprecated wrapper | Не повторился |
| inf scale-x/scale-y WindowPreview | Не повторились |
| disposed WindowPreview / invalid sibling | Не повторились |
| logical monitor/work-area assertions при logout | Не повторились |
| GRD g_close(fd:0) EBADF | Не повторился |
| BIO_new failed for certificate | Не повторился |
| Broken pipe из-за раннего закрытия client | Не повторился |
| **GJS callback during GC sweeping, ShellWindowTracker::notify** | **Новое наблюдение:1critical при shutdown** |

Новый critical:

```text
Attempting to call back into JSAPI during the sweeping phase of GC
The offending signal was notify on ShellWindowTracker
```

GJS заблокировал callback; session завершилась с0, kernel fault/зависания нет. Это реальный userspace lifecycle defect. Точное место оставшейся подписки и причинная связь с правками v2.1 ещё не доказаны. В офлайн-прогонах сообщение не воспроизводилось. Его нельзя скрывать или считать исправленным.

Остались: OpenRC systemd/logind/GDM fallback; отсутствующие colord/Polkit/GeoClue/AccountsService; Glycin без sandbox; TPM -> приватный RAM GKeyFile; optional GRD EGL/Zink; FreeRDP deprecated client/runtime-check build/Kerberos realm/FUSE/pthread scheduling; RTKit unavailable; libcamera IPA key/dma-buf provider; Weston без физических input devices.

IBus portal startup failure из v2 в этом прогоне не наблюдался, но его причина отдельно не исправлялась. При штатном RDP logout остаются ERRINFO_RPC_INITIATED_DISCONNECT, ERRINFO_LOGOFF_BY_USER, STATE_RUN_QUIT_SESSION, cliprdr file/resetPointer. Все stderr сохранены без фильтрации.

## Память и производительность

| Показатель | v2 | v2.1 |
|---|---:|---:|
| Общий одновременный sampled PSS |912835KiB /891.44MiB |908191KiB /886.91MiB |
| Минимальный MemAvailable в samples |1256284KiB |1286240KiB |
| Максимальный CPU одного процесса,100%=ядро |137.82% |143.32% |
| Peak interval aggregate CPU по совпадающим PID/starttime |190.20% |189.01% |
| PW nonempty buffers |73/31.031s;2.32updates/s |84/28.623s;2.90updates/s |
| Максимум PW updates в1s bin |13 |21 |
| Client Wayland surface commits |62/32.423s;1.88/s |60/30.025s;1.965/s |
| Максимум client commits в1s bin |12 |12 |
| Notify dispatch RTT median |10.993ms |11.455ms |
| Notify dispatch RTT p95 |108.915ms |70.066ms |
| Notify dispatch RTT max |154.226ms |134.329ms |
| Максимальная наблюдавшаяся температура |57.6°C |57.3°C |

PSS разница -4644KiB (~4.54MiB,0.51%) не доказывает оптимизацию или исправление утечки: одна попытка, разные sampled phases/длительность, дополнительная instrumentation в v2.1. Изменение p95/FPS также не является статистически доказанным улучшением.

Группы **в одном общем пиковом memory sample**:

| Компонент | v2 PSS KiB | v2.1 PSS KiB | v2.1 RSS KiB |
|---|---:|---:|---:|
| Shell/Mutter | 165034 | 167732 | 284308 |
| GRD | 132367 | 132865 | 229008 |
| PipeWire | 2134 | 2116 | 4932 |
| WirePlumber | 21118 | 21704 | 58576 |
| Weston | 32960 | 33069 | 48516 |
| RDP client | 229383 | 229569 | 245012 |
| Other | 329839 | 321136 | 725428 |

RSS повторно учитывает shared pages. В v2 RSS был приблизительным stat×4KiB, в v2.1 — smaps_rollup. PSS не учитывает всю tmpfs/rootfs/dma-buf/kernel память. CPU interval и memory peak — разные моменты, они не суммируются.

В общем peak CPU interval v2.1: Shell/Mutter66.21%, GRD44.51%, client56.59%, Weston1.37%, Other20.33%. Это matched-live-PID estimate; короткоживущие процессы могут быть пропущены, snapshots не атомарны.

RDP trace:146 scale_rectangle calls,16492896pixels,42.246ms суммарно, p500.0808ms, p951.0265ms, failed0. Это прямоугольники, не146уникальных кадров; hooks не покрывают весь codec/encode/decode путь.

PW queue != encoded frame, wl_surface commit != LCD scanout. Частоты включают idle и не являются maximum GNOME FPS. Weston timeline не включался: пустой файл означает **не измерено**, не0FPS. Реальная input-to-photon задержка не измерена; приведён RTT D-Bus Notify. Частота LCD60Hz не засчитывается как60FPS.

## Postflight и сохранность

- Новых GPU/IOMMU faults нет. Единственная новая kernel строка во время GUI — нормальная загрузка qcom/a630_sqe.fw. Новых kernel errors не обнаружено.
- GPU после реального рендеринга **suspended**, проверено SSH и затем COM4. MSM оставлен загруженным, MDSS hold сохранён; MDSS/DISPCC/DSI/PHY непривязаны, MIPI DSI devices пусты. Новая аппаратная инициализация панели/LCDB/REFGEN не выполнялась.
- tty1 и SimpleDRM1080×2340 сохранены. SSH strict-host, NCM192.168.77.1/30 ↔192.168.77.2/30 и COM4 доступны. COM4 закрыт после диагностики.
- **Все17полей stat каждого из6UFS LUN совпали до GPU restore и после сеанса.** В19мониторинговых snapshots read/write/discard/flush counts также не менялись. Mounts/swap на UFS отсутствуют.
- Windows IPv4 interface/address/prefix sets совпали до/после. Агент не менял домашнюю сеть, DNS или routes.
- Системный /run до/после0:0:1777. Глобальный render node chmod/chown не выполнялся; использован отдельный private device inode.
- RDP secrets, sockets и временные rootfs удалены из RAM после выгрузки журналов. Постоянных изменений v8b нет. Исходные service процессы сохранены.

Резервная v2 проверена повторно:549080249bytes, SHA256 `88b81bbad652a7ef146031541f849a1e6520a324f671600528646d6c5fd3fedc`.
Пакет v2.1:548756171bytes, SHA256 `260dcb7493ccf70effa34e617ebf7314485068783bfdffc3739248ed5504fad9`.

Нет flash/reboot, изменений boot/recovery/dtbo/vbmeta, записи UFS, PMIC операций, изменений USB gadget или физических timings. Stage C/B остаётся **NO-GO** для повторной аппаратной инициализации дисплейного питания.

## Следующий шаг

Оставить v2 резервом; v2.1 зафиксировать как аппаратно подтверждённую C-сессию с известным GC critical. Следующая программная задача — офлайн-найти владельца ShellWindowTracker notify и корректный teardown; отдельно сохраняется Glycin sandbox blocker для недоверенных изображений. Производительность требует одинакового фиксированного сценария и нового отдельного разрешения. Сенсор — отдельный kernel/input bring-up. Дополнительных аппаратных тестов в этом задании не выполнялось.
