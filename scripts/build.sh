DIR=$(pwd)

#Set up functions
source $DIR/scripts/utils.sh

#Cleanup from past builds
setup_temp
clear_artifacts

#Install event lambdas
create_dependency_zip
install_lambda infected-logger

#Build API Docker image
#build_api

#Cleanup
remove_temp