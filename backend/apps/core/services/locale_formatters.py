# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Formattatori per export e render lato BE — centralizzati
#        per garantire coerenza visiva sui formati date/numeri/booleani
#        e per facilitare la localizzazione futura.
#
#        v1 (questa): costanti hardcoded italiane (DD-MM-YYYY, virgola
#        decimale, "Si"/"No"). Usato dal renderer export liste (DEF-1).
#
#        v2 (futuro): le costanti diventano default di
#        `config.parameters` con catena override
#        user → group → emittente → sistema. Codici parameter previsti:
#          - LOCALE_DATE_FORMAT       (default '%d-%m-%Y')
#          - LOCALE_DATETIME_FORMAT   (default '%d-%m-%Y %H:%M')
#          - LOCALE_BOOL_TRUE_LABEL   (default 'Si')
#          - LOCALE_BOOL_FALSE_LABEL  (default 'No')
#          - LOCALE_DECIMAL_SEPARATOR (default ',')
#          - LOCALE_THOUSANDS_SEPARATOR (default '.')
#        Il refactor sara' invisibile ai chiamanti: la funzione
#        `format_for_export(value, tipo_dato, formato)` resta uguale,
#        cambia solo da dove vengono lette le costanti.
#
#        Per supportare un nuovo stato (es. US):
#          - oggi: editare le costanti del modulo + redeploy
#          - in v2: settare i parameter `LOCALE_*` per l'emittente
#            specifico oppure per il singolo utente, niente deploy
#
#        ⭐ IL FUSO E' PARTE DEL FORMATO (decisione di Tid, 2026-09-14): un
#        istante si scrive nell'ORA DELL'AZIENDA (BB `fuso_aziendale`, dal
#        parametro `SYSTEM_FUSO_ORARIO`; fino al 2026-10-09 era `TIME_ZONE` di
#        Django, oggi 'UTC' e neutro), mai nel fuso che il valore porta. Con `USE_TZ` la connessione consegna i timestamptz in
#        UTC, e fino a quel giorno ogni export scriveva ore UTC — una o due
#        indietro — mentre le liste a video le mostravano giuste, perche' il
#        browser converte. Lo stesso istante con due ore a seconda del canale
#        e' una data senza il suo contesto: il difetto e' emerso sul digest
#        dei presidi (testata in ora locale, corse in UTC) e vale qui per
#        tutti, cosi' nessun chiamante deve ricordarsi di convertire.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.utils import timezone

from apps.core.services.fuso_aziendale import fuso_aziendale

# =================================================================
# Costanti di default italiane (v1).
# v2: alimentate da `config.parameters` con catena override.
# =================================================================

# Formato date: DD-MM-YYYY (es. "10-05-2026").
# Allineato al formato visibile nelle DataTable lato FE
# (`displayDate` in core/utils/date.js).
DATE_FORMAT: str = "%d-%m-%Y"

# Formato datetime: DD-MM-YYYY HH:MM (es. "10-05-2026 17:30").
# Niente secondi per leggibilita'; chi serve precisione al secondo
# usa `format_for_export` con `formato='datetime_full'`.
DATETIME_FORMAT: str = "%d-%m-%Y %H:%M"
DATETIME_FULL_FORMAT: str = "%d-%m-%Y %H:%M:%S"

# Etichette booleane in italiano. Coerenti con quelle usate in altri
# moduli (es. RowActionsMenu, ListaConfigurabile slot default per
# tipo_dato='boolean').
BOOL_TRUE_LABEL: str = "Si"
BOOL_FALSE_LABEL: str = "No"

# Separatori numerici italiani: virgola decimale, punto migliaia.
# In v1 NON applichiamo automaticamente il thousands separator (un id
# come 1000 non deve diventare "1.000"). Si attiva solo quando il
# formato della colonna lo richiede esplicitamente (`thousand`,
# `currency_eur`).
DECIMAL_SEPARATOR: str = ","
THOUSANDS_SEPARATOR: str = "."

# Simbolo valuta default. Per multi-valuta in futuro, override per
# emittente fiscale via parameter `LOCALE_CURRENCY_SYMBOL`.
CURRENCY_SYMBOL: str = "€"


# =================================================================
# Formattatori atomici (uno per tipo)
# =================================================================

