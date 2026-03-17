## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_sepa_mandati_guard()`

> 👀 **Vedi anche**   
>
**Approfondimento tabelle:**    
>
[pagamenti.sepa_mandati](/dbzero/pagamenti/tabelle/sepa_mandati)   
>
**Approfondimento Funzioni:**   
>
[anagrafiche.fn_log_and_raise_error](/dbzero/anagrafiche/funzioni/fn_log_and_raise_error)   
> [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed)   

---

### 🎯 Scopo Principale

(latest review 29-12-25)
Garantire che un mandato SEPA sia coerente quando e' in stato **ATTIVO** e normalizzare i campi di input sensibili (`umr`, `iban_snapshot`).

---

### Come Funziona

1. **Validazione stato**
   * Se `NEW.stato = 'ATTIVO'` allora `NEW.data_attivazione` deve essere valorizzata.
   * In caso contrario, genera errore applicativo con `anagrafiche.fn_log_and_raise_error`.
2. **Normalizzazione UMR**
   * Se presente, rimuove spazi multipli e consecutivi da `NEW.umr`.
3. **Normalizzazione IBAN snapshot**
   * Se presente, rimuove gli spazi e forza il maiuscolo su `NEW.iban_snapshot`.

---

### Parametri del Trigger

* `NEW`: record in fase di INSERT o UPDATE su `pagamenti.sepa_mandati`.
* `OLD`: record precedente (non usato).

---

### Valore di Ritorno

* **`NEW`**: record con campi normalizzati e validati.

---

## Trigger Associato

```sql
CREATE TRIGGER trg_sepa_mandati_guard
  BEFORE INSERT OR UPDATE
  ON pagamenti.sepa_mandati
  FOR EACH ROW
  EXECUTE FUNCTION anagrafiche.trgfn_sepa_mandati_guard();
```

---

### 🚨 Errori Gestiti

| Codice errore                  | Quando si verifica                      |
| ------------------------------ | --------------------------------------- |
| **E_DATA_ATTIVAZIONE_MANDATO** | Stato `ATTIVO` senza `data_attivazione` |

Gli errori sono prodotti tramite:
`anagrafiche.fn_log_and_raise_error('<contesto>', '<funzione>', '<codice>', <meta>, ...)`.

---

### Note Operative

* La normalizzazione di `umr` e `iban_snapshot` riduce duplicazioni dovute a spazi e formattazioni diverse.
* La validazione su `data_attivazione` e' un vincolo di business: un mandato attivo deve avere data di attivazione.

---

> **"Un mandato SEPA attivo deve avere data valida; UMR e IBAN vengono sempre normalizzati."**

