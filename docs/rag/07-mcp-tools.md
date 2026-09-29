---
title: Каталог MCP tools
project: mcp-ai
document_type: technical_documentation
source: repository
---

# Каталог MCP tools

## Источник tools

Все восемь tools зарегистрированы декораторами `@mcp.tool` в `weather-mcp/weather_mcp/server.py`. Их JSON schema генерируется MCP SDK из type annotations и Pydantic `Field` constraints. Примеры результатов ниже иллюстративны по формату моделей; числовые значения не являются гарантированными данными provider.

### `get_current_weather`

**MCP server:** `weather-mcp`. **Исходник:** `server.py`, функция `get_current_weather(city, ctx)`. **Назначение:** получает текущую нормализованную погоду, не создавая sample.

**Параметры:** обязательный `city: string`, после trim от 1 до 100 символов.

**Пример input:** `{"city":"Москва"}`.

**Результат:** `WeatherResult`: `requested_city`, `resolved_location`, `temperature_c`, `feels_like_c`, `condition`, `humidity_percent`, pressure/wind/precipitation/cloud/visibility/UV и observation fields.

**Пример результата:** `{"requested_city":"Москва","resolved_location":{"city":"Москва","country":"Россия"},"temperature_c":12.0,"humidity_percent":70,"wind_speed_kmh":9.0}`.

**Ошибки:** invalid city; `CITY_NOT_FOUND`, `WEATHER_PROVIDER_TIMEOUT`, `WEATHER_PROVIDER_UNAVAILABLE`, `WEATHER_PROVIDER_INVALID_RESPONSE`.

### `get_weather_forecast`

**MCP server:** `weather-mcp`. **Исходник:** `server.py`, функция `get_weather_forecast(city, days, ctx)`.

**Параметры:** обязательные `city: string` и `days: integer` от 1 до 3.

**Пример input:** `{"city":"Новосибирск","days":3}`.

**Результат:** `WeatherForecastResult` с resolved location и `forecast[]`; каждый `ForecastDay` содержит date, min/max/avg temperature, optional sunrise/sunset/moon phase.

**Пример результата:** `{"city":"Новосибирск","forecast":[{"date":"2026-09-29","min_temperature_c":5.0,"max_temperature_c":12.0,"avg_temperature_c":8.0}]}`.

**Ошибки:** validation city/days и provider errors WeatherService.

### `get_hourly_weather`

**MCP server:** `weather-mcp`. **Исходник:** `server.py`, функция `get_hourly_weather(city, ctx)`.

**Параметры:** обязательный `city: string` длиной до 100.

**Пример input:** `{"city":"Казань"}`.

**Результат:** `HourlyWeatherResult` с первым доступным forecast date и `hours[]`: time, temperature, feels-like, condition, humidity, precipitation, chance of rain, wind.

**Пример результата:** `{"city":"Казань","date":"2026-09-29","hours":[{"time":"09:00","temperature_c":10.0,"humidity_percent":72,"wind_speed_kmh":8.0}]}`.

**Ошибки:** city validation и provider/invalid provider payload errors.

### `create_weather_schedule`

**MCP server:** `weather-mcp`. **Исходник:** `server.py`, функция `create_weather_schedule(city, interval_seconds, ctx)`; логика `WeatherScheduler.create_schedule(...)`.

**Параметры:** обязательные `city: string`; `interval_seconds: integer` от 30 до 86400.

**Пример input:** `{"city":"Новосибирск","interval_seconds":60}`.

**Результат:** `ScheduleResult` с UUID-like `schedule_id`, city, interval, active, timestamps и `created`. Повтор для активной пары city/interval возвращает существующее расписание с `created=false`.

**Пример результата:** `{"schedule_id":"<SCHEDULE_ID>","city":"Новосибирск","interval_seconds":60,"active":true,"created_at":"2026-09-29T12:00:00Z","last_run_at":null,"next_run_at":"2026-09-29T12:01:00Z","created":true}`.

**Ошибки:** schema validation. Внутренний `WeatherScheduler` дополнительно проверяет минимальные 30 секунд.

### `list_weather_schedules`

**MCP server:** `weather-mcp`. **Исходник:** `server.py`, функция `list_weather_schedules(ctx)`.

**Параметры:** отсутствуют.

**Пример input:** `{}`.

**Результат:** `ScheduleListResult` с `schedules[]`, включая активные и остановленные записи.

**Пример результата:** `{"schedules":[{"schedule_id":"<SCHEDULE_ID>","city":"Новосибирск","interval_seconds":60,"active":true,"created":false}]}`.

**Ошибки:** отдельная domain error handling не определена; возможные SQLite/MCP transport failures доставляются протоколом.

### `stop_weather_schedule`

**MCP server:** `weather-mcp`. **Исходник:** `server.py`, функция `stop_weather_schedule(schedule_id, ctx)`.

**Параметры:** обязательный `schedule_id: string`, минимум один символ.

**Пример input:** `{"schedule_id":"<SCHEDULE_ID>"}`.

**Результат:** `StopScheduleResult` с `schedule_id`, `stopped` и message. Неизвестный ID возвращает `stopped=false`, а не exception. История measurements остаётся.

**Пример результата:** `{"schedule_id":"<SCHEDULE_ID>","stopped":true,"message":"Расписание остановлено; накопленные измерения сохранены."}`.

**Ошибки:** schema validation или persistence/MCP failures.

### `run_weather_collection_now`

**MCP server:** `weather-mcp`. **Исходник:** `server.py`, функция `run_weather_collection_now(city, ctx)`.

**Параметры:** обязательный `city: string` длиной 1–100 после trim.

**Пример input:** `{"city":"Москва"}`.

**Результат:** `WeatherSampleResult`: city, collected_at, temperature, humidity, wind и optional weather metrics. Tool сохраняет один sample и не создаёт schedule.

**Пример результата:** `{"city":"Москва","collected_at":"2026-09-29T12:00:00Z","temperature_c":12.0,"humidity_percent":70,"wind_speed_kmh":9.0,"condition":"Partly cloudy"}`.

**Ошибки:** city validation и WeatherService provider errors.

### `get_weather_summary`

**MCP server:** `weather-mcp`. **Исходник:** `server.py`, функция `get_weather_summary(city, minutes, ctx)`.

**Параметры:** обязательные `city: string`; `minutes: integer` от 1 до 525600.

**Пример input:** `{"city":"Новосибирск","minutes":60}`.

**Результат:** `WeatherSummary`: count samples, actual `from`/`to`, min/max/avg weather metrics, first/last temperature, precipitation total/max и unique conditions. При отсутствии samples метрики и range равны null, есть message.

**Пример результата:** `{"city":"Новосибирск","period_minutes":60,"samples":2,"from":"2026-09-29T11:00:00Z","to":"2026-09-29T12:00:00Z","temperature":{"min":8.0,"max":10.0,"avg":9.0,"first":8.0,"last":10.0}}`.

**Ошибки:** schema validation или SQLite/MCP transport failures.
