## 📚 Documentazione Tabella: `config.storico_set_storicizza`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche:**
>
Guide :
>
[Storicizzazione Tabelle](/guide/storicizzazione-tabelle)
>
Approfondimento funzioni:
>
[dbops.proc_sync_storico_set_storicizza](/dbzero/maintenance/funzioni/proc_sync_storico_set_storicizza)
> [maintenance.fn_apply_storicizza_defaults](/dbzero/maintenance/funzioni/fn_apply_storicizza_defaults)
> [maintenance.proc_apply_storicizza_defaults_job](/dbzero/maintenance/funzioni/proc_apply_storicizza_defaults_job) *(job pgAgent che richiama la procedura)*
> [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log)

---
### 🎯 Scopo Principale
`config.storico_set_storicizza` è la **tabella di configurazione** che elenca le tabelle per le quali lo **storico dei dati** deve essere abilitato **in modo predefinito**.
Le tabelle presenti qui hanno la colonna `storicizza` con **default TRUE**: ciò garantisce che **ogni nuova riga** venga automaticamente marcata per la storicizzazione (snapshot su UPDATE/DELETE e protezione dal reset a FALSE a cura dei trigger).


---

### Flusso Operativo (con le procedure collegate)

1. **Sincronizzazione automatica** — `dbops.proc_sync_storico_set_storicizza()`

   * Scansiona il catalogo PostgreSQL e **rileva** tutte le tabelle che hanno la colonna `storicizza` con **default `true`**.
   * Inserisce (se mancanti) i relativi nomi in `config.storico_set_storicizza` con `insert_manuale = FALSE`.

2. **Applicazione dei default** — `dbops.apply_storicizza_defaults()`

   * Legge l’elenco da `config.storico_set_storicizza` e imposta/forza il **default `TRUE`** della colonna `storicizza` su ciascuna tabella elencata.
   * Usata per **riallineare** lo schema quando cambiano le decisioni di storicizzazione o dopo deploy/migrazioni.

3. **Schedulazione** (opzionale ma consigliata)

   * Un job (es. via pgAgent) può invocare periodicamente le procedure per **mantenere allineata** la configurazione allo stato reale delle tabelle.

---

### Vincoli e Regole

* **PK**: `storico_set_storicizza_pkey` sulla colonna `table_name` assicura **unicità** per tabella.
* **`insert_manuale`**:

  * `TRUE` → la riga è stata **inserita manualmente** dall’operatore.
  * `FALSE` → la riga è stata **inserita automaticamente** da procedure/trigger di sincronizzazione.
* **Audit di base**: `data_insert` (timestamp), `user_insert` (utente applicativo o DB che ha effettuato l’inserimento).

---

### Considerazioni di Progettazione

* La configurazione qui presente è **declarativa**: evita la dispersione di logiche per tabella, centralizzando la scelta su *quali tabelle storicizzare*.
* La coppia di procedure consente sia la **rilevazione** (sync) sia la **forzatura** (apply) del default `TRUE` sulla colonna `storicizza` per tutte le tabelle interessate.
* Il flag `insert_manuale` permette di distinguere le scelte **operative** da quelle **derivate** automaticamente, utile per audit e manutenzione.

---

### Esempi d’Uso

**Aggiungere manualmente una tabella alla lista**

```sql
INSERT INTO config.storico_set_storicizza(table_name, insert_manuale)
VALUES ('anagrafiche.soggetti', TRUE)
ON CONFLICT (table_name) DO NOTHING;
```

**Allineare i default di storicizzazione in base alla configurazione**

```sql
CALL dbops.apply_storicizza_defaults();
```

**Sincronizzare la configurazione dalle tabelle che hanno già il default TRUE**

```sql
CALL dbops.proc_sync_storico_set_storicizza();
```

---

### Manutenzione & Best Practice

* Eseguire periodicamente `proc_sync_storico_set_storicizza` per **intercettare** nuove tabelle con `storicizza DEFAULT TRUE` create da migrazioni recenti.
* Dopo cambiamenti strutturali o decisioni architetturali, usare `apply_storicizza_defaults` per **forzare l’allineamento** dello schema.
* In fase di audit, filtrare per `insert_manuale = TRUE` per distinguere le scelte **esplicite** degli operatori.

---

> **Nota**: questa tabella **non abilita da sola** i trigger di storicizzazione; definisce *solo* l’impostazione predefinita della colonna `storicizza`. I trigger devono essere presenti e configurati nelle singole tabelle per registrare gli snapshot.

---

{% include-markdown "signature-core.md" %}
