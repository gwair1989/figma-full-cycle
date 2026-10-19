# Device Hub: окружение и возможности

Проверено по документации Apple и локальному Xcode 27.1 / devicectl 651.13.5 на 2026-10-18. Это исходная точка, а не требование использовать конкретную версию или модель. При обновлении сверять локальный `--help`, capabilities выбранного target и release notes установленной версии.

## Предварительная проверка

1. Сопоставить `xcode-select -p`, возможный `DEVELOPER_DIR`, `xcodebuild -version`, `xcrun devicectl --version` и версию запущенного Device Hub. При нескольких Xcode bundle ID может открыть другую копию: выбрать приложение из нужного Xcode по абсолютному пути. Глобально переключать toolchain ради проверки не требуется.
2. Выбрать **Physical Devices** в фильтре sidebar при необходимости; сопоставить модель, OS и UDID. CoreDevice ID — другой идентификатор. В Info → Edit Visibility можно показать скрытые свойства; имена устройств не обязательно уникальны.
3. Прочитать `device info details`: pairing, transport, connection, Developer Mode и `capabilities`. Connected, готовность developer services, доступ к экрану и работа ввода — разные проверки. Команда может вернуть сохранённые сведения, даже если подключиться не удалось; сверять status/timestamp и результат живого запроса.
4. Проверить нужный сервис через read-only `info` перед изменениями. Отсутствующая capability и ошибка «not supported» не лечатся серией reconnect. Наличие подкоманды в CLI не означает поддержку физическим target.

Примеры после проверки локальной справки; `DEVICE_ID` и `EVIDENCE` задать из текущего прогона, папку evidence создать заранее с ограниченными правами:

```sh
xcrun devicectl device info details --device "$DEVICE_ID" --json-output "$EVIDENCE/device-details.json"
xcrun devicectl device info lockState --device "$DEVICE_ID" --json-output "$EVIDENCE/lock-state.json"
xcrun devicectl device info displays --device "$DEVICE_ID" --json-output "$EVIDENCE/displays.json"
xcrun devicectl device info appearance --device "$DEVICE_ID" --json-output "$EVIDENCE/appearance.json"
```

В JSON v5 сведения сгруппированы в `result.properties` (`connection`, `hardware`, `software`, `state`). Старые `connectionProperties`, `hardwareProperties`, `deviceProperties` deprecated; учитывать `info.jsonVersion` и `_deprecationNotice`, а не разбирать текстовую таблицу. Новые CLI поддерживают `--json-output -`, но отдельные команды совмещают stdout с другими данными: например, `process launch --console` требует файл. Для сохраняемого evidence файл удобнее в обоих случаях.

`lockState` читать буквально: `unlockedSinceBoot` означает разблокировку после старта, а не гарантирует текущую готовность к вводу. Сопоставлять с `passcodeRequired` и живым экраном. Не переносить размеры framebuffer из `displays` в CUA без нового определения геометрии окна.

## Подключение

Проводное подключение: USB → штатный Trust на iPhone → pairing/Developer Mode по указаниям Hub. Для уже paired устройства повторный trust/reset не нужен. Установка приложения и View Screen проверяются отдельно.

Для нового беспроводного pairing iPhone/iPad Apple указывает iOS/iPadOS 27+: **+ → Pair Nearby Device…**, одна Wi-Fi сеть и действия владельца по подсказкам. Работа через Wi-Fi после проводного pairing — отдельный сценарий; Apple указывает поддержку IPv6 в сети. При ошибке обнаружения проверить доступ Mac-приложения к локальной сети и состояние pairing; не отключать firewall целиком. После обновления OS при потере связи проверить, не требуется ли повторное pairing.

Требования iPhone Mirroring — Apple Account, 2FA и заблокированный телефон — не являются общими prerequisites Device Hub. View Screen может работать при разблокированном телефоне. При camera/microphone конфликте следовать [control.md](control.md), не объявлять это ошибкой USB.

## Инспекторы и конфигурация прогона

