# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Override delle view SimpleJWT per agganciare:
#   - Logging sessioni utente (login/refresh) in dbops.sessioni_utente
#   - Throttling login per IP (LoginRateThrottle)
#   - Blocco per utente dopo tentativi falliti (fn_check_blocco_login,
#     fn_registra_tentativo_login)
# ------------------------------------------------------------

from __future__ import annotations

import logging

from django.contrib.auth.models import User
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.api.jwt_audit_authentication import set_jwt_gucs
from apps.core.api.multi_veste_token_serializer import (
    AdminTokenSerializer,
    PortaleTokenSerializer,
    ShopTokenSerializer,
    VesteNonAttivaError,
)
from apps.core.api.throttling import LoginRateThrottle
from apps.core.db.auth_repository import AuthRepository
from apps.core.services import session_audit_service
from apps.core.services.auth_constants import (
    JWT_CLAIM_EMITTENTE_ATTIVO_ID,
    JWT_CLAIM_IDENTITA_ID,
    JWT_CLAIM_RUOLO_APPLICATIVO,
    JWT_CLAIM_SID,
    RUOLO_APPLICATIVO_CLIENTE_PORTALE,
    RUOLO_APPLICATIVO_FORNITORE_PORTALE,
    RUOLO_APPLICATIVO_OPERATORE,
    RUOLO_APPLICATIVO_SHOP_CUSTOMER,
)


# Scopo: Decode non-verificato (payload-only) del refresh token.
# La firma/blacklist/exp sono gia' state validate da SimpleJWT a monte
# (super().post() del login o del refresh), quindi qui basta leggere
# il payload. Fail-open: dict vuoto se parse fallisce + log warning.
def _decode_refresh_payload(refresh_str: str | None) -> dict:
    if not refresh_str:
        return {}
    import jwt as pyjwt
    try:
        return pyjwt.decode(refresh_str, options={"verify_signature": False})
    except Exception:
        logger.warning(
            "security.refresh_decode_failed",
            exc_info=True,
        )
        return {}


# Scopo: Estrae il claim `identita_id` dal refresh token. Usato dai
# call site login/refresh per passare l'identita a set_jwt_gucs.
def _extract_identita_id_from_refresh(refresh_str: str | None) -> int | None:
    val = _decode_refresh_payload(refresh_str).get(JWT_CLAIM_IDENTITA_ID)
    return int(val) if val is not None else None


# Scopo: Estrae il claim `emittente_attivo_id` dal refresh token, per
# ripopolare la GUC durante il refresh (che non passa dalla DRF auth chain).
# Claim assente = modalita' «Tutti gli emittenti» → None, GUC vuota.
def _extract_emittente_attivo_from_refresh(refresh_str: str | None) -> int | None:
    val = _decode_refresh_payload(refresh_str).get(JWT_CLAIM_EMITTENTE_ATTIVO_ID)
    return int(val) if val is not None else None


# Scopo: Estrae il claim `ruolo_applicativo` dal refresh token.
# Usato dal guard cross-namespace di AuditTokenRefreshView per
# verificare che il refresh fatto su /admin/token/refresh/ abbia
# veste OPERATORE, /portale/token/refresh/ veste portale, ecc.
def _extract_ruolo_applicativo_from_refresh(refresh_str: str | None) -> str | None:
    val = _decode_refresh_payload(refresh_str).get(JWT_CLAIM_RUOLO_APPLICATIVO)
    return str(val) if val is not None else None

logger = logging.getLogger("security")
_auth_repo = AuthRepository()


