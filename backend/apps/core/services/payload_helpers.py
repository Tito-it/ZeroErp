# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper condivisi per la validazione di payload nei service admin
#        CRUD. Estratti da categorie_clienti_service, utilities_tipi_ruolo_service,
#        tipi_ruolo_tipi_indirizzo_service (pattern duplicato in 3 service, in
#        crescita con la Fase 2 v5 listini).
#
#        Riferimento: docs/it/dev/work-in-progress/sviluppo-listini-v6.md §2.2
#        (V6-B1).
#
#        Nota: listini_service.py usa helper a livello modulo con firme diverse
#        (function_name + log_to_db per-chiamata, necessari per orchestrazione
#        pipeline). La sua migrazione a PayloadValidator e' deferita: richiede
#        un overload che accetti function_name/log_to_db per-chiamata, fuori
#        scope di questo primo sprint V6-B1.
# ------------------------------------------------------------

from __future__ import annotations

import json
import re
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping
from contextlib import contextmanager
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, NoReturn, TypeVar
from uuid import UUID

from django.db import DatabaseError, IntegrityError

from apps.core.db._helpers import order_dir_ammessa
from apps.core.services.db_error_fields import APP_ERROR_CODE_RE, diagnostica_db
from apps.core.services.error_manager import ErrorManager
from apps.core.services.value_normalizer import empty_to_none


# Regex per int firmato: segno opzionale seguito da almeno una cifra.
# Evita che lstrip("-") accetti stringhe degeneri tipo "--5" o "---0".
_SIGNED_INT_RE = re.compile(r"^-?\d+$")


# Costanti range per smallint PostgreSQL (INT2): [-32768, 32767]. I service
# admin tipicamente restringono a valori non negativi: un ordinamento < 0 non
# ha semantica UI.
SMALLINT_MIN = -32768
SMALLINT_MAX = 32767
SMALLINT_UNSIGNED_MIN = 0
# Range di integer (INT4) e bigint (INT8) PostgreSQL. ⚠️ Un intero Python fuori
# dal tipo di un PARAMETRO di funzione o di un cast non e' un «nessun risultato»:
# psycopg lo manda come bigint (o numeric) e la chiamata fallisce a DB, un 500.
# Li usa `qp_int_optional` (payload_validators) per il tetto del parametro.
INTEGER_MIN = -2_147_483_648
INTEGER_MAX = 2_147_483_647
BIGINT_MIN = -9_223_372_036_854_775_808
BIGINT_MAX = 9_223_372_036_854_775_807


# Sentinel per distinguere "chiave assente" (non aggiornare) da "valore None
# esplicito" (reset) nei PATCH parziali. Oggetto unico modulo-level: i chiamanti
# fanno `is MISSING`, quindi va condiviso (no istanze per-modulo divergenti).
class MissingType:
    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover
        return "<MISSING>"


MISSING = MissingType()

# Il tipo della voce letta da `PayloadValidator.voci`.
_T = TypeVar("_T")


