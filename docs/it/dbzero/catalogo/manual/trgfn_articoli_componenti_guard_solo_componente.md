## 📘 Documentazione Concettuale – Trigger function `catalogo.trgfn_articoli_componenti_guard_solo_componente`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — la distinta su cui opera
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — dove sta il flag `is_solo_componente` del padre
>
> Approfondimento funzioni:
>
> * [catalogo.trgfn_articoli_componenti_guard_is_composito](/dbzero/catalogo/funzioni/trgfn_articoli_componenti_guard_is_composito) — l'altro guard sul padre
> * [catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva](/dbzero/catalogo/funzioni/trgfn_articoli_guard_flags_struttura_bom_attiva) — i flag di struttura dal lato articolo
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva l'errore

---

### 🎯 Scopo Principale

Impedisce di usare come padre di una distinta (`prodotto_id`) un articolo solo componente: un articolo che esiste
solo dentro un kit non può essere a sua volta un kit.

---

### Quando giudica

Scatta prima dell'INSERT di un legame e dell'UPDATE di `prodotto_id`. Legge `is_solo_componente` del padre: se è
vero, il legame è rifiutato. Giudica anche un legame spento.

Come componente, invece, un articolo solo componente è il caso normale: il guard non guarda `componente_id`.

---

### ⚠️ Che cosa oggi non copre

* **Un articolo può essere composito e solo componente insieme.** Nessun vincolo sull'articolo lo esclude. Un
  articolo così non può fare da padre (lo ferma questo guard) e non può fare da componente (la distinta ha un
  livello): è inerte.
* **Il padre che diventa solo componente.** Il lato articolo blocca `is_solo_componente` sui componenti di una
  distinta in vigore, non sui padri: un kit con una distinta in vigore, finché nessun documento lo usa, può
  diventare solo componente, e i suoi legami restano.
* **La riattivazione e le date.** Il guard non scatta su `attivo`, `valido_dal` o `valido_al`: riattivare o
  riaprire un legame il cui padre nel frattempo è diventato solo componente passa.

---

### Codici errore

* `E_ARTICOLO_SOLO_COMPONENTE` — il padre è un articolo solo componente.

---

### Test

* `db/pgtap/catalogo/test-articoli-componenti-solo-componente.sql` — un articolo solo componente come padre è
  rifiutato; un padre normale passa; un articolo solo componente come componente passa.

---

{% include-markdown "signature-core.md" %}
