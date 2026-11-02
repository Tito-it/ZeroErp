# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper di formattazione numerica condivisi dai context builder
#        documentali. Gemello di `_date_formatting`: le date erano gia'
#        formattate nel builder, i numeri no — e arrivavano al template come
#        stringhe grezze del DB, cioe' con la scala della colonna. Da qui
#        quantita' come «5.000000» nel PDF (segnalazione di Tid, 2026-08-04).
#
#        PERCHE' NEL BUILDER E NON NEL TEMPLATE. L'ambiente Jinja del render
#        e' volutamente vanilla (nessun filtro custom): con i soli built-in
#        non si ottiene il formato italiano — `|round(2)` produce «5.0», col
#        punto e senza padding. Formattare qui e' anche coerente con le date,
#        e mantiene i template leggibili: stampano quello che ricevono.
#
#        NONE-PRESERVING, come `_date_formatting` e per la stessa ragione: il
#        context viene serializzato per il `context_hash` e il template
#        distingue «assente» (None → ramo "-") da «zero».
#
#        ⚠️ DUE REGOLE DIVERSE, E LA DIFFERENZA E' DI DOMINIO:
#        * gli IMPORTI hanno sempre 2 decimali — sono denaro;
#        * quantita' e prezzi unitari hanno **minimo 2, massimo 6** decimali,
#          con gli zeri superflui tolti. Troncare a 2 anche questi sembrerebbe
#          piu' semplice ma in un ERP di utilities e' una perdita di dato
#          vera: un prezzo di 0,153 €/kWh diventerebbe 0,15 (-2%), e una
#          quantita' di 1,234567 mc perderebbe la misura del contatore. Cosi'
#          invece «5.000000» si legge «5,00» — che e' cio' che si voleva — e
#          «0.153000» resta «0,153».
#
#        ⛔ UN NUMERO CHE NON E' UN NUMERO FERMA LA GENERAZIONE (decisione di
#        Tid, 2026-10-09, opzione C di brief-db-valore-numerico-non-finito-nei-
#        documenti): NaN e infiniti non si stampano come «NaN» e non si
#        nascondono dietro un trattino. Il DB li rifiuta su ogni colonna
#        `numeric` (CHECK `chk_*_finito`), ma non vede dentro il `context_json`
#        congelato che la ristampa rilegge: questa e' la sola difesa su quel
#        percorso. Per questo ogni formattatore riceve il nome del `campo`.
# ------------------------------------------------------------

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.core.services.locale_formatters import (
    DECIMAL_SEPARATOR,
    THOUSANDS_SEPARATOR,
)

E_DOCUMENTI_VALORE_NUMERICO_NON_FINITO = "E_DOCUMENTI_VALORE_NUMERICO_NON_FINITO"

# Decimali dei valori "di misura" (quantita', prezzi unitari, coefficienti):
# padding fino al minimo, troncatura oltre il massimo.
_MIN_DECIMALI_MISURA = 2
_MAX_DECIMALI_MISURA = 6
# Decimali del denaro: sempre esattamente due.
_DECIMALI_IMPORTO = 2


# Scopo: converte in Decimal cio' che e' convertibile. Ritorna None per i
#        valori non numerici (stringhe descrittive, dict): il chiamante li
#        lascia passare invariati invece di corromperli.
def _to_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value.strip())
        except (InvalidOperation, ValueError):
            return None
    return None


# Scopo: converte come `_to_decimal` e in piu' pretende un numero FINITO.
#        Invariante rotta (classe TECNICO): il campo e il valore vanno nel
#        dettaglio e nel contesto, per chi diagnostica — la frase del catalogo
#        e' senza segnaposto (§6.3 del brief).
def _to_decimal_finito(value: Any, campo: str) -> Decimal | None:
    d = _to_decimal(value)
    if d is None or d.is_finite():
        return d
    ErrorManager.raise_error(
        code=E_DOCUMENTI_VALORE_NUMERICO_NON_FINITO,
        message="Il documento non si può generare: un valore numerico non è un numero.",
        detail=f"Il campo «{campo}» vale {value!r}: NaN e infiniti non si stampano.",
        context={"field": campo, "valore": str(value)},
        function_name="documenti.context_builders._to_decimal_finito",
        log_to_db=True,
    )


