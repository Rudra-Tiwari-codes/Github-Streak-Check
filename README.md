# GitHub Streak Monitor

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-Lambda-FF9900?logo=amazonaws)
![Free Tier](https://img.shields.io/badge/Cost-$0%2Fmonth-success)

## Problem Statement

Maintaining a GitHub contribution streak requires daily commits—easy to forget during busy periods. Existing streak trackers only show current status; they don't proactively warn you before the streak breaks.

## Solution

A serverless monitoring function that checks your GitHub activity daily and sends email alerts if you haven't committed, running entirely on AWS Free Tier.

## Methodology

- **Scheduled Trigger** — EventBridge runs daily at configurable time
- **GitHub API** — Checks contribution calendar for today's activity
- **Smart Alerts** — Only notifies if no commits detected
- **Email Delivery** — AWS SES for reliable notifications

## Results

| Component | Free Tier Limit | Usage |
|-----------|-----------------|-------|
| Lambda | 1M requests/month | ~30 |
| EventBridge | Unlimited scheduled rules | 1 |
| SES | 62,000 emails/month | ~30 |
| **Total Cost** | — | **$0/month** |

## Architecture

```
EventBridge (Daily) → Lambda → GitHub API
                          ↓
                        SES → Email Alert
```

## Configuration

| Variable | Description |
|----------|-------------|
| `GITHUB_USERNAME` | Your GitHub username |
| `ALERT_EMAIL` | Email for notifications |
| `CHECK_TIME` | UTC time for daily check |

## Future Improvements

- Add weekly summary report with contribution graph
- Implement Slack/Discord webhook as alternative to email

---

[Rudra Tiwari](https://github.com/Rudra-Tiwari-codes)
