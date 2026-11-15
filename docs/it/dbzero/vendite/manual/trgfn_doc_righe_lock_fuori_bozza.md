## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_doc_righe_lock_fuori_bozza`

> **Ultimo aggiornamento**: 14 novembre 2026

> 👀 **Vedi anche**
>
> [script.fn_get_stato_testata_documento](/dbzero/script/funzioni/fn_get_stato_testata_documento) — il lettore `SECURITY DEFINER` da cui prende lo stato
> [script.fn_get_testata_id_di_riga](/dbzero/script/funzioni/fn_get_testata_id_di_riga) — il lettore `SECURITY DEFINER` riga → testata, per il livello RIGA (dal 2026-10-05)
> [vendite.trgfn_doc_guard_delete_solo_bozza](/dbzero/vendite/funzioni/trgfn_doc_guard_delete_solo_bozza) — la stessa regola, sulla testata
> [vendite.trgfn_dlt_block_ordrig_ddtrig](/dbzero/vendite/funzioni/trgfn_dlt_block_ordrig_ddtrig) — il traduttore dei legami a valle, che parla dopo
> [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe) · [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe) · [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe) · [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe) — gli adottanti
> [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato) — l'helper di fixture: nei pgTAP la testata nasce in bozza, prende le righe, poi cambia stato
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
con due argomenti obbligatori e quattro facoltativi.

| `TG_ARGV` | Cosa | Esempio |
| --- | --- | --- |
| `[0]` | tipo di documento, per il lettore di stato (`DDT`, `ORDINE`, `CONTRATTO`, `OFFERTA`, `RESO`, `PREVENTIVO`) | `'DDT'` |
| `[1]` | colonna della riga che porta l'id del padre | `'ddt_id'` |
| `[2]` (opz.) | stato «bozza»: **non si legge**. La bozza è lo stato iniziale del vocabolario del documento (vedi [script.fn_doc_lock_regola](/dbzero/script/manual/fn_doc_lock_regola)) | i montaggi di oggi scrivono `'BOZZA'` sull'offerta |
| `[3]` (opz., dal 2026-10-05) | **livello** del padre: `TESTATA` (default) se la colonna punta alla testata, `RIGA` se punta a una riga del documento (tabelle *nipoti*) | `'RIGA'` per i componenti |
| `[4]` (opz., dal 2026-10-08) | le **colonne che un UPDATE può cambiare fuori bozza**, separate da virgola | `'data_consegna_confermata'` per l'ordine |
| `[5]` (opz., dal 2026-10-08; obbligatorio con `[4]`) | gli **stati** (`codice_interno`, separati da virgola) in cui le colonne `[4]` si cambiano | `'CONFERMATO,PARZIALMENTE_EVASO'` |

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
  restava al lock **della testata** (`trgfn_contratti_lock_post_attivazione`),
  che non era una copia: le quattro colonne di pricing sono un'altra regola. Dal
  2026-10-10 quel lock è ritirato anche lui: le quattro colonne le ferma il
  gemello di testata `trgfn_doc_testata_lock_fuori_bozza`.
* **il ramo 1 di `vendite.trgfn_dlt_block_ordrig_ddtrig`** (dal `20260826-21`,
  tolto con `20260922-05`): «documento non più in bozza → rifiuto», scritto per
  la sola porta del `DELETE` di DDT e ordini. Con il BB in fascia `_a05_` quel
  ramo non sarebbe mai stato raggiunto: una seconda implementazione mai
  provata è la prima a divergere. Il traduttore dei legami a valle resta, e
  parla **dopo**.

---

### Gli adottanti, e le colonne che restano aperte

