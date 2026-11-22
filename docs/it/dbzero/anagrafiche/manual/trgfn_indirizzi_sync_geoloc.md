## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_indirizzi_sync_geoloc`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — gli indirizzi dei ruoli, su cui è montata
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — gli indirizzi dei soggetti, su cui è montata
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — il civico, da cui copia la posizione
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_indirizzi_base_normalize](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_base_normalize) — gira prima, e svuota la posizione degli indirizzi col dettaglio

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_indirizzi_sync_geoloc` copia nell'indirizzo di un ruolo o di un soggetto la posizione del
civico che punta, a ogni nascita e a ogni modifica della riga.

---

### La posizione di un indirizzo col dettaglio è quella del civico

Con il dettaglio, la posizione (`geoloc`) è sempre il punto del civico (`civic_geoloc`): un valore passato da chi
scrive è sostituito, e un civico senza punto lascia la riga senza posizione. Il trigger che mette in ordine la
riga, prima di questo, la svuota; questo la riempie.

Nella forma libera il trigger non interviene, e la posizione resta quella scritta da chi salva.

Il trigger non solleva errori.

---

### ⚠️ Che cosa oggi non copre

* **La posizione è una copia presa quando si scrive la riga.** Se poi cambia il punto del civico, gli indirizzi
  che lo puntano lo riprendono solo alla loro prossima scrittura: nessun trigger sul civico lo propaga. Le viste
  risolte leggono il punto direttamente dal civico, e non hanno questo ritardo.

---

{% include-markdown "it/dbzero/anagrafiche/_indirizzo-libero-o-dettaglio.md" %}

---

{% include-markdown "signature-core.md" %}
