## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_albero_ba_emittente`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — l'albero padre/figli
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_ba_coppia_emittente_omogenea](/dbzero/anagrafiche/funzioni/fn_check_ba_coppia_emittente_omogenea) — il confronto di una coppia
> * [anagrafiche.trgfn_billing_account_guard_albero_emittente](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_albero_emittente) — chiamante: nasce un billing account, o cambia il padre
> * [anagrafiche.trgfn_efba_guard_albero_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_albero_emittente) — chiamante: cambia il collegamento all'azienda
> * [anagrafiche.fn_guard_albero_ba_gestore_globale](/dbzero/anagrafiche/funzioni/fn_guard_albero_ba_gestore_globale) — lo stesso controllo, quando si sposta la predefinita

---

### 🎯 Scopo Principale

`anagrafiche.fn_guard_albero_ba_emittente` verifica che un billing account sia della stessa azienda del suo
padre e di tutti i suoi figli, e ferma l'operazione con `E_ALBERO_EMITTENTE_MISTO` se non lo è.

---

### Perché un albero misto è un danno muto

L'azienda che emette la fattura di un albero si prende dal padre. Un albero che attraversa due aziende produce
quindi documenti emessi da un'azienda che chi ha lavorato sul figlio non vede, su una numerazione che non è la
sua. Nessun dato è sbagliato da solo, e nessun errore compare: per questo il controllo sta nel database.

---

### Due versi: il padre e i figli

Il controllo guarda prima **verso il padre**, poi **verso ogni figlio**, in ordine. Il secondo è quello che si
dimentica: cambiare l'azienda di un billing account non spezza solo il legame verso l'alto, ma tutti quelli
verso il basso in un colpo. Il primo rifiuto trovato dice il verso, i due billing account e le due aziende.

L'azienda confrontata è quella risolta, sui tre livelli; un billing account che non esiste più (cancellato
nella stessa transazione) non ha niente da presidiare.

---

### ⭐ Coi privilegi del proprietario, senza interruttori

`billing_account` ha regole di visibilità per azienda: coi permessi di chi scrive, un padre o un figlio di
un'altra azienda sarebbe invisibile, e «non lo vedo» diventerebbe «è a posto». Il guard gira quindi coi
privilegi del proprietario. Non ha eccezioni per i dati preesistenti né un modo per spegnerlo.

Risponde a una domanda diversa da quella della storia: un cambio di azienda ammesso perché il cliente non ha
documenti numerati resta vietato se rende misto l'albero. I due cancelli si sommano.

---

### ⚠️ Che cosa oggi non copre

* **Lo scollegamento fatto in sessione.** Tolto il collegamento da un utente in sessione, il billing account
  si confronta con l'azienda di chi agisce, non con la predefinita su cui ricade: l'albero può restare misto
  per l'installazione (vedi `fn_check_ba_coppia_emittente_omogenea`).

---

### Codici errore

* `E_ALBERO_EMITTENTE_MISTO` — il billing account e il padre, o un figlio, risolvono a due aziende diverse.
  Il contesto porta il verso (`padre` o `figlio`) e il campo `parent_account_id`.

---

### Test

* `db/pgtap/anagrafiche/test-guard-albero-ba-omogeneo-v1.sql` — padre di un'altra azienda, azienda cambiata sul
  figlio e sul padre, collegamento del figlio cancellato: tutti rifiutati; due alberi separati dello stesso
  soggetto ammessi; il guard vede un figlio fuori dal perimetro di chi scrive.

---

### Note di migrazione

* 2026-08-18 — nasce col perimetro dell'azienda sulle liste e sulla gerarchia dei billing account.

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

---

{% include-markdown "signature-core.md" %}
