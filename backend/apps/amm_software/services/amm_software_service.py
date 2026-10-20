# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service layer per Amm. Software — validazione, orchestrazione.
#        Ref: docs/it/dev/api.md (sezione 6 Layering)
# ------------------------------------------------------------

from __future__ import annotations

import uuid as uuid_mod
from collections.abc import Callable, Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

from django.contrib.auth.hashers import make_password
from django.db import DatabaseError, transaction

from apps.core.api.constants import MAX_LIMIT
from apps.core.api.payload_validators import optional_int
from apps.core.services.auth_constants import CATEGORIA_ACCESSO_OPERATORE
from apps.core.services.error_manager import ErrorManager
from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.services.invito_veste import PORTA_OPERATORE, InvitoVeste
from apps.core.services.parameter_service import ParameterService
from apps.core.services.payload_helpers import MISSING, PayloadValidator, translate_db_errors, vincolo_violato
from apps.core.services.service_errors import ServiceError
from apps.core.services.permissions_cache import invalidate_department, invalidate_user
from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository
from apps.amm_software.types import CredenzialePerEmailRow, OperatoreDetailRow

E_AMM_VALIDAZIONE = "E_AMM_VALIDAZIONE"
E_AMM_NOT_FOUND = "E_AMM_OPERATORE_NOT_FOUND"
E_AMM_SCOPE_NON_AMMESSO = "E_AMM_SCOPE_NON_AMMESSO"
# Il vincolo «un profilo per identita'» di `config.profili_accesso_bindings`.
_UQ_BINDING_IDENTITA = "uq_profili_accesso_bindings_identita"

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

# Scopo: Le voci di un PUT di override, validate PRIMA del repository: una
#        lista di oggetti, e in ciascuno i campi che il repository legge con
#        `item["x"]` (`leggi` li estrae col BB, 400 col campo), piu' i campi
#        comuni a ogni override (`motivo`, `valido_dal`, `valido_al`).
# ⛔ `items` ASSENTE e' un 400, non una lista vuota: il repository sostituisce
#    in blocco (DELETE + INSERT), e un corpo `{}` o una chiave sbagliata
#    cancellavano tutti gli override con un 200. La lista vuota ESPLICITA resta
#    il modo di toglierli tutti.
# ⛔ Fino al 2026-10-20 la voce arrivava cruda al repository: una chiave
#    mancante era un KeyError, una voce che non e' un oggetto un AttributeError
#    — cioe' un 500 `E_GENERICO` per un errore di chi chiama.
def _voci_override(
    items: Any, leggi: Callable[[dict[str, Any]], dict[str, Any]],
) -> list[dict[str, Any]]:
    ErrorManager.require(
        isinstance(items, list), code=E_AMM_VALIDAZIONE,
        message="'items' deve essere una lista.", context={"field": "items"},
    )
    voci: list[dict[str, Any]] = []
    for item in items:
        ErrorManager.require(
            isinstance(item, dict), code=E_AMM_VALIDAZIONE,
            message="Ogni voce di 'items' deve essere un oggetto.", context={"field": "items"},
        )
        voci.append({
            **item,
            "motivo": _V_AMM.optional_string(item, "motivo"),
            "valido_dal": _V_AMM.optional_date(item, "valido_dal"),
            "valido_al": _V_AMM.optional_date(item, "valido_al"),
            **leggi(item),
        })
    return voci


