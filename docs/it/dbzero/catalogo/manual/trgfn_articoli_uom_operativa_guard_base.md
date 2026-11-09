## 📘 Documentazione Concettuale – Trigger function `catalogo.trgfn_articoli_uom_operativa_guard_base`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli_uom_operativa](/dbzero/catalogo/tabelle/articoli_uom_operativa) — la tabella su cui è montata, e la riga base
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — l'unità base dell'articolo, in `uom_id`
>
> Approfondimento funzioni:
>
> * [catalogo.trgfn_articoli_seed_uom_base](/dbzero/catalogo/funzioni/trgfn_articoli_seed_uom_base) — crea la riga base alla nascita dell'articolo
> * [catalogo.fn_get_uom_factor](/dbzero/catalogo/funzioni/fn_get_uom_factor) — il fattore, che sulla base vale 1
>
> Approfondimento viste:
>
> * [catalogo.vw_articoli_uom_operativa_dettaglio](/dbzero/catalogo/views/vw_articoli_uom_operativa_dettaglio) — la capability che dice in anticipo che la riga base non si cancella

---

### 🎯 Scopo Principale

Tiene giusta la riga dell'unità base di un articolo in `catalogo.articoli_uom_operativa`: sta
sull'unità dell'articolo, non si sposta, non smette di essere la base e non si toglie finché
c'è l'articolo.

---

### Che cosa rifiuta

Con `E_UOM_RIGA_BASE_IMMUTABILE`:

* **una riga base nuova su un'unità diversa** da `articoli.uom_id`;
* **lo spostamento della riga base** su un'altra unità o su un altro articolo;
* **il cambio di `is_base`**, in un verso o nell'altro: la base non smette di esserlo, e una
  riga normale non lo diventa;
* **la cancellazione della riga base.**

La frase dice l'unità base e l'articolo; il bersaglio porta all'articolo.

Fattore 1 e nessuna data non li controlla questa funzione: li impone un CHECK della tabella,
per ogni riga base. Insieme, la riga base vale sempre, a ogni data, con fattore 1.

---

### Quando passa

* Su una riga che non è la base e non lo diventa, la funzione non fa niente: le mappature
  normali si modificano e si cancellano liberamente.
* Quando si cancella l'articolo, la riga base va con lui: la funzione vede che l'articolo non
  c'è più e lascia passare la cancellazione a cascata.
* Una riga base su un articolo che non esiste la rifiuta la chiave esterna.

L'unità dell'articolo a sua volta non si cambia (lock di colonna su `articoli.uom_id`):
articolo e riga base restano allineati.

---

### Quando scatta

Prima di ogni inserimento, degli aggiornamenti che scrivono `articolo_id`, `uom_id` o
`is_base`, e di ogni cancellazione, riga per riga, nella fase dei guard.

---

### Codici errore

* `E_UOM_RIGA_BASE_IMMUTABILE` — la riga base spostata, tolta, o creata su un'unità diversa da
  quella dell'articolo. Campo `uom_id`.

---

### Test

* `db/pgtap/catalogo/test-uom-fattore-e-regole-v1.sql` — la riga base spostata, cancellata e
  creata su un'altra unità sono rifiutate; il fattore diverso da 1 lo rifiuta il CHECK; una riga
  normale si cancella; cancellare l'articolo porta via la riga base.

---

### Note di migrazione

* 2026-11-09 — nasce: prima la riga base la proteggeva solo l'interfaccia, attraverso la
  capability della vista (brief-db-revisione-catalogo, giro 2).

---

{% include-markdown "signature-core.md" %}
