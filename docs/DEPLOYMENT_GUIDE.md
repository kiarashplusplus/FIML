# Deployment Guide: Update and Migration Procedures

## Quick Reference

**Use this guide when:**
- Updating lesson content
- Deploying code changes
- Performing schema migrations
- Rolling back deployments

---

## Pre-Deployment Checklist

### For Lesson Updates

- [ ] Update lesson YAML file
- [ ] Increment version number appropriately:
  - **Patch** (1.0.0 → 1.0.1): Typos, small fixes
  - **Minor** (1.0.0 → 1.1.0): New content, improved examples
  - **Major** (1.0.0 → 2.0.0): Complete rewrite, breaking changes
- [ ] Add changelog entry with date and changes
- [ ] Archive old version if major change
- [ ] Test lesson rendering locally
- [ ] Validate YAML syntax
- [ ] Test quiz questions and answers

### For Code Updates

- [ ] All tests passing locally
- [ ] Code review completed
- [ ] Security scan passed (CodeQL)
- [ ] Documentation updated
- [ ] Migration scripts ready (if schema change)
- [ ] Rollback plan documented
- [ ] Monitoring alerts configured

---

## Deployment Procedures

### Procedure 1: Deploy Lesson Content Update (Patch/Minor)

**Time Required:** 5-10 minutes  
**Risk Level:** Low  
**Rollback:** Automatic via Git

```bash
# 1. Update lesson file
vim fiml/bot/content/lessons/01_understanding_stock_prices.yaml

# Update version and changelog
# version: "1.0.1"  # or "1.1.0" for minor
# changelog:
#   - version: "1.0.1"
#     date: "2024-11-24"
#     changes:
#       - "Fixed typo in explanation"

# 2. Validate lesson
python scripts/validate_lessons.py --lesson 01_understanding_stock_prices.yaml

# 3. Test rendering
python examples/lesson_content_demo.py

# 4. Commit and push
git add fiml/bot/content/lessons/01_understanding_stock_prices.yaml
git commit -m "Update lesson stock_basics_001 to v1.0.1: Fix typo"
git push origin main

# 5. Deploy (blue-green)
./scripts/deploy.sh --environment production --strategy blue-green

# 6. Monitor for 10 minutes
./scripts/monitor_deployment.sh --duration 10m

# Done! Lesson auto-updates for all users.
```

**User Impact:**
- In-progress lessons: Continue seamlessly
- Completed lessons: Can review updated version
- Patch updates: No notification
- Minor updates: Optional "Updated" badge

---

### Procedure 2: Deploy Major Lesson Update

**Time Required:** 30 minutes  
**Risk Level:** Medium  
**Rollback:** Via version rollback

```bash
# 1. Archive current version
mkdir -p fiml/bot/content/lessons/archive/1.0/
cp fiml/bot/content/lessons/01_understanding_stock_prices.yaml \
   fiml/bot/content/lessons/archive/1.0/

# 2. Update lesson with major changes
vim fiml/bot/content/lessons/01_understanding_stock_prices.yaml

# Update to major version
# version: "2.0"
# changelog:
#   - version: "2.0"
#     date: "2024-11-24"
#     changes:
#       - "Complete rewrite with new examples"
#       - "Updated quiz questions"
#       - "New FIML data integration"

# 3. Test thoroughly
python scripts/validate_lessons.py --lesson 01_understanding_stock_prices.yaml
python scripts/test_lesson_migration.py --lesson stock_basics_001 \
  --from-version 1.0 --to-version 2.0

# 4. Deploy with feature flag
./scripts/deploy.sh --environment production \
  --feature-flag lesson_v2_stock_basics_001=10%

# 5. Monitor beta rollout (10% of users)
./scripts/monitor_deployment.sh --duration 1h --alert-threshold 2%

# 6. If healthy, increase rollout
./scripts/feature_flag.sh lesson_v2_stock_basics_001 50%  # 50% users
# Monitor 2 hours
./scripts/monitor_deployment.sh --duration 2h

# 7. Full rollout
./scripts/feature_flag.sh lesson_v2_stock_basics_001 100%

# 8. Remove feature flag after 24h
./scripts/feature_flag.sh lesson_v2_stock_basics_001 --remove
```

