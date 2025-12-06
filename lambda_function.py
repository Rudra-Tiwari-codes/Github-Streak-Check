"""
GitHub Streak Monitor 
(AWS Lambda Function)
This script runs on AWS Lambda (Amazon's serverless computing service) and:
1. Checks if you made any GitHub commits today
2. Sends you an email telling you whether you committed or not (harder part honestly)

It's designed to help you maintain your GitHub contribution streak (the green dots on your profile)
How it works:
- AWS EventBridge triggers this function daily at 6:30 PM Australian time
- The function calls GitHub's API to fetch your recent activity
- It looks for "PushEvents" (commits) within today's time window. It looks only for push events, nothing els
- It DOES NOT look for pull requests, issues, or any lazy event like "created a new repository".
- It sends an email with the result. You can modify it to make it more fun.

Required Environment Variables are in the .env.example file. You can modify it to your liking.
"""

# 'os' lets us read environment variables (like passwords stored securely in AWS)
import os
# 'smtplib' is Python's built-in library for sending emails via SMTP protocol
import smtplib
# 'logging' helps us print debug messages that show up in AWS CloudWatch logs...very helpful if you are building your own version of this project.
import logging
from datetime import datetime, timezone

# These two imports help us create nicely formatted emails with HTML
# MIMEText creates the email body, MIMEMultipart combines multiple formats # Found this on google and a youtube video. Helped a ton with formatting.
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 'requests' for making HTTP requests (calling APIs)
# We use it to call GitHub's API
import requests

# 'pytz' handles timezone conversions properly..PYthon Time Zone
# Important because GitHub uses UTC but we want Australian time
import pytz

# Create a logger, this sends messages to AWS CloudWatch so we can debug issues...hopefully you face none. Ever.
# It's like print but with timestamps and log levels
logger = logging.getLogger()

# INFO level means we'll see informational messages (not just errors)
# Level: DEBUG < INFO < WARNING < ERROR < CRITICAL.
logger.setLevel(logging.INFO)
def get_env(key, required=True):
    """
    Safely get an environment variable.
    Environment variables are like secret settings stored outside the code.
    In AWS Lambda, you set these in the console under "Configuration > Environment variables". DO NOT MISS THIS.
    """
    # os.environ.get() returns the value of the environment variable, If it doesn't exist, it returns None
    value = os.environ.get(key)
    # If it's missing, raise an error with a helpful message
    if required and not value:
        raise ValueError(f"Missing the required environment variable: {key}")
    return value

# GITHUB API FUNCTION

