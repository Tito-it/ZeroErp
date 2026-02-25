## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_note_validate_generic()`

> 👀 **Vedi anche**
>
> • [vendite.note](/dbzero/vendite/tabelle/note)  
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)  

---

### 🎯 Scopo Principale

La trigger function `vendite.trgfn_note_validate_generic()` valida la coerenza
delle note ancorate a una riga documento (`anchor_tipo = 'RIGA'`), verificando
che `target_riga_id` appartenga davvero alla testata indicata da `target_id`.

---

### ✅ Regole principali

* se `anchor_tipo <> 'RIGA'` non applica controlli di appartenenza;
* per note a riga:
  * `target_riga_id` e` obbligatorio;
  * la tabella righe configurata in `TG_ARGV` deve esistere;
  * la FK della riga verso la testata deve coincidere con `NEW.target_id`;
* in caso di mismatch/config errata genera errore tramite `script.fn_log_and_raise_error`.

---

### 🧩 Utilizzo

Viene usata come validatore generico su trigger `BEFORE INSERT/UPDATE` delle
tabelle note dominio vendite, evitando note agganciate a righe non coerenti.

---

{% include-markdown "signature-core.md" %}
