# Configuration Netlify pour TrappistAI

## URGENT: Variable d'environnement manquante !

Le site ne peut pas communiquer avec le backend car VITE_API_URL n'est pas configuré.

## Étapes (30 secondes)

1. Va sur https://app.netlify.com
2. Clique sur **TrappistAI** (ton site)
3. Va dans **Site settings**
4. Clique sur **Environment variables** (menu gauche)
5. Clique **Add a variable**
6. Configure:
   ```
   Key: VITE_API_URL
   Value: https://trappistai-backend.onrender.com
   ```
7. Clique **Save**
8. Va dans **Deploys**
9. Clique **Trigger deploy** → **Clear cache and deploy**
10. Attends 1-2 minutes

## Pourquoi c'est cassé ?

Sans VITE_API_URL, le frontend utilise:
```javascript
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
//                                               ^^^^^^^^^^^^^^^^^^^^^^^^
//                                               ❌ Ne marche pas sur Netlify !
```

Résultat: 
- `/my-rwa` essaie de fetch localhost:8000 → échoue
- `/marketplace` essaie de fetch localhost:8000 → échoue
- Aucune donnée ne s'affiche

## Après le fix

✅ Frontend → https://trappistai-backend.onrender.com
✅ /my-rwa affiche tes tokens
✅ /marketplace affiche les listings
✅ Tout fonctionne !
