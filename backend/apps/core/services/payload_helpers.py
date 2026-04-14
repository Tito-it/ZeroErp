# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
from typing import Any, NoReturn

from django.db import IntegrityError

from apps.core.services.error_manager import ErrorManager


# Regex per int firmato: segno opzionale seguito da almeno una cifra.
# Evita che lstrip("-") accetti stringhe degeneri tipo "--5" o "---0".
_SIGNED_INT_RE = re.compile(r"^-?\d+$")


# Costanti range per smallint PostgreSQL (INT2): [-32768, 32767]. I service
# admin tipicamente restringono a valori non negativi: un ordinamento < 0 non
# ha semantica UI.
SMALLINT_MIN = -32768
SMALLINT_MAX = 32767
SMALLINT_UNSIGNED_MIN = 0
INTEGER_MAX = 2_147_483_647


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

    # =================================================================
    # Whitelist colonne ORDER BY
    # =================================================================

    # Scopo: Valida che `order_by` sia nella whitelist di colonne ammesse.
    #        Coerente con policy anti-SQL-injection sui parametri di
    #        ordinamento lista (ogni repo ha la sua _ORDER_COLS).
    def validate_order_by(
        self,
        order_by: str,
        *,
        allowed: frozenset[str],
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
            raise AssertionError("unreachable")  # pragma: no cover
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
                context={key: value},
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
                context={key: value},
                **em,
            )
            raise AssertionError("unreachable")  # pragma: no cover
        ErrorManager.require(
            min_val <= normalized <= max_val,
            code=self._code,
            message=f"Campo '{key}' fuori range.",
            detail=f"Deve essere tra {min_val} e {max_val}.",
            context={key: normalized},
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
            context={key: value},
            **self._em_kwargs(log_to_db=log_to_db, function_name=function_name),
        )
        raise AssertionError("unreachable")  # pragma: no cover

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
                    context={f"{key}_raw": raw},
                    cause=exc,
                    **em,
                )
                raise AssertionError("unreachable") from exc  # pragma: no cover
            if isinstance(parsed, dict):
                return parsed
        ErrorManager.raise_error(
            code=self._code,
            message=f"Il campo '{key}' deve essere un oggetto JSON.",
            context={f"{key}_type": type(raw).__name__},
            **em,
        )
        raise AssertionError("unreachable")  # pragma: no cover


# =================================================================
# Mapping IntegrityError -> codici errore parlanti
# =================================================================


# Scopo: Traduce IntegrityError DB in ServiceError con codice parlante
#        del dominio. Le mappe associano frammento di vincolo DB (UNIQUE
#        o FK) a una coppia (error_code, message). Il match e' case-insensitive
#        sullo `str(exc)` ed e' lineare — la chiave piu' specifica va prima.
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
#                        ),
#                    },
#                    fk_constraints={},
#                    fallback_code=E_ANAG_VALIDAZIONE,
#                    fallback_message="Violazione vincolo DB su categoria cliente.",
#                    context={"codice": data.get("codice")},
#                )
#                raise  # pragma: no cover — map_integrity_error solleva sempre
def map_integrity_error(
    exc: IntegrityError,
    *,
    unique_constraints: dict[str, tuple[str, str]] | None = None,
    fk_constraints: dict[str, tuple[str, str]] | None = None,
    fallback_code: str,
    fallback_message: str = "Violazione vincolo DB.",
    context: dict[str, Any] | None = None,
) -> NoReturn:
    msg = str(exc).lower()
    ctx = context or {}

    # Match con word boundary (`\b`) per evitare collisioni su sottostringhe:
    # es. `fk_foo` non deve matchare `fk_foo_bar` se quest'ultimo ha una voce
    # distinta nella mappa. Senza boundary, l'ordine di inserimento della
    # mappa determinerebbe quale vince — fragile.
    def _match_exact(constraint_name: str) -> bool:
        return re.search(
            r"\b" + re.escape(constraint_name.lower()) + r"\b", msg
        ) is not None

    for constraint_name, (error_code, message) in (unique_constraints or {}).items():
        if _match_exact(constraint_name):
            ErrorManager.raise_error(
                code=error_code,
                message=message,
                detail=str(exc),
                context=ctx,
                cause=exc,
            )

    for constraint_name, (error_code, message) in (fk_constraints or {}).items():
        if _match_exact(constraint_name):
            ErrorManager.raise_error(
                code=error_code,
                message=message,
                detail=str(exc),
                context=ctx,
                cause=exc,
            )

    # Fallback euristico per coppia UNIQUE/FK generica: solo se la mappa
    # non ha un match esatto e il codice fallback vale la pena distinguere,
    # il chiamante passa la mappa. Qui cadiamo sul fallback puro.
    ErrorManager.raise_error(
        code=fallback_code,
        message=fallback_message,
        detail=str(exc),
        context=ctx,
        cause=exc,
    )
