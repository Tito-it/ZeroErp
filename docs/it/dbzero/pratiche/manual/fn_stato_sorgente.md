## 📘 Documentazione Concettuale – Funzione `pratiche.fn_stato_sorgente`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche_sorgenti](/dbzero/pratiche/tabelle/pratiche_sorgenti) — i collegamenti fra pratiche e documenti, nelle stesse colonne
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — i tipi di documento e la loro chiave
> * [config.esiti_flussi_pratiche](/dbzero/config/tabelle/esiti_flussi_pratiche) — i verdetti
>
> Approfondimento viste:
>
> * [script.vw_stato_sorgente](/dbzero/script/views/vw_stato_sorgente) — la union dei resolver di dominio, l'unica superficie che legge
>
> Approfondimento funzioni:
>
> * [pratiche.fn_reconcile_sorgente](/dbzero/pratiche/funzioni/fn_reconcile_sorgente) — il motore che ne usa l'esito
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza: tipo, documento, riga

---

### 🎯 Scopo Principale

Il descrittore normalizzato dello stato di un documento, per il motore delle pratiche: dato il
documento, risponde **sempre con una riga**, con la fase, l'esito e il flag terminale nel
vocabolario comune. Il motore ragiona solo su questi tre valori e non nomina mai uno stato di
dominio.

---

### Due risposte possibili, mai un errore sul documento

* **La proiezione del dominio** (`risolto` vero), se il tipo ha un resolver in
  `script.vw_stato_sorgente` e il documento esiste ed è visibile a chi legge.
* **La sentinella `UNKNOWN`** (`risolto` falso, fase `APERTO`, esito vuoto, non terminale, con la
  chiave ricevuta), in tutti gli altri casi: un tipo senza resolver, un documento che non c'è più o
  non c'è ancora. Il milestone resta manuale, come prima che il dominio avesse un resolver.

Il flag `risolto` distingue l'`APERTO` vero dal ripiego: la fase `APERTO` della sentinella serve solo
all'instradamento del motore, e chi disegna l'interfaccia guarda `risolto`.

---

### Il documento si passa con le colonne del modello

Il documento si indica con il tipo (`config.sorgenti`), `sorgente_id` e `sorgente_uid`, come lo
scrive il modello della provenienza, e il risultato riporta la chiave nelle stesse due colonne. Chi
ha il documento passa il suo id e il suo uid; chi ha la chiave del modello passa quella, e vuoto
nell'altra.

⭐ **Due letture, non una con l'OR.** La funzione cerca prima per uid, sulla colonna
`sorgente_chiave_uuid` della vista, e solo se non trova niente per id, su `sorgente_chiave_id`. Un
OR sulle due chiavi non scenderebbe nei rami della union e la leggerebbe per intero; due letture per
chiave nativa, sotto RLS, arrivano all'indice di ogni ramo (i confronti fra uuid e fra interi sono
`leakproof`).

⚠️ **Per le liste non si chiama riga per riga.** Una lista di pratiche che volesse lo stato di ogni
documento con questa funzione farebbe una lettura per riga: si legge direttamente
`script.vw_stato_sorgente`, o la vista che ne sceglie il documento per pratica
(`script.vw_pratica_doc_sorgente`).

La funzione è `STABLE` e non scrive: nessuna copia dello stato, il documento resta l'unica verità.

---

### Codici errore

* `E_STATO_SORGENTE_PARAM_INVALIDO` — il tipo è vuoto o non positivo, oppure manca la chiave del
  documento (né `sorgente_id` né `sorgente_uid`). Un documento che non si trova non è un errore: dà
  la sentinella.

---

### Test

* `db/pgtap/pratiche/test-proiezione-stato-sorgente.sql` — le mappe di stato dei domini, la
  proiezione, la sentinella, il guard sui parametri.
* `db/pgtap/pratiche/test-sorgente-pratiche-sorgenti-v1.sql` — il preventivo per uid e l'ordine per
  id, la chiave nelle colonne del modello, la sentinella con la chiave ricevuta, il rifiuto senza
  chiave.
* `db/pgtap/vendite/test-vw-stato-sorgente-ddt-reso-v1.sql` — i rami di bolla e reso, a chiave id.

---

### Note di migrazione

* 2026-07-01 — nasce con la proiezione dello stato di dominio (`brief-db-proiezione-stato-dominio`).
* 2026-10-05 — la ricerca passa sulle chiavi native della vista, invece che sulla chiave in testo.
* 2026-11-08 — il documento si passa con tipo, `sorgente_id` e `sorgente_uid` al posto della chiave
  in testo, e il risultato porta la chiave nelle stesse colonne (`brief-db-sorgente-documento-e-riga`).

---
{% include-markdown "signature-core.md" %}