class AuditTokenObtainPairView(TokenObtainPairView):
    """Classe base astratta: contract audit + throttle + blocco utente
    per il login JWT. NON va usata direttamente nelle rotte — solo tramite
    le 3 sottoclassi namespace (`AdminTokenView` / `PortaleTokenView` /
    `ShopTokenView`) che forniscono un `serializer_class` subclass di
    `MultiVesteTokenSerializer` con `allowed_ruoli_applicativi` settato.
    Senza quella subclass il JWT emesso sarebbe "senza veste"
    (claim `identita_id` + `ruolo_applicativo` assenti) e
    `JwtAuditAuthentication` (§8.3.4) non potrebbe popolare le GUC.

    Override di TokenObtainPairView con:
    - Throttle per IP (5 tentativi / 5 minuti)
    - Blocco per utente (DB: tentativi_falliti + bloccato_fino_a)
    - Audit login in dbops.sessioni_utente
    """

    throttle_classes = [LoginRateThrottle]
    # `serializer_class = None` + guard in post() rendono la base effettivamente
    # astratta: chiamare `AuditTokenObtainPairView.as_view()` direttamente
    # senza override di serializer_class solleva AssertionError subito.
    serializer_class = None  # type: ignore[assignment]

    @extend_schema(summary="Login JWT con audit e blocco utente", responses={200: dict})
    # Scopo: Esegue il login JWT con check blocco utente e registrazione tentativi.
    # Flusso: check blocco → verifica credenziali → registra esito → audit sessione.
    def post(self, request: Request, *args, **kwargs) -> Response:
        # Guard astratta: serializer_class deve essere MultiVesteTokenSerializer
        # (o subclass). Previene regressione silente: senza questa subclass
        # i claim JWT non conterrebbero identita_id/ruolo_applicativo e l'intero
        # flusso multi-face auth risulterebbe disallineato.
        from apps.core.api.multi_veste_token_serializer import (
            MultiVesteTokenSerializer,
        )
        assert self.serializer_class is not None and issubclass(
            self.serializer_class, MultiVesteTokenSerializer
        ), (
            "AuditTokenObtainPairView e' astratta: usa AdminTokenView / "
            "PortaleTokenView / ShopTokenView (o una nuova subclass con "
            "serializer_class subclass di MultiVesteTokenSerializer)."
        )

        username = request.data.get("username", "")
        user = self._find_user(username)

        # 1. Se utente esiste, verifica blocco (lancia errore DB se bloccato)
        if user:
            try:
                _auth_repo.check_blocco_login(user.id)
            except Exception as exc:
                # L'errore DB viene propagato al middleware che lo converte in JSON
                logger.warning("security.login_blocked user=%s", username)
                raise

        # 2. Tenta login (SimpleJWT)
        try:
            response = super().post(request, *args, **kwargs)
        except VesteNonAttivaError:
            # Credenziali corrette ma l'utente non ha la veste richiesta dal
            # namespace (es. operatore che tenta /portale/token/). Non e'
            # un tentativo fallito di credenziali: non incrementa
            # tentativi_falliti ne' attiva blocco utente/IP. Logga per audit
            # forense (qualcuno sta provando canali a cui non ha accesso).
            logger.warning("security.veste_non_attiva user=%s", username)
            raise
        except (AuthenticationFailed, InvalidToken):
            # Login fallito: registra tentativo
            if user:
                result = _auth_repo.registra_tentativo_login(user.id, successo=False)
                if result.get("bloccato"):
                    logger.warning(
                        "security.login_locked user=%s tentativi=%s blocco_minuti=%s",
                        username, result.get("tentativi"), result.get("minuti_rimanenti"),
                    )
            raise

        # 3. Login OK: reset contatore + audit sessione + check cambio password
        if response.status_code == 200:
            if user:
                _auth_repo.registra_tentativo_login(user.id, successo=True)

            user_id, jti = self._extract_claims(response)
            # §8.3.4: il MultiVesteTokenSerializer ha iniettato
            # `identita_id` nel refresh token; lo estraiamo subito perche'
            # serve sia al check `deve_cambiare_password` (§8.4.1 — puntato
            # alla veste specifica) sia alle GUC di audit.
            identita_id = _extract_identita_id_from_refresh(
                response.data.get("refresh") if response.data else None
            )

            # Check flag deve_cambiare_password sulla veste del JWT
            # appena emesso (non su una identita arbitraria dell'utente).
            if user and _auth_repo.get_deve_cambiare_password(
                user.id, identita_id=identita_id
            ):
                response.data["password_change_required"] = True

            # Hotfix BE-2.0ter: il login NON passa dalla DRF auth chain
            # (l'utente non e' ancora autenticato a authenticate() time),
            # quindi JwtAuditAuthentication NON setta le GUC. Le settiamo
            # qui manualmente, prima della scrittura di audit, cosi' i
            # trigger DB di sessioni_utente popolano user_insert con lo
            # username effettivo invece di 'zeroerp_app'. Il marker
            # _zeroerp_jwt_guc_set fa partire il reset simmetrico nel
            # JwtAuditMiddleware.process_response.
            if user and user_id:
                gucs_ok = set_jwt_gucs(
                    username=user.username,
                    user_id=user_id,
                    identita_id=identita_id,
                    request=request._request if hasattr(request, "_request") else request,
                )
                # Se identita_id e' None o l'identita risulta non attiva,
                # l'audit storico in record_login sara' scritto con GUC
                # vuote (user_insert='zeroerp_app'). Segnaliamo l'anomalia
                # — il JWT di un login appena emesso dovrebbe sempre avere
                # un identita_id valido. Assenza indica bug nel serializer
                # o race DB tra emissione JWT e record_login.
                if not gucs_ok:
                    logger.warning(
                        "security.login_guc_mancate user=%s identita_id=%s",
                        user.username, identita_id,
                    )
            session_audit_service.record_login(
                user_id=user_id,
                request=request._request if hasattr(request, "_request") else request,
                jti=jti,
            )

        return response

    @staticmethod
    # Scopo: Trova user Django per username (best-effort, non lancia errore).
    def _find_user(username: str) -> User | None:
        if not username:
            return None
        try:
            return User.objects.filter(username=username).first()
        except Exception:
            return None

    @staticmethod
    # Scopo: Estrae user_id e sid dal refresh token nella response (no query DB extra).
    def _extract_claims(response: Response) -> tuple[int, str | None]:
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh_str = response.data.get("refresh", "")
        if not refresh_str:
            return 0, None
        try:
            token = RefreshToken(refresh_str)
            return int(token.get("user_id", 0)), str(token.get(JWT_CLAIM_SID, ""))
        except Exception:
            return 0, None


