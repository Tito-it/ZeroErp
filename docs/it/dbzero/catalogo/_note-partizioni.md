> **Ultimo aggiornamento**: 11 novembre 2026

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

### La nota non tiene acceso il suo bersaglio

Una nota annota l'oggetto, non lo tiene in vita: non è un figlio vivo. Le due chiavi verso il
bersaglio sono fra le eccezioni dell'automazione dell'attivo
([dbops.automazione_attivo_eccezioni](/dbzero/dbops/tabelle/automazione_attivo_eccezioni)), e
quindi:

* **un articolo o un legame con delle note si spegne**, e si riaccende ritrovandole com'erano;
* **una nota si scrive anche su un oggetto spento.**

Le note vanno via con l'oggetto solo quando lo si cancella.

---

### La forma delle note degli altri schemi

Le colonne sono quelle delle note dei documenti ([vendite.note](/dbzero/vendite/tabelle/note)):
`user_insert` e `user_update` sono testo libero, e `tx_id` lega la nota all'audit (lo scrive il
trigger generato dall'automazione `TX_ID`). Come lì, **una nota ha un testo**: almeno uno fra
`testo` e `testo_md` (`chk_note_testo_non_vuoto`).

**L'àncora è sempre il documento.** Una nota di catalogo annota un'anagrafica, e su
un'anagrafica non c'è una riga: `anchor_tipo` vale `DOCUMENTO` e `target_riga_id` resta vuota
(`chk_note_catalogo_ancora_documento`). Le colonne ci sono perché le note di tutti gli schemi
hanno la stessa forma. La posizione invece è libera: `BEFORE` e `AFTER` dicono dove va la nota
rispetto alla riga del documento in cui l'articolo compare.

---

### ⚠️ Che cosa oggi non copre

* **Un codice senza partizione esce come errore grezzo.** La chiave verso
  `config.tipi_entita` ammette ogni codice del vocabolario, ma solo due hanno una partizione:
  per gli altri l'inserimento dal padre fallisce con l'errore di routing di PostgreSQL, non con
  un codice registrato.
* **La lettura comune delle note non le vede.**
  [script.fn_get_note](/dbzero/script/funzioni/fn_get_note) vuole un bersaglio `bigint`, e
  queste note hanno un `uuid`: si leggono da [catalogo.vw_note](/dbzero/catalogo/views/vw_note),
  la proiezione comune, o dalle due viste che la leggono per il loro bersaglio,
  [catalogo.vw_articoli_note](/dbzero/catalogo/views/vw_articoli_note) e
  [catalogo.vw_articoli_componenti_note](/dbzero/catalogo/views/vw_articoli_componenti_note).
