## 📘 Documentazione Concettuale – Tabella `catalogo.unita_misura_conversioni`

> **Ultimo aggiornamento**: 10 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura) — le due unità che la conversione collega
> * [catalogo.uom_tipi](/dbzero/catalogo/tabelle/uom_tipi) — la famiglia che le due unità devono avere in comune
> * [catalogo.articoli_uom_operativa](/dbzero/catalogo/tabelle/articoli_uom_operativa) — i fattori di un solo articolo, la sede delle confezioni
>
> Approfondimento funzioni:
>
> * [catalogo.fn_uom_fonti_conversione](/dbzero/catalogo/funzioni/fn_uom_fonti_conversione) — l'unica funzione che legge questa tabella: le fonti del fattore coi loro periodi
> * [catalogo.fn_get_uom_factor](/dbzero/catalogo/funzioni/fn_get_uom_factor) — il fattore a una data, dalle fonti
> * [catalogo.trgfn_uom_guard_storia](/dbzero/catalogo/funzioni/trgfn_uom_guard_storia) — la conversione è storia: cosa si cambia e cosa no
> * [catalogo.trgfn_uom_guard_listini_attivi](/dbzero/catalogo/funzioni/trgfn_uom_guard_listini_attivi) — una conversione non si chiude sotto un listino attivo che la usa
> * [script.trgfn_qta_from_operativa](/dbzero/script/funzioni/trgfn_qta_from_operativa) — il calcolo della quantità sulle righe di vendita, che la legge attraverso il fattore
> * [catalogo.trgfn_uom_conversioni_guard_tipo](/dbzero/catalogo/funzioni/trgfn_uom_conversioni_guard_tipo) — rifiuta una conversione fra due famiglie

---

### 🎯 Scopo Principale

Contiene le conversioni globali fra unità di misura della stessa famiglia (chilogrammi in
grammi, metri in centimetri), valide per ogni articolo e per un periodo. Ogni riga dice
quante unità di arrivo vale una unità di partenza.

Le confezioni e i rapporti che dipendono dal prodotto (la scatola da 50 pezzi, il bancale)
non stanno qui ma in `articoli_uom_operativa`, dove il fattore è per articolo.

---

### Come si legge una riga

* `fattore` è il moltiplicatore da `uom_from_id` a `uom_to_id`: con chilogrammo → grammo il
  fattore è 1000. Dev'essere positivo e finito.
* Le due unità devono essere diverse, e della stessa famiglia.
* `valido_dal` è obbligatorio; `valido_al` vuoto vuol dire «senza fine». Il periodo può
  durare un giorno solo, ma la fine non può venire prima dell'inizio.
* Per la stessa coppia di unità, in un verso o nell'altro, due periodi non si sovrappongono:
  in un dato giorno c'è al più una conversione fra A e B, scritta da A a B oppure da B ad A.
  L'inversa non si scrive, la calcola la funzione. Quando il fattore cambia, si chiude la riga
  vecchia e se ne scrive una nuova. Anche una riga spenta conta nella sovrapposizione.

---

### La conversione è storia

Le regole sono quelle della mappatura di un articolo (`trgfn_uom_guard_storia`):

* **le due unità, il fattore e l'inizio** non si cambiano mai (`E_UOM_STORIA_IMMUTABILE`): un
  fattore nuovo è una riga nuova, dal giorno dopo la chiusura della vecchia;
* **la fine** si sposta, ma non prima di ieri (`E_UOM_STORIA_CHIUSURA_RETROATTIVA`); una
  conversione già finita non si riapre né si accorcia (`E_UOM_STORIA_CHIUSA`);
* **spegnere, riaccendere o cancellare** si può solo finché la conversione non ha giorni
  passati; una già in vigore si chiude (`E_UOM_STORIA_IN_VIGORE`);
* chiudere o spegnere una conversione che un listino attivo usa ancora, oltre la nuova fine,
  è rifiutato a fine transazione (`E_UOM_CHIUSURA_CON_LISTINI_ATTIVI`).

Per lo stesso motivo la conversione **non è legata all'attivo** delle sue unità (le due FK
sono fra le eccezioni dell'automazione ATTIVO): un'unità si spegne anche se ha conversioni, e
si riaccende trovandole come le aveva lasciate.

---

### Chi la legge

La legge solo `catalogo.fn_uom_fonti_conversione`, e attraverso di lei `fn_get_uom_factor`, come ripiego quando l'articolo non ha una sua
mappatura per l'unità richiesta: la conversione fra l'unità richiesta e la base
dell'articolo, attiva e in vigore alla data che la funzione riceve. Se è scritta dall'unità
richiesta verso la base vale il suo fattore, se è scritta al contrario il suo reciproco.

La funzione la chiama il trigger della quantità delle righe di vendita, alla data del
documento: una conversione scritta qui cambia le quantità delle righe nuove nelle unità che
l'articolo non mappa. Le righe già scritte tengono il fattore che hanno fotografato.

---

### ⚠️ Che cosa oggi non copre

* Il seed è vuoto: nessuna conversione è scritta di serie.
* Una conversione che viola la sovrapposizione esce come errore del vincolo, non con un codice
  registrato: il backend lo traduce dal nome del vincolo.

---

### Codici errore

* `E_UOM_CONVERSIONE_TIPO_DIVERSO` — le due unità sono di famiglie diverse (dal guard di tipologia).
* `E_DATA_AL_MINORE_DAL` — `valido_al` prima di `valido_dal`.
* `E_UOM_STORIA_IMMUTABILE`, `E_UOM_STORIA_IN_VIGORE`, `E_UOM_STORIA_CHIUSURA_RETROATTIVA`,
  `E_UOM_STORIA_CHIUSA` — le regole della storia, qui sopra.
* `E_UOM_CHIUSURA_CON_LISTINI_ATTIVI` — una conversione chiusa o spenta mentre un listino
  attivo ne usa le unità oltre la nuova fine, alla fine della transazione.

---

### Test

* `db/pgtap/catalogo/test-uom-tipi-global-conversioni-v1.sql` — una conversione dentro la
  stessa famiglia passa, una fra due famiglie è rifiutata.
* `db/pgtap/catalogo/test-fn-get-uom.sql` — la funzione trova la conversione diretta e
  quella inversa.
* `db/pgtap/catalogo/test-uom-fattore-e-regole-v1.sql` — la conversione nei due versi, il verso
  opposto sovrapposto rifiutato, il codice della famiglia diversa.
* `db/pgtap/catalogo/test-uom-storia-v1.sql` — cosa si cambia e cosa no, la chiusura a ieri,
  l'unità che si spegne con le sue conversioni.
* `db/pgtap/vendite/test-listino-uom-periodo-v1.sql` — una conversione non si chiude sotto un
  listino attivo che la usa.
* `db/pgtap/dbops/test-anti-overlap-enforcement-gate-v1.sql` — la tabella ha il vincolo che
  esclude le sovrapposizioni.

---

### Note di migrazione

* 2026-04-28 — il controllo sulla famiglia restringe la tabella alle conversioni fra unità
  dello stesso tipo.
* 2026-05-14 — il periodo `validita` diventa una colonna calcolata da `valido_dal` e
  `valido_al`.
* 2026-11-09 — una conversione per coppia, nei due versi; la legge il calcolo delle quantità,
  alla data del documento (brief-db-revisione-catalogo, giro 2).
* 2026-11-10 — la conversione è storia, come la mappatura; non si chiude sotto un listino
  attivo; esce dal legame ATTIVO con le sue unità (brief-db-revisione-catalogo, giro 2-bis).

---

{% include-markdown "signature-core.md" %}
