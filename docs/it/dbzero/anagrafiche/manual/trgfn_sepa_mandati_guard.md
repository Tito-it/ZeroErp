## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_sepa_mandati_guard`

> **Ultimo aggiornamento**: 27 novembre 2026
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
> * [anagrafiche.trgfn_conti_bancari_normalize](/dbzero/anagrafiche/funzioni/trgfn_conti_bancari_normalize) — la forma dell'IBAN del registro, da cui la copia del mandato viene
>
> Guide:
>
> * [Gestione dei conti bancari](/guide/gestione-conti-bancari) — i conti e i mandati che vi si agganciano

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_sepa_mandati_guard` pretende la data di attivazione su un mandato SEPA attivo, normalizza il
codice del mandato (UMR), e scrive la copia dell'IBAN dal conto del legame addebitato.

---

### Un mandato attivo ha la sua data

Un mandato in stato `ATTIVO` senza `data_attivazione` è rifiutato (`E_DATA_ERRATA`, sul campo `data_attivazione`). Gli
altri stati non chiedono la data. L'ordine delle date (la firma, l'attivazione, la revoca) lo dice il vincolo
`chk_sepa_mandati_date`, non il trigger.

Il trigger scatta prima di ogni nascita e di ogni modifica, sulla tabella dei mandati, che è nello schema
`pagamenti`, mentre la funzione sta in `anagrafiche`, con le altre dei conti bancari.

---

### L'UMR nella forma canonica, l'IBAN dal conto

* **L'UMR** perde tutti gli spazi; le maiuscole e le minuscole restano come sono.
* **La copia dell'IBAN** (`iban_snapshot`) è l'IBAN del conto del legame che il mandato nomina
  (`soggetto_ruolo_conto_id`), scritto a ogni nascita e a ogni modifica: un valore mandato da fuori si sovrascrive.
  L'IBAN del conto e il conto del legame hanno il lucchetto, quindi la copia resta quella con cui il mandato è nato.
* **L'intestatario** (`intestatario_snapshot`) resta il dato scritto da chi crea il mandato.

Il formato li giudicano poi i vincoli della tabella.

---

### Codici errore

* `E_DATA_ERRATA` — un mandato `ATTIVO` senza data di attivazione.

---

### Test

* `db/pgtap/dbops/test-punti-canale-campo-v1.sql` — il rifiuto dichiara il campo `data_attivazione`.
* `db/pgtap/anagrafiche/test-conti-bancari-forma-e-legami-v1.sql` — la copia dell'IBAN è quella del conto, qualunque
  cosa si mandi. Nessun test prova il rifiuto della data.

---

### Note di migrazione

* 2026-08-04 — il rifiuto passa per il registro degli errori di `script` e porta nel contesto la data vera, non uno
  zero.
* 2026-11-27 — la copia dell'IBAN la scrive il trigger dal conto del legame, invece di normalizzare quella mandata.

---

{% include-markdown "signature-core.md" %}
