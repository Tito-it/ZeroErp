## 📘 Documentazione Concettuale – Tabella `catalogo.articoli_uom_operativa`

> **Ultimo aggiornamento**: 11 novembre 2026
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
> * [catalogo.vw_articoli_uom_operativa_dettaglio](/dbzero/catalogo/views/vw_articoli_uom_operativa_dettaglio) — la lista delle unità di un articolo, con i codici e la capability di riga (eliminare, spegnere, chiudere)
>
> Approfondimento funzioni:
>
> * [catalogo.fn_uom_operativa_alla_data](/dbzero/catalogo/funzioni/fn_uom_operativa_alla_data) — la mappatura di un'unità a una data, sede unica della lettura
> * [catalogo.fn_get_uom_factor](/dbzero/catalogo/funzioni/fn_get_uom_factor) — il fattore: base, mappatura, conversione generale
> * [catalogo.fn_uom_fonti_conversione](/dbzero/catalogo/funzioni/fn_uom_fonti_conversione) — le fonti del fattore con i loro periodi, che le due letture qui sopra condividono
> * [catalogo.trgfn_uom_guard_storia](/dbzero/catalogo/funzioni/trgfn_uom_guard_storia) — la mappatura è storia: cosa si cambia e cosa no
> * [catalogo.trgfn_uom_guard_listini_attivi](/dbzero/catalogo/funzioni/trgfn_uom_guard_listini_attivi) — una mappatura non si chiude sotto un listino attivo che la usa
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

---

### La mappatura è storia

Un documento di ieri ha letto il fattore di ieri: cambiarlo sul posto riscriverebbe il passato
di ogni riga che lo rilegge. Per questo una mappatura scritta si chiude, non si corregge
(`trgfn_uom_guard_storia`, sulle righe che non sono la base):

* **fattore, unità, articolo e inizio** non si cambiano mai, neppure su una mappatura che
  comincia domani (`E_UOM_STORIA_IMMUTABILE`). Un fattore nuovo è una riga nuova: si chiude la
  vecchia e si inserisce la nuova dal giorno dopo. Queste quattro colonne le blocca il lock di
  colonna (`script.trgfn_lock_columns`, dal registro dei lock), così il form le mostra non
  modificabili;
* **la fine** si sposta, ma non prima di ieri (`E_UOM_STORIA_CHIUSURA_RETROATTIVA`): chiudere a
  ieri vuol dire «da oggi non vale più». Una mappatura già finita non si riapre né si
  accorcia (`E_UOM_STORIA_CHIUSA`);
* **spegnere, riaccendere o cancellare** si può solo finché la mappatura non ha giorni
  passati, cioè se comincia oggi o dopo: è quella inserita per errore. Una mappatura già in
  vigore si chiude (`E_UOM_STORIA_IN_VIGORE`);
* le colonne che non fanno la conversione (i flag d'uso, `gtin`, le regole di input) si
  cambiano liberamente;
* cancellare l'articolo porta via le sue mappature, anche quelle in vigore.

Che cosa si può fare oggi su una riga lo dice in anticipo la vista di dettaglio, con lo stesso
giudizio del guard (`catalogo.fn_uom_conversione_capability`).

Chiudere o spegnere una mappatura che un listino attivo usa ancora, oltre la nuova fine, è
rifiutato a fine transazione (`E_UOM_CHIUSURA_CON_LISTINI_ATTIVI`): il prezzo del listino
resterebbe in un'unità che per l'articolo non si converte più. Chiudere e inserire nella
stessa transazione passa.

Proprio perché è storia, la mappatura **non è legata all'attivo** dell'articolo e
dell'unità (le due FK sono fra le eccezioni dell'automazione ATTIVO): l'articolo e l'unità si
spengono anche se hanno mappature, e si riaccendono trovandole come le avevano lasciate.
Una riga di documento su un articolo spento la fermano già i controlli del documento. Le
modifiche e le cancellazioni finiscono nello storico.

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

Le attività delle commesse e le attività fatturabili seguono la stessa regola per il fattore,
alla data dell'attività (`vendite.trgfn_attivita_fattore_alla_data`): senza fattore lo
leggono dalla mappatura, e senza mappatura la riga è rifiutata.

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
* `E_UOM_STORIA_IMMUTABILE` — fattore, unità, articolo o inizio cambiati su una mappatura scritta.
* `E_UOM_STORIA_IN_VIGORE` — una mappatura con giorni passati spenta, riaccesa o cancellata.
* `E_UOM_STORIA_CHIUSURA_RETROATTIVA` — una mappatura chiusa prima di ieri.
* `E_UOM_STORIA_CHIUSA` — la fine di una mappatura già finita cambiata.
* `E_UOM_CHIUSURA_CON_LISTINI_ATTIVI` — una mappatura chiusa o spenta mentre un listino attivo
  ne usa l'unità oltre la nuova fine, alla fine della transazione.
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
* `db/pgtap/catalogo/test-uom-storia-v1.sql` — cosa della mappatura e della conversione
  generale si cambia e cosa no, chiudi e inserisci, l'articolo e l'unità che si spengono con
  le loro mappature.
* `db/pgtap/vendite/test-listino-uom-periodo-v1.sql` — una mappatura non si chiude sotto un
  listino attivo che la usa.
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
* 2026-11-10 — la mappatura è storia: fattore, unità e inizio fermi, la fine non
  retroattiva, spegnimento e cancellazione solo prima del primo giorno; non si chiude
  sotto un listino attivo; esce dal legame ATTIVO con articolo e unità
  (brief-db-revisione-catalogo, giro 2-bis).
* 2026-11-11 — fattore, unità, articolo e inizio passano al lock di colonna; la vista di
  dettaglio pubblica la capability del guard (brief-db-revisione-catalogo, §15.11).

---

{% include-markdown "signature-core.md" %}
