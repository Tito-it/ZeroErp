## 📘 Documentazione Concettuale – Vista `vendite.vw_documento_lineage_nodi`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — i tipi dei nodi e la loro chiave (`key_selector`)
>
> Approfondimento viste:
>
> * [vendite.vw_documento_lineage_archi](/dbzero/vendite/views/vw_documento_lineage_archi) — gli archi fra i nodi
>
> Approfondimento funzioni:
>
> * [vendite.fn_documento_lineage_nodi](/dbzero/vendite/funzioni/fn_documento_lineage_nodi) — il corpo, chiamabile per i soli documenti che servono
> * [vendite.fn_documento_lineage_sintesi](/dbzero/vendite/funzioni/fn_documento_lineage_sintesi) — la sintesi per documento (frontiera, transito, pratica)
> * [script.fn_sorgente_documento_da_chiave](/dbzero/script/funzioni/fn_sorgente_documento_da_chiave) — chi risolve un documento dalla chiave in testo del nodo
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — §5 le chiavi in testo, §8 i grafi tra documenti

---

### 🎯 Scopo Principale

La **dimensione nodo** del grafo di genealogia dei documenti di vendita: **una riga per documento** delle otto testate-nodo (preventivo, offerta, ordine, contratto, bolla, fattura, commessa, reso), con la chiave del nodo e lo stato e la fase normalizzati.

È la proiezione «senza seme» di
[`vendite.fn_documento_lineage_nodi`](/dbzero/vendite/funzioni/fn_documento_lineage_nodi): stesse
colonne, stessi tipi. Chi vuole solo una parte del grafo chiama la funzione con l'elenco dei nodi
che gli servono; la vista li dà tutti.

---

### ⭐ Un posto solo per l'unione delle otto testate

È il **mattone condiviso** dei lettori del grafo: la vista degli archi la usa per decorare i nodi
d'arrivo, la sintesi e la genealogia di un documento per gli attributi dei nodi. Così l'unione delle
otto testate è scritta **una volta sola**.

---

### 🔑 La chiave del nodo

L'identità di un nodo è **tipo + chiave del documento**, come la scrive il modello della
provenienza: `tipo_id` e `uid`, dove `uid` è la chiave del documento **in testo**, nella forma
canonica, secondo `config.sorgenti.key_selector`:

| `key_selector` | Tipi | `uid` esposto |
| --- | --- | --- |
| `uid` | PREVENTIVO, OFFERTA_COMMERCIALE | l'uid del documento, in testo |
| `id` | ORDINE_VENDITA, CONTRATTO, DDT_VENDITA, FATTURA, COMMESSA, RESO_VENDITA | l'id del documento, in testo |

⚠️ Il nome della colonna è storico: `uid` qui è **la chiave del nodo**, non l'uid del documento.
Per un ordine vale il suo id.

La chiave è testo **per costruzione** (un nodo deve poter essere di un tipo qualunque). Chi deve
tornare dal nodo al documento non la traduce da sé: passa tipo e chiave a
[`script.fn_sorgente_documento_da_chiave`](/dbzero/script/funzioni/fn_sorgente_documento_da_chiave),
che riconosce la forma canonica e risolve come il BB che risolve.

Il `tipo_id` è sempre risolto da `config.sorgenti` per `codice_interno` (chiave stabile), mai con
un id scritto nel codice; accanto c'è `tipo_codice_interno`, il codice del tipo, per chi deve fare
logica o tradurre l'etichetta senza un altro join.

---

### Che cosa dice di ogni nodo

* **Etichetta**: `codice`, il numero parlante del documento (`numero` per preventivi, ordini,
  contratti, bolle e resi; il numero composto per la fattura; `codice` per offerte e commesse).
* **Stato nativo**: `stato_codice_interno` (logica, immutabile), `stato_codice` e
  `stato_descrizione` (display) — alias **fedeli** alla sorgente.
* **Proiezione**: `fase` (`APERTO` / `IN_ATTESA` / `IN_CORSO` / `CHIUSO`) e `is_abortito`.
* **`pipeline_rank`**: la posizione del tipo nel flusso verso la fattura (crescente = più a valle):
  `1` preventivo e offerta · `2` ordine e contratto · `3` bolla · `4` commessa · `5` fattura · `0`
  reso. Serve come spareggio nella scelta della frontiera.

---

### ⭐ La natura del documento, solo sulla fattura

Il nodo espone anche `natura_doc_codice_interno` e `natura_doc_descrizione`, da
`config.nature_doc_fiscale`. Il *tipo* dice da quale tabella viene il nodo, la *natura* che cosa è
fiscalmente: senza, una fattura e la nota di credito che la rettifica sarebbero due nodi uguali
(stesso tipo, stesso stato, numero vuoto finché non sono numerati).

⚠️ È valorizzata nel solo ramo della fattura, e negli altri è vuota — ed è corretto: un preventivo o
una bolla non hanno una natura fiscale.

⚠️ `LEFT JOIN` e non `JOIN`, sulla natura e sullo stato: `natura_doc_id` e lo stato fiscale della
fattura possono essere vuoti, e con un `JOIN` quel documento **sparirebbe dal grafo**, che è molto
peggio di un attributo vuoto.

---

### Note operative

* **Una riga per documento**, anche per i nodi isolati (senza genealogia).
* **`security_invoker = on`**: la vista applica la RLS emittente del **chiamante**; il backend non
  passa l'utente. La reloption non compare nella definizione della vista e va ri-specificata a ogni
  `CREATE OR REPLACE`.
* Test: `db/pgtap/vendite/test-documento-lineage-v1.sql`.

---

### Note di migrazione

* 2026-07-14 — nasce col grafo di genealogia dei documenti di vendita (brief-db-lineage-documenti-vendite).
* 2026-08-20 — arriva la natura del documento.
* 2026-10-11 — il corpo passa a `fn_documento_lineage_nodi`, e la vista ne diventa la proiezione
  senza seme; la sintesi per documento `vw_documento_lineage` si ritira a favore di
  `fn_documento_lineage_sintesi` (brief-db-lineage-seminata-per-chiave).

---

{% include-markdown "signature-core.md" %}
