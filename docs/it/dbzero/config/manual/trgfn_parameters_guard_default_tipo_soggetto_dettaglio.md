## 📘 Documentazione Concettuale – Funzione `config.trgfn_parameters_guard_default_tipo_soggetto_dettaglio()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [config.parameters](/dbzero/config/tabelle/parameters)
> [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio)
> [config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides)
> [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
Approfondimento funzioni:
> [script.fn_get_parameter_full](/dbzero/script/funzioni/fn_get_parameter_full)
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

### 🎯 Scopo Principale

(latest review 27-04-2026)

La trigger function **`config.trgfn_parameters_guard_default_tipo_soggetto_dettaglio()`**
fa da **FK-surrogata** sui parametri di pattern
`DEFAULT_TIPO_SOGGETTO_DETTAGLIO_<RUOLO>` in `config.parameters`. Verifica
che `default_value` esista come `codice_interno` in
`config.tipi_soggetto_dettaglio` quando il `code` matcha il prefisso.

E' applicata dal trigger
`trg_parameters_a10_guard_default_tipo_soggetto_dettaglio_ins_upd`
(`BEFORE INSERT OR UPDATE OF code, default_value` con
`WHEN (NEW.code LIKE 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_%')`,
fase `_a10_` come guard fail-fast).

### Perche' un guard e non una FK reale

`config.parameters.default_value` e' `text` generico: ospita parametri
di tipi diversi (numeri, codici, flag, identificatori) — convertirla in
FK avrebbe rotto tutti gli altri parametri. Il guard scatta **solo**
sulle entry del pattern `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_*`,
lasciando intatti gli altri (`DEFAULT_IVA_ID`, `DEFAULT_UTILITY_ID`,
`VENDITE_MAX_*`, `tx_id_bypass_enabled`, `state_code_iso3`, ...).

Pattern coerente con la convenzione `feedback_no_hardcoded_ids`: il
parametro stocca il `codice_interno` (varchar **stabile** via
`script.trgfn_lock_columns`) anziche' l'`id` numerico, che potrebbe
cambiare in caso di reseed/cancellazione e ricreazione.

---

### Regole applicate

| Operazione | Pre-condizione | Esito |
|---|---|---|
| INSERT/UPDATE con `code NOT LIKE 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_%'` | — | Guard non scatta (clausola WHEN del trigger) |
| INSERT con `code LIKE 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_%'` e `default_value` esistente in `tipi_soggetto_dettaglio.codice_interno` | exists | OK |
| INSERT con `code LIKE 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_%'` e `default_value` non esistente | not exists | **Raise** `E_PARAMETER_DEFAULT_TIPO_SOGGETTO_INVALID` |
| UPDATE che tocca solo colonne fuori `OF (code, default_value)` (es. `description`) | — | Guard non scatta (clausola `OF` del trigger) |
| UPDATE di `default_value` su record DEFAULT_*, nuovo valore esistente | exists | OK |
| UPDATE di `default_value` su record DEFAULT_*, nuovo valore non esistente | not exists | **Raise** |
| INSERT/UPDATE con `default_value IS NULL` | — | OK (defense-in-depth, oggi inarrivabile per NOT NULL constraint) |

---

### Logica operativa

1. **Short-circuit NULL**: se `NEW.default_value IS NULL` → `RETURN NEW`.
   La colonna e' oggi `NOT NULL`, ma il branch resta come defense-in-depth
   (irrobustisce il trigger contro futuri allentamenti del vincolo o
   chiamate da contesti speciali).
2. **Lookup esistenza**: `SELECT 1 FROM config.tipi_soggetto_dettaglio
   WHERE codice_interno = NEW.default_value`. Niente `attivo` (la tabella
   non ha la colonna): il dominio e' considerato "tutto attivo".
3. **Raise**: se non esiste, `script.fn_log_and_raise_error` con codice
   `E_PARAMETER_DEFAULT_TIPO_SOGGETTO_INVALID` (id 399 in
   [`config.messaggi_errore`](/dbzero/config/tabelle/messaggi_errore))
   e contesto JSONB `parameter_id`/`code`/`default_value`. Due `%s` nel
   template messaggio.

---

### Override per emittente / user / group

I parametri `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_*` sono override-abili
gratuitamente via [`config.parameter_overrides`](/dbzero/config/tabelle/parameter_overrides)
e risolti da
[`script.fn_get_parameter_full`](/dbzero/script/funzioni/fn_get_parameter_full)
con cascade `user → group → emittente → session → function → default`.

**Limitazione attuale**: questo guard **non scatta** sugli INSERT/UPDATE
in `parameter_overrides`. Quando il primo override `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_*`
entra in produzione conviene replicare il guard sulla tabella di override
(stessa logica, lookup speculare). Rinviato finche' il caso non e' reale.

---

### Errori sollevati

| Codice | Contesto | Quando |
|---|---|---|
| `E_PARAMETER_DEFAULT_TIPO_SOGGETTO_INVALID` | `parameter_id`, `code`, `default_value`. Due `%s` (`code`, `default_value`) nel template ([`config.messaggi_errore`](/dbzero/config/tabelle/messaggi_errore) id 399). | INSERT/UPDATE su `parameters` con `code LIKE 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_%'` e `default_value` non presente in `tipi_soggetto_dettaglio.codice_interno`. SQLSTATE P0001. |

---

### Esempi

**1) Seed default cliente (ammesso):**

