## 📘 Documentazione Concettuale – Trigger Function `config.trgfn_comuni_protect_update()`

> 👀 **Vedi anche**   
>
**Approfondimento tabelle:**    
>
[config.comuni](/dbzero/config/tabelle/comuni)   
> [config.stradario](/dbzero/config/tabelle/stradario)   
>
**Approfondimento funzioni:**   
>
[script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)   
>
🎯 Scopo Principale

(latest review 29-12-25)
Impedire la modifica dei campi chiave di `config.comuni` quando il comune e' gia' utilizzato nello stradario.

---

### Come Funziona

1. Verifica se il comune e' referenziato in `config.stradario`.
2. Se **non** e' usato, consente l'UPDATE.
3. Se e' usato, blocca la modifica di:
   * `descrizione`
   * `provincia_id`
   * `extra_country`

In caso di modifica, genera errore applicativo con `script.fn_log_and_raise_error`.

---

### 🚨 Errori Gestiti

| Codice errore                  | Quando si verifica                           |
| ------------------------------ | -------------------------------------------- |
| **E_COLONNA_NON_MODIFICABILE** | Modifica di un campo chiave su comune in uso |

---

## Trigger Associato

```sql
CREATE TRIGGER trg_comuni_a10_protect_update_upd
  BEFORE UPDATE
  ON config.comuni
  FOR EACH ROW
  EXECUTE FUNCTION config.trgfn_comuni_protect_update();
```

---

### Note Operative

* La protezione e' applicata **solo** se il comune risulta in uso nello stradario.
* I campi di audit restano aggiornabili tramite i trigger standard.

---

> **"Un comune in uso non si modifica: si crea un nuovo riferimento e si riallineano le dipendenze."**

