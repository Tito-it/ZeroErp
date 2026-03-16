# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Validazione congruenza codice fiscale italiano (suffisso _it).
#        La validazione formale (check digit, omocodia) e' nel DB
#        (script.fn_valida_codice_fiscale). Qui si verifica la congruenza
#        con i dati anagrafici: data nascita, sesso, comune di nascita.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date

# Tabella omocodia: cifre sostituite con lettere (posizioni 7,8,10,11,13,14,15)
_OMOCODIA_MAP = {
    'L': '0', 'M': '1', 'N': '2', 'P': '3', 'Q': '4',
    'R': '5', 'S': '6', 'T': '7', 'U': '8', 'V': '9',
}

# Mapping mese CF → numero mese
_MESE_MAP = {
    'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'H': 6,
    'L': 7, 'M': 8, 'P': 9, 'R': 10, 'S': 11, 'T': 12,
}


def _decodifica_omocodia(c: str) -> str:
    """Scopo: Sostituisce lettere omocodiche con la cifra corrispondente."""
    return _OMOCODIA_MAP.get(c, c)


def _estrai_dati_cf(cf: str) -> dict | None:
    """Scopo: Estrae data di nascita, sesso e codice catastale dal CF.
    Gestisce l'omocodia decodificando le posizioni numeriche sostituite."""
    cf = cf.upper().strip()
    if len(cf) != 16:
        return None

    # Posizioni numeriche che possono avere omocodia: 7,8 (anno), 10,11 (giorno), 13,14 (codice comune cifre)
    anno_str = _decodifica_omocodia(cf[6]) + _decodifica_omocodia(cf[7])
    mese_char = cf[8]
    giorno_str = _decodifica_omocodia(cf[9]) + _decodifica_omocodia(cf[10])

    try:
        anno_2d = int(anno_str)
        giorno = int(giorno_str)
    except ValueError:
        return None

    mese = _MESE_MAP.get(mese_char)
    if mese is None:
        return None

    # Sesso: femmine hanno giorno + 40
    if giorno > 40:
        sesso = 'F'
        giorno -= 40
    else:
        sesso = 'M'

    # Anno a 4 cifre: euristica — se >= 40 → 1900, altrimenti 2000
    # Copre nascite 1940-2039 (sufficiente per uso corrente)
    anno = 1900 + anno_2d if anno_2d >= 40 else 2000 + anno_2d

    # Codice catastale (posizioni 12-15): lettera + 3 cifre (con possibile omocodia)
    codice_catastale = (
        cf[11]
        + _decodifica_omocodia(cf[12])
        + _decodifica_omocodia(cf[13])
        + _decodifica_omocodia(cf[14])
    )

    return {
        'anno': anno,
        'mese': mese,
        'giorno': giorno,
        'sesso': sesso,
        'codice_catastale': codice_catastale,
    }


def valida_cf_congruenza_it(
    cf: str,
    data_nascita: date | None = None,
    sesso: str | None = None,
    codice_catastale_comune: str | None = None,
) -> list[str]:
    """Scopo: Verifica congruenza CF italiano con dati anagrafici.
    Restituisce lista di errori (vuota = tutto ok).
    Non valida il check digit (lo fa la funzione DB).

    Parametri:
        cf: codice fiscale (16 caratteri)
        data_nascita: data di nascita del soggetto (opzionale)
        sesso: 'M' o 'F' (opzionale)
        codice_catastale_comune: codice Belfiore del comune di nascita (opzionale)

    Risultato: lista stringhe errore (vuota = congruente).
    """
    errors: list[str] = []

    dati = _estrai_dati_cf(cf)
    if dati is None:
        errors.append("Formato codice fiscale non valido.")
        return errors

    # Congruenza data nascita
    if data_nascita is not None:
        if data_nascita.year != dati['anno']:
            errors.append(
                f"Anno di nascita nel CF ({dati['anno']}) "
                f"non corrisponde a {data_nascita.year}."
            )
        if data_nascita.month != dati['mese']:
            errors.append(
                f"Mese di nascita nel CF ({dati['mese']}) "
                f"non corrisponde a {data_nascita.month}."
            )
        if data_nascita.day != dati['giorno']:
            errors.append(
                f"Giorno di nascita nel CF ({dati['giorno']}) "
                f"non corrisponde a {data_nascita.day}."
            )

    # Congruenza sesso
    if sesso is not None:
        sesso_upper = sesso.upper()
        if sesso_upper in ('M', 'F') and sesso_upper != dati['sesso']:
            errors.append(
                f"Sesso nel CF ({dati['sesso']}) "
                f"non corrisponde a {sesso_upper}."
            )

    # Congruenza comune di nascita (codice catastale/Belfiore)
    if codice_catastale_comune is not None:
        cat_upper = codice_catastale_comune.upper()
        if cat_upper != dati['codice_catastale']:
            errors.append(
                f"Codice catastale nel CF ({dati['codice_catastale']}) "
                f"non corrisponde a {cat_upper}."
            )

    return errors
