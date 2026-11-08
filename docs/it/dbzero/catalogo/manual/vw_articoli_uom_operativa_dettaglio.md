## 📘 Documentazione Concettuale – Vista `catalogo.vw_articoli_uom_operativa_dettaglio`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli_uom_operativa](/dbzero/catalogo/tabelle/articoli_uom_operativa) — la tabella che la vista espone, riga per riga
> * [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura) — da cui prende codice e descrizione dell'unità
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — da cui prende codice e descrizione dell'articolo
>
> Approfondimento viste:
>
> * [catalogo.vw_articoli_componenti_dettaglio](/dbzero/catalogo/views/vw_articoli_componenti_dettaglio) — la vista gemella della distinta, con la stessa forma «capability più motivo»

---

### 🎯 Scopo Principale

Espone le unità operative di ogni articolo con il codice e la descrizione dell'unità e
dell'articolo, e dice per ogni riga se l'interfaccia può offrire l'eliminazione. È la
sorgente della lista configurabile delle unità di un articolo (`catalogo.articolo_uom`).

---

### Una riga per mappatura, con i nomi accanto

Ogni riga è una riga di `articoli_uom_operativa`, con tutte le sue colonne, più i codici e le
descrizioni dell'unità e dell'articolo. Le due giunzioni sono esterne: una mappatura si vede
anche se la descrizione manca. La vista non aggrega niente e non filtra niente: le righe
spente e quelle fuori periodo ci sono.

---

### La capability di eliminazione

`puo_eliminarsi` è falso sulla riga base e vero sulle altre; `motivo_non_eliminabile` vale
`UOM_BASE_NON_ELIMINABILE` sulla riga base ed è vuoto quando l'eliminazione è permessa. È la
stessa forma della vista della distinta: il motivo c'è solo quando il blocco c'è.

⭐ La regola guarda solo `is_base`, perché nessuna tabella punta a una riga di mappatura: i
documenti, i listini e i movimenti puntano all'unità di misura, non alla mappatura, e una riga
di vendita conserva il fattore che ha fotografato. Togliere una mappatura non base non rompe
quindi nessun riferimento.

---

### ⚠️ Che cosa oggi non copre

* **La capability è solo un'indicazione.** Nel database nessun vincolo vieta di cancellare o
  modificare la riga base: lo rispetta solo l'interfaccia che legge `puo_eliminarsi`.
* **Togliere una mappatura cambia le righe future.** Le righe già scritte tengono il loro
  fattore, ma una riga nuova nella stessa unità, senza più la mappatura, prende il fattore 1.
  La capability non lo dice.
* La vista e le sue colonne non hanno COMMENT.

---

### Test

* `db/pgtap/catalogo/test-vw-articoli-uom-operativa-dettaglio-capability-v1.sql` — sulla riga
  base la capability è falsa con il motivo `UOM_BASE_NON_ELIMINABILE`, sulla riga non base è
  vera con il motivo vuoto; codice dell'articolo e dell'unità sono valorizzati.

---

### Note di migrazione

* 2026-04-28 — nasce per il pannello delle unità operative di un articolo, sullo schema della
  vista della distinta.

---

{% include-markdown "signature-core.md" %}