class PayloadValidator:
    """Validator parametrizzato per `validation_code` di dominio.

    Ogni service CRUD admin crea un'istanza con il proprio codice errore
    (es. `E_ANAG_VALIDAZIONE`, `E_CONFIG_VALIDATION`) e chiama i metodi
    di estrazione/validazione per normalizzare il payload in ingresso.

    I metodi preservano la semantica dei helper privati pre-estrazione
    nei 3 service originali: rigore sui tipi (bool != int, int != float,
    stringhe numeriche ammesse solo per gli id), errori strutturati via
    ErrorManager, niente default impliciti.

    Parametri opzionali `log_to_db` e `function_name` (estensione V6-B2)
    abilitano il logging DB dei ServiceError via `script.fn_log_error_only`,
    utile per service con orchestrazione pipeline (es. listini). Default
    False/None: comportamento invariato per i service CRUD admin che non
    necessitano telemetria DB.
    """

    # Scopo: Inizializza il validator con il codice errore del dominio.
    #        `log_to_db` e `function_name` sono default di istanza; ogni
    #        metodo li accetta anche come override per-chiamata.
    def __init__(
        self,
        *,
        validation_code: str,
        log_to_db: bool = False,
        function_name: str | None = None,
    ) -> None:
        self._code = validation_code
        self._log_to_db = log_to_db
        self._function_name = function_name

    # Scopo: Compone i kwargs comuni da passare a ErrorManager.require/raise
    #        risolvendo override per-chiamata con fallback agli istance default.
    def _em_kwargs(
        self,
        *,
        log_to_db: bool | None,
        function_name: str | None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        effective_log = self._log_to_db if log_to_db is None else log_to_db
        if effective_log:
            kwargs["log_to_db"] = True
        effective_fn = function_name if function_name is not None else self._function_name
        if effective_fn is not None:
            kwargs["function_name"] = effective_fn
        return kwargs

    # =================================================================
    # Whitelist chiavi payload
    # =================================================================

    # Scopo: Verifica che tutte le chiavi del payload siano nella whitelist.
    def validate_allowed_keys(
        self,
        payload: dict[str, Any],
        *,
        allowed: frozenset[str],
        message: str = "Payload non valido.",
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> None:
        unknown = sorted(k for k in payload if k not in allowed)
        ErrorManager.require(
            not unknown,
            code=self._code,
            message=message,
            detail=f"Campi non supportati: {', '.join(unknown)}",
            context={
                "unknown_keys": unknown,
                "allowed_keys": sorted(allowed),
            },
            **self._em_kwargs(log_to_db=log_to_db, function_name=function_name),
        )

    # Scopo: Il CONTRATTO di un payload di scrittura in un gesto solo: una
    #        chiave fuori `ammesse` e' un 400 (`validate_allowed_keys`), e si
    #        restituisce il dict da scrivere, coi vuoti normalizzati a None
    #        (`empty_to_none`).
    #        `colonne`: quando le chiavi ammesse sono PIU' delle colonne scritte
    #        (la mappa `componenti_overrides` di una riga, letta a parte), il
    #        dict tiene le sole colonne; assente, tiene tutte le ammesse.
    # ⭐ Regola del 2 (ok Tid 2026-10-20): le due righe «controlla, poi filtra»
    #    erano ricopiate in 13 punti di ordini, resi e DDT, ciascuna con lo
    #    stesso commento incollato sopra. Una chiave ignota scartata in silenzio
    #    era il difetto che le aveva fatte nascere (brief-be-verifica-
    #    documentazione-api §3.22): qui il controllo e il filtro non si separano.
    def solo_chiavi_ammesse(
        self,
        payload: dict[str, Any],
        *,
        ammesse: frozenset[str],
        colonne: frozenset[str] | None = None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> dict[str, Any]:
        self.validate_allowed_keys(
            payload, allowed=ammesse, log_to_db=log_to_db, function_name=function_name,
        )
        tenute = ammesse if colonne is None else colonne
        return {k: empty_to_none(v) for k, v in payload.items() if k in tenute}

    # =================================================================
    # Whitelist colonne ORDER BY
    # =================================================================

    # Scopo: Valida che `order_by` sia nella whitelist di colonne ammesse E
    #        che `order_dir`, se indicato, sia una direzione riconosciuta.
    #        Coerente con policy anti-SQL-injection sui parametri di
    #        ordinamento lista (ogni repo ha la sua _ORDER_COLS).
    # ⛔ `order_dir` e' OBBLIGATORIO come argomento (2026-09-26): fino a quel
    #    giorno questo metodo guardava la sola colonna, e i sette service che
    #    lo usavano — alcuni con il commento «validazione order_by/dir» sopra —
    #    lasciavano passare `?order_dir=giu`, che il repository trasformava in
    #    ASC. Renderlo obbligatorio fa si' che chi valida la colonna non possa
    #    dimenticare la direzione.
    # ⭐ Il predicato e' `order_dir_ammessa` del BB SQL, non una copia di
    #    `{asc, desc}`: il service rifiuta ESATTAMENTE cio' che il repository
    #    rifiuterebbe (maiuscole e spazi ammessi, assente = default), solo con
    #    il codice di dominio invece del generico `E_VALIDATION_INPUT`.
    def validate_order_by(
        self,
        order_by: str,
        *,
        allowed: frozenset[str],
        order_dir: str | None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> None:
        ErrorManager.require(
            order_by in allowed,
            code=self._code,
            message="Parametri ordinamento non validi.",
            detail=f"order_by deve essere uno tra: {', '.join(sorted(allowed))}",
            context={"order_by": order_by},
            **self._em_kwargs(log_to_db=log_to_db, function_name=function_name),
        )
        ErrorManager.require(
            order_dir_ammessa(order_dir),
            code=self._code,
            message="Parametri ordinamento non validi.",
            detail="order_dir deve essere 'asc' o 'desc'",
            context={"order_dir": order_dir},
            **self._em_kwargs(log_to_db=log_to_db, function_name=function_name),
        )

    # =================================================================
    # Chiavi rifiutate (FK immutabili / campi read-only in PATCH)
    # =================================================================

    # Scopo: Rifiuta la presenza di chiavi vietate nel payload (es. FK
    #        dimensionali immutabili in PATCH). Complementare a
    #        `validate_allowed_keys`: e' usato prima del check whitelist
    #        per dare un messaggio di dominio piu' specifico ("sono
    #        immutabili") invece di "campi non supportati".
    def reject_keys(
        self,
        payload: dict[str, Any],
        *,
        forbidden: frozenset[str],
        reason: str,
        detail_prefix: str = "Campi non modificabili",
        context_extra: dict[str, Any] | None = None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> None:
        present = sorted(k for k in payload if k in forbidden)
        ctx: dict[str, Any] = {"forbidden_keys": present}
        if context_extra:
            ctx.update(context_extra)
        ErrorManager.require(
            not present,
            code=self._code,
            message=reason,
            detail=f"{detail_prefix}: {', '.join(present)}" if present else None,
            context=ctx,
            **self._em_kwargs(log_to_db=log_to_db, function_name=function_name),
        )

    # =================================================================
    # Guard su id esistenti (non da payload)
    # =================================================================

    # Scopo: Verifica che un id passato come parametro sia int positivo.
    #        bool esplicitamente rifiutato (isinstance(True, int) == True).
    def guard_positive_int(
        self,
        value: Any,
        *,
        field: str,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> None:
        ErrorManager.require(
            isinstance(value, int) and not isinstance(value, bool) and value > 0,
            code=self._code,
            message=f"Identificatore '{field}' non valido.",
            context={field: value},
            **self._em_kwargs(log_to_db=log_to_db, function_name=function_name),
        )

    # ⛔ `guard_non_empty_string` ritirato il 2026-11-08 (Tid): il suo ultimo
    #    consumatore era l'uid della sorgente in `genera_documento`, che dal
    #    giro D.1 di brief-db-sorgente-documento-e-riga riceve l'id. La
    #    motivazione delle offerte, il caso precedente, la chiede il verbo DB
    #    dal 2026-10-26.

    # Scopo: un aggiornamento deve portare almeno un campo da scrivere: un PATCH
    #        vuoto e' una richiesta malformata (400), MAI un «salvato» che non
    #        ha scritto niente, e mai un 404 su un record che esiste.
    #        `data` sono i campi GIA' estratti per la scrittura (dopo whitelist
    #        e normalizzazione: una chiave presente col valore None e' un
    #        reset, quindi conta). `sotto_oggetti` i satelliti scritti nella
    #        stessa richiesta (es. la scheda `utility` di offerta e contratto):
    #        contano solo se portano almeno una chiave — `{"utility": {}}` non
    #        e' una modifica.
    # Perimetro: si chiama PRIMA della scrittura. ⛔ Non dal rowcount del
    #        repository dopo l'UPDATE: «zero righe» confonde il payload vuoto
    #        col record sparito, ed e' cosi' che PATCH vuoti uscivano 404.
    # ⭐ BB per la regola del 2 (2026-10-14, ok Tid): la stessa regola era
    #    scritta a mano in ~45 punti di 25 service, con 13 codici, quattro
    #    formulazioni, e alcuni dopo la scrittura. Il codice resta quello del
    #    dominio (`validation_code` dell'istanza).
    def require_campi_da_aggiornare(
        self,
        data: Mapping[str, Any],
        *,
        sotto_oggetti: Mapping[str, Any] | None = None,
        message: str = "Nessun campo aggiornabile presente nel payload.",
        detail: str | None = None,
        context: dict[str, Any] | None = None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> None:
        satelliti = sotto_oggetti or {}
        ErrorManager.require(
            bool(data) or any(isinstance(v, Mapping) and bool(v) for v in satelliti.values()),
            code=self._code,
            message=message,
            detail=detail,
            context=context,
            **self._em_kwargs(log_to_db=log_to_db, function_name=function_name),
        )

    # =================================================================
    # Estrazione stringhe
    # =================================================================

    # Scopo: Estrae una stringa obbligatoria dal payload con trim e cap lunghezza.
    #        Stringa vuota o whitespace-only rifiutata. `max_len=None` disabilita
    #        il controllo lunghezza (usato da service che validano solo la
    #        presenza/non-vuotezza, lasciando il bound alla DB).
    def require_string(
        self,
        payload: dict[str, Any],
        key: str,
        *,
        max_len: int | None = None,
        message: str | None = None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> str:
        em = self._em_kwargs(log_to_db=log_to_db, function_name=function_name)
        base_message = message or f"Campo '{key}' obbligatorio."
        raw = payload.get(key)
        ErrorManager.require(
            isinstance(raw, str) and raw.strip() != "",
            code=self._code,
            message=base_message,
            detail=f"{key} obbligatorio e non vuoto." if message else None,
            context={key: raw, "field": key},
            **em,
        )
        assert isinstance(raw, str)
        value = raw.strip()
        if max_len is not None:
            ErrorManager.require(
                len(value) <= max_len,
                code=self._code,
                message=message or f"Campo '{key}' troppo lungo.",
                detail=f"Lunghezza massima: {max_len} caratteri.",
                context={key: value, "len": len(value), "field": key},
                **em,
            )
        return value

    # Scopo: Estrae stringa opzionale dal payload con normalizzazione
    #        empty -> None (pattern null_vs_empty: backend tratta stringa
    #        vuota e null come equivalenti, ma normalizza sempre a NULL).
    #        Ritorna None se chiave assente, valore None esplicito, o
    #        stringa vuota dopo strip. Cap lunghezza opzionale via
    #        `max_len`.
    def optional_string(
        self,
        payload: dict[str, Any],
        key: str,
        *,
        max_len: int | None = None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> str | None:
        if key not in payload:
            return None
        raw = payload[key]
        if raw is None:
            return None
        em = self._em_kwargs(log_to_db=log_to_db, function_name=function_name)
        ErrorManager.require(
            isinstance(raw, str),
            code=self._code,
            message=f"Campo '{key}' deve essere una stringa o null.",
            detail=f"Tipo ricevuto: {type(raw).__name__}",
            context={key: raw, "field": key},
            **em,
        )
        assert isinstance(raw, str)
        value = raw.strip()
        if value == "":
            return None
        if max_len is not None:
            ErrorManager.require(
                len(value) <= max_len,
                code=self._code,
                message=f"Campo '{key}' troppo lungo.",
                detail=f"Lunghezza massima: {max_len} caratteri.",
                context={key: value, "len": len(value), "field": key},
                **em,
            )
        return value

    # Scopo: Codice a vocabolario MAIUSCOLO dal payload (es. il sesso M/F/X):
    #        `optional_string` + upper. Assente, null o vuoto → None; un
    #        non-stringa → 400 col campo, come `optional_string`.
    #        Solo la FORMA: il valore ammesso lo giudica chi possiede il
    #        vocabolario (un CHECK, un guard), non questo helper.
    # ⭐ Regola del 2 (ok Tid, 2026-10-09): unifica le copie
    #    `(payload.get(k) or "").strip().upper() or None` del sesso in
    #    anagrafiche e amm_software. Con due forme «x» passava in creazione e
    #    finiva nel CHECK in modifica; e `.strip()` su un non-stringa era un 500.
    #    Gemello per la query string: `qp_str_upper` (payload_validators).
    def optional_upper(
        self,
        payload: dict[str, Any],
        key: str,
        *,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> str | None:
        value = self.optional_string(
            payload, key, log_to_db=log_to_db, function_name=function_name,
        )
        return value.upper() if value else None

    # =================================================================
    # Estrazione interi
    # =================================================================

    # Scopo: Estrae un intero positivo obbligatorio dal payload. Accetta int
    #        o stringa numerica; rifiuta bool, float, stringhe non numeriche.
    def require_positive_int(
        self,
        payload: dict[str, Any],
        key: str,
        *,
        message: str | None = None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> int:
        em = self._em_kwargs(log_to_db=log_to_db, function_name=function_name)
        base_message = message or f"Campo '{key}' obbligatorio."
        raw = payload.get(key)
        ErrorManager.require(
            raw is not None,
            code=self._code,
            message=base_message,
            detail=f"{key} e' obbligatorio." if message else None,
            context={key: raw, "field": key},
            **em,
        )
        value = self._coerce_positive_int(raw, key, message=message, em=em)
        return value

    # Scopo: Estrae un intero positivo opzionale (None se chiave assente o
    #        valore None). Se presente, stessa validazione di require_positive_int.
    def optional_positive_int(
        self,
        payload: dict[str, Any],
        key: str,
        *,
        message: str | None = None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> int | None:
        raw = payload.get(key)
        if raw is None:
            return None
        em = self._em_kwargs(log_to_db=log_to_db, function_name=function_name)
        return self._coerce_positive_int(raw, key, message=message, em=em)

    # Scopo: Coerce valore raw a int positivo, rifiutando bool/float e
    #        stringhe non numeriche. Helper interno usato da required/optional.
    def _coerce_positive_int(
        self,
        raw: Any,
        key: str,
        *,
        message: str | None = None,
        em: dict[str, Any] | None = None,
    ) -> int:
        em = em or {}
        if isinstance(raw, bool):
            ErrorManager.raise_error(
                code=self._code,
                message=message or f"Campo '{key}' deve essere un intero.",
                detail=f"{key} deve essere un intero." if message else None,
                context={key: raw, "field": key},
                **em,
            )
        value: int
        if isinstance(raw, int):
            value = raw
        elif isinstance(raw, str) and raw.strip().isdigit():
            value = int(raw.strip())
        else:
            ErrorManager.raise_error(
                code=self._code,
                message=message or f"Campo '{key}' deve essere un intero positivo.",
                detail=f"{key} deve essere un intero positivo." if message else None,
                context={key: raw, "field": key},
                **em,
            )
        ErrorManager.require(
            value > 0,
            code=self._code,
            message=message or f"Campo '{key}' deve essere un intero positivo.",
            detail=f"{key} deve essere un intero positivo." if message else None,
            context={key: value, "field": key},
            **em,
        )
        return value

    # Scopo: Estrae uno smallint opzionale con range configurabile. Default
    #        [0, 32767] (unsigned) coerente con campi ordinamento UI. Rifiuta
    #        bool; accetta int o stringa numerica (anche negativa).
    def optional_smallint(
        self,
        payload: dict[str, Any],
        key: str,
        *,
        min_val: int = SMALLINT_UNSIGNED_MIN,
        max_val: int = SMALLINT_MAX,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> int | None:
        if key not in payload or payload[key] is None:
            return None
        em = self._em_kwargs(log_to_db=log_to_db, function_name=function_name)
        value = payload[key]
        if isinstance(value, bool):
            ErrorManager.raise_error(
                code=self._code,
                message=f"Campo '{key}' deve essere un intero.",
                context={key: value, "field": key},
                **em,
            )
        normalized: int
        if isinstance(value, int):
            normalized = value
        elif isinstance(value, str) and _SIGNED_INT_RE.match(value.strip()):
            # Regex _SIGNED_INT_RE rifiuta "--5", "++1", "1.0" — solo int firmato valido.
            normalized = int(value.strip())
        else:
            ErrorManager.raise_error(
                code=self._code,
                message=f"Campo '{key}' deve essere un intero.",
                context={key: value, "field": key},
                **em,
            )
        ErrorManager.require(
            min_val <= normalized <= max_val,
            code=self._code,
            message=f"Campo '{key}' fuori range.",
            detail=f"Deve essere tra {min_val} e {max_val}.",
            context={key: normalized, "field": key},
            **em,
        )
        return normalized

    # =================================================================
    # Estrazione booleani
    # =================================================================

    # Scopo: Estrae un bool opzionale rigoroso. Rifiuta stringhe "true"/"false"
    #        e numeri 0/1 per evitare ambiguita'; accetta solo `bool` stretto.
    #        Ritorna None se chiave assente o valore None esplicito.
    def optional_bool(
        self,
        payload: dict[str, Any],
        key: str,
        *,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> bool | None:
        if key not in payload or payload[key] is None:
            return None
        value = payload[key]
        if isinstance(value, bool):
            return value
        ErrorManager.raise_error(
            code=self._code,
            message=f"Campo '{key}' deve essere booleano.",
            context={key: value, "field": key},
            **self._em_kwargs(log_to_db=log_to_db, function_name=function_name),
        )

    # Scopo: Estrae un bool obbligatorio rigoroso: assente o None si rifiutano
    #        come un valore non booleano (stesse regole di `optional_bool`).
    #        Per i comandi che accendono o spengono qualcosa, dove «assente =
    #        invariato» non ha senso.
    def require_bool(
        self,
        payload: dict[str, Any],
        key: str,
        *,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> bool:
        value = self.optional_bool(payload, key, log_to_db=log_to_db, function_name=function_name)
        if value is None:
            ErrorManager.raise_error(
                code=self._code,
                message=f"Campo '{key}' obbligatorio (booleano).",
                context={key: None, "field": key},
                **self._em_kwargs(log_to_db=log_to_db, function_name=function_name),
            )
        return value

    # =================================================================
    # Estrazione UUID
    # =================================================================

    # Scopo: Coerce di un UUID da stringa o oggetto UUID. Solleva errore
    #        strutturato se il valore non e' convertibile. Helper interno
    #        usato da require_uuid/optional_uuid.
    def _coerce_uuid(
        self,
        value: Any,
        *,
        field: str,
        message: str | None,
        em: dict[str, Any],
    ) -> str:
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, str):
            try:
                return str(UUID(value.strip()))
            except ValueError as exc:
                ErrorManager.raise_error(
                    code=self._code,
                    message=message or f"Campo '{field}' deve essere un UUID valido.",
                    detail=f"{field} non e' un UUID valido." if message else None,
                    context={"field": field, "value": value},
                    cause=exc,
                    **em,
                )
        ErrorManager.raise_error(
            code=self._code,
            message=message or f"Campo '{field}' deve essere un UUID (stringa o oggetto).",
            detail=f"{field} ha tipo non supportato." if message else None,
            context={"field": field, "type": type(value).__name__},
            **em,
        )

    # Scopo: Estrae un UUID obbligatorio dal payload. Accetta stringa ISO o
    #        oggetto uuid.UUID; normalizza a stringa lower-case canonica.
    def require_uuid(
        self,
        payload: dict[str, Any],
        key: str,
        *,
        message: str | None = None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> str:
        em = self._em_kwargs(log_to_db=log_to_db, function_name=function_name)
        raw = payload.get(key)
        ErrorManager.require(
            raw is not None,
            code=self._code,
            message=message or f"Campo '{key}' obbligatorio.",
            detail=f"{key} obbligatorio." if message else None,
            context={"field": key},
            **em,
        )
        return self._coerce_uuid(raw, field=key, message=message, em=em)

    # Scopo: Estrae un UUID opzionale (None se chiave assente o valore None).
    def optional_uuid(
        self,
        payload: dict[str, Any],
        key: str,
        *,
        message: str | None = None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> str | None:
        raw = payload.get(key)
        if raw is None:
            return None
        em = self._em_kwargs(log_to_db=log_to_db, function_name=function_name)
        return self._coerce_uuid(raw, field=key, message=message, em=em)

    # =================================================================
    # Estrazione decimali (quantita', importi, prezzi, coefficienti)
    # =================================================================
    #
    # ⭐ Estratti il 2026-09-18 (regola del 2, ok Tid) da OTTO siti in sette
    #    moduli e TRE forme: `decimal_da_payload` di pagamenti e la sua copia in
    #    magazzino (due stati, `obbligatorio`, rifiuto di bool e NaN);
    #    `_extract_decimal` di catalogo e listini (tre stati `MISSING`,
    #    `nullable`, `.strip()`, `min_value` — e listini sul parse fallito
    #    sollevava un `ValueError`, cioe' un `E_VALIDATION_INPUT` generico al
    #    posto del codice del suo dominio); `_coerce_decimal` di contratti e i
    #    due blocchi inline di commesse (solo la coercizione del valore).
    #    ⭐ Stessa sera, alla rilettura critica, altri QUATTRO: `imponibile`
    #    della forzatura sui titoli IVA, `valore_variazione` di categorie
    #    clienti/listini e di promo, `payload_prezzo` del gate L1/L2 — che
    #    accettavano `NaN` o, il primo, un `bool`. ⚠️ E un QUINTO alla
    #    rilettura della rilettura, sulla stessa strada del gate: i due campi
    #    di `_validate_riga_economic` di preventivi (`prezzo_unitario`,
    #    `qta_operativa`), dove `NaN >= 0` era un 500 e una quantita' NaN
    #    passava fino al DB. Restano FUORI di proposito,
    #    e non sono copie: i cast best-effort di un PARAMETRO di sistema
    #    (`parameter_service`, `amm_software`, `views_pricing`: «non parsabile
    #    = nessuna soglia», nessun campo di form da accendere), il salto
    #    difensivo sui prezzi negoziati di un'offerta (`ordini_service`) e gli
    #    override per componente (`_componenti_service_helpers`), che nominano
    #    il componente nella frase invece di un campo.
    # ⚠️ Il rigore e' quello PIU' ALTO fra le copie, per tutti: si passa da
    #    `str` (`Decimal(0.1)` porta dentro l'errore del float), un `bool` non
    #    e' un numero (`True` sommerebbe come 1 senza che nessuno lo segnali),
    #    e `NaN`/`Infinity` — che `Decimal("NaN")` costruisce senza protestare
    #    e un JSON puo' portare — si rifiutano: arriverebbero fino alla colonna
    #    `numeric`, dove ogni somma che li incontra diventa NaN, e un totale NaN
    #    non si vede — si legge come un campo vuoto. Tre copie su cinque non li
    #    guardavano.
    # ⚠️ `min_value` e' INCLUSIVO (`>=`), come il range di `optional_smallint`:
    #    i guard stretti di dominio (`> 0` su un prezzo) restano nel chiamante,
    #    con la loro frase.

    # Scopo: Coerce di un valore SCALARE a Decimal finito — la forma per chi
    #        riceve il numero come parametro di firma e non dentro un payload
    #        (speculare a `guard_positive_int`). `None` e' «obbligatorio».
    #        I tre metodi da payload qui sotto delegano a questo.
    def coerce_decimal(
        self,
        raw: Any,
        *,
        field: str,
        min_value: Decimal | None = None,
        message: str | None = None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> Decimal:
        em = self._em_kwargs(log_to_db=log_to_db, function_name=function_name)
        return self._coerce_decimal(
            raw, field=field, message=message, min_value=min_value, em=em,
        )

    # Scopo: Il corpo della coercizione, coi kwargs di ErrorManager gia' risolti.
    def _coerce_decimal(
        self,
        raw: Any,
        *,
        field: str,
        message: str | None,
        min_value: Decimal | None,
        em: dict[str, Any],
    ) -> Decimal:
        if raw is None:
            ErrorManager.raise_error(
                code=self._code,
                message=message or f"Campo '{field}' obbligatorio.",
                detail=f"{field} obbligatorio." if message else None,
                context={"field": field},
                **em,
            )
        # Il valore ricevuto sta SEMPRE nel detail: e' cio' che serve a chi
        # legge il log (e all'operatore, quando la frase di titolo e' generica).
        contesto = {"field": field, field: str(raw)}
        titolo = message or f"Campo '{field}' deve essere un numero."
        if isinstance(raw, bool):
            ErrorManager.raise_error(
                code=self._code,
                message=titolo,
                detail=f"{field} deve essere numerico, non un booleano: {raw!r}.",
                context=contesto,
                **em,
            )
        try:
            valore = Decimal(str(raw).strip())
        except (InvalidOperation, ValueError, TypeError, AttributeError) as exc:
            ErrorManager.raise_error(
                code=self._code,
                message=titolo,
                detail=f"{field} non e' un numero valido: {raw!r}.",
                context=contesto,
                cause=exc,
                **em,
            )
        ErrorManager.require(
            valore.is_finite(),
            code=self._code,
            message=titolo,
            detail=f"{field} non e' un numero finito: {raw!r}.",
            context=contesto,
            **em,
        )
        if min_value is not None:
            ErrorManager.require(
                valore >= min_value,
                code=self._code,
                message=message or f"Campo '{field}' deve essere >= {min_value}.",
                detail=f"{field} deve essere >= {min_value} (ricevuto: {valore}).",
                context={"field": field, field: str(valore), "min_value": str(min_value)},
                **em,
            )
        return valore

    # Scopo: Estrae un Decimal obbligatorio dal payload. Rifiuta None
    #        esplicito e chiave assente.
    def require_decimal(
        self,
        payload: dict[str, Any],
        key: str,
        *,
        min_value: Decimal | None = None,
        message: str | None = None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> Decimal:
        em = self._em_kwargs(log_to_db=log_to_db, function_name=function_name)
        return self._coerce_decimal(
            payload.get(key), field=key, message=message, min_value=min_value, em=em,
        )

    # Scopo: Estrae un Decimal opzionale. Ritorna None se chiave assente o
    #        valore None esplicito; coerce se presente.
    def optional_decimal(
        self,
        payload: dict[str, Any],
        key: str,
        *,
        min_value: Decimal | None = None,
        message: str | None = None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> Decimal | None:
        if key not in payload or payload[key] is None:
            return None
        em = self._em_kwargs(log_to_db=log_to_db, function_name=function_name)
        return self._coerce_decimal(
            payload[key], field=key, message=message, min_value=min_value, em=em,
        )

    # Scopo: Estrae un Decimal opzionale distinguendo 3 stati (per i PATCH),
    #        come `extract_optional_string`:
    #          - chiave assente   -> MISSING (campo non aggiornato)
    #          - valore None      -> None se nullable, altrimenti errore
    #          - valore           -> Decimal finito (con `min_value` se dato)
    def extract_optional_decimal(
        self,
        payload: dict[str, Any],
        key: str,
        *,
        nullable: bool = False,
        min_value: Decimal | None = None,
        message: str | None = None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> Decimal | None | MissingType:
        if key not in payload:
            return MISSING
        em = self._em_kwargs(log_to_db=log_to_db, function_name=function_name)
        value = payload.get(key)
        if value is None:
            ErrorManager.require(
                nullable,
                code=self._code,
                message=message or f"Campo '{key}' non puo' essere null.",
                detail=f"{key} non puo' essere null." if message else None,
                context={"field": key},
                **em,
            )
            return None
        return self._coerce_decimal(
            value, field=key, message=message, min_value=min_value, em=em,
        )

    # =================================================================
    # Estrazione enum (un codice a vocabolario chiuso: tipo, ambito, livello)
    # =================================================================
    #
    # ⭐ Estratti il 2026-09-18 (regola del 2, ok Tid) da CINQUE siti in tre
    #    moduli con la stessa forma — `isinstance(raw, str)` → `.strip().upper()`
    #    → `in <whitelist>` — e la stessa frase («deve essere uno tra: …»):
    #    `tipo_variazione` di promo (con un flag `required`) e di categorie
    #    clienti/listini, `ambito`, `tipo_variazione_globale` e
    #    `tipo_eccezione` di contratti. ⚠️ Le whitelist restano DEL DOMINIO
    #    (specchiano `CHECK` diversi: due valori in categorie, tre in promo,
    #    uno in contratti): il BB unifica la lettura, non il vocabolario.
    # ⚠️ Il rigore e' quello piu' alto fra le copie, per tutti: un valore che
    #    non e' una stringa (`True`, `3`) e' un rifiuto e non un `AttributeError`
    #    su `.strip()`; una stringa VUOTA e' «obbligatorio», non «uno tra»; e il
    #    `context` porta SEMPRE `field` — quattro copie su cinque, sul valore
    #    fuori vocabolario, scrivevano `{"tipo_variazione": tipo}` e il form non
    #    accendeva niente.
    # ⚠️ Il confronto e' sul valore NORMALIZZATO: la whitelist va scritta in
    #    maiuscolo, com'e' a catalogo.

    # Scopo: Coerce di un valore SCALARE a codice del vocabolario `allowed` —
    #        la forma per chi riceve il codice come parametro di firma
    #        (speculare a `coerce_decimal`). `None` e' «obbligatorio».
    #        `nota` e' la frase in piu' che il dominio aggiunge al detail del
    #        rifiuto («VALORE_FISSO non e' ammesso sulla testata: …»).
    def coerce_enum(
        self,
        raw: Any,
        *,
        field: str,
        allowed: Collection[str],
        message: str | None = None,
        nota: str | None = None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> str:
        em = self._em_kwargs(log_to_db=log_to_db, function_name=function_name)
        return self._coerce_enum(
            raw, field=field, allowed=allowed, message=message, nota=nota, em=em,
        )

    # Scopo: Il corpo della coercizione, coi kwargs di ErrorManager gia' risolti.
    def _coerce_enum(
        self,
        raw: Any,
        *,
        field: str,
        allowed: Collection[str],
        message: str | None,
        nota: str | None,
        em: dict[str, Any],
    ) -> str:
        ammessi = ", ".join(sorted(allowed))
        ErrorManager.require(
            isinstance(raw, str),
            code=self._code,
            message=message or f"Campo '{field}' deve essere una stringa.",
            detail=f"{field} deve essere una stringa, non {type(raw).__name__}." if message else None,
            context={"field": field},
            **em,
        )
        assert isinstance(raw, str)
        value = raw.strip().upper()
        ErrorManager.require(
            value != "",
            code=self._code,
            message=message or f"Campo '{field}' obbligatorio.",
            detail=f"{field} obbligatorio." if message else None,
            context={"field": field},
            **em,
        )
        ErrorManager.require(
            value in allowed,
            code=self._code,
            message=message or f"Campo '{field}' deve essere uno tra: {ammessi}.",
            detail=f"{field} deve essere uno tra: {ammessi}." + (f" {nota}" if nota else ""),
            # Il valore ricevuto sta nel context (al log), MAI nel detail: e' un
            # codice scritto dall'operatore, non un dato da rimandargli.
            context={"field": field, field: value},
            **em,
        )
        return value

    # Scopo: Estrae un codice obbligatorio dal payload. Rifiuta None
    #        esplicito, chiave assente e stringa vuota.
    def require_enum(
        self,
        payload: dict[str, Any],
        key: str,
        *,
        allowed: Collection[str],
        message: str | None = None,
        nota: str | None = None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> str:
        em = self._em_kwargs(log_to_db=log_to_db, function_name=function_name)
        raw = payload.get(key)
        if raw is None:
            ErrorManager.raise_error(
                code=self._code,
                message=message or f"Campo '{key}' obbligatorio.",
                detail=f"{key} obbligatorio." if message else None,
                context={"field": key},
                **em,
            )
        return self._coerce_enum(
            raw, field=key, allowed=allowed, message=message, nota=nota, em=em,
        )

    # Scopo: Estrae un codice opzionale. Ritorna None se chiave assente o
    #        valore None esplicito; coerce se presente.
    def optional_enum(
        self,
        payload: dict[str, Any],
        key: str,
        *,
        allowed: Collection[str],
        message: str | None = None,
        nota: str | None = None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> str | None:
        if key not in payload or payload[key] is None:
            return None
        em = self._em_kwargs(log_to_db=log_to_db, function_name=function_name)
        return self._coerce_enum(
            payload[key], field=key, allowed=allowed, message=message, nota=nota, em=em,
        )

    # Scopo: Estrae un codice opzionale distinguendo 3 stati (per i PATCH),
    #        come `extract_optional_decimal`:
    #          - chiave assente   -> MISSING (campo non aggiornato)
    #          - valore None      -> None se nullable, altrimenti errore
    #          - valore           -> codice normalizzato e ammesso
    def extract_optional_enum(
        self,
        payload: dict[str, Any],
        key: str,
        *,
        allowed: Collection[str],
        nullable: bool = False,
        message: str | None = None,
        nota: str | None = None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> str | None | MissingType:
        if key not in payload:
            return MISSING
        em = self._em_kwargs(log_to_db=log_to_db, function_name=function_name)
        value = payload.get(key)
        if value is None:
            ErrorManager.require(
                nullable,
                code=self._code,
                message=message or f"Campo '{key}' non puo' essere null.",
                detail=f"{key} non puo' essere null." if message else None,
                context={"field": key},
                **em,
            )
            return None
        return self._coerce_enum(
            value, field=key, allowed=allowed, message=message, nota=nota, em=em,
        )

    # =================================================================
    # Estrazione date ISO
    # =================================================================

    # Scopo: Coerce di una data da `datetime.date` o stringa ISO YYYY-MM-DD.
    #        Helper interno usato da require_date/optional_date.
    def _coerce_date(
        self,
        value: Any,
        *,
        field: str,
        message: str | None,
        em: dict[str, Any],
    ) -> date:
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value.strip())
            except ValueError as exc:
                ErrorManager.raise_error(
                    code=self._code,
                    message=message or f"Campo '{field}' deve essere una data ISO YYYY-MM-DD.",
                    detail=f"{field} deve essere una data ISO YYYY-MM-DD." if message else None,
                    context={"field": field, "value": value},
                    cause=exc,
                    **em,
                )
        ErrorManager.raise_error(
            code=self._code,
            message=message or f"Campo '{field}' deve essere una data o stringa ISO.",
            detail=f"{field} ha tipo non supportato." if message else None,
            context={"field": field, "type": type(value).__name__},
            **em,
        )

    # Scopo: Estrae una data obbligatoria dal payload. Rifiuta None esplicito
    #        e chiave assente.
    def require_date(
        self,
        payload: dict[str, Any],
        key: str,
        *,
        message: str | None = None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> date:
        em = self._em_kwargs(log_to_db=log_to_db, function_name=function_name)
        if key not in payload or payload[key] is None:
            ErrorManager.raise_error(
                code=self._code,
                message=message or f"Campo '{key}' obbligatorio.",
                detail=f"{key} obbligatorio." if message else None,
                context={"field": key},
                **em,
            )
        return self._coerce_date(payload[key], field=key, message=message, em=em)

    # Scopo: Estrae una data opzionale. Ritorna None se chiave assente o
    #        valore None esplicito; coerce se presente.
    def optional_date(
        self,
        payload: dict[str, Any],
        key: str,
        *,
        message: str | None = None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> date | None:
        if key not in payload or payload[key] is None:
            return None
        em = self._em_kwargs(log_to_db=log_to_db, function_name=function_name)
        return self._coerce_date(payload[key], field=key, message=message, em=em)

    # Scopo: Estrae una stringa opzionale distinguendo 3 stati (per i PATCH):
    #          - chiave assente   -> MISSING (campo non aggiornato)
    #          - valore None      -> None se nullable, altrimenti errore
    #          - stringa          -> strip; vuota+nullable -> None;
    #                                vuota+non nullable -> errore
    #        `max_len` (2026-09-21, regola del 2): lo stesso tetto di
    #        `require_string`/`optional_string`, con lo stesso messaggio e lo
    #        stesso `context` — il PATCH per delta delle anagrafiche di
    #        magazzino lo riscriveva a mano dopo la chiamata.
    def extract_optional_string(
        self,
        payload: dict[str, Any],
        key: str,
        *,
        nullable: bool = False,
        max_len: int | None = None,
        message: str | None = None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> str | None | MissingType:
        if key not in payload:
            return MISSING
        em = self._em_kwargs(log_to_db=log_to_db, function_name=function_name)
        msg = message or f"Campo '{key}' non valido."
        value = payload.get(key)
        if value is None:
            ErrorManager.require(
                nullable,
                code=self._code,
                message=msg,
                detail=f"{key} non puo' essere null.",
                context={"field": key},
                **em,
            )
            return None
        ErrorManager.require(
            isinstance(value, str),
            code=self._code,
            message=msg,
            detail=f"{key} deve essere una stringa.",
            context={"field": key},
            **em,
        )
        cleaned = value.strip()
        if nullable and cleaned == "":
            return None
        ErrorManager.require(
            bool(cleaned),
            code=self._code,
            message=msg,
            detail=f"{key} non puo' essere vuoto.",
            context={"field": key},
            **em,
        )
        if max_len is not None:
            ErrorManager.require(
                len(cleaned) <= max_len,
                code=self._code,
                message=message or f"Campo '{key}' troppo lungo.",
                detail=f"Lunghezza massima: {max_len} caratteri.",
                context={key: cleaned, "len": len(cleaned), "field": key},
                **em,
            )
        return cleaned

    # =================================================================
    # Estrazione meta (JSONB)
    # =================================================================

    # Scopo: Estrae il campo meta opzionale normalizzando stringa JSON o dict.
    #        Semantica:
    #          - chiave assente         -> None (non aggiornare)
    #          - chiave presente, None  -> {} (reset esplicito)
    #          - chiave presente, dict  -> dict
    #          - chiave presente, str   -> json.loads, deve risultare dict
    def optional_meta(
        self,
        payload: dict[str, Any],
        key: str = "meta",
        *,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> dict[str, Any] | None:
        em = self._em_kwargs(log_to_db=log_to_db, function_name=function_name)
        if key not in payload:
            return None
        raw = payload[key]
        if raw is None:
            return {}
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except (ValueError, TypeError) as exc:
                ErrorManager.raise_error(
                    code=self._code,
                    message=f"Il campo '{key}' contiene JSON non valido.",
                    context={f"{key}_raw": raw, "field": key},
                    cause=exc,
                    **em,
                )
            if isinstance(parsed, dict):
                return parsed
        ErrorManager.raise_error(
            code=self._code,
            message=f"Il campo '{key}' deve essere un oggetto JSON.",
            context={f"{key}_type": type(raw).__name__, "field": key},
            **em,
        )

    # =================================================================
    # PATCH letta per presenza
    # =================================================================

    # Scopo: ⭐ I campi di una PATCH, letti per PRESENZA: una chiave presente
    #        si scrive (anche `null`, che svuota un campo nullable), una chiave
    #        assente non si tocca. Una chiave fuori contratto e' un 400
    #        (`validate_allowed_keys`), una PATCH che non porta campi e' un 400
    #        (`require_campi_da_aggiornare`). Ritorna il dict da scrivere.
    #   - `testi`: chiave -> (nullable, max_len). nullable False = NOT NULL a
    #     DB (`null` e `""` sono 400); `max_len` la lunghezza della colonna
    #     (None = nessun tetto). Letti con `extract_optional_string`;
    #   - `maiuscoli`: i testi che si scrivono in maiuscolo (sigle, codici ISO);
    #   - `interi`: chiave -> nullable. True: `null` AZZERA, un valore e' un
    #     id positivo; False: id positivo obbligatorio se la chiave c'e';
    #   - `flag`: booleani NOT NULL (`require_bool`: un `null` e' un 400, non
    #     uno «spegni»);
    #   - `altri`: chiave -> lettore `(payload, chiave)`, chiamato solo se la
    #     chiave c'e' — le forme che il dominio legge con un altro BB
    #     (`optional_meta`, `require_date`, `optional_date`...);
    #   - `ammesse`: il contratto PUBBLICATO del metodo (la costante che legge
    #     anche lo schema OpenAPI), quando esiste. Deve coincidere con le chiavi
    #     dichiarate: una chiave ammessa e non letta sarebbe scartata in
    #     silenzio, una letta e non ammessa un 400 su un campo del contratto.
    #     Assente, il contratto sono le chiavi dichiarate.
    #   - `message` per la chiave fuori contratto; `message_vuoto` /
    #     `detail_vuoto` / `context_vuoto` per la PATCH vuota: le frasi del
    #     dominio. Il codice e' il `validation_code` dell'istanza.
    # ⛔ Una dichiarazione incoerente (la stessa chiave in due gruppi, un
    #    maiuscolo che non e' un testo, `ammesse` diversa dalle dichiarate) e'
    #    `RuntimeError`, un 500: e' un errore di chi scrive il service, non di
    #    chi chiama (stessa scelta di `execute_dynamic_update`).
    # ⭐ Regola del 2 (ok Tid 2026-10-21): la stessa lettura era scritta in
    #    geo (`_campi_patch_geo`), nelle anagrafiche di magazzino
    #    (`_testi_presenti` / `_int_nullable_presente` / `_bool_presente`),
    #    nella testata della commessa e nell'unita' di misura del catalogo.
    #    Le copie dicevano un `null` su un flag in due frasi diverse e un testo
    #    NOT NULL vuoto in due altre.
    def campi_per_presenza(
        self,
        payload: dict[str, Any],
        *,
        testi: Mapping[str, tuple[bool, int | None]] | None = None,
        maiuscoli: Collection[str] = frozenset(),
        interi: Mapping[str, bool] | None = None,
        flag: Collection[str] = frozenset(),
        altri: Mapping[str, Callable[[dict[str, Any], str], Any]] | None = None,
        ammesse: frozenset[str] | None = None,
        message: str = "Payload non valido.",
        message_vuoto: str = "Nessun campo aggiornabile presente nel payload.",
        detail_vuoto: str | None = None,
        context_vuoto: dict[str, Any] | None = None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> dict[str, Any]:
        testi = testi or {}
        interi = interi or {}
        altri = altri or {}
        dichiarate = [*testi, *interi, *flag, *altri]
        lette = frozenset(dichiarate)
        if len(lette) != len(dichiarate):
            raise RuntimeError(f"campi_per_presenza: chiave dichiarata in due gruppi ({sorted(dichiarate)}).")
        if not frozenset(maiuscoli) <= frozenset(testi):
            raise RuntimeError(f"campi_per_presenza: maiuscoli fuori dai testi ({sorted(frozenset(maiuscoli) - frozenset(testi))}).")
        if ammesse is not None and ammesse != lette:
            raise RuntimeError(
                "campi_per_presenza: il contratto e le chiavi lette divergono "
                f"(ammesse e non lette: {sorted(ammesse - lette)}; lette e non ammesse: {sorted(lette - ammesse)})."
            )
        em: dict[str, Any] = {"log_to_db": log_to_db, "function_name": function_name}
        self.validate_allowed_keys(payload, allowed=lette, message=message, **em)
        campi: dict[str, Any] = {}
        for chiave, (nullable, max_len) in testi.items():
            valore = self.extract_optional_string(payload, chiave, nullable=nullable, max_len=max_len, **em)
            if isinstance(valore, MissingType):
                continue
            campi[chiave] = valore.upper() if valore and chiave in maiuscoli else valore
        for chiave, nullable in interi.items():
            if chiave in payload:
                campi[chiave] = (
                    self.optional_positive_int(payload, chiave, **em) if nullable
                    else self.require_positive_int(payload, chiave, **em)
                )
        for chiave in sorted(flag):
            if chiave in payload:
                campi[chiave] = self.require_bool(payload, chiave, **em)
        for chiave, leggi in altri.items():
            if chiave in payload:
                campi[chiave] = leggi(payload, chiave)
        self.require_campi_da_aggiornare(
            campi, message=message_vuoto, detail=detail_vuoto, context=context_vuoto, **em,
        )
        return campi

    # =================================================================
    # Liste di voci
    # =================================================================

    # Scopo: ⭐ Una LISTA DI VOCI dal corpo, ogni voce un oggetto: `valori`
    #        deve essere una lista, ogni elemento un dict, e ogni voce passa da
    #        `leggi(voce, indice)`, che ne estrae i campi col BB (400 col
    #        campo) e ritorna la voce da scrivere. Ritorna le voci lette.
    #        `campo` e' la chiave del corpo: sta nel `context` (`field`) e nelle
    #        frasi; l'indice della voce sta nel `detail` e nel `context`.
    #        `message` sostituisce le due frasi quando il dominio ne ha una
    #        sua («Preferenza lista non valida.»): il dettaglio resta.
    # ⛔ `None` NON e' una lista vuota: e' un 400. Chi riceve la lista spesso
    #    sostituisce in blocco (DELETE + INSERT), e un corpo `{}` diventato
    #    `[]` svuotava tutto con un 200. Dove la lista e' davvero facoltativa
    #    (le righe alla creazione di un reso, le colonne di una preferenza) lo
    #    decide il chiamante, che non chiama il BB se la chiave manca.
    # ⭐ Regola del 2 (ok Tid 2026-10-21): la stessa lettura era in
    #    amm_software (`_voci`: override dell'operatore e profilo di reparto),
    #    nel salvataggio dei prezzi bundle del listino, nella creazione del
    #    reso e nelle colonne di preferenza e preset delle liste — dove una
    #    voce che non e' un oggetto era, secondo il punto, un 400, un
    #    `AttributeError` o un `KeyError` (500).
    def voci(
        self,
        valori: Any,
        leggi: Callable[[dict[str, Any], int], _T],
        *,
        campo: str,
        message: str | None = None,
        log_to_db: bool | None = None,
        function_name: str | None = None,
    ) -> list[_T]:
        em = self._em_kwargs(log_to_db=log_to_db, function_name=function_name)
        ErrorManager.require(
            isinstance(valori, list),
            code=self._code,
            message=message or f"'{campo}' deve essere una lista.",
            detail=f"Il campo '{campo}' deve essere una lista.",
            context={"field": campo},
            **em,
        )
        assert isinstance(valori, list)
        lette: list[_T] = []
        for indice, voce in enumerate(valori):
            ErrorManager.require(
                isinstance(voce, dict),
                code=self._code,
                message=message or f"Ogni voce di '{campo}' deve essere un oggetto.",
                detail=f"{campo}[{indice}] deve essere un oggetto.",
                context={"field": campo, "indice": indice},
                **em,
            )
            lette.append(leggi(voce, indice))
        return lette


# =================================================================
# Mapping IntegrityError -> codici errore parlanti
# =================================================================


# Scopo: ⭐ IL RICONOSCIMENTO DEL VINCOLO VIOLATO — il pezzo che chiunque
#        traduca un `IntegrityError` deve fare allo stesso modo.
#
#        Match con word boundary (`\b`) e non per sottostringa: senza,
#        `fk_foo` matcha anche `fk_foo_bar`, e a decidere quale vince e'
#        l'ordine di inserimento nella mappa — cioe' il caso.
#
#        ⚠️ ESISTE PERCHE' LO STESSO RICONOSCIMENTO ERA SCRITTO DUE VOLTE
#        (2026-08-08). `map_integrity_error` lo faceva con la word boundary,
#        `create_with_constraint_mapping` (anagrafiche) con un `in` nudo: la
#        seconda aveva ancora il difetto che la prima aveva gia' corretto, e
#        nessuno poteva accorgersene perche' erano due copie senza un legame.
#        E' lo stesso genere di guasto del cantiere dei codici errore: due
#        elenchi della stessa cosa che si sfilano in silenzio.
def vincolo_violato(exc: Exception, nomi: Iterable[str]) -> str | None:
    msg = str(exc).lower()
    for nome in nomi:
        if re.search(r"\b" + re.escape(nome.lower()) + r"\b", msg):
            return nome
    return None


# Scopo: Traduce IntegrityError DB in ServiceError con codice parlante
#        del dominio. Le mappe associano frammento di vincolo DB (UNIQUE
#        UNIQUE, FK o CHECK) a una coppia (error_code, message). Il match e' case-insensitive
#        sullo `str(exc)` ed e' lineare — la chiave piu' specifica va prima.
#
#        ⭐ TERZO ELEMENTO — IL CAMPO DA CORREGGERE (2026-08-08). Ogni voce puo'
#        essere `(codice, messaggio)` oppure `(codice, messaggio, campo)`: il
#        campo finisce nel `context` della SOLA voce che ha fatto match, arriva
#        al client nell'envelope (`error.fields`) e gli accende l'input.
#        E' il caso in cui serve di piu': su un duplicato il form e' compilato
#        bene, la validazione client non ha niente da dire, e senza il campo
#        l'operatore legge «esiste gia'» e deve indovinare quale.
#
#        ⚠️ Si dichiara il campo SOLO quando e' vero. Un vincolo composto su piu'
#        colonne che l'operatore sceglie davvero (una coppia di select) non ha
#        UN campo, e uno inventato accenderebbe l'input sbagliato — peggio che
#        non accenderne nessuno: manda a correggere un campo giusto. In quei
#        casi si lascia la tupla a due elementi.
#
#        `function_name` e `log_to_db` (2026-11-09, come `PayloadValidator` e
#        `validate_enum_param`): il chiamante che vuole la violazione nel diario
#        (`dbops.error_log`) lo dice, col nome della sua funzione. I default sono
#        quelli di `ErrorManager.raise_error`: chi non li passa non cambia.
#
#        Esempio d'uso:
#
#            try:
#                repo.create(data)
#            except IntegrityError as exc:
#                map_integrity_error(
#                    exc,
#                    unique_constraints={
#                        "uq_categorie_clienti_codice": (
#                            E_ANAG_DUPLICATO,
#                            "Esiste gia' una categoria con questo codice.",
#                            "codice",   # <- il campo che si accende nel form
#                        ),
#                    },
#                    fk_constraints={},
#                    check_constraints={},
#                    fallback_code=E_ANAG_VALIDAZIONE,
#                    fallback_message="Violazione vincolo DB su categoria cliente.",
#                    context={"codice": data.get("codice")},
#                )
def map_integrity_error(
    exc: IntegrityError,
    *,
    unique_constraints: dict[str, tuple] | None = None,
    fk_constraints: dict[str, tuple] | None = None,
    check_constraints: dict[str, tuple] | None = None,
    fallback_code: str,
    fallback_message: str = "Violazione vincolo DB.",
    context: dict[str, Any] | None = None,
    function_name: str = "django_service",
    log_to_db: bool = False,
) -> NoReturn:
    ctx = context or {}

    def _match_exact(constraint_name: str) -> bool:
        return vincolo_violato(exc, [constraint_name]) is not None

    # Scopo: solleva per il vincolo che ha fatto match, aggiungendo al contesto
    #        il CAMPO dichiarato dalla mappa (terzo elemento della tupla).
    #
    #        ⚠️ IL CAMPO STA SULLA VOCE, NON SUL CONTESTO CONDIVISO, e la
    #        differenza non e' stilistica: una mappa puo' avere piu' vincoli su
    #        campi diversi, e un `field` messo nel `context` comune si
    #        applicherebbe a QUALUNQUE di essi facesse match. Il client
    #        accenderebbe l'input sbagliato — che e' peggio di non accenderne
    #        nessuno, perche' manda l'operatore a correggere un campo giusto.
    def _solleva(voce: tuple, campi_extra: dict[str, Any]) -> NoReturn:
        error_code, message = voce[0], voce[1]
        campo = voce[2] if len(voce) > 2 else None
        ErrorManager.raise_error(
            code=error_code,
            message=message,
            detail=str(exc),
            context={**campi_extra, **({"field": campo} if campo else {})},
            function_name=function_name,
            log_to_db=log_to_db,
            cause=exc,
        )

    for constraint_name, voce in (unique_constraints or {}).items():
        if _match_exact(constraint_name):
            _solleva(voce, ctx)

    for constraint_name, voce in (fk_constraints or {}).items():
        if _match_exact(constraint_name):
            _solleva(voce, ctx)

    for constraint_name, voce in (check_constraints or {}).items():
        if _match_exact(constraint_name):
            _solleva(voce, ctx)

    # Fallback euristico per coppia UNIQUE/FK generica: solo se la mappa
    # non ha un match esatto e il codice fallback vale la pena distinguere,
    # il chiamante passa la mappa. Qui cadiamo sul fallback puro.
    # ⭐ Ma il CAMPO, quando PostgreSQL lo dice da solo, viaggia (2026-09-21):
    # su una violazione NOT NULL (23502) `column_name` e' la colonna che
    # manca, e nessuna mappa per nome di vincolo puo' nominarla — un NOT NULL
    # non ha un vincolo con un nome. Stessa lettura unica di `translate_db_errors`
    # (`diagnostica_db`): prima il fallback arrivava senza `fields`, e il form
    # restava spento sull'unico caso in cui il DB sa gia' quale campo accendere.
    ErrorManager.raise_error(
        code=fallback_code,
        message=fallback_message,
        detail=str(exc),
        context=ctx,
        fields=diagnostica_db(exc).fields,
        function_name=function_name,
        log_to_db=log_to_db,
        cause=exc,
    )


# Scopo: Regex di estrazione del codice errore strutturato E_* dal testo di
#        un'eccezione DB. I guard/fn DB sollevano via
#        script.fn_log_and_raise_error: il codice arriva nella stringa
#        dell'eccezione (MESSAGE o CONTEXT PL/pgSQL con l'istruzione SQL che
#        contiene il literal del codice).
# Ripiego storico, ora dentro `db_error_fields.APP_ERROR_CODE_RE`: qui resta
# come alias per i chiamanti/test che lo importavano da questo modulo.
DB_ERROR_CODE_RE = APP_ERROR_CODE_RE


# Scopo: Context manager condiviso che normalizza gli errori DB in
#        ServiceError parlanti (BB estratto 2026-07-13, regola del 2 — era la
#        5a copia identica in resi/ddt/ordini/offerte/_indirizzi_documento):
#        - IntegrityError (unique/fk/check) -> map_integrity_error con le
#          mappe vincolo del dominio;
#        - DatabaseError (RAISE P0001 di trigger/fn madri) -> estrazione
#          regex del codice E_* dal testo, cosi' il FE fa routing UI
#          specifico via error_policies; fallback sul codice di dominio.
#        NB: IntegrityError e' sottoclasse di DatabaseError — l'ordine degli
#        except e' vincolante.
@contextmanager
def translate_db_errors(
    *,
    context: dict[str, Any],
    fallback_code: str,
    fallback_message: str,
    unique_constraints: dict[str, tuple] | None = None,
    fk_constraints: dict[str, tuple] | None = None,
    check_constraints: dict[str, tuple] | None = None,
) -> Iterator[None]:
    try:
        yield
    except IntegrityError as exc:
        map_integrity_error(
            exc,
            unique_constraints=unique_constraints,
            fk_constraints=fk_constraints,
            check_constraints=check_constraints,
            fallback_code=fallback_code,
            fallback_message=fallback_message,
            context=context,
        )
    except DatabaseError as exc:
        exc_text = str(exc)
        # ⭐ UNA lettura sola della diagnostica (BB `diagnostica_db`, 2026-08-24).
        # Campo strutturato per primo (`CONSTRAINT` su P0001), poi il ripiego
        # a regex sul testo: stessa semantica di prima — qualunque codice il DB
        # dichiari vince sul `fallback_code` — ma letto da una fonte che non
        # dipende da come e' scritto il call site nel corpo della funzione.
        diag_dominio = diagnostica_db(exc, text=exc_text)
        code = diag_dominio.codice or fallback_code
        # ⭐ L'HINT del database e' l'AZIONE SUGGERITA che il team DB scrive a
        # catalogo per ogni codice («se il documento non e' ancora numerato, la
        # strada e' il reset del lotto…»): la parte che dice all'operatore cosa
        # fare. Fino al 2026-08-18 si perdeva qui — sopravviveva solo annegata
        # nel testo grezzo di `detail` — e un dominio che volesse darla
        # all'utente doveva RISCRIVERLA in Python, cioe' duplicare il catalogo.
        # ⚠️ `ErrorTranslator._from_database_error` la legge gia' dalla diag, ma
        # quel ramo vale solo per un DatabaseError che arriva NUDO al
        # middleware: appena un service traduce — cioe' sempre, qui — non ci
        # passa. Ora il campo viaggia strutturato fino all'envelope.
        # ⭐ IL CAMPO DA CORREGGERE E IL BERSAGLIO, dal 2026-08-24, e sono la
        # stessa lezione dell'`hint` qui sopra ripetuta due volte. Misurato: il
        # canale `COLUMN` viaggia dall'08/08 ed e' valorizzato da quasi tutti i
        # punti di sollevamento del database, ma arrivava all'envelope SOLO
        # dalla strada del `DatabaseError` nudo — cioe' praticamente mai, perche'
        # questo context manager ha 46 punti di chiamata. I 136 binding di
        # `campiErrati` sul frontend non si illuminavano su un errore nato in
        # PL/pgSQL, e nessuno poteva vederlo dal lato che riceve.
        # Il bersaglio (canale `DATATYPE`) sarebbe nato con lo stesso difetto.
        ErrorManager.raise_error(
            hint=diag_dominio.hint,
            code=code,
            message=exc_text.split("\n", maxsplit=1)[0].strip()
            or fallback_message,
            detail=exc_text,
            context=context,
            fields=diag_dominio.fields,
            targets=diag_dominio.bersagli or None,
        )


# Scopo: Factory per i service di dominio "stile op": fissa una volta
#        fn_prefix + mappe vincolo + fallback e ritorna un context manager
#        `_db_errors(op)` con context {"op": "<fn_prefix>.<op>"} — i call
#        site dei domini restano `with _db_errors("crea_x"):`.
def make_db_errors_translator(
    *,
    fn_prefix: str,
    fallback_code: str,
    fallback_message: str,
    unique_constraints: dict[str, tuple] | None = None,
    fk_constraints: dict[str, tuple] | None = None,
    check_constraints: dict[str, tuple] | None = None,
) -> Any:
    @contextmanager
    # Scopo: Traduttore errori DB del dominio per l'operazione `op`.
    def _translator(op: str) -> Iterator[None]:
        with translate_db_errors(
            context={"op": f"{fn_prefix}.{op}"},
            fallback_code=fallback_code,
            fallback_message=fallback_message,
            unique_constraints=unique_constraints,
            fk_constraints=fk_constraints,
            check_constraints=check_constraints,
        ):
            yield

    return _translator
