# GitHub Streak Monitor

AWS Lambda function that monitors daily GitHub commit activity and sends email status reports. Checks for commits between 00:01 and 18:30 Australian Eastern Time and sends a daily status email at 6:30 PM.

## Architecture

- **AWS Lambda**: Executes commit checking logic
- **EventBridge**: Scheduled trigger (daily at 6:30 PM Australian time).EventBridge is not directly referenced in the Lambda code. It invokes lambda_handler(event, context) at the scheduled time and the function receives an empty event {} from EventBridge.
- **SMTP**: Email notifications

## Features

- Checks GitHub API for commits in specified time window
- Sends daily status email regardless of commit status. Applauds if commits were made, otherwise sends a warning email.
- Uses Australian Eastern Time (handles AEST/AEDT automatically)
- Configurable check window (00:01-18:30 by default)

## If you want to create your own instance of the project

See [SETUP_YOUR_OWN_INSTANCE](SET_UP_YOUR_OWN_INSTANCE.md) for setting this up for your own account. 

(The AWS configuration would be hard. The rest is just checking off the boxes in this file and ensuring it runs. Be advised that the code is in australian time but AWS runs on UTC. Ensure both of them are coordinated to receive the results at the right time)

## Requirements

- AWS account (free tier eligible...I used free tier as well)
- GitHub Personal Access Token with `repo` scope. (Github classic token. Ensure the scope is selected otherwise it only gets access to the public repos). You can create this by going to Developer Settings in Setting on Github.
- Email credentials (Gmail App Password recommended) (Create a google application and use the app password without the spaces) 

## Configuration

### Environment Variables

| Variable |  Description |
|----------|-------------|
| `GITHUB_USERNAME`  | GitHub username |
| `GITHUB_TOKEN`  | GitHub (classic)Personal Access Token |
| `SMTP_SERVER`  | SMTP server (e.g., `smtp.gmail.com`) |
| `SMTP_PORT`  | SMTP port (e.g., `587` - for gmail...I used gmail) |
| `SENDER_EMAIL` | Sender email address |
| `SENDER_PASSWORD` | Email app password |
| `RECIPIENT_EMAIL` | Recipient email address |

(SENDER_PASSWORD Stands for the application password that you will create using Sender's gmail account. Ensure 2FA is enabled on the sender account for Google to easily authorize you as a human.)

## Testing

I would recommend testing through the Lambda console since it's just a click there. However, you could also use AWS CLI

```bash
aws lambda invoke --function-name github-streak-monitor output.json
```

## Cost
Free tier covers this use case (I'm not spending money on AWS yet):
- Lambda: 1M requests/month free
- EventBridge: Free for scheduled rules
- CloudWatch: 5GB logs/month free

## License
MIT
