Deployment: quick EC2 bootstrap (us-east-2)
=========================================

Files added:
- `deploy/cloud-init.yml` — cloud-init to bootstrap an Ubuntu instance: installs packages, clones repo into `/opt/ghw`, creates venv, writes `/etc/ghw/env` and a `systemd` unit.
- `deploy/backup.sh` — simple script to upload `/opt/ghw/ghw.db` to S3 (`S3_BUCKET` configured in `/etc/ghw/env`).

How to launch (recommended via AWS CLI using profile `ghw-deployer`):

1) Create a keypair (one-time):

```bash
aws ec2 create-key-pair --key-name ghw-key --query 'KeyMaterial' --output text --profile ghw-deployer --region us-east-2 > ghw-key.pem
chmod 600 ghw-key.pem
```

2) Create a security group that allows SSH only:

```bash
SG_ID=$(aws ec2 create-security-group --group-name ghw-sg --description "ghw ssh" --vpc-id $(aws ec2 describe-vpcs --profile ghw-deployer --region us-east-2 --query 'Vpcs[0].VpcId' --output text) --profile ghw-deployer --region us-east-2 --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0 --profile ghw-deployer --region us-east-2
echo $SG_ID
```

3) Find latest Ubuntu 22.04 AMI (Canonical owner 099720109477):

```bash
AMI=$(aws ec2 describe-images --owners 099720109477 --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" "Name=state,Values=available" --query 'Images | sort_by(@, &CreationDate)[-1].ImageId' --profile ghw-deployer --region us-east-2 --output text)
echo $AMI
```

4) Launch the instance with cloud-init:

```bash
aws ec2 run-instances --image-id $AMI --count 1 --instance-type t3.small --key-name ghw-key --security-group-ids $SG_ID --user-data file://deploy/cloud-init.yml --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=ghw-bot}]' --profile ghw-deployer --region us-east-2
```

5) After instance is running, ssh in and set `/etc/ghw/env` TELEGRAM_TOKEN and optionally `S3_BUCKET`, then restart the service:

```bash
ssh -i ghw-key.pem ubuntu@<EC2_PUBLIC_IP>
sudoedit /etc/ghw/env   # paste TELEGRAM_TOKEN=your_token and S3_BUCKET=your-bucket
sudo systemctl restart ghw.service
sudo journalctl -u ghw.service -f
```

6) Optional: add a cron job for backups (runs daily at 03:00):

```bash
(sudo crontab -l 2>/dev/null; echo "0 3 * * * /opt/ghw/deploy/backup.sh >> /var/log/ghw-backup.log 2>&1") | sudo crontab -
```

Security & notes
- The `cloud-init.yml` writes `/etc/ghw/env` with permissions 600. Keep `TELEGRAM_TOKEN` secret.
- For production, use an EC2 Instance Profile (IAM Role) with an S3 policy instead of long-lived keys.
- If you want I can generate a CloudFormation or Terraform template next.
