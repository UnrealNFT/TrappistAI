# Comment Restart le Bot sur Render (Fix Conflict Error)

## Symptômes
```
telegram.error.Conflict: terminated by other getUpdates request
```
= 2 instances du bot tournent en même temps

## Solution (30 secondes)

1. Va sur https://dashboard.render.com
2. Clique sur **PiraBot** (Background Worker)
3. En haut à droite, clique **Manual Deploy** (bouton bleu)
4. Coche **"Clear build cache"** ✅
5. Clique **Deploy** 
6. Attends 1-2 minutes
7. Vérifie logs : `PiranAI Bot started` sans erreur

## Pourquoi ça arrive ?

Quand tu push du code :
- Render build le nouveau code (30s)
- MAIS l'ancien process tourne encore
- Les 2 bots essaient de fetch Telegram updates
- Telegram dit "non, 1 seul bot à la fois"

Le restart avec cache clear **force kill** l'ancien process.

## Alternative (si ça marche pas)

1. **Suspend** le service
2. Attends 10 secondes
3. **Resume** le service
