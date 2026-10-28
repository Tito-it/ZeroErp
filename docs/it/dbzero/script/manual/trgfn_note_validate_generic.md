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

La tabella righe e la colonna FK si passano per `TG_ARGV` (i due soli argomenti), quindi la stessa
funzione serve domini diversi senza sapere niente di loro.

### Il dominio dell'errore

> Ultima revisione: 2026-10-25 (brief-db-grammatica-unica-documenti, lotto 3), L3-4.

In `E_NOTE_RIGA_MISMATCH` il dominio viene dalla riga, non da un argomento del trigger:

* nel payload (`p_context ->> 'dominio'`, per la macchina) c'è `NEW.target_tipo`, il codice;
* nella frase per l'operatore («…al documento di dominio %s…») c'è la parola che una persona riconosce,
  `config.sorgenti.etichetta` di quel codice («DDT», «Ordine»), o il codice se il tipo non è una sorgente.

Fino al 2026-10-25 il dominio era un terzo argomento (`'DDT'`, `'ORDINE'`, `'OFFERTA'`…) che ripeteva a mano il
confine della partizione: ritirato dal `20261025-66`, e i montaggi lo hanno perso (`-67`, `-68`). Il pgTAP
`config/test-grammatica-note-target-tipo-v1` presidia i due argomenti e la frase.

---

{% include-markdown "signature-core.md" %}
