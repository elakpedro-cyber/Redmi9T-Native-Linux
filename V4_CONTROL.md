# Контрольная рабочая сборка v4

2026-11-05 на реальном COM3 подтверждены `7.4.0-rc1-lemon-bringup-v4`,
`LEMON_INIT_V4_REACHED`, EL1 bootshim, шесть Micron UFS LUN, таблицы разделов,
ACM shell и simpledrm. Live `/proc/config.gz` считан Base64 и побайтово совпал
с config/linux-v4.config. SHA конфигурации:
`fbac36349b9e9667049eea53ffbe8b5ce8b70716a0b621fd6baeeb3b3bb5b6b7`.

Контрольный снимок: `snapshots/v4-known-good/`, 332 файла с проверенным
MANIFEST.json. Включены bootshim, конфиги, скрипты, исходные архивы Linux и BusyBox,
артефакты v4, используемый mainline DTB, отчёты и первые live-логи этой сессии.
Снимок не перезаписывается сборкой v5. Позднее считанные полный live DTB и config
и остальные live-логи сохранены отдельно в `snapshots/v4-live-supplement/`.
Toolchain/WSL и промежуточные объекты не копировались; их версии/пути описаны в сборочных скриптах и отчётах.

Контрольный образ: artifacts/boot-linux-test-v4.img, 9576448 байт.
SHA-256: `4cf10f2a9c6d7298e46aec7afdcc64421b532705d29bbbf7b703ae2c90bffa45`.
Сохраняется и копия snapshots/v4-known-good/artifacts/boot-linux-test-v4.img.

## Ограниченная проверка UFS чтением

Прочитаны только первые 16384 байта каждого из sda–sdf, два раза с паузой 20 секунд.
Все шесть результатов совпали по SHA; GPT signature находится по смещению 4096,
CRC каждого primary GPT header корректен. Значения offsets/size в sysfs /stat
считаются в 512-байтных секторах, несмотря на logical_block_size=4096.

На всех LUN ioerr_cnt уже был 3 и остался 3. Причина начальных ошибок не установлена;
нельзя называть счётчики нулевыми. Новых сообщений об I/O timeout/reset в интервале
не появилось. Счётчики completed writes и sectors written остались нулевыми.
В /proc/mounts нет UFS-разделов.

Это небольшие buffered reads; повтор мог обслуживаться page cache. Это не
длительный стресс-тест, direct-I/O, проверка всего носителя или suspend/resume.
Изначальная попытка head -c не выполнилась: этот applet v4 не поддерживает -c.
После проверки на ПК использован `hexdump -v -n 16384`, без dd и без sysfs writes.

Доказательства: logs/v4-live-diagnostics/*.raw и *.json,
reports/v4-live-read-audit.json, reports/v4-live-config-proof.json,
reports/live-v4.dtb. Время наблюдения и uptime находятся в исходных логах.
COM3 закрывался в finally после каждого сеанса; чужие процессы не завершались.
