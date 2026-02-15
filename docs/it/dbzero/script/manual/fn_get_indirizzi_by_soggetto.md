## 📘 Documentazione Concettuale – Funzione `script.fn_get_indirizzi_by_soggetto`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti)  
> • [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)  
> • [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)  
> • [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi)  
>
> **Approfondimento viste:**
>
> • [anagrafiche.vw_indirizzi_resolved_soggetto](/dbzero/anagrafiche/views/vw_indirizzi_resolved_soggetto)  
> • [anagrafiche.vw_indirizzi_resolved_all](/dbzero/anagrafiche/views/vw_indirizzi_resolved_all)  

---

### 🎯 Scopo Principale
(latest review 15-02-26)
Restituisce tutti gli **indirizzi** associati direttamente a un **soggetto** (`anagrafiche.indirizzi_soggetti`), utilizzando come sorgente la vista
`anagrafiche.vw_indirizzi_resolved_soggetto` per ottenere un output **uniforme e human-readable**.

Questa funzione:

* centralizza la lettura del layer **SOGGETTO**,
* evita duplicazione della logica di composizione,
* garantisce ordinamento deterministico (`tipo_indirizzo_codice`, `indirizzo_id`).

---

### 🧩 Firma

```sql
CREATE OR REPLACE FUNCTION script.fn_get_indirizzi_by_soggetto(
  p_soggetto_id uuid
)
RETURNS SETOF anagrafiche.vw_indirizzi_resolved_soggetto
LANGUAGE sql
STABLE
PARALLEL UNSAFE;
```

---

### 🔢 Parametri di input

| Nome            | Tipo   | Descrizione                                |
| --------------- | ------ | ------------------------------------------ |
| `p_soggetto_id` | `uuid` | ID del soggetto in `anagrafiche.soggetti`. |

---

### 📤 Valori restituiti

La funzione restituisce le stesse colonne della vista:

* `anagrafiche.vw_indirizzi_resolved_soggetto`

con i campi principali:

* `tipo_indirizzo_codice`
* `indirizzo_display` (human-readable)
* `is_normalizzato`
* `comune_descrizione`, `cap`, `provincia`
* `geoloc`

---

### 🧪 Esempi d’uso

```sql
SELECT *
FROM script.fn_get_indirizzi_by_soggetto(:soggetto_id);
```

```sql
-- Solo indirizzi normalizzati
SELECT *
FROM script.fn_get_indirizzi_by_soggetto(:soggetto_id)
WHERE is_normalizzato = TRUE;
```

---

### ✅ Note e Best Practice

* Usare questa funzione come **entry point** per gli indirizzi soggetto.
* La provenienza e tracciabile nelle viste resolved tramite campo derivato `source`.
* Per risolvere un solo indirizzo con fallback, usare `script.fn_get_indirizzo_by_soggetto`.

---

{% include-markdown "signature-core.md" %}
