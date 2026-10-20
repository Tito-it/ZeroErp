from __future__ import annotations

import math
import re
from datetime import date, datetime
from typing import Any
from uuid import UUID

from rest_framework.exceptions import ParseError

from apps.core.api.constants import DEFAULT_LIMIT, MAX_LIMIT
from apps.core.api.request_parsers import oggetto_json, parse_iso_date
from apps.core.services.payload_helpers import BIGINT_MAX, BIGINT_MIN, PayloadValidator
from apps.core.services.service_errors import E_VALIDATION_INPUT, ServiceError

# Validator centralizzati payload API (riusabili cross-domain).


# ------------------------------------------------------------------
# Corpo della richiesta (POST/PUT/PATCH DRF)
# ------------------------------------------------------------------


# Scopo: ⭐ Il corpo della richiesta come OGGETTO, o un 400 nell'envelope. Il
#        JSON valido non e' per forza un oggetto: con una lista (o un numero)
#        `request.data` e' quella lista, e il primo `.get()` diventava un 500
#        (F-9, 2026-09-27: logout, refresh del token, override permessi…),
#        mentre `dict(request.data)` su una lista di coppie la trasformava in
#        un oggetto, in silenzio.
# ⭐ La regola «e' un oggetto?» e' `oggetto_json`, la stessa di
#    `handle_post_json`: qui si traduce il suo rifiuto nel codice del catalogo.
#    Anche il JSON illeggibile (`ParseError` di DRF) passa di qui, e non esce
#    piu' nel formato DRF.
# ⛔ Non `{}` al posto del corpo sbagliato: un client che manda una lista ha
#    sbagliato la richiesta, e un oggetto vuoto la farebbe eseguire coi
#    default, in silenzio.
# Un form (`QueryDict`) e' un dict: passa com'e'.
_MESSAGGIO_CORPO = {
    "invalid_json": "Il corpo della richiesta non e' un JSON valido.",
    "invalid_payload": "Il corpo della richiesta deve essere un oggetto JSON.",
}


def corpo_oggetto(request: Any) -> dict[str, Any]:
    try:
        return oggetto_json(request.data)
    except (ParseError, ValueError) as exc:
        raise errore_corpo(exc) from exc


# Scopo: ⭐ Il rifiuto di un corpo illeggibile o che non e' un oggetto, in UN
#        posto: 400 `E_VALIDATION_INPUT` nell'envelope, con `context.motivo`
#        (`invalid_json` / `invalid_payload`). Lo usano `corpo_oggetto` (view
#        DRF) e `handle_post_json` (E-6, 2026-10-07: fino a quel giorno
#        rispondeva `{"error": "invalid_json"}` fuori envelope — la stessa
#        regola in due forme). `exc` e' il `ParseError` di DRF o il
#        `ValueError` di `parse_json_body`/`oggetto_json`, che porta il motivo.
def errore_corpo(exc: Exception) -> ServiceError:
    motivo = "invalid_json" if isinstance(exc, ParseError) else str(exc)
    if motivo not in _MESSAGGIO_CORPO:
        motivo = "invalid_payload"
    return ServiceError(
        code=E_VALIDATION_INPUT,
        message=_MESSAGGIO_CORPO[motivo],
        context={"motivo": motivo},
    )


# Scopo: ⭐ Una password dal corpo COSI' COM'E' digitata: assente = "", un
#        valore che non e' testo = `ValueError` (400 E_VALIDATION_INPUT).
# ⛔ Niente `strip` (S-5, 2026-09-27): si salva e si verifica quella digitata,
#    come fa il login (`SidTokenObtainPairSerializer`). E niente `str(...)`: un
#    numero non e' una password, e arrivava ai validatori di Django come 500.
# Le regole della nuova password stanno in `auth_helpers.valida_nuova_password`.
def password_digitata(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{key}_invalid")
    return value


# ------------------------------------------------------------------
# Helper query-params GET (riusabili da qualsiasi view GET)
# ------------------------------------------------------------------

# Scopo: Normalizza parametro booleano da query string con default configurabile.
def qp_bool(raw: str | None, default: bool = True) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "n", "off"}


# Scopo: Parametro booleano OPZIONALE e RIGOROSO da query string.
#        None se assente o vuoto; True/False sui token riconosciuti;
#        ValueError(f"{name}_invalid") su valore non riconosciuto (no coercion
#        silenziosa). Simmetrico a qp_int_optional. NB: `?x=` (vuoto) -> None,
#        come chiave assente.
def qp_bool_optional(raw: str | None, name: str) -> bool | None:
    if raw is None:
        return None
    val = raw.strip().lower()
    if val == "":
        return None
    if val in {"1", "true", "yes", "y", "on"}:
        return True
    if val in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"{name}_invalid")