**User Impact:**
- In-progress (old version): Prompted to continue or restart
- Completed: Can review new version
- New users: Get v2.0 automatically

---

### Procedure 3: Deploy Code Update (No Schema Change)

**Time Required:** 20 minutes  
**Risk Level:** Low-Medium  
**Rollback:** Automatic

```bash
# 1. Merge PR to main
# (After code review, tests, security scan)

# 2. Tag release
git tag v1.5.0
git push origin v1.5.0

# 3. Build Docker image
docker build -t fiml-bot:v1.5.0 .
docker push fiml-bot:v1.5.0

# 4. Deploy to green environment
./scripts/deploy.sh --environment green --version v1.5.0

# 5. Run smoke tests on green
./scripts/smoke_test.sh green

# 6. Canary deployment (10% traffic)
./scripts/traffic_switch.sh green 10%

# 7. Monitor for 30 minutes
./scripts/monitor_deployment.sh --duration 30m --rollback-on-error 5%

# 8. If healthy, gradual rollout
./scripts/traffic_switch.sh green 50%   # Monitor 1h
./scripts/traffic_switch.sh green 100%  # Full cutover

# 9. Mark blue as old
./scripts/mark_environment.sh blue old
```

**Automatic Rollback Triggers:**
- Error rate > 5%
- Response time > 2s p95
- User complaints > 10 in 5min
- Health check failures

---

### Procedure 4: Deploy Schema Migration

**Time Required:** 1-2 hours  
**Risk Level:** High  
**Rollback:** Manual (with snapshot restore)

```bash
# 1. Create database snapshot
./scripts/db_snapshot.sh production --name pre_migration_v1_1

# 2. Test migration on copy
./scripts/db_copy.sh production test_migration
./scripts/db_migrate.sh test_migration --version 1.1 --dry-run
./scripts/db_migrate.sh test_migration --version 1.1 --execute

# 3. Validate test migration
./scripts/validate_migrated_data.sh test_migration

# 4. If test successful, schedule production migration
# (During low-traffic window: 2-4 AM UTC)

# 5. Put app in maintenance mode
./scripts/maintenance_mode.sh enable \
  --message "Upgrading for new features. Back in 10 minutes!"

# 6. Run migration
./scripts/db_migrate.sh production --version 1.1 --execute

# 7. Validate migration
./scripts/validate_migrated_data.sh production

# 8. Deploy new code (compatible with both schemas)
./scripts/deploy.sh --environment production --version v1.6.0

# 9. Smoke test
./scripts/smoke_test.sh production

# 10. Disable maintenance mode
./scripts/maintenance_mode.sh disable

# 11. Monitor closely for 4 hours
./scripts/monitor_deployment.sh --duration 4h --page-on-error
```

**Rollback (if issues):**
```bash
# 1. Enable maintenance mode
./scripts/maintenance_mode.sh enable

# 2. Restore database snapshot
./scripts/db_restore.sh production pre_migration_v1_1

# 3. Deploy old code version
./scripts/deploy.sh --environment production --version v1.5.0 --force

# 4. Validate data integrity
./scripts/validate_user_progress.sh

# 5. Disable maintenance mode
./scripts/maintenance_mode.sh disable

# 6. Post-mortem
./scripts/generate_incident_report.sh
```

---

## Monitoring Commands

### Real-Time Metrics

```bash
# Watch error rate
./scripts/metrics.sh error_rate --live

# Watch lesson completion rate
./scripts/metrics.sh lesson_completions --live

# Watch XP calculations
./scripts/metrics.sh xp_awards --live --validate

# Watch user feedback
./scripts/metrics.sh user_feedback --live --alert-negative
```

### Health Checks

