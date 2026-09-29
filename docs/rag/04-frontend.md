---
title: Angular frontend
project: mcp-ai
document_type: technical_documentation
source: repository
---

# Angular frontend

## Bootstrap и структура

`frontend/src/main.ts` вызывает `bootstrapApplication(App, { providers: [provideHttpClient()] })`. Корневой standalone component `App` находится в `frontend/src/app/app.ts`; template — `app.html`, styles — `app.scss`. Angular routing в проекте отсутствует.

## Компонент `App`

### State

`App` использует signals `sessions`, `activeSession`, `status`, `loadingSessions`, `statusLoading`, `pending`, `error` и `sidebarCollapsed`. `draft` начинается со строки `Какая сейчас погода в Москве?`.

### Initial load

`ngOnInit()` параллельно запускает `loadSessions()` и `refreshStatus()`. `loadSequence` предотвращает применение устаревшего результата конкурирующих загрузок.

### Сессии

`createSession()` вызывает `ApiService.createSession()`, перезагружает summaries и фокусирует textarea. `selectSession(...)` получает полную сессию. Список показывает title, `message_count` и `updated_at`.

### Отправка

`sendMessage()` trim-ит `draft`, создаёт session при её отсутствии и вызывает `ApiService.sendMessage(...)`. Во время операции `pending` отключает выбор/создание сессий и composer. При error компонент пробует заново загрузить session и status.

### Обработка клавиатуры

`handleKeydown(...)` отправляет сообщение по Enter; Shift+Enter оставляет перенос строки. Template ограничивает textarea `maxlength="2000"`.

## `ApiService`

`frontend/src/app/api.service.ts` предоставляет методы `listSessions()`, `getSession(id)`, `createSession()`, `sendMessage(sessionId, message)` и `getMCPStatus()`. Все URL относительные: production nginx должен проксировать `/api/` в backend.

## Типы данных

`ChatMessage` содержит `mcp_data`, `ChatSession` расширяет summary массивом messages. `MCPToolCall` включает `id`, `name`, `arguments`, `result`, `error`, `duration_ms`. `MCPStatus` описывает live status endpoint.

## Chat UI

### Сообщения

`app.html` показывает user role как `Вы`, прочие roles как `MCP AI`, timestamp и content с сохранёнными переносами CSS. Assistant message может показать технические MCP calls: name, duration, JSON arguments, result или error.

### MCP status

Topbar отображает `Проверяем MCP`, `MCP подключён` или `MCP недоступен`, server URL и tool count. Кнопка вызывает `refreshStatus()`.

### Legacy data

`toolsFor(...)` отображает `mcp_data.tools` как карточки «Ответ tools/list». Обычный agent endpoint сохраняет discovery в `mcp_data.available_tools`, которого TypeScript interface/template не выводят отдельным списком.

### Адаптивность

`frontend/src/app/app.scss` содержит breakpoints `900px` и `680px`; при узком экране sidebar становится горизонтальной областью, composer — одноколоночным. `styles.scss` задаёт minimum body width 320px и общие focus/disabled styles.

## Ошибки UI

`errorText(...)` показывает backend `detail`, если он string. Network error с status 0 превращается в русское сообщение о недоступном backend. Другие ошибки выводят `Error.message` или fallback.

## Ограничения frontend

Нет frontend unit/e2e tests, streaming, authentication UI, удаления или переименования session. `npm run start` запускает `ng serve` без proxy configuration, поэтому отдельно запущенный dev server не получает nginx proxy автоматически.
