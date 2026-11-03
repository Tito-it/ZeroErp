## 📘 Documentazione Concettuale – Tabella `pagamenti.vendite_contabili_stati`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili) — la testata che porta lo stato
> * [pagamenti.transizioni_stati_contabile](/dbzero/pagamenti/tabelle/transizioni_stati_contabile) — i passaggi ammessi fra questi stati
> * [pagamenti.vendite_contabili_righe_stati](/dbzero/pagamenti/tabelle/vendite_contabili_righe_stati) — il catalogo gemello, per le righe
>
> Approfondimento funzioni:
>
> * [pagamenti.fn_posta_contabile](/dbzero/pagamenti/funzioni/fn_posta_contabile) — legge `is_registrabile`
> * [pagamenti.trgfn_vendite_contabili_guard_validazione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_validazione) — legge `righe_lavorabili` per l'annullo
> * [pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_distinta_finale) — congela le righe sotto `righe_lavorabili = false`
>
> Guide:
>
> * [Frontend standards](/dev/frontend/frontend-standards) — l'informazione di stato nel drawer (`infoKey`)

---

### 🎯 Scopo Principale

Il catalogo degli stati della distinta contabile: `BOZZA`, `IMPORTATA`, `VALIDATA`,
`CHIUSA`, `ANNULLATA`. Oltre al codice, ogni stato dichiara se è finale, se da lì si può
registrare e se le righe sotto di lui si lavorano ancora.

---

### ⭐ Le domande si fanno al catalogo, non al nome dello stato

Due bandiere rispondono alle domande che il codice altrimenti scriverebbe come letterali:

* **`is_registrabile`** — «da questo stato si può registrare?». Vera **solo** su
  `VALIDATA`. La legge [fn_posta_contabile](/dbzero/pagamenti/funzioni/fn_posta_contabile)
  per rifiutare la registrazione (`E_CONTABILE_NON_REGISTRABILE`), e il dettaglio della
  distinta la espone per spegnere «Registra» col motivo invece di finire in un rifiuto. Una
  bandiera e non una funzione di check: il motivo è uno e statico, lo stato.
* **`righe_lavorabili`** — «sotto questo stato le righe della distinta si lavorano
  ancora?». Falsa **solo** su `ANNULLATA`.

Entrambe valgono `false` per default: uno stato nuovo è fail-closed finché qualcuno non
dichiara il contrario.

---

### ⚠️ `is_final` non basta: le due finali sono opposte per le righe

`CHIUSA` e `ANNULLATA` sono entrambe finali, ma per le righe dicono cose opposte. Sotto una
chiusa una sospesa ha ancora la registrazione tardiva e una scartata si riprende; sotto
un'annullata non c'è niente da dire, perché quel denaro per il registro non è mai arrivato.

Per questo esiste `righe_lavorabili`, e la leggono:

* il guard delle righe ([trgfn_vendite_contabili_righe_guard_distinta_finale](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_distinta_finale)):
  sotto `false` ogni scrittura su una riga è rifiutata;
* la check di eliminabilità della riga;
* la coda del riconciliatore: le righe escono dalla lista di lavoro;
* il frontend, che spegne le azioni di riga;
* il guard di validazione della testata
  ([trgfn_vendite_contabili_guard_validazione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_validazione)):
  in uno stato con `righe_lavorabili = false` entra solo una distinta `MANUALE`.

---

### Il testo dello stato è un indirizzo, non una frase

Il `meta` di ogni stato porta la chiave i18n `nessuna_azione_key`
(`pagamenti.distinte.stato_info.<stato>`): è il testo che il drawer della distinta mostra
per dire *dove si è* (bozza: si digita · validata: pronta da registrare, il denaro non è
ancora registrato · registrata …). Il backend la trasporta come `stato_info_key`, il
frontend la passa alla barra delle azioni del drawer: è lo stesso meccanismo degli altri
cataloghi di stato, descritto in
[frontend-standards](/dev/frontend/frontend-standards) («L'informazione di stato»).

⚠️ Il testo **non** sta qui: qui c'è solo l'indirizzo.

---

### ⛔ I valori si cambiano nel CSV, mai con un `UPDATE`

Le bandiere e il `meta` sono seme del catalogo: la loro sede è il CSV
`80_data/sql/pagamenti/vendite_contabili_stati.csv`. Un `UPDATE` a mano non sta nel seme:
un database costruito da zero non lo avrebbe, e il prossimo caricamento del CSV lo
riscriverebbe.

L'id di `BOZZA` (1) è un contratto: è il default della colonna `stato_id` della testata,
perché un default di colonna non può cercare uno stato per codice.

---

### Test

* `db/pgtap/pagamenti/test-vendite-contabili-stato-obbligatorio.sql` — l'id 1 è `BOZZA`,
  contratto del default della testata.
* `db/pgtap/pagamenti/test-righe-distinta-annullata-congelate-v1.sql` — `righe_lavorabili`:
  la bandiera c'è, fail-closed, e sotto un'annullata le righe si leggono soltanto.
* `db/pgtap/pagamenti/test-fn-posta-contabile.sql` — una distinta non registrabile non si
  registra.

---

### Note di migrazione

* 2026-02-13 — prima revisione del catalogo.
* 2026-09-15 — il `meta` di tutti e cinque gli stati riceve `nessuna_azione_key`.
* 2026-09-18 — nasce `is_registrabile`: la registrazione smette di confrontare il
  letterale `'VALIDATA'`.
* 2026-09-30 — nasce `righe_lavorabili`.

---

{% include-markdown "signature-core.md" %}
