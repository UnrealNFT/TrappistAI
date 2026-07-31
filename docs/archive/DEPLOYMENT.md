# 🚀 Production Deployment Guide

Deploy TrappistAI to production on VPS, cloud platforms, or dedicated servers.

---

## 🏗️ Deployment Options

### Option 1: Docker on VPS (Recommended)
- **Providers**: Hetzner, DigitalOcean, Linode, Vultr
- **Cost**: $10-40/month
- **Requirements**: 4GB RAM, 2 vCPUs, 80GB storage

### Option 2: Managed Services
- **Frontend**: Vercel, Netlify, Cloudflare Pages
- **Backend**: Railway, Fly.io, Render
- **Database**: Supabase, Neon, RDS

### Option 3: Kubernetes
- **For**: High-traffic production (1000+ concurrent users)
- **Providers**: GKE, EKS, AKS, DigitalOcean Kubernetes

---

## 🐳 Option 1: Docker on VPS (Step-by-Step)

### 1. Provision VPS

**Hetzner** (Recommended for EU):
- CPX31: 4 vCPUs, 8GB RAM → €11.90/month
- Location: Helsinki, Nuremberg

**DigitalOcean**:
- Droplet: 4GB RAM, 2 vCPUs → $24/month
- Location: New York, Singapore

**Setup**:
```bash
# SSH to server
ssh root@your-server-ip

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose -y
```

### 2. Deploy Application

```bash
# Clone repo
git clone https://github.com/yourusername/trappistai.git
cd trappistai

# Create production .env files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Edit with production values
nano backend/.env
nano frontend/.env

# Start services
docker-compose up -d

# View logs
docker-compose logs -f
```

### 3. Configure Nginx Reverse Proxy

```bash
# Install Nginx
apt install nginx -y

# Create config
nano /etc/nginx/sites-available/trappistai
```

**Nginx Config**:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:5173;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
# Enable site
ln -s /etc/nginx/sites-available/trappistai /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### 4. SSL Certificate (Let's Encrypt)

```bash
# Install Certbot
apt install certbot python3-certbot-nginx -y

# Get certificate
certbot --nginx -d your-domain.com

# Auto-renewal (already configured)
certbot renew --dry-run
```

### 5. Firewall

```bash
# Allow HTTP/HTTPS/SSH
ufw allow 22
ufw allow 80
ufw allow 443
ufw enable
```

---

## 🔒 Production Security Checklist

- [ ] **Environment Variables**: All secrets in `.env`, never in code
- [ ] **SSL Certificate**: HTTPS only (Certbot)
- [ ] **Firewall**: UFW enabled, only 22/80/443 open
- [ ] **Database**: Strong password, localhost-only access
- [ ] **Rate Limiting**: Enabled in FastAPI (SlowAPI)
- [ ] **CORS**: Restricted to production domain
- [ ] **Backup**: Daily database backups
- [ ] **Monitoring**: Sentry, Datadog, or Grafana
- [ ] **Updates**: Regular security patches

---

## 📊 Monitoring & Logging

### Sentry (Error Tracking)

**Backend**:
```bash
pip install sentry-sdk[fastapi]
```

```python
import sentry_sdk
sentry_sdk.init(
    dsn="your-sentry-dsn",
    traces_sample_rate=1.0
)
```

**Frontend**:
```bash
npm install @sentry/react
```

```javascript
import * as Sentry from "@sentry/react";
Sentry.init({ dsn: "your-sentry-dsn" });
```

### Uptime Monitoring
- **UptimeRobot**: https://uptimerobot.com/ (free)
- **Pingdom**: https://www.pingdom.com/
- **Better Uptime**: https://betteruptime.com/

---

## 💾 Database Backups

### Daily Backup Script

```bash
# Create backup script
nano /root/backup-db.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/root/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="piranai"
DB_USER="piranai"

mkdir -p $BACKUP_DIR
pg_dump -U $DB_USER $DB_NAME > $BACKUP_DIR/piranai_$DATE.sql
gzip $BACKUP_DIR/piranai_$DATE.sql

# Keep only last 7 days
find $BACKUP_DIR -name "piranai_*.sql.gz" -mtime +7 -delete
```

