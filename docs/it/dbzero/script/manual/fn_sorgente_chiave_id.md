## 📘 Documentazione Concettuale – Funzione `script.fn_sorgente_chiave_id`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — `key_selector`, che dice con quale chiave si riconosce un tipo di documento
>
> Approfondimento viste:
>
> * [script.vw_stato_sorgente](/dbzero/script/views/vw_stato_sorgente) — la colonna `sorgente_chiave_id`, su cui si cerca con la chiave convertita
>
> Approfondimento funzioni:
>
> * [script.fn_sorgente_chiave_uuid](/dbzero/script/funzioni/fn_sorgente_chiave_uuid) — la gemella, per le chiavi uuid: il perché sta lì
> * [script.fn_sorgente_documento_da_chiave](/dbzero/script/funzioni/fn_sorgente_documento_da_chiave) — il ponte per le chiavi in testo, che la usa per riconoscerle
> * [script.fn_sorgente_chiave](/dbzero/script/funzioni/fn_sorgente_chiave) — il BB che scrive, che la usa sulla chiave che riceve
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza, e le chiavi in testo

---

### 🎯 Scopo Principale

Il lettore della **forma canonica** di una chiave di documento scritta come testo, per i tipi
riconosciuti dall'**id**: riporta il testo al suo tipo intero, se è scritto esattamente come lo
scrive il database, e altrimenti risponde vuoto.

---

### La forma canonica, e nient'altro

| Testo in ingresso | Risultato |
| --- | --- |
| un intero scritto come lo scrive il database (`42`) | 42 |
| un intero in un'altra forma (`042`, ` 42`, `+42`) | vuoto |
| un uuid, o qualunque altra cosa | vuoto |
| vuoto | vuoto |

Non solleva mai errori. Dove esistono le chiavi in testo, chi le legge, perché le forme non
canoniche danno vuoto e perché si converte il parametro e non la colonna: le ragioni sono le stesse
della gemella `script.fn_sorgente_chiave_uuid`.

---

### Test

* `db/pgtap/script/test-sorgente-documento-e-chiave-v1.sql` — il ponte per chiave testuale: l'id in
  testo si risolve, con gli zeri davanti no.

---

### Note di migrazione

* 2026-10-05 — nasce con la gemella `script.fn_sorgente_chiave_uuid`.
* 2026-11-08 — con il cantiere della provenienza documento e riga (`brief-db-sorgente-documento-e-riga`)
  resta come lettore della forma canonica delle chiavi che sono testo per costruzione; il guard
  «modello B», che la usava sulle chiavi in testo delle tabelle, è ritirato.

---

{% include-markdown "signature-core.md" %}
