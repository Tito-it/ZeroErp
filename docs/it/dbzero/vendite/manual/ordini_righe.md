## 📘 Documentazione Concettuale – Tabella `vendite.ordini_righe`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.ordini](/dbzero/vendite/tabelle/ordini) — la testata
> * [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment) — che cosa della riga è stato spedito
> * [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe) — le righe di bolla che ne nascono
> * [config.stati_doc_ordini](/dbzero/config/tabelle/stati_doc_ordini) — gli stati dell'ordine
>
> Approfondimento viste:
>
> * [vendite.vw_ordini_righe_dettaglio](/dbzero/vendite/views/vw_ordini_righe_dettaglio) — la riga con i blocchi della data confermata
> * [vendite.vw_situazione_merce_ordine](/dbzero/vendite/views/vw_situazione_merce_ordine) — residuo e ritardo
>
> Approfondimento funzioni:
>
> * [script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) — il guard unico della provenienza
> * [script.trgfn_righe_natura_vendita](/dbzero/script/funzioni/trgfn_righe_natura_vendita) — la natura con cui la riga è venduta
> * [vendite.trgfn_doc_righe_lock_fuori_bozza](/dbzero/vendite/funzioni/trgfn_doc_righe_lock_fuori_bozza) — le righe solo in bozza
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

Le righe dell'**ordine cliente**, con la fotografia di descrizione, unità di misura e IVA presa alla scrittura, la provenienza dal documento da cui nascono e le date di consegna promesse.

Ogni riga ha **due rappresentazioni della quantità**: quella **operativa** (`qta_operativa` con `uom_operativa_id`), con cui si inserisce, e quella **base** (`quantita`), derivata, su cui si calcolano residui, confronti e reporting. `factor_to_base` conserva il fattore di conversione applicato alla riga.

---

### La quantità: si scrive l'operativa, si calcola la base

* **Chi comanda** è la coppia operativa: `quantita = qta_operativa × factor_to_base` (scala 6),
  calcolata dal trigger `script.trgfn_qta_from_operativa` a ogni inserimento e modifica.
  `factor_to_base` è la fotografia della regola di conversione valida in quel momento.
* **Co-presenza**: quantità operativa e sua unità sono o tutte e due vuote o tutte e due
  valorizzate (`chk_ordini_v_r_uom_qta_operativa_copres`), mai uno stato ibrido.
* **Aggiornamenti**: se cambia la quantità operativa o la sua unità, si ricalcolano `quantita` e
  `factor_to_base`. La quantità base non si scrive a mano.
* `quantita` è sempre positiva; `qta_operativa`, se c'è, pure. `prezzo_unitario` non è negativo:
  l'omaggio è una quantità positiva a prezzo zero. Lo sconto percentuale sta fra 0 e 100.
* Il numero di riga è unico nell'ordine.

---

### Da dove nasce la riga

La riga dichiara il documento da cui nasce con le colonne della
[provenienza universale](/guide/sorgente-polimorfa): il tipo (`sorgente_tipo_id`), la chiave del
documento in una sola fra `sorgente_id` e `sorgente_uid` (quella del `key_selector` del tipo), e la
riga di quel documento (`sorgente_riga`).

* dal **preventivo**: tipo `PREVENTIVO`, l'uid del preventivo e la sua riga. Il legame diretto
  `preventivo_riga_id` resta accanto, ed è **unico**: una riga di preventivo genera al più una riga
  d'ordine;
* dall'**offerta**: tipo `OFFERTA_COMMERCIALE`, l'uid dell'offerta e l'eccezione da cui viene la
  riga;
* una riga scritta a mano non ha provenienza: le colonne restano tutte vuote.

La forma la dice `chk_ordini_righe_sorgente_forma` (tutto vuoto, oppure il tipo con **una**
chiave); esistenza e coerenza di documento e riga le verifica, alla scrittura, il guard unico
(`trg_ordini_righe_a10_guard_sorgente_ins_upd`, livello minimo `DOCUMENTO`, `BLOCCA`). Gli indici
`(tipo, chiave)` e `(tipo, riga)` servono a chi cerca le righe nate da un documento: **non** sono
unici, perché un vincolo generico «una riga per sorgente» non esiste. L'unicità che il dominio
vuole è quella di `preventivo_riga_id`.

Quando si cancella una riga d'ordine, il lato «in uscita» della provenienza guarda le righe che la
dichiarano come origine (le righe di bolla) e applica la regola che ognuna ha dichiarato.

---

### Che cosa la ferma

* **Righe solo in bozza, sulla cancellazione** (`trg_ordini_righe_a05_doc_righe_lock_fuori_bozza_dlt`):
  su un ordine fuori da `DRAFT` nessuna riga si toglie (`E_RIGA_DOC_NON_BOZZA`). ⚠️ Inserimento e
  modifica restano **aperti di proposito**: `data_consegna_confermata` si decide alla conferma e
  può cambiare dopo, e il verbo che la governa non esiste ancora. Quando ci sarà, la porta si
  allarga rimontando il trigger.
