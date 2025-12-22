# EC2 Deployment Guide - Project Annapurna

## Prerequisites

- AWS Account with EC2 access
- SSH key pair for EC2 access
- Domain name (optional, for SSL)

---

## 1. Launch EC2 Instance

### Recommended Instance Type

| Workload | Instance Type | vCPUs | Memory | Monthly Cost (approx) |
|----------|--------------|-------|--------|----------------------|
| Development/Testing | t3.medium | 2 | 4 GB | ~$30 |
| **Production (Recommended)** | t3.large | 2 | 8 GB | ~$60 |
| High Traffic | t3.xlarge | 4 | 16 GB | ~$120 |

### Launch Steps

1. **Go to EC2 Dashboard** → Launch Instance

2. **Configure Instance:**
   - **Name:** `annapurna-api`
   - **AMI:** Ubuntu 22.04 LTS (64-bit x86)
   - **Instance type:** t3.large (recommended)
   - **Key pair:** Select or create new

3. **Network Settings:**
   - VPC: Default or your VPC
   - Auto-assign public IP: **Enable**

4. **Security Group Rules:**
   ```
   | Type  | Port  | Source    | Description           |
   |-------|-------|-----------|----------------------|
   | SSH   | 22    | Your IP   | SSH access           |
   | HTTP  | 80    | 0.0.0.0/0 | Web traffic          |
   | HTTPS | 443   | 0.0.0.0/0 | Secure web traffic   |
   | Custom| 8000  | 0.0.0.0/0 | API (optional)       |
   ```

5. **Storage:**
   - Root volume: 30 GB gp3 (minimum)
   - For production: 50+ GB recommended

6. **Launch the instance**

---

## 2. Connect to EC2

```bash
# Set permissions on your key
chmod 400 your-key.pem

# Connect via SSH
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>
```

---

## 3. Initial Server Setup

Run these commands on your EC2 instance:

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install essential tools
sudo apt-get install -y git curl wget htop

# Set timezone (optional)
sudo timedatectl set-timezone Asia/Kolkata
```

---

## 4. Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose plugin
sudo apt-get install -y docker-compose-plugin

# Log out and back in for group changes
exit
```

SSH back in:
```bash
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>

# Verify Docker installation
docker --version
docker compose version
```

---

## 5. Deploy Application

### Option A: Clone from Git

```bash
# Clone your repository
git clone https://github.com/your-repo/annapurna.git
cd annapurna
```

### Option B: Copy files from local machine

From your local machine:
```bash
# Create tarball (excluding unnecessary files)
cd /home/poojabhattsinghania/Desktop/KMKB/app
tar -czvf annapurna.tar.gz \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='.venv' \
    --exclude='*.pyc' \
    --exclude='data' \
    .

# Copy to EC2
scp -i your-key.pem annapurna.tar.gz ubuntu@<EC2_PUBLIC_IP>:~/

# On EC2: Extract files
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>
mkdir -p annapurna && cd annapurna
tar -xzvf ~/annapurna.tar.gz
rm ~/annapurna.tar.gz
```

---

## 6. Configure Environment

```bash
cd ~/annapurna

# Create production environment file
cat > .env << 'EOF'
# Database Configuration
DATABASE_NAME=annapurna
DATABASE_USER=annapurna
DATABASE_PASSWORD=YOUR_STRONG_PASSWORD_HERE

# LLM API Keys (REQUIRED)
GOOGLE_API_KEY=your_google_api_key
OPENAI_API_KEY=your_openai_api_key

# Qdrant Vector Database
QDRANT_URL=http://13.200.235.39:6333

# Application Settings
ENVIRONMENT=production
LOG_LEVEL=INFO
API_VERSION=v1
EOF

# Edit with your actual values
nano .env
```

**Important:** Replace placeholder values with actual credentials.

---

## 7. Create SSL Directory (for later)

```bash
mkdir -p nginx/ssl nginx/certbot
```

---

## 8. Start Services

```bash
cd ~/annapurna

# Build and start all services
docker compose -f docker-compose.prod.yml up -d --build

# Watch the build progress
docker compose -f docker-compose.prod.yml logs -f
```

The first build takes ~5-10 minutes (downloading dependencies, building images).

---

## 9. Verify Deployment

```bash
# Check all services are running
docker compose -f docker-compose.prod.yml ps

# Expected output:
# NAME                      STATUS
# annapurna-api             Up (healthy)
# annapurna-celery-beat     Up
# annapurna-celery-worker   Up
# annapurna-nginx           Up
# annapurna-postgres        Up (healthy)
# annapurna-redis           Up (healthy)

# Check API health
curl http://localhost/health

# Check logs if issues
docker compose -f docker-compose.prod.yml logs api --tail=100
```

---

## 10. Run Database Migrations

