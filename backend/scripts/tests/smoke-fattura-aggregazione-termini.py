# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Smoke — PRESIDIO DI D-7: il termine di pagamento e' in chiave, quindi
#         cambia QUANTE fatture nascono da un lotto. Percorso REALE
#         (`FattureRigheService.generate_fatture_righe`, il task
#         `generate_fatture_righe` della pipeline).
# Uso:    ./manage-env.sh shell < scripts/tests/smoke-fattura-aggregazione-termini.py
# ------------------------------------------------------------
#
# PERCHE' ESISTE (piano BE/FE satelliti §3.3, «lo smoke piu' importante»).
# D-7 e' l'unica decisione del cantiere che cambia un NUMERO osservabile
# dall'utente: prima due attivita' dello stesso cliente finivano in una
# fattura, ora possono finire in due. Un cambio del genere non si scopre da
# un errore — si scopre da un cliente che riceve due documenti invece di uno.
# I pgTAP del DB (3b.5) presidiano i «tre specchi» della chiave a livello di
# funzione; questo smoke presidia la CONSEGUENZA sul percorso applicativo.
#
# LA VIA REALE, non una scorciatoia. Dopo D-R il termine non sta piu' sul
# documento sorgente ma sulla COMMESSA, ed entra nella sua chiave a 10
# dimensioni: due sorgenti con termini diversi aprono due commesse, e la
# catena `fn_resolve_termini_pagamento` lo raccoglie da li'. Il fixture fa
# esattamente questo — mette il termine sulla commessa — invece di scriverlo
# a mano sulla testata: cosi' esercita D-R, la catena, la chiave e il lookup
# in un colpo solo. Un fixture che avesse forzato `fatture.termine_pagamento_id`
# avrebbe testato se stesso.
#
# IDEMPOTENZA. Tutto in transazione con `set_rollback(True)`: commesse, lotto,
# attivita' e fatture non persistono. Rieseguibile all'infinito.
#
# ✅ PROVA DI MUTAZIONE (2026-08-01). Un presidio che non puo' fallire non
# presidia nulla. Rieseguito il fixture con i TRE termini uguali: nascono
# **1 fattura invece di 2** e i casi 1, 2 e 5 diventano rossi. Quindi il file
# morde dove dice di mordere, e insieme dimostra il caso «termine uguale ->
# una fattura»: tre commesse DIVERSE confluiscono in un solo documento, cioe'
# a discriminare e' il termine e non la commessa.
#
# ⚠️ COSA QUESTO SMOKE NON COPRE, e va detto invece che taciuto: il caso
# «utility diverse -> due fatture» del piano §3.3. L'utility in chiave viene
# dal BA dell'attivita', quindi servirebbero due billing account distinti —
# e allora a separare sarebbe anche il BA, non l'utility: l'asserzione non
# discriminerebbe. Quel caso e' presidiato dove puo' esserlo davvero, cioe'
# nel pgTAP `test-chiave-fattura-tre-specchi-v1` (3b.5). Qui resta il caso 6,
# che presidia la meta' applicativa del difetto: che la testata PORTI la
# propria utility invece di dedurla (D-S).
#
# Indice test (0..6):
#   0  controprova a monte: la catena risolve i due termini DISTINTI dalla
#      commessa (D-R) — se fallisce qui, il difetto e' nella catena, non
#      nell'aggregazione
#   1  termini DIVERSI -> DUE fatture (il cuore di D-7)
#   2  la separazione e' PER TERMINE, non per commessa: tre commesse, due
#      delle quali con lo STESSO termine -> UNA fattura per termine
#   3  la testata porta il termine della chiave (lookup e INSERT si specchiano)
#   4  idempotenza: riesecuzione del giro -> NESSUNA fattura in piu'
#   5  ogni attivita' e' agganciata alla fattura del proprio termine
#   6  la testata porta la propria `utility_id` (D-S: colonna, non deduzione)
# ------------------------------------------------------------

import uuid
from decimal import Decimal

from django.db import connection, transaction

from apps.vendite.services.fatture_righe_service import FattureRigheService
from scripts.tests._smoke_commessa import crea_riga_commessa
from scripts.tests._smoke_contesto import apri_contesto_smoke

