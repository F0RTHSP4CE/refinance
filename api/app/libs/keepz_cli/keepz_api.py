from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import quote
from uuid import uuid4

import requests
from pydantic import BaseModel, Field, ValidationError

DEFAULT_BASE_URL = "https://gateway.keepz.me"
DEFAULT_USER_AGENT = "keepz/2 CFNetwork/3896.200.61 Darwin/27.2.0"
DEFAULT_APP_VERSION = "4.6.5"
DEFAULT_ACCEPT = "application/json, text/plain, */*"
DEFAULT_ACCEPT_LANGUAGE = "en-GB,en;q=0.9"


def generate_device_token() -> str:
    return f"e-{uuid4().hex[:20]}:APA91b{uuid4().hex}{uuid4().hex[:12]}"


class KeepzApiError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class KeepzBaseModel(BaseModel):
    model_config = {"extra": "allow"}


class JwtAccessTokenClaims(KeepzBaseModel):
    exp: int
    iat: int
    jti: str
    iss: str
    aud: str
    sub: str
    typ: str
    azp: str
    session_state: str
    allowed_origins: list[str] = Field(alias="allowed-origins")
    realm_access: Dict[str, Any]
    resource_access: Dict[str, Any]
    scope: str
    sid: str
    email_verified: bool
    database_id: Optional[str] = None
    preferred_username: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class JwtRefreshTokenClaims(KeepzBaseModel):
    iat: int
    jti: str
    iss: str
    aud: str
    sub: str
    typ: str
    azp: str
    session_state: str
    scope: str
    sid: str


