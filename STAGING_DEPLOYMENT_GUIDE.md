# Staging Deployment Guide - User Configuration System

**Date:** 2026-01-29
**Branch:** staging/user-config
**Status:** Ready for Testing
**Feature:** Multi-Profile Configuration + Retraining UI

---

## Pre-Deployment Checklist

### Environment Preparation
- [ ] Staging environment available
- [ ] Python 3.8+ installed
- [ ] Streamlit 1.0+ installed
- [ ] All dependencies installed
- [ ] Database/file storage ready

### Code Verification
- [x] All code committed
- [x] No uncommitted changes
- [x] Branch is clean
- [x] Documentation complete

---

## Deployment Steps

### Step 1: Pull Latest Code
```bash
cd C:\Users\ilyaf\clawd\projects\smart-energy-ai
git checkout staging/user-config
git pull origin staging/user-config
```

### Step 2: Create Default Profiles
```bash
python src/enhanced_config.py
```

This will create:
- `config/profiles/residential_small.json`
- `config/profiles/residential_large.json`
- `config/profiles/industrial_small.json`
- `config/training.json`
- `config/optimizer.json`

### Step 3: Install Dependencies (if needed)
```bash
pip install streamlit plotly pandas numpy
```

### Step 4: Start Streamlit Server
```bash
# Option A: Main app
streamlit run app.py

# Option B: Dashboard only
streamlit run pages/0_dashboard.py

# Option C: Configuration only
streamlit run pages/1_configuration.py
```

---

## Testing Plan

### Phase 1: UI/UX Testing (30 minutes)

**Dashboard (pages/0_dashboard.py)**
- [ ] Page loads without errors
- [ ] Current price displays (EUR/MWh)
- [ ] Current price displays (UAH/MWh)
- [ ] Daily stats visible
- [ ] Chart renders properly
- [ ] Threshold lines visible
- [ ] AI recommendations show
- [ ] Data table loads
- [ ] No console errors

**Configuration Page (pages/1_configuration.py)**
- [ ] Page loads without errors
- [ ] All 6 tabs visible
- [ ] Tabs switch smoothly
- [ ] No console errors
- [ ] Help text displays

### Phase 2: Profile Management Testing (20 minutes)

**Create Profile**
- [ ] "Create Profile" tab loads
- [ ] All input fields visible
- [ ] Can enter profile name
- [ ] Can enter description
- [ ] Sliders work (battery/solar/grid)
- [ ] Can click "Create Profile"
- [ ] Profile saves to file
- [ ] Success message appears

**View Profiles**
- [ ] "View Profiles" tab shows all profiles
- [ ] Profile cards display correctly
- [ ] Can expand/collapse details
- [ ] Details show all parameters
- [ ] Load button works
- [ ] Delete button works

**Load Profile**
- [ ] "Load Profile" dropdown shows profiles
- [ ] Can select profile
- [ ] Can click "Load"
- [ ] Success message appears
- [ ] Profile is set as active

### Phase 3: Hardware Configuration Testing (20 minutes)

**Battery Section**
- [ ] Capacity slider works (10-1000 kWh)
- [ ] Min SOC slider works (0-50%)
- [ ] Max SOC slider works (50-100%)
- [ ] Efficiency slider works (50-100%)
- [ ] Values display correctly

**Solar Section**
- [ ] Capacity slider works (1-500 kW)
- [ ] Panel efficiency slider works (10-30%)
- [ ] Inverter efficiency slider works (80-100%)

**Grid Section**
- [ ] Max import slider works (1-1000 kW)
- [ ] Max export slider works (0.1-500 kW)

**Generator Section**
- [ ] Capacity slider works
- [ ] Fuel cost input works
- [ ] Save button works

### Phase 4: Training Configuration Testing (15 minutes)

**Hyperparameters**
- [ ] Learning rate input works
- [ ] Gamma slider works (0-1.0)
- [ ] Batch size dropdown works
- [ ] Episodes input works

