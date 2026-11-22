## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_efba_guard_albero_emittente`

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
> * [anagrafiche.fn_guard_albero_ba_emittente](/dbzero/anagrafiche/funzioni/fn_guard_albero_ba_emittente) — il controllo su un billing account
> * [anagrafiche.fn_guard_albero_ba_gestore_globale](/dbzero/anagrafiche/funzioni/fn_guard_albero_ba_gestore_globale) — il controllo sullo spostamento della predefinita
> * [anagrafiche.trgfn_efba_guard_istanza_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_istanza_emittente) — il gemello sull'istanza
> * [anagrafiche.trgfn_efba_guard_storia_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_storia_emittente) — il cancello della storia sugli stessi movimenti

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_efba_guard_albero_emittente` fa scattare il controllo dell'albero omogeneo a ogni movimento
del collegamento fra billing account e azienda, nascita compresa.

---

### Tutti e quattro i movimenti

È montata dopo ogni inserimento, modifica e cancellazione di una riga, e smista:

* un collegamento che **nasce** (anche quello scritto alla nascita del billing account), **cambia azienda** o
  **si cancella**: controlla quel billing account verso il padre e verso i figli;
* una modifica che **sposta** la riga da un billing account a un altro: controlla tutti e due;
* la riga **senza billing account**, cioè la predefinita: controlla tutti gli alberi con un billing account
  senza collegamento.

La cancellazione è il movimento che sfugge: il billing account ricade sulla predefinita e cambia azienda senza
che nessuno abbia scritto un'azienda. Lo spostamento della predefinita è quello col raggio più largo.

---

### Dopo la scrittura

Il controllo rilegge il collegamento per risolvere l'azienda: prima della scrittura leggerebbe lo stato
vecchio. Sulla stessa tabella il cancello della storia scatta invece prima, perché ricava «prima» e «dopo» dalla
riga: i due si sommano, e uno dice «l'albero non diventa misto», l'altro «la storia non si sposta». Fra i due
controlli che scattano dopo, questo parla prima di quello dell'istanza.

---

### ⚠️ Che cosa oggi non copre

* **Una modifica che trasforma la predefinita in un collegamento, o un collegamento nella predefinita,**
  controlla solo il billing account nominato: il controllo sugli alberi dei billing account senza collegamento
  non parte. Il gemello dell'istanza, nello stesso caso, lo chiama.
* **Lo scollegamento fatto in sessione** si giudica con l'azienda di chi agisce (vedi
  `fn_check_ba_coppia_emittente_omogenea`).

---

### Codici errore

* `E_ALBERO_EMITTENTE_MISTO` — dai due controlli che chiama.

---

### Test

* `db/pgtap/anagrafiche/test-guard-albero-ba-omogeneo-v1.sql` — attraverso questo trigger: azienda cambiata sul
  figlio e sul padre, collegamento cancellato, predefinita spostata con una coppia mista e con una omogenea.

---

### Note di migrazione

* 2026-08-18 — nasce col controllo dell'albero omogeneo.

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

---

{% include-markdown "signature-core.md" %}
