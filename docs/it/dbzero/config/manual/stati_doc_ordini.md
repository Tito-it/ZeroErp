## 📘 Documentazione Concettuale – Tabella `config.stati_doc_ordini`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**    
>
• [vendite.ordini](/dbzero/vendite/tabelle/ordini)    
> • [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)    
>
### 🎯 Scopo Principale
(latest review 29-03-2026)
`config.stati_doc_ordini` definisce gli **stati documento** del ciclo ordine di
vendita. Raccoglie in un catalogo unico le fasi di avanzamento commerciale e
operativo dell'ordine, dalla bozza fino all'evasione o chiusura.

---

### Campi chiave (semantica)

* **Identita` stato**: `id`, `codice`, `codice_interno`.
* **Ordine**: `ordine` per rappresentare la progressione del flusso ordine.
* **Governance**: `attivo`, `meta`.

---

### Regole operative

* Lo stato e` usato come riferimento da `vendite.ordini.stato_doc_ordine_id`.
* Lo stesso catalogo e` richiamato anche dalle righe ordine per allineare la fase documentale del dettaglio.
* `codice` e `codice_interno` devono restare **immutabili** dal punto di vista funzionale.
* La disattivazione di stati gia` usati in ordini o righe esistenti e` bloccata da trigger DB.

---

### Uso tipico nel processo

* **Preparazione**: stati iniziali per ordine in bozza o inserimento.
* **Conferma**: stati che rendono l'ordine valido per evasione o passaggi successivi.
* **Evasione/chiusura**: stati finali o avanzati per spedizione, completamento, annullo.

---

{% include-markdown "signature-core.md" %}
