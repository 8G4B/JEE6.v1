# Python 3.12의 slim 이미지를 베이스 이미지로 합니다
FROM python:3.12-slim
# /app 디렉토리를 생성하고, 이 디렉토리를 작업 디렉토리로 설정합니다
WORKDIR /app
# requirements.txt 파일을 /app 디렉토리로 복사합니다
COPY requirements.txt .
# app.py 파일을 /app 디렉토리로 복사합니다
COPY app.py .
# 각 디렉토리를 /app 하위 디렉토리로 복사합니다
COPY features/ ./features/
COPY assets/ ./assets/
COPY shared/ ./shared/
# 모든 .py 파일을 /app 디렉토리로 복사합니다
COPY *.py .
COPY gambling_data.json .
# COPY .env .
# requirements.txt에 명시된 패키지를 설치합니다
RUN pip install --no-cache-dir -r requirements.txt
# 시차 이슈 해결
ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
# 8000 포트를 외부에 노출합니다
EXPOSE 8000

RUN mkdir -p /app/logs && \
    touch /app/logs/discord.log && \
    chown -R root:root /app

USER root
# 컨테이너가 실행될 때 실행할 명령어를 설정합니다
CMD ["python", "app.py"]