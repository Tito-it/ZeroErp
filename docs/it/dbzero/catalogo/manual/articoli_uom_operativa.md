## 📘 Documentazione Concettuale – Tabella `catalogo.articoli_uom_operativa`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — l'articolo e la sua unità base, in `uom_id`
> * [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura) — le unità che la mappatura collega
> * [catalogo.unita_misura_conversioni](/dbzero/catalogo/tabelle/unita_misura_conversioni) — le conversioni globali, che il calcolo delle righe non legge
> * [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe) — una delle righe di vendita che usano la mappatura
>
> Approfondimento viste:
>
> * [catalogo.vw_articoli_uom_operativa_dettaglio](/dbzero/catalogo/views/vw_articoli_uom_operativa_dettaglio) — la lista delle unità di un articolo, con i codici e la capability di eliminazione
>
> Approfondimento funzioni:
>
> * [script.trgfn_qta_from_operativa](/dbzero/script/funzioni/trgfn_qta_from_operativa) — il calcolo della quantità base sulle righe di vendita, il lettore che conta
> * [catalogo.fn_get_uom_factor](/dbzero/catalogo/funzioni/fn_get_uom_factor) — la regola completa del fattore, oggi senza chiamanti nel database
> * [catalogo.trgfn_articoli_seed_uom_base](/dbzero/catalogo/funzioni/trgfn_articoli_seed_uom_base) — crea la riga base alla nascita dell'articolo

---

### 🎯 Scopo Principale

Per ogni articolo elenca le unità di misura in cui lo si può vendere, comprare o
movimentare, e per ognuna il fattore verso l'unità base dell'articolo. Così si lavora con le
confezioni (la scatola da 50 pezzi, il cartone da 6 bottiglie) e le quantità restano
confrontabili nell'unità base.

La quantità base di una riga è la quantità operativa per il fattore: 3 scatole da 50 pezzi
sono 150 pezzi. Qui stanno i rapporti che dipendono dal prodotto; quelli che valgono per ogni
articolo (chilogrammi in grammi) stanno in `unita_misura_conversioni`.

---

### La riga base

Ogni articolo nasce con una riga base: la crea il trigger di seed alla creazione, sull'unità
di `articoli.uom_id`, con fattore 1. Un articolo ha al più una riga base (indice unico
parziale su `is_base`). La riga base si riconosce dal flag, non dall'unità: nessun vincolo
la lega a `articoli.uom_id` né le impone il fattore 1 (vedi sotto).

---

### Una riga per articolo e unità

La coppia (articolo, unità) è unica, senza contare il tempo: per lo stesso articolo e la
stessa unità c'è una riga sola. `valido_dal` e `valido_al` sono facoltativi; la fine non può
venire prima dell'inizio, e un periodo di un giorno è ammesso. Fuori dal periodo, o con la
riga spenta, per quell'articolo e quell'unità la mappatura semplicemente non c'è.

Una riga attiva vuole l'articolo e l'unità attivi, e un'unità che compare in una mappatura
attiva non si spegne. La riattivazione di un articolo non riaccende le sue mappature: si
riaccendono a parte. Cancellare l'articolo cancella le sue mappature. Le modifiche e le
cancellazioni finiscono nello storico.

---

### Come la usano le righe di vendita

Su preventivi, ordini, DDT, resi, righe di contratto ed eccezioni di offerta l'operatore
scrive l'unità operativa e la quantità operativa; `script.trgfn_qta_from_operativa` ricava la
quantità base.

* **L'unità vuota** diventa l'unità base dell'articolo.
* **Il fattore** viene dalla mappatura attiva per quell'articolo e quell'unità, in vigore
  alla data operativa di oggi (non alla data del documento).
* **Il fattore si fotografa sulla riga**: alla prima scrittura, se la riga non ha un
  fattore, il trigger salva quello usato. Da lì in poi la riga tiene il suo, e cambiare la
  mappatura non tocca le righe già scritte.
* **Le regole di input applicate** sono due: con `forbid_fraction` la quantità operativa
  dev'essere intera, con `qty_step` dev'essere un multiplo del passo.
* **Il risultato** si arrotonda sempre a 6 decimali.

`fn_articolo_usato` non conta le mappature: avere unità operative non rende «usato» un
articolo.

---

### I flag d'uso e le altre colonne

