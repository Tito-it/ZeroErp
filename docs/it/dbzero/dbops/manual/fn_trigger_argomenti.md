## 📘 Documentazione Concettuale – Funzione `dbops.fn_trigger_argomenti`

> 👀 **Vedi anche**
>
Approfondimento funzioni:    
> [dbops.fn_lock_columns_divergenze](/dbzero/dbops/funzioni/fn_lock_columns_divergenze)    
> [dbops.fn_ritira_attivo_eccezioni](/dbzero/dbops/funzioni/fn_ritira_attivo_eccezioni)    

---
### 🎯 Scopo Principale
(latest review 26-09-26)

Restituisce gli **argomenti di un trigger** (`pg_trigger.tgargs`) come `text[]`,
nell'ordine in cui li scrive il `CREATE TRIGGER`. Array vuoto se il trigger non
ne ha.

Serve a chi riconosce un trigger **generico** (una funzione, tanti trigger)
da quello che gli viene passato, e non dal nome: il nome può essere hashato
oltre i 63 caratteri o scritto a mano, gli argomenti no.

**Building block** (regola del 2), dal 2026-09-26. Lo usano
`dbops.fn_lock_columns_divergenze`, `dbops.fn_ritira_attivo_eccezioni`,
`dbops.fn_trigger_attivo_orfani`, il pgTAP
`catalogo/test-articoli-seed-uom-base-lock` e il guardrail
`scripts/sql/guardrail_codice_errore_strutturato.sql`. Chi deve leggere
`tgargs` passa da qui.

---

### ⛔ Perché non `encode(tgargs, 'escape')`

Era la forma usata prima, e ha due difetti:

| Forma | Problema | Esempio |
| --- | --- | --- |
| `rtrim(encode(tgargs,'escape'), '\000')` | `rtrim` toglie l'**insieme** di caratteri `\` e `0`, non la sequenza: un ultimo argomento che finisce con uno zero lo perde | `'col', 'E_X10'` → `{col,E_X1}` |
| `encode(…, 'escape')` in generale | ogni byte con il bit alto diventa `\nnn` | `città` → `citt\303\240` |

Questa funzione taglia i **byte** su ogni `NUL` (ogni argomento in `tgargs` ne è
chiuso) e riconverte i pezzi con la codifica del server.

---

### Esempi di utilizzo

```sql
SELECT t.tgname, dbops.fn_trigger_argomenti(t.tgargs)
  FROM pg_trigger t
 WHERE t.tgrelid = 'catalogo.articoli'::regclass
   AND NOT t.tgisinternal;
```

Brief: `brief-db-lock-di-colonna-fuori-registro`.
