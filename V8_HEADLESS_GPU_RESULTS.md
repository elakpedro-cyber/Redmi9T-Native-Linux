# v8b — аппаратный headless Freedreno и Weston GL

**Итог.** На Redmi 9T NFC штатный MSM создал GPU-only DRM устройство. Freedreno FD610 выполнил GLES shader. Weston 14.0.2 использовал аппаратный GL на том же render node и сохранил проверенный Wayland-кадр без KMS/DSI. Linux v8b оставлен работающим, Stage C/B **NO-GO**.

## Предпроверка и изоляция

SSH проверен со сверкой host key, COM4 ответил, NCM carrier 1. До загрузки только SimpleDRM card0, MDSS/DISPCC без драйверов, DSI Host/PHY platform devices отсутствуют, MIPI DSI bus пуст. Live DT оставляет DPU и подсветку disabled, у DSI нет panel child. В регуляторах отсутствует LCDB. [Снимок](logs/v8-headless-gpu/before.out) · [Предпроверка](logs/v8-headless-gpu/binding-preflight.out).

В ядре v8b `separate_gpu_kms=1` отделяет GPU DRM от KMS, но init MSM регистрирует также MDSS, DSI и другие platform drivers. MDSS создаёт дочерние устройства в своём probe. До единственного `modprobe msm separate_gpu_kms=1` установлен и проверен `driver_override=lemon-stage-b-hold` на уже непривязанном MDSS. Это запретило сопоставление с `msm-mdss` без unbind, выключения или изменения DT. Отдельный DISPCC не входит в modules.dep MSM и остался незагруженным. GPU использует GPUCC/GCC, RPM VDDCX, GPU GDSC через GMU wrapper, Adreno SMMU. VDDCX является общей зависимостью SoC, самостоятельного включения display provider эта цепочка не требует. [Исходники](logs/v8-headless-gpu/source.txt) · [DT зависимости](logs/v8-headless-gpu/gpu-dt-providers.txt) · [Render node](logs/v8-headless-gpu/msm-once.out).

## Результаты

| Проверка | Наблюдение |
|---|---|
| MSM и render node | Единственный modprobe завершился с кодом 0. Параметр прочитан как 1. `/dev/dri/renderD128` 226:128 привязан к Adreno `5900000.gpu`, MSM 1.13.0. SimpleDRM сохранился. |
| Freedreno | EGL 1.5, OpenGL ES 3.2 Mesa 26.1.6, FD610, код 0. 256 проверенных RGBA пикселей. SHA-256 `ebec48648edef1e298a2e12473d1c837bfc6ce99151088606b4cda794434b9cb` совпал с эталоном и скачанным файлом. |
| Weston GL | Weston 14.0.2, headless backend, EGL vendor Mesa Project, EGL 1.5, GLES 3.2 Mesa 26.1.6, GL renderer FD610. Журнал и открытый FD процесса подтвердили `/dev/dri/renderD128`. Режимы Pixman, llvmpipe и softpipe не использованы. |
| Wayland-кадр | `weston-simple-shm` виден на PNG 320×240, снятом `weston-screenshooter` из GL output. SHA-256 локального и RAM-файла `046abf848e6664247f5df1264a024669a4d1419db0f95f8282677e0c29d968cd`. Сценарий завершился с кодом 0. |

[Лог shader](logs/v8-headless-gpu/shader-gbm-path.out) · [Журнал Weston](logs/v8-headless-gpu/weston-gl.log) · [GL-кадр](logs/v8-headless-gpu/lemon-headless-gl.png).

## Ошибки запуска и восстановление

Исходный chroot предоставил render node, но Mesa не смогла получить device info без sysfs. Следующий запуск в обычном namespace завершился до отрисовки, поскольку загрузчик GBM искал `dri_gbm.so` в системном пути. После задания RAM-путей для GBM/DRI выполнена одна успешная отрисовка. Первый запуск Weston завершился на загрузке `libexec_weston.so.0`, до инициализации GL. Добавление каталога Weston в путь библиотек позволило провести один успешный GL-прогон. Временные переменные окружения касались только тестовых процессов. Новых монтирований, копирования библиотек в системные каталоги или повторной загрузки MSM не было.

Weston сообщил об отсутствии двух desktop assets и cursor themes, а при штатной остановке по TERM вывел предупреждение о layer с views. Кадр сохранился, тестовые процессы завершились. Логи и PNG забраны через SFTP, RAM-каталог удалён с проверкой. [Неудачный EGL в chroot](logs/v8-headless-gpu/shader-log.out) · [GBM loader](logs/v8-headless-gpu/shader-host.err) · [Weston loader](logs/v8-headless-gpu/weston-gl.err) · [Финальный stderr](logs/v8-headless-gpu/weston-gl-fixed.err) · [Очистка](logs/v8-headless-gpu/cleanup.out).

## Стабильность

- SSH доступен, COM4 ответил, UDC configured, NCM carrier 1 и ping 3/3. Adreno вернулся в runtime suspend. MSM оставлен загруженным, override MDSS сохранён до перезапуска.
- Новых GPU/IOMMU faults нет. В dmesg появились ожидаемые предупреждения dummy vdd/vddcx, инициализация MSM и загрузка SQE firmware. Эти предупреждения относятся к Adreno и уже наблюдались на Stage B.
- MDSS и DISPCC остались без привязки, display clock provider не зарегистрирован, DSI Host/PHY не появились, MIPI DSI bus пуст, backlight class и LCDB regulators отсутствуют. Debugfs не был смонтирован, прямые счётчики display clocks, состояние `mdss_gdsc` и уровни физического питания не измерялись.
- Шесть UFS LUN имеют прежние счётчики, запись/discard/flush нулевые, дисковых mounts и swap нет. Образ v8b сохранил прежний SHA-256.

[Сравнение](logs/v8-headless-gpu/comparison.txt) · [Снимок после теста](logs/v8-headless-gpu/final.out) · [Разница dmesg](logs/v8-headless-gpu/dmesg-delta.txt).

## Следующий шаг без физического дисплея

Офлайн упаковать проверенный RAM launcher с путями GBM/DRI и модулями Weston, добавить явные пути ресурсов desktop shell и тест корректного завершения. Затем подготовить отдельный согласуемый запуск минимального UI через headless compositor с передачей кадров по USB и отдельно проверенным каналом ввода. Для физической панели остаются действующие блокеры Stage C/B.
