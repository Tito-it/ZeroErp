## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_documento_reconcile_proiezione`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il tipo del documento e la sua chiave, letti dal codice dell'argomento
> * [pratiche.reconcile_errori](/dbzero/pratiche/tabelle/reconcile_errori) — dove finiscono gli errori inghiottiti
>
> Approfondimento funzioni:
>
> * [pratiche.fn_reconcile_sorgente](/dbzero/pratiche/funzioni/fn_reconcile_sorgente) — il motore che chiama
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza e la chiave del documento

---

### 🎯 Scopo Principale

L'innesco generico dell'avanzamento sull'esito proiettato: montata dopo l'aggiornamento della
colonna di stato di una tabella-documento, a ogni cambio di stato, su qualsiasi percorso di
scrittura e anche per un documento standalone, chiama `pratiche.fn_reconcile_sorgente` sul
documento.

Un corpo solo, un montaggio per dominio. Oggi è montata su `vendite.preventivi`, sul cambio di
`stato_doc_preventivo_id`.

---

### L'argomento: il codice del tipo

Il montaggio passa **un argomento**, il codice del tipo del documento
(`config.sorgenti.codice_interno`, per esempio `PREVENTIVO`), scritto esplicitamente nel
`CREATE TRIGGER`. Il tipo non si ricava dalla tabella: il catalogo non vieta che una stessa tabella
compaia in più tipi, e la ricerca all'indietro sarebbe ambigua.

Dal codice la funzione legge nel catalogo l'id del tipo e il suo `key_selector`, e prende la chiave
del documento dalla colonna che il selettore dichiara: l'`id` della riga per i tipi a chiave id,
l'`uid` per quelli a chiave uid. La chiave passa al motore nella sua colonna del modello
(`sorgente_id` oppure `sorgente_uid`), senza SQL dinamico. Una riga senza chiave non chiama niente.

⚠️ Un montaggio con un codice che non è un tipo non ferma il documento: la funzione scrive una riga
`E_SORG_CONF` in `pratiche.reconcile_errori`, senza tipo e senza chiave, e il cambio di stato
resta.

---

### ⭐ Il documento è sovrano

La chiamata al motore sta in un blocco di eccezione: un errore lato pratiche **non si propaga mai** e
non annulla il cambio di stato del documento. L'errore originale si registra in
`pratiche.reconcile_errori`, con il tipo e la chiave del documento; se anche quella scrittura
fallisce, resta un avviso nel log del server. Il trigger è `AFTER` e il suo valore di ritorno non
conta.

Finché nessun milestone ha un binding in `pratiche.template_flussi_avanzamento_proiezione`, il
montaggio è dormiente: il motore non trova candidati e ritorna 0.

---

### Test

* `db/pgtap/pratiche/test-sorgente-pratiche-sorgenti-v1.sql` — il montaggio sul preventivo passa il
  codice del tipo; un codice che non è un tipo lascia la riga `E_SORG_CONF` e il cambio di stato
  resta.
* `db/pgtap/pratiche/test-guida-avanza-esito-proiettato.sql` — l'avanzamento di un preventivo
  standalone, attraverso il trigger.

---

### Note di migrazione

* 2026-07-06 — nasce con il meccanismo dell'avanzamento su esito proiettato
  (`brief-db-guida-avanza-esito-proiettato`): gli argomenti erano l'id del tipo e il nome della
  colonna chiave.
* 2026-11-08 — l'argomento diventa il codice del tipo; id e chiave si leggono dal catalogo, e la
  chiave passa al motore nelle colonne del modello (`brief-db-sorgente-documento-e-riga`).

---
{% include-markdown "signature-core.md" %}
