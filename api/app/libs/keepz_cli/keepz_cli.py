from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, Optional

from keepz_api import (
    KeepzApiError,
    KeepzClient,
    TokenBundle,
    default_token_path,
    generate_device_token,
    load_tokens,
    parse_access_claims,
    parse_refresh_claims,
    save_tokens,
)
from pydantic import BaseModel


def _require_tokens(path: Optional[str]) -> TokenBundle:
    bundle = load_tokens(path)
    if not bundle:
        raise SystemExit("No saved credentials found. Run 'auth' first.")
    return bundle


def _as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return {"value": value}


def _print_transactions(transactions: Any) -> None:
    payload = _as_dict(transactions)
    page = payload.get("transactionsPage", {})
    items = page.get("content", [])
    if not items:
        print("No transactions found.")
        return

    for tx in items:
        line = (
            f"{tx.get('id')} | {tx.get('amount')} {tx.get('currencyCode')} | "
            f"{tx.get('status')} | {tx.get('transactionDate')} | "
            f"{tx.get('acquiringTransactionType')} | note={tx.get('note') or '-'}"
        )
        print(line)


def cmd_auth(args: argparse.Namespace) -> None:
    client = KeepzClient(base_url=args.base_url)

    phone = args.phone
    country_code = args.country_code

    check = client.auth_check(phone=phone, country_code=country_code)
    print(json.dumps(_as_dict(check), indent=2))

    client.send_sms(phone=phone, country_code=country_code)
    code = args.sms_code or input("SMS code: ").strip()

    user_sms_id = client.verify_sms(code=code, phone=phone, country_code=country_code)
    device_token = args.device_token or generate_device_token()
    login_payload = client.login(
        user_sms_id=user_sms_id,
        device_token=device_token,
        mobile_name=args.mobile_name,
        mobile_os=args.mobile_os,
        mobile_number=f"{country_code}{phone}",
        user_type=args.user_type,
    )

    if isinstance(login_payload, BaseModel):
        access_token = login_payload.access_token
    else:
        access_token = login_payload.get("access_token")
    if not access_token:
        raise SystemExit("Login response missing access_token.")

    client.set_access_token(access_token)
    profile = client.profile_details()
    user_id = _as_dict(profile).get("userId")

    login_payload_dict = _as_dict(login_payload)
    bundle = TokenBundle.from_login_payload(login_payload_dict, user_id=user_id)
    token_path = save_tokens(bundle, args.token_path)
    print(f"Saved credentials to {token_path}.")


def cmd_create_payment(args: argparse.Namespace) -> None:
    bundle = _require_tokens(args.token_path)
    client = KeepzClient(base_url=args.base_url)
    client.set_access_token(bundle.access_token)

    short_url = client.create_payment_link(
        amount=args.amount,
        currency=args.currency,
        commission_type=args.commission_type,
        note=args.note,
    )
    print(f"Payment link: {short_url}")

    if args.resolve:
        final_url = client.resolve_payment_url(short_url)
        print(f"QR URL: {final_url}")


def cmd_list_payments(args: argparse.Namespace) -> None:
    bundle = _require_tokens(args.token_path)
    client = KeepzClient(base_url=args.base_url)
    client.set_access_token(bundle.access_token)

    transactions = client.list_transactions(
        page=args.page,
        limit=args.limit,
        sent_or_received=args.sent_or_received,
        sender_info=args.sender_info,
        recipient_info=args.recipient_info,
    )
    _print_transactions(transactions)


def cmd_get_payment(args: argparse.Namespace) -> None:
    bundle = _require_tokens(args.token_path)
    client = KeepzClient(base_url=args.base_url)
    client.set_access_token(bundle.access_token)

    transaction = client.get_transaction(args.transaction_id)
    print(json.dumps(_as_dict(transaction), indent=2))


def cmd_refresh_token(args: argparse.Namespace) -> None:
    bundle = _require_tokens(args.token_path)
    client = KeepzClient(base_url=args.base_url)

    refreshed = client.refresh_login(bundle)
    token_path = save_tokens(refreshed, args.token_path)
    print(f"Refreshed credentials saved to {token_path}.")


def cmd_show_token_info(args: argparse.Namespace) -> None:
    bundle = _require_tokens(args.token_path)
    payload: Dict[str, Any] = {"access": None, "refresh": None}

    try:
        access_claims = parse_access_claims(bundle.access_token)
        payload["access"] = access_claims.model_dump()
    except KeepzApiError as exc:
        payload["access"] = {"error": str(exc)}

    if bundle.refresh_token:
        try:
            refresh_claims = parse_refresh_claims(bundle.refresh_token)
            payload["refresh"] = refresh_claims.model_dump()
        except KeepzApiError as exc:
            payload["refresh"] = {"error": str(exc)}

    payload["obtained_at"] = bundle.obtained_at
    payload["expires_in"] = bundle.expires_in
    payload["token_type"] = bundle.token_type
    payload["user_id"] = bundle.user_id

    print(json.dumps(payload, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="keepz-cli")
    parser.add_argument("--base-url", default="https://gateway.keepz.me")
    parser.add_argument("--token-path", default=default_token_path())

    subparsers = parser.add_subparsers(dest="command", required=True)

    auth = subparsers.add_parser("auth", help="Authenticate via SMS")
    auth.add_argument("--phone", required=True)
    auth.add_argument("--country-code", required=True)
    auth.add_argument("--sms-code")
    auth.add_argument(
        "--device-token",
        default=generate_device_token(),
    )
    auth.add_argument("--mobile-name", default="iPhone 12 mini")
    auth.add_argument("--mobile-os", default="IOS")
    auth.add_argument("--user-type", default="INDIVIDUAL")
    auth.set_defaults(func=cmd_auth)

    create = subparsers.add_parser("create-payment", help="Create a payment link")
    create.add_argument("--amount", type=float, required=True)
    create.add_argument("--currency", default="GEL")
    create.add_argument("--commission-type", default="SENDER")
    create.add_argument("--note")
    create.add_argument("--resolve", action="store_true")
    create.set_defaults(func=cmd_create_payment)

    list_cmd = subparsers.add_parser("list-payments", help="List payment transactions")
    list_cmd.add_argument("--page", type=int, default=0)
    list_cmd.add_argument("--limit", type=int, default=20)
    list_cmd.add_argument("--sent-or-received", default="ALL")
    list_cmd.add_argument("--sender-info", default="")
    list_cmd.add_argument("--recipient-info", default="")
    list_cmd.set_defaults(func=cmd_list_payments)

    get_cmd = subparsers.add_parser("get-payment", help="Get payment details by id")
    get_cmd.add_argument("transaction_id", type=int)
    get_cmd.set_defaults(func=cmd_get_payment)

    refresh_cmd = subparsers.add_parser("refresh-token", help="Refresh access token")
    refresh_cmd.set_defaults(func=cmd_refresh_token)

    info_cmd = subparsers.add_parser(
        "show-token-info",
        help="Print access/refresh token claims from saved credentials",
    )
    info_cmd.set_defaults(func=cmd_show_token_info)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        raise SystemExit(130)


if __name__ == "__main__":
    main()
