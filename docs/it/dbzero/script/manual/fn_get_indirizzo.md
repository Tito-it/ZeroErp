## 📘 Documentazione Concettuale – Funzione `script.fn_get_indirizzo`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**    
>
> • [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi)   
> • [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)    
> • [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi)    
> • [config.tipi_ruolo_tipi_indirizzo](/dbzero/config/tabelle/tipi_ruolo_tipi_indirizzo)    
> • [config.comuni](/dbzero/config/tabelle/comuni)   
> • [config.codici_postali](/dbzero/config/tabelle/codici_postali)  
>
> **Approfondimento funzioni:**
>
> • [`script.fn_get_indirizzi_by_ruolo`](/dbzero/script/funzioni/fn_get_indirizzi_by_ruolo.md)   

---

### 🎯 Scopo Principale
(latest review 01-12-25)
Restituisce **il miglior indirizzo disponibile** (uno o più record tecnici) relativo ad un determinato `soggetto_ruolo`, filtrando per **tipo di indirizzo** identificato dal **codice interno** (`config.tipi_indirizzi.codice_interno`).

La funzione:

* **non replica** la logica di composizione dell’indirizzo,
* ma la **delegata a `script.fn_get_indirizzi_by_ruolo`**, garantendo coerenza e riusabilità,
* integra una logica di **fallback multi-livello** basata sulla matrice
  [`config.tipi_ruolo_tipi_indirizzo`](/dbzero/config/tabelle/tipi_ruolo_tipi_indirizzo).

In pratica:

> “Dammi l’indirizzo per questo tipo; se non esiste, segui la catena di fallback definita in `config.tipi_ruolo_tipi_indirizzo` finché trovi un indirizzo utilizzabile, o finché la catena termina.”

---

### 🧩 Firma (concettuale)

> ⚠️ La firma reale restituisce molti più campi (allineati a `fn_get_indirizzi_by_ruolo`).
> Qui è riportata una **vista logica semplificata** dei parametri principali.

```sql
CREATE OR REPLACE FUNCTION script.fn_get_indirizzo(
  p_soggetto_ruolo_id bigint,
  p_tipo_codice       character varying
)
RETURNS TABLE(
  indirizzo_completo   text,
  geoloc               geometry,
  comune_id            integer,
  comune_descrizione   text,
  codice_postale       text,
  provincia            text,
  stato                text,
  is_normalizzato      boolean,
  -- + tutti i campi tecnici restituiti da fn_get_indirizzi_by_ruolo
  ...
)
LANGUAGE sql / plpgsql
STABLE
PARALLEL UNSAFE;
```

---

### 🔢 Parametri di input

| Nome                  | Tipo      | Descrizione                                                                                                  |
| --------------------- | --------- | ------------------------------------------------------------------------------------------------------------ |
| `p_soggetto_ruolo_id` | `bigint`  | ID della relazione in `anagrafiche.soggetti_ruoli`.                                                          |
| `p_tipo_codice`       | `varchar` | **Codice interno** del tipo indirizzo (`config.tipi_indirizzi.codice_interno`, es. `RES`, `FATT`, `SEDEOP`). |

> 🔹 *Non si passa l’ID del tipo indirizzo, ma il suo `codice_interno`, pensato come chiave funzionale stabile.*

---

### 📤 Valori restituiti (principali)

| Colonna              | Tipo       | Descrizione                                                                                                |
| -------------------- | ---------- | ---------------------------------------------------------------------------------------------------------- |
| `indirizzo_completo` | `text`     | Indirizzo formattato “human-readable”, applicando le regole A/B/C definite in `fn_get_indirizzi_by_ruolo`. |
| `geoloc`             | `geometry` | Geolocalizzazione (SRID 4326). Priorità: `indirizzi_dettaglio.civic_geoloc` → `indirizzi.geoloc`.          |
| `comune_id`          | `integer`  | Comune associato (se disponibile).                                                                         |
| `comune_descrizione` | `text`     | Nome del comune.                                                                                           |
| `codice_postale`     | `text`     | Codice postale (CAP).                                                                                      |
| `provincia`          | `text`     | Sigla / descrizione provincia (da `config.comuni` / `config.province`).                                    |
| `stato`              | `text`     | Stato (derivato da `config.stati` via catena stato/regione/provincia/comune).                              |
| `is_normalizzato`    | `boolean`  | `TRUE` se derivato da `indirizzo_dettaglio`; `FALSE` se indirizzo libero o estero.                         |

