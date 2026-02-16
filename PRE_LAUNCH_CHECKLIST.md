# Pre-Launch Checklist

## 🚀 MVP Launch Readiness

### ✅ Completed Features

#### Core Features
- [x] User registration (phone + PIN)
- [x] User authentication (session-based)
- [x] KYC phone verification (OTP)
- [x] M-Pesa payment integration
- [x] Market creation (admin)
- [x] Betting functionality
- [x] Market resolution (admin)
- [x] Automatic payout distribution
- [x] Input validation (all endpoints)
- [x] Error handling and logging

#### Infrastructure
- [x] PostgreSQL database configuration
- [x] Gunicorn application server
- [x] Nginx reverse proxy
- [x] Docker containerization
- [x] Environment variable management
- [x] Database migrations

#### Documentation
- [x] Feature documentation (FEATURES_IMPLEMENTATION.md)
- [x] Testing guide (API_TESTING_GUIDE.md)
- [x] Deployment guide (DEPLOYMENT.md)
- [x] Implementation summary (IMPLEMENTATION_SUMMARY.md)
- [x] Project README (README.md)

---

## 📋 Pre-Launch Tasks

### Phase 1: Database & Initial Setup (Before First Deployment)
- [ ] **Test database migrations**
  ```bash
  python manage.py migrate --plan  # Review
  python manage.py migrate         # Apply
  ```

- [ ] **Create admin user**
  ```bash
  python manage.py createsuperuser
  # Use phone: 254722000000, PIN: 1234
  ```

- [ ] **Verify environment variables**
  - [ ] Copy .env.example to .env
  - [ ] Fill in all required variables
  - [ ] Test database connection
  - [ ] Test M-Pesa credentials

- [ ] **Test static files collection**
  ```bash
  python manage.py collectstatic --noinput
  ```

### Phase 2: Feature Testing (Functional Testing)
- [ ] **Test user signup**
  - [ ] Valid inputs accepted
  - [ ] Duplicate phone rejected
  - [ ] Invalid phone rejected
  - [ ] Invalid PIN rejected
  
- [ ] **Test user login**
  - [ ] Correct credentials work
  - [ ] Wrong credentials rejected
  - [ ] Session cookie set
  - [ ] CSRF token returned

- [ ] **Test KYC verification**
  - [ ] OTP generation works
  - [ ] OTP expires after 10 minutes
  - [ ] Invalid OTP rejected
  - [ ] Failed attempts locked after 3
  - [ ] Successful verification updates kyc_verified flag
  - [ ] Status endpoint shows verification

- [ ] **Test M-Pesa integration**
  - [ ] Mock mode works (MPESA_DEBUG=True)
  - [ ] Real API credentials tested
  - [ ] STK push initiated successfully
  - [ ] Amount validation enforced (1-150,000)
  - [ ] Callback processing updates balance

- [ ] **Test betting**
  - [ ] Bet placed successfully
  - [ ] User balance deducted
  - [ ] Transaction created
  - [ ] Cannot bet more than balance
  - [ ] Cannot bet on closed markets

- [ ] **Test market resolution**
  - [ ] Admin can resolve markets
  - [ ] Non-admin cannot resolve
  - [ ] Payouts calculated correctly
  - [ ] Winners get original bet + share
  - [ ] Losers balance unchanged
  - [ ] Platform takes 10% fee

### Phase 3: API Testing (Integration Testing)
- [ ] **Run Postman collection** (see API_TESTING_GUIDE.md)
  - [ ] All GET endpoints return 200
  - [ ] All POST endpoints validate inputs
  - [ ] Auth endpoints set cookies
  - [ ] Admin endpoints require staff flag
  - [ ] Error responses formatted correctly

- [ ] **Test error conditions**
  - [ ] Invalid JSON rejected
  - [ ] Missing fields rejected
  - [ ] Invalid phone format rejected
  - [ ] Amount out of range rejected
  - [ ] Authentication required errors (401)
  - [ ] Authorization required errors (403)