class AdminTokenView(AuditTokenObtainPairView):
    """Login /api/v1/admin/token/ — solo operatori interni.

    Eredita audit + throttle + blocco utente da AuditTokenObtainPairView;
    cambia solo il serializer per esporre la veste OPERATORE.
    """

    serializer_class = AdminTokenSerializer


class PortaleTokenView(AuditTokenObtainPairView):
    """Login /api/v1/portale/token/ — clienti e fornitori portale B2B.

    Eredita lo stesso ciclo audit/throttle/blocco di AdminTokenView:
    il blocco login e' legato ad auth_user (non a identita), e un
    cliente/fornitore che sbaglia password piu' volte deve comunque
    essere bloccato. Cambia solo il serializer per esporre la veste
    CLIENTE_PORTALE | FORNITORE_PORTALE.
    """

    serializer_class = PortaleTokenSerializer


class ShopTokenView(AuditTokenObtainPairView):
    """Login /api/v1/shop/token/ — shop B2C self-service.

    Stesso ciclo audit/throttle/blocco di AdminTokenView; cambia solo
    il serializer per esporre la veste SHOP_CUSTOMER. Stub PR-B4:
    il flusso utente completo (registrazione self-service, attivazione)
    e' in PR-C.
    """

    serializer_class = ShopTokenSerializer