```sql
INSERT INTO config.parameters(id, code, default_value, description)
VALUES (15, 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL', 'PR',
        'Default tipo soggetto per ruolo CL.');
-- ok (PR esiste in config.tipi_soggetto_dettaglio.codice_interno)
```

**2) UPDATE con codice inesistente (bloccato):**

```sql
UPDATE config.parameters
   SET default_value = 'XYZ_INESISTENTE'
 WHERE code = 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL';
-- ERROR: P0001 — Parameter DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL: il default_value 'XYZ_INESISTENTE' non esiste in config.tipi_soggetto_dettaglio.codice_interno.
```

**3) UPDATE solo `description` (guard skip via clausola OF):**

```sql
UPDATE config.parameters
   SET description = 'Aggiornata'
 WHERE code = 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL';
-- ok: la clausola OF (code, default_value) salta il trigger se non
-- cambiano quelle colonne.
```

**4) Parametro fuori prefisso (guard skip via WHEN):**

```sql
INSERT INTO config.parameters(id, code, default_value, description)
VALUES (50, 'PGTAP_TEST_PARAM', 'qualsiasi_stringa', 'Test');
-- ok: la clausola WHEN limita il trigger ai code che matchano il
-- prefisso DEFAULT_TIPO_SOGGETTO_DETTAGLIO_.
```

**5) Lookup applicativo dal backend:**

```sql
SELECT script.fn_get_parameter_full(
    'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL',
    p_emittente_fiscale_id => 123  -- override per emittente se presente
);
-- 'PR' (oppure il valore override risolto)
```

---

### Note operative

* **Scope ristretto al prefisso**: clausola `WHEN (NEW.code LIKE
  'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_%')` evita overhead inutile sugli altri
  parametri (oggi 13 entry, in futuro decine).
* **Scope ristretto alle colonne sensibili**: clausola `OF (code,
  default_value)` evita di scattare su UPDATE che toccano solo
  `description`, `data_update`, `tx_id`, etc.
* **Pattern allineato a `script.trgfn_lock_columns`**: si appoggia sul
  fatto che `tipi_soggetto_dettaglio.codice_interno` e' immutabile per
  lock_columns. Se un giorno il lock venisse rimosso, il guard
  continuerebbe a funzionare correttamente (lookup sul valore corrente),
  ma i parametri esistenti potrebbero rimanere "appesi" su codici
  rinominati: rinvio a quel punto la decisione di estendere il guard
  a un trigger di sync.
* **Niente FK-cascade su DELETE**: se un `tipi_soggetto_dettaglio` viene
  eliminato, i parametri che lo referenziano restano "appesi" finche'
  non vengono aggiornati. Il guard scatta solo su INSERT/UPDATE, non su
  DELETE della tabella di lookup. Se serve consistenza forte aggiungere
  un guard speculare su `tipi_soggetto_dettaglio` (BEFORE DELETE).
* **Override su `parameter_overrides`**: il guard NON scatta sugli
  override (rinviato — vedi sezione "Override per emittente / user /
  group").

---

{% include-markdown "signature-core.md" %}

---