### Phase 4: Database Testing
- [ ] **Verify data integrity**
  ```bash
  python manage.py shell
  >>> from users.models import CustomUser
  >>> user = CustomUser.objects.first()
  >>> print(user.phone_number, user.kyc_verified)
  ```

- [ ] **Check transactions table**
  ```sql
  SELECT COUNT(*) FROM payments_transaction;
  SELECT type, status, COUNT(*) FROM payments_transaction GROUP BY type, status;
  ```

- [ ] **Verify bet payouts**
  ```sql
  SELECT 
    COUNT(*) as total_bets,
    SUM(CASE WHEN result='WON' THEN 1 ELSE 0 END) as winners,
    SUM(payout) as total_distributed
  FROM markets_bet;
  ```

### Phase 5: Performance Testing
- [ ] **Load test with 100 concurrent users**
  ```bash
  # Using Apache Bench
  ab -n 1000 -c 100 http://localhost:8000/api/users/check/
  
  # Or using Locust (see DEPLOYMENT.md)
  locust -f locustfile.py --host=http://localhost:8000
  ```

- [ ] **Check response times**
  - [ ] Signup: < 500ms
  - [ ] Login: < 500ms
  - [ ] Place bet: < 500ms
  - [ ] List markets: < 200ms

- [ ] **Monitor resource usage**
  - [ ] CPU: < 80%
  - [ ] Memory: < 2GB
  - [ ] Database connections: adequate
  - [ ] No query timeouts

### Phase 6: Security Testing
- [ ] **Test CSRF protection**
  - [ ] POST without CSRF token rejected
  - [ ] CSRF token updated on login

- [ ] **Test authentication**
  - [ ] Unauthenticated requests return 401
  - [ ] Admin-only endpoints return 403 for non-admin
  - [ ] Session expires properly

- [ ] **Test input validation**
  - [ ] XSS attempts blocked
  - [ ] SQL injection attempts blocked
  - [ ] Rate limiting working

- [ ] **Test sensitive data**
  - [ ] Passwords not logged
  - [ ] Balance not exposed in responses (except to owner)
  - [ ] Phone numbers masked in some contexts

### Phase 7: Deployment Testing (Docker)
- [ ] **Test Docker build**
  ```bash
  docker-compose build
  ```

- [ ] **Test Docker startup**
  ```bash
  docker-compose up -d
  docker-compose logs -f django
  ```

- [ ] **Test in container**
  ```bash
  docker-compose exec django python manage.py migrate
  docker-compose exec django python manage.py shell
  ```

- [ ] **Test nginx proxy**
  - [ ] Static files served
  - [ ] API endpoints proxied correctly
  - [ ] CORS headers set

### Phase 8: Final Integration
- [ ] **Test complete user flow**
  1. Signup
  2. Login
  3. Start KYC
  4. Verify KYC
  5. Initiate deposit (mock)
  6. Check balance
  7. Place bet
  8. Resolve market (as admin)
  9. Verify payout

- [ ] **Test edge cases**
  - [ ] Same user betting twice on same market
  - [ ] Multiple users on same market
  - [ ] Market resolution with no bets
  - [ ] Market resolution with tie (50-50 split)

---

## 🔍 Verification Checklist

### Code Quality
- [ ] No syntax errors: `python manage.py check`
- [ ] No import errors: `python manage.py shell` (empty, just checking imports)
- [ ] No logging errors: Search for `logger.error` mentions
- [ ] No hardcoded passwords

### Database
- [ ] All migrations applied: `python manage.py showmigrations` (none pending)
- [ ] Database accessible
- [ ] Tables created
- [ ] Indexes created (if any)

### Configuration
- [ ] .env file exists and is complete
- [ ] SECRET_KEY is set and strong
- [ ] DEBUG=False in production
- [ ] ALLOWED_HOSTS configured
- [ ] Database credentials correct