# Scopo: Porta un istante nel fuso DELL'AZIENDA prima di
#        scriverlo (vedi l'intestazione del modulo). E' la sede unica della
#        conversione: la usano i formattatori qui sotto e il helper
#        None-preserving dei documenti (`_date_formatting`), cosi' un PDF e un
#        export dicono la stessa ora.
# ⚠️ Un datetime NAIVE non si tocca: non porta un fuso, quindi non c'e'
#    niente da convertire (`timestamp without time zone`, o un valore costruito
#    a mano nei test) — e `localtime` su un naive solleverebbe.
# ⭐ Il fuso e' DICHIARATO, non quello attivato: la conversione e' giusta anche
#    fuori da una richiesta o da un comando (un thread, un test).
def in_ora_locale(value: datetime) -> datetime:
    return timezone.localtime(value, fuso_aziendale()) if timezone.is_aware(value) else value


# Scopo: Formatta una `date` Python in DD-MM-YYYY (formato italiano).
#        Accetta anche stringhe ISO ('2026-05-10') per robustezza:
#        alcune query potrebbero ritornare stringhe (jsonb opaco) e il
#        chiamante non sempre fa il cast.
#        None -> stringa vuota (export-friendly).
# ⚠️ Da un `datetime` si prende il giorno IN ORA LOCALE: le 23:30 UTC del 14
#    sono gia' il 15 a Roma, e la data di un export deve essere quella che
#    l'operatore ha visto a video.
def format_date(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        # datetime e' anche date in Python: prendi solo la parte data.
        return in_ora_locale(value).strftime(DATE_FORMAT)
    if isinstance(value, date):
        return value.strftime(DATE_FORMAT)
    if isinstance(value, str):
        # Best-effort: parse ISO e riformatta. Se fallisce, ritorna
        # la stringa originale per non perdere informazione.
        try:
            return in_ora_locale(datetime.fromisoformat(value)).strftime(DATE_FORMAT)
        except (ValueError, TypeError):
            return value
    return str(value)


# Scopo: Formatta una `datetime` Python in DD-MM-YYYY HH:MM, in ORA LOCALE.
#        `with_seconds=True` per casi che richiedono precisione (audit,
#        logs). Accetta anche stringhe ISO con timezone.
def format_datetime(value: Any, *, with_seconds: bool = False) -> str:
    fmt = DATETIME_FULL_FORMAT if with_seconds else DATETIME_FORMAT
    if value is None:
        return ""
    if isinstance(value, datetime):
        return in_ora_locale(value).strftime(fmt)
    if isinstance(value, str):
        try:
            return in_ora_locale(datetime.fromisoformat(value)).strftime(fmt)
        except (ValueError, TypeError):
            return value
    return str(value)


# Scopo: Formatta un boolean in etichetta italiana ("Si"/"No"). Accetta
#        bool stretto + None ("" stringa vuota).
def format_bool(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return BOOL_TRUE_LABEL if value else BOOL_FALSE_LABEL
    # Tolleranza per stringhe "true"/"false" (alcuni JSONB).
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("true", "t", "1", "yes", "y", "si", "sì"):
            return BOOL_TRUE_LABEL
        if v in ("false", "f", "0", "no", "n"):
            return BOOL_FALSE_LABEL
    return str(value)


# Scopo: Formatta un numero (int/float/Decimal) con separatori
#        italiani. Default: niente migliaia (preserva ID/conteggi),
#        virgola decimale solo se il valore ne ha. `formato` opzionale
#        per casi specifici:
#          - 'thousand'     : 1234.56 -> "1.234,56"
#          - 'currency_eur' : 1234.56 -> "1.234,56 €"
#          - 'currency_eur_6': 12.5 -> "12,500000 €" (prezzi UNITARI: listini a
#                             6 decimali, brief-db-liste-righe-documento)
#          - 'percent_2'    : 12.34 -> "12,34 %" — il valore e' GIA' in
#                             percentuale, come lo salva il modello
#                             (`sconto_percentuale` = 10 per il 10%).
#          ⛔ Fino al 2026-09-28 `percent_2` qui era una FRAZIONE (0.1234 ->
#             12,34%) e a video no: lo stesso formato di catalogo diceva due
#             cose, e uno sconto del 10 sarebbe uscito nel file come 1000%.
#             Nessuna lista lo usava ancora; la sede del significato e' il
#             frontend (`CellaConfigurabile`), decisione di Tid.
def format_number(value: Any, *, formato: str | None = None) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        # bool e' int in Python: tratta come boolean italiano se passato
        # qui per errore.
        return format_bool(value)
    if not isinstance(value, (int, float, Decimal)):
        return str(value)

    if formato == "percent_2":
        return _format_decimal(value, decimals=2, thousands=True) + " %"
    if formato == "currency_eur":
        return _format_decimal(value, decimals=2, thousands=True) + f" {CURRENCY_SYMBOL}"
    if formato == "currency_eur_6":
        return _format_decimal(value, decimals=6, thousands=True) + f" {CURRENCY_SYMBOL}"
    if formato == "thousand":
        return _format_decimal(value, decimals=None, thousands=True)
    # Default: niente migliaia; rispetta i decimali presenti.
    return _format_decimal(value, decimals=None, thousands=False)


# Scopo: Helper privato — converte numero in stringa con separatori
#        italiani. `decimals=None` mantiene i decimali nativi (no
#        padding); `decimals=N` forza N cifre dopo la virgola.
def _format_decimal(
    value: Any,
    *,
    decimals: int | None,
    thousands: bool = False,
) -> str:
    # Normalizza a Decimal per controllo formato.
    d = Decimal(str(value))
    if decimals is not None:
        # Quantize a N cifre (no banker's rounding: ROUND_HALF_UP per
        # consistenza con UI/Excel).
        from decimal import ROUND_HALF_UP
        q = Decimal(10) ** -decimals
        d = d.quantize(q, rounding=ROUND_HALF_UP)
    # Formatta con punto/virgola standard Python, poi sostituisci.
    raw = format(d, "f")
    if "." in raw:
        int_part, dec_part = raw.split(".", 1)
    else:
        int_part, dec_part = raw, ""
    if thousands:
        # Inserisci THOUSANDS_SEPARATOR ogni 3 cifre dell'int_part.
        sign = ""
        if int_part.startswith("-"):
            sign = "-"
            int_part = int_part[1:]
        groups: list[str] = []
        while len(int_part) > 3:
            groups.insert(0, int_part[-3:])
            int_part = int_part[:-3]
        groups.insert(0, int_part)
        int_part = sign + THOUSANDS_SEPARATOR.join(groups)
    if dec_part:
        return f"{int_part}{DECIMAL_SEPARATOR}{dec_part}"
    return int_part


# =================================================================
# Dispatcher principale per export
# =================================================================

# Scopo: Formatta un valore per l'export tabellare (CSV/XLSX) basandosi
#        sui metadata della colonna.
#
#        Argomenti:
#          - value: valore raw dal repository (Python date/datetime/
#            int/float/Decimal/bool/str/None)
#          - tipo_dato: enum `ui.tipo_dato` ('string', 'numeric',
#            'date', 'datetime', 'boolean', 'enum'). Se None, fallback
#            alla rilevazione automatica via isinstance.
#          - formato: token formato dalla `lista_colonna.formato`
#            (es. 'currency_eur', 'percent_2'). Solo per tipo_dato
#            'numeric'.
#
#        Ritorna: stringa formattata adatta a CSV/XLSX. Sempre str
#        (mai None) per non rompere CSV writer.
#
#        Pattern dispatch:
#          1. None -> "" (sempre)
#          2. tipo_dato fornito -> usa quello (priorita' alta)
#          3. tipo_dato None -> isinstance dispatch
#          4. Fallback: str(value)
def format_for_export(
    value: Any,
    *,
    tipo_dato: str | None = None,
    formato: str | None = None,
) -> str:
    if value is None:
        return ""

    # Priorita' al `tipo_dato` dichiarato in `lista_colonna`: e' la
    # fonte di verita' del catalogo (l'admin l'ha dichiarato registrando
    # la colonna). isinstance e' fallback per quando il caller non
    # passa il tipo (es. test rapidi, righe ad-hoc).
    if tipo_dato == "date":
        return format_date(value)
    if tipo_dato == "datetime":
        return format_datetime(value)
    if tipo_dato == "boolean":
        return format_bool(value)
    if tipo_dato == "numeric":
        return format_number(value, formato=formato)
    if tipo_dato in ("string", "enum"):
        return str(value)

    # Fallback: dispatch per tipo Python. NB: `bool` prima di `int`
    # (in Python bool e' int).
    if isinstance(value, bool):
        return format_bool(value)
    if isinstance(value, datetime):
        return format_datetime(value)
    if isinstance(value, date):
        return format_date(value)
    if isinstance(value, (int, float, Decimal)):
        return format_number(value, formato=formato)
    if isinstance(value, str):
        return value
    return str(value)
