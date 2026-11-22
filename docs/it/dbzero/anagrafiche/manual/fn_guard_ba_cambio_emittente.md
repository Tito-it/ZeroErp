## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_ba_cambio_emittente`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — il collegamento che si vuole cambiare
>
> Approfondimento funzioni:
>
> * [script.fn_check_ba_cambio_emittente](/dbzero/script/funzioni/fn_check_ba_cambio_emittente) — dove sta la regola
> * [script.fn_raise_primo_motivo_se_presente](/dbzero/script/funzioni/fn_raise_primo_motivo_se_presente) — solleva il primo motivo
> * [anagrafiche.trgfn_efba_guard_storia_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_storia_emittente) — chiamante: i movimenti del collegamento
> * [anagrafiche.fn_guard_ba_gestore_globale_storia](/dbzero/anagrafiche/funzioni/fn_guard_ba_gestore_globale_storia) — chiamante: lo spostamento della predefinita

---

### 🎯 Scopo Principale

`anagrafiche.fn_guard_ba_cambio_emittente` impedisce di cambiare l'azienda di un billing account che ha già una
storia, cioè almeno un documento numerato su un registro, e lo ferma con `E_BA_EMITTENTE_CON_STORIA`.

---

### Libero finché non c'è storia, vietato dopo

Un documento numerato porta il numero del registro di un'azienda, e non lo cambia: spostare il cliente su
un'altra azienda lascerebbe quei documenti a chi non vede più il cliente a cui si riferiscono. Vietare ogni
cambio, però, renderebbe definitivo un errore ordinario: il collegamento nasce con l'azienda di chi crea il
cliente, e chi lavora sull'azienda sbagliata crea un cliente sbagliato. La regola tiene aperta la correzione
finché sul cliente non è passato del lavoro numerato.

Riceve il billing account e le due aziende, prima e dopo: quando sono la stessa il cambio non sposta niente e
passa, anche con la storia. È il caso di un collegamento tolto quando la predefinita è la stessa azienda.

---

### ⭐ La regola non sta qui

Il guard chiede a `script.fn_check_ba_cambio_emittente` l'elenco ordinato dei motivi e solleva il primo,
coi suoi valori. La stessa check è quella da cui la lista dei collegamenti di un'azienda prende il motivo per
spegnere il cestino di riga: il pulsante spento e il rifiuto non possono dire due cose diverse, perché sono la
stessa riga di codice. Per questo l'ordine dei motivi è un contratto.

Il messaggio nomina il billing account, l'azienda di prima per codice e le famiglie di documento che bloccano,
con i conteggi. Non c'è un campo da correggere: è la situazione che non lo consente.

Non risale ai billing account figli: un cambio che spezzerebbe l'albero lo respinge il guard dell'albero, con
un messaggio più preciso. Nessuna eccezione per i dati preesistenti e nessun modo per spegnerlo.

---

### ⚠️ Che cosa oggi non copre

* **Quando lo chiama la predefinita**, il billing account da guardare lo sceglie
  `fn_guard_ba_gestore_globale_storia` con un'altra definizione di storia: il guard decide bene sul billing
  account che riceve, ma può non ricevere quello giusto.

---

### Codici errore

* `E_BA_EMITTENTE_CON_STORIA` — l'azienda cambia davvero e il billing account ha almeno un documento numerato.

---

### Test

* `db/pgtap/anagrafiche/test-ba-cambio-emittente-storia-v1.sql` — lo stesso cambio sullo stesso cliente passa
  appena nato ed è respinto dopo una commessa; passa se l'azienda non cambia davvero; la frase nomina la
  specie e l'azienda per codice; il guard chiama la check e non contiene il predicato.
* `db/pgtap/anagrafiche/test-ba-storia-solo-numerati-v1.sql` — col DDT in bozza passa, col DDT emesso no.

---

### Note di migrazione

* 2026-08-26 — nasce: prima il collegamento di un cliente si spostava senza condizioni.
* 2026-08-27 — il predicato passa in `script.fn_check_ba_cambio_emittente`.
* 2026-08-31 — la storia diventa «documento numerato di qualunque famiglia»: prima erano fatture e commesse, e
  ordini e DDT restavano fuori perché un controllo ne riallinea l'azienda al cliente; il numero del registro,
  invece, non lo riallinea nessuno.

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

---

{% include-markdown "signature-core.md" %}
