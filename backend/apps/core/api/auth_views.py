# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Override delle view SimpleJWT per agganciare:
#   - Logging sessioni utente (login/refresh) in dbops.sessioni_utente
#   - Throttling login per IP (LoginRateThrottle)
#   - Freno sui tentativi falliti per credenziale + provenienza, attesa
#     crescente e blocco dell'admin (fn_check_blocco_login,
#     fn_registra_tentativo_login — config.credenziali); per un nome che non
#     trova una credenziale, lo stesso freno sul nome tentato (R-7)
# ------------------------------------------------------------

from __future__ import annotations

import logging

from django.contrib.auth.models import User, update_last_login
from django.db import DatabaseError
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.fields import empty
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings as simplejwt_settings
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.api.jwt_audit_authentication import set_jwt_gucs
from apps.core.api.refresh_cookie import (
    claims_refresh_firmati,
    leggi_refresh_cookie,
    richiedi_header_anti_csrf,
    sposta_refresh_nel_cookie,
)
from apps.core.api.multi_veste_token_serializer import (
    AdminTokenSerializer,
    MultiVesteTokenSerializer,
    PortaleTokenSerializer,
    ShopTokenSerializer,
    VesteNonAttivaError,
)
from apps.core.api.throttling import LoginRateThrottle
from apps.core.db.auth_repository import AuthRepository
from apps.core.db.secondo_fattore_repository import STATO_DEVICE_ATTIVO, SecondoFattoreRepository
from apps.core.services import session_audit_service
from apps.core.services.db_error_fields import structured_db_error_code
from apps.core.services.nome_tentato import digest_nome_tentato, etichetta_log
from apps.core.services.request_context import provenienza_obbligatoria, richiesta_django
from apps.core.services.revoca_token import blocca_token_sessioni
from apps.core.services.service_errors import ServiceError
from apps.core.services.sfida_secondo_fattore import DURATA_SFIDA_SECONDI, Sfida, emetti_sfida
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
# ⚠️ Solo per il LOGIN: il refresh e' quello appena emesso da SimpleJWT in
# questa stessa richiesta, quindi e' nostro per costruzione. Il REFRESH
# presentato dal browser non passa di qui: ha i claim con la firma
# verificata (`claims_refresh_firmati`), e una seconda lettura alla cieca
# dello stesso token sarebbe una seconda regola (dal 2026-09-28).
# Fail-open: dict vuoto se parse fallisce + log warning.
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


# Scopo: Un claim intero dei claim dati, None se assente o non intero.
#        Una regola per `identita_id`, `emittente_attivo_id` e `user_id`, di
#        login e refresh: fino al 2026-09-28 erano tre conversioni scritte a
#        mano, e solo una sopravviveva a un valore non intero.
def _int_claim(claims: dict, nome: str) -> int | None:
    val = claims.get(nome)
    try:
        return int(val) if val is not None else None
    except (TypeError, ValueError):
        return None


# Scopo: Estrae il claim `identita_id` dal refresh appena emesso al login,
# per passare l'identita a set_jwt_gucs.
def _extract_identita_id_from_refresh(refresh_str: str | None) -> int | None:
    return _int_claim(_decode_refresh_payload(refresh_str), JWT_CLAIM_IDENTITA_ID)


logger = logging.getLogger("security")
_auth_repo = AuthRepository()
_secondo_fattore_repo = SecondoFattoreRepository()


