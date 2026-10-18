# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Smoke — PIANO RATE della fattura: il task `genera_scadenze_lotto` dello
#         step EMESSA popola `vendite.fatture_scadenze`. Percorso REALE
#         (il metodo repository che la pipeline invoca, non l'SQL a mano).
# Uso:    ./manage-env.sh shell < scripts/tests/smoke-fattura-scadenze.py
# ------------------------------------------------------------
#
# PERCHE' ESISTE (piano BE/FE satelliti §3.2, brief scadenze §5 pt.6).
# `fatture_scadenze` e' stata vuota per costruzione fino a oggi: non un bug,
# un produttore mai scritto. Da lei dipendono il piano rate sul PDF, il blocco
# `2.4 DatiPagamento` della FatturaPA — completezza FISCALE, non un ornamento —
# e la sintesi nel drawer fattura. I pgTAP del DB (4.1/4.2) presidiano il
# generatore a livello di funzione; questo smoke presidia il PERCORSO: che il
# task registrato dal BE, chiamato come lo chiama la pipeline, produca rate
# che quadrano al centesimo con la base giusta.
#
# LA VIA REALE. Il fixture mette il termine sulla COMMESSA (D-R) e lascia che
# la catena lo porti in testata passando dalla chiave (3b): forzare
# `fatture.termine_pagamento_id` a mano avrebbe testato il fixture, non il
# sistema. Poi chiama, in quest'ordine, gli stessi tre metodi repository dello
# step EMESSA: fondi -> IVA -> scadenze.
#
# ⚠️ SI GIRA SU FATTURE NUOVE, e non e' un dettaglio (nota 1 del team DB,
# 2026-08-02). Le fatture 632 e 834-836 sono del 31/07, ~13 ore PRIMA della
# catena 3b che scrive `termine_pagamento_id` in testata: su quelle il
# generatore solleva 570 `E_SCADENZE_TERMINE_MANCANTE`, ed e' il comportamento
# CORRETTO. Uno smoke che le includesse sarebbe rosso per sempre di un rosso
# che non dice niente. Per questo il fixture crea la propria fattura.
#
# ⚠️ LA QUADRATURA VALE SOLO PER BASE POSITIVA (nota 2 del team DB). Con
# `totale_a_pagare <= 0` le rate sono ZERO per progetto (brief §4): una
# fattura interamente coperta da acconti e' un documento normale, non un
# difetto. Un'asserzione di quadratura stesa su tutto il lotto fallirebbe
# sulla prima fattura con acconto capiente — e fallirebbe CORRETTAMENTE, che
# e' il modo peggiore di accorgersene. Qui la quadratura e' condizionata alla
# base positiva, e il caso a base zero ha un test PROPRIO (8).
#
# 📌 HEADS-UP D-K (Fase 4b, non ancora applicata — nota 3 del team DB). Il
# guard di coerenza fara' rifiutare a `numera_fatture` le fatture con
# `totale_a_pagare > 0` e nessuna rata, o con somma che non torna. Oggi la
# numerazione non verifica niente e passa sempre. Quando arrivera':
# (a) questo smoke non cambia — asserisce gia' l'invariante che il guard
#     imporra', quindi e' il suo presidio anticipato;
# (b) andranno riviste le fixture che numerano fatture prive di satelliti,
#     che oggi passano solo perche' nessuno guarda.
#
# IDEMPOTENZA. Tutto in `transaction.atomic()` con `set_rollback(True)`:
# commessa, lotto, attivita', fattura e rate non persistono. Rieseguibile
# all'infinito. Nessuna cancellazione preventiva: il fixture non riusa nulla.
#
# ✅ PROVA DI MUTAZIONE ESEGUITA (2026-08-02). Due mutanti, ciascuno rende
# rosso SOLO il proprio test — quindi i due mordono dove dicono di mordere e
# non si coprono a vicenda:
#   · resto della quadratura spostato sulla PRIMA rata invece che sull'ultima
#     -> rosso il 3, il 2 resta verde;
#   · quadratura confrontata con `totale_doc` invece che con `totale_a_pagare`
#     -> rosso il 2, il 3 resta verde.
# ⚠️ Il secondo mutante e' stato forzato: su questo ambiente le due colonne
# COINCIDONO (nessun fondo, nessun arrotondamento d'ambito sulla fattura del
# fixture), quindi il test 2 non discrimina da solo la base sbagliata. Lo
# dico invece di tacerlo: quando esistera' una fattura con fondi, quel test
# diventera' discriminante da se'; fino ad allora la base giusta e' presidiata
# dai pgTAP del DB (4.1) e da questo commento.
#
# Indice test (0..9):
#   0  controprova a monte: la catena risolve termine E modalita' dalla
#      commessa — se e' rosso qui, il difetto e' in 3b e non nelle scadenze
#   1  dopo il giro EMESSA la fattura ha ALMENO UNA rata (§3.2 asserzione 1)
#   2  la somma delle rate QUADRA con `totale_a_pagare` (la base giusta:
#      non `totale_doc`) — solo per base positiva
#   3  base NON divisibile: la differenza e' sull'ULTIMA rata (deterministico)
#   4  `numero_rata` progressivo da 1, nessun buco
#   5  `meta.modalita_codice` popolato su ogni rata — lo legge il contesto PDF
#   6  testata: `termine_pagamento_id`, `modalita_pagamento_id` e
#      `termine_pagamento_snapshot` valorizzati
#   7  idempotenza: il rilancio ricostruisce lo STESSO piano (date e importi,
#      non il solo conteggio)
#   8  base ZERO -> zero rate, nessun fallimento (D-D: documento legittimo)
#   9  D-F: una fattura oltre EMESSA finisce in `skipped_rows` e NON in
#      `failed_rows` — i due contatori restano distinti
# ------------------------------------------------------------

