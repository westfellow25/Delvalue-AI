# Deployment Guide

## Streamlit Cloud Deployment

### Prerequisites

- GitHub account
- Repository with DelValue AI code
- (Optional) Anthropic API key

### Steps

1. **Push code to GitHub**
```bash
   git push origin main
```

2. **Go to Streamlit Cloud**
   - Visit https://share.streamlit.io/
   - Sign in with GitHub

3. **Create new app**
   - Click "New app"
   - Select repository: `YOUR_USERNAME/delvalue-ai`
   - Branch: `main`
   - Main file: `app.py`

4. **Configure secrets (optional)**
   
   Add in Streamlit Cloud secrets:
```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   DEBUG = "False"
   LOG_LEVEL = "INFO"
```

5. **Deploy**
   - Click "Deploy!"
   - Wait 2-5 minutes
   - App will be live at: `https://YOUR-APP-NAME.streamlit.app`

### Post-Deployment

**Test the deployment:**
- [ ] Home page loads
- [ ] Can navigate between pages
- [ ] Can load sample data
- [ ] Can add processes manually
- [ ] Analysis works
- [ ] Charts render correctly

**Share the app:**
- Public URL: `https://YOUR-APP-NAME.streamlit.app`
- Share with beta users
- Collect feedback

### Troubleshooting

**App won't start:**
- Check logs in Streamlit Cloud dashboard
- Verify requirements.txt has all dependencies
- Check Python version (3.12+)

**Database errors:**
- SQLite works on Streamlit Cloud
- Database resets on each deploy (expected)
- For persistence, consider PostgreSQL

**Import errors:**
- Verify all files committed to GitHub
- Check __init__.py files exist
- Verify relative imports

### Monitoring

**Streamlit Cloud provides:**
- App logs
- Resource usage
- Uptime monitoring

**Access logs:**
- Go to Streamlit Cloud dashboard
- Select your app
- Click "Logs"

### Updates

**To update the app:**
```bash
# Make changes locally
git add .
git commit -m "Your changes"
git push origin main

# Streamlit Cloud auto-redeploys
```

### Custom Domain (Optional)

1. Go to app settings in Streamlit Cloud
2. Add custom domain
3. Update DNS records
4. Enable HTTPS (automatic)

## Local Deployment

### Docker (Alternative)

Create `Dockerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py"]
```

Build and run:
```bash
docker build -t delvalue-ai .
docker run -p 8501:8501 delvalue-ai
```

## Production Considerations

### For Production Use:

1. **Authentication**
   - Add user login
   - Implement RBAC

2. **Database**
   - Migrate to PostgreSQL
   - Add connection pooling
   - Implement backups

3. **Security**
   - Enable HTTPS
   - Add rate limiting
   - Implement CSRF protection
   - Sanitize inputs

4. **Monitoring**
   - Add error tracking (Sentry)
   - Implement analytics
   - Set up alerts

5. **Performance**
   - Add caching
   - Optimize queries
   - Use CDN for assets

### Scaling

**Streamlit Cloud limitations:**
- Free tier: 1 app
- Community tier: 3 apps
- Team/Enterprise: Unlimited

**For heavy usage:**
- Consider dedicated hosting
- Use load balancer
- Implement async processing

## Cost Estimate

**Free Tier (Streamlit Cloud):**
- 1 app
- Public only
- $0/month

**Team Plan:**
- Private apps
- More resources
- ~$250/month

**API Costs (Anthropic):**
- Claude API usage-based
- Estimate: $10-50/month (depending on volume)

## Backup & Recovery

**Data backup:**
```bash
# Export database
sqlite3 data/delvalue.db .dump > backup.sql

# Restore
sqlite3 data/delvalue.db < backup.sql
```

**Code backup:**
- GitHub serves as backup
- Tag releases: `git tag v1.0.0`

## Support

**Issues:**
- GitHub Issues: Create issue
- Streamlit Community: forum.streamlit.io

**Updates:**
- Check for Streamlit updates
- Update dependencies regularly
- Monitor security advisories
