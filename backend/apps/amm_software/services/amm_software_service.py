# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service layer per Amm. Software — validazione, orchestrazione.
#        Ref: docs/it/dev/api.md (sezione 6 Layering)
# ------------------------------------------------------------

from __future__ import annotations

import uuid as uuid_mod
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Any

from django.contrib.auth.hashers import make_password
from django.db import DatabaseError

from apps.core.api.payload_validators import optional_int
from apps.core.services.error_manager import ErrorManager
from apps.core.services.parameter_service import ParameterService
from apps.core.services.service_errors import ServiceError
from apps.core.services.permissions_cache import invalidate_department, invalidate_user
from apps.amm_software.constants import DEFAULT_SESSO
from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository

E_AMM_VALIDAZIONE = "E_AMM_VALIDAZIONE"
E_AMM_NOT_FOUND = "E_AMM_OPERATORE_NOT_FOUND"
E_AMM_SCOPE_NON_AMMESSO = "E_AMM_SCOPE_NON_AMMESSO"

# Fase 5 audit hardening — codici stabili dal team DB.
E_AUDIT_SUMMARY_PARAM_NON_VALIDO = "E_AUDIT_SUMMARY_PARAM_NON_VALIDO"
E_AUDIT_SOURCE_NON_TROVATO = "E_AUDIT_SOURCE_NON_TROVATO"
E_AUDIT_SNAPSHOT_NON_TROVATO = "E_AUDIT_SNAPSHOT_NON_TROVATO"
E_OPERATORE_SCOPE_PARAM_NON_VALIDO = "E_OPERATORE_SCOPE_PARAM_NON_VALIDO"

# Scope mode ammessi post Q2 (refactor operatore-emittenti). MULTI e'
# architetturalmente chiuso dal vincolo UNIQUE(auth_user_id) su
# config.user_emittenti_fiscali. Il valore arriva sia dalla fn DB
# (allowed_scope_modes) che dal payload PUT — manteniamo entrambi
# allineati come fonte unica.
_SCOPE_MODE_GLOBAL = "GLOBAL"
_SCOPE_MODE_SINGLE = "SINGLE"
_SCOPE_MODI_AMMESSI = frozenset({_SCOPE_MODE_GLOBAL, _SCOPE_MODE_SINGLE})

# Marker code sollevato dal trigger DB
# `trgfn_profili_accesso_bindings_guard_ultimo_super_admin` quando un
# UPDATE/DELETE lascerebbe il sistema senza super admin attivi. Il preview
# lato detail (`can_disable`/`can_demote_super_admin`) non e' una garanzia:
# in caso di race tra sessioni il trigger resta l'autorita'. Quando un'azione
# fallisce con questo marker, lo traduciamo in ServiceError preservando il
# code per l'envelope errore (HTTP 409, vedi error_policies.py).
_E_PROFILO_ULTIMO_SUPER_ADMIN = "E_PROFILO_ULTIMO_SUPER_ADMIN"

# Fase 3 — Form-defaults emittente fiscale.
# Modi di arrotondamento ammessi per `anagrafiche.emittenti_fiscali.rounding_policy`.
# Allineati al CHECK constraint DB `chk_emittenti_fiscali_rounding_policy`:
# 4 valori, NO `HALF_EVEN` (a differenza di catalogo UoM operativa che ne ha 5).
# Single source of truth lato Python: il lookup statico dell'API serve l'enum
# direttamente da qui, niente tabella DB. Validazione fail-fast sui valori
# ricevuti dal parameters cascade (best-effort: invalido -> None, no raise).
_ROUNDING_MODE_VALIDI_EMITTENTE: frozenset[str] = frozenset(
    {"UP", "DOWN", "HALF_UP", "HALF_DOWN"}
)

# Mappa codice -> (descrizione, ordering) per lookup statico.
# Ordering "default-first": HALF_UP e' il default seedato in config.parameters
# (`EMITTENTE_DEFAULT_ROUNDING_POLICY`).
_ROUNDING_MODE_DESCRIZIONI_EMITTENTE: tuple[tuple[str, str, int], ...] = (
    ("HALF_UP", "Arrotondamento meta' su (5 va su)", 1),
    ("HALF_DOWN", "Arrotondamento meta' giu' (5 va giu')", 2),
    ("UP", "Arrotondamento sempre su (verso infinito)", 3),
    ("DOWN", "Arrotondamento sempre giu' (verso zero)", 4),
)

