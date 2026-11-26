## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_istanza_ba_emittente`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — i billing account dell'istanza, uno per utility
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — l'istanza nominata nel rifiuto
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_ba_coppia_emittente_omogenea](/dbzero/anagrafiche/funzioni/fn_check_ba_coppia_emittente_omogenea) — il confronto di una coppia
> * [anagrafiche.trgfn_billing_account_guard_istanza_emittente](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_istanza_emittente) — chiamante: nasce un billing account
> * [anagrafiche.trgfn_efba_guard_istanza_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_istanza_emittente) — chiamante: il collegamento all'azienda nasce o cambia azienda
> * [anagrafiche.fn_guard_albero_ba_emittente](/dbzero/anagrafiche/funzioni/fn_guard_albero_ba_emittente) — il gemello sull'albero padre/figli
>
> Guide:
>
> * [Gestione delle istanze utility](/guide/gestione-delle-istanze-utility) — un'istanza, un'azienda

---

### 🎯 Scopo Principale

`anagrafiche.fn_guard_istanza_ba_emittente` verifica che un billing account sia della stessa azienda di tutti
gli altri billing account della sua istanza, e ferma l'operazione con `E_ISTANZA_EMITTENTI_DIVERSI` se non lo è.

---

### ⭐ Un'istanza, un'azienda

«Di chi è questa istanza?» ha una risposta sola: dell'azienda dei suoi billing account. È la regola con cui si
decide chi vede un'istanza; un'istanza con billing account di due aziende sarebbe di tutte e due, e la
risposta smetterebbe di esistere. Un'istanza ha un billing account per utility: il guard li confronta tutti
con quello toccato, in ordine, e si ferma alla prima coppia di aziende diverse.

---

### Lo stesso confronto dell'albero

È il gemello del guard sull'albero padre/figli: cambia l'insieme guardato, qui gli altri billing account della
stessa istanza, e il confronto è lo stesso, `anagrafiche.fn_check_ba_coppia_emittente_omogenea`, sull'azienda
come la usa la fatturazione: quella del collegamento, che ogni billing account ha sempre. Due controlli che la
calcolassero in modo diverso potrebbero dire cose diverse sullo stesso billing account.

Un id che non trova un billing account non ha niente da presidiare; il billing account, del resto, non si
cancella. Spostare l'azienda predefinita non cambia l'azienda di nessun billing account, e non chiede questo
controllo. Il
guard gira coi privilegi del proprietario: coi permessi di chi scrive, un billing account di un'altra azienda
sarebbe invisibile e il controllo direbbe «a posto» proprio nel caso da fermare.

---

### Codici errore

* `E_ISTANZA_EMITTENTI_DIVERSI` — due billing account della stessa istanza risolvono a due aziende. Il
  messaggio nomina i due billing account e l'istanza per codice.

---

### Test

* `db/pgtap/anagrafiche/test-istanza-nasce-col-ba-v1.sql` — un secondo billing account della stessa istanza e
  della stessa azienda vive; spostato su un'altra azienda è rifiutato.

---

### Note di migrazione

* 2026-10-08 — nasce con la regola «un'istanza, un'azienda».
* 2026-11-26 — ogni billing account ha sempre il suo collegamento: il confronto risponde col collegamento, e il
  gemello che giudicava lo spostamento della predefinita è ritirato.

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

---

{% include-markdown "signature-core.md" %}
