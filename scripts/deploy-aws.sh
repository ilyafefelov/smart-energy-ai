#!/bin/bash
# Smart Energy AI V2 - AWS Deployment Script

set -e

echo "☁️ Deploying Smart Energy AI V2 to AWS..."

# Check required environment variables
if [ -z "$AWS_ACCOUNT_ID" ] || [ -z "$AWS_REGION" ]; then
    echo "❌ Please set AWS_ACCOUNT_ID and AWS_REGION environment variables"
    exit 1
fi

AWS_REGION=${AWS_REGION:-us-east-1}
ECR_REGISTRY="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
IMAGE_NAME="smart-energy-ai-v2"
CLUSTER_NAME="smart-energy-cluster"

echo "📦 Building production Docker image..."
docker build -t $IMAGE_NAME:latest --target production .

echo "🏷️ Tagging image for ECR..."
docker tag $IMAGE_NAME:latest $ECR_REGISTRY/$IMAGE_NAME:latest

echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

echo "📤 Pushing image to ECR..."
docker push $ECR_REGISTRY/$IMAGE_NAME:latest

echo "⚙️ Creating ECS infrastructure..."

# Create ECS cluster (if it doesn't exist)
if ! aws ecs describe-clusters --clusters $CLUSTER_NAME --region $AWS_REGION > /dev/null 2>&1; then
    echo "Creating ECS cluster..."
    aws ecs create-cluster --cluster-name $CLUSTER_NAME --region $AWS_REGION
fi

# Create task definition
cat > task-definition.json << EOF
{
    "family": "smart-energy-ai-v2",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "512",
    "memory": "1024",
    "executionRoleArn": "arn:aws:iam::$AWS_ACCOUNT_ID:role/ecsTaskExecutionRole",
    "containerDefinitions": [
        {
            "name": "dagster-webserver",
            "image": "$ECR_REGISTRY/$IMAGE_NAME:latest",
            "portMappings": [
                {
                    "containerPort": 3000,
                    "protocol": "tcp"
                }
            ],
            "essential": true,
            "environment": [
                {
                    "name": "DAGSTER_HOME",
                    "value": "/opt/dagster/dagster_home"
                }
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/smart-energy-ai-v2",
                    "awslogs-region": "$AWS_REGION",
                    "awslogs-stream-prefix": "ecs"
                }
            }
        }
    ]
}
EOF

echo "📝 Registering task definition..."
aws ecs register-task-definition --cli-input-json file://task-definition.json --region $AWS_REGION

echo "🚀 Creating ECS service..."
aws ecs create-service \
    --cluster $CLUSTER_NAME \
    --service-name smart-energy-ai-v2-service \
    --task-definition smart-energy-ai-v2:1 \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxxx],securityGroups=[sg-xxxxxx],assignPublicIp=ENABLED}" \
    --region $AWS_REGION

echo "✅ Deployment complete!"
echo ""
echo "🔗 Next steps:"
echo "  1. Update security group and subnet IDs in the script"
echo "  2. Create RDS PostgreSQL instance for production"
echo "  3. Setup ALB for load balancing"
echo "  4. Configure Route53 for custom domain"

# Cleanup
rm task-definition.json