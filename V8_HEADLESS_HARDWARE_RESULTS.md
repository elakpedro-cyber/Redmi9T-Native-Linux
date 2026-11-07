# v8b — аппаратная проверка headless Wayland

Redmi 9T NFC остался на Linux v8b. SSH с закреплённым host key, NCM и COM4 подтверждены. До испытания не обнаружено новых GPU/IOMMU ошибок. В этой загрузке список модулей пуст, в /dev/dri только card0 SimpleDRM. У Adreno нет render node, MSM ещё не загружен. По заранее утверждённому сценарию тест использует только существующий render node. [Предпроверка](logs/v8-headless-hardware/gates.txt).

Архив ARM64 116 573 498 байт проверен на ПК и после передачи SFTP в tmpfs /tmp. SHA-256 `724868f97a2e541c0f23e8f16c265651617ea0f4a18fcdb4f9bb6d9c415eb2ad`. Проверены зависимости shader probe через musl loader. Runtime изолирован через chroot, в него переданы только null/random/urandom, GPU и KMS nodes отсутствовали. Таймаут контрольного теста 18 с и ещё 3 с для принудительного завершения. [Проверка архива](logs/v8-headless-hardware/archive.txt) · [Зависимости](logs/v8-headless-hardware/dependencies.out).

| Этап | Результат |
|---|---|
| A. Weston headless/Pixman | **PASS на телефоне.** Weston 14.0.2, Pixman, headless backend. EGL, GL renderer и DRM render node в этой проверке не использовались. Код завершения 0. |
| B. EGL/GLES Freedreno | **Заблокирован** отсутствием render node. Mesa 26.1.6 входит в архив. EGL vendor и renderer на этой загрузке не опрашивались. Прежний FD610 результат Stage B остаётся отдельным аппаратным свидетельством. |
| C. Weston headless GL | **Заблокирован** той же предпроверкой. Аппаратный GL-композитинг Weston пока не подтверждён. |
| D. Клиент и кадр | **PASS с Pixman.** `weston-simple-shm` виден на PNG 320×240. Кадр получен из RAM через SFTP. SHA-256 на ПК и телефоне `54d1d7665f68ddc175fdb6fd9763187c91b7fe4f22120b7e4f0ffbe45c5c2924`. GPU-кадр в этой загрузке не получен. |

[Журнал Weston](logs/v8-headless-hardware/weston-test.log) · [Кадр](logs/v8-headless-hardware/lemon-headless.png) · [Аппаратный Freedreno Stage B](V8_STAGE_B_RESULTS.md).

После проверки SSH отвечает, ping 3/3, NCM carrier 1, COM4 ответил, UDC configured. Новых строк dmesg нет. MDSS, DISPCC, Host и PHY не получили driver bindings. MIPI-DSI bus пуст, класс подсветки отсутствует, LCDB не зарегистрирован. Физические напряжения не измерялись. Шесть UFS LUN имеют прежние счётчики, записи/discard/flush нулевые, дисковых mounts и swap нет. Все процессы chroot завершены, временный каталог удалён с проверкой. [После теста](logs/v8-headless-hardware/after.txt) · [UFS](logs/v8-headless-hardware/storage-check.txt) · [Удаление](logs/v8-headless-hardware/cleanup.exit).

## Следующий шаг

Отдельно согласовать загрузку штатного MSM из v8b в GPU-only режиме с уже проверенным удержанием MDSS через временный platform driver override. До загрузки проверить, что MDSS не привязан и DSI/PHY children отсутствуют; DISPCC оставить незагруженным. После получения Adreno render node выполнить один короткий shader и, если стабильность подтверждена, один Weston GL с обязательным renderer check и PNG. Любой software renderer, timeout, GPU/IOMMU fault или потеря USB прекращает прогон. Затем можно готовить headless Wayland-сессию для UI и ввода через отдельный согласованный канал. Физический дисплей остаётся отдельной работой, Stage C/B **NO-GO**.
