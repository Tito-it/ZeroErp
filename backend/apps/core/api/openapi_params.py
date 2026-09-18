# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le frasi dei parametri di lista nello schema OpenAPI, scritte una
#        volta — oggi la descrizione di `order_by`, LETTA dalla whitelist del
#        repository invece che ricopiata accanto a lei.
# Note: ⛔ Il file non definisce comportamento: definisce cosa lo schema DICE.
#       Nato il 2026-09-19 (regola del 2, ok Tid) dalle due copie di
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
