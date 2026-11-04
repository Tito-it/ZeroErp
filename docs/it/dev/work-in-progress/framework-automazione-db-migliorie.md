# WIP – Framework Automazione DB: migliorie e implementazioni proposte

> (creato 02-03-26)
>
> Questo documento raccoglie le modifiche, migliorie e implementazioni proposte per il framework di automazione DB, emerse dall'analisi critica della documentazione e del codice.

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

### 1.3 Miglioramenti futuri alla documentazione

- [ ] **Checklist standalone**: estrarre la checklist operativa in un documento separato (es. `docs/it/guide/automazione-db-checklist.md`) per chi la stampa e la usa in deploy
- [ ] **Diagramma flowchart dettagliato**: il diagramma Mermaid attuale e semplificato; valutare un diagramma piu dettagliato che mostri le interazioni tra i runner specifici
- [ ] **Documentazione per runner**: una scheda tecnica per ciascun orchestratore con parametri, output e casi limite
- [ ] **Indice tutorial**: creare un `docs/it/tutorial/index.md` man mano che si aggiungono altri tutorial

---

## 2. Codice e implementazione

### 2.1 Funzione `fn_populate_fk_index_policy` – chiarire il naming

La guida originale listava `fn_populate_fk_index_policy` due volte con descrizioni diverse:

1. "registra in policy le FK senza indice" → **questo e il ruolo reale della funzione**
2. "crea/rimuove indici in base alla policy" → **questo e il ruolo di `apply_fk_index_policy`**

**Azione proposta:** verificare che nella documentazione auto-generata in `dbzero/dbops/funzioni/` la descrizione di `fn_populate_fk_index_policy` sia coerente e non confondibile con `apply_fk_index_policy`. Se la funzione fa entrambe le cose, considerare lo split in due funzioni con nomi espliciti.

**Stato:** la guida e stata corretta; verificare il codice SQL.

### 2.2 Recovery da esecuzione parziale del runner

Attualmente se un runner fallisce a meta esecuzione, i trigger gia creati restano in piedi. L'idempotenza del framework mitiga il problema (rieseguire e sicuro), ma manca un meccanismo di:

- [ ] **Rollback esplicito**: una funzione che, dato un `execution_id` da `audit_log`, rimuova tutti i trigger creati in quella esecuzione
- [ ] **Resume**: un parametro `p_resume_from` che salti le tabelle gia processate con successo

**Priorita:** bassa — il workaround (fix + riesegui) funziona bene nella pratica.

### 2.3 Conflitto trigger manuali vs generati

Non esiste un meccanismo automatico per rilevare trigger manuali che fanno la stessa cosa dei trigger generati. Questo puo portare a doppia esecuzione.

**Azione proposta:**

- [ ] Aggiungere al dry-run un warning quando rileva un trigger manuale con nome simile a quello che starebbe per generare
- [ ] Oppure: una view/funzione di diagnostica `dbops.fn_check_trigger_conflicts(schema, table)` che elenchi i potenziali conflitti

**Priorita:** media — diventa importante quando il team cresce.

### 2.4 Validazione ambito vs rules al momento dell'insert

Attualmente e possibile inserire una regola con `target_schema='vendite'` anche se `vendite` non rientra nell'ambito. La regola semplicemente non viene applicata, ma questo puo confondere.

**Azione proposta:**

- [ ] Aggiungere un trigger di validazione su `automation_rules_tbl` che emetta un WARNING (non un errore) se il `target_schema` non e presente nell'ambito
- [ ] Lo stesso vale per `dbops.automation_delete_block` (aggiunta del 2026-11-04, `brief-db-revisione-dbops` D41):
  una riga su una tabella fuori ambito viene ignorata da `fn_run_automations_delete_block` senza nessuna
  traccia, mentre una tabella in ambito ma sparita lascia un `WARN TABLE_NOT_FOUND`. La validazione va
  fatta qui, sull'ambito, e non nel runner.

**Priorita:** bassa — utile per developer experience ma non critico.

---

## 3. Funzionalita mancanti

### 3.1 Report stato automazioni

Manca una view sintetica che mostri per ogni tabella nell'ambito quali automazioni sono attive e quali no.

**Proposta:**

- [ ] Creare `dbops.vw_automazioni_stato` con colonne: `schema`, `table`, `has_tx_id`, `has_audit`, `has_storico`, `has_lock_columns`, `has_attivo`, `last_apply_date`

**Priorita:** media — molto utile per onboarding e audit periodici.

### 3.2 Dashboard audit

L'`audit_log` contiene dati preziosi ma non e facilmente consultabile per trend.

**Proposta:**

- [ ] View `dbops.vw_audit_summary` con conteggi per status, rule_type, periodo
- [ ] View `dbops.vw_audit_errors_recent` con gli ultimi N errori con context

**Priorita:** bassa — utile per monitoring ma non bloccante.

### 3.3 Test pgTAP per le automazioni

Non ci sono test automatizzati che verifichino il comportamento del framework su una tabella di esempio.

**Proposta:**

- [ ] Creare `db/pgtap/dbops/test_automazioni_framework.sql` con:
    - Test dry-run su tabella di laboratorio
    - Test apply + verifica trigger esistenti
    - Test idempotenza (apply due volte = stesso risultato)
    - Test rollback ambito (tabella fuori ambito non viene toccata)

**Priorita:** alta — fondamentale per evitare regressioni.

---

## 4. Priorita riepilogo

| Miglioria | Priorita | Tipo |
| --- | --- | --- |
| Test pgTAP per automazioni | Alta | Codice |
| Report stato automazioni (view) | Media | Codice |
| Rilevamento conflitti trigger | Media | Codice |
| Checklist standalone | Bassa | Documentazione |
| Recovery da esecuzione parziale | Bassa | Codice |
| Dashboard audit (view) | Bassa | Codice |
| Validazione ambito vs rules | Bassa | Codice |
| Documentazione per singolo runner | Bassa | Documentazione |