> ℹ️ In realtà la funzione restituisce anche tutti i campi tecnici (`indirizzo_id`, `tipo_indirizzo_id`, `stato_id`, ecc.), perché è direttamente basata sul result-set di `fn_get_indirizzi_by_ruolo`.

---

### 🧠 Logica di estrazione (senza dettagli tecnici)

La logica può essere vista come una **sequenza di tentativi**:

1. **Determina il tipo ruolo** del `soggetto_ruolo`.
2. **Prova il tipo richiesto (`p_tipo_codice`)** tramite `fn_get_indirizzi_by_ruolo`.

   * Se trova almeno un indirizzo → **restituisce e termina**.
3. **Altrimenti, cerca un fallback** in `config.tipi_ruolo_tipi_indirizzo`.

   * Prosegue seguendo la catena di fallback (multi-livello) finché non trova un indirizzo.
   * Protezione da **loop** nella catena (es. A→B→A): la funzione termina senza errori.

---

### 🔁 Esempio di catena di fallback

| tipo_indirizzo | fallback_tipo_indirizzo |
| -------------- | ----------------------- |
| SEDEOP         | SEDELEG                 |
| FORNITURA      | SEDEOP                  |

Effetto pratico: `fn_get_indirizzo(p_sr, 'FORNITURA')` → prova FORNITURA → SEDEOP → SEDELEG.

---

### 🧷 Dipendenze tecniche

| Tipo       | Riferimento                                                                                                                                                                                                                                          |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Funzione   | `script.fn_get_indirizzi_by_ruolo`                                                                                                                                                                                                                   |
| Tabelle    | `anagrafiche.indirizzi`, `anagrafiche.indirizzi_dettaglio`, `anagrafiche.soggetti_ruoli`, `config.tipi_indirizzi`, `config.tipi_ruolo_tipi_indirizzo`, `config.comuni`, `config.codici_postali`, `config.province`, `config.regioni`, `config.stati` |
| Estensioni | Richiede **PostGIS** per tipo `geometry`                                                                                                                                                                                                             |

---

### ⚙️ Proprietà tecniche

| Attributo    | Valore                       | Note                                                                    |
| ------------ | ---------------------------- | ----------------------------------------------------------------------- |
| Stabilità    | `STABLE`                     | Non modifica i dati, ma legge configurazione/anagrafiche                |
| Parallelismo | `PARALLEL UNSAFE`            | Uso di `geometry` e logica non sicura in parallel                       |
| Semantica    | “Best address with fallback” | Può restituire più righe se anomalie (es. doppio indirizzo stesso tipo) |

---

### 🧪 Esempi d’uso

```sql
-- 1) Indirizzo SEDEOP per un Gestore, con fallback su SEDELEG se assente
SELECT *
FROM script.fn_get_indirizzo(63, 'SEDEOP');

-- 2) Estrazione dinamica in JOIN laterale
SELECT sr.id, sr.soggetto_id, f.indirizzo_completo
FROM anagrafiche.soggetti_ruoli sr
CROSS JOIN LATERAL script.fn_get_indirizzo(sr.id, 'FATT') AS f;

-- 3) Solo indirizzi normalizzati con geoloc
SELECT *
FROM script.fn_get_indirizzo(123, 'FORNITURA')
WHERE is_normalizzato = TRUE
  AND geoloc IS NOT NULL;
```

---

{% include-markdown "signature-core.md" %}
