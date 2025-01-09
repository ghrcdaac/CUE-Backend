#!/bin/bash
export REPO_NAME=cue/api
export AWS_REGION=us-west-2


function push_to_ecr(){
    # AWS account number
    # prefix = $2
    # tag = $3
    docker_image_name=$1.dkr.ecr.$AWS_REGION.amazonaws.com/${REPO_NAME}:$3
    docker tag $REPO_NAME $docker_image_name
    
    echo "ECR login"
    aws ecr get-login-password \
        --region $AWS_REGION \
        | docker login \
            --username AWS \
            --password-stdin $1.dkr.ecr.$AWS_REGION.amazonaws.com

    echo "Pushing to ECR"
    docker push $docker_image_name
    docker rmi $docker_image_name
}

function build_docker(){
    docker_build="docker buildx build --push --platform linux/arm64 -t"
    ${docker_build} $1 .
}

build_docker ${REPO_NAME}

push_to_ecr $AWS_ACCOUNT_NUMBER ${ENV} ${TAG}