| Раздел Hub | Что использовать |
| --- | --- |
| Settings | Appearance, Liquid Glass, Text Size, accessibility и Location, доступные конкретному target. Записать исходные значения, менять только в пределах задачи, затем восстановить и проверить. Это может менять сам телефон, а не только картинку Mac. |
| Reports | Найти crash/диагностический отчёт по времени и процессу; получение списка не заменяет чтение и символикацию конкретного отчёта. |
| Info → Info | OS, модель, идентификаторы, дополнительные свойства через Edit Visibility. |
| Info → Apps | Поиск установленной app, фильтр Developer/другие доступные фильтры; установка и доступ к данным зависят от прав. |
| Info → Profiles | Установленные configuration/provisioning profiles; логирующий профиль использовать для конкретной диагностики и учитывать его срок/удаление. |
| More Actions → Show in Finder / Collect sysdiagnose | DeviceFS для доступных файлов и sysdiagnose при системном сбое; собирать только нужное, сырые данные хранить локально. |

Начать с доступных read-only инспекторов. Для багов, зависящих от окружения, добавить в матрицу только релевантные варианты: light/dark, обычный/крупный Dynamic Type, Reduce Motion/Transparency, orientation. Не менять весь набор настроек автоматически и не переносить все simulator controls на физический iPhone.

Zoom меняет масштаб окна Mac; Resize Mode меняет размеры сцены приложения и требует отдельной поддержки. DeviceFS/`info mountpoint` не обходят права контейнеров. Download Container не гарантирует готовый `.xcappdata`: перед использованием в Xcode Run проверить структуру `<name>.xcappdata/AppData/{Documents,Library,tmp}` и совместимость данных. Подробнее об установке и диагностике — [deploy-and-logs.md](deploy-and-logs.md).

## Проверка известных проблем по версии

Перед повторными пробами сопоставить установленную версию с конкретным issue в release notes. Запись «fixed» в более новой beta не означает, что исправление есть в установленном stable, и сходство симптомов само по себе не доказывает причину.

На 2026-10-18 Apple перечисляет в **Xcode 27.2 beta 2** исправления:

- прекращения touch/button-ввода после простоя — `182695157` / `FB23873443`;
- неверного направления modifier keys при нескольких device windows — `177181719`;
- сохранения hardware-keyboard mode до двух минут после отключения — `182553164`.

Для похожего отказа на 27.1 сохранить версии, время простоя, число открытых окон и различающие контрольные действия. Ограниченный recovery из [control.md](control.md) остаётся рабочей процедурой. Проверку новой версии проводить как отдельный эксперимент в согласованном окружении; не обновлять Xcode или iOS автоматически ради предположения.

В notes Xcode 27 также отмечены отсутствие двухпальцевого touch, неработающий Shake и невидимость color filter физического устройства в картинке Hub. Это ограничения разных функций; wheel/trackpad transform не подтверждает настоящий multitouch. Для старых OS отдельно проверять минимальную версию **input**, а не только deployment/debugging: у Xcode 27 эти границы различаются.

## Источники

- [Device Hub и инспекторы](https://developer.apple.com/documentation/xcode/device-hub).
- [Подключение и управление устройствами](https://developer.apple.com/documentation/xcode/managing-your-simulated-and-physical-devices-in-device-hub).
- [Управление приложениями](https://developer.apple.com/documentation/xcode/managing-apps-on-devices).
- [devicectl, JSON и DeviceFS](https://developer.apple.com/documentation/xcode/interacting-with-devices-using-the-command-line).
- [WWDC26: Get the most out of Device Hub](https://developer.apple.com/videos/play/wwdc2026/260/).
- [Xcode 27 notes](https://developer.apple.com/documentation/xcode-release-notes/xcode-27-release-notes), [27.1 notes](https://developer.apple.com/documentation/xcode-release-notes/xcode-27_1-release-notes), [27.2 beta notes](https://developer.apple.com/documentation/xcode-release-notes/xcode-27_2-release-notes).
