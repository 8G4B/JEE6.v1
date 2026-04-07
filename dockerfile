FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Seoul
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -o Acquire::Retries=5 -o Acquire::http::Timeout="30" -o Acquire::https::Timeout="30" \
    && apt-get install -y --no-install-recommends \
    gcc \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY assets/ ./assets/

RUN touch /app/discord.log && chmod 666 /app/discord.log

CMD ["python", "-m", "src.main"]