#!/bin/bash

# This script builds the FastAPI Docker image and pushes it to AWS ECR.
# It requires three arguments:
# 1. AWS Account ID
# 2. AWS Region
# 3. Image Tag (e.g., 'latest', 'v1.2.0')

set -e # Exit immediately if a command exits with a non-zero status.

# --- Input Validation ---
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <aws_account_id> <aws_region> <image_tag>"
    exit 1
fi

AWS_ACCOUNT_ID=$1
AWS_REGION=$2
IMAGE_TAG=$3
REPO_NAME="cue/api" # Your repository name in ECR

# Get the absolute path of the project root.
# Assumes this script is in the 'scripts' directory.
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( dirname "$DIR" )"

ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
REMOTE_IMAGE_NAME="${ECR_REGISTRY}/${REPO_NAME}:${IMAGE_TAG}"
LOCAL_IMAGE_NAME="${REPO_NAME}:${IMAGE_TAG}"

echo "--- Building API Docker Image ---"
echo "Project Root: ${PROJECT_ROOT}"
echo "Local Image: ${LOCAL_IMAGE_NAME}"
echo "Remote Image: ${REMOTE_IMAGE_NAME}"

# --- ECR Login ---
echo "Attempting to log in to ECR..."
aws ecr get-login-password --region "${AWS_REGION}" --profile cue-uat| docker login --username AWS --password-stdin "${ECR_REGISTRY}"
if [ $? -ne 0 ]; then
    echo "ECR login failed. Please check your AWS credentials and region."
    exit 1
fi
echo "ECR login successful."

# --- Docker Build ---
# We run the build from the project root to ensure the Dockerfile context is correct.
cd "${PROJECT_ROOT}" || exit

echo "Building Docker image from Dockerfile.aws..."
docker build --no-cache -t "${LOCAL_IMAGE_NAME}" -f Dockerfile.aws .
if [ $? -ne 0 ]; then
    echo "Docker build failed."
    exit 1
fi
echo "Docker build successful."

# --- Tag and Push ---
echo "Tagging image for ECR push..."
docker tag "${LOCAL_IMAGE_NAME}" "${REMOTE_IMAGE_NAME}"

echo "Pushing image to ECR..."
docker push "${REMOTE_IMAGE_NAME}"
if [ $? -ne 0 ]; then
    echo "Docker push failed."
    exit 1
fi
echo "Image pushed successfully to ${REMOTE_IMAGE_NAME}"

# --- Cleanup ---
echo "Cleaning up local Docker images..."
docker rmi "${LOCAL_IMAGE_NAME}" "${REMOTE_IMAGE_NAME}"

echo "API build and push complete."
