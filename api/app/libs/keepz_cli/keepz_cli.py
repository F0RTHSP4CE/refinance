from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, Dict, Optional

from keepz_api import (
    DEFAULT_APP_VERSION,
    DEFAULT_BASE_URL,
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


def _authenticated_client(args: argparse.Namespace) -> KeepzClient:
    bundle = _require_tokens(args.token_path)
    client = KeepzClient(base_url=args.base_url)
    client.set_access_token(bundle.access_token)
    return client


def _as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return {"value": value}


def _print_transactions(transactions: Any) -> None:
    payload = _as_dict(transactions)
    page = payload.get("transactionsPage") or {}
    items = page.get("content") or []
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
        version=args.app_version,
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
    client = _authenticated_client(args)

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
    client = _authenticated_client(args)

    transactions = client.list_transactions(
        page=args.page,
        limit=args.limit,
        sent_or_received=args.sent_or_received,
        sender_info=args.sender_info,
        recipient_info=args.recipient_info,
    )
    _print_transactions(transactions)


def cmd_get_payment(args: argparse.Namespace) -> None:
    client = _authenticated_client(args)

    transaction = client.get_transaction(args.transaction_id)
    print(json.dumps(_as_dict(transaction), indent=2))


def cmd_refresh_token(args: argparse.Namespace) -> None:
    bundle = _require_tokens(args.token_path)
    client = KeepzClient(base_url=args.base_url)

    refreshed = client.refresh_login(bundle)
    token_path = save_tokens(refreshed, args.token_path)
    print(f"Refreshed credentials saved to {token_path}.")


def cmd_logout(args: argparse.Namespace) -> None:
    client = _authenticated_client(args)
    client.logout()
    Path(args.token_path).unlink(missing_ok=True)
    print("Logged out and removed saved credentials.")


def _dump_model(value: BaseModel) -> dict[str, Any]:
    return value.model_dump(mode="json", by_alias=True, exclude_unset=True)


def _run_api_command(args: argparse.Namespace) -> None:
    if args.authenticated:
        client = _authenticated_client(args)
    else:
        client = KeepzClient(base_url=args.base_url)
    kwargs = {name: getattr(args, name) for name in args.api_arguments}
    result = args.api_method(client, **kwargs)
    print(json.dumps(result, default=_dump_model, ensure_ascii=False, indent=2))


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
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
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
    auth.add_argument(
        "--app-version", default=DEFAULT_APP_VERSION, help="Keepz app version"
    )
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

    def add_api_command(
        name: str,
        help_text: str,
        method: Callable[..., Any],
        *arguments: str,
        authenticated: bool = True,
    ) -> argparse.ArgumentParser:
        command = subparsers.add_parser(name, help=help_text)
        command.set_defaults(
            func=_run_api_command,
            api_method=method,
            api_arguments=arguments,
            authenticated=authenticated,
        )
        return command

    add_api_command("profile", "Show profile details", KeepzClient.profile_details)
    add_api_command(
        "profile-tiny-url", "Get the profile short URL", KeepzClient.profile_tiny_url
    )
    add_api_command("list-ibans", "List saved IBANs", KeepzClient.list_ibans)
    add_api_command(
        "system-status", "Check Keepz system status", KeepzClient.system_status
    )
    add_api_command(
        "force-update",
        "Check minimum app versions",
        KeepzClient.force_update,
        authenticated=False,
    )

    account = add_api_command(
        "user-account",
        "Show a user's payment account",
        KeepzClient.user_account,
        "user_id",
    )
    account.add_argument("user_id", help="Keepz user ID")

    add_api_command("plan", "Show the current payment plan", KeepzClient.get_plan)
    add_api_command(
        "list-limits", "List payment limits by currency", KeepzClient.list_limits
    )
    add_api_command("balance", "Show balances by currency", KeepzClient.get_balance)
    add_api_command(
        "balance-config", "Show balance settings", KeepzClient.get_balance_config
    )

    acquiring = add_api_command(
        "acquiring-choice",
        "List payment options for a receiver",
        KeepzClient.get_acquiring_choice,
        "receiver_id",
        "receiver_type",
    )
    acquiring.add_argument("receiver_id", help="Keepz receiver ID")
    acquiring.add_argument("--receiver-type", default="USER")

    cards = add_api_command(
        "list-cards",
        "List saved payment cards",
        KeepzClient.list_cards,
        "page",
        "limit",
    )
    cards.add_argument("--page", type=int, default=0)
    cards.add_argument("--limit", type=int, default=10)
    add_api_command(
        "list-recurring-consents",
        "List recurring open-banking consents",
        KeepzClient.list_recurring_consents,
    )

    add_api_command(
        "get-default-amount",
        "Show the default QR amount",
        KeepzClient.get_default_amount,
    )
    set_amount = add_api_command(
        "set-default-amount",
        "Set the default QR amount",
        KeepzClient.set_default_amount,
        "amount",
        "currency",
        "note",
    )
    set_amount.add_argument("--amount", type=float, required=True)
    set_amount.add_argument("--currency", default="GEL")
    set_amount.add_argument("--note")
    add_api_command(
        "delete-default-amount",
        "Clear the default QR amount",
        KeepzClient.delete_default_amount,
    )
    add_api_command(
        "default-amount-currencies",
        "List currencies for the default QR amount",
        KeepzClient.get_default_amount_currencies,
    )

    device = add_api_command(
        "update-device-token",
        "Update a mobile push token",
        KeepzClient.update_device_token,
        "device_token",
    )
    device.add_argument("--device-token", required=True)

    device_auth = add_api_command(
        "unregister-device-auth",
        "Remove a device authentication method",
        KeepzClient.unregister_device_auth,
        "auth_method",
        "device_token",
    )
    device_auth.add_argument(
        "--auth-method", required=True, choices=("BIOMETRIC", "PASSCODE")
    )
    device_auth.add_argument("--device-token", required=True)

    logout = subparsers.add_parser(
        "logout", help="Log out and remove saved credentials"
    )
    logout.set_defaults(func=cmd_logout)

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
