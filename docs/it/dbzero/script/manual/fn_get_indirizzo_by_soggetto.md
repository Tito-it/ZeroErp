## 📘 Documentazione Concettuale – Funzione `script.fn_get_indirizzo_by_soggetto`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti)  
> • [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)  
> • [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi)  
> • [config.tipi_soggetto_dettaglio_tipi_indirizzo](/dbzero/config/tabelle/tipi_soggetto_dettaglio_tipi_indirizzo)  
>
**Approfondimento funzioni:**
>
• [`script.fn_get_indirizzi_by_soggetto`](/dbzero/script/funzioni/fn_get_indirizzi_by_soggetto.md)  
>
**Approfondimento viste:**
>
• [anagrafiche.vw_indirizzi_resolved_soggetto](/dbzero/anagrafiche/views/vw_indirizzi_resolved_soggetto)  

---
### 🎯 Scopo Principale
(latest review 23-12-25)
Restituisce **il miglior indirizzo disponibile** per un soggetto, filtrato per
**tipo indirizzo** (codice interno), con **fallback configurabile** sulla matrice
`config.tipi_soggetto_dettaglio_tipi_indirizzo`.

La funzione:

* non ricompone l’indirizzo,
* usa `anagrafiche.vw_indirizzi_resolved_soggetto` come sorgente,
* segue la catena di fallback (se configurata) in base al tipo soggetto.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION script.fn_get_indirizzo_by_soggetto(
  p_soggetto_id uuid,
  p_tipo_codice character varying
)
RETURNS SETOF anagrafiche.vw_indirizzi_resolved_soggetto
LANGUAGE plpgsql
STABLE
PARALLEL UNSAFE;
```

---

### Parametri di input

| Nome            | Tipo      | Descrizione                                                                 |
| --------------- | --------- | --------------------------------------------------------------------------- |
| `p_soggetto_id` | `uuid`    | ID del soggetto in `anagrafiche.soggetti`.                                  |
| `p_tipo_codice` | `varchar` | Codice interno del tipo indirizzo (`config.tipi_indirizzi.codice_interno`). |

---

### Valori restituiti

La funzione restituisce le stesse colonne della vista:

* `anagrafiche.vw_indirizzi_resolved_soggetto`

Il campo `indirizzo_display` contiene l’indirizzo **human-readable**.

---

### Logica di funzionamento (concettuale)

1. Recupera il `tipo_soggetto_dettaglio_id` del soggetto.
2. Prova il tipo richiesto (`p_tipo_codice`). ⭐ Lo riconosce **per id** (rev 2026-09-23,
   `20260923-49`): il codice interno si risolve in `config.tipi_indirizzi.id` e si confronta con
   `tipo_indirizzo_id` della vista. La vista espone in `tipo_indirizzo_codice` il **codice** (etichetta
   a video, es. `RESID`), non il codice interno (`RES`): confrontati come testo non si incontravano.
3. Se non trova indirizzi, cerca il `fallback_tipo_indirizzo_id` nella matrice:

   `config.tipi_soggetto_dettaglio_tipi_indirizzo`

4. Ripete finché:

   * trova almeno un indirizzo,
   * il fallback è `NULL`,
   * viene rilevato un loop nella catena.

---

### Esempi d’uso

```sql
SELECT *
FROM script.fn_get_indirizzo_by_soggetto(:soggetto_id, 'RES');
```

```sql
-- Fallback automatico su altro tipo se RES non presente
SELECT *
FROM script.fn_get_indirizzo_by_soggetto(:soggetto_id, 'DOMFISC');
```

---

### Note e Best Practice

* La funzione non solleva errori: se non trova nulla, restituisce zero righe.
* La catena di fallback e la validita temporale sono determinate dalla matrice di configurazione.

---

{% include-markdown "signature-core.md" %}
