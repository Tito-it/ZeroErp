## 📘 Documentazione Concettuale – Funzione `config.trgfn_parameter_overrides_fk_surrogate_dispatch()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides)
> [config.parameter_fk_surrogate](/dbzero/config/tabelle/parameter_fk_surrogate)
> [config.parameters](/dbzero/config/tabelle/parameters)
>
Approfondimento funzioni:
> [script.fn_check_parameter_fk_surrogate](/dbzero/script/funzioni/fn_check_parameter_fk_surrogate)
> [config.trgfn_parameters_fk_surrogate_dispatch](/dbzero/config/funzioni/trgfn_parameters_fk_surrogate_dispatch)
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

### 🎯 Scopo Principale

(latest review 02-05-2026)

Trigger function di **dispatch generico** del framework FK-surrogata sulla
tabella `config.parameter_overrides`. Speculare a
`config.trgfn_parameters_fk_surrogate_dispatch`: applica gli stessi vincoli
del default ai valori override.

E' applicata dal trigger
`trg_parameter_overrides_a10_fk_surrogate_dispatch_ins_upd`
(`BEFORE INSERT OR UPDATE OF parameter_id, overridden_value`, fase `_a10_`).

### Perche' un dispatcher su `parameter_overrides`

Il guard ad-hoc precedente (DEFAULT_TIPO_SOGGETTO_DETTAGLIO_*, droppato) era
limitato ai default su `parameters` e **non scattava sugli override**: un admin
poteva inserire un override con valore non valido senza che nessun controllo DB
intervenisse. La validazione era delegata implicitamente al BE / FE, in
violazione del principio DB-first.

Questo dispatcher chiude la lacuna: gli override **devono** rispettare lo
stesso vincolo dei default.

### Logica

1. **Short-circuit NULL**: se `NEW.overridden_value IS NULL` -> `RETURN NEW`.
2. **Lookup `code` padre**: `SELECT code FROM config.parameters WHERE id = NEW.parameter_id`.
   Se NULL (caso difensivo, FK garantisce esistenza), ritorna `NEW`.
3. **Delega a `script.fn_check_parameter_fk_surrogate(v_code, NEW.overridden_value)`**.
   Se `true` -> passa.
4. **Caso fallimento**: lookup target + raise `E_PARAMETER_OVERRIDE_VALUE_INVALID`
   via `script.fn_log_and_raise_error` con context JSONB:
   * `override_id` (PK riga `parameter_overrides`)
   * `parameter_id` (FK al parametro padre)
   * `code` (code del parametro padre)
   * `overridden_value` (valore non valido)
   * `target` (label `schema.table.column`)

   Tre `%s` nel template messaggio: `code`, `overridden_value`, `target`.

### Errori sollevati

| Codice | Contesto | Quando |
|---|---|---|
| `E_PARAMETER_OVERRIDE_VALUE_INVALID` (id 423) | `override_id`, `parameter_id`, `code`, `overridden_value`, `target`. | INSERT/UPDATE su `parameter_overrides` con `parameter_id` che risolve a un `code` matchante un pattern abilitato e `overridden_value` non presente nella colonna target. SQLSTATE P0001. |

### Esempi

**1) Override valido (passa):**

```sql
INSERT INTO config.parameter_overrides
  (parameter_id, overridden_value, django_user_id)
SELECT id, 'GAS', 42
  FROM config.parameters
 WHERE code = 'DEFAULT_UTILITY';
-- ok: GAS esiste in config.utilities.codice_interno
```

**2) Override invalido (raise):**

```sql
INSERT INTO config.parameter_overrides
  (parameter_id, overridden_value, django_user_id)
SELECT id, 'XYZ_INESISTENTE', 42
  FROM config.parameters
 WHERE code = 'DEFAULT_UTILITY';
-- ERROR: P0001 — Override del parametro DEFAULT_UTILITY: il valore 'XYZ_INESISTENTE' non esiste in config.utilities.codice_interno.
```

**3) Override su parametro fuori registry (no-op):**

```sql
INSERT INTO config.parameter_overrides
  (parameter_id, overridden_value)
SELECT id, '15'
  FROM config.parameters
 WHERE code = 'login_max_tentativi_falliti';
-- ok: nessun pattern matcha -> dispatcher passa.
```

**4) UPDATE valore override verso valido (passa):**

```sql
UPDATE config.parameter_overrides
   SET overridden_value = 'IDRICO'
 WHERE id = 1;
-- ok se il parametro padre e' DEFAULT_UTILITY (e IDRICO esiste).
```

---

### Note operative

* **API endpoint `/api/v1/core/parameters/settings/override/`** — il backend
  esegue INSERT/UPDATE su questa tabella; il dispatcher scatta in transazione
  e propaga `E_PARAMETER_OVERRIDE_VALUE_INVALID` come errore DB. Il middleware
  `apps.core.middleware.api_exception_middleware` lo traduce nel codice
  errore standard, mappato HTTP 400 in `error_policies.py` (BE-side).
* **Storicizzazione**: la tabella ha trigger `z90_storico_*` standard. Un
  override eliminato dopo modifica resta in storico.
* **Cascade FK**: il vincolo `fk_overrides_parameter` ha cascade implicito sul
  parametro padre. Se il parametro viene eliminato, gli override seguono;
  il dispatcher non scatta su DELETE.

---

{% include-markdown "signature-core.md" %}

---
