## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_istanza_ba_gestore_globale`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — la riga della predefinita
>
> Approfondimento funzioni:
>
> * [script.fn_get_ba_emittente_sr_id_installazione](/dbzero/script/funzioni/fn_get_ba_emittente_sr_id_installazione) — l'azienda per l'installazione
> * [anagrafiche.fn_guard_istanza_ba_emittente](/dbzero/anagrafiche/funzioni/fn_guard_istanza_ba_emittente) — lo stesso controllo, su un billing account
> * [anagrafiche.fn_guard_albero_ba_gestore_globale](/dbzero/anagrafiche/funzioni/fn_guard_albero_ba_gestore_globale) — il gemello sull'albero
> * [anagrafiche.fn_guard_ba_gestore_globale_storia](/dbzero/anagrafiche/funzioni/fn_guard_ba_gestore_globale_storia) — il cancello della storia sullo stesso movimento
>
> Guide:
>
> * [Gestione delle istanze utility](/guide/gestione-delle-istanze-utility) — un'istanza, un'azienda

---

### 🎯 Scopo Principale

`anagrafiche.fn_guard_istanza_ba_gestore_globale` impedisce che lo spostamento dell'azienda predefinita lasci
un'istanza con billing account di due aziende, e lo ferma con `E_ISTANZA_EMITTENTI_DIVERSI`.

---

### Conta la coppia mista

Un billing account senza collegamento segue la predefinita. Due billing account della stessa istanza tutti e
due senza collegamento si spostano insieme; tutti e due collegati non si spostano; uno collegato e uno no si
separano. Il guard cerca la prima coppia, in ordine, di un billing account senza collegamento e di un altro
della stessa istanza le cui aziende, a spostamento fatto, sono diverse, e la nomina nel rifiuto con gli stessi
valori del guard sul singolo billing account.

---

### ⭐ L'azienda per l'installazione, non per chi agisce

L'azienda di ciascuno si chiede con `script.fn_get_ba_emittente_sr_id_installazione`: il collegamento,
altrimenti la predefinita. Col livello di sessione, a un utente con la sua azienda il billing account senza
collegamento sembrerebbe restare alla sua azienda, e lo spostamento passerebbe. Il rifiuto non dipende da chi
sposta: lo stesso a un operatore con la sua azienda e a un super admin senza.

Gira coi privilegi del proprietario: legge `billing_account`, che ha regole di visibilità per azienda. Lo
chiama il trigger dell'istanza quando la riga toccata è quella senza billing account, e anche quando una
modifica trasforma un collegamento nella riga predefinita o il contrario.

---

### ⚠️ Che cosa oggi non copre

* **Una coppia già mista prima dello spostamento** ferma ogni spostamento della predefinita che non vada
  sull'azienda dell'altro billing account, anche quando lo spostamento non c'entra: il controllo guarda lo
  stato dopo, non la differenza.

---

### Codici errore

* `E_ISTANZA_EMITTENTI_DIVERSI` — dopo lo spostamento, un billing account senza collegamento e un altro della
  stessa istanza sono di due aziende. Il messaggio nomina i due billing account e l'istanza per codice.

---

### Test

* `db/pgtap/anagrafiche/test-istanza-ba-gestore-globale-v1.sql` — lo spostamento sopra un'istanza mista è
  rifiutato sia a un operatore con la sua azienda sia a un super admin senza, e la frase nomina l'istanza
  costruita; verso l'azienda del collegato passa.

---

### Note di migrazione

* 2026-10-08 — nasce con la regola «un'istanza, un'azienda».
* 2026-10-10 — chiede l'azienda per l'installazione: prima delegava al guard del singolo billing account, che
  risolve per chi agisce, e uno spostamento fatto da un utente con la sua azienda passava sopra una coppia mista.

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

---

{% include-markdown "signature-core.md" %}
