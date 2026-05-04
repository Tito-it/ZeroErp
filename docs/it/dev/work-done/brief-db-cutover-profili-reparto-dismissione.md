# Brief team DB — Dismissione modello legacy `profili_reparto_*`

> **Stato:** brief tecnico, scritto a fronte del completamento lato Backend Python del cutover PR2 (modello permessi). Le azioni qui descritte sono **DDL/DML/migrations** e spettano al team DB (regola operativa: l'agente backend non esegue azioni DB).
>
> **Branch di riferimento:** `dev/db-tid` (target del PR DB).
>
> **Data:** 2026-05-04.

---

## 1. Contesto

Il modello permessi è in transizione duale dal refactor multi-face-auth (PR-B, aprile 2026):

- **Modello legacy**: `config.profili_reparto_aree`, `config.profili_reparto_azioni` (1 riga = 1 reparto x area/azione).
- **Modello nuovo**: `config.profili_accesso` + `config.profili_accesso_aree` + `config.profili_accesso_azioni` + `config.profili_accesso_bindings` (modello generalizzato a 3 tipi: REPARTO / PORTALE / AD_HOC).

I 4 resolver DB (`fn_resolve_livello_area`, `fn_check_azione_processo`, `fn_get_user_permissions_map`, `fn_get_user_actions_map`) hanno già fatto il cutover lettura sul nuovo modello (migration `20260419-51..54` + GUC-aware `20260421-04`).

**Bug residuo della transizione**: il backend Python amministrativo continuava a scrivere sulle tabelle legacy. La sincronia avveniva solo al deploy via la migration `runOnChange` `20260418-42-migrate-profili-reparto-to-profili-accesso`. Risultato: ogni save UI dei livelli reparto restava effettivo solo dopo `make db-migrate` manuale.

Questo brief chiude la transizione lato BE e chiede al team DB di rimuovere il modello legacy.

## 2. Cosa è già stato fatto lato Backend Python

Su branch `dev/backend-tid`, file modificati:

### 2.1 `apps/amm_software/db/amm_software_repository.py`

- `put_profilo_reparto(uo_id, aree, azioni)` riscritto per scrivere direttamente su:
  1. UPSERT su `config.profili_accesso` con `tipo='REPARTO'` e `codice = 'REPARTO_' || uo.codice_interno` (stessa convenzione della migration di backfill).
  2. UPSERT su `config.profili_accesso_bindings` per `(profilo_accesso_id, unita_organizzativa_id)`, con `ON CONFLICT` sull'indice parziale `uq_profili_accesso_bindings_uo`.
  3. `DELETE` + `INSERT` su `config.profili_accesso_aree` filtrate per `profilo_accesso_id`.
  4. `DELETE` + `INSERT` su `config.profili_accesso_azioni` filtrate per `profilo_accesso_id`.
  - Operazione atomica in `transaction.atomic()`.
  - Fail-fast `E_AMM_VALIDAZIONE` se `uo_id` inesistente, prima di toccare qualunque tabella.

- `get_profilo_reparto(uo_id)` riscritto per leggere via `JOIN profili_accesso_bindings → profili_accesso_aree/_azioni → aree_funzionali/_azioni_processo`, filtrato per `unita_organizzativa_id`. Contratto API invariato (`{"aree": [...], "azioni": [...]}`).

- `list_reparti()` riscritto: i conteggi `profilo_aree_count` / `profilo_azioni_count` vengono ora dalle tabelle `profili_accesso_*` joinate via `profili_accesso_bindings`.

- Blacklist `_MODEL_OVERRIDE_RISERVATI` aggiornata: rimosso `('config', 'profili_reparto_aree/_azioni')`, aggiunto `('config', 'profili_accesso_aree/_azioni')`.

### 2.2 `apps/core/db/permissions_audit_repository.py`

- `_DEPT_TABLES` aggiornato a 3 entry su `storico.profili_accesso_*`. La struttura della tupla è ora `(schema_table, label, kind)` dove `kind`:
  - `direct` → snapshot ha `unita_organizzativa_id` (caso `storico.profili_accesso_bindings`)
  - `profilo` → snapshot ha `profilo_accesso_id`, risolto via sub-query su `config.profili_accesso_bindings` corrente (casi `storico.profili_accesso_aree/_azioni`)

- I label valid-table cambiano: `profili_reparto_aree/_azioni` rimossi, aggiunti `profili_accesso_aree/_azioni/_bindings`. Se la UI ha select/filter cablati sui vecchi label, va aggiornata (ma legge da `_VALID_TABLE_NAMES` quindi auto-allineata).

### 2.3 `apps/config/models.py`

- ORM Django `ProfiloRepartoArea` e `ProfiloRepartoAzione` rimossi. Erano `managed=False` e usati solo da introspezione `_meta`, nessuna scrittura.

### 2.4 Test BE

- `test_permissions_audit.py`: aggiornate le asserzioni `assertNotIn("profili_reparto", sql)` mantenute più strict aggiungendo anche `assertNotIn("profili_accesso_*", sql)` quando atteso assente.
- I test `test_profili_reparto.py` (api) e `test_amm_software_service.py` (services) mockano il repository: passano invariati.
- Suite `apps.core` + `apps.amm_software` + `apps.config`: 647/650 verde, 3 errori pre-esistenti (`test_invio_invito`, `test_emittenti_form_defaults`) per `OperationalError` su DB non raggiungibile dal server backend — non sono regressi dal cutover.

## 3. Cosa serve fare lato DB

### 3.1 Rimuovere la migration di backfill (priorità alta)

File: `db/changelog/migrations_v2/80_data/changelog/20260418-42-migrate-profili-reparto-to-profili-accesso-mctit.yaml`.

**Opzione A (preferita, semantica di archivio):** sostituire il contenuto del changeset con un commento storico + `SELECT 1` no-op. Mantenere `runOnChange: true` e `validCheckSum: [ANY]` per non rompere i checksum Liquibase.

**Opzione B:** lasciare il file ma aggiungere una `precondition sqlCheck` che salta se le tabelle legacy non esistono più (`tableExists` con `onError: MARK_RAN`). Il file diventa quindi self-disabling dopo il drop.

Preferenza: opzione A — più chiara, archivio storico esplicito.

### 3.2 DROP delle tabelle legacy (DDL)

Nuovo changeset, ad esempio `db/changelog/migrations_v2/00_schema/config/20260505-XX-drop-profili-reparto-mctit.yaml`:

```yaml
- DROP TABLE config.profili_reparto_aree;
- DROP TABLE config.profili_reparto_azioni;
- DROP TABLE storico.profili_reparto_aree;
- DROP TABLE storico.profili_reparto_azioni;
```

Verificare prima che:
- Nessun trigger su altre tabelle referenzi quelle legacy.
- `config.area_model_overrides` non punti a model `profili_reparto_*` (verifica seed `20260410-11`).

Se ci sono riferimenti residui, segnalarmi e li gestisco lato Python prima del DROP.

### 3.3 Sorgenti audit `script.vw_audit_sources`

Verificare che la vista (o seed che la popola) **non includa più** `profili_reparto_aree/_azioni` come `code` ammissibili. Devono comparire `profili_accesso_aree`, `profili_accesso_azioni`, `profili_accesso_bindings` (i corrispondenti hanno tabelle `storico.profili_accesso_*` già esistenti — migrations `20260418-34..37`).

Se la vista è seedata via `db/changelog/migrations_v2/80_data/...`, individuare il file e aggiornare. La whitelist BE Python attinge dalla vista lato API (`amm_software_repository.py:_AUDIT_TABLES_CACHE` via `script.vw_audit_sources`), quindi il front-end vedrà i nuovi nomi automaticamente al refresh della vista.

### 3.4 Test pgTAP da rimuovere/aggiornare

- `db/pgtap/config/test-permessi-profili-reparto.sql` — rimuovere il file (test specifici sulle tabelle droppate).
- `db/pgtap/dbops/test-audit-sources-seed.sql` — aggiornare il check sui code ammissibili (rimuovere legacy, aggiungere `profili_accesso_*`).
- `db/pgtap/script/test-fn-audit-summary.sql` — sostituire i test su `storico.profili_reparto_aree/_azioni` con i nuovi `storico.profili_accesso_aree/_azioni/_bindings`.
- `db/pgtap/script/test-fn-resolve-regression-operatore.sql` — rimuovere il commento NOTA e adeguare la fixture dati al modello nuovo (popolare `profili_accesso_*` invece di `profili_reparto_*`).

### 3.5 Documentazione

File da rimuovere o marcare archive:

- `docs/it/dbzero/config/manual/profili_reparto_aree.md`
- `docs/it/dbzero/config/manual/profili_reparto_azioni.md`
- `docs/it/dbzero/config/tabelle/profili_reparto_aree.md` (auto-gen, sparirà al prossimo rebuild post-DROP)
- `docs/it/dbzero/config/tabelle/profili_reparto_azioni.md` (idem)
- `docs/it/dbzero/storico/tabelle/profili_reparto_aree.md` (idem)
- `docs/it/dbzero/storico/tabelle/profili_reparto_azioni.md` (idem)

File da aggiornare per rimuovere riferimenti alla transizione:

- `docs/it/guide/architettura-permessi-e-autorizzazioni.md` — sezioni 4.4-4.5: aggiornare con le tabelle `profili_accesso_*` come autoritative.
- `docs/it/guide/architettura-multi-face-auth.md` — tabella comparativa sez. 12 "Cosa resta / Cosa si generalizza": rimuovere la riga che dice `profili_reparto_aree → diventa profili_accesso_aree`, sostituire con conferma del completamento cutover.
- `docs/it/dbzero/script/manual/fn_get_profili_accesso_applicabili.md` — aggiornare la sezione "Coerenza con il modello legacy" rimuovendo la nota "Durante la transizione (prima del merge di PR2 backend) il backend amministrativo continua a scrivere su `profili_reparto_*`". La transizione è chiusa.
- `docs/it/dbzero/config/manual/profili_accesso.md`, `profili_accesso_aree.md`, `profili_accesso_azioni.md` — aggiornare frasi tipo "rimpiazzo concettuale" / "restano in uso" per riflettere lo stato finale.
- `docs/it/backend/amm-software/manual/api_amm_software.md`, `docs/it/backend/core/manual/permissions_resolver.md`, `docs/it/backend/core/manual/api_permessi_effettivi.md`, `docs/it/backend/core/manual/api_permessi_audit.md` — aggiornare elenchi sorgenti audit/tabelle citate.

### 3.6 Funzioni DB residue che potrebbero leggere dal legacy

Verifica grep finale dopo il DROP:

```bash
grep -rn "profili_reparto" db/changelog/migrations_v2/20_code/
```

Le funzioni storiche che leggevano dal legacy sono già state aggiornate dalle migrations `20260419-51..54`, ma vale la pena un check finale prima del DROP per evitare errori `relation "config.profili_reparto_aree" does not exist`.

## 4. Ordine di esecuzione consigliato

1. **Backend Python merge** del PR `dev/backend-tid` con il cutover sopra descritto. Conferma deploy in dev: ogni save UI dei livelli reparto si propaga in real-time al resolver.
2. **Verifica funzioni DB**: grep `profili_reparto` su `20_code/`. Se tutto pulito, procedi a 3.
3. **Rimuovi/archive backfill** (`20260418-42`): si svuota a no-op.
4. **Drop tabelle legacy** (4 tabelle: 2 in `config`, 2 in `storico`) in unico changeset.
5. **Aggiorna `vw_audit_sources`** + test pgTAP correlati.
6. **Rimuovi/archive doc** auto-gen e aggiorna doc concettuale.
7. **Smoke test** end-to-end: salva profilo reparto da UI → verifica con `script.fn_resolve_livello_area` che il livello si propaghi immediatamente per gli operatori del reparto.

## 5. Test smoke finale post-deploy

Comando psql:

```sql
-- Pre: prendere un operatore non-admin con il suo reparto.
-- 1) Salvare via UI un livello specifico (es. documenti=TUTTO) per quel reparto.
-- 2) Verificare immediatamente:
SELECT script.fn_resolve_livello_area(<auth_user_id>, 'documenti');
-- Atteso: 'TUTTO'. Se 'BLOCCATO' → bug residuo, NON deployare il drop.
```

Smoke test lato BE: la suite `apps.amm_software.tests.api.test_profili_reparto` resta verde (mock-based). Per smoke real-DB, eseguire `manage-test.sh apps.amm_software` con DB up.

## 6. Compatibilità

**Niente compat shim**. Il progetto non è in produzione (memoria operativa: niente fasi di compat, breaking change ammessi). Una volta merge del BE Python e DROP delle tabelle, ogni eventuale codice non aggiornato che provasse a fare `INSERT/SELECT` sulle legacy fallirebbe con `relation does not exist` — comportamento corretto fail-fast.

## 7. Note finali

Il refactor backend è **idempotente** sul DB attuale: chiamare `put_profilo_reparto` su un reparto che ha già il binding REPARTO popolato dalla migration `20260418-42` aggiorna correttamente `aree`/`azioni` senza creare duplicati (UPSERT sul codice profilo + UPSERT sul binding).

Eventuali profili `REPARTO` orfani (binding cancellato ma profilo ancora presente) NON sono prodotti dal nuovo BE. Se il team DB rileva orfani pre-esistenti durante il drop, una pulizia opzionale:

```sql
DELETE FROM config.profili_accesso pa
 WHERE pa.tipo = 'REPARTO'
   AND NOT EXISTS (
     SELECT 1 FROM config.profili_accesso_bindings pab
      WHERE pab.profilo_accesso_id = pa.id
   );
```

Buon merge.
