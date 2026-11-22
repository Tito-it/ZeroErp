## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_ba_gestore_globale_storia`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — la riga della predefinita
> * [vendite.fatture](/dbzero/vendite/tabelle/fatture) — guardata per scegliere il billing account
> * [vendite.commesse](/dbzero/vendite/tabelle/commesse) — guardata per scegliere il billing account
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_guard_ba_cambio_emittente](/dbzero/anagrafiche/funzioni/fn_guard_ba_cambio_emittente) — decide e compone il rifiuto
> * [anagrafiche.fn_ba_ha_storia_emittente](/dbzero/anagrafiche/funzioni/fn_ba_ha_storia_emittente) — la definizione di storia della delegata
> * [anagrafiche.trgfn_efba_guard_storia_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_storia_emittente) — chiamante
> * [anagrafiche.fn_guard_albero_ba_gestore_globale](/dbzero/anagrafiche/funzioni/fn_guard_albero_ba_gestore_globale) — l'altro cancello sullo stesso movimento

---

### 🎯 Scopo Principale

`anagrafiche.fn_guard_ba_gestore_globale_storia` impedisce di spostare l'azienda predefinita quando un billing
account senza collegamento, che la segue, ha già una storia.

---

### Il raggio più largo del dominio

Gli altri controlli guardano un billing account. Spostare la predefinita cambia l'azienda di **tutti** quelli
senza collegamento: una riga sola può riattribuire l'azienda di un numero qualunque di documenti già emessi.
La chiama il trigger della storia quando la riga toccata è quella senza billing account: quando la predefinita
cambia azienda, quando ne nasce una nuova, quando sparisce. Se l'azienda non cambia davvero esce subito.

---

### Cerca un billing account e delega

La risposta a «c'è storia?» non cambia dopo il primo cliente che ne ha: il guard cerca **il primo** billing
account senza collegamento con fatture o commesse, in ordine di id, e lo passa a `fn_guard_ba_cambio_emittente`
con le due aziende della predefinita, prima e dopo. Il messaggio è quindi quello del singolo billing account,
e nomina un cliente vero invece di dire «da qualche parte»; l'ordine fisso fa sì che due tentativi uguali
nominino lo stesso cliente.

Su un'installazione che ha già fatturato questo cancello chiude quasi sempre, ed è corretto: spostare la
predefinita lì è una riscrittura della storia. Se serve un'altra azienda, si collegano esplicitamente i
clienti che devono passarci, e per quelli con documenti numerati vale la regola di sempre: una fornitura nuova
presso la nuova azienda.

Gira coi privilegi del proprietario: legge billing account, fatture e commesse, che hanno regole di visibilità.

---

### ⚠️ Che cosa oggi non copre

* **Sceglie con una definizione di storia diversa da quella con cui si decide.** Il billing account da
  guardare è il primo che ha **una fattura o una commessa**, in qualunque stato; la delegata decide invece sul
  **documento numerato di qualunque famiglia**. Le due definizioni divergono in due versi:
  * un billing account senza collegamento che ha solo ordini, DDT o resi numerati non viene scelto, e lo
    spostamento passa;
  * se il primo scelto ha solo una fattura o una commessa senza numero, la delegata non solleva, e gli altri
    billing account non si guardano: lo spostamento passa anche se uno di loro ha documenti numerati.

---

### Codici errore

* `E_BA_EMITTENTE_CON_STORIA` — dalla delegata, col billing account scelto.

---

### Test

* `db/pgtap/anagrafiche/test-istanza-ba-gestore-globale-v1.sql` e
  `db/pgtap/anagrafiche/test-cliente-manuale-chiave-unica-v1.sql` — spostano la predefinita in scene costruite
  e attraversano questo cancello; nessuno dei due prova il rifiuto per storia.

---

### Note di migrazione

* 2026-08-26 — nasce, quando «storia» erano fatture e commesse. Dal 2026-08-31 la delegata decide sui documenti
  numerati di qualunque famiglia, e la scelta del billing account qui non è cambiata.

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

---

{% include-markdown "signature-core.md" %}
