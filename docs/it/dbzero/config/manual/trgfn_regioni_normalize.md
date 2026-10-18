## 📘 Documentazione Concettuale – Funzione `config.trgfn_regioni_normalize()`

> 👀 **Vedi anche**
>
Approfondimento Tabelle:
>
[config.regioni](/dbzero/config/tabelle/regioni)
> [config.stati](/dbzero/config/tabelle/stati)
>
Approfondimento funzioni:
>
[script.fn_stato_proposto_id](/dbzero/script/funzioni/fn_stato_proposto_id)

---
### 🎯 Scopo Principale
(latest review 15-01-26)
* **Impostare valori di default** per campi mancanti in `config.regioni` (ad esempio, assegnare `stato_id` da `config.stati` se `NEW.stato_id` è `NULL`).
* **Pulire e normalizzare** ulteriori campi (es. trimming, uppercasing) seguendo le regole di business.

---

### Collegamenti

* **`config.regioni`** – tabella su cui si applica il trigger `BEFORE INSERT OR UPDATE`.
* **`config.stati`** – lo stato proposto si cerca per `codice_iso2`.
* **`script.fn_stato_proposto_id`** – lo stato proposto (parametro `STATO_PROPOSTO_ISO2`): valida e non ripiega (rev 18-10-2026; prima `fn_get_default_by_param` su `state_code_iso3`, ritirati).
* **Trigger associato**: `trg_regioni_normalize` (viene creato dal Liquibase changeSet `20250730-07-trgfn_regioni_normalize_v1`).

---

### Note Operative

* Il trigger viene invocato **BEFORE INSERT OR UPDATE** su `config.regioni` e agisce su **`NEW`**.
* **Assegnazione default**: `stato_id` non detto = `script.fn_stato_proposto_id(TG_NAME)`. Se il parametro manca, è vuoto o indica più stati, l'inserimento si ferma con un errore che lo dice (`E_CONFIG_MANCANTE`, `E_DEFAULT_ERRATO`, `E_STATO_ISO2_AMBIGUO`).
* **`TG_NAME`** passa automaticamente il nome del trigger alla funzione per migliorare il contesto di log in caso di errore.
* **Estendibilità**: dopo il lookup di default è possibile inserire ulteriori blocchi di cleanup (es. normalizzazione di `nome`, `cognome`).
* **Robustezza**: la funzione di lookup solleva eccezione se non trova il valore, garantendo coerenza dei dati.

---

> **“Allinea i record di `config.regioni` a regole di default e pulizia automatica: default lookup, normalizzazione e coerenza garantita.”**
