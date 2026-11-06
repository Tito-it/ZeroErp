# Brief DB — La sorgente polimorfa: un documento, una riga, una grammatica sola

## ⏭️ Chi riparte — aggiornato al 2026-11-06

**Riparte: team DB**, col censimento di dettaglio e il piano a lotti (§7). Lo sviluppo parte solo col via di Tid.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ Tid | il modello: tipo + chiave del documento (`sorgente_id` o `sorgente_uid`) + `sorgente_riga` = la riga (2026-11-06) | §4 | — |
| 2 | ✅ DB | storia, censimento delle forme, dei dati e dei lettori (dbdev, 2026-11-06) | §2, §3 | — |
| 3 | ✅ Tid | S-1 … S-7, tutte decise (2026-11-06) | §6.1 | — |
| 3-bis | ✅ Tid | analisi critica: S-8, S-9 decise; S-10 da analizzare; S-7 precisata (2026-11-06) | §6.2, §7.1 | — |
| 4 | DB (in corso) | censimento di dettaglio, tabella per tabella, sul perimetro del §3.1; analisi S-10 e S-7; piano a lotti | §7, Appendice | — |
| 5 | Tid | S-10, eventuali eccezioni a S-8 che il censimento segnala, via allo sviluppo del lotto 0 | §6.2, §7 | 4 |

**Decisioni aperte di Tid:** S-10 (§6.2), e le eventuali eccezioni a S-8 che il censimento segnalerà. Lavoro
da committare: nessuno di questo brief (solo il documento).

**Fermo collegato:** il lotto B di `brief-db-articoli-obsoleto-dal` (verbi che scrivono la sorgente,
`20261105-15…-19`) **non si applica** finché questo modello non è deciso: i verbi si riscrivono una volta sola. Il
§9 di quel brief (indici «idempotenza import», commenti, import esterno su tabella di collegamento) confluisce qui.
Il lotto A dello stesso brief è applicato e resta: legge solo «la sorgente c'è o no».

