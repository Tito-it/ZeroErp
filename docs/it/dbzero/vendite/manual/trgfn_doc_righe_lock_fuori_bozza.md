## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_doc_righe_lock_fuori_bozza`

> 👀 **Vedi anche**
>
> [script.fn_get_stato_testata_documento](/dbzero/script/funzioni/fn_get_stato_testata_documento) — il lettore `SECURITY DEFINER` da cui prende lo stato
> [script.fn_get_testata_id_di_riga](/dbzero/script/funzioni/fn_get_testata_id_di_riga) — il lettore `SECURITY DEFINER` riga → testata, per il livello RIGA (dal 2026-10-05)
> [vendite.trgfn_doc_guard_delete_solo_bozza](/dbzero/vendite/funzioni/trgfn_doc_guard_delete_solo_bozza) — la stessa regola, sulla testata
> [vendite.trgfn_dlt_block_ordrig_ddtrig](/dbzero/vendite/funzioni/trgfn_dlt_block_ordrig_ddtrig) — il traduttore dei legami a valle, che parla dopo
> [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe) · [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe) · [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe) — gli adottanti
> [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children) — lo stampo dei building block parametrizzati

---

### 🎯 Scopo Principale

**Le righe di un documento si aggiungono, modificano e tolgono solo finché il
documento è in bozza.**

Fuori dalla bozza il contenuto di un documento non è più una proposta ma un
fatto: una merce spedita, una riga già instradata alla fatturazione, un
pricing in vigore. Le correzioni passano da documenti di rettifica — reso,
ri-consegna, nota — non da una riga che cambia.

È un **building block**: una sola funzione, montata su ogni tabella di righe
con due argomenti obbligatori e due facoltativi.

| `TG_ARGV` | Cosa | Esempio |
| --- | --- | --- |
| `[0]` | tipo di documento, per il lettore di stato (`DDT`, `ORDINE`, `CONTRATTO`, `OFFERTA`, `RESO`) | `'DDT'` |
| `[1]` | colonna della riga che porta l'id del padre | `'ddt_id'` |
| `[2]` (opz.) | `codice_interno` dello stato «bozza», default `DRAFT` | `'BOZZA'` per l'offerta |
| `[3]` (opz., dal 2026-10-05) | **livello** del padre: `TESTATA` (default) se la colonna punta alla testata, `RIGA` se punta a una riga del documento (tabelle *nipoti*) | `'RIGA'` per i componenti |

```sql
CREATE TRIGGER trg_ddt_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt
  BEFORE INSERT OR UPDATE OR DELETE ON vendite.ddt_righe
  FOR EACH ROW
  EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('DDT', 'ddt_id');
```

---

### ⭐ Da dove nasce: una riga di merce che poteva sparire

Letto dal catalogo il 21 settembre: `vendite.ddt_righe.attivo` non aveva nessun
guard fuori da `DRAFT`. I soli trigger su `attivo` erano i `block_deact` delle
figlie (fulfillment, resi, componenti, note), e una riga standalone già
instradata alla fatturazione non ne ha — il legame fra la riga e l'attività di
commessa è una **chiave di testo** (`segment_key`), non una FK, e il framework
ATTIVO non può vederlo. Il modello ammetteva quindi di disattivare, o cambiare,
una riga di DDT emesso che un'attività dice `ALLOCATA` o `EMESSA`: merce in
fattura che nessun documento mostra più.

La regola c'era, e in tre posti: la capability
(`fn_available_actions_ddt`: `can_edit_righe = (stato = DRAFT)`), il backend
(`_STATI_RIGHE_MODIFICABILI = {DRAFT}`, identico per ordini e preventivi) e la
guida. A DB no. Una capability senza il suo guard è l'inversione che le linee
guida API vietano: *il motivo lo produce la stessa funzione che il database usa
per rifiutare*.

> Decisione di Tid, 21 settembre 2026 (D7 del brief sulla partita di merce):
> **non un guard su `attivo`, ma la regola del documento — e come building
> block**, perché a DB la regola aveva già due copie parziali.

---

### ⭐ Le due copie che ha ritirato

* **`vendite.trgfn_contratti_righe_lock_post_attivazione`** (nata con
  `20260515-14`, droppata con `20260922-06`): la stessa regola scritta per i
  soli contratti, nella forma «righe bloccate quando il padre è `ATTIVO`». ⚠️
  Lasciava aperti `CESSATO` e `ANNULLATO`, dove il backend le negava da sempre:
  il BB legge la regola nel verso giusto — solo in `DRAFT` — e da oggi quei due
  stati sono chiusi anche a DB. Il codice `E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE`
  resta al lock **della testata** (`trgfn_contratti_lock_post_attivazione`),
  che non è una copia: le quattro colonne di pricing sono un'altra regola.
* **il ramo 1 di `vendite.trgfn_dlt_block_ordrig_ddtrig`** (dal `20260826-21`,
  tolto con `20260922-05`): «documento non più in bozza → rifiuto», scritto per
  la sola porta del `DELETE` di DDT e ordini. Con il BB in fascia `_a05_` quel
  ramo non sarebbe mai stato raggiunto: una seconda implementazione mai
  provata è la prima a divergere. Il traduttore dei legami a valle resta, e
  parla **dopo**.

