# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Smoke — SNAPSHOT INDIRIZZI FATTURA (accettazione §3.1 del piano BE/FE
#         satelliti) + ciclo D-Q completo: errore → correzione → rilancio →
#         ritiro segnalazioni. Percorso REALE: fixture di lotto con fatture
#         DRAFT vere, poi `run_snapshot_indirizzi_lotto_task` — lo STESSO
#         wrapper che l'handler di pipeline invoca (il task non è ancora
#         armato nei `processi`: l'armamento è del team DB, 2.3 parte 2, e la
#         sua posizione è presidiata dal pgTAP 2.4).
# Uso:    ./manage-env.sh shell < scripts/tests/smoke-fattura-indirizzi-snapshot.py
# ------------------------------------------------------------
#
# IDEMPOTENZA. Tutto in transazione con `set_rollback(True)`: lotto, fatture e
# indirizzi di prova non persistono. Rieseguibile all'infinito.
#
# Indice test (1..8):
#   1  D-Q parte «errore»: cliente SENZA indirizzo FATT -> failed_rows = n
#      fatture, log 'C' su fatture_log, stato_esecuzione ERRORE sulla ponte
#   2  il giro NON è morto: la funzione ha risposto, nessuna eccezione
#   2b guard uscita DRAFT (I.4): la fattura incompleta NON esce dalla bozza
#      nemmeno con UPDATE diretto -> E_FATTURA_NON_EMETTIBILE_INCOMPLETA
#   3  correzione + rilancio: failed_rows = 0, ogni fattura ha la riga FATT
#   4  D-Q parte «ritiro»: al successo i log 'C' del task sono disabilitati
#      e la ponte NON è più in ERRORE
#   5  shape canonico dello snapshot + origine_indirizzo_id valorizzato
#   6  tipi opzionali assenti (CON/FORNITURA/RES) -> nessun errore
#   7  idempotenza: terzo giro -> nessuna riga nuova (0 inserted), niente dup
#   8  RISTAMPA CONFORME (accesa con la Fase 2): il contesto di stampa viene
#      dagli snapshot congelati (riga FATT + emittente_snapshot) e NON cambia
#      dopo una modifica all'anagrafica
# ------------------------------------------------------------

import uuid
from decimal import Decimal

from django.db import connection, transaction

from apps.vendite.db.pipeline_repository import VenditePipelineRepository
from apps.vendite.services import _kit_meta as kit_meta  # noqa: F401 (parita' fixture)
from apps.vendite.services.fatture_righe_service import FattureRigheService
from scripts.tests._smoke_indirizzo import crea_indirizzo_libero_ruolo
from scripts.tests._smoke_contesto import apri_contesto_smoke
from scripts.tests._smoke_fatturazione import (
    costruisci_base_fatturazione,
    crea_attivita_di_commessa,
    crea_lotto_di_prova,
)

FAIL: list[str] = []


# Scopo: Registra ed emette l'esito di una singola asserzione dello smoke.
def check(label, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + label + (f" — {detail}" if detail else ""))
    if not cond:
        FAIL.append(label)



print("\n=== SMOKE snapshot indirizzi fattura (accettazione + ciclo D-Q) ===\n")

repo = VenditePipelineRepository()

