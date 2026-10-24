# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Smoke — DOCUMENTO -> COMMESSA -> FATTURA: le condizioni di pagamento del
#         documento sorgente arrivano fino al piano rate. Percorso REALE a
#         ogni passo (push `pr_run_commesse_push_one`, pull `fn_emit_*`,
#         selezione `fn_select_*`, generazione `FattureRigheService`,
#         scadenze via task repository).
# Uso:    ./manage-env.sh shell < scripts/tests/smoke-push-termine-documento-commessa.py
# ------------------------------------------------------------
#
# PERCHE' ESISTE (brief-db-termine-dal-documento-alla-commessa §7, punti 2-4).
# La fattura 2263 e' uscita col piano rate del CLIENTE invece che con quello
# dell'ORDINE, in silenzio: il BE non passava le condizioni al push e il
# livello 1 del resolver era strutturalmente irraggiungibile. Le due meta'
# del fix (colonne nel contratto di push `20260803-02` + ripuntamento del
# resolver `20260803-03` lato DB; propagazione + cache_key lato BE
# `ad1151da9`) sono state provate ciascuna nel proprio recinto. Questo smoke
# prova la CATENA INTERA dal documento al piano rate — il giro reale che la
# §9.4 della risposta DB chiede esplicitamente per chiudere i punti 2, 3, 4.
#
# COSA NON RIFA'. Non riprova cio' che i fratelli gia' presidiano:
# l'aggregazione per termine a parita' di commessa e' di
# `smoke-fattura-aggregazione-termini.py`, la meccanica del piano rate
# (quadratura, resto, basi non positive) e' di `smoke-fattura-scadenze.py`.
# Qui il termine NON viene mai scritto sulla commessa dal fixture: ce lo deve
# portare il push, o i test sono rossi.
#
# LA VIA REALE. Il fixture clona un ordine vero (testata+riga) in stato
# CONFERMATO col termine multi-rata, poi ogni passo successivo e' il codice
# di produzione: `pr_run_commesse_push_one` (handler + ponte approvazione +
# PRONTA_FATTURAZIONE), `fn_emit_attivita_fatturabili_da_commessa` (la pull
# che ristampa la sorgente a COMMESSA — la forma che ha nascosto il bug),
# `fn_select_attivita_fatturabili` con lock, `FattureRigheService`, task IVA
# e scadenze. Un fixture che scrivesse il termine sulla commessa o sulla
# testata fattura testerebbe se stesso (lezione
# `feedback_whitelist_dal_percorso_reale`).
#
# ISOLAMENTO. La competenza dei documenti clonati e' spostata ~14 mesi nel
# futuro: la selezione del lotto (gia' filtrata per BA + emittente + tipo
# doc) non puo' rastrellare attivita' vive dell'ambiente, ne' esserne
# inquinata. L'attivita' di CONTROLLO del test 4 usa la competenza del mese
# precedente per NON entrare nel lotto.
#
# IDEMPOTENZA. Tutto in `transaction.atomic()` con `set_rollback(True)`:
# ordini, commesse, attivita', lotto, fatture e rate non persistono.
# Rieseguibile all'infinito. Nessuna cancellazione preventiva: il fixture
# non riusa nulla (marker uuid per ogni giro).
#
# Indice test (0..7):
#   0  controprova binding: `fn_list_ordini_da_pushare` espone le condizioni
#      dell'ordine e `PushableRow` le PORTA (il `col_map.get` e' vivo, non
#      piu' inerte) — se e' rosso qui, il difetto e' nel contratto di push
#   1  push reale: la commessa creata porta termine E modalita' dell'ordine
#      (§7 punto 2)
#   2  due ordini stesso cliente, termini diversi -> DUE commesse distinte
#      (§7 punto 4, meta' commesse; esercita la chiave DB + cache_key)
#   3  pull: le attivita' nascono nella forma reale (sorgente COMMESSA +
#      `commessa_attivita_id`) e il resolver risolve il termine
#      dell'ORDINE dal percorso che le attraversa (livello 1 ripuntato
#      `20260803-03` + livello 2)
#   4  controllo discriminante: commessa SENZA termine -> il resolver NON
#      da' il termine dell'ordine (il valore del test 3 viene dal documento,
#      non dal default ambientale) — skip parlante se il catalogo coincide
#   5  giro fatture: DUE fatture, una per termine (§7 punto 4, meta' fatture)
#   6  la testata porta il termine del DOCUMENTO, non del cliente
#      (il caso 2263 alla rovescia) (§7 punto 3, testata)
#   7  piano rate: la fattura del termine multi-rata ha le SUE rate e la
#      somma quadra con `totale_a_pagare` (§7 punto 3, rate)
# ------------------------------------------------------------

