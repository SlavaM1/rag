---
title: Weather MCP
project: mcp-ai
document_type: technical_documentation
source: repository
---

# Weather MCP

## Назначение

`weather-mcp` — MCP 2.2 Streamable HTTP server из `weather-mcp/weather_mcp/server.py`. Server предоставляет текущую погоду, прогноз, почасовые данные, сохранение weather samples и background schedules.

## HTTP и lifecycle

`mcp.streamable_http_app(...)` публикует MCP path `/mcp`, `stateless_http=True`, host `0.0.0.0`. Custom route `GET /health` возвращает `{"status":"ok"}`. `TransportSecuritySettings` допускает hosts `weather-mcp:8001`, `localhost:8001`, `127.0.0.1:8001`.

`lifespan(...)` создаёт один `httpx2.AsyncClient`, `WeatherRepository`, `WeatherService` и `WeatherScheduler`; запускает scheduler до yield и закрывает scheduler/repository после yield.

## Валидация города

Type alias `City` вызывает `_normalize_city(...)`: только string, trim, непустой, максимум 100 characters. Неверные значения дают Pydantic custom errors на русском.

## Weather provider

### wttr.in

`WttrWeatherClient.get_weather(...)` в `weather-mcp/weather_mcp/weather.py` обращается к `{WEATHER_BASE_URL}/{quote(city)}?format=j1`. Default `WEATHER_BASE_URL` — `https://wttr.in`; city URL-encoded через `quote(..., safe='')`.

### Geocoding

Отдельного geocoding API в коде нет. `WeatherService._location(...)` извлекает `nearest_area` из ответа wttr.in как resolved location; provider request передаёт исходную строку city напрямую wttr.in.

### Нормализация

`WeatherService` валидирует обязательные и optional values, rejects bool/nonfinite numbers и формирует `WeatherResult`, `WeatherForecastResult`, `HourlyWeatherResult`. Температуры измеряются в Celsius, wind speed — km/h, humidity — percent.

## Fallback

Fallback provider, Open-Meteo integration и wttr.in fallback chain отсутствуют. Используется только URL из `WEATHER_BASE_URL`; по умолчанию это wttr.in.

## Ошибки provider

`_tool_error(...)` возвращает MCP `ToolError` с JSON text: `CITY_NOT_FOUND`, `WEATHER_PROVIDER_TIMEOUT`, `WEATHER_PROVIDER_UNAVAILABLE` или `WEATHER_PROVIDER_INVALID_RESPONSE`. HTTP 4xx/5xx и network errors скрывают provider details, malformed response становится invalid response.

## Flow погодного запроса

```text
User request
→ ChatAgent и LLM
→ LLM выбирает get_current_weather/get_weather_forecast/get_hourly_weather
→ MCP ClientSession.call_tool
→ weather-mcp WeatherService
→ WttrWeatherClient GET wttr.in
→ нормализованный tool result
→ ChatAgent добавляет tool message
→ LLM создаёт итог
```

## Связь с агентом

`weather-mcp` не выбирает tool сам. Backend передаёт его dynamic schema LLM, а LLM выбирает один или несколько tools. Backend сохраняет normalized MCP transport result в `ChatMessage.mcp_data.tool_calls`.