# Scopo: Normalizza parametro intero da query string con default configurabile.
def qp_int(raw: str | None, default: int) -> int:
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except (ValueError, AttributeError):
        return default


# Scopo: Converte parametro intero da query string; solleva ValueError se non
#        numerico o fuori da bigint (oltre, nessun intero PG lo regge: un 500).
def qp_int_strict(raw: str | None, name: str, default: int) -> int:
    if raw is None:
        return default
    try:
        valore = int(raw.strip())
    except (ValueError, AttributeError):
        raise ValueError(f"{name}_invalid") from None
    if not BIGINT_MIN <= valore <= BIGINT_MAX:
        raise ValueError(f"{name}_invalid")
    return valore


# Scopo: Parametro intero OPZIONALE da query string: None se assente o vuoto;
#        solleva ValueError(f"{name}_invalid") se presente ma non numerico, o
#        fuori da [min_val, max_val]. Variante "optional" di qp_int_strict.
# ⚠️ Il tetto e' il TIPO DOVE IL VALORE ARRIVA, non la colonna: un confronto
#    `col = %s` regge qualunque intero (int4 = int8 si confronta), un PARAMETRO
#    di funzione `integer` o un cast `::integer` no — 3000000000 diventa un
#    bigint, la funzione non si risolve e la risposta e' un 500 al posto di un
#    400. Default: bigint, sempre corretto (oltre, nessun intero PG). Chi passa
#    il valore a un parametro `integer` dichiara `max_val=INTEGER_MAX` (e
#    `min_val=INTEGER_MIN`), da `apps.core.services.payload_helpers`.
def qp_int_optional(
    raw: str | None,
    name: str,
    *,
    min_val: int = BIGINT_MIN,
    max_val: int = BIGINT_MAX,
) -> int | None:
    if raw is None:
        return None
    cleaned = raw.strip()
    if cleaned == "":
        return None
    try:
        valore = int(cleaned)
    except ValueError as exc:
        raise ValueError(f"{name}_invalid") from exc
    if not min_val <= valore <= max_val:
        raise ValueError(f"{name}_invalid")
    return valore


# Scopo: Data ISO OPZIONALE da query string: None se assente o vuota;
#        date.fromisoformat altrimenti, ValueError(f"{name}_invalid") se
#        malformata. Simmetrico a qp_int_optional per i filtri data.
def qp_iso_date_optional(raw: str | None, name: str) -> date | None:
    if raw is None:
        return None
    cleaned = raw.strip()
    if cleaned == "":
        return None
    try:
        return date.fromisoformat(cleaned)
    except ValueError as exc:
        raise ValueError(f"{name}_invalid") from exc


# Scopo: Normalizza parametro stringa da query string (strip + None se vuoto).
def qp_str(raw: str | None) -> str | None:
    if raw is None:
        return None
    cleaned = raw.strip()
    return cleaned or None


# Scopo: Normalizza parametro enum da query string: strip + UPPER, None se
#        assente/vuoto. Per i filtri a vocabolario maiuscolo (area, fase,
#        classe, stadio) di liste e dashboard. Estratto 2026-07-07 (regola
#        del 2, ok Tid): unifica 5 copie del pattern
#        `raw = qp_str(...); v = raw.upper() if raw else None` nelle view
#        dashboard vendite.
def qp_str_upper(raw: str | None) -> str | None:
    cleaned = qp_str(raw)
    return cleaned.upper() if cleaned else None


# ------------------------------------------------------------------
# Helper query-params per endpoint lista paginata
# ------------------------------------------------------------------


