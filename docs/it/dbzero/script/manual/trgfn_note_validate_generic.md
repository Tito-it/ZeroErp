## 📘 Documentazione Concettuale – Trigger function `script.trgfn_note_validate_generic`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.note](/dbzero/vendite/tabelle/note) — la tabella partizionata delle note di vendita
> * [acquisti.note](/dbzero/acquisti/tabelle/note) — la tabella partizionata delle note di acquisto
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — l'etichetta del tipo di documento nella frase d'errore
>
> Approfondimento funzioni:
>
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva gli errori

---

### 🎯 Scopo Principale

La trigger function `script.trgfn_note_validate_generic` valida le note ancorate a una riga di
documento (`anchor_tipo = 'RIGA'`): la riga indicata da `target_riga_id` deve appartenere davvero
alla testata indicata da `target_id`.

Impedisce che una nota resti agganciata a una riga che appartiene a un altro documento.

---

### Le regole

* Se `anchor_tipo` non è `'RIGA'`, la nota è ancorata alla testata e la funzione non controlla
  niente.
* Per una nota a riga:
  * `target_riga_id` è obbligatorio;
  * la tabella delle righe passata come primo argomento del trigger deve esistere;
  * la colonna della riga che punta alla testata (secondo argomento) deve valere `NEW.target_id`.
* Ogni violazione si solleva con `script.fn_log_and_raise_error`, nell'area dello schema della
  tabella su cui scatta il trigger.

---

### ⭐ Una funzione, un montaggio per partizione

Il validatore vive in `script` perché non appartiene a un dominio solo: non sa niente delle tabelle
che controlla. Il montaggio gli passa due soli argomenti, la tabella delle righe (qualificata con lo
schema) e il nome della colonna che collega la riga alla sua testata.

È montato come trigger `BEFORE INSERT OR UPDATE`, riga per riga, su **otto** partizioni di note,
ognuna con la tabella righe del proprio documento:

| Partizione | Tabella delle righe |
| --- | --- |
| `vendite.note_preventivo` | `vendite.preventivi_righe` |
| `vendite.note_offerte_commerciali` | `vendite.offerte_commerciali_eccezioni` (le righe di un'offerta sono le sue eccezioni) |
| `vendite.note_contratto` | `vendite.contratti_righe` |
| `vendite.note_ordini` | `vendite.ordini_righe` |
| `vendite.note_ddt` | `vendite.ddt_righe` |
| `vendite.note_fatture` | `vendite.fatture_righe` |
| `acquisti.note_ordini` | `acquisti.ordini_righe` |
| `acquisti.note_ddt` | `acquisti.ddt_righe` |

⛔ `vendite.note_attivita_fatturabili` non ha il montaggio: un'attività fatturabile non ha righe a cui
ancorare una nota.

---

### Il dominio dell'errore viene dalla nota

In `E_NOTE_RIGA_MISMATCH` il tipo di documento si legge dalla nota stessa, non da un argomento del
trigger:

* nel contesto dell'errore, per la macchina, c'è `NEW.target_tipo`, il codice della sorgente;
* nella frase per l'operatore c'è la parola che una persona riconosce, l'`etichetta` di quel codice in
  `config.sorgenti` («DDT», «Ordine»), o il codice stesso se il tipo non è una sorgente.

---

### Codici errore

* `E_NOTE_TARGET_ID` — nota a riga senza `target_riga_id`.
* `E_NOTE_CONFIG` — la tabella delle righe passata al montaggio non esiste: è un errore di
  configurazione del trigger, non dei dati.
* `E_NOTE_RIGA_MISMATCH` — la riga non esiste o appartiene a un'altra testata.

---

### Test

* `vendite/test-note-partitioning` — il trigger di validazione esiste sulle note di preventivi,
  contratti, ordini, DDT e fatture di vendita, e manca su `note_attivita_fatturabili`.
* `config/test-grammatica-note-target-tipo-v1` — i montaggi passano i soli due argomenti che la
  funzione legge, e la frase di `E_NOTE_RIGA_MISMATCH` porta l'etichetta della sorgente, non il codice.

---

### Note di migrazione

* 2026-10-25 — il dominio dell'errore era un terzo argomento del trigger (`'DDT'`, `'ORDINE'`,
  `'OFFERTA'`…) che ripeteva a mano il confine della partizione: è stato ritirato e i montaggi lo hanno
  perso (brief-db-grammatica-unica-documenti).

---

{% include-markdown "signature-core.md" %}