---

### Gli adottanti, e una porta lasciata aperta di proposito

| Tabella | Trigger | Porte |
| --- | --- | --- |
| `vendite.ddt_righe` | `trg_ddt_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt` | INSERT, UPDATE, DELETE |
| `vendite.ordini_righe` | `trg_ordini_righe_a05_doc_righe_lock_fuori_bozza_dlt` | **solo DELETE** |
| `vendite.contratti_righe` | `trg_contratti_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt` | INSERT, UPDATE, DELETE |
| `vendite.offerte_commerciali_eccezioni` | `trg_offerte_commerciali_eccezioni_a05_doc_bozza_ins_upd_dlt` (dal 2026-10-04; stato bozza `BOZZA`, terzo argomento) | INSERT, UPDATE, DELETE |
| `vendite.contratti_righe_componenti` | `trg_contratti_righe_componenti_a05_doc_bozza_ins_upd_dlt` (dal 2026-10-05, livello `RIGA`) | INSERT, UPDATE, DELETE |
| `vendite.offerte_commerciali_eccezioni_componenti` | `trg_oce_comp_a05_doc_bozza_ins_upd_dlt` (dal 2026-10-05, livello `RIGA`, stato bozza `BOZZA`) | INSERT, UPDATE, DELETE |
| `vendite.resi_righe_rientri` | `trg_resi_righe_rientri_a05_doc_bozza_ins_upd_dlt` (dal 2026-10-05, livello `RIGA`) | INSERT, UPDATE, DELETE |

⚠️ **Sugli ordini `INSERT` e `UPDATE` restano aperti, ed è una decisione**
(Tid, 14 settembre, voce «la promessa di consegna dopo la conferma» in
`PROJECT_CONTEXT`): `data_consegna_confermata` si decide alla conferma e può
cambiare dopo, e il verbo che la governa non esiste ancora. Montare le tre
porte chiuderebbe quella colonna prima del verbo. Il pgTAP del BB pinna
questa apertura (test 14), così un allargamento futuro sarà deliberato: è un
`CREATE OR REPLACE TRIGGER`, non un guard nuovo.

I **preventivi** sono il candidato successivo (`_STATI_RIGHE_MODIFICABILI =
{DRAFT}` anche lì), ma non in questo giro: il flusso di approvazione prezzo
scrive `stato_approvazione_prezzo` sulle righe, e va censito prima di chiudere
la porta.

---

### ⚠️ Fascia `_a05_`, e non è stile

I `BEFORE ROW` girano in ordine alfabetico. Con `_a10_` il nome verrebbe
**dopo** `trg_ddt_righe_a10_block_ddt_dlt` e i `trg_*_block_deact_upd`, e
l'operatore leggerebbe *«c'è un fulfillment»* o *«ci sono figli»* prima di
*«il documento è emesso»* — un rimedio che non è il rimedio: toglierebbe il
fulfillment per sbattere un attimo dopo contro il muro vero.

**Prima l'immutabilità, poi la validità del valore nuovo.** Precedente:
`trg_emittenti_fiscali_a05_guard_codice_forma`.

---

### ⛔ Lo stato si legge da un lettore `SECURITY DEFINER`

Testate **e** righe hanno RLS (letto dal catalogo il 22 settembre: `ddt`,
`ddt_righe`, `ordini`, `ordini_righe`, `contratti`, `contratti_righe`). Un
guard invoker che leggesse la testata sotto policy non distinguerebbe *«la
testata non c'è»* da *«la testata non la vedo»*, e diventerebbe fail-open
proprio per chi sta fuori perimetro. Per questo lo stato arriva da
[`script.fn_get_stato_testata_documento`](/dbzero/script/funzioni/fn_get_stato_testata_documento),
che risponde sempre, e il verdetto è sul **valore**.

**Testata assente ⇒ il guard passa.** Sul `DELETE` è un cascade partito dalla
testata, e la regola di stato l'ha già applicata
`trgfn_doc_guard_delete_solo_bozza`; su `INSERT`/`UPDATE` parlerà la FK. Le
colonne `ddt_id`, `ordine_id`, `contratto_id` sono `NOT NULL` con FK: una riga
orfana non esiste, quindi «assente» non può voler dire altro.

Su `UPDATE`, se la riga cambia padre, si guardano **entrambe** le testate:
spostare una riga da un documento emesso a una bozza è comunque una modifica
del documento emesso.

---

### Codici errore

| Codice | Classe | Quando | Valori |
| --- | --- | --- | --- |
| `E_RIGA_DOC_NON_BOZZA` | `CONFLITTO_STATO` | il documento non è più in bozza | etichetta del documento, stato, verbo (`aggiungere` / `modificare` / `togliere`) |
| `E_DOC_RIGHE_LOCK_MONTAGGIO` | `TECNICO` | argomenti mancanti, colonna FK che la riga non ha, o un livello che non è `TESTATA` né `RIGA` | trigger, tabella, nota |
| `E_DOC_TIPO_NON_GESTITO` | `TECNICO` | tipo di documento sconosciuto al lettore (lo solleva il lettore) | il tipo ricevuto |

