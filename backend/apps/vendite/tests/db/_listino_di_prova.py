# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: UN LISTINO PER UN TEST SUL DB VERO, quando al test serve un listino e
#        non il listino di un cliente: `crea_listino_di_prova(cur, etichetta=…,
#        valido_dal=…, valido_al=…) -> (listino_id, tipologia_id)`, dal builder
#        `dbops.fn_pgtap_crea_listino`, su una utility che ha una tipologia di
#        listino attiva. La tipologia serve agli articoli del test
#        (`fn_pgtap_crea_articolo(p_listino_tipologia_id => …)`).
# Note: estratto il 2026-11-11 (regola del 2, ok Tid) da
#       `catalogo/.../test_chiusura_legame_prezzi_db` e
#       `vendite/.../test_listino_uom_compatibile_db`.
#       ⛔ Nessuna utility adatta = test ROSSO, non saltato: le coppie
#       utility/tipologia sono un seed di `80_data`
#       (`config/listini_tipologie_utilities.csv`), cioe' contratto. Le due
#       copie saltavano, e su un DB senza il seed sarebbero passate a vuoto.
#       ⚠️ Chi ha un CLIENTE prende la sua utility dal mondo
#       (`fn_pgtap_crea_mondo_cliente`): e' un'altra domanda, e resta li'.
#       ⭐ La scelta e' `min(id)` fra le utility adatte: deterministica, e
#       qualunque di esse va bene — il test non dipende da quale.
# ------------------------------------------------------------
from __future__ import annotations

from datetime import date


def crea_listino_di_prova(
    cur, *, etichetta: str, valido_dal: date, valido_al: date | None,
) -> tuple[int, int]:
    cur.execute(
        "SELECT min(u.id) FROM config.utilities u"
        " WHERE EXISTS (SELECT 1 FROM config.listini_tipologie_utilities ltu"
        "                WHERE ltu.utility_id = u.id AND ltu.attivo)"
    )
    utility = cur.fetchone()[0]
    if utility is None:
        raise AssertionError(
            "nessuna utility con una tipologia di listino attiva (seed config/listini_tipologie_utilities.csv)"
        )
    cur.execute(
        "SELECT listino_id, tipologia_id FROM dbops.fn_pgtap_crea_listino(%s, %s, %s, %s)",
        [utility, etichetta, valido_dal, valido_al],
    )
    listino, tipologia = cur.fetchone()
    return int(listino), int(tipologia)