def check_commits_today(username, token):
    """
    Check if the user has made any commits today (Australian time).
    
    This function figures out what "today" means in Australian time, calls GitHub's Events API to get recent activity, and filters for PushEvents (commits) within today's window. You can also 
    modify this to make it lineant and inclue pull requests, issues, etc.
    
    How GitHub's Events API works: https://api.github.com/users/{username}/events.
    Returns up to 300 events (paginated, 100 per page). Events include: PushEvent, CreateEvent, IssueCommentEvent, etc.
    We only care about PushEvent (which represents commits).
    """
    
    # Set up Australian timezone (very painful debugging which I didn't realise until very later on before asking this on Stack Overflow)

    aus_tz = pytz.timezone('Australia/Sydney')
    now_aus = datetime.now(aus_tz)
    today_aus = now_aus.date()
    # We are creating a time object for 00:01 and 18:30, because we want to check for commits between 00:01 and 18:30 Australian time. You can modify this window.
    check_start_aus = aus_tz.localize(
        datetime.combine(today_aus, datetime(1900, 1, 1, 0, 1).time())
    )
    check_end_aus = aus_tz.localize(
        datetime.combine(today_aus, datetime(1900, 1, 1, 18, 30).time())
    )
    
    # Convert to UTC for comparison with GitHub timestamps
    check_start_utc = check_start_aus.astimezone(timezone.utc)
    check_end_utc = check_end_aus.astimezone(timezone.utc)

    # Log what we're doing (these messages appear in AWS CloudWatch...I used this for debugging)
    logger.info(f"Checking commits for {today_aus} between 00:01-18:30 AEDT")
    logger.info(f"UTC range: {check_start_utc} to {check_end_utc}")

    # Prepare the API request
    url = f"https://api.github.com/users/{username}/events"
    
    # HTTP headers tell GitHub who we are and what format we want
    headers = {
        # Authorization header with our token - this authenticates us
        "Authorization": f"token {token}",
        
        # Telling GitHub we want JSON in their v3 API format..
        "Accept": "application/vnd.github.v3+json"
    }

    # Fetch events with pagination
    all_events = []  # We'll collect all events here
    page = 1  # Start at page 1
    
    while page <= 5:
        params = {"page": page, "per_page": 100}
        
        try:
            # Make the HTTP GET request to GitHub's API, give up if it takes more than 10 seconds
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            # Raise an exception if the request failed
            response.raise_for_status()
            
            # Parse the JSON response into a Python list of dictionaries...again, this is how we get the data from the API.
            events = response.json()
            
        except Exception as e:
            # If anything goes wrong, log the error and stop fetching...this is how we handle errors.
            logger.error(f"Failed to fetch events: {e}")
            break

        if not events:
            break
        
        # Add this page's events to our collection...this is how we collect the data from the API.
        all_events.extend(events)
        logger.info(f"Page {page}: {len(events)} events (total: {len(all_events)})")
        
        # Stop early if we've gone past our time window...this is how we optimize the function.
        oldest_event_time = datetime.fromisoformat(
            events[-1]["created_at"].replace("Z", "+00:00")
        )
        
        # If the oldest event is before our window, stop fetching...this is how we stop the function.
        if oldest_event_time < check_start_utc:
            break
        
        # Next page
        page += 1

    logger.info(f"Total events: {len(all_events)}")

    # -------------------------------------------------------------------------
    # STEP 6: Filter for commits within our time window
    # -------------------------------------------------------------------------
    
    commits_today = []  # Will hold timestamps of commits we find
    
    # Loop through all events we fetched
    for event in all_events:
        
        # We only care about "PushEvent" - this is when commits are pushed
        # Other events like "IssueCommentEvent" or "WatchEvent" don't count
        # .get() is safer than ['type'] - it returns None if key doesn't exist
        if event.get("type") != "PushEvent":
            continue  # Skip to the next event
        
        # Parse the event timestamp from ISO 8601 format
        event_time = datetime.fromisoformat(
            event["created_at"].replace("Z", "+00:00")
        )
        
        # Convert to Australian time for logging (easier to understand)
        event_time_aus = event_time.astimezone(aus_tz)
        
        # Get the repository name for logging
        # .get() with a default handles missing keys gracefully
        repo_name = event.get('repo', {}).get('name', 'unknown')
        
        # Log each PushEvent we find
        logger.info(
            f"PushEvent: {event_time_aus.strftime('%Y-%m-%d %H:%M:%S %Z')} - {repo_name}"
        )
        
        # Check if this commit falls within our time window
        if check_start_utc <= event_time <= check_end_utc:
            # This commit counts - it's within our window
            logger.info(f"  -> Found commit in window!")
            commits_today.append(event_time)
            
        elif event_time > check_end_utc:
            # This commit is after our window (e.g., made after 6:30 PM)
            logger.info(f"  -> After 18:30, skipping")
            
        else:
            # This commit is before our window (e.g., from yesterday)
            logger.info(f"  -> Before window or old")

    # -------------------------------------------------------------------------
    # STEP 7: Return the results
    # -------------------------------------------------------------------------
    
    if commits_today:
        logger.info(f"Found {len(commits_today)} commit(s) today")
        # Return True (commits found) and the list of commit times
        return True, commits_today
    else:
        logger.info("No commits found in check window")
        # Return False (no commits) and an empty list
        return False, []


# =============================================================================
# EMAIL FUNCTION
# =============================================================================