# Attivita' gia' esistente usata come TEMPLATE: da lei si ereditano billing
# account, istanza utility, uom, valuta e tipo documento, cosi' il fixture
# resta coerente con la configurazione reale dell'ambiente invece di inventare
# identificativi. Stesso criterio degli altri smoke di fatturazione.
SQL_TEMPLATE = """
    SELECT a.commessa_id, a.articolo_id, a.istanza_utility_id,
           a.billing_account_id, a.uom_id, a.valuta_id, a.tipo_doc_fiscale_id,
           a.sorgente_tipo_id, a.sorgente_origine_tipo_id, a.competenza_mese,
           c.emittente_soggetto_ruolo_id, c.utility_id
      FROM vendite.attivita_fatturabili a
      JOIN vendite.commesse c ON c.id = a.commessa_id
     WHERE a.commessa_id IS NOT NULL
     ORDER BY a.id DESC
     LIMIT 1
"""

FAIL: list[str] = []


# Scopo: Registra ed emette l'esito di una singola asserzione dello smoke.
def check(label, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + label + (f" — {detail}" if detail else ""))
    if not cond:
        FAIL.append(label)


# Scopo: Crea (o riusa) una commessa che PORTA un termine di pagamento. E' il
#        punto in cui D-R entra nel fixture: `p_force_new` garantisce commesse
#        distinte anche quando il termine coincide, cosi' il test 2 puo'
#        dimostrare che a discriminare e' il termine e non la commessa.
def crea_commessa(cur, t, *, termine_id, marker):
    cur.execute(
        """
        SELECT vendite.fn_get_or_create_commessa(
            p_billing_account_id => %s, p_utility_id => %s,
            p_competenza_dal => %s, p_competenza_al => %s,
            p_meta => %s::jsonb, p_force_new => true,
            p_termine_pagamento_id => %s
        )
        """,
        [t["billing_account_id"], t["utility_id"],
         t["competenza_mese"], t["competenza_mese"],
         f'{{"smoke": "{marker}"}}', termine_id],
    )
    return cur.fetchone()[0]


# Scopo: Riga di commessa + attivita' fatturabile gia' lockata sul lotto: e'
#        lo stato in cui il task `select_attivita` le consegna al generatore.
def crea_attivita(cur, t, *, commessa_id, segment_key, lock_batch_id, prezzo):
    ca_id = crea_riga_commessa(
        cur, commessa_id=commessa_id, segment_key=segment_key,
        articolo_id=t["articolo_id"], istanza_utility_id=t["istanza_utility_id"],
        uom_id=t["uom_id"], data_attivita=t["data"],
        competenza_mese=t["competenza_mese"], competenza_dal=t["data"],
        competenza_al=t["data"], prezzo=prezzo,
        tipo_doc_fiscale_id=t["tipo_doc_fiscale_id"], valuta_id=t["valuta_id"],
    )
    cur.execute(
        """
        INSERT INTO vendite.attivita_fatturabili (
            articolo_id, istanza_utility_id, billing_account_id, data_attivita,
            quantita, uom_id, qta_operativa, uom_operativa_id, factor_to_base,
            prezzo_unitario, valuta_id, tipo_doc_fiscale_id,
            competenza_mese, competenza_dal, competenza_al,
            commessa_id, commessa_attivita_id,
            sorgente_tipo_id, sorgente_uid, sorgente_origine_tipo_id,
            lock_batch_id, lock_in_fatturazione, approvato,
            stato_esecuzione, prezzo_bloccato, meta
        ) VALUES (
            %s, %s, %s, %s, 1, %s, 1, %s, 1, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s,
            %s, TRUE, TRUE, 'PENDING', TRUE, '{}'::jsonb
        ) RETURNING id
        """,
        [t["articolo_id"], t["istanza_utility_id"], t["billing_account_id"],
         t["data"], t["uom_id"], t["uom_id"], prezzo, t["valuta_id"],
         t["tipo_doc_fiscale_id"], t["competenza_mese"], t["data"], t["data"],
         commessa_id, ca_id, t["sorgente_tipo_id"], str(uuid.uuid4()),
         t["sorgente_origine_tipo_id"], lock_batch_id],
    )
    return cur.fetchone()[0]


# Scopo: Fatture del lotto con il loro termine di testata, ordinate.
def fatture_del_lotto(cur, lotto_id):
    cur.execute(
        """
        SELECT f.id, f.termine_pagamento_id, f.utility_id
          FROM vendite.fatturazione_lotti_fatture lf
          JOIN vendite.fatture f ON f.id = lf.fattura_id
         WHERE lf.lotto_id = %s
         ORDER BY f.id
        """, [lotto_id],
    )
    return cur.fetchall()