> **Chi scrive:** team DB (`dev/db-tid`), 2026-11-06. **A chi:** Tid, poi il team DB, poi BE/FE.
> **Origine:** Tid, 2026-11-06, sui verbi dell'offerta: *«abbiamo usato male la chiave: sorgente_riga è la riga del
> documento, il fatto che ora su sorgente_riga si metta la testata è errato; dovrebbero esistere sorgente_uid,
> sorgente_id e sorgente_riga»*; *«sorgente_uid e sorgente_id servivano per distinguere le tabelle che hanno chiave
> uid da id»*; *«va verificato dove si è propagato il problema, come viene letta la sorgente polimorfa. Dare una
> dimensione al buco»*.
> **Brief vicini verificati:** `work-done/brief-db-guard-sorgente-polimorfa` (2026-07-18: modello A e B, D1 «la colonna
> `sorgente_riga` ha due scopi», D4 rinviata), `work-done/brief-db-bonifica-pgtap-sorgente-polimorfa`,
> `work-done/brief-db-commesse-multi-sorgente`, `work-in-progress/analisi-db-magazzino-aggancio-documento-e-produzione`
> (D-1…D-3: il magazzino sul modello A; D-2 lascia aperti gli indici unici vecchi),
> `work-done/brief-db-grammatica-unica-documenti` (K-1 del 2026-10-19: la chiave id/uid di un tipo non si unifica;
> `fn_segment_key`, il costruttore unico della chiave d'idempotenza del push). Nessun brief aperto sul tema.
> **Ambito:** trasversale: vendite, acquisti, magazzino, pratiche, documenti. È un cambio di modello: si decide prima,
> si misura il dettaglio dopo.

---

## 1. Il buco in una frase

Lo **stesso concetto**, «questo record nasce da quel documento (e da quella sua riga)», è scritto oggi in **sette
grammatiche diverse** nelle stesse colonne `sorgente_*`. Ogni lettore deve sapere quale grammatica ha la tabella che
sta leggendo; se sbaglia, la query torna **zero righe in silenzio**.

## 2. La storia (fatti, con le date)

1. **2025-09-06** — `vendite.ordini` nasce con `source_tipo_id` + `source_id uuid`, «Origine import (**id
   esterno**)», più un indice unico «idempotenza import». Sulle righe (ordini, fatture, attività) c'è anche
   `source_riga`: «Progressivo/ID **riga nella sorgente**». Lo schema originale è quello di Tid: il documento + la sua
   riga.
2. **2025-10-05** — rinomino `source_*` → `sorgente_*` (`20251005-01…-06`, più le testate di magazzino
   `-23`/`-24`). Le colonne si ricreano uguali, indice compreso.
3. **2026-02-09** — `20260209-01`, il primo guard polimorfo, **rilegge** le colonne: `sorgente_riga` è la chiave
   quando `key_selector = 'id'`, `sorgente_uid` quando è `'uid'`, in alternativa. Una testata a chiave `id` finisce
   così in `sorgente_riga`. Per riferire una riga nascono i tipi `*_RIGA` in `config.sorgenti`.
4. **2026-07-18** — `brief-db-guard-sorgente-polimorfa` dà un nome alle due letture: **modello A** (colonne
   alternative) e **modello B** (tabelle di collegamento: chiave testuale del documento + `sorgente_riga` = la riga, cioè
   il modello di Tid). D1 di Tid: `sorgente_riga` si tiene, «doppio scopo documentato». D4 (verificare che la riga
   esista) rinviata: `config.sorgenti` conosce la tabella del documento, non quella delle righe.
5. **2026-07-09** — `20260709-01` toglie l'indice unico su `vendite.ddt`, che vietava più bolle per ordine. Solo lì.
6. **2026-09-15** — il magazzino (Lotto 1) adotta il modello A su sei tabelle.
7. **2026-11-05** — il lotto A di `brief-db-articoli-obsoleto-dal` lo adotta sulle righe di vendita e d'acquisto.
8. **2026-11-06** — la «testata + progressivo» decisa per l'offerta non ci sta nel modello A (vuole una sola delle due
   colonne): è il modello di Tid che riemerge.

## 3. La dimensione (dbdev, 2026-11-06: fatto datato, non motivo)

### 3.1 Le sette grammatiche

29 tabelle hanno `sorgente_tipo_id`. Per i tipi a chiave `id` scrivono:

| # | Grammatica | Tabelle | Cosa c'è per un tipo a chiave `id` |
| --- | --- | --- | --- |
| G1 | testata, solo `sorgente_uid uuid` | `vendite.ordini`, `ddt`, `fatture`, `contratti`, `resi`; `acquisti.ordini`, `acquisti.ddt` | l'**uid** del documento, contro il `key_selector`. Non hanno `sorgente_riga` |
| G2 | modello A: `sorgente_riga` **oppure** `sorgente_uid` | `magazzino.movimenti`, `movimenti_attesi`, le quattro testate; le righe del lotto A (`preventivi_righe`, `ordini_righe`, `ddt_righe`, `contratti_righe`, `acquisti.ddt_righe`) | l'**id** in `sorgente_riga`, del documento o della riga secondo il tipo |
| G3 | modello B: `sorgente_uid text` canonico + `sorgente_riga` = riga | `pratiche.pratiche_sorgenti`, `vendite.commesse_sorgenti` | `id::text` del documento; la riga a parte |
| G4 | `sorgente_uid text` = sempre l'uid | `vendite.commesse_attivita`, `vendite.documenti_fatturazione_canali` | l'**uid** come testo, contro il `key_selector` |
| G5 | tipo COMMESSA + `sorgente_riga` = riga della commessa | `vendite.attivita_fatturabili`, `vendite.fatture_righe` | `sorgente_riga` = `commesse_attivita.id` (64/64, 8/8); `sorgente_uid` = un hash, non la commessa |
| G6 | mista nella stessa tabella | `documenti.documenti_generati` | l'uid per CONTRATTO, DDT, ORDINE; l'id per FATTURA |
| G7 | `sorgente_id bigint` + `sorgente_uid text` | `vendite.fatture_stampa_coda` | l'id, scritto due volte |

