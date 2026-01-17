# 🚀 Smart Prompt Parser - Push-to-Deploy Pipeline

This guide will help you set up automatic deployment of the Smart Prompt Parser & Canonicalisation Engine to AWS EC2.

## 📋 Prerequisites

- AWS Account with EC2 access
- Docker Hub account
- GitHub repository with this code

## 🔥 Phase 1: Repository Setup (COMPLETED)

✅ **Dockerfile** - Production-ready container
✅ **.dockerignore** - Optimized build context
✅ **GitHub Actions Workflow** - Automated CI/CD pipeline
✅ **Production Config** - Environment variable template

## 🏗️ Phase 2: AWS EC2 Setup (YOU DO THIS)

### Launch EC2 Instance

1. **Go to AWS Console** → EC2 → Launch Instance
2. **Choose AMI**: Ubuntu Server 22.04 LTS (HVM)
3. **Instance Type**: t3.medium (2 vCPU, 4GB RAM) or larger for production
4. **Key Pair**: Create new key pair, download `.pem` file
5. **Security Group**:
   - SSH (Port 22): My IP
   - Custom TCP (Port 8000): Anywhere (0.0.0.0/0)
6. **Storage**: 20GB gp3 (default is fine)

### Connect to EC2

```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

### Install Docker on EC2

```bash
sudo apt-get update
sudo apt-get install -y docker.io
sudo usermod -aG docker ubuntu
exit  # Reconnect for group changes to take effect
```

## 🔐 Phase 3: GitHub Secrets Setup (YOU DO THIS)

Go to **GitHub Repository** → **Settings** → **Secrets and variables** → **Actions**

Add these secrets:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `DOCKER_USERNAME` | Your DockerHub username | Docker Hub login |
| `DOCKER_PASSWORD` | Your DockerHub password/token | Docker Hub password or access token |
| `EC2_HOST` | Your EC2 Public IP | EC2 instance IP address |
| `EC2_KEY` | Contents of `.pem` file | SSH private key (copy entire file content) |
| `PORTKEY_API_KEY` | Your Portkey API key | From Portkey dashboard |
| `DB_HOST` | Database host | PostgreSQL hostname |
| `DB_PASSWORD` | Database password | PostgreSQL password |
| `DB_USER` | Database user | PostgreSQL username |
| `DB_NAME` | Database name | PostgreSQL database name |
| `REDIS_HOST` | Redis host | Redis hostname |
| `REDIS_PASSWORD` | Redis password | Redis password |
| `QDRANT_HOST` | Qdrant host | Qdrant hostname |
| `QDRANT_API_KEY` | Qdrant API key | Qdrant API key |
| `AWS_ACCESS_KEY_ID` | AWS access key | For Secrets Manager |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | For Secrets Manager |
| `AWS_DEFAULT_REGION` | AWS region | e.g., us-east-1 |

## 🧪 Phase 4: Test Deployment

### Trigger Deployment

1. **Make a change** to any file in the repository
2. **Commit and push** to the `main` branch
3. **Watch GitHub Actions** → See the pipeline run
4. **Check your app** at `http://YOUR_EC2_IP:8000`

### Health Check

```bash
curl http://YOUR_EC2_IP:8000/health
```

## 🗄️ Database Setup (Optional)

For production, you'll need:

- **PostgreSQL** database (AWS RDS or self-hosted)
- **Redis** instance (AWS ElastiCache or self-hosted)
- **Qdrant** vector database (self-hosted or cloud)

Set the connection details in GitHub secrets.

## 🔧 Troubleshooting

### Check Container Logs

```bash
ssh -i your-key.pem ubuntu@YOUR_EC2_IP
docker logs smart-prompt-parser
```

### Restart Container

```bash
docker restart smart-prompt-parser
```

### View Running Containers

```bash
docker ps
```

## 🎯 What's Automated

✅ **Code Checkout** - Gets latest code from GitHub
✅ **Docker Build** - Builds optimized production image
✅ **Image Push** - Uploads to Docker Hub
✅ **EC2 Deploy** - SSH into server, pull & run new container
✅ **Zero Downtime** - Stops old container before starting new one
✅ **Environment Config** - Injects secrets securely

## 🚀 Next Steps

Once deployed, you can:
- Access the web interface at `http://YOUR_EC2_IP:8000`
- Use the API endpoints for prompt clustering
- Monitor logs via `docker logs`
- Scale by adjusting EC2 instance size

The pipeline will automatically deploy every time you push to `main`! 🎉
