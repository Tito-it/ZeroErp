## 📘 Documentazione Concettuale – Tabella `catalogo.unita_misura_conversioni`

> **Ultimo aggiornamento**: 8 novembre 2026
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
> * [catalogo.fn_get_uom_factor](/dbzero/catalogo/funzioni/fn_get_uom_factor) — l'unica funzione che legge questa tabella
> * [script.trgfn_qta_from_operativa](/dbzero/script/funzioni/trgfn_qta_from_operativa) — il calcolo della quantità sulle righe di vendita, che questa tabella non la legge
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
* Per la stessa coppia ordinata (da A a B) due periodi non si sovrappongono: quando il
  fattore cambia, si chiude la riga vecchia e se ne scrive una nuova.
* Una conversione attiva vuole le due unità attive, e un'unità che ha conversioni attive
  non si spegne.

---

### Chi la legge

La legge solo `catalogo.fn_get_uom_factor`, come ripiego quando l'articolo non ha una sua
mappatura per l'unità richiesta: prima la conversione diretta (dall'unità richiesta alla
base dell'articolo), poi quella inversa, di cui prende il reciproco. Si considerano solo le
righe attive in vigore alla data operativa di oggi.

---

### ⚠️ Che cosa oggi non copre

* **Il calcolo delle quantità non la usa.** Le righe dei documenti di vendita ricavano la
  quantità base con `script.trgfn_qta_from_operativa`, che legge solo la mappatura
  dell'articolo e, se non la trova, usa il fattore 1 senza errore. `fn_get_uom_factor`, che
  ha il ripiego su questa tabella, non la chiama nessuna funzione del database. Una
  conversione scritta qui, oggi, non cambia nessuna quantità.
* **Le due direzioni possono contraddirsi.** Il divieto di sovrapposizione vale per la
  coppia ordinata: A → B con fattore 10 e B → A con fattore 0,2 possono essere attive
  insieme, e la funzione prende la diretta senza segnalare niente.
* **Il controllo sulla famiglia non è al riparo dalla concorrenza.** Se una transazione
  cambia la famiglia di un'unità mentre un'altra scrive una conversione che la usa, nessuna
  delle due aspetta l'altra, e può nascere una conversione fra famiglie diverse.
* Il seed è vuoto: nessuna conversione è scritta di serie.

---

### Codici errore

* `E_GENERICO` — le due unità sono di famiglie diverse (dal guard di tipologia).
* `E_DATA_AL_MINORE_DAL` — `valido_al` prima di `valido_dal`.
* `E_ATTIVO_PADRE_NON_ATTIVO` — una conversione attiva su un'unità spenta, alla fine della
  transazione.

---

### Test

* `db/pgtap/catalogo/test-uom-tipi-global-conversioni-v1.sql` — una conversione dentro la
  stessa famiglia passa, una fra due famiglie è rifiutata.
* `db/pgtap/catalogo/test-fn-get-uom.sql` — la funzione trova la conversione diretta e
  quella inversa.
* `db/pgtap/dbops/test-anti-overlap-enforcement-gate-v1.sql` — la tabella ha il vincolo di
  unicità nel tempo.

---

### Note di migrazione

* 2026-04-28 — il controllo sulla famiglia restringe la tabella alle conversioni fra unità
  dello stesso tipo.
* 2026-05-14 — il periodo `validita` diventa una colonna calcolata da `valido_dal` e
  `valido_al`.

---

{% include-markdown "signature-core.md" %}
