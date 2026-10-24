## 📘 Documentazione Concettuale – Funzione `script.fn_get_indirizzo`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi)   
> • [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)  
> • [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)   
> • [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi)  
> • [config.tipi_ruolo_tipi_indirizzo](/dbzero/config/tabelle/tipi_ruolo_tipi_indirizzo)  
> • [config.comuni](/dbzero/config/tabelle/comuni)  
> • [config.codici_postali](/dbzero/config/tabelle/codici_postali)  
>
**Approfondimento funzioni:**
>
• [`script.fn_get_indirizzi_by_ruolo`](/dbzero/script/funzioni/fn_get_indirizzi_by_ruolo.md)  

---
### 🎯 Scopo Principale
*(latest review 25-03-26)*
La funzione **`script.fn_get_indirizzo`** restituisce **uno o più indirizzi tecnici** associati a un determinato **`soggetto_ruolo`**, filtrando per **tipo di indirizzo** identificato dal **codice interno** (`config.tipi_indirizzi.codice_interno`) e opzionalmente per **istanza utility** (`anagrafiche.istanze_utilities.id`).

La funzione:

* **non implementa** la logica di composizione dell’indirizzo,
* **delega integralmente** il recupero e la normalizzazione dei dati a `script.fn_get_indirizzi_by_ruolo`,
* aggiunge una logica di **fallback a 3 livelli** (istanza → generico → soggetto) con catena tipo basata sulla matrice di configurazione
  [`config.tipi_ruolo_tipi_indirizzo`](/dbzero/config/tabelle/tipi_ruolo_tipi_indirizzo).
* se il layer ruolo non risolve alcun indirizzo, applica fallback sul layer soggetto
  tramite `script.fn_get_indirizzo_by_soggetto`.

In pratica:

> “Dammi l’indirizzo per questo tipo: prima cerca nel layer ruolo per la istanza specifica, poi nel layer ruolo generico, poi nel layer soggetto — applicando la catena fallback tipo a ogni livello.”

📌 **Nota di ambito**
La funzione opera con policy a **3 livelli**:

* **Livello 1**: ruolo + istanza specifica (se `p_istanza_utility_id` valorizzato)
* **Livello 2**: ruolo generico (istanza NULL)
* **Livello 3**: fallback finale su indirizzi diretti del soggetto (matrice `config.tipi_soggetto_dettaglio_tipi_indirizzo`)

---

### Firma (reale)

```sql
CREATE OR REPLACE FUNCTION script.fn_get_indirizzo(
  p_soggetto_ruolo_id  anagrafiche.soggetti_ruoli.id%TYPE,
  p_tipo_codice        config.tipi_indirizzi.codice_interno%TYPE,
  p_istanza_utility_id anagrafiche.istanze_utilities.id%TYPE DEFAULT NULL
)
RETURNS TABLE(
  tipo_indirizzo         config.tipi_indirizzi.codice_interno%TYPE,
  indirizzo_completo     text,
  geoloc                 geometry,
  indirizzo_id           anagrafiche.indirizzi.id%TYPE,
  soggetto_ruolo_id      anagrafiche.indirizzi.soggetto_ruolo_id%TYPE,
  istanza_utility_id     anagrafiche.indirizzi.istanza_utility_id%TYPE,
  tipo_indirizzo_id      anagrafiche.indirizzi.tipo_indirizzo_id%TYPE,
  indirizzo_dettaglio_id anagrafiche.indirizzi.indirizzo_dettaglio_id%TYPE,
  indirizzo_libero       anagrafiche.indirizzi.indirizzo_libero%TYPE,
  is_normalizzato        boolean,
  ...campi geografici (stato, regione, provincia, comune, CAP, locality, administrative_area, sublocality, postal_code)
)
LANGUAGE plpgsql
STABLE ROWS 10;
```

📌 Il result-set include ora `istanza_utility_id`. La struttura è identica a `script.fn_get_indirizzi_by_ruolo`, con i record filtrati per tipo indirizzo e cascata fallback.

---

### Parametri di input

| Nome                  | Tipo      | Obbligatorio | Descrizione                                                                                              |
| --------------------- | --------- | :---: | -------------------------------------------------------------------------------------------------------- |
| `p_soggetto_ruolo_id` | `bigint`  | si | ID della relazione in `anagrafiche.soggetti_ruoli`.                                                      |
| `p_tipo_codice`       | `varchar` | si | Codice interno del tipo indirizzo (`config.tipi_indirizzi.codice_interno`, es. `RES`, `FATT`, `SEDEOP`). |
| `p_istanza_utility_id` | `bigint` | no | ID della istanza utility (`anagrafiche.istanze_utilities.id`). Se NULL, salta il livello 1 e parte dal livello 2 (ruolo generico). |

> 🔹 Il tipo indirizzo viene passato tramite **codice interno** (chiave funzionale stabile), non tramite ID tecnico.

