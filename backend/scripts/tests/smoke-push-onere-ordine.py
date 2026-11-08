# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Smoke — l'ONERE come riga dell'ordine: dal documento alla commessa con la
#         sua causale, e in fondo alle righe in lettura e in stampa. Percorso
#         REALE: lister `fn_list_ordini_da_pushare`, push
#         `pr_run_commesse_push_one` (wrapper batch del DB), lettura completa
#         del repository, builder di stampa.
# Uso:    ./manage-env.sh shell < scripts/tests/smoke-push-onere-ordine.py
# ------------------------------------------------------------
#
# PERCHE' ESISTE (brief-db-addebito-trasporto-ordine §9.3, §9.8). Gli oneri
# sono righe di ordine e bolla; in commessa nascono ONERE, e la madre
# `fn_upsert_commessa_attivita` vuole ONERE <=> causale. La causale attraversa
# tre giunture, e ognuna l'ha gia' persa una volta: la whitelist
# `_PUSHABLE_SHARED_COLS` (un nome assente resta None in silenzio), l'input del
# handler e il JSON del wrapper batch (prima del 20261103-49 il DB la
# scartava). I test unitari le vedono una per una, coi mock: questo smoke le
# attraversa tutte e tre sul DB vero.
#
# IL CASO SI COSTRUISCE. L'onere e' l'articolo del seed `ONERE_TRASPORTO`
# (causale TRASPORTO, giro 2 del brief), messo come riga 1, prima della merce:
# cosi' il test 4 distingue «oneri dopo gli articoli» da «in ordine di riga».
#
# IDEMPOTENZA. Tutto in `transaction.atomic()` con `set_rollback(True)`:
# ordine, commessa e righe non persistono. Marker uuid per ogni giro.
#
# Indice test (0..5):
#   0  il lister espone la riga-onere come ONERE con la causale dell'articolo
#      e `PushableRow` la porta (la whitelist e' viva)
#   1  push reale: nessuna riga in errore (con la causale persa la madre
#      rifiuta la riga ONERE)
#   2  in commessa la riga dell'onere e' ONERE, con la causale TRASPORTO e la
#      sorgente dell'ORDINE (non sourceless: e' un onere di documento)
#   3  la merce resta NORMALE, senza causale
#   4  la lettura completa delle righe mette l'onere DOPO la merce, anche se
#      ha il numero di riga piu' basso (`sezione_documento` del DB)
#   5  la stampa della conferma d'ordine ha le righe nello stesso ordine
# ------------------------------------------------------------

import uuid
from decimal import Decimal

from django.db import connection, transaction

from apps.vendite.db.commesse_repository import CommesseRepository
from apps.vendite.db.ordini_repository import OrdiniRepository
from apps.vendite.services.commesse_service import pr_run_commesse_push_one
from apps.vendite.services.ordine_document_context_builder import OrdineDocumentContextBuilder
from scripts.tests._smoke_contesto import apri_contesto_smoke
from scripts.tests._smoke_fatturazione import (
    costruisci_base_fatturazione,
    crea_articolo_di_prova,
    data_documento_isolata,
)

FAIL: list[str] = []


# Scopo: Registra ed emette l'esito di una singola asserzione dello smoke.
def check(label, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + label + (f" — {detail}" if detail else ""))
    if not cond:
        FAIL.append(label)


# Scopo: Una riga d'ordine. `quantita` la deriva il trigger dalla coppia
#        operativa; IVA e UoM sono quelle dell'articolo.
def crea_riga(cur, ordine_id, *, riga_nr, articolo_id, descrizione, prezzo):
    cur.execute(
        """
        INSERT INTO vendite.ordini_righe (
            ordine_id, riga_nr, articolo_id, descrizione, quantita,
            qta_operativa, uom_operativa_id,
            prezzo_unitario, sconto_percentuale, iva_id, factor_to_base, attivo
        )
        SELECT %s, %s, a.id, %s, 1, 1, a.uom_id, %s, 0, a.iva_id, 1, true
          FROM catalogo.articoli a WHERE a.id = %s
        RETURNING id
        """,
        [ordine_id, riga_nr, descrizione, prezzo, articolo_id],
    )
    return cur.fetchone()[0]


print("\n=== SMOKE onere come riga dell'ordine: push con la causale, righe in fondo ===\n")

