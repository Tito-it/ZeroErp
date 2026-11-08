## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_preventivo_con_righe`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe) — la riga che la fixture scrive in bozza
>
> Approfondimento funzioni:
>
> * [dbops.fn_pgtap_crea_preventivo](/dbzero/dbops/funzioni/fn_pgtap_crea_preventivo) — la testata su cui si appoggia, che resta senza righe
> * [dbops.fn_pgtap_crea_articolo](/dbzero/dbops/funzioni/fn_pgtap_crea_articolo) — l'articolo di merce costruito quando il test non ne dà uno
> * [script.fn_natura_e_merce](/dbzero/script/funzioni/fn_natura_e_merce) — il predicato del dominio che sceglie la natura di merce
> * [vendite.trgfn_preventivi_guard_transizione](/dbzero/vendite/funzioni/trgfn_preventivi_guard_transizione) — il controllo dell'emissione che chiede una riga attiva
> * [dbops.fn_pgtap_crea_ordine_con_righe](/dbzero/dbops/funzioni/fn_pgtap_crea_ordine_con_righe) — il gemello, per l'ordine
> * [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato) — la strada per portarlo avanti
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — le fixture e quando usarle

---

### 🎯 Scopo Principale

Un preventivo con **una riga valida per l'emissione**, nello stato chiesto (di norma
**emesso**), in una chiamata sola, per la strada vera del dominio: la riga in bozza, poi lo
stato per la matrice, dal verbo.

---

### ⭐ Perché esiste

L'emissione di un preventivo chiede almeno una riga attiva. Prima che il cambio di stato
passasse dal verbo, i test emettevano preventivi senza righe, un documento che il modello
non ammette; la fixture è la strada corta e giusta per averne uno emesso, accettato o oltre.

---

### Che cosa decide la fixture e che cosa decide il dominio

* **La testata** è nuova, da [dbops.fn_pgtap_crea_preventivo](/dbzero/dbops/funzioni/fn_pgtap_crea_preventivo)
  (che resta senza righe), oppure quella del test, che deve essere in bozza: fuori bozza si
  rifiuta, perché le righe si scrivono solo in bozza.
* **La riga** è una sola, di quantità 1, a prezzo 10 se il test non lo sceglie, con la prima
  aliquota **positiva** del catalogo, dell'articolo del test o di un articolo costruito su
  una natura di vendita di **merce**, attiva. Che una natura sia merce lo dice il predicato del
  dominio `script.fn_natura_e_merce`, non la fixture: se la regola cambia, la fixture la segue.
* **Lo stato** si raggiunge per la matrice dei passaggi, sotto i controlli veri: validità,
  prezzi autorizzati, emettibilità li giudica il dominio. La validità è quella della testata
  (da oggi a trenta giorni per quella costruita), quindi l'accettazione la regge.

Restituisce la testata, la riga scritta e il suo articolo, il billing account, l'azienda,
l'operatore del contesto e lo stato. Uno stato che non c'è (fra quelli attivi) si ferma prima
di costruire.

Senza un contesto aperto, il mondo lo apre sull'operatore che costruisce. Esce con i vincoli
**richiusi** (`IMMEDIATE`), come ogni helper di fixture.

---

### Test

Non ha un presidio suo. La usano, fra gli altri,
`db/pgtap/script/test-fn-available-actions-preventivo-v1.sql`,
`db/pgtap/vendite/test-preventivo-scadenza-v1.sql` e
`db/pgtap/vendite/test-fn-list-preventivi-da-pushare-v1.sql`, che falliscono se il preventivo
che costruisce non arriva allo stato chiesto; `db/pgtap/dbops/test-fn-pgtap-crea-preventivo-v1.sql`
la usa per il preventivo emesso.

---

### Note di migrazione

* 2026-10-25 — nasce quando il preventivo passa sotto la porta del verbo
  (`brief-modello-documento-vendita` §8).
* 2026-10-27 — lo stato iniziale si legge dalla testata e non dal vocabolario
  (`brief-modello-documento-vendita` §15.13).
* 2026-11-04 — la natura di merce si sceglie con `script.fn_natura_e_merce`; prima la fixture
  ne ricopiava la regola con la destinazione `ORDINE_VENDITA` scritta in linea
  (`brief-db-revisione-dbops`).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
