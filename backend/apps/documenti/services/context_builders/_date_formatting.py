# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper di formattazione date condivisi dai context builder
#        documentali (PREVENTIVO/OFFERTA_COMMERCIALE/CONTRATTO/ORDINE_VENDITA).
#        Estratti applicando la regola del 2 (memoria
#        `feedback_regola_del_2_estrai_bb`): le tre funzioni erano duplicate
#        byte-identiche in 4 builder.
#
#        Specificita' vs `apps.core.services.locale_formatters.format_date`
#        (che e' export-oriented): qui le funzioni sono **None-preserving**
#        (`None -> None`, non `""`) ed espongono anche la variante ISO. Il
#        None-preserving e' deliberato: il context del documento viene
#        serializzato in JSON per il `context_hash` (dedup logico
#        deterministico) e il template Jinja distingue "data assente" (None)
#        da "data vuota". Per stringhe non parsabili si restituisce il valore
#        originale (no perdita d'informazione), coerente col comportamento
#        storico dei builder.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from apps.core.services.locale_formatters import in_ora_locale


# Scopo: Formatta una data in DD-MM-YYYY (formato italiano). None-preserving;
#        valore non parsabile -> stringa originale.
def format_date_it(value: Any) -> str | None:
    parsed = _parse_date(value)
    if parsed is None:
        return None if value is None else str(value)
    return parsed.strftime("%d-%m-%Y")


# Scopo: Formatta una data in ISO 8601 (YYYY-MM-DD). None-preserving;
#        valore non parsabile -> stringa originale.
def format_date_iso(value: Any) -> str | None:
    parsed = _parse_date(value)
    if parsed is None:
        return None if value is None else str(value)
    return parsed.isoformat()


# Scopo: Parsing tollerante a date/datetime/stringa ISO. Ritorna None se non
#        interpretabile (il caller decide il fallback).
def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        # ⚠️ Il giorno in ORA LOCALE, come negli export (2026-09-14): un
        #    istante a cavallo della mezzanotte UTC e' gia' il giorno dopo a
        #    Roma, e il documento deve portare la data che l'operatore vede.
        return in_ora_locale(value).date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        raw = value.strip()
        # ⚠️ Una stringa con l'ORA e' un istante: il giorno e' quello
        #    dell'azienda, non i primi dieci caratteri (che con un offset `Z` o
        #    `+00:00` sono il giorno UTC). Fino al 2026-10-09 si tagliava e
        #    basta (brief un-solo-fuso-aziendale B-6).
        if len(raw) > 10:
            try:
                return in_ora_locale(datetime.fromisoformat(raw)).date()
            except ValueError:
                return None
        if len(raw) == 10:
            try:
                return date.fromisoformat(raw)
            except ValueError:
                return None
    return None
