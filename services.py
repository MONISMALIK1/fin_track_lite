# Railway Deployment TODO

- [ ] Merge PR #6 (if pending)
- [ ] `pip install -r requirements.txt` ✅
- [ ] Kill local server Ctrl+C
- [ ] Railway dashboard → Variables → Add SECRET_KEY=`python -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] Add Postgres plugin (generates DATABASE_URL)
- [ ] `railway up`
- [ ] Test: curl $RAILWAY_PUBLIC_URL/health
- [ ] Open frontend/index.html → connect to Railway URL