with transaction.atomic():
    with connection.cursor() as cur:
        apri_contesto_smoke(cur)
        # La base della fixture si COSTRUISCE dalle radici di prova
        # (brief-be-utenti-di-sviluppo T-7b): niente attivita' esistente da
        # copiare, che su un database nuovo non c'e'.
        marker = uuid.uuid4().hex[:8]
        t = costruisci_base_fatturazione(cur, marker=marker)

        # Il soggetto_ruolo del cliente: e' su di lui che si toglie/mette FATT.
        cur.execute(
            "SELECT soggetto_ruolo_id FROM anagrafiche.billing_account WHERE id = %s",
            [t["billing_account_id"]],
        )
        sr_id = cur.fetchone()[0]
        cur.execute("SELECT id FROM config.tipi_indirizzi WHERE codice_interno='FATT'")
        tipo_fatt = cur.fetchone()[0]

        # --- lotto + 2 AF semplici (niente kit: qui contano gli indirizzi) ---
        lock_batch_id = str(uuid.uuid4())
        lotto_id = crea_lotto_di_prova(cur, t, codice=f"SMOKE-{marker}", lock_batch_id=lock_batch_id)

        for seg, qta, prezzo in [(f"SMOKE:{marker}:A1", Decimal("1"), Decimal("10.00")),
                                 (f"SMOKE:{marker}:A2", Decimal("2"), Decimal("20.00"))]:
            crea_attivita_di_commessa(
                cur, t, segment_key=seg, lock_batch_id=lock_batch_id,
                prezzo=prezzo, quantita=qta,
            )

    # Righe/fatture reali dal percorso vivo.
    FattureRigheService().generate_fatture_righe(lotto_id)

    with connection.cursor() as cur:
        cur.execute(
            "SELECT array_agg(DISTINCT fattura_id) FROM vendite.fatturazione_lotti_fatture"
            " WHERE lotto_id = %s", [lotto_id],
        )
        fattura_ids = cur.fetchone()[0] or []
        n_fatture = len(fattura_ids)
        print(f"lotto {lotto_id}: {n_fatture} fatture DRAFT\n")

        # --- FASE ERRORE: il cliente NON deve avere FATT risolvibile ----------
        # Layer RUOLO. ⚠️ Le righe FATT NON si cancellano: possono essere
        # referenziate come origine dagli snapshot congelati di ALTRI documenti
        # (`ddt_indirizzi.origine_indirizzo_id` e gemelli), e la FK farebbe
        # morire lo smoke nella fixture invece che in un'asserzione — successo
        # davvero il 2026-07-31, appena un DDT ha congelato quell'indirizzo.
        # Si ri-puntano a un tipo «di parcheggio»: ammesso al ruolo, ma fuori
        # dall'ambito FATTURA. La riga sopravvive (FK salva) e la catena non
        # trova piu' FATT. Effimero come tutto il resto: rollback finale.
        # I filtri attivo/valido_dal/valido_al DEVONO rispecchiare il guard
        # trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo per intero: una riga
        # di matrice scaduta passerebbe una selezione solo-attivo e verrebbe
        # respinta dal guard — e lo smoke morirebbe di nuovo nella fixture.
        cur.execute(
            """
            SELECT m.tipo_indirizzo_id
              FROM config.tipi_ruolo_tipi_indirizzo m
              JOIN anagrafiche.soggetti_ruoli sr ON sr.id = %s
             WHERE m.tipo_ruolo_id = sr.tipo_ruolo_id
               AND m.attivo IS TRUE
               AND (m.valido_dal IS NULL OR m.valido_dal <= CURRENT_DATE)
               AND (m.valido_al  IS NULL OR m.valido_al  >= CURRENT_DATE)
               AND m.tipo_indirizzo_id NOT IN (
                     SELECT a.tipo_indirizzo_id FROM config.tipi_indirizzi_allowed a
                      WHERE a.ambito = 'FATTURA' AND a.attivo IS TRUE)
               AND m.tipo_indirizzo_id NOT IN (
                     SELECT i.tipo_indirizzo_id FROM anagrafiche.indirizzi i
                      WHERE i.soggetto_ruolo_id = %s)
             ORDER BY m.tipo_indirizzo_id
            """, [sr_id, sr_id],
        )
        parcheggio = [r[0] for r in cur.fetchall()]
        # UN tipo di parcheggio basta per TUTTE le righe FATT: le unique di
        # anagrafiche.indirizzi sono parziali — (sr, tipo) solo con istanza
        # NULL, (sr, istanza, tipo) altrimenti — quindi la riga generica e'
        # al piu' una e le altre hanno istanze tutte diverse: ri-tipate allo
        # stesso parcheggio non collidono mai fra loro.
        if parcheggio:
            cur.execute(
                "UPDATE anagrafiche.indirizzi SET tipo_indirizzo_id = %s"
                "  WHERE soggetto_ruolo_id = %s AND tipo_indirizzo_id = %s",
                [parcheggio[0], sr_id, tipo_fatt],
            )
        else:
            # Nessun tipo libero in matrice: la DELETE e' l'ultima risorsa e
            # regge finche' la riga non e' origine di qualche snapshot.
            cur.execute(
                "DELETE FROM anagrafiche.indirizzi"
                "  WHERE soggetto_ruolo_id = %s AND tipo_indirizzo_id = %s",
                [sr_id, tipo_fatt],
            )
        # Layer SOGGETTO: anche il FATT proprio del soggetto va tolto (tabella
        # `anagrafiche.indirizzi_soggetti`, sorgente del ramo SOGGETTO della
        # vista risolta), altrimenti la catena risolve comunque — e la fase
        # errore, che e' la meta' di D-Q che conta, non si eserciterebbe mai.
        # Effimero come tutto il resto: rollback finale.
        cur.execute(
            """
            DELETE FROM anagrafiche.indirizzi_soggetti isg
             USING anagrafiche.soggetti_ruoli sr
             WHERE sr.id = %s AND isg.soggetto_id = sr.soggetto_id
               AND isg.tipo_indirizzo_id = %s
            """, [sr_id, tipo_fatt],
        )

    esito_err = repo.run_snapshot_indirizzi_lotto_task(lotto_id=lotto_id)
    check("1) cliente senza FATT -> failed_rows = n fatture",
          esito_err["failed_rows"] == n_fatture,
          f"esito={esito_err}")
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT count(DISTINCT fl.fattura_id)
              FROM vendite.fatture_log fl
             WHERE fl.fattura_id = ANY(%s) AND fl.status = 'C'
               AND fl.disabilitato IS FALSE
            """, [fattura_ids],
        )
        con_log_c = cur.fetchone()[0]
        cur.execute(
            "SELECT count(*) FROM vendite.fatturazione_lotti_fatture"
            " WHERE lotto_id = %s AND stato_esecuzione = 'ERRORE'", [lotto_id],
        )
        in_errore = cur.fetchone()[0]
    check("2) giro vivo: log 'C' per fattura + ponte in ERRORE (nessuna eccezione)",
          con_log_c == n_fatture and in_errore == n_fatture,
          f"log_C={con_log_c} ponte_errore={in_errore}")

    # 2b) Guard uscita DRAFT (I.4, brief intestazione §10.9): la fattura e'
    #     incompleta PER COSTRUZIONE proprio adesso (niente FATT, niente
    #     intestazione) — un UPDATE diretto verso EMESSA deve essere respinto
    #     con E_FATTURA_NON_EMETTIBILE_INCOMPLETA. Savepoint dedicato: il
    #     RAISE del trigger non deve avvelenare la transazione dello smoke.
    from django.db import DatabaseError
    guard_msg = ""
    try:
        with transaction.atomic():  # savepoint
            with connection.cursor() as cur:
                cur.execute(
                    """
                    UPDATE vendite.fatture
                       SET stato_doc_fiscale_id =
                           (SELECT id FROM config.stati_doc_fiscale
                             WHERE codice_interno = 'EMESSA')
                     WHERE id = %s
                    """, [fattura_ids[0]],
                )
    except DatabaseError as exc:
        guard_msg = str(exc)
    check("2b) guard uscita DRAFT: fattura incompleta respinta con il codice giusto",
          "E_FATTURA_NON_EMETTIBILE_INCOMPLETA" in guard_msg,
          f"errore={'(nessuno! il guard non e scattato)' if not guard_msg else guard_msg.splitlines()[0][:120]}")

    # --- CORREZIONE + RILANCIO -------------------------------------------
    with connection.cursor() as cur:
        id_fatt_nuovo = crea_indirizzo_libero_ruolo(
            cur, soggetto_ruolo_id=sr_id, tipo_indirizzo_id=tipo_fatt,
            testo="Via Fatturazione 1 - smoke",
        )

    esito_ok = repo.run_snapshot_indirizzi_lotto_task(lotto_id=lotto_id)
    check("3) rilancio dopo correzione: failed_rows = 0 e riga FATT per ogni fattura",
          esito_ok["failed_rows"] == 0,
          f"esito={esito_ok}")

    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT count(*) FROM vendite.fatture_indirizzi fi
              JOIN config.tipi_indirizzi ti ON ti.id = fi.tipo_indirizzo_id
             WHERE fi.fattura_id = ANY(%s) AND ti.codice_interno = 'FATT'
            """, [fattura_ids],
        )
        righe_fatt = cur.fetchone()[0]
        check("3b) una riga FATT per fattura", righe_fatt == n_fatture,
              f"righe FATT={righe_fatt} su {n_fatture}")

        # 4) D-Q ritiro: i log 'C' del task ora sono disabilitati, ponte pulita.
        cur.execute(
            """
            SELECT count(*) FROM vendite.fatture_log fl
             WHERE fl.fattura_id = ANY(%s) AND fl.status='C'
               AND fl.disabilitato IS FALSE
            """, [fattura_ids],
        )
        c_attivi = cur.fetchone()[0]
        cur.execute(
            "SELECT count(*) FROM vendite.fatturazione_lotti_fatture"
            " WHERE lotto_id = %s AND stato_esecuzione = 'ERRORE'", [lotto_id],
        )
        ancora_errore = cur.fetchone()[0]
        check("4) D-Q: al successo il task ritira le proprie segnalazioni",
              c_attivi == 0 and ancora_errore == 0,
              f"log_C_attivi={c_attivi} ponte_errore={ancora_errore}")

        # 5) shape canonico + origine agganciata.
        cur.execute(
            """
            SELECT fi.snapshot, fi.origine_indirizzo_id
              FROM vendite.fatture_indirizzi fi
              JOIN config.tipi_indirizzi ti ON ti.id = fi.tipo_indirizzo_id
             WHERE fi.fattura_id = ANY(%s) AND ti.codice_interno='FATT' LIMIT 1
            """, [fattura_ids],
        )
        srow = cur.fetchone()
    import json as _json
    snap = srow[0] if isinstance(srow[0], dict) else _json.loads(srow[0])
    canoniche = {"intestazione", "via", "cap", "citta", "prov", "stato", "display"}
    check("5) shape canonico + origine_indirizzo_id valorizzato",
          bool(snap) and set(snap.keys()) <= canoniche
          and srow[1] == id_fatt_nuovo,
          f"chiavi={sorted(snap.keys())} origine={srow[1]} attesa={id_fatt_nuovo}")

    # 6) tipi opzionali assenti -> nessun errore (failed 0 al punto 3 lo prova;
    #    qui si asserisce che non siano state inventate righe).
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT count(*) FROM vendite.fatture_indirizzi fi
              JOIN config.tipi_indirizzi ti ON ti.id = fi.tipo_indirizzo_id
             WHERE fi.fattura_id = ANY(%s) AND ti.codice_interno <> 'FATT'
            """, [fattura_ids],
        )
        righe_altri = cur.fetchone()[0]
        # Il cliente potrebbe avere RES/FORNITURA veri in anagrafica: righe > 0
        # sono legittime. L'asserzione e' sull'assenza di errori, gia' coperta
        # dal punto 3: qui si stampa il contesto.
        print(f"  INFO 6) righe di tipi opzionali scritte: {righe_altri} "
              "(0 o piu': dipende dall'anagrafica — nessun errore in entrambi i casi)")

    # 7) idempotenza: terzo giro, nessuna riga nuova.
    esito_ter = repo.run_snapshot_indirizzi_lotto_task(lotto_id=lotto_id)
    with connection.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM vendite.fatture_indirizzi WHERE fattura_id = ANY(%s)",
            [fattura_ids],
        )
        tot_righe = cur.fetchone()[0]
    check("7) idempotenza: 0 inserted al terzo giro, conteggio righe stabile",
          esito_ter["inserted_rows"] == 0 and esito_ter["failed_rows"] == 0,
          f"esito={esito_ter} righe_totali={tot_righe}")

    # 8) RISTAMPA CONFORME — l'asserzione che giustifica tutto il lavoro
    #    (accesa con la Fase 2, 2026-07-31). Il contesto di stampa legge SOLO
    #    gli snapshot congelati: si sporca l'anagrafica e si ricostruisce ->
    #    il documento NON cambia. In piu' si ancora il contesto ai valori
    #    congelati (indirizzo = display della riga FATT del satellite,
    #    denominazione emittente = emittente_snapshot), non solo a se' stesso:
    #    due letture live sarebbero uguali fra loro anche senza snapshot.
    from apps.vendite.services.fattura_document_context_builder import (
        FatturaDocumentContextBuilder,
    )
    builder = FatturaDocumentContextBuilder()
    fattura_id_1 = fattura_ids[0]
    ctx_prima = builder.build_context(fattura_id_1)
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT fi.snapshot->>'display',
                   f.emittente_snapshot->>'denominazione'
              FROM vendite.fatture f
              JOIN vendite.fatture_indirizzi fi ON fi.fattura_id = f.id
              JOIN config.tipi_indirizzi ti ON ti.id = fi.tipo_indirizzo_id
             WHERE f.id = %s AND ti.codice_interno = 'FATT'
            """, [fattura_id_1],
        )
        srow8 = cur.fetchone()
        assert srow8 is not None
        display_snap, emitt_denom_snap = srow8
        # Deriva anagrafica post-emissione: si sporca l'indirizzo di
        # correzione — la catena live ora risolverebbe un'altra via.
        cur.execute(
            "UPDATE anagrafiche.indirizzi"
            "   SET indirizzo_libero = 'VIA DERIVATA DOPO EMISSIONE 999'"
            " WHERE id = %s", [id_fatt_nuovo],
        )
    ctx_dopo = builder.build_context(fattura_id_1)
    check("8) ristampa conforme: contesto dagli snapshot, immune alla deriva anagrafica",
          display_snap is not None
          and ctx_prima["cliente"]["indirizzo"] == display_snap
          and ctx_prima["fattura"]["emittente"]["denominazione"] == emitt_denom_snap
          and ctx_dopo == ctx_prima,
          f"indirizzo={ctx_prima['cliente']['indirizzo']!r} atteso={display_snap!r} "
          f"emittente={ctx_prima['fattura']['emittente']['denominazione']!r} "
          f"identici_post_deriva={ctx_dopo == ctx_prima}")

    transaction.set_rollback(True)

print("\n=== ROLLBACK eseguito: nessun dato persistito ===")
print(f"=== ESITO: {'FALLITO — ' + ', '.join(FAIL) if FAIL else 'TUTTO VERDE'} ===\n")
