> **Ultimo aggiornamento**: 8 novembre 2026

### 🗒️ Le partizioni di note in `catalogo`

Le note del catalogo stanno in [catalogo.note](/dbzero/catalogo/tabelle/note), il padre
partizionato per `target_tipo`: una partizione per ciascun oggetto che si può annotare, e il
`target_tipo` è il codice di [config.tipi_entita](/dbzero/config/tabelle/tipi_entita)
dell'oggetto (`ARTICOLO` per [catalogo.note_articoli](/dbzero/catalogo/tabelle/note_articoli),
`ARTICOLO_COMPONENTE` per
[catalogo.note_articoli_componenti](/dbzero/catalogo/tabelle/note_articoli_componenti)).
Posizionamento, ordinamento di rendering, stile e lingua sono quelli del meccanismo note del
progetto, documentato per intero in **[vendite.note](/dbzero/vendite/tabelle/note)**.

Qui non si documentano le colonne una per una: sono quelle del padre.

---

### Il bersaglio è un'anagrafica, e la sua chiave è un `uuid`

Una nota di catalogo non annota un documento ma una voce dell'anagrafica: vale per tutte le
apparizioni future dell'articolo o del legame di distinta, non per una riga di un documento.
Per questo `target_id` è un `uuid`, la chiave delle tabelle del catalogo, mentre le note dei
documenti puntano a chiavi `bigint`.

Le note di catalogo non hanno emittente né RLS: l'articolo è un catalogo unico per tutte le
aziende, e le sue note con lui.

---

### Perché una partizione per ciascun bersaglio

Ogni partizione ha la propria **chiave esterna forte** verso la tabella che annota; sul padre
quella chiave non potrebbe esistere, perché il bersaglio cambia da una partizione all'altra.

La chiave è `ON DELETE CASCADE` e `ON UPDATE CASCADE`: **le note seguono il ciclo di vita di
ciò che annotano**. Se si cancella un articolo, le sue note se ne vanno con lui; un legame di
distinta invece non si cancella mai (la sua struttura è immutabile), e le sue note restano
finché non le si toglie.

---

### ⚠️ Una nota si scrive solo su un oggetto attivo, e lo tiene acceso

Le automazioni dell'attivo montano due trigger su ciascuna partizione e sul suo bersaglio:

* **Scrivere una nota** su un articolo o su un legame spento è rifiutato con
  `E_ATTIVO_PADRE_NON_ATTIVO`. Il controllo è differito: scatta alla fine della transazione.
* **Spegnere l'oggetto annotato** è rifiutato con `E_ATTIVO_BLOCK_CHILDREN_EXIST` finché ha
  almeno una nota. La partizione non ha una colonna `attivo`, e allora il blocco conta ogni
  nota come un figlio vivo: un articolo con una nota non si disattiva, e lo stesso vale per un
  legame di distinta.

Ne segue che un articolo annotato si può cancellare, quando nient'altro lo trattiene (le note
se ne vanno per cascata), ma non disattivare: per spegnerlo, oggi, bisogna prima togliere le
sue note.

---

### ⚠️ Che cosa oggi non copre

Rispetto alle note dei documenti ([vendite.note](/dbzero/vendite/tabelle/note)):

* **Il testo vuoto passa.** Manca il vincolo che chiede almeno uno fra `testo` e `testo_md`: una
  nota senza testo è ammessa.
* **L'àncora `RIGA` è ammessa e non ha significato.** `anchor_tipo` accetta `RIGA` e
  `target_riga_id` si può valorizzare, ma su un'anagrafica non c'è una riga: la colonna non ha
  chiave esterna e nessun guard la controlla (le note dei documenti la verificano con
  [script.trgfn_note_validate_generic](/dbzero/script/funzioni/trgfn_note_validate_generic)).
* **La forma tecnica è diversa.** `user_insert` e `user_update` sono testi limitati a 80
  caratteri invece che liberi, e manca `tx_id`.
* **Un codice senza partizione esce come errore grezzo.** La chiave verso
  `config.tipi_entita` ammette ogni codice del vocabolario, ma solo due hanno una partizione:
  per gli altri l'inserimento dal padre fallisce con l'errore di routing di PostgreSQL, non con
  un codice registrato.
* **La lettura comune delle note non le vede.**
  [script.fn_get_note](/dbzero/script/funzioni/fn_get_note) vuole un bersaglio `bigint`, e
  queste note hanno un `uuid`: si leggono dalle due viste
  [catalogo.vw_articoli_note](/dbzero/catalogo/views/vw_articoli_note) e
  [catalogo.vw_articoli_componenti_note](/dbzero/catalogo/views/vw_articoli_componenti_note).
