# Brief DB — Simmetria workflow L3 approvazione prezzo su `vendite.contratti_righe`

> Data: 2026-05-18
> Owner: team DB (`dev/db-tid`)
> Stato: pronto per applicazione
> Backend: predisposto. Il BB orchestratore `resolve_or_check_override_prezzo_riga_contratto` esiste già in [`contratti_service.py`](../../../../backend/apps/vendite/services/contratti_service.py) e attende il wiring `create_riga`/`update_riga`, bloccato sui campi DB qui richiesti.

## Contesto

Il refactor contratti modalità (2026-05-15..18) ha estratto come BB condiviso l'orchestratore dei 3 gate prezzo (L1 permesso override + L2 soglia % + L3 escalation richiesta approvazione) in `_pricing_gate_helpers.resolve_or_check_override_prezzo`, parametrico su `resolver_fn`/`error_code_validazione`. Entry point contratti `resolve_or_check_override_prezzo_riga_contratto` è già pronto (thin wrapper) ma **non cablato** in `ContrattiService.create_riga` / `ContrattiService.update_riga` come debito tecnico documentato.

Il blocco è il modello DB asimmetrico fra preventivi e contratti:

| Tabella | `stato_approvazione_prezzo` | `pratica_approvazione_prezzo_id` | Indice partial | FK | Trigger guard PENDING |
|---|---|---|---|---|---|
| `vendite.preventivi_righe` | ✅ esiste (migration `20260422-04-01`) | ✅ esiste | ✅ (migration `20260422-04-02`) | ✅ `fk_prevrighe_pratica_approvazione_prezzo` | ✅ `trg_preventivi_righe_a10_guard_pending_upd` (migration `20260422-07`) |
| `vendite.contratti_righe` | ❌ **manca** | ❌ **manca** | ❌ | ❌ | ❌ |
| `vendite.contratti_righe_componenti` | ✅ esiste | ✅ esiste | ✅ | ✅ | ✅ `trg_contratti_righe_componenti_a10_guard_pending_upd` |

Conseguenza operativa: oggi una riga contratto **semplice** (articolo non composito) con `tipo_eccezione = OVERRIDE` che viola la soglia L2 non ha dove salvare `PENDING` se l'operatore chiede approvazione. Il workflow L3 è già funzionante solo per le righe componenti. La simmetria a livello padre serve per chiudere il pattern e completare il wiring BE.

Decisione di dominio confermata 2026-05-18 (con Tid): simmetria piena, non rinviare a fase 2. Coerente con feedback memoria `feedback_simmetria_modello_no_meta_scope` + `feedback_no_quick_fix_soluzione_assoluta`.

## Richiesta

Replicare su `vendite.contratti_righe` lo stesso pattern già applicato a `vendite.preventivi_righe` (migrations `20260422-04` / `20260422-07`).

### Step 1 — Schema (DDL)

Aggiungere 2 colonne nullable + FK a `vendite.contratti_righe`:

| Colonna | Tipo | Nullable | Default | Note |
|---|---|---|---|---|
| `stato_approvazione_prezzo` | `config.stato_approvazione_prezzo` (ENUM) | YES | NULL | NULL = riga non in workflow (caso comune). Valori: PENDING, APPROVED, REJECTED |
| `pratica_approvazione_prezzo_id` | `bigint` | YES | NULL | FK `pratiche.pratiche(id)` |

Constraint:

- `fk_contrighe_pratica_approvazione_prezzo`: `FOREIGN KEY (pratica_approvazione_prezzo_id) REFERENCES pratiche.pratiche(id)`

Migration suggerita: `00_schema/vendite/20260519-NN-alter-contratti-righe-add-approvazione-prezzo-mctit.yaml`

Replica letterale di `20260422-04-01` adattando `preventivi_righe` → `contratti_righe` e il prefisso constraint `fk_prevrighe_*` → `fk_contrighe_*`. Stessi `COMMENT ON COLUMN` (testo già pronto sul migration preventivi).

### Step 2 — Indice partial

`CREATE INDEX ix_vendite_contratti_righe_stato_approvazione ON vendite.contratti_righe (stato_approvazione_prezzo) WHERE stato_approvazione_prezzo IS NOT NULL;`

