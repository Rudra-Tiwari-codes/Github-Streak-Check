# Set Up Your Own Instance

Complete deployment guide for THE GitHub Streak Monitor. AWS configuration can be tricky, but this checklist ensures you don't miss steps. 

## Prerequisites

- [ ] AWS account (free tier eligible - I used free tier)
- [ ] GitHub Personal Access Token with `repo` scope
  - Use GitHub **Classic Token** (Settings → Developer Settings → Personal Access Tokens)
  - Select `repo` scope, not just `public_repo` (otherwise only accesses public repos)
- [ ] Gmail App Password
  - Enable 2FA on Gmail (required for App Passwords)
  - Google Account → Security → App Passwords → Generate (16-character password)
  - Use this password **without spaces** as `SENDER_PASSWORD`

| Variable | Example |
|----------|---------|
| `GITHUB_USERNAME` | Your GitHub username |
| `GITHUB_TOKEN` | GitHub Classic Personal Access Token |
| `SMTP_SERVER` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` (for Gmail) |
| `SENDER_EMAIL` | Your Gmail address |
| `SENDER_PASSWORD` | Gmail App Password (16-char, no spaces) |
| `RECIPIENT_EMAIL` | Email to receive notifications |

---

## Deployment Steps

### 1. Create AWS Account

1. Go to [aws.amazon.com](https://aws.amazon.com) and create account
2. Complete verification
3. Free tier covers this completely

### 2. Package Lambda Function

**Windows:**
```powershell
.\package.ps1
```

**Linux/Mac:**
```bash
./package.sh
```

Creates `deployment.zip` with dependencies (requests, pytz).

- [ ] `deployment.zip` created

### 3. Create IAM Role

1. AWS Console → IAM → Roles → Create role
2. AWS service → Lambda
3. Attach policy: `AWSLambdaBasicExecutionRole`
4. Name: `github-streak-monitor-role`

- [ ] IAM role created

### 4. Create Lambda Function

1. AWS Console → Lambda → Functions → Create function
2. Function name: `github-streak-monitor`
3. Runtime: Python 3.11, Architecture: x86_64
4. Execution role: `github-streak-monitor-role`

- [ ] Lambda function created

### 5. Upload Code & Configure

1. Code tab → Upload from .zip → `deployment.zip`
2. Configuration → General configuration:
   - Timeout: **30 seconds**
   - Memory: **128 MB**
3. Configuration → Environment variables → Add all 7 variables from Prerequisites table

- [ ] Code uploaded
- [ ] Timeout/memory configured  
- [ ] All environment variables set

### 6. Test Function

1. Test tab → Create test event → Event JSON: `{}`
2. Test and verify success
3. Check email for notification

### 7. Create EventBridge Schedule

1. AWS Console → EventBridge → Rules → Create rule
2. Name: `github-streak-daily-check`, Type: Schedule
3. Cron expression:
   - **6:30 PM AEDT** (Oct-Apr): `cron(30 7 * * ? *)`
   - **6:30 PM AEST** (Apr-Oct): `cron(30 8 * * ? *)`
4. Target: Lambda function → `github-streak-monitor`

**Note**: EventBridge uses UTC. Update cron twice yearly for daylight saving, or use the current season's expression.

- [ ] EventBridge rule created
- [ ] Target configured

### 8. Verify

- [ ] EventBridge rule enabled
- [ ] CloudWatch logs show success
- [ ] Daily email received at 6:30 PM


---

## Troubleshooting

**Email Error (535)**: Gmail needs App Password, not regular password. Enable 2FA first, then generate App Password.

**Commits Not Detected**: 
- Token needs `repo` scope (not `public_repo`)
- Commits must be **pushed** to GitHub (not just local commits)
- Only detects PushEvents (actual commits), not PRs or issues
- Check CloudWatch logs for time conversions...very useful

**Function Not Triggering**: 
- Verify EventBridge rule is enabled
- Check cron expression matches current timezone (AEST vs AEDT)
- Review EventBridge metrics

**Lambda Errors**: Check CloudWatch logs under Monitor tab, verify environment variables.

---

## Updating Code

1. Edit `lambda_function.py` locally
2. Run packaging script
3. Lambda → Code → Upload .zip
4. Test function