# Scopo: Parsing standard parametri lista paginata da query string.
# Restituisce dict con search, limit, offset, order_by, order_dir, page.
def parse_list_params(
    qp,
    *,
    default_order: str = "descrizione",
    default_limit: int = DEFAULT_LIMIT,
    max_limit: int = MAX_LIMIT,
) -> dict:
    search = qp_str(qp.get("search"))
    # ⚠️ Il limite sta fra 1 e `max_limit`, l'offset non e' negativo: i
    #    repository li riportano gia' nei limiti, ma l'envelope si calcola da
    #    QUESTI valori — con `limit=0` usciva `page_size: 0` accanto a una
    #    pagina di righe, cioe' un paginatore che non torna.
    limit = max(1, min(qp_int(qp.get("limit"), default_limit), max_limit))
    offset = max(0, qp_int(qp.get("offset"), 0))
    order_by = qp.get("order_by") or default_order
    # ⛔ Assente = `None`, NON "asc" (2026-09-26). Il ripiego su "asc"
    #    annullava il default dei repository (`default_desc`, `colonne_desc`),
    #    che si accende solo su `None`: le liste che nascono dal piu' recente
    #    si aprivano al contrario, senza errore, e ogni view che lo sapeva
    #    rileggeva la direzione grezza dalla query string. La direzione si
    #    VALIDA a valle (`order_dir_ammessa`, nel service o nel BB SQL).
    order_dir = qp_str(qp.get("order_dir"))
    page = (offset // limit) + 1
    return {
        "search": search,
        "limit": limit,
        "offset": offset,
        "order_by": order_by,
        "order_dir": order_dir,
        "page": page,
    }


# ------------------------------------------------------------------
# Envelope paginato standard (riusabile da qualsiasi service)
# ------------------------------------------------------------------

# Scopo: Costruisce l'envelope paginato standard con count, page, page_size, total_pages, results.
def paginated_envelope(
    results: list, total_count: int, page: int, page_size: int,
) -> dict[str, Any]:
    total_pages = math.ceil(total_count / page_size) if page_size > 0 else 0
    return {
        "count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "results": results,
    }


# Un intero scritto in una stringa: solo cifre ASCII. ⛔ Non `str.isdigit()`:
# accetta anche «²» o «٣», e il primo poi fa fallire `int()` con un ValueError
# che non e' il `{key}_invalid` atteso dai chiamanti.
_INTERO_DECIMALE_RE = re.compile(r"[0-9]+")


# Scopo: Valida e converte il campo opzionale `int` mantenendo `None` se assente.
def optional_int(payload: dict[str, Any], key: str, *, zero_as_none: bool = False) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if zero_as_none and value in (0, "0"):
        return None
    if isinstance(value, bool):
        raise ValueError(f"{key}_invalid")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and _INTERO_DECIMALE_RE.fullmatch(value.strip()):
        return int(value.strip())
    raise ValueError(f"{key}_invalid")


# Scopo: Il flag `key` del CORPO JSON: assente o `null` -> `default`.
# ⛔ Una regola sola per il corpo, ed e' quella di `PayloadValidator.optional_bool`,
#    a cui questa funzione delega: un flag e' un booleano JSON, e qualunque altra
#    cosa — `"false"`, `"1"`, `0` — e' un 400 `E_VALIDATION_INPUT` col campo.
#    JSON ha il tipo: accettare una stringa vuol dire indovinarlo. Fino al
#    2026-10-20 qui si accettava un vocabolario di stringhe (`"off"`, `"y"`…)
#    diverso da quello di `as_bool` e rifiutato dal BB dei service: tre letture
#    dello stesso flag (brief-be-verifica-documentazione-api §3).
# ⚠️ Query string e multipart NON passano di qui: li' ogni valore e' una stringa
#    per natura, e si leggono coi loro BB (`qp_bool`, …).
def optional_bool(payload: dict[str, Any], key: str, default: bool = False) -> bool:
    value = PayloadValidator(validation_code=E_VALIDATION_INPUT).optional_bool(payload, key)
    return default if value is None else value


# Scopo: Valida e converte il campo opzionale `iso_date` mantenendo `None` se assente.
def optional_iso_date(payload: dict[str, Any], key: str):
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key}_invalid")
    return parse_iso_date(value)


# Scopo: Valida e converte il campo opzionale ISTANTE (ISO 8601 con data e ora)
#        mantenendo `None` se assente o vuoto. ⛔ L'OFFSET E' OBBLIGATORIO
#        (`Z` o `+02:00`): senza, PostgreSQL leggerebbe l'ora nel fuso della
#        SESSIONE (UTC), cioe' un'ora che nessuno ha scritto. Una stringa senza
#        offset e' `ValueError` -> 400 `E_VALIDATION_INPUT`, non un'ipotesi.
#        Brief un-solo-fuso-aziendale B-7 (2026-10-09).
def optional_istante(payload: dict[str, Any], key: str) -> datetime | None:
    value = payload.get(key)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key}_invalid")
    try:
        istante = datetime.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError(f"{key}_invalid") from exc
    if istante.tzinfo is None or istante.utcoffset() is None:
        raise ValueError(f"{key}_senza_offset")
    return istante


# Scopo: Valida e converte il campo opzionale `uuid` mantenendo `None` se assente.
def optional_uuid(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    # Per compatibilita` input legacy/UI: 0 o stringa vuota => NULL.
    if value in (0, "0", ""):
        return None
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        try:
            return str(UUID(candidate))
        except ValueError as exc:
            raise ValueError(f"{key}_invalid") from exc
    raise ValueError(f"{key}_invalid")
