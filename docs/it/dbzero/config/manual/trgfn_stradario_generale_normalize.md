## 📘 Documentazione Concettuale – Trigger Function `config.trgfn_stradario_generale_normalize()`

> 👀 **Vedi anche**   
>
**Approfondimento tabelle:**    
>
[config.stradario_generale](/dbzero/config/tabelle/stradario_generale)   
> [config.toponomastica](/dbzero/config/tabelle/toponomastica)   
>
**Approfondimento funzioni:**   
>
[script.fn_norm_via](/dbzero/script/funzioni/fn_norm_via)   
>
🎯 Scopo Principale

(latest review 30-12-25)
Normalizzare automaticamente l'indirizzo dello stradario generale, combinando il prefisso toponomastico con la descrizione della via.

---

### Come Funziona

1. Recupera la descrizione del toponimo (`config.toponomastica.descrizione`) in base a `NEW.toponomastica_id`.
2. Calcola `NEW.indirizzo_normalizzato` tramite `script.fn_norm_via(prefisso, descrizione)`, assicurando una forma coerente e unificata.
3. Restituisce `NEW` con il campo normalizzato aggiornato.

---

### Cosa garantisce

* Coerenza del campo `indirizzo_normalizzato` in insert/update.
* Allineamento automatico quando cambia il toponimo o la descrizione della via.

---

## Trigger Associati

```sql
CREATE TRIGGER trg_stradario_generale_normalize_ins_upd
  BEFORE INSERT OR UPDATE
  ON config.stradario_generale
  FOR EACH ROW
  EXECUTE FUNCTION config.trgfn_stradario_generale_normalize();
```

---

### Note Operative

* Il trigger non modifica altri campi oltre a `indirizzo_normalizzato`.
* La rinormalizzazione puo' essere forzata da `config.trgfn_toponomastica_bump_normalize` quando cambia la descrizione di un toponimo.

---

> **"Normalizzazione centralizzata per garantire indirizzi omogenei e ricercabili."**

