## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_sepa_mandati_guard`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.sepa_mandati](/dbzero/pagamenti/tabelle/sepa_mandati) — i mandati SEPA, la tabella su cui è montata
> * [anagrafiche.soggetti_ruoli_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_ruoli_conti_bancari) — il legame del conto addebitato, che il mandato nomina
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_conti_bancari_normalize](/dbzero/anagrafiche/funzioni/trgfn_conti_bancari_normalize) — la stessa normalizzazione sull'IBAN del registro
>
> Guide:
>
> * [Gestione dei conti bancari](/guide/gestione-conti-bancari) — i conti e i mandati che vi si agganciano

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_sepa_mandati_guard` pretende la data di attivazione su un mandato SEPA attivo, e normalizza il
codice del mandato (UMR) e la copia dell'IBAN prima che i vincoli li giudichino.

---

### Un mandato attivo ha la sua data

Un mandato in stato `ATTIVO` senza `data_attivazione` è rifiutato (`E_DATA_ERRATA`, sul campo `data_attivazione`). Gli
altri stati non chiedono la data. L'ordine delle date (la firma, l'attivazione, la revoca) lo dice il vincolo
`chk_sepa_mandati_date`, non il trigger.

Il trigger scatta prima di ogni nascita e di ogni modifica, sulla tabella dei mandati, che è nello schema
`pagamenti`, mentre la funzione sta in `anagrafiche`, con le altre dei conti bancari.

---

### UMR e IBAN nella forma canonica

* **L'UMR** perde tutti gli spazi; le maiuscole e le minuscole restano come sono.
* **La copia dell'IBAN** (`iban_snapshot`) perde gli spazi e passa in maiuscolo, come l'IBAN del registro.

Il formato di tutti e due lo giudicano poi i vincoli della tabella, sul valore normalizzato.

---

### ⚠️ Che cosa oggi non copre

* **La copia dell'IBAN non si confronta col conto.** Niente lega `iban_snapshot` all'IBAN del conto che il legame
  nomina: la copia può dire un conto diverso.

---

### Codici errore

* `E_DATA_ERRATA` — un mandato `ATTIVO` senza data di attivazione.

---

### Test

* `db/pgtap/dbops/test-punti-canale-campo-v1.sql` — il rifiuto dichiara il campo `data_attivazione`. Nessun test prova
  il rifiuto o la normalizzazione su un mandato.

---

### Note di migrazione

* 2026-08-04 — il rifiuto passa per il registro degli errori di `script` e porta nel contesto la data vera, non uno
  zero.

---

{% include-markdown "signature-core.md" %}