# Codici parameters consumati dal form di creazione emittente fiscale.
# Cascata user -> group -> emittente -> default via fn_get_parameter_full
# (in creazione `emittente_fiscale_id` e' None: cascata effettiva user->group->default).
_EMITTENTE_FORM_DEFAULTS_CODES: tuple[str, ...] = (
    "EMITTENTE_DEFAULT_BOLLO_AUTO",
    "EMITTENTE_DEFAULT_BOLLO_SOGLIA",
    "EMITTENTE_DEFAULT_ROUNDING_POLICY",
)

# Campi non editabili in modifica emittente (oggi statici, in attesa che
# `dbops.vw_non_editable_fields` di Fase 5 includa anche le tabelle anagrafiche).
# Espono i metadata gia' nella response Fase 3 per non avere breaking change
# quando la fonte diventera' DB-driven.
_EMITTENTE_NON_EDITABLE_FIELDS: tuple[str, ...] = ("codice", "soggetto_id")

# Fase 5 — Lookup statico stati email log.
# Single source of truth lato Python: l'enum e' un set chiuso (PENDING, SENT,
# FAILED, RETRY) gestito dal `EmailDispatchService`/log writer, non c'e' una
# tabella DB di config. Pattern simmetrico ai rounding modes Fase 3.
# Ordering "default-first": SENT come stato finale piu' frequente.
_EMAIL_LOG_STATI_VALIDI: frozenset[str] = frozenset(
    {"SENT", "PENDING", "RETRY", "FAILED", "SIMULATA"}
)

_EMAIL_LOG_STATI_DESCRIZIONI: tuple[tuple[str, str, int], ...] = (
    ("SENT",    "Inviata",                                  1),
    ("PENDING", "In attesa di invio",                       2),
    ("RETRY",   "Tentativo successivo programmato",         3),
    ("FAILED",  "Invio fallito",                            4),
    # ⭐ `SIMULATA` (2026-09-11): la mail e' stata STAMPATA a video invece che
    #    spedita — sviluppo senza SMTP. E' terminale e VOLUTA, e per questo non
    #    e' `FAILED`; e non e' `SENT` perche' non e' arrivata a nessuno.
    #    ⚠️ La frase dice l'esito, non il canale: chi legge il giornale chiede
    #    «e' arrivata?», non «da quale strada e' uscita» (brief §7.1).
    ("SIMULATA", "Simulata — non spedita",                   5),
)


# Scopo: Cast best-effort di un valore parameter (sempre str per BE) a bool.
# `'true'`/`'false'` case-insensitive -> bool. Altro (None, '', stringhe non
# parsabili) -> False (default-safe per `bollo_auto`: il form parte con flag
# OFF, allineato al seed `EMITTENTE_DEFAULT_BOLLO_AUTO=false`).
def _cast_param_bool(raw: object) -> bool:
    if isinstance(raw, str):
        return raw.strip().lower() == "true"
    return False


# Scopo: Cast best-effort di un valore parameter a Decimal.
# Convenzione DB: stringa vuota = "nessuna soglia" -> None. Stringhe non
# parsabili -> None (il form mostra comunque, l'utente compila manualmente).
def _cast_param_decimal(raw: object) -> Decimal | None:
    if not isinstance(raw, str):
        return None
    candidate = raw.strip()
    if not candidate:
        return None
    try:
        return Decimal(candidate)
    except (InvalidOperation, ValueError):
        return None


# Scopo: Esegue una callable repo che puo' violare il guard "ultimo super
# admin" e traduce l'errore DB nel ServiceError canonico
# `E_PROFILO_ULTIMO_SUPER_ADMIN`. Il trigger e' l'autorita': preview
# `can_disable`/`can_demote_super_admin` lato detail puo' essere stale a
# causa di race tra sessioni. Tutte le altre `DatabaseError` sono ri-sollevate
# (gestite dal middleware globale).
def _run_or_raise_super_admin_guard(repo_call: Callable[[], None]) -> None:
    try:
        repo_call()
    except DatabaseError as exc:
        msg = str(exc)
        if _E_PROFILO_ULTIMO_SUPER_ADMIN in msg:
            raise ServiceError(
                code=_E_PROFILO_ULTIMO_SUPER_ADMIN,
                message="Impossibile rimuovere l'ultimo super admin attivo.",
                detail=msg,
            ) from exc
        # Fase 5: il refactor DB di Fase 2 ha sostituito `RAISE EXCEPTION 22023`
        # generico con codice stabile `E_OPERATORE_SCOPE_PARAM_NON_VALIDO` per
        # i guard di `fn_change_user_emittenti_scope` (es. scope_mode invalido,
        # array vuoto/multi-elemento). Lo distinguiamo da E_AMM_SCOPE_NON_AMMESSO
        # (validazione applicativa pre-call) e dal guard "ultimo SA" (semantica
        # diversa). Trigger DB resta autorita' finale.
        if E_OPERATORE_SCOPE_PARAM_NON_VALIDO in msg:
            raise ServiceError(
                code=E_OPERATORE_SCOPE_PARAM_NON_VALIDO,
                message="Parametri scope operatore non validi.",
                detail=msg,
            ) from exc
        raise


