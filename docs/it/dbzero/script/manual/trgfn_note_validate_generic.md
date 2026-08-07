## 📘 Documentazione Concettuale – Funzione `script.trgfn_note_validate_generic()`

> 👀 **Vedi anche**
>
• [vendite.note](/dbzero/vendite/tabelle/note)  
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)  

---
### 🎯 Scopo Principale
La trigger function `script.trgfn_note_validate_generic()` valida la coerenza
delle note ancorate a una riga documento (`anchor_tipo = 'RIGA'`), verificando
che `target_riga_id` appartenga davvero alla testata indicata da `target_id`.

---

### Regole principali

* se `anchor_tipo <> 'RIGA'` non applica controlli di appartenenza;
* per note a riga:
  * `target_riga_id` e` obbligatorio;
  * la tabella righe configurata in `TG_ARGV` deve esistere;
  * la FK della riga verso la testata deve coincidere con `NEW.target_id`;
* in caso di mismatch/config errata genera errore tramite `script.fn_log_and_raise_error`.

---

### Utilizzo

Validatore **generico**: vive in `script` proprio perche' non appartiene a un
dominio solo. E' agganciato a **sette** trigger `BEFORE INSERT/UPDATE` sulle
tabelle note — `note_contratto`, `note_ddt`, `note_fatture`,
`note_offerte_commerciali`, `note_ordini`, `note_preventivo` — ed evita che una
nota resti agganciata a una riga che appartiene a un altro documento.

La tabella righe e la colonna FK si passano per `TG_ARGV`, quindi la stessa
funzione serve domini diversi senza sapere niente di loro.

---

{% include-markdown "signature-core.md" %}