Più `pratiche.reconcile_errori` (testo, senza FK) e `documenti.template_documenti` (solo il tipo, non è una
provenienza).

#### 3.1-bis Che cosa mancava al conteggio (analisi critica, 2026-11-06)

Tre tabelle con `sorgente_*` non comparivano nella tabella sopra:

| Tabella | Che cosa ha | Grammatica |
| --- | --- | --- |
| `acquisti.ordini_righe` | `sorgente_tipo_id`, `sorgente_uid uuid` «Origine import», `sorgente_riga DEFAULT 0`; indice unico `uq_ordini_righe_v_sorgente_fk (tipo, uid)`; **nessun guard** | G1 di riga (import) |
| `magazzino.eventi_assets` | modello A con CHECK «esattamente una chiave»; guard tipizzato. L'evento è a sua volta il **bersaglio** del tipo `EVENTO_ASSET` (sorgente del movimento) | G2; il tipo `EVENTO_ASSET` è S-10 |
| `vendite.attivita_fatturabili.sorgente_origine_tipo_id` | una **quarta** colonna: il tipo del documento d'origine (copiato da `commesse_attivita.sorgente_tipo_id` da `fn_emit_…`), **senza chiave** | provenienza a metà, in G5 |

**G1 non è una grammatica sola.** Le stesse colonne, sulle testate, dicono cose diverse (lo scrivono i manuali
delle tabelle):

