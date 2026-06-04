# Brief DB — Immutabilità cliente su `vendite.ordini` (DB-ORD-LOCK)

> ✅ **COMPLETATO (DB) — 2026-06-04.** Seed registro + codice errore (469) +
> cleanup `trgfn_ordini_normalize` + trigger materializzato (drift §5.4) + pgTAP
> 8/8 verde + doc manuale aggiornata. Resta solo il **commit/PR** (S8, attende
> "procedi") e l'**hand-off BE** (S9, fuori scope DB).

> **Branch**: `dev/db-tid`. **Destinatario**: team DB.
> **Natura**: difesa DB autoritativa a complemento del fix BE «cliente immutabile»
> (chiuso 2026-06-04, vedi [analisi-ordini-vendita.md](analisi-ordini-vendita.md)).
> Il BE è solo metà del pattern ZeroErp (guard applicativo + trigger DB come
> difesa finale, api.md principio DB-first).
> **Vincolo**: ZeroErp non in produzione → breaking ammessi, ma la consegna è
> additiva e non-breaking verso il BE.
>
> ⚙️ **Revisione 2026-06-04**: questo brief riscrive una bozza precedente che
> proponeva trigger scritti a mano. Tre correzioni sostanziali (verificate sul
> codice): (1) si usa il **registro `dbops.automation_lock_columns`**, non DDL
> artigianale; (2) va **rimosso un ramo ora morto** in `trgfn_ordini_normalize`;
> (3) serve il **seed del codice errore** in `config.messaggi_errore`, non solo
> la mappatura BE. Dettaglio sotto.

---

## 1. Problema (verificato)

`vendite.ordini` denormalizza due colonne cliente che devono restare coerenti
([ordini.md](../../dbzero/vendite/tabelle/ordini.md)):

- `soggetto_ruolo_id bigint NOT NULL` — cliente logico (FK `fk_ordini_v_cliente_ruolo`);
- `billing_account_id bigint NULL` — aggancio billing (FK `fk_ordini_v_billing_account`).

La relazione **BA → SR è 1:1 deterministica** (`anagrafiche.billing_account.soggetto_ruolo_id`
NOT NULL); alla creazione `crea_ordine` deriva `soggetto_ruolo_id` dal BA. **Nessun
trigger ri-sincronizza le due colonne su UPDATE**: una `UPDATE` che cambia
`billing_account_id` lascerebbe `soggetto_ruolo_id` **stantio** → incoerenza
cliente↔soggetto (bug logico del modello, `feedback_bug_logici_modello`).

Difesa BE già applicata (necessaria ma non sufficiente):
`ordini_service.aggiorna_ordine` ha tolto `billing_account_id` dalla whitelist e
rifiuta il cambio BA (`E_ORD_VALIDAZIONE`). Ma l'autorità sui vincoli è il DB: una
`UPDATE` diretta che bypassa il service resta esposta.

## 2. Decisione di dominio (ratificata) — e cambio di comportamento da dichiarare

**«Cambiare cliente = nuovo ordine».** Le colonne `billing_account_id` e
`soggetto_ruolo_id` diventano **immutabili su UPDATE** (INSERT libero: la
creazione le valorizza normalmente).

> ⚠️ **Non è solo "difesa di un bug": è un cambio di comportamento esplicito.**
> Oggi `trgfn_ordini_normalize` ha un ramo *progettato* per gestire il **cambio di
> `billing_account_id` su UPDATE** (ri-eredita `fatturazione_trigger` dal nuovo
> BA, vedi [20260225-34](../../../db/changelog/migrations_v2/20_code/vendite/20260225-34-trgfn-ordini-normalize-fatturazione-trigger-mctit.yaml)).
> Bloccare il BA **revoca quella capacità**. La decisione la conferma: ma va
> registrata come scelta, e quel ramo va rimosso (§5.3), altrimenti resta logica
> morta e contraddittoria.

