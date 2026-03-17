## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_indirizzi_dettaglio_protect_update()`

> 👀 **Vedi anche**   
>
**Approfondimento tabelle:**    
>
[anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)   
> [config.stradario](/dbzero/config/tabelle/stradario)   
>
**Approfondimento funzioni/procedure:**   
>
[maintenance.proc_bump_indirizzi_dettaglio](/dbzero/maintenance/manual/proc_bump_indirizzi_dettaglio)   
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)   

---

### 🎯 Scopo Principale

(latest review 02-02-26)
Impedire la modifica manuale di `stradario_id` su `anagrafiche.indirizzi_dettaglio` per garantire una riclassificazione coerente e tracciata.

---

### Come Funziona

1. Se e' attiva la manutenzione (`zeroerp.maintenance_indirizzi_dettaglio = 'on'`), consente l'UPDATE.
2. Se non in manutenzione, blocca qualsiasi variazione di `stradario_id` con errore applicativo.

---

### 🚨 Errori Gestiti

| Codice errore                  | Quando si verifica                                      |
| ------------------------------ | ------------------------------------------------------- |
| **E_COLONNA_NON_MODIFICABILE** | Tentativo di cambiare `stradario_id` fuori manutenzione |

---

## Trigger Associato

```sql
CREATE TRIGGER trg_indirizzi_dettaglio_a10_protect_update_upd
  BEFORE UPDATE
  ON anagrafiche.indirizzi_dettaglio
  FOR EACH ROW
  EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_dettaglio_protect_update();
```

---

### Note Operative

* La riclassificazione deve essere effettuata tramite `maintenance.proc_bump_indirizzi_dettaglio(...)`.
* Il guard non blocca aggiornamenti a civico, palazzina, ecc.; agisce solo sul cambio di via.

---

> **"Cambio via solo tramite procedura: coerenza garantita e storico completo."**