| Tabella | Trigger | Porte |
| --- | --- | --- |
| `vendite.ddt_righe` | `trg_ddt_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt` | INSERT, UPDATE, DELETE |
| `vendite.ordini_righe` | `trg_ordini_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt` (tre porte dal 2026-10-08; prima solo DELETE) | INSERT, UPDATE, DELETE — **aperta la sola `data_consegna_confermata` in `CONFERMATO` e `PARZIALMENTE_EVASO`** |
| `vendite.preventivi_righe` | `trg_preventivi_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt` (dal 2026-10-08, tipo `PREVENTIVO`) | INSERT, UPDATE, DELETE |
| `vendite.contratti_righe` | `trg_contratti_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt` | INSERT, UPDATE, DELETE |
| `vendite.offerte_commerciali_eccezioni` | `trg_offerte_commerciali_eccezioni_a05_doc_bozza_ins_upd_dlt` (dal 2026-10-04; stato bozza `BOZZA`, terzo argomento) | INSERT, UPDATE, DELETE |
| `vendite.contratti_righe_componenti` | `trg_contratti_righe_componenti_a05_doc_bozza_ins_upd_dlt` (dal 2026-10-05, livello `RIGA`) | INSERT, UPDATE, DELETE |
| `vendite.offerte_commerciali_eccezioni_componenti` | `trg_oce_comp_a05_doc_bozza_ins_upd_dlt` (dal 2026-10-05, livello `RIGA`, stato bozza `BOZZA`) | INSERT, UPDATE, DELETE |
| `vendite.resi_righe_rientri` | `trg_resi_righe_rientri_a05_doc_bozza_ins_upd_dlt` (dal 2026-10-05, livello `RIGA`) | INSERT, UPDATE, DELETE |
| `vendite.preventivi_righe_componenti` | `trg_preventivi_righe_componenti_a05_doc_bozza_ins_upd_dlt` (dal 2026-10-08, livello `RIGA`, tipo `PREVENTIVO`) | INSERT, UPDATE, DELETE |
| `vendite.ordini_righe_componenti` | `trg_ordini_righe_componenti_a05_doc_bozza_ins_upd_dlt` (dal 2026-10-08, livello `RIGA`) | INSERT, UPDATE, DELETE |
| `vendite.ddt_righe_componenti` | `trg_ddt_righe_componenti_a05_doc_bozza_ins_upd_dlt` (dal 2026-10-08, livello `RIGA`) | INSERT, UPDATE, DELETE |
| `vendite.ddt_righe_prelievi` | `trg_ddt_righe_prelievi_a05_doc_bozza_ins_upd_dlt` (dal 2026-10-08, livello `RIGA`) | INSERT, UPDATE, DELETE — **aperta la sola `ubicazione_arrivo_id` in `EMESSO` e `SPEDITO`** |

⭐ **Le colonne che il dominio cambia dopo** (dal 2026-10-08, D-1 di Tid in
`brief-db-righe-e-componenti-debiti-residui`). Fino a quel giorno le righe
d'ordine avevano il lock sul solo `DELETE`, perché `data_consegna_confermata` si
decide alla conferma e può cambiare dopo: per lasciare aperta una colonna
restavano aperte tutte, e a DB si cambiava la quantità di un ordine confermato.
Ora le porte sono tre, e il montaggio dichiara l'eccezione con gli argomenti
`[4]` e `[5]`: un `UPDATE` con il documento in uno degli stati `[5]` passa se,
tolte le colonne `[4]` e quelle tecniche (`data_update`, `user_update`,
`tx_id`), la riga è identica a com'era. È un elenco di colonne **ammesse**, non
di colonne vietate: una colonna nuova nasce chiusa. `INSERT` e `DELETE` non hanno
eccezioni. Colonne senza stati, o una colonna che la riga non ha, sono un errore
di montaggio (`E_DOC_RIGHE_LOCK_MONTAGGIO`).

Gli stati dell'eccezione si dicono per `codice_interno`: un flag di
catalogo che dica «da evadere» non c'è (`fase = IN_CORSO` comprende anche
`SPEDITO` e `CONSEGNATO`).

