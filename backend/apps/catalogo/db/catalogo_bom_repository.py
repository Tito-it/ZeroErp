# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB specializzato per la BoM degli articoli. I codici dei due
#        bersagli delle note di catalogo stanno qui (`NOTA_TARGET_*`).
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any
from uuid import UUID

from django.db import connection

from apps.core.db._helpers import (
    RicercaFull,
    row_to_dict,
    rows_to_list,
)
from apps.core.db.righe_lista_mixin import RigheListaCompletaMixin
from apps.core.db.sql_write_helpers import execute_dynamic_insert

# Colonne SCRIVIBILI di una riga BoM: whitelist RIGIDA del BB di scrittura
# (2026-09-26 — prima mappa nome -> tipo per `sql_placeholder`/`to_write_param`,
# ritirati). `meta` (jsonb) arriva dal service come dict o None: il BB lo
# casta da solo, `jsonb=` non serve. `prodotto_id` NON e' qui: lo scrive il
# repository dal path (`create_componente`), mai il payload.
COMPONENTE_WRITE_COLUMNS: frozenset[str] = frozenset({
    "componente_id",
    "coeff_qta",
    # `partecipa_qta` e `determina_qta_padre` ritirati il 2026-10-02: nessuna
    # logica li leggeva (brief-db-bom-flag-quantita-e-kit-in-fattura, D-1).
    "obbligatorio",
    "valido_dal",
    "valido_al",
    "attivo",
    # Il modo di esposizione in fattura (NASCOSTO / DESCRITTIVO / VALORIZZATO,
    # `config.esposizioni_componente`): il valore lo giudica la FK, un codice
    # fuori catalogo torna 23503 (brief-db-esposizione-componenti-kit-in-fattura).
    "esposizione_in_fattura",
    "meta",
})

# ⭐ LE RIGHE DELLA DISTINTA SI LEGGONO DALLA VISTA, e solo da li'
#    (brief-db-liste-righe-documento, D-8.5, 2026-09-28).
#    `catalogo.vw_articoli_componenti_dettaglio` e' la sede unica della
#    proiezione e della capability di chiusura (`puo_chiudersi`,
#    `data_min_chiusura`, `data_default_chiusura`, `motivo_non_chiudibile`).
#    Fino a quel giorno questo modulo la ricopiava in Python
#    (`COMPONENTE_DETAIL_COLUMNS`, con il commento «aggiornare ENTRAMBI»), e le
#    due copie erano gia' divergite: la vista non aveva `esposto_in_fattura` ne'
#    `determina_qta_padre`. Il DB le ha portate al pari, qui la copia si ritira.
#    ⛔ La vista non filtra e non ordina (per progetto, dal suo `COMMENT`):
#    l'ordine lo mette il repository.
_VISTA_COMPONENTI = "catalogo.vw_articoli_componenti_dettaglio"

# La lista configurabile `catalogo.articolo_componenti` (lista 101): la ricerca
# sulle colonne `ricercabile_full = t` del seed, il codice e la descrizione del
# componente. `test_ricerca_full_seed` legge questa costante.
_RICERCA_COMPONENTI = RicercaFull(
    "catalogo.articolo_componenti", ("componente_codice", "componente_descrizione"),
)

# Whitelist di ordinamento della lista 101: le colonne `ordinabile = t` del
# seed, chiavate sul `campo_sorgente` (lo manda `<ListaConfigurabile>`).
# ⭐ `valido_al` si ordina con `COALESCE(…, 'infinity')`: una riga senza fine
#    e' la piu' «lontana», non una data mancante (regola delle date di
#    validita'). Costante di MODULO, come vuole il presidio
#    `test_liste_configurabili_seed` (mockare la classe non la svuota).
COMPONENTI_SORT_COLUMNS: dict[str, str] = {
    "componente_codice": "v.componente_codice",
    "componente_descrizione": "v.componente_descrizione",
    "coeff_qta": "v.coeff_qta",
    "valido_dal": "v.valido_dal",
    "valido_al": "COALESCE(v.valido_al, 'infinity'::date)",
    # La colonna «In fattura» mostra il CODICE del modo, e si ordina su quello
    # (dal 2026-10-01 non e' piu' un booleano).
    "esposizione_in_fattura_codice": "v.esposizione_in_fattura_codice",
}
# Le date partono DESC quando nessuno chiede un verso (regola di Tid del
# 2026-09-02).
COMPONENTI_SORT_COLONNE_DATA: frozenset[str] = frozenset({"valido_dal", "valido_al"})

# I due bersagli delle note catalogo: codici di `config.tipi_entita` (FK del
# padre `catalogo.note`) e confini delle due partizioni. Li scrive il service
# alla creazione e li confronta col `target_tipo` letto, quindi stanno in UN
# posto. Fino al 2026-10-25 `ARTICOLI` / `ARTICOLI_COMPONENTI` (lotto 3 di
# brief-db-grammatica-unica-documenti).
NOTA_TARGET_ARTICOLO = "ARTICOLO"
NOTA_TARGET_COMPONENTE = "ARTICOLO_COMPONENTE"