* La frase è **una per tre porte**, ed è il verbo a dire quale: *«DDT 0023456
  non è più in bozza (stato CONSEGNATO): le sue righe si possono modificare
  solo finché è in bozza»*. Generalizza `E_DELETE_RIGA_DOC_NON_BOZZA`, ritirato
  lo stesso giorno (`obsoleto_dal`, messaggio conservato per il diario).
* Nessuna chiave `campo` nel contesto: su un `CONFLITTO_STATO` non c'è nessun
  campo da accendere — è la situazione a non consentire l'operazione.

---

### Note operative

* **Le fixture pgTAP costruiscono il documento nel verso vero**: bozza, righe,
  poi la transizione. Un documento «che nasce fuori bozza» non può più ricevere
  righe — era una scorciatoia che saltava tutti i gate di emissione, ed è
  esattamente ciò che il BB chiude. Cinque file sono stati riscritti così il
  22 settembre; la ricetta è in `test-fn-partite-merce-chiusura-v1`
  (`fn_genera_ddt_da_ordine`, causale, indirizzo CON, transizioni contigue).
* Il rimedio, quando rifiuta, **non è insistere**: si agisce sul documento
  intero con il verbo che il suo stato ammette, o con un documento di rettifica.
* Presidio: `db/pgtap/vendite/test-trgfn-doc-righe-lock-fuori-bozza-v1.sql`
  (21 casi costruiti, fra cui la riga `ALLOCATA` disattivata — il caso da cui
  tutto è partito — e la precedenza sul fulfillment).

> 📎 changeSet `20260922-01 … -06`. Brief:
> `brief-db-partita-merce-per-documento` (D7, giro 5).

### 🔄 rev 2026-10-04 — l'offerta (brief-db-righe-esclusione-solo-non-si-vende, R5a)

Le righe dell'offerta si scrivono solo in `BOZZA`: prima lo diceva solo il
backend, e il push copia le righe dell'offerta nel contratto, che la regola ce
l'ha. Il nome del trigger porta il prefisso lungo della tabella
(`trg_offerte_commerciali_eccezioni_a05_…`) per parlare **prima** dei trigger
generati di quella tabella, che hanno lo stesso prefisso.

⚠️ **Conseguenza voluta (decisione di Tid, «lock pieno»):** dopo l'emissione
anche lo stato di approvazione di un prezzo resta com'è. Cambiarlo su un
componente ricalcola il prezzo della riga madre, e quell'aggiornamento è fuori
bozza. Una nuova richiesta di approvazione passa da una revisione, che nasce in
bozza.

### 🔄 rev 2026-10-05 — le tabelle *nipoti* (brief-db-righe-esclusione-solo-non-si-vende, §8.2 B3)

Alcune tabelle non stanno sotto la testata ma sotto una **riga**: i componenti
di una riga di kit (contratto e offerta), i rientri di una riga di reso. Per
loro la regola è la stessa — si toccano solo col documento in bozza — ma la
colonna che hanno punta alla riga. Col quarto argomento `'RIGA'` il building
block prima risale alla testata con
[`script.fn_get_testata_id_di_riga`](/dbzero/script/funzioni/fn_get_testata_id_di_riga)
(anche lui `SECURITY DEFINER`, per la stessa ragione), poi fa il controllo di
sempre. **Riga assente ⇒ passa**, come per la testata: è il figlio che se ne va
insieme alla riga cancellata, o una chiave esterna che parlerà. Nel contesto
dell'errore, per questi, c'è anche `riga_documento_id`.

* **I componenti di contratto e offerta** prima li proteggeva solo un effetto:
  cambiare un componente ricalcola il prezzo della riga madre, e
  quell'aggiornamento della madre incontrava il lock delle righe. Il rifiuto
  arrivava **dopo** i controlli del componente (spegnere un componente
  obbligatorio rispondeva «è obbligatorio», non «il documento è emesso») e
  dipendeva da un trigger nato per altro. Ora la regola sta sulla tabella del
  componente, in fascia `_a05_`.
* **I rientri del reso** avevano la regola scritta a mano dentro
  `vendite.trgfn_resi_righe_rientri_guard`: era la seconda copia della forma
  «nipote». È stata ritirata nello stesso giro, e quel guard tiene solo la
  coerenza del prelievo (fascia `_a10_`).
* **I prelievi della bolla no**: la loro regola, in `EMESSO` e `SPEDITO`,
  ammette il cambio della sola ubicazione d'arrivo. È un'altra regola, non una
  copia, e resta in `vendite.trgfn_ddt_righe_prelievi_guard`.

> 📎 changeSet `20261005-15 … -18`. Presidio:
> `db/pgtap/vendite/test-righe-gemelle-secondo-giro-v1.sql` (test 8-18, 23-26).
