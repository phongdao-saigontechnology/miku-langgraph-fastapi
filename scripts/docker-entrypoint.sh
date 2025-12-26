#!/bin/bash
set -e

# Print environment info
echo "============================================"
echo "Starting Miku LangGraph FastAPI"
echo "============================================"
echo "APP_ENV: ${APP_ENV:-development}"
echo "LLM_PROVIDER: ${LLM_PROVIDER:-mistral}"

# Show only the part after @ for database URL (for security)
if [[ -n "$POSTGRES_URL" && "$POSTGRES_URL" == *"@"* ]]; then
    DB_DISPLAY=$(echo "$POSTGRES_URL" | sed 's/.*@/@/')
    echo "Database URL: *********$DB_DISPLAY"
else
    echo "Database URL: ${POSTGRES_URL:-Not set}"
fi

# Check required sensitive environment variables
required_vars=("JWT_SECRET_KEY")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        missing_vars+=("$var")
    fi
done

# Check for LLM API key based on provider
LLM_PROVIDER=${LLM_PROVIDER:-mistral}
case "$LLM_PROVIDER" in
    mistral)
        if [[ -z "${MISTRAL_API_KEY}" && -z "${LLM_API_KEY}" ]]; then
            missing_vars+=("MISTRAL_API_KEY or LLM_API_KEY")
        else
            echo "LLM API Key: ✓ (Mistral)"
        fi
        ;;
    openai)
        if [[ -z "${OPENAI_API_KEY}" && -z "${LLM_API_KEY}" ]]; then
            missing_vars+=("OPENAI_API_KEY or LLM_API_KEY")
        else
            echo "LLM API Key: ✓ (OpenAI)"
        fi
        ;;
    google)
        if [[ -z "${GOOGLE_API_KEY}" && -z "${LLM_API_KEY}" ]]; then
            missing_vars+=("GOOGLE_API_KEY or LLM_API_KEY")
        else
            echo "LLM API Key: ✓ (Google)"
        fi
        ;;
    *)
        if [[ -z "${LLM_API_KEY}" ]]; then
            missing_vars+=("LLM_API_KEY")
        else
            echo "LLM API Key: ✓"
        fi
        ;;
esac

if [[ ${#missing_vars[@]} -gt 0 ]]; then
    echo ""
    echo "ERROR: The following required environment variables are missing:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Please set these in your .env.${APP_ENV:-development} file or docker-compose.yml"
    exit 1
fi

# Print final configuration
echo ""
echo "Configuration:"
echo "  LLM Model: ${LLM_MODEL:-default}"
echo "  MCP Enabled: ${MCP_ENABLED:-false}"
echo "  Debug Mode: ${DEBUG:-false}"
echo "============================================"
echo ""

# Execute the CMD
exec "$@"