Naming coerente con `ix_vendite_preventivi_righe_stato_approvazione`. Migration: sub-changeSet `20260519-NN-02-create-ix-contratti-righe-stato-approvazione` nello stesso file di Step 1.

### Step 3 — Trigger guard PENDING

Replicare `trgfn_preventivi_righe_guard_pending` adattando per `contratti_righe`. Pattern allowlist identico:

**Campi modificabili in stato PENDING (allowlist):**
- `stato_approvazione_prezzo` (transizione workflow)
- `pratica_approvazione_prezzo_id` (aggancio/disaggancio pratica)
- `meta` (payload jsonb)
- `data_update`, `user_update` (audit gestiti da framework)

**Campi struttura bloccati (denylist enumerata)** — colonne attuali di `vendite.contratti_righe` (vedi `docs/it/dbzero/vendite/tabelle/contratti_righe.md`):

```
contratto_id, articolo_id, tipo_erogazione, fonte_quantita_attesa,
periodicita, generazione_canone, competenza_canone, prezzo_unitario,
quantita, ordine, attivo, qta_operativa, uom_operativa_id,
factor_to_base, tipo_eccezione
```

`tx_id` escluso (gestione tx framework, non modificabile applicativamente).

Pattern guard scope:
- `IF OLD.stato_approvazione_prezzo IS DISTINCT FROM 'PENDING'::config.stato_approvazione_prezzo THEN RETURN NEW;`
- Solo se OLD era PENDING applica il vincolo denylist
- Ingresso in PENDING ammesso (NEW.stato = PENDING, OLD.stato = NULL/APPROVED/REJECTED)

Raise via `script.fn_log_and_raise_error` con codice `E_RIGA_PREZZO_PENDENTE` (già esistente in `config.messaggi_errore`, lo stesso usato dal trigger preventivi simmetrico — niente seed nuovo).

Trigger su tabella: nome `trg_contratti_righe_a10_guard_pending_upd`, BEFORE UPDATE, FOR EACH ROW, no `UPDATE OF` (intercettare qualsiasi UPDATE su riga PENDING). Migration: `20_code/vendite/20260519-NN-create-trgfn-contratti-righe-guard-pending-mctit.yaml`.

### Step 4 — Convivenza con trigger esistenti

Su `contratti_righe` esistono già 3 trigger BEFORE UPDATE pertinenti (visibili in `contratti_righe.md`):
- `trg_contratti_righe_a10_lock_post_attivazione_ins_upd_dlt` — blocca ogni UPDATE su righe di contratto in stato ATTIVO/CESSATO (post-attivazione lock immutabilità)
- `trg_contratti_righe_a10_guard_aggiunta_fuori_listino_ins_upd` — guard tipo_eccezione=AGGIUNTA
- `trg_contratti_righe_a10_guard_esclusione_figlio_bundle_ins_upd` — guard tipo_eccezione=ESCLUSIONE bundle

Il nuovo `_a10_guard_pending_upd` si applica SOLO se la riga era PENDING. In stato DRAFT del contratto (unico stato in cui le righe sono modificabili a livello service `_assert_contratto_draft`) tutti i 4 trigger BEFORE UPDATE coesistono senza ordine determinato. Verifica suggerita: nessuno dei 3 trigger esistenti modifica le colonne in allowlist; quindi l'ordine di esecuzione fra di loro non è rilevante.

