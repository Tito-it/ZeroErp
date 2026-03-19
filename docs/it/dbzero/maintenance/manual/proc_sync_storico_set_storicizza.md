## 📘 Documentazione Concettuale – Procedura: `maintenance.proc_sync_storico_set_storicizza`

> 👀 **Vedi anche:**
>
Approfondimento tabelle:
>
[config.storico_set_storicizza](/dbzero/config/tabelle/storico_set_storicizza)
>
Approfondimento funzioni:
>
[maintenance.proc_apply_storicizza_defaults](/dbzero/maintenance/funzioni/proc_apply_storicizza_defaults)

---
### 🎯 Scopo Principale
(latest review 07-01-26)
`maintenance.proc_sync_storico_set_storicizza` è una procedura di sincronizzazione che individua, all’interno del database, tutte le tabelle che possiedono la colonna `storicizza` con **valore di default `true`** e le registra nella tabella di configurazione `config.storico_set_storicizza`.

Questa operazione consente di mantenere allineata la configurazione del sistema con lo stato effettivo delle tabelle che partecipano alla storicizzazione.

---

### Comportamento

1. **Scansione metadati**

   * Interroga le viste del catalogo PostgreSQL (`pg_attribute`, `pg_class`, `pg_namespace`, `pg_attrdef`) per individuare le tabelle di tipo `BASE TABLE` (`relkind = 'r'`) con una colonna `storicizza`.

2. **Filtro per default `true`**

   * Verifica che il valore di default della colonna sia la stringa `'true'`.

3. **Inserimento configurazione**

   * Inserisce il nome completo della tabella (schema.tabella) in `config.storico_set_storicizza`, impostando `insert_manuale = false`.
   * Utilizza `ON CONFLICT (table_name) DO NOTHING` per evitare duplicati.

---

### Dettagli Tecnici

* **Rilevamento default**: si basa sulla stringa restituita da `pg_get_expr(ad.adbin, ad.adrelid)`.
* **Formato nome tabella**: il campo `table_name` è valorizzato come testo `schema.tabella` tramite cast da `regclass`.
* **Gestione duplicati**: l’`ON CONFLICT` impedisce l’inserimento di voci già presenti.

---

### Frequenza di utilizzo

* Può essere eseguita manualmente dopo modifiche allo schema.
* Può essere integrata in **job di manutenzione periodici** per mantenere aggiornata la configurazione.

---

### Esempio di utilizzo

```sql
CALL maintenance.proc_sync_storico_set_storicizza();
```

---

> **Nota**: questa procedura non modifica lo schema delle tabelle, ma aggiorna unicamente la configurazione interna per la storicizzazione.

---

{% include-markdown "signature-core.md" %}