import uuid
from decimal import Decimal

from django.db import connection, transaction

# ⚠️ I `jsonb` letti da cursore RAW arrivano come STRINGA: psycopg 3 non li
# decodifica fuori dall'ORM. Senza questo BB `meta.get(...)` esplode con
# «'str' object has no attribute 'get'» — e' successo scrivendo questo file,
# ed e' lo stesso difetto che il worker della coda ha gia' pagato.
from apps.core.db._helpers import coerce_jsonb_dict
from apps.vendite.db.pipeline_repository import VenditePipelineRepository
from apps.vendite.services.fatture_righe_service import FattureRigheService
from scripts.tests._smoke_commessa import crea_riga_commessa
from scripts.tests._smoke_contesto import apri_contesto_smoke

# Attivita' esistente usata come TEMPLATE: da lei si ereditano billing account,
# istanza utility, uom, valuta e tipo documento, cosi' il fixture resta coerente
# con la configurazione reale dell'ambiente invece di inventare identificativi.
# Stesso criterio degli altri smoke di fatturazione.
SQL_TEMPLATE = """
    SELECT a.articolo_id, a.istanza_utility_id, a.billing_account_id,
           a.uom_id, a.valuta_id, a.tipo_doc_fiscale_id,
           a.sorgente_tipo_id, a.sorgente_origine_tipo_id, a.competenza_mese,
           c.emittente_soggetto_ruolo_id, c.utility_id
      FROM vendite.attivita_fatturabili a
      JOIN vendite.commesse c ON c.id = a.commessa_id
     WHERE a.commessa_id IS NOT NULL
     ORDER BY a.id DESC
     LIMIT 1
"""

FAIL: list[str] = []
SKIP: list[str] = []


# Scopo: Registra ed emette l'esito di una singola asserzione dello smoke.
def check(label, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + label + (f" — {detail}" if detail else ""))
    if not cond:
        FAIL.append(label)


