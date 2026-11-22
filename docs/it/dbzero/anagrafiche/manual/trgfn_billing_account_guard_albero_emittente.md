## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_billing_account_guard_albero_emittente`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — la tabella su cui è montata
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_guard_albero_ba_emittente](/dbzero/anagrafiche/funzioni/fn_guard_albero_ba_emittente) — il controllo a cui delega
> * [anagrafiche.trgfn_efba_guard_albero_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_albero_emittente) — lo stesso controllo, quando cambia il collegamento all'azienda
> * [anagrafiche.trgfn_billing_account_link_ef](/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef) — il collegamento della nascita, che deve venire prima
> * [anagrafiche.trgfn_billing_account_guard_normalize](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_normalize) — l'altra domanda sul padre: la stessa identità fiscale

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_billing_account_guard_albero_emittente` fa scattare, quando un billing account nasce o
cambia padre, il controllo che padre e figli siano della stessa azienda. Il controllo vero sta in
`fn_guard_albero_ba_emittente`: il trigger dice solo quando.

---

### Quando scatta

All'inserimento e alla modifica di `parent_account_id`. Il controllo guarda il billing account toccato contro
il suo padre e contro tutti i suoi figli, anche quelli fuori dal perimetro di chi scrive (la funzione a cui
delega è privilegiata), e rifiuta un albero misto con `E_ALBERO_EMITTENTE_MISTO`.

Lo stesso controllo lo chiama il trigger del collegamento all'azienda, quando l'azienda di un billing account
cambia senza che cambi il padre.

---

### ⭐ Dopo la scrittura, in fascia `z95`

I controlli di casa stanno prima della scrittura; questo no, per una ragione concreta. L'azienda di un billing
account nuovo esiste quando esiste il suo collegamento, e il collegamento lo scrive
`trgfn_billing_account_link_ef` dopo l'inserimento, in fascia `z90`. Un controllo che girasse prima leggerebbe
un'azienda che non è ancora scritta; ricopiare qui la regola che la sceglie vorrebbe dire avere due regole
destinate a divergere. A parità di momento i trigger girano per nome: `z95` viene dopo `z90`.

L'identità fiscale fra padre e figlio è un'altra domanda, e la tiene `trgfn_billing_account_guard_normalize`.

---

### Codici errore

* `E_ALBERO_EMITTENTE_MISTO` — da `fn_guard_albero_ba_emittente`: padre e figlio risolvono ad aziende diverse.

---

### Test

* `db/pgtap/anagrafiche/test-guard-albero-ba-omogeneo-v1.sql` — l'albero omogeneo passa, il padre di un'altra
  azienda è rifiutato, il controllo vede anche un figlio fuori perimetro.
* `db/pgtap/anagrafiche/test-istanza-ba-gestore-globale-v1.sql` — l'ordine dei trigger quando si sposta
  l'azienda predefinita.

---

### Note di migrazione

* 2026-08-18 — nasce, col controllo dell'albero omogeneo per azienda.

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

{% include-markdown "signature-core.md" %}
