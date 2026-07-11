# Piano — Allineamento stato fattura allo stato dello step (pipeline lotti)

> **Tipo**: piano operativo unico (BE + DB). La parte **BE** va passata al team backend;
> la parte **DB** si esegue su `dev/db-tid`.
>
> **Data**: 2026-06-19 (agg. 2026-06-20) · **Stato**: 🟢 **DB IMPLEMENTATO E APPLICATO**
> (DB-1/DB-2/DB-3 su `dev/db-tid`) · 🟢 **BE IMPLEMENTATO E COMMITTATO** (`8824cafc7` su
> `dev/backend-tid`) · ✅ **SMOKE E2E VERDE DAL VIVO** (2026-06-20): lotto 117 MASSIVO
> `DEFINITIVA/CHIUSO`, fattura 210 `DEFINITIVA` numerata 1/2026/R2 — catena per-step
> `1→2→8` completata end-to-end. Dettaglio esecuzione DB in §4.1, BE in §3.1.

---

## 1. Problema (sintesi)

Nel batch fatturazione MASSIVO lo step **DEFINITIVA fallisce**:

```
E_LOTTO_PARAMETRO_NON_COERENTE — transizione 1→8 (fattura) non ammessa
(trgfn_fatture_guard_stato, da fn_sync_lotto_fatture_stato)
```

Causa: lo **stato documentale della fattura** (`stato_doc_fiscale_id`) **non segue** quello
dello step. La fattura nasce DRAFT(1), lo step EMESSA(2) calcola l'IVA ma **non porta la
fattura a EMESSA**, e lo step DEFINITIVA(8) tenta `1→8` — salto vietato dalla matrice
(per la fattura esiste solo `1→2→8`).

### Evidenza (codice vivo)

