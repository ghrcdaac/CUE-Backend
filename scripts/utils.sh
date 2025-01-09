setup_temp() {
    rm -rf ${DIR}/temp
    mkdir -p ${DIR}/temp
}

remove_temp() {
    cd ${DIR}
    rm -rf ${DIR}/temp
}

clear_artifacts() {
    rm -f ${DIR}/artifacts/*
}

create_dependency_zip() {
    mkdir -p ${DIR}/temp/package
    pip install -r ${DIR}/src/python/event_lambdas/requirements.txt -t ${DIR}/temp/package
    cp -R ${DIR}/src/python/lambda_utils ${DIR}/temp/package
    cd ${DIR}/temp/package
    touch __init__.py
    zip -r ../my_deployment_package.zip .
    cd ${DIR}
}

install_lambda() {
    cd ${DIR}/artifacts
    cp ${DIR}/src/python/event_lambdas/${1}.py .
    cp ${DIR}/temp/my_deployment_package.zip ${1}-lambda.zip
    zip ${1}-lambda.zip ${1}.py
    rm ${1}.py
}

# build_api() {

# }