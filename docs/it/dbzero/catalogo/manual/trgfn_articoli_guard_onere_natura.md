## 📘 Documentazione Concettuale – Trigger function `catalogo.trgfn_articoli_guard_onere_natura`

> **Ultimo aggiornamento**: 12 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — la tabella su cui il guard è montato
> * [config.causali_onere](/dbzero/config/tabelle/causali_onere) — la causale che fa di un articolo un onere
> * [config.nature_vendita](/dbzero/config/tabelle/nature_vendita) — il vocabolario da cui si legge la destinazione
>
> Approfondimento funzioni:
>
> * [script.fn_natura_e_merce](/dbzero/script/funzioni/fn_natura_e_merce) — la regola «la natura è merce»
> * [vendite.fn_aggiungi_onere_commessa](/dbzero/vendite/funzioni/fn_aggiungi_onere_commessa) — la porta che scrive gli oneri in commessa
> * [catalogo.trgfn_articoli_guard_struttura_se_usato](/dbzero/catalogo/funzioni/trgfn_articoli_guard_struttura_se_usato) — il guard «usato», che non apre questo
>
> Approfondimento viste:
>
> * [catalogo.vw_causali_onere_assegnabili](/dbzero/catalogo/views/vw_causali_onere_assegnabili) — le causali che il picker offre, quelle che questo guard non rifiuta

---

### 🎯 Scopo Principale

Un articolo-onere (con `causale_onere_id`) è un addebito, non un bene: la sua causale non è già
di un altro articolo, la sua natura non è merce, e non è gestito a magazzino, composito, a lotti o
a matricola. Il guard lo fa rispettare quando
l'articolo nasce e quando cambia.

Un onere è una trasferta, un'urgenza, una spesa, una penale. Entra nelle righe di ordine e di
bolla come un articolo, ma resta un addebito.

---

### ⭐ Perché serve

* **La natura.** `natura_vendita_id` ha come default la merce. Senza il guard, un onere creato
  senza dire la natura diventerebbe un bene da evadere in ordine e in bolla, e per il fisco una
  cessione di beni.
* **La struttura.** Magazzino, prelievi, scarico e distinta leggono i flag dell'articolo. Se un
  onere non li ha mai, quei lettori restano corretti per costruzione, senza un filtro ciascuno.
* **Una causale, un articolo.** Ordini, bolle e commesse prendono prezzo e IVA dell'addebito
  dall'articolo della causale: due articoli con la stessa causale renderebbero la scelta ambigua.
  Il legame è 1:1 anche nell'indice `uq_articoli_causale_onere`, ma l'indice risponde con un
  errore tecnico, senza una frase per l'operatore.

---

### Le tre regole

Il guard è `BEFORE INSERT` e `BEFORE UPDATE` delle sei colonne in gioco: natura, causale,
`gestito_a_magazzino`, `is_composito`, `requires_lotto`, `requires_serial`.

* Un articolo senza causale passa.
* Un UPDATE che non cambia nessuna delle sei colonne non si rigiudica (per esempio il loader del
  seed che riscrive gli stessi valori).
* **Prima la causale.** Se la causale è già di un altro articolo, il guard rifiuta
  (`E_ARTICOLO_CAUSALE_ONERE_GIA_USATA`). Si giudica quando l'articolo nasce e quando la causale
  cambia, non quando cambiano gli altri campi. Il messaggio porta il codice dell'articolo, la
  causale e il codice dell'articolo che la porta. L'indice resta: due operatori che scelgono la
  stessa causale nello stesso istante non si vedono a vicenda, e lì risponde l'indice.
* **Poi la natura.** Se la natura è merce, cioè ha destinazione `ORDINE_VENDITA`, il guard
  rifiuta (`E_ARTICOLO_ONERE_NATURA_MERCE`). Il messaggio porta il codice dell'articolo e la
  descrizione della natura.
* **Poi la struttura.** Se l'onere è gestito a magazzino, composito, a lotti o a matricola, il
  guard rifiuta (`E_ARTICOLO_ONERE_STRUTTURA`). Il campo è la prima caratteristica in
  quest'ordine, e il messaggio ne porta il nome leggibile
  (`catalogo.fn_articolo_flag_etichetta`, lo stesso del guard dell'uso).

Le regole parlano in quest'ordine: causale, natura, struttura. Un articolo merce che riceve una
causale libera si sente dire della natura.

---

### La regola legge la destinazione, non il codice della natura

«È merce» lo dice `script.fn_natura_e_merce`, dalla destinazione della natura. È la stessa
lettura dell'ammissione delle righe di ordine e bolla e dello smistamento del preventivo. Se una
natura cambia destinazione nel vocabolario, la regola la segue senza toccare codice.

⚠️ Il guard giudica l'articolo. Un cambio di destinazione in `config.nature_vendita` è una
modifica del vocabolario, e qui non si giudica: gli oneri che hanno già quella natura non si
ricontrollano.

---

### ⛔ Nessuna porta amministratore

Nemmeno la correzione di struttura del SUPER_ADMIN fa di un onere un bene: la porta apre il
guard «usato», non questo.

---

### Codici errore

* `E_ARTICOLO_CAUSALE_ONERE_GIA_USATA` — la causale è già di un altro articolo, quando l'articolo
  nasce o quando cambia causale. Il campo è `causale_onere_id`.
* `E_ARTICOLO_ONERE_NATURA_MERCE` — un onere con una natura che va in ordine: quando nasce,
  quando cambia natura, o quando un articolo merce riceve una causale. Il campo è
  `natura_vendita_id`.
* `E_ARTICOLO_ONERE_STRUTTURA` — un onere gestito a magazzino, composito, a lotti o a matricola,
  quando nasce o quando cambia uno solo di quei flag.

---

### Test

* `db/pgtap/catalogo/test-articolo-onere-struttura-v1.sql` — l'onere non nasce né diventa
  gestito a magazzino, composito, a lotti o a matricola, nemmeno cambiando una sola colonna; un
  UPDATE che non tocca le sei colonne passa.
* `db/pgtap/catalogo/test-causale-onere-assegnabile-v1.sql` — la causale già di un altro
  articolo è rifiutata alla nascita e al cambio, anche prima della struttura; riscrivere la stessa
  causale passa; l'indice resta.
* `db/pgtap/catalogo/test-distinta-un-livello-e-onere-natura-v1.sql` — l'onere con una natura
  che va in ordine è rifiutato quando nasce, quando cambia natura e quando un articolo merce
  diventa onere; con la natura di servizio passa.

---

### Note di migrazione

* 2026-10-13 — nasce, con la sola regola della natura (brief-db-articoli-ammessi-per-documento).
* 2026-10-19 — la destinazione della merce si chiama `ORDINE_VENDITA` (prima `ORDINE`).
* 2026-11-03 — si aggiunge la regola della struttura, e «è merce» passa al building block
  comune (brief-db-addebito-trasporto-ordine).
* 2026-11-09 — il nome leggibile della caratteristica dal building block
  `catalogo.fn_articolo_flag_etichetta` (brief-db-revisione-catalogo, giro 3).
* 2026-11-12 — si aggiunge la regola della causale già di un altro articolo, prima delle altre
  due (brief-db-addebito-trasporto-ordine).

---

{% include-markdown "signature-core.md" %}
