#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DIR="$( dirname "$DIR" )"

echo "Project root directory: ${DIR}"

source "${DIR}/scripts/utils.sh"

# Cleanup from past builds
setup_temp
clear_artifacts

# Package all event-driven lambdas
create_dependency_zip
install_lambda infected-logger
install_lambda notification-manager
install_lambda email-sender
install_lambda file-transfer

# Cleanup
remove_temp

echo "All Lambda functions built successfully."
