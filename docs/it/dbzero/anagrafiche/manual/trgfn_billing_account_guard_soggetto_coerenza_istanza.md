## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_billing_account_guard_soggetto_coerenza_istanza`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — la tabella su cui è montata
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — l'istanza, di cui si legge il soggetto
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo a cui il billing account fattura
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_istanza_di_altro_soggetto](/dbzero/anagrafiche/funzioni/fn_istanza_di_altro_soggetto) — la domanda «l'istanza è di un altro soggetto?», comune ad altri guard
> * [script.fn_guard_soggetto_ruolo](/dbzero/script/funzioni/fn_guard_soggetto_ruolo) — il controllo del tipo di ruolo
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns) — il blocco di istanza e ruolo, che parla prima

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_billing_account_guard_soggetto_coerenza_istanza` verifica che il ruolo di un billing account
sia quello giusto per la sua istanza: un ruolo **cliente** dello **stesso soggetto** dell'istanza.

---

### Due domande sul ruolo

1. **Il soggetto.** Il soggetto del ruolo deve essere quello dell'istanza; se no, `E_BA_SOGGETTO_INCOERENTE_ISTANZA`.
   Il confronto lo fa `fn_istanza_di_altro_soggetto`, la stessa domanda dei guard di indirizzi, contatti, conti
   del ruolo e pratiche. Se il ruolo o l'istanza non esistono questa domanda tace: un'istanza inesistente
   la dice la FK, un ruolo inesistente la seconda domanda.
2. **Il tipo.** Il ruolo deve essere di tipo cliente (`CL`): un billing account non nasce, per esempio, sul ruolo
   fornitore del soggetto giusto. Lo dice `script.fn_guard_soggetto_ruolo` (`E_SOGGETTI_RUOLI`), lo stesso
   controllo delle specializzazioni di ruolo.

Non c'è un'eccezione per un terzo pagante: chi paga è chi intesta l'istanza.

---

### ⭐ In fascia `a20`, dopo il blocco

Il trigger scatta all'inserimento e alla modifica di `istanza_utility_id` o `soggetto_ruolo_id`. Le due colonne
sono bloccate dopo la nascita, e il blocco gira prima, in fascia `a10`: una modifica che cambia l'una o l'altra
riceve `E_BA_ISTANZA_IMMUTABILE`, non il rifiuto di coerenza. In pratica la regola si giudica alla nascita.

Resta vera anche dopo, perché i due soggetti da confrontare sono bloccati a loro volta: quello del ruolo
(`E_SOGGETTO_RUOLO_SOGGETTO_IMMUTABILE`) e quello dell'istanza (`E_ISTANZA_SOGGETTO_IMMUTABILE`).

---

### ⚠️ Che cosa oggi non copre

* **Il tipo del ruolo dopo la nascita.** Su `soggetti_ruoli` il tipo di ruolo non è bloccato e nessun guard di
  quella tabella guarda i billing account: un ruolo cliente che cambia tipo lascia i suoi billing account su un
  ruolo che cliente non è più.

---

### Codici errore

* `E_BA_SOGGETTO_INCOERENTE_ISTANZA` — il soggetto del ruolo non è quello dell'istanza.
* `E_SOGGETTI_RUOLI` — il ruolo non è di tipo cliente, o non esiste (da `script.fn_guard_soggetto_ruolo`).

---

### Test

* `db/pgtap/anagrafiche/test-trgfn-billing-account-guard-soggetto-coerenza-istanza-v1.sql` — il ruolo coerente
  passa, quello di un altro soggetto è rifiutato.
* `db/pgtap/vendite/test-esecutivi-ba-coppia-v1.sql` — il billing account non nasce sul ruolo fornitore del
  soggetto giusto, e il trigger è in fascia `a20`.
* `db/pgtap/anagrafiche/test-istanza-nasce-col-ba-v1.sql` — il blocco della coppia, che parla prima.

---

### Note di migrazione

* 2026-05-02 — nasce: prima la coerenza fra il soggetto del ruolo e quello dell'istanza era solo una regola del
  flusso applicativo.
* 2026-10-09 — si aggiunge il controllo del tipo cliente, e il trigger passa dalla fascia `a10` alla `a20`,
  dopo il blocco di colonna.
* 2026-10-19 — il confronto dei soggetti passa a `fn_istanza_di_altro_soggetto`; codice e messaggio non
  cambiano.

---

{% include-markdown "signature-core.md" %}