* **Cancellazione con legami a valle** (`trg_ordini_righe_a10_block_dlt`): a rifiutare sono le FK
  (fulfillment, resi); il trigger traduce il rifiuto in una frase
  ([`trgfn_dlt_block_ordrig_ddtrig`](/dbzero/vendite/funzioni/trgfn_dlt_block_ordrig_ddtrig)).
* **Data confermata ferma su una riga spedita** (`trg_ordini_righe_a10_guard_data_consegna_spedita_upd`):
  la `data_consegna_confermata` di una riga già partita con una bolla uscita dalla bozza, anche
  per una parte, non cambia più (`E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA`). Il guard solleva il primo
  motivo di
  [`script.fn_check_ordine_riga_data_consegna_confermata`](/dbzero/script/funzioni/fn_check_ordine_riga_data_consegna_confermata),
  la stessa check della colonna `data_consegna_confermata_blocco` di
  [vw_ordini_righe_dettaglio](/dbzero/vendite/views/vw_ordini_righe_dettaglio).
* **Una riga-onere non porta date di consegna** (`trg_ordini_righe_a10_riga_onere_senza_date_consegna_ins_upd`):
  su una riga che non è merce (`script.fn_natura_e_merce` sulla natura congelata) le due date di
  consegna restano vuote (`E_RIGA_ONERE_DATA_CONSEGNA`): un onere non si spedisce. Il nome lo fa
  parlare dopo la natura e l'ammissione dell'articolo.

---

### La natura di vendita

`natura_vendita_id` (obbligatoria) è la natura con cui la riga è stata venduta. La scrive
[`script.trgfn_righe_natura_vendita`](/dbzero/script/funzioni/trgfn_righe_natura_vendita): quella
portata dal verbo che copia la riga (`fn_push_preventivo_a_ordine` porta quella della riga di
preventivo), altrimenti quella dell'articolo; si riscrive solo quando cambia l'articolo. A mano non
si cambia (`E_RIGA_NATURA_VENDITA_IMMUTABILE`, dal registro `dbops.automation_lock_columns`).

---

### Le date di consegna, sulla riga

Due date facoltative: **`data_consegna_richiesta_cliente`** — quando il cliente la vuole — e
**`data_consegna_confermata`** — quando **noi** ci impegniamo a darla. La differenza fra le due è
la promessa. Il suffisso `_cliente` segue la regola dei documenti: non marcato = nostro, marcato =
della controparte.

* **Sulla riga, non sulla testata**: una riga può essere pronta e un'altra no. La testata la
  espone come minimo delle righe attive ([vw_ordini_lista](/dbzero/vendite/views/vw_ordini_lista)).
* **Nessun vincolo fra le due**, né con la data del documento: si può confermare prima di quanto
  chiesto, e la retrodatazione è un caso d'uso.
* La richiesta arriva dal preventivo al push; la conferma si decide alla conferma dell'ordine.
* Con il residuo da spedire danno il **ritardo**
  ([vw_situazione_merce_ordine](/dbzero/vendite/views/vw_situazione_merce_ordine)).

---

### Con bolle, fulfillment e fatture

* Il **residuo** della riga si calcola sulla quantità base, per coerenza con il magazzino e con i
  confronti fra documenti.
* Nel **fulfillment** la guardia riga ↔ riga confronta l'articolo e, se c'è, l'unità di misura; la
  quantità evasa non supera il residuo dell'ordine.
* Lo stato della testata lo riallinea il trigger del fulfillment, non la riga.
* Le API accettano le due rappresentazioni della quantità con la priorità all'operativa; la stampa
  può mostrare l'unità operativa lasciando i calcoli in base.

---

### Note di migrazione

* 2026-06-03 — `chk_ordini_v_r_qta_pos` controlla la quantità (prima ripeteva per errore il
  controllo del prezzo) e nasce il `CHECK` di co-presenza della quantità operativa.
* 2026-09-13 — arrivano le due date di consegna (brief-db-modifiche-certe-ciclo-vendita-e-articolo §2).
* 2026-09-22 — le righe di un ordine fuori bozza non si cancellano più.
* 2026-10-11 — la data confermata si ferma sulla riga spedita (brief-db-date-consegna-righe-in-blocco).
* 2026-10-13 — arriva la natura di vendita (brief-db-articoli-ammessi-per-documento).
* 2026-11-03 — la riga-onere non porta date di consegna (brief-db-addebito-trasporto-ordine).
* 2026-11-06 — la provenienza passa al modello (tipo, chiave del documento, riga) col guard unico;
  l'indice unico di «idempotenza» su tipo e uid lascia il posto a indici non unici
  (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
