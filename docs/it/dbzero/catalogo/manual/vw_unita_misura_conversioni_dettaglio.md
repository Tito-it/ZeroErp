## 📘 Documentazione Concettuale – Vista `catalogo.vw_unita_misura_conversioni_dettaglio`

> **Ultimo aggiornamento**: 11 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.unita_misura_conversioni](/dbzero/catalogo/tabelle/unita_misura_conversioni) — la tabella che la vista espone, riga per riga
> * [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura) — da cui prende codice e descrizione delle due unità
>
> Approfondimento funzioni:
>
> * [catalogo.fn_uom_conversione_capability](/dbzero/catalogo/funzioni/fn_uom_conversione_capability) — il giudizio della capability, lo stesso del guard
>
> Approfondimento viste:
>
> * [catalogo.vw_articoli_uom_operativa_dettaglio](/dbzero/catalogo/views/vw_articoli_uom_operativa_dettaglio) — la gemella delle mappature di un articolo

---

### 🎯 Scopo Principale

Espone le conversioni generali fra unità di misura con il codice e la descrizione delle due unità,
e dice per ogni riga che cosa l'interfaccia può offrire: eliminarla, spegnerla o riaccenderla,
chiuderla. È la sorgente della lista configurabile delle conversioni (`catalogo.conversioni_uom`).

---

### Una riga per conversione

Ogni riga è una riga di `unita_misura_conversioni`, con le sue colonne, più codice e descrizione
dell'unità di partenza e di quella di arrivo. La vista non filtra niente: le conversioni spente e
quelle chiuse ci sono, e filtro e ordine li mette chi legge.

---

### La capability di riga

Le colonne e le regole sono quelle della vista delle mappature, senza la riga base:

* **eliminarla** e **spegnerla o riaccenderla**: solo se non ha giorni passati; altrimenti il motivo
  è `UOM_STORIA_IN_VIGORE`, e la conversione si chiude;
* **chiuderla**: se la fine è vuota o non è ancora passata, dalla più tarda fra l'inizio e ieri;
  altrimenti il motivo è `UOM_STORIA_CHIUSA`.

Le due unità, il fattore e l'inizio non si cambiano mai: il form li legge fra i campi non
modificabili.

---

### ⚠️ Che cosa oggi non copre

* **Un listino attivo può impedire la chiusura o lo spegnimento**: se la conversione serve all'unità
  di un listino attivo, il guard dei listini rifiuta a fine transazione. La capability non lo
  anticipa.

---

### Test

* `db/pgtap/catalogo/test-uom-conversione-capability-v1.sql` — la vista dice quello che dice la
  funzione, il guard fa quello che la vista promette, e la lista la legge con tutte le sue colonne.

---

### Note di migrazione

* 2026-11-11 — nasce come sorgente della lista delle conversioni (brief-db-revisione-catalogo,
  §15.11).

---

{% include-markdown "signature-core.md" %}
