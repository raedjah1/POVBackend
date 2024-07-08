#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status.

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# Check if required environment variables are set
if [ -z "$REGION" ]; then
    echo "Error: REGION environment variable is not set. Please check your .env file."
    exit 1
fi

# Function to deploy an Elastic Beanstalk environment
deploy_environment() {
    local env_name=$1
    local platform=$2

    # Check if the environment exists
    if ! eb status $env_name 2>/dev/null; then
        echo "Creating environment $env_name..."
        eb create $env_name --platform "$platform" --region $REGION
    else
        echo "Deploying to existing environment $env_name..."
        eb use $env_name
        eb deploy $env_name
    fi
}

# Deploy Backend Environment
echo "Deploying Backend Environment..."
deploy_environment "pov-backend" "Python 3.9 running on 64bit Amazon Linux 2023"

# Deploy Streaming Environment
echo "Deploying Streaming Environment..."
cd streaming-env
deploy_environment "pov-streaming" "Docker running on 64bit Amazon Linux 2"
cd ../

echo "Deployment process completed successfully."