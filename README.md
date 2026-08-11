# 10bis Credit Retrieval

Steps to run this script:

1. Open a terminal.
2. Go to the folder where the script lives:
   ```bash
   cd /home/user/path-with-script
   ```
3. Run the script once manually to create the session cookie:
   ```bash
   /usr/bin/python3 retrieve-10bis-credit.py
   ```
4. Follow the prompts and enter the OTP if the script asks for it.

After the first successful run, the script can run automatically with cron.

## Cron setup

Use this cron line to run every day at 07:00 and save the log:

```cron
0 7 * * SUN-THU cd /home/user/path-with-script && /usr/bin/python3 retrieve-10bis-credit.py >> /home/user/path-with-script/retrieve-10bis-credit.log 2>&1
```

## Notes

- The script stores session cookies locally, so it can reuse the login.
- We do not know how long the session will stay valid.
- If the saved session expires, run the script manually again and enter a new OTP.
- In case you are using gmail, create an "App password" for the email sender. Check the picture to understand where it's located in Google settings.
<img width="1582" height="916" alt="image" src="https://github.com/user-attachments/assets/d0b94fa5-6b76-42a2-b38e-36bbcf22dd59" />


