## 📘 Documentazione Concettuale – Tabella `vendite.offerte_commerciali_eccezioni`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> • [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe)
> • [vendite.note_offerte_commerciali](/dbzero/vendite/tabelle/note_offerte_commerciali)
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)
> • [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura)

---

### 🎯 Scopo Principale

(rev 2026-05-24)

`vendite.offerte_commerciali_eccezioni` contiene le **eccezioni puntuali al listino**
proposte nell'offerta commerciale: ogni riga rappresenta una deviazione tipizzata
rispetto al listino di riferimento dell'offerta.

E' il **mirror fedele di `vendite.contratti_righe`**, con la sola differenza
intenzionale di `offerta_id` al posto di `contratto_id`.

> **Refactor 2026-06-01** (gate L3 sulle offerte): aggiunte
> `stato_approvazione_prezzo` e `pratica_approvazione_prezzo_id` (+ FK
> `fk_offerte_eccezioni_pratica_approvazione_prezzo` → `pratiche.pratiche`, indice
> parziale `ix_vendite_offerte_eccezioni_stato_approvazione`), prima escluse. Le
> eccezioni OVERRIDE/AGGIUNTA non composite hanno ora dove registrare lo stato L3,
> in piena simmetria con `contratti_righe`. Il flusso di approvazione prezzo si
> applica quindi anche all'offerta (guida §6/§11.3), e il push ne trasporta lo
> stato 1:1 sul contratto. Una guard riga generica
> [`script.trgfn_righe_guard_pending('offerta_id')`](/dbzero/script/funzioni/trgfn_righe_guard_pending)
> (trigger `trg_offerte_eccezioni_a10_guard_pending_upd`) congela i campi struttura
> mentre lo stato è `PENDING`.

La simmetria strutturale garantisce che `fn_push_offerta_a_contratto` sia una
copia 1:1 senza conversioni di colonne (§5.1 analisi).

---

### Tipi di eccezione

Ogni riga porta un campo `tipo_eccezione` (enum `vendite.tipo_eccezione_contratto`):

| Valore       | Significato                                          | `prezzo_unitario` |
| ------------ | ---------------------------------------------------- | ----------------- |
| `OVERRIDE`   | Prezzo personalizzato per articolo gia' nel listino  | NOT NULL          |
| `ESCLUSIONE` | Articolo del listino escluso per questo cliente      | NULL              |
| `AGGIUNTA`   | Articolo non presente nel listino, aggiunto          | NOT NULL          |

#### CHECK `chk_offerte_eccezioni_prezzo_per_tipo_eccezione`

```text
ESCLUSIONE  → prezzo_unitario IS NULL
OVERRIDE    → prezzo_unitario IS NOT NULL
AGGIUNTA    → prezzo_unitario IS NOT NULL
```

#### Vincoli di unicita parziale

| Indice                                         | Predicato                               | Semantica |
| ---------------------------------------------- | --------------------------------------- | --------- |
| `uq_offerte_eccezioni_one_eccezione_per_articolo` | `WHERE tipo_eccezione IN ('OVERRIDE','ESCLUSIONE')` | OVERRIDE e ESCLUSIONE sono mutualmente esclusivi per la stessa coppia `(offerta, articolo)` |
| `uq_offerte_eccezioni_one_aggiunta_per_articolo`  | `WHERE tipo_eccezione = 'AGGIUNTA'`    | Al piu' una AGGIUNTA per coppia `(offerta, articolo)` |

Gli stessi indici esistono su `contratti_righe` con gli stessi predicati, confermando
la simmetria strutturale.

---

### Tipo erogazione e fonte quantita attesa

Le colonne `tipo_erogazione` e `fonte_quantita_attesa` replicano la stessa semantica
di `contratti_righe`:

- `tipo_erogazione` — `CANONE | UNA_TANTUM | ORARIO | CONSUMO` (CHECK
  `chk_offerte_eccezioni_tipo_erog`).
- `fonte_quantita_attesa` — `FISSA | MANUALE | TIMESHEET | LETTURE` (le combinazioni di `config.erogazioni_fonti`; `DERIVATA_COMPONENTI` ritirata il 2026-10-21, e sul composito solo la `FISSA`: `brief-db-offerta-emissione-ed-erogazione` §I.1)
  (CHECK `chk_offerte_eccezioni_fonte_qta`), NOT NULL.
- CHECK `chk_offerte_eccezioni_coerenza_canone` — se `tipo_erogazione = 'CANONE'`,
  `generazione_canone` deve essere in `('INIZIO_PERIODO', 'FINE_PERIODO', 'PRORATA')`.
- CHECK `chk_offerte_eccezioni_coerenza_fonte_erogazione` — blocca le 7 combinazioni
  vietate tra `tipo_erogazione` e `fonte_quantita_attesa` (stessa matrice di `contratti_righe`).

