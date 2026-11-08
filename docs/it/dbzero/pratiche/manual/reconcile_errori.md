## 📘 Documentazione Concettuale – Tabella `pratiche.reconcile_errori`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [pratiche.fn_reconcile_sorgente](/dbzero/pratiche/funzioni/fn_reconcile_sorgente) — il motore che vi scrive gli avanzamenti saltati
> * [pratiche.trgfn_documento_reconcile_proiezione](/dbzero/pratiche/funzioni/trgfn_documento_reconcile_proiezione) — il trigger che vi scrive i fallimenti inghiottiti
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza, e perché questo log ne resta fuori

---

### 🎯 Scopo Principale

Il log, solo in aggiunta, dei fallimenti e degli avanzamenti saltati della riconciliazione
sull'esito proiettato: la superficie che rende diagnosticabile un milestone che non è avanzato.

Il trigger `pratiche.trgfn_documento_reconcile_proiezione` lavora al meglio delle possibilità: il
documento è **sovrano**, e un errore lato pratiche viene inghiottito senza annullare il cambio di
stato del documento. Senza questa tabella un avanzamento mancato resterebbe muto, anche quando la
causa è un difetto; qui resta scritto.

---

### Chi la scrive

* **Il trigger**, nel proprio blocco di eccezione, quando la riconciliazione fallisce: la riga porta
  il codice SQL e il messaggio dell'errore. La scrittura avviene nella transazione del cambio di
  stato, fuori dal punto di ripristino che ha annullato il tentativo. Lo stesso trigger vi scrive
  `E_SORG_CONF` quando è montato con un codice che non è un tipo di `config.sorgenti`, senza tipo e
  senza chiave.
* **`pratiche.fn_reconcile_sorgente`**, per gli avanzamenti saltati di proposito: più milestone
  candidati senza un tie-break usabile, codice `E_RECONCILE_AMBIGUO`.

Se anche scrivere il log fallisce, l'errore diventa un avviso nel log del server: il log non deve
mai far fallire il cambio di stato.

---

### Il documento, nelle colonne del modello

Il documento che ha innescato la riconciliazione sta nelle colonne del modello della provenienza:
`sorgente_tipo_id` e una fra `sorgente_id` e `sorgente_uid`, quella della chiave del tipo. Qui però
**tutte possono restare vuote** (il `CHECK` di forma vuole al più una chiave): il trigger può non
aver risolto il tipo.

⭐ **Un log resta fuori dal guard.** Nessun guard verifica che il documento esista, e nessuna FK
lega la riga a pratiche, milestone o documenti: la riga si scrive proprio quando qualcosa è andato
storto, anche su un dato incoerente, e deve restare leggibile quando il documento non c'è più. Per
la stessa ragione la tabella è un'esenzione dichiarata nel perimetro del presidio degli orfani.

`pratica_id` e `flusso_id`, quando ci sono, dicono la pratica e il milestone coinvolti; `tx_id` lega
la riga al giornale e al registro degli errori della stessa transazione.

---

### Test

* `db/pgtap/pratiche/test-sorgente-pratiche-sorgenti-v1.sql` — al più una chiave, nessun guard,
  l'esenzione dichiarata, la riga `E_SORG_CONF` senza tipo e senza chiave, due chiavi rifiutate.
* `db/pgtap/pratiche/test-guida-avanza-esito-proiettato.sql` — il caso ambiguo lascia una riga.

---

### Note di migrazione

* 2026-07-06 — nasce con il meccanismo dell'avanzamento su esito proiettato
  (`brief-db-guida-avanza-esito-proiettato`).
* 2026-11-08 — la chiave in testo è ritirata: il documento sta in `sorgente_id` o `sorgente_uid`
  uuid, con il `CHECK` «al più una chiave» (`brief-db-sorgente-documento-e-riga`).

---
{% include-markdown "signature-core.md" %}