## 3. Cosa serve (il *cosa*; il *come* operativo è già deciso dal pattern, §4)

Rendere immutabili **solo su UPDATE**, lato DB:

- `vendite.ordini.billing_account_id`
- `vendite.ordini.soggetto_ruolo_id`

### 3.1 Perché entrambe (non solo BA)

Non basta lockare `billing_account_id`: gli ordini con `billing_account_id NULL`
sono identificati dal **solo** `soggetto_ruolo_id`. Il lock sul solo BA non
coprirebbe quei record → serve lockare anche `soggetto_ruolo_id`. (Razionale
assente nella bozza precedente, qui esplicitato.)

---

## 4. Meccanismo canonico — registro `automation_lock_columns`, NON trigger a mano

ZeroErp **non** scrive i lock-trigger a mano: c'è un registro data-driven
`dbops.automation_lock_columns` ([CSV](../../../db/changelog/migrations_v2/80_data/sql/dbops/automation_lock_columns.csv))
e un'automazione (`dbops.fn_run_automations_lock_columns` → proc
`maintenance.proc_automations_lock_columns_job()`, schedulata pgAgent) che
**genera** i trigger dalle righe del registro. I trigger usano
`script.trgfn_lock_columns` (coppie `colonna, codice`, override GUC
`zeroerp.allow_lock_columns_override`).

**Prova nel codebase** — la stessa immutabilità su `preventivi.emittente_fiscale_id`
(che la bozza citava come analogo) **è una riga di registro, non un trigger
artigianale**:

```csv
vendite,preventivi,emittente_fiscale_id,EMITTENTE_NON_MODIFICABILE,AUTO,t,"Snapshot user-derived ..."
```

Anche `vendite,ordini,numero` (il lock già attivo) e `catalogo,articoli,uom_id`
(`script.trgfn_lock_columns`) sono righe dello stesso registro. → Per ordini il
deliverable sono **due righe**, non DDL:

```csv
vendite,ordini,billing_account_id,E_ORD_CLIENTE_IMMUTABILE,AUTO,t,"Cliente immutabile post-create: cambiare cliente = nuovo ordine (DB-ORD-LOCK 2026-06-04)",2026-06-04 00:00:00,mctit,2026-06-04 00:00:00,mctit
vendite,ordini,soggetto_ruolo_id,E_ORD_CLIENTE_IMMUTABILE,AUTO,t,"Cliente immutabile post-create: coerenza con billing_account_id; copre ordini con BA NULL (DB-ORD-LOCK 2026-06-04)",2026-06-04 00:00:00,mctit,2026-06-04 00:00:00,mctit
```

> La **forma** del trigger generato (uno aggregato per tabella con coppie miste
> vs uno per colonna) la decide l'automazione: `trgfn_lock_columns` supporta più
> coppie con codici diversi, quindi convive con il lock esistente su `numero`
> (`CODICE_NON_MODIFICABILE`). Nessuna scelta di naming a carico del brief.
> Esiste anche una variante "conditional" (`20260522-02-create-lock-columns-conditional`):
> **non serve** qui — l'immutabilità è incondizionata post-create.

---

## 5. Deliverable DB (3 + cleanup)

### 5.1 Registro lock (seed)

Due righe in `automation_lock_columns.csv` (§4). Il CSV è caricato dal changeset
[20260110-15](../../../db/changelog/migrations_v2/80_data/changelog/20260110-15-upsert-dbops-automation-lock-columns-table.yaml)
(`runOnChange: true` + `validCheckSums: ANY`, upsert su PK
`target_schema,target_table,column_name`): aggiungendo le righe, alla prossima
migrazione il registro cresce. **Nessun nuovo changeset** per il seed.

### 5.2 Codice errore dedicato (seed)

Una riga in [messaggi_errore.csv](../../../db/changelog/migrations_v2/80_data/sql/config/messaggi_errore.csv)
(header `codice,lingua,messaggio,id,causa,soluzione`; max id attuale **468** →
usare **469** o prossimo libero, `feedback_error_codes_messaggi_errore`):

