#  Copyright 2024 Amazon.com, Inc. or its affiliates.
#!/bin/bash

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)
AWS_REGION=${AWS_REGION:-us-west-2}
CONTAINER_NAME="data-bulk-ingest-container"

# If the repository doesn't exist in ECR, create it.
aws ecr describe-repositories --repository-names "${CONTAINER_NAME}" --region ${AWS_REGION} > /dev/null 2>&1

if [ $? -ne 0 ]
then
    aws ecr create-repository --repository-name "${CONTAINER_NAME}" --region ${AWS_REGION} > /dev/null
fi

# Get the login command from ECR and execute it directly
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com || exit 1

# Build the docker image locally with the image name and then push it to ECR
docker build -t ${CONTAINER_NAME} -f docker/Dockerfile.bulk . || exit 1

# Tag the Docker image for ECR
docker tag ${CONTAINER_NAME}:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${CONTAINER_NAME}:latest

# Push Docker image to ECR
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${CONTAINER_NAME}:latest

echo "Completed pushing docker image to ECR."
echo "Bulk Ingest Container URI: ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${CONTAINER_NAME}:latest"
