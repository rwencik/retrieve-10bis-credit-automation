import argparse
import logging
import requests
import smtplib
import os
import pickle
import re
import traceback
from pathlib import Path
from email.message import EmailMessage

BASE_DIR = Path(__file__).resolve().parent
COOKIES_DIR = BASE_DIR / "cookies"

EMAIL_ADDRESS = "<your-email>"
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '<email-password>')
REQUEST_TIMEOUT = 30

BASE_HEADERS = {
    "x-app-type": "web",
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json",
    "Origin": "https://www.10bis.co.il",
}

logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(
            BASE_DIR / "10bis_charger.log", encoding="utf-8"
        ),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("10bis_charger")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Retrieve 10bis credit for a specific account"
    )
    parser.add_argument(
        "--email",
        required=True,
        help="10bis account email",
    )
    parser.add_argument(
        "--notify-email",
        default="<your email to receive notification>",
        help="Notification recipient",
    )
    return parser.parse_args()


def get_cookie_path(email):
    email = email.strip().lower()

    if not re.fullmatch(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+", email):
        raise ValueError("Invalid account email")

    account_dir = COOKIES_DIR / email
    account_dir.mkdir(parents=True, exist_ok=True)
    account_dir.chmod(0o700)

    return account_dir / "cookie.pkl"


def save_cookies(session, cookie_path):
    temp_path = cookie_path.with_suffix(".tmp")

    with open(temp_path, "wb") as f:
        os.chmod(temp_path, 0o600)
        pickle.dump(session.cookies, f)

    os.replace(temp_path, cookie_path)
    logger.info("Cookies saved for %s", cookie_path.parent.name)


def load_cookies(session, cookie_path):
    with open(cookie_path, "rb") as f:
        session.cookies.update(pickle.load(f))

    logger.info("Cookies loaded for %s", cookie_path.parent.name)


def send(body, recipient, subject="10bis Charger Alert"):
    if not EMAIL_PASSWORD:
        logger.error("EMAIL_PASSWORD is not configured")
        return

    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = recipient

    try:
        with smtplib.SMTP_SSL(
            "smtp.gmail.com", 465, timeout=30
        ) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)

        logger.info("Notification email sent to %s", recipient)

    except Exception:
        logger.exception("FAILED TO SEND NOTIFICATION EMAIL")