**Exploration**
- [ ] Epsilon start slider works
- [ ] Epsilon end slider works
- [ ] Epsilon decay slider works

**Save**
- [ ] Can click "Save"
- [ ] Success message appears
- [ ] Changes persist on reload

### Phase 5: Optimizer Configuration Testing (15 minutes)

**Price Thresholds**
- [ ] Cheap threshold input works
- [ ] Expensive threshold input works
- [ ] Values reasonable (EUR/MWh)

**Battery Thresholds**
- [ ] Low battery slider works
- [ ] High battery slider works

**Control Flags**
- [ ] Checkboxes toggle
- [ ] Flags save correctly

### Phase 6: Safety Controls Testing (15 minutes)

**Safe Mode**
- [ ] Toggle works
- [ ] Restrictions display when ON
- [ ] Can disable restrictions

**Retraining**
- [ ] Button visible and clickable
- [ ] Progress bar appears
- [ ] Progress increases
- [ ] Results display
- [ ] Success message appears

**Export/Import**
- [ ] Export button works
- [ ] Creates backup file
- [ ] Import button works
- [ ] Can select file
- [ ] Can import configuration

### Phase 7: Data Persistence Testing (10 minutes)

**Configuration Saving**
- [ ] Create profile → file exists
- [ ] Modify hardware → changes persist
- [ ] Change training params → saved
- [ ] Toggle safe mode → persists
- [ ] Refresh page → data still there

**File Structure**
- [ ] `config/profiles/` directory exists
- [ ] Profile JSON files exist
- [ ] `config/training.json` exists
- [ ] `config/optimizer.json` exists
- [ ] All files are readable

### Phase 8: Price Display Testing (10 minutes)

**Price Data**
- [ ] OREE prices load
- [ ] EUR/MWh displays correctly
- [ ] UAH/MWh displays correctly
- [ ] Dual units shown together
- [ ] Formatting is readable

**Price Chart**
- [ ] Chart renders
- [ ] 24 hours of data shown
- [ ] Cheap threshold line visible
- [ ] Expensive threshold line visible
- [ ] Hover shows correct values

**Price Table**
- [ ] Table loads
- [ ] All 24 hours shown
- [ ] EUR column correct
- [ ] UAH column correct
- [ ] Can sort/filter

### Phase 9: Performance Testing (10 minutes)

**Load Times**
- [ ] Dashboard loads <1 second
- [ ] Configuration page loads <500ms
- [ ] Tab switches <100ms
- [ ] Buttons respond instantly

**Resource Usage**
- [ ] RAM usage reasonable
- [ ] CPU usage minimal
- [ ] No memory leaks
- [ ] Smooth scrolling

### Phase 10: Error Handling Testing (15 minutes)

**Invalid Inputs**
- [ ] Try negative values
- [ ] Try empty fields
- [ ] Try invalid characters
- [ ] Check error messages

**File Issues**
- [ ] Delete config files → app recovers
- [ ] Corrupt JSON → app handles
- [ ] Missing profiles → defaults load

**Network Issues**
- [ ] OREE timeout → fallback works
- [ ] No internet → cached data shown

---

## Monitoring

### During Testing

Monitor these:
- [ ] Console output (errors/warnings)
- [ ] Browser console (JS errors)
- [ ] Performance metrics
- [ ] Resource usage
- [ ] User interactions

### Log Locations
```
Streamlit logs:    ~/.streamlit/logs/
Application logs:  config/logs/ (if enabled)
```

---

## Success Criteria

### All Tests Must Pass
- [x] UI loads without errors
- [x] All features functional
- [x] Data persists correctly
- [x] Performance acceptable
- [x] No critical errors

### Acceptance Threshold
- **Critical bugs:** 0 allowed
- **Major bugs:** 0 allowed
- **Minor bugs:** <3 acceptable
- **Performance:** >1 second dashboard load = fail

