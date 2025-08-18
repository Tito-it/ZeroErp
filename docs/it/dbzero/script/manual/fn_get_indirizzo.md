## 📘 Documentazione Concettuale – Funzione `script.fn_get_indirizzo`

> 👀 **Vedi anche**

> **Approfondimento tabelle:**
>
> • [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi)   
> • [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)   
> • [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi)   
> • [config.comuni](/dbzero/config/tabelle/comuni)   
> • [config.codici_postali](/dbzero/config/tabelle/codici_postali)   
>
> **Approfondimento funzioni:**
>
> • [`script.fn_get_indirizzi_by_ruolo`](/dbzero/script/funzioni/fn_get_indirizzi_by_ruolo.md)   

---

### 🎯 Scopo Principale

Restituisce **un singolo indirizzo** (testo + geolocalizzazione) per uno specifico `soggetto_ruolo`, filtrando per **tipo di indirizzo** identificato dal **codice interno** (`config.tipi_indirizzi.codice_interno`).
La funzione **delegata** è `script.fn_get_indirizzi_by_ruolo`, da cui eredita la logica di formattazione e la priorità della geolocalizzazione.

---

### 🧩 Firma

```sql
CREATE OR REPLACE FUNCTION script.fn_get_indirizzo(
  p_soggetto_ruolo_id integer,
  p_tipo_codice character varying
)
RETURNS TABLE(
  indirizzo_completo text,
  geoloc geometry
)
LANGUAGE sql
COST 100
STABLE
PARALLEL UNSAFE
ROWS 1000;
```

---

### 🔢 Parametri di input

| Nome                  | Tipo      | Descrizione                                                                                                           |
| --------------------- | --------- | --------------------------------------------------------------------------------------------------------------------- |
| `p_soggetto_ruolo_id` | `integer` | ID della relazione in `anagrafiche.soggetti_ruoli` (chiave esterna degli indirizzi).                                  |
| `p_tipo_codice`       | `varchar` | **Codice interno** del tipo indirizzo (campo `config.tipi_indirizzi.codice_interno`, es. `SEDE`, `FATT`, `DOM`, ...). |

> ℹ️ **Nota:** il parametro `p_tipo_codice` non è l’ID ma il **codice** del tipo indirizzo.

---

### 📤 Valori restituiti

| Colonna              | Tipo       | Descrizione                                                                                                                                               |
| -------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `indirizzo_completo` | `text`     | Indirizzo “human‑readable”, composizione ereditata da `fn_get_indirizzi_by_ruolo` (priorità: dettaglio normalizzato → indirizzo libero → internazionale). |
| `geoloc`             | `geometry` | Geometria (tipicamente `POINT` SRID **4326**). Priorità: `anagrafiche.indirizzi_dettaglio.civic_geoloc` → `anagrafiche.indirizzi.geoloc`.                 |

---

### 🧠 Logica

```sql
SELECT indirizzo_completo, geoloc
FROM script.fn_get_indirizzi_by_ruolo(p_soggetto_ruolo_id)
WHERE tipo_indirizzo = p_tipo_codice
LIMIT 1;
```

* Filtra la tabella restituita da `fn_get_indirizzi_by_ruolo` per il tipo richiesto.
* **Limita** a **una sola riga**.

> ⚠️ **Determinismo**: senza `ORDER BY`, in presenza di più indirizzi con lo stesso tipo, la riga scelta **non è garantita** in modo deterministico. Se serve una regola di preferenza (es. **geoloc non NULL**), usare la **variante** seguente:
>
> ```sql
> SELECT indirizzo_completo, geoloc
> FROM script.fn_get_indirizzi_by_ruolo(p_soggetto_ruolo_id)
> WHERE tipo_indirizzo = p_tipo_codice
> ORDER BY (geoloc IS NULL) -- prima quelli con geoloc valorizzata
> LIMIT 1;
> ```

---

### 🧷 Dipendenze (indirette)

* **Funzione**: `script.fn_get_indirizzi_by_ruolo`
* **Tabelle**:
  `anagrafiche.indirizzi`, `anagrafiche.indirizzi_dettaglio`,
  `config.tipi_indirizzi`, `config.comuni`, `config.codici_postali`

---

### ⚙️ Comportamento e proprietà tecniche

* **Stabilità**: `STABLE` (nessun effetto collaterale; risultati coerenti nella stessa transazione).
* **Parallelismo**: `PARALLEL UNSAFE` (eredita le caratteristiche della funzione delegata e dei tipi `geometry`).
* **Prestazioni**: previsto `ROWS 1000` (indicativo). Assicurare indici su `anagrafiche.indirizzi(soggetto_ruolo_id)` e su chiavi esterne correlate.
* **Requisiti**: estensione **PostGIS** abilitata per il tipo `geometry`.

---

### 🧪 Esempi d’uso

```sql
-- 1) Indirizzo di SEDE legale per il soggetto_ruolo 123
SELECT *
FROM script.fn_get_indirizzo(123, 'SEDE');

-- 2) Indirizzo di FATTURAZIONE con geoloc disponibile (variante suggerita)
SELECT indirizzo_completo, geoloc
FROM (
  SELECT *
  FROM script.fn_get_indirizzi_by_ruolo(123)
  WHERE tipo_indirizzo = 'FATT'
  ORDER BY (geoloc IS NULL)
  LIMIT 1
) t;

-- 3) Uso come subquery in una SELECT più ampia
SELECT sr.id, f.indirizzo_completo
FROM anagrafiche.soggetti_ruoli sr
CROSS JOIN LATERAL script.fn_get_indirizzo(sr.id, 'DOM') AS f;
```

---

### ✅ Best practice e note

* **Preferisci indirizzi normalizzati** (se disponibili) per qualità e precisione della geocodifica – la funzione delegata lo fa automaticamente.
* Se nel dominio applicativo **possono esistere più indirizzi per lo stesso tipo**, valuta di **codificare una regola di ordinamento** (es. geoloc presente, data più recente, flag “principale”, ecc.).
* Verifica che `config.tipi_indirizzi` sia coerente e che i **codici interni** utilizzati dall’applicativo siano stabilizzati.

---

### 💬 Commento catalogo (PostgreSQL)

Per tracciare una descrizione nel catalogo:

```sql
COMMENT ON FUNCTION script.fn_get_indirizzo(integer, character varying) IS
  'Ritorna un singolo indirizzo (indirizzo_completo, geoloc) per soggetto_ruolo e codice del tipo (config.tipi_indirizzi.codice_interno). Delegata a fn_get_indirizzi_by_ruolo; senza ORDER BY, la scelta tra più indirizzi dello stesso tipo non è deterministica.';
```

---


{% include-markdown "signature-core.md" %}