class TokenBundle(KeepzBaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int = 0
    obtained_at: str
    user_id: Optional[str] = None

    @staticmethod
    def from_login_payload(
        payload: Dict[str, Any], user_id: Optional[str]
    ) -> "TokenBundle":
        access_token = payload["access_token"]
        claims = parse_access_claims(access_token)
        token_user_id = user_id or extract_user_id_from_database_id(claims.database_id)
        return TokenBundle(
            access_token=access_token,
            refresh_token=payload.get("refresh_token"),
            token_type=payload.get("token_type") or "Bearer",
            expires_in=int(payload.get("expires_in") or 0),
            obtained_at=datetime.now(timezone.utc).isoformat(),
            user_id=token_user_id,
        )

    def to_json(self) -> Dict[str, Any]:
        return self.model_dump()

    @staticmethod
    def from_json(data: Dict[str, Any]) -> "TokenBundle":
        return TokenBundle(**data)

    def is_access_token_expired(self, skew_seconds: int = 30) -> bool:
        try:
            claims = parse_access_claims(self.access_token)
            return datetime.now(timezone.utc).timestamp() > (claims.exp - skew_seconds)
        except KeepzApiError:
            if not self.obtained_at:
                return True
            try:
                obtained = datetime.fromisoformat(self.obtained_at)
            except ValueError:
                return True
            expiry = obtained.timestamp() + self.expires_in
            return datetime.now(timezone.utc).timestamp() > (expiry - skew_seconds)


class AuthUserPreview(KeepzBaseModel):
    name: Optional[str] = None
    image: Optional[str] = None
    hasPassword: Optional[bool] = None
    biometricEnabled: Optional[bool] = None
    passcodeSet: Optional[bool] = None


class AuthCheckResponse(KeepzBaseModel):
    individualExists: Optional[bool] = None
    businessExists: Optional[bool] = None
    individualUserPreview: Optional[AuthUserPreview] = None
    businessUserPreview: Optional[AuthUserPreview] = None
    phoneChangeRequired: Optional[bool] = None
    hasPassword: Optional[bool] = None


class LoginResponse(KeepzBaseModel):
    access_token: Optional[str] = None
    expires_in: Optional[int] = None
    refresh_expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None
    not_before_policy: Optional[int] = Field(default=None, alias="not-before-policy")
    session_state: Optional[str] = None
    scope: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class BrandingDto(KeepzBaseModel):
    headerColor: Optional[str] = None
    buttonColor: Optional[str] = None
    buttonTextColor: Optional[str] = None
    titleColor: Optional[str] = None


class ProfileDetails(KeepzBaseModel):
    userId: Optional[str] = None
    name: Optional[str] = None
    lastName: Optional[str] = None
    birthdate: Optional[str] = None
    personalNumber: Optional[str] = None
    email: Optional[str] = None
    phoneNumber: Optional[str] = None
    countryCode: Optional[str] = None
    imagePath: Optional[str] = None
    userType: Optional[str] = None
    verified: Optional[bool] = None
    verificationStatus: Optional[str] = None
    tcToBeAccepted: Optional[bool] = None
    qrCode: Optional[int] = None
    iban: Optional[str] = None
    currency: Optional[str] = None
    defaultQrUrl: Optional[str] = None
    showName: Optional[bool] = None
    emailIsVerified: Optional[bool] = None
    softPosAlreadyRequested: Optional[bool] = None
    passwordToBeSet: Optional[bool] = None
    passwordChangePermitted: Optional[bool] = None
    language: Optional[str] = None
    tppaySessionExpired: Optional[bool] = None
    isSuspended: Optional[bool] = None
    paymentForbiddenInApp: Optional[bool] = None
    passwordRequired: Optional[bool] = None
    passwordSet: Optional[bool] = None
    biometricEnabled: Optional[bool] = None
    passcodeSet: Optional[bool] = None


class ProfileTinyUrl(KeepzBaseModel):
    tinyURL: Optional[str] = None


class Iban(KeepzBaseModel):
    iban: Optional[str] = None
    ibanName: Optional[str] = None
    isDefault: Optional[bool] = None
    isMasterDefault: Optional[bool] = None
    id: Optional[int] = None
    status: Optional[str] = None
    accountNumberType: Optional[str] = None


class SystemStatus(KeepzBaseModel):
    systemStatus: Optional[str] = None
    message: Optional[str] = None
    expectationDate: Optional[str] = None


class ForceUpdate(KeepzBaseModel):
    iosVersion: Optional[str] = None
    androidVersion: Optional[str] = None


class MobileDevice(KeepzBaseModel):
    id: Optional[int] = None
    deviceToken: Optional[str] = None
    userId: Optional[str] = None


class SenderCommission(KeepzBaseModel):
    receiverCommission: Optional[float] = None
    senderCommission: Optional[float] = None
    startAmount: Optional[float] = None
    rateType: Optional[str] = None
    acquiringType: Optional[str] = None
    minAmountPerTransaction: Optional[float] = None
    maxAmountPerTransaction: Optional[float] = None
    currency: Optional[str] = None


class PlanLimit(KeepzBaseModel):
    dailyLimit: Optional[float] = None
    monthlyLimit: Optional[float] = None
    currency: Optional[str] = None


class PaymentLimit(PlanLimit):
    receivedAmount: Optional[float] = None
    receivedAmountDaily: Optional[float] = None
    rating: Optional[float] = None


class PlanDetails(KeepzBaseModel):
    groupId: Optional[int] = None
    groupName: Optional[str] = None
    commissions: Optional[list[SenderCommission]] = None
    limits: Optional[list[PlanLimit]] = None
    fee: Any = None


class Plan(KeepzBaseModel):
    currentPlanDetails: Optional[PlanDetails] = None
    targetPlanDetails: Optional[PlanDetails] = None
    targetPlans: Optional[list[PlanDetails]] = None


class UserBalance(KeepzBaseModel):
    currency: Optional[str] = None
    amount: Optional[float] = None


class UserBalanceConfig(KeepzBaseModel):
    enabled: Optional[bool] = None
    cashOutMode: Optional[str] = None


class AcquiringDetails(KeepzBaseModel):
    productList: Optional[list[Dict[str, Any]]] = None
    acquiringDetailsType: Optional[str] = None


class AcquiringProvider(KeepzBaseModel):
    id: Optional[int] = None
    acquiringType: Optional[str] = None
    acquiringName: Optional[str] = None
    priority: Optional[int] = None
    logo: Optional[str] = None
    providerId: Optional[int] = None
    applePayToken: Optional[str] = None
    googlePayToken: Optional[str] = None
    url: Optional[str] = None
    merchantId: Optional[str] = None
    isSubMerchant: Optional[bool] = None


class AcquiringChoice(KeepzBaseModel):
    availableAcquiringTypes: Optional[dict[str, list[AcquiringProvider]]] = None
    id: Optional[str] = None


class PaymentNote(KeepzBaseModel):
    field: Optional[str] = None
    fieldType: Optional[str] = None
    isEditable: Optional[bool] = None
    visibility: Optional[str] = None
    fieldNameEn: Optional[str] = None
    fieldNameKa: Optional[str] = None
    fieldNameIt: Optional[str] = None
    value: Optional[str] = None
    type: Optional[str] = None


class UserAccount(KeepzBaseModel):
    name: Optional[str] = None
    imagePath: Optional[str] = None
    senderCommissions: Optional[list[SenderCommission]] = None
    userType: Optional[str] = None
    descriptionRequired: Optional[bool] = None
    reviewRequired: Optional[bool] = None
    tipsEnabled: Optional[bool] = None
    commissionType: Optional[str] = None
    amountForDefaultQR: Optional[float] = None
    note: PaymentNote | str | None = None
    currency: Optional[str] = None
    currencyRate: Optional[float] = None
    userId: Optional[str] = None
    acquiringDetails: Optional[AcquiringDetails] = None
    showAwardedGiftComponent: Optional[bool] = None
    pointsToMoneyRate: Optional[float] = None
    acquiringCurrency: Optional[str] = None
    labels: Optional[Dict[str, Any]] = None
    softPosActivated: Optional[bool] = None
    posMerchantId: Optional[str] = None
    posTerminalId: Optional[str] = None
    posActivationCode: Optional[str] = None
    language: Optional[str] = None
    defaultQrUrl: Optional[str] = None
    showName: Optional[bool] = None
    possibleCurrencies: Optional[list[str]] = None
    initialCurrencies: Optional[list[str]] = None
    brandingDto: Optional[BrandingDto] = None
    isItalian: Optional[bool] = None


class AmountForDefault(KeepzBaseModel):
    defaultExists: Optional[bool] = None
    amountForDefaultQR: Optional[float] = None
    amountValidForSeconds: Optional[int] = None
    currency: Optional[str] = None
    softPosDefaultExists: Optional[bool] = None
    softPosAmountForDefaultQR: Optional[float] = None
    softPosAmountValidForSeconds: Optional[int] = None
    softPoscurrency: Optional[str] = None
    note: Optional[str] = None


class AmountForDefaultSet(KeepzBaseModel):
    amount: Optional[float] = None
    id: Optional[str] = None


class DefaultAmountCurrencies(KeepzBaseModel):
    currencies: Optional[list[str]] = None


class Transaction(KeepzBaseModel):
    id: Optional[int] = None
    uuid: Optional[str] = None
    amount: Optional[float] = None
    initialAmount: Optional[float] = None
    senderCommissionAmount: Optional[float] = None
    receiverCommissionAmount: Optional[float] = None
    receiverCashBackAmount: Optional[float] = None
    refundedAmount: Optional[float] = None
    currencyCode: Optional[str] = None
    recipientInfo: Optional[str] = None
    senderInfo: Optional[str] = None
    senderUserId: Optional[str] = None
    senderUserType: Optional[str] = None
    receiverUserId: Optional[str] = None
    receiverUserType: Optional[str] = None
    senderImagePath: Optional[str] = None
    receiverImagePath: Optional[str] = None
    status: Optional[str] = None
    transactionDate: Optional[str] = None
    secondParty: Optional[str] = None
    isReceived: Optional[bool] = None
    isSent: Optional[bool] = None
    senderBusinessName: Optional[str] = None
    recipientBusinessName: Optional[str] = None
    senderPersonalNumber: Optional[str] = None
    receiverPersonalNumber: Optional[str] = None
    description: Optional[str] = None
    acquiringTransactionType: Optional[str] = None
    canBeRefunded: Optional[bool] = None
    softposTransactionId: Optional[str] = None
    softposAcquiringAmount: Optional[float] = None
    softposCurrency: Optional[str] = None
    paymentMethod: Optional[str] = None
    note: Optional[str] = None
    receivedOnIban: Optional[str] = None
    cardMask: Optional[str] = None
    operationType: Optional[str] = None
    canBeSent: Optional[bool] = None


class PageableInfo(KeepzBaseModel):
    pageNumber: Optional[int] = None
    pageSize: Optional[int] = None
    sort: dict[str, Any] | list[Any] | None = None
    offset: Optional[int] = None
    paged: Optional[bool] = None
    unpaged: Optional[bool] = None


class Page(KeepzBaseModel):
    pageable: Optional[PageableInfo] = None
    totalPages: Optional[int] = None
    totalElements: Optional[int] = None
    last: Optional[bool] = None
    number: Optional[int] = None
    size: Optional[int] = None
    numberOfElements: Optional[int] = None
    sort: dict[str, Any] | list[Any] | None = None
    first: Optional[bool] = None
    empty: Optional[bool] = None


class TransactionsPage(Page):
    content: Optional[list[Transaction]] = None


class UserCard(KeepzBaseModel):
    id: Optional[int] = None
    cardMask: Optional[str] = None
    expirationDate: Optional[str] = None
    cardBrand: Optional[str] = None
    paymentProvider: Optional[str] = None


class UserCardsPage(Page):
    content: Optional[list[UserCard]] = None


class TransactionsResponse(KeepzBaseModel):
    transactionsPage: Optional[TransactionsPage] = None
    allTimeTotalAmount: Optional[float] = None
    todayTotalAmount: Optional[float] = None
    todayTotalInitialAmount: Optional[float] = None
    specificDatesTransactionAmountSum: Optional[float] = None
    currency: Optional[str] = None


def decode_jwt_payload(token: str) -> Dict[str, Any]:
    parts = token.split(".")
    if len(parts) < 2:
        raise KeepzApiError("Invalid JWT format")
    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    raw = base64.urlsafe_b64decode(payload + padding)
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise KeepzApiError("Invalid JWT payload") from exc


def parse_access_claims(token: str) -> JwtAccessTokenClaims:
    return JwtAccessTokenClaims.model_validate(decode_jwt_payload(token))


def parse_refresh_claims(token: str) -> JwtRefreshTokenClaims:
    return JwtRefreshTokenClaims.model_validate(decode_jwt_payload(token))


def extract_user_id_from_database_id(database_id: Optional[str]) -> Optional[str]:
    if not database_id:
        return None
    try:
        data = json.loads(database_id)
    except ValueError:
        return None
    return data.get("userId")


def _maybe_parse_response(model: type[KeepzBaseModel], data: Any) -> Any:
    if not isinstance(data, dict):
        return data
    try:
        return model.model_validate(data)
    except ValidationError:
        return data


def _maybe_parse_list_response(model: type[KeepzBaseModel], data: Any) -> Any:
    if isinstance(data, list):
        return [_maybe_parse_response(model, item) for item in data]
    return data


class KeepzClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "accept": DEFAULT_ACCEPT,
                "accept-language": DEFAULT_ACCEPT_LANGUAGE,
                "user-agent": user_agent,
            }
        )

    def set_access_token(self, access_token: str) -> None:
        self.session.headers["authorization"] = f"Bearer {access_token}"

    def clear_access_token(self) -> None:
        self.session.headers.pop("authorization", None)

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        expected_statuses: Optional[list[int]] = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        expected = expected_statuses or [200]
        resp = self.session.request(
            method,
            url,
            params=params,
            json=json_body,
            timeout=self.timeout,
        )
        if resp.status_code not in expected:
            raise KeepzApiError(
                f"Unexpected status {resp.status_code} for {method} {path}: {resp.text}",
                status_code=resp.status_code,
            )

        if resp.status_code == 204 or not resp.content:
            return None

        try:
            data = resp.json()
        except ValueError as exc:
            raise KeepzApiError(f"Invalid JSON response for {method} {path}") from exc

        if isinstance(data, dict):
            return data.get("value", data)
        return data

    def auth_check(self, phone: str, country_code: str) -> Any:
        payload = {
            "phone": f"{country_code}{phone}",
            "phoneNumberDetails": {"phoneNumber": phone, "countryCode": country_code},
        }
        data = self._request_json(
            "POST", "/common-service/api/v1/auth/check", json_body=payload
        )
        return _maybe_parse_response(AuthCheckResponse, data)

    def send_sms(self, phone: str, country_code: str, sms_type: str = "LOGIN") -> None:
        payload = {
            "phone": phone,
            "countryCode": country_code,
            "otphash": "",
            "smsType": sms_type,
            "phoneNumberDetails": {"phoneNumber": phone, "countryCode": country_code},
        }
        self._request_json(
            "POST",
            "/common-service/api/v1/auth/send-sms",
            json_body=payload,
            expected_statuses=[200],
        )

    def verify_sms(self, code: str, phone: str, country_code: str) -> str:
        payload = {"code": code, "countryCode": country_code, "phone": phone}
        return self._request_json(
            "POST",
            "/common-service/api/v1/auth/verify-sms",
            json_body=payload,
            expected_statuses=[202],
        )

    def login(
        self,
        user_sms_id: str,
        device_token: str,
        mobile_name: str,
        mobile_os: str,
        mobile_number: str,
        user_type: str,
        version: str = DEFAULT_APP_VERSION,
    ) -> Any:
        payload = {
            "deviceToken": device_token,
            "mobileName": mobile_name,
            "mobileOS": mobile_os,
            "mobileNumber": mobile_number,
            "userSMSId": user_sms_id,
            "userType": user_type,
            "version": version,
        }
        data = self._request_json(
            "POST", "/common-service/api/v1/auth/login", json_body=payload
        )
        return _maybe_parse_response(LoginResponse, data)

    def refresh_login(self, bundle: TokenBundle) -> TokenBundle:
        if not bundle.refresh_token:
            raise KeepzApiError("No refresh_token available for refresh")

        payload = {"refresh_token": bundle.refresh_token}
        data = self._request_json(
            "POST", "/common-service/api/v1/auth/refresh-login", json_body=payload
        )
        login_payload = _maybe_parse_response(LoginResponse, data)
        if isinstance(login_payload, BaseModel):
            payload_dict = login_payload.model_dump()
        else:
            payload_dict = login_payload

        refreshed = TokenBundle.from_login_payload(payload_dict, user_id=bundle.user_id)
        self.set_access_token(refreshed.access_token)
        return refreshed

    def unregister_device_auth(self, auth_method: str, device_token: str) -> None:
        self._request_json(
            "DELETE",
            "/common-service/api/v1/auth/device-auth/register",
            params={"authMethod": auth_method, "deviceToken": device_token},
            expected_statuses=[204],
        )

    def update_device_token(self, device_token: str) -> Any:
        data = self._request_json(
            "PUT",
            "/notification-service/api/v1/mobile-device/device_token",
            params={"device_token": device_token},
        )
        return _maybe_parse_response(MobileDevice, data)

    def logout(self) -> None:
        self._request_json("POST", "/common-service/api/v1/profile/logout")
        self.clear_access_token()

    def profile_details(self) -> Any:
        data = self._request_json("GET", "/common-service/api/v1/profile/details")
        return _maybe_parse_response(ProfileDetails, data)

    def profile_tiny_url(self) -> Any:
        data = self._request_json("GET", "/common-service/api/v1/profile/tiny-url")
        return _maybe_parse_response(ProfileTinyUrl, data)

    def list_ibans(self) -> Any:
        data = self._request_json("GET", "/common-service/api/v1/ibans")
        return _maybe_parse_list_response(Iban, data)

    def system_status(self) -> Any:
        data = self._request_json("GET", "/common-service/api/v1/system/status")
        return _maybe_parse_response(SystemStatus, data)

    def force_update(self) -> Any:
        data = self._request_json("GET", "/payment-service/api/force/update")
        return _maybe_parse_response(ForceUpdate, data)

    def user_account(self, user_id: str) -> Any:
        account_id = quote(str(user_id), safe="")
        data = self._request_json(
            "GET", f"/payment-service/api/v1/user-account/{account_id}"
        )
        return _maybe_parse_response(UserAccount, data)

    def get_plan(self) -> Any:
        data = self._request_json("GET", "/payment-service/api/v1/plan")
        return _maybe_parse_response(Plan, data)

    def list_limits(self) -> Any:
        data = self._request_json("GET", "/payment-service/api/limit")
        return _maybe_parse_list_response(PaymentLimit, data)

    def get_balance(self) -> Any:
        data = self._request_json("GET", "/payment-service/api/v1/user-balance")
        return _maybe_parse_list_response(UserBalance, data)

    def get_balance_config(self) -> Any:
        data = self._request_json("GET", "/payment-service/api/v1/user-balance/config")
        return _maybe_parse_response(UserBalanceConfig, data)

    def get_acquiring_choice(
        self, receiver_id: str, receiver_type: str = "USER"
    ) -> Any:
        data = self._request_json(
            "GET",
            "/payment-service/api/v1/acquiring/choice/",
            params={"receiverId": receiver_id, "receiverType": receiver_type},
        )
        return _maybe_parse_response(AcquiringChoice, data)

    def list_cards(self, page: int = 0, limit: int = 10) -> Any:
        data = self._request_json(
            "GET",
            "/payment-service/api/user-card",
            params={"page": page, "limit": limit},
        )
        return _maybe_parse_response(UserCardsPage, data)

    def list_recurring_consents(self) -> Any:
        return self._request_json(
            "GET", "/payment-service/api/v1/open-banking/transaction/recurring/consents"
        )

    def create_payment_link(
        self,
        amount: float,
        currency: str,
        commission_type: str = "SENDER",
        note: Optional[str] = None,
    ) -> str:
        params = {
            "amount": amount,
            "currency": currency,
            "commissionType": commission_type,
        }
        if note:
            params["note"] = note
        return self._request_json(
            "POST", "/payment-service/api/merchant/product", params=params
        )

    def list_transactions(
        self,
        page: int = 0,
        limit: int = 20,
        sent_or_received: str = "ALL",
        sender_info: str = "",
        recipient_info: str = "",
    ) -> Any:
        payload = {
            "sentOrReceived": sent_or_received,
        }
        if sender_info:
            payload["senderInfo"] = sender_info
        if recipient_info:
            payload["recipientInfo"] = recipient_info
        params = {"page": page, "limit": limit}
        data = self._request_json(
            "POST",
            "/payment-service/api/v1/generic-transaction/filter",
            params=params,
            json_body=payload,
        )
        return _maybe_parse_response(TransactionsResponse, data)

    def get_transaction(self, transaction_id: int) -> Any:
        data = self._request_json(
            "GET", f"/payment-service/api/v1/generic-transaction/{transaction_id}"
        )
        return _maybe_parse_response(Transaction, data)

    def set_default_amount(
        self, amount: float, currency: str, note: Optional[str] = None
    ) -> Any:
        payload = {"amount": amount, "currency": currency, "note": note}
        data = self._request_json(
            "POST", "/payment-service/api/v1/amount-for-default", json_body=payload
        )
        return _maybe_parse_response(AmountForDefaultSet, data)

    def delete_default_amount(self) -> None:
        self._request_json(
            "DELETE",
            "/payment-service/api/v1/amount-for-default",
            expected_statuses=[204],
        )

    def get_default_amount(self) -> Any:
        data = self._request_json("GET", "/payment-service/api/v1/amount-for-default")
        return _maybe_parse_response(AmountForDefault, data)

    def get_default_amount_currencies(self) -> Any:
        data = self._request_json(
            "GET", "/payment-service/api/v1/amount-for-default/currencies"
        )
        return _maybe_parse_response(DefaultAmountCurrencies, data)

    def resolve_payment_url(self, short_url: str, max_redirects: int = 5) -> str:
        resp = self.session.get(short_url, allow_redirects=True, timeout=self.timeout)
        if len(resp.history) > max_redirects:
            raise KeepzApiError("Redirect chain too long when resolving payment URL")
        return resp.url


def default_token_path() -> str:
    base_dir = os.path.join(os.path.expanduser("~"), ".config", "keepz")
    return os.path.join(base_dir, "credentials.json")


def load_tokens(path: Optional[str] = None) -> Optional[TokenBundle]:
    token_path = path or default_token_path()
    if not os.path.exists(token_path):
        return None
    with open(token_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return TokenBundle.from_json(data)


def save_tokens(bundle: TokenBundle, path: Optional[str] = None) -> str:
    token_path = path or default_token_path()
    os.makedirs(os.path.dirname(token_path), exist_ok=True)
    with open(token_path, "w", encoding="utf-8") as handle:
        json.dump(bundle.to_json(), handle, indent=2)
    return token_path