I **preventivi** hanno le tre porte chiuse senza eccezioni: le marche di
approvazione prezzo si scrivono in bozza, perché un prezzo in attesa o rifiutato
su una riga attiva ferma l'uscita dalla bozza.

#### La terza copia ritirata: i prelievi della bolla

La forma «fuori bozza tutto chiuso, salvo queste colonne in questi stati»
esisteva già, scritta a mano, in
[`vendite.trgfn_ddt_righe_prelievi_guard`](/dbzero/vendite/funzioni/trgfn_ddt_righe_prelievi_guard):
in `EMESSO` e `SPEDITO` si compila la sola ubicazione d'arrivo. Il 2026-10-05 era
rimasta fuori, «un'altra regola, non una copia», perché il building block non
sapeva dire l'eccezione. Con le righe d'ordine la stessa forma è comparsa la
seconda volta: il building block l'ha imparata, e la copia dei prelievi si è
ritirata nello stesso giro (`20261008-92`, `-93`). La regola del kit resta nel
guard dei prelievi.

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
| `E_DOC_RIGHE_LOCK_MONTAGGIO` | `TECNICO` | argomenti mancanti, colonna FK che la riga non ha, un livello che non è `TESTATA` né `RIGA`, colonne ammesse senza stati (o il contrario), una colonna ammessa che la riga non ha | trigger, tabella, nota |
| `E_DOC_TIPO_NON_GESTITO` | `TECNICO` | tipo di documento sconosciuto al lettore (lo solleva il lettore) | il tipo ricevuto |

* La frase è **una per tre porte**, ed è il verbo a dire quale: *«DDT 0023456
  non è più in bozza (stato CONSEGNATO): le sue righe si possono modificare
  solo finché è in bozza»*. Generalizza `E_DELETE_RIGA_DOC_NON_BOZZA`, ritirato
  lo stesso giorno (`obsoleto_dal`, messaggio conservato per il diario).
* Nessuna chiave `campo` nel contesto: su un `CONFLITTO_STATO` non c'è nessun
  campo da accendere — è la situazione a non consentire l'operazione.
* Con le colonne ammesse (`[4]`/`[5]`) nel contesto entrano anche
  `colonne_ammesse` e `stati_ammessi`, per chi diagnostica.

---

### Note operative

* **Le fixture pgTAP costruiscono il documento nel verso vero**: bozza, righe,
  poi la transizione. Un documento «che nasce fuori bozza» non può più ricevere
  righe — era una scorciatoia che saltava tutti i gate di emissione, ed è
  esattamente ciò che il BB chiude. Cinque file sono stati riscritti così il
  22 settembre; la ricetta è in `test-fn-partite-merce-chiusura-v1`
  (`fn_genera_ddt_da_ordine`, causale, indirizzo CON, transizioni contigue).
  Dal 2026-10-08 vale anche per ordini e preventivi, e la transizione la fa
  [`dbops.fn_pgtap_porta_a_stato`](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato):
  circa cinquanta file sono stati riscritti così.
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
  ammette il cambio della sola ubicazione d'arrivo, e il building block non
  sapeva ancora dirlo. ⚠️ Superato il 2026-10-08: con le colonne ammesse la
  forma è la stessa, e i prelievi hanno adottato il building block (sopra, «La
  terza copia ritirata»).

> 📎 changeSet `20261005-15 … -18`. Presidio:
> `db/pgtap/vendite/test-righe-gemelle-secondo-giro-v1.sql` (test 8-18, 23-26).

### 🔄 rev 2026-10-08 — le colonne che restano aperte (brief-db-righe-e-componenti-debiti-residui, D-1)

Due argomenti facoltativi in coda, `[4]` e `[5]`: le colonne che un `UPDATE` può
cambiare fuori bozza e gli stati in cui lo può fare (sopra, «Le colonne che il
dominio cambia dopo»). Le righe d'ordine passano alle tre porte con aperta la sola
data di consegna confermata negli stati da evadere, le righe del preventivo alle
tre porte senza eccezioni, i prelievi della bolla adottano il building block e
ritirano la loro copia.