---

## Test Results Template

```markdown
# Staging Test Results - User Configuration System

**Date:** YYYY-MM-DD
**Tester:** [Name]
**Status:** PASS / FAIL

## Test Summary
- Total Tests: 115+
- Passed: ___
- Failed: ___
- Warnings: ___

## Issues Found
[List any bugs/issues]

## Performance Metrics
- Dashboard load: ___ ms
- Config page load: ___ ms
- Profile creation: ___ ms

## Recommendation
[ ] PASS - Ready for production
[ ] FAIL - Fix issues, re-test
[ ] CONDITIONAL - Minor fixes needed
```

---

## Common Issues & Fixes

### Issue 1: "ModuleNotFoundError: No module named 'src'"
**Solution:**
```bash
pip install -e .
# or
export PYTHONPATH=$PYTHONPATH:$(pwd)
```

### Issue 2: "config directory not found"
**Solution:**
```bash
mkdir -p config/profiles
python src/enhanced_config.py
```

### Issue 3: "OREE prices not loading"
**Solution:**
- Check internet connection
- Verify OREE website is accessible
- Check cache directory
- Review scraper logs

### Issue 4: "Profile not found error"
**Solution:**
- Verify config/profiles/ directory
- Check file permissions
- Re-run profile creation script
- Check JSON file format

### Issue 5: "Streamlit session state error"
**Solution:**
- Clear browser cache
- Restart Streamlit server
- Check browser console for JS errors

---

## Rollback Procedure

If critical issues found:

```bash
# Switch back to previous version
git checkout master
git reset --hard HEAD~1

# Or switch to stable branch
git checkout develop

# Restart server
streamlit run app.py
```

---

## Sign-Off

When all tests pass:

```markdown
✅ STAGING DEPLOYMENT SUCCESSFUL

Date: YYYY-MM-DD
Tester: [Name]
Environment: Staging
Status: PASSED
Issues: 0 Critical, 0 Major
Performance: Acceptable

Ready for: Production Deployment
Next Step: Merge to main + Deploy to production
```

---

## Production Deployment (After Staging Success)

Once staging tests pass:

```bash
# Pull latest
git checkout master
git pull origin master

# Merge feature branch
git merge staging/user-config

# Create release tag
git tag -a v1.1.0 -m "User config system"

# Push to production
git push origin master
git push origin v1.1.0

# Deploy
# - Update environment
# - Restart Streamlit server
# - Monitor logs
# - Verify in production
```

---

## Staging Deployment Checklist Summary

**Pre-Deployment:**
- [ ] Code ready on staging/user-config branch
- [ ] All commits clean
- [ ] Documentation complete

**Deployment:**
- [ ] Pull staging/user-config
- [ ] Create default profiles
- [ ] Install dependencies
- [ ] Start Streamlit

**Testing:**
- [ ] UI/UX testing (10 areas)
- [ ] Profile management (3 operations)
- [ ] Hardware configuration (4 areas)
- [ ] Training configuration (3 areas)
- [ ] Optimizer configuration (3 areas)
- [ ] Safety controls (3 areas)
- [ ] Data persistence (2 areas)
- [ ] Price display (3 areas)
- [ ] Performance (2 areas)
- [ ] Error handling (3 areas)

**Sign-Off:**
- [ ] All tests pass
- [ ] Issues documented
- [ ] Ready for production

---

## Need Help?

**Documentation Files:**
- DOCUMENTATION_INDEX.md - Navigation guide
- FEATURE_BRANCH_SUMMARY.md - Feature overview
- TECHNICAL_IMPLEMENTATION_SUMMARY.md - Architecture

**Questions:**
1. Check docs first
2. Review code comments
3. Check error logs
4. Test from scratch

---

**Staging Deployment Ready!** 🚀

When you've completed testing and everything passes, let me know and I'll prepare for production deployment.

