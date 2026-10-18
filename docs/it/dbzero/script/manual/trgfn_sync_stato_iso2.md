## 📘 Documentazione Concettuale – Funzione `script.trgfn_sync_stato_iso2()`

> 👀 **Vedi anche**
>
Approfondimento Tabelle:
>
[config.stati](/dbzero/config/tabelle/stati)
>
Approfondimento Funzioni:
>
[script.fn_stato_proposto_id](/dbzero/script/funzioni/fn_stato_proposto_id)

---
### 🎯 Scopo Principale
* **Sincronizzazione automatica** del campo `stato_iso2` all’interno delle tabelle che lo richiedono.
* **Garantire coerenza** tra il campo `stato_id` e il relativo `codice_iso2`, estraendolo dinamicamente da `config.stati`.

---

### Collegamenti

* **`config.stati`** – tabella sorgente contenente la relazione tra `id` (PK) e `codice_iso2`.
* La funzione può essere collegata a qualunque tabella che:
  - Contiene i campi `stato_id` e `stato_iso2`
  - Richiede aggiornamento automatico del campo `stato_iso2` da lookup su `config.stati`.

---

### Dettagli Tecnici

```sql
CREATE OR REPLACE FUNCTION script.trgfn_sync_stato_iso2()
RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  -- Sincronizza stato_iso2 da config.stati basandosi su stato_id
  SELECT s.codice_iso2
    INTO NEW.stato_iso2
    FROM config.stati s
   WHERE s.id = NEW.stato_id;
  RETURN NEW;
END;
$$;
