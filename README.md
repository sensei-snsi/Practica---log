
# Log Analyzer API

Небольшой API над уже существующим анализатором логов из `log_analyzer.py`. Позволяет отправлять логи из Postman/curl и получать текстовый отчёт в JSON.

## Состав
- `log_analyzer.py` — ваш исходный анализатор (CLI), менять не обязательно. Используется функцией `analyze(path, topn)` для разбора логов. 
- `app.py` — простой Flask-сервер с эндпоинтом `/analyze`.
- `requirements.txt` — зависимости для запуска API.
- `sample_log.txt` — пример лог-файла для проверки.

## Быстрый запуск локально

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py  # поднимет сервер на http://localhost:8000
```

Проверка здоровья:
```bash
curl http://localhost:8000/health
```

## Отправка логов

Эндпоинт: `POST /analyze`  
Параметры:
- `top` (query или body) — сколько топ-значений показать в отчёте (по умолчанию 5).

Поддерживаются три способа передачи логов:

### 1) multipart/form-data (файл)
```bash
curl -X POST "http://localhost:8000/analyze?top=5"   -F "file=@sample_log.txt"
```

### 2) text/plain (сырой текст в теле)
```bash
curl -X POST "http://localhost:8000/analyze"   -H "Content-Type: text/plain"   --data-binary @sample_log.txt
```

### 3) JSON с полем `log`
```bash
curl -X POST "http://localhost:8000/analyze"   -H "Content-Type: application/json"   -d @- <<'JSON'
{
  "top": 10,
  "log": "2025-09-26T13:54:06Z ERROR 192.168.1.12 - User login failed user=eve\n"
}
JSON
```

Ответ всегда в JSON:
```json
{
  "report": "=== SUMMARY ===\nTotal lines: ...\nBy level: ..."
}
```

## Пример через Postman

1. Импортируйте коллекцию `Log Analyzer API.postman_collection.json` в Postman (File → Import).
2. В запросе **Analyze (multipart/form-data)**:
   - Метод: POST
   - URL: `http://localhost:8000/analyze?top=5`
   - Body → form-data → key=`file` (type *File*), value — `sample_log.txt`
3. В запросе **Analyze (text/plain)**:
   - Метод: POST
   - URL: `http://localhost:8000/analyze`
   - Headers: `Content-Type: text/plain`
   - Body → raw → вставьте содержимое логов
4. В запросе **Analyze (JSON)**:
   - Метод: POST
   - URL: `http://localhost:8000/analyze`
   - Body → raw (JSON) →
     ```json
     {"top": 5, "log": "2025-09-26T13:54:06Z ERROR 192.168.1.12 - User login failed user=eve\n"}
     ```

## Как это работает
- API вызывает `analyze(path, topn)` из `log_analyzer.py`, который поддерживает:
  - строки в простом формате вида `2025-09-26T13:54:06Z ERROR 192.168.1.12 - ...`,
  - Apache Combined-подобные строки вида `93.184... [25/Sep/2025:10:15:32 +0000] "GET /... 200 ..."`.  
- В отчёте есть суммарные счётчики по уровням, статусам HTTP, топ IP/сообщений, ошибки по часам и *slow lines* по `duration_ms=N`.  

## Тест на примере
```bash
curl -X POST http://localhost:8000/analyze -F "file=@sample_log.txt" | jq -r .report
```

## Запуск анализатора как CLI (без API)
```bash
python log_analyzer.py sample_log.txt --top 10
```

## Замечания
- Никаких дополнительных серверов/облачных платформ не требуется. Достаточно локального Python и Flask.
- `werkzeug` отдельно ставить не нужно — он идёт как зависимость Flask.
