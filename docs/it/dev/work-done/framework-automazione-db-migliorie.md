# Framework Automazione DB: migliorie e implementazioni proposte (archiviato)

## ⏭️ Chi riparte — aggiornato al 2026-11-13

**Riparte: nessuno.** Il brief è archiviato: le voci sono chiuse, superate dal modello della convergenza, o scartate da Tid
(2026-11-13). L'ultimo residuo (§2.4, la riga di `automation_delete_block` fuori ambito) è stato chiuso nello stesso giro
dell'archiviazione.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione DB | Riverifica voce per voce contro lo stato del 2026-11-13 | §5 | — |
| 2 | ✅ Tid | Scartati i punti facoltativi (§1.3, §3.1, §3.2, il WARNING su `target_schema` di §2.4); unico residuo da chiudere: §2.4 delete_block | §5 | 1 |
| 3 | ✅ sessione DB | Presidio della riga attiva fuori ambito (test 3 e 18 di `test-delete-block-convergenza-v1`), guida §4.4 e pagine `manual/` | §2.4 | 2 |
| 4 | Tid | Esecuzione del pgTAP modificato e commit | `db/pgtap/dbops/test-delete-block-convergenza-v1.sql` | 3 |

**Decisioni aperte di Tid:** il residuo `ILIKE r.target_table` (§2.4): brief nuovo o chiuso subito.
**Da committare:** il giro del 2026-11-13 (test, guida, due pagine `manual/`, questo spostamento e i link).

> (creato 02-03-26)
>
> Questo documento raccoglieva le modifiche, migliorie e implementazioni proposte per il framework di automazione DB,
> emerse dall'analisi critica della documentazione e del codice. Gran parte delle voci di codice le ha poi assorbite
> [brief-db-revisione-dbops](brief-db-revisione-dbops.md) (archiviato), che ha portato i runner al modello della
> convergenza.

---

## 1. Documentazione

### 1.1 Guida riscritta (completato)

La guida `docs/it/guide/automazione-db.md` e stata riscritta con:

- [x] Flusso narrativo: problema → modello → flusso → regole → esempi
- [x] Numerazione corretta delle sezioni (1-9 + checklist)
- [x] Separazione regole **core** e **specializzate**
- [x] Descrizioni leggibili per non-tecnici in ogni sezione
- [x] Relazione ambito/rules esplicitata (precedenza chiara)
- [x] Diagrammi Mermaid: flusso esecuzione + ER tabelle configurazione
- [x] Sezione troubleshooting
- [x] Checklist operativa integrata ma chiaramente separata
- [x] Tabella di riferimento rapido per tutte le tabelle coinvolte
- [x] Correzione duplicazione `fn_populate_fk_index_policy` (ora seed/populate/apply separati)

### 1.2 Tutorial creato (completato)

Creato `docs/it/tutorial/aggiungere-tabella-al-framework.md`:

- [x] Guida step-by-step per portare una nuova tabella nel framework
- [x] Scenario di esempio concreto (tabella `catalogo.categorie_materiali`)
- [x] Sezione errori comuni e soluzioni
- [x] 7 passi dall'inizio alla fine (5 obbligatori + 2 opzionali)

---

## 2. Codice e implementazione

### 2.1 Funzione `fn_populate_fk_index_policy` – chiarire il naming ✅

La guida originale listava `fn_populate_fk_index_policy` due volte con descrizioni diverse: il ruolo reale (registrare
in policy le FK senza indice) e quello di `apply_fk_index_policy` (creare o togliere gli indici).

✅ Chiusa da `brief-db-revisione-dbops` §29 (giro 10d, 2026-11-10): COMMENT e pagina riscritti, e la politica delle FK
ha la colonna `decisione` (`20261110-42`, `20261110-47`).

### 2.2 Recovery da esecuzione parziale del runner

⚠️ **Superata dal modello della convergenza** (`brief-db-revisione-dbops`, giri 10b-10d). La proposta era un rollback per
`execution_id` e un parametro `p_resume_from`. Oggi ogni runner confronta i trigger vivi con quelli dichiarati nel
registro e li porta lì (crea, rigenera, toglie): un giro interrotto si recupera rilanciandolo, e uno stato parziale è
solo una divergenza che il giro dopo chiude.