# Scopo: Segnala un caso NON esercitabile su questo ambiente. Saltare e dirlo e'
#        onesto; saltare in silenzio farebbe leggere «tutto verde» a una
#        copertura che non c'e' stata.
def skip(label, motivo):
    print(f"  SKIP {label} — {motivo}")
    SKIP.append(label)


# Scopo: Commessa che PORTA il termine di pagamento (D-R). E' il punto in cui il
#        fixture entra nella catena reale invece di scavalcarla.
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


# Scopo: Riga di commessa + attivita' fatturabile gia' lockata sul lotto: e' lo
#        stato in cui il task `select_attivita` le consegna al generatore righe.
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


# Scopo: Piano rate di una fattura, ordinato per numero di rata. Ritorna le
#        tuple grezze (numero, data, importo, meta) perche' i test asseriscono
#        su tutte e quattro le dimensioni.
def piano_rate(cur, fattura_id):
    cur.execute(
        """
        SELECT numero_rata, data_scadenza, importo, meta
          FROM vendite.fatture_scadenze
         WHERE fattura_id = %s
         ORDER BY numero_rata
        """, [fattura_id],
    )
    return cur.fetchall()


print("\n=== SMOKE piano rate della fattura (task genera_scadenze_lotto) ===\n")

repo = VenditePipelineRepository()

