## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_albero_ba_gestore_globale`

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
> * [anagrafiche.fn_guard_albero_ba_emittente](/dbzero/anagrafiche/funzioni/fn_guard_albero_ba_emittente) — lo stesso controllo, su un billing account
> * [anagrafiche.fn_guard_istanza_ba_gestore_globale](/dbzero/anagrafiche/funzioni/fn_guard_istanza_ba_gestore_globale) — il gemello sull'istanza
> * [anagrafiche.fn_guard_ba_gestore_globale_storia](/dbzero/anagrafiche/funzioni/fn_guard_ba_gestore_globale_storia) — il cancello della storia sullo stesso movimento

---

### 🎯 Scopo Principale

`anagrafiche.fn_guard_albero_ba_gestore_globale` impedisce che lo spostamento dell'azienda predefinita lasci un
albero di billing account su due aziende, e lo ferma con `E_ALBERO_EMITTENTE_MISTO`.

---

### Una riga sposta molti billing account

Un billing account senza collegamento appartiene all'azienda predefinita. Spostare la predefinita cambia in
un colpo l'azienda di tutti quelli senza collegamento, senza che nessuno abbia scritto un'azienda su di loro.
La chiama il trigger dell'albero quando la riga toccata è quella senza billing account.

---

### Conta la coppia mista

| Padre e figlio | Spostando la predefinita |
| --- | --- |
| tutti e due senza collegamento | si spostano insieme: l'albero resta omogeneo |
| tutti e due collegati | non si sposta nessuno dei due |
| uno collegato e uno no | ⚠️ si separano |

Il controllo cerca quindi la prima coppia padre/figlio in cui almeno uno è senza collegamento e le cui aziende,
a spostamento fatto, sono diverse, e la nomina nel rifiuto, con gli stessi valori del guard sul singolo billing
account. Un controllo più largo («esiste un albero») fermerebbe spostamenti legittimi.

---

### ⭐ L'azienda per l'installazione, non per chi agisce

L'azienda di ogni billing account si chiede con `script.fn_get_ba_emittente_sr_id_installazione`: il
collegamento, altrimenti la predefinita. Col livello di sessione, a un utente con la sua azienda il billing
account senza collegamento sembrerebbe restare alla sua azienda, e lo spostamento passerebbe sopra un albero
misto. Il rifiuto non dipende da chi sposta.

Gira coi privilegi del proprietario: legge `billing_account`, che ha regole di visibilità per azienda.

---

### ⚠️ Che cosa oggi non copre

* **Una coppia già mista prima dello spostamento.** Il controllo guarda lo stato dopo lo spostamento, non la
  differenza: una coppia mista che c'era già (per esempio dopo uno scollegamento fatto in sessione, vedi
  `fn_check_ba_coppia_emittente_omogenea`) ferma ogni spostamento della predefinita che non vada sull'azienda
  del billing account collegato, anche quando lo spostamento non c'entra.

---

### Codici errore

* `E_ALBERO_EMITTENTE_MISTO` — dopo lo spostamento, un padre e un figlio, di cui almeno uno senza collegamento,
  sono di due aziende.

---

### Test

* `db/pgtap/anagrafiche/test-guard-albero-ba-omogeneo-v1.sql` — predefinita spostata con una coppia mista:
  rifiutata; con una coppia omogenea: passa.
* `db/pgtap/anagrafiche/test-istanza-ba-gestore-globale-v1.sql` — lo stesso rifiuto da un operatore con la sua
  azienda; la predefinita portata sull'azienda del collegato passa.

---

### Note di migrazione

* 2026-08-18 — nasce col controllo dell'albero omogeneo.
* 2026-10-10 — chiede l'azienda per l'installazione: prima delegava al guard del singolo billing account, che
  risolve per chi agisce, e uno spostamento fatto da un utente con la sua azienda passava sopra un albero misto.

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

---

{% include-markdown "signature-core.md" %}
