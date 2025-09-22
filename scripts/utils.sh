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
clear_artifacts() {
    echo "--- Clearing previous artifacts ---"
    mkdir -p "${DIR}/artifacts"
    rm -f "${DIR}/artifacts/*"
}


build_common_dependencies() {
    echo "--- Building common dependency layer using Docker ---"
    
    if ! docker info > /dev/null 2>&1; then
        echo "ERROR: Docker is not running. Please start Docker and try again."
        exit 1
    fi

    local common_deps_dir="${DIR}/temp/common_deps"
    mkdir -p "${common_deps_dir}"
    
    echo "Installing requirements into Docker container for Lambda compatibility..."
    docker run --rm \
        --entrypoint "/bin/sh" \
        -v "${DIR}/src/python/event_lambdas/requirements.txt:/var/task/requirements.txt:ro" \
        -v "${common_deps_dir}:/var/task/package_out" \
        public.ecr.aws/lambda/python:3.13 \
        -c "pip install -r /var/task/requirements.txt -t /var/task/package_out"

    if [ $? -ne 0 ]; then
        echo "ERROR: pip install failed inside the Docker container."
        exit 1
    fi
    # Create a 'core' package in the build layer and copy ONLY the db.py file into it.
    echo "Copying shared core database utility..."
    local core_target_dir="${common_deps_dir}/core"
    mkdir -p "${core_target_dir}"
    cp "${DIR}/src/python/api/core/db.py" "${core_target_dir}/"
    cp "${DIR}/src/python/api/core/logging_config.py" "${core_target_dir}/"
    cp "${DIR}/src/python/api/core/db_pool.py" "${core_target_dir}/"
    cp "${DIR}/src/python/api/core/idfs_certs.json" "${core_target_dir}/"
    # Add an __init__.py to make 'core' a package, allowing `from core.db import ...`
    touch "${core_target_dir}/__init__.py"
     
    echo "Common dependency layer created successfully."
}

# This function now reuses the common dependency layer, making it much faster.
install_lambda() {
    local lambda_name_arg=$1
    echo "--- Packaging Lambda: ${lambda_name_arg} ---"

    local build_dir="${DIR}/temp/${lambda_name_arg}"
    mkdir -p "${build_dir}"

    # 1. Quickly copy the pre-built common dependencies.
    cp -R "${DIR}/temp/common_deps/." "${build_dir}/"

    # 2. Add the Lambda's specific source code.
    local lambda_package_name=${lambda_name_arg//-/_}
    local source_path="${DIR}/src/python/event_lambdas/${lambda_package_name}"
    
    if [ -d "${source_path}" ]; then
        cp -R "${source_path}/." "${build_dir}/"
    else
        local source_file="${DIR}/src/python/event_lambdas/${lambda_name_arg}.py"
        if [ -f "${source_file}" ]; then
            cp "${source_file}" "${build_dir}/"
        else
            echo "ERROR: Could not find source for '${lambda_name_arg}'."
            exit 1
        fi
    fi

    # 3. Zip the complete package.
    cd "${build_dir}" || exit
    zip -r -q "${DIR}/artifacts/${lambda_name_arg}-lambda.zip" .
    cd "${DIR}" || exit
    
    echo "Successfully packaged ${lambda_name_arg}-lambda.zip."
}

