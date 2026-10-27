# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Smoke — FASE 6: un lotto riportato a bozza RIPARTE DALLO STEP GIUSTO e
#         rigenera le righe. Percorso REALE (fn DB + `LottoPipelineRunner`,
#         non una simulazione della scelta step).
# Uso:    ./manage-env.sh shell < scripts/tests/smoke-ritorno-lotto-a-draft.py
# ------------------------------------------------------------
#
# PERCHE' ESISTE (brief DB→BE ritorno-lotto-a-draft §7). Il DB ha consegnato
# `fn_riporta_lotto_a_draft`; il brief avverte che **senza la meta' applicativa
# la funzione gira ma il lotto riparte dal passo sbagliato**: cade nel ramo
# «lotto esistente riuscito» e va a EMESSA, saltando la rigenerazione delle
# righe — cioe' proprio cio' per cui era stato riaperto. I test unitari del
# runner presidiano la SCELTA dello step su mock; questo presidia che la scelta
# sia giusta quando il segnale arriva dal DB vero, dopo una fn vera.
#
# ⚠️ LA COSA CHE PIU' CONTA (§7 punto 1). Il criterio non e' «la funzione ha
# risposto»: e' che dopo il rilancio le righe fattura **esistano di nuovo**.
# Un test che si fermasse ai contatori della fn direbbe verde anche nel caso
# che il brief teme, perche' la fn fa il suo mestiere comunque.
#
# IDEMPOTENZA. Tutto in `transaction.atomic()` con `set_rollback(True)`: lotto,
# fatture, righe e stato delle attivita' non persistono. Rieseguibile.
# Il fixture crea il PROPRIO lotto e non riusa nulla dell'ambiente.
#
# Indice test (0..6):
#   0  precondizione: il fixture ha prodotto un lotto EMESSA con righe fattura
#   1  la fn cancella le fatture e riporta le commesse_attivita a NON_EMESSA
#   2  il segnale `riaperto_il` e' acceso, lo stato fiscale e' tornato DRAFT
#   3  🔴 il rilancio RIFA' lo step DRAFT (non salta a EMESSA) e le righe
#      fattura tornano a esistere — §7 punto 1
#   4  dopo il rilancio il segnale e' spento (niente loop infinito, §3 pt.2)
#   5  il lotto NON risulta fra i falliti: `stato_lotto` non e' ERRORE (§7 pt.3)
#   6  controprova: senza segnale lo stesso lotto AVANZA invece di rifare
#   7  i task_run del giro precedente sono chiusi ad ANNULLATO (nessuno resta
#      COMPLETATO): e' cio' che impedisce al resolver di rispondere SKIP
#   8  il rifacimento apre task_run NUOVI con `tentativo = 2` — la storia non
#      si cancella, si accumula
# ------------------------------------------------------------

import uuid
from datetime import timedelta
from decimal import Decimal

from django.db import connection, transaction

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.vendite.db.pipeline_repository import VenditePipelineRepository
from apps.vendite.services.pipeline_step_executor import PipelineStepExecutor
from apps.vendite.services.pipeline_runner import (
    LottoPipelineParams,
    LottoPipelineRunner,
)
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


# Scopo: Righe fattura del lotto (il numero che deve tornare a esistere).
def righe_del_lotto(cur, lotto_id):
    cur.execute(
        """
        SELECT count(*)
          FROM vendite.fatturazione_lotti_fatture lf
          JOIN vendite.fatture_righe r ON r.fattura_id = lf.fattura_id
         WHERE lf.lotto_id = %s
        """, [lotto_id],
    )
    return cur.fetchone()[0]


# Scopo: Stato fiscale corrente del lotto, per codice interno.
def stato_fiscale(cur, lotto_id):
    cur.execute(
        """
        SELECT s.codice_interno FROM vendite.fatturazione_lotti l
          JOIN config.stati_doc_fiscale s ON s.id = l.stato_doc_fiscale_id
         WHERE l.id = %s
        """, [lotto_id],
    )
    r = cur.fetchone()
    return r[0] if r else None


print("\n=== SMOKE ritorno del lotto a DRAFT (Fase 6) ===\n")

repo = VenditePipelineRepository()

