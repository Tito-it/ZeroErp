## 📘 Documentazione Concettuale – Funzione `dbops.fn_apply_automazione_overlap`

> 👀 **Vedi anche**
>
Guide:
> [Automazione DB](/guide/automazione-db)
>
Approfondimento tabelle:    
> [dbops.automazione_overlap](/dbzero/dbops/tabelle/automazione_overlap)    
>
Approfondimento funzioni:
> [dbops.fn_seed_automazione_overlap](/dbzero/dbops/funzioni/fn_seed_automazione_overlap)    
>
### 🎯 Scopo Principale
(latest review 19-01-26)
La funzione **`dbops.fn_apply_automazione_overlap(p_exec_mode, p_dry_run)`** applica
i vincoli `EXCLUDE USING gist` alle tabelle marcate `active=true` in
`dbops.automazione_overlap`.

---

### Parametri di input

| Parametro     | Tipo    | Descrizione                                  |
| ------------- | ------- | -------------------------------------------- |
| `p_exec_mode` | text    | Modalita' di esecuzione (AUTO/CI/SCHEDULED). |
| `p_dry_run`   | boolean | Se true non crea vincoli.                    |

---

### Logica operativa (sintesi)

1. Legge le righe `active=true` compatibili con `exec_mode`.
2. Verifica esistenza colonne chiave e colonne periodo.
3. Salta la tabella se trova gia' un `EXCLUDE` equivalente.
4. Crea il vincolo `EXCLUDE` usando:
   * `key_columns` con `WITH =`;
   * `daterange(valido_dal, COALESCE(valido_al,'infinity'), bounds) WITH &&`.

---

### Esempi

**Applicazione reale:**

```sql
SELECT dbops.fn_apply_automazione_overlap('AUTO', false);
```

**Dry-run:**

```sql
SELECT dbops.fn_apply_automazione_overlap('AUTO', true);
```

---

### Note

* Se `key_columns` e' vuoto/non valido, il vincolo non viene creato.
* `range_bounds` default `[]` (inclusivo).
* Per chiavi UUID e' richiesto `btree_gist`.

---

{% include-markdown "signature-core.md" %}

---
