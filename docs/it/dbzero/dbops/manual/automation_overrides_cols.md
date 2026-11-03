## 📘 Documentazione Concettuale – Tabella `dbops.automation_overrides_cols`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
Approfondimento funzioni: 
> [dbops.fn_run_automations](/dbzero/dbops/funzioni/fn_run_automations)
> [dbops.fn_get_override_col](/dbzero/dbops/funzioni/fn_get_override_col)

> Esempio Helper: [dbops.fn_get_override_col(schema, table, key, default)]
### 🎯 Scopo Principale
Centralizzare le **eccezioni di naming delle colonne** usate dagli automatismi (audit, soft‑delete, storico, ecc.).
Quando il tuo schema usa nomi diversi dagli standard (es. `attivo` → `is_enabled`, `data_update` → `modified_at`), qui definisci l’override **per tabella**.

---

### Come funziona (lookup & precedenze)

Gli automatismi risolvono il nome della colonna così:

1. **Override tabellare** da `automation_overrides_cols` (match esatto su `target_schema` + `target_table` + `key`).
2. **Parametro di regola** (es. `automation_rules_tbl.params` → `audit_ts`, `audit_user`).
3. **Default di framework** (es. `attivo`, `data_update`, `user_update`, `<table>_id`).

L’helper `fn_get_override_col(schema, table, key, default)` incapsula questa logica e restituisce il valore finale.

> *Match*: `target_table` è normalmente un nome esatto; opzionalmente puoi usare pattern (LIKE), ma in tal caso gestisci **priorità** per evitare sorprese.

---

### Chiavi supportate (key)

* **`ATTIVO_COL`** → nome della colonna boolean che indica lo stato attivo/disattivo.
  *Default*: `attivo`.
* **`AUDIT_TS`** → timestamp aggiornamento.
  *Default*: `data_update` (sovrascrivibile anche via params della regola `AUDIT_UPDATE`).
* **`AUDIT_USER`** → utente aggiornamento.
  *Default*: `user_update` (sovrascrivibile anche via params della regola `AUDIT_UPDATE`).
* **`STORICO_FK`** → FK verso la tabella base nella tabella `storico.<table>_storico`.
  *Default*: `<table>_id`.
* **`CODICE_COL`** → colonna da esporre come alias `codice` in `dbops.fn_get_lookup_codici`. Usare per tabelle che non hanno la colonna `codice` standard ma hanno una chiave naturale stabile con nome diverso (es. `codice_iso` su `config.lingue`). *Nessun default* — se assente, la funzione usa l'introspezione pg_attribute.
* **`CODICE_INTERNO_COL`** → colonna da esporre come alias `codice_interno` in `dbops.fn_get_lookup_codici`. Usare per tabelle che non hanno `codice_interno` ma hanno una chiave naturale ISO o simile (es. `codice_iso`, `iso_code`). *Nessun default* — se assente, la funzione restituisce `NULL::text` per `codice_interno`.

> Se in futuro serviranno altre chiavi (es. `TX_ID_COL`), basterà inserirle nella stessa tabella e aggiornare gli automatismi che le usano.

---

### Precedenza e conflitti

* Se esistono più righe che matchano (es. pattern di schema/tabla):

  * applica la **più specifica** (match esatto) o la **priority** più alta secondo la tua convenzione;
  * mantieni **univocità logica** per `schema+table+key` per evitare ambiguità.
* Gli automatismi loggano la risoluzione in `dbops.audit_log` se vuoi tracciare i casi dubbi.

---

### Esempi

**Override `ATTIVO_COL`** per una tabella che usa `is_enabled`:

```sql
INSERT INTO dbops.automation_overrides_cols(target_schema, target_table, key, value, note)
VALUES ('anagrafiche','utenti','ATTIVO_COL','is_enabled','colonna attivo non standard');
```

**Override `AUDIT_TS`/`AUDIT_USER`** per una tabella che usa convenzioni inglesi:

```sql
INSERT INTO dbops.automation_overrides_cols(target_schema, target_table, key, value, note)
VALUES ('vendite','ordini','AUDIT_TS','updated_at','ts aggiornamento custom');

INSERT INTO dbops.automation_overrides_cols(target_schema, target_table, key, value, note)
VALUES ('vendite','ordini','AUDIT_USER','updated_by','utente aggiornamento custom');
```

**Override `STORICO_FK`** quando la FK dello storico non è `<table>_id`:

```sql
INSERT INTO dbops.automation_overrides_cols(target_schema, target_table, key, value, note)
VALUES ('catalogo','articoli','STORICO_FK','articolo_id','storico con fk esplicita');
```

---

### Buone pratiche

* Standardizza dove possibile; usa gli override solo per i casi necessari.
* Documenta gli override nel **modulo applicativo** che mantiene la tabella, per ridurre la “conoscenza tribale”.
* Evita sovrapposizioni (pattern + match esatto) senza una **priority** chiara.

---


### Vincoli (logici)

* Unicità consigliata: `(target_schema, target_table, key)`.
* Attenzione ai pattern: se usati, governa con `priority` per evitare collisioni.

### Interazione con gli automatismi

* **AUDIT_UPDATE**: legge `AUDIT_TS` e `AUDIT_USER` per scegliere la funzione `script.trgfn_audit_data_user_generic()`.
* **ATTIVO**: legge `ATTIVO_COL` su **padre** e **figlio** per i tre trigger (cascade/require/block).
* **STORICO**: legge `STORICO_FK` per i trigger `trgfn_storico_generic()`.

---

### Troubleshooting

* Se un override non sembra applicarsi, verifica con:

```sql
SELECT dbops.fn_get_override_col('schema','tabella','ATTIVO_COL','attivo');
```

* Controlla i log in `dbops.audit_log` (status `DRYRUN` / `OK`) per vedere quale colonna è stata risolta.