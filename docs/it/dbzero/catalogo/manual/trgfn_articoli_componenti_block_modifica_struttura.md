## 📘 Documentazione Concettuale – Trigger function `catalogo.trgfn_articoli_componenti_block_modifica_struttura`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — la distinta che protegge
>
> Approfondimento viste:
>
> * [catalogo.vw_articoli_componenti_dettaglio](/dbzero/catalogo/views/vw_articoli_componenti_dettaglio) — le capability di chiusura offerte al frontend
>
> Approfondimento funzioni:
>
> * [catalogo.trgfn_articoli_componenti_guard_componente](/dbzero/catalogo/funzioni/trgfn_articoli_componenti_guard_componente) — giudica la fine che si allontana, come composizione nuova
> * [script.trgfn_guard_date_validita](/dbzero/script/funzioni/trgfn_guard_date_validita) — giudica l'ordine delle date, che qui non si guarda
> * [script.fn_data_operativa](/dbzero/script/funzioni/fn_data_operativa) — il giorno aziendale, a cui si misura «già passato»
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva l'errore
> * [catalogo.fn_chiudi_legame_distinta](/dbzero/catalogo/funzioni/fn_chiudi_legame_distinta) — il verbo che chiude un legame coi suoi prezzi bundle
> * [script.fn_check_legame_distinta_chiudibile](/dbzero/script/funzioni/fn_check_legame_distinta_chiudibile) — perché un legame non si chiude, per i suoi prezzi
>
> Guide:
>
> * [Gestione listini](/guide/gestione-listini#53-immutabilita-della-bom-pattern-chiudi-nuova-versione) — chiudi e nuova versione

---

### 🎯 Scopo Principale

Rende la distinta base una storia: rifiuta ogni DELETE di un legame, ogni UPDATE che cambia un campo di struttura,
e ogni cambio della fine (`valido_al`) che toccherebbe giorni già passati. Un legame non si corregge: si chiude con
`valido_al` e se ne inserisce uno nuovo.

Così le commesse e le fatture che hanno già usato una versione della distinta restano ancorate alla struttura e ai
giorni di allora.

---

### Che cosa blocca e che cosa lascia passare

* **Il DELETE** è sempre rifiutato: un legame non si elimina, si chiude.
* **Un UPDATE della struttura** è rifiutato se cambia `prodotto_id`, `componente_id`, `coeff_qta`, `obbligatorio`,
  `esposizione_in_fattura` o `valido_dal`. Anche il padre è struttura: un legame non passa sotto un altro kit,
  perché le righe-componente dei documenti che lo citano resterebbero legate a un kit diverso da quello per cui
  erano nate.
* **Passano** le modifiche a `attivo`, alle note, a `meta` e ai campi di audit, e i cambi di `valido_al` descritti
  sotto.

`validita` non è nell'elenco perché è una colonna generata: PostgreSQL ne rifiuta la scrittura prima che il
trigger giri.

---

### ⭐ La fine non cambia i giorni già passati

Il riferimento è il giorno aziendale (`script.fn_data_operativa`).

* **Un legame la cui fine è già passata non si tocca più** (`E_BOM_LEGAME_CHIUSO`): né spostata in avanti né tolta.
  Rimettere il componente nella distinta è un legame nuovo.
* **Negli altri legami la fine nuova è vuota, oppure da ieri in avanti.** Una fine prima di ieri toglierebbe al
  legame giorni in cui era in vigore, e i documenti di quei giorni lo rileggono (`E_BOM_CHIUSURA_RETROATTIVA`, con la
  prima data ammessa nel messaggio).
* **Chiudere a ieri è ammesso**: non cambia la storia, ed è il modo di far valere da oggi la versione nuova, perché la
  validità comprende i due estremi.
* **Togliere una fine futura è ammesso**: non tocca il passato. È però una composizione nuova, e la giudica il guard
  del legame (`catalogo.trgfn_articoli_componenti_guard_componente`), come l'allungamento della fine.

Il trigger, per nome, parla prima del guard del legame: il rifiuto d'immutabilità arriva per primo.

---

### ⭐ Una fine che lascia fuori dei prezzi bundle

Un prezzo bundle sta dentro il periodo del suo legame (chiave esterna temporale dei prezzi verso la distinta). Se la
fine nuova lascia fuori dei prezzi del legame (`vendite.fn_prezzi_legame_oltre_la_fine`), la chiusura non passa in
silenzio:

* **prima ciò che vieta**, il primo motivo di `script.fn_check_legame_distinta_chiudibile`: prezzi in listini che
  chi chiude non vede (`E_BOM_CHIUSURA_PREZZI_ALTRE_AZIENDE`), o prezzi di una versione non in bozza che cominciano
  dopo la fine (`E_BOM_CHIUSURA_PRIMA_DEI_PREZZI`, con la prima fine ammessa);
* **poi l'avviso** `E_BOM_CHIUSURA_CON_PREZZI`, coi numeri dei prezzi e delle versioni. La chiusura si conferma col
  verbo `catalogo.fn_chiudi_legame_distinta`, che chiude (o toglie) i prezzi prima di arrivare qui: a quel punto
  non ne resta nessuno, e il guard lascia passare.

Senza questi due passi la chiusura moriva sulla chiave esterna, con un errore grezzo.

---

### ⭐ L'ordine delle date ha un'altra sede

Che `valido_al` non preceda `valido_dal` lo giudica il guard comune delle date, montato su ogni tabella con la
coppia di date (`E_DATA_AL_MINORE_DAL`), che parla dopo questo trigger: una fine prima dell'inizio qui non si giudica,
così l'operatore legge la frase giusta. `valido_al` uguale a `valido_dal` è un legame di un giorno, ed è ammesso.
Che due versioni della stessa coppia non si sovrappongano lo garantisce il vincolo
`uq_articoli_componenti_no_overlap` della tabella.

---

### Codici errore

* `E_BOM_MODIFICA_VIETATA` — un DELETE, o un UPDATE che cambia un campo di struttura. Il dettaglio dice quale
  delle due operazioni, e il suggerimento è di chiudere la riga e inserirne una nuova.
* `E_BOM_LEGAME_CHIUSO` — campo `valido_al`: si cambia la fine di un legame già finito.
* `E_BOM_CHIUSURA_RETROATTIVA` — campo `valido_al`: la fine nuova è prima di ieri; il messaggio dice la prima data
  ammessa.
* `E_BOM_CHIUSURA_PREZZI_ALTRE_AZIENDE`, `E_BOM_CHIUSURA_PRIMA_DEI_PREZZI` — campo `valido_al`: i prezzi bundle che
  vietano la chiusura.
* `E_BOM_CHIUSURA_CON_PREZZI` — campo `valido_al`: l'avviso, coi numeri; bersaglio il kit.

---

### Test

* `db/pgtap/catalogo/test-articoli-componenti-immutabilita.sql` — il DELETE e la modifica di ogni campo di
  struttura sono rifiutati; la chiusura, anche nello stesso giorno dell'inizio, e le modifiche a note, `meta` e
  `attivo` passano; una data di fine prima dell'inizio la ferma il guard comune; una nuova versione dal giorno
  dopo la chiusura si inserisce.
* `db/pgtap/catalogo/test-distinta-storia-e-ritorni-v1.sql` — il padre non cambia; la fine di un legame finito non
  si sposta né si toglie; la fine prima di ieri è rifiutata, quella a ieri passa; una fine futura si toglie; una
  fine prima dell'inizio la ferma la regola del periodo.
* `db/pgtap/catalogo/test-chiudi-legame-con-prezzi-v1.sql` — la chiusura coi prezzi bundle aperti: l'avviso e i
  due motivi che vietano, dall'UPDATE diretto.

---

### Note di migrazione

* 2026-04-22 — nasce: la distinta diventa immutabile sui campi di struttura.
* 2026-09-24 — l'ordine delle date esce dal trigger e passa al guard comune; il codice suo che lo giudicava è
  ritirato.
* 2026-10-01 — il booleano `esposto_in_fattura` diventa `esposizione_in_fattura`, sempre fra i campi bloccati.
* 2026-10-02 — escono dall'elenco `partecipa_qta` e `determina_qta_padre`, ritirate dalla tabella.
* 2026-11-09 — `prodotto_id` entra fra i campi di struttura, e la fine di un legame non cambia più i giorni già
  passati: nascono `E_BOM_LEGAME_CHIUSO` ed `E_BOM_CHIUSURA_RETROATTIVA` (brief-db-revisione-catalogo, giro 1).
* 2026-11-09 — una fine che lascia fuori dei prezzi bundle non passa in silenzio: prima i motivi che vietano, poi
  l'avviso `E_BOM_CHIUSURA_CON_PREZZI`, e la conferma dal verbo (brief-db-revisione-catalogo, giro 3).

---

{% include-markdown "signature-core.md" %}