```csv
E_ORD_CLIENTE_IMMUTABILE,it,"Cliente immutabile: la colonna %s non è modificabile dopo la creazione dell'ordine.",469,"billing_account_id e soggetto_ruolo_id sono protetti da automation_lock_columns (script.trgfn_lock_columns): identificano il cliente dell'ordine e sono uno snapshot post-creazione. Cambiarli post-fact creerebbe incoerenza cliente↔soggetto.","Per cambiare il cliente di un ordine creare un nuovo ordine. Modifiche straordinarie solo via override manutenzione (SET LOCAL zeroerp.allow_lock_columns_override = 'on')."
```

> **Scartato** il fallback a `CODICE_NON_MODIFICABILE`: quel messaggio è
> *"Impossibile modificare il valore **interno** della colonna %s"* — semantica di
> colonna di sistema, fuorviante per il cliente. Il precedente corretto è
> `EMITTENTE_NON_MODIFICABILE` (id 421): codice parlante dedicato.

### 5.3 Cleanup obbligatorio — ramo morto in `trgfn_ordini_normalize`

Con il BA immutabile, il ramo UPDATE di `trgfn_ordini_normalize`
(`TG_OP='UPDATE' AND OLD.billing_account_id IS DISTINCT FROM NEW.billing_account_id`)
**non è più raggiungibile**: per ordine alfabetico dei trigger BEFORE UPDATE,
`trg_ordini_a10_lock_columns…` (a10) scatta **prima** di
`trg_ordini_normalize_ins_upd` e solleva l'errore. Lasciarlo = trigger che prova
a gestire un caso vietato da un altro trigger.

→ Nuovo changeset `runOnChange` in `20_code/vendite/` (mai modificare il changeset
pushato): riscrivere `vendite.trgfn_ordini_normalize` restringendo l'eredità di
`fatturazione_trigger` al **solo `TG_OP='INSERT'`** (mantenere anche il blocco
anno/data su INSERT). Sul percorso override manutenzione l'eredità non si applica:
è una via straordinaria, accettabile.

### 5.4 Materializzazione trigger

Eseguire l'automazione che genera i trigger dal registro:
`CALL maintenance.proc_automations_lock_columns_job();` (oppure attendere il job
pgAgent). Da coordinare col team DB nel flusso migrate (come fu per preventivi
emittente).

> ⚠️ **Nota drift (DB di lunga vita) — leggere prima di applicare su un ambiente
> esistente.** L'automazione `dbops.fn_run_automations_lock_columns` è
> **create-if-not-exists, NON reconcile**: genera un unico trigger per tabella
> (`trg_{table}_a10_lock_columns_upd`) solo se **non esiste già** per nome; la
> funzione di cleanup droppa il trigger solo quando **non resta alcuna colonna da
> lockare**. `vendite.ordini` aveva già `trg_ordini_a10_lock_columns_upd` (lock su
> `numero`), quindi il semplice `CALL` **non aggiunge** le nuove colonne cliente:
> le salta. Su DB **pulito/CI** non c'è problema (il trigger nasce completo al
> primo giro, via `90_end/ci_apply`). Sui **DB esistenti** serve una tantum:
>
> ```sql
> DROP TRIGGER IF EXISTS trg_ordini_a10_lock_columns_upd ON vendite.ordini;
> SELECT dbops.fn_run_automations_lock_columns('AUTO', NULL, false);
> ```
>
> Esito atteso: trigger ricreato `BEFORE UPDATE OF billing_account_id, numero,
> soggetto_ruolo_id` con codici misti (`E_ORD_CLIENTE_IMMUTABILE` per le due
> colonne cliente, `CODICE_NON_MODIFICABILE` per `numero`). Applicato sul dev il
> 2026-06-04. Coerente con la prassi di `preventivi.emittente_fiscale_id` (nessun
> changeset di remediation; auto su CI/fresh, manuale sui DB esistenti).
>
> **TODO produzione**: all'avvio del primo ambiente persistente non-CI, valutare
> un changeset di remediation riproducibile (DROP + `fn_run_automations_lock_columns`)
> così ogni ambiente esistente si auto-ripara al migrate, invece dell'intervento
> manuale (soluzione "B" del confronto 2026-06-04).

