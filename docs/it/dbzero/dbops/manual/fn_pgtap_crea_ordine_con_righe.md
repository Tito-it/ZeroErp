## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_ordine_con_righe`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe) — le righe che la fixture scrive in bozza
>
> Approfondimento funzioni:
>
> * [dbops.fn_pgtap_crea_ordine](/dbzero/dbops/funzioni/fn_pgtap_crea_ordine) — la testata su cui si appoggia, che resta senza righe
> * [dbops.fn_pgtap_crea_articolo](/dbzero/dbops/funzioni/fn_pgtap_crea_articolo) — l'articolo di merce costruito quando il test non ne dà uno
> * [dbops.fn_pgtap_crea_ddt_da_ordine](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt_da_ordine) — la bolla che nasce da questo ordine
> * [dbops.fn_pgtap_crea_preventivo_con_righe](/dbzero/dbops/funzioni/fn_pgtap_crea_preventivo_con_righe) — il gemello, per il preventivo
> * [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato) — la strada per portarlo avanti
> * [script.fn_doc_stato_id](/dbzero/script/funzioni/fn_doc_stato_id) — lo stato chiesto, per codice, fra i soli attivi
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — le fixture e quando usarle

---

### 🎯 Scopo Principale

Un ordine con le sue righe, nello stato chiesto (di norma **confermato**), in una chiamata
sola, per la strada vera del dominio: testata in bozza, righe in bozza, poi lo stato per la
matrice.

---

### ⭐ Perché esiste: la trappola d'ordine

Una trentina di test scrivevano a mano la stessa strada in un ordine obbligato: la testata in
bozza con la data scelta alla nascita, il momento di fatturazione riscritto in bozza, le
righe con la loro aliquota, poi la conferma. La stessa strada viveva anche dentro il builder
della bolla da ordine. Ora ha una sede, e la bolla da ordine la compone.

---

### Che cosa decide la fixture e che cosa decide il dominio

* **La testata** la fa [dbops.fn_pgtap_crea_ordine](/dbzero/dbops/funzioni/fn_pgtap_crea_ordine),
  che **resta senza righe** per scelta: i test che provano le righe le scrivono da sé. Qui la
  testata nasce col cliente del test (o uno nuovo) e con la data scelta alla nascita.
* **Il momento di fatturazione** si scrive in bozza, se il test lo sceglie: all'inserimento
  il dominio lo eredita dal billing account, e fuori bozza è congelato.
* **Le righe**: una dai parametri (di norma 10 pezzi a 25), oppure più righe descritte dal
  test, con articolo, quantità, prezzo, sconto, aliquota, descrizione e date di consegna
  (richiesta dal cliente e confermata). Le due forme insieme sono un errore, e una chiave che
  la fixture non conosce si ferma: un errore di battitura non passa in silenzio. Quando
  mancano, l'articolo è uno di merce non gestita costruito apposta e l'aliquota è la prima
  attiva; lo sconto si scrive solo se chiesto, perché il suo default è della tabella.
* **Lo stato** chiesto lo traduce
  [script.fn_doc_stato_id](/dbzero/script/funzioni/fn_doc_stato_id), fra i soli stati attivi
  (uno stato spento si rifiuta prima di costruire), e si raggiunge per la matrice dei passaggi,
  sotto i controlli veri; `DRAFT`
  lascia l'ordine in bozza con le righe.
* **Una testata del test**, in bozza: quando la testata è il caso del test (un emittente di
  default, un flag, dei termini) la fixture ci scrive righe e stato. Cliente, data e momento
  di fatturazione sono allora della testata, e passarli è un errore; una testata fuori bozza
  si rifiuta, perché le righe si scrivono solo in bozza.

Restituisce l'ordine, la sua **prima** riga (per numero) e il suo articolo, il cliente,
l'azienda, l'operatore e lo stato. Con più righe, il test le legge da sé.

---

### ⚠️ Le regole delle righe le giudica il dominio

La fixture non filtra gli articoli: un articolo-onere passato dal test entra con le regole
dell'ordine (un onere non ha date di consegna; un ordine di soli oneri non si conferma), e
se le viola si ferma col motivo vero.

Stato, forme delle righe e chiavi si giudicano **prima** di costruire. Senza un contesto
aperto, il mondo lo apre sull'operatore che costruisce. Esce con i vincoli **richiusi**
(`IMMEDIATE`), come ogni helper di fixture.

---

### Test

* `db/pgtap/dbops/test-fn-pgtap-crea-ordine-con-righe-v1.sql` — l'ordine confermato con la
  riga e l'aliquota; data alla nascita e momento di fatturazione; due righe in bozza con
  sconto e data di consegna sulla riga giusta; il builder della testata resta senza righe;
  la riga aggiunta alla testata del test, che si conferma; gli errori del chiamante rifiutati.

---

### Note di migrazione

* 2026-10-25 — nasce per raccogliere la strada che i test ricopiavano, e ritira la copia che
  stava nel builder della bolla da ordine (`brief-db-pgtap-reso-costruito`, E-1).
* 2026-10-27 — lo stato iniziale si legge dalla testata e non dal vocabolario
  (`brief-modello-documento-vendita` §15.13).
* 2026-11-08 — lo stato chiesto si traduce dalla sede, fra i soli attivi, invece che da una copia
  della regola.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
