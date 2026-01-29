# Smart Energy AI - Deployment Guide

## Pre-Deployment Checklist

### Code Quality
- [ ] All tests passing (5/5 phases)
- [ ] No Python syntax errors
- [ ] No Streamlit warnings
- [ ] Git history clean

### Data Integrity
- [ ] OREE prices verified (live data)
- [ ] Solar data verified (realistic values)
- [ ] Version tracking verified
- [ ] Model checkpoints verified

### Performance
- [ ] Dashboard loads <1s
- [ ] Price fetch <0.5s
- [ ] Solar fetch <0.2s
- [ ] Training time acceptable

## Deployment Steps

### 1. Production Environment Setup
```bash
cd /var/www/smart-energy-ai
git clone <repo>
cd smart-energy-ai
git checkout main
poetry install --no-dev
```

### 2. Environment Variables
```bash
# .env file
OPENWEATHERMAP_API_KEY=your_key
NOTION_API_KEY=your_key
```

### 3. Start Services
```bash
# Streamlit app
streamlit run app.py --server.port 8501

# Background worker (optional)
python background_tasks.py
```

### 4. Verification
```bash
python final_verification.py
# Expected: ✅ ALL SYSTEMS OPERATIONAL
```

### 5. Monitoring
- Check logs every hour
- Monitor price data freshness
- Verify training completion
- Track error rates

## Rollback Procedure

If issues occur:
```bash
git checkout previous-release
streamlit run app.py
```

## Support Contacts
- Code issues: GitHub Issues
- Data issues: OREE support team
- Deployment: Infrastructure team
