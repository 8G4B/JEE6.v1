# JEE6

<img src="https://github.com/user-attachments/assets/d6b5f0cd-9363-40ad-a356-c1449664750b" width="50%"/> <br/>

[JEE6 서버에 초대하기](https://discord.com/oauth2/authorize?client_id=1318114372438196328&permissions=8&integration_type=0&scope=bot)

[개발자 깃허브](https://github.com/976520)

[개발자한테 쌕쌕 사주기](http://aq.gy/f/9LOJx)

## 명령어 일람

1. 급식 관련

   > NIES API를 이용했어요.

   - `!급식` 을 통해 다음 급식을 확인할 수 있어요.

   - `!급식.아침` `!급식.점심` `!급식.저녁` 을 통해 오늘의 각 식사메뉴를 확인할 수 있어요.

   - `!급식.내일아침` `!급식.내일점심` `!급식.내일저녁` 을 통해 내일의 각 식사메뉴를 확인할 수 있어요.

2. 도박 관련

   > 진짜 돈을 걸지 않아요!

   - `!도박.노동` 을 통해 정직하게 돈을 벌 수 있어요. (쿨타임: 60초)

   - `!도박.지갑` 을 통해 재산을 확인할 수 있어요.

   - `!도박.동전 [예측] [베팅]` 을 통해 동전 던지기를 할 수 있어요. (쿨타임: 5초)

     예측이 맞으면 베팅한 돈의 0.8배~1.8배를 얻을 수 있고, 틀리면 베팅한 돈을 잃어요. **(확률: $\frac{1}{2}$)**

     5초 쿨타임이 있어요.

   - `!도박.주사위 [예측] [베팅]` 을 통해 주사위 던지기를 할 수 있어요. (쿨타임: 5초)

     예측이 맞으면 베팅한 돈의 4.5배~5.5배를 얻을 수 있고, 틀리면 베팅한 돈을 잃어요. **(확률: $\frac{1}{6}$)**

   - `!도박.잭팟 [베팅]` 을 통해 잭팟을 할 수 있어요. (쿨타임: 5초)

     당첨되면 다른 사람들이 베팅한 돈을 모두 얻을 수 있고, 틀리면 베팅한 돈을 잃어요. **(확률: $\frac{1}{100}$)**

3. 기타

   - `!시간` 을 통해 현재 서버 시간을 확인할 수 있어요.

   - `!정보` 를 통해 JEE6의 정보를 확인할 수 있어요.

   - ~~`!질문 [내용]` 을 통해 질문을 할 수 있어요.~~

     지금 GPT API 돈없음 이슈로 작동하지 않아요...

## 로컬에서 실행

1. 패키지 설치

   `requirements.txt` 파일을 통해 패키지를 설치해주세요.

   ```shell
   pip install -r requirements.txt
   ```

   설치되는 패키지는 다음과 같아요.

   - python-dotenv
   - discord.py
   - requests
   - openai

2. 환경변수 설정

   `.env` 파일을 만들어서 환경변수를 설정해주세요. 이 파일은 보안상의 이유로 `.gitignore`에 포함되어 있어서 github에 올라가지 않아요.

   ```shell
   echo "DISCORD_TOKEN=[여기에 토큰 입력]" >> .env
   echo "MEAL_API_KEY=[여기에 키 입력]" >> .env
   echo "GPT_API_KEY=[여기에 키 입력]" >> .env
   ```

3. 실행

   `app.py` 파일을 실행해주세요.

## 도커로 실행

Windows의 경우와 Ubuntu의 경우로 나뉘어요.

### Windows

1. 도커 설치

   [Docker Desktop](https://www.docker.com/products/docker-desktop)을 설치해주세요.

2. 환경변수 설정

   `.env` 파일을 만들어서 환경변수를 설정해주세요. 이 파일은 보안상의 이유로 `.gitignore`에 포함되어 있어서 github에 올라가지 않아요.

   ```shell
   echo "DISCORD_TOKEN=[여기에 토큰 입력]" >> .env
   echo "MEAL_API_KEY=[여기에 키 입력]" >> .env
   echo "GPT_API_KEY=[여기에 키 입력]" >> .env
   ```

3. 도커 이미지 빌드

   다음 명령어 `PowerShell`에서 실행해주세요.

   ```shell
   docker build -t jee6 .
   ```

4. 도커 컨테이너 실행

   다음 명령어를 실행해주세요.

   ```shell
   docker run --env-file .env jee6
   ```

### Ubuntu

1. 도커 설치

   다음 명령어를 실행해주세요.

   ```bash
   sudo apt-get update
   sudo apt-get install docker.io
   ```

2. 환경변수 설정

   `.env` 파일을 만들어서 환경변수를 설정해주세요. 이 파일은 보안상의 이유로 `.gitignore`에 포함되어 있어서 github에 올라가지 않아요.

   ```bash
    echo "DISCORD_TOKEN=[여기에 토큰 입력]" >> .env
    echo "MEAL_API_KEY=[여기에 키 입력]" >> .env
    echo "GPT_API_KEY=[여기에 키 입력]" >> .env
   ```

3. 도커 이미지 빌드

   다음 명령어를 실행해주세요.

   ```bash
   sudo docker build -t jee6 .
   ```

4. 도커 컨테이너 실행

   다음 명령어를 실행해주세요.

   ```bash
   sudo docker run --env-file .env jee6
   ```
