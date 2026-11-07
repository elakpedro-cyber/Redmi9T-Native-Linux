# GNOME Physical LCD v2.1 — реальные предупреждения

Исходные аппаратные журналы: `logs/gnome-physical-v2/20261107T053802561073Z/`. Они не заменены офлайн-логами. Новая версия проверялась только на ПК: `logs/gnome-physical-v2.1/`. Нового аппаратного испытания не было.

## Исправленные причины

| Сообщение и исходный журнал | Причина и влияние | Изменение | Проверка |
|---|---|---|---|
| `Client4 failed to reply before timeout`, shell.log:67 | Фактический Shell регистрируется в Session48 через ранее добавленный в ресурс `_notifyGnomeSessionReady`, но не отвечает на ClientPrivate. Отдельный wrapper регистрировал второй клиент. Это мешало штатному logout. | Убран второй wrapper. Настоящий Shell отвечает на QueryEndSession/EndSession, завершает context один раз. Обычный `org.gnome.Shell.desktop`. | Разобраны реальные main.js и ClientPrivate ID; ARM64 C TERM/INT/deadline: logout без timeout, Session reaped. |
| `scale-x/scale-y inf`, shell.log:42–44 | В `WindowPreview.showOverlay` деление на нулевой размер. Возникало до остановки, поэтому одним порядком cleanup не исправляется. | Проверка ненулевого размера; нейтральный scale при нулевой геометрии. | GNOME с Console, Activities и Settings под ARM64 QEMU, ошибка не повторилась. |
| disposed WindowPreview, sibling parent assertion; no logical monitor, shell.log:47–62 | GRD и клиент завершались до Shell: виртуальный монитор исчезал при работающих previews. Есть также возможность restack после destroy. | Logout Shell, затем GRD, WirePlumber, PipeWire; далее клиент, Weston, system bus. Restack проверяет живого actor/parent. | Полные C-прогоны, lifecycle-логи. Нет этих critical в успешных финальных прогонах. |
| disposed ScreenSharingIndicator в промежуточном офлайн-прогоне | Callback и таймер переживали actor. | `connectObject` с владельцем; удаление таймера на destroy. | Финальный TERM/INT/deadline без повторения. |
| `GLib.unix_signal_add moved`, shell.log:7 | Устаревший API в удалённом wrapper, не в Mutter. | Удалён дублирующий wrapper; не маскировка GJS log. | Новый launcher не использует эту функцию. |
| `BIO_new failed for certificate`, rdp.log:1 | Два отдельных `grdctl` устанавливали key/cert последовательно; промежуточное состояние TLS неполное. | Оба пути GSettings записываются одной delayed/apply транзакцией до работы grdctl. TLS, NLA и pin остаются. | Новый ARM64 RDP connection и кадры; BIO_new отсутствует. |
| `g_close(fd:0) ... EBADF`, rdp.log:21 | GRD50.1 обнулял структуру fd; EGL error cleanup считал 0 валидным descriptor. | Два fd инициализируются `-1` в `grd_egl_thread_new`. Собран отдельный GRD из официального 50.1. | `grd-egl-negative.txt`: исходник воспроизводит закрытый stdin и EBADF, исправленный сохраняет fd0 при том же отказе. |
| Broken pipe / failed DisconnectProviderUltimatum / client TERM, rdp.log:33–34 и client.log:18–21 | Ранее клиент принудительно закрывался первым. | Упорядоченное серверное завершение до клиента. | Финальный GRD пишет server stopped. Обычный `ERRINFO_RPC_INITIATED_DISCONNECT` при штатном logout сохраняется и не считается GPU fault. |

Патчи применяются через приватный `G_RESOURCE_OVERLAYS` и замену GRD только внутри RAM-root. Исходные ресурсы, их SHA и патчи: `userspace/gnome-physical-v2.1/shell-ui/manifest.json`, `*.patch`. Это исправление фактической сборки проекта; нельзя автоматически приписывать её дополнительный session-код чистому upstream Shell.

## Оставшиеся сообщения и ограничения

