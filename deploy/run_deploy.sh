#!/usr/bin/env bash
set -euo pipefail

# Usage:
# AWS_PROFILE=ghw-deployer REGION=us-east-2 ./deploy/run_deploy.sh

REGION=${REGION:-us-east-2}
KEY_NAME=${KEY_NAME:-ghw-key}
SG_NAME=${SG_NAME:-ghw-sg}
INSTANCE_TYPE=${INSTANCE_TYPE:-t3a.small}
CLOUD_INIT=${CLOUD_INIT:-deploy/cloud-init.yml}

PROFILE_FLAG=""
if [ -n "${AWS_PROFILE:-}" ]; then
  PROFILE_FLAG="--profile $AWS_PROFILE"
fi

echo "Region: $REGION"

echo "Fetching Ubuntu 22.04 AMI via SSM..."
AMI_ID=$(aws ssm get-parameter --name /aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id --region $REGION $PROFILE_FLAG --query Parameter.Value --output text)

if [ -z "$AMI_ID" ]; then
  echo "Failed to fetch AMI ID." >&2
  exit 1
fi

echo "AMI: $AMI_ID"

# Create key pair if not present locally
if [ ! -f "${KEY_NAME}.pem" ]; then
  echo "Creating key pair $KEY_NAME and saving ${KEY_NAME}.pem"
  aws ec2 create-key-pair --key-name $KEY_NAME $PROFILE_FLAG --query 'KeyMaterial' --output text > ${KEY_NAME}.pem
  chmod 600 ${KEY_NAME}.pem
else
  echo "Key file ${KEY_NAME}.pem already exists; skipping create." 
fi

# Determine default VPC
VPC_ID=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --region $REGION $PROFILE_FLAG --query 'Vpcs[0].VpcId' --output text)
if [ -z "$VPC_ID" ] || [ "$VPC_ID" = "None" ]; then
  VPC_ID=$(aws ec2 describe-vpcs --region $REGION $PROFILE_FLAG --query 'Vpcs[0].VpcId' --output text)
fi

echo "Using VPC: $VPC_ID"

# Create or get security group
SG_ID=""
set +e
SG_ID=$(aws ec2 describe-security-groups --group-names $SG_NAME --region $REGION $PROFILE_FLAG --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null)
EC2_DESC_RET=$?
set -e

if [ "$EC2_DESC_RET" -ne 0 ] || [ -z "$SG_ID" ] || [ "$SG_ID" = "None" ]; then
  echo "Creating security group $SG_NAME in VPC $VPC_ID"
  SG_ID=$(aws ec2 create-security-group --group-name $SG_NAME --description "ghw access" --vpc-id $VPC_ID --region $REGION $PROFILE_FLAG --query GroupId --output text)
  echo "Created SG $SG_ID"
else
  echo "Found existing SG $SG_ID"
fi

# Allow SSH (adjust CIDR as needed)
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0 --region $REGION $PROFILE_FLAG || true

if [ ! -f "$CLOUD_INIT" ]; then
  echo "cloud-init file $CLOUD_INIT not found. Please ensure deploy/cloud-init.yml exists." >&2
  exit 1
fi

echo "Launching instance..."
INSTANCE_ID=$(aws ec2 run-instances --image-id $AMI_ID --count 1 --instance-type $INSTANCE_TYPE --key-name $KEY_NAME --security-group-ids $SG_ID --user-data file://$CLOUD_INIT --region $REGION $PROFILE_FLAG --query 'Instances[0].InstanceId' --output text)

echo "Instance launched: $INSTANCE_ID"

echo "Waiting for instance to be running..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION $PROFILE_FLAG

PUBLIC_IP=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --region $REGION $PROFILE_FLAG --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

echo "Instance is running at: $PUBLIC_IP"

echo "SSH command (from this directory):"
echo "ssh -i ${KEY_NAME}.pem ubuntu@${PUBLIC_IP}"

echo "Done. After SSH, edit /etc/ghw/env and set TELEGRAM_TOKEN, then: sudo systemctl restart ghw.service; sudo journalctl -u ghw.service -f"
