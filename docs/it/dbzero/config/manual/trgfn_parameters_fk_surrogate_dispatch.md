## 📘 Documentazione Concettuale – Funzione `config.trgfn_parameters_fk_surrogate_dispatch()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [config.parameter_fk_surrogate](/dbzero/config/tabelle/parameter_fk_surrogate)
> [config.parameters](/dbzero/config/tabelle/parameters)
> [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
Approfondimento funzioni:
> [script.fn_check_parameter_fk_surrogate](/dbzero/script/funzioni/fn_check_parameter_fk_surrogate)
> [config.trgfn_parameter_overrides_fk_surrogate_dispatch](/dbzero/config/funzioni/trgfn_parameter_overrides_fk_surrogate_dispatch)
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

### 🎯 Scopo Principale

(latest review 02-05-2026)

Trigger function di **dispatch generico** del framework FK-surrogata su
`config.parameters`. Sostituisce e generalizza il guard ad-hoc
`trgfn_parameters_guard_default_tipo_soggetto_dettaglio` (droppato in
20260502-07).

E' applicata dal trigger
`trg_parameters_a10_fk_surrogate_dispatch_ins_upd`
(`BEFORE INSERT OR UPDATE OF code, default_value`, fase `_a10_`,
**senza clausola WHEN**: il filtro dei `code` interessati e' fatto runtime
dal lookup nel registry).

### Differenza chiave vs guard ad-hoc precedente

| Aspetto | Guard ad-hoc (legacy) | Dispatcher framework |
|---|---|---|
| Filtro pattern | Clausola WHEN hard-coded sul prefisso | Lookup runtime su `parameter_fk_surrogate` |
| Aggiungere nuovo pattern | Nuovo trigger DB + funzione | Riga seed in CSV registry |
| Path `parameter_overrides` | Non gestito | Coperto da dispatcher speculare |
| Codice errore | Per-pattern | Generico con `target` nel context |

### Logica

1. **Short-circuit NULL**: se `NEW.default_value IS NULL` -> `RETURN NEW`.
   La colonna e' oggi `NOT NULL`, ma il branch resta come defense-in-depth.
2. **Delega a `script.fn_check_parameter_fk_surrogate(NEW.code, NEW.default_value)`**.
   Se ritorna `true` -> `RETURN NEW` (passa).
3. **Caso fallimento**: lookup target (per messaggio diagnostico) + raise
   `E_PARAMETER_DEFAULT_VALUE_INVALID` via
   `script.fn_log_and_raise_error` con context JSONB:
   * `parameter_id` (PK riga parameters)
   * `code` (es. `DEFAULT_UTILITY`)
   * `default_value` (valore non valido)
   * `target` (label `schema.table.column`)

   Tre `%s` nel template messaggio: `code`, `default_value`, `target`.

### Errori sollevati

| Codice | Contesto | Quando |
|---|---|---|
| `E_PARAMETER_DEFAULT_VALUE_INVALID` (id 422) | `parameter_id`, `code`, `default_value`, `target`. | INSERT/UPDATE su `parameters` con `code` matchante un pattern abilitato in `parameter_fk_surrogate` e `default_value` non presente nella colonna target. SQLSTATE P0001. |

### Esempi

**1) Code coperto, valore valido (passa):**

```sql
INSERT INTO config.parameters(id, code, default_value, description)
VALUES (50, 'DEFAULT_UTILITY', 'ENERGIA', 'Default utility');
-- ok (ENERGIA esiste in config.utilities.codice_interno)
```

**2) Code coperto, valore invalido (raise):**

```sql
UPDATE config.parameters
   SET default_value = 'XYZ_INESISTENTE'
 WHERE code = 'DEFAULT_UTILITY';
-- ERROR: P0001 — Parameter DEFAULT_UTILITY: il default_value 'XYZ_INESISTENTE' non esiste in config.utilities.codice_interno.
```

**3) UPDATE solo `description` (no scatto via clausola OF):**

```sql
UPDATE config.parameters
   SET description = 'Aggiornata'
 WHERE code = 'DEFAULT_UTILITY';
-- ok: la clausola OF (code, default_value) non include description.
```

**4) Code fuori registry (no-op):**

```sql
INSERT INTO config.parameters(id, code, default_value, description)
VALUES (51, 'PGTAP_TEST_FOO', 'qualunque', 'Test');
-- ok: nessun pattern matcha 'PGTAP_TEST_FOO' -> dispatcher passa.
```

**5) Pattern LIKE (DEFAULT_TIPO_SOGGETTO_DETTAGLIO_*):**

```sql
INSERT INTO config.parameters(id, code, default_value, description)
VALUES (52, 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL', 'PR', 'Default ruolo CL');
-- ok (PR esiste in config.tipi_soggetto_dettaglio.codice_interno).
```

---

### Note operative

* **Costo runtime**: il lookup nel registry e' O(N) sui pattern (oggi 2-3, in
  futuro decine). `config.parameters` non e' tabella ad alto volume di
  scrittura: il costo e' trascurabile.
* **Niente clausola WHEN**: scelta intenzionale per centralizzare il filtro
  nel registry. Per code fuori registry il dispatcher fa solo SELECT al
  registry e ritorna -- nessun raise.
* **Override su `parameter_overrides`**: gestito dal dispatcher speculare
  `config.trgfn_parameter_overrides_fk_surrogate_dispatch`. **Lacuna del
  guard precedente chiusa**.
* **DEFAULT_IVA_ID**: NON e' nel framework finche' `config.iva` non espone
  `codice_interno`. Vedi tech debt in
  [linee-guida-sql §6b](/it/linee-guida-sql.md#6b-riferimenti-esterni-a-tabelle-di-catalogo-chiave-naturale-stabile).
* **Niente FK-cascade su DELETE target**: se viene cancellata una riga di
  `utilities` o `tipi_soggetto_dettaglio` referenziata da un parametro, il
  parametro resta "appeso" finche' non viene aggiornato. Il dispatcher
  scatta solo su INSERT/UPDATE di `parameters`, non su DELETE delle tabelle
  di lookup.

---

{% include-markdown "signature-core.md" %}

---