`is_sell_uom`, `is_purchase_uom` e `is_logistic_uom` dicono a che cosa serve l'unità
(vendita, acquisto, logistica); `gtin` è il codice a barre della confezione. Nel database
nessuna funzione li legge: sono informazioni per il backend e per l'interfaccia.

Un CHECK lega le regole di input fra loro: con `forbid_fraction` acceso, `max_decimals` dev'essere
0 e `qty_step` 1. `max_decimals` sta fra 0 e 6, `rounding_mode` fra `UP`, `DOWN`, `HALF_UP`,
`HALF_DOWN`, `HALF_EVEN`, il fattore e il passo sono positivi.

---

### ⚠️ Che cosa oggi non copre

* **Senza mappatura il fattore è 1.** Se la riga di vendita usa un'unità diversa dalla base
  e la mappatura manca, è spenta o è fuori periodo, la quantità base diventa la quantità
  operativa per 1, senza errore. Il calcolo non guarda le conversioni globali, che pure
  esistono per questo caso: la regola completa (mappatura, poi conversione diretta, poi
  inversa) sta in `fn_get_uom_factor`, che nessuna funzione del database chiama.
* **Tre regole di input non le applica nessuno.** `max_decimals` il trigger lo legge e non lo
  usa; `rounding_mode` non lo legge nessuno; `require_lot` non ha lettori, e la regola vera
  del lotto è `articoli.requires_lotto`. I loro COMMENT promettono un comportamento che non
  c'è.
* **La riga base non è protetta.** Nessun vincolo impone il fattore 1 sulla base, e la base
  si può modificare (unità, flag, fattore) o cancellare: il divieto di cancellarla lo
  rispetta solo l'interfaccia, attraverso la capability della vista. Si può così avere un
  articolo senza base, con la base su un'unità diversa da `articoli.uom_id`, o con un
  fattore diverso da 1, che il calcolo poi usa.
* **Le date non permettono versioni.** Con la coppia unica senza tempo, non si può chiudere
  una mappatura e aprirne una nuova con un altro fattore: le date dicono solo «fuori da qui
  la mappatura non c'è», e lì vale il fattore 1.
* **Cambiare unità su una riga di vendita tiene il fattore vecchio.** Se un aggiornamento
  cambia l'unità operativa ma non il fattore, la riga conserva il fattore dell'unità di prima.
* **Un articolo creato spento non si salva.** La riga base nasce sempre attiva, e una riga
  attiva vuole l'articolo attivo: alla fine della transazione l'inserimento di un articolo
  spento viene rifiutato.

---

### Codici errore

La tabella non solleva codici suoi. Intorno a lei:

* `E_ATTIVO_PADRE_NON_ATTIVO` — una mappatura attiva su un articolo o un'unità spenti, alla
  fine della transazione.
* `E_DATA_AL_MINORE_DAL` — `valido_al` prima di `valido_dal`.
* `E_QTA_OPERATIVA_NON_INTERA`, `E_QTA_OPER_STEP_INVALIDO` — dal calcolo sulle righe di
  vendita, quando la quantità operativa viola `forbid_fraction` o `qty_step`.

---

### Test

* `db/pgtap/catalogo/test-articoli-vincoli-note-uom-overlap.sql` — una seconda riga per la
  stessa coppia (articolo, unità) e una seconda riga base sono rifiutate.
* `db/pgtap/catalogo/test-articoli-seed-uom-base-lock.sql` — l'articolo nasce con la sua riga
  base, una sola.
* `db/pgtap/script/test-trgfn-guard-date-validita-v1.sql` — date invertite rifiutate, periodo
  di un giorno ammesso.
* `db/pgtap/catalogo/test-fn-riattiva-articolo-v1.sql` — la riattivazione dell'articolo
  lascia spente le mappature.
* `db/pgtap/vendite/test-refactor-qta-operativa-preventivi-v1.sql` — sui preventivi la quantità
  base è la quantità operativa per il fattore della mappatura, e il fattore si fotografa.
* `db/pgtap/vendite/offerte_commerciali/test_offerte_eccezioni_qta_from_operativa.sql` — lo
  stesso calcolo sulle eccezioni di offerta.

---

### Note di migrazione

* 2026-04-07 — la riga base nasce da sola alla creazione dell'articolo.
* 2026-05-14 — il periodo `validita` diventa una colonna calcolata da `valido_dal` e
  `valido_al`.

---

{% include-markdown "signature-core.md" %}
