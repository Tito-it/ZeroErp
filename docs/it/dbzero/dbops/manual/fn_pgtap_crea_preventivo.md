## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_preventivo`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.preventivi](/dbzero/vendite/tabelle/preventivi) — la testata che la fixture scrive
>
> Approfondimento funzioni:
>
> * [dbops.fn_pgtap_crea_mondo_cliente](/dbzero/dbops/funzioni/fn_pgtap_crea_mondo_cliente) — il mondo su cui la fixture appoggia la testata
> * [dbops.fn_pgtap_crea_preventivo_con_righe](/dbzero/dbops/funzioni/fn_pgtap_crea_preventivo_con_righe) — il preventivo con una riga, costruito sopra questa
> * [dbops.fn_pgtap_crea_ordine](/dbzero/dbops/funzioni/fn_pgtap_crea_ordine) — il gemello, per l'ordine
> * [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato) — la strada per portarlo avanti
> * [script.fn_doc_stato_id](/dbzero/script/funzioni/fn_doc_stato_id) — lo stato chiesto, per codice, fra i soli attivi
> * [vendite.fn_get_valuta_id](/dbzero/vendite/funzioni/fn_get_valuta_id) — la valuta, dalla catena del dominio
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — le fixture e quando usarle

---

### 🎯 Scopo Principale

Un preventivo del mondo, **senza righe**, in una chiamata sola: l'azienda con il suo
operatore, il cliente fatturabile e la testata nello stato scelto. Restituisce tutte le
chiavi, `uid` compreso.

---

### ⭐ Perché esiste

Il preventivo si scriveva a mano in molti pgTAP, ognuno con la sua ricetta: chi lo pescava dal
database, chi lo scriveva col billing account e chi senza, chi sceglieva validità e valuta a
modo suo. Era la stessa regola scritta più volte: ora ha una sede.

---

### Che cosa decide la fixture e che cosa decide il dominio

* **Il mondo** viene sempre da
  [dbops.fn_pgtap_crea_mondo_cliente](/dbzero/dbops/funzioni/fn_pgtap_crea_mondo_cliente):
  senza contesto lo costruisce e lo apre sull'operatore che costruisce; con un contesto
  aperto riusa l'azienda di chi agisce, con un cliente nuovo a ogni chiamata. A differenza
  dell'ordine, non accetta il cliente di un'altra fixture.
* **L'emittente** è quello del mondo, scritto esplicito; **istanza e utility** sono quelle
  del billing account. Sono le coppie che i controlli del preventivo verificano.
* **La valuta** viene dalla catena del dominio,
  [vendite.fn_get_valuta_id](/dbzero/vendite/funzioni/fn_get_valuta_id), scritta esplicita, come
  per l'ordine e la fattura: è la valuta che il trigger di default darebbe al preventivo.
* **La validità** va da oggi (la data operativa dell'azienda) a trenta giorni: un caso che la
  vuole diversa la scrive lui.
* **Il numero** non lo scrive: lo genera il dominio.

---

### ⛔ Le righe non le scrive

Le righe sono il caso del test, e si scrivono **solo in bozza**. Chi vuole un preventivo già
emesso, con una riga valida, usa
[dbops.fn_pgtap_crea_preventivo_con_righe](/dbzero/dbops/funzioni/fn_pgtap_crea_preventivo_con_righe).

---

### Nasce in bozza, poi si porta avanti

Un documento nasce solo nel suo stato iniziale. Il preventivo nasce in bozza e, se il test
chiede un altro stato, ci arriva per la matrice dei passaggi
([dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato)), dal verbo del
preventivo, sotto i controlli veri. L'emissione chiede almeno una riga attiva: chiesta a
questa fixture, che non scrive righe, si ferma lì. Uno stato che non chiede righe (per
esempio l'annullo dalla bozza) si raggiunge.

Lo stato chiesto si traduce per codice **prima** di costruire, con
[script.fn_doc_stato_id](/dbzero/script/funzioni/fn_doc_stato_id), fra i soli stati attivi: uno
stato che non c'è, o che è spento, ferma la fixture subito, senza lasciare un mondo a metà.

Esce con i vincoli **richiusi** (`IMMEDIATE`), come ogni helper di fixture.

---

### Test

* `db/pgtap/dbops/test-fn-pgtap-crea-preventivo-v1.sql` — la testata esiste col billing
  account e l'istanza tornati; l'emittente è quello del billing account; il numero viene dal
  dominio e la validità parte da oggi; uno stato senza righe (l'annullo) si raggiunge, mentre
  l'emissione senza righe si ferma; la seconda chiamata riusa l'azienda; uno stato inesistente
  parla, e uno spento si ferma prima di costruire.

---

### Note di migrazione

* 2026-10-07 — nasce per raccogliere le ricette dei test (`brief-db-fixture-rls-documenti-costruiti`,
  giro 2).
* 2026-10-24 — il preventivo nasce in bozza e lo stato chiesto si raggiunge per la matrice
  (`brief-modello-documento-vendita` N-1).
* 2026-10-27 — lo stato iniziale si legge dalla testata e non dal vocabolario
  (`brief-modello-documento-vendita` §15.13).
* 2026-11-08 — lo stato chiesto si traduce dalla sede, fra i soli attivi: uno stato spento si
  ferma prima di costruire; la valuta viene dalla catena del dominio, non è più la prima del
  catalogo.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