| Компонент / фактическое сообщение | Причина / уверенность | Влияние и действие | Как проверить дальше |
|---|---|---|---|
| Session48: systemd environment/unit/reset errors, fallback, null tracking | OpenRC, нет systemd user/logind; доказано D-Bus errors | Не блокирует ограниченную сессию. Не создавать фиктивный systemd и не устанавливать его ради чистого stderr. Null tracking не подходит как доказательство полноценной seat security. | Полный login/seat lifecycle отдельно от этого RAM-сеанса. |
| Shell/Mutter: colord absent | Служба не включена; доказано | Нет управления цветовыми профилями, стандартный вывод работает. | Добавлять colord только при необходимости, отдельный service test. |
| Shell: GDM RegisterSession/RegisterDisplay | GDM отсутствует; доказано | Нет display-manager integration. Штатная сессия проекта запускается без GDM. | Не подменять GDM фиктивным D-Bus endpoint. |
| Shell: IBus portal exited / AuthenticationAgent / PolicyKit1 / network permission | Изолированная системная шина не содержит полноценного polkit и host services. IBus конкретный exit требует отдельного разбора. | Привилегированные Settings и сложные IME не подтверждены; сетевые настройки хоста не выдаются сессии. Исправлять отдельно, не ослабляя policy. | Сохранить stderr IBus и service ownership; тест агента с настоящей policy. |
| Shell: GeoClue2 absent | Нет location service; доказано | Геолокация недоступна. Не включать ради удаления warning. | Только при появлении задачи геолокации. |
| accountsservice: user null, uid -1 | Нет полноценного AccountsService на приватной system bus; источник известен, точная ветка lookup не трассировалась | Отдельные account settings не подтверждены. | Запуск настоящей службы с приватным state и проверка lookup, отдельно. |
| Glycin: running without sandbox | Факт из журнала; точная причина выбора sandbox в этом пакете НЕ установлена | Открытый security blocker для недоверенных изображений. v2.1 не добавляет GLYCIN_SANDBOX=off, не выключает защиту и не скрывает warning. | Исследовать точный Alpine build и sandbox subprocess/namespace policy до повседневного использования. |
| GRD: TPM unavailable, GKeyFile fallback | TPM в namespace не предоставлен; доказано | Реквизиты только в приватном RAM home 0700, пароль stdin, key0600, удаляются. Не является отключением TLS/NLA. | Проверять права и удаление RAM credentials, не объявлять TPM работающим. |
| GRD: EGL driver fd -1 / Zink / dri2 errors | Отказ отдельного optional EGL path GRD; это не доказательство отказа FD610 у Shell | Hardware video encoding GRD не подтверждён. Shell guard остаётся жёстким. Нельзя объявить GRD аппаратным кодировщиком. | Отдельно трассировать выбор EGL device GRD без ослабления Shell guard. |
| FreeRDP: WITH_VERBOSE_WINPR_ASSERT | Параметр официальной используемой сборки; доказано | Возможны накладные расходы; защита assert не снимается без измерений. | Отдельное сравнение одинаковых сборок, не новый аппаратный benchmark сейчас. |
| wlfreerdp3 deprecated | Предупреждение upstream | Рабочий клиент сохранён. SDL3 не подставляется без регрессии ввода/VT. | Будущий отдельный client migration. |
| Kerberos default realm missing | Локальная NLA-аутентификация не использует Kerberos realm | TLS/NLA не выключены, локальное соединение успешно. | Уточнить supported auth-package options до изменения negotiation. |
| FUSE device absent, cliprdr file cleanup | В приватный /dev не выдаётся FUSE; опциональная file redirection | Не монтировать FUSE/не загружать модуль. Передача изображения/ввода не зависит от drive redirection. | Точно отключать ненужный channel только после проверки FreeRDP CLI, не угадывать флаг. |
| pthread_setschedprio not implemented | musl / WinPR scheduler API | Нет подтверждённого real-time scheduling. Не менять глобальные priorities. | CPU/frame pacing в следующем согласованном тесте. |
| PipeWire и WirePlumber RTKit absent | RTKit не предоставлен на приватной system bus | Работают без RTKit; scheduling limits остаются известным ограничением. | Если потребуется RT, отдельная безопасная служба и проверка прав. |
| libcamera IPA public key invalid; dma-buf provider absent | Запущен camera monitor в окружении без camera/dma-heap devices | Камеры не работают. Причина invalid key не исправлена фиктивным ключом. | Можно ограничить профиль только screen sharing через supported WirePlumber features после отдельной регрессии. v2.1 не меняет профиль камеры ради скрытия ошибки. |
| Weston no input devices | /dev/input намеренно не передаётся | Физический сенсор не работает; это не сбой SimpleDRM. | Отдельный allowlist подтверждённого touchscreen после kernel bring-up. |
| CalendarServer lost name on shutdown | Исчезновение session bus при выходе | Ожидаемо только после logout. | Сопоставлять с порядком выхода, не считать нормальным при активной сессии. |

Ни один журнал не очищается фильтрацией предупреждений; stderr компонентов сохраняется. Оставшиеся служебные и security ограничения не позволяют объявить окружение законченным повседневным GNOME phone.

## Источники

- Реальные ресурсы из frozen `libshell-18.so`: `logs/gnome-physical-v2.1/actual-*.js`.
- [GNOME Session48 manager](https://github.com/GNOME/gnome-session/blob/48.0/gnome-session/gsm-manager.c): QueryEndSession/EndSession и timeout.
- [Официальный GRD50.1 source](https://download.gnome.org/sources/gnome-remote-desktop/50/gnome-remote-desktop-50.1.tar.xz): `src/grd-egl-thread.c`, `grd-ctl.c`, `grd-rdp-server.c`.
- [WirePlumber video configuration](https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/video.html): отдельные camera monitors. Это основание для будущей конфигурации, не измеренный выигрыш v2.1.
