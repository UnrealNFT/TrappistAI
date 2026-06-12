# Configuration VS Code pour TrappistAI

## Erreurs Pylance "Import could not be resolved"

Les 134 erreurs que tu vois dans VS Code sont **normales en développement local** - elles n'affectent pas le déploiement sur Render.

### Cause
VS Code Pylance ne trouve pas les packages Python (fastapi, pydantic, etc.) parce que l'environnement virtuel n'est pas activé.

### Solution (3 options)

#### Option 1 : Créer un venv local (recommandé)
```powershell
cd C:\Users\Djaf\scai\TrappistAI\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Puis dans VS Code :
1. `Ctrl+Shift+P` → "Python: Select Interpreter"
2. Choisir `.venv` dans `backend/.venv`

#### Option 2 : Ignorer les erreurs
Ajoute dans `.vscode/settings.json` :
```json
{
  "python.analysis.diagnosticSeverityOverrides": {
    "reportMissingImports": "none"
  }
}
```

#### Option 3 : Utiliser l'environnement existant
Si tu as déjà un venv dans `C:\Users\Djaf\scai\Agent\.venv` :
1. `Ctrl+Shift+P` → "Python: Select Interpreter"
2. Choisir `C:\Users\Djaf\scai\Agent\.venv\Scripts\python.exe`

## API Endpoints ajoutés

### Code de vérification visible
Le endpoint `/api/profile/link-telegram` retourne maintenant :
```json
{
  "success": true,
  "code": "123456",
  "telegram_username": "djaf77",
  "message": "Go to @PiraAi_bot and type: /verify 123456"
}
```

Le frontend doit **afficher `response.code`** directement à l'utilisateur.

### Déconnexion Telegram
```http
POST /api/profile/unlink-telegram
Content-Type: application/json

{
  "walletAddress": "020200927927ec53d1969e76dd69739830cdac7fbb21e9d7b3984dc6c3b3267b92ca"
}
```

Réponse :
```json
{
  "success": true,
  "message": "Telegram account disconnected successfully"
}
```

### Vérifier le code en attente
```http
GET /api/profile/{walletAddress}
```

Retourne maintenant `pending_code` si un code existe et n'est pas expiré :
```json
{
  "wallet_address": "...",
  "telegram_username": "djaf77",
  "telegram_verified": false,
  "pending_code": "123456"  // ← nouveau
}
```

Le frontend peut utiliser ce code pour :
1. L'afficher si l'utilisateur rafraîchit la page
2. Vérifier si le code est encore valide (non null = code actif)

## Déploiement

Sur Render, les packages sont installés automatiquement depuis `requirements.txt`, donc **aucune erreur en production** 🎉
