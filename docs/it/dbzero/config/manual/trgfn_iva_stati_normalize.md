## 📘 Documentazione Concettuale – Funzione `config.trgfn_iva_stati_normalize()`

> 👀 **Vedi anche**
>
Approfondimento Tabelle:
>
[config.iva_stati](/dbzero/config/tabelle/iva_stati)
> [config.stati](/dbzero/config/tabelle/stati)
>
Approfondimento funzioni:
>
[script.fn_get_default_by_param](/dbzero/script/funzioni/fn_get_default_by_param)

---
### 🎯 Scopo Principale
(latest review 15-01-26)
* **Impostare valori di default** per campi mancanti in `config.iva_stati` (ad esempio, assegnare `stato_id` da `config.stati` se `NEW.stato_id` è `NULL`).
* **Pulire e normalizzare** ulteriori campi (es. trimming, uppercasing) seguendo le regole di business.

---

### Collegamenti

* **`config.iva_stati`** – tabella su cui si applica il trigger `BEFORE INSERT OR UPDATE`.
* **`config.stati`** – usata come lookup per recuperare il PK di default tramite `codice_iso3`.
* **`script.fn_get_default_by_param`** – funzione dinamica che esegue il lookup del valore di default da una tabella di configurazione.
* **Trigger associato**: `trg_iva_stati_normalize` (viene creato dal Liquibase changeSet `20250730-07-trgfn_iva_stati_normalize_v1`).

---

### Note Operative

* Il trigger viene invocato **BEFORE INSERT OR UPDATE** su `config.iva_stati` e agisce su **`NEW`**.
* **Assegnazione default**: utilizza `fn_get_default_by_param('config','stati','codice_iso3','state_code_iso3', TG_NAME)::integer` per ottenere il `stato_id`.
* **`TG_NAME`** passa automaticamente il nome del trigger alla funzione per migliorare il contesto di log in caso di errore.
* **Estendibilità**: dopo il lookup di default è possibile inserire ulteriori blocchi di cleanup (es. normalizzazione di `nome`, `cognome`).
* **Robustezza**: la funzione di lookup solleva eccezione se non trova il valore, garantendo coerenza dei dati.

---

> **“Allinea i record di `config.iva_stati` a regole di default e pulizia automatica: default lookup, normalizzazione e coerenza garantita.”**