import uuid
from datetime import timedelta
from decimal import Decimal

from django.db import connection, transaction

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.vendite.db.commesse_repository import CommesseRepository
from apps.vendite.db.pipeline_repository import VenditePipelineRepository
from apps.vendite.services.commesse_service import pr_run_commesse_push_one
from apps.vendite.services.fatture_righe_service import FattureRigheService
from scripts.tests._smoke_commessa import crea_riga_commessa
from scripts.tests._smoke_contesto import apri_contesto_smoke
from scripts.tests._smoke_fatturazione import (
    costruisci_base_fatturazione,
    crea_articolo_di_prova,
    crea_lotto_di_prova,
)

FAIL: list[str] = []
SKIP: list[str] = []


# Scopo: Registra ed emette l'esito di una singola asserzione dello smoke.
def check(label, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + label + (f" — {detail}" if detail else ""))
    if not cond:
        FAIL.append(label)


# Scopo: Segnala un caso NON esercitabile su questo ambiente, invece di
#        tacerlo e far leggere «tutto verde» a una copertura mancata.
def skip(label, motivo):
    print(f"  SKIP {label} — {motivo}")
    SKIP.append(label)


# Scopo: Un ordine in BOZZA del cliente di prova (la base `t`) con le
#        condizioni di pagamento volute. E' il punto d'ingresso della catena:
#        da qui in poi il termine viaggia SOLO per mano del codice di produzione.
#        La testata la scrive il builder del DB sul BA della base
#        (`dbops.fn_pgtap_crea_ordine`, R-3 del 2026-10-22: due ordini dello
#        STESSO cliente, che il test 2 vuole); data, termine e modalita' li
#        scrive lo smoke in bozza, come li sceglierebbe l'operatore.
#        Prima clonava «l'ultimo ordine visibile» con un INSERT, e poi lo
#        scriveva a mano (brief-be-utenti-di-sviluppo T-7b, §9.11).
# ⛔ In BOZZA, non gia' CONFERMATO: le righe si aggiungono solo finche' il
#    documento e' in bozza (`trgfn_doc_righe_lock_fuori_bozza`,
#    `E_RIGA_DOC_NON_BOZZA`). La conferma la fa `conferma_ordine`, DOPO le
#    righe — l'ordine in cui accade davvero.
def crea_ordine(cur, t, *, data_doc, termine_id, modalita_id, marker):
    cur.execute(
        "SELECT ordine_id FROM dbops.fn_pgtap_crea_ordine(%s, 'DRAFT', %s)",
        [f"smoke push termine {marker}", t["billing_account_id"]],
    )
    ordine_id = cur.fetchone()[0]
    cur.execute(
        """
        UPDATE vendite.ordini
           SET data = %s, termine_pagamento_id = %s, modalita_pagamento_id = %s
         WHERE id = %s
        """,
        [data_doc, termine_id, modalita_id, ordine_id],
    )
    return ordine_id


# Scopo: Porta a CONFERMATO l'ordine clonato, dopo le sue righe. La coppia di
#        stati la valida il DB (grafo delle transizioni), come per l'operatore.
def conferma_ordine(cur, ordine_id):
    cur.execute(
        """
        UPDATE vendite.ordini
           SET stato_doc_ordine_id = (SELECT id FROM config.stati_doc_ordini
                                       WHERE codice_interno = 'CONFERMATO')
         WHERE id = %s
        """,
        [ordine_id],
    )


# Scopo: Una riga d'ordine minimale (articolo NON composito: il fan-out BoM e'
#        presidiato altrove e qui sporcherebbe i conteggi). `quantita` la
#        deriva il trigger `trgfn_qta_from_operativa` dalla coppia operativa.
def crea_riga(cur, ordine_id, riga_tpl, *, prezzo):
    cur.execute(
        """
        INSERT INTO vendite.ordini_righe (
            ordine_id, riga_nr, articolo_id, descrizione, quantita,
            qta_operativa, uom_operativa_id,
            prezzo_unitario, sconto_percentuale, iva_id, factor_to_base, attivo
        ) VALUES (%s, 1, %s, %s, 1, 1, %s, %s, 0, %s, 1, true)
        RETURNING id
        """,
        [ordine_id, riga_tpl["articolo_id"], riga_tpl["descrizione"],
         riga_tpl["uom_id"], prezzo, riga_tpl["iva_id"]],
    )
    return cur.fetchone()[0]