Per la matrice completa e la semantica di ogni valore vedi la documentazione di
[`vendite.contratti_righe`](/dbzero/vendite/tabelle/contratti_righe).

> **Refactor 2026-05-31** (specularita'): l'offerta ha ora anche il default-fonte,
> trigger `trg_offerte_eccezioni_a10_default_fonte_qta_ins_upd` →
> `script.trgfn_righe_default_fonte_qta` (funzione **generica** condivisa con
> `contratti_righe`). Su INSERT imposta `fonte_quantita_attesa` dal `tipo_erogazione`
> se NULL (backstop al NOT NULL); su UPDATE la resetta se il cambio tipo rende la
> combinazione vietata. Esegue prima di `qta_from_operativa` (`_a10_d…` < `_a10_q…`).

---

### Quantita operative e unita di misura

> **Refactor 2026-05-31**: l'offerta ora **converte** come il contratto (prima aveva
> le colonne ma nessuna derivazione: `qta_operativa` restava NULL, `factor_to_base` 1).

- `uom_operativa_id` — FK → `catalogo.unita_misura(id)`. UoM operativa dichiarata in riga.
- `qta_operativa` — **SORGENTE**: quantita nella UoM operativa. Nullable solo per
  `fonte_quantita_attesa ≠ 'FISSA'` (quantita da sorgente esterna); per `FISSA` e'
  obbligatoria (altrimenti `E_QTA_MISSING`).
- `factor_to_base` — snapshot del fattore, **nullable**: se NULL il trigger lo deriva
  dal mapping `catalogo.articoli_uom_operativa` e lo salva. `numeric(18,6)` dal
  2026-10-05 (era `(18,8)`): la scala del fattore dell'articolo e della riga del
  contratto in cui il push lo copia.
- `quantita` — **DERIVATA** (UoM base): la calcola il trigger
  `trg_offerte_eccezioni_a10_qta_from_operativa_ins_upd` →
  `script.trgfn_qta_from_operativa('true','false','quantita','fonte_quantita_attesa')`
  (stessa configurazione di `contratti_righe`).
  ⭐ **Dal 2026-10-08 è calcolata per intero**: con una fonte a valle
  (`script.fn_fonte_porta_quantita` = false: MANUALE, LETTURE, TIMESHEET) il trigger la
  porta a NULL a ogni INSERT e UPDATE, e nessun client la scrive. Il rifiuto
  `E_RIGA_QUANTITA_CON_FONTE_A_VALLE` (guard `script.trgfn_righe_guard_quantita_per_fonte`)
  resta sull'input, `qta_operativa`. Rete: `chk_offerte_eccezioni_quantita_per_fonte`.
  Brief `brief-db-offerta-emissione-ed-erogazione` §F.1.
- Vincolo `chk_offerte_eccezioni_qta_operativa_nonzero` (`qta_operativa IS NULL OR
  qta_operativa <> 0`): negativi ammessi, zero vietato.

Avere `qta_operativa` valorizzata gia' a monte rende la copia 1:1 di
`fn_push_offerta_a_contratto` coerente: il trigger contratti ricalcola la stessa
`quantita`, senza `E_QTA_MISSING` (regressione smoke §8b chiusa).

---

### Relazione con l'offerta e ciclo di vita

- La riga e' **posseduta dall'offerta**: `ON DELETE CASCADE` su `offerta_id`. Se l'offerta
  viene eliminata (solo in BOZZA), le eccezioni scompaiono con essa.
- Le righe si aggiungono, modificano e tolgono solo finche' l'offerta e' in stato
  BOZZA: dal 2026-10-04 lo dice il trigger
  `trg_offerte_commerciali_eccezioni_a05_doc_bozza_ins_upd_dlt`, il building block
  [`trgfn_doc_righe_lock_fuori_bozza`](/dbzero/vendite/funzioni/trgfn_doc_righe_lock_fuori_bozza)
  dei contratti e dei DDT → `E_RIGA_DOC_NON_BOZZA`. Prima lo diceva solo il backend.
- Il campo `attivo` permette di disattivare una riga senza eliminarla; il trigger
  `dbops.trgfn_child_requires_active_parent` blocca la disattivazione dell'articolo
  padre se esiste almeno una riga eccezione attiva che vi fa riferimento.

---

### Una riga che si fattura dice come si eroga (2026-10-04)

Come sul contratto: ogni riga che non è `ESCLUSIONE` vuole `tipo_erogazione`.
Il trigger `trg_offerte_eccezioni_a10_guard_erogazione_obbligatoria_ins_upd`
(→ [`trgfn_righe_guard_erogazione_obbligatoria`](/dbzero/script/funzioni/trgfn_righe_guard_erogazione_obbligatoria))
rifiuta la riga che la lascia vuota → `E_RIGA_EROGAZIONE_OBBLIGATORIA`, col campo
`tipo_erogazione`; dietro c'è il vincolo
`chk_offerte_eccezioni_erogazione_per_tipo_eccezione`. La regola deve stare
anche qui perché `fn_push_offerta_a_contratto` copia l'erogazione nel
contratto: senza, un'offerta accettata farebbe nascere un contratto che il
contratto stesso rifiuta.