- Le transizioni **fattura** ammesse (`config.stati_doc_fiscale_transizioni`, `solo_fattura`):
  `1→2`, `2→8`, `2→3`, `8→3`, `3→6`. **Non esiste `1→8`** (giusto: non si numera fiscalmente
  ciò di cui non si è certificata l'IVA).
- Il sync fattura↔step è **cablato in un solo task**: [`pipeline_step_executor.py:481`](../../../../backend/apps/vendite/services/pipeline_step_executor.py#L481)
  (`_handle_numera_fatture_task`) chiama `sync_lotto_fatture_stato(lotto, stato_doc_fiscale_id=8)`.
  Gli handler dello step EMESSA (`genera_fondi`, `applica_fondi`, `ricalcola_iva`) **non**
  sincronizzano la fattura.
- Il **lotto**, invece, avanza già per step in modo generico:
  [`pipeline_runner.py:208`](../../../../backend/apps/vendite/services/pipeline_runner.py#L208)
  `update_lotto_stato_doc(lotto, step.stato_doc_fiscale_id)`. È solo l'allineamento delle
  **fatture** a non essere generico.
- `fn_numera_fattura_opz_emessa` "emette" con `COALESCE(stato, EMESSA)`: no-op perché la
  fattura è già DRAFT(1), non NULL.

**Diagnosi**: asimmetria di orchestrazione, non un buco di modello. La matrice e
`fn_sync_lotto_fatture_stato` sono corrette; manca l'**applicazione uniforme per step**.

---

## 2. Principio della fix (parametrico)

Ogni riga `fatturazione_pipeline` dichiara già il suo `stato_doc_fiscale_id` (1,2,8,3). La
fix sfrutta quel parametro: **a ogni avanzamento di step, allineare lotto E fatture allo
`stato_doc_fiscale_id` di quello step** — un solo punto generico, nessuna logica per-step.

Risultato:
- **MASSIVO**: fattura `1→2→8→3` automatico (IVA congelata in 2 prima della numerazione in 8).
- **GIORNALIERO**: idem. Le righe pipeline GIORNALIERO **esistono già** (DRAFT id 8, **EMESSA
  id 2 con `processi=[]`**, DEFINITIVA id 6, INVIATA id 7): con la fix la fattura passa per
  EMESSA(2) anche se lo step non ha task. **Zero nuove righe di seed.**
- Matrice e guard **invariati**: il guard ora protegge correttamente (niente più salti).

---

## 3. Parte BE — da passare al team backend

> Obiettivo: spostare il sync fattura da "dentro il task numera" a **finalizzazione
> generica di step**, guidata da `step.stato_doc_fiscale_id`.

### 3.1 Stato esecuzione BE (2026-06-20)

| Item | Stato | Note |
| --- | --- | --- |
| **B1** sync fattura per-step nel runner | ✅ committato | `pipeline_runner.py::_execute_pipeline_step`: `sync_lotto_fatture_stato(stato=step.stato_doc_fiscale_id)` dopo `execute_step`, sotto guard `if not dry_run`. |
| **B2** rimosso sync dal task numera | ✅ committato | `_handle_numera_fatture_task` resta **solo numerazione** (`fn_numera_fattura_opz_emessa`). Sync accentrato → niente duplicazione. |
| **B3** rollback / dry-run | ✅ by-design | dry-run sotto guard; il rollback **non** passa da `_execute_pipeline_step` (path separato `execute_step(rollback=True)`) → il sync non scatta mai in rollback, nessun codice extra. |
| **B4** test BE | ✅ committato | +2 test runner (sync su forward; nessun sync in dry-run); executor asserisce `sync_lotto_fatture_stato.assert_not_called()`. **957 test vendite+core verdi**. |

> Commit BE: **`8824cafc7`** su `dev/backend-tid` (insieme alla discovery lane a 4 assi e ai
> fix uuid/grant del workstream batch). Doc orchestrazione aggiornata in
> `work-done/fatturazione-attivita-progetto.md` (sez. *"Allineamento stato fattura ↔
> stato step"*).
>
> ⚠️ **Osservazione su DB-2 (reset EMESSA→DRAFT) — da chiarire col team DB.** La fn viva
> `fn_reset_lotto_draft` ora accetta fatture **DRAFT/EMESSA** (✅), ma **mantiene il guard
> "il lotto deve essere DRAFT"** (`stato_doc_fiscale_id IS DISTINCT FROM v_draft_id` →
> errore). Con la fix per-step **lotto e fattura avanzano insieme**: dopo lo step EMESSA il
> **lotto** è a `2` (EMESSA), quindi `fn_reset_lotto_draft` lo **rifiuterebbe sul guard
> lotto** prima ancora di arrivare al controllo fattura. Lo stato "lotto DRAFT + fatture
> EMESSA" **non si produce** nel MASSIVO per-step. → Perché il reset sia davvero usabile
> dopo EMESSA, il **guard del lotto** va rilassato a pre-fiscale (DRAFT *o* EMESSA),
> simmetrico a quello fattura appena introdotto. Altrimenti il reset post-EMESSA resta
> inarrivabile e la relax fattura di DB-2 non è esercitabile dal flusso reale (solo da test
> con stato fabbricato). Vedi §4.5.

### B1 — Sync fattura generico per step (core)
In [`pipeline_runner.py::_execute_pipeline_step`](../../../../backend/apps/vendite/services/pipeline_runner.py#L193):
dopo che `self.step_executor.execute_step(...)` (riga ~223) completa con successo (forward,
**non** dry-run, **non** rollback), chiamare il sync delle fatture allo stato dello step:
```
self.repository.sync_lotto_fatture_stato(lotto_id, stato_doc_fiscale_id=step.stato_doc_fiscale_id)
```
- **Dopo** i task dello step (non prima): la fattura diventa EMESSA *dopo* il ricalcolo IVA
  (semantica "EMESSA = IVA certificata").
- Il lotto continua ad avanzare come ora (riga 208); ora le fatture lo seguono **sempre**.

### B2 — Rimuovere il sync dal task numera
In [`_handle_numera_fatture_task`](../../../../backend/apps/vendite/services/pipeline_step_executor.py#L460):
togliere la chiamata `sync_lotto_fatture_stato` (righe 481-484). Il task resta **solo**
numerazione (`numera_fattura_opz_emessa` per fattura). Il sync a 8 lo fa ora la
finalizzazione di step (B1).

### B3 — Rollback / dry-run
- La finalizzazione B1 **non** deve scattare sugli step di **rollback** (`reset_lotto_draft`):
  in rollback lo stato target è quello dello step a cui si **torna** (vedi DB-2).
- In **dry-run** nessun sync (coerente con il resto dell'executor).

### B4 — Test BE
- Aggiornare/aggiungere test executor+runner: dopo lo step EMESSA la fattura è a 2; dopo
  DEFINITIVA è a 8; numera non chiama più il sync.
- Verificare il caso `reset_lotto_draft` (vedi DB-2) post-fix.

---

## 4. Parte DB — da eseguire qui (`dev/db-tid`)

### 4.1 Stato esecuzione DB (2026-06-20)

| Item | Stato | Artefatto |
| --- | --- | --- |
| **DB-1** matrice unificata `1→2→8` | ✅ applicato | `80_data/sql/config/stati_doc_fiscale_transizioni.csv` (runOnChange) |
| **DB-2** reset accetta EMESSA | ✅ applicato | `20_code/vendite/20260619-16-update-fn-reset-lotto-draft-accetta-emessa-mctit.yaml` |
| **DB-3** doc invariante | ✅ fatto | `docs/it/guide/fatturazione.md` (sez. "Stato documentale della fattura") |
| **pgTAP DB-1** (giornaliero) | ✅ verde 3/3 | `db/pgtap/vendite/test-stati-doc-transizioni-giornaliero.sql` |
| **pgTAP DB-2** (reset EMESSA) | ⏳ rimandato | il test reset esistente è bit-rotted (vedi §4.5); verifica DB-2 via test BE |

> Dettaglio matrice applicata (DB-1): `1→2` (id 1) e `2→8` (id 3) rese **universali**
> (`meta={}`), `1→8` GIORNALIERO (id 4) **deprecata** (`ammesso=f`), `2→1` (id 2) resta
> MASSIVO. Scoperto in apply: `uq_stati_doc_fiscale_transizioni` **non** include `meta`, quindi
> una sola riga per transizione → si rilassa il tag, non si duplica (vedi DB-1).

### DB-1 — Unificare il lotto GIORNALIERO a `1→2→8` (decisione A) — *seed matrice*

**Verificato**: il guard del lotto (`trgfn_fatturazione_lotti_guard_stato`) **filtra per
`tipo_lotto`** (`meta->>'tipo_lotto'`). In matrice il lotto giornaliero ha **solo** `1→8`
(id 4, GIORNALIERO); `1→2` e `2→8` sono taggate **MASSIVO**. Quindi oggi il lotto giornaliero
**non può** fare `1→2` → lo step pipeline EMESSA(2) giornaliero (id 2, `processi=[]`) verrebbe
rifiutato dal guard. Lotto e fattura per il giornaliero **divergono** (lotto `1→8`, fattura
deve `1→2→8`).

**Decisione A (unificare)**: portare anche il **lotto** giornaliero a `1→2→8`, così le due
macchine coincidono e la fix per-step copre entrambe le tipologie.

> ⚠️ **Vincolo scoperto in apply**: `uq_stati_doc_fiscale_transizioni` è su
> `(stato_from_id, stato_to_id, solo_lotto, solo_fattura)` — **NON include `meta`**. Quindi
> **non** si possono avere due righe `1→2` (una MASSIVO, una GIORNALIERO): esiste una sola
> riga per transizione. Il guard usa `meta.tipo_lotto` come **filtro** (NULL/`{}` = vale per
> tutti). → La fix è **rendere universali** le transizioni condivise, non duplicarle.

- **Rendere universali** (`meta = {}`) le righe lotto **`1→2` (id 1)** e **`2→8` (id 3)**:
  erano taggate `MASSIVO`, ora valgono per ogni `tipo_lotto` → le usa anche il GIORNALIERO.
- **Deprecare** la riga **`(1→8, GIORNALIERO)`** (id 4): `ammesso = f` (no delete: la matrice
  conserva la storia, il guard non l'ammette più).
- `2→1` (id 2) resta **MASSIVO** (solo il massivo ha rollback/reset).
- Lo step EMESSA(2) giornaliero resta a `processi=[]` (l'IVA giornaliera è già calcolata alla
  nascita del documento): serve solo ad avanzare lo stato.
- **Meccanismo**: il loader `20260210-01` è `loadUpdateData` **`runOnChange: true`** keyed su
  `id` → si **edita il CSV** `80_data/sql/config/stati_doc_fiscale_transizioni.csv` (upsert al
  prossimo migrate). Niente changeset nuovo.

### DB-2 — Reset: cancellare anche le fatture in EMESSA (pre-fiscali) — *DECISA*

**Verificato**: `fn_reset_lotto_draft` **cancella** le fatture (`fn_cleanup_fatture_by_ids`),
ma ha una safety guard che le **pretende a DRAFT** (`v_bad_fatture > 0 → errore`). Dopo la fix
le fatture saranno a EMESSA(2) → la guard le rifiuterebbe.

**Decisione (presa)**: **rilassare la guard** di `fn_reset_lotto_draft` ad accettare le fatture
**pre-fiscali (DRAFT *o* EMESSA)** e cancellarle; **rifiutare** le fiscali (DEFINITIVA in poi,
numerate). Coerente con la regola già definita "rollback solo pre-fiscale" (il rollback è
configurato solo sullo step EMESSA: `fatturazione_pipeline.rollback`).

- ✅ **Fatto**: changeset `20260619-16-update-fn-reset-lotto-draft-accetta-emessa-mctit.yaml`
  (corpo dalla doc auto-gen + `%TYPE`). Solo il controllo fattura cambia (accetta DRAFT+EMESSA,
  via `v_emessa_id`); il controllo lotto-DRAFT resta.
- **Niente** riga matrice `2→1`: il reset **cancella** (DELETE), non transiziona → non passa
  dal guard di transizione.

### DB-3 — Documentazione

✅ **Fatto**: aggiunta la sezione *"Stato documentale della fattura: segue lo step
(invariante)"* in [fatturazione.md](../../guide/fatturazione.md) — macchine distinte
lotto/fattura, invariante `1→2→8` (mai `1→8`), MASSIVO vs GIORNALIERO, regola rollback
pre-fiscale.

### DB-4 — (no-op confermato) Matrice e guard fattura

Nessuna modifica a `trgfn_fatture_guard_stato` né alle transizioni **fattura** `1→2`/`2→8`:
già corrette. (DB-1 ha toccato solo le righe **lotto** `solo_lotto`.)

### 4.5 Bit-rot dei pgTAP esistenti (finding, follow-up)

Il pgTAP `test-fatturazione-reset-lotto-draft.sql` (e probabilmente altri test `vendite` che
inseriscono `attivita_fatturabili` diretto) è **silenziosamente rotto** da evoluzioni di schema
**successive** alla scrittura: `fatturazione_lotti.emittente_soggetto_ruolo_id` NOT NULL,
`attivita_fatturabili.commessa_id`/`commessa_attivita_id` NOT NULL + guard di coerenza. Non
emerso perché **i pgTAP non girano in CI**.

→ **Follow-up (opzione b)**: ricostruire i fixture con la catena reale
`fn_get_or_create_commessa → fn_upsert_commessa_attivita (APPROVATA + tipo_doc) → AF → fattura`,
e — idealmente — **portare i pgTAP in CI** per non ripetere il problema. La verifica funzionale
di DB-2 (reset accetta EMESSA) avviene nel frattempo via **test BE**.

---

## 5. Criteri di accettazione

- `run_fatturazione_batch --modalita differita` e `--modalita immediata` completano
  **end-to-end** (numerazione + chiusura lotto), **0 errori** di transizione stato.
- Dopo lo step EMESSA: lotto **e** fatture a stato 2. Dopo DEFINITIVA: entrambi a 8.
- GIORNALIERO: stesso comportamento (fattura `1→2→8`), IVA certificata prima della
  numerazione.
- `reset_lotto_draft` su lotto MASSIVO con fatture in EMESSA: le **accetta e cancella**
  (pre-fiscali); rifiuta le fiscali. ✅ logica applicata; verifica funzionale via test BE
  (pgTAP dedicato rimandato, §4.5).
- pgTAP **giornaliero** (`test-stati-doc-transizioni-giornaliero.sql`) **verde** (DB-1).

---

## 6. Fuori scope (segnalato, non bloccante)

**Atomicità rollback driver**: quando uno step va in errore, il rollback rimuove anche il
lotto creato in Fase 1, lasciando `fatture_righe`/ponte orfani. È un tema di
atomicità/cleanup del driver — da affrontare separatamente.
