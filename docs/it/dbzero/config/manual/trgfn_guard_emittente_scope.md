## Documentazione Concettuale – Trigger Function `config.trgfn_guard_emittente_scope`

> **Vedi anche**
>
> **Tabelle protette:**
>
> * [vendite.fatture](/dbzero/vendite/tabelle/fatture)
> * [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti)
>
> **Funzioni correlate:**
>
> * [config.fn_check_user_emittente_scope](/dbzero/config/funzioni/fn_check_user_emittente_scope)

---

### Scopo Principale

(latest review 28-02-2026)
La trigger function **`config.trgfn_guard_emittente_scope`** implementa il
defense-in-depth: blocca INSERT/UPDATE se l'utente corrente non ha scope
sull'emittente fiscale della riga.

---

### Parametri trigger (TG_ARGV)

| Indice | Valore | Descrizione |
| ------ | ------ | ----------- |
| `TG_ARGV[0]` | `'soggetto_ruolo'` o `'fattura'` | Modalita di risoluzione emittente. |
| `TG_ARGV[1]` | nome colonna | Colonna della riga che contiene l'ID da risolvere. |

---

### Modalita di risoluzione

* **`soggetto_ruolo`**: la colonna contiene un `soggetto_ruolo_id`;
  l'emittente si risolve via `anagrafiche.emittenti_fiscali.soggetto_ruolo_id`.
  Usato su `vendite.fatture` (colonna `emittente_soggetto_ruolo_id`).

* **`fattura`**: la colonna contiene un `fattura_id`;
  l'emittente si risolve via `vendite.fatture → emittenti_fiscali`.
  Usato su `pagamenti.vendite_movimenti` (colonna `fattura_id`).

---

### Logica di controllo

1. Legge `app.current_user_id` dalla sessione PostgreSQL (`current_setting`).
   Se `NULL` (job batch) → **skip** (RETURN NEW).
2. Legge il valore della colonna da `NEW` (via `to_jsonb`).
   Se `NULL` → **skip**.
3. Su `UPDATE`, se il valore colonna non e cambiato → **skip**.
4. Risolve `emittente_fiscale_id` in base alla modalita.
   Se non risolvibile → **skip** (dati non ancora linkati).
5. Chiama `config.fn_check_user_emittente_scope()`.
   Se `false` → errore via `script.fn_log_and_raise_error` con codice `E_SCOPE_EMITTENTE`.

---

### Trigger associati

```sql
-- Su vendite.fatture
CREATE TRIGGER trg_fatture_a10_guard_emittente_scope_ins_upd
  BEFORE INSERT OR UPDATE ON vendite.fatture
  FOR EACH ROW
  EXECUTE FUNCTION config.trgfn_guard_emittente_scope('soggetto_ruolo', 'emittente_soggetto_ruolo_id');

-- Su pagamenti.vendite_movimenti
CREATE TRIGGER trg_vendite_movimenti_a10_guard_emittente_scope_ins_upd
  BEFORE INSERT OR UPDATE ON pagamenti.vendite_movimenti
  FOR EACH ROW
  EXECUTE FUNCTION config.trgfn_guard_emittente_scope('fattura', 'fattura_id');
```

---

### Regole principali

* Trigger **BEFORE INSERT OR UPDATE**, fase `_a10_` (guard).
* Generica e riusabile: basta un nuovo trigger con i parametri `TG_ARGV` appropriati.
* Errori segnalati con `script.fn_log_and_raise_error` per logging + RAISE coerente.

---

{% include-markdown "signature-core.md" %}
