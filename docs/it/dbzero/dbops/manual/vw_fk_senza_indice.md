## 📘 Documentazione Concettuale – View `dbops.vw_fk_senza_indice`

> 👀 **Vedi anche**
>
Approfondimento Tabelle:  
>
[dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy)  
>
Approfondimento funzioni:  
>
[dbops.fn_populate_fk_index_policy](/dbzero/dbops/funzioni/fn_populate_fk_index_policy)  
> [dbops.apply_fk_index_policy](/dbzero/dbops/funzioni/apply_fk_index_policy)  
> [dbops.vw_fk_con_indice_missing_policy](/dbzero/dbops/views/vw_fk_con_indice_missing_policy)  
> [dbops.vw_indici_ridondanti_prefisso](/dbzero/dbops/views/vw_indici_ridondanti_prefisso)  
>
Catalogo dei vincoli FK in PostgreSQL (`pg_constraint`, `pg_class`, `pg_namespace`)

La view **`dbops.vw_fk_senza_indice`** elenca le foreign key definite **solo negli schemi presenti in `dbops.automation_scope`** che **non hanno alcun indice in grado di servirle**, suggerendo lo statement `CREATE INDEX` corrispondente e rispettando le eccezioni definite in `dbops.fk_index_policy`.

Il punto delicato di questa view non è trovare le FK: è decidere **quando una FK si considera coperta**. La risposta è cambiata il 27-07-2026, ed è il motivo per cui il database aveva accumulato decine di indici inutili.

---
### 🎯 Scopo Principale
(latest review 27-07-26)

* Individuare vincoli di integrità referenziale (FK) privi di indice, potenziali colli di bottiglia nelle operazioni di `JOIN` e `DELETE`.
* Fornire suggerimenti di creazione indice coerenti, facilitando l'ottimizzazione delle performance.
* Applicare le policy di esclusione gestite in `dbops.fk_index_policy`.
* Fare da **guardia** ad `apply_fk_index_policy()`, che crea un indice solo se la FK compare ancora qui.

---

### 🔑 Quando una FK si considera coperta

Non serve un indice **dedicato**. Il trigger di integrità referenziale esegue

```sql
SELECT 1 FROM figlio WHERE fkcol = $1 FOR SHARE;
```

e qualunque btree sappia servire quella ricerca va bene. La FK è quindi coperta quando esiste un btree **valido e pronto** tale che:

1. **Copertura per prefisso** — le colonne della FK coincidono, **come insieme**, con le sue prime N colonne chiave. Un indice su `(contratto_id, riga_nr)` copre la FK su `contratto_id`, perché `contratto_id` è in testa.
   Il confronto è insiemistico e non posizionale: il controllo filtra per uguaglianza su *tutte* le colonne della FK, quindi qualunque loro permutazione in testa all'indice funziona.
2. **Predicato assente, oppure soli `IS NOT NULL` sulle colonne della FK** — vedi sotto.
3. Le colonne del prefisso devono essere **colonne vere**, non espressioni: se in testa c'è un `COALESCE(...)`, il planner non può usarlo per un'uguaglianza sulla colonna sottostante.

#### Perché un parziale `WHERE colonna IS NOT NULL` copre

Perché `$1` **non è mai nullo**: una riga figlia con FK nulla non ha padre da verificare, e il trigger non parte nemmeno. La condizione `fkcol = $1` implica quindi `fkcol IS NOT NULL`, il planner PostgreSQL sa dimostrarlo e usa l'indice parziale senza problemi.

> Su una foreign key nullabile un indice parziale così **non è un ripiego: è strettamente migliore** di uno totale, perché non indicizza righe che nessuno cercherà mai.

#### Perché ogni altro predicato viene rifiutato

Un indice con, per dire, `WHERE ruolo_link = 'ROOT'` **non** copre la FK: il controllo referenziale deve poter trovare qualsiasi riga figlia, anche non-ROOT. La view rifiuta quindi ogni predicato che non sia una congiunzione di soli `<colonna della FK> IS NOT NULL`, **anche nei casi in cui di fatto coprirebbe**.

