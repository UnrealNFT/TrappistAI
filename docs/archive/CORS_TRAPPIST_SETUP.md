# CORS Configuration for trappist.land

## Backend (Render)

The backend uses environment variable `ALLOWED_ORIGINS` to configure CORS.

### Steps to add trappist.land domain:

1. Go to Render dashboard: https://dashboard.render.com/
2. Select your backend service: `trappistai-backend`
3. Go to "Environment" tab
4. Find `ALLOWED_ORIGINS` variable
5. Add the new domains (comma-separated):

```
http://localhost:3000,http://localhost:5173,https://trappistai.netlify.app,https://trappist.land,https://www.trappist.land
```

6. Click "Save Changes"
7. Render will automatically redeploy

## Frontend (Netlify)

1. Domain already configured in Netlify DNS
2. Nameservers set at Namecheap:
   - dns1.p07.nsone.net
   - dns2.p07.nsone.net
   - dns3.p07.nsone.net
   - dns4.p07.nsone.net

3. DNS propagation may take 24-48h

## Verification

After backend redeploys with new CORS origins:

```bash
# Test CORS from trappist.land
curl -H "Origin: https://trappist.land" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS \
     https://trappistai-backend.onrender.com/api/balance/your-wallet-address
```

Should return:
```
Access-Control-Allow-Origin: https://trappist.land
Access-Control-Allow-Credentials: true
```

## Current Status

- ✅ Code ready (uses ALLOWED_ORIGINS env var)
- ⏳ Needs: Update ALLOWED_ORIGINS on Render
- ⏳ Needs: Wait for DNS propagation
