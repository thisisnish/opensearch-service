#!/bin/bash
#
# ecr-push.sh
#
# Author: Lain Musgrove (lain.musgrove@hearst.com)
# Date: Wednesday November 15, 2023
#

# Push docker image into ECR - does not run/start
account_id=`aws sts get-caller-identity --query "Account" --output text`
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin $account_id.dkr.ecr.us-east-2.amazonaws.com
# Build to AMD64 rather than Mac's ARM64 for running in AWS ECS
docker buildx build --platform linux/amd64 -t marketplace-search-service . #add .dockerignore later
docker tag marketplace-search-service:latest $account_id.dkr.ecr.us-east-2.amazonaws.com/marketplace-search-service:dev
docker push $account_id.dkr.ecr.us-east-2.amazonaws.com/marketplace-search-service:dev
