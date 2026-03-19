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
*(latest review 01-12-25)*
La funzione **`script.fn_get_indirizzo`** restituisce **uno o più indirizzi tecnici** associati a un determinato **`soggetto_ruolo`**, filtrando per **tipo di indirizzo** identificato dal **codice interno** (`config.tipi_indirizzi.codice_interno`).

La funzione:

* **non implementa** la logica di composizione dell’indirizzo,
* **delega integralmente** il recupero e la normalizzazione dei dati a `script.fn_get_indirizzi_by_ruolo`,
* aggiunge una logica di **fallback multi-livello** basata sulla matrice di configurazione
  [`config.tipi_ruolo_tipi_indirizzo`](/dbzero/config/tabelle/tipi_ruolo_tipi_indirizzo).
* se il layer ruolo non risolve alcun indirizzo, applica fallback sul layer soggetto
  tramite `script.fn_get_indirizzo_by_soggetto`.

In pratica:

> “Dammi l’indirizzo per questo tipo dal layer ruolo; se non esiste, segui la catena fallback del ruolo e, in ultima istanza, usa il layer soggetto.”

📌 **Nota di ambito**
La funzione opera con policy:
* **master** su `soggetto_ruolo` (matrice **ruolo ↔ tipo indirizzo**),
* **fallback finale** su indirizzi diretti del soggetto (matrice `config.tipi_soggetto_dettaglio_tipi_indirizzo`).

---

### Firma (reale)

```sql
CREATE OR REPLACE FUNCTION script.fn_get_indirizzo(
  p_soggetto_ruolo_id bigint,
  p_tipo_codice       character varying
)
RETURNS TABLE(
  tipo_indirizzo          character varying,
  indirizzo_completo     text,
  geoloc                 geometry,
  indirizzo_id           bigint,
  soggetto_ruolo_id      bigint,
  tipo_indirizzo_id      integer,
  indirizzo_dettaglio_id bigint,
  indirizzo_libero       text,
  is_normalizzato        boolean,
  stato_id               integer,
  stato_descrizione      character varying,
  stato_iso2             character,
  regione_id             integer,
  regione_descrizione    character varying,
  provincia_id           integer,
  provincia_sigla        character varying,
  provincia_descrizione  character varying,
  comune_id              integer,
  comune_descrizione     character varying,
  codice_postale_id      integer,
  cap_codice             character,
  locality               character varying,
  administrative_area    character varying,
  sublocality            character varying,
  postal_box             character varying
)
LANGUAGE plpgsql
STABLE
PARALLEL UNSAFE;
```

📌 Il result-set restituito è **identico** a quello prodotto da `script.fn_get_indirizzi_by_ruolo`, con la sola differenza che i record sono **filtrati** per tipo indirizzo e fallback.

---

### Parametri di input

| Nome                  | Tipo      | Descrizione                                                                                              |
| --------------------- | --------- | -------------------------------------------------------------------------------------------------------- |
| `p_soggetto_ruolo_id` | `bigint`  | ID della relazione in `anagrafiche.soggetti_ruoli`.                                                      |
| `p_tipo_codice`       | `varchar` | Codice interno del tipo indirizzo (`config.tipi_indirizzi.codice_interno`, es. `RES`, `FATT`, `SEDEOP`). |

> 🔹 Il tipo indirizzo viene passato tramite **codice interno** (chiave funzionale stabile), non tramite ID tecnico.

---

### Valori restituiti

La funzione restituisce **zero, uno o più record**, tutti con struttura **completa e coerente**, derivata direttamente da `fn_get_indirizzi_by_ruolo`.

Alcuni campi rilevanti:

| Colonna              | Tipo       | Descrizione                                                                      |
| -------------------- | ---------- | -------------------------------------------------------------------------------- |
| `tipo_indirizzo`     | `varchar`  | Codice interno del tipo indirizzo **effettivamente utilizzato** (post-fallback). |
| `indirizzo_completo` | `text`     | Indirizzo formattato in forma human-readable.                                    |
| `geoloc`             | `geometry` | Geolocalizzazione (SRID 4326), se disponibile.                                   |
| `is_normalizzato`    | `boolean`  | TRUE se derivato da `indirizzi_dettaglio`, FALSE se indirizzo libero/estero.     |
| `indirizzo_id`       | `bigint`   | Identificativo tecnico dell’indirizzo.                                           |
| `tipo_indirizzo_id`  | `integer`  | ID tecnico del tipo indirizzo effettivo.                                         |

📌 Tutti gli altri campi geografici (stato, regione, provincia, comune, CAP) sono già **risolti e coerenti**, in quanto prodotti dalla funzione base.

---

### Logica di funzionamento (concettuale)

La funzione implementa una **ricerca iterativa con fallback configurabile**:

1. Determina il **tipo ruolo** associato al `soggetto_ruolo`.
2. Prova a recuperare indirizzi del tipo richiesto (`p_tipo_codice`) nel layer ruolo.
3. Se vengono trovati uno o più record, **li restituisce e termina**.
4. In assenza di risultati nel layer ruolo:

   * consulta `config.tipi_ruolo_tipi_indirizzo` per individuare un `fallback_tipo_indirizzo_id`,
   * traduce l’ID in `codice_interno`,
   * ripete il tentativo.
5. La catena ruolo termina quando:

   * viene trovato almeno un indirizzo,
   * il fallback è `NULL`,
   * viene rilevato un **loop** nella catena (protezione A → B → A).
6. Se il layer ruolo non produce risultati, applica fallback su `script.fn_get_indirizzo_by_soggetto(...)`.

📌 **Comportamento intenzionale**: la funzione **non solleva errori** se nessun indirizzo è disponibile; restituisce semplicemente zero righe.

---

### Esempio di catena di fallback

| tipo_indirizzo | fallback_tipo_indirizzo |
| -------------- | ----------------------- |
| SEDEOP         | SEDELEG                 |
| FORNITURA      | SEDEOP                  |

Effetto pratico:

```sql
SELECT *
FROM script.fn_get_indirizzo(p_soggetto_ruolo_id, 'FORNITURA');
```

Ordine dei tentativi:

`FORNITURA → SEDEOP → SEDELEG`

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