# Scopo: La veste del refresh presentato e' ancora UTILIZZABILE? Chiede la
#        veste `identita_id` legata alla credenziale `user_id` (dai claim
#        verificati) al repository, che la fa decidere al building block DB
#        `script.fn_veste_utilizzabile` (accesa, nelle sue date, rapporto per
#        l'operatore: brief-db-veste-utilizzabile). Claim assente (None) =
#        False: ogni refresh nostro lo porta (`emetti_refresh_veste`), come gia'
#        il claim `ruolo_applicativo`.
#        La stessa regola la chiede `set_jwt_gucs` a ogni richiesta: una
#        condizione nuova sulla veste si scrive nel building block, non qui.
#
# ⛔ D-5 (Tid, 2026-10-02): spegnere una veste (o farla uscire dalle sue
#    date) chiude le sue sessioni al primo rinnovo, QUALUNQUE sia la strada
#    che l'ha spenta — interruttore
#    «Accesso attivo», «Disabilita», portale, shop, e le strade che verranno.
#    Fino a quel giorno il controllo stava solo in `set_jwt_gucs`, DOPO la
#    rotazione, e un esito negativo era un warning: il refresh ruotava per
#    sempre una sessione che non poteva piu' fare nulla. La regola sta qui,
#    in un posto solo; la blacklist dei singoli comandi e' la chiusura
#    IMMEDIATA, non la regola.
# ⚠️ Un guasto della lettura PROPAGA (500): non e' una prova che la veste sia
#    utilizzabile, e il refresh non si concede su un dubbio.
def _veste_utilizzabile(identita_id: int | None, user_id: int | None) -> bool:
    if identita_id is None or not user_id:
        return False
    return _auth_repo.get_veste_utilizzabile(identita_id, user_id) is not None