with transaction.atomic():
    with connection.cursor() as cur:
        # RLS: ordini e commesse sono scoped per emittente (senza GUC operatore
        # le SELECT tornano vuote e sembrano un dato).
        apri_contesto_smoke(cur)

        cur.execute(
            """
            SELECT a.id, a.causale_onere_id
              FROM catalogo.articoli a
              JOIN config.causali_onere c ON c.id = a.causale_onere_id
             WHERE a.codice = 'ONERE_TRASPORTO' AND c.codice_interno = 'TRASPORTO'
            """
        )
        r = cur.fetchone()
        if not r:
            raise SystemExit("Seed ONERE_TRASPORTO / causale TRASPORTO assente: giro non esercitabile.")
        art_onere, causale_trasporto = r

        cur.execute(
            "SELECT nv.id FROM config.nature_vendita nv"
            " WHERE nv.attivo AND script.fn_natura_e_merce(nv.id) ORDER BY nv.id LIMIT 1"
        )
        r = cur.fetchone()
        if not r:
            raise SystemExit("Nessuna natura di vendita di merce (script.fn_natura_e_merce) a catalogo.")

        marker = uuid.uuid4().hex[:8]
        data_doc = data_documento_isolata()
        t = costruisci_base_fatturazione(cur, marker=marker, competenza_mese=data_doc.replace(day=1))
        art_merce, _ = crea_articolo_di_prova(cur, prefisso="SMOKE-ONERE", natura_vendita_id=r[0])

        cur.execute(
            "SELECT ordine_id FROM dbops.fn_pgtap_crea_ordine(%s, 'DRAFT', %s, %s)",
            [f"smoke onere {marker}", t["billing_account_id"], data_doc],
        )
        ordine_id = cur.fetchone()[0]
        # L'onere PRIMA della merce: e' il caso che distingue la sezione
        # dall'ordine di riga (test 4 e 5).
        riga_onere = crea_riga(cur, ordine_id, riga_nr=1, articolo_id=art_onere,
                               descrizione=f"Trasporto {marker}", prezzo=Decimal("15.00"))
        riga_merce = crea_riga(cur, ordine_id, riga_nr=2, articolo_id=art_merce,
                               descrizione=f"Merce {marker}", prezzo=Decimal("100.00"))
        cur.execute(
            "SELECT dbops.fn_pgtap_porta_a_stato('vendite.ordini', %s, 'CONFERMATO')",
            [ordine_id],
        )
        cur.execute("SELECT uid::text, fatturazione_trigger FROM vendite.ordini WHERE id = %s", [ordine_id])
        ordine_uid, trigger = cur.fetchone()
        print(f"ordine {ordine_id} ({trigger}) · onere riga {riga_onere} · merce riga {riga_merce}\n")

    # 0) Il lister e la whitelist.
    rows = CommesseRepository().fetch_pushable_rows("ORDINE_VENDITA", sorgente_id=ordine_id)
    row_onere = next((x for x in rows if x.riga_sorgente_id == riga_onere), None)
    check("0) fn_list -> PushableRow: riga ONERE con la causale dell'articolo",
          row_onere is not None and row_onere.tipo_movimento == "ONERE"
          and row_onere.causale_onere_id == causale_trasporto,
          f"righe={len(rows)} onere={row_onere and (row_onere.tipo_movimento, row_onere.causale_onere_id)} "
          f"(atteso ONERE, {causale_trasporto})")

    # 1) Il push reale, dal wrapper batch del DB.
    # ⚠️ Gli errori di riga stanno nei report dei handler, non in testa al
    #    risultato: una chiave di testata che non esiste darebbe sempre «vuoto».
    res = pr_run_commesse_push_one(sorgente_codice="ORDINE_VENDITA", sorgente_id=ordine_id)
    errori = [e for h in res["handlers"] for e in h["errors"]]
    creati = sum(h["created"] for h in res["handlers"])
    check("1) push senza righe in errore: due righe create",
          not errori and creati == 2 and len(res["commesse_ids"]) == 1,
          f"errori={errori} create={creati} commesse={res['commesse_ids']}")

    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT ca.segment_key, ca.tipo_movimento, ca.causale_onere_id,
                   s.codice_interno, ca.sorgente_id, ca.sorgente_riga
              FROM vendite.commesse_attivita ca
              LEFT JOIN config.sorgenti s ON s.id = ca.sorgente_tipo_id
             WHERE ca.commessa_id = ANY(%s)
            """,
            [res.get("commesse_ids", [])],
        )
        attivita = {r[0]: r for r in cur.fetchall()}
    ca_onere = next((a for k, a in attivita.items() if k.endswith(f":R:{riga_onere}")), None)
    ca_merce = next((a for k, a in attivita.items() if k.endswith(f":R:{riga_merce}")), None)

    # 2) L'onere in commessa: ONERE, causale, sorgente del documento.
    # ⭐ Dal giro C.3 (brief-db-sorgente-documento-e-riga, BE-C.3-b) l'ordine,
    #    tipo a chiave id, sta in `sorgente_id`; e la RIGA dell'ordine in
    #    `sorgente_riga`, che il push passa da BE-C.3-a. Fino a quel giorno si
    #    leggeva l'uid dell'ordine in `sorgente_uid`.
    check("2) in commessa l'onere e' ONERE con causale TRASPORTO e la sorgente "
          "dell'ordine, fino alla sua riga",
          ca_onere is not None and ca_onere[1] == "ONERE" and ca_onere[2] == causale_trasporto
          and ca_onere[3] == "ORDINE_VENDITA" and ca_onere[4] == int(ordine_id)
          and ca_onere[5] == int(riga_onere),
          f"riga={ca_onere}")

    # 3) La merce non cambia.
    check("3) la merce resta NORMALE, senza causale",
          ca_merce is not None and ca_merce[1] == "NORMALE" and ca_merce[2] is None,
          f"riga={ca_merce}")

    # 4) La lettura completa (dialog e stampe): l'onere in fondo.
    righe = OrdiniRepository().list_righe(ordine_id)
    ordine_letto = [r["id"] for r in righe]
    check("4) lettura completa: l'onere dopo la merce, anche con riga_nr piu' basso",
          ordine_letto == [riga_merce, riga_onere]
          and [r["e_onere"] for r in righe] == [False, True],
          f"ordine={ordine_letto} e_onere={[r['e_onere'] for r in righe]}")

    # 5) La stampa legge la stessa lettura: stesso ordine, nessun riordino suo.
    ctx = OrdineDocumentContextBuilder().build_context(ordine_id)
    stampa = [r["id"] for r in ctx["righe"]]
    check("5) stampa della conferma d'ordine: stesso ordine della lettura",
          stampa == [riga_merce, riga_onere], f"ordine={stampa}")

    transaction.set_rollback(True)

print("\n=== ROLLBACK eseguito: nessun dato persistito ===")
if FAIL:
    print(f"=== FALLITI ({len(FAIL)}): {', '.join(FAIL)} ===")
else:
    print("=== TUTTI I TEST OK ===")
