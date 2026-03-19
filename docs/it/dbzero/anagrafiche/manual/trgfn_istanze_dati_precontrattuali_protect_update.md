## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_istanze_dati_precontrattuali_protect_update()`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**    
>
• [anagrafiche.istanze_dati_precontrattuali](/dbzero/anagrafiche/tabelle/istanze_dati_precontrattuali)    
> • [vendite.contratti_utilities](/dbzero/vendite/manual/contratti_utilities)    
>
**Approfondimento funzioni:**
>
• [`script.fn_log_and_raise_error`](/dbzero/script/funzioni/fn_log_and_raise_error)   

---
### 🎯 Scopo Principale
(latest review 20-01-26)
La funzione `anagrafiche.trgfn_istanze_dati_precontrattuali_protect_update()` impedisce la modifica
o cancellazione dei dati precontrattuali quando sono gia` stati **congelati** in
`vendite.contratti_utilities`.

La funzione e` eseguita da un trigger **BEFORE UPDATE OR DELETE** su
`anagrafiche.istanze_dati_precontrattuali`.

---

### Regola di protezione

Se esiste almeno uno snapshot collegato:

* **UPDATE** → viene bloccato con `script.fn_log_and_raise_error`
* **DELETE** → viene bloccato con `script.fn_log_and_raise_error`

In questo modo si garantisce che:

* il contratto rimanga coerente con lo snapshot;
* ogni correzione richieda la creazione di un **nuovo contratto**.

---

### Contesto operativo

**Tabella controllata:** `anagrafiche.istanze_dati_precontrattuali`  
**Condizione:** esistenza di righe in `vendite.contratti_utilities`
con `istanza_dati_precontrattuali_id = OLD.id`.

---

### Ruolo nel processo

La funzione protegge la stabilita` dei dati che alimentano la fase contrattuale,
imponendo una regola chiara: una volta creato lo snapshot, il dato precontrattuale
non e` piu` modificabile.

---

{% include-markdown "signature-core.md" %}

---