# Scopo: Chiude un accesso RIUSCITO, cioe' una sessione appena emessa per
#        `user` nella veste `identita_id`: il successo sul freno (della sola
#        coppia credenziale + provenienza), l'ultimo accesso, le GUC per i
#        trigger di audit, la riga LOGIN in `dbops.sessioni_utente`.
#        Restituisce se la credenziale deve cambiare la password.
#        ⭐ Due chiamanti (regola del 2, 2026-10-01): il login senza secondo
#        fattore e il secondo passo (`secondo_fattore_token_views`). Con il
#        secondo fattore attivo la password giusta NON chiude l'accesso: lo
#        chiude il codice (§9.5.3 del brief DB) — altrimenti la password
#        azzererebbe i tentativi del codice.
#        `dettaglio` finisce nella riga LOGIN (es. con quale secondo fattore).
def chiudi_accesso_riuscito(
    *,
    user: User,
    digest: bytes,
    provenienza: str,
    identita_id: int | None,
    sid: str | None,
    django_request,
    dettaglio: dict | None = None,
) -> bool:
    _auth_repo.registra_tentativo_login(
        user.id, nome_digest=digest, provenienza=provenienza, successo=True,
    )
    # Ultimo accesso (D-8): della credenziale, a ogni accesso riuscito. Qui e
    # non con `UPDATE_LAST_LOGIN` di SimpleJWT: quello lo scrive nel
    # serializer PRIMA del controllo della veste, cioe' anche per chi ha la
    # password giusta e nessun accesso a questa porta (E_VESTE_NON_ATTIVA) —
    # e, col secondo fattore, prima del codice.
    # Lo stub vuole il `sender` del segnale; il ricevitore non lo usa e
    # SimpleJWT stesso passa None.
    update_last_login(None, user)  # type: ignore[arg-type]

    # Il login NON passa dalla DRF auth chain (l'utente non e' ancora
    # autenticato a authenticate() time), quindi JwtAuditAuthentication NON
    # setta le GUC: le si setta qui, prima della scrittura di audit, cosi' i
    # trigger DB di sessioni_utente popolano user_insert con lo username
    # effettivo invece di 'zeroerp_app'. Il marker _zeroerp_jwt_guc_set fa
    # partire il reset nel JwtAuditMiddleware.
    gucs_ok = set_jwt_gucs(
        username=user.username,
        user_id=user.id,
        identita_id=identita_id,
        request=django_request,
    )
    # Una sessione appena emessa ha sempre un identita_id valido: l'assenza
    # indica un bug nel serializer o una veste spenta in mezzo. L'audit
    # resta scritto, con GUC vuote (user_insert='zeroerp_app').
    if not gucs_ok:
        logger.warning(
            "security.login_guc_mancate user=%s identita_id=%s",
            user.username, identita_id,
        )
    session_audit_service.record_login(
        user_id=user.id,
        request=django_request,
        jti=sid,
        dettaglio=dettaglio,
    )
    # Cambio password obbligatorio: e' della CREDENZIALE (D-7), vale per
    # qualunque porta si stia usando.
    return _auth_repo.get_deve_cambiare_password(user.id)


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
    - Throttle per IP (5 richieste / 5 minuti): contro chi INONDA l'endpoint,
      qualunque credenziale provi
    - Stato della credenziale (DB, config.credenziali): contro chi PROVA una
      credenziale — freno sulla coppia credenziale + provenienza, attesa
      crescente oltre un tetto, blocco dell'admin. ⚠️ Due regole distinte,
      anche se oggi i numeri (5 e 5) coincidono
    - Audit login in dbops.sessioni_utente
    """

    throttle_classes = [LoginRateThrottle]
    # La porta della view (il segmento del path): la sfida del secondo
    # fattore vale solo sulla porta che l'ha emessa.
    porta: str = ""
    # `serializer_class = None` + guard in post() rendono la base effettivamente
    # astratta: chiamare `AuditTokenObtainPairView.as_view()` direttamente
    # senza override di serializer_class solleva RuntimeError subito.
    serializer_class: type[MultiVesteTokenSerializer] | None = None  # type: ignore[assignment]

    @extend_schema(summary="Login JWT con audit e blocco utente", responses={200: dict})
    # Scopo: Esegue il login JWT con check blocco utente e registrazione tentativi.
    # Flusso: check blocco → verifica credenziali → registra esito → audit sessione.
    def post(self, request: Request, *args, **kwargs) -> Response:
        # Guard astratta: serializer_class deve essere MultiVesteTokenSerializer
        # (o subclass). Previene regressione silente: senza questa subclass
        # i claim JWT non conterrebbero identita_id/ruolo_applicativo e l'intero
        # flusso multi-face auth risulterebbe disallineato.
        if self.serializer_class is None or not issubclass(
            self.serializer_class, MultiVesteTokenSerializer
        ):
            raise RuntimeError(
                "AuditTokenObtainPairView e' astratta: usa AdminTokenView / "
                "PortaleTokenView / ShopTokenView (o una nuova subclass con "
                "serializer_class subclass di MultiVesteTokenSerializer)."
            )

        django_request = richiesta_django(request)

        # 0. La provenienza (IP fidato) e' la chiave del freno: senza, il
        #    freno non si puo' applicare e il login si rifiuta (fail-closed).
        #    Prima di cercare l'utente: la risposta non deve dipendere
        #    dall'esistenza dello username. Causa tipica: la richiesta non e'
        #    passata dalla catena di proxy dichiarata (DJANGO_TRUSTED_PROXY_COUNT).
        provenienza = provenienza_obbligatoria(django_request)

        # Il nome tentato come lo vedra' `authenticate` (vedi `_nome_tentato`).
        # None = la richiesta non porta un nome: il serializer rispondera' 400
        # senza guardare la password, quindi non e' un tentativo e non conta.
        nome = self._nome_tentato(request)
        user = self._find_user(nome) if nome is not None else None
        credenziale_id = user.id if user else None
        # ⭐ R-7 (brief-db-blocco-login-per-credenziale §13): check e
        # registrazione si fanno SEMPRE, anche per un nome che non trova
        # niente — la chiave (credenziale o nome) la sceglie il DB. Fino al
        # 2026-09-25 stavano dentro `if user:`, e il numero di chiamate al DB
        # e la risposta dopo la soglia dicevano se il nome esisteva.
        digest = digest_nome_tentato(nome) if nome is not None else None
        chi = etichetta_log(credenziale_id, digest) if digest is not None else "nome=-"

        # 1. Blocco dell'admin, freno sulla provenienza e attesa (lancia
        #    errore DB, convertito dal middleware)
        if digest is not None:
            try:
                _auth_repo.check_blocco_login(
                    credenziale_id, nome_digest=digest, provenienza=provenienza,
                )
            except DatabaseError as exc:
                # Il codice nel log: un rifiuto (E_CREDENZIALE_BLOCCATA,
                # E_UTENTE_BLOCCATO, E_LOGIN_ATTESA) e un guasto del DB non
                # sono la stessa riga di sicurezza.
                # ⛔ Mai il nome in chiaro nei log (B-11): chi digita la
                # password nel campo username la lascerebbe qui.
                logger.warning(
                    "security.login_blocked %s provenienza=%s code=%s",
                    chi, provenienza, structured_db_error_code(exc),
                )
                raise

        # 2. Tenta login (SimpleJWT)
        try:
            response = super().post(request, *args, **kwargs)
        except VesteNonAttivaError:
            # Credenziali corrette ma l'utente non ha la veste richiesta dal
            # namespace (es. operatore che tenta /portale/token/). Non e'
            # un tentativo fallito di credenziali: non conta ne' sulla
            # credenziale ne' sulla provenienza. Logga per audit
            # forense (qualcuno sta provando canali a cui non ha accesso).
            logger.warning("security.veste_non_attiva %s", chi)
            raise
        except (AuthenticationFailed, InvalidToken):
            # Login fallito: registra tentativo.
            # ⛔ `AuthenticationFailed` e' quello di DRF, non quello di
            # SimpleJWT: il serializer (`TokenObtainSerializer.validate`)
            # solleva il primo, e il secondo ne e' una SOTTOCLASSE — catturare
            # la sottoclasse non prende l'istanza della madre. Fino al
            # 2026-09-25 l'import era quello di SimpleJWT e nessuna password
            # sbagliata arrivata dall'API veniva contata: il freno non e' mai
            # scattato. Lo prova test_login_credenziale_db (login vero).
            if digest is not None:
                result = _auth_repo.registra_tentativo_login(
                    credenziale_id, nome_digest=digest, provenienza=provenienza,
                    successo=False,
                )
                # ⭐ Ogni password sbagliata nel log di sicurezza, non solo
                #    quella che fa scattare il freno (2026-10-02): fino ad
                #    allora i primi errori stavano solo a DB, mentre un codice
                #    del secondo fattore sbagliato lasciava gia' la sua riga
                #    (`security.secondo_fattore_fallito`).
                logger.warning(
                    "security.login_fallito %s provenienza=%s bloccato=%s",
                    chi, provenienza, bool(result.get("bloccato")),
                )
                if result.get("bloccato"):
                    logger.warning(
                        "security.login_locked %s provenienza=%s tentativi=%s blocco_minuti=%s",
                        chi, provenienza, result.get("tentativi"),
                        result.get("minuti_rimanenti"),
                    )
                if result.get("attesa_secondi"):
                    logger.warning(
                        "security.login_attesa %s provenienza=%s attesa_secondi=%s",
                        chi, provenienza, result.get("attesa_secondi"),
                    )
            raise

        # 3. Password giusta, veste risolta.
        if response.status_code == 200:
            _, jti = self._extract_claims(response)
            # §8.3.4: il MultiVesteTokenSerializer ha iniettato
            # `identita_id` nel refresh token; serve alle GUC di audit e,
            # col secondo fattore, alla sfida.
            identita_id = _extract_identita_id_from_refresh(
                response.data.get("refresh") if response.data else None
            )
            # Un accesso riuscito ha sempre la credenziale: il nome e' passato
            # dalla stessa normalizzazione di `authenticate`. Un successo senza
            # credenziale il DB lo rifiuta come chiamata non valida.
            if not (user and digest is not None):
                logger.error("security.login_senza_credenziale %s", chi)
                raise ServiceError(
                    code="E_AUTH_CHIAMATA_NON_VALIDA",
                    message="Chiamata non valida al login.",
                    detail="password accettata senza una credenziale trovata dal nome",
                )

            # 3a. Secondo fattore attivo: la password non basta. Niente JWT
            #     (quelli appena emessi da SimpleJWT non escono da qui), niente
            #     successo sul freno, niente sessione: una sfida breve, e il
            #     secondo passo chiude l'accesso col codice
            #     (brief sicurezza §3.4-bis, T-2).
            if _secondo_fattore_repo.get_device(user.id)["stato"] == STATO_DEVICE_ATTIVO:
                if identita_id is None:
                    raise ServiceError(
                        code="E_AUTH_CHIAMATA_NON_VALIDA",
                        message="Chiamata non valida al login.",
                        detail="refresh del login senza identita_id",
                    )
                logger.info("security.login_secondo_passo %s provenienza=%s", chi, provenienza)
                sfida = emetti_sfida(Sfida(
                    auth_user_id=user.id,
                    identita_id=identita_id,
                    porta=self.porta,
                    provenienza=provenienza,
                ))
                return Response({
                    "two_factor_required": True,
                    "sfida": sfida,
                    "scade_in_secondi": DURATA_SFIDA_SECONDI,
                })

            # 3b. Accesso chiuso dalla password.
            if chiudi_accesso_riuscito(
                user=user,
                digest=digest,
                provenienza=provenienza,
                identita_id=identita_id,
                sid=jti,
                django_request=django_request,
            ):
                response.data["password_change_required"] = True
            # ⭐ Ultimo passo: i claim del refresh sono gia' stati letti dal
            #    corpo (sopra); ora il refresh esce dal corpo e va nel cookie
            #    HttpOnly. Al client resta il solo access.
            sposta_refresh_nel_cookie(response, response.data)

        return response

    # Scopo: Il nome tentato normalizzato DAL CAMPO del serializer, cioe'
    # esattamente il valore che arrivera' ad `authenticate`.
    # ⛔ Non una normalizzazione scritta qui: il `CharField` di SimpleJWT toglie
    # gli spazi (`trim_whitespace`) e converte i numeri. Fino al 2026-09-25 il
    # lookup usava il valore grezzo: con « tid» non trovava la credenziale,
    # quindi blocco dell'admin, freno e attesa non si controllavano, mentre
    # `authenticate("tid")` faceva entrare. E due normalizzazioni diverse
    # riaprono l'oracolo del nome (brief §13.3). ⭐ Il campo e' quello che la
    # porta dichiara (`username_field` del serializer: il nome utente per
    # admin, l'email per portale e shop dal 2026-10-06, L-4): lookup e
    # impronta lo seguono da soli.
    # Ritorna None se il campo rifiuta il valore (assente, vuoto, non testo).
    def _nome_tentato(self, request: Request) -> str | None:
        dati = request.data
        if not hasattr(dati, "get"):
            return None
        # Senza contesto: i campi non ne dipendono, e cosi' il metodo non
        # chiede che `dispatch` abbia gia' impostato `self.request`.
        serializer = self._serializer_porta()()
        campo = serializer.fields[serializer.username_field]
        try:
            return campo.run_validation(dati.get(serializer.username_field, empty))
        except ValidationError:
            return None

    # Scopo: Trova la credenziale del nome tentato (best-effort, non lancia
    # errore), con la ricerca della porta (`trova_credenziale` del serializer:
    # nome utente esatto per admin, email senza maiuscole per portale e shop),
    # sul nome gia' normalizzato da `_nome_tentato`.
    # ⛔ Nessun `except`: un guasto del DB qui NON e' «nome inesistente». Fino
    # al 2026-09-25 un `except Exception` lo trasformava in `None`, e il login
    # proseguiva col freno sul nome tentato invece che sulla credenziale —
    # cioe' senza controllare il blocco dell'admin — mentre `authenticate`
    # poteva far entrare. Fail-closed: l'errore sale e il login si ferma.
    def _find_user(self, nome: str) -> User | None:
        return self._serializer_porta().trova_credenziale(nome)

    # Scopo: la classe del serializer della porta col tipo che questa view usa
    #        (`username_field`, `trova_credenziale`). Lo garantisce il guard di
    #        `post`, che rifiuta una porta senza `MultiVesteTokenSerializer`.
    def _serializer_porta(self) -> type[MultiVesteTokenSerializer]:
        classe = self.get_serializer_class()
        assert issubclass(classe, MultiVesteTokenSerializer)
        return classe

    @staticmethod
    # Scopo: Estrae user_id e sid dal refresh token nella response (no query DB extra).
    def _extract_claims(response: Response) -> tuple[int, str | None]:
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh_str = response.data.get("refresh", "")
        if not refresh_str:
            return 0, None
        try:
            token = RefreshToken(refresh_str)
            return int(token.get(simplejwt_settings.USER_ID_CLAIM, 0)), str(token.get(JWT_CLAIM_SID, ""))
        except Exception:
            return 0, None


class AdminTokenView(AuditTokenObtainPairView):
    """Login /api/v1/admin/token/ — solo operatori interni.

    Eredita audit + throttle + blocco utente da AuditTokenObtainPairView;
    cambia solo il serializer per esporre la veste OPERATORE.
    """

    serializer_class = AdminTokenSerializer
    porta = "admin"


class PortaleTokenView(AuditTokenObtainPairView):
    """Login /api/v1/portale/token/ — clienti e fornitori portale B2B.

    Eredita lo stesso ciclo audit/throttle/blocco di AdminTokenView:
    il blocco login e' legato ad auth_user (non a identita), e un
    cliente/fornitore che sbaglia password piu' volte deve comunque
    essere bloccato. Cambia solo il serializer per esporre la veste
    CLIENTE_PORTALE | FORNITORE_PORTALE. Si entra con l'EMAIL, non col nome
    utente (L-4, D-9): corpo `{"email", "password"}`.
    """

    serializer_class = PortaleTokenSerializer
    porta = "portale"


class ShopTokenView(AuditTokenObtainPairView):
    """Login /api/v1/shop/token/ — shop B2C self-service.

    Stesso ciclo audit/throttle/blocco di AdminTokenView; cambia solo
    il serializer per esporre la veste SHOP_CUSTOMER. Stub PR-B4:
    il flusso utente completo (registrazione self-service, attivazione)
    e' in PR-C. Si entra con l'EMAIL (L-4, D-9): corpo `{"email", "password"}`.
    """

    serializer_class = ShopTokenSerializer
    porta = "shop"


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
    # senza override solleva RuntimeError.
    expected_ruoli_applicativi: tuple[str, ...] = ()

    @extend_schema(summary="Refresh JWT con audit sessione", request=None, responses={200: dict})
    # Scopo: Esegue il refresh JWT, valida la veste tramite il guard
    # cross-namespace e registra l'evento REFRESH in dbops.sessioni_utente.
    def post(self, request: Request, *args, **kwargs) -> Response:
        # Guard astratta: le subclass DEVONO settare expected_ruoli_applicativi.
        # Previene regressione silente in cui qualcuno usa la base class
        # in urls.py o in test dimenticando l'override: il refresh
        # funzionerebbe cross-namespace senza check.
        if not self.expected_ruoli_applicativi:
            raise RuntimeError(
                "AuditTokenRefreshView e' astratta: usa AdminTokenRefreshView / "
                "PortaleTokenRefreshView / ShopTokenRefreshView (o una nuova "
                "subclass con expected_ruoli_applicativi settato)."
            )

        # ⭐ Il refresh arriva dal cookie HttpOnly, mai dal corpo (brief
        #    sicurezza §2, 2026-09-28): e' l'unica richiesta autenticata dal
        #    SOLO cookie, quindi pretende anche l'header anti-CSRF. Senza
        #    cookie: 401 come un token non valido, e il client va al login.
        richiedi_header_anti_csrf(request)
        refresh_str = leggi_refresh_cookie(request)
        if refresh_str is None:
            raise InvalidToken("Sessione assente: nessun cookie di refresh.")

        # ⭐ La veste si legge da claim con la FIRMA verificata (BB
        #    `claims_refresh_firmati`, 2026-09-28). Un token illeggibile o non
        #    emesso da noi e' una sessione non valida: 401, come ogni altro
        #    refresh rifiutato. Fino a quel giorno la decodifica era alla
        #    cieca, e un token illeggibile diventava «veste assente» → 403
        #    `E_VESTE_NON_ATTIVA` (E-8 dell'analisi difetti doc API core).
        claims = claims_refresh_firmati(refresh_str)
        if claims is None:
            raise InvalidToken("Sessione non valida: refresh illeggibile o non emesso da questo backend.")

        # Guard cross-namespace: rifiuta il refresh di un token la cui
        # veste non rientra nel set ammesso dal namespace del path
        # (es. refresh portale su /admin/token/refresh/). Nessuna
        # escalation di privilegio — il claim veste viene dal token
        # firmato — ma chiude l'ambiguita' semantica cross-path. Un token
        # nostro SENZA claim veste (pre-§8.3.2) resta 403: grace 0.
        ruolo_claim = claims.get(JWT_CLAIM_RUOLO_APPLICATIVO)
        ruolo = str(ruolo_claim) if ruolo_claim is not None else None
        if ruolo is None or ruolo not in self.expected_ruoli_applicativi:
            logger.warning(
                "security.refresh_cross_namespace path=%s ruolo=%s",
                request.path, ruolo,
            )
            raise VesteNonAttivaError()

        # ⛔ Veste non piu' utilizzabile (spenta o fuori date): la sessione e'
        #    chiusa, PRIMA della rotazione (D-5, `_veste_utilizzabile`). Si
        #    blocca anche il refresh presentato, per sid:
        #    una veste riaccesa dopo non resuscita la sessione — si rientra col
        #    login. 401 e non il 403 del guard sopra: il token era buono, la
        #    sessione non c'e' piu', e il client va al login come per ogni
        #    refresh rifiutato.
        user_id, sid = self._extract_claims(claims)
        identita_id = _int_claim(claims, JWT_CLAIM_IDENTITA_ID)
        if not _veste_utilizzabile(identita_id, user_id):
            if user_id and sid:
                blocca_token_sessioni(user_id, lambda s: s == sid)
            logger.warning(
                "security.refresh_veste_spenta user_id=%s identita_id=%s",
                user_id, identita_id,
            )
            raise InvalidToken("Sessione chiusa: la veste non e' piu' utilizzabile.")

        # `_rinnova` risponde 200 o solleva: da qui in poi il rinnovo e' riuscito.
        response = self._rinnova(refresh_str)
        # Il refresh ruotato torna nel cookie, e dal corpo esce.
        sposta_refresh_nel_cookie(response, response.data)
        django_request = richiesta_django(request)
        # Audit e GUC dagli STESSI claim verificati del guard (letti sopra:
        # `user_id`, `sid`, `identita_id`), non da una seconda lettura del
        # token (la rotazione preserva i claim custom).
        # Hotfix BE-2.0ter: il refresh NON passa dalla DRF auth chain
        # (la request porta solo il refresh token nel cookie, niente
        # Authorization Bearer), quindi JwtAuditAuthentication NON
        # setta le GUC. Le settiamo qui manualmente prima della
        # scrittura di audit. Lo username viene risolto dal user_id
        # dei claim con la firma verificata, quindi affidabile.
        if user_id:
            username = self._resolve_username(user_id)
            if username:
                # §8.3.4: il refresh token (anche dopo rotation) preserva
                # il claim identita_id iniettato al login: quello del
                # refresh in entrata basta per le GUC sulla veste giusta.
                gucs_ok = set_jwt_gucs(
                    username=username,
                    user_id=user_id,
                    identita_id=identita_id,
                    # L'emittente attivo viaggia col refresh (rotation
                    # preserva i claim custom): senza, ogni refresh
                    # riporterebbe l'utente in modalita' globale a sua
                    # insaputa. La CTE ricontrolla che sia ancora attivo.
                    # Claim assente = «Tutti gli emittenti» → None.
                    emittente_attivo_id=_int_claim(claims, JWT_CLAIM_EMITTENTE_ATTIVO_ID),
                    request=django_request,
                )
                if not gucs_ok:
                    logger.warning(
                        "security.refresh_guc_mancate user_id=%s identita_id=%s",
                        user_id, identita_id,
                    )
        session_audit_service.record_refresh(
            user_id=user_id,
            request=django_request,
            jti=sid,
        )
        return response

    # Scopo: Il corpo di `TokenViewBase.post`, col refresh preso dal cookie
    #        invece che da `request.data`: stessa validazione (firma, scadenza,
    #        blacklist, rotazione) e stessa traduzione degli errori (401).
    def _rinnova(self, refresh_str: str) -> Response:
        serializer = self.get_serializer(data={"refresh": refresh_str})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0]) from exc
        return Response(serializer.validated_data, status=200)

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
    # Scopo: user_id e sid dai claim VERIFICATI del refresh presentato (quelli
    # del guard). §8.3.9: non `RefreshToken(refresh_str)`, che a rotazione
    # avvenuta trova il token in blacklist e solleva — l'audit finirebbe con
    # user_insert=zeroerp_app.
    def _extract_claims(claims: dict) -> tuple[int, str | None]:
        raw_sid = claims.get(JWT_CLAIM_SID)
        sid = str(raw_sid) if raw_sid is not None else None
        return _int_claim(claims, simplejwt_settings.USER_ID_CLAIM) or 0, sid


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
