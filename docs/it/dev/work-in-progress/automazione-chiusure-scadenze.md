# Piano di esecuzione — Automazione chiusure per scadenza (`dbops.automazione_chiusura_scadenze`)

> **Stato**: piano operativo — implementazione in corso (2026-04-26)
> **Branch DB**: `dev/db-tid`
> **Origine**: brief BE 2026-04-25 sui contratti (cessazione data-driven). Promozione al nucleo del pattern già implementato per `vendite.listini_versioni` (24-04-2026).
> **Manifesto sviluppo concentrico §7**: due consumatori reali → astrazione promossa al nucleo.

---

## 1. Contesto

Nel progetto esiste un pattern ricorrente per tabelle che hanno **sia** un ciclo di stato gestionale (workflow utente, tipicamente con uno stato terminale "chiuso") **sia** una finestra di validita' temporale (`valido_dal`/`valido_al`):

- `vendite.listini_versioni` con stati `BOZZA`/`ATTIVA`/`CHIUSA` (varchar diretto + CHECK constraint)
- `vendite.contratti` con stati `DRAFT`/`ATTIVO`/`CESSATO` (FK a `config.stati_doc_contratti`, codici_interno omonimi)

Nota: `SOSPESO` esiste come `codice_interno` in `config.stati_doc_contratti` ma **non rientra in questo piano** — la sua semantica (riattivabilita', ripristino stato) richiede logica dedicata che sara' affrontata separatamente. Il framework di chiusura ignora i contratti in SOSPESO.

In entrambi i casi:

1. La **fonte di verita' operativa** sono le date (`validita @> CURRENT_DATE`) — il resolver/i caller filtrano data-driven, mai per stato.
   - **Semantica di `valido_al`**: ultimo giorno **incluso** (convenzione `script.trgfn_set_validita`, bounds `[]` canonicalizzati a `[)`). Esempio: `valido_al = 2026-04-26` → la riga e' operativa fino al 2026-04-26 23:59:59, scade dal 2026-04-27 00:00:00.
   - **Conseguenza per la chiusura**: la query `valido_al < CURRENT_DATE` chiude le righe **dal giorno successivo** a `valido_al`. Schedule 00:05 cattura la scadenza al primo momento utile dopo il cambio data.
   - **Conseguenza per il guard transizione**: `ATTIVO→CESSATO` (e analoghi) ammesso solo se `NEW.valido_al < CURRENT_DATE` — l'utente non puo' chiudere manualmente nel giorno stesso di `valido_al`; deve attendere il giorno successivo, oppure impostare `valido_al` a una data gia' passata via PATCH.
2. Lo `stato` e' flag gestionale per UI/audit, va sincronizzato a `CHIUSA`/`CESSATO` quando `valido_al` scade.
3. Un **trigger guard** specifico della tabella vincola le transizioni e impedisce stati incoerenti (es. `CHIUSA` con `valido_al IS NULL` o futuro).
4. Un **job notturno** allinea automaticamente lo stato alla scadenza temporale.

I punti 1-3 sono inevitabilmente specifici della tabella (codici stato, transizioni ammesse, messaggi errore tipati). Il punto 4 e' **identico** nei due casi: si riduce a un UPDATE `SET stato=chiuso WHERE stato=attivo AND valido_al<CURRENT_DATE`. E' questa la parte che ora viene **promossa al nucleo `dbops`** come framework parametrico.

---

## 2. Architettura del framework

### 2.1 Tabella di configurazione `dbops.automazione_chiusura_scadenze`

Schema:

| Colonna | Tipo | Descrizione |
|---|---|---|
| `id` | smallserial PK | id tecnico |
| `schema_tabella` | text NOT NULL | es. `vendite` |
| `nome_tabella` | text NOT NULL | es. `listini_versioni`, `contratti` |
| `col_stato` | text NOT NULL | nome colonna stato (es. `stato`, `stato_doc_contratto_id`) |
| `tipo_stato` | text NOT NULL CHECK IN (`VARCHAR`, `FK`) | discrimina varchar diretto vs FK con lookup |
| `col_valido_al` | text NOT NULL DEFAULT `valido_al` | nome colonna data fine validita' |
| `stato_attivo_codice` | text NOT NULL | valore atteso prima della chiusura. Per VARCHAR e' direttamente il valore (es. `ATTIVA`); per FK e' il `codice_interno` (es. `ATTIVO`) |
| `stato_chiuso_codice` | text NOT NULL | valore target (es. `CHIUSA`, `CESSATO`) — semantica analoga |
| `fk_lookup_schema` | text NULL | per `tipo_stato='FK'`: schema della tabella di lookup (es. `config`) |
| `fk_lookup_table` | text NULL | per `tipo_stato='FK'`: nome tabella di lookup (es. `stati_doc_contratti`) |
| `fk_lookup_codice_col` | text NULL DEFAULT `codice_interno` | colonna su cui matchare il codice |
| `fk_lookup_id_col` | text NULL DEFAULT `id` | colonna PK della tabella lookup |
| `attivo` | boolean NOT NULL DEFAULT true | abilita/disabilita la riga |
| `descrizione` | text | doc inline |
| audit | | `data_insert`, `user_insert`, `data_update`, `user_update` standard |

**CHECK constraint coerenza** `chk_automazione_chiusura_scadenze_tipo_stato_coerente`:

```sql
(tipo_stato = 'VARCHAR' AND fk_lookup_schema IS NULL
  AND fk_lookup_table IS NULL
  AND fk_lookup_codice_col IS NULL
  AND fk_lookup_id_col IS NULL)
OR
(tipo_stato = 'FK' AND fk_lookup_schema IS NOT NULL
  AND fk_lookup_table IS NOT NULL
  AND fk_lookup_codice_col IS NOT NULL
  AND fk_lookup_id_col IS NOT NULL)
```

**Indice unique** `uq_automazione_chiusura_scadenze_target` su `(schema_tabella, nome_tabella)` — una sola riga per tabella target.

### 2.2 Funzione `dbops.fn_apply_chiusura_scadenze()`

Signature:
```sql
RETURNS jsonb
LANGUAGE plpgsql
```

Comportamento:

1. **Pre-check** per ogni riga `attivo=true`:
   - Verifica esistenza schema/tabella in `pg_class` + `pg_namespace`
   - Verifica esistenza colonna `col_stato` e `col_valido_al` in `pg_attribute`
   - Per `tipo_stato='FK'`: verifica esistenza `fk_lookup_schema.fk_lookup_table` e codici (lookup `stato_attivo_codice`/`stato_chiuso_codice` non null)
   - In caso di errore: raise `E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA` con contesto JSONB della riga problematica
2. **Esecuzione UPDATE dinamica** per ogni riga `attivo=true`:
   - Costruzione SQL via `format()` con `%I` (quote_ident) per identificatori e `%L` (quote_literal) per valori
   - Per VARCHAR: `UPDATE %I.%I SET %I = %L WHERE %I = %L AND %I IS NOT NULL AND %I < CURRENT_DATE`
   - Per FK: prima `SELECT id FROM %I.%I WHERE %I = %L` per `stato_chiuso_codice` e `stato_attivo_codice`, poi UPDATE con id
   - `EXECUTE` + `GET DIAGNOSTICS v_count = ROW_COUNT`
3. **Aggregazione risultato** in JSONB:
   ```json
   {
     "vendite.listini_versioni": 3,
     "vendite.contratti": 12,
     "_total": 15,
     "_executed_at": "2026-04-27T00:05:01+02:00"
   }
   ```
4. **Audit**: insert in `dbops.audit_log` con `area='database'`, `function_name='fn_apply_chiusura_scadenze'`, `context=<risultato JSONB>`.

**Sicurezza SQL dinamico**:
- Tutti gli identificatori passano per `quote_ident()` o `format(... %I ...)`
- Tutti i valori utente passano per `quote_literal()` o `format(... %L ...)`
- I valori in `dbops.automazione_chiusura_scadenze` sono comunque amministrativamente controllati (Liquibase seed), ma applichiamo igiene comunque

**Compatibilita' con guard tabella-specifici**: ogni UPDATE soddisfa per costruzione il guard della tabella target (precondizione `valido_al < CURRENT_DATE` identica al WHERE). Nessun bypass, nessun privilegio elevato.

### 2.3 Job pgAgent unico `chiusura_scadenze_daily`

Schedule: 00:05 ogni giorno. Step: `SELECT dbops.fn_apply_chiusura_scadenze()`.
Sostituisce il job specifico `listini_versioni_close_scadute_daily` (verra' droppato).

---

## 3. Componenti tabella-specifici (NON generalizzati)

Restano nelle rispettive cartelle dei domini:

| Componente | Listini | Contratti |
|---|---|---|
| Trigger guard transizione | `vendite.trgfn_listini_versioni_guard_transizione_stato` (esistente) | **da creare**: `vendite.trgfn_contratti_guard_transizione_stato` |
| Codice errore | `E_VERSIONE_STATO_TRANSIZIONE_INVALIDA` (id 391) | **da creare**: `E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA` (id 392) |
| Test pgTAP guard | `test-listini-versioni-guard-transizione-stato-v1.sql` (esistente) | **da creare**: `test-contratti-guard-transizione-stato-v1.sql` |
| Manual doc | `docs/it/dbzero/vendite/manual/listini_versioni.md` (da aggiornare) | `docs/it/dbzero/vendite/manual/contratti.md` (da aggiornare) |

Trigger guard contratti: matrice transizioni hardcoded (3 stati validi nel piano, 3 transizioni ammesse + 1 condizione temporale):

| Da | A | Ammessa | Condizione |
|---|---|---|---|
| DRAFT | ATTIVO | sì | — |
| ATTIVO | CESSATO | sì | `valido_al IS NOT NULL AND valido_al < CURRENT_DATE` |
| ATTIVO | ATTIVO | sì | no-op |
| DRAFT | DRAFT | sì | no-op |
| CESSATO | * | no | terminale |
| * → DRAFT (eccetto no-op) | no | irreversibile |
| ATTIVO → SOSPESO | non gestito ora | (vedi nota su SOSPESO) |
| SOSPESO → * | non gestito ora | |

Lookup via `codice_interno` su `config.stati_doc_contratti`. Codici DB seedati confermati: `1=DRAFT, 2=ATTIVO, 4=SOSPESO, 5=CESSATO`.

---

## 4. Step di esecuzione

### Fase A — Framework `dbops`

**A1**. `db/changelog/migrations_v2/00_schema/dbops/20260426-01-create-automazione-chiusura-scadenze-mctit.yaml`
- `createTable` per `dbops.automazione_chiusura_scadenze`
- CHECK constraint coerenza `tipo_stato`
- Indice UNIQUE su `(schema_tabella, nome_tabella)`
- audit fields standard

**A2**. `db/changelog/migrations_v2/20_code/dbops/20260426-01-create-fn-apply-chiusura-scadenze-mctit.yaml`
- `CREATE OR REPLACE FUNCTION dbops.fn_apply_chiusura_scadenze() RETURNS jsonb`
- Pre-check completo + dispatch VARCHAR/FK + audit log + ritorno JSONB

### Fase B — Migrazione caso esistente (listini_versioni)

**B1**. `db/changelog/migrations_v2/80_data/sql/dbops/automazione_chiusura_scadenze.csv` + changeset `loadUpdateData`
- Riga: `vendite.listini_versioni`, `tipo_stato='VARCHAR'`, codici `ATTIVA`/`CHIUSA`

**B2**. `db/changelog/migrations_v2/20_code/vendite/20260426-02-drop-fn-listini-versioni-close-scadute-mctit.yaml`
- `DROP FUNCTION IF EXISTS vendite.fn_listini_versioni_close_scadute()` (sostituita)

**B3**. Aggiornamento `docs/it/dbzero/vendite/manual/listini_versioni.md`: refactor sezione "Chiusura automatica via job pgAgent" — la chiusura ora avviene via framework `dbops`, non via funzione dedicata. Riferimento al catalogo `dbops.automazione_chiusura_scadenze`.

### Fase C — Nuovo caso (contratti)

**C1**. Aggiornamento `db/changelog/migrations_v2/80_data/sql/config/messaggi_errore.csv`:
- riga id 392: `E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA`
- riga id 393: `E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA`

**C2**. `db/changelog/migrations_v2/20_code/vendite/20260426-03-create-trgfn-contratti-guard-transizione-stato-mctit.yaml`
- Funzione trigger `vendite.trgfn_contratti_guard_transizione_stato`
- Trigger `trg_contratti_a10_guard_transizione_stato_upd` BEFORE UPDATE OF `stato_doc_contratto_id`

**C3**. Append in `automazione_chiusura_scadenze.csv` (stesso file di B1):
- Riga: `vendite.contratti`, `tipo_stato='FK'`, codici `ATTIVO`/`CESSATO`, lookup `config.stati_doc_contratti`

### Fase D — Job pgAgent unificato

**D1**. `db/changelog/migrations_v2/85_pgagent/20260426-01-create-pgagent-job-chiusura-scadenze-daily-mctit.yaml`
- DELETE eventuale job `listini_versioni_close_scadute_daily` esistente
- CREATE nuovo job `chiusura_scadenze_daily` schedule 00:05
- Step: `SELECT dbops.fn_apply_chiusura_scadenze();`

### Fase E — Test pgTAP

**E1**. `db/pgtap/dbops/test-fn-apply-chiusura-scadenze-v1.sql`
- 6-8 casi: pre-check tabella inesistente, pre-check colonna mancante, pre-check codice FK inesistente, esecuzione VARCHAR (un record chiuso), esecuzione FK (un record chiuso), idempotenza (2° esecuzione no-op), conteggio JSONB ritornato

**E2**. `db/pgtap/vendite/test-contratti-guard-transizione-stato-v1.sql`
- 7-8 casi (omettendo SOSPESO): DRAFT→ATTIVO ammesso, ATTIVO→CESSATO con valido_al NULL vietato, ATTIVO→CESSATO con valido_al futuro vietato, ATTIVO→CESSATO con valido_al scaduto ammesso, ATTIVO→DRAFT vietato, CESSATO→* vietato, no-op ammessa, framework chiude contratto scaduto

### Fase F — Documentazione

**F1**. `docs/it/linee-guida-sql.md` §7c: refactor con sezione "Framework `dbops.automazione_chiusura_scadenze`" + tassonomia tipo_stato VARCHAR/FK + esempi listini e contratti.

**F2**. `docs/it/guide/processi-pgagent-funzionali.md`: rimozione del job specifico listini, aggiunta del job unico `chiusura_scadenze_daily` con dettaglio framework.

**F3**. `docs/it/dbzero/vendite/manual/contratti.md`: nuova sezione "Workflow stato e transizioni" + sezione "Chiusura automatica via framework dbops".

**F4**. `docs/it/dbzero/vendite/manual/listini_versioni.md`: refactor sezione chiusura (rinvio al framework).

**F5**. `docs/it/mappa-concentrica.md` caso di studio "pratiche prima di vendite": aggiunta nota positiva — esempio virtuoso di applicazione del principio §7 (2 consumatori → promozione al nucleo).

---

## 5. Verifiche pre-landing

- [x] Codici_interno reali `config.stati_doc_contratti` confermati: `1=DRAFT, 2=ATTIVO, 4=SOSPESO, 5=CESSATO`
- [x] Pattern `dbops.automazione_overlap` come riferimento per `automazione_chiusura_scadenze`
- [x] Test pgTAP esistenti su `vendite.contratti`: solo `test-contratti-modalita-pricing-v1.sql`, fa solo DRAFT→ATTIVO (transizione ammessa dal nuovo guard, no rotture)
- [ ] Grep callers DB che filtrano per `stato_doc_contratto_id`: alcuni (`fn_list_contratti_da_pushare`) filtrano per stato_attivo_id — coerente con principio fail-safe? Da verificare se devono essere migrati a filtri data-driven (`validita @> CURRENT_DATE`). **Decisione rinviata post-implementazione**: il guard non blocca, sono solo letture.
- [x] EXCLUDE `ex_contratti_no_overlap` non filtra per stato — intenzionale, nessun back-fill che possa creare collisioni (no contratti CESSATI con `valido_al=NULL` in dev confermato dall'utente).

---

## 6. Ordine di landing operativo

L'ordine dei file YAML segue la timeline 20260426 (autogen Liquibase ordina per nome file):

1. A1 (00_schema/dbops/20260426-01)
2. A2 (20_code/dbops/20260426-01)
3. C1 (80_data CSV update — caricato runOnChange dal changeset esistente `20250717-22-upsert-messaggi_errore`)
4. C2 (20_code/vendite/20260426-03)
5. B2 (20_code/vendite/20260426-02 — drop fn vecchia, dopo C2 per non avere periodo senza chiusura)
6. B1 + C3 (80_data CSV — `automazione_chiusura_scadenze.csv` con entrambe le righe)
7. D1 (85_pgagent/20260426-01)
8. E1, E2 (test pgTAP — non vanno via Liquibase, eseguiti separatamente)
9. F1-F5 (doc, no impatto Liquibase)

Per la rinumerazione: gli ID dei changeSet hanno doppia numerazione interna `-NN-MM` per separare sub-changeset dentro lo stesso file. Es. `20260426-01-01` per createTable, `20260426-01-02` per addCheckConstraint, ecc.

---

## 7. Comunicazione al BE post-landing

Quando il framework e' applicato in dev e i test pgTAP passano, la comunicazione al backend includera':

- Conferma che la cessazione contratti via PATCH `valido_al` + job notturno funziona end-to-end DB (analogamente a quanto gia' fatto per listini)
- Codice errore `E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA` da mappare in `apps/core/services/error_policies.py` con HTTP status appropriato
- Service `apps/vendite/services/contratti_service.py::cambia_stato`: verificare che le transizioni manuali ammesse coincidano con la matrice DB (DRAFT→ATTIVO; cessazione data-driven via PATCH); rimuovere eventuali transizioni manuali ATTIVO→CESSATO ancora presenti

---

## 8. Estensioni future (fuori scope di questo piano)

- **SOSPESO** come stato gestionale: richiede logica dedicata (effetti su fatturazione, durata sospensione, ripristino). Sara' affrontato come piano separato.
- **Estensione framework ad altre tabelle** con pattern stato+validita': promozione automatica via INSERT in `dbops.automazione_chiusura_scadenze`, nessun nuovo codice DB richiesto. Eventuali nuovi tipi (es. ENUM nativo) richiederebbero estensione del dispatch nella funzione `fn_apply_chiusura_scadenze`.
- **Generalizzazione del guard transizione**: rinviata al 3° caso (manifesto §7). Per ora restano hardcoded per tabella.
- **Dashboard di monitoraggio**: vista `dbops.vw_chiusura_scadenze_stato` per audit umano dell'esito ultimo run del job.

---

*Piano redatto 2026-04-26. Aggiornare in coda con esito landing + decisioni operative residue.*