_V_AMM = PayloadValidator(validation_code=E_AMM_VALIDAZIONE)


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
                message=ErrorPolicyRegistry.resolve(_E_PROFILO_ULTIMO_SUPER_ADMIN).user_message,
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
        # Un'identita' ha un profilo legato solo: SUPER_ADMIN su un accesso che
        # ne ha gia' un altro e' rifiutato dal vincolo (2026-10-18, madre
        # `config.fn_lega_profilo_identita`). Prima la richiesta spariva in
        # silenzio (`ON CONFLICT DO NOTHING`).
        if vincolo_violato(exc, [_UQ_BINDING_IDENTITA]) is not None:
            raise ServiceError(
                code=E_AMM_VALIDAZIONE,
                message=(
                    "Questo accesso ha gia' un altro profilo legato: per renderlo "
                    "Super Admin va tolto prima quel profilo."
                ),
                detail=msg,
                context={"field": "is_super_admin"},
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
    # In entrambi: username, email, qualifica obbligatori.
    # Contract pubblico Fase 7 multi-face: `is_super_admin?: bool` (default false).
    # ⛔ Regola unica dell'invito (L-3, analisi §4.2): la veste OPERATORE nasce
    # SPENTA e la accende l'attivazione dell'invito; la password non la
    # sceglie l'admin — una credenziale nuova nasce col segnaposto non
    # utilizzabile e la persona la sceglie attivando. Se l'email e' gia' di
    # una credenziale (D-6) la si riusa: la risposta lo dice
    # (`credenziale_riusata`, `username` effettivo) perche' il pannello lo
    # mostri all'admin. ⛔ Il riuso vuole il consenso (`20260925-51`): la
    # prima chiamata va SENZA `riusa_auth_user_id`; sul 409
    # `E_CREDENZIALE_DA_CONFERMARE` il pannello mostra la credenziale trovata e,
    # confermato, rimanda con il suo id. Il service non lo deduce: lo passa.
    def create_operatore(self, payload: dict) -> dict[str, Any]:
        ErrorManager.require(
            "ruolo_sistema" not in payload,
            code=E_AMM_VALIDAZIONE,
            message="Campo 'ruolo_sistema' non ammesso: usa is_super_admin.",
        )
        # Rifiuto esplicito, non silenzio: un client che la manda ancora
        # crederebbe che valga.
        ErrorManager.require(
            "password" not in payload,
            code=E_AMM_VALIDAZIONE,
            message="Campo 'password' non ammesso: la sceglie l'operatore attivando l'invito.",
            context={"field": "password"},
        )
        # ⚠️ Letti dal BB: un non-stringa e' un 400 sul campo; con
        #    `(payload.get(k) or "").strip()` era un AttributeError, cioe' un 500.
        _v = _V_AMM
        soggetto_id = _v.optional_string(payload, "soggetto_id")
        username = _v.optional_string(payload, "username") or ""
        email = _v.optional_string(payload, "email") or ""
        raw_qualifica = payload.get("qualifica_id")

        # Guard UUID soggetto_id (flusso B)
        if soggetto_id:
            try:
                uuid_mod.UUID(soggetto_id)
            except ValueError as exc:
                ErrorManager.raise_error(code=E_AMM_VALIDAZIONE, message="UUID soggetto non valido.", context={"field": "soggetto_id"}, cause=exc)

        # Guard qualifica_id numerico
        try:
            qualifica_id = int(raw_qualifica) if raw_qualifica is not None else None
        except (ValueError, TypeError):
            qualifica_id = None

        # Validazione comune (entrambi i flussi)
        ErrorManager.require(bool(username), code=E_AMM_VALIDAZIONE, message="Username obbligatorio.", context={"field": "username"})
        ErrorManager.require(bool(email), code=E_AMM_VALIDAZIONE, message="Email obbligatoria.", context={"field": "email"})
        ErrorManager.require(qualifica_id is not None and qualifica_id > 0, code=E_AMM_VALIDAZIONE, message="Qualifica obbligatoria.", context={"field": "qualifica_id"})

        # Validazione flusso A: dati persona obbligatori solo se soggetto nuovo
        cognome = _v.optional_string(payload, "cognome") or ""
        nome = _v.optional_string(payload, "nome") or ""
        codice_fiscale = _v.optional_string(payload, "codice_fiscale") or ""
        sesso = _v.optional_upper(payload, "sesso")

        if not soggetto_id:
            ErrorManager.require(bool(cognome), code=E_AMM_VALIDAZIONE, message="Cognome obbligatorio per soggetto nuovo.", context={"field": "cognome"})
            ErrorManager.require(bool(nome), code=E_AMM_VALIDAZIONE, message="Nome obbligatorio per soggetto nuovo.", context={"field": "nome"})
            ErrorManager.require(bool(codice_fiscale), code=E_AMM_VALIDAZIONE, message="Codice fiscale obbligatorio per soggetto nuovo.", context={"field": "codice_fiscale"})
            # ⛔ Il sesso NON si controlla qui, e non ha default (decisione di
            #    Tid, 2026-10-09; fino a quel giorno `DEFAULT_SESSO = "M"`).
            #    Il flusso A crea un privato (PR, `sesso_policy = REQUIRED`): il
            #    rifiuto del sesso mancante arriva dal guard
            #    `trgfn_soggetti_guard_sesso_policy`, prima del consenso al riuso,
            #    con il campo acceso dal canale `COLUMN`. Una copia qui ammetteva
            #    solo M/F, mentre `X` («non si puo' stabilire») e' un valore.

        # Contract Fase 7: il caller passa `is_super_admin` (default False).
        # Il caller non puo' creare DISABILITATI via questo endpoint: la
        # disabilitazione e' un comando dedicato. La traduzione verso
        # l'enum legacy della fn DB e' incapsulata nel repository.
        # ⛔ Dal BB, non `bool(...)`: `bool("false")` e' True, e una stringa
        #    nel corpo creava un SUPER_ADMIN. Un non-booleano e' un 400 sul campo.
        is_super_admin = _v.optional_bool(payload, "is_super_admin") is True

        creato = self._repo.crea_operatore(
            soggetto_id=soggetto_id,
            cognome=cognome or None,
            nome=nome or None,
            codice_fiscale=codice_fiscale or None,
            username=username,
            email=email,
            # Segnaposto non utilizzabile: la password la sceglie la persona.
            password_hash=make_password(None),
            qualifica_id=qualifica_id,  # type: ignore[arg-type]
            unita_organizzativa_id=int(payload["unita_organizzativa_id"]) if payload.get("unita_organizzativa_id") else None,
            data_nascita=payload.get("data_nascita"),
            # Col soggetto esistente (flusso B) il DB non lo legge.
            sesso=sesso if not soggetto_id else None,
            is_super_admin=is_super_admin,
            valido_dal=payload.get("valido_dal"),
            valido_al=payload.get("valido_al"),
            comune_nascita_id=optional_int(payload, "comune_nascita_id"),
            indirizzo_resid_dettaglio_id=optional_int(payload, "indirizzo_resid_dettaglio_id"),
            indirizzo_domfisc_dettaglio_id=optional_int(payload, "indirizzo_domfisc_dettaglio_id"),
            riusa_auth_user_id=optional_int(payload, "riusa_auth_user_id"),
        )
        dettaglio: Mapping[str, Any] = self._repo.get_operatore_detail(creato["auth_user_id"]) or {}
        return {**dettaglio, "credenziale_riusata": creato["credenziale_riusata"]}

    # Scopo: Dettaglio operatore con validazione esistenza.
    # ⛔ Un operatore e' una credenziale di categoria OPERATORE
    #    (`script.fn_categoria_accesso`, R-DB-A1). Le altre — una macchina, un
    #    cliente del portale — rispondono 404 come un id inesistente: i comandi
    #    di questa porta spengono e riaccendono la veste operatore, e su un
    #    utente tecnico la troverebbero (dal 2026-10-02 la sua veste e'
    #    `OPERATORE` con `tecnica`, e non la distingue piu' la risorsa umana).
    #    Fermerebbero un processo automatico all'insaputa del suo pannello (A-6).
    def get_operatore(self, auth_user_id: int) -> OperatoreDetailRow:
        operatore = None
        if self._repo.get_categoria_accesso(auth_user_id) == CATEGORIA_ACCESSO_OPERATORE:
            operatore = self._repo.get_operatore_detail(auth_user_id)
        ErrorManager.require(operatore is not None, code=E_AMM_NOT_FOUND, message=f"Operatore {auth_user_id} non trovato.")
        assert operatore is not None
        return operatore

    # Scopo: Aggiorna operatore e invalida cache permessi.
    # Contract pubblico Fase 7 multi-face:
    #   {is_super_admin?: bool, attivo?: bool, email?, first_name?, last_name?,
    #    unita_organizzativa_id?, valido_al?: date | null}
    # `valido_al` e' la fine del RAPPORTO: `null` la toglie, assente non la tocca.
    # `is_super_admin` e `attivo` sono ortogonali: ognuno puo' essere
    # presente da solo (NO-OP per il flag mancante). Il guard "ultimo super
    # admin" e' centralizzato sul trigger DB; il service traduce l'errore in
    # `E_PROFILO_ULTIMO_SUPER_ADMIN`.
    def update_operatore(self, auth_user_id: int, payload: dict) -> OperatoreDetailRow | dict[str, Any]:
        ErrorManager.require(
            "ruolo_sistema" not in payload,
            code=E_AMM_VALIDAZIONE,
            message="Campo 'ruolo_sistema' non ammesso: usa is_super_admin + attivo.",
        )
        operatore = self.get_operatore(auth_user_id)  # verifica esistenza
        veste_attiva = operatore.get("veste_attiva") is True
        # I due flag dal BB: un non-booleano e' un 400 sul campo. Prima i
        # confronti `is True`/`is False` lasciavano cadere una stringa in
        # silenzio, e il PATCH rispondeva 200 senza aver fatto niente.
        _v = _V_AMM
        attivo = _v.optional_bool(payload, "attivo")
        is_super_admin = _v.optional_bool(payload, "is_super_admin")
        # ⛔ D-3 (Tid, 2026-09-24/2026-10-04): l'accesso NON si riaccende da
        #    qui. Un operatore spento si riattiva col reinvio dell'invito, che
        #    riapre il rapporto, e la veste la accende la persona attivando:
        #    nessuna veste torna attiva senza che la persona lo sappia.
        #    Fino al 2026-10-04 `attivo: true` la riaccendeva subito, e cosi'
        #    l'endpoint `…/riattiva/`, ritirato lo stesso giorno.
        ErrorManager.require(
            not (attivo is True and not veste_attiva),
            code=E_AMM_VALIDAZIONE,
            message="L'accesso si riattiva col reinvio dell'invito, non dall'interruttore.",
            context={"field": "attivo", "auth_user_id": auth_user_id},
        )
        # `attivo` conta solo come TRANSIZIONE da accesa a spenta: il drawer lo
        # manda a ogni salvataggio, e ripeterlo non e' un gesto. `true` su una
        # veste accesa non cambia niente; `false` su una veste gia' spenta
        # (spenta da poco, o mai attivata e in attesa dell'invito) non deve
        # chiudere il rapporto che l'invito ha appena riaperto.
        spegni = attivo is False and veste_attiva
        # La data di fine del RAPPORTO: assente non si tocca, `null` la toglie
        # (§10 del brief-db-veste-utilizzabile). Il formato lo controlla il
        # validator; l'ordine con `valido_dal` e l'ultimo SUPER_ADMIN senza
        # scadenza li giudica il DB (`trgfn_guard_date_validita`,
        # `trgfn_risorse_umane_guard_ultimo_super_admin`).
        valido_al = (
            _V_AMM.optional_date(payload, "valido_al")
            if "valido_al" in payload else MISSING
        )

        def _aggiorna() -> None:
            self._repo.update_operatore(
                auth_user_id,
                email=payload.get("email"),
                first_name=payload.get("first_name"),
                last_name=payload.get("last_name"),
                is_super_admin=is_super_admin,
                unita_organizzativa_id=payload.get("unita_organizzativa_id"),
                valido_al=valido_al,
            )

        # ⛔ Spegnere dall'interruttore E' «Disabilita» (Tid, 2026-10-04):
        #    la stessa scrittura del repository — veste spenta, rapporto
        #    chiuso con `valido_al = oggi`, sync di `is_active`. Fino a quel
        #    giorno l'interruttore ne aveva una sua, che lasciava `valido_al`
        #    com'era. Dopo i campi: se il payload porta anche `valido_al`, la
        #    chiusura del rapporto vince, come su «Disabilita».
        def _aggiorna_e_spegni() -> None:
            _aggiorna()
            self._repo.disabilita_operatore(auth_user_id)

        # ⛔ L'interruttore «Accesso attivo» spento e' uno spegnimento come
        #    «Disabilita» (A-5): inviti, sessioni e cache della veste operatore,
        #    e solo di quella. Fino al 2026-10-02 invalidava la sola cache.
        # ⛔ Solo quando la veste PASSA da accesa a spenta (`veste_attiva`).
        #    Il drawer manda `attivo` a OGNI salvataggio: su un operatore gia'
        #    spento, correggere l'email arriva con `attivo: false` invariato, e
        #    trattarlo da spegnimento invaliderebbe l'invito appena spedito per
        #    riaccenderlo (D-3). Un salvataggio non e' un gesto di revoca.
        if spegni:
            self._spegni_veste_operatore(auth_user_id, _aggiorna_e_spegni)
        else:
            _run_or_raise_super_admin_guard(_aggiorna)
            invalidate_user(auth_user_id)
        return self._repo.get_operatore_detail(auth_user_id) or {}

    # Scopo: Spegne la veste operatore con `spegni` e ne chiude cio' che resta
    #        aperto (inviti, sessioni, cache: `InvitoVeste.chiudi_veste_spenta`),
    #        in UNA transazione: la strada unica di «Disabilita» e
    #        dell'interruttore (regola del 2, 2026-10-02).
    # ⛔ Gli inviti pendenti si invalidano come per portale e shop (A-5,
    #    2026-10-02): fino a quel giorno un operatore disabilitato con un
    #    invito in volo poteva ancora attivarlo, e l'attivazione riaccendeva la
    #    veste che l'amministratore aveva appena spento.
    # ⛔ Si chiudono le sessioni della SOLA veste operatore (D-5,
    #    `blocca_token_sessioni` per `identita_id`): la stessa credenziale puo'
    #    avere una veste shop o portale, che resta accesa e connessa. Fino al
    #    2026-10-02 «Disabilita» chiudeva tutte le sessioni della credenziale.
    #    L'id si legge PRIMA di spegnere: e' quello della veste che si spegne.
    # ⛔ Una revoca fallita PROPAGA e annulla anche lo spegnimento
    #    (2026-09-26): l'amministratore riprova su uno stato intero.
    # ⚠️ La cache dei permessi si invalida a COMMIT avvenuto: invalidata
    #    prima, una richiesta concorrente la ricaricherebbe dallo stato
    #    ancora attivo.
    def _spegni_veste_operatore(self, auth_user_id: int, spegni: Callable[[], None]) -> None:
        with transaction.atomic():
            veste_id = self._repo.get_veste_operatore_id(auth_user_id)
            _run_or_raise_super_admin_guard(spegni)
            if veste_id is not None:
                InvitoVeste().chiudi_veste_spenta(
                    PORTA_OPERATORE, auth_user_id=auth_user_id, identita_id=veste_id,
                )
            else:
                transaction.on_commit(lambda: invalidate_user(auth_user_id))

    # Scopo: Disabilita operatore, invalida cache e chiude le sessioni della
    # sua veste operatore (non quelle delle altre vesti della credenziale).
    # Preview UX `can_disable=false` evita il round-trip DB nel 99% dei casi
    # (single source of truth: `script.fn_check_ultimo_super_admin_attivo`
    # consumata da `fn_get_operatore_detail`). L'autorita' finale resta il
    # trigger DB `trgfn_profili_accesso_bindings_guard_ultimo_super_admin`
    # che intercetta anche le race tra sessioni: traduciamo l'errore in
    # `E_PROFILO_ULTIMO_SUPER_ADMIN`.
    def disabilita_operatore(self, auth_user_id: int) -> OperatoreDetailRow | dict[str, Any]:
        operatore = self.get_operatore(auth_user_id)
        # ⛔ `disable_reason` e' un CODICE (`ULTIMO_SUPER_ADMIN`, §16 del
        #    brief blocco-login), non una spiegazione: non si ricopia nel
        #    `detail`. Viaggia nel contesto, per il log. Il messaggio e'
        #    quello del catalogo, come nella traduzione del trigger: preview e
        #    autorita' dicono la stessa frase.
        if operatore.get("can_disable") is False:
            raise ServiceError(
                code=_E_PROFILO_ULTIMO_SUPER_ADMIN,
                message=ErrorPolicyRegistry.resolve(_E_PROFILO_ULTIMO_SUPER_ADMIN).user_message,
                detail="Deve esistere almeno un super admin attivo nel sistema.",
                context={
                    "auth_user_id": auth_user_id,
                    "reason": operatore.get("disable_reason"),
                },
            )
        # Disattivazione e chiusura delle sessioni della veste operatore in
        # UNA transazione: `_spegni_veste_operatore`.
        self._spegni_veste_operatore(
            auth_user_id, lambda: self._repo.disabilita_operatore(auth_user_id)
        )
        return self._repo.get_operatore_detail(auth_user_id) or {}

    # ⛔ Niente `riattiva_operatore` (ritirato il 2026-10-04, D-3): un
    #    operatore spento si riattiva col reinvio dell'invito
    #    (`InvitoOperatoreService.invia_invito`).

    # =================================================================
    # Override permessi
    # =================================================================

    # Scopo: Salva override aree e invalida cache.
    def put_override_aree(self, auth_user_id: int, items: list) -> list:
        # ⛔ Prima la guardia di `get_operatore`: l'id dev'essere un OPERATORE.
        #    Senza, un id di macchina o di cliente del portale riceveva override
        #    (PUT) o una lista vuota (GET) invece del 404 delle altre rotte
        #    `operatori/{id}/`.
        self.get_operatore(auth_user_id)
        items = _voci_override(items, lambda it: {
            "area_id": _V_AMM.require_positive_int(it, "area_id"),
            "livello": _V_AMM.require_string(it, "livello"),
        })
        # Cio' che solo il DB sa giudicare — un `livello` fuori dall'enum, un
        # `area_id` inesistente, la stessa area due volte — e' un 400, non il
        # 500 di un errore DB nudo (come `put_override_oggetti`).
        with translate_db_errors(
            context={"op": "amm_software.put_override_aree"},
            fallback_code=E_AMM_VALIDAZIONE,
            fallback_message="Override aree non salvati.",
            unique_constraints={
                "uq_user_override_aree_user_area": (E_AMM_VALIDAZIONE, "La stessa area compare due volte."),
            },
            fk_constraints={
                "fk_user_override_aree_area": (E_AMM_VALIDAZIONE, "Area inesistente."),
            },
        ):
            self._repo.put_override_aree(auth_user_id, items)
        invalidate_user(auth_user_id)
        return self._repo.get_override_aree(auth_user_id)

    # Scopo: Salva override azioni e invalida cache.
    def put_override_azioni(self, auth_user_id: int, items: list) -> list:
        self.get_operatore(auth_user_id)  # vedi `put_override_aree`
        items = _voci_override(items, lambda it: {
            "azione_id": _V_AMM.require_positive_int(it, "azione_id"),
            "abilitata": _V_AMM.require_bool(it, "abilitata"),
        })
        with translate_db_errors(  # vedi `put_override_aree`
            context={"op": "amm_software.put_override_azioni"},
            fallback_code=E_AMM_VALIDAZIONE,
            fallback_message="Override azioni non salvati.",
            unique_constraints={
                "uq_user_override_azioni_user_azione": (E_AMM_VALIDAZIONE, "La stessa azione compare due volte."),
            },
            fk_constraints={
                "fk_user_override_azioni_azione": (E_AMM_VALIDAZIONE, "Azione inesistente."),
            },
        ):
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

    # Scopo: La credenziale di un'email (username e vesti) per il dialog di
    #        conferma del riuso: il pannello la mostra sul 409
    #        E_CREDENZIALE_DA_CONFERMARE e, confermato, rimanda la creazione
    #        con il suo `auth_user_id`. None = l'email non ha credenziale.
    def get_credenziale_per_email(self, email: str | None) -> CredenzialePerEmailRow | None:
        return self._repo.get_credenziale_per_email(email)

    # Scopo: Lista operatori con filtri.
    def list_operatori(self, **params) -> tuple[list, int]:
        return self._repo.list_operatori(**params)

    # Scopo: Lista override aree.
    def get_override_aree(self, auth_user_id: int) -> list:
        self.get_operatore(auth_user_id)  # vedi `put_override_aree`
        return self._repo.get_override_aree(auth_user_id)

    # Scopo: Lista override azioni.
    def get_override_azioni(self, auth_user_id: int) -> list:
        self.get_operatore(auth_user_id)  # vedi `put_override_aree`
        return self._repo.get_override_azioni(auth_user_id)

    # Scopo: Salva override oggetti e invalida cache.
    #        Valida che ogni app_label+model_name esista nel catalogo
    #        area_model_overrides E sia override-abile (capability `can_override`
    #        — Fase 8). I model riservati al kernel permessi sono rifiutati
    #        anche se registrati in catalogo.
    # ⭐ Il controllo qui serve al MESSAGGIO (nomina l'oggetto e il perche');
    #    il rifiuto vero e' del DB, la FK composita
    #    `fk_user_override_oggetti_catalogo` (D-4, `20260928-02`), che vale
    #    anche per una scrittura che non passa da qui. Se il catalogo cambia fra
    #    la lettura e la scrittura, la FK risponde col suo 23503: tradotto nello
    #    stesso `E_AMM_VALIDAZIONE`, non un 500.
    def put_override_oggetti(self, auth_user_id: int, items: list) -> list:
        self.get_operatore(auth_user_id)  # vedi `put_override_aree`
        # `app_label`/`model_name` li giudica il catalogo qui sotto.
        items = _voci_override(items, lambda it: {
            "livello": _V_AMM.require_string(it, "livello"),
        })
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
                    code=E_AMM_VALIDAZIONE,
                    message=f"Model {key[0]}.{key[1]} non registrato nel catalogo override.",
                )
                ErrorManager.require(
                    key in overridable,
                    code=E_AMM_VALIDAZIONE,
                    message=f"Model {key[0]}.{key[1]} riservato: override non ammesso.",
                )
        with translate_db_errors(
            context={"op": "amm_software.put_override_oggetti"},
            fallback_code=E_AMM_VALIDAZIONE,
            fallback_message="Override oggetti non salvati.",
            fk_constraints={
                "fk_user_override_oggetti_catalogo": (
                    E_AMM_VALIDAZIONE,
                    "Oggetto non a catalogo o riservato: override non ammesso.",
                ),
            },
        ):
            self._repo.put_override_oggetti(auth_user_id, items)
        invalidate_user(auth_user_id)
        return self._repo.get_override_oggetti(auth_user_id)

    # Scopo: Lista override oggetti.
    def get_override_oggetti(self, auth_user_id: int) -> list:
        self.get_operatore(auth_user_id)  # vedi `put_override_aree`
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

    # Scopo: Lista paginata dei reparti (`amm.reparti`): (righe, totale).
    def list_reparti(self, **params) -> tuple[list, int]:
        return self._repo.list_reparti(**params)

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

    # Scopo: I permessi EFFETTIVI dell'operatore su azioni e oggetti, col
    #        tetto d'area gia' applicato a DB (brief-db-permessi-tetto-area).
    # ⚠️ `get_operatore` prima, per la stessa ragione di
    #    `get_permessi_ereditati`: su un id inesistente il DB risponderebbe
    #    «tutto negato / BLOCCATO» (niente identita' OPERATORE), plausibile e
    #    sbagliato al posto di un errore.
    def get_permessi_effettivi(self, auth_user_id: int) -> dict:
        self.get_operatore(auth_user_id)
        return self._repo.get_permessi_effettivi(auth_user_id)

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
    ) -> dict[str, Any]:
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
    def list_emittente_rounding_modes(self) -> list[dict[str, Any]]:
        return [
            {"codice": codice, "descrizione": descrizione, "ordering": ordering}
            for codice, descrizione, ordering in _ROUNDING_MODE_DESCRIZIONI_EMITTENTE
        ]

    # =================================================================
    # Profili reparto
    # =================================================================

    # Scopo: Salva profilo reparto e invalida cache di tutti gli operatori del reparto.
    #        `richiede_secondo_fattore` letto dal corpo: assente = invariato; se
    #        c'e' dev'essere un booleano (brief sicurezza §3.4-bis, T-3).
    def put_profilo_reparto(
        self, uo_id: int, aree: list, azioni: list, *, payload: dict[str, Any] | None = None,
    ) -> dict:
        richiede_secondo_fattore = _V_AMM.optional_bool(
            payload or {}, "richiede_secondo_fattore",
        )
        self._repo.put_profilo_reparto(
            uo_id, aree, azioni, richiede_secondo_fattore=richiede_secondo_fattore,
        )
        invalidate_department(uo_id)
        return self._repo.get_profilo_reparto(uo_id)

    # =================================================================
    # Riepilogo permessi
    # =================================================================

    # Scopo: Riepilogo permessi per area degli operatori indicati (le righe
    #        di una pagina della lista operatori). Gli id arrivano gia' interi
    #        dalla view; qui si tiene il tetto, perche' la funzione DB fa tre
    #        letture per operatore.
    def get_permessi_riepilogo(self, auth_user_ids: list[int]) -> list[dict[str, Any]]:
        ErrorManager.require(
            len(auth_user_ids) <= MAX_LIMIT,
            code=E_AMM_VALIDAZIONE,
            message=f"Al massimo {MAX_LIMIT} operatori per richiesta.",
            context={"parametro": "auth_user_ids"},
        )
        return self._repo.get_permessi_riepilogo(auth_user_ids)

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