def send_email(smtp_server, smtp_port, sender, password, recipient, has_commit, commit_times, date_str):
    """
    Send a status email about today's commit activity.
    
    This function:
    1. Creates an email with both plaintext and HTML versions
    2. Connects to the SMTP server (like Gmail)
    3. Authenticates and sends the email
    
    Parameters:
        smtp_server (str): Mail server address (e.g., "smtp.gmail.com")
        smtp_port (str): Mail server port (usually "587" for TLS)
        sender (str): Email address sending the email
        password (str): Password for the sender email (use App Password for Gmail)
        recipient (str): Email address to send to
        has_commit (bool): Whether commits were found today
        commit_times (list): List of commit timestamps
        date_str (str): Today's date as a string (e.g., "2025-12-06")
    
    What is SMTP?
        SMTP (Simple Mail Transfer Protocol) is the standard way to send emails.
        It's like the postal service for email - you give it a message and address,
        and it delivers it. Gmail, Outlook, etc. all have SMTP servers.
    
    Why both plaintext and HTML?
        Some email clients don't support HTML, so we include both versions.
        The email client will pick the best one it can display.
    """
    
    # Get Australian timezone (not used in this function but kept for consistency)
    aus_tz = pytz.timezone('Australia/Sydney')
    
    # -------------------------------------------------------------------------
    # STEP 1: Create the email message container
    # -------------------------------------------------------------------------
    
    # MIMEMultipart("alternative") creates an email that can hold multiple versions
    # "alternative" means: "here are different versions of the same content"
    message = MIMEMultipart("alternative")
    
    # -------------------------------------------------------------------------
    # STEP 2: Set up email content based on whether commits were found
    # -------------------------------------------------------------------------
    
    if has_commit:
        # SUCCESS: User made commits today
        subject = f"GitHub Streak Monitor - You're Slaying ({date_str})"
        status = "FIRE"
        status_color = "#28a745"  # Green color (hex code)
        status_text = f"Found {len(commit_times)} commit(s) between 00:01 and 18:30"
        body_text = (
            f"No cap, you're absolutely crushing it! "
            f"You made {len(commit_times)} commit(s) today. "
            f"That green dot is looking fresh."
        )
        footer = "Keep up the grind, you're doing amazing!"
    else:
        # WARNING: No commits found today
        subject = f"GitHub Streak Monitor - We Need to Talk ({date_str})"
        status = "ALERT"
        status_color = "#dc3545"  # Red color (hex code)
        status_text = "No commits found between 00:01 and 18:30"
        body_text = (
            "Yikes, no commits detected today. "
            "Your contribution streak is about to catch these hands if you don't commit something ASAP. "
            "Don't let that green dot ghost you!"
        )
        footer = "Time to push something before it's too late. You got this!"
    
    # -------------------------------------------------------------------------
    # STEP 3: Set email headers
    # -------------------------------------------------------------------------
    
    # These are standard email headers that every email needs
    message["Subject"] = subject  # The email subject line
    message["From"] = sender      # Who the email is from
    message["To"] = recipient     # Who the email is going to

    # -------------------------------------------------------------------------
    # STEP 4: Create plaintext version of the email
    # -------------------------------------------------------------------------
    
    # This is the simple text version for email clients that don't support HTML
    # Triple quotes (""") allow multi-line strings in Python
    text = f"""GitHub Streak Monitor - Daily Status

Date: {date_str}
Status: {status}
{status_text}

{body_text}

Check Window: 00:01 - 18:30 (Australian Eastern Time)

{footer}
"""

    # -------------------------------------------------------------------------
    # STEP 5: Create HTML version of the email
    # -------------------------------------------------------------------------
    
    # This is the fancy formatted version with colors and styling
    # Most modern email clients will display this version
    html = f"""
<html>
<body>
<h2>GitHub Streak Monitor - Daily Status</h2>
<p><strong>Date:</strong> {date_str}</p>
<p><strong>Status:</strong> <span style="color: {status_color}; font-weight: bold;">{status}</span></p>
<p><strong>{status_text}</strong></p>
<hr>
<p>{body_text}</p>
<p><strong>Check Window:</strong> 00:01 - 18:30 (Australian Eastern Time)</p>
<p><em>{footer}</em></p>
</body>
</html>
"""

    # -------------------------------------------------------------------------
    # STEP 6: Attach both versions to the email
    # -------------------------------------------------------------------------
    
    # MIMEText creates a text block that can be attached to an email
    # The second argument specifies the content type
    message.attach(MIMEText(text, "plain"))  # Plaintext version
    message.attach(MIMEText(html, "html"))   # HTML version

    # -------------------------------------------------------------------------
    # STEP 7: Connect to SMTP server and send the email
    # -------------------------------------------------------------------------
    
    # 'with' statement ensures the connection is properly closed when done
    # smtplib.SMTP() opens a connection to the mail server
    with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
        
        # starttls() upgrades the connection to use encryption (TLS)
        # This is important for security - it encrypts your password and email
        server.starttls()
        
        # login() authenticates with your email and password
        # For Gmail, you MUST use an "App Password" (not your regular password)
        server.login(sender, password)
        
        # sendmail() actually sends the email
        # message.as_string() converts our MIME message to the format SMTP expects
        server.sendmail(sender, recipient, message.as_string())

    # Log that we successfully sent the email
    logger.info(f"Email sent to {recipient}")


