# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il DDT CONSEGNATO dei test sul DATABASE PROVVISTO, in un posto solo
#        (regola del 2, ok Tid 2026-10-19): il reso nasce SOLO da una bolla
#        consegnata (`trgfn_resi_guard_ddt_consegnato`), e non c'e' un BB
#        `dbops.fn_pgtap_*` che la costruisca. La catena ordine in BOZZA ->
#        riga -> CONFERMATO -> DDT generato -> EMESSO -> SPEDITO -> CONSEGNATO
#        (la conferma e gli ultimi tre dal verbo, con `dbops.fn_pgtap_porta_a_stato`) e' la stessa di `db/pgtap/vendite/test-annulla-reso-gate-accredito-v1.sql`
#        (`agr_mk_partita`), sul mondo di `dbops.fn_pgtap_crea_mondo_cliente` +
#        `fn_pgtap_crea_articolo`. Era scritta in `test_resi_create_db`; alla
#        seconda occorrenza (`test_righe_bozza_guard`, l'etichetta del reso)
#        e' stata estratta qui.
# Note: ⚠️ Lascia le tabelle temporanee `_mondo`, `_art`, `_refs`, `_ord`,
#       `_ddt`, che il chiamante puo' rileggere: quindi UNA chiamata per
#       transazione (la seconda troverebbe `_mondo` gia' esistente). Va
#       chiamata dentro una transazione che il test ANNULLA.
# ------------------------------------------------------------
from __future__ import annotations

from typing import Any
from uuid import uuid4

# ⚠️ Padre e figlio in istruzioni SEPARATE (mai nella stessa CTE): una policy
#    che risolve il perimetro dal padre non vede le righe scritte dallo stesso
#    comando e nega fail-closed.
# ⚠️ L'ordine nasce in BOZZA, prende la riga, POI si conferma (transizione
#    DRAFT -> CONFERMATO della matrice): le righe di un ordine si scrivono solo
#    in bozza (`trgfn_doc_righe_lock_fuori_bozza`, dal `20261008-90`). Fino al
#    2026-10-09 l'ordine nasceva gia' CONFERMATO e la riga gli si aggiungeva
#    dopo — la forma che quel lock rifiuta.
_PASSI: tuple[str, ...] = (
    "CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente(%(etichetta)s)",
    "CREATE TEMP TABLE _art AS SELECT dbops.fn_pgtap_crea_articolo('RSART-' || %(sfx)s, false) AS articolo_id",
    """
    CREATE TEMP TABLE _refs AS
    SELECT (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
           (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
           (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno = 'DRAFT' AND s.attivo) AS ord_draft,
           (SELECT c.id FROM config.causali_trasporto c WHERE c.codice = 'VENDITA' ORDER BY c.id LIMIT 1) AS causale_vendita,
           (SELECT t.id FROM config.tipi_indirizzi t WHERE t.codice_interno = 'CON') AS tipo_ind_con
    """,
    """
    CREATE TEMP TABLE _ord AS
    WITH ins AS (
        INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
            valuta_id, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
        SELECT m.cliente_soggetto_ruolo_id, m.billing_account_id, r.ord_draft, r.valuta_id,
               'CONSEGNATO', m.emittente_fiscale_id, false, jsonb_build_object('test_scope', %(etichetta)s)
          FROM _mondo m, _refs r
        RETURNING id
    )
    SELECT id AS ordine_id FROM ins
    """,
    """
    INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
        qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
    SELECT o.ordine_id, 1, a.articolo_id, 'Riga reso BE', 2, 2, 10.00, r.iva_id, true, false,
           jsonb_build_object('test_scope', %(etichetta)s)
      FROM _ord o, _art a, _refs r
    """,
    # ⛔ Lo stato dell'ordine si scrive solo dal verbo (porta comune,
    #    E_DOC_STATO_SOLO_DAL_VERBO, dal 2026-10-25, brief-modello-documento-
    #    vendita §9.6 C-6): la fixture passa dal verbo e concede l'azione.
    "SELECT dbops.fn_pgtap_porta_a_stato('vendite.ordini', (SELECT ordine_id FROM _ord), 'CONFERMATO')",
    "CREATE TEMP TABLE _ddt AS SELECT vendite.fn_genera_ddt_da_ordine((SELECT ordine_id FROM _ord)) AS ddt_id",
    """
    INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
    SELECT d.ddt_id, r.tipo_ind_con, '{"display": "CON"}'::jsonb FROM _ddt d, _refs r
    ON CONFLICT DO NOTHING
    """,
    "UPDATE vendite.ddt SET causale_trasporto_id = (SELECT causale_vendita FROM _refs) WHERE id = (SELECT ddt_id FROM _ddt)",
    # ⛔ Lo stato della bolla si scrive solo dal verbo (porta comune,
    #    E_DOC_STATO_SOLO_DAL_VERBO, dal 2026-10-25): il builder passa dal verbo
    #    per la matrice, EMESSO -> SPEDITO -> CONSEGNATO, e concede all'utente
    #    del contesto l'azione del passaggio.
    "SELECT dbops.fn_pgtap_porta_a_stato('vendite.ddt', (SELECT ddt_id FROM _ddt), 'CONSEGNATO')",
)


# Scopo: costruisce il mondo e la bolla consegnata; restituisce `id`, `uid`
#        e lo stato riletto (il chiamante verifica che il caso si sia
#        formato davvero: senza, un reso sarebbe rifiutato dal guard e il test
#        proverebbe il guard).
def crea_ddt_consegnato(cur: Any, *, etichetta: str) -> dict[str, Any]:
    parametri = {"etichetta": etichetta, "sfx": uuid4().hex[:8].upper()}
    for passo in _PASSI:
        cur.execute(passo, parametri)
    cur.execute(
        "SELECT d.id, d.uid::text, s.codice_interno"
        "  FROM vendite.ddt d JOIN config.stati_doc_ddt s ON s.id = d.stato_doc_ddt_id"
        " WHERE d.id = (SELECT ddt_id FROM _ddt)"
    )
    riga = cur.fetchone()
    assert riga is not None
    return {"id": int(riga[0]), "uid": riga[1], "stato": riga[2]}
