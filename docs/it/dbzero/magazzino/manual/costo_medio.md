## 📘 Documentazione Concettuale – Tabella `magazzino.costo_medio`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti)
> • [magazzino.vw_costo_medio](/dbzero/magazzino/views/vw_costo_medio)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Stato corrente del costo medio ponderato (CMP)** per la coppia articolo × magazzino: due
accumulatori, `qta` e `valore`.

⭐ Il costo medio **non è memorizzato**: si ricava dividendo `valore / qta`, e lo fa la vista
`vw_costo_medio`. Tenere i due accumulatori invece del quoziente è ciò che rende la media
aggiornabile per incrementi successivi senza perdita di precisione — sommare valore e quantità
di ogni carico e dividere solo alla lettura.

---

### ⚠️ È uno stato, non un ledger

A differenza di `magazzino.movimenti`, questa tabella **si aggiorna**: contiene il valore
corrente, non la storia. La storia dei costi va ricostruita dai movimenti.

Chi la disallinea dal ledger — un aggiornamento diretto, un ricalcolo parziale — non lascia
nessuna traccia, e il disallineamento si scopre solo riconciliando con i movimenti.
⚠️ Prima di attivare il dominio va deciso **chi** la scrive: oggi non c'è nessun trigger che
la mantenga a partire da `movimenti`.

---

### La divisione per zero è protetta a valle

`qta` può arrivare a zero (tutto scaricato) con `valore` non nullo per effetto degli
arrotondamenti. `vw_costo_medio` gestisce il caso restituendo `NULL`, non un errore.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
