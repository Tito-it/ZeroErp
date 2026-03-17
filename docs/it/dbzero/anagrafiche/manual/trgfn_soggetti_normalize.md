## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_soggetti_normalize()`

> 👀 **Vedi anche**
>
Approfondimento Tabelle:
>
[anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> [config.stati](/dbzero/config/tabelle/stati)
>
Approfondimento funzioni:
>
[script.fn_get_default_by_param](/dbzero/script/funzioni/fn_get_default_by_param)

---

### 🎯 Scopo Principale

(latest review 28-12-25)
* **Impostare valori di default** per campi mancanti in `anagrafiche.soggetti` (ad esempio, assegnare `stato_id` da `config.stati` se `NEW.stato_id` è `NULL`).
* **Pulire e normalizzare** ulteriori campi (es. trimming, uppercasing) seguendo le regole di business.

---

### Collegamenti

* **`anagrafiche.soggetti`** – tabella su cui si applica il trigger `BEFORE INSERT OR UPDATE`.
* **`config.stati`** – usata come lookup per recuperare il PK di default tramite `codice_iso3`.
* **`script.fn_get_default_by_param`** – funzione dinamica che esegue il lookup del valore di default da una tabella di configurazione.
* **Trigger associato**: `trg_soggetti_normalize_ins_upd` (viene creato dal  `trgfn_soggetti_normalize`).

---

### Note Operative

* Il trigger viene invocato **BEFORE INSERT OR UPDATE** su `anagrafiche.soggetti` e agisce su **`NEW`**.
* **Assegnazione default**: utilizza `fn_get_default_by_param('config','stati','codice_iso3','state_code_iso3', TG_NAME)::integer` per ottenere il `stato_id`.
* **`TG_NAME`** passa automaticamente il nome del trigger alla funzione per migliorare il contesto di log in caso di errore.
* **Estendibilità**: dopo il lookup di default è possibile inserire ulteriori blocchi di cleanup (es. normalizzazione di `nome`, `cognome`).
* **Robustezza**: la funzione di lookup solleva eccezione se non trova il valore, garantendo coerenza dei dati.

---

> **“Allinea i record di `anagrafiche.soggetti` a regole di default e pulizia automatica: default lookup, normalizzazione e coerenza garantita.”**
