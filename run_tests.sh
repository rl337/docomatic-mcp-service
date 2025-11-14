#!/bin/bash
# Test runner script for Doc-O-Matic

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Doc-O-Matic Test Runner${NC}"
echo "================================"

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: UV is not installed. Please install UV first.${NC}"
    echo "Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    uv sync
fi

# Parse command line arguments
TEST_TYPE="${1:-all}"
COVERAGE="${2:-true}"

case "$TEST_TYPE" in
    unit)
        echo -e "${GREEN}Running unit tests...${NC}"
        if [ "$COVERAGE" = "true" ]; then
            uv run pytest tests/ -m "unit" --cov=docomatic --cov-report=term-missing --cov-report=html
        else
            uv run pytest tests/ -m "unit"
        fi
        ;;
    integration)
        echo -e "${GREEN}Running integration tests...${NC}"
        if [ "$COVERAGE" = "true" ]; then
            uv run pytest tests/integration/ -m "integration" --cov=docomatic --cov-report=term-missing --cov-report=html --cov-append
        else
            uv run pytest tests/integration/ -m "integration"
        fi
        ;;
    performance)
        echo -e "${GREEN}Running performance tests...${NC}"
        uv run pytest tests/performance/ -m "performance" -v
        ;;
    all)
        echo -e "${GREEN}Running all tests...${NC}"
        if [ "$COVERAGE" = "true" ]; then
            uv run pytest tests/ --cov=docomatic --cov-report=term-missing --cov-report=html --cov-report=xml
        else
            uv run pytest tests/
        fi
        ;;
    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo "Usage: $0 [unit|integration|performance|all] [coverage=true|false]"
        exit 1
        ;;
esac

echo -e "${GREEN}Tests completed!${NC}"
