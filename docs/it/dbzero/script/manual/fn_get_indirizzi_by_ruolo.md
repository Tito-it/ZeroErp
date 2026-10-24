
## 📘 Documentazione Concettuale – Funzione `script.fn_get_indirizzi_by_ruolo`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**  
>
• [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi)   
> • [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)    
> • [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi)    
> • [config.comuni](/dbzero/config/tabelle/comuni)   
> • [config.codici_postali](/dbzero/config/tabelle/codici_postali)   
> • [config.province](/dbzero/config/tabelle/province)   
> • [config.stati](/dbzero/config/tabelle/stati)    

---
### 🎯 Scopo Principale
(latest review 25-03-26)
Restituisce gli **indirizzi** associati a uno specifico `soggetto_ruolo`, con filtro opzionale per **istanza utility**, producendo per ciascuno:

* il **tipo di indirizzo** (`codice_interno`) e indicazione se **normalizzato**;
* una stringa **human‑readable** dell’**indirizzo completo** secondo regole di priorità;
* la **migliore geolocalizzazione disponibile** (priorità civico → indirizzo);
* i **dati strutturati territoriali**, recuperati anche attraverso *fallback logico*:

  * `comune_id`, `comune_descrizione`,
  * `provincia_id`, `provincia_sigla`,
  * `stato_id`, `stato_iso2`, `stato_descrizione`,
  * `cap_codice`.

Questa funzione usa il layer **RUOLO** come sorgente master e legge dalla vista resolved base.
Non applica fallback su indirizzi soggetto (la policy master/fallback e demandata a `script.fn_get_indirizzo`).

Se `p_istanza_utility_id` è valorizzato, restituisce solo gli indirizzi della istanza specifica + quelli generici (istanza NULL). Se `p_istanza_utility_id` è NULL, restituisce tutti gli indirizzi del ruolo.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION script.fn_get_indirizzi_by_ruolo(
  p_soggetto_ruolo_id  anagrafiche.soggetti_ruoli.id%TYPE,
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
  ...campi geografici (stato, regione, provincia, comune, CAP, locality, ecc.)
)
LANGUAGE sql
STABLE;
```

---

### Parametri di input

| Nome | Tipo | Obbligatorio | Descrizione |
| --- | --- | :---: | --- |
| `p_soggetto_ruolo_id` | `bigint` | si | ID della relazione in `anagrafiche.soggetti_ruoli` a cui sono collegati gli indirizzi. |
| `p_istanza_utility_id` | `bigint` | no | ID della istanza utility (`anagrafiche.istanze_utilities.id`). Se valorizzato filtra per istanza specifica + generici (NULL). Se NULL restituisce tutti. |

---

### Valori restituiti


| Colonna              | Tipo       | Descrizione                                                                          |
| -------------------- | ---------- | ------------------------------------------------------------------------------------ |
| `tipo_indirizzo`     | varchar    | Codice interno da `config.tipi_indirizzi.codice_interno`.                            |
| `indirizzo_completo` | text       | Indirizzo formattato human-readable secondo logica A/B/C.                            |
| `geoloc`             | geometry   | Geometria preferenziale → `civic_geoloc` → `ai.geoloc`.                              |
| `indirizzo_id`       | bigint     | Identificativo tecnico dell’indirizzo.                                               |
| `soggetto_ruolo_id`  | bigint     | ID del soggetto/ruolo associato.                                                     |
| `tipo_indirizzo_id`  | integer    | ID tecnico del tipo indirizzo.                                                       |
| `indirizzo_dettaglio_id` | bigint | FK al dettaglio civico, se presente.                                                 |
| `indirizzo_libero`   | text       | Indirizzo libero (se non normalizzato).                                              |
| `is_normalizzato`    | boolean    | TRUE se collegato a `indirizzo_dettaglio`.                                           |
| `comune_id`          | integer    | Comune recuperato da `ai.comune_id`, o da `stradario` tramite `indirizzo_dettaglio`. |
| `comune_descrizione` | text       | Nome del comune.                                                                     |
| `provincia_id`       | integer    | Provincia collegata al comune.                                                       |
| `provincia_sigla`    | text       | Sigla della provincia (es. RM, MI).                                                  |
| `provincia_descrizione` | text    | Descrizione estesa della provincia.                                                  |
| `stato_id`           | integer    | Stato recuperato da `ai.stato_id`, o se NULL da comune/provincia.                    |
| `stato_iso2`         | varchar(2) | Codice ISO2.                                                                         |
| `stato_descrizione`  | text       | Nome dello stato.                                                                    |
| `regione_id`         | integer    | Regione associata alla provincia.                                                    |
| `regione_descrizione`| text       | Nome della regione.                                                                  |
| `codice_postale_id`  | integer    | ID tecnico del codice postale.                                                       |
| `cap_codice`         | varchar    | Codice CAP (solo se italiano).                                                       |
| `locality`           | varchar    | Località (uso internazionale).                                                       |
| `administrative_area`| varchar    | Area amministrativa (uso internazionale).                                            |
| `sublocality`        | varchar    | Sublocalità (uso internazionale).                                                    |
| `postal_code`        | varchar    | Codice postale libero della forma estera (facoltativo; era `postal_box` fino al 18-10-2026). |

---

### 🗺️ Logica (attuale)

1. Legge da `anagrafiche.vw_indirizzi_resolved_base`.
2. Filtra `scope = 'RUOLO'`.
3. Filtra per `soggetto_ruolo_id = p_soggetto_ruolo_id`.
4. Se `p_istanza_utility_id` è valorizzato: filtra `istanza_utility_id = p_istanza_utility_id OR istanza_utility_id IS NULL`.
5. Ordina per `tipo_indirizzo_codice, istanza_utility_id NULLS LAST, indirizzo_id`.

---

### Dipendenze principali

* `anagrafiche.vw_indirizzi_resolved_base`
* `anagrafiche.vw_indirizzi_resolved_ruolo`

---

### Proprietà tecniche

| Proprietà      | Valore                           |
| -------------- | -------------------------------- |
| Determinismo   | `STABLE`                         |
| Parallelismo   | `PARALLEL UNSAFE`                |
| Ordinamento    | `ORDER BY tipo_indirizzo`        |
| Indicizzazione | Ottimale per FK su tutte le join |
| Sicurezza      | Nessun effetto collaterale       |

---

### Esempi d’uso

```sql
-- Tutti gli indirizzi del ruolo
SELECT * FROM script.fn_get_indirizzi_by_ruolo(123);

-- Solo indirizzi per istanza GAS (id=1) + generici
SELECT * FROM script.fn_get_indirizzi_by_ruolo(123, 1);

-- Solo indirizzi normalizzati
SELECT * FROM script.fn_get_indirizzi_by_ruolo(123)
WHERE is_normalizzato;
```

---

### Note e Best Practice

* Prediligere **normalizzati (A)** per qualità del dato.
* Il fallback logico permette alta robustezza anche in fase di migrazione/import.
* L’ordinamento per tipo indirizzo consente utilizzo diretto nelle viste applicative.
* Per casi multi-record (inconsitenza), demandare a test pgTAP o funzione wrapper per errore.

---

{% include-markdown "signature-core.md" %}
\
