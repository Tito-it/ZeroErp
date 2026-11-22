# Refactor overlap v2 — portare i vincoli anti-overlap PARZIALI dentro l'automation

> **Data:** 2026-06-02
> **Origine:** follow-up di [refactor-overlap.md](refactor-overlap.md). Lì abbiamo
> ripristinato a mano 5 EXCLUDE parziali (migration `20260602-01..05`, applicate).
> Qui pianifichiamo l'**evoluzione del framework** `dbops.automazione_overlap` per
> gestire anche i vincoli **parziali** (con `WHERE`), eliminando la casistica "a mano".
> **Natura:** lato DB. Le migration si generano fase per fase, **solo dopo "procedi"**.
> **Convenzione avanzamento:** ogni step ha una checkbox. Si spunta `[x]` man mano
> che viene eseguito (con accanto il numero migration reale, es. `20260603-NN`).

---

## 0. Perché (in una frase)

Oggi l'automation sa creare solo EXCLUDE **totali** (niente `WHERE`); i vincoli
"niente sovrapposizioni **solo tra le righe attive**" (attivo / stato) restano
scritti a mano. Introducendo un parametro **`where_predicate`** in config, il
framework copre anche i parziali: una sola fonte di verità, ri-applicabile — e
soprattutto **immune** al tipo di regressione PG18 (drop+ricrea a indice) che ha
originato tutto.

---

## 1. Stato attuale (baseline verificata su dev — 2026-06-02)

- Config `dbops.automazione_overlap`: PK `(target_schema, target_table)`, **non**
  ha colonna per il predicato. Colonne: `key_columns`, `valido_dal_col`,
  `valido_al_col`, `range_bounds`, `range_col`, `constraint_name`, `active`,
  `exec_mode`, `note` + audit.
- `fn_apply_automazione_overlap(p_exec_mode text, p_dry_run boolean)`: costruisce
  `EXCLUDE USING gist (<chiavi WITH => , <validita WITH &&>)` **senza** `WHERE`.
- `fn_seed_automazione_overlap`: rileva EXCLUDE (contype `x`) e indici GiST su
  **espressione** `daterange(...)`; **non** cattura il predicato `WHERE`.
- I 6 vincoli parziali reali oggi sono **fuori dal framework**:
  - `vendite.contratti` → in config con `active=false` (override deliberato);
  - le 5 di `20260602-*` (`listini_righe_componenti`, `promo_articoli`,
    `listini_versioni`, `categorie_clienti_listini`, `template_documenti_versioni`)
    → **non presenti** in config.

---

## 2. Disegno della soluzione

**Idea minima:** una colonna `where_predicate text` (NULL = totale, come oggi).
`fn_apply` appende `WHERE (<predicate>)` quando valorizzata.

**Vincoli/decisioni di design:**

- **Predicato = frammento DDL di fiducia.** Le chiavi sono protette con
  `quote_ident`; il predicato è un'espressione libera (`attivo = true`) e **non**
  è quotabile → va iniettato as-is. Scrivibile **solo da DBA** (è una tabella
  `dbops`). Da documentare esplicitamente.
- **Un solo vincolo overlap per tabella** (PK `schema+table`). Sufficiente per i
  nostri casi; se servisse un secondo constraint parziale sulla stessa tabella, il
  modello andrebbe esteso (PK + `constraint_name`). Fuori scope ora.
- **Idempotenza invariata:** `fn_apply` salta se trova *qualsiasi* EXCLUDE sulla
  colonna periodo. Conseguenza: **cambiare** un predicato richiede prima un drop
  manuale del constraint (il framework non fa ALTER). Da documentare.
- **Le migration `20260602-*` restano valide.** La Fase 2 le "adotta" (registra in
  config); non serve droppare/ricreare nulla per correttezza — solo per governance.

---

## 3. FASE 1 — Core: il framework sa creare EXCLUDE parziali

Obiettivo: aggiungere `where_predicate` e farlo usare a `fn_apply`. Nessuna
tabella applicativa toccata in questa fase.

- [x] **1.1** Migration `00_schema/dbops` → **`20260602-06`** (`alter-automazione-overlap-add-where-predicate`):
      `ADD COLUMN where_predicate text` + `COMMENT` (predicato parziale, DDL di
      fiducia DBA-only, NULL = vincolo totale).