class AmmSoftwareService:
    """Service per gestione operatori, permessi, profili reparto."""

    def __init__(self) -> None:
        self._repo = AmmSoftwareRepository()

    # =================================================================
    # Operatori
    # =================================================================

    # Scopo: Crea operatore completo. Due flussi:
    # Flusso A (soggetto_id assente): crea soggetto PF nuovo — cognome/nome/CF obbligatori.
    # Flusso B (soggetto_id presente): associa soggetto esistente — dati persona non richiesti.
    # In entrambi: username, email, password, qualifica obbligatori.
    # Contract pubblico Fase 7 multi-face: `is_super_admin?: bool` (default
    # false). L'operatore viene sempre creato con `attivo=true` (la
    # disabilitazione e' un comando dedicato).
    def create_operatore(self, payload: dict) -> dict[str, Any]:
        ErrorManager.require(
            "ruolo_sistema" not in payload,
            code=E_AMM_VALIDAZIONE,
            message="Campo 'ruolo_sistema' non ammesso: usa is_super_admin.",
        )
        soggetto_id = (payload.get("soggetto_id") or "").strip() or None
        username = (payload.get("username") or "").strip()
        email = (payload.get("email") or "").strip()
        password = payload.get("password") or ""
        raw_qualifica = payload.get("qualifica_id")

        # Guard UUID soggetto_id (flusso B)
        if soggetto_id:
            try:
                uuid_mod.UUID(soggetto_id)
            except (ValueError, AttributeError):
                ErrorManager.require(False, code=E_AMM_VALIDAZIONE, message="UUID soggetto non valido.", context={"field": "soggetto_id"})

        # Guard qualifica_id numerico
        try:
            qualifica_id = int(raw_qualifica) if raw_qualifica is not None else None
        except (ValueError, TypeError):
            qualifica_id = None

        # Validazione comune (entrambi i flussi)
        ErrorManager.require(bool(username), code=E_AMM_VALIDAZIONE, message="Username obbligatorio.", context={"field": "username"})
        ErrorManager.require(bool(email), code=E_AMM_VALIDAZIONE, message="Email obbligatoria.", context={"field": "email"})
        ErrorManager.require(bool(password), code=E_AMM_VALIDAZIONE, message="Password obbligatoria.", context={"field": "password"})
        ErrorManager.require(qualifica_id is not None and qualifica_id > 0, code=E_AMM_VALIDAZIONE, message="Qualifica obbligatoria.", context={"field": "qualifica_id"})

        # Validazione flusso A: dati persona obbligatori solo se soggetto nuovo
        cognome = (payload.get("cognome") or "").strip()
        nome = (payload.get("nome") or "").strip()
        codice_fiscale = (payload.get("codice_fiscale") or "").strip()

        if not soggetto_id:
            ErrorManager.require(bool(cognome), code=E_AMM_VALIDAZIONE, message="Cognome obbligatorio per soggetto nuovo.", context={"field": "cognome"})
            ErrorManager.require(bool(nome), code=E_AMM_VALIDAZIONE, message="Nome obbligatorio per soggetto nuovo.", context={"field": "nome"})
            ErrorManager.require(bool(codice_fiscale), code=E_AMM_VALIDAZIONE, message="Codice fiscale obbligatorio per soggetto nuovo.", context={"field": "codice_fiscale"})

        # Contract Fase 7: il caller passa `is_super_admin` (default False).
        # Il caller non puo' creare DISABILITATI via questo endpoint: la
        # disabilitazione e' un comando dedicato. La traduzione verso
        # l'enum legacy della fn DB e' incapsulata nel repository.
        is_super_admin = bool(payload.get("is_super_admin"))

        auth_user_id = self._repo.crea_operatore(
            soggetto_id=soggetto_id,
            cognome=cognome or None,
            nome=nome or None,
            codice_fiscale=codice_fiscale or None,
            username=username,
            email=email,
            password_hash=make_password(password),
            qualifica_id=qualifica_id,  # type: ignore[arg-type]
            unita_organizzativa_id=int(payload["unita_organizzativa_id"]) if payload.get("unita_organizzativa_id") else None,
            data_nascita=payload.get("data_nascita"),
            sesso=payload.get("sesso", DEFAULT_SESSO),
            is_super_admin=is_super_admin,
            attivo=True,
            valido_dal=payload.get("valido_dal"),
            valido_al=payload.get("valido_al"),
            comune_nascita_id=optional_int(payload, "comune_nascita_id"),
            indirizzo_resid_dettaglio_id=optional_int(payload, "indirizzo_resid_dettaglio_id"),
            indirizzo_domfisc_dettaglio_id=optional_int(payload, "indirizzo_domfisc_dettaglio_id"),
        )
        return self._repo.get_operatore_detail(auth_user_id) or {}

    # Scopo: Dettaglio operatore con validazione esistenza.
    def get_operatore(self, auth_user_id: int) -> dict[str, Any]:
        operatore = self._repo.get_operatore_detail(auth_user_id)
        ErrorManager.require(operatore is not None, code=E_AMM_NOT_FOUND, message=f"Operatore {auth_user_id} non trovato.")
        assert operatore is not None
        return operatore

    # Scopo: Aggiorna operatore e invalida cache permessi.
    # Contract pubblico Fase 7 multi-face:
    #   {is_super_admin?: bool, attivo?: bool, email?, first_name?, last_name?,
    #    unita_organizzativa_id?, valido_al?}
    # `is_super_admin` e `attivo` sono ortogonali: ognuno puo' essere
    # presente da solo (NO-OP per il flag mancante). Il guard "ultimo super
    # admin" e' centralizzato sul trigger DB; il service traduce l'errore in
    # `E_PROFILO_ULTIMO_SUPER_ADMIN`.
    def update_operatore(self, auth_user_id: int, payload: dict) -> dict[str, Any]:
        ErrorManager.require(
            "ruolo_sistema" not in payload,
            code=E_AMM_VALIDAZIONE,
            message="Campo 'ruolo_sistema' non ammesso: usa is_super_admin + attivo.",
        )
        self.get_operatore(auth_user_id)  # verifica esistenza
        _run_or_raise_super_admin_guard(
            lambda: self._repo.update_operatore(
                auth_user_id,
                email=payload.get("email"),
                first_name=payload.get("first_name"),
                last_name=payload.get("last_name"),
                is_super_admin=payload.get("is_super_admin"),
                unita_organizzativa_id=payload.get("unita_organizzativa_id"),
                attivo=payload.get("attivo"),
                valido_al=payload.get("valido_al"),
            )
        )
        invalidate_user(auth_user_id)
        return self._repo.get_operatore_detail(auth_user_id) or {}

    # Scopo: Disabilita operatore, invalida cache e blacklist token.
    # Preview UX `can_disable=false` evita il round-trip DB nel 99% dei casi
    # (single source of truth: `script.fn_check_ultimo_super_admin_attivo`
    # consumata da `fn_get_operatore_detail`). L'autorita' finale resta il
    # trigger DB `trgfn_profili_accesso_bindings_guard_ultimo_super_admin`
    # che intercetta anche le race tra sessioni: traduciamo l'errore in
    # `E_PROFILO_ULTIMO_SUPER_ADMIN`.
    def disabilita_operatore(self, auth_user_id: int) -> dict[str, Any]:
        operatore = self.get_operatore(auth_user_id)
        if operatore.get("can_disable") is False:
            raise ServiceError(
                code=_E_PROFILO_ULTIMO_SUPER_ADMIN,
                message="Impossibile rimuovere l'ultimo super admin attivo.",
                detail=operatore.get("disable_reason")
                or "Deve esistere almeno un super admin attivo nel sistema.",
            )
        _run_or_raise_super_admin_guard(
            lambda: self._repo.disabilita_operatore(auth_user_id)
        )
        invalidate_user(auth_user_id)
        _blacklist_user_tokens(auth_user_id)
        return self._repo.get_operatore_detail(auth_user_id) or {}

    # Scopo: Riattiva operatore disabilitato, invalida cache.
    def riattiva_operatore(self, auth_user_id: int) -> dict[str, Any]:
        self.get_operatore(auth_user_id)  # verifica esistenza
        self._repo.riattiva_operatore(auth_user_id)
        invalidate_user(auth_user_id)
        return self._repo.get_operatore_detail(auth_user_id) or {}

    # =================================================================
    # Override permessi
    # =================================================================

    # Scopo: Salva override aree e invalida cache.
    def put_override_aree(self, auth_user_id: int, items: list) -> list:
        self._repo.put_override_aree(auth_user_id, items)
        invalidate_user(auth_user_id)
        return self._repo.get_override_aree(auth_user_id)

    # Scopo: Salva override azioni e invalida cache.
    def put_override_azioni(self, auth_user_id: int, items: list) -> list:
        self._repo.put_override_azioni(auth_user_id, items)
        invalidate_user(auth_user_id)
        return self._repo.get_override_azioni(auth_user_id)

    # Scopo: Cambia lo scope emittenti dell'operatore (Fase 2 multi-face).
    # Contract pubblico:
    #   {scope_mode: 'GLOBAL'|'SINGLE', emittenti_ids: list[int]}
    #
    # Validazione lato service:
    #   - scope_mode in {GLOBAL, SINGLE} (no MULTI: rejection esplicita).
    #   - GLOBAL  -> emittenti_ids normalizzato a [].
    #   - SINGLE  -> emittenti_ids deve avere esattamente 1 elemento int>0.
    #
    # Il guard "ultimo super admin" e' integrato nella fn DB
    # `fn_change_user_emittenti_scope` e arriva come DatabaseError con marker
    # E_PROFILO_ULTIMO_SUPER_ADMIN — riusiamo `_run_or_raise_super_admin_guard`
    # di Fase 1 per la traduzione.
    def put_emittenti_scope(self, auth_user_id: int, payload: dict) -> dict[str, Any]:
        self.get_operatore(auth_user_id)  # verifica esistenza
        scope_mode = (payload.get("scope_mode") or "").strip().upper()
        emittenti_ids_raw = payload.get("emittenti_ids") or []

        ErrorManager.require(
            scope_mode in _SCOPE_MODI_AMMESSI,
            code=E_AMM_SCOPE_NON_AMMESSO,
            message=f"Scope mode '{scope_mode}' non ammesso. Valori validi: {sorted(_SCOPE_MODI_AMMESSI)}.",
        )

        if scope_mode == _SCOPE_MODE_GLOBAL:
            emittenti_ids: list[int] = []
        else:
            # SINGLE: esattamente 1 elemento int positivo. Tre check in
            # cascata ognuno con messaggio specifico.
            ErrorManager.require(
                isinstance(emittenti_ids_raw, list) and len(emittenti_ids_raw) == 1,
                code=E_AMM_SCOPE_NON_AMMESSO,
                message="scope_mode='SINGLE' richiede esattamente 1 emittente in emittenti_ids.",
            )
            # Guard tipo + valore in un solo require (no try/except/else macchinoso).
            try:
                eid: int | None = int(emittenti_ids_raw[0])
            except (ValueError, TypeError):
                eid = None
            ErrorManager.require(
                eid is not None and eid > 0,
                code=E_AMM_SCOPE_NON_AMMESSO,
                message="emittenti_ids[0] deve essere int positivo.",
            )
            assert eid is not None  # per il type checker (require sopra)
            emittenti_ids = [eid]

        _run_or_raise_super_admin_guard(
            lambda: self._repo.change_user_emittenti_scope(auth_user_id, emittenti_ids)
        )
        invalidate_user(auth_user_id)
        # Rilegge lo stato post-change per consistenza col GET (la fn change
        # ritorna jsonb ma non lo proiettiamo: single source of truth = fn_get).
        return self._repo.get_user_emittenti_scope(auth_user_id) or {}

    # Scopo: Lista operatori con filtri.
    def list_operatori(self, **params) -> tuple[list, int]:
        return self._repo.list_operatori(**params)

    # Scopo: Lista override aree.
    def get_override_aree(self, auth_user_id: int) -> list:
        return self._repo.get_override_aree(auth_user_id)

    # Scopo: Lista override azioni.
    def get_override_azioni(self, auth_user_id: int) -> list:
        return self._repo.get_override_azioni(auth_user_id)

    # Scopo: Salva override oggetti e invalida cache.
    #        Valida che ogni app_label+model_name esista nel catalogo
    #        area_model_overrides E sia override-abile (capability `can_override`
    #        — Fase 8). I model riservati al kernel permessi sono rifiutati
    #        anche se registrati in catalogo (defense-in-depth: il FE filtra
    #        gia' le opzioni, ma una request crafted bypassa il dropdown).
    def put_override_oggetti(self, auth_user_id: int, items: list) -> list:
        if items:
            catalog = self._repo.list_model_overrides()
            registered = {(m["app_label"], m["model_name"]) for m in catalog}
            overridable = {
                (m["app_label"], m["model_name"])
                for m in catalog
                if m.get("can_override")
            }
            for item in items:
                key = (item.get("app_label"), item.get("model_name"))
                ErrorManager.require(
                    key[0] and key[1] and key in registered,
                    code="E_AMM_VALIDAZIONE",
                    message=f"Model {key[0]}.{key[1]} non registrato nel catalogo override.",
                )
                ErrorManager.require(
                    key in overridable,
                    code="E_AMM_VALIDAZIONE",
                    message=f"Model {key[0]}.{key[1]} riservato: override non ammesso.",
                )
        self._repo.put_override_oggetti(auth_user_id, items)
        invalidate_user(auth_user_id)
        return self._repo.get_override_oggetti(auth_user_id)

    # Scopo: Lista override oggetti.
    def get_override_oggetti(self, auth_user_id: int) -> list:
        return self._repo.get_override_oggetti(auth_user_id)

    # Scopo: Lista model registrati per lookup admin.
    def list_model_overrides(self) -> list:
        return self._repo.list_model_overrides()

    # Scopo: Scope emittenti dichiarativo per un operatore (Fase 2 multi-face).
    # Ritorna lo shape della fn DB (scope_mode + capability + reason).
    # `emittenti_ids` viene derivato come array per simmetria col PUT (anche
    # se post Q2 puo' avere al massimo 1 elemento): GLOBAL -> [],
    # SINGLE -> [emittente_id]. Manteniamo l'array per non vincolare
    # l'eventuale futura riapertura di MULTI lato API.
    def get_emittenti_scope(self, auth_user_id: int) -> dict[str, Any]:
        self.get_operatore(auth_user_id)  # verifica esistenza
        row = self._repo.get_user_emittenti_scope(auth_user_id) or {}
        emittente_id = row.get("emittente_id")
        emittenti_ids = [emittente_id] if emittente_id is not None else []
        return {
            "scope_mode": row.get("scope_mode") or _SCOPE_MODE_GLOBAL,
            "emittenti_ids": emittenti_ids,
            "emittente_descrizione": row.get("emittente_descrizione"),
            "allowed_scope_modes": list(row.get("allowed_scope_modes") or [_SCOPE_MODE_GLOBAL, _SCOPE_MODE_SINGLE]),
            "can_change_scope": bool(row.get("can_change_scope", True)),
            "change_scope_reason": row.get("change_scope_reason"),
        }

    # Scopo: Lista reparti.
    def list_reparti(self) -> list:
        return self._repo.list_reparti()

    # Scopo: Profilo reparto.
    def get_profilo_reparto(self, uo_id: int) -> dict:
        return self._repo.get_profilo_reparto(uo_id)

    # Scopo: I livelli che l'operatore eredita dal profilo (area + azione),
    #        cioe' cosa avrebbe SENZA override individuali. Serve al pannello
    #        permessi per non far scrivere override che ripetono il profilo.
    # ⚠️ `get_operatore` prima della lettura, e non e' cerimonia: su un id
    #    inesistente le due query tornerebbero due liste VUOTE, che a video
    #    sono indistinguibili da «questo utente non eredita niente» — cioe' la
    #    risposta sbagliata invece di un errore.
    def get_permessi_ereditati(self, auth_user_id: int) -> dict:
        self.get_operatore(auth_user_id)
        return self._repo.get_permessi_ereditati(auth_user_id)

    # Scopo: Lista UO.
    def list_unita_organizzative(self) -> list:
        return self._repo.list_unita_organizzative()

    # Scopo: Lista aree funzionali.
    def list_aree_funzionali(self) -> list:
        return self._repo.list_aree_funzionali()

    # Scopo: Lista azioni processo.
    def list_azioni_processo(self) -> list:
        return self._repo.list_azioni_processo()

    # Scopo: Lista emittenti fiscali.
    def list_emittenti_fiscali(self) -> list:
        return self._repo.list_emittenti_fiscali()

    # Scopo: Setup status del refactor operatore-emittenti.
    # Conta emittenti attivi, operatori totali, assegnati, admin globali,
    # non assegnati. Usato dal banner UI "operatori non assegnati" per
    # avvisare l'admin durante la transizione (decisione D1 del WIP).
    def get_setup_status(self) -> dict:
        return self._repo.get_setup_status()

    # =================================================================
    # Form-defaults emittente fiscale (Fase 3)
    # =================================================================

    # Scopo: Restituisce i defaults per il form di creazione/modifica
    #        anagrafica emittente fiscale (Fase 3 — A5/A6).
    #        Centralizza il consumo di `config.parameters`
    #        (`EMITTENTE_DEFAULT_BOLLO_AUTO`, `_BOLLO_SOGLIA`,
    #        `_ROUNDING_POLICY`) con cast tipi gia' applicato:
    #          - `bollo_auto`     : bool ('true'/'false', case-insensitive)
    #          - `bollo_soglia`   : Decimal | None (stringa vuota -> None)
    #          - `rounding_policy`: str validato vs _ROUNDING_MODE_VALIDI_EMITTENTE
    #                               (invalido -> None, no raise: il form mostra
    #                               comunque, l'utente seleziona manualmente)
    #        Il campo `attivo` NON passa per parameters (la colonna DB ha gia'
    #        DEFAULT true). `non_editable_fields` ritornato statico oggi (vedi
    #        nota su _EMITTENTE_NON_EDITABLE_FIELDS).
    def get_emittente_form_defaults(
        self,
        *,
        django_user_id: int | None = None,
        group_ids: list[int] | None = None,
        emittente_fiscale_id: int | None = None,
    ) -> dict[str, object]:
        raw = ParameterService().get_defaults(
            list(_EMITTENTE_FORM_DEFAULTS_CODES),
            django_user_id=django_user_id,
            group_ids=group_ids,
            emittente_fiscale_id=emittente_fiscale_id,
        )

        bollo_auto = _cast_param_bool(raw.get("EMITTENTE_DEFAULT_BOLLO_AUTO"))
        bollo_soglia = _cast_param_decimal(raw.get("EMITTENTE_DEFAULT_BOLLO_SOGLIA"))
        rounding_policy_raw = raw.get("EMITTENTE_DEFAULT_ROUNDING_POLICY")
        rounding_policy: str | None = None
        if isinstance(rounding_policy_raw, str):
            candidate = rounding_policy_raw.strip().upper()
            if candidate in _ROUNDING_MODE_VALIDI_EMITTENTE:
                rounding_policy = candidate

        return {
            "defaults": {
                "bollo_auto": bollo_auto,
                "bollo_soglia": bollo_soglia,
                "rounding_policy": rounding_policy,
            },
            "non_editable_fields": list(_EMITTENTE_NON_EDITABLE_FIELDS),
        }

    # Scopo: Lista statica dei modi di arrotondamento ammessi per emittente
    #        fiscale (Fase 3 — A6). Single source of truth =
    #        _ROUNDING_MODE_VALIDI_EMITTENTE + _ROUNDING_MODE_DESCRIZIONI_EMITTENTE.
    #        Niente DB: enum tecnico fisso (4 valori, no HALF_EVEN), allineato
    #        al CHECK constraint sulla colonna `rounding_policy`.
    #        L'invariante "descrizioni copre l'enum" e' garantita dal test
    #        `test_list_emittente_rounding_modes_coverage` (CI), non a runtime.
    def list_emittente_rounding_modes(self) -> list[dict[str, object]]:
        return [
            {"codice": codice, "descrizione": descrizione, "ordering": ordering}
            for codice, descrizione, ordering in _ROUNDING_MODE_DESCRIZIONI_EMITTENTE
        ]

    # =================================================================
    # Profili reparto
    # =================================================================

    # Scopo: Salva profilo reparto e invalida cache di tutti gli operatori del reparto.
    def put_profilo_reparto(self, uo_id: int, aree: list, azioni: list) -> dict:
        self._repo.put_profilo_reparto(uo_id, aree, azioni)
        invalidate_department(uo_id)
        return self._repo.get_profilo_reparto(uo_id)

    # =================================================================
    # Riepilogo permessi
    # =================================================================

    # Scopo: Matrice permessi effettivi per tutti gli operatori attivi.
    def get_permessi_riepilogo(self, **params) -> dict:
        return self._repo.get_permessi_riepilogo(**params)

    # Scopo: Audit log globale modifiche permessi (Fase 5 — A13/A16).
    #        Ogni evento ora include `code`/`storico_id`/`area_funzionale` +
    #        `audit: {summary, diff}` calcolato inline da `fn_audit_summary`.
    def list_audit_log(self, **params) -> tuple[list, int]:
        return self._repo.list_audit_log(**params)

    # Scopo: Lookup statico sorgenti audit ammesse (Fase 5 — A13).
    #        Single source of truth lato DB: `script.vw_audit_sources`.
    #        Sostituisce `buildAuditTabellaOptions` hardcoded FE.
    def list_audit_sources(self) -> list[dict[str, Any]]:
        return self._repo.list_audit_sources()

    # Scopo: Calcola summary + diff per uno snapshot audit (Fase 5 — A13).
    #        Wrapper validato su `fn_audit_summary(code, storico_id)`.
    #        Errori:
    #          - `E_AUDIT_SUMMARY_PARAM_NON_VALIDO` se code/storico_id assenti
    #            o malformati (storico_id non int positivo).
    #          - `E_AUDIT_SOURCE_NON_TROVATO` se code non e' in vw_audit_sources.
    #          - `E_AUDIT_SNAPSHOT_NON_TROVATO` se la fn DB non trova lo snapshot.
    def get_audit_summary(self, code: str | None, storico_id: int | None) -> dict[str, Any]:
        ErrorManager.require(
            isinstance(code, str) and bool(code.strip()),
            code=E_AUDIT_SUMMARY_PARAM_NON_VALIDO,
            message="Codice sorgente audit obbligatorio.",
        )
        ErrorManager.require(
            isinstance(storico_id, int) and storico_id > 0,
            code=E_AUDIT_SUMMARY_PARAM_NON_VALIDO,
            message="ID storico audit non valido.",
        )
        assert code is not None and storico_id is not None  # type narrowing
        normalized_code = code.strip()
        valid_codes = {row["code"] for row in self._repo.list_audit_sources()}
        ErrorManager.require(
            normalized_code in valid_codes,
            code=E_AUDIT_SOURCE_NON_TROVATO,
            message="Sorgente audit non riconosciuta.",
            context={"code": normalized_code},
        )
        result = self._repo.get_audit_summary(normalized_code, storico_id)
        ErrorManager.require(
            result is not None,
            code=E_AUDIT_SNAPSHOT_NON_TROVATO,
            message="Snapshot audit non trovato.",
            context={"code": normalized_code, "storico_id": storico_id},
        )
        assert result is not None
        return result

    # Scopo: Lookup statico stati email log (Fase 5).
    #        Single source of truth in `_EMAIL_LOG_STATI_DESCRIZIONI`. Niente
    #        DB: enum chiuso (5 valori, `SIMULATA` dal 2026-09-11) gestito dal
    #        log writer. Pattern simmetrico ai rounding modes Fase 3.
    # ⚠️ La lista NON viene ordinata: esce nell'ordine in cui la tupla e'
    #    dichiarata, ed e' `test_list_email_log_stati_ok` a pretendere che
    #    quell'ordine coincida col campo `ordering`.
    def list_email_log_stati(self) -> list[dict[str, object]]:
        return [
            {"codice": codice, "descrizione": descrizione, "ordering": ordering}
            for codice, descrizione, ordering in _EMAIL_LOG_STATI_DESCRIZIONI
        ]


# Scopo: Invalida token JWT operatore via blacklist SimpleJWT (best-effort).
def _blacklist_user_tokens(auth_user_id: int) -> None:
    try:
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
        tokens = OutstandingToken.objects.filter(user_id=auth_user_id)
        for token in tokens:
            try:
                from rest_framework_simplejwt.tokens import RefreshToken
                rt = RefreshToken(token.token)
                rt.blacklist()
            except Exception:
                pass
    except ImportError:
        pass