### 2.3 Conflitto trigger manuali vs generati

⚠️ **Superata dai giri di convergenza.** La proposta era un warning nel dry run o una funzione di diagnostica. Oggi un
trigger si riconosce dalla funzione che esegue, non dal nome; un trigger della funzione che il registro non conosce
ferma il runner (SCONOSCIUTO), e i presidi lo vedono: `test-delete-block-convergenza-v1`,
`test-lock-columns-convergenza`, `test-guard-utility-convergenza-v1`, `test-trigger-attivo-orfani-v1`,
`test-vw-bersagli-non-dichiarati`.

### 2.4 Validazione del registro

- ✅ **Vocabolari del registro (D17-bis)**: `rule_type`, `exec_mode` e `col_role` sono vocabolari chiusi, con CHECK
  (`brief-db-revisione-dbops`, giro 10b; `test-registro-regole-vincoli-v1`).
- ✅ **`fn_name_from_template` non idempotente** (lì §28.6 punto 1, indirizzato qui): reso idempotente nel blocco 10c-4,
  col censimento dei nomi vivi (2026-11-09).
- ✅ **Una riga di `dbops.automation_delete_block` su una tabella fuori ambito** (aggiunta del 2026-11-04,
  `brief-db-revisione-dbops` D41): `fn_run_automations_delete_block` la saltava senza traccia, e la tabella restava
  cancellabile mentre il registro la dichiarava protetta: una promessa senza esecutore, come N5 per i lock. Chiusa il
  2026-11-13 col presidio a due metà di `test-delete-block-convergenza-v1`: il test 2 (già c'era) vieta un blocco vivo
  fuori ambito, il test 3 (nuovo) una riga accesa fuori ambito; il test 18 prova che il presidio la vede. A differenza
  dei lock, fuori ambito non c'è il trigger montato da una migrazione: la tabella entra nell'ambito, o la riga resta
  spenta (guida `automazione-db.md` §4.4, pagina `manual/` di `automation_delete_block`). Fatto datato: su scratch e
  dbdev, il 2026-11-13, le otto righe accese erano tutte in ambito.
- ⏳ **`ILIKE r.target_table`** (residuo di `brief-db-revisione-dbops` §27.8, indirizzato qui): `target_table` è un modello
  LIKE, e `_` vi fa da jolly, quindi una regola su `event_log` copre anche una `eventXlog`. Sta in
  `dbops.fn_cleanup_at_regola` e nel ciclo del purge di `fn_run_automations_cleanup`. Non toccato perché cambia il
  significato di ogni regola del registro. **Decide Tid**: brief nuovo o chiuso subito.

---

## 3. Funzionalità mancanti

### 3.3 Test pgTAP per le automazioni ✅

La proposta era un `test_automazioni_framework.sql` con dry run, apply, idempotenza e ambito. ✅ Coperta, per runner, dai
pgTAP di `db/pgtap/dbops/` nati con `brief-db-revisione-dbops`: convergenza (`test-*-convergenza*`), dry run e audit
(`test-delete-block-audit-v1`, `test-cleanup-framework`), tabelle sparite (`test-overlap-tabella-sparita-v1`), ambito
(i presidi fuori ambito dei test di convergenza).

---

## 4. Vicoli ciechi

- **Rollback per `execution_id`** (§2.2): avrebbe tolto i trigger di un giro, ma un trigger non dice da quale giro è
  nato; con la convergenza non serve.
- **Riconoscere un trigger manuale dal nome simile** (§2.3): il nome non dice cosa fa un trigger; il criterio giusto è la
  funzione che esegue, e su quello si sono costruiti i presidi.

---

## 5. Riverifica del 2026-11-13

Ogni voce confrontata con il codice, i pgTAP e i brief archiviati. Le voci facoltative scartate da Tid il 2026-11-13 sono
state tolte dal documento.