| Tabella | Che cosa vuol dire oggi `sorgente_tipo_id + sorgente_uid` | Fonte |
| --- | --- | --- |
| `vendite.ordini`, `vendite.fatture`, `acquisti.ordini`, `acquisti.ddt`, le righe d'ordine | **import da un sistema esterno** (idempotenza CRM), «distinto da `documento_origine_*`» | manuali `ordini` §idempotenza, `fatture` §idempotenza; commenti di colonna «Origine import (uid)» |
| `vendite.ddt`, `vendite.resi` | il **documento padre** (l'ordine, la bolla), per uid | manuali `ddt`, `resi` |
| `vendite.contratti` | l'offerta, **scritta due volte**: `fn_push_offerta_a_contratto` valorizza `sorgente_*` **e** `offerta_id` | corpo della funzione |

Col §4 l'import esce da queste colonne (tabella di collegamento propria): sulle testate dove oggi vogliono dire
«import», `sorgente_*` **cambia significato** e diventa la provenienza. Gli indici «idempotenza import» si ritirano
con l'import, non prima.

**Lo stesso concetto vive anche fuori da `sorgente_*`** (G8, le colonne parallele):

| Dove | Che cosa | Regola di dominio che porta |
| --- | --- | --- |
| `vendite.ordini.documento_origine_tipo` (codice di `config.sorgenti`) + `documento_origine_id bigint` | la provenienza da preventivo o offerta, **per id** anche per il preventivo, che nel catalogo ha chiave `uid` | `uq_ordini_v_documento_origine_offerta` (un ordine vivo per offerta) |
| `vendite.contratti.offerta_id` (FK) | l'offerta del contratto | `uq_contratti_offerta_id` (un contratto vivo per offerta) |
| `vendite.ordini_righe_fulfillment` | riga di bolla ↔ riga d'ordine | la quantità evasa; il commento di `ddt_righe.sorgente_tipo_id` dice che il verbo scrive **prima** la sorgente e **poi** il legame: lo stesso fatto due volte |

Sono il caso di S-8 (§6.2).

**Esempio** (numeri di fantasia, comportamento del codice). Ordine `id 163`, `uid 0192ab…`, riga `5001`; ne nasce la
bolla 77 con il prelievo 12. Oggi «viene dall'ordine 163» si legge così: `commesse_sorgenti.sorgente_uid = '163'`;
`commesse_attivita.sorgente_uid = '0192ab…'`; `ddt.sorgente_uid = 0192ab…` (uuid); `ddt_righe`: tipo
ORDINE_VENDITA_RIGA, `sorgente_riga = 5001`, più la riga di fulfillment; `magazzino.movimenti`: tipo
DDT_VENDITA_PRELIEVO, `sorgente_riga = 12`. Sei `WHERE` diversi; uno sbagliato torna zero righe. Col §4: ovunque
tipo ORDINE_VENDITA, `sorgente_id = 163`, `sorgente_riga` = 5001 o NULL.

### 3.2 I dati

* **~6.860 righe** hanno una sorgente scritta.
* **~2.850** hanno l'uid dove il `key_selector` dice `id`:
  * `documenti_fatturazione_canali` 1.385;
  * `documenti_generati` 648;
  * `commesse_attivita` 515;
  * `ddt` 216;
  * `resi` 88.

  Oggi sono **coerenti con la grammatica della loro tabella**, ma non con `config.sorgenti`.
* **387 orfani** in `documenti_fatturazione_canali`: la sorgente punta a un documento che non esiste più.
  * PREVENTIVO 352, CONTRATTO 14, DDT 16, ORDINE 5;
  * letti come owner: la RLS di quelle tabelle non è forzata, quindi non nasconde righe;
  * nessuna FK e nessun guard lo impediscono: è la tabella G4 senza guard.
* Il **modello di Tid è già vivo in tre posti**, con tre forme: G3 (testo), G5 (tipo COMMESSA + riga) e la «testata +
  progressivo» dell'offerta.

### 3.3 I lettori

| Dove | Quanti |
| --- | --- |
| funzioni DB che nominano le colonne | 92 (vendite 54, script 16, dbops 7, magazzino 6, documenti 5, pratiche 4) |
| viste | 26 (vendite 15, dbops 5, script 3, documenti 3) |
| di cui scrivono la sorgente | 19 |
| leggono `key_selector` | 16 |
| usano i BB `script.fn_sorgente_chiave_id/_uuid` | 8 |
| BE: file Python (test compresi) | 79 |
| FE: file | 10 |
| pgTAP: file | 165 |

**I BB del meccanismo** (da tenere allineati):

* i guard `script.trgfn_guard_sorgente_polimorfa_tipizzata` e `_testuale`;
* `script.fn_sorgente_chiave_id/_uuid`;
* `vendite.fn_get_sorgente_documento_ref`;
* `vendite.fn_link_commessa_sorgente`;
* `pratiche.fn_stato_sorgente`;
* `script.vw_stato_sorgente` con i sei rami `vendite.vw_stato_sorgente_*`;
* `script.vw_pratica_doc_sorgente`;
* `script.fn_check_sorgente_chiudibile`;
* `script.fn_get_sorgente_emittente_sr_id`;
* `vendite.fn_commessa_viva_di_sorgente`;
* `vendite.fn_ritira_commessa_attivita_da_sorgente`;
* `magazzino.fn_storna_movimenti_sorgente`;
* **il presidio degli orfani** `dbops.fn_sorgenti_orfane` + `fn_sorgenti_orfane_perimetro` (vista
  `dbops.vw_sorgenti_orfane`). Legge `sorgente_riga` come chiave del documento, e il suo perimetro pretende
  **entrambe** le colonne di chiave: `documenti_fatturazione_canali` (solo `sorgente_uid`) ne è fuori, ed è per
  questo che i 387 orfani del §3.2 non li segnalava.

Più chi nomina i **codici** dei tipi `*_RIGA` (S-2): `config.tipi_entita` (FK `fk_tipi_entita_sorgenti`,
`is_sorgente = true` sulle 11 righe `*_RIGA` e sui due livelli sotto la riga, G-1 del 2026-10-19), lo scope delle
note (`script.fn_scope_note_ef_perimetro`, `fn_scope_note_magazzino_ef_perimetro`), il BE
(`apps/config/sorgenti.py`, `apps/magazzino/db/famiglie.py`).

### 3.4 Che cosa costa già oggi

* **La lineage traduce a mano.** `vendite.fn_documento_lineage_legami` cerca le righe di commessa con un `CASE` per
  tipo, che rilegge l'uid del documento da preventivi, ordini, contratti e ddt, perché `commesse_attivita` (G4)
  scrive l'uid dove `commesse_sorgenti` (G3) scrive l'id. Ogni tipo nuovo va aggiunto lì a mano. Il
  `brief-db-guard-sorgente-polimorfa` §1d l'aveva già segnato: stesse colonne, stesso push, valori diversi.
* **Gli indici unici «idempotenza import»** (sette documenti) bloccano la derivazione: due righe da un'offerta, un
  secondo ordine dopo un annullo. Sulle testate di magazzino coprono solo la chiave `uid`, quindi non controllano
  niente.
* **Le testate G1 non possono scrivere la chiave giusta**: non hanno né `sorgente_riga` né `sorgente_id`.
* **Il guard tipizzato non può verificare la riga**: legge una sola chiave (D4 rinviata a luglio).
* **Gli orfani** del §3.2.
* **`sorgente_riga DEFAULT 0`** su `vendite.ordini_righe`, `acquisti.ordini_righe`, `vendite.fatture_righe`,
  `vendite.attivita_fatturabili` («0 se non applicabile»): nel modello lo 0 è una riga che non esiste; il
  documento intero è NULL.
* **Gli indici unici da riclassificare sono più dei sette di testata**: anche quelli di riga
  (`uq_*_righe_v_sorgente_fk (tipo, uid)` su ordini_righe di vendita e d'acquisto e su fatture_righe) e quelli
  delle testate di magazzino. Le regole di dominio vive che stanno su una sorgente: `uq_doc_fatt_canali_un_aperto`,
  `uq_documenti_generati_sorgente_progressivo`, `uq_ordini_v_documento_origine_offerta`, `uq_contratti_offerta_id`,
  `uq_pratiche_sorgenti_pratica_tipo_uid_ruolo`, `uq_commesse_sorgenti_src_uid_commessa` e
  **`uq_mag_movimenti_identita`**, l'idempotenza delle registrazioni di magazzino: con S-3 la sua chiave cambia
  (tipo + documento + riga + dettaglio) e deve restare **equivalente**, o si registra due volte.
* **Il guard non controlla l'esclusività**: niente impedisce di valorizzare entrambe le chiavi (solo
  `eventi_assets` ha un CHECK).

### 3.5 Che cosa revoca (dichiarato, 2026-11-06)

Il modello del §4 **non** unifica la chiave: `key_selector` resta, preventivo e offerta restano a `uid`, **K-1 del
2026-10-19 resta**. Revoca invece, e va scritto qui perché chi legge la guida trova «decisione definitiva»:

* la **D1** del 2026-07-18 (`brief-db-guard-sorgente-polimorfa` §3): `sorgente_riga` col «doppio scopo
  documentato» → ha un solo scopo, la riga;
* il **modello A** (colonne alternative) e il **modello B** (chiave testuale) di quel brief, e con loro le due
  funzioni sorelle `_tipizzata` / `_testuale` (D3) → un guard solo;
* nella guida `sorgente-polimorfa.md` il §4a («colonne che sembrano polimorfe ma non lo sono»:
  `commesse_attivita` «sempre l'uid», `ddt`/`resi` «colonna tipizzata diretta», `attivita_fatturabili` «hash») e le
  motivazioni del §4 che si appoggiano a quelle eccezioni;
* il manuale di `config.sorgenti` §Convenzione chiave sorgente, per le stesse parti.

Guida, manuali e memoria del team si riscrivono **nello stesso lotto** che porta la tabella al modello, non dopo.

## 4. Il modello (Tid, 2026-11-06)

* `sorgente_tipo_id` → `config.sorgenti`: il tipo del **documento**.
* La chiave del **documento**, una sola delle due, secondo il `key_selector` del tipo:
  * `sorgente_id bigint`, se il documento ha chiave `id`;
  * `sorgente_uid uuid`, se ha chiave `uid`.
* `sorgente_riga` = la **riga** di quel documento; NULL se la provenienza è il documento intero.
* Una grammatica sola per tutte le tabelle, scritta da un BB unico e validata da un guard unico, che controlla anche che
  la riga appartenga al documento.
* **Unicità solo dove il dominio ha una regola**, dichiarata e sulla chiave giusta (`NULLS NOT DISTINCT`, parziale su
  `sorgente_tipo_id IS NOT NULL`). Nessuna unicità «per sorgente» generica.
* **L'import da un sistema esterno** non usa queste colonne: avrà una tabella di collegamento propria (canale, tipo
  record, id esterno `text`), come da `brief-db-articoli-obsoleto-dal` §9.2.

## 5. Che cosa NON è questo brief

* Non è il magazzino (D-5, l'ODL) né l'import esterno: li tocca solo perché usano le stesse colonne.
* Non riscrive la lineage: la semplifica, quando le grammatiche diventano una.

## 6. Da decidere (Tid)

| # | Domanda | Perché serve | Proposta DB |
| --- | --- | --- | --- |
| S-1 | **`sorgente_riga` è l'id della riga o un progressivo?** | L'offerta espansa non ha una riga sua (listino o eccezione) | l'**id della riga** quando esiste; `fn_offerta_righe_espanse` restituisce la riga d'origine |
| S-2 | **I tipi `*_RIGA` in `config.sorgenti` si ritirano?** | Col modello il tipo è il documento: PREVENTIVO_RIGA e simili diventano doppioni | sì; `config.sorgenti` prende la tabella delle righe (la `target_righe_table` della D4 di luglio) |
| S-3 | **I livelli sotto la riga** (`DDT_VENDITA_PRELIEVO`, `RESO_VENDITA_RIENTRO`, sorgenti di `magazzino.movimenti`) | Sono la riga di una riga: due livelli non bastano | da decidere: terzo livello, oppure il prelievo resta un tipo a sé con chiave `id` (documento = il prelievo, nessuna riga) |
| S-4 | **Le tabelle di collegamento (G3) tengono il testo?** | `pratiche_sorgenti` e `commesse_sorgenti` hanno una chiave `text` canonica con `ON CONFLICT` vivi | allineate alle colonne tipizzate, per avere una sola grammatica |
| S-5 | **Le ~2.850 righe con l'uid per un tipo `id`** si convertono? | Senza conversione restano due grammatiche | sì, conversione con l'id del documento (dato derivato, non si perde niente); la lineage perde il `CASE` |
| S-6 | **Gli orfani** (387) e le tabelle senza guard (G1, G4, G6, G7) | Nessuno impedisce una sorgente che non esiste | guard unico su tutte; gli orfani si censiscono e si decide, prima del guard |
| S-7 | **G5** (`attivita_fatturabili`, `fatture_righe`): il tipo resta COMMESSA con la riga della commessa? | È già documento + riga; l'uid è un hash d'idempotenza, non una chiave | sì al tipo e alla riga; l'hash esce da `sorgente_uid` e va in una colonna sua |

### 6.1 Stato delle decisioni (2026-11-06)

* ✅ **S-1 (Tid):** `sorgente_riga` = l'id della riga quando la riga esiste; per l'offerta, `fn_offerta_righe_espanse`
  restituisce la riga d'origine.
* ✅ **S-3 (Tid ha delegato la scelta al team DB: «fare la scelta migliore»):** un **terzo livello**,
  `sorgente_dettaglio bigint`, solo sulle tabelle che riferiscono la riga di una riga (oggi `magazzino.movimenti` e
  `movimenti_attesi`). Tipo = DDT_VENDITA, documento = la bolla, riga = la riga della bolla, dettaglio = il prelievo.
  Il «tipo a sé» (il prelievo come documento) è scartato: romperebbe la regola «il tipo è il documento», e ogni
  lettore dovrebbe risalire a mano prelievo → riga → bolla, cioè la traduzione che questo brief toglie.
  `config.sorgenti` prende la tabella del dettaglio accanto a quella delle righe (S-2).
* ✅ **S-5 (Tid):** si convertono solo le righe con l'uid di un documento padre che ha chiave `id`: si mette l'id del
  padre in `sorgente_id`. Dove il padre ha chiave `uid` (preventivo, offerta) non cambia niente.
* ✅ **S-6 (Tid):** un guard unico impedisce una sorgente che non esiste. Gli orfani sono dati di test: si puliscono
  con un one-shot manuale su dbdev prima di montare il guard (dati di test → correzione manuale, non migration, come
  nel `brief-db-guard-sorgente-polimorfa` Appendice A). Da zero non ce ne sono.
* ✅ **S-2 (Tid):** i tipi `*_RIGA` si ritirano: una riga si scrive col tipo del suo documento + `sorgente_riga`.
  `config.sorgenti` prende la tabella delle righe (e, dove c'è, quella del dettaglio, S-3): serve al guard per
  verificare che la riga esista e appartenga a quel documento.
* ✅ **S-4 (Tid):** anche `pratiche_sorgenti` e `commesse_sorgenti` passano alle due colonne tipizzate
  (`sorgente_id` / `sorgente_uid`), con lo stesso guard e gli stessi BB. Si riscrivono i loro lettori e scrittori,
  compresi gli `ON CONFLICT` vivi: `pratiche_repository.upsert_pratica_sorgente` nel BE e la funzione dei canali.
* ✅ **S-7 (Tid):** in `attivita_fatturabili` e `fatture_righe` l'impronta d'idempotenza esce da `sorgente_uid` e va in
  una colonna sua, con un nome che dice che cos'è. `sorgente_*` resta la sola provenienza (COMMESSA, la commessa, la
  sua riga). Prima si verifica chi la calcola e chi la legge: `md5(segment_key)` coincide su 2 righe di 64, quindi la
  formula è un'altra.

**Tutte le decisioni del §6 sono prese (2026-11-06).**

### 6.2 Dall'analisi critica (2026-11-06)

| # | Domanda | Decisione |
| --- | --- | --- |
| S-8 | Le **colonne parallele** (G8: `ordini.documento_origine_*`, `contratti.offerta_id`, `ordini_righe_fulfillment`) | ✅ **Tid:** confluiscono in `sorgente_*`. Se descrivono una provenienza polimorfa, si usa sempre lo stesso meccanismo. Il censimento **segnala** che cosa non può rientrare, con il motivo; l'eccezione la decide Tid. Le regole di unicità che portano si trasferiscono sulla chiave nuova |
| S-9 | La **cancellazione** del documento sorgente (gli orfani tornano anche dopo S-6) | ✅ **Tid:** la governa la regola padre-figli della tabella padre. Se la cancellazione è permessa, le azioni conseguenti sui figli si fanno **dentro le regole DB**, non fuori. Il legame polimorfo non ha FK: il censimento dice quali `target_table` ammettono la cancellazione e che cosa succede oggi ai figli; il lotto 0 dà al meccanismo il suo lato «in uscita», derivato dal catalogo |
| S-10 | I **tipi che non sono documenti** (`EVENTO_ASSET`, `ATTIVITA`; con S-2 il tipo è «il documento») | ⏳ **da analizzare** (Tid: «si potrebbe pensare a qualche cosa che descrive altro?»). Ipotesi da verificare nel censimento: il tipo è **l'oggetto di provenienza**, e il catalogo dice se ha righe (`target_righe_table`) o no. Un oggetto senza righe (l'evento, l'attività) ha solo la chiave e `sorgente_riga` sempre NULL, verificato dal guard. Prima si misura chi scrive davvero questi tipi |
| S-7 | (precisata) l'**impronta** di `attivita_fatturabili.sorgente_uid` | ✅ **Tid:** se esiste, c'è un motivo. Si **verifica** con certezza piena che nessuno la usi (DB, BE, FE, pgTAP, e il motivo per cui è nata) **prima** di pulirla. Fatto noto: la formula è `md5(segment_key)` in `fn_emit_attivita_fatturabili_da_commessa`, che la usa per ritrovare la riga già emessa; la tabella ha anche `uq_attivita_fatturabili_commessa_attivita` |
| — | il **lotto A** di `brief-db-articoli-obsoleto-dal` (`20261105-02`, `-03`, `-14`, non ancora committati) | ✅ **Tid:** nessuna riscrittura. Si fanno YAML nuovi |

## 7. Dopo le decisioni

### 7.1 Il censimento (in corso, 2026-11-06)

Per **ogni** tabella del §3.1 e §3.1-bis, più le colonne parallele G8, una scheda in Appendice:

* grammatica di oggi e significato scritto (commento di colonna, manuale);
* chi **scrive** (funzioni DB, BE) e chi **legge** (funzioni, viste, BE, FE, pgTAP);
* default, CHECK, indici unici, ognuno classificato: **regola di dominio** / **idempotenza import** / **residuo**;
* guard montati;
* la cancellazione del bersaglio (S-9): la `target_table` la ammette? che cosa succede oggi ai figli?;
* il lotto di destinazione, e che cosa **non può rientrare** nel meccanismo (S-8), col motivo.

Più tre schede trasversali: i BB del §3.3 (che cosa cambia in ciascuno), i consumatori dei codici `*_RIGA` (S-2),
e l'analisi di S-10 e dell'impronta di S-7.

### 7.2 Il piano a lotti (bozza, da fissare dopo il censimento)

* **Lotto 0, trasversale e additivo.** Non rompe niente; i lotti dopo ne hanno bisogno:
  * il catalogo: in `config.sorgenti` la tabella delle righe e quella del dettaglio, ognuna con la sua **colonna
    FK** verso il livello sopra, dichiarata (non ricavata da `pg_constraint`) e presidiata;
  * i BB: uno che **scrive** (riceve tipo e una chiave qualsiasi, salva quella giusta: chi passa l'uid oggi
    continua a farlo) e uno che **risolve** (da tipo + chiave: id, uid, numero; i lettori non scrivono più un
    `CASE` per tipo);
  * il guard unico: una sola chiave, documento esistente, riga del documento, dettaglio della riga; CHECK di
    forma per tabella;
  * il lato «in uscita» (S-9) e il presidio degli orfani riscritto sul modello;
  * un **presidio di struttura** in CI: una tabella con colonne `sorgente_*` senza il guard unico è rossa. È ciò che
    impedisce alla prossima tabella di nascere con una grammatica sua.
* **Poi, per famiglia**, nell'ordine: colonne → conversione dei dati → guard → lettori → pgTAP → ritiro dei tipi.
  Il guard di oggi rifiuta i tipi spenti (`attivo = true`): spegnere un tipo `*_RIGA` prima di aver convertito le
  righe rompe ogni UPDATE su quelle righe. Per `config.tipi_entita` prima `is_sorgente = false`, poi il ritiro del
  tipo: l'entità «riga di preventivo» resta (giornale, note, errori).
* Il primo lotto di famiglia sono le **righe di vendita**, che sbloccano il lotto B degli articoli obsoleti.
* Solo YAML nuovi: i changeSet del lotto A non si riscrivono.
* Ricadute BE/FE: le richieste si scrivono qui, percorso intero, quando il censimento le fa emergere.
