# Security Guide — API Key Management

This document covers how to securely manage API keys and credentials for this project. Inspired by real incidents where leaked API keys caused $100K+ in unauthorized charges within days.

---

## API Keys Used

| Key | Required | Used By | Service |
|-----|----------|---------|---------|
| `GOOGLE_CLOUD_API_KEY` | Yes | `ocr_cloud_vision.py`, `server.py`, Cloud Function | Cloud Vision, Drive API |
| `GEMINI_API_KEY` | Yes | `ocr_multimodel.py`, Cloud Function | Gemini Flash OCR |
| `ANTHROPIC_API_KEY` | No | `ocr_multimodel.py` | Claude (optional 3rd model) |

**Note:** `GOOGLE_CLIENT_ID` in `useAuth.js` is a public OAuth Client ID — this is designed to be visible in frontend code and does not need protection.

---

## Current Protections

### In this repository

- **`.env` in `.gitignore`** — API keys never committed to git
- **`.env.example`** — template with empty values, safe to commit
- **All token files gitignored** — `token*.json`, `credentials.json`, `service_account*.json`
- **No hardcoded keys in current tracked files** — all keys loaded via `os.environ` or `.env` file
- **⚠️ Git history contains leaked keys** — `cloud/env.yaml` and `cloud/_env_vars.yaml` were previously committed with a Gemini API key. The key (`AIzaSyC8_...`) has been **revoked** and is no longer valid. Files have been removed from tracking but remain in git history. Consider `git filter-repo` or BFG to fully purge if needed.

### Verification

Run these commands to verify no secrets are exposed:

```bash
# Search for hardcoded API keys (should return 0 results)
grep -r "AIzaSy" --include="*.py" --include="*.js" --include="*.json"

# Check git history for accidentally committed secrets
git log --all --diff-filter=A -- "*.env" "token*.json" "credentials.json"

# List untracked files that might contain secrets
git status --porcelain | grep "^??" | grep -E "\.(env|json|pem|p12)$"
```

---

## Required Google Cloud Console Settings

### 1. Budget Alert (CRITICAL)

Without this, a leaked key can generate unlimited charges.

```
Google Cloud Console → Billing → Budgets & Alerts
→ Create Budget
  - Name: "Election Verification Monthly"
  - Amount: $50 (or your preferred limit)
  - Alert thresholds: 50%, 90%, 100%
  - Notifications: Email + Pub/Sub
→ Save
```

**Why $50?** Normal OCR usage for this project costs ~$5-15/month. A $50 alert catches anomalies early while allowing burst usage during batch processing.

### 2. API Key Restrictions

```
Google Cloud Console → APIs & Services → Credentials
→ Select your API Key → Edit

Application restrictions:
  → IP addresses → Add your machine's public IP
  → (Optional) Add Cloud Function's egress IP range

API restrictions:
  → Restrict key → Select APIs:
    ✅ Generative Language API (Gemini)
    ✅ Cloud Vision API
    ✅ Google Drive API
    ❌ Everything else — DISABLED
→ Save
```

### 3. Quota Limits

```
Google Cloud Console → APIs & Services → Generative Language API → Quotas

Set limits:
  - Requests per minute: 60
  - Requests per day: 5,000

Google Cloud Console → APIs & Services → Cloud Vision API → Quotas
  - Requests per minute: 60
  - Requests per day: 5,000
```

These quotas cap maximum possible spend even if a key is compromised.

### 4. Cloud Function Authentication

The current deployment uses `--allow-unauthenticated`, which means anyone who discovers the Cloud Function URL can call it and consume Gemini API credits.

**To fix:**

```powershell
# In cloud/deploy.ps1, change:
#   --allow-unauthenticated
# To:
#   --no-allow-unauthenticated

# Then authenticate dispatch scripts with a service account:
gcloud auth activate-service-account --key-file=service-account.json
```

---

## Emergency Response — If a Key Is Leaked

### Immediate actions (do within 5 minutes):

1. **Revoke the key immediately**
   ```
   Google Cloud Console → APIs & Services → Credentials
   → Find the compromised key → Delete / Disable
   ```

2. **Check billing for unauthorized usage**
   ```
   Google Cloud Console → Billing → Reports
   → Filter by last 24 hours → Look for spikes
   ```

3. **Delete Cloud Function (if applicable)**
   ```bash
   gcloud functions delete ocr-worker --project election-ocr
   ```

4. **Rotate all keys**
   - Create new API keys with restrictions
   - Update `.env` with new keys
   - Re-deploy Cloud Function with new keys

5. **Audit git history**
   ```bash
   # Check if the key was accidentally committed
   git log --all -p | grep -i "AIzaSy"
   ```

### After the incident:

- Review how the key was leaked (logs, commit history, environment)
- Enable Cloud Audit Logging for future detection
- Consider switching to short-lived tokens (OAuth2) instead of long-lived API keys

---

## Best Practices

### Do
- ✅ Store keys in `.env` only
- ✅ Set budget alerts before using any paid API
- ✅ Restrict API keys to specific APIs and IPs
- ✅ Set daily quota limits
- ✅ Use `--no-allow-unauthenticated` for Cloud Functions
- ✅ Rotate keys periodically (every 90 days)
- ✅ Review billing dashboard weekly

### Don't
- ❌ Hardcode keys in source code
- ❌ Pass keys in URL query strings (use headers instead)
- ❌ Share `.env` files via chat, email, or cloud storage
- ❌ Use unrestricted API keys
- ❌ Skip budget alerts ("it's just a small project")
- ❌ Ignore billing spikes ("it's probably just a glitch")

---

## Cost Reference

Typical costs for this project's operations:

| Operation | Cost per unit | Daily budget |
|-----------|--------------|-------------|
| Gemini Flash OCR | ~$0.001/page | $5 (5,000 pages) |
| Cloud Vision OCR | ~$0.0015/page | $7.50 (5,000 pages) |
| Google Drive API | Free (quota-limited) | $0 |
| Claude OCR | ~$0.003/page | $15 (5,000 pages) |

**Maximum possible daily cost with quotas set:** ~$27.50

**Without quotas, a leaked key could cost:** $1,000+/hour (automated high-volume requests)

---

*Last updated: 4 April 2026*
