## 📘 Documentazione Concettuale – Tabella `documenti.documenti_generati_eventi`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — la stampa a cui l'evento appartiene
> * [documenti.documenti_generati_file](/dbzero/documenti/tabelle/documenti_generati_file) — i file che un evento può citare
>
> Approfondimento funzioni:
>
> * [documenti.trgfn_documenti_generati_eventi_block_update](/dbzero/documenti/funzioni/trgfn_documenti_generati_eventi_block_update) — un evento non si modifica
> * [documenti.trgfn_documenti_generati_eventi_block_delete](/dbzero/documenti/funzioni/trgfn_documenti_generati_eventi_block_delete) — un evento non si cancella
> * [script.fn_resolve_emittente_fiscale_id](/dbzero/script/funzioni/fn_resolve_emittente_fiscale_id) — l'azienda dell'evento, presa dalla stampa
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — che cosa succede quando si genera e si ristampa un documento

---

### 🎯 Scopo Principale

`documenti.documenti_generati_eventi` è la storia di una stampa dopo la sua nascita: una riga per ogni fatto che la
riguarda (la generazione, ogni scaricamento, gli allegati aggiunti, le ristampe fedeli), con chi, quando, l'esito
e un dettaglio tecnico.

Gli eventi si aggiungono e basta: non si modificano e non si cancellano. Una correzione è un evento nuovo.

---

### Gli eventi sono un elenco chiuso

`evento_tipo` ammette, con un `CHECK`:

* `GENERATO` — la stampa è stata emessa e il suo PDF salvato;
* `SCARICATO` — il PDF salvato è stato scaricato; si registra a ogni scaricamento, l'anteprima no;
* `ALLEGATO_AGGIUNTO` — dopo l'emissione si sono aggiunti degli allegati alla stampa;
* `RISTAMPA_FEDELE` — la stampa è stata riprodotta dal contesto congelato e dalla versione registrata. Non è
  un'emissione: non nasce una riga nuova in `documenti_generati`;
* `STORAGE_ORPHAN` — un file salvato nello storage è rimasto senza registrazione e va tolto a mano.

Un evento nuovo vuole una migrazione che allarghi il `CHECK`: gli stati tecnici del motore li decide il codice, non
un vocabolario configurabile.

`esito` è `OK`, `KO` o `WARN`. `user_id` è l'utente che ha originato l'evento, vuoto per un evento tecnico.
`messaggio`, quando c'è, non è vuoto; `detail` e `meta` sono sempre oggetti JSON.

---

### ⭐ La timeline non si riscrive

Un `UPDATE` e un `DELETE` sono sempre rifiutati, su qualunque colonna, dai due trigger della tabella. Per questo lo
storico standard non c'è: la tabella è essa stessa il log, e i campi di audit valgono come data e autore
dell'inserimento.

---

### Chi vede gli eventi

Un evento segue il perimetro della sua stampa: l'azienda si risale dalla stampa, e un operatore vede e scrive solo
gli eventi delle stampe delle aziende del suo perimetro. Un evento su una stampa fuori perimetro è rifiutato dalla
policy prima ancora della foreign key.

---

### ⚠️ Che cosa oggi non copre

* **`STORAGE_ORPHAN` non ha chi lo scriva.** Un file orfano nasce quando il salvataggio nello storage riesce e la
  registrazione nel database no: in quel caso la stampa non esiste, e l'evento, che vuole sempre una stampa, non
  si può scrivere. Il backend oggi lo registra solo nel log applicativo.

---

### Codici errore

* `E_EVENTO_DOCUMENTO_UPDATE_VIETATA` — si è cercato di modificare un evento;
* `E_EVENTO_DOCUMENTO_DELETE_VIETATA` — si è cercato di cancellare un evento.

---

### Test

* `db/pgtap/documenti/test-documenti-generati-eventi.sql` — gli eventi ammessi e rifiutati, gli esiti, il
  messaggio e il dettaglio, i due blocchi, lo storico spento, il perimetro;
* `db/pgtap/rls/test-rls-documenti-satelliti.sql` — il perimetro degli eventi.

---

### Note di migrazione

* 2026-05-03 — nasce la tabella, con `GENERATO`, `SCARICATO` e `STORAGE_ORPHAN`: prende il posto di colonne di
  audit dedicate su `documenti_generati`.
* 2026-06-03 — si aggiunge `ALLEGATO_AGGIUNTO`.
* 2026-08-03 — si aggiunge `RISTAMPA_FEDELE`.
* 2026-09-10 — la tabella entra nel perimetro delle aziende.

---

{% include-markdown "signature-core.md" %}