---

### Le stesse regole del contratto (2026-10-04)

`fn_push_offerta_a_contratto` copia le righe nel contratto 1:1, con la stessa
versione di listino. Ogni regola che il contratto ha e l'offerta no è
un'offerta che passa e un contratto rifiutato al push. Dal 2026-10-04 l'offerta
ha le stesse regole, con le stesse funzioni:

* **Un'esclusione è solo «non si vende»**: i dati di vendita restano vuoti
  (vincolo `chk_offerte_eccezioni_esclusione_senza_dati`, guard
  [`trgfn_righe_guard_esclusione_senza_dati`](/dbzero/script/funzioni/trgfn_righe_guard_esclusione_senza_dati)
  → `E_RIGA_ESCLUSIONE_CON_DATI`). `fonte_quantita_attesa` non è più `NOT NULL`:
  è obbligatoria solo sulle righe che non sono esclusioni. I trigger della fonte
  di default e della quantità saltano l'esclusione.
* **Un'esclusione non si modifica**: si crea e si cancella
  ([`trgfn_righe_guard_esclusione_immutabile`](/dbzero/script/funzioni/trgfn_righe_guard_esclusione_immutabile)
  → `E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE`).
* **Quali articoli ammette la riga** lo dice una check sola per tipo di riga,
  [script.fn_check_articolo_riga](/dbzero/script/manual/fn_check_articolo_riga), sollevata dal guard di tabella
  [script.trgfn_righe_guard_articolo_ammesso](/dbzero/script/manual/trgfn_righe_guard_articolo_ammesso) (2026-10-13, brief-db-articoli-ammessi-per-documento, Lotto 3b):
  un'**aggiunta** è un articolo fuori listino (`E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO`);
  un **prezzo diverso** (OVERRIDE) o un'**esclusione** si fanno solo su un articolo del
  listino del documento (`E_RIGA_ECCEZIONE_FUORI_LISTINO`, `E_RIGA_ECCEZIONE_SENZA_LISTINO`:
  prima si scrivevano anche fuori, e la riga non compariva); **si esclude il bundle, non il
  suo componente** (`E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA`); un articolo **solo
  componente** non sta in una riga autonoma, e uno **senza erogazioni** non sta in
  un'offerta. «Nel listino» vuol dire nella versione espansa, standalone e bundle.
* **Il tipo di una riga non si cambia**: lock di colonna su `tipo_eccezione`
  → `E_CONTRATTO_RIGA_TIPO_ECCEZIONE_IMMUTABILE`.

I codici portano «CONTRATTO» nel nome per storia; i messaggi non nominano il
documento, o lo nominano con la sua etichetta.

⭐ **I due rifiuti `_a05_` hanno il prefisso lungo del nome della tabella**
(`trg_offerte_commerciali_eccezioni_a05_…`): fra i trigger `BEFORE ROW` parla
per primo il nome minore, e i trigger generati da `ci_apply` su questa tabella
hanno quel prefisso. Con il prefisso corto dei trigger scritti a mano
(`trg_offerte_eccezioni_…`) «fuori bozza» parlerebbe dopo il lock di colonna.

La lista del drawer, coi verbi che il DB ammette, è
[`vendite.fn_offerta_righe_preview`](/dbzero/vendite/funzioni/fn_offerta_righe_preview).

---

### Gli stessi tipi della riga del contratto (2026-10-05)

Il push copia questa riga nel contratto 1:1, e il 2026-10-05 le due gemelle sono
state allineate colonna per colonna: il contratto ha preso le scale dell'offerta
sul prezzo e sui codici di erogazione, l'offerta quella dell'articolo sul
fattore di conversione. Lo presidia
`db/pgtap/vendite/test-righe-gemelle-secondo-giro-v1.sql` (test 1, 3). Brief:
`brief-db-righe-esclusione-solo-non-si-vende` §8.2 B2.

La **lista** di queste righe nel drawer dell'offerta è la lista configurabile
`vendite.offerta_righe` (106), gemella di `vendite.contratto_righe` (103), sulla
funzione `vendite.fn_offerta_righe_preview` (2026-10-05, §8.1 dello stesso brief).

### Note collegate

Le note testuali sulle singole eccezioni risiedono in `vendite.note_offerte_commerciali`
(partizione `'OFFERTA'` di `vendite.note`) con `target_tipo = 'RIGA'` e
`target_riga_id → offerte_commerciali_eccezioni(id)`.

---

{% include-markdown "signature-core.md" %}

---