# Scopo: l'esponente di un Decimal FINITO. Per NaN e infiniti `as_tuple()`
#        rende una lettera ('n', 'N', 'F'), non un int: ci si arriva solo dopo
#        `_to_decimal_finito`, e il controllo esplicito lo dice anche al type
#        checker (prima il segno meno sulla lettera era un TypeError anonimo).
def _esponente(d: Decimal) -> int:
    exp = d.as_tuple().exponent
    if isinstance(exp, str):
        raise TypeError(f"Decimal non finito: {d!r}")
    return exp


# Scopo: rende un Decimal in stile italiano (virgola decimale, punto per le
#        migliaia). Riusa i separatori di `locale_formatters`: il formato
#        italiano si decide in un posto solo.
def _rendi(d: Decimal, *, thousands: bool) -> str:
    raw = format(d, "f")
    int_part, _, dec_part = raw.partition(".")
    if thousands:
        segno = ""
        if int_part.startswith("-"):
            segno, int_part = "-", int_part[1:]
        gruppi: list[str] = []
        while len(int_part) > 3:
            gruppi.insert(0, int_part[-3:])
            int_part = int_part[:-3]
        gruppi.insert(0, int_part)
        int_part = segno + THOUSANDS_SEPARATOR.join(gruppi)
    return f"{int_part}{DECIMAL_SEPARATOR}{dec_part}" if dec_part else int_part


# Scopo: formatta un valore di MISURA (quantita', prezzo unitario,
#        coefficiente): minimo 2 decimali, massimo 6, zeri superflui tolti.
#        None-preserving; valore non numerico restituito invariato; valore
#        non finito → E_DOCUMENTI_VALORE_NUMERICO_NON_FINITO col `campo`.
def format_misura(value: Any, *, campo: str) -> Any:
    d = _to_decimal_finito(value, campo)
    if d is None:
        return value
    # Oltre il massimo si arrotonda (ROUND_HALF_UP come UI/Excel, mai
    # banker's rounding: su un documento la meta' deve salire).
    if -_esponente(d) > _MAX_DECIMALI_MISURA:
        d = d.quantize(Decimal(10) ** -_MAX_DECIMALI_MISURA, rounding=ROUND_HALF_UP)
    # `normalize` toglie gli zeri finali ma su interi produce la notazione
    # esponenziale (5E+1): il quantize successivo la riporta a posizionale.
    d = d.normalize()
    decimali_attuali = max(0, -_esponente(d))
    if decimali_attuali < _MIN_DECIMALI_MISURA:
        d = d.quantize(Decimal(10) ** -_MIN_DECIMALI_MISURA)
    return _rendi(d, thousands=True)


# Scopo: formatta un IMPORTO in denaro: sempre 2 decimali, con migliaia.
#        Nessun simbolo di valuta — quello lo mette il template, che sa se
#        la colonna ha gia' l'intestazione.
#        None-preserving; valore non numerico restituito invariato; valore
#        non finito → E_DOCUMENTI_VALORE_NUMERICO_NON_FINITO col `campo`.
def format_importo(value: Any, *, campo: str) -> Any:
    d = _to_decimal_finito(value, campo)
    if d is None:
        return value
    d = d.quantize(Decimal(10) ** -_DECIMALI_IMPORTO, rounding=ROUND_HALF_UP)
    return _rendi(d, thousands=True)


# Scopo: applica un formattatore alle sole chiavi indicate di un dict,
#        lasciando intatto tutto il resto. Le chiavi assenti si ignorano:
#        i builder condividono questo helper ma non le stesse proiezioni.
def formatta_campi(
    riga: dict[str, Any],
    *,
    misure: tuple[str, ...] = (),
    importi: tuple[str, ...] = (),
) -> dict[str, Any]:
    out = dict(riga)
    for chiave in misure:
        if chiave in out:
            out[chiave] = format_misura(out[chiave], campo=chiave)
    for chiave in importi:
        if chiave in out:
            out[chiave] = format_importo(out[chiave], campo=chiave)
    return out