È una scelta deliberata: l'errore possibile diventa segnalare come scoperta una FK coperta — un indice di troppo — e mai il contrario, cioè lasciare una FK davvero scoperta credendola a posto.

---

### ⚠️ Cosa è cambiato il 27-07-2026, e perché conta

| Prima | Adesso |
| --- | --- |
| Copertura per **uguaglianza esatta** dell'array di colonne | Copertura per **prefisso** |
| `fk_cols` alfabetico confrontato con colonne d'indice **posizionali** | Entrambi i lati ordinati allo stesso modo |
| **Qualsiasi** indice contava, anche parziale o non valido | Solo btree validi; predicato assente o soli `IS NOT NULL` |

La regola dell'uguaglianza esatta faceva risultare scoperte le FK già servite da una `UNIQUE` più larga. Venivano registrate in `fk_index_policy` e l'automazione ci piantava sopra un indice gemello: **27 dei 48 indici ridondanti** censiti il 27-07-2026 sono nati così.

Il difetto speculare era altrettanto serio: non guardando `indpred`, un indice **parziale** veniva contato come copertura. Due foreign key risultavano a posto quando non lo erano, e ogni `DELETE` sulla tabella padre faceva seq scan sulla figlia.

---

### Colonne e Descrizione

| Colonna | Descrizione |
| --- | --- |
| `schema_name` | Schema in cui si trova la tabella con FK |
| `table_name` | Nome della tabella che contiene la FK |
| `constraint_name` | Nome del vincolo di foreign key |
| `fk_cols` | Elenco delle colonne coinvolte nella FK (ordine alfabetico) |
| `create_index_suggestion` | Statement SQL suggerito, nella forma `ix_<tabella>_<colonne>` |

---

### Esempi di Utilizzo

1. **Verificare le FK senza indice**:

   ```sql
   SELECT * FROM dbops.vw_fk_senza_indice;
   ```

2. **Portare le FK trovate sotto il governo dell'automazione** — la policy è OPT-IN, quindi `fn_populate_fk_index_policy()` le registra con `consentito = false` e serve un seed esplicito per portarle a `true`:

   ```sql
   SELECT dbops.fn_populate_fk_index_policy();
   -- poi, in 80_data, un CSV + loadUpdateData che porta a true le righe volute
   ```

   > ⚠️ **Non eseguire a mano il `create_index_suggestion`.** Gli indici FK nascono da `apply_fk_index_policy()` in `90_end`, mai da un `CREATE INDEX` scritto a mano: un indice creato fuori dalla policy non è governato da nessuno e riappare in [vw_fk_con_indice_missing_policy](/dbzero/dbops/views/vw_fk_con_indice_missing_policy).

3. **Escludere esplicitamente un vincolo tramite policy**:

   ```sql
   INSERT INTO dbops.fk_index_policy (schema_name, table_name, constraint_name, consentito)
   VALUES ('public', 'orders', 'orders_customer_id_fkey', false);
   -- Ora la view non mostrerà più questo vincolo
   ```

---

### Vantaggi Operativi

* **Miglioramento performance**: individuazione rapida di join e delete lenti dovuti a FK senza indice.
* **Nessun falso allarme**: una FK servita da una UNIQUE più larga o da un parziale `IS NOT NULL` non compare, quindi non genera indici inutili.
* **Automazione**: suggerimenti pronti all'uso, consumati da `fn_populate_fk_index_policy()`.
* **Governance**: rispetto delle policy per le eccezioni all'indice automatico.
* **Sicurezza**: usata come guardia da `apply_fk_index_policy()`, impedisce che un `consentito` rimesso a `true` per errore rigeneri ridondanze.

---

> **“Con una view dedicata alle FK prive di indice e ai suggerimenti di creazione, si ottimizzano le query e si mantiene il controllo sulle eccezioni di policy.”**