```bash
# Check all services
./scripts/health_check.sh all

# Check specific component
./scripts/health_check.sh lesson_engine
./scripts/health_check.sh quiz_system
./scripts/health_check.sh gamification

# Check database
./scripts/health_check.sh database --include-migrations
```

---

## Common Scenarios

### Scenario: Fix Typo in Lesson

```bash
# 1. Edit lesson (increment patch version)
# 2. Validate and test
# 3. Deploy
./scripts/quick_deploy_lesson.sh 01_understanding_stock_prices.yaml

# Auto-updates for all users, no notification
```

### Scenario: Add New Lesson Section

```bash
# 1. Edit lesson (increment minor version)
# 2. Add changelog entry
# 3. Validate and test
# 4. Deploy with notification
./scripts/deploy_lesson_update.sh 01_understanding_stock_prices.yaml --notify

# Users see "Updated" badge, can review new content
```

### Scenario: Complete Lesson Rewrite

```bash
# 1. Archive old version
# 2. Create new version (major increment)
# 3. Test thoroughly
# 4. Beta rollout
./scripts/deploy_lesson_update.sh 01_understanding_stock_prices.yaml \
  --major --beta-percentage 10

# In-progress users: Choice to continue or restart
# Completed users: Can review new version
# New users: Get new version
```

### Scenario: Emergency Bug Fix

```bash
# 1. Fix bug
# 2. Fast-track review
# 3. Emergency deploy
./scripts/emergency_deploy.sh --version v1.5.1 \
  --reason "Fix XP calculation bug" \
  --skip-canary

# Deploys immediately to all users
# Monitoring alerts active for 2 hours
```

### Scenario: Rollback Deployment

```bash
# If automatic rollback didn't trigger:
./scripts/manual_rollback.sh --to-version v1.5.0 \
  --reason "High error rate on v1.5.1"

# Switches all traffic back to old version
# Preserves user data
# Generates incident report
```

---

## Best Practices

### Version Numbering
- ✅ Use semantic versioning
- ✅ Update changelog with every version
- ✅ Archive major versions
- ✅ Test version migrations

### Deployments
- ✅ Always deploy to staging first
- ✅ Use blue-green for zero downtime
- ✅ Start with 10% canary
- ✅ Monitor for 30min before increasing
- ✅ Have rollback plan ready

### User Data
- ✅ Never delete user progress
- ✅ Snapshot before schema changes
- ✅ Validate migrations thoroughly
- ✅ Preserve XP even on rollback

### Communication
- ✅ Notify users of major changes
- ✅ Be transparent about improvements
- ✅ Offer choices for breaking changes
- ✅ Update in-app help

---

## Emergency Contacts

**On-Call Engineer:** (Use PagerDuty)  
**Database Admin:** (For migration issues)  
**Product Owner:** (For user communication)  

**Incident Response:**
1. Assess severity
2. Trigger rollback if needed
3. Page on-call if critical
4. Communicate to users
5. Post-mortem within 24h

---

## Automation Scripts Location

All deployment scripts:
```
scripts/
├── deploy.sh                 # Main deployment
├── rollback.sh              # Rollback deployment
├── traffic_switch.sh        # Traffic management
├── db_migrate.sh            # Database migration
├── db_snapshot.sh           # Backup creation
├── health_check.sh          # Health monitoring
├── validate_lessons.sh      # Lesson validation
├── monitor_deployment.sh    # Deployment monitoring
└── emergency_deploy.sh      # Emergency procedures
```

**Note:** Create these scripts based on your infrastructure (K8s, Docker, etc.)

---

## Summary

✅ **Patch updates**: Auto-deploy, no user impact  
✅ **Minor updates**: Auto-deploy with notification  
✅ **Major updates**: Beta rollout, user choice  
✅ **Code updates**: Blue-green deployment  
✅ **Schema changes**: Maintenance window, snapshots  
✅ **Rollbacks**: Automatic on errors, manual available  
✅ **User data**: Always preserved, never lost  

**Key Principle:** User progress and XP are sacred - never lose data, always preserve achievements.
