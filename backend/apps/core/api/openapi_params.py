# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le frasi dei parametri di lista nello schema OpenAPI, scritte una
#        volta — la descrizione di `order_by`, LETTA dalla whitelist del
#        repository invece che ricopiata accanto a lei, e il parametro `search`
#        delle liste che cercano col BB `add_ricerca_full_condition`.
# Note: ⛔ Il file non definisce comportamento: definisce cosa lo schema DICE.
#       Nato il 2026-09-18 (regola del 2, ok Tid) dalle due copie di
#       `_descrizione_order_by` in `pagamenti` e `magazzino`, gia' divergenti
#       nel testo («nome FISICO» contro «nome FISICO della colonna»), e dalle
#       QUATTRO descrizioni ancora scritte a mano nello stesso file di
#       pagamenti, accanto all'helper: la prima stesura della lista rate ne
#       elencava sette colonne su nove, e quella delle rate fuori capienza
#       aveva perso la colonna aggiunta il giorno prima — due elenchi scritti a
#       mano accanto alla mappa che li smentiva. Una descrizione che LEGGE la
#       mappa non puo' smentirla.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Iterable

from drf_spectacular.utils import OpenApiParameter

from apps.core.db._helpers import RICERCA_MIN_CARATTERI


# Scopo: la frase «Whitelist (nome FISICO): …» di un `order_by`, dalla
#        whitelist del repository (`dict[chiave esposta -> colonna SQL]`, o
#        qualunque iterabile di nomi). `nota` e' cio' che la lista aggiunge:
#        il default, le colonne che non ordinano, un significato di coppia.
# ⚠️ Il nome esposto e' quello FISICO del catalogo (`campo_sorgente`): e' cio'
#    che `<ListaConfigurabile>` manda in `order_by` (api.md §«La whitelist di
#    ordinamento si chiava sul campo_sorgente FISICO»).
def descrizione_order_by(colonne: Iterable[str], nota: str = "") -> str:
    elenco = " | ".join(colonne)
    frase = f"Whitelist (nome FISICO della colonna): {elenco}."
    return f"{frase} {nota}" if nota else frase


# Scopo: il parametro `search` di una lista configurabile che cerca col BB
#        `add_ricerca_full_condition`. Gli argomenti ripetono quelli della
#        chiamata al BB nel repository (`min_caratteri`) e dicono se la view
#        risponde 400 sotto soglia (`require_min_search_length`).
# ⛔ La frase NON elenca le colonne: le decide il catalogo della lista, per
#    l'operatore, e l'amministratore le cambia dal pannello. Un elenco scritto
#    qui e' una seconda sede che invecchia al primo cambio — ed e' come e'
#    nato questo BB (regola del 2 fra domini, ok Tid 2026-09-24): una trentina
#    di dichiarazioni, con testi gia' separati dal codice («min 2», «>=3 char»
#    dove il 400 era stato ritirato, P.IVA e C.F. dove si cerca l'id fiscale
#    univoco, il codice interno che non si cerca).
def param_ricerca_full(
    *,
    min_caratteri: int = RICERCA_MIN_CARATTERI,
    rifiuta_sotto_soglia: bool = False,
) -> OpenApiParameter:
    frase = (
        "Ricerca libera sulle colonne che il catalogo della lista accende per "
        "l'operatore (`ricerca_full` nella configurazione della lista)."
    )
    if min_caratteri <= 1:
        soglia = "Da un carattere."
    elif rifiuta_sotto_soglia:
        soglia = f"Sotto {min_caratteri} caratteri: 400 `E_SEARCH_VALIDATION`."
    else:
        soglia = f"Sotto {min_caratteri} caratteri non filtra."
    return OpenApiParameter(
        name="search", type=str, location=OpenApiParameter.QUERY, required=False,
        description=f"{frase} {soglia}",
    )
