#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DIR="$( dirname "$DIR" )"

echo "Project root directory: ${DIR}"

source "${DIR}/scripts/utils.sh"

# Cleanup from past builds
setup_temp
clear_artifacts

# Package all event-driven lambdas
build_common_dependencies
install_lambda infected-logger
install_lambda notification-manager
# install_lambda email-sender
# install_lambda file-transfer
# install_lambda process-athena-query
# install_lambda cost-update
install_lambda manual-file-transfer
install_lambda manual-infected-logger
install_lambda manual-email-sender
install_lambda manual-notification-manager
install_lambda manual-cost-update
install_lambda manual-process-athena-query
install_lambda cleanup-uploads

# Cleanup
remove_temp

echo "All Lambda functions built successfully."