- [x] **1.2** Migration `20_code/dbops` (`runOnChange: true`) → **`20260602-07`**
      (`update-fn-apply-automazione-overlap-where-predicate`): `fn_apply` costruisce
      `v_where` e appende `WHERE (<predicate>)` all'`EXECUTE`; `where_predicate`
      nei `p_params` audit (OK + DRYRUN); idempotenza/dry-run invariati.
- [x] **1.3** Test pgTAP → **`db/pgtap/dbops/test-fn-apply-automazione-overlap-where-predicate-v1.sql`**
      (6 test): EXCLUDE creato, def contiene `WHERE attivo`, due righe attive
      sovrapposte bloccate (`23P01`), riga disattiva sovrapposta ammessa,
      `where_predicate` NULL → EXCLUDE totale senza `WHERE`.
- [x] **1.4** Validazione su dev: i 6 test pgTAP eseguiti **in transazione con
      ROLLBACK** (nulla persistito) → tutti verdi. (Il dry-run formale
      `fn_apply('AUTO', true)` post-apply resta da rieseguire dopo l'applicazione
      ufficiale: atteso nessun effetto, le righe `active=true` sono già a EXCLUDE.)
- [x] **1.5** Doc: `guide/automazione-db.md §4.3` (sezione `where_predicate` +
      idempotenza/cambio predicato) e `linee-guida-sql.md §7b` (nota aggiornata:
      i parziali sono ora delegabili al framework).

