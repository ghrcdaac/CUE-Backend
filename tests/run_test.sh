#!/bin/env bash
# Run pytest test by group: unit, integration, or both.
#
# Usage:
#   ./run_tests.sh [--unit | --integration | --all]
#
# Examples:
#   ./run_tests.sh --unit
#   ./run_tests.sh --integration
#   ./run_tests.sh --all 
# Note: 
# If not option is provided defaults to run all tests 

set -u

mode="all"
root="/app"
pytest_args=()

print_usage() {
  echo "Usage: $0 [--unit | --integration | --all]" 
  echo "Options:"
  echo "  -u, --unit           Run unit tests only"
  echo "  -i, --integration    Run integration tests only"
  echo "  -a, --all            Run both unit and integration tests (default)"
  echo "  -h, --help           Show this help"
}

while [ $# -gt 0 ]; do
  case "$1" in
    -u|--unit) mode="unit"; shift ;;
    -i|--integration) mode="integration"; shift ;;
    -a|--all) mode="all"; shift ;;
    -h|--help) print_usage; exit 0 ;;
#    -r|--root)
#      if [ $# -lt 2 ]; then
#        echo "Error: --root requires a path" >&2
#        exit 64
#      fi
#      root="$2"
#      shift 2
#      ;;
  esac
done

# Ensure pytest is available
if ! command -v pytest >/dev/null 2>&1; then
  echo "Error: pytest not found in PATH" >&2
  exit 127
fi

# Change to project root if provided
if [ "$root" != "/app" ]; then
  if [ ! -d "$root" ]; then
    echo "Error: root directory '$root' does not exist" >&2
    exit 66
  fi
  cd "$root" || {
    echo "Error: failed to cd into '$root'" >&2
    exit 66
  }
fi

run_unit_tests() {
    # Run unit tests
    pytest -v \
    --cov=v2 --cov=event_lambdas \
    --cov-config=tests/unit_tests/.coveragerc \
    --cov-report=term-missing --cov-append \
    tests/unit_tests/
}

run_integration_tests() {
    # Run integration tests
    pytest -v \
    --cov=v2 --cov=event_lambdas \
    --cov-config=tests/integration_tests/.coveragerc \
    --cov-report=term-missing --cov-append \
    tests/integration_tests/
}

final_exit_code=0

case "$mode" in
  unit)
    run_unit_tests 
    final_exit_code=$?
    ;;
  integration)
    run_integration_tests 
    final_exit_code=$?
    ;;
  all)
    run_unit_tests 
    exit_code_1=$?
    run_integration_tests
    exit_code_2=$?
    if [ "$exit_code_1" -eq 0 ] && [ "$exit_code_2" -eq 0 ] ; then
        final_exit_code=0
    else
      # Return the more severe non-zero code (higher number).
      # pytest exit codes: 0 pass, 1 fail, 2 interrupt, 3 internal, 4 usage, 5 no tests collected.
      if [ "$exit_code_1" -ge "$exit_code_2" ]; then final_exit_code="$exit_code_1"; else final_exit_code="$exit_code_2"; fi
    fi
    ;;
  *)
    echo "Unknown mode: $mode" >&2
    exit 64
    ;;
esac
coverage erase

exit "$final_exit_code"