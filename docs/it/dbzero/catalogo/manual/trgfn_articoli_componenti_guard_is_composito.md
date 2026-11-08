## 📘 Documentazione Concettuale – Trigger function `catalogo.trgfn_articoli_componenti_guard_is_composito`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — la distinta su cui opera
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — dove sta il flag `is_composito` del padre
>
> Approfondimento funzioni:
>
> * [catalogo.trgfn_articoli_componenti_guard_solo_componente](/dbzero/catalogo/funzioni/trgfn_articoli_componenti_guard_solo_componente) — l'altro guard sul padre
> * [catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva](/dbzero/catalogo/funzioni/trgfn_articoli_guard_flags_struttura_bom_attiva) — il lato articolo: un padre di una distinta in vigore resta composito
> * [catalogo.fn_articolo_padre_di_distinta_in_vigore](/dbzero/catalogo/funzioni/fn_articolo_padre_di_distinta_in_vigore) — il predicato che quel guard usa

---

### 🎯 Scopo Principale

Impedisce di usare come padre di una distinta (`prodotto_id`) un articolo che non è composito: una distinta si
definisce solo per un kit.

---

### Quando giudica

Scatta prima dell'INSERT di un legame e dell'UPDATE di `prodotto_id`. Legge `is_composito` del padre: se non è
vero, il legame è rifiutato. Giudica anche un legame spento: il padre deve essere composito comunque.

Fra i trigger della tabella parla prima del guard sul componente: se il padre non è composito, l'errore è questo,
anche se il componente ha un altro difetto.

---

### ⚠️ Che cosa oggi non copre

* **La riattivazione e le date.** Il guard non scatta su `attivo`, `valido_dal` o `valido_al`. Se il padre smette di
  essere composito mentre ha solo legami spenti, chiusi o futuri, riattivare o riaprire quei legami passa, e la
  distinta torna in vigore sotto un articolo che non è un kit.
* **Il lato articolo** protegge solo i padri di una distinta in vigore oggi: un articolo con legami solo futuri,
  finché nessun documento lo usa, può smettere di essere composito senza errore.

---

### Codici errore

* `E_ARTICOLO_NON_COMPOSITO` — il padre non è composito.

---

### Test

* `db/pgtap/catalogo/test-articoli-componenti-guard-attivo-composito.sql` — un legame con un padre non composito è
  rifiutato.
* `db/pgtap/catalogo/test-distinta-un-livello-e-onere-natura-v1.sql` — con un padre non composito e un componente
  composito, parla il padre.

---

{% include-markdown "signature-core.md" %}
