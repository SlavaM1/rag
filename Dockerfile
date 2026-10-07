FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.5.1+cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY docs ./docs
COPY scripts ./scripts
COPY tests ./tests
COPY evaluation ./evaluation
RUN chmod +x scripts/start.sh

EXPOSE 8000
CMD ["./scripts/start.sh"]
