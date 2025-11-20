# JEE6

<img src="https://github.com/user-attachments/assets/d6b5f0cd-9363-40ad-a356-c1449664750b" width="30%"/> <br/>

> JEE6은 GSM 학생들을 위해 여러 기능을 제공하는 discord 봇입니다.

[JEE6 서버에 초대하기](https://discord.com/oauth2/authorize?client_id=1318114372438196328&permissions=8&integration_type=0&scope=bot)

[개발자 깃허브](https://github.com/976520)

[개발자한테 쌕쌕 사주기](http://aq.gy/f/9LOJx)

## 명령어 일람

1.  급식 관련

    > NIES API를 이용했어요.

    - `!급식` `!밥`을 통해 다음 급식을 확인할 수 있어요.

      - 7:30, 12:30, 18:30을 기준으로 다음 급식이 바뀝니다

    - `!급식.아침` `!급식.점심` `!급식.저녁` 을 통해 오늘의 각 식사메뉴를 확인할 수 있어요.

    - `!급식.내일아침` `!급식.내일점심` `!급식.내일저녁` 을 통해 내일의 각 식사메뉴를 확인할 수 있어요.

2.  도박 관련

    > 진짜 돈을 걸지 않아요!

    - `!도박.노동` `!도박.일` `!도박.돈` 을 통해 정직하게 돈을 벌 수 있어요. (쿨타임: 60초)

      - 근로소득세를 제외한 수익이에요!

    - `!도박.지갑` 을 통해 재산을 확인할 수 있어요.

    - `!도박.랭킹` 을 통해 상위 3명의 랭킹을 볼 수 있고, `!도박.전체랭킹` 를 통해 전체 랭킹을 볼 수 있어요.

      - ~~전체랭킹 조회는 조금 오래 걸려요...~~ 최적화 완료.

    - `!도박.송금 [유저] [금액]` 을 통해 돈을 송금할 수 있어요.

      - 송금 시 다음과 같은 증여세가 적용됩니다.

        | 과세표준                | 세율  |
        | ----------------------- | ----- |
        | 1조원 이하              | 5%    |
        | 1조원 초과 5조원 이하   | 7.5%  |
        | 5조원 초과 10조원 이하  | 10%   |
        | 10조원 초과 30조원 이하 | 12.5% |
        | 30조원 초과             | 15%   |

    - `!도박.[게임] [베팅]` 을 통해 게임을 할 수 있어요.

      - 할 수 있는 게임은 다음과 같아요.

        - 동전(확률: $\frac{1}{2}$)
        - 주사위(확률: $\frac{1}{6}$)
        - 블랙잭
        - 바카라
        - 인디언포커

      - JEE6 에서의 베팅은 투자의 일종인 장외거래로 간주되어 다음과 같은 증권거래세가 적용됩니다.

        | 과세표준                | 세율 |
        | ----------------------- | ---- |
        | 10조원 이하             | 0.5% |
        | 10조원 초과 30조원 이하 | 1%   |
        | 30조원 초과             | 2%   |

    - `!도박.잭팟 [베팅]` 을 통해 잭팟을 할 수 있어요. (쿨타임: 5초)

      - 당첨되면 다른 사람들이 베팅한 돈을 모두 얻는 대신 쿨타임이 30초로 늘어나요. 당첨에 실패하면 베팅한 돈을 잃어요. **(확률: $\frac{1}{100}$)**

      - 잭팟은 매일 조식, 중식, 석식시간마다 100만원으로 초기화되어요.

      - 잭팟의 수령액은 복권당첨에 따른 기타소득으로 취급되어 다음과 같은 종합소득세가 적용됩니다.

        | 과세표준                    | 세율 |
        | --------------------------- | ---- |
        | 500억원 이하                | 면제 |
        | 500억원 초과 1400억원 이하  | 6%   |
        | 1400억원 초과 5000억원 이하 | 15%  |
        | 5000억원 초과 8800억원 이하 | 24%  |
        | 8800억원 초과 1.5조원 이하  | 35%  |
        | 1.5조원 초과 3조원 이하     | 38%  |
        | 3조원 초과 5조원 이하       | 40%  |
        | 5조원 초과 10조원 이하      | 42%  |
        | 10조원 초과                 | 45%  |

3.  롤 관련

    > RIOT API를 이용했어요.

    - `!롤.로테이션` 을 통해 현재 무료 로테이션 챔피언 목록을 확인할 수 있어요.

    - `!롤.티어 [유저명]` 을 통해 그 유저의 티어를 확인할 수 있어요.

    - `!롤.전적 [유저명]` 을 통해 최근 5게임 전적을 확인할 수 있어요.

4.  기타

    - `!시간` 을 통해 현재 서버 시간을 확인할 수 있어요.

    - `!정보` 를 통해 JEE6의 정보를 확인할 수 있어요.

    - ~~`!질문 [내용]` 을 통해 질문을 할 수 있어요.~~

      - 지금 GPT API 돈없음 이슈로 작동하지 않아요...

## env

```env
MEAL_API_KEY=[나이스 API KEY]
DISCORD_TOKEN=[디코 APP Token]
RIOT_API_KEY=RGAPI-...

TZ=Asia/Seoul
AWS_REGION=ap-northeast-2
AWS_ACCOUNT_ID=[aws sts get-caller-identity 하면 나옴]
EFS_FILE_SYSTEM_ID=fs-...

DB_HOST=mariadb
DB_PORT=3306
DB_NAME=...
DB_PASSWORD=...
DB_USER=...

SUBNET_ID_1=subnet-...
SUBNET_ID_2=subnet-...
SECURITY_GROUP_ID=sg-...

M=[서버 관리 명령어 활성화 boolean]
G=[도박 명령어 활성화 boolean]
```

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
   - aiohttp
   - openai
   - riotwatcher

2. 환경변수 설정

   `.env` 파일을 만들어서 환경변수를 설정해주세요. 이 파일은 보안상의 이유로 `.gitignore`에 포함되어 있어서 github에 올라가지 않아요.

3. 실행

   `app.py` 파일을 실행해주세요.

## 도커로 실행

Windows의 경우와 Ubuntu의 경우로 나뉘어요.

### Windows

1. 도커 설치

   [Docker Desktop](https://www.docker.com/products/docker-desktop)을 설치해주세요.

2. 환경변수 설정

   `.env` 파일을 만들어서 환경변수를 설정해주세요. 이 파일은 보안상의 이유로 `.gitignore`에 포함되어 있어서 github에 올라가지 않아요.

3. 도커 이미지 빌드

   다음 명령어 `PowerShell`에서 실행해주세요.

   ```shell
   docker build -t jee6 .
   ```

4. 도커 컨테이너 실행

   다음 명령어를 실행하거나,

   ```shell
   docker run --env-file .env jee6
   ```

   Docker Desktop을 통해 이미지를 빌드하고 컨테이너를 실행해주세요.

### Ubuntu

1. 도커 설치

   다음 명령어를 실행해주세요.

   ```bash
   sudo apt-get update
   sudo apt-get install docker.io
   ```

2. 환경변수 설정

   `.env` 파일을 만들어서 환경변수를 설정해주세요. 이 파일은 보안상의 이유로 `.gitignore`에 포함되어 있어서 github에 올라가지 않아요.

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

## AWS로 배포

이대로 따라하려면 AWS CLI가 설치되어 있어야 해요~

### 1. EFS 파일 시스템 생성

```bash
EFS_FILE_SYSTEM_ID=$(aws efs create-file-system \
  --region ap-northeast-2 \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --encrypted \
  --query 'FileSystemId' \
  --output text)
```
생성된 값을 .env의 EFS_FILE_SYSTEM_ID에 복사해 넣어주세요.

### 2. EFS 마운트 타겟 생성

```bash
source .env

aws efs create-mount-target \
  --file-system-id ${EFS_FILE_SYSTEM_ID} \
  --subnet-id ${SUBNET_ID_1} \
  --security-groups ${SECURITY_GROUP_ID} \
  --region ap-northeast-2

aws efs create-mount-target \
  --file-system-id ${EFS_FILE_SYSTEM_ID} \
  --subnet-id ${SUBNET_ID_2} \
  --security-groups ${SECURITY_GROUP_ID} \
  --region ap-northeast-2
```

### 3. IAM 역할 생성

```bash
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document file://trust-policy.json

aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

aws iam put-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-name EFSAccessPolicy \
  --policy-document file://efs-access-policy.json

aws iam create-role \
  --role-name ecsTaskRole \
  --assume-role-policy-document file://trust-policy.json

aws iam put-role-policy \
  --role-name ecsTaskRole \
  --policy-name EFSAccessPolicy \
  --policy-document file://efs-access-policy.json
```

### 4. CloudWatch Logs 그룹 생성

```bash
aws logs create-log-group --log-group-name /ecs/jee6-bot/mariadb --region ap-northeast-2
aws logs create-log-group --log-group-name /ecs/jee6-bot/discord-bot --region ap-northeast-2
```
처음 한 번만 실행하면 됩니다

### 5. .env 파일 설정 및 배포

```bash
nano .env

./deploy.sh
```

### 배포 확인

```bash
aws ecs describe-services \
  --cluster jee6-bot-cluster \
  --services jee6-bot-service \
  --region ap-northeast-2 \
  --query 'services[0].{Status:status,RunningCount:runningCount,DesiredCount:desiredCount}'

aws logs tail /ecs/jee6-bot/discord-bot --follow --region ap-northeast-2
```

