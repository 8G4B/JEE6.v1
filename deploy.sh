set -e

source .env

AWS_REGION=${AWS_REGION:-"ap-northeast-2"}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}
ECR_REPO_NAME="jee6-bot"
CLUSTER_NAME="jee6-bot-cluster"
SERVICE_NAME="jee6-bot-service"
TASK_DEFINITION_FAMILY="jee6-bot-task"

echo "🔐 ECR login"
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

echo "🔨 docker build"
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker build -t ${ECR_REPO_NAME}:latest -f dockerfile .

ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:latest"
docker tag ${ECR_REPO_NAME}:latest ${ECR_URI}

echo "📤 ECR에 이미지 푸시"
docker push ${ECR_URI}

echo "📋 Task Definition 등록"
aws ecs register-task-definition \
  --cli-input-json file://ecs-task-definition-generated.json \
  --region ${AWS_REGION}

echo "🔄 ECS 서비스 업데이트"
if aws ecs describe-services --cluster ${CLUSTER_NAME} --services ${SERVICE_NAME} --region ${AWS_REGION} --query 'services[0].status' --output text 2>/dev/null | grep -q "ACTIVE"; then
  aws ecs update-service \
    --cluster ${CLUSTER_NAME} \
    --service ${SERVICE_NAME} \
    --task-definition ${TASK_DEFINITION_FAMILY} \
    --force-new-deployment \
    --region ${AWS_REGION}
else
  sed -e "s|subnet-xxxxxxxxx|${SUBNET_ID_1}|g" \
      -e "s|subnet-yyyyyyyyy|${SUBNET_ID_2}|g" \
      -e "s|sg-xxxxxxxxx|${SECURITY_GROUP_ID}|g" \
      ecs-service-definition.json > ecs-service-definition-updated.json
  
  aws ecs create-service \
    --cli-input-json file://ecs-service-definition-updated.json \
    --region ${AWS_REGION}
fi

echo "✅ 배포 완료!"

