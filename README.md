# 10bis Credit Retrieval

This Python script automatically checks your available 10bis credit, loads it onto your 10bis card when eligible, and sends an email notification with the result.

## 1. Email Configuration

Before running the script, configure the sender email address and password.

Open `retrieve-10bis-credit.py` and locate:

```python
EMAIL_ADDRESS = "<your-email>"
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '<email-password>')
```

You have two options:

### Option 1: Configure directly in the script

Replace `<your-email>` and `<email-password>` with your actual sender email address and password.

**Note:** This is simpler but less secure. Never commit a script containing real credentials to GitHub.

### Option 2: Use environment variables (recommended)

Update the Python script to:

```python
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
```

Then configure the environment variables in your terminal:

```bash
export EMAIL_ADDRESS="your-email@gmail.com"
export EMAIL_PASSWORD="your-app-password"
```

The script will automatically read these values.

**For Gmail users:** You must generate a Google App Password instead of using your regular Gmail password. See the screenshot at the bottom of this README.

## 2. Steps to Run

1. Open a terminal.

2. Navigate to the folder containing the script:

   ```bash
   cd /home/user/path-with-script
   ```

3. Install the required dependency if it is not already installed:

   ```bash
   /usr/bin/python3 -m pip install requests
   ```

4. Run the script manually for the first time:

   ```bash
   /usr/bin/python3 retrieve-10bis-credit.py --email "your-work-email@example.com" --notify-email "your-notification-email@example.com"
   ```

5. Follow the prompts and enter the SMS verification code (OTP) when requested.

After successful authentication, the script saves the session cookies locally so future runs can reuse the existing session.

## 3. Cron Setup

After the first successful run, you can schedule the script to run automatically.

Open your crontab:

```bash
crontab -e
```

Add the following line to run the script every Sunday through Thursday at 07:00:

```cron
0 7 * * SUN-THU cd /home/user/path-with-script && /usr/bin/python3 retrieve-10bis-credit.py --email "your-work-email@example.com" --notify-email "your-notification-email@example.com" >> /home/user/path-with-script/retrieve-10bis-credit.log 2>&1
```

**Important:** If you use environment variables for email authentication, cron must have access to them.

One option is to define them at the top of your crontab:

```cron
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-app-password

0 7 * * SUN-THU cd /home/user/path-with-script && /usr/bin/python3 retrieve-10bis-credit.py --email "your-work-email@example.com" --notify-email "your-notification-email@example.com" >> /home/user/path-with-script/retrieve-10bis-credit.log 2>&1
```

The cron schedule uses the server's configured timezone. Ensure it matches your intended 07:00 execution time.

## 4. Session Cookies

- The script stores authentication cookies locally under `cookies/<account-email>/cookie.pkl`.
- Cookies are reused during subsequent executions to avoid repeating the login process.
- The session expiration time is unknown.
- If authentication expires, remove the relevant account's `cookie.pkl` file and run the script manually again to complete OTP verification.
- Keep the `cookies/` directory private because session cookies may grant access to your account.

## 5. Gmail App Password

If you are using Gmail as the notification sender, you need a Google App Password.

1. Open your Google Account settings.
2. Navigate to **Security**.
3. Enable **2-Step Verification** if it is not already enabled.
4. Open [Google App Passwords](https://myaccount.google.com/apppasswords).
5. Generate an App Password for this script.
6. Use the generated password as `EMAIL_PASSWORD`.

Refer to the screenshot below for guidance:

![Gmail App Password Settings](https://github.com/user-attachments/assets/d0b94fa5-6b76-42a2-b38e-36bbcf22dd59)

## 6. Additional Notes

- The script checks available 10bis credit and attempts to load the full eligible amount.
- A notification email is sent after each execution, indicating success, no available credit, or failure.
- Authentication cookies are stored separately for each 10bis account.
- If the session expires, manual OTP authentication may be required again.
- Successful submission of a credit-loading request does not necessarily confirm that the credit was applied. Verify the balance or transaction history when necessary.
- The script uses unofficial 10bis API endpoints, which may change without notice.
