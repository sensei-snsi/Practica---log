from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
import tempfile
from pathlib import Path

# ваш анализатор
from log_analyzer import analyze

app = Flask(__name__)

# Кросс-платформенная временная папка (работает и на Windows, и на Linux/macOS)
TMP_DIR = Path(tempfile.gettempdir())
TMP_DIR.mkdir(parents=True, exist_ok=True)

def analyze_text_via_tempfile(text: str, top: int):
    """Пишем текст во временный файл в системной temp-директории и передаем путь в analyze()."""
    fd, temp_path = tempfile.mkstemp(prefix="log_", suffix=".log", dir=TMP_DIR)
    os.close(fd)  # закроем дескриптор, будем писать обычным open()
    try:
        with open(temp_path, "w", encoding="utf-8") as tmp:
            tmp.write(text)
        return analyze(temp_path, topn=int(top))
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass

@app.get("/health")
def health():
    return jsonify(status="ok")

@app.post("/analyze")
def analyze_endpoint():
    """
    Принимает:
      - multipart/form-data: поле file (файл логов)
      - text/plain: сырой текст в body
      - application/json: поле "log" (строка)
    Доп.параметр: top (int) — размер "топов" в отчете.
    """
    # top можно передать в query (?top=10), form-data или JSON
    top = (
        request.args.get("top", type=int)
        or request.form.get("top", type=int)
        or ((request.get_json(silent=True) or {}).get("top") if request.is_json else None)
        or 5
    )

    # 1) Файл (multipart/form-data)
    if "file" in request.files:
        f = request.files["file"]
        filename = secure_filename(f.filename) or "uploaded.log"
        # создадим безопасный временный файл
        fd, temp_path = tempfile.mkstemp(prefix="upload_", suffix="_" + filename, dir=TMP_DIR)
        os.close(fd)
        try:
            f.save(temp_path)
            report = analyze(temp_path, topn=int(top))
            return jsonify(report=report)
        finally:
            try:
                os.remove(temp_path)
            except Exception:
                pass

    # 2) Сырой текст (text/plain)
    if request.data and request.content_type and request.content_type.startswith("text/plain"):
        raw_text = request.data.decode("utf-8", errors="ignore")
        report = analyze_text_via_tempfile(raw_text, top)
        return jsonify(report=report)

    # 3) JSON с полем "log"
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        if isinstance(payload.get("log"), str):
            report = analyze_text_via_tempfile(payload["log"], top)
            return jsonify(report=report)

    return jsonify(
        error="Дайте логи как 'file' (multipart/form-data), как raw text/plain, или JSON с полем 'log' (string).",
        hint="Пример: POST /analyze?top=5 c form-data: file=@sample_log.txt",
    ), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