```bash
# Make executable
chmod +x /root/backup-db.sh

# Add to crontab (daily at 2am)
crontab -e
# Add: 0 2 * * * /root/backup-db.sh
```

---

## 🔄 CI/CD (GitHub Actions)

### `.github/workflows/deploy.yml`

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy via SSH
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.VPS_HOST }}
          username: root
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /root/trappistai
            git pull origin main
            docker-compose down
            docker-compose up -d --build
```

**Setup**:
1. Generate SSH key: `ssh-keygen -t rsa -b 4096`
2. Add public key to VPS: `~/.ssh/authorized_keys`
3. Add private key to GitHub Secrets: `VPS_SSH_KEY`
4. Add VPS IP to GitHub Secrets: `VPS_HOST`

---

## 📈 Scaling Strategies

### Horizontal Scaling (Multiple Servers)

**Load Balancer** (Nginx):
```nginx
upstream backend {
    server backend1.example.com:8000;
    server backend2.example.com:8000;
    server backend3.example.com:8000;
}

server {
    location /api {
        proxy_pass http://backend;
    }
}
```

### Database Scaling

**Read Replicas**:
- Master: Write operations
- Replicas: Read operations (balance, payments)

**Connection Pooling**:
```python
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40
)
```

### Redis Caching

```bash
# Install Redis
apt install redis-server -y
```

```python
# Backend caching
from redis import Redis
cache = Redis(host='localhost', port=6379)

@app.get("/api/user/{wallet}/balance")
async def get_balance(wallet: str):
    cached = cache.get(f"balance:{wallet}")
    if cached:
        return {"tokens": int(cached)}
    
    balance = await get_user_balance(wallet)
    cache.setex(f"balance:{wallet}", 60, balance)
    return {"tokens": balance}
```

---

## 🌍 CDN (Optional)

### Cloudflare
- **DNS**: Point domain to Cloudflare
- **Proxy**: Enable orange cloud
- **Benefits**: DDoS protection, caching, free SSL

### Setup
1. Add site to Cloudflare
2. Update nameservers
3. Enable "Full (strict)" SSL
4. Enable Brotli compression

---

## 💰 Cost Breakdown (Production)

| Service | Provider | Cost/Month |
|---------|----------|------------|
| VPS (4GB RAM) | Hetzner | $12 |
| Domain | Namecheap | $1 |
| SSL | Let's Encrypt | Free |
| CDN | Cloudflare | Free |
| Monitoring | Sentry | Free (10k events) |
| Backups | VPS storage | Included |
| **Total** | | **~$15/month** |

**API Costs** (variable):
- WaveSpeed.ai: ~$1,290/month (1000 users/day)
- CSPR.cloud: $29/month (100k events)
- Groq: Free tier or $0.10/1M tokens

**Total Infrastructure**: **~$1,350/month** for 1000 users/day

---

## 🧪 Testing Deployment

```bash
# Test backend
curl https://api.your-domain.com/health

# Test frontend
curl https://your-domain.com

# Test payment verification
curl -X POST https://api.your-domain.com/api/payments/verify \
  -H "Content-Type: application/json" \
  -d '{"walletAddress": "test", "txHash": "test"}'
```

---

## 🔧 Troubleshooting

### Docker containers not starting
```bash
docker-compose logs backend
docker-compose logs frontend
```

### Database connection issues
```bash
docker exec -it trappistai-db psql -U piranai -d piranai
```

### Nginx errors
```bash
tail -f /var/log/nginx/error.log
```

---

## 📝 Post-Deployment Checklist

- [ ] Domain pointing to server IP
- [ ] SSL certificate installed
- [ ] Environment variables set
- [ ] Database backups scheduled
- [ ] Monitoring configured
- [ ] Firewall enabled
- [ ] Log rotation configured
- [ ] CI/CD pipeline tested
- [ ] Error tracking enabled
- [ ] Load testing completed

---

## 🆘 Support

- **Discord**: https://discord.gg/trappistai
- **Email**: devops@trappistai.com

---

**Last Updated**: June 6, 2026
