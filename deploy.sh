#!/bin/bash

# deploy.sh

set -e  # Exit immediately if a command exits with a non-zero status.

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# Check if required environment variables are set
if [ -z "$VPC_ID" ] || [ -z "$SUBNET_ID" ] || [ -z "$REGION" ] || [ -z "$BACKEND_ECR_REPO" ]; then
    echo "Error: Missing required environment variables. Please check your .env file."
    exit 1
fi

# Function to check if VPC setup is complete
check_vpc_setup() {
    # Check if Internet Gateway is attached to the VPC
    IGW_ID=$(aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=$VPC_ID" --query 'InternetGateways[0].InternetGatewayId' --output text)
    
    # Check if a route to 0.0.0.0/0 exists in the route table associated with the subnet
    ROUTE_TABLE_ID=$(aws ec2 describe-route-tables --filters "Name=association.subnet-id,Values=$SUBNET_ID" --query 'RouteTables[0].RouteTableId' --output text)
    ROUTE_EXISTS=$(aws ec2 describe-route-tables --route-table-id $ROUTE_TABLE_ID --query 'RouteTables[0].Routes[?DestinationCidrBlock==`0.0.0.0/0`]' --output text)

    if [ -n "$IGW_ID" ] && [ -n "$ROUTE_EXISTS" ]; then
        return 0  # VPC setup is complete
    else
        return 1  # VPC setup is incomplete
    fi
}

# Step 1: Set up VPC and Subnet (if not already done)
setup_vpc() {
    echo "Checking VPC setup..."
    
    if check_vpc_setup; then
        echo "VPC setup is already complete. Skipping..."
        return
    fi

    echo "Setting up VPC and Subnet..."
    
    # Enable DNS hostnames for the VPC
    aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames

    # Create and attach an internet gateway if not exists
    if [ -z "$IGW_ID" ]; then
        IGW_ID=$(aws ec2 create-internet-gateway --query 'InternetGateway.InternetGatewayId' --output text)
        aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID
    fi

    # Create a route table and associate it with the subnet if not exists
    if [ -z "$ROUTE_TABLE_ID" ]; then
        ROUTE_TABLE_ID=$(aws ec2 create-route-table --vpc-id $VPC_ID --query 'RouteTable.RouteTableId' --output text)
        aws ec2 associate-route-table --route-table-id $ROUTE_TABLE_ID --subnet-id $SUBNET_ID
    fi

    # Add a route to the internet gateway if not exists
    if [ -z "$ROUTE_EXISTS" ]; then
        aws ec2 create-route --route-table-id $ROUTE_TABLE_ID --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID
    fi

    echo "VPC and Subnet setup complete."
}

# Step 2: Build and push Docker image for backend
build_and_push_backend() {
    echo "Building and pushing backend Docker image..."
    docker build -t $BACKEND_ECR_REPO:latest .
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $BACKEND_ECR_REPO
    docker push $BACKEND_ECR_REPO:latest
    echo "Backend Docker image pushed to ECR."
}

# Function to apply environment-specific configurations
apply_env_config() {
    local env_type=$1
    local config_file=""

    if [ "$env_type" == "backend" ]; then
        config_file=".ebextensions/04_backend_autoscaling.config"
    elif [ "$env_type" == "streaming" ]; then
        config_file=".ebextensions/04_streaming_autoscaling.config"
    else
        echo "Unknown environment type: $env_type"
        return 1
    fi

    if [ -f "$config_file" ]; then
        cp "$config_file" .ebextensions/04_autoscaling.config
        echo "Applied $env_type autoscaling configuration."
    else
        echo "Configuration file not found: $config_file"
        return 1
    fi
}

# Step 3: Create or update Elastic Beanstalk environments
update_eb_environments() {
    echo "Updating Elastic Beanstalk environments..."

    # Backend Environment
    apply_env_config "backend"
    eb use pov-backend-env
    eb deploy
    rm .ebextensions/04_autoscaling.config  # Clean up

    # Streaming Environment
    apply_env_config "streaming"
    eb use pov-streaming-env
    eb deploy
    rm .ebextensions/04_autoscaling.config  # Clean up

    echo "Elastic Beanstalk environments updated."
}

# Step 4: Configure security groups
configure_security_groups() {
    echo "Configuring security groups..."

    # Create security group for backend if it doesn't exist
    BACKEND_SG_ID=$(aws ec2 describe-security-groups --filters Name=group-name,Values=pov-backend-sg Name=vpc-id,Values=$VPC_ID --query 'SecurityGroups[0].GroupId' --output text)
    if [ "$BACKEND_SG_ID" == "None" ]; then
        BACKEND_SG_ID=$(aws ec2 create-security-group --group-name pov-backend-sg --description "Security group for POV backend" --vpc-id $VPC_ID --query 'GroupId' --output text)
    fi

    # Create security group for streaming if it doesn't exist
    STREAMING_SG_ID=$(aws ec2 describe-security-groups --filters Name=group-name,Values=pov-streaming-sg Name=vpc-id,Values=$VPC_ID --query 'SecurityGroups[0].GroupId' --output text)
    if [ "$STREAMING_SG_ID" == "None" ]; then
        STREAMING_SG_ID=$(aws ec2 create-security-group --group-name pov-streaming-sg --description "Security group for POV streaming" --vpc-id $VPC_ID --query 'GroupId' --output text)
    fi

    # Allow inbound traffic between the security groups
    aws ec2 authorize-security-group-ingress --group-id $BACKEND_SG_ID --protocol all --source-group $STREAMING_SG_ID
    aws ec2 authorize-security-group-ingress --group-id $STREAMING_SG_ID --protocol all --source-group $BACKEND_SG_ID

    # Allow inbound traffic from the internet to the backend
    aws ec2 authorize-security-group-ingress --group-id $BACKEND_SG_ID --protocol tcp --port 8000 --cidr 0.0.0.0/0

    # Allow inbound traffic from the internet to the streaming service
    aws ec2 authorize-security-group-ingress --group-id $STREAMING_SG_ID --protocol tcp --port 1935 --cidr 0.0.0.0/0

    echo "Security groups configured."
}

# Main execution
echo "Starting deployment process..."

setup_vpc
build_and_push_backend
update_eb_environments
configure_security_groups

echo "Deployment process completed successfully."
