## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_istanze_dati_precontrattuali_dettaglio`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle:
>
> * [anagrafiche.istanze_dati_precontrattuali](/dbzero/anagrafiche/tabelle/istanze_dati_precontrattuali)  
> * [config.classi_utenze](/dbzero/config/tabelle/classi_utenze)  
> * [config.tipi_utenze](/dbzero/config/tabelle/tipi_utenze)  
>
> Approfondimenti viste:
>
> * [anagrafiche.vw_istanze_utilities_dettaglio](/dbzero/anagrafiche/views/vw_istanze_utilities_dettaglio)  

---

### 🎯 Scopo Principale

(latest review 09-01-26) 
La vista **`anagrafiche.vw_istanze_dati_precontrattuali_dettaglio`** unisce i dati pre‑contrattuali
con i dettagli dell’istanza utility e le decodifiche di **classe** e **tipo utenza**.
Il **tipo utenza** è derivato dalla classe (`config.classi_utenze.tipo_utenza_id`).

È pensata per **consultazione** e **reportistica**, evitando join ripetitivi in applicazione.

---

### 🧱 Struttura logica della vista

La vista parte da `anagrafiche.istanze_dati_precontrattuali` e aggiunge:

* join a `anagrafiche.vw_istanze_utilities_dettaglio` per i dati dell’istanza utility;
* join a `config.classi_utenze` per descrizione/codice classe;
* join a `config.tipi_utenze` per descrizione/codice tipo utenza (derivato).

---

### 📑 Campi esposti (principali)

| Colonna                           | Tipo      | Descrizione                                                 |
| --------------------------------- | --------- | ----------------------------------------------------------- |
| `istanza_dati_precontrattuali_id` | `bigint`  | Identificativo riga pre‑contrattuale.                       |
| `istanza_utility_id`              | `bigint`  | Istanza utility collegata.                                  |
| `classe_utenza_id`                | `integer` | Classe utenza.                                              |
| `classe_utenza_descrizione`       | `text`    | Descrizione classe.                                         |
| `classe_utenza_codice`            | `text`    | Codice classe.                                              |
| `tipo_utenza_id`                  | `integer` | Tipo utenza (derivato dalla classe).                        |
| `tipo_utenza_descrizione`         | `text`    | Descrizione tipo utenza.                                    |
| `tipo_utenza_codice`              | `text`    | Codice tipo utenza.                                         |
| `param_1_num`                     | `numeric` | Parametro numerico core.                                    |
| `param_2_txt`                     | `text`    | Parametro testuale core.                                    |
| `meta`                            | `jsonb`   | Estensioni specifiche per utility.                          |
| `istanza_id`                      | `bigint`  | Identificativo istanza (da vw_istanze_utilities_dettaglio). |
| `utility_codice`                  | `text`    | Codice utility (da vw_istanze_utilities_dettaglio).         |
| `utility_descrizione`             | `text`    | Descrizione utility (da vw_istanze_utilities_dettaglio).    |

(Sono esposti anche i campi di audit di `istanze_dati_precontrattuali` e i campi di dettaglio istanza.)

---

### 🔍 Modalita' d'uso tipiche

```sql
SELECT *
FROM anagrafiche.vw_istanze_dati_precontrattuali_dettaglio
WHERE istanza_utility_id = :istanza_utility_id;
```

---

### ✅ Best practice e raccomandazioni

* Usare la vista per letture e reportistica.
* Per aggiornamenti/modifiche operare sempre sulle tabelle base.

---
{% include-markdown "signature-core.md" %}