print("\n=== SMOKE aggregazione per TERMINE di pagamento (presidio D-7) ===\n")

with transaction.atomic():
    with connection.cursor() as cur:
        # `vendite.fatturazione_lotti` e `vendite.fatture` sono RLS: senza GUC
        # le query tornano 0 righe e lo smoke mentirebbe (trappola gia' pagata:
        # un conteggio fail-closed somiglia a un dato).
        apri_contesto_smoke(cur)

        cur.execute(SQL_TEMPLATE)
        row = cur.fetchone()
        if not row:
            raise SystemExit("Nessuna attivita' fatturabile da usare come template.")
        t = {
            "commessa_id": row[0], "articolo_id": row[1], "istanza_utility_id": row[2],
            "billing_account_id": row[3], "uom_id": row[4], "valuta_id": row[5],
            "tipo_doc_fiscale_id": row[6], "sorgente_tipo_id": row[7],
            "sorgente_origine_tipo_id": row[8], "competenza_mese": row[9],
            "emittente_sr_id": row[10], "utility_id": row[11],
        }
        t["data"] = t["competenza_mese"]

        # Due termini REALI del catalogo riformato (3a.1 + 3a.3 ne hanno seminati
        # 9): la fixture che il piano §3.3-b temeva di dover creare non serve.
        cur.execute(
            "SELECT id, codice_interno FROM config.termini_pagamento"
            "  WHERE codice_interno IN ('TP_30G_1R','TP_90G_1R') ORDER BY id"
        )
        termini = cur.fetchall()
        if len(termini) != 2:
            raise SystemExit(
                "Servono due termini di catalogo distinti (TP_30G_1R, TP_90G_1R): "
                f"trovati {termini}. Catalogo non riformato?"
            )
        (term_a, cod_a), (term_b, cod_b) = termini

        marker = uuid.uuid4().hex[:8]
        lock_batch_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO vendite.fatturazione_lotti (
                codice, competenza_mese, utility_id, tipo_doc_fiscale_id,
                stato_doc_fiscale_id, emittente_soggetto_ruolo_id, tipo_lotto,
                stato_lotto, stato_operativo, lock_batch_id, meta
            )
            SELECT %s, %s, %s, %s,
                   (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno='DRAFT'),
                   %s, 'MASSIVO', 'IN_ESECUZIONE', 'APERTO', %s,
                   '{"smoke": true}'::jsonb
            RETURNING id
            """,
            [f"SMOKE-D7-{marker}", t["competenza_mese"], t["utility_id"],
             t["tipo_doc_fiscale_id"], t["emittente_sr_id"], lock_batch_id],
        )
        lotto_id = cur.fetchone()[0]

        # Tre commesse, STESSO cliente / utility / emittente:
        #   C1 termine A  ·  C2 termine B  ·  C3 termine A (commessa diversa da C1)
        # Attesa: C1 e C3 confluiscono, C2 si separa -> 2 fatture, non 3.
        c1 = crea_commessa(cur, t, termine_id=term_a, marker=f"{marker}-1")
        c2 = crea_commessa(cur, t, termine_id=term_b, marker=f"{marker}-2")
        c3 = crea_commessa(cur, t, termine_id=term_a, marker=f"{marker}-3")
        print(f"lotto {lotto_id} · commesse {c1} ({cod_a}), {c2} ({cod_b}), "
              f"{c3} ({cod_a}) · stesso BA {t['billing_account_id']}\n")

        af = {
            "A1": crea_attivita(cur, t, commessa_id=c1, lock_batch_id=lock_batch_id,
                                segment_key=f"SMOKE:{marker}:A1", prezzo=Decimal("10.00")),
            "A2": crea_attivita(cur, t, commessa_id=c2, lock_batch_id=lock_batch_id,
                                segment_key=f"SMOKE:{marker}:A2", prezzo=Decimal("20.00")),
            "A3": crea_attivita(cur, t, commessa_id=c3, lock_batch_id=lock_batch_id,
                                segment_key=f"SMOKE:{marker}:A3", prezzo=Decimal("30.00")),
        }

        # 0) Controprova a monte, ASSERITA e non solo stampata (una controprova
        #    che non puo' fallire non controprova nulla): la catena unica deve
        #    gia' vedere i due termini diversi. Se fallisce qui, il difetto e'
        #    nella catena (o nel livello commessa di 3b.1-fix) e non
        #    nell'aggregazione — e i casi sotto vanno letti in quella luce.
        cur.execute(
            "SELECT termine_pagamento_id FROM vendite.fn_resolve_termini_pagamento(%s)",
            [af["A1"]],
        )
        risolto_1 = cur.fetchone()[0]
        cur.execute(
            "SELECT termine_pagamento_id FROM vendite.fn_resolve_termini_pagamento(%s)",
            [af["A2"]],
        )
        risolto_2 = cur.fetchone()[0]
        check("0) la catena risolve i termini distinti dalla commessa (D-R)",
              risolto_1 == term_a and risolto_2 == term_b,
              f"A1 -> {risolto_1} (atteso {term_a} {cod_a}), "
              f"A2 -> {risolto_2} (atteso {term_b} {cod_b})")
        print()

    # --- percorso REALE: lo stesso servizio del task di pipeline -------------
    FattureRigheService().generate_fatture_righe(lotto_id)

    with connection.cursor() as cur:
        fatture = fatture_del_lotto(cur, lotto_id)
        termini_prodotti = sorted({f[1] for f in fatture})

        check("1) termini diversi -> DUE fatture", len(fatture) == 2,
              f"fatture={[f[0] for f in fatture]} termini={termini_prodotti} "
              f"(attese 2 su 3 commesse)")

        check("2) separazione per TERMINE, non per commessa: 3 commesse -> 2 fatture",
              len(fatture) == 2 and termini_prodotti == sorted([term_a, term_b]),
              f"termini in testata={termini_prodotti} attesi={sorted([term_a, term_b])}")

        check("3) la testata porta il termine della chiave (lookup e INSERT si specchiano)",
              all(f[1] is not None for f in fatture),
              f"termini di testata={[f[1] for f in fatture]}")

        # 5) ogni attivita' sulla fattura del proprio termine. Il legame
        #    attivita' -> fattura passa dalla RIGA (`fattura_riga_id`): non
        #    esiste una FK diretta, ed e' corretto — un'attivita' confluisce in
        #    una riga aggregata, e la fattura e' della riga.
        cur.execute(
            """
            SELECT a.id, f.termine_pagamento_id
              FROM vendite.attivita_fatturabili a
              JOIN vendite.fatture_righe r ON r.id = a.fattura_riga_id
              JOIN vendite.fatture f ON f.id = r.fattura_id
             WHERE a.id = ANY(%s) ORDER BY a.id
            """, [list(af.values())],
        )
        mappa = dict(cur.fetchall())
        atteso = {af["A1"]: term_a, af["A2"]: term_b, af["A3"]: term_a}
        check("5) ogni attivita' e' sulla fattura del proprio termine",
              mappa == atteso, f"ottenuto={mappa} atteso={atteso}")

        # 6) D-S: la testata porta la propria utility (colonna, non deduzione).
        cur.execute(
            "SELECT utility_id FROM anagrafiche.billing_account WHERE id = %s",
            [t["billing_account_id"]],
        )
        utility_ba = cur.fetchone()[0]
        check("6) la testata porta la propria utility_id (D-S)",
              all(f[2] == utility_ba for f in fatture),
              f"utility in testata={[f[2] for f in fatture]} attesa={utility_ba}")

    # 4) IDEMPOTENZA: il giro si rilancia e non nascono fatture nuove. E' la
    #    stessa proprieta' che il lookup di `fn_get_or_create_fattura_header`
    #    garantisce, vista dal percorso applicativo.
    FattureRigheService().generate_fatture_righe(lotto_id)
    with connection.cursor() as cur:
        fatture_dopo = fatture_del_lotto(cur, lotto_id)
    check("4) idempotenza: riesecuzione -> nessuna fattura in piu'",
          [f[0] for f in fatture_dopo] == [f[0] for f in fatture],
          f"prima={[f[0] for f in fatture]} dopo={[f[0] for f in fatture_dopo]}")

    transaction.set_rollback(True)

print("\n=== ROLLBACK eseguito: nessun dato persistito ===")
print(f"=== ESITO: {'FALLITO — ' + ', '.join(FAIL) if FAIL else 'TUTTO VERDE'} ===\n")