# =============================================================================
# MAIN LAMBDA HANDLER
# =============================================================================

def lambda_handler(event, context):
    """
    AWS Lambda entry point - this function is called when Lambda runs.
    
    When AWS Lambda executes this file, it looks for a function called
    "lambda_handler" (configured in the Lambda console). AWS calls this
    function and passes in two arguments:
    
    Parameters:
        event (dict): Data passed to the function (from EventBridge, API Gateway, etc.)
                      For our scheduled task, this is usually empty ({})
        
        context (object): Lambda runtime information (request ID, time remaining, etc.)
                          We don't use this, but Lambda always passes it
    
    Returns:
        dict: Response with statusCode and body
              - statusCode 200: Success
              - statusCode 500: Error occurred
    
    How AWS Lambda works:
        1. You upload your code as a .zip file
        2. You configure environment variables (secrets, settings)
        3. You set up a trigger (EventBridge schedule, API Gateway, etc.)
        4. When triggered, Lambda runs your handler function
        5. Lambda automatically scales - runs multiple copies if needed
        6. You only pay for the time your code runs
    """
    
    try:
        # ---------------------------------------------------------------------
        # STEP 1: Get configuration from environment variables
        # ---------------------------------------------------------------------
        
        # These were set in AWS Lambda console under Configuration > Environment variables
        username = get_env("GITHUB_USERNAME")
        token = get_env("GITHUB_TOKEN")
        
        # ---------------------------------------------------------------------
        # STEP 2: Get today's date in Australian time
        # ---------------------------------------------------------------------
        
        aus_tz = pytz.timezone('Australia/Sydney')
        today_aus = datetime.now(aus_tz).date()
        
        # Format the date as "2025-12-06" for use in email
        date_str = today_aus.strftime("%Y-%m-%d")

        # ---------------------------------------------------------------------
        # STEP 3: Check if user made commits today
        # ---------------------------------------------------------------------
        
        has_commit, commit_times = check_commits_today(username, token)

        # ---------------------------------------------------------------------
        # STEP 4: Send status email
        # ---------------------------------------------------------------------
        
        logger.info(f"Sending status email for {date_str}")

        try:
            send_email(
                get_env("SMTP_SERVER"),
                # SMTP_PORT is optional - default to 587 if not set
                get_env("SMTP_PORT", required=False) or "587",
                get_env("SENDER_EMAIL"),
                get_env("SENDER_PASSWORD"),
                get_env("RECIPIENT_EMAIL"),
                has_commit,
                commit_times,
                date_str
            )
        except Exception as e:
            # If email fails, log the error and return a 500 error
            logger.error(f"Email failed: {e}")
            return {"statusCode": 500, "body": f"Email failed: {e}"}

        # ---------------------------------------------------------------------
        # STEP 5: Return success response
        # ---------------------------------------------------------------------
        
        result = "commit found" if has_commit else "no commit found"
        
        # Return a success response
        # statusCode 200 means "OK" in HTTP terms
        return {"statusCode": 200, "body": f"Email sent. {result}."}

    except Exception as e:
        # Catch any unexpected errors and return a 500 error
        logger.error(f"Error: {e}")
        return {"statusCode": 500, "body": str(e)}
