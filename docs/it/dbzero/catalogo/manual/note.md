## 📘 Documentazione Concettuale – Tabella `catalogo.note`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.note_articoli](/dbzero/catalogo/tabelle/note_articoli) — la partizione delle note sugli articoli
> * [catalogo.note_articoli_componenti](/dbzero/catalogo/tabelle/note_articoli_componenti) — la partizione delle note sui legami di distinta
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — l'anagrafica annotata, che può anche puntare una sua nota
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — il legame di distinta annotato
> * [config.tipi_entita](/dbzero/config/tabelle/tipi_entita) — il vocabolario dei codici di `target_tipo`
> * [config.note_stili](/dbzero/config/tabelle/note_stili) — lo stile della nota
> * [config.lingue](/dbzero/config/tabelle/lingue) — la lingua della nota
> * [vendite.note](/dbzero/vendite/tabelle/note) — il meccanismo delle note, documentato per intero
>
> Approfondimento viste:
>
> * [catalogo.vw_articoli_note](/dbzero/catalogo/views/vw_articoli_note) — la lettura delle note di un articolo
> * [catalogo.vw_articoli_componenti_note](/dbzero/catalogo/views/vw_articoli_componenti_note) — la lettura delle note di un legame di distinta

---

### 🎯 Scopo Principale

La tabella madre delle note del catalogo, divisa in partizioni per `target_tipo`: non annota un bersaglio proprio, le note stanno nelle partizioni `note_articoli` e `note_articoli_componenti`, una per ciascuna tabella annotata.

---

{% include-markdown "it/dbzero/catalogo/_note-partizioni.md" %}

---

### L'articolo e il legame possono puntare una loro nota

Oltre alle note che li annotano, [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) e
[catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) hanno la coppia
`note_target_tipo` e `note_id`, una chiave esterna composta verso questo padre. Un CHECK su
ciascuna tabella ammette in `note_target_tipo` soltanto il codice della propria partizione
(`ARTICOLO` sull'articolo, `ARTICOLO_COMPONENTE` sul legame), così il puntatore non può finire
sulla nota di un altro tipo di oggetto. Se la nota puntata si cancella, il puntatore torna
vuoto.

Il puntatore non verifica che la nota annoti proprio quell'oggetto: basta che stia nella
partizione giusta.

---

### Codici errore

* `E_ATTIVO_PADRE_NON_ATTIVO` — una nota scritta su un articolo o su un legame spento.
* `E_ATTIVO_BLOCK_CHILDREN_EXIST` — si spegne un articolo o un legame che ha una nota.

---

### Test

* `db/pgtap/catalogo/test-articoli-vincoli-note-uom-overlap.sql` — crea una nota su un articolo
  dal padre, e prova il puntatore dell'articolo: il codice di un'altra partizione e una nota
  inesistente sono rifiutati.
* `db/pgtap/config/test-grammatica-note-target-tipo-v1.sql` — `target_tipo` porta il codice di
  `config.tipi_entita` con una chiave esterna, ogni partizione ha per confine un codice del
  vocabolario, un codice ritirato non trova partizione; il CHECK del puntatore ammette
  esattamente il confine della partizione a cui punta.
* `db/pgtap/ui/test-lista-note-gemelle-v1.sql` — la lista delle note di catalogo ha le stesse
  colonne di quella delle note di vendita.
* `db/pgtap/ui/test-lista-definizione-perimetro-emittente-v1.sql` — la lista delle note di
  catalogo non ha perimetro dell'emittente.

---

### Note di migrazione

* 2026-01-13 — nasce la tabella, con le due partizioni per gli articoli e per i legami di
  distinta.
* 2026-10-25 — `target_tipo` passa al codice di `config.tipi_entita`, al singolare (prima
  `ARTICOLI` e `ARTICOLI_COMPONENTI`), con una chiave esterna al posto del CHECK scritto a mano;
  il padre è ricostruito e le partizioni staccate e riattaccate.

---

{% include-markdown "signature-core.md" %}