```bash
# Run Alembic migrations
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

---

## 11. Access Your API

Your API is now accessible at:

- **API Base URL:** `http://<EC2_PUBLIC_IP>`
- **API Docs:** `http://<EC2_PUBLIC_IP>/v1/docs`
- **ReDoc:** `http://<EC2_PUBLIC_IP>/v1/redoc`
- **Health Check:** `http://<EC2_PUBLIC_IP>/health`

---

## 12. Setup SSL (Optional but Recommended)

### Using Let's Encrypt with Certbot

```bash
# Install Certbot
sudo apt-get install -y certbot

# Stop nginx temporarily
docker compose -f docker-compose.prod.yml stop nginx

# Get certificate (replace with your domain)
sudo certbot certonly --standalone -d your-domain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/
sudo chown -R $USER:$USER nginx/ssl/

# Update nginx.conf to use HTTPS (uncomment SSL sections)
nano nginx/nginx.conf

# Restart nginx
docker compose -f docker-compose.prod.yml up -d nginx
```

### Auto-Renewal Cron Job

```bash
# Add to crontab
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet && docker compose -f ~/annapurna/docker-compose.prod.yml restart nginx") | crontab -
```

---

## 13. Useful Commands

```bash
# View all logs
docker compose -f docker-compose.prod.yml logs -f

# View specific service logs
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f celery-worker

# Restart a service
docker compose -f docker-compose.prod.yml restart api

# Stop all services
docker compose -f docker-compose.prod.yml down

# Stop and remove volumes (CAUTION: deletes data)
docker compose -f docker-compose.prod.yml down -v

# Rebuild and restart
docker compose -f docker-compose.prod.yml up -d --build

# Enter container shell
docker compose -f docker-compose.prod.yml exec api bash

# Check resource usage
docker stats
```

---

## 14. Monitoring & Maintenance

### View System Resources

```bash
# Check disk space
df -h

# Check memory
free -h

# Check Docker disk usage
docker system df

# Clean up unused Docker resources
docker system prune -a
```

### Backup Database

```bash
# Backup PostgreSQL
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U annapurna annapurna > backup_$(date +%Y%m%d).sql

# Restore (if needed)
cat backup.sql | docker compose -f docker-compose.prod.yml exec -T postgres psql -U annapurna annapurna
```

### Log Rotation

Create `/etc/logrotate.d/docker-containers`:
```bash
sudo tee /etc/logrotate.d/docker-containers << EOF
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    size=10M
    missingok
    delaycompress
    copytruncate
}
EOF
```

---

## 15. Troubleshooting

### Container won't start

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs api --tail=100

# Check if port is in use
sudo lsof -i :8000
sudo lsof -i :80
```

### Database connection issues

```bash
# Check if postgres is running
docker compose -f docker-compose.prod.yml ps postgres

# Check postgres logs
docker compose -f docker-compose.prod.yml logs postgres

# Connect to postgres directly
docker compose -f docker-compose.prod.yml exec postgres psql -U annapurna
```

### Out of memory

```bash
# Check memory usage
docker stats

# Increase swap (temporary fix)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Rebuild from scratch

```bash
# Stop everything
docker compose -f docker-compose.prod.yml down

# Remove all containers and images
docker system prune -a

# Rebuild
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 16. Quick Reference - API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /v1/docs` | Swagger UI |
| `POST /v1/auth/send-otp` | Send OTP |
| `POST /v1/auth/verify-otp` | Verify OTP & login |
| `POST /v1/onboarding/start` | Start onboarding |
| `GET /v1/recommendations/first` | Get first recommendations |
| `GET /v1/recommendations/next-meal` | Get next meal |

---

## 17. Security Checklist

- [ ] Change default database password in `.env`
- [ ] Configure Security Group to allow only necessary ports
- [ ] Enable SSL/HTTPS
- [ ] Set up regular backups
- [ ] Configure CloudWatch for monitoring (optional)
- [ ] Enable AWS WAF for additional security (optional)
- [ ] Use AWS Secrets Manager for API keys (optional)

---

## Architecture Overview

```
                    ┌─────────────────────────────────────────┐
                    │              EC2 Instance               │
                    │                                         │
 Internet ──────────┤  ┌─────────┐      ┌──────────────────┐ │
     :80/:443       │  │  Nginx  │──────│   FastAPI (x4)   │ │
                    │  └─────────┘      └──────────────────┘ │
                    │                           │            │
                    │       ┌───────────────────┴──────┐     │
                    │       │                          │     │
                    │  ┌────▼────┐              ┌──────▼───┐ │
                    │  │  Redis  │              │ Postgres │ │
                    │  └─────────┘              └──────────┘ │
                    │       │                                │
                    │  ┌────▼────────────┐                   │
                    │  │  Celery Worker  │                   │
                    │  │  Celery Beat    │                   │
                    │  └─────────────────┘                   │
                    │                                         │
                    └──────────────────────────────────────── │
                                     │
                              ┌──────▼──────┐
                              │   Qdrant    │
                              │ (External)  │
                              └─────────────┘
```
