# GNOME Physical LCD v2.1 — память и методика производительности

## Измерено на телефоне: исходная v2

Источник `logs/gnome-physical-v2/20261107T053802561073Z/samples.txt`. Новый анализ: `memory-accounting.json`; код `userspace/gnome-physical-v2.1/memory-report.py`.

Один общий пиковый sample, uptime4920.49, 38 процессов; сумма PSS912835KiB = 891.4MiB. Это не сумма независимых максимумов компонентов.

| Группа в том же sample | PSS KiB | RSS KiB |
|---|---:|---:|
| GNOME Shell / Mutter | 165034 | 283884 |
| GRD | 132367 | 228128 |
| PipeWire | 2134 | 4468 |
| WirePlumber | 21118 | 58528 |
| Weston | 32960 | 48052 |
| Локальный RDP-клиент | 229383 | 244520 |
| Остальные, включая приложения | 329839 | 747164 |
| **Общий PSS** | **912835** | RSS не равен занятой физической RAM |

В группе Other: kgx104732KiB, Settings92214KiB, goa18540KiB, evolution-address13244KiB, два gjs12428/11971KiB, calendar11565KiB, ibus11526KiB, sources9307KiB, pulseaudio8067KiB. Полный список PID и start_ticks в JSON.

RSS исходного v2 получен из `/proc/PID/stat` ×4096: это приблизительный счётчик. Размер страницы подтверждён `config/linux-v8b.config`, CONFIG_ARM64_4K_PAGES=y. В v2.1 собирается точный `Rss` из smaps_rollup, а также Pss_Anon/Pss_File/Pss_Shmem/Private_Clean/Private_Dirty/Swap.

Минимальный MemAvailable в v2:1256284KiB. PSS не учитывает все распакованные tmpfs-файлы, framebuffer, unmapped dma-buf, память ядра и драйверов. RSS суммирует общие mappings повторно. PSS также опрашивается последовательно, не атомарно; исчезнувшие PID отмечаются. Максимумы разных сценариев (desktop/Console/Settings) разделены.

GRD+клиент занимали361750KiB PSS (~353.3MiB,39.6% общей суммы). Это не означает, что все эти страницы — дубликаты кадров. Один несжатый XRGB8888 кадр1080×2340 =10108800байт (~9.64MiB); неизвестное число буферов нельзя получать делением PSS на эту величину. Размеры actual chunks PipeWire и committed regions требуется трассировать отдельно.

Утечка памяти не доказана и не опровергнута одним коротким сеансом. Для проверки: одинаковые idle/apps/scenario, старт/стоп по одному разрешению, одинаковый warm-cache status, отдельный временной ряд каждого PID/start_ticks, учёт MemAvailable и tmpfs до/после. Не суммировать независимые пики и не сравнивать QEMU PSS с native FD610 как оптимизацию.

## Что уже видно в v2 frame logs

73 непустых PipeWire buffers/31.031s (~2.32 updates/s), максимум13 в секундном bin. 62 client Wayland commits/32.423s (~1.88/s), burst12. В тесте были idle-интервалы: эти числа не являются пределом FPS. LCD mode60Hz не измеряет скорость GNOME.

D-Bus input dispatch: median10.993ms, p95 108.915ms, max154.226ms. Это RTT вызова Notify, а не input-to-photon. FPS кодировщика, время decode и видимая задержка LCD в v2 не измерены.

## Воспроизводимый сбор v2.1

1. Только после отдельного разрешения: C,60s, тот же режим1080×2340, baseline; сначала фиксированные idle, затем одинаковые Console/Activities/Settings actions.
2. `-Measure` включает дополнительный `rdp-copy-trace.so` только в локальном клиенте. Он измеряет длительность и площадь interposed `freerdp_image_copy`, `freerdp_image_scale`, `nsc_process_message`. Не пишет пиксели, клавиши или реквизиты. ABI взят из заголовков используемого FreeRDP, ARM64 pixel-copy selftest проверяет неизменность результата.
3. Каждые2s controller сохраняет smaps_rollup и stat/start_ticks. CPU вычисляется по delta utime+stime/CLK_TCK, отдельно от PSS; повторно использованный PID не смешивается. Controller прекращает сессию при MemAvailable<512MiB, thermal>=75C или новом GPU/IOMMU fault.
4. Точки кадров: Shell/PipeWire queue; client wl_surface commit; Weston timeline repaint begin/posted. Они не отождествляются. Rectangles не равны уникальным frames. Если использован другой codec или inlined/static call, отсутствие hook событий означает «не наблюдалось», а не нулевую стоимость encode/decode.
5. `python userspace/gnome-physical-v2.1/summarize.py LOG_DIR`; `python userspace/gnome-physical-v2.1/memory-report.py LOG_DIR --page-size 4096`.
6. Для реальной задержки LCD нужна согласованная смена visual marker по input ID с captured frame matching либо внешняя high-speed camera. Одного D-Bus RTT недостаточно. GPU compositor timestamp и decode clocks необходимо сопоставлять по monotonic clock; нельзя вычитать произвольные wall-clock логи.
7. Сравнивать trace-on/off одинакового сценария: tracing сам имеет overhead. Указывать количество скопированных прямоугольников и pixels, repaint interval p50/p95, CPU и drops на каждой наблюдаемой границе отдельно.

Офлайн instrumentation regression `offline-release-deadline/metrics.json`:41 scale operations,5021696pixels,0failed. Это проверка работоспособности трассы в QEMU, не характеристика производительности телефона и не NSC benchmark. Возможен аппаратный encode/decode путь, не покрытый этими hooks.

## Оптимизация

Рабочие FD610, TLS/NLA, resolution и безопасность не менялись ради неподтверждённого ускорения. Основное изменение — устранение ошибок logout. Quiet profile остаётся явным выбором и только отключает анимации; выигрыш на телефоне для v2.1 не измерен. Переключение codec/resolution/camera profiles и native KMS не выдаются за выполненную оптимизацию.

Путь B/Devkit и A/native остаются отдельными исследованиями. В v2.1 их новый launcher блокирует до собственной регрессии. Рабочий C и неизменяемая v2 сохранены.