Nessun conflitto con `lock_post_attivazione`: una riga PENDING è per definizione in contratto DRAFT (il workflow L3 si chiude prima dell'attivazione del contratto). Defense-in-depth: i 2 guard sono ortogonali — `lock_post_attivazione` blocca per stato testata, `guard_pending` blocca per stato riga.

## Verifica post-apply

Su istanza dev:

```sql
-- Step 1 + 2: schema + indice
SELECT column_name, data_type, is_nullable
  FROM information_schema.columns
 WHERE table_schema = 'vendite' AND table_name = 'contratti_righe'
   AND column_name IN ('stato_approvazione_prezzo', 'pratica_approvazione_prezzo_id');
-- Deve ritornare 2 righe

SELECT indexname FROM pg_indexes
 WHERE schemaname = 'vendite' AND tablename = 'contratti_righe'
   AND indexname = 'ix_vendite_contratti_righe_stato_approvazione';
-- Deve ritornare 1 riga

-- Step 1: FK
SELECT conname FROM pg_constraint
 WHERE conrelid = 'vendite.contratti_righe'::regclass
   AND conname = 'fk_contrighe_pratica_approvazione_prezzo';
-- Deve ritornare 1 riga

-- Step 3: trigger + funzione
SELECT proname FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname = 'vendite' AND p.proname = 'trgfn_contratti_righe_guard_pending';
-- Deve ritornare 1 riga

SELECT tgname FROM pg_trigger
 WHERE tgrelid = 'vendite.contratti_righe'::regclass
   AND tgname = 'trg_contratti_righe_a10_guard_pending_upd';
-- Deve ritornare 1 riga
```

## pgTAP

Replicare la suite pgTAP di `preventivi_righe` (file `db/pgtap/vendite/test_preventivi_righe_guard_pending.sql` se esiste). I casi pattern:

1. Riga NULL → UPDATE qualsiasi campo OK
2. Riga PENDING → UPDATE `prezzo_unitario` → RAISE `E_RIGA_PREZZO_PENDENTE`
3. Riga PENDING → UPDATE `stato_approvazione_prezzo` da PENDING → APPROVED OK (transizione workflow)
4. Riga PENDING → UPDATE `pratica_approvazione_prezzo_id` OK (aggancio)
5. Riga PENDING → UPDATE `meta` OK (payload)
6. Riga PENDING → UPDATE multi-campo con almeno uno fuori allowlist → RAISE
7. Riga APPROVED → UPDATE `prezzo_unitario` OK (lock solo su PENDING)
8. Riga REJECTED → UPDATE `prezzo_unitario` OK (lock solo su PENDING)

## Backend post-apply (BE su `dev/backend-tid`)

Una volta atterrato il DB, il backend completa la chiusura del debito tecnico documentato in `refactor-contratti-modalita.md` §7.6:

1. Fix bug latente nel wrapper `resolve_or_check_override_prezzo_riga_contratto`: normalizzare `testata["data"] = testata["valido_dal"]` prima di passare al BB (oggi senza fix il BB skipperebbe i gate per `data is None`)
2. Refactor `approvazioni_prezzo_service` sorgente-agnostico: generalizzare `crea_richiesta_approvazione` per accettare sorgente PREVENTIVO o CONTRATTO, `link_riga_a_pratica` con due chiavi meta distinte, `_get_riga_pending` con dispatch su tabella
3. Cablare `resolve_or_check_override_prezzo_riga_contratto` in `ContrattiService.create_riga` e `ContrattiService.update_riga` con stessa logica di `preventivi_service.gestisci_riga`:
   - Skip totale per `tipo_eccezione = ESCLUSIONE` (prezzo NULL)
   - Per OVERRIDE / AGGIUNTA: L1 sempre, L2/L3 condizionali al resolver (Alternativa B confermata 2026-05-18)
4. 6-8 test mirati BE + verifica suite verde
5. Aggiornare `api_contratti.md` + `catalogo-building-block-backend.md` + `ai-context.md`

## Riferimenti

- Refactor contratti modalità: [`refactor-contratti-modalita.md`](refactor-contratti-modalita.md) §6 + §7.6 (debito tecnico residuo aperto)
- Modello componenti unificato: [`modello-componenti-bom.md`](../../../../docs/it/dev/manual/modello-componenti-bom.md)
- Pattern simmetrico preventivi (riferimento di adattamento):
  - DDL: `db/changelog/migrations_v2/00_schema/vendite/20260422-04-alter-preventivi-righe-add-approvazione-prezzo-mctit.yaml`
  - Trigger guard: `db/changelog/migrations_v2/20_code/vendite/20260422-07-create-trgfn-preventivi-righe-guard-pending-mctit.yaml`
- BB orchestratore L1+L2+L3: `apps/vendite/services/_pricing_gate_helpers.py:resolve_or_check_override_prezzo`
- Pattern caller preventivi: `apps/vendite/services/preventivi_service.py:gestisci_riga` + `_orchestrate_l3_request`
- BB sorgente contratti già pronto: `apps/vendite/services/contratti_service.py:resolve_or_check_override_prezzo_riga_contratto`
- Catalogo BB backend: `docs/it/dev/backend/catalogo-building-block-backend.md` sezione "Vendite — Gate autorizzazioni prezzi L1+L2+L3"
