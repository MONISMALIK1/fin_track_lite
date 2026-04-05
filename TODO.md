# Railway Deployment Steps

1. Kill local server (Ctrl+C)
2. Railway dashboard Variables → SECRET_KEY = python -c \"import secrets; print(secrets.token_urlsafe(32))\"
3. Add Postgres plugin (DATABASE_URL auto-added)
4. git add . && git commit -m \"Railway production fixes\" && git push
5. railway up
6. Test curl $RAILWAY_PUBLIC_URL/health