def login_flow(session, email):
    logger.info("Starting login flow for %s", email)

    url = (
        "https://www.10bis.co.il/NextApi/"
        "GetUserAuthenticationDataAndSendAuthenticationCodeToUser"
    )

    payload = {
        "culture": "he-IL",
        "uiCulture": "he",
        "email": email,
    }

    response = session.post(
        url,
        headers=BASE_HEADERS,
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("Success"):
        raise RuntimeError(
            f"Login failed: HTTP {response.status_code}"
        )

    auth_data = data["Data"]["codeAuthenticationData"]

    return (
        data["ShoppingCartGuid"],
        auth_data["authenticationToken"],
    )


def generate_token(
    session, auth_code, auth_token,
    shopping_guid, email, cookie_path
):
    logger.info("Generating token for %s", email)

    url = "https://www.10bis.co.il/NextApi/GetUserV2"

    payload = {
        "shoppingCartGuid": shopping_guid,

        "culture": "he-IL",
        "uiCulture": "he",
        "email": email,
        "authenticationToken": auth_token,
        "authenticationCode": auth_code,
    }

    response = session.post(
        url,
        headers=BASE_HEADERS,
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    data = response.json()

    if not data.get("Success"):
        raise RuntimeError("Token generation failed")

    session_token = data["Data"]["sessionToken"]

    logger.info("Session token generated successfully")

    save_cookies(session, cookie_path)

    return session_token


def refresh_token(session, cookie_path):
    logger.info("Refreshing token")


    url = (
        "https://api.10bis.co.il/api/v1/"
        "Authentication/RefreshToken"
    )

    response = session.post(
        url,
        headers=BASE_HEADERS,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    save_cookies(session, cookie_path)

    logger.info("Token refreshed successfully")


def get_credit_cards(session):
    logger.info("Resolving credit card list")

    url = "https://www.10bis.co.il/NextApi/UserTransactionsReport"

    payload = {
        "culture": "he-IL",
        "uiCulture": "he",
        "dateBias": "0",
    }

    response = session.post(
        url,
        headers=BASE_HEADERS,
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()
    data = response.json()

    if not data.get("Success"):
        raise RuntimeError(
            "UserTransactionsReport returned failure"
        )

    moneycards = data.get("Data", {}).get("moneycards", [])

    for credit_card in moneycards:
        card_id = credit_card["moneycardId"]

        logger.info("Checking card #%s", card_id)

        conversion = credit_card.get(
            "tenbisCreditConversion", {}
        )

        if conversion.get("isEnabled"):
            amount = conversion.get("availableAmount", 0)

            if amount > 0:
                logger.info(
                    "Card %s can be charged in ₪%s",
                    card_id, amount
                )
                return card_id, amount

    logger.info("No eligible chargeable amount found")
    return None, 0


def card_charge(session, card_id, amount):
    logger.info(
        "Charging card_id #%s with ₪%s",
        card_id, amount
    )

    url = (
        "https://api.10bis.co.il/api/v1/"
        "Payments/LoadTenbisCredit"
    )

    options_headers = {
        "Host": "api.10bis.co.il",
        "Connection": "keep-alive",
        "Accept": "*/*",
        "Access-Control-Request-Method": "PATCH",
        "Access-Control-Request-Headers":
            "content-type,language,x-app-type",
        "Origin": "https://www.10bis.co.il",
        "User-Agent": "Mozilla/5.0",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Dest": "empty",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en,he;q=0.9,en-US;q=0.8",
    }

    options_response = session.options(
        url,
        headers=options_headers,
        timeout=REQUEST_TIMEOUT,
    )
    options_response.raise_for_status()

    patch_headers = {
        **BASE_HEADERS,
        "language": "he",
    }

    payload = {
        "amount": amount,
        "moneycardIdToCharge": card_id,
    }

    response = session.patch(
        url,
        headers=patch_headers,
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    logger.info("Charge request successful")

    return (
        f"Successfully submitted charge of ₪{amount} "
        f"to card #{card_id}"
    )


def main(args):
    email = args.email.strip().lower()
    cookie_path = get_cookie_path(email)

    logger.info("Processing 10bis account: %s", email)

    with requests.Session() as session:

        if cookie_path.exists():
            load_cookies(session, cookie_path)

            try:
                refresh_token(session, cookie_path)

            except requests.RequestException as e:
                raise RuntimeError(
                    f"Token refresh failed for {email}. "
                    "Cookies may have expired. "
                    "Run the script interactively after "
                    "removing this account's cookie file."
                ) from e

        else:
            logger.info("No saved cookies for %s", email)

            if not os.isatty(0):
                raise RuntimeError(
                    f"No cookies for {email}. "
                    "Run interactively to authenticate first."
                )

            shopping_guid, token = login_flow(
                session, email
            )

            code = input("Insert SMS verification code:\n")

            generate_token(
                session,
                code,
                token,
                shopping_guid,
                email,
                cookie_path,
            )

        card_id, available_amount = get_credit_cards(
            session
        )

        if card_id is not None and available_amount > 0:
            return card_charge(
                session, card_id, available_amount
            )

        return "No chargeable amount found"


if __name__ == "__main__":
    args = parse_args()

    try:
        result = main(args)

        logger.info("[%s] %s", args.email, result)

        send(
            f"Account: {args.email}\n\n{result}",
            args.notify_email,
            subject=f"10bis Charger - SUCCESS - {args.email}",
        )

    except Exception as e:
        logger.exception(
            "10bis charger failed for %s", args.email
        )

        error_message = (
            f"10bis charger FAILED.\n"
            f"Account: {args.email}\n\n"
            f"Error type: {type(e).__name__}\n"
            f"Error: {e}\n\n"
            f"Traceback:\n{traceback.format_exc()}"
        )

        send(
            error_message,
            args.notify_email,
            subject=f"10bis Charger - FAILED - {args.email}",
        )

        raise SystemExit(1)
