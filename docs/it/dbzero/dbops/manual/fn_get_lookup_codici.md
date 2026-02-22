## 📘 Documentazione Concettuale – Funzione `dbops.fn_get_lookup_codici`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> * [config.valute](/dbzero/config/tabelle/valute)  
> * [config.utilities](/dbzero/config/tabelle/utilities)  
> * [config.stati_cliente](/dbzero/config/tabelle/stati_cliente)  

---

### 🎯 Scopo Principale

(latest review 21-02-2026)  
La funzione **`dbops.fn_get_lookup_codici()`** fornisce una lista lookup
uniforme (`id`, `codice`, `descrizione`) su tabelle di configurazione con
cardinalita` bassa o media, con ordinamento parametrico e filtro automatico
su `attivo` quando presente.

---

### 🔍 Parametri di input

| Parametro | Tipo | Default | Descrizione |
| --------- | ---- | ------- | ----------- |
| `p_rel` | regclass | - | Tabella target (`schema.tabella`) da interrogare. |
| `p_order_col` | text | `descrizione` | Colonna ordinamento: `descrizione` oppure `codice`. |
| `p_order_dir` | text | `ASC` | Direzione ordinamento: `ASC` oppure `DESC`. |
| `p_attivo_only` | boolean | `true` | Se la tabella ha `attivo`, applica `WHERE attivo IS TRUE`. |
| `p_limit` | integer | `200` | Limite righe opzionale per estrazioni piu` leggere. |
| `p_offset` | integer | `0` | Offset opzionale per paginazione. |

---

### ✅ Regole principali

* La tabella deve avere colonne `id`, `codice`, `descrizione`.
* `id` deve essere numerico (`smallint`, `integer`, `bigint`).
* `id` di tipo `uuid` non e` ammesso: la funzione alza errore.
* Se la colonna `attivo` non esiste, `p_attivo_only` viene ignorato.
* La funzione e` pensata per lookup/configurazioni, non per dataset voluminosi.

---

### ✅ Output

Ritorna una tabella con:

* `id bigint`
* `codice text`
* `descrizione text`

---

### 🧪 Esempi d’uso

```sql
-- default: ordine per descrizione ASC, solo attivi se disponibile
SELECT *
FROM dbops.fn_get_lookup_codici('config.valute'::regclass);

-- ordine per codice DESC, includendo anche non attivi
SELECT *
FROM dbops.fn_get_lookup_codici(
  'config.utilities'::regclass,
  'codice',
  'DESC',
  false
);

-- estrazione limitata/paginata
SELECT *
FROM dbops.fn_get_lookup_codici(
  'config.stati_cliente'::regclass,
  'descrizione',
  'ASC',
  true,
  50,
  0
);
```

---

{% include-markdown "signature-core.md" %}