### Documentation
- [ ] README.md complete and accurate
- [ ] API_TESTING_GUIDE.md has all endpoints
- [ ] FEATURES_IMPLEMENTATION.md covers all features
- [ ] Code comments on complex logic
- [ ] Docstrings on all public functions

### Monitoring
- [ ] Logging configured
- [ ] Error tracking working
- [ ] API monitoring in place (if available)
- [ ] Database monitoring setup

---

## 🎯 Pre-Launch Day Tasks

### 24 Hours Before Launch
- [ ] Final code review
- [ ] Run full test suite
- [ ] Backup database
- [ ] Verify all endpoints in staging
- [ ] Check M-Pesa production credentials
- [ ] Brief team on launch plan

### 2 Hours Before Launch
- [ ] Verify all services running
- [ ] Check database disk space
- [ ] Review error logs (should be clean)
- [ ] Final health check on all endpoints
- [ ] Prepare rollback plan

### Launch Time
- [ ] Deploy to production
- [ ] Verify services started
- [ ] Run smoke tests (basic endpoints)
- [ ] Monitor logs for errors
- [ ] Check error tracking dashboard

### Post-Launch (First 24 Hours)
- [ ] Monitor API response times
- [ ] Check error rates
- [ ] Verify M-Pesa callbacks working
- [ ] Monitor database performance
- [ ] Have support team on standby

---

## 📊 Success Criteria

### Performance Targets
- [ ] API response time < 500ms average
- [ ] Database query time < 100ms average
- [ ] 99% uptime
- [ ] Zero downtime deployments possible

### Reliability Targets
- [ ] No data loss
- [ ] All transactions logged
- [ ] Payment confirmations reliable
- [ ] No duplicate transactions

### Security Targets
- [ ] No unauthorized access
- [ ] All inputs validated
- [ ] No SQL injections
- [ ] No XSS vulnerabilities
- [ ] HTTPS enabled
- [ ] Secure headers set

### Business Targets
- [ ] User registration works
- [ ] At least 1 test transaction successful
- [ ] Market creation possible
- [ ] Betting functional
- [ ] Admin panel accessible

---

## 🚨 Rollback Plan

### Quick Rollback
If critical issues found:

```bash
# Revert to previous version
git revert [commit-hash]

# Or restore from backup
docker-compose down
docker volume rm [volume-name]  # Database
docker-compose up -d

# Restore from backup
psql -U kibeezy_user kibeezy < backup.sql
```

### Partial Rollback
If specific feature broken:

1. Disable feature via environment variable
2. Revert specific file
3. Re-migrate if database changes

### Communication
- [ ] Notify users of issue
- [ ] Post status update
- [ ] Commit to fix ETA

---

## 📝 Documentation Before Launch

Ensure customers have:
- [ ] **Getting Started Guide** - How to signup and place bets
- [ ] **FAQ** - Common questions answered
- [ ] **Terms of Service** - Legal document
- [ ] **Privacy Policy** - Data handling
- [ ] **Support Contact** - How to get help
- [ ] **API Documentation** - For developers (optional)

---

## ✅ Final Sign-Off

Before launching, confirm:

- [ ] **Development Lead**: All tests passing
- [ ] **DevOps**: Infrastructure verified
- [ ] **Product Manager**: Features meet requirements
- [ ] **Business**: Legal/compliance reviewed
- [ ] **CEO**: Ready to launch

---

## 🎉 You're Ready to Launch!

Once all boxes are checked, the platform is ready for:

✅ Public access  
✅ Real users  
✅ Real money  
✅ Production traffic  

---

## 📞 Post-Launch Support

### First Week
- Daily monitoring
- Quick response to issues
- User feedback collection
- Performance optimization

### Second Week
- Stability confirmation
- Load testing results review
- User feedback analysis
- Plan Phase 2 features

### Ongoing
- Monthly security audits
- Performance monitoring
- Feature requests triage
- User support

---

**Current Status**: Phase 1 Completed ✅  
**Next Step**: Run database migrations and start Phase 2 (Feature Testing)

Use this checklist to track progress toward launch! 🚀
