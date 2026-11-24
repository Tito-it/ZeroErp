# Scopo: Helper di validazione/estrazione condivisi per i service anagrafiche.
#        require_str, optional_str, extract_optional_fields, require_found,
#        create_with_dedup, create_with_constraint_mapping, update_with_dedup,
#        rifiuto_integrita (la traduzione di un IntegrityError per SQLSTATE),
#        regime_nel_catalogo (la FK del regime fiscale in 400 sul campo).

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, NoReturn, TypeVar

from django.db import IntegrityError

from apps.core.services.error_manager import ErrorManager
from apps.core.services.db_error_fields import diagnostica_db
from apps.core.services.payload_helpers import PayloadValidator, map_integrity_error, vincolo_violato
from apps.core.services.service_errors import ServiceError
from apps.core.services.testata_guard import o_not_found
from apps.anagrafiche.error_codes import (
    E_ANAG_DUPLICATO,
    E_ANAG_FK,
    E_ANAG_NOT_FOUND,
    E_ANAG_VALIDAZIONE,
)

# Il validator del dominio per le letture di questo modulo: i campi opzionali
# si leggono col codice di anagrafiche e col campo nell'errore, non con le
# funzioni della view (2026-11-24, brief-be-fe-BB-audit §2).
_V = PayloadValidator(validation_code=E_ANAG_VALIDAZIONE)

# SQLSTATE di PostgreSQL che decidono la traduzione di un `IntegrityError`.
_SQLSTATE_UNICITA = "23505"  # unique_violation: «esiste gia'»
_SQLSTATE_FK = "23503"  # foreign_key_violation: il riferimento non esiste


def require_str(payload: dict, key: str, message: str) -> str:
    """Estrae, strippa e valida campo stringa obbligatorio."""
    value = (payload.get(key) or "").strip()
    ErrorManager.require(bool(value), code=E_ANAG_VALIDAZIONE, message=message)
    return value


def optional_str(payload: dict, key: str, message: str | None = None) -> str | None:
    """Estrae e strippa campo stringa opzionale. Se fornito e vuoto dopo strip, errore."""
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if message:
            ErrorManager.require(bool(value), code=E_ANAG_VALIDAZIONE, message=message)
        return value or None
    return None


