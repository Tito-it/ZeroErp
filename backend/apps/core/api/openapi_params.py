# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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

from drf_spectacular.utils import OpenApiParameter, inline_serializer
from rest_framework import serializers


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
#        `add_ricerca_full_condition`.
# ⛔ La frase NON elenca le colonne: le decide il catalogo della lista, per
#    l'operatore, e l'amministratore le cambia dal pannello. Un elenco scritto
#    qui e' una seconda sede che invecchia al primo cambio — ed e' come e'
#    nato questo BB (regola del 2 fra domini, ok Tid 2026-09-24): una trentina
#    di dichiarazioni, con testi gia' separati dal codice («min 2», «>=3 char»
#    dove il 400 era stato ritirato, P.IVA e C.F. dove si cerca l'id fiscale
#    univoco, il codice interno che non si cerca).
# ⛔ E per la stessa ragione NON dice la soglia: e' un fatto della lista
#    (`ricerca_min_caratteri` nella configurazione, brief-db-be-fe-ricerca-
#    soglia-per-lista), e lo schema non puo' leggere il catalogo all'import.
#    Fino al 2026-09-26 la view la ripeteva (`min_caratteri=1`), accanto al
#    repository che la ripeteva una seconda volta.
# ⭐ Nessuna lista a catalogo risponde 400 sotto soglia (§6 a, Tid 2026-09-26):
#    il termine corto non filtra, sempre. L'opzione `rifiuta_sotto_soglia`, che
#    lo dichiarava per sette view, e' uscita con loro.
def param_ricerca_full() -> OpenApiParameter:
    return OpenApiParameter(
        name="search", type=str, location=OpenApiParameter.QUERY, required=False,
        description=(
            "Ricerca libera sulle colonne che il catalogo della lista accende per "
            "l'operatore (`ricerca_full` nella configurazione della lista). Sotto "
            "la soglia della lista (`ricerca_min_caratteri` nella configurazione) "
            "il termine non filtra."
        ),
    )


# Scopo: ⭐ Lo schema della risposta di un LOOKUP, in un punto solo:
#        `{"data": {"results": [...]}, "meta": {...}}` (api.md §«L'envelope di un
#        lookup»). `nome` e' il nome del componente OpenAPI; `riga` lo schema di
#        una riga, se lo si vuole dichiarare (default: oggetto libero).
# ⛔ Regola del 2 (2026-10-21, brief-be-verifica-documentazione-api §B10): dieci
#    lookup di `core/api/views_lookup.py` dichiaravano `data` come LISTA NUDA,
#    mentre rispondono `{results}`. Chi genera il client dallo schema leggeva una
#    lista che non arriva mai. Scritto a mano, lo schema diverge dalla risposta.
def risposta_lookup(nome: str, riga: serializers.Field | None = None) -> serializers.Serializer:
    return inline_serializer(
        name=nome,
        fields={
            "data": inline_serializer(
                name=f"{nome}Data",
                fields={"results": serializers.ListField(child=riga or serializers.DictField())},
            ),
            "meta": serializers.DictField(required=False),
        },
    )


# Scopo: ⭐ I parametri OpenAPI della finestra di una lista, `limit` e `offset`,
#        in un punto solo: da usare con `*parametri_finestra()` dentro
#        `parameters=[...]`. Dal 2026-10-21 tutte le liste paginano cosi'
#        (`pagina_da_query`); `page`/`page_size` sono un 400.
#        `default_limit`/`max_limit` quelli della lista, se non sono gli standard
#        (gli stessi passati a `pagina_da_query`).
def parametri_finestra(
    *, default_limit: int | None = None, max_limit: int | None = None,
) -> list[OpenApiParameter]:
    from apps.core.api.constants import DEFAULT_LIMIT, MAX_LIMIT

    return [
        OpenApiParameter(
            name="limit", type=int, location=OpenApiParameter.QUERY, required=False,
            description=(
                f"Righe per pagina (default {default_limit or DEFAULT_LIMIT}, "
                f"max {max_limit or MAX_LIMIT})."
            ),
        ),
        OpenApiParameter(
            name="offset", type=int, location=OpenApiParameter.QUERY, required=False,
            description="Righe da saltare (default 0). `page`/`page_size` sono un 400.",
        ),
    ]

