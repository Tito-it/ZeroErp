## 📘 Documentazione Concettuale – Funzione `script.fn_check_parameter_fk_surrogate(text, text)`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [config.parameter_fk_surrogate](/dbzero/config/tabelle/parameter_fk_surrogate)
> [config.parameters](/dbzero/config/tabelle/parameters)
>
Approfondimento funzioni:
> [script.fn_parameter_fk_surrogate_regola](/dbzero/script/funzioni/fn_parameter_fk_surrogate_regola)
> [config.trgfn_parameters_fk_surrogate_dispatch](/dbzero/config/funzioni/trgfn_parameters_fk_surrogate_dispatch)
> [config.trgfn_parameter_overrides_fk_surrogate_dispatch](/dbzero/config/funzioni/trgfn_parameter_overrides_fk_surrogate_dispatch)

### 🎯 Scopo Principale

(latest review 02-05-2026)

La funzione **`script.fn_check_parameter_fk_surrogate(p_code text, p_value text)`**
ritorna `boolean` ed e' il **check riusabile** del framework FK-surrogata sui
parametri. Centralizza la logica condivisa tra il dispatcher su `parameters`
e quello su `parameter_overrides`.

### Logica

1. **Short-circuit NULL**: se `p_value IS NULL` ritorna `true`. Significa "no
   default" / "no override" per quel parametro: il caller applichera' fallback
   logico.
2. **La regola che governa il codice** la sceglie
   `script.fn_parameter_fk_surrogate_regola`, la sola sede della scelta: fra le
   regole abilitate di `config.parameter_fk_surrogate`, `EXACT > LIKE`, e a
   parita' il pattern piu' lungo (piu' specifico). La stessa funzione la usa il
   presidio `dbops.vw_parameter_fk_surrogate_dangling`, che quindi nomina la
   stessa regola della check.
3. **Nessun pattern matcha** -> ritorna `true`. Il `code` non e' soggetto al
   framework: il dispatcher e' di fatto no-op.
4. **Pattern matcha** -> esegue `EXECUTE` di un `SELECT EXISTS` dinamico:

   ```sql
   SELECT EXISTS (
       SELECT 1 FROM <target_schema>.<target_table>
        WHERE <target_column> = $1
   )
   ```

   Ritorna `true` se trovato, `false` altrimenti.

### Ritorno

| Caso | Ritorno |
|---|---|
| `p_value IS NULL` | `true` |
| Nessun pattern in registry matcha `p_code` | `true` |
| Pattern matcha, valore esiste in target | `true` |
| Pattern matcha, valore NON esiste in target | `false` |

Il chiamante (dispatcher) decide come tradurre `false` in errore con context
specifico (parameters vs parameter_overrides).

### Stabilita' e cache

La funzione e' marcata `STABLE`: il risultato dipende solo dagli argomenti e
dallo stato del DB nel momento della chiamata, non da side-effect. PostgreSQL
puo' invocarla una sola volta per riga in trigger BEFORE INSERT/UPDATE.

### SQL dinamico e sicurezza

Il `format()` usa `%I` (quote_ident) su `target_schema/target_table/target_column`,
quindi e' immune a SQL injection da quei campi. La sola superficie di attacco
sarebbe un INSERT in `parameter_fk_surrogate` con identifier malevoli, ma il
registry e' tabella di configurazione gestita da DBA via seed CSV, non
esposta a input utente.

---

### Esempi

```sql
-- 1) Code non in registry: passa.
SELECT script.fn_check_parameter_fk_surrogate('VENDITE_MAX_SCONTO_PCT', '5');
-- => true

-- 2) Pattern EXACT, valore esistente.
SELECT script.fn_check_parameter_fk_surrogate('DEFAULT_UTILITY', 'ENERGIA');
-- => true

-- 3) Pattern EXACT, valore inesistente.
SELECT script.fn_check_parameter_fk_surrogate('DEFAULT_UTILITY', 'XYZ');
-- => false

-- 4) Pattern LIKE matcha, valore inesistente.
SELECT script.fn_check_parameter_fk_surrogate('DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL', 'XYZ');
-- => false

-- 5) Valore NULL passa sempre.
SELECT script.fn_check_parameter_fk_surrogate('DEFAULT_UTILITY', NULL);
-- => true
```

---

{% include-markdown "signature-core.md" %}

---