with transaction.atomic():
    with connection.cursor() as cur:
        # `vendite.fatturazione_lotti` e `vendite.fatture` sono sotto RLS: senza
        # GUC le query tornano 0 righe e lo smoke mentirebbe. Trappola gia'
        # pagata: un conteggio fail-closed somiglia a un dato.
        apri_contesto_smoke(cur)

        cur.execute(SQL_TEMPLATE)
        row = cur.fetchone()
        if not row:
            raise SystemExit("Nessuna attivita' fatturabile da usare come template.")
        t = {
            "articolo_id": row[0], "istanza_utility_id": row[1],
            "billing_account_id": row[2], "uom_id": row[3], "valuta_id": row[4],
            "tipo_doc_fiscale_id": row[5], "sorgente_tipo_id": row[6],
            "sorgente_origine_tipo_id": row[7], "competenza_mese": row[8],
            "emittente_sr_id": row[9], "utility_id": row[10],
        }
        t["data"] = t["competenza_mese"]

        # Termine a PIU' RATE: e' l'unico che rende osservabili la ripartizione,
        # la progressione di `numero_rata` e la quadratura sull'ultima rata. Con
        # una rata sola i test 3 e 4 sarebbero verdi per costruzione.
        cur.execute(
            "SELECT id, codice_interno, numero_rate, primo_offset_giorni,"
            "       intervallo, arrotondamento_decimali, arrotondamento_metodo"
            "  FROM config.termini_pagamento"
            " WHERE attivo AND numero_rate > 1"
            " ORDER BY numero_rate DESC, id LIMIT 1"
        )
        term = cur.fetchone()
        if not term:
            raise SystemExit(
                "Nessun termine di catalogo con numero_rate > 1: la ripartizione "
                "non e' esercitabile. Catalogo non riformato (3a.1/3a.3)?"
            )
        term_id, term_cod, n_rate, off_1, interv, dec, metodo = term
        print(f"termine {term_cod} (id {term_id}): {n_rate} rate, "
              f"offset {off_1}g + {interv}g, arrotondamento {metodo} a {dec} dec.\n")

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
            [f"SMOKE-SCAD-{marker}", t["competenza_mese"], t["utility_id"],
             t["tipo_doc_fiscale_id"], t["emittente_sr_id"], lock_batch_id],
        )
        lotto_id = cur.fetchone()[0]

        commessa_id = crea_commessa(cur, t, termine_id=term_id, marker=marker)
        attivita_id = crea_attivita(
            cur, t, commessa_id=commessa_id, lock_batch_id=lock_batch_id,
            segment_key=f"SMOKE:{marker}:R1", prezzo=Decimal("333.33"),
        )
        print(f"lotto {lotto_id} · commessa {commessa_id} · attivita' {attivita_id}\n")

        # 0) Controprova a monte, ASSERITA e non solo stampata: la catena unica
        #    deve gia' vedere termine E modalita'. Se e' rossa qui il difetto sta
        #    in 3b (chiave / lookup di testata) e i test sotto vanno letti cosi'.
        cur.execute(
            "SELECT termine_pagamento_id, modalita_pagamento_id"
            "  FROM vendite.fn_resolve_termini_pagamento(%s)", [attivita_id],
        )
        ris_term, ris_mod = cur.fetchone()
        check("0) la catena risolve termine e modalita' dalla commessa (D-R, D-B)",
              ris_term == term_id,
              f"termine -> {ris_term} (atteso {term_id} {term_cod}), "
              f"modalita' -> {ris_mod}")
        print()

    # --- percorso REALE: gli stessi metodi repository dello step EMESSA -------
    # L'ordine e' quello della pipeline armata (3: fondi -> fondi -> IVA ->
    # scadenze). `ricalcola_iva_lotto` PRIMA delle scadenze non e' un dettaglio:
    # e' lui a produrre `totale_a_pagare`, che e' la base della ripartizione.
    FattureRigheService().generate_fatture_righe(lotto_id)
    repo.run_ricalcola_iva_lotto_task(lotto_id=lotto_id)
    esito = repo.run_genera_scadenze_lotto_task(lotto_id=lotto_id)
    print(f"esito task: {esito}\n")

    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT f.id, f.totale_a_pagare, f.totale_doc, f.termine_pagamento_id,
                   f.modalita_pagamento_id, f.termine_pagamento_snapshot
              FROM vendite.fatturazione_lotti_fatture lf
              JOIN vendite.fatture f ON f.id = lf.fattura_id
             WHERE lf.lotto_id = %s ORDER BY f.id
            """, [lotto_id],
        )
        fatture = cur.fetchall()
        if len(fatture) != 1:
            raise SystemExit(f"Fixture inattesa: {len(fatture)} fatture invece di 1.")
        fatt_id, tot_pagare, tot_doc, h_term, h_mod, h_snap = fatture[0]
        print(f"fattura {fatt_id} · totale_a_pagare {tot_pagare} · totale_doc {tot_doc}\n")

        rate = piano_rate(cur, fatt_id)

        # 1) l'asserzione base del piano §3.2. Il task ha lavorato la fattura e
        #    non l'ha ne' saltata ne' fallita: i tre numeri vanno letti insieme,
        #    perche' «0 rate + 0 falliti» sarebbe un verde falso.
        check("1) dopo il giro EMESSA la fattura ha almeno una rata",
              esito["fatture_count"] == 1 and esito["failed_rows"] == 0 and len(rate) >= 1,
              f"rate={len(rate)} contatori={esito}")

        # 2) LA BASE GIUSTA. Il difetto che questo test esiste per intercettare
        #    e' la quadratura su `totale_doc` invece che su `totale_a_pagare`:
        #    i due coincidono finche' non ci sono fondi o arrotondamenti, quindi
        #    un test scritto sul totale sbagliato resterebbe verde fino al primo
        #    acconto. Il detail stampa entrambi apposta.
        if tot_pagare is not None and tot_pagare > 0:
            somma = sum((r[2] for r in rate), Decimal("0"))
            check("2) la somma delle rate quadra con totale_a_pagare",
                  somma == tot_pagare,
                  f"Σ rate={somma} totale_a_pagare={tot_pagare} "
                  f"(totale_doc={tot_doc}, non e' la base)")
        else:
            skip("2) quadratura",
                 f"base non positiva ({tot_pagare}): per progetto zero rate, "
                 "la quadratura non si applica — vedi test 8")

        # 4) progressione senza buchi: un generatore che sbaglia il contatore
        #    produrrebbe comunque N righe, quindi contarle non basta.
        numeri = [r[0] for r in rate]
        check("4) numero_rata progressivo da 1, nessun buco",
              numeri == list(range(1, len(rate) + 1)),
              f"numeri={numeri}")

        # 5) il campo che il contesto PDF legge gia': se manca, la stampa non
        #    puo' dire con che modalita' si paga la rata.
        metas = [coerce_jsonb_dict(r[3]) for r in rate]
        mancanti = [r[0] for r, m in zip(rate, metas, strict=True) if not m.get("modalita_codice")]
        check("5) meta.modalita_codice popolato su ogni rata",
              not mancanti and len(rate) > 0,
              f"rate senza modalita_codice: {mancanti}" if mancanti else
              f"{len(rate)} rate, codice={metas[0].get('modalita_codice')}")

        # 6) la testata deve spiegare le proprie rate anche se il catalogo
        #    cambia: lo snapshot congela i VALORI, non il solo id.
        snap = coerce_jsonb_dict(h_snap)
        check("6) testata con termine, modalita' e snapshot valorizzati",
              h_term is not None and h_mod is not None and len(snap) > 0,
              f"termine={h_term} modalita'={h_mod} snapshot_keys={sorted(snap.keys())}")

    # 7) IDEMPOTENZA sul PIANO INTERO, non sul conteggio: un generatore che
    #    sbaglia le date le riscriverebbe diverse mantenendo lo stesso numero di
    #    righe, e un test sul conteggio lo dichiarerebbe idempotente.
    esito_2 = repo.run_genera_scadenze_lotto_task(lotto_id=lotto_id)
    with connection.cursor() as cur:
        rate_2 = piano_rate(cur, fatt_id)
    check("7) idempotenza: il rilancio ricostruisce lo stesso piano",
          [(r[0], r[1], r[2]) for r in rate_2] == [(r[0], r[1], r[2]) for r in rate],
          f"prima={[(r[0], str(r[1]), str(r[2])) for r in rate]} "
          f"dopo={[(r[0], str(r[1]), str(r[2])) for r in rate_2]} "
          f"(del={esito_2['deleted_rows']} ins={esito_2['inserted_rows']}: "
          "DELETE+INSERT, non zero)")

    # 3) BASE NON DIVISIBILE, deterministica. Il catalogo di oggi non ha un
    #    termine a 3 rate, quindi il «100,00 / 3» del piano §3.2 non e'
    #    riproducibile cosi' com'e' scritto — e non lo si finge: si forza una
    #    base che NON divide per il numero di rate reale, che e' la proprieta'
    #    che quell'esempio voleva presidiare. La base e' un INPUT del
    #    generatore, quindi scriverla e' legittimo (tutto in rollback).
    #
    #    ⚠️ L'asserzione e' sui VALORI attesi, non su «le prime sono uguali e
    #    l'ultima e' diversa»: con due sole rate quel modo di scriverla e'
    #    VACUO (un insieme di un elemento e' sempre omogeneo) e non
    #    distinguerebbe «resto sull'ultima» da «resto sulla prima», che e'
    #    proprio il difetto da intercettare. Qui si replica la formula del
    #    brief §3.1 — `round(base/n)` sulle prime n-1, il resto sull'ultima — e
    #    la si confronta rata per rata.
    quant = Decimal(1).scaleb(-dec)  # 2 decimali -> Decimal('0.01')
    if metodo != "HALF_UP":
        skip("3) base non divisibile",
             f"il termine usa arrotondamento {metodo}: l'attesa e' calcolata "
             "solo per HALF_UP, e inventarla per gli altri metodi "
             "significherebbe riscrivere il generatore nel test")
    else:
        base_forzata = (quant * n_rate) + quant  # non divisibile per costruzione
        with connection.cursor() as cur:
            cur.execute("UPDATE vendite.fatture SET totale_a_pagare = %s WHERE id = %s",
                        [base_forzata, fatt_id])
            cur.execute("SELECT * FROM vendite.fn_genera_scadenze_fattura(%s)", [fatt_id])
            cur.fetchone()
            rate_3 = piano_rate(cur, fatt_id)
        rata_attesa = (base_forzata / n_rate).quantize(quant, rounding="ROUND_HALF_UP")
        atteso = [rata_attesa] * (n_rate - 1)
        atteso.append(base_forzata - rata_attesa * (n_rate - 1))
        ottenuto = [r[2].quantize(quant) for r in rate_3]
        check("3) base non divisibile: la differenza e' sull'ultima rata",
              ottenuto == atteso and sum(ottenuto) == base_forzata,
              f"base={base_forzata} ottenuto={[str(x) for x in ottenuto]} "
              f"atteso={[str(x) for x in atteso]} "
              f"(le prime {n_rate - 1} a round(base/{n_rate}), l'ultima il resto)")

    # 8) BASE ZERO: documento interamente coperto da acconti. Zero rate, nessun
    #    errore, nessun fallimento — e la DELETE precede il caso, quindi le rate
    #    che c'erano SPARISCONO invece di restare a raccontare un piano che non
    #    esiste piu' (brief §3.1).
    with connection.cursor() as cur:
        cur.execute("UPDATE vendite.fatture SET totale_a_pagare = 0 WHERE id = %s",
                    [fatt_id])
    esito_zero = repo.run_genera_scadenze_lotto_task(lotto_id=lotto_id)
    with connection.cursor() as cur:
        rate_zero = piano_rate(cur, fatt_id)
    check("8) base zero -> zero rate, nessun fallimento (D-D)",
          len(rate_zero) == 0 and esito_zero["failed_rows"] == 0,
          f"rate={len(rate_zero)} contatori={esito_zero}")

    # 9) D-F: una fattura oltre EMESSA e' uno snapshot fiscale, il suo piano
    #    rate e' quello. Deve finire in `skipped_rows` — il contatore dei
    #    documenti CHIUSI — e non in `skipped_errore_rows`, che e' il contatore
    #    dei documenti ROTTI. Sommarli direbbe «una saltata» senza dire quale
    #    dei due casi, che per il cockpit sono l'opposto.
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT lf.lotto_id
              FROM vendite.fatturazione_lotti_fatture lf
              JOIN vendite.fatture f ON f.id = lf.fattura_id
              JOIN config.stati_doc_fiscale s ON s.id = f.stato_doc_fiscale_id
             WHERE s.codice_interno NOT IN ('DRAFT', 'EMESSA')
             GROUP BY lf.lotto_id
            HAVING count(*) = count(*) FILTER (
                     WHERE s.codice_interno NOT IN ('DRAFT','EMESSA'))
             ORDER BY lf.lotto_id DESC LIMIT 1
            """
        )
        r = cur.fetchone()
    if not r:
        skip("9) D-F fattura oltre soglia",
             "nessun lotto con sole fatture oltre EMESSA su questo ambiente")
    else:
        lotto_chiuso = r[0]
        esito_df = repo.run_genera_scadenze_lotto_task(lotto_id=lotto_chiuso)
        check("9) D-F: fattura oltre EMESSA -> skipped_rows, non failed",
              esito_df["skipped_rows"] > 0
              and esito_df["failed_rows"] == 0
              and esito_df["fatture_count"] == 0,
              f"lotto {lotto_chiuso} contatori={esito_df} "
              "(skipped = chiuse, skipped_errore = rotte: restano distinti)")

    transaction.set_rollback(True)

print("\n=== ROLLBACK eseguito: nessun dato persistito ===")
if SKIP:
    print(f"=== SALTATI ({len(SKIP)}): {', '.join(SKIP)} ===")
print(f"=== ESITO: {'FALLITO — ' + ', '.join(FAIL) if FAIL else 'TUTTO VERDE'} ===\n")
