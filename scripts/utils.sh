#!/bin/bash

# A collection of utility functions for the build process.

# Ensures a clean temporary directory exists for the build.
setup_temp() {
    echo "--- Setting up temporary build directory ---"
    rm -rf "${DIR}/temp"
    mkdir -p "${DIR}/temp"
}

# Removes the temporary directory after the build is complete.
remove_temp() {
    echo "--- Cleaning up temporary build directory ---"
    cd "${DIR}" || exit
    rm -rf "${DIR}/temp"
}

# Clears the artifacts directory to ensure a fresh build.
# Creates the directory if it doesn't exist.
clear_artifacts() {
    echo "--- Clearing previous artifacts ---"
    mkdir -p "${DIR}/artifacts"
    rm -f "${DIR}/artifacts/*"
}

# Creates a base zip file with dependencies installed inside a Docker container
# to ensure they are compatible with the AWS Lambda Linux environment.
create_dependency_zip() {
    echo "--- Creating common dependency layer using Docker ---"
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        echo "ERROR: Docker is not running. Please start Docker and try again."
        exit 1
    fi

    local package_dir="${DIR}/temp/package"
    mkdir -p "${package_dir}"
    
    echo "Installing requirements into Docker container for Lambda compatibility..."
    # This command runs a temporary Docker container based on the official AWS Lambda Python image.
    # It mounts the requirements file and the target package directory as volumes.
    # It then runs pip install inside the container, placing the Linux-compatible files
    # into the mounted package directory on your local machine.
    # CORRECTED: Added --entrypoint to override the default container command.
    docker run --rm \
        --entrypoint "/bin/sh" \
        -v "${DIR}/src/python/event_lambdas/requirements.txt:/var/task/requirements.txt:ro" \
        -v "${package_dir}:/var/task/package_out" \
        public.ecr.aws/lambda/python:3.13 \
        -c "pip install -r /var/task/requirements.txt -t /var/task/package_out"

    if [ $? -ne 0 ]; then
        echo "ERROR: pip install failed inside the Docker container."
        exit 1
    fi
    
    echo "Copying shared lambda_utils module..."
    cp -R "${DIR}/src/python/lambda_utils" "${package_dir}"
    
    cd "${package_dir}" || exit
    zip -r -q ../my_deployment_package.zip .
    cd "${DIR}" || exit
    echo "Dependency layer created successfully at temp/my_deployment_package.zip"
}

# Packages a specific Lambda function.
install_lambda() {
    local lambda_name_arg=$1
    echo "--- Packaging Lambda: ${lambda_name_arg} ---"
    
    cp "${DIR}/temp/my_deployment_package.zip" "${DIR}/artifacts/${lambda_name_arg}-lambda.zip"

    cd "${DIR}/src/python/event_lambdas/" || exit
    
    local lambda_package_name=${lambda_name_arg//-/_}

    if [ -d "${lambda_package_name}" ]; then
        echo "Found package directory: '${lambda_package_name}'. Adding to zip..."
        zip -r -q "${DIR}/artifacts/${lambda_name_arg}-lambda.zip" "${lambda_package_name}"
    else
        echo "ERROR: Could not find lambda source directory '${lambda_package_name}/'."
        cd "${DIR}" || exit
        exit 1
    fi
    
    cd "${DIR}" || exit
    echo "Successfully packaged ${lambda_name_arg}-lambda.zip in artifacts directory."
}
