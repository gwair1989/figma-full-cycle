# Установка, диагностика и завершение

Для проверки toolchain, capabilities и JSON v5 сначала использовать [device-hub.md](device-hub.md). Не разбирать человекочитаемую таблицу `devicectl` как стабильный формат.

## Выбор сборки

Сохранить текущие version/build, источник установки и состояние данных до замены. Различать configuration (Debug/Release) и signing channel (development/Ad Hoc/App Store/TestFlight). Release может быть development-signed.

Для исследования уже установленного приложения без замены достаточно доступных read-only metadata/сведений UI. Если точечный запрос приложений пуст, это не доказывает отсутствие приложения: сверить `device info apps --help`, при необходимости получить `--include-all-apps` и локально выделить нужный bundle ID из JSON. Этот флаг в проверенной версии CLI игнорирует остальные фильтры; полный список содержит посторонние приложения и идентификаторы, поэтому в отчёт переносить только минимальные сведения целевого приложения. `builtByDeveloper=false` не различает App Store и TestFlight; неизвестный источник установки оставить неизвестным.

Для локальной установки использовать build/run script текущего проекта, если он подходит, и его правила cache lifecycle. Иначе подготовить device build через xcodebuild с существующим workspace/project, scheme, target, signing team и повторно используемым DerivedData. Не подставлять сведения из предыдущего проекта.

Команды ниже — шаблоны; переменные задаются из обнаруженного окружения. DEVICE_ID подходит devicectl, UDID — hardware identifier для libimobiledevice. Сверить текущий --help и JSON schema CLI.

```sh
xcrun devicectl list devices --json-output "$EVIDENCE/devices.json"
xcrun devicectl device info apps --device "$DEVICE_ID" \
  --bundle-id "$BUNDLE_ID" --include-default-apps \
  --json-output "$EVIDENCE/app-before.json"
```

В многодевайсном списке явно сопоставить hardware UDID, CoreDevice ID и модель. DeveloperApp/ContainerAccessible в metadata не доказывают источник установки, get-task-allow или фактическую возможность debugger/container access после замены на TestFlight.

Если нужна копия доступного контейнера до замены:

```sh
xcrun devicectl device copy from --device "$DEVICE_ID" --source . \
  --destination "$BACKUP_DIR" --domain-type appDataContainer \
  --domain-identifier "$BUNDLE_ID" --timeout 120
```

Проверить exit status и результат. App-container copy не является полным device backup; не включает все Keychain/iCloud данные, может быть несогласованной при активных записях, доступна не для каждого приложения. Ограничить локальные права на копию. Не обещать rollback без доступной исходной сборки, совместимых данных и проверенного restore.

Для development-сборки при подходящих capabilities можно использовать обычные command-line overrides CODE_SIGN_STYLE=Automatic, DEVELOPMENT_TEAM, CODE_SIGN_IDENTITY="Apple Development", пустой PROVISIONING_PROFILE_SPECIFIER. Условные CLI settings вида SETTING[sdk=...]=... не переносить из .xcconfig вслепую: проверить effective values. Provisioning updates выполнять в рамках доступного аккаунта и запроса. Release settings репозитория ради одноразовой установки менять не требуется.

Проверить signing identity, embedded profile, ProvisionedDevices/срок и нужные entitlements. Успешная компиляция не доказывает installability. Ошибка 0xe800801f с текстом Beta profile without proper entitlement требует исследования профиля/entitlements, а не переустановки циклом; один код не определяет универсальную причину.

APP_PATH получить из TARGET_BUILD_DIR + WRAPPER_NAME правильного target, bundle ID — из продукта. Установка и запуск — отдельные проверяемые шаги:

```sh
xcrun devicectl device install app --device "$DEVICE_ID" \
  --json-output "$EVIDENCE/install.json" "$APP_PATH" \
  > "$EVIDENCE/install.log" 2>&1
```

После успешного install подтвердить version/build, затем запуск:

```sh
xcrun devicectl device process launch --device "$DEVICE_ID" \
  --json-output "$EVIDENCE/launch.json" "$BUNDLE_ID" \
  > "$EVIDENCE/launch.log" 2>&1
```

Проверить данные и ожидаемый экран. Для TestFlight/App Store/чужого приложения сохранить выбранный пользователем канал; внешнее UI-управление не требует автоматически пересборки AUT. Uninstall удаляет данные и не заменяет update.