with transaction.atomic():
    with connection.cursor() as cur:
        # RLS: lotti, fatture e commesse sono scoped per emittente. Senza GUC
        # le letture tornano 0 righe e lo smoke mentirebbe.
        apri_contesto_smoke(cur)

        # Competenza ISOLATA nel futuro: la selezione del lotto non può
        # rastrellare attività vive dell'ambiente. La base della fixture si
        # COSTRUISCE dalle radici di prova (brief-be-utenti-di-sviluppo T-7b),
        # con la commessa su quella competenza.
        competenza = (oggi_aziendale() + timedelta(days=760)).replace(day=1)
        marker = uuid.uuid4().hex[:8]
        t = costruisci_base_fatturazione(cur, marker=marker, competenza_mese=competenza)
        commessa_id = t["commessa_id"]
        lock_batch_id = str(uuid.uuid4())

        lotto_id = crea_lotto_di_prova(cur, t, codice=f"SMOKE-F6-{marker}", lock_batch_id=lock_batch_id)

        # Riga + attivita' lockata sul lotto: lo stato in cui il task
        # `select_attivita` le consegna al generatore righe. Una riga gia'
        # APPROVATA ed EMESSA.
        # ⛔ 2026-09-04 (changeSet 20260904-50): `fn_select_attivita_fatturabili`
        #   prende SOLO le righe marchiate col proprio giro
        #   (`a.emit_batch_id = p_lock_batch_id`). Senza marchio la select
        #   torna zero, il rilancio non rigenera righe e i test 3-4-6
        #   falliscono — non e' un difetto da aggirare, e' l'effetto voluto
        #   dal cantiere «esito parziale». La fixture si marchia col PROPRIO
        #   giro, come fa il backend nel task di pull.
        ca_id, af_id = crea_attivita_di_commessa(
            cur, t, segment_key=f"SMOKE:F6:{marker}", lock_batch_id=lock_batch_id,
            prezzo=Decimal("250.00"), stato_approvazione="APPROVATA",
            stato_emissione="EMESSA", emit_batch_id=lock_batch_id,
        )
        print(f"lotto {lotto_id} · commessa {commessa_id} · attivita' {af_id}\n")

    # --- il giro che porta il lotto ad avere righe fattura -----------------
    # ⚠️ Passa dallo STEP della pipeline e non dal solo `FattureRigheService`:
    # e' l'esecuzione dello step che apre i `task_run`, e senza quelli i casi
    # 7 e 8 non avrebbero niente da osservare — il fixture verificherebbe un
    # ritorno a bozza su un lotto che non ha mai eseguito nulla, cioe' proprio
    # la condizione in cui il difetto NON si manifesta.
    PipelineStepExecutor().execute_step(
        lotto_id=lotto_id,
        stato_doc_fiscale_id=1,  # DRAFT
        tipo_lotto="MASSIVO",
        rollback=False,
        dry_run=False,
    )
    # ⛔ Lo stato del lotto non si scrive con un `UPDATE` (2026-10-27,
    #    brief-modello-documento-vendita §15.8): la porta del DB lo rifiuta. Si
    #    passa dagli stessi tre passi del runner — il verbo dello step, le
    #    fatture che lo seguono, lo stato del job giudicato dal guard.
    emessa_id = repo.get_stato_doc_fiscale_id("EMESSA")
    repo.set_lotto_job_stato(lotto_id, "IN_ESECUZIONE", "smoke: step EMESSA")
    repo.update_lotto_stato_doc(lotto_id, emessa_id)
    repo.sync_lotto_fatture_stato(lotto_id=lotto_id, stato_doc_fiscale_id=emessa_id)
    repo.set_lotto_job_stato(lotto_id, "COMPLETATO", "smoke: giro completato")
    with connection.cursor() as cur:
        righe_prima = righe_del_lotto(cur, lotto_id)
        check("0) precondizione: il lotto EMESSA ha righe fattura",
              righe_prima > 0 and stato_fiscale(cur, lotto_id) == "EMESSA",
              f"righe={righe_prima} stato={stato_fiscale(cur, lotto_id)}")

    # --- 1) la funzione DB: il ritorno a bozza ----------------------------
    esito = repo.riporta_lotto_a_draft(lotto_id)
    with connection.cursor() as cur:
        cur.execute(
            "SELECT stato_emissione FROM vendite.commesse_attivita WHERE id = %s",
            [ca_id],
        )
        stato_ca = cur.fetchone()[0]
        check("1) fn: fatture cancellate e commessa_attivita a NON_EMESSA",
              esito["deleted_fatture"] >= 1 and stato_ca == "NON_EMESSA",
              f"esito={esito} stato_commessa_attivita={stato_ca}")

        cur.execute(
            "SELECT riaperto_il IS NOT NULL FROM vendite.fatturazione_lotti"
            " WHERE id = %s", [lotto_id],
        )
        segnale_acceso = cur.fetchone()[0]
        check("2) segnale `riaperto_il` acceso e stato fiscale tornato DRAFT",
              segnale_acceso and stato_fiscale(cur, lotto_id) == "DRAFT",
              f"riaperto={segnale_acceso} stato={stato_fiscale(cur, lotto_id)}")

    # --- 7) i task_run del giro precedente devono essere ANNULLATI -------
    # ⚠️ E' il pezzo senza il quale tutto il resto e' inutile, e non si vede da
    # nessun'altra parte: se restassero COMPLETATO,
    # `fn_resolve_lotto_task_execution_mode` risponderebbe SKIP e il rilancio
    # attraverserebbe lo step SENZA eseguire un solo task — il lotto tornerebbe
    # a bozza e non ripartirebbe, in silenzio. E' successo davvero (lotto 1279,
    # 2026-08-03) ed e' costato una diagnosi lunga, perche' non produce errori:
    # produce un giro che sembra riuscito.
    # ⚠️ `attivo = false` NON sarebbe bastato: la SELECT del resolver non filtra
    # su quella colonna (rilievo del team DB). La leva e' lo STATO.
    with connection.cursor() as cur:
        cur.execute(
            "SELECT task_stato, count(*) FROM vendite.fatturazione_lotti_task_runs"
            " WHERE lotto_id = %s GROUP BY task_stato", [lotto_id],
        )
        stati = dict(cur.fetchall())
        check("7) i task_run del giro precedente sono chiusi ad ANNULLATO",
              stati.get("COMPLETATO", 0) == 0 and stati.get("ANNULLATO", 0) > 0,
              f"stati={stati} · annullati dalla fn={esito.get('annullati_task_run')}")

    # --- 3) 🔴 IL PUNTO: il rilancio rifà lo step DRAFT e rigenera --------
    # Percorso reale: lo stesso runner della pipeline, non una simulazione.
    runner = LottoPipelineRunner()
    runner.run_pipeline(LottoPipelineParams(lotto_id=lotto_id, dry_run=False))

    with connection.cursor() as cur:
        righe_dopo = righe_del_lotto(cur, lotto_id)
        stato_dopo = stato_fiscale(cur, lotto_id)
        check("3) il rilancio RIFA' lo step DRAFT e le righe tornano a esistere",
              righe_dopo > 0 and stato_dopo == "DRAFT",
              f"righe prima={righe_prima} dopo={righe_dopo} · stato={stato_dopo} "
              "(se stato=EMESSA e righe=0 e' il difetto che il brief prevedeva)")

        cur.execute(
            "SELECT riaperto_il FROM vendite.fatturazione_lotti WHERE id = %s",
            [lotto_id],
        )
        segnale_dopo = cur.fetchone()[0]
        check("4) il segnale e' stato spento (niente loop infinito)",
              segnale_dopo is None, f"riaperto_il={segnale_dopo}")

        cur.execute(
            "SELECT stato_lotto FROM vendite.fatturazione_lotti WHERE id = %s",
            [lotto_id],
        )
        stato_lotto = cur.fetchone()[0]
        check("5) il lotto riaperto NON risulta fra i falliti",
              stato_lotto != "ERRORE", f"stato_lotto={stato_lotto}")

    # --- 8) il rifacimento ha aperto task_run NUOVI, non riusato i vecchi -
    with connection.cursor() as cur:
        cur.execute(
            "SELECT count(*), min(tentativo), max(tentativo)"
            "  FROM vendite.fatturazione_lotti_task_runs"
            " WHERE lotto_id = %s AND tentativo >= 2", [lotto_id],
        )
        n_nuovi, t_min, t_max = cur.fetchone()
        check("8) il rifacimento apre task_run nuovi con tentativo = 2",
              n_nuovi > 0 and t_min == 2 and t_max == 2,
              f"task_run con tentativo>=2: {n_nuovi} (min={t_min} max={t_max})")

    # --- 6) controprova: senza segnale, lo stesso lotto AVANZA ------------
    # Se questa fosse rossa insieme a una versione rotta del test 3, vorrebbe
    # dire che il ramo non discrimina: le due vanno lette in coppia.
    runner.run_pipeline(LottoPipelineParams(lotto_id=lotto_id, dry_run=False))
    with connection.cursor() as cur:
        stato_finale = stato_fiscale(cur, lotto_id)
        check("6) controprova: senza segnale il lotto AVANZA (DRAFT -> EMESSA)",
              stato_finale == "EMESSA",
              f"stato dopo il secondo rilancio={stato_finale}")

    transaction.set_rollback(True)

print("\n=== ROLLBACK eseguito: nessun dato persistito ===")
if FAIL:
    print(f"=== FALLITI ({len(FAIL)}): {', '.join(FAIL)} ===")
else:
    print("=== TUTTI I TEST OK ===")
