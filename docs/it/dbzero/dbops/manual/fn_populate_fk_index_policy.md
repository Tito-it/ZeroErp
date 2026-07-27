## 📘 Documentazione Concettuale – Funzione `dbops.fn_populate_fk_index_policy()`

> 👀 **Vedi anche**
>
Approfondimento Tabelle:  
>
[dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy)  
>
Approfondimento view:  
>
[dbops.vw_fk_senza_indice](/dbzero/dbops/views/vw_fk_senza_indice)  
> [dbops.fn_seed_fk_index_policy](/dbzero/dbops/funzioni/fn_seed_fk_index_policy)  
> [dbops.apply_fk_index_policy](/dbzero/dbops/funzioni/apply_fk_index_policy)  

La funzione **`dbops.fn_populate_fk_index_policy()`** esegue il popolamento automatico di `dbops.fk_index_policy` aggiungendo tutte le foreign key presenti in `dbops.vw_fk_senza_indice` che non hanno ancora un record in policy, impostando per ciascuna `consentito = false`.

---
### 🎯 Scopo Principale
(latest review 27-07-26)

* **Coerenza iniziale**
  Garantire che ogni FK rilevata senza copertura abbia la propria entry di policy, evitando omissioni.
* **Popolamento “a freddo”**
  Tutti i nuovi record vengono creati con `consentito = false`, lasciando in carico all'operatore la decisione di abilitare o meno l'indice.
* **Automazione**
  Riduce il lavoro manuale di inserimento di policy per nuove FK.

---

### ⚠️ La policy è OPT-IN, e questa funzione da sola non crea nulla

È il fraintendimento più costoso. `fn_populate_fk_index_policy()` **registra** la FK, non la indicizza: la riga nasce a `consentito = false`, e finché resta così `apply_fk_index_policy()` non crea nessun indice — anzi, esegue un `DROP INDEX IF EXISTS` sul nome previsto.

Perché l'indice nasca serve un **seed esplicito** che porti il flag a `true`, in `80_data`, come CSV più `loadUpdateData`.

> Su una tabella nuova, quindi, l'automazione da sola **non** produce gli indici FK. Chi crea la tabella deve prevedere il seed dei flag.

---

### 🔑 Cosa significa "senza indice"

Questa funzione non decide nulla: si limita a leggere `dbops.vw_fk_senza_indice`, che è dove vive la definizione di **copertura**. In sintesi, la FK è coperta se le sue colonne coincidono, come insieme, con le prime N colonne chiave di un btree valido, il cui predicato sia assente oppure una congiunzione di soli `<colonna della FK> IS NOT NULL`.

Il dettaglio, e il motivo per cui la regola è cambiata il 27-07-2026, stanno nella [documentazione della view](/dbzero/dbops/views/vw_fk_senza_indice).

Conseguenza pratica: **una FK già servita da una `UNIQUE` più larga non viene più registrata**. Prima lo era, e l'automazione ci piantava sopra un indice gemello.

---

### Flusso Logico

1. **Lettura FK senza copertura**
   Seleziona da `dbops.vw_fk_senza_indice` tutte le tuple `(schema_name, table_name, constraint_name)` non ancora presenti in `dbops.fk_index_policy`.
2. **Inserimento in `fk_index_policy`**
   Per ciascuna riga inserisce `schema_name`, `table_name`, `constraint_name`, `consentito = false` e il `dll_command` preso da `create_index_suggestion`.

> La definizione SQL corrente è riportata per intero nella sezione auto-generata qui sotto: **fa fede quella**, non una copia in questa pagina.

---

### Utilizzo

Essendo una **funzione** che restituisce `void`, puoi eseguirla direttamente con:

```sql
SELECT dbops.fn_populate_fk_index_policy();
```

In alternativa, in un contesto PL/pgSQL o in un DO block:

```plpgsql
DO $$
BEGIN
  PERFORM dbops.fn_populate_fk_index_policy();
END;
$$;
```

> **Nota:** non usare `SELECT * FROM dbops.fn_populate_fk_index_policy()`, poiché la funzione non restituisce righe tabellari.

È invocata automaticamente dal job pgAgent settimanale, tramite `maintenance.proc_apply_fk_index_policy_job(true)`, subito prima di `apply_fk_index_policy()`.

---

### Vantaggi Operativi

* **Nessuna FK dimenticata**: ogni vincolo senza copertura finisce in policy e diventa una decisione esplicita.
* **Nessun indice a sorpresa**: il default `false` fa sì che nulla venga creato senza che qualcuno lo abbia voluto.
* **Idempotenza**: rieseguirla non duplica righe né sovrascrive decisioni già prese.

---

> **“Esegui la funzione con `SELECT` o `PERFORM`: non è necessario usare `SELECT * FROM`.”**