> Esito Fase 1: il framework **può** creare partial EXCLUDE (validato su dev), ma
> **nessun** vincolo reale è ancora gestito da lui (le tabelle restano
> `active=false`/assenti). Zero impatto runtime. **File generati, da applicare via
> Liquibase + committare** (li applica l'utente). Punto di commit sicuro.

---

## 4. FASE 2 — Governance: portare i 6 vincoli sotto il framework

Obiettivo: registrare in config i 6 vincoli parziali con il loro predicato e
`active=true`, così che il framework li **ri-applichi** dopo un eventuale drop
futuro (anti-regressione). Opzionale ma è il vero valore.

### 4.1 Core — chiavi su espressione esplicite (opzione A)

**Decisione presa: opzione A "esplicita".** Per gestire
`categorie_clienti_listini` (chiave su `COALESCE(classe_utenza_id,-1)`) **dentro**
il framework, senza eccezioni e senza euristiche fragili, si estende la config con
una colonna **`key_expressions`** separata da `key_columns`:

- `key_columns text[]` → **colonne semplici** (validate via `fn_col_exists`, quotate
  con `quote_ident`) — come oggi;
- `key_expressions text[]` → **espressioni** (es. `COALESCE(classe_utenza_id,-1)`),
  iniettate **as-is** (frammento DDL di fiducia DBA-only, stessa natura di
  `where_predicate`; non quotabili, non validabili).

La chiave finale del constraint = colonne quotate **+** espressioni raw, poi
`validita WITH &&`. (L'ordine delle chiavi `WITH =` non cambia la semantica
anti-overlap; impatta solo l'indice.)

- [x] **2.1** Migration `00_schema/dbops` → **`20260602-08`**
      (`alter-automazione-overlap-add-key-expressions`): `ADD COLUMN
      key_expressions text[]` + COMMENT (DDL di fiducia DBA-only; NULL/vuoto = solo
      colonne semplici). **Applicata.**
- [x] **2.2** Migration `20_code/dbops` (`runOnChange`) → **`20260602-09`**
      (`update-fn-apply-automazione-overlap-key-expressions`): `fn_apply` appende le
      `key_expressions` as-is dopo le `key_columns` validate; guard "no key" solo se
      **entrambe** vuote. **Applicata.**
- [x] **2.3** pgTAP → **`db/pgtap/dbops/test-fn-apply-automazione-overlap-key-expressions-v1.sql`**
      (4 test): EXCLUDE creato, def con `COALESCE`, due righe `classe NULL`
      sovrapposte bloccate (i NULL resi uguali dal `COALESCE`), `classe NULL` vs
      valorizzata ammesse. **Verde 4/4 sulla funzione live.** Doc dbzero rigenerati
      (funzione + tabella `automazione_overlap`).

### 4.2 Registrazione dei 6 vincoli in config (`active=true`)

I 6 hanno **già** l'EXCLUDE reale (applicato in Fase 0/`20260602-*`): registrarli
serve a farli **ri-creare** dal framework dopo un eventuale drop futuro (l'apply è
idempotente → oggi li **salta**). Censimento overlap già = 0 (refactor-overlap
§5.1). Registrazione via INSERT/UPSERT **idempotente** (non CSV `80_data`: è config
operativa `dbops`, segue il precedente `20260110-13-insert-automation-rule-*`).

> **Tutti i 6 in un'unica migration → `80_data/changelog/20260602-10`**
> (`insert-automazione-overlap-vincoli-parziali`), upsert su PK
> `(target_schema, target_table)`. `range_col='validita'` così un eventuale
> re-apply ricrea l'EXCLUDE identico (`validita WITH &&`). **Validata su dev**
> (upsert → `fn_apply('AUTO',false)` salta tutti i 6, nessun `_c` creato, rollback
> pulito). **Da applicare.**

- [x] **2.4** `vendite.contratti` → `where_predicate='NOT is_abortito_snapshot'`,
      `constraint_name='ex_contratti_no_overlap'`, `active=true` (era `false`).
- [x] **2.5** `vendite.listini_righe_componenti` → `where_predicate='attivo = true'`,
      `constraint_name='ex_listini_righe_comp_no_overlap'`, `active=true`.
- [x] **2.6** `vendite.promo_articoli` → `where_predicate='attivo IS TRUE'`,
      `constraint_name='ex_promo_articoli_no_overlap'`, `active=true`.
- [x] **2.7** `vendite.listini_versioni` → `where_predicate='attivo IS TRUE AND
      (stato)::text = ''ATTIVA''::text'`,
      `constraint_name='ex_listini_versioni_no_overlap'`, `active=true`.
- [x] **2.8** `anagrafiche.categorie_clienti_listini` (**usa 4.1**) →
      `where_predicate='attivo IS TRUE'`,
      `key_columns=['categoria_cliente_id','utility_id','emittente_soggetto_ruolo_id']`,
      `key_expressions=['COALESCE(classe_utenza_id, ''-1''::integer)']`,
      `constraint_name='ex_categ_cli_listini_no_overlap'`, `active=true`.
- [x] **2.9** `documenti.template_documenti_versioni` →
      `where_predicate='attivo IS TRUE AND (stato)::text = ''PUBBLICATA''::text'`,
      `constraint_name='ex_template_documenti_versioni_no_overlap_pubblicata'`,
      `active=true`.

### 4.3 Seed auto-detect — NON FATTO (scelta consapevole)

> **Decisione (2026-06-02): non implementato, di proposito.** Non è un TODO
> dimenticato. Estendere `fn_seed_automazione_overlap` per *dedurre*
> `where_predicate`/`key_expressions` dagli EXCLUDE esistenti richiederebbe di
> **parsare** `pg_get_constraintdef` (testo SQL) — fragile e a basso valore:
> - la registrazione esplicita (§4.2, migration `20260602-10`) copre **già** tutti
>   e 6 i vincoli in modo affidabile e leggibile;
> - i predicati/espressioni sono **business logic** (`NOT is_abortito_snapshot`,
>   `COALESCE(...)`): è più sicuro dichiararli a mano in una migration rivista da un
>   DBA che farli "indovinare" a un parser;
> - rischio sproporzionato (un parser sbagliato genererebbe vincoli errati) per un
>   beneficio minimo (evitare poche righe di config su tabelle nuove).
>
> **Quando riprenderlo:** solo se in futuro nascono *molte* tabelle versionate
> parziali e la registrazione manuale diventa un costo reale. Fino ad allora, una
> nuova tabella si aggiunge con una riga in `dbops.automazione_overlap` (vedi §4.2).
>
> *(Gli step 2.10 e 2.11 sotto sono marcati `[~]` = non fatti di proposito.)*

- [~] **2.10** *(non fatto, vedi sopra)* estendere `fn_seed_automazione_overlap`
      per catturare `where_predicate`/`key_expressions` dagli EXCLUDE esistenti.
- [~] **2.11** *(non fatto, dipende da 2.10)* strategia re-seed: non sovrascrivere
      `where_predicate`/`key_expressions`/`active` impostati a mano.

### 4.4 Validazione e anti-regressione permanente

- [x] **2.12** Prova **drop→riapply** su `promo_articoli` (transazione + ROLLBACK,
      su config applicata): `DROP CONSTRAINT` → ASSENTE → `fn_apply('SCHEDULED',
      false)` → ricreato **identico** (`EXCLUDE ... (articolo_id WITH =, uom_id
      WITH =, validita WITH &&) WHERE (attivo IS TRUE)`). Auto-guarigione provata.
- [x] **2.13** **Runner schedulato OVERLAP** (la lacuna: overlap aveva seed+apply
      ma nessun job, a differenza degli altri 5 rule). Generato:
      - **`20_code/maintenance/20260602-11`** `proc_automations_overlap_job` →
        `fn_apply_automazione_overlap('SCHEDULED', false)` con `fn_run_and_log`
        (logging+lock), allineato agli altri wrapper;
      - **`85_pgagent/20260602-12`** job `automations_overlap` su schedule
        `daily_21` (21:00), che `CALL`a il proc. Non tocca il job esistente
        (`20250825-02`), ne crea uno separato.
      **Validato** in transazione (proc creato, job/step/schedule corretti, rollback
      pulito). Da applicare. Post-apply: ogni notte `fn_apply` ricrea gli EXCLUDE
      mancanti delle righe `active=true` (idempotente → di norma nessuna modifica).
      Verifica post-apply: `fn_apply('AUTO', false)` salta tutti i 6.
- [x] **2.14** Test pgTAP →
      **`db/pgtap/dbops/test-anti-overlap-enforcement-gate-v1.sql`** (4 test):
      ogni `constraint_name` attivo è `contype='x'`; **nessun** `ex_*_no_overlap`
      è un indice-civetta; i 2 temporal UNIQUE restano `contype='u'`. **Verde su dev.**
- [x] **2.15** Doc aggiornati: `refactor-overlap.md §5` (follow-up risolti) +
      banner `piano-miglioramenti-db-pg18.md` (✅ risolto, governato dal framework) +
      **dbzero** (`fn_apply_automazione_overlap` con `key_expressions`, tabella
      `automazione_overlap`, **manual + funzioni** per `proc_automations_overlap_job`) +
      **guida `automazione-db.md §4.3`** (`where_predicate`, `key_expressions`,
      runner schedulato, auto-guarigione).

---

## 5. Ordine di esecuzione e punti di commit

```text
FASE 1 (sicura, zero impatto runtime)
  1.1 colonna → 1.2 funzione → 1.3 pgTAP → 1.4 dry-run → 1.5 doc      [COMMIT]

FASE 2 (governance, opzionale ma consigliata)
  4.1 core opz.A:  2.1 colonna key_expressions → 2.2 fn_apply → 2.3 pgTAP
  4.2 config:      2.4..2.9 registra i 6 (active=true)
  4.3 seed (opz.): 2.10 autodetect → 2.11 strategia re-seed
  4.4 verifica:    2.12 drop/apply → 2.13 apply+pipeline → 2.14 pgTAP → 2.15 doc  [COMMIT]
```

Le due fasi sono **indipendenti**: la Fase 1 ha valore da sola (sblocca i parziali
per ogni tabella futura). La Fase 2 è la migrazione dei vincoli esistenti sotto il
framework e si può fare in un secondo momento.

---

## 6. Rischi e cose da NON dimenticare

- `where_predicate` è DDL di fiducia: **niente input utente**, solo DBA. Documentare.
- Cambiare un predicato = drop manuale + riapply (no ALTER). Documentare.
- Chiavi su **espressione** (`COALESCE`) → gestite via colonna `key_expressions`
  (opzione A esplicita, §4.1): DDL di fiducia, non validabile, DBA-only.
- L'anti-regressione richiede che `fn_apply` venga invocato: **risolto** col runner
  schedulato `automations_overlap` (proc `20260602-11` + pgagent `20260602-12`,
  daily 21:00) — prima OVERLAP era l'unico rule senza job (2.13).
- Re-seed non deve azzerare `where_predicate`/`active` impostati a mano (2.2).
- Numerazione migration: sequenza **globale per data** (es. `20260603-01..NN`),
  un changeSet per file, `logicalFilePath`, mai modificare changelog già mergiati.
- Rigenerare `changelog-autogen.yaml` con `scripts/gen_master_autogen.py --strict`
  dopo aver aggiunto i file (lo fa anche il wrapper `liquibase5.sh`).