# Scopo: Fatture del lotto con termine di testata, ordinate.
def fatture_del_lotto(cur, lotto_id):
    cur.execute(
        """
        SELECT f.id, f.termine_pagamento_id, f.modalita_pagamento_id,
               f.totale_a_pagare
          FROM vendite.fatturazione_lotti_fatture lf
          JOIN vendite.fatture f ON f.id = lf.fattura_id
         WHERE lf.lotto_id = %s ORDER BY f.id
        """, [lotto_id],
    )
    return cur.fetchall()


print("\n=== SMOKE termine dal DOCUMENTO alla commessa e alla fattura (§7 punti 2-4) ===\n")

repo_commesse = CommesseRepository()
repo_pipeline = VenditePipelineRepository()

with transaction.atomic():
    with connection.cursor() as cur:
        # RLS: ordini/commesse/lotti/fatture sono scoped per emittente. Senza
        # GUC operatore le SELECT tornano 0 righe e le INSERT falliscono il
        # WITH CHECK (trappola gia' pagata: un conteggio fail-closed somiglia
        # a un dato).
        apri_contesto_smoke(cur)

        # --- catalogo: il termine multi-rata (il caso ORD0004786) + un termine
        #     DIVERSO per il secondo ordine. Presi dal catalogo reale.
        cur.execute(
            "SELECT id, codice_interno, numero_rate FROM config.termini_pagamento"
            " WHERE attivo AND numero_rate > 1 ORDER BY numero_rate DESC, id LIMIT 1"
        )
        term = cur.fetchone()
        if not term:
            raise SystemExit("Nessun termine multi-rata a catalogo: giro non esercitabile.")
        term_doc, term_doc_cod, n_rate = term

        cur.execute(
            "SELECT id, codice_interno FROM config.termini_pagamento"
            " WHERE attivo AND id <> %s ORDER BY numero_rate ASC, id LIMIT 1",
            [term_doc],
        )
        alt = cur.fetchone()
        if not alt:
            raise SystemExit("Serve un secondo termine attivo distinto: catalogo troppo povero.")
        term_alt, term_alt_cod = alt

        cur.execute("SELECT id FROM config.modalita_pagamento ORDER BY id LIMIT 1")
        r = cur.fetchone()
        modalita_id = r[0] if r else None

        # Competenza ISOLATA: ~14 mesi nel futuro, meta' mese. La selezione
        # del lotto non incrocia nulla di vivo.
        data_doc = (oggi_aziendale() + timedelta(days=425)).replace(day=15)
        competenza = data_doc.replace(day=1)

        # --- la base: cliente di prova sull'emittente di prova
        #     (brief-be-utenti-di-sviluppo T-7b), al posto dell'ordine template.
        marker = uuid.uuid4().hex[:8]
        t = costruisci_base_fatturazione(cur, marker=marker, competenza_mese=competenza)
        ba_id = t["billing_account_id"]

        # L'articolo deve essere una MERCE: in un ordine (e in una bolla) vanno
        # solo articoli la cui natura di vendita ha destinazione ORDINE_VENDITA
        # (script.fn_check_articolo_riga, E_RIGA_NATURA_NON_AMMESSA). Si
        # COSTRUISCE, non composito (il fan-out BoM e' presidiato altrove).
        cur.execute(
            "SELECT nv.id FROM config.nature_vendita nv"
            " WHERE nv.attivo AND nv.destinazione_tipo = 'ORDINE_VENDITA' ORDER BY nv.id LIMIT 1"
        )
        r = cur.fetchone()
        if not r:
            raise SystemExit("Nessuna natura di vendita con destinazione ORDINE_VENDITA a catalogo.")
        art_merce, uom_merce = crea_articolo_di_prova(cur, prefisso="SMOKE-ORD", natura_vendita_id=r[0])
        cur.execute("SELECT iva_id FROM catalogo.articoli WHERE id = %s", [art_merce])
        riga_tpl = {"articolo_id": art_merce, "descrizione": f"Smoke ordine {marker}",
                    "iva_id": cur.fetchone()[0], "uom_id": uom_merce}
        ord_a = crea_ordine(cur, t, data_doc=data_doc, termine_id=term_doc,
                             modalita_id=modalita_id, marker=f"{marker}-A")
        crea_riga(cur, ord_a, riga_tpl, prezzo=Decimal("100.00"))
        conferma_ordine(cur, ord_a)
        ord_b = crea_ordine(cur, t, data_doc=data_doc, termine_id=term_alt,
                             modalita_id=modalita_id, marker=f"{marker}-B")
        crea_riga(cur, ord_b, riga_tpl, prezzo=Decimal("200.00"))
        conferma_ordine(cur, ord_b)
        # uid dei due ordini: e' con questi che si costruisce il perimetro
        # dei gruppi, cosi' la selezione prende SOLO cio' che il fixture ha
        # creato (vedi la nota sulla selezione piu' avanti).
        cur.execute(
            "SELECT id, uid::text FROM vendite.ordini WHERE id = ANY(%s)",
            [[ord_a, ord_b]],
        )
        uid_per_id = dict(cur.fetchall())
        uid_a, uid_b = uid_per_id[ord_a], uid_per_id[ord_b]

        print(f"ordini: A={ord_a} ({term_doc_cod}, {n_rate} rate) · "
              f"B={ord_b} ({term_alt_cod}) · BA {ba_id} · competenza {competenza}\n")

    # 0) BINDING. La fn espone le colonne (T.1) e il PushableRow le porta
    #    (`col_map.get`, ad1151da9): e' il punto esatto in cui il fix BE era
    #    INERTE fino al changeset di oggi.
    rows_a = repo_commesse.fetch_pushable_rows("ORDINE_VENDITA", sorgente_uid=ord_a)
    check("0) fn_list -> PushableRow porta termine e modalita' dell'ordine",
          len(rows_a) == 1
          and rows_a[0].termine_pagamento_id == term_doc
          and (modalita_id is None or rows_a[0].modalita_pagamento_id == modalita_id),
          f"righe={len(rows_a)} termine={rows_a[0].termine_pagamento_id if rows_a else None} "
          f"(atteso {term_doc} {term_doc_cod}) "
          f"modalita'={rows_a[0].modalita_pagamento_id if rows_a else None} (attesa {modalita_id})")
    print()

    # --- push REALE (handler + ponte approvazione + PRONTA_FATTURAZIONE) ----
    res_a = pr_run_commesse_push_one(sorgente_codice="ORDINE_VENDITA", sorgente_uid=ord_a)
    res_b = pr_run_commesse_push_one(sorgente_codice="ORDINE_VENDITA", sorgente_uid=ord_b)
    if len(res_a["commesse_ids"]) != 1 or len(res_b["commesse_ids"]) != 1:
        raise SystemExit(f"Push inatteso: A->{res_a['commesse_ids']} B->{res_b['commesse_ids']}")
    com_a, com_b = res_a["commesse_ids"][0], res_b["commesse_ids"][0]

    with connection.cursor() as cur:
        cur.execute(
            "SELECT id, termine_pagamento_id, modalita_pagamento_id,"
            "       emittente_soggetto_ruolo_id"
            "  FROM vendite.commesse WHERE id = ANY(%s) ORDER BY id",
            [[com_a, com_b]],
        )
        commesse = {r[0]: r for r in cur.fetchall()}

        # 1) §7 punto 2: la commessa PORTA le condizioni del documento.
        ca = commesse.get(com_a)
        check("1) la commessa del push porta termine e modalita' dell'ordine (§7.2)",
              ca is not None and ca[1] == term_doc
              and (modalita_id is None or ca[2] == modalita_id),
              f"commessa {com_a}: termine={ca[1] if ca else None} (atteso {term_doc}) "
              f"modalita'={ca[2] if ca else None} (attesa {modalita_id})")

        # 2) §7 punto 4 (meta' commesse): termini diversi -> commesse diverse.
        cb = commesse.get(com_b)
        check("2) due ordini stesso cliente, termini diversi -> DUE commesse (§7.4)",
              com_a != com_b and cb is not None and cb[1] == term_alt,
              f"A->commessa {com_a} ({term_doc_cod}) · B->commessa {com_b} "
              f"({cb[1] if cb else None}, atteso {term_alt} {term_alt_cod})")
        emittente_sr_id = ca[3] if ca else None
    print()

    # --- pull REALE: e' il passo che ristampa la sorgente a COMMESSA --------
    # ⭐ Il giro si dichiara QUI, prima del pull: dal changeSet 20260904-50 la
    #   select prende solo le righe che il PROPRIO pull ha marchiato
    #   (`a.emit_batch_id = p_lock_batch_id`), quindi il marchio e il lucchetto
    #   sono lo stesso identificativo e nascono insieme. E' la forma che ha il
    #   backend: `pipeline_step_executor` passa `context.lock_batch_id` al pull.
    lock_batch_id = str(uuid.uuid4())
    with connection.cursor() as cur:
        for cid in (com_a, com_b):
            cur.execute(
                "SELECT inserted_rows FROM"
                " vendite.fn_emit_attivita_fatturabili_da_commessa("
                "    p_commessa_id => %s, p_emit_batch_id => %s::uuid)",
                [cid, lock_batch_id],
            )
            inserted = cur.fetchone()[0]
            if inserted < 1:
                raise SystemExit(f"Pull commessa {cid}: nessuna attivita' emessa.")

        cur.execute(
            """
            SELECT a.id, s.codice_interno, a.commessa_attivita_id, a.commessa_id,
                   a.tipo_doc_fiscale_id, a.valuta_id
              FROM vendite.attivita_fatturabili a
              JOIN config.sorgenti s ON s.id = a.sorgente_tipo_id
             WHERE a.commessa_id = ANY(%s) ORDER BY a.id
            """, [[com_a, com_b]],
        )
        afs = cur.fetchall()
        af_a = next((a for a in afs if a[3] == com_a), None)
        forma_ok = bool(afs) and all(a[1] == "COMMESSA" and a[2] is not None for a in afs)

        # 3) La FORMA REALE (quella che rendeva morto il vecchio livello 1) +
        #    il resolver che ci vede attraverso (T.2). Asserzione doppia di
        #    proposito: se un domani il pull smettesse di ristampare la
        #    sorgente, questo test dira' che il contesto del giro e' cambiato.
        ris_a = ris_b = None
        if af_a is not None:
            cur.execute(
                "SELECT termine_pagamento_id FROM"
                " vendite.fn_resolve_termini_pagamento(%s)", [af_a[0]],
            )
            ris_a = cur.fetchone()[0]
        af_b = next((a for a in afs if a[3] == com_b), None)
        if af_b is not None:
            cur.execute(
                "SELECT termine_pagamento_id FROM"
                " vendite.fn_resolve_termini_pagamento(%s)", [af_b[0]],
            )
            ris_b = cur.fetchone()[0]
        check("3) forma reale (sorgente COMMESSA + commessa_attivita_id) e il"
              " resolver risolve il termine dell'ORDINE",
              forma_ok and ris_a == term_doc and ris_b == term_alt,
              f"forma={'ok' if forma_ok else 'NO'} · A->{ris_a} (atteso {term_doc}) "
              f"· B->{ris_b} (atteso {term_alt})")

        tipo_doc_id = afs[0][4] if afs else None
        valuta_id = afs[0][5] if afs else None

        # 4) CONTROLLO DISCRIMINANTE: senza il termine del documento la catena
        #    deve dare ALTRO (cliente o default D-J). Se desse comunque
        #    `term_doc`, il test 3 non proverebbe nulla. Competenza al mese
        #    PRIMA per non entrare nel lotto di sotto.
        cur.execute(
            """
            SELECT vendite.fn_get_or_create_commessa(
                p_billing_account_id => %s, p_utility_id => c.utility_id,
                p_competenza_dal => %s, p_competenza_al => %s,
                p_meta => %s::jsonb, p_force_new => true)
              FROM vendite.commesse c WHERE c.id = %s
            """,
            [ba_id, competenza - timedelta(days=1), competenza - timedelta(days=1),
             f'{{"smoke": "{marker}-ctrl"}}', com_a],
        )
        com_ctrl = cur.fetchone()[0]
        cur.execute(
            "SELECT istanza_utility_id, uom_id FROM vendite.attivita_fatturabili"
            " WHERE id = %s", [af_a[0]],
        )
        istanza_ctrl, uom_ctrl = cur.fetchone()
        giorno_ctrl = competenza - timedelta(days=1)
        ca_ctrl = crea_riga_commessa(
            cur, commessa_id=com_ctrl, segment_key=f"SMOKE:{marker}:CTRL",
            articolo_id=riga_tpl["articolo_id"], istanza_utility_id=istanza_ctrl,
            uom_id=uom_ctrl, data_attivita=giorno_ctrl,
            competenza_mese=giorno_ctrl.replace(day=1),
            competenza_dal=giorno_ctrl, competenza_al=giorno_ctrl, prezzo=10,
            tipo_doc_fiscale_id=tipo_doc_id, valuta_id=valuta_id,
        )
        cur.execute(
            """
            INSERT INTO vendite.attivita_fatturabili (
                articolo_id, istanza_utility_id, billing_account_id,
                data_attivita, quantita, uom_id, qta_operativa,
                uom_operativa_id, factor_to_base, prezzo_unitario, valuta_id,
                tipo_doc_fiscale_id, competenza_mese, competenza_dal,
                competenza_al, commessa_id, commessa_attivita_id,
                sorgente_tipo_id, sorgente_uid, lock_in_fatturazione, approvato, stato_esecuzione, prezzo_bloccato, meta
            )
            SELECT a.articolo_id, a.istanza_utility_id, a.billing_account_id,
                   %s, 1, a.uom_id, 1, a.uom_id, 1, 10, a.valuta_id,
                   a.tipo_doc_fiscale_id, %s, %s, %s, %s, %s,
                   a.sorgente_tipo_id, %s, FALSE, FALSE,
                   'PENDING', TRUE, '{}'::jsonb
              FROM vendite.attivita_fatturabili a WHERE a.id = %s
            RETURNING id
            """,
            [competenza - timedelta(days=1),
             (competenza - timedelta(days=1)).replace(day=1),
             competenza - timedelta(days=1), competenza - timedelta(days=1),
             com_ctrl, ca_ctrl, str(uuid.uuid4()), af_a[0]],
        )
        af_ctrl = cur.fetchone()[0]
        cur.execute(
            "SELECT termine_pagamento_id FROM"
            " vendite.fn_resolve_termini_pagamento(%s)", [af_ctrl],
        )
        ris_ctrl = cur.fetchone()[0]
        if ris_ctrl == term_doc:
            skip("4) controllo discriminante",
                 f"il fallback ambientale (cliente/D-J) coincide col termine "
                 f"del documento ({term_doc} {term_doc_cod}): il catalogo di "
                 "questo ambiente non permette la controprova")
        else:
            check("4) senza termine sul documento la catena da' ALTRO"
                  " (il test 3 e' discriminante)",
                  ris_ctrl != term_doc,
                  f"controllo -> {ris_ctrl} (cliente/default), documento -> {term_doc}")
    print()

    # --- lotto + selezione REALE + generazione REALE ------------------------
    with connection.cursor() as cur:
        utility_id = t["utility_id"]
        # `lock_batch_id` e' gia' quello con cui il pull ha marchiato le righe.
        # Tipo documento ed emittente vengono dalle attivita' e dalla commessa
        # del pull, non dalla base: il lotto e' il loro.
        lotto_id = crea_lotto_di_prova(
            cur, {**t, "competenza_mese": competenza, "tipo_doc_fiscale_id": tipo_doc_id,
                  "emittente_sr_id": emittente_sr_id},
            codice=f"SMOKE-TDOC-{marker}", lock_batch_id=lock_batch_id,
        )

        # Selezione REALE: stessa funzione del task `select_attivita`, con
        # lock. Il perimetro e' ristretto ai GRUPPI dei due ordini clonati.
        # ⚠️ Prima ci si affidava a «BA + competenza futura + emittente + tipo
        # doc», presumendo che bastassero a isolare il fixture: non bastano.
        # Il template e' «l'ordine piu' recente», quindi cambia insieme
        # all'ambiente, e con lui il BA di lavoro — il 2026-08-03 il perimetro
        # ha iniziato a contenere una terza attivita' e lo smoke si e' fermato
        # sul proprio guard. Filtrare per gruppo lega il fixture a cio' che ha
        # creato lui, non a cio' che gli capita intorno.
        cur.execute(
            """
            SELECT vendite.fn_select_attivita_fatturabili(
                p_competenza_mese => %s,
                p_tipo_doc_fiscale_id => %s,
                p_lock_batch_id => %s::uuid,
                p_lock => true,
                p_data_fatturazione => CURRENT_DATE,
                p_billing_account_id => %s,
                p_utility_id => %s,
                p_valuta_id => NULL,
                p_emittente_soggetto_ruolo_id => %s,
                p_limit => NULL,
                p_gruppi => %s::text[]
            )
            """,
            [competenza, tipo_doc_id, lock_batch_id, ba_id, utility_id,
             emittente_sr_id,
             [f"ORDINE_VENDITA:{uid_a}", f"ORDINE_VENDITA:{uid_b}"]],
        )
        cur.execute(
            "SELECT count(*) FROM vendite.attivita_fatturabili"
            " WHERE lock_batch_id = %s::uuid", [lock_batch_id],
        )
        n_lock = cur.fetchone()[0]
        if n_lock != 2:
            raise SystemExit(
                f"Selezione inattesa: {n_lock} attivita' lockate sul lotto "
                f"{lotto_id} (attese 2). Contesto del giro cambiato?"
            )
        print(f"lotto {lotto_id} · 2 attivita' selezionate e lockate\n")

    FattureRigheService().generate_fatture_righe(lotto_id)
    repo_pipeline.run_ricalcola_iva_lotto_task(lotto_id=lotto_id)
    esito_scad = repo_pipeline.run_genera_scadenze_lotto_task(lotto_id=lotto_id)

    with connection.cursor() as cur:
        fatture = fatture_del_lotto(cur, lotto_id)
        termini_prodotti = sorted({f[1] for f in fatture})

        # 5) §7 punto 4 (meta' fatture): due commesse, due fatture.
        check("5) il giro produce DUE fatture, una per termine (§7.4)",
              len(fatture) == 2 and termini_prodotti == sorted([term_doc, term_alt]),
              f"fatture={[f[0] for f in fatture]} termini={termini_prodotti} "
              f"attesi={sorted([term_doc, term_alt])}")

        # 6) §7 punto 3 (testata): il termine e' quello del DOCUMENTO. La 2263
        #    usci' col termine del cliente; qui deve uscire con quello
        #    dell'ordine, e la controprova del test 4 dice che non e' un caso.
        fatt_doc = next((f for f in fatture if f[1] == term_doc), None)
        check("6) la testata porta il termine del documento, non del cliente (§7.3)",
              fatt_doc is not None
              and (modalita_id is None or fatt_doc[2] == modalita_id),
              f"fattura={fatt_doc[0] if fatt_doc else None} termine={term_doc} "
              f"{term_doc_cod} modalita'={fatt_doc[2] if fatt_doc else None}")

        # 7) §7 punto 3 (rate): il piano rate e' quello del termine del
        #    documento — N rate, somma = totale_a_pagare. Il caso ORD0004786
        #    (2 rate 30/60 fine mese) e' esattamente questo.
        if fatt_doc is None:
            skip("7) piano rate", "nessuna fattura col termine del documento (vedi 5/6)")
        else:
            cur.execute(
                "SELECT numero_rata, data_scadenza, importo"
                "  FROM vendite.fatture_scadenze WHERE fattura_id = %s"
                " ORDER BY numero_rata", [fatt_doc[0]],
            )
            rate = cur.fetchall()
            somma = sum((r[2] for r in rate), Decimal("0"))
            check(f"7) piano rate del documento: {n_rate} rate e quadratura (§7.3)",
                  len(rate) == n_rate and fatt_doc[3] is not None
                  and somma == fatt_doc[3] and esito_scad["failed_rows"] == 0,
                  f"rate={[(r[0], str(r[1]), str(r[2])) for r in rate]} "
                  f"Σ={somma} totale_a_pagare={fatt_doc[3]} contatori={esito_scad}")

    transaction.set_rollback(True)

print("\n=== ROLLBACK eseguito: nessun dato persistito ===")
if SKIP:
    print(f"=== SALTATI ({len(SKIP)}): {', '.join(SKIP)} ===")
if FAIL:
    print(f"=== FALLITI ({len(FAIL)}): {', '.join(FAIL)} ===")
else:
    print("=== TUTTI I TEST OK ===")
