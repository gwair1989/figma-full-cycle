# Повторяемые сценарии и дополнительные инструменты

Device Hub остаётся основным каналом исследовательского прохода; Mirroring — запасным. Дополнительный stack выбирать, когда нужны locators, assertions, управляемые жесты или диагностические services. Его установка не входит автоматически в любой UI-прогон.

| Вариант | Применение и граница |
| --- | --- |
| Native XCTest UI runner | Элементы, ожидания, жесты; нужен подписанный runner на trusted device, WDA не нужен |
| Appium XCUITest + WebDriverAgent | WebDriver и повторяемые сценарии; подписать WDA отдельно от AUT |
| Appium Inspector | Просмотр элементов и разработка сценариев; требует подготовленных server/driver/WDA |
| pymobiledevice3 | Диагностика и дополнительные device services; отдельный pilot, совместимость проверять |

Начать с имеющихся Hub/Console/devicectl и logger. Подпись automation runner и подпись app under test — разные сущности; preinstalled приложение не требуется автоматически пересобирать. У Appium есть real-device конфигурация с udid, bundleId и noReset=true. Проверять фактические права отдельно от metadata.

Для XCTest/Appium предпочитать accessibility identifiers, bounded waits, hittable и видимый результат. exists не гарантирует возможность нажать. Для управляемой скорости изучить текущие XCTest swipeUp(velocity:) / Appium mobile:swipe; каждый жест всё равно подтверждать на устройстве. mobile:scroll имеет ограничения надёжности.

При повторных Appium-сессиях рассмотреть переиспользование WDA через useNewWDA=false. При зависании сначала изучить main-thread idle и logs; глобальное отключение ожиданий не является универсальным исправлением.

Проверять версии и local --help перед установкой/командами. У pymobiledevice3 screenshot, syslog, display/HID и accessibility services имеют разные prerequisites. В recipes версии 11.31.0 HID swipe — pointer motion без touch contact, а touch-scroll требует drag; координаты 0..65535, не CUA pixels. Это сведения конкретной версии, не вечный контракт. Наличие CLI не доказывает доступность всех AX-элементов стороннего приложения.

Maestro 2.11.0 не поддерживает physical iOS. Если рассматривается более новая версия, проверить актуальную поддержку; Simulator-прохождение не засчитывать за реальный iPhone.

Пока новый runner/CLI не подтвердил контрольные tap, scroll в обе стороны, logger и восстановление, считать его непроверенным кандидатом. Не выводить большую стабильность из документации. Прогоны разных каналов проводить последовательно с отдельными строками coverage.

Первичные источники (исходное исследование: 2026-10-15; перед подготовкой нового stack проверить актуальность):

- [XCTest hittable](https://developer.apple.com/documentation/xcuiautomation/xcuielement/ishittable)
- [Appium device setup](https://appium.github.io/appium-xcuitest-driver/latest/getting-started/device-setup/)
- [Appium preinstalled app](https://appium.github.io/appium-xcuitest-driver/latest/guides/capability-sets/)
- [Appium capabilities](https://appium.github.io/appium-xcuitest-driver/latest/reference/capabilities/)
- [Appium gestures](https://appium.github.io/appium-xcuitest-driver/latest/reference/execute-methods/)
- [Appium Inspector](https://github.com/appium/appium-inspector)
- [pymobiledevice3 recipes v11.31.0](https://github.com/doronz88/pymobiledevice3/blob/v11.31.0/docs/guides/cli-recipes.md)
- [Maestro 2.11.0 physical-device support](https://maestro.dev/blog/maestro-cli-2-11-0)
