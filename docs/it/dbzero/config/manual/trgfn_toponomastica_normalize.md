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
[script.fn_get_default_by_param](/dbzero/script/funzioni/fn_get_default_by_param)   
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)   

---

### 🎯 Scopo Principale

(latest review 02-01-26)

Impostare lo `stato_id` di default per la toponomastica e garantire che il valore sia sempre presente.

---

### Come Funziona

1. Se `NEW.stato_id` e' NULL, recupera il default da `script.fn_get_default_by_param` (parametro `state_code_iso3`).
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

* Il default e' guidato dal parametro `state_code_iso3` in `config.parameters`.
* La validazione finale impedisce di creare toponimi senza stato.

---

> **"Toponomastica sempre coerente: default da parametro e blocco se mancante."**