---

## 6. pgTAP (verifica consegna) — `db/pgtap/vendite/`

- presenza del/i trigger BEFORE UPDATE che lockano `billing_account_id` e
  `soggetto_ruolo_id`;
- `UPDATE` che cambia `billing_account_id` → **rifiutata** con `E_ORD_CLIENTE_IMMUTABILE`;
- `UPDATE` che cambia `soggetto_ruolo_id` → **rifiutata**;
- `UPDATE` di un campo lecito (es. `data`, `meta`) con cliente invariato → **passa**;
- `INSERT` con cliente valorizzato → **passa** (lock solo su UPDATE);
- override GUC `zeroerp.allow_lock_columns_override='on'` → `UPDATE` cliente **passa**
  (via di manutenzione);
- regressione: il lock su `numero` (`CODICE_NON_MODIFICABILE`) resta attivo.

## 7. Confine — semantica NULL e flusso "aggancia BA a posteriori"

Il lock rende immutabile **ogni** transizione di `billing_account_id`, incluse
`NULL → valore` e `valore → NULL`. Coerente con la decisione. **Implicazione**: un
ordine creato con `billing_account_id` NULL (solo `soggetto_ruolo_id`) non potrà
più ricevere un BA via UPDATE applicativa → servirebbe override manutenzione o
nuovo ordine. Se esiste/emergerà un flusso legittimo "aggancia BA a posteriori",
sarà un'azione di processo dedicata, non una UPDATE generica
(`feedback_no_quick_fix_soluzione_assoluta`). **Confermare col team che oggi non
esista tale flusso.**

## 8. Impatto / rischio

Additivo, basso rischio: nessuna colonna nuova, nessun dato modificato, nessun
impatto RLS. Tocca solo il percorso UPDATE (oggi gli ordini si modificano in DRAFT
lato BE). Unico effetto comportamentale: revoca del cambio-BA-su-update (§2, §5.3),
voluto. Il guard BE resta difesa-in-profondità con messaggio user-facing; il
trigger DB è la difesa finale autoritativa.

## 9. Coordinamento BE (fuori scope DB, hand-off a Tid)

Registrare `E_ORD_CLIENTE_IMMUTABILE` in `apps/core/services/error_policies.py`
(categoria validazione → HTTP 400) e nel traduttore `ordini_service._db_errors`
(estrae il codice `E_*` dal messaggio trigger). Belt-and-suspenders: il guard BE
intercetta già il cambio BA, quindi il codice emerge solo su UPDATE diretta che
bypassa il service.

## 10. Riferimenti

- Analisi + bug BE chiuso: [analisi-ordini-vendita.md](analisi-ordini-vendita.md).
- Funzione lock: `script.trgfn_lock_columns` ([doc](../../dbzero/script/funzioni/trgfn_lock_columns.md)).
- Registro + automazione: `dbops.automation_lock_columns`,
  `dbops.fn_run_automations_lock_columns`, `maintenance.proc_automations_lock_columns_job`.
- Precedente identico: `vendite,preventivi,emittente_fiscale_id` → `EMITTENTE_NON_MODIFICABILE` (id 421).
- Normalize da ripulire: [20260225-34](../../../db/changelog/migrations_v2/20_code/vendite/20260225-34-trgfn-ordini-normalize-fatturazione-trigger-mctit.yaml).

---

## 11. Piano di lavoro a step (da evadere)

> Ordine pensato per minimizzare i rischi: prima i seed (dato), poi la pulizia
> codice, poi la materializzazione, infine i test. Tutto su `dev/db-tid`. Nessun
> commit/migrate senza "procedi" (`feedback_no_commit_autonomo`).

