## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_efba_guard_storia_emittente`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — la tabella su cui è montato
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_guard_ba_cambio_emittente](/dbzero/anagrafiche/funzioni/fn_guard_ba_cambio_emittente) — il controllo su un billing account
> * [anagrafiche.fn_ba_ha_storia_emittente](/dbzero/anagrafiche/funzioni/fn_ba_ha_storia_emittente) — che cosa è la storia: qualunque documento, anche in bozza
> * [script.trgfn_prevent_modification_generic](/dbzero/script/funzioni/trgfn_prevent_modification_generic) — i trigger `a05` che rifiutano cancellazione e spostamento
> * [anagrafiche.trgfn_efba_guard_albero_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_albero_emittente) — il cancello dell'albero sugli stessi movimenti

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_efba_guard_storia_emittente` è il cancello della storia sul collegamento fra billing account
e azienda: quando si modifica l'azienda sul collegamento di un billing account, lascia decidere al controllo
della storia se il billing account può cambiare azienda.

---

### Un solo movimento cambia l'azienda di un cliente

Ogni billing account ha sempre il suo collegamento, e il collegamento non si cancella e non passa a un altro
conto. Resta un solo movimento che cambia l'azienda di un cliente: la **modifica** dell'azienda sul suo
collegamento. Il trigger la riconosce (un collegamento di un billing account, l'azienda di prima diversa da
quella di dopo) e passa a `anagrafiche.fn_guard_ba_cambio_emittente` il billing account e le due aziende.

Gli altri movimenti non hanno niente da giudicare:

| Movimento | Perché la storia non si guarda |
| --- | --- |
| nasce il collegamento | nasce col billing account, che non ha ancora documenti |
| si cancella il collegamento, o passa a un altro billing account | lo rifiutano prima i trigger `a05` della tabella (`E_BA_COLLEGAMENTO_NON_SI_TOGLIE`, `E_BA_COLLEGAMENTO_NON_SI_SPOSTA`) |
| si sposta la riga della predefinita | decide solo l'azienda dei billing account che nasceranno: non cambia l'azienda di nessun cliente |

---

### ⛔ Su una cancellazione restituisce la riga vecchia

Il trigger è montato anche sulla cancellazione, che i trigger `a05` rifiutano prima. Lì non fa niente, ma
restituisce la riga vecchia: restituire niente annullerebbe la cancellazione in silenzio, e un gesto rifiutato
deve restare un errore, non sparire.

Scatta prima della scrittura, nella fase dei guard di blocco; i controlli dell'albero, dell'istanza e della
chiave del cliente scattano dopo, perché rileggono il collegamento. Rispondono a domande diverse e si sommano.

---

### Codici errore

* `E_BA_EMITTENTE_CON_STORIA` — dal controllo che chiama: il billing account ha almeno un documento, anche in
  bozza.

---

### Test

* `db/pgtap/anagrafiche/test-ba-cambio-emittente-storia-v1.sql` — il trigger è montato su inserimento, modifica
  e cancellazione; il controllo che chiama passa sul cliente appena nato e respinge il cambio dopo una commessa.
* `db/pgtap/anagrafiche/test-billing-account-sempre-collegato-v1.sql` — senza documenti l'azienda si cambia
  modificando il collegamento, all'andata e al ritorno; con una fattura in bozza il cambio è respinto; lo
  spostamento della predefinita passa e non cambia l'azienda di nessun billing account.

---

### Note di migrazione

* 2026-08-26 — nasce: prima il collegamento di un cliente si toglieva e si ricreava senza condizioni.
* 2026-11-26 — giudica solo la modifica dell'azienda sul collegamento di un billing account: la cancellazione
  e lo spostamento del collegamento sono rifiutati a monte, e il ramo dello spostamento della predefinita è
  ritirato con il suo controllo.

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

---

{% include-markdown "signature-core.md" %}
