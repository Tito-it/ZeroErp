## 📘 Documentazione Concettuale – Funzione `dbops.fn_get_lookup_codici`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[config.valute](/dbzero/config/tabelle/valute)
> [config.utilities](/dbzero/config/tabelle/utilities)
> [config.lingue](/dbzero/config/tabelle/lingue)
> [dbops.automation_overrides_cols](/dbzero/dbops/tabelle/automation_overrides_cols)

---

### 🎯 Scopo Principale
(rev 2026-05-20 — override dichiarativi via automation_overrides_cols)

La funzione **`dbops.fn_get_lookup_codici()`** fornisce una lista lookup uniforme
(`id`, `codice`, `codice_interno`, `descrizione`, `attivo`) su tabelle di configurazione
a bassa/media cardinalita', con ordinamento parametrico e filtro automatico su `attivo`.

Supporta tabelle con chiavi non-standard (es. `codice_iso`, `iso_code`) tramite
**override dichiarativi** in `dbops.automation_overrides_cols` — senza branch custom
nel codice e senza modificare la struttura delle tabelle.

---

### Parametri di input

| Parametro | Tipo | Default | Descrizione |
| --------- | ---- | ------- | ----------- |
| `p_rel` | regclass | obbligatorio | Tabella target (`schema.tabella`). |
| `p_order_col` | text | `descrizione` | Colonna ordinamento: `descrizione` o `codice`. |
| `p_order_dir` | text | `ASC` | Direzione: `ASC` o `DESC`. |
| `p_attivo_only` | boolean | `true` | Se la tabella ha `attivo boolean`, applica `WHERE attivo IS TRUE`. |
| `p_limit` | integer | `500` | Limite righe. |
| `p_offset` | integer | `0` | Offset per paginazione. |

---

### Regole di risoluzione colonne

La funzione risolve le colonne in questo ordine di priorita`:

1. **Override dichiarativo** da `dbops.automation_overrides_cols` (col_role `CODICE_COL` / `CODICE_INTERNO_COL`).
2. **Introspezione `pg_attribute`**: colonne `codice` e `codice_interno` della tabella.
3. **Fallback**: se `codice` assente, usa `COALESCE(codice_interno, id::text)` per il campo `codice`.

Vincoli strutturali obbligatori (nessun override):

* `id` deve essere `integer` o `bigint` (`uuid` non ammesso — `E_LOOKUP_STRUTTURA_TABELLA_INVALIDA` 456).
* Almeno una tra `codice`, `codice_interno` o un override dichiarativo deve essere presente.
* `descrizione` obbligatoria.
* `attivo` opzionale; se presente deve essere `boolean`.

---

### Override dichiarativi per tabelle non-standard

Per tabelle che non hanno colonne `codice` o `codice_interno` ma hanno una chiave naturale stabile con nome diverso, aggiungere righe in `dbops.automation_overrides_cols`:

| `col_role` | Semantica |
|---|---|
| `CODICE_COL` | Colonna da esporre come alias `codice` nell’output. |
| `CODICE_INTERNO_COL` | Colonna da esporre come alias `codice_interno` nell’output. |

**Esempio** — `config.lingue` (chiave naturale `codice_iso`):

```sql
-- Seed gia’ presente in automation_overrides_cols (migration 20260520-05)
-- schema_name=config, table_name=lingue, col_role=CODICE_COL,         col_name=codice_iso
-- schema_name=config, table_name=lingue, col_role=CODICE_INTERNO_COL, col_name=codice_iso
SELECT * FROM dbops.fn_get_lookup_codici(‘config.lingue’::regclass);
-- Ritorna: codice=’it’, codice_interno=’it’, descrizione=’Italiano’, attivo=true
```

---

### Output

```text
id             bigint
codice         text    -- colonna ‘codice’ o override CODICE_COL, fallback a COALESCE(codice_interno, id::text)
codice_interno text    -- colonna ‘codice_interno’ o override CODICE_INTERNO_COL, NULL se assente
descrizione    text
attivo         boolean -- NULL se la tabella non ha colonna ‘attivo’
```

---

### Codici errore

| Codice | id | Quando |
|---|---|---|
| `E_PARAMETRO_INVALIDO` | 204 | `p_rel` NULL, `order_col`/`order_dir` non validi, `limit`/`offset` fuori range |
| `E_LOOKUP_STRUTTURA_TABELLA_INVALIDA` | 456 | `id` mancante / uuid / tipo non supportato; né `codice` né `codice_interno` né override; `descrizione` mancante; `attivo` non boolean |

---

### Esempi d’uso

```sql
-- Tabella standard
SELECT * FROM dbops.fn_get_lookup_codici(‘config.valute’::regclass);

-- Tabella con chiave non-standard (override in automation_overrides_cols)
SELECT * FROM dbops.fn_get_lookup_codici(‘config.lingue’::regclass);

-- Ordine per codice DESC, includendo anche non attivi
SELECT * FROM dbops.fn_get_lookup_codici(
    ‘config.utilities’::regclass, ‘codice’, ‘DESC’, false
);

-- Paginato
SELECT * FROM dbops.fn_get_lookup_codici(
    ‘config.stati_cliente’::regclass, ‘descrizione’, ‘ASC’, true, 50, 0
);
```

---

{% include-markdown "signature-core.md" %}
