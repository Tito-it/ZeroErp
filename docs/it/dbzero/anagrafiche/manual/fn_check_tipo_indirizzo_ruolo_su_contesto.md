## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_tipo_indirizzo_ruolo](/dbzero/anagrafiche/funzioni/fn_check_tipo_indirizzo_ruolo) — la check sul ruolo salvato, che la compone
> * [anagrafiche.fn_tipi_indirizzo_proponibili_ruolo](/dbzero/anagrafiche/funzioni/fn_tipi_indirizzo_proponibili_ruolo) — il picker sul ruolo salvato
> * [anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo](/dbzero/anagrafiche/funzioni/fn_tipi_indirizzo_proponibili_tipo_ruolo) — il picker all'assegnazione del ruolo
> * [anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_ammesso_per_ruolo) — il predicato del tipo di ruolo
> * [anagrafiche.fn_tipo_indirizzo_ammesso_per_natura](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_ammesso_per_natura) — il predicato della natura
> * [anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto](/dbzero/anagrafiche/funzioni/fn_check_tipo_indirizzo_soggetto_su_contesto) — la gemella sullo strato del soggetto
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — i due strati degli indirizzi e le loro regole

---

### 🎯 Scopo Principale

`anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto` dice perché un tipo d'indirizzo non si può scrivere su
un ruolo con un dato contesto: restituisce l'elenco ordinato dei motivi, vuoto se il tipo è ammesso. È la metà
pura della check del ruolo, che la madre e i picker leggono allo stesso modo.

---

### Il contesto, invece del ruolo

Non legge il ruolo: riceve il **tipo di ruolo**, i **tipi** che la chiave di destinazione ha già, il **giorno**
e la **natura** del soggetto del ruolo. Così la stessa regola serve al ruolo salvato e al ruolo che non esiste
ancora, quando il picker dell'assegnazione passa il tipo di ruolo scelto, nessun tipo presente e la natura del
soggetto, se il soggetto è già scelto. Il ruolo, quando c'è, entra solo nel dettaglio dei motivi.

* I **tipi presenti** arrivano già filtrati sulla chiave (ruolo, istanza): la funzione non sa di quale
  istanza si parli.
* La **natura** vuota (soggetto senza natura, o non ancora scelto) non dà motivi; il tipo di ruolo vuoto
  nemmeno.

I motivi sono tre, nell'ordine: il tipo già presente, il tipo che il tipo di ruolo non ammette, il tipo che la
natura non ammette. Il terzo è lo stesso motivo, con lo stesso codice, della gemella del soggetto.

---

{% include-markdown "it/dbzero/anagrafiche/_tipo-indirizzo-ammesso.md" %}

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — il tipo d'indirizzo o il giorno non sono passati.

I codici dei motivi la funzione non li solleva: li restituisce.

---

### Test

* `db/pgtap/anagrafiche/test-check-tipo-indirizzo-v1.sql` — il tipo già presente e la riga scaduta, i due motivi
  nell'ordine; i valori del motivo del tipo di ruolo per descrizione.
* `db/pgtap/anagrafiche/test-fornitore-privato-indirizzi-v1.sql` — il privato e la sede legale: il motivo della
  natura col codice del guard del soggetto, coi valori natura e tipo; la natura vuota senza motivi.

---

### Note di migrazione

* 2026-11-15 — nasce con la copia degli indirizzi, coi primi due motivi.
* 2026-11-16 — prende la natura del soggetto del ruolo in coda, e il terzo motivo, col fornitore privato.

---

{% include-markdown "signature-core.md" %}