def extract_optional_fields(
    payload: dict,
    *,
    ints: tuple[str, ...] = (),
    bools: tuple[str, ...] = (),
    strings: tuple[str, ...] = (),
    numeric: tuple[str, ...] = (),
    dates: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Costruisce un dict coi soli campi opzionali valorizzati nel payload.

    Centralizza il pattern _extract_*_data (fornitori/emittenti): per categoria
    applica il parser appropriato e include la chiave solo se il valore non e'
    None — così il DB usa i propri default sui campi assenti.
      - ints:    `PayloadValidator.optional_int` (codice E_ANAG_VALIDAZIONE)
      - bools:   `PayloadValidator.optional_bool` (solo se la chiave e' presente e non-None)
      - strings: optional_str (strip + None se vuoto)
      - numeric: valore grezzo (float/decimal), solo se presente e non-None
      - dates:   `PayloadValidator.optional_date`
    """
    data: dict[str, Any] = {}
    for key in ints:
        val_int = _V.optional_int(payload, key)
        if val_int is not None:
            data[key] = val_int
    for key in bools:
        if key in payload and payload[key] is not None:
            data[key] = _V.optional_bool(payload, key)
    for key in strings:
        val_str = optional_str(payload, key)
        if val_str is not None:
            data[key] = val_str
    for key in numeric:
        if key in payload and payload[key] is not None:
            data[key] = payload[key]
    for key in dates:
        val_data = _V.optional_date(payload, key)
        if val_data is not None:
            data[key] = val_data
    return data


def require_found(entity: dict | None, message: str) -> dict:
    """Solleva E_ANAG_NOT_FOUND se entity e' None, altrimenti la ritorna.

    Centralizza il pattern get → require not-found → assert (per il type checker)
    → return, identico nei get_* di clienti/fornitori/soggetti/emittenti.
    Dal 2026-09-21 e' la faccia di dominio del BB core `o_not_found`: il
    codice e' fisso, la regola sta in un posto solo.
    """
    return o_not_found(entity, code=E_ANAG_NOT_FOUND, message=message)


# Scopo: ⭐ La traduzione di un `IntegrityError` per i service anagrafiche, in
#        un posto solo: decide lo SQLSTATE, non il chiamante.
#        - 23505 (unicita') → `E_ANAG_DUPLICATO` col messaggio del chiamante;
#        - 23503 (FK) → `E_ANAG_FK`;
#        - ogni altra violazione (CHECK, NOT NULL, esclusione…) →
#          `E_ANAG_VALIDAZIONE`, col campo quando PostgreSQL lo nomina (NOT NULL).
# ⚠️ Fino al 2026-10-07 `create_with_dedup` / `update_with_dedup` traducevano
#    QUALUNQUE `IntegrityError` nel messaggio di duplicato: un `CHECK` violato
#    usciva «Codice fiscale o partita IVA duplicata», cioe' un messaggio che
#    afferma il falso su un campo che l'operatore non ha toccato (E-7 di
#    analisi-be-difetti-emersi-verifica-doc-api-core, parte «fuori perimetro»).
#    Lo SQLSTATE e' il contratto di PostgreSQL, non il testo (che si traduce
#    con `lc_messages`).
def rifiuto_integrita(exc: IntegrityError, duplicate_message: str) -> NoReturn:
    sqlstate = diagnostica_db(exc).sqlstate
    if sqlstate == _SQLSTATE_UNICITA:
        raise ServiceError(code=E_ANAG_DUPLICATO, message=duplicate_message, detail=str(exc)) from exc
    if sqlstate == _SQLSTATE_FK:
        raise ServiceError(
            code=E_ANAG_FK,
            message="Riferimento non valido: l'entita' indicata non esiste.",
            detail=str(exc),
        ) from exc
    map_integrity_error(
        exc,
        fallback_code=E_ANAG_VALIDAZIONE,
        fallback_message="Dati non validi: il database ha rifiutato il valore.",
    )


_T = TypeVar("_T")


# ⚠️ Restituisce cio' che restituisce `fn` (l'id creato: uno `str` o un `int`),
#    non un dict: fino al 2026-10-09 l'annotazione diceva `-> dict`.
def create_with_dedup(fn: Callable[[], _T], duplicate_message: str) -> _T:
    """Esegue fn (create); un IntegrityError lo traduce `rifiuto_integrita`."""
    try:
        return fn()
    except IntegrityError as exc:
        rifiuto_integrita(exc, duplicate_message)


def create_with_constraint_mapping(
    fn: Any,
    constraint_messages: dict[str, str | tuple[str, str]],
    default_message: str | None = None,
) -> Any:
    """Esegue fn (create) mappando le violazioni UNIQUE su messaggi per-constraint.

    Per tabelle con piu' vincoli UNIQUE: evita il mascheramento di
    `create_with_dedup` (che riconduce ogni unicita' a un unico messaggio). Sul vincolo che fa match solleva
    ServiceError(E_ANAG_DUPLICATO, messaggio). Se nessun constraint matcha:
    se `default_message` e' dato lo solleva, altrimenti RILANCIA l'IntegrityError
    (no mascheramento; il middleware lo gestisce) — pattern coerente con clienti.

    Il valore della mappa e' il messaggio, oppure `(messaggio, campo)`: il campo
    e' quello che l'operatore deve correggere, arriva al client in
    `error.fields` e gli accende l'input. Si dichiara **solo quando e' vero** —
    dev'essere una chiave del payload, non solo una colonna del database.

    ⚠️ IL RICONOSCIMENTO DEL VINCOLO NON E' PIU' SCRITTO QUI (2026-08-08): usa
    `vincolo_violato` di `payload_helpers`, lo stesso di `map_integrity_error`.
    Prima erano due copie, e non erano identiche — qui il match era un `in`
    nudo, quindi `uq_foo` matchava anche `uq_foo_bar` e a decidere quale
    vincesse era l'ordine del dizionario. Il difetto era gia' stato corretto
    nell'altra copia con la word boundary, ma nessuno poteva accorgersi che
    questa era rimasta indietro: e' esattamente il guasto da «due elenchi della
    stessa cosa» che il cantiere dei codici errore ha inseguito per giorni.

    ⚠️ Resta invece DIVERSA la politica di ripiego, e va tenuta: `map_integrity_error`
    maschera sempre con un `fallback_code`, questa RILANCIA. Non sono due copie
    della stessa decisione — sono due decisioni diverse, ed e' voluto.
    """
    try:
        return fn()
    except IntegrityError as exc:
        detail = str(exc)
        nome = vincolo_violato(exc, constraint_messages)
        if nome is not None:
            voce = constraint_messages[nome]
            message, campo = voce if isinstance(voce, tuple) else (voce, None)
            raise ServiceError(
                code=E_ANAG_DUPLICATO,
                message=message,
                detail=detail,
                context={"field": campo} if campo else None,
            ) from exc
        if default_message is not None:
            # Il messaggio di ripiego dice «esiste gia'»: vale solo per
            # un'unicita' (o una violazione che non si sa classificare, che
            # `rifiuto_integrita` porta a validazione), mai per FK o CHECK.
            rifiuto_integrita(exc, default_message)
        raise


# Il campo del regime fiscale (FatturaPA, RF01…): stessa chiave del payload su
# emittente e fornitore, FK su `config.regimi_fiscali.codice_interno` in tutti e due.
CAMPO_REGIME_FISCALE = "regime_fiscale_rf"


# Scopo: Traduce in 400 sul campo `regime_fiscale_rf` un codice di regime fuori
#        catalogo, cioe' la FK `fk` (il nome del vincolo della tabella che il
#        chiamante scrive) verso `config.regimi_fiscali`.
#        ⚠️ Traduce SOLO quella FK: ogni altra IntegrityError si rilancia com'e',
#        perche' il ripiego dei chiamanti (o il middleware) la gestisce gia' —
#        un ripiego qui la maschererebbe da errore di regime. Per questo, dentro
#        il blocco, `create_with_constraint_mapping` va chiamata SENZA
#        `default_message`: col ripiego tradurrebbe lei la FK in `E_ANAG_FK`.
#        Consumatori: emittenti fiscali (`fk_emittenti_fiscali_regimi_fiscali`)
#        e fornitori (`fk_fornitori_regimi_fiscali`), creazione e PATCH.
# ⭐ Regola del 2 (ok Tid, 2026-11-21): nasce dalla copia privata del service
#    dell'emittente, quando il regime del fornitore e' passato sul catalogo.
#    Resta fuori la regola sul VUOTO, che non e' la stessa: sull'emittente il
#    regime e' NOT NULL e il vuoto e' un 400, sul fornitore e' nullable.
@contextmanager
def regime_nel_catalogo(fk: str) -> Iterator[None]:
    try:
        yield
    except IntegrityError as exc:
        if vincolo_violato(exc, [fk]) is None:
            raise
        ErrorManager.raise_error(
            code=E_ANAG_VALIDAZIONE,
            message="Regime fiscale non presente nel catalogo dei regimi.",
            detail=str(exc),
            context={"field": CAMPO_REGIME_FISCALE},
            cause=exc,
        )


def update_with_dedup(fn: Any, duplicate_message: str, not_found_message: str) -> dict:
    """Esegue fn (update); IntegrityError via `rifiuto_integrita`, poi not found."""
    try:
        updated = fn()
    except IntegrityError as exc:
        rifiuto_integrita(exc, duplicate_message)
    ErrorManager.require(updated, code=E_ANAG_NOT_FOUND, message=not_found_message)
    return {"updated": True}
