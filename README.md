# TrappistAI

**Multi-modal AI Generation Platform** powered by **Casper Blockchain**

Generate images, music, 3D models, and chat with AI. Pay with CSPR tokens.

---

## 🚀 Features

- **🎨 Image Generation**: FLUX.1-schnell (1024x1024) — 1 token
- **🎵 Music Creation**: HeartMuLa & MiniMax HD — 10-15 tokens
- **📦 3D Models**: Hunyuan & Tripo3D — 5-20 tokens  
- **💬 AI Chat**: Groq LLM — Free (0 tokens)
- **💰 CSPR Payments**: Automatic token crediting via blockchain

---

## 🏗️ Architecture

```
TrappistAI/
├── backend/          # FastAPI + Python
│   ├── main.py       # API endpoints
│   ├── cspr_listener.py  # WebSocket payment listener
│   ├── db.py         # PostgreSQL operations
│   ├── wavespeed.py  # WaveSpeed.ai client
│   └── schema.sql    # Database schema
├── frontend/         # React + Vite
│   └── src/
│       ├── App.jsx
│       ├── pages/    # Home, Generate, BuyCredits
│       └── services/ # API client
└── docker-compose.yml
```

**Stack**:
- Backend: FastAPI, SQLAlchemy, WebSockets
- Frontend: React 18, Vite, TailwindCSS
- Database: PostgreSQL 14
- Payments: CSPR.cloud WebSocket + RPC verification

---

## 📦 Installation

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Casper Wallet extension

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/trappistai.git
cd trappistai
```

### 2. Backend Setup
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your credentials
# - DATABASE_URL
# - CSPR_CLOUD_KEY
# - WAVESPEED_API_KEY
# - RECEIVER_WALLET
# - RECEIVER_ACCOUNT_HASH
```

### 3. Database Setup
```bash
# Create database
createdb piranai

# Apply schema
psql -U piranai -d piranai -f schema.sql
```

### 4. Frontend Setup
```bash
cd ../frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Edit .env with backend URL
```

### 5. Run Development Servers

**Backend**:
```bash
cd backend
python main.py
# -> http://localhost:8000
```

**Frontend**:
```bash
cd frontend
npm run dev
# -> http://localhost:5173
```

---

## 🐳 Docker Deployment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services:
- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- PostgreSQL: localhost:5432

---

## 💰 Payment System

### CSPR Packages
- **Starter**: 100 tokens → 10 CSPR
- **Pro**: 500 tokens → 45 CSPR
- **Creator**: 1000 tokens → 80 CSPR
- **Enterprise**: 5000 tokens → 350 CSPR

### How It Works
1. User sends CSPR to `RECEIVER_WALLET`
2. WebSocket listener detects transfer on mainnet
3. RPC verification fetches sender public key
4. Tokens credited automatically to user's account
5. Frontend refreshes balance

**Security**: 
- Transaction hash uniqueness enforced (no double-spend)
- Mainnet-only (testnet blocked)
- All secrets in `.env` (never hardcoded)

---

## 🔧 Configuration

### Required Environment Variables

**Backend** (`.env`):
```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/piranai
RECEIVER_WALLET=your-public-key
RECEIVER_ACCOUNT_HASH=your-account-hash-without-prefix
CSPR_CLOUD_KEY=your-cspr-cloud-api-key
WAVESPEED_API_KEY=your-wavespeed-api-key
GROQ_API_KEY=your-groq-api-key
ALLOWED_ORIGINS=http://localhost:5173
```

**Frontend** (`.env`):
```bash
VITE_API_URL=http://localhost:8000
VITE_RECEIVER_WALLET=your-public-key
```

---

## 📡 API Endpoints

### User
- `GET /api/user/{wallet}/balance` — Get token balance
- `GET /api/user/{wallet}/payments` — Get payment history

### Payments
- `POST /api/payments/verify` — Manual payment verification

### Generation
- `POST /api/generate/image` — Generate image (1 token)
- `POST /api/generate/music` — Generate music (10-15 tokens)
- `POST /api/generate/3d` — Generate 3D model (5-20 tokens)
- `POST /api/chat` — AI chat (free)

---

## 🧪 Testing

### Test Database Connection
```bash
cd backend
python db.py
```

### Test WaveSpeed API
```bash
cd backend
python wavespeed.py
```

### Test CSPR Listener (standalone)
```bash
cd backend
python cspr_listener.py
```

---

## 🔐 Security

- ✅ All secrets in `.env` (excluded from git)
- ✅ PostgreSQL with prepared statements (SQL injection protection)
- ✅ Rate limiting on all endpoints
- ✅ CORS restricted to allowed origins
- ✅ Transaction hash uniqueness enforced
- ✅ Mainnet-only payment validation

**DO NOT**:
- Hardcode API keys
- Commit `.env` files
- Expose private keys
- Run testnet in production

---

## 📈 Pricing Model

### Token Costs
- Image (FLUX): 1 token ($0.03)
- Music (HeartMuLa): 10 tokens ($0.30)
- Music (MiniMax HD): 15 tokens ($0.45)
- 3D (no texture): 5 tokens ($0.15)
- 3D (with texture): 20 tokens ($0.60)
- Chat: Free

### WaveSpeed.ai API Costs
- FLUX.1-schnell: $0.003
- HeartMuLa: $0.10
- MiniMax Music 2.5 HD: $0.15
- Hunyuan-3D V3.1: $0.0225
- Tripo3D v2.5: $0.30

**Margins**: 200% - 900% depending on service

---

## 🛠️ Tech Stack

### Backend
- **FastAPI**: Web framework
- **SQLAlchemy**: ORM
- **websockets**: CSPR.cloud streaming
- **httpx**: Async HTTP client
- **SlowAPI**: Rate limiting

### Frontend
- **React 18**: UI library
- **Vite**: Build tool
- **TailwindCSS**: Styling
- **Axios**: HTTP client
- **Lucide React**: Icons
- **Casper JS SDK**: Wallet integration

### Infrastructure
- **PostgreSQL**: Database
- **Docker**: Containerization
- **CSPR.cloud**: Payment streaming
- **WaveSpeed.ai**: AI generation

---

## 📝 TODO

- [ ] Add 3D generation (Hunyuan/Tripo integration)
- [ ] Implement Groq chat streaming
- [ ] Add generation history page
- [ ] Add admin dashboard
- [ ] Deploy to production (VPS/Cloud)
- [ ] Add analytics (user activity, revenue tracking)
- [ ] Implement referral system
- [ ] Add social sharing (Twitter, Discord)

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

---

## 🙏 Credits

- **WaveSpeed.ai**: AI generation APIs
- **CSPR.cloud**: Casper blockchain streaming
- **Groq**: LLM inference
- **Casper Labs**: Blockchain infrastructure

---

## 📧 Support

- **Email**: support@trappistai.com
- **Discord**: [Join our server](https://discord.gg/trappistai)
- **Twitter**: [@TrappistAI](https://twitter.com/TrappistAI)

---

**Built with 💜 by the TrappistAI Team**
