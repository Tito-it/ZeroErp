## 📘 Documentazione Concettuale – Funzione `vendite.fn_documento_lineage_nodi`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento viste:
>
> * [vendite.vw_documento_lineage_nodi](/dbzero/vendite/views/vw_documento_lineage_nodi) — la stessa cosa per tutti i documenti, senza seme
>
> Approfondimento funzioni:
>
> * [vendite.fn_documento_lineage_archi](/dbzero/vendite/funzioni/fn_documento_lineage_archi) — gli archi, con lo stesso seme
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — la chiave del documento e i grafi tra documenti

---

### 🎯 Scopo Principale

I documenti del grafo della lineage, una riga per documento, con codice, stato, fase e natura
fiscale, per i soli documenti che si chiedono. La vista `vendite.vw_documento_lineage_nodi` ne è la
proiezione senza seme, cioè tutti i documenti.

Serve a chi ha già trovato gli archi di una catena e vuole decorare solo i documenti visitati,
invece di leggerli tutti.

---

### Il seme è la chiave del nodo

Il seme è lo stesso di `vendite.fn_documento_lineage_archi`: due array paralleli, il tipo
(`config.sorgenti.id`) e la chiave del documento resa a testo secondo il `key_selector` del tipo
(l'uid per preventivo e offerta, l'id per gli altri).

* Entrambi `NULL`: tutti i documenti.
* Array vuoti: nessun documento.
* Un tipo ignoto o una chiave che non esiste: nessun documento per quella coppia.
* ⚠️ Una chiave **fuori forma** per il suo tipo (un testo che non è un numero per un tipo a chiave
  `id`) non è «nessun documento»: fa fallire la conversione della chiave, e la chiamata si ferma
  con un errore.

La natura fiscale c'è solo sulla fattura.

---

### ⭐ Si pianifica una volta per sessione

I due modi, con seme e senza, sono rami separati in `UNION ALL`, mai una condizione «parametro
vuoto oppure uguale»: ogni ramo cerca per indice. La funzione disattiva il JIT e chiede il piano
generico: con un seme che cambia a ogni chiamata il piano tiene i due rami, e senza queste due
impostazioni il JIT ne ricompilava le espressioni ogni volta. Chi la chiama non deve dichiarare
niente.

È `SECURITY INVOKER`: la RLS resta quella di chi legge, e un documento fuori perimetro non
compare.

---

### Note di migrazione

* 2026-10-11 — nasce col grafo seminato per chiave: la lineage non legge più tutti i documenti per
  decorarne pochi.

---

{% include-markdown "signature-core.md" %}