| # | Step | File / azione | Tipo | Verifica |
| --- | --- | --- | --- | --- |
| S1 | **Decisione codice errore** — confermare nome `E_ORD_CLIENTE_IMMUTABILE` con Tid/BE | — | decisione | nome ratificato |
| S2 | **Seed registro lock** — 2 righe (BA + SR) | append `automation_lock_columns.csv` (§4) | seed | righe presenti, `enabled=t` |
| S3 | **Seed codice errore** — riga id 469 | append `messaggi_errore.csv` (§5.2) | seed | codice risolvibile da `fn_log_and_raise_error` |
| S4 | **Cleanup normalize** — rimuovi ramo UPDATE morto | nuovo changeset `runOnChange` `20_code/vendite/YYYYMMDD-NN-update-trgfn-ordini-normalize-insert-only-mctit.yaml` (§5.3) | code | funzione eredita `fatturazione_trigger` solo su INSERT |
| S5 | **Materializza trigger** | `CALL maintenance.proc_automations_lock_columns_job();` (o pgAgent) | run | trigger lock su BA+SR presenti su `vendite.ordini` |
| S6 | **pgTAP** | nuovo `db/pgtap/vendite/test-ordini-lock-cliente.sql` (§6) | test | 7 asserzioni verdi |
| S7 | **Migrate locale + test** | `make db-migrate` + `scripts/testpgtap.sh …` | run | migrate ok, pgTAP verde, regressione `numero` ok |
| S8 | **Commit / PR** `dev/db-tid` → `Tito-dev` | git | release | **attende "procedi"** |
| S9 | **Hand-off BE** (fuori DB) | nota a Tid per `error_policies.py` + `_db_errors` (§9) | coordinamento | mappatura 400 attiva |

**Numerazione `NN`**: oggi 2026-06-04 nessun changeset preesistente → la cleanup
normalize usa `NN=01`. I due seed sono append a CSV già caricati da changeset
`runOnChange` (nessun NN consumato).

### Stato esecuzione (2026-06-04)

- [x] **S1** — codice `E_ORD_CLIENTE_IMMUTABILE` confermato (Tid).
- [x] **S2** — 2 righe in `automation_lock_columns.csv` (BA + SR).
- [x] **S3** — riga id 469 in `messaggi_errore.csv` (`E_ORD_CLIENTE_IMMUTABILE`).
- [x] **S4** — changeset `20260604-01-update-trgfn-ordini-normalize-insert-only-mctit.yaml` (eredità solo INSERT).
- [x] **S6** — test `db/pgtap/vendite/test-ordini-lock-cliente.sql` (8 asserzioni).
- [x] **S5** — trigger materializzato sul dev (2026-06-04) via DROP + `fn_run_automations_lock_columns('AUTO',NULL,false)` per il drift §5.4 (il solo `CALL` non bastava: trigger `numero`-only già presente).
- [x] **S7** — pgTAP `test-ordini-lock-cliente.sql` eseguito: **8/8 verde** (2026-06-04).
- [x] **Doc manuale** aggiornata: `trgfn_ordini_normalize.md` (eredità solo INSERT) + `ordini.md` (§"Immutabilità cliente").
- [ ] **S8** — commit / PR → **attende "procedi"** (`feedback_no_commit_autonomo`).
- [ ] **S9** — hand-off BE (`error_policies.py` + `_db_errors`).

### Decisioni — risolte (2026-06-04)

1. **S1** — codice errore: **`E_ORD_CLIENTE_IMMUTABILE`** ✅ confermato.
2. **§7** — nessun flusso "aggancia BA a posteriori": il BA è assegnato subito
   alla creazione ✅ → lock incondizionato corretto.
3. **S5** — materializzazione: `CALL maintenance.proc_automations_lock_columns_job();`
   eseguito da Tid, seguito dal pgTAP specifico ✅.