---

### Valori restituiti

La funzione restituisce **zero, uno o più record**, tutti con struttura **completa e coerente**, derivata direttamente da `fn_get_indirizzi_by_ruolo`.

Alcuni campi rilevanti:

| Colonna              | Tipo       | Descrizione                                                                      |
| -------------------- | ---------- | -------------------------------------------------------------------------------- |
| `tipo_indirizzo`     | `varchar`  | **Codice** del tipo effettivamente utilizzato (post-fallback): l'etichetta a video di `config.tipi_indirizzi.codice` (es. `DOM-FISC`), **non** il codice interno, anche se la firma lo dichiara `codice_interno%TYPE`. Per la logica si legge `tipo_indirizzo_id`. |
| `indirizzo_completo` | `text`     | Indirizzo formattato in forma human-readable.                                    |
| `geoloc`             | `geometry` | Geolocalizzazione (SRID 4326), se disponibile.                                   |
| `is_normalizzato`    | `boolean`  | TRUE se derivato da `indirizzi_dettaglio`, FALSE se indirizzo libero/estero.     |
| `indirizzo_id`       | `bigint`   | Identificativo tecnico dell’indirizzo.                                           |
| `tipo_indirizzo_id`  | `integer`  | ID tecnico del tipo indirizzo effettivo.                                         |

📌 Tutti gli altri campi geografici (stato, regione, provincia, comune, CAP) sono già **risolti e coerenti**, in quanto prodotti dalla funzione base.

---

### Logica di funzionamento (concettuale)

La funzione implementa una **ricerca a 3 livelli**, ciascuno con catena fallback tipo:

**FASE 1 — Ruolo + istanza specifica** (solo se `p_istanza_utility_id` è valorizzato):

1. Cerca indirizzi con `istanza_utility_id = p_istanza_utility_id` per il tipo richiesto.
2. Se non trovati, segue la catena fallback tipo sulla matrice `config.tipi_ruolo_tipi_indirizzo`.
3. Se trovati, restituisce e termina.

**FASE 2 — Ruolo generico** (istanza NULL):

1. Cerca indirizzi con `istanza_utility_id IS NULL` per il tipo richiesto.
2. Se non trovati, segue la catena fallback tipo.
3. Se trovati, restituisce e termina.

**FASE 3 — Fallback soggetto**:

1. Delega a `script.fn_get_indirizzo_by_soggetto(...)` con la propria catena fallback tipo.

⭐ **Il tipo si riconosce per id** (rev 2026-09-23, `20260923-49`): a ogni giro della catena il
codice interno richiesto si risolve in `config.tipi_indirizzi.id` e si confronta con
`tipo_indirizzo_id`. Le viste risolte espongono il **codice**, non il codice interno: confrontati
come testo, i due si incontravano solo per i tipi in cui coincidono (`FATT`), e per `RES`,
`DOMFISC`, `SEDELEG`, `SEDEOP` e gli altri nessuna fase trovava mai niente.

La catena tipo a ogni livello termina quando:

* viene trovato almeno un indirizzo,
* il fallback è `NULL`,
* viene rilevato un **loop** nella catena (protezione A → B → A).

📌 **Comportamento intenzionale**: la funzione **non solleva errori** se nessun indirizzo è disponibile; restituisce semplicemente zero righe.

---

### Esempio di cascata con istanza

Soggetto Titini, ruolo CLIENTE (id=64), istanza GAS (id=1):

```sql
-- Con istanza: cerca prima GAS, poi generico, poi soggetto
SELECT * FROM script.fn_get_indirizzo(64, 'FATT', 1);
```

Ordine dei tentativi:

1. `FATT` con `istanza_utility_id = 1` (GAS)
2. `FATT` con `istanza_utility_id IS NULL` (generico)
3. `FATT` dal layer soggetto (con propria catena fallback tipo)

### Esempio di catena fallback tipo (senza utility)

```sql
SELECT * FROM script.fn_get_indirizzo(63, 'FORNITURA');
```

Ordine: `FORNITURA → SEDEOP → SEDELEG` (catena da matrice `tipi_ruolo_tipi_indirizzo`)

---

### Proprietà tecniche

| Attributo    | Valore            | Note                                              |
| ------------ | ----------------- | ------------------------------------------------- |
| Stabilità    | `STABLE`          | Funzione di sola lettura su dati e configurazione |
| Parallelismo | `PARALLEL UNSAFE` | Uso di `geometry` e logica iterativa              |
| Semantica    | Multi-row         | Può restituire più righe per lo stesso tipo       |

---

### Esempi d’uso

```sql
-- 1) Indirizzo SEDEOP per un Gestore, con fallback su SEDELEG
SELECT *
FROM script.fn_get_indirizzo(63, 'SEDEOP');

-- 2) Uso in JOIN laterale
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