class CatalogoBomRepository(RigheListaCompletaMixin):
    """Repository specializzato per i componenti della BoM.

    Le note di catalogo NON sono qui: dal 2026-11-11 (giro 4 di
    brief-db-revisione-catalogo) passano dal BB `PartitionedNoteRepository`
    (`apps/catalogo/db/note_repositories.py`), come quelle di vendita.
    """

    # ⭐ Le righe della distinta di un prodotto: la lettura completa
    #    (`list_righe`: il dettaglio dell'articolo, i controlli del service) e
    #    la PAGINA della lista configurabile `catalogo.articolo_componenti`
    #    (`list_righe_pagina`) sono il BB core `RigheListaCompletaMixin`
    #    (2026-10-04, regola del 2 fra domini, ok Tid): qui erano scritte a
    #    mano, gemelle di quelle delle righe di vendita. Restano qui le
    #    dichiarazioni (vista, padre, ordine, whitelist, ricerca) e il filtro
    #    proprio della lista, «in vigore al».
    # ⚠️ L'ordine della distinta quando nessuno chiede altro: la versione piu'
    #    recente in cima (e il preset della lista 101). Nessun filtro `attivo`:
    #    una riga della distinta non si disattiva, si chiude con `valido_al`.
    _righe_vista = _VISTA_COMPONENTI
    _righe_fk_documento = "prodotto_id"
    _righe_ordine_documento = "valido_dal"
    _righe_ordine_documento_desc = True
    _righe_ordinamento = COMPONENTI_SORT_COLUMNS
    _righe_ricerca = _RICERCA_COMPONENTI
    _righe_colonne_desc = COMPONENTI_SORT_COLONNE_DATA
    _righe_solo_attive = False

    # Scopo: il filtro proprio della lista 101. `valido_al` = «in vigore al»:
    #        tiene le righe che a quella data NON sono ancora chiuse — senza
    #        fine, o con la fine da quel giorno in poi — comprese quelle che
    #        iniziano dopo. `None` = tutte le versioni.
    def _righe_filtri(
        self, conditions: list[str], params: list[Any], filtri: Mapping[str, Any],
    ) -> None:
        propri = dict(filtri)
        valido_al = propri.pop("valido_al", None)
        if valido_al is not None:
            conditions.append("(v.valido_al IS NULL OR v.valido_al >= %s)")
            params.append(valido_al)
        super()._righe_filtri(conditions, params, propri)

    # Scopo: Restituisce il singolo componente BoM con ownership sul prodotto.
    def get_componente(
        self,
        articolo_id: UUID | str,
        componente_row_id: UUID | str,
    ) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT v.*
                  FROM {_VISTA_COMPONENTI} v
                 WHERE v.prodotto_id = %s
                   AND v.id = %s
                """,  # noqa: S608 — vista costante di modulo; valori come parametri
                [articolo_id, componente_row_id],
            )
            return row_to_dict(cursor)

    # Scopo: Inserisce un componente BoM sul prodotto indicato.
    # ⛔ Dal 2026-09-26 una chiave fuori `COMPONENTE_WRITE_COLUMNS` e'
    #    `RuntimeError` (BB), non piu' scartata: il 400 lo da' il service
    #    (`_extract_componente_payload`). Il padre viene dal path e si scrive
    #    PER ULTIMO, quindi VINCE: il payload non puo' spostare la riga su un
    #    altro prodotto (e il service `prodotto_id` non lo ammette).
    def create_componente(self, articolo_id: UUID | str, data: dict[str, Any]) -> UUID:
        riga = execute_dynamic_insert(
            "catalogo.articoli_componenti",
            {**data, "prodotto_id": articolo_id},
            allowed=COMPONENTE_WRITE_COLUMNS | {"prodotto_id"},
        )
        return riga["id"]

    # ⛔ Nessun UPDATE di un legame (2026-11-10): la distinta e' una storia, e
    #    la sua fine passa dal verbo (`chiudi_legame`). `update_componente` e la
    #    PATCH che lo chiamava sono ritirati.

    # Scopo: I prezzi bundle del legame che vanno oltre la fine `valido_al`, per
    #        la finestra di conferma della chiusura (BE19 di
    #        brief-db-revisione-catalogo, giro 3): listino, versione, stato,
    #        periodo, prezzo, `importo_per_kit` ed `esito` (CHIUDE, TOGLIE,
    #        BLOCCA), dal lettore del DB `vendite.fn_prezzi_legame_oltre_la_fine`.
    # ⭐ Il perimetro lo applica il lettore: un prezzo di un listino che chi
    #    chiama non vede esce con `nel_perimetro = false` e le altre colonne
    #    vuote. Si sa solo che c'e', e la chiusura lo rifiuta.
    # ⚠️ Il lettore e' di `vendite`, ma la domanda e' della distinta: sta qui,
    #    accanto al verbo che la conferma, e non in un repository dei listini.
    def prezzi_legame_oltre_la_fine(
        self, legame_id: UUID | str, valido_al: date,
    ) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM vendite.fn_prezzi_legame_oltre_la_fine(%s::uuid, %s::date)",
                [legame_id, valido_al],
            )
            return rows_to_list(cursor)

    # Scopo: Chiude il legame alla data `valido_al` insieme ai suoi prezzi
    #        bundle, col verbo del DB `catalogo.fn_chiudi_legame_distinta`.
    #        `prezzi_confermati` e' la dichiarazione della conferma (quanti
    #        prezzi l'operatore ha visto): None al primo tentativo.
    # ⛔ Il backend non giudica niente: permessi (catalogo e listini), prezzi di
    #    altre aziende, prezzi che cominciano dopo, conferma che manca o non
    #    corrisponde (`E_BOM_CHIUSURA_CON_PREZZI`, `confirm_and_retry`) e i
    #    guard della distinta parlano dal verbo, coi loro codici.
    def chiudi_legame(
        self, legame_id: UUID | str, valido_al: date, prezzi_confermati: int | None,
    ) -> dict[str, Any]:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM catalogo.fn_chiudi_legame_distinta(%s::uuid, %s::date, %s::integer)",
                [legame_id, valido_al, prezzi_confermati],
            )
            riga = row_to_dict(cursor)
        assert riga is not None
        return riga
