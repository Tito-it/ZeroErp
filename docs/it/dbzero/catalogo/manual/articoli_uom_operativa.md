## 📘 Documentazione Concettuale – Tabella `catalogo.articoli_uom_operativa`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — l'articolo e la sua unità base, in `uom_id`
> * [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura) — le unità che la mappatura collega
> * [catalogo.unita_misura_conversioni](/dbzero/catalogo/tabelle/unita_misura_conversioni) — le conversioni generali, il ripiego quando l'articolo non ha una mappatura
> * [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe) — una delle righe di vendita che usano la mappatura
>
> Approfondimento viste:
>
> * [catalogo.vw_articoli_uom_operativa_dettaglio](/dbzero/catalogo/views/vw_articoli_uom_operativa_dettaglio) — la lista delle unità di un articolo, con i codici e la capability di eliminazione
>
> Approfondimento funzioni:
>
> * [catalogo.fn_uom_operativa_alla_data](/dbzero/catalogo/funzioni/fn_uom_operativa_alla_data) — la mappatura di un'unità a una data, sede unica della lettura
> * [catalogo.fn_get_uom_factor](/dbzero/catalogo/funzioni/fn_get_uom_factor) — il fattore: base, mappatura, conversione generale
> * [script.trgfn_qta_from_operativa](/dbzero/script/funzioni/trgfn_qta_from_operativa) — il calcolo della quantità base sulle righe di vendita
> * [catalogo.trgfn_articoli_seed_uom_base](/dbzero/catalogo/funzioni/trgfn_articoli_seed_uom_base) — crea la riga base alla nascita dell'articolo
> * [catalogo.trgfn_articoli_uom_operativa_guard_base](/dbzero/catalogo/funzioni/trgfn_articoli_uom_operativa_guard_base) — protegge la riga base

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
di `articoli.uom_id`, con fattore 1, senza date, attiva o spenta come l'articolo. Un articolo
ha al più una riga base (indice unico parziale su `is_base`).

La riga base è fissa:

* fattore 1 e nessuna data: lo impone un CHECK, quindi vale sempre;
* resta sull'unità dell'articolo e sull'articolo, non smette di essere la base e una riga
  normale non lo diventa; non si cancella; non se ne crea una su un'unità diversa da quella
  dell'articolo. Lo garantisce `trgfn_articoli_uom_operativa_guard_base`
  (`E_UOM_RIGA_BASE_IMMUTABILE`);
* va via solo con l'articolo: cancellare l'articolo cancella anche lei.

L'unità dell'articolo a sua volta non si cambia (lock di colonna su `articoli.uom_id`): base e
articolo restano allineati.

---

### Una mappatura versionata

Per lo stesso articolo e la stessa unità ci possono essere più righe, purché i loro periodi
non si sovrappongano (vincolo unico temporale sulla validità). Così il fattore si cambia
«chiudendo e inserendo»: la riga vecchia finisce un giorno, la nuova comincia il giorno dopo.
`valido_dal` e `valido_al` sono facoltativi e compresi nel periodo; la fine non può venire
prima dell'inizio.

Una riga spenta resta nel conto della sovrapposizione: per ritirare un fattore si chiude il
periodo, non si spegne la riga.

Una riga attiva vuole l'articolo e l'unità attivi, e un'unità che compare in una mappatura
attiva non si spegne. La riattivazione di un articolo non riaccende le sue mappature: si
riaccendono a parte. Le modifiche e le cancellazioni finiscono nello storico.

---

### Come la usano le righe di vendita

Su preventivi, ordini, DDT, resi, righe di contratto ed eccezioni di offerta l'operatore
scrive l'unità operativa e la quantità operativa; `script.trgfn_qta_from_operativa` ricava la
quantità base.

* **L'unità vuota** diventa l'unità base dell'articolo.
* **Il fattore** si legge alla data del documento: prima la mappatura dell'articolo in vigore
  quel giorno, poi la conversione generale fra le due unità (`fn_get_uom_factor`). Senza
  nessuna delle due la riga è rifiutata (`E_UOM_MISSING`).
* **Il fattore si fotografa sulla riga**: alla prima scrittura, se la riga non ha un
  fattore, il trigger salva quello usato. Da lì in poi la riga tiene il suo, e cambiare la
  mappatura non tocca le righe già scritte. Se un aggiornamento cambia l'unità e non il
  fattore, il fattore si rilegge per l'unità nuova.
* **Le regole di input** sono quelle della mappatura alla data: con `forbid_fraction` la
  quantità operativa dev'essere intera, con `max_decimals` non può avere più decimali di
  quelli ammessi (gli zeri in coda non contano), con `qty_step` dev'essere un multiplo del
  passo. Un'unità convertita dalle conversioni generali non ha regole.
* **Il risultato** si arrotonda sempre a 6 decimali.

`fn_articolo_usato` non conta le mappature: avere unità operative non rende «usato» un
articolo.

---

### I flag d'uso e le altre colonne

`is_sell_uom`, `is_purchase_uom` e `is_logistic_uom` dicono a che cosa serve l'unità
(vendita, acquisto, logistica); `gtin` è il codice a barre della confezione. Nel database
nessuna funzione li legge: sono informazioni per il backend e per l'interfaccia.

Un CHECK lega le regole di input fra loro: con `forbid_fraction` acceso, `max_decimals` dev'essere
0 e `qty_step` 1. `max_decimals` sta fra 0 e 6, il fattore e il passo sono positivi.

L'arrotondamento non si sceglie per unità: la quantità base si arrotonda sempre a 6 decimali.
Il lotto è una proprietà dell'articolo (`articoli.requires_lotto`), non dell'unità.

---

### Codici errore

* `E_UOM_RIGA_BASE_IMMUTABILE` — la riga base spostata, tolta, o creata su un'unità diversa da
  quella dell'articolo.
* `E_ATTIVO_PADRE_NON_ATTIVO` — una mappatura attiva su un articolo o un'unità spenti, alla
  fine della transazione.
* `E_DATA_AL_MINORE_DAL` — `valido_al` prima di `valido_dal`.
* Dal calcolo sulle righe di vendita: `E_UOM_MISSING` (nessun fattore alla data del
  documento), `E_QTA_OPERATIVA_NON_INTERA`, `E_QTA_OPERATIVA_DECIMALI`,
  `E_QTA_OPER_STEP_INVALIDO`.

---

### Test

* `db/pgtap/catalogo/test-uom-fattore-e-regole-v1.sql` — la mappatura versionata letta a due
  date, la sovrapposizione rifiutata, la riga base fissa e protetta, l'articolo creato spento
  con la riga base spenta, `max_decimals` applicato.
* `db/pgtap/catalogo/test-articoli-vincoli-note-uom-overlap.sql` — una seconda riga base è
  rifiutata.
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
* 2026-11-09 — la mappatura diventa versionata, la riga base fissa e protetta;
  `rounding_mode` e `require_lot` si ritirano, `max_decimals` si applica
  (brief-db-revisione-catalogo, giro 2).

---

{% include-markdown "signature-core.md" %}
