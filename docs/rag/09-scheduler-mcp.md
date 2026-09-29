---
title: Scheduler MCP
project: mcp-ai
document_type: technical_documentation
source: repository
---

# Scheduler MCP

## Назначение

Scheduler MCP не является отдельным MCP server. Планирование реализовано внутри `weather-mcp` классом `WeatherScheduler` из `weather-mcp/weather_mcp/scheduler.py` и доступно через weather tools.

## Доступные scheduling tools

- `create_weather_schedule(city, interval_seconds)` создаёт active interval job.
- `list_weather_schedules()` возвращает active и stopped schedules.
- `stop_weather_schedule(schedule_id)` деактивирует запись и удаляет running APScheduler job.
- `run_weather_collection_now(city)` сохраняет single sample без schedule.
- `get_weather_summary(city, minutes)` агрегирует ранее сохранённые samples.

## Создание task

`WeatherScheduler.create_schedule(...)` создаёт UUID через `uuid4()`, active `WeatherSchedule`, initial `next_run_at = now + interval`, сохраняет его и регистрирует job только при создании. Минимальный интервал в class — 30 seconds; MCP schema разрешает от 30 до 86400.

`WeatherRepository.create_schedule(...)` ищет active schedule с той же точной парой `city` и `interval_seconds`. Partial unique index `active_weather_schedule_by_city_interval` поддерживает это правило в SQLite. Регистр города не нормализуется для persistence.

## Запуск задач

`AsyncIOScheduler` создаётся в UTC с `coalesce=True`, `max_instances=1`, `misfire_grace_time=30`. `_register(...)` устанавливает новый next run `utc_now() + interval`, сохраняет его и добавляет interval job.

`_run_schedule(...)` получает active schedule, до provider call записывает `last_run_at` и следующий run, затем `await collect_now(schedule.city)`. `collect_now(...)` получает current weather и сохраняет `WeatherSample`.

## Хранение задач и результатов

`WeatherRepository` использует sqlite3, не PostgreSQL и не SQLAlchemy. Default path — `/data/weather.db`; Compose монтирует named volume `mcp-ai-weather-mcp-data` в `/data`.

### `weather_schedules`

Хранит `schedule_id`, city, interval_seconds, active, created_at, last_run_at, next_run_at. Остановленное расписание сохраняется, но `next_run_at` очищается.

### `weather_samples`

Хранит city, collected_at, mandatory temperature/humidity/wind и nullable extended measurements. `weather_samples_by_city_collected_at` ускоряет выборку summary range.

## Восстановление после restart

`WeatherScheduler.start()` читает `list_schedules(active_only=True)` и повторно регистрирует jobs. APScheduler jobs не persistent: `_register(...)` пересчитывает next run от времени restart, не использует прежний `next_run_at` и не воспроизводит пропущенные runs. Coalescing также не повторяет несколько missed intervals.

## Ошибки

`_run_schedule(...)` ловит любой `Exception`, логирует `Scheduled weather collection failed` и сохраняет job active. При provider failure sample не создаётся, но schedule не отключается. SQLite operation errors не имеют отдельного domain-to-MCP mapping.
