## 📘 Documentazione Concettuale – Funzione `script.fn_get_indirizzi_by_ruolo`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi)   
> • [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)  
> • [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi)   
> • [config.comuni](/dbzero/config/tabelle/comuni)   
> • [config.codici_postali](/dbzero/config/tabelle/codici_postali)   

---

### 🎯 Scopo Principale

Restituisce tutti gli **indirizzi** associati a uno specifico `soggetto_ruolo` (cliente, fornitore, ecc.), producendo per ciascuno:

* il **tipo di indirizzo** (codice interno configurato),
* una stringa **human‑readable** dell’**indirizzo completo** secondo regole di priorità ben definite,
* la **migliore geolocalizzazione disponibile** (priorità civico → indirizzo).

Questa funzione centralizza la **composizione e presentazione** dell’indirizzo, evitando ridondanza di logiche a livello di viste o applicativo.

---

### 🧩 Firma

```sql
CREATE OR REPLACE FUNCTION script.fn_get_indirizzi_by_ruolo(
  p_soggetto_ruolo_id integer
)
RETURNS TABLE(
  tipo_indirizzo character varying,
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

| Nome                  | Tipo      | Descrizione                                                                            |
| --------------------- | --------- | -------------------------------------------------------------------------------------- |
| `p_soggetto_ruolo_id` | `integer` | ID della relazione in `anagrafiche.soggetti_ruoli` a cui sono collegati gli indirizzi. |

---

### 📤 Valori restituiti

| Colonna              | Tipo       | Descrizione                                                                                                                           |
| -------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `tipo_indirizzo`     | `varchar`  | Codice interno del tipo indirizzo da `config.tipi_indirizzi.codice_interno`.                                                          |
| `indirizzo_completo` | `text`     | Indirizzo formattato “leggibile” costruito secondo la **priorità** descritta in seguito.                                              |
| `geoloc`             | `geometry` | Geometria (tipicamente `POINT` SRID 4326). Priorità: `anagrafiche.indirizzi_dettaglio.civic_geoloc` → `anagrafiche.indirizzi.geoloc`. |

---

### 🗺️ Logica di composizione dell’indirizzo (priorità)

1. **Dettaglio normalizzato** (`ai.indirizzo_dettaglio_id` **non NULL**):
   Usa `ad.indirizzo_normalizzato`, quindi concatena **Comune** (`co.descrizione`) e **CAP** (`cp.codice`, se presente).
   *Esempio*: `Via Roma 10, Firenze 50100`.

2. **Indirizzo libero nazionale** (`ai.indirizzo_libero` **non NULL**):
   Concatena l’indirizzo libero con **Comune** e **CAP** se disponibili.
   *Esempio*: `Strada Provinciale 23, Siena 53100`.

3. **Fallback internazionale/estero** (altrimenti):
   Concatena `ai.indirizzo_libero`, `ai.locality`, `ai.administrative_area`, `ai.postal_box` (se presenti), separati da virgole.
   *Esempio*: `221B Baker Street, London, Greater London, NW1`.

**Geolocalizzazione**: viene effettuato un `COALESCE(ad.civic_geoloc, ai.geoloc)` per privilegiare la posizione puntuale del civico quando disponibile.

---

### 🧷 Dipendenze e riferimenti (tabelle)

* **`anagrafiche.indirizzi (ai)`**: sorgente principale degli indirizzi; campi usati:
  `soggetto_ruolo_id`, `tipo_indirizzo_id`, `indirizzo_dettaglio_id`, `indirizzo_libero`, `locality`, `administrative_area`, `postal_box`, `geoloc`, `comune_id`, `codice_postale_id`.
* **`anagrafiche.indirizzi_dettaglio (ad)`**: dettaglio normalizzato; campi:
  `id`, `indirizzo_normalizzato`, `civic_geoloc`.
* **`config.tipi_indirizzi (ti)`**: classificazione del tipo; campi:
  `id`, `codice_interno`.
* **`config.comuni (co)`**: descrizione del Comune; campi:
  `id`, `descrizione`.
* **`config.codici_postali (cp)`**: codice postale; campi:
  `id`, `codice`.

---

### ⚙️ Comportamento e proprietà tecniche

* **Determinismo**: `STABLE` (nessun effetto collaterale; risultati coerenti nella stessa transazione).
* **Parallelismo**: `PARALLEL UNSAFE` (usa oggetti non garantiti thread‑safe a livello planner).
* **Ordinamento**: risultato ordinato per `ti.codice_interno` (tipo indirizzo).
* **Prestazioni**: previsto `ROWS 1000` (indicativo). Considerare indici su chiavi esterne:
  `anagrafiche.indirizzi(soggetto_ruolo_id)`, `anagrafiche.indirizzi(tipo_indirizzo_id)`,
  e (se usati in filtri altrove) su `anagrafiche.indirizzi(comune_id)`, `anagrafiche.indirizzi(codice_postale_id)`.

---

### 🧪 Esempi d’uso

```sql
-- Indirizzi del soggetto_ruolo 123
SELECT *
FROM script.fn_get_indirizzi_by_ruolo(123);

-- Solo indirizzi con geolocalizzazione disponibile
SELECT *
FROM script.fn_get_indirizzi_by_ruolo(123)
WHERE geoloc IS NOT NULL;
```

---

### ✅ Best practice e note

* **Preferire l’indirizzo normalizzato** quando possibile (`indirizzo_dettaglio_id`) per qualità e geocodifica più affidabile.
* **SRID consigliato**: 4326 per compatibilità con servizi GIS/web. Valutare indici `GIST` sulle colonne `geometry` coinvolte.
* **Internazionalizzazione**: l’ordine dei componenti nel fallback internazionale è neutro; se servono formattazioni locali, demandare al livello applicativo.
* **Pulizia spazi**: la funzione usa `trim` e `COALESCE` per evitare doppie virgole/spazi quando alcuni segmenti non sono presenti.

---

### 🔄 Manutenzione / Impatti

* Rinominare campi nelle tabelle dipendenti **non richiede modifiche** finché la SELECT resta coerente.
* Modifiche al modello degli indirizzi (es. aggiunta di nuovi segmenti) possono richiedere un aggiornamento della logica di concatenazione e della sezione **Dipendenze**.

---

{% include-markdown "signature-core.md" %}