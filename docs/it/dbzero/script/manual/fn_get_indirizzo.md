## 📘 Documentazione Concettuale – Funzione `script.fn_get_indirizzo`

> 👀 **Vedi anche**
>
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

Restituisce **un singolo indirizzo completo e geolocalizzato** relativo ad un determinato `soggetto_ruolo`, filtrando per **tipo di indirizzo** identificato dal **codice interno** (`config.tipi_indirizzi.codice_interno`).

La funzione **non replica la logica di composizione**, bensì **delegata a `script.fn_get_indirizzi_by_ruolo`**, garantendo coerenza e riusabilità.

Restituisce il **miglior indirizzo disponibile** secondo le regole di priorità (normalizzato → libero nazionale → estero) e con geolocalizzazione preferita ove esistente.

---

### 🧩 Firma

```sql
CREATE OR REPLACE FUNCTION script.fn_get_indirizzo(
  p_soggetto_ruolo_id integer,
  p_tipo_codice character varying
)
RETURNS TABLE(
  indirizzo_completo text,
  geoloc geometry,
  -- Estensioni v2 (allineate alla funzione madre)
  comune_id integer,
  comune_descrizione text,
  codice_postale text,
  provincia text,
  stato text,
  is_normalizzato boolean
)
LANGUAGE sql
COST 100
STABLE
PARALLEL UNSAFE
ROWS 1000;
```

>  *Estesa rispetto alla versione precedente per includere i campi territoriali e il flag `is_normalizzato`, in linea con la funzione madre `fn_get_indirizzi_by_ruolo`.*

---

### 🔢 Parametri di input

| Nome                  | Tipo      | Descrizione                                                                                                    |
| --------------------- | --------- | -------------------------------------------------------------------------------------------------------------- |
| `p_soggetto_ruolo_id` | `integer` | ID della relazione in `anagrafiche.soggetti_ruoli`.                                                            |
| `p_tipo_codice`       | `varchar` | **Codice interno** del tipo indirizzo (`config.tipi_indirizzi.codice_interno`, es. `SEDE`, `FATT`, `DOMFISC`). |

 *Non è richiesto l’ID della tabella `tipi_indirizzi`, ma il valore del campo `codice_interno`.*

---

### 📤 Valori restituiti

| Colonna              | Tipo       | Descrizione                                                                                                      |
| -------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------- |
| `indirizzo_completo` | `text`     | Indirizzo formattato “human-readable”, applicando le regole di priorità definite in `fn_get_indirizzi_by_ruolo`. |
| `geoloc`             | `geometry` | Geolocalizzazione (SRID 4326). Priorità: `indirizzi_dettaglio.civic_geoloc` → `indirizzi.geoloc`.                |
| `comune_id`          | `integer`  | Comune associato (se disponibile).                                                                               |
| `comune_descrizione` | `text`     | Nome del comune.                                                                                                 |
| `codice_postale`     | `text`     | Codice postale (CAP).                                                                                            |
| `provincia`          | `text`     | Provincia (derivata dalla tabella `config.comuni`).                                                              |
| `stato`              | `text`     | Stato del soggetto o dell’indirizzo (gestione futura per internazionale).                                        |
| `is_normalizzato`    | `boolean`  | `TRUE` se derivato da `indirizzo_dettaglio`; `FALSE` se indirizzo libero o fallback internazionale.              |

---

### 🧠 Logica di estrazione (semplificata)

```sql
SELECT indirizzo_completo, geoloc, comune_id, comune_descrizione, codice_postale,
       provincia, stato, is_normalizzato
FROM script.fn_get_indirizzi_by_ruolo(p_soggetto_ruolo_id)
WHERE tipo_indirizzo = p_tipo_codice
ORDER BY (geoloc IS NULL), is_normalizzato DESC
LIMIT 1;
```

 *Senza `ORDER BY`, non vi è determinismo se esistono più indirizzi dello stesso tipo.* La regola suggerita:

* 1️⃣ privilegia indirizzi con **geolocalizzazione valida**,
* 2️⃣ privilegia quelli **normalizzati** rispetto a liberi.

---

### 🧷 Dipendenze tecniche

| Tipo       | Riferimento                                                                                                                   |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Funzione   | `script.fn_get_indirizzi_by_ruolo`                                                                                            |
| Tabelle    | `anagrafiche.indirizzi`, `anagrafiche.indirizzi_dettaglio`, `config.tipi_indirizzi`, `config.comuni`, `config.codici_postali` |
| Estensioni | Richiede **PostGIS** per tipo `geometry`                                                                                      |

---

### ⚙️ Proprietà tecniche

| Attributo    | Valore                 | Note                                                    |
| ------------ | ---------------------- | ------------------------------------------------------- |
| Stabilità    | `STABLE`               | Nessuna modifica ai dati.                               |
| Parallelismo | `PARALLEL UNSAFE`      | Per via del tipo `geometry` e funzioni non thread-safe. |
| Rows (hint)  | `1000`                 | Indicativo.                                             |
| Determinismo | Consigliato `ORDER BY` | In caso di indirizzi multipli per tipo.                 |

---

### 🧪 Esempi d’uso

```sql
-- 1) Indirizzo DOMFISC per il soggetto_ruolo 63
SELECT *
FROM script.fn_get_indirizzo(63, 'DOMFISC');

-- 2) Uso in JOIN laterale (estrazione dinamica)
SELECT sr.id, sr.ruolo, f.indirizzo_completo
FROM anagrafiche.soggetti_ruoli sr
CROSS JOIN LATERAL script.fn_get_indirizzo(sr.id, 'RES') AS f;

-- 3) Verifica indirizzo con geoloc disponibile
SELECT *
FROM script.fn_get_indirizzo(123, 'FATT')
WHERE geoloc IS NOT NULL;
```

---

### ✅ Best practice

* Usare **sempre codici interni standardizzati** (non ID) per richiamare la funzione.
* Mantenere **coerenza con `fn_get_indirizzi_by_ruolo`** per ogni modifica futura.
* In presenza di applicativi o API, valutare gestione esplicita `ORDER BY`.
* Validare sempre tramite test pgTAP in caso di modifiche a tabelle correlate.

---

### 💬 Commento catalogo (SQL)

```sql
COMMENT ON FUNCTION script.fn_get_indirizzo(integer, character varying) IS
  'Restituisce un singolo indirizzo completo e geolocalizzato per soggetto_ruolo e codice tipo indirizzo, ' ||
  'delegando a fn_get_indirizzi_by_ruolo. Include campi territoriali e flag is_normalizzato. ' ||
  'La selezione è deterministica solo se definito un ORDER BY.';
```

---

{% include-markdown "signature-core.md" %}