class AuditTokenRefreshView(TokenRefreshView):
    """Classe base astratta: contract audit + guard cross-namespace per
    il refresh JWT. NON va usata direttamente nelle rotte — solo tramite
    le 3 sottoclassi namespace (`AdminTokenRefreshView` /
    `PortaleTokenRefreshView` / `ShopTokenRefreshView`) che settano
    `expected_ruoli_applicativi`. Senza quella subclass non c'e' guard
    cross-namespace → potrebbe accettare refresh di token di vesti
    diverse dal path, rumore semantico. Consistenza con
    `AuditTokenObtainPairView` (§8.3.3 A1).

    Claim preservation: SimpleJWT con `ROTATE_REFRESH_TOKENS=True` ruota
    solo `jti/exp/iat`, mantenendo i claim custom (`identita_id`,
    `ruolo_applicativo`, `sid`) nel nuovo refresh emesso. Verificato
    manualmente; se in futuro SIMPLE_JWT cambia, aggiornare qui.
    """

    # Le 3 subclass override con il subset di ruoli del loro namespace.
    # `expected_ruoli_applicativi = ()` + guard in post() rendono la
    # base effettivamente astratta: chiamare as_view() direttamente
    # senza override solleva AssertionError.
    expected_ruoli_applicativi: tuple[str, ...] = ()

    @extend_schema(summary="Refresh JWT con audit sessione", responses={200: dict})
    # Scopo: Esegue il refresh JWT, valida la veste tramite il guard
    # cross-namespace e registra l'evento REFRESH in dbops.sessioni_utente.
    def post(self, request: Request, *args, **kwargs) -> Response:
        # Guard astratta: le subclass DEVONO settare expected_ruoli_applicativi.
        # Previene regressione silente in cui qualcuno usa la base class
        # in urls.py o in test dimenticando l'override: il refresh
        # funzionerebbe cross-namespace senza check.
        assert self.expected_ruoli_applicativi, (
            "AuditTokenRefreshView e' astratta: usa AdminTokenRefreshView / "
            "PortaleTokenRefreshView / ShopTokenRefreshView (o una nuova "
            "subclass con expected_ruoli_applicativi settato)."
        )

        # Guard cross-namespace: rifiuta il refresh di un token la cui
        # veste non rientra nel set ammesso dal namespace del path
        # (es. refresh portale su /admin/token/refresh/). Nessuna
        # escalation di privilegio — il claim veste viene dal token
        # firmato — ma chiude l'ambiguita' semantica cross-path.
        refresh_str = request.data.get("refresh")
        ruolo = _extract_ruolo_applicativo_from_refresh(refresh_str)
        if ruolo is None or ruolo not in self.expected_ruoli_applicativi:
            logger.warning(
                "security.refresh_cross_namespace path=%s ruolo=%s",
                request.path, ruolo,
            )
            raise VesteNonAttivaError()

        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            user_id, jti = self._extract_claims(request)
            # Hotfix BE-2.0ter: il refresh NON passa dalla DRF auth chain
            # (la request porta solo il refresh token nel body, niente
            # Authorization Bearer), quindi JwtAuditAuthentication NON
            # setta le GUC. Le settiamo qui manualmente prima della
            # scrittura di audit. Lo username viene risolto dal user_id
            # estratto dal claim del refresh token (gia' validato dal
            # parent SimpleJWT, quindi affidabile).
            if user_id:
                username = self._resolve_username(user_id)
                if username:
                    # §8.3.4: il refresh token (anche dopo rotation) preserva
                    # il claim identita_id iniettato al login. Lo estraiamo
                    # dal body della request per popolare le GUC sulla veste
                    # corretta — il refresh rotation produce un NUOVO refresh
                    # nella response, ma il claim identita_id e' gia'
                    # disponibile nel refresh in entrata (sufficiente per le GUC).
                    identita_id = _extract_identita_id_from_refresh(
                        request.data.get("refresh")
                    )
                    gucs_ok = set_jwt_gucs(
                        username=username,
                        user_id=user_id,
                        identita_id=identita_id,
                        # L'emittente attivo viaggia col refresh (rotation
                        # preserva i claim custom): senza, ogni refresh
                        # riporterebbe l'utente in modalita' globale a sua
                        # insaputa. La CTE ricontrolla che sia ancora attivo.
                        emittente_attivo_id=_extract_emittente_attivo_from_refresh(
                            request.data.get("refresh")
                        ),
                        request=request._request if hasattr(request, "_request") else request,
                    )
                    if not gucs_ok:
                        logger.warning(
                            "security.refresh_guc_mancate user_id=%s identita_id=%s",
                            user_id, identita_id,
                        )
            session_audit_service.record_refresh(
                user_id=user_id,
                request=request._request if hasattr(request, "_request") else request,
                jti=jti,
            )
        return response

    @staticmethod
    # Scopo: Risolve lo username da auth_user.id per la propagazione GUC.
    # Best-effort: ritorna None se l'utente non esiste o la query fallisce
    # (in quel caso le GUC non vengono settate, fail-open).
    def _resolve_username(user_id: int) -> str | None:
        try:
            user = User.objects.filter(pk=user_id).only("username").first()
        except Exception:
            return None
        return user.username if user else None

    @staticmethod
    # Scopo: Estrae user_id e sid dal refresh token nel body della request.
    # §8.3.9 fix audit REFRESH: NON usare `RefreshToken(refresh_str)` qui
    # — il super().post() poco sopra ha gia' blacklistato il refresh in
    # entrata (BLACKLIST_AFTER_ROTATION=True default), quindi SimpleJWT
    # solleverebbe TokenError e il catch generico restituirebbe (0, None),
    # facendo saltare set_jwt_gucs e scrivendo audit con
    # user_insert=zeroerp_app. Usiamo `pyjwt.decode` senza validazione
    # (identico pattern di `_decode_refresh_payload`): il refresh qui e'
    # gia' stato validato da SimpleJWT nel super().post(), ci servono
    # solo i claim per audit + GUC.
    def _extract_claims(request: Request) -> tuple[int, str | None]:
        refresh_str = request.data.get("refresh", "")
        if not refresh_str:
            return 0, None
        payload = _decode_refresh_payload(refresh_str)
        raw_user_id = payload.get("user_id")
        raw_sid = payload.get(JWT_CLAIM_SID)
        try:
            user_id = int(raw_user_id) if raw_user_id is not None else 0
        except (TypeError, ValueError):
            user_id = 0
        sid = str(raw_sid) if raw_sid is not None else None
        return user_id, sid


# ── Refresh view per namespace (§8.3.5) ─────────────────────
# Ogni namespace ha la sua view di refresh che restringe le vesti
# ammesse tramite `expected_ruoli_applicativi`. Impedisce il refresh
# di un token di un namespace attraverso il path di un altro
# (rumore semantico anche se non escalation).


class AdminTokenRefreshView(AuditTokenRefreshView):
    """Refresh /api/v1/admin/token/refresh/ — solo token di operatori."""

    expected_ruoli_applicativi = (RUOLO_APPLICATIVO_OPERATORE,)


class PortaleTokenRefreshView(AuditTokenRefreshView):
    """Refresh /api/v1/portale/token/refresh/ — solo token portale."""

    expected_ruoli_applicativi = (
        RUOLO_APPLICATIVO_CLIENTE_PORTALE,
        RUOLO_APPLICATIVO_FORNITORE_PORTALE,
    )


class ShopTokenRefreshView(AuditTokenRefreshView):
    """Refresh /api/v1/shop/token/refresh/ — solo token shop."""

    expected_ruoli_applicativi = (RUOLO_APPLICATIVO_SHOP_CUSTOMER,)
