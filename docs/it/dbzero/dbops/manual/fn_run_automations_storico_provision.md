## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_storico_provision`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — la regola `STORICO_PROVISION` e il suo parametro dell'indice GIN
> * [dbops.automation_overrides_cols](/dbzero/dbops/tabelle/automation_overrides_cols) — gli override `STORICIZZA_COL` e `STORICO_FK`
>
> Approfondimento funzioni:
>
> * [dbops.fn_ensure_storico_table](/dbzero/dbops/funzioni/fn_ensure_storico_table) — crea, arma e cede la shadow; qui c'è solo la scelta delle tabelle
> * [dbops.fn_run_automations_storico](/dbzero/dbops/funzioni/fn_run_automations_storico) — monta poi il trigger sulle tabelle che hanno la shadow
> * [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope) — l'ambito degli schemi
> * [dbops.fn_table_in_scope](/dbzero/dbops/funzioni/fn_table_in_scope) — il filtro per tabella
> * [dbops.fn_get_override_col](/dbzero/dbops/funzioni/fn_get_override_col) — i nomi delle due colonne
> * [dbops.fn_col_exists](/dbzero/dbops/funzioni/fn_col_exists) — la presenza della colonna `storicizza`
> * [maintenance.proc_automations_storico_provision_job](/dbzero/maintenance/funzioni/proc_automations_storico_provision_job) — il wrapper del job
>
> Guide:
>
> * [Storicizzazione delle tabelle](/guide/storicizzazione-tabelle) — il provisioning delle tabelle di storico

---

### 🎯 Scopo Principale

Crea la shadow `storico.<tabella>` di ogni tabella dell'ambito che ha la colonna `storicizza`,
delegando la creazione a `dbops.fn_ensure_storico_table`. È il primo dei due runner della
storicizzazione: prima la shadow, poi il trigger.

La funzione sceglie solo **dove**: la struttura della shadow, l'armatura dello scope, la cessione
al proprietario e la gestione degli errori stanno tutte nella funzione che chiama.

---

### Su quali tabelle

Le tabelle ordinarie degli schemi dell'ambito, tolto `storico`, che passano il filtro per tabella.
Per ciascuna valgono le regole `STORICO_PROVISION` attive del registro il cui bersaglio la comprende
e il cui modo di esecuzione è `AUTO` o quello della corsa. Il confronto sul tipo di regola e sul modo
di esecuzione è letterale, maiuscole comprese.

Per ogni tabella e regola:

1. **la colonna `storicizza` deve esserci**: il nome si legge dall'override `STORICIZZA_COL`,
   altrimenti è `storicizza`. Una tabella senza la colonna si salta in silenzio;
2. **il nome della colonna di legame** è l'override `STORICO_FK`, altrimenti `<tabella>_id`: è lo
   stesso calcolo dell'altro runner, che lo passerà al trigger;
3. **l'indice GIN sullo snapshot** si crea se il parametro `create_gin_index` della regola è vero
   (nel seed è falso).

⚠️ Conta la **presenza** della colonna, non il suo default né i valori: una tabella con
`storicizza` riceve la shadow anche se le sue righe nascono non storicizzate.

---

### Che cosa non fa

* Non aggiorna una shadow che esiste già: se `storico.<tabella>` c'è, la funzione che chiama esce
  senza toccarla. L'armatura delle shadow esistenti la fa la convergenza dello scope.
* Non monta il trigger: lo fa `fn_run_automations_storico`.
* Non scrive niente di suo nell'audit: le righe di creazione, simulazione e cessione sono della
  funzione chiamata, registrate sotto il nome di questo runner.

---

### Chi la chiama

Il job pgAgent tramite il suo wrapper, la convergenza dei processi strutturali e la passata
`ci_apply`, sempre prima del runner che monta il trigger.

---

### Codici errore

Non ne solleva di suoi. Escono da qui i codici di `fn_ensure_storico_table`:
`E_STORICO_PARENT_PK_NOT_FOUND` e `E_STORICO_PROVISION`. Il primo errore ferma la corsa: le tabelle
successive restano senza shadow fino al giro dopo.

---

### Test

Nessun pgTAP chiama il runner. La forma delle shadow che produce la provano i test di
`fn_ensure_storico_table`.

---

{% include-markdown "signature-core.md" %}