> 📎 changeSet `20261008-89 … -94`. Presidio:
> `db/pgtap/vendite/test-righe-e-componenti-debiti-residui-v1.sql` (test 4-20) e
> `test-trgfn-doc-righe-lock-fuori-bozza-v1.sql` (test 2, 14).

### 🔄 rev 2026-10-10 — gli argomenti e la decisione in una sede condivisa (brief-db-testata-dopo-emissione, fase 1)

Le colonne che restano aperte fuori bozza servono anche a chi accende i pulsanti: la
capability della promessa di consegna deve sapere **in quali stati** la data si cambia, e
deve saperlo dagli argomenti di questo trigger, non da una sua lista. Per questo il trigger
non interpreta più gli argomenti da sé:

* la **grammatica** (quale argomento è cosa, i default, le liste) sta in
  [`script.fn_doc_lock_regola`](/dbzero/script/funzioni/fn_doc_lock_regola);
* la **decisione** (in bozza tutto; fuori, solo le colonne ammesse negli stati ammessi)
  sta in [`script.fn_doc_lock_colonna_bloccata`](/dbzero/script/funzioni/fn_doc_lock_colonna_bloccata).

Le stesse due le usa il lettore del montaggio,
[`script.fn_doc_lock_montaggi`](/dbzero/script/funzioni/fn_doc_lock_montaggi): trigger e
capability leggono lo stesso montaggio e decidono con la stessa funzione.

Per gli adottanti non cambia niente: stessi codici, stesse frasi, stesso contesto.
L'eccezione è la stessa detta per colonna: ogni colonna che cambia deve essere ammessa, o
fra quelle che scrive l'audit. Unica stretta: una lista di sole virgole accanto a una piena
è ora un montaggio a metà.

> 📎 changeSet `20261010-60 … -64`. Presidio:
> `db/pgtap/script/test-doc-lock-montaggio-v1.sql`.

### 🔄 rev 2026-10-11 — i satelliti del documento (brief-db-testata-dopo-emissione §11, R-DB-3 e D-12)

Il building block si monta anche sui **satelliti** del documento: gli indirizzi di DDT,
ordine, preventivo, offerta e contratto (`vendite.*_indirizzi`) e la fornitura 1:1 di offerta
e contratto (`vendite.offerte_commerciali_utilities`, `vendite.contratti_utilities`). Si
scrivono solo in bozza, come diceva il solo backend.

Per questi il montaggio passa un settimo argomento, il codice: rifiutano con
`E_DOC_DATI_COLLEGATI_NON_BOZZA`, la cui frase parla di indirizzi e fornitura. Gli adottanti
di prima non lo passano e restano su `E_RIGA_DOC_NON_BOZZA`.

Le capability leggono lo stesso montaggio con `script.fn_doc_riga_modificabile`
(`can_edit_indirizzi`, `can_edit_utility`).

### 🔄 rev 2026-10-11 — la nascita (brief-db-testata-dopo-emissione §11.6, D-13)

Un documento può nascere già fuori bozza: un seed o un import inserisce un contratto
direttamente ATTIVO. Quello che un **trigger** scrive in quel momento fa parte della nascita
e passa: è lo snapshot della fornitura, che `trgfn_contratti_snapshot_precontrattuali` scrive
dopo l'inserimento del contratto. Il lock lo riconosce da due cose insieme: la scrittura la
fa un altro trigger, e la testata è nata nella transazione corrente (`nata_in_transazione` di
`script.fn_get_stato_testata_documento`).

Una scrittura **diretta** resta rifiutata fuori bozza, anche nella transazione che ha creato
il documento. Per questo i pgTAP dei lock, che girano in una transazione sola, vedono ancora
il rifiuto.
