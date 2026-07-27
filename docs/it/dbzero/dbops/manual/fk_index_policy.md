## 📚 Documentazione concettuale - Tabella `dbops.fk_index_policy`
### 🎯 Scopo Principale
(latest review 27-07-26)
La tabella **`dbops.fk_index_policy`** definisce una **policy centralizzata** per la gestione degli indici sulle foreign key: una riga per vincolo, un flag che dice se l'indice deve esistere, e il comando che lo crea.

È l'unico posto da cui gli indici FK devono nascere e morire. Chi li crea o li droppa a mano si trova l'automazione che disfa il lavoro al `migrate` successivo.

---

### 🔑 Le colonne che contano

| Colonna | Cosa contiene |
| --- | --- |
| `schema_name`, `table_name`, `constraint_name` | Chiave primaria: identificano il vincolo FK |
| `consentito` | `true` = l'indice deve esistere, `false` = deve **non** esistere |
| `dll_command` | Il DDL **eseguibile** che crea l'indice |
| `generated_by_script` | `true` se la riga nasce da `fn_seed_fk_index_policy()` |

> ⚠️ **`dll_command` non è un campo note.** Contiene SQL che `apply_fk_index_policy()` esegue alla lettera con `EXECUTE`, e da cui estrae il nome dell'indice — il **sesto token** — per il `DROP`. Una descrizione in italiano al suo posto produce, con `consentito = true`, un errore di sintassi a ogni `migrate`.
>
> Per lo stesso motivo **non lasciare mai `dll_command` a NULL**: `format('%I', NULL)` solleva *«i valori vuoti non possono essere formattati come un identificativo SQL»*, e poiché `apply_fk_index_policy()` gira `runAlways` in `90_end`, **ogni deploy si bloccherebbe**.

Perché il sesto token corrisponda al nome, il comando deve avere questa forma esatta:

```text
CREATE  INDEX  IF  NOT  EXISTS  <nome_indice>  ON  <schema>.<tabella>(<colonne>);
   1      2     3   4     5          6
```

---

### ⚖️ La policy è OPT-IN

`fn_populate_fk_index_policy()` registra le FK nuove con `consentito = false`. **Perché l'indice nasca serve un seed esplicito** che porti il flag a `true`: senza, l'automazione non crea nulla.

Su una tabella nuova, quindi, l'automazione da sola non produce gli indici FK: chi crea la tabella deve prevedere il seed.

---

### Vincoli

| Tipo | Nome | Colonne | Descrizione |
| --- | --- | --- | --- |
| PRIMARY KEY | `fk_index_policy_pkey` | `schema_name, table_name, constraint_name` | Chiave primaria composita per identificare univocamente la policy. |

---

### Uso e Casi d'Oro

* **Controllo centralizzato**: gestire in un unico punto l'abilitazione o meno degli indici sui vincoli referenziali, evitando di creare indici non necessari o ridondanti.
* **Ottimizzazione delle performance**: disabilitare indici su FK già coperte da una UNIQUE più larga per ridurre overhead in scrittura, o abilitarli su FK critiche per migliorare join e `DELETE` a cascata.
* **Bonifica reversibile**: portando a `false` una riga, l'indice viene rimosso ma il `dll_command` resta. Se un domani la UNIQUE coprente sparisse, basta rimettere `true` e l'indice torna, con lo stesso nome di prima.
* **Guardia permanente**: con `consentito = false` l'automazione **ridroppa** l'indice se qualcuno lo ricrea fuori Liquibase.
* **Integrazione con script di DBOps**: [apply_fk_index_policy](/dbzero/dbops/funzioni/apply_fk_index_policy) legge questa tabella a ogni `migrate` e nel job settimanale.

---

### Come si modifica

**In un changeSet, con CSV più `loadUpdateData`** — la forma usata da tutti i seed di questa tabella. La chiave primaria è `schema_name,table_name,constraint_name`, quindi la stessa riga aggiorna o inserisce:

```csv
schema_name,table_name,constraint_name,consentito,dll_command,generated_by_script,user_insert,data_insert
anagrafiche,soggetti_ruoli,fk_soggetti_anagrafiche,false,CREATE INDEX IF NOT EXISTS ix_anagrafiche_soggetti_ruoli_soggetto_id ON anagrafiche.soggetti_ruoli(soggetto_id);,true,titodb,2026-01-16 11:59:34+01
```

```yaml
- loadUpdateData:
    relativeToChangelogFile: true
    file: ../sql/dbops/fk_index_policy_<descrizione>.csv
    tableName: fk_index_policy
    schemaName: dbops
    primaryKey: "schema_name,table_name,constraint_name"
```

> Nota su questa riga reale: la FK `fk_soggetti_anagrafiche` su `anagrafiche.soggetti_ruoli` è a `false` perché già coperta per prefisso da `uq_soggetto_ruolo`. Il `dll_command` resta valorizzato — è ciò che rende la decisione reversibile.

---

### Esempi di Utilizzo

1. **Vedere cosa l'automazione farebbe**

   ```sql
   SELECT schema_name, table_name, constraint_name, consentito, dll_command
   FROM dbops.fk_index_policy
   WHERE schema_name = 'vendite'
   ORDER BY table_name, constraint_name;
   ```

2. **Trovare le righe che stanno mantenendo in vita un indice ridondante**

   ```sql
   SELECT * FROM dbops.vw_indici_ridondanti_prefisso
   WHERE origine = 'AUTOMAZIONE_FK';
   ```

   La colonna `policy_constraint_name` indica la riga da portare a `false`.

3. **Applicare la policy**

   ```sql
   CALL dbops.apply_fk_index_policy();
   ```

   > Non scrivere script `DO $$ ... $$` che ricostruiscono la logica di applicazione: la procedura ufficiale contiene due guardie — non crea ciò che è già coperto, non droppa ciò che sostiene un vincolo — che una copia artigianale non avrebbe.

---

### 💡 Miglioramento suggerito, non ancora implementato

`dll_command` è **nullable** e senza `CHECK` di forma. Una riga inserita a mano senza comando, o con un testo libero, rompe `apply_fk_index_policy()` a ogni `migrate`. Un `NOT NULL` più un `CHECK (dll_command ~ '^CREATE INDEX IF NOT EXISTS ')` renderebbe impossibile l'errore all'origine, invece di lasciarlo emergere in fase di deploy.

---

> **“Utilizzare `fk_index_policy` consente di adattare dinamicamente la presenza di indici su foreign key per ottimizzare scritture e letture, centralizzando le decisioni e mantenendo tracciabilità.”**
