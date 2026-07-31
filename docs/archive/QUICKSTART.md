# 🚀 TrappistAI - Quick Start Guide

Get TrappistAI running in **5 minutes**!

---

## ⚡ Prerequisites

```bash
# Check versions
python --version  # 3.10+
node --version    # 18+
psql --version    # 14+
```

---

## 📦 Step 1: Clone & Setup

```bash
# Clone repo
cd C:\Users\Djaf\scai
cd TrappistAI

# Backend dependencies
cd backend
pip install -r requirements.txt

# Frontend dependencies
cd ../frontend
npm install
```

---

## 🗄️ Step 2: Database

```bash
# Create PostgreSQL database
createdb piranai

# Apply schema
psql -U postgres -d piranai -f backend/schema.sql

# Verify
psql -U postgres -d piranai -c "SELECT * FROM users LIMIT 1;"
```

---

## 🔑 Step 3: Environment Variables

### Backend `.env`
```bash
cd backend
cp .env.example .env
```

**Edit `backend/.env`**:
```bash
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/piranai
RECEIVER_WALLET=0123456789abcdef0123456789abcdef01234567
RECEIVER_ACCOUNT_HASH=1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
CSPR_CLOUD_KEY=your-api-key-from-cspr-cloud
WAVESPEED_API_KEY=your-api-key-from-wavespeed
GROQ_API_KEY=your-api-key-from-groq
ALLOWED_ORIGINS=http://localhost:5173
```

### Frontend `.env`
```bash
cd ../frontend
cp .env.example .env
```

**Edit `frontend/.env`**:
```bash
VITE_API_URL=http://localhost:8000
VITE_RECEIVER_WALLET=0123456789abcdef0123456789abcdef01234567
```

---

## 🚀 Step 4: Run Servers

### Terminal 1 - Backend
```bash
cd backend
python main.py
```

✅ Backend running at **http://localhost:8000**

### Terminal 2 - Frontend
```bash
cd frontend
npm run dev
```

✅ Frontend running at **http://localhost:5173**

---

## 🧪 Step 5: Test

1. **Open browser**: http://localhost:5173
2. **Click "Connect Wallet"** (install Casper Wallet extension if needed)
3. **Go to "Buy Credits"** → Select package → Send CSPR
4. **Go to "Generate"** → Try image generation

---

## 🐳 Alternative: Docker (One Command)

```bash
# Create .env files first (see Step 3)

# Start everything
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## 🔧 Troubleshooting

### Database Connection Error
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check connection
psql -U postgres -d piranai -c "SELECT 1;"
```

### CORS Error
```bash
# Make sure ALLOWED_ORIGINS includes frontend URL
# backend/.env
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Casper Wallet Not Found
- Install: https://www.casperwallet.io/
- Refresh page after installation

### API Key Errors
- WaveSpeed: https://wavespeed.ai/ → Sign up → Get API key
- CSPR.cloud: https://cspr.cloud/ → Sign up → Get streaming key
- Groq: https://console.groq.com/ → Get API key

---

## 📝 Next Steps

1. **Get CSPR**: Buy on exchanges (Gate.io, MEXC, KuCoin)
2. **Configure receiver wallet**: Use your own Casper wallet
3. **Test payments**: Send test CSPR to your receiver wallet
4. **Deploy to production**: See [DEPLOYMENT.md](DEPLOYMENT.md)

---

## 🆘 Need Help?

- Check [README.md](README.md) for full documentation
- Join Discord: https://discord.gg/trappistai
- Open issue: https://github.com/yourusername/trappistai/issues

---

**Happy Generating! 🎨🎵📦**
