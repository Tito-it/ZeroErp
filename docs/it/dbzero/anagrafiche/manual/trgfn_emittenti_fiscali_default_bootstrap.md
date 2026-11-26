## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_emittenti_fiscali_default_bootstrap`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — la tabella su cui scatta
> * [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — dove scrive la riga dell'azienda predefinita
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_emittenti_fiscali_default_guard](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_default_guard) — il controllo al COMMIT che la predefinita ci sia, una sola
> * [anagrafiche.trgfn_billing_account_link_ef](/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef) — il collegamento alla nascita del billing account, che senza sessione usa la predefinita

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_emittenti_fiscali_default_bootstrap` fa del primo emittente l'azienda predefinita: dopo
l'inserimento di un emittente, se l'installazione non ha ancora una predefinita, scrive la riga senza billing
account che la dice.

---

### ⭐ Un'installazione con un'azienda ha sempre la predefinita

La predefinita è l'azienda che riceve, alla nascita, un billing account creato senza sessione o da chi non ha
un'azienda (`anagrafiche.trgfn_billing_account_link_ef`); senza nessuna azienda, e quindi senza predefinita,
un billing account non nasce. Un'installazione che ha un emittente e non ha la predefinita è respinta al
COMMIT da `anagrafiche.trgfn_emittenti_fiscali_default_guard`: questo trigger fa sì che il primo emittente non
debba pensarci. Chi crea gli emittenti successivi non tocca la predefinita, che resta dov'è finché qualcuno non
la sposta modificandone la riga; spostarla non cambia l'azienda di nessun billing account già nato.

Il trigger scatta dopo l'inserimento e non solleva. Scrive la predefinita solo quando non c'è, quindi non decide
mai fra due aziende.

---

### ⚠️ Che cosa oggi non copre

* **Un primo emittente nato spento** riceve lo stesso la predefinita, e la riga è respinta al COMMIT perché un
  collegamento chiede un'azienda accesa (`E_ATTIVO_PADRE_NON_ATTIVO`): il primo emittente di un'installazione
  deve nascere acceso.

---

### Test

* `db/pgtap/anagrafiche/test-emittenti-fiscali.sql` — dopo il primo emittente esiste una sola predefinita.

---

{% include-markdown "signature-core.md" %}
