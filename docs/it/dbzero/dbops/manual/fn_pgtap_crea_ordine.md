## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_ordine`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.ordini](/dbzero/vendite/tabelle/ordini) — la testata che la fixture scrive
>
> Approfondimento funzioni:
>
> * [dbops.fn_pgtap_cliente_del_builder](/dbzero/dbops/funzioni/fn_pgtap_cliente_del_builder) — il cliente: quello del test o uno nuovo
> * [dbops.fn_pgtap_crea_mondo_cliente](/dbzero/dbops/funzioni/fn_pgtap_crea_mondo_cliente) — il mondo, quando il test non passa un cliente
> * [dbops.fn_pgtap_cliente_ba_del_mondo](/dbzero/dbops/funzioni/fn_pgtap_cliente_ba_del_mondo) — la verifica del billing account del test
> * [dbops.fn_pgtap_crea_ordine_con_righe](/dbzero/dbops/funzioni/fn_pgtap_crea_ordine_con_righe) — l'ordine con le righe, costruito sopra questa
> * [dbops.fn_pgtap_crea_preventivo](/dbzero/dbops/funzioni/fn_pgtap_crea_preventivo) — il gemello, per il preventivo
> * [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato) — la strada per portarlo avanti
> * [script.fn_doc_stato_id](/dbzero/script/funzioni/fn_doc_stato_id) — lo stato chiesto, per codice, fra i soli attivi
> * [vendite.fn_get_valuta_id](/dbzero/vendite/funzioni/fn_get_valuta_id) — la valuta, dalla catena del dominio
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — le fixture e quando usarle

---

### 🎯 Scopo Principale

Un ordine di vendita del mondo, **senza righe**, in una chiamata sola: l'azienda con il suo
operatore, il cliente fatturabile e la testata nello stato scelto. Restituisce tutte le
chiavi, `uid` compreso, che serve a chi lega un documento a valle con la sua sorgente.

---

### ⭐ Perché esiste

L'ordine si scriveva a mano in molti pgTAP, ognuno con la sua ricetta: chi pescava cliente
ed emittente dal database (e su un database ricostruito da zero non trovava niente), chi li
prendeva da un mondo costruito ma sceglieva valuta, utility ed emittente a modo suo. Era la
stessa regola scritta più volte: ora ha una sede.

---

### Che cosa decide la fixture e che cosa decide il dominio

* **Il cliente**: senza billing account dal test, il mondo di
  [dbops.fn_pgtap_crea_mondo_cliente](/dbzero/dbops/funzioni/fn_pgtap_crea_mondo_cliente)
  (senza contesto lo costruisce e lo apre sull'operatore che costruisce; con un contesto
  aperto riusa l'azienda di chi agisce, con un cliente nuovo a ogni chiamata). Col billing
  account di un cliente già costruito — per due ordini dello stesso cliente — quel conto,
  **verificato** dell'azienda di chi agisce: uno di un'altra azienda si ferma subito.
* **L'emittente** è quello del cliente, scritto esplicito: è lo stesso che il controllo
  emittente/billing account pretende.
* **Utility** dal billing account. **La valuta** dalla catena del dominio,
  [vendite.fn_get_valuta_id](/dbzero/vendite/funzioni/fn_get_valuta_id) («cliente → azienda →
  gestore»), scritta esplicita: è la valuta che il dominio darebbe all'ordine, e il cliente di
  prova ne ha una perché i builder delle radici la scrivono.
* **La data** dell'ordine si sceglie **alla nascita**: fuori bozza è congelata, quindi o si
  sceglie qui o non si sceglie più. Senza, vale il default della colonna (la data
  operativa). Serve a chi costruisce bolle di date passate.
* **Numero, anno, registro e momento di fatturazione** non li scrive: li assegnano i
  trigger del dominio, come in produzione.

---

### ⛔ Le righe non le scrive

Le righe sono il caso del test, e si scrivono **solo in bozza**. Chi vuole un ordine con le
righe già scritte usa
[dbops.fn_pgtap_crea_ordine_con_righe](/dbzero/dbops/funzioni/fn_pgtap_crea_ordine_con_righe),
che compone questa fixture.

---

### Nasce in bozza, poi si porta avanti

Un documento nasce solo nel suo stato iniziale. L'ordine nasce in bozza e, se il test chiede
un altro stato, ci arriva per la matrice dei passaggi
([dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato)), dal verbo
dell'ordine, sotto i controlli veri. Un passaggio che pretende ciò che la fixture non scrive
(le righe, per la conferma) qui si ferma: allora il test chiede la bozza, scrive le righe e
porta avanti da sé.

Lo stato chiesto si traduce per codice **prima** di costruire, con
[script.fn_doc_stato_id](/dbzero/script/funzioni/fn_doc_stato_id), fra i soli stati attivi: uno
stato che non c'è, o che è spento, ferma la fixture subito, senza lasciare un mondo a metà.

Esce con i vincoli **richiusi** (`IMMEDIATE`), come ogni helper di fixture.

---

### Test

* `db/pgtap/dbops/test-fn-pgtap-crea-ordine-v1.sql` — la testata esiste ed è scrivibile;
  l'emittente è quello del billing account; numero e registro vengono dal dominio; lo stato
  chiesto si raggiunge per la matrice, uno inesistente parla e uno spento si ferma prima di
  costruire; la valuta è quella del billing account; la seconda chiamata riusa
  l'azienda; il cliente del test è riusato e uno di un'altra azienda rifiutato; la conferma
  senza righe non si salta; la data scelta alla nascita.

---

### Note di migrazione

* 2026-10-07 — nasce per raccogliere le ricette dei test (`brief-db-fixture-rls-documenti-costruiti`,
  giro 2).
* 2026-10-22 — terzo parametro, il billing account di un cliente già costruito (richiesta BE R-3).
* 2026-10-24 — l'ordine nasce in bozza e lo stato chiesto si raggiunge per la matrice
  (`brief-modello-documento-vendita` N-1).
* 2026-10-25 — quarto parametro, la data alla nascita (`brief-db-pgtap-bolla-e-reso-costruiti` D-1).
* 2026-10-27 — lo stato iniziale si legge dalla testata e non dal vocabolario
  (`brief-modello-documento-vendita` §15.13).
* 2026-11-08 — lo stato chiesto si traduce dalla sede, fra i soli attivi: uno stato spento si
  ferma prima di costruire; la valuta viene dalla catena del dominio, non è più la prima del
  catalogo.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
