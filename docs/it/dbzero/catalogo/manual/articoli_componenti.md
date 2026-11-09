## 📘 Documentazione Concettuale – Tabella `catalogo.articoli_componenti`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — il kit (padre) e i suoi componenti stanno entrambi qui
> * [config.esposizioni_componente](/dbzero/config/tabelle/esposizioni_componente) — i tre modi in cui un componente si vede in fattura
> * [catalogo.note](/dbzero/catalogo/tabelle/note) — le note agganciate a un legame
>
> Approfondimento viste:
>
> * [catalogo.vw_articoli_componenti_dettaglio](/dbzero/catalogo/views/vw_articoli_componenti_dettaglio) — la distinta letta dalla lista, con codici e capability di chiusura
> * [vendite.vw_fattura_righe_esposte](/dbzero/vendite/views/vw_fattura_righe_esposte) — applica l'esposizione in fattura
>
> Approfondimento funzioni:
>
> * [catalogo.trgfn_articoli_componenti_block_modifica_struttura](/dbzero/catalogo/funzioni/trgfn_articoli_componenti_block_modifica_struttura) — la struttura di un legame non si modifica, la fine non cambia il passato
> * [catalogo.trgfn_articoli_componenti_guard_componente](/dbzero/catalogo/funzioni/trgfn_articoli_componenti_guard_componente) — giudica ogni composizione nuova, padre e componente
> * [script.fn_articolo_riga_contesto](/dbzero/script/funzioni/fn_articolo_riga_contesto) — il lato documento della check: il padre deve essere composito
> * [catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva](/dbzero/catalogo/funzioni/trgfn_articoli_guard_flags_struttura_bom_attiva) — le stesse regole viste dal lato articolo
> * [script.trgfn_guard_date_validita](/dbzero/script/funzioni/trgfn_guard_date_validita) — l'ordine delle date
>
> Guide:
>
> * [Gestione listini](/guide/gestione-listini#53-immutabilita-della-bom-pattern-chiudi-nuova-versione) — come si cambia una distinta: chiudi e nuova versione
> * [Modello componenti BoM](/dev/manual/modello-componenti-bom) — il modello del kit e dei suoi componenti

---

### 🎯 Scopo Principale

La distinta base di vendita: ogni riga lega un articolo composito (il kit, `prodotto_id`) a un suo componente
(`componente_id`), con un coefficiente di quantità e un periodo di validità da `valido_dal` a `valido_al`.

La distinta cambia nel tempo per versioni: una riga non si corregge, si chiude e se ne inserisce una nuova.
Così le commesse e le fatture che hanno già usato una versione restano spiegabili con la struttura di allora.

---

### Che cosa porta un legame

* **La quantità.** Nei documenti la quantità del componente è sempre la quantità del kit moltiplicata per
  `coeff_qta`. Il coefficiente non è negativo ed è un numero finito.
* **L'obbligatorietà.** `obbligatorio` oggi vuol dire una cosa sola: il componente non può avere prezzo zero.
* **L'esposizione in fattura.** `esposizione_in_fattura` dice come il componente si vede sotto il suo kit, ed è
  solo presentazione: tutti i componenti attivi generano comunque righe nei documenti e in commessa.
  * `NASCOSTO` (il default): il componente non compare, il suo valore sta nel totale del kit.
  * `DESCRITTIVO`: una riga sotto il kit senza prezzo né importo; il valore sta nel totale del kit.
  * `VALORIZZATO`: una riga sotto il kit con quantità, prezzo e importo suoi, fuori dal totale del kit.
* **L'unità di misura** è quella del componente, libera: nessun vincolo la lega a quella del kit. Un kit può essere
  fatto di pezzi, metri e ore. In fattura la riga del kit stampa quantità e unità della riga padre del documento.

---

### Le regole su padre e componente

* **Il padre è un articolo composito** (`is_composito`). Lo giudica il lato documento della check comune, a ogni
  composizione nuova. Un articolo solo componente non fa da padre perché non può essere composito: lo esclude il
  CHECK `chk_articoli_composito_non_solo_componente` di `catalogo.articoli`.
* **Il componente non è il padre stesso, non è composito, ha la stessa IVA del padre** e, quando il legame è una
  scelta nuova, non è ritirato. La distinta ha un livello solo: un kit non contiene altri kit. Le regole stanno in
  una check comune (`script.fn_check_articolo_riga`, documento `ARTICOLO`), e il guard di tabella solleva il primo
  motivo. Il CHECK `chk_articoli_componenti_no_selfref` resta come rete sotto il guard.
* **Una composizione nuova si giudica sempre**: un legame attivo che nasce, che si riattiva, o la cui fine si
  allontana (`valido_al` tolto o spostato in avanti). La chiusura non si giudica: un legame si chiude sempre.
* **Padre e componente sono attivi.** Lo controllano due constraint trigger differiti, generati dalla regola
  `ATTIVO` delle automazioni, uno per colonna: scattano al COMMIT.
* **Dal lato articolo** valgono le stesse regole al contrario: un componente di una distinta in vigore o futura
  non diventa composito, il padre di una distinta in vigore o futura resta composito, e l'IVA di un articolo che sta in un legame attivo non si cambia da sola
  (`trgfn_articoli_guard_flags_struttura_bom_attiva`, `trgfn_articoli_guard_iva_bom_attiva`).

---

### ⛔ Una riga non si corregge: si chiude e se ne inserisce un'altra

Il DELETE è sempre vietato, e così la modifica di `prodotto_id`, `componente_id`, `coeff_qta`, `obbligatorio`,
`esposizione_in_fattura` e `valido_dal` (`E_BOM_MODIFICA_VIETATA`). Si possono cambiare `attivo`, le note, `meta`, i
campi di audit e `valido_al` (è la chiusura), con le regole della fine qui sotto.

Per cambiare un legame si chiude la riga corrente con `valido_al` e se ne inserisce una nuova che parte **dal
giorno dopo**. Il periodo comprende il primo e l'ultimo giorno: una riga chiusa oggi vale ancora per tutto oggi.
Per far valere la versione nuova già da oggi, la riga corrente si chiude a ieri.

---

### ⛔ La fine non cambia i giorni già passati

La distinta è una storia, e i documenti già emessi la rileggono com'era. Al giorno aziendale:

* la fine di un legame **già finito** non si tocca più, né si toglie (`E_BOM_LEGAME_CHIUSO`): rimettere il
  componente è un legame nuovo;
* negli altri legami la fine nuova è vuota oppure **da ieri in avanti** (`E_BOM_CHIUSURA_RETROATTIVA`); chiudere a
  ieri è ammesso;
* togliere una fine futura è ammesso, ed è una composizione nuova che il guard del legame giudica.

Le modifiche e le cancellazioni passano dalla storicizzazione generica, e lo spegnimento di un legame
(`attivo = false`) è rifiutato finché una riga componente di un documento di vendita, o una nota, lo cita.

---

### ⭐ Le versioni della stessa coppia non si sovrappongono

`validita` è una colonna generata: il periodo da `valido_dal` a `valido_al` con entrambi gli estremi compresi, e
infinito se `valido_al` è vuoto. Il vincolo `uq_articoli_componenti_no_overlap`, un `UNIQUE … WITHOUT OVERLAPS`
su prodotto, componente e periodo, impedisce che due versioni della stessa coppia valgano nello stesso giorno.

`valido_al` può essere uguale a `valido_dal`: è un legame di un giorno. Che non lo preceda lo giudica il guard
comune delle date (`E_DATA_AL_MINORE_DAL`), lo stesso di ogni tabella con la coppia di date.

Gli indici per prodotto e per componente, ciascuno con le due date, servono a espandere la distinta di un kit a
una data e a trovare in quali kit compare un componente.

---

### Codici errore

* `E_BOM_MODIFICA_VIETATA` — DELETE, o modifica di un campo di struttura.
* `E_BOM_LEGAME_CHIUSO` — si cambia la fine di un legame già finito.
* `E_BOM_CHIUSURA_RETROATTIVA` — la fine nuova è prima di ieri.
* `E_ARTICOLO_NON_COMPOSITO` — il padre non esiste o non è composito.
* `E_ARTICOLO_OBSOLETO`, `E_BOM_COMPONENTE_PADRE`, `E_BOM_COMPONENTE_COMPOSITO`, `E_BOM_IVA_DISCORDANTE` — i motivi
  sul componente, nell'ordine in cui la check li elenca.
* `E_DATA_AL_MINORE_DAL` — `valido_al` precede `valido_dal`.

---

### Test

* `db/pgtap/catalogo/test-articoli-componenti-immutabilita.sql` — DELETE e modifiche di struttura rifiutate; la
  chiusura, anche nello stesso giorno, e le modifiche a note, `meta` e `attivo` ammesse.
* `db/pgtap/catalogo/test-articoli-componenti-guard-attivo-composito.sql` — padre o componente non attivi, padre
  non composito: rifiutati.
* `db/pgtap/catalogo/test-articoli-componenti-solo-componente.sql` — un kit non diventa solo componente (CHECK);
  un articolo solo componente non fa da padre, ma fa da componente.
* `db/pgtap/catalogo/test-distinta-storia-e-ritorni-v1.sql` — il padre non cambia, le regole della fine, la
  riattivazione e l'allungamento della fine giudicati come composizioni nuove.
* `db/pgtap/catalogo/test-distinta-un-livello-e-onere-natura-v1.sql` — la distinta a un livello, dal legame e
  dall'articolo, e l'ordine dei rifiuti.
* `db/pgtap/catalogo/test-articoli-vincoli-note-uom-overlap.sql` — due versioni sovrapposte della stessa coppia:
  rifiutate.
* `db/pgtap/dbops/test-anti-overlap-enforcement-gate-v1.sql` — il vincolo di non sovrapposizione è un `UNIQUE`
  temporale.

---

### Note di migrazione

* 2026-04-22 — la struttura di un legame diventa immutabile: si chiude e si inserisce.
* 2026-04-27 — ammessa la chiusura nello stesso giorno di inizio: era rifiutata da un CHECK `valido_al > valido_dal`,
  ritirato.
* 2026-05-13 — modello unificato: tutti i componenti attivi generano righe, e l'esposizione diventa una regola di
  presentazione.
* 2026-05-14 — `validita` diventa una colonna generata, e il vincolo di esclusione GiST lascia il posto al
  `UNIQUE … WITHOUT OVERLAPS`.
* 2026-10-01 — il booleano `esposto_in_fattura` diventa `esposizione_in_fattura`, convertito sul posto: `false` →
  `NASCOSTO`, `true` → `DESCRITTIVO`.
* 2026-10-02 — ritirate `partecipa_qta` e `determina_qta_padre`: si salvavano, ma nessuna logica le leggeva.
* 2026-10-13 — la distinta ha un livello solo; le regole sul componente passano alla check comune.
* 2026-11-09 — `prodotto_id` diventa immutabile, la fine di un legame non cambia più i giorni passati, e ogni
  composizione nuova (anche la riattivazione e la fine che si allontana) passa dalla check, che giudica anche il
  padre. Ritirati i due guard sul padre, `trgfn_articoli_componenti_guard_is_composito` e
  `trgfn_articoli_componenti_guard_solo_componente`: il secondo lo sostituisce il CHECK di `catalogo.articoli`
  (brief-db-revisione-catalogo, giro 1).

---

{% include-markdown "signature-core.md" %}
