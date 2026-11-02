# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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


# ============================================================
# Generazione codice fiscale italiano
# ============================================================

# Tabella mese inversa (numero → lettera)
_MESE_MAP_INV = {v: k for k, v in _MESE_MAP.items()}

# Tabella check digit (algoritmo Ministero delle Finanze)
_DISPARI = {
    '0': 1, '1': 0, '2': 5, '3': 7, '4': 9, '5': 13, '6': 15, '7': 17, '8': 19, '9': 21,
    'A': 1, 'B': 0, 'C': 5, 'D': 7, 'E': 9, 'F': 13, 'G': 15, 'H': 17, 'I': 19, 'J': 21,
    'K': 2, 'L': 4, 'M': 18, 'N': 20, 'O': 11, 'P': 3, 'Q': 6, 'R': 8, 'S': 12, 'T': 14,
    'U': 16, 'V': 10, 'W': 22, 'X': 25, 'Y': 24, 'Z': 23,
}
_PARI = {
    '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
    'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9,
    'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19,
    'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25,
}
_CHECK_ALPHA = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

_VOCALI = set('AEIOU')


def _estrai_consonanti_vocali(s: str) -> tuple[str, str]:
    """Scopo: Separa consonanti e vocali da una stringa (solo lettere)."""
    s = ''.join(c for c in s.upper() if c.isalpha())
    consonanti = ''.join(c for c in s if c not in _VOCALI)
    vocali = ''.join(c for c in s if c in _VOCALI)
    return consonanti, vocali


def _codice_cognome(cognome: str) -> str:
    """Scopo: Genera i 3 caratteri del cognome per il CF.
    Regola: prime 3 consonanti, poi vocali, poi X se insufficiente."""
    cons, voc = _estrai_consonanti_vocali(cognome)
    pool = cons + voc
    return (pool + 'XXX')[:3]


def _codice_nome(nome: str) -> str:
    """Scopo: Genera i 3 caratteri del nome per il CF.
    Regola speciale: se >= 4 consonanti, prende 1a, 3a, 4a."""
    cons, voc = _estrai_consonanti_vocali(nome)
    if len(cons) >= 4:
        return cons[0] + cons[2] + cons[3]
    pool = cons + voc
    return (pool + 'XXX')[:3]


def _check_digit(cf15: str) -> str:
    """Scopo: Calcola il carattere di controllo (16° carattere) del CF."""
    total = 0
    for i, c in enumerate(cf15.upper()):
        total += _DISPARI[c] if (i % 2 == 0) else _PARI[c]
    return _CHECK_ALPHA[total % 26]


def genera_cf_it(
    cognome: str,
    nome: str,
    data_nascita: date,
    sesso: str,
    codice_catastale: str,
) -> str:
    """Scopo: Genera codice fiscale italiano da dati anagrafici.

    Parametri:
        cognome: cognome del soggetto
        nome: nome del soggetto
        data_nascita: data di nascita
        sesso: 'M' o 'F'
        codice_catastale: codice Belfiore del comune di nascita (es. 'L736')

    Risultato: codice fiscale di 16 caratteri (maiuscolo).
    """
    parte_cognome = _codice_cognome(cognome)
    parte_nome = _codice_nome(nome)

    anno = f"{data_nascita.year % 100:02d}"
    mese = _MESE_MAP_INV[data_nascita.month]
    giorno = data_nascita.day + (40 if sesso.upper() == 'F' else 0)
    giorno_str = f"{giorno:02d}"

    cf15 = f"{parte_cognome}{parte_nome}{anno}{mese}{giorno_str}{codice_catastale.upper()}"
    return cf15 + _check_digit(cf15)
