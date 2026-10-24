## 📘 Documentazione Concettuale – Trigger Function `config.trgfn_toponomastica_normalize()`

> 👀 **Vedi anche**   
>
**Approfondimento tabelle:**    
>
[config.toponomastica](/dbzero/config/tabelle/toponomastica)   
> [config.stati](/dbzero/config/tabelle/stati)   
>
**Approfondimento funzioni:**   
>
[script.fn_stato_proposto_id](/dbzero/script/funzioni/fn_stato_proposto_id)   
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)   

---
### 🎯 Scopo Principale
(latest review 02-01-26)

Impostare lo `stato_id` di default per la toponomastica e garantire che il valore sia sempre presente.

---

### Come Funziona

1. Se `NEW.stato_id` e' NULL, lo stato proposto da `script.fn_stato_proposto_id` (parametro `STATO_PROPOSTO_ISO2`; rev 18-10-2026, prima `state_code_iso3`).
2. Se dopo il default il valore e' ancora NULL, blocca l'operazione con errore applicativo.

---

### 🚨 Errori Gestiti

| Codice errore           | Quando si verifica                           |
| ----------------------- | -------------------------------------------- |
| **E_STATO_ID_REQUIRED** | `stato_id` assente e default non configurato |

---

## Trigger Associato

```sql
CREATE TRIGGER trg_toponomastica_normalize_ins_upd
  BEFORE INSERT OR UPDATE
  ON config.toponomastica
  FOR EACH ROW
  EXECUTE FUNCTION config.trgfn_toponomastica_normalize();
```

---

### Note Operative

* Il default e' guidato dal parametro `STATO_PROPOSTO_ISO2` in `config.parameters`, che si puo' cambiare per utente o sessione. Il controllo «ancora NULL» resta come rete: il lettore si ferma prima, col suo codice.
* La validazione finale impedisce di creare toponimi senza stato.

---

> **"Toponomastica sempre coerente: default da parametro e blocco se mancante."**

