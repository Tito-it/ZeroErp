## 📘 Documentazione Concettuale – Tabella `dbops.automazione_overlap`

> 👀 **Vedi anche**
>
Guide:
> [Automazione DB](/guide/automazione-db)
>
Approfondimento funzioni:
> [dbops.fn_seed_automazione_overlap](/dbzero/dbops/funzioni/fn_seed_automazione_overlap)
> [dbops.fn_apply_automazione_overlap](/dbzero/dbops/funzioni/fn_apply_automazione_overlap)
>
🎯 Scopo Principale

(latest review 19-01-26)
La tabella **`dbops.automazione_overlap`** centralizza la configurazione del controllo
**anti-overlap temporale** tramite vincoli `EXCLUDE USING gist` sulle tabelle versionate.

L'obiettivo e':

* censire automaticamente le tabelle con colonne periodo (`valido_dal/valido_al` o `valid_from/valid_to`);
* marcare con **`active=true`** solo le tabelle versionate (o gia' con exclude/index GiST);
* fornire tutti i parametri necessari per applicare il vincolo in modo uniforme.

---

### Campi chiave e semantica

* **`target_schema`** *(text)* – schema della tabella target.
* **`target_table`** *(text)* – nome tabella target.
* **`key_columns`** *(text[])* – colonne della chiave logica per cui l'overlap e' vietato.
* **`valido_dal_col`** *(text)* – nome colonna inizio validita (default `valido_dal`).
* **`valido_al_col`** *(text)* – nome colonna fine validita (default `valido_al`).
* **`range_bounds`** *(text)* – bounds della `daterange` (default `[]`).
* **`constraint_name`** *(text)* – nome vincolo `EXCLUDE` desiderato (opzionale).
* **`active`** *(boolean)* – se `true` la riga e' eleggibile all'applicazione.
* **`exec_mode`** *(text)* – `AUTO` | `CI` | `SCHEDULED`.
* **`note`** *(text)* – motivazione o esito del seed.
* **Audit** – `data_insert`, `user_insert`, `data_update`, `user_update`.

---

### Comportamento previsto

1. `fn_seed_automazione_overlap` popola la tabella rilevando:
   * presenza di colonne periodo (`valido_*` o `valid_*`);
   * vincoli `EXCLUDE` esistenti;
   * indici GiST con `daterange`;
   * vincoli UNIQUE/PK che includono il periodo.
2. Se il pattern indica versioning, imposta `active=true`; altrimenti `active=false`.
3. `fn_apply_automazione_overlap` crea i vincoli `EXCLUDE` solo sulle righe `active=true`.

---

### Esempi

**1) Seed automatico (tutte le tabelle nell'ambito):**

```sql
SELECT dbops.fn_seed_automazione_overlap();
```

**2) Forzare una riga (tabella versionata senza chiavi rilevate):**

```sql
UPDATE dbops.automazione_overlap
SET key_columns = ARRAY['billing_account_id','istanza_utility_id','utility_id','ambito'],
    active = true,
    note = 'chiavi impostate manualmente'
WHERE target_schema = 'vendite'
  AND target_table  = 'contratti';
```

---

### Note operative

* Le tabelle non versionate **devono restare `active=false`**.
* Se `key_columns` e' vuoto o le colonne non esistono, il vincolo non viene creato.
* Se la chiave contiene UUID, e' necessario `btree_gist` per l'EXCLUDE su GiST.

---

{% include-markdown "signature-core.md" %}

---
