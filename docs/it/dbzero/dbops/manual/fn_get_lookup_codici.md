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
(rev 2026-06-30 — filtro asse `obsoleto_dal`; rev 2026-05-20 — override dichiarativi via automation_overrides_cols)

La funzione **`dbops.fn_get_lookup_codici()`** fornisce una lista lookup uniforme
(`id`, `codice`, `codice_interno`, `descrizione`, `attivo`) su tabelle di configurazione
a bassa/media cardinalita', con ordinamento parametrico e **due filtri opzionali e
introspettivi**: su `attivo` (`p_attivo_only`) e su `obsoleto_dal` (`p_includi_obsoleti`).

Supporta tabelle con chiavi non-standard (es. `codice_iso`, `iso_code`) tramite
**override dichiarativi** in `dbops.automation_overrides_cols` — senza branch custom
nel codice e senza modificare la struttura delle tabelle.

I due filtri sono **ortogonali** e rispecchiano due assi distinti del catalogo:
`attivo` = *"riferimento ancora valido"*; `obsoleto_dal` = *"selezionabile per il nuovo"*
(vedi `reference_deprecabilita_catalogo_obsoleto_dal` e i brief deprecabilita catalogo).

---

### Parametri di input

| Parametro | Tipo | Default | Descrizione |
| --------- | ---- | ------- | ----------- |
| `p_rel` | regclass | obbligatorio | Tabella target (`schema.tabella`). |
| `p_order_col` | text | `descrizione` | Colonna ordinamento: `descrizione` o `codice`. |
| `p_order_dir` | text | `ASC` | Direzione: `ASC` o `DESC`. |
| `p_attivo_only` | boolean | `true` | Se la tabella ha `attivo boolean`, applica `attivo IS TRUE`. |
| `p_limit` | integer | `500` | Limite righe. |
| `p_offset` | integer | `0` | Offset per paginazione. |
| `p_includi_obsoleti` | boolean | `true` | Se la tabella ha `obsoleto_dal date` **e** il valore è `false`, esclude i record con `obsoleto_dal <= CURRENT_DATE`. Default `true` = mostra tutto (vedi nota sotto). |

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
* `obsoleto_dal` opzionale; se presente deve essere `date` (altrimenti `E_LOOKUP_STRUTTURA_TABELLA_INVALIDA`).

---

### Filtro asse `obsoleto_dal` (selezione per il nuovo vs storico)

`obsoleto_dal` separa **"riferimento valido"** (`attivo`, serve alle istanze già create) da
**"selezionabile per il nuovo"**. La funzione lo rileva da sola via `pg_attribute`, esattamente
come `attivo`: se la colonna **non esiste**, nessun filtro viene applicato e la lista è restituita
intera (degradazione trasparente).

| `p_includi_obsoleti` | Comportamento (tabella con `obsoleto_dal`) | Uso tipico |
|---|---|---|
| `true` (**default**) | mostra **tutti** i record, anche gli obsoleti | letture **storico/filtro** (es. filtrare le pratiche per tipo, incluso un tipo ritirato) |
| `false` | esclude i record con `obsoleto_dal <= CURRENT_DATE` | **selezione per il nuovo** (tendine di creazione) |

Regole:

* `obsoleto_dal IS NULL` → sempre selezionabile.
* `obsoleto_dal > CURRENT_DATE` → **ritiro programmato**: ancora selezionabile fino a quella data.
* `obsoleto_dal <= CURRENT_DATE` → escluso quando `p_includi_obsoleti = false`.

> ⚠️ **Asimmetria di default voluta** rispetto a `p_attivo_only` (default `true` = *restringe*):
> qui il default `true` **non** restringe. Un default "nascondi obsoleti" cambierebbe in silenzio
> il comportamento di tutti i chiamatori esistenti (inclusi i contesti storico/filtro). La policy
> "nascondi nel nuovo" è quindi una scelta del **chiamatore** (passa `false`), non del DB.
>
> 🛡️ La sola selezione **nasconde**; la **difesa in profondità** che *vieta* nuove istanze su un
> catalogo obsoleto è il guard `dbops.trgfn_child_requires_non_obsolete_parent`.

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
| `E_LOOKUP_STRUTTURA_TABELLA_INVALIDA` | 456 | `id` mancante / uuid / tipo non supportato; né `codice` né `codice_interno` né override; `descrizione` mancante; `attivo` non boolean; `obsoleto_dal` non `date` |

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

-- Selezione PER IL NUOVO: nasconde anche gli obsoleti (obsoleto_dal <= oggi)
SELECT * FROM dbops.fn_get_lookup_codici(
    p_rel => ‘pratiche.tipi_prestazione’::regclass,
    p_includi_obsoleti => false
);

-- Filtro STORICO: mostra tutto, obsoleti inclusi (default)
SELECT * FROM dbops.fn_get_lookup_codici(‘pratiche.tipi_prestazione’::regclass);

-- Paginato
SELECT * FROM dbops.fn_get_lookup_codici(
    ‘config.stati_cliente’::regclass, ‘descrizione’, ‘ASC’, true, 50, 0
);
```

---

{% include-markdown "signature-core.md" %}
