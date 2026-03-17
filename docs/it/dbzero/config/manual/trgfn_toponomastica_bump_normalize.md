## 📘 Documentazione Concettuale – Trigger Function `config.trgfn_toponomastica_bump_normalize()`

> 👀 **Vedi anche**   
>
**Approfondimento tabelle:**    
>
[config.toponomastica](/dbzero/config/tabelle/toponomastica)   
> [config.stradario_generale](/dbzero/config/tabelle/stradario_generale)   
>
**Approfondimento funzioni:**   
>
[config.trgfn_stradario_generale_normalize](/dbzero/config/funzioni/trgfn_stradario_generale_normalize)   
>
🎯 Scopo Principale

(latest review 30-12-25)
Forzare la **rinormalizzazione** dei record di `config.stradario_generale` collegati a un toponimo aggiornato, senza modificare l'ID dei record.

---

### Come Funziona

1. Dopo un UPDATE su `config.toponomastica`, esegue un UPDATE "neutro" su `config.stradario_generale`:
   * `SET toponomastica_id = toponomastica_id` sulle righe con `toponomastica_id = NEW.id`.
2. L'UPDATE innesca il trigger `config.trgfn_stradario_generale_normalize`, che rigenera `indirizzo_normalizzato` in base alla nuova descrizione del toponimo.

---

### Cosa fa / ❌ Cosa non fa

* **Aggiorna** la normalizzazione dei record collegati.
* **Non cambia** gli ID di `config.stradario_generale`.
* **Non sposta** riferimenti da un ID a un altro.

Se serve spostare i record su un **nuovo** toponimo, occorre aggiornare esplicitamente `toponomastica_id` nelle righe di `config.stradario_generale` interessate.

---

## Trigger Associato

```sql
CREATE TRIGGER trg_toponomastica_bump_normalize_aft_upd
  AFTER UPDATE OF descrizione
  ON config.toponomastica
  FOR EACH ROW
  EXECUTE FUNCTION config.trgfn_toponomastica_bump_normalize();
```

---

### Note Operative

* Il trigger e' pensato per **riallineare la normalizzazione**, non per gestire migrazioni di ID.
* La politica consigliata rimane: **creare un nuovo toponimo** e riallineare i record di `stradario_generale` se serve cambiare il riferimento.

---

> **"Ricalcola le normalizzazioni quando cambia il prefisso, senza alterare gli ID esistenti."**
