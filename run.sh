#!/bin/bash
set -e
IMAGE_NAME="jee6:latest"
CONTAINER_NAME="jee6-container"
GIT_REPO="https://github.com/8G4B/JEE6.v1.git"
GIT_DIR="JEE6.v1"
echo "🐳 Git 업데이트 및 Docker 빌드 시작..."
if [ -d "$GIT_DIR" ]; then
  cd "$GIT_DIR" && git pull
else
  git clone "$GIT_REPO" "$GIT_DIR" && cd "$GIT_DIR"
fi
if ! docker images | grep -q "$IMAGE_NAME"; then
  docker build -t "$IMAGE_NAME" .
else
  echo "✅ 이미지 $IMAGE_NAME 이미 존재합니다."
fi
if docker ps -a | grep -q "$CONTAINER_NAME"; then
  docker stop "$CONTAINER_NAME"  true && docker rm "$CONTAINER_NAME"  true
fi
docker run -d -p 8000:8000 --name "$CONTAINER_NAME" \
  -e DISCORD_TOKEN="MTMxODExNDM3MjQzODE5NjMyOA.Gj5ask.uCMewx-kw6Dwm46np-OSJOpup3oEWEBh2sSuqs" \
  -e MEAL_API_KEY="0012751c202148a48a3d74102383c8de" \
  -e GPT_API_KEY="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" \
  "$IMAGE_NAME"
echo "🎉 Docker 컨테이너 실행 완료. 로그 확인: docker logs -f $CONTAINER_NAME"