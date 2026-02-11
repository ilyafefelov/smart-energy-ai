# Git Branch Cleanup & Consolidation Plan

**Status:** Master is clean (all Phase 3 work merged ✅)  
**Current State:** Multiple feature branches with overlapping work  
**Goal:** Clean up, consolidate, establish clear working point, create new branch for battery upgrades

---

## 📊 Current Branch Status

### Local Branches
```
master                                    ✅ ACTIVE (current, clean, all Phase 3 merged)
feature/ml-pipeline                       ❌ STALE (Phase 3, already merged to master)
feature/v2-software-defined-assets        ❌ DUPLICATE (Phase 2, different path than master)
feature/nuxt-ui-enhancements-and-fixes    ❌ DUPLICATE (Phase 2, different path than master)
feature/user-config-and-retraining        ❌ UNKNOWN (check commits)
feature/week1-data-pipeline               ❌ STALE (old branch)
feature/week2-rl-training                 ❌ STALE (old branch)
```

### Remote Branches
```
origin/HEAD -> origin/feature/week1-data-pipeline  (outdated)
origin/feature/week1-data-pipeline                  (stale)
origin/staging/user-config                         (stale)
origin/dependabot/*                                (auto-generated)
```

---

## 🎯 Branch History & Status

### ✅ Master (Safe Working Point NOW)
```
Latest commits:
642580d docs: Complete data flow explanation
769c9ba docs: Project status complete
95ccf09 docs: ML Dashboard Integration complete
42d54b0 feat: Add MLPipelineMonitor component
a144ed0 feat: Dashboard integration with ML pipeline

Status: PRODUCTION READY
├── Nuxt 4 dashboard: ✅ 4 pages, real-time data
├── Dagster ML pipeline: ✅ 31 assets, 72.5% accuracy
├── MLflow integration: ✅ 4 API endpoints
├── Dashboard integration: ✅ Real-time monitoring
└── Documentation: ✅ Complete

Safe to work from: YES
```

### ❌ feature/ml-pipeline (Already in master)
```
Last commit: d74e7af docs: PHASE 3 COMPLETE
Status: MERGED (all commits are in master)
Action: DELETE (no new work)
```

### ❌ feature/v2-software-defined-assets (Phase 2 work)
```
Last commit: b1bac63 fix: Navigation menu rendering
Status: MERGED (different merge path, but all in master now)
Action: DELETE (Phase 2 complete, Phase 3 supersedes)
```

### ❌ feature/nuxt-ui-enhancements-and-fixes (Phase 2 work)
```
Last commit: b1350e4 feat: Add navigation menu
Status: MERGED (same work as above)
Action: DELETE (duplicate work)
```

### ❓ feature/user-config-and-retraining
```
Need to check commits...
```

### ❌ feature/week1-data-pipeline (Very old)
```
Old Phase 1 data pipeline work
Status: OBSOLETE (superseded by Phase 3 Dagster)
Action: DELETE
```

### ❌ feature/week2-rl-training (Very old)
```
Old RL training experimentation
Status: OBSOLETE (replaced by XGBoost)
Action: DELETE
```

---

## 🧹 Cleanup Plan (7 Steps)

### Step 1: Check feature/user-config-and-retraining
<command will execute>

### Step 2: Delete old branches (local)
```bash
git branch -D feature/ml-pipeline
git branch -D feature/v2-software-defined-assets
git branch -D feature/nuxt-ui-enhancements-and-fixes
git branch -D feature/week1-data-pipeline
git branch -D feature/week2-rl-training
```

### Step 3: Delete old branches (remote)
```bash
git push origin --delete feature/v2-software-defined-assets
git push origin --delete feature/week1-data-pipeline
git push origin --delete staging/user-config
```

### Step 4: Clean up remote references
```bash
git remote prune origin
```

### Step 5: Create working document
Create: BRANCH_STRATEGY.md with clear guidelines

### Step 6: Establish master as safe point
Tag current master as stable release point:
```bash
git tag -a v1.0.0-stable -m "Phase 3 complete: Nuxt + Dagster + MLflow integration"
```

### Step 7: Create new branch for battery work
```bash
git checkout -b feature/battery-upgrades-v2
# Work on discharge calculations + battery optimizations
```

---

## 📋 Execution Steps (For You)

Let me do this step by step:

**STEP 1: Check user-config branch** (below)

**STEP 2-4: Clean up** (I'll execute next)

**STEP 5-7: Establish safe point + create new branch** (final)

---

## 🎯 New Branch Strategy

After cleanup, here's the branch discipline:

### Branch Naming Convention
```
feature/*          = Feature development (based on master)
bugfix/*           = Bug fixes (based on master)
experimental/*     = Risky experiments (based on master, can be deleted)
release/*          = Release candidates (based on master, tagged)
```

### Branch Rules
```
1. Always branch FROM master
2. Keep branches focused (one feature = one branch)
3. Delete merged branches immediately
4. Tag stable points (v1.0.0-stable, v1.1.0-stable)
5. PR/review before merging back to master
```

### For Battery Upgrades
```
Branch name: feature/battery-upgrades-v2
Description: Enhanced discharge calculations + battery state optimization
Based on: master (current stable)
Focus areas:
  ├── Discharge scheduling improvements
  ├── Battery health degradation modeling
  ├── Optimal charge/discharge rates
  └── Multi-hour lookahead planning

When complete:
  └── Merge back to master with tag v1.1.0-battery-enhanced
```

---

## 📊 End State (After Cleanup)

```
Local branches:
✅ master                          (stable, all Phase 3)
✅ feature/battery-upgrades-v2     (your current work)

Remote branches:
✅ origin/master                   (synced)
✅ origin/feature/battery-upgrades-v2 (pushed)

Tags:
✅ v1.0.0-stable                   (current master state)
✅ v1.1.0-battery-enhanced         (after battery work merged)

Deleted (no longer needed):
❌ feature/ml-pipeline
❌ feature/v2-software-defined-assets
❌ feature/nuxt-ui-enhancements-and-fixes
❌ feature/week1-data-pipeline
❌ feature/week2-rl-training
❌ feature/user-config-and-retraining (if obsolete)
```

---

## ✨ Result

**Before:** 8 branches, overlapping work, confusing history  
**After:** 2 branches (master + feature/battery-upgrades-v2), clear strategy, clean history

Safe working point established + ready for new work!
