## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_efba_guard_storia_emittente`

> **Ultimo aggiornamento**: 22 novembre 2026
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
> * [anagrafiche.fn_guard_ba_gestore_globale_storia](/dbzero/anagrafiche/funzioni/fn_guard_ba_gestore_globale_storia) — il controllo sullo spostamento della predefinita
> * [anagrafiche.trgfn_efba_guard_albero_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_albero_emittente) — il cancello dell'albero sugli stessi movimenti

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_efba_guard_storia_emittente` è il cancello della storia sul collegamento fra billing account
e azienda: a ogni movimento che cambia l'azienda di un billing account ricava l'azienda di prima e quella di
dopo, e lascia decidere ai controlli della storia.

---

### ⚠️ Il movimento che si dimentica è la cancellazione

Spostare un cliente da un'azienda all'altra si fa togliendo il collegamento e creandone uno nuovo. Il primo
passo, da solo, è già un cambio: il billing account ricade sulla predefinita. Un controllo sulla sola creazione
lascerebbe passare tutto, perché il danno lo fa la cancellazione.

---

### Prima e dopo, movimento per movimento

| Movimento | Prima | Dopo | Controllo |
| --- | --- | --- | --- |
| nasce un collegamento | la predefinita | l'azienda scelta | sul billing account |
| il collegamento cambia azienda | quella di prima | quella nuova | sul billing account |
| la riga passa a un altro billing account | il vecchio: la sua; il nuovo: la predefinita | il vecchio: la predefinita; il nuovo: quella della riga | sui due billing account |
| si cancella un collegamento | quella che c'era | la predefinita | sul billing account |
| nasce, cambia o sparisce la predefinita | la predefinita di prima | quella nuova, o nessuna | sui billing account senza collegamento |

---

### Due accorgimenti

**La predefinita si legge dalla sua riga, non dal risolutore.** Il cancello scatta prima della scrittura: in
una cancellazione la riga che sta sparendo c'è ancora, e il risolutore risponderebbe proprio quella. «Prima» e
«dopo» coinciderebbero e il controllo non scatterebbe mai. Per questo legge la riga predefinita, escludendo
quella che si cancella.

**Su una cancellazione restituisce la riga vecchia.** Restituire niente annullerebbe la cancellazione in
silenzio: la differenza fra un cancello che blocca dicendolo e uno che fa sparire il gesto senza errori.

Scatta prima della scrittura, nella fase dei guard di blocco; i controlli dell'albero e dell'istanza scattano
dopo, perché rileggono il collegamento. Rispondono a domande diverse e si sommano.

---

### ⚠️ Che cosa oggi non copre

* **Una modifica che trasforma la predefinita in un collegamento, o un collegamento nella predefinita,**
  controlla solo il billing account nominato: la storia dei billing account senza collegamento, che cambiano
  azienda con la predefinita, non si guarda.
* **Sostituire la predefinita cancellandola e reinserendola** è respinto alla cancellazione, anche se la nuova
  riga riporterà la stessa azienda, quando un billing account senza collegamento ha storia: il «dopo» della
  cancellazione è «nessuna azienda». Cambiare l'azienda sulla riga predefinita non ha questo limite.
* Sui movimenti della predefinita vale il limite di `fn_guard_ba_gestore_globale_storia`, che sceglie il
  billing account da guardare con un'altra definizione di storia.

---

### Codici errore

* `E_BA_EMITTENTE_CON_STORIA` — dai due controlli che chiama.

---

### Test

* `db/pgtap/anagrafiche/test-ba-cambio-emittente-storia-v1.sql` — il trigger è montato su inserimento, modifica
  e cancellazione; il controllo che chiama passa sul cliente appena nato e respinge il cambio dopo una commessa.

---

### Note di migrazione

* 2026-08-26 — nasce: prima il collegamento di un cliente si toglieva e si ricreava senza condizioni.

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

---

{% include-markdown "signature-core.md" %}
