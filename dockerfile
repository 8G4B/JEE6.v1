FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
COPY app.py .
COPY commands/ ./commands/
COPY alarm/ ./alarm/
COPY *.py .

RUN pip install --no-cache-dir -r requirements.txt

COPY .env .

CMD ["python", "app.py"]
