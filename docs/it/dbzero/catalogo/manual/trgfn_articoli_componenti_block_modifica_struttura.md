## 📘 Documentazione Concettuale – Trigger function `catalogo.trgfn_articoli_componenti_block_modifica_struttura`

> **Ultimo aggiornamento**: 8 novembre 2026
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
> * [script.trgfn_guard_date_validita](/dbzero/script/funzioni/trgfn_guard_date_validita) — giudica l'ordine delle date, che qui non si guarda
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva l'errore
>
> Guide:
>
> * [Gestione listini](/guide/gestione-listini#53-immutabilita-della-bom-pattern-chiudi-nuova-versione) — chiudi e nuova versione

---

### 🎯 Scopo Principale

Rende immutabile la struttura di un legame della distinta base: rifiuta ogni DELETE e ogni UPDATE che cambia un
campo di struttura. Un legame non si corregge: si chiude con `valido_al` e se ne inserisce uno nuovo.

Così le commesse e le fatture che hanno già usato una versione della distinta restano ancorate alla struttura di
allora.

---

### Che cosa blocca e che cosa lascia passare

* **Il DELETE** è sempre rifiutato: un legame non si elimina, si chiude.
* **Un UPDATE** è rifiutato se cambia `coeff_qta`, `componente_id`, `obbligatorio`, `esposizione_in_fattura` o
  `valido_dal`.
* **Passano** la chiusura con `valido_al`, e le modifiche a `attivo`, alle note, a `meta` e ai campi di audit.

`validita` non è nell'elenco perché è una colonna generata: PostgreSQL ne rifiuta la scrittura prima che il
trigger giri.

`valido_al` è fra le colonne che fanno scattare il trigger, ma il corpo non lo confronta: il trigger scatta e lascia
passare.

---

### ⭐ L'ordine delle date ha un'altra sede

Che `valido_al` non preceda `valido_dal` lo giudica il guard comune delle date, montato su ogni tabella con la
coppia di date (`E_DATA_AL_MINORE_DAL`). `valido_al` uguale a `valido_dal` è un legame di un giorno, ed è ammesso.
Che due versioni della stessa coppia non si sovrappongano lo garantisce il vincolo
`uq_articoli_componenti_no_overlap` della tabella.

---

### ⚠️ Che cosa oggi non copre

* **`prodotto_id` è libero.** Il trigger non lo guarda: un legame può passare sotto un altro kit, e le righe
  componente dei documenti che lo citano restano legate a un kit diverso da quello per cui erano nate.
* **`valido_al` si sposta in ogni direzione.** Il trigger ammette qualunque data di fine che non preceda l'inizio:
  la chiusura nel passato di un legame già usato e la riapertura con `valido_al` vuoto passano. La struttura è
  protetta, la storia delle date no.

---

### Codici errore

* `E_BOM_MODIFICA_VIETATA` — un DELETE, o un UPDATE che cambia un campo di struttura. Il dettaglio dice quale
  delle due operazioni, e il suggerimento è di chiudere la riga e inserirne una nuova.

---

### Test

* `db/pgtap/catalogo/test-articoli-componenti-immutabilita.sql` — il DELETE e la modifica di ogni campo di
  struttura sono rifiutati; la chiusura, anche nello stesso giorno dell'inizio, e le modifiche a note, `meta` e
  `attivo` passano; una data di fine prima dell'inizio la ferma il guard comune; una nuova versione dal giorno
  dopo la chiusura si inserisce.

---

### Note di migrazione

* 2026-04-22 — nasce: la distinta diventa immutabile sui campi di struttura.
* 2026-09-24 — l'ordine delle date esce dal trigger e passa al guard comune; il codice suo che lo giudicava è
  ritirato.
* 2026-10-01 — il booleano `esposto_in_fattura` diventa `esposizione_in_fattura`, sempre fra i campi bloccati.
* 2026-10-02 — escono dall'elenco `partecipa_qta` e `determina_qta_padre`, ritirate dalla tabella.

---

{% include-markdown "signature-core.md" %}
