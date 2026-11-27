## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_efba_guard_albero_emittente`

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
> * [anagrafiche.fn_guard_albero_ba_emittente](/dbzero/anagrafiche/funzioni/fn_guard_albero_ba_emittente) — il controllo su un billing account
> * [anagrafiche.trgfn_efba_guard_istanza_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_istanza_emittente) — il gemello sull'istanza
> * [anagrafiche.trgfn_efba_guard_storia_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_storia_emittente) — il cancello della storia sugli stessi movimenti

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_efba_guard_albero_emittente` fa scattare il controllo dell'albero omogeneo quando il
collegamento di un billing account nasce o cambia azienda.

---

### Due movimenti, un billing account

È montata dopo ogni inserimento, modifica e cancellazione di una riga, e giudica solo il collegamento di un
billing account:

* un collegamento che **nasce** (è quello scritto alla nascita del billing account) o **cambia azienda**:
  controlla quel billing account verso il padre e verso i figli.

Il resto non tocca nessun albero: la cancellazione del collegamento e il suo passaggio a un altro billing
account li rifiutano prima i trigger `a05` della tabella, e la riga della predefinita non si giudica, perché
spostarla non cambia l'azienda di nessun billing account.

---

### Dopo la scrittura

Il controllo rilegge il collegamento per risolvere l'azienda: prima della scrittura leggerebbe lo stato
vecchio. Sulla stessa tabella il cancello della storia scatta invece prima, perché ricava «prima» e «dopo» dalla
riga: i due si sommano, e uno dice «l'albero non diventa misto», l'altro «il cliente non ha documenti». Fra i
due controlli che scattano dopo, questo parla prima di quello dell'istanza.

---

### Codici errore

* `E_ALBERO_EMITTENTE_MISTO` — dal controllo che chiama.

---

### Test

* `db/pgtap/anagrafiche/test-guard-albero-ba-omogeneo-v1.sql` — attraverso questo trigger: azienda cambiata sul
  figlio e sul padre, rifiutata; la cancellazione del collegamento è rifiutata prima
  (`E_BA_COLLEGAMENTO_NON_SI_TOGLIE`); la predefinita spostata lascia padre e figlio sulla loro azienda.

---

### Note di migrazione

* 2026-08-18 — nasce col controllo dell'albero omogeneo.
* 2026-11-26 — giudica solo il collegamento di un billing account che nasce o cambia azienda: i rami della
  cancellazione, dello spostamento e della predefinita sono ritirati.

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

---

{% include-markdown "signature-core.md" %}