[Apple CLI](https://developer.apple.com/documentation/xcode/interacting-with-devices-using-the-command-line), [Developer Mode](https://developer.apple.com/documentation/xcode/enabling-developer-mode-on-a-device).

## Логи

| Источник | Что проверять |
| --- | --- |
| Hub → Reports | Время/процесс/build конкретного crash report; список не является live log |
| Console на Mac | Правильный iPhone, Start, фильтр process/subsystem, свежие события |
| idevicesyslog | Совместимый CLI, hardware UDID, реальное имя процесса, обновление файла |
| devicectl launch --console | stdout/stderr нового запуска; это не полный unified log |
| Crash/Jetsam report | Время, build, причина завершения, соответствующий dSYM для символикации |

До установки нового диагностического stack проверить встроенные Reports, More Actions → Show in Finder (DeviceFS), `device info mountpoint` и доступный домен `systemCrashLogs`. Для системного сбоя при необходимости использовать Collect sysdiagnose / `device sysdiagnose --help`; это отдельный сбор с временем и расходом ресурсов, не обязательный шаг каждого UI-теста. Сведения о профилях доступны в Info → Profiles; logging profile и его удаление учитывать отдельно. DeviceFS не расширяет права на app container.

Если libimobiledevice уже доступен, запускать foreground collector в управляемой сессии и записывать её ID/PID:

```sh
idevicesyslog -u "$UDID" -p "$PROCESS_NAME" --no-colors \
  > "$EVIDENCE/device-process.log" 2>&1
```

UI выполнять из другой сессии. После install/relaunch проверить новые timestamp и известное логируемое действие. Живой PID или непустой файл могут принадлежать stale stream. При stale capture перезапустить только свой collector и повторить проверку; пустой лог не доказывает отсутствие ошибок.

Для нового запуска с stdout/stderr, когда запуск разрешён сценарием:

```sh
xcrun devicectl device process launch --device "$DEVICE_ID" --console \
  --json-output "$EVIDENCE/console-launch.json" "$BUNDLE_ID" \
  > "$EVIDENCE/app-stdio.log" 2>&1
```

Существующему процессу streams этим флагом не переподключаются. --console ждёт завершения процесса и передаёт catchable signals приложению: Ctrl-C может изменить lifecycle AUT. Использовать файл для --json-output, не stdout '-'; проверять контракт своей версии CLI.

Error/Fault severity системного framework в процессе не является автоматически багом приложения. Коррелировать с действием, временем и симптомом. Signal 9 при install/replacement также не доказывает crash. Сырые логи, идентификаторы, личные фото и account data хранить локально; в отчёт выносить необходимые очищенные фрагменты.

[Console](https://support.apple.com/guide/console/view-log-messages-cnsl1012/mac), [crash reports](https://developer.apple.com/documentation/xcode/acquiring-crash-reports-and-diagnostic-logs), [idevicesyslog](https://github.com/libimobiledevice/libimobiledevice/blob/master/docs/idevicesyslog.1).

## Coverage manifest и баги

```markdown
Run: <date/time/timezone>; device/iOS/macOS/Xcode/tools: <versions>
App: <bundle ID/version/build/source>; install: <outcome/evidence>
Initial state/data: <fixture or existing>; allowed changes: <scope>
Hub/device configuration: <appearance/text size/accessibility/location/orientation; keyboard modes; relevant overrides>
Logger: <source/session/verified freshness>
| Route/state | Entry → exit | Checks, scroll ↓/↑ | Result | Evidence | Recovery/blocker |
| --- | --- | --- | --- | --- | --- |
| ... | ... | ... | passed/failed/blocked/not-run | ... | ... |
Uncovered: <states and reasons>
Final: <screen/data/build/configuration restored or remaining changes>; sessions: <stopped/remaining>; backups/cache: <disposition>
```

Для бага сохранить build/channel, начальное состояние, точные шаги, expected/actual, повторяемость, evidence и уверенность. Клик пустой части строки против клика по тексту, смена масштаба и другой канал — разные контрольные условия. Совпадение через Hub и Mirroring усиливает гипотезу, но общий CUA ещё не исключён; физическое касание или XCTest помогают изолировать причину.

Закрыть тестовые drafts без сохранения, если сохранение не было частью сценария; остановить собственные collectors с учётом forwarding signals. Указать оставленные screen sessions, сборку, изменения данных, backup и build cache. Не чистить чужие/неизвестные caches.
