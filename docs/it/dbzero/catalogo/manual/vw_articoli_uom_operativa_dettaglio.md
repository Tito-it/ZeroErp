## 📘 Documentazione Concettuale – Vista `catalogo.vw_articoli_uom_operativa_dettaglio`

> **Ultimo aggiornamento**: 11 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli_uom_operativa](/dbzero/catalogo/tabelle/articoli_uom_operativa) — la tabella che la vista espone, riga per riga
> * [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura) — da cui prende codice e descrizione dell'unità
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — da cui prende codice e descrizione dell'articolo
>
> Approfondimento funzioni:
>
> * [catalogo.fn_uom_conversione_capability](/dbzero/catalogo/funzioni/fn_uom_conversione_capability) — il giudizio della capability, lo stesso del guard
> * [catalogo.trgfn_uom_guard_storia](/dbzero/catalogo/funzioni/trgfn_uom_guard_storia) — il guard che la capability anticipa
>
> Approfondimento viste:
>
> * [catalogo.vw_unita_misura_conversioni_dettaglio](/dbzero/catalogo/views/vw_unita_misura_conversioni_dettaglio) — la gemella delle conversioni generali, con le stesse colonne di capability
> * [catalogo.vw_articoli_componenti_dettaglio](/dbzero/catalogo/views/vw_articoli_componenti_dettaglio) — la vista della distinta, con la stessa forma «capability più motivo»

---

### 🎯 Scopo Principale

Espone le unità operative di ogni articolo con il codice e la descrizione dell'unità e
dell'articolo, e dice per ogni riga che cosa l'interfaccia può offrire: eliminarla, spegnerla o
riaccenderla, chiuderla. È la sorgente della lista configurabile delle unità di un articolo
(`catalogo.articolo_uom`).

---

### Una riga per mappatura, con i nomi accanto

Ogni riga è una riga di `articoli_uom_operativa`, con tutte le sue colonne, più i codici e le
descrizioni dell'unità e dell'articolo. Le due giunzioni sono esterne: una mappatura si vede
anche se la descrizione manca. La vista non aggrega niente e non filtra niente: le righe
spente e quelle fuori periodo ci sono.

---

### La capability di riga

Una mappatura è versionata: vale per i suoi giorni, e non si riscrive. La capability dice in
anticipo che cosa il database lascia fare oggi, con lo stesso giudizio del guard della storia
(lo dà `fn_uom_conversione_capability`):

* **eliminarla** (`puo_eliminarsi`) e **spegnerla o riaccenderla** (`puo_cambiare_attivo`): solo
  se non ha giorni passati, cioè comincia oggi o dopo. Una mappatura in vigore si chiude; il
  motivo è `UOM_STORIA_IN_VIGORE`;
* **chiuderla** (`puo_chiudersi`): se la fine è vuota o non è ancora passata. La prima fine
  ammessa (`data_min_chiusura`) è la più tarda fra l'inizio e ieri, quella proposta
  (`data_default_chiusura`) la più tarda fra l'inizio e oggi. Una fine già passata non si tocca
  più: il motivo è `UOM_STORIA_CHIUSA`.

Il motivo c'è solo quando il blocco c'è, come nella vista della distinta.

**La riga base** non si cancella (`UOM_BASE_NON_ELIMINABILE`, dal guard della riga base), e attivo
e fine non si offrono (motivo `UOM_BASE`): la base vale 1 a ogni data, e chiuderla o spegnerla non
cambierebbe niente.

Le colonne che non si cambiano mai (unità, articolo, fattore, inizio) non sono qui: il form le
legge fra i campi non modificabili, perché le blocca il lock di colonna.

---

### ⚠️ Che cosa oggi non copre

* **Togliere una mappatura futura cambia le righe future.** Le righe già scritte tengono il loro
  fattore; una riga nuova nella stessa unità, senza più la mappatura, prende il fattore della
  conversione generale o è rifiutata. La capability non lo dice.
* **Un listino attivo può impedire la chiusura**: la chiusura che lascia senza conversione l'unità
  di un listino attivo la rifiuta, a fine transazione, il guard dei listini. La capability non la
  anticipa.

---

### Test

* `db/pgtap/catalogo/test-vw-articoli-uom-operativa-dettaglio-capability-v1.sql` — la riga base,
  una mappatura che comincia oggi (si elimina) e una in vigore (no, `UOM_STORIA_IN_VIGORE`).
* `db/pgtap/catalogo/test-uom-conversione-capability-v1.sql` — la vista dice quello che dice la
  funzione, e la funzione quello che fa il guard, riga per riga.

---

### Note di migrazione

* 2026-04-28 — nasce per il pannello delle unità operative di un articolo, sullo schema della
  vista della distinta.
* 2026-11-09 — ricreata senza `rounding_mode` e `require_lot`, ritirate dalla tabella, e con il
  suo COMMENT (brief-db-revisione-catalogo, giro 2).
* 2026-11-11 — la capability segue il guard della storia, con le colonne della chiusura
  (brief-db-revisione-catalogo, §15.11).

---

{% include-markdown "signature-core.md" %}
