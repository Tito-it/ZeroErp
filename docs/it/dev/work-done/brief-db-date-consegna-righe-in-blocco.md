# Brief DB — Le date di consegna delle righe, aggiornate in blocco

## ⏭️ Chi riparte — aggiornato al 2026-10-13

**Riparte: nessuno** — ✅ **chiuso e archiviato** in `work-done/` (2026-10-13). Lavoro chiuso: DB applicato e verde, BE/FE scritto, rivisto e **collaudato a video** (Tid, 2026-10-13, §8.3).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | BE/FE | policy, ripiego e locales del codice nuovo | §5 | ✅ 2026-10-12 |
| 2 | BE | repository + service + due endpoint `…/righe/date-consegna/`, verbo per riga sulla stessa funzione, test (anche sul DB vero) | §5, §8 | ✅ 2026-10-12 |
| 3 | FE | dialog condiviso, azione nei drawer ordine e preventivo, kebab di riga spento dal motivo di riga, spec | §5, §8 | ✅ 2026-10-12 |
| 4 | BE/FE | guide `gestione-ordini` §3.5 e `gestione-preventivi`, doc API, cataloghi BB | §5 | ✅ 2026-10-12 |
| 5 | Tid | revisione: anteprima vera, scritture dallo store, esito intero | §8.1 | ✅ 2026-10-12 |
| 6 | DB | pgTAP: il test 13 sulla forma vera del BE (BF-1), e il 23 che la distingue da quella del §5 | §4.7 | ✅ 2026-10-12 |
| 7 | DB | regola del 2, scelta (a): il BB `script.vw_stati_doc_ddt_merce_partita` e le tre sedi riallineate, pgTAP nuovo | §4.1, §4.7 | ✅ 2026-10-12 |
| 8 | Tid | apply `20261012-30 … -33`; pgTAP della data di consegna, del BB (dopo la correzione dei test 6/8) e regressione | §4.7 | ✅ 2026-10-12, verdi, nessuna regressione |
| 9 | BE | rigenerare `error_policies_generated.py`: la nota di `E_DOC_ANNULLO_CON_LEGAMI` era già allineata; il rigenero ha portato i due codici di brief-db-indirizzi-documento-seguono-il-cliente (`E_DOC_FORNITURA_FUORI_TESTATA`, `E_DOC_FORNITURA_PARAMETRO_MANCANTE`, nel CSV in git), coi loro ripieghi. `--check` pulito, guardrail e test della data di consegna sul DB vero verdi | — | ✅ 2026-10-12 |
| 10 | Tid | collaudo a video: dodici casi, ordini, preventivi e revisione | §8.3 | ✅ 2026-10-13, riuscito |
| 11 | Tid | archiviazione in `work-done/` | — | ✅ 2026-10-13 |

**Decisioni aperte di Tid:** nessuna (§8.2 decisa il 2026-10-12: (a), si accetta).
**Da committare:** il collaudo (§8.3), lo spostamento in `work-done/` e i link riallineati (api_ordini, api_preventivi, i due cataloghi BB). Il passo #9 è in git dal 2026-10-13.
Il secondo giro DB è in git (c395c2e1b), il lavoro BE/FE anche (6fdd888cc).

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-11, su decisione di Tid. **A chi:** team DB
> (§4), poi BE/FE (§5).
> **Stato:** ✅ **lato DB applicato, pgTAP verdi** (Tid, 2026-10-12; §4.6): quattro changeSet
> `20261012-04 … -07`, il codice nuovo nei due CSV, un pgTAP nuovo e due adeguati.
> ✅ **Lato BE/FE scritto e rivisto** (2026-10-12, §8 e §8.1), **collaudato a video** (Tid, 2026-10-13, §8.3).
> ✅ **Secondo giro DB** (2026-10-12, §4.7): regola del 2 chiusa con la scelta (a) di Tid, e il
> pgTAP allineato alla forma vera del BE. **Applicato, pgTAP verdi, nessuna regressione** (Tid).
> Decisioni D-1 … D-7 e P-1 prese da Tid il 2026-10-11 (§3, §6).
> **Storia:** la prima versione (sessione BE, stesso giorno, col nome
> `brief-db-data-consegna-proposta-in-testata`) proponeva due date sulla testata come **seme**
> delle righe. Tid l'ha **superata** (D-1): con la data in testata, cambiare la data di un ordine
> già scritto obbligava di nuovo a correggere le righe una per una, perché una riga che aveva preso
> il seme non si distingueva più da una scritta a mano. Al suo posto c'è una utility che scrive
> una data su più righe.
> **Non è un doppione di:**
> * [brief-db-modifiche-certe-ciclo-vendita-e-articolo](../work-done/brief-db-modifiche-certe-ciclo-vendita-e-articolo.md)
>   P-6: lì si è scartata una data di testata come riassunto delle righe. Qui di date in testata
>   non ce ne sono: P-6 resta com'è;
> * [brief-db-testata-dopo-emissione](../work-done/brief-db-testata-dopo-emissione.md): è la sede
>   della regola «fuori bozza, che cosa si cambia e in quale stato», anche per le righe (eccezione
>   `[4]`/`[5]` del lock). Qui non si riscrive: l'utility la **attraversa**, e si aggiunge una
>   regola di **riga** che quella regola di stato non sa dire (D-7).

## 1. La domanda

Su un documento di vendita la data di consegna sta solo sulle righe. Un ordine che si consegna
tutto insieme obbliga a scrivere la stessa data riga per riga, e a riscriverla riga per riga
quando il cliente la sposta. Tid chiede un gesto che scriva **una** data su più righe.

## 2. Il modello

* **La riga decide, sempre.** Non esiste una data di documento: nessuna colonna nuova in testata,
  nessuna lettura `COALESCE(riga, testata)`.
* **L'utility è una scrittura di massa sulle righe**, niente di più: l'operatore sceglie la
  colonna, la data e la modalità — **tutte le righe** o **solo quelle senza data**.
* **Il DB resta il giudice, riga per riga.** L'utility non porta regole sue: si accende dove la
  colonna si può scrivere (D-3) e scrive passando per i lock delle righe. Se una riga non si può
  toccare, la decisione è del DB, e il BE la legge da lì (§4.1), non la ricopia.

## 3. Decisioni di Tid (2026-10-11)

| # | Domanda | Decisione |
| --- | --- | --- |
| **D-1** | Data in testata come seme delle righe? | **No.** Superata la prima versione del brief: nessuna colonna nuova in testata |
| **D-2** | Che cosa fa l'utility? | Chiede una data e la scrive sulle righe del documento, in una delle due modalità: **tutte** / **solo non valorizzate** |
| **D-3** | Quando si accende? | Dove la colonna, oggi, si può scrivere: le regole di attivazione sono quelle di modificabilità della data di riga |
| **D-4** | Quali documenti? | **Ogni documento di vendita la cui riga porta almeno una delle due date**, e per ciascuno le sole colonne che ha. L'utility è parametrica per colonna. Censimento dalla doc auto-generata, 2026-10-11: `vendite.ordini_righe` le ha tutte e due, `vendite.preventivi_righe` la sola data richiesta; nessun'altra riga di vendita ne porta una (`vendite.ddt.data_ora_consegna_prev` è un dato del viaggio, sulla testata, e non c'entra). Un documento che domani porta una delle due date entra aggiungendo la colonna all'elenco del §5 |
| **D-5** | Acquisti? | **Fuori, per ora.** Senza lock e senza capability, non c'è ancora una regola da attraversare |
| **D-6** | Data **richiesta** su righe già evase? | Non si aggiorna. **Vale già**: il lock delle righe la lascia scrivere solo in bozza, e una riga di un documento in bozza non è evasa. Nessun lavoro |
| **D-7** | Data **confermata** su una riga già spedita? | **Non si cambia**: la data di consegna si scrive prima di spedire. Una riga che ha già un DDT confermato la tiene ferma. ⚠️ Oggi **non vale**: il lock decide sullo stato della **testata**, non sulla riga (§4) |

## 4. Lavoro DB — la sola regola nuova è D-7

Per D-6 e per l'attivazione (D-3) il DB ha già tutto: il lock delle righe
(`vendite.trgfn_doc_righe_lock_fuori_bozza`, eccezione `[4]`/`[5]` per
`data_consegna_confermata` in `CONFERMATO` e `PARZIALMENTE_EVASO`), `can_edit_righe` e
`can_edit_data_consegna_confermata` nelle capability. Manca solo la regola di riga di D-7.

### 4.1 Il predicato: «la data confermata di questa riga si cambia?»

* Una funzione **pura** `fn_check_*` per riga d'ordine (nome di lavoro
  `script.fn_check_ordine_riga_data_consegna_confermata(p_riga_id)`): `[]` se sì, i motivi se no,
  `NULL` se la riga non si vede.
* **Compone, non ricopia**: il motivo di stato viene da
  `script.fn_check_ordine_data_consegna_confermata` (che legge il montaggio del lock); il motivo
  nuovo è **riga già spedita**.
* «Riga già spedita» = esiste un `vendite.ordini_righe_fulfillment` verso una riga di DDT la cui
  testata è **uscita dalla bozza** e non è annullata. ⚠️ Prima di scriverlo si cerca chi lo dice
  già (`fn_situazione_merce_ordine`, `fn_documento_legami`, `fn_ordine_ha_residuo_evasione` e i
  lettori del fulfillment): una seconda definizione di «spedito» diverge dalla prima.
* Ha **tre** consumatori: il guard (§4.2), la capability per riga del verbo esistente, la
  selezione dell'utility (§5). Per questo è nel DB e non nel BE.
* ✅ **Scritto così** (2026-10-12): il predicato «riga spedita» sta in un lettore suo,
  `vendite.fn_ordine_riga_spedita(riga)`, **`SECURITY DEFINER`**: DDT e righe di DDT hanno RLS,
  e un guard che leggesse sotto la RLS di chi scrive lascerebbe passare la modifica proprio a chi
  non vede il DDT (fail-open). Stessa scelta di `script.fn_get_stato_testata_documento`.
* ✅ **«Spedito» non si è definito da capo**: è l'espressione di `vendite.fn_partite_merce`
  (stato del DDT con `ordine` ≥ quello di `EMESSO` e non `is_abortito`), letta dal catalogo
  degli stati e non da un elenco di codici.
* ✅ **Regola del 2 — scelta (a) di Tid, 2026-10-12.** Quell'espressione viveva in più sedi del
  previsto: il censimento per **significato** ne ha trovate **quattro**, in due forme —
  `fn_partite_merce` due volte (CTE `riga` e `ponte_riga`), il lettore nuovo, e il presidio
  `dbops.vw_ddt_emessi_senza_scarico`, che la scriveva come elenco di codici (EMESSO, SPEDITO,
  CONSEGNATO, RESO: oggi coincide, al primo stato nuovo diverge). Ora sta nel BB
  `script.vw_stati_doc_ddt_merce_partita` e le quattro sedi la leggono (§4.7). Il motivo del
  rinvio non c'era più: nel cantiere plancache la D-2 è chiusa (`20261012-03` applicato) e
  l'unica voce aperta, D-3b, è sul verbo dei resi, non su `fn_partite_merce`.
  Non sono copie, e restano dove sono: `fn_check_ordine_annullabile` («DDT figlio vivo» = non
  abortito, bozza compresa), la soglia di fatturazione di `fn_ddt_push_diagnosi` (SPEDITO /
  CONSEGNATO o lo stato-trigger), gli `IF stato = 'EMESSO'` dei guard di transizione.

### 4.2 Il guard

* `BEFORE UPDATE` su `vendite.ordini_righe`, `WHEN (OLD.data_consegna_confermata IS DISTINCT FROM
  NEW.data_consegna_confermata)`, che rifiuta quando il motivo «riga già spedita» c'è.
* Fascia `_a10_`: dopo il lock di stato (`_a05_`), che deve parlare per primo.
* Codice nuovo, registrato con policy e frase di ripiego (nome di lavoro
  `E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA`): la frase dice che la riga è già partita con un DDT, e
  la data di consegna non si cambia più.
* Solo `UPDATE`: una riga che nasce non ha ancora un fulfillment.

### 4.3 La capability per riga

Il verbo per la singola riga che già esiste (`cambia_data_consegna_confermata` del BE) oggi si
accende per documento (`can_edit_data_consegna_confermata`). Con D-7 la risposta è anche **di
riga**. ✅ **Scritto** nella forma di linee-guida-sql §12.5.1: la sede delle righe d'ordine è
`vendite.vw_ordini_righe_dettaglio` (la sorgente della lista righe e del repository), e la
colonna è **`data_consegna_confermata_blocco`** = il `reason` del primo motivo della check
(`NULL` = si cambia), come `correggi_qta_evasa_blocco` del DDT. La `reason_key` il FE la ricava
dal reason (`vendite.ordini.data_consegna_confermata_reason.<reason minuscolo>`).
⚠️ La chiave `…riga_spedita` è un debito verso il frontend (§5).

### 4.4 Che cosa **non** si fa nel DB

* Nessuna colonna, nessun trigger di seme, nessun verbo di massa: l'utility è un `UPDATE` del BE
  che i lock giudicano riga per riga (§5).
* Nessuna regola nuova per il preventivo: la data richiesta segue il suo lock delle righe.

### 4.5 pgTAP (fixture fabbricati)

* Riga d'ordine con fulfillment verso un DDT **emesso** → cambiare la data confermata è
  rifiutato col codice nuovo, e il predicato dà il motivo.
* Riga spedita **in parte** (DDT emesso per una quantità minore di quella della riga) → rifiutato
  allo stesso modo (P-1).
* Stessa riga con fulfillment verso un DDT **in bozza** → si cambia.
* Fulfillment verso un DDT **annullato** → si cambia (o si dichiara come il lettore esistente
  tratta l'annullato).
* Riga senza fulfillment, ordine `CONFERMATO` → si cambia; ordine in uno stato fuori
  dall'eccezione → rifiuta il lock di stato, **prima** del guard nuovo (ordine dei rifiuti).
* `UPDATE` di massa sull'ordine con il filtro del predicato → aggiorna le sole righe ammesse.

### 4.6 ✅ Che cosa è stato scritto (2026-10-12) — applicato, test verdi

> ✅ **Applicato il 2026-10-12** (su `zeroerp_ci` il `databasechangelog` registra `20261012-04 …
> -07` alle 00:14) e **pgTAP verdi** nella corsa di Tid.

| File | Che cosa |
| --- | --- |
| `20_code/vendite/20261012-04-create-fn-ordine-riga-spedita` | il lettore `vendite.fn_ordine_riga_spedita(riga)`, `SECURITY DEFINER`, `search_path` stretto, `GRANT` all'app (§4.1) |
| `20_code/script/20261012-05-create-fn-check-ordine-riga-data-consegna-confermata` | la check di riga: prima i motivi di stato di `fn_check_ordine_data_consegna_confermata` così come sono, poi `RIGA_SPEDITA` |
| `20_code/vendite/20261012-06-create-trgfn-ordini-righe-guard-data-consegna-spedita` | il guard e `trg_ordini_righe_a10_guard_data_consegna_spedita_upd` (`BEFORE UPDATE … WHEN` la data cambia): chiama la check e solleva il primo motivo con `fn_raise_primo_motivo_se_presente` (§12.5.2) |
| `20_code/vendite/20261012-07-update-vw-ordini-righe-dettaglio-data-consegna-blocco` | `+ data_consegna_confermata_blocco` in coda alla vista (§4.3). Il rollback tiene la colonna a `NULL` e toglie la chiamata: un `DROP` della vista perderebbe i grant del loop |
| `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` | `E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA`, `CONFLITTO_STATO`, messaggio id 1290 («%s, riga %s: la merce è già partita con un DDT…») |
| `db/pgtap/vendite/test-data-consegna-confermata-riga-spedita-v1.sql` | nuovo, 22 test (indice in testa) |
| `db/pgtap/vendite/test-vw-righe-dettaglio-sorgente-lista-v1.sql` | test 6: + la colonna nuova |
| `db/pgtap/script/test-rubinetto-primo-motivo-v1.sql` | test 5: da 37 a 38 siti (il guard nuovo), con la nota datata |
| `docs/it/dbzero/vendite/manual/ordini_righe.md`, `vw_ordini_righe_dettaglio.md` | il guard e la colonna |

**`%TYPE`**: firme, `DECLARE`, `COMMENT`, `GRANT` e i `DROP` dei rollback ancorati a
`vendite.ordini_righe.id/ordine_id/riga_nr`; nudi, con la ragione accanto, solo i tipi calcolati
(`RETURNS boolean`/`jsonb`, l'array dei motivi, l'etichetta composta). Firme verificate dopo il
`CREATE`: una funzione per nome, `(p_ordine_riga_id bigint)`.

**La prova** (2026-10-12, `zeroerp_ci` come `zeroerp`, SQL **estratto** dagli YAML con le due
righe di catalogo, in transazione annullata; preConditions provate a parte):

* il pgTAP nuovo **22/22**; due mutazioni mordono — senza trigger cadono 1, 9, 10, 14; un lettore
  che conta anche i DDT in bozza fa cadere 5 e 14;
* presidi trasversali verdi: rubinetto (7/7, col 38), sorgente-lista (9/9), riferimenti morti
  (`plpgsql_check`, 9/9), catalogo messaggi completo (7/7), motivo nominato (8/8), viste
  `security_invoker` (7/7), storico-scope-policy (36/36);
* regressione verde: lock-montaggio 30/30, debiti residui 24/24, ritardo 11/11, date di consegna
  13/13, lock righe fuori bozza 21/21, imponibile 15/15, componenti 31/31, righe evase 42/43;
* i rossi sono **identici senza l'estratto**: il 43 delle righe evase («rosso da owner, verde come
  app», dichiarato nel file) e tre `ERRORE_FIXTURE` già nel registro dei rossi
  (`test-vw-situazione-merce-ordine-v1`, `test-fn-genera-ddt-da-ordine-v1`,
  `test-fn-push-preventivo-a-ordine-v1`);
* rollback provato in ordine inverso: zero funzioni, vista con le sue 30 colonne.

L'apply, il pgTAP **come app** (RLS vera) e la corsa intera li ha fatti Tid dopo: verdi.

⚠️ **Un rosso nuovo su `zeroerp_ci` dopo l'apply, non causato da questi oggetti** (2026-10-12):
`dbops/test-vw-funzioni-check-codici-sotto-jit-v1.sql` test 3 —
`dbops.vw_punti_canale_campo` stima 191.880 contro la soglia 100.000 (e la sorella
`vw_funzioni_check_codici`, test 1, è a 91.674: il file la dava a ~9.400 il 2026-10-10).
Misurato in transazione annullata: **togliendo tutti e quattro i changeSet la stima non cambia di
un decimale**. A cambiare sono le **statistiche di `pg_proc`**: l'autoanalyze è scattato alle
00:15:43, un minuto dopo l'apply (00:14:39), e la stima della CTE `motivo` dipende dai `rows`
che il pianificatore ricava da quelle statistiche (join su `proname`, ricorsione `codici_rec`).
La premessa del test — «la stima viene dalla STRUTTURA, non dai dati: uguale in CI» — non regge:
viene dalle statistiche del catalogo, che un autoanalyze rinfresca.
✅ **Corretto** (2026-10-12, su indicazione di Tid, senza brief a parte): `20261012-25`
(`dbops.fn_regexp_occorrenze`, le occorrenze di una regex con `ROWS 1` dichiarato) e `20261012-26`
(`dbops.vw_funzioni_check_codici`: le sei estrazioni dall'helper, `unnest(regexp_split_to_array)`
al posto di `regexp_split_to_table`, l'estrazione delle deleghe materializzata). Righe identiche
sulle tre viste; stima da 92.006 / 92.963 / 192.883 a 11.586 / 12.700 / 32.135, e sotto la soglia
anche col prefiltro forzato a 594 corpi; ~320 ms senza JIT contro ~560. Il pgTAP del presidio ha la
premessa corretta e due test nuovi (4, 5) sulle proprietà invisibili della cura. ✅ Applicati (Tid,
2026-10-12). Gli avvisi `fn_log_error_only … fk_error_log_messaggio_errore_id` della prova sono
dell'estratto: il log via dblink non vede la riga di catalogo non committata.

### 4.7 ✅ Secondo giro DB (2026-10-12, dopo il lato BE) — applicato, test verdi

> ✅ **Applicato il 2026-10-12** (`20261012-30 … -33`) e **pgTAP verdi** nella corsa di Tid: la
> data di consegna, il BB (dopo la correzione dei test 6/8, sotto), la regressione. Nessuna
> regressione.

Due lavori, chiesti da Tid dopo il push del BE: il pgTAP che diceva di provare «la forma
dell'utility del backend» provava quella del §5, che il BE non usa (BF-1); e la regola del 2 del
§4.1, scelta (a).

| File | Che cosa |
| --- | --- |
| `20_code/script/20261012-30-create-vw-stati-doc-ddt-merce-partita` | il BB: una riga per ogni stato del DDT, `merce_partita` = `ordine` ≥ quello di EMESSO e non `is_abortito`, letto dal catalogo; ⛔ mai NULL (`ordine` NULL o EMESSO assente = false); `security_invoker`, `GRANT SELECT` all'app |
| `20_code/vendite/20261012-31-update-fn-ordine-riga-spedita-dal-bb-merce-partita` | il lettore legge il BB; firma, DEFINER, `search_path`, grant invariati |
| `20_code/vendite/20261012-32-update-fn-partite-merce-dal-bb-merce-partita` | via la CTE `soglia`: `riga` filtra `sm.merce_partita`, `ponte_riga` proietta `sm_n.merce_partita AS emesso`. Il resto è il corpo del `20260922-16`, verificato identico al vivo prima di scrivere (zeroerp_ci; dbdev a `search_path` neutro). Commento: la rev nuova, e gli apostrofi raddoppiati due volte nella nota del 22-09 tornano singoli |
| `20_code/dbops/20261012-33-update-vw-ddt-emessi-senza-scarico-dal-bb-merce-partita` | il presidio legge il BB invece dell'elenco; stesse colonne, `security_invoker` ripetuto |
| `db/pgtap/script/test-vw-stati-doc-ddt-merce-partita-v1.sql` | nuovo, 8 test: oggetto e grant, una riga per stato, i casi DRAFT/EMESSO/RESO/ANNULLATO, il fail-closed su uno stato fabbricato senza `ordine`, e le tre sedi che leggono il BB senza più la regola |
| `db/pgtap/vendite/test-data-consegna-confermata-riga-spedita-v1.sql` | da 22 a 23: il 13 esegue la forma del repository BE (CTE `candidate` + `UPDATE`, salta solo `RIGA_SPEDITA`, «aggiornate 1 \| saltate 1»); il **23** nuovo, ordine ANNULLATO senza spedite: l'utility non salta, il lock rifiuta con `E_RIGA_DOC_NON_BOZZA` |
| `docs/it/dbzero/script/manual/vw_stati_doc_ddt_merce_partita.md` (nuovo), `vendite/manual/fn_partite_merce.md` | il BB e dove lo legge la partita |

**Il significato cambia in un solo punto, e verso il modello.** In `ponte_riga` la regola
guadagna `NOT is_abortito`: una ri-consegna in un DDT abortito conta «in riconsegna», non
«riconsegnata». Per il modello il caso non si forma (l'annullo ritira i legami, ed è rifiutato
finché ci sono); e un `emesso` NULL (stato con `ordine` NULL) non fa più sparire la quantità
da tutte e due le colonne.

**La prova** (2026-10-12, SQL **estratto** dai quattro YAML, in transazione annullata):

* `zeroerp_ci` come `zeroerp`, fuso ostile: preConditions in ordine (tutte vere), apply, firma e
  DEFINER del lettore, `security_invoker` delle due viste, ACL dell'app; rollback in ordine
  inverso fino alla forma di partenza. ⚠️ Lì non ci sono DDT: l'equivalenza su quel database è
  vuota, e non si conta;
* **equivalenza su dbdev come app** (contesto operatore; i corpi nuovi montati come funzioni
  `pg_temp`, il BB in linea): `fn_partite_merce` nei tre modi (tutte, per ognuno dei DDT, per
  ognuno degli ordini), `fn_ordine_riga_spedita` su tutte le righe d'ordine, il presidio:
  `EXCEPT ALL` a zero nei due versi. Fatto datato: 37 partite, 6 con ri-consegna, 129 righe
  d'ordine di cui 21 spedite; il presidio è vuoto da tutte e due le parti, quindi su di lui
  l'equivalenza non dice niente (lo dice il pgTAP 8, sulla forma);
* tempi su dbdev come app, stessa sessione: «tutte» ~120-130 ms vecchia e nuova, per DDT
  ~225 ms tutte e due. ⚠️ È la funzione montata in `pg_temp`, non quella applicata: la misura
  che conta (20260922-16) è dopo l'apply;
* pgTAP: il nuovo **8/8**, la data di consegna **23/23** (anche senza l'estratto: i test 13 e 23
  non dipendono dal BB). Mutazioni che mordono: il filtro del §5 nel 13/23 fa cadere il **23**; il
  BB senza `COALESCE` e coi consumatori non migrati fa cadere **5, 6, 7, 8**;
* regressione con e senza l'estratto, **esiti identici**: viste `security_invoker` 7/7, chiusura
  della partita 14/15, situazione merce chiusura 12/13, resi da accreditare chiusura 11/12 (i tre
  rossi sono i test di scope, «rossi da owner, verdi come app»), ponte riconsegna 2/2, SRF una
  riga 4/4, ritardo 11/11; `ERRORE` di fixture identici in `test-vw-partite-merce-v1`,
  `-riconsegna-dopo-nc-v1`, `test-fn-list-ddt-da-pushare-contatore-v1`,
  `test-vw-situazione-merce-ordine-v1` (già nel registro dei rossi), `test-fn-genera-ddt-riconsegna-eredita-v1`:
  su `zeroerp_ci` vuoto i fixture non si costruiscono. Rilanciati da Tid come app dopo l'apply:
  verdi;
* presidi trasversali, identici con e senza: riferimenti morti 9/9, piano generico 7/7, costo
  delle policy 4/4, catalogo presidi 11/11, conta presidio per variante 13/13, debiti dichiarati
  8/8, check codici sotto JIT 5/5, rubinetto 7/7.

⚠️ **Dopo l'apply, la corsa di Tid (2026-10-12): il pgTAP del BB 7/8, rosso il 6.** Difetto del
**test**, non del changeSet. `pg_get_function_sqlbody` e `pg_get_viewdef` stampano i nomi senza
schema quando lo schema è nel `search_path` della sessione, e quello dell'app è `django, public,
config, dbops, script, anagrafiche`: il corpo applicato usciva `vw_stati_doc_ddt_merce_partita`,
non `script.vw_…`. La mia prova girava da owner, con un path senza `script`, e non poteva vederlo.
Peggio del rosso: sotto lo stesso path la negazione su `config.stati_doc_ddt` sarebbe stata verde
per sottrazione. Corretto: i test 6 e 8 leggono il catalogo con due helper `pg_temp` a
`search_path = pg_catalog` (nomi sempre qualificati), e l'8 ha anche la negazione su
`config.stati_doc_ddt`. I tre predicati, rieseguiti come app su dbdev col path del runner: veri.
✅ Rilanciato da Tid: 8/8.

## 5. Ricaduta BE/FE (dopo la consegna DB)

* **Policy del codice nuovo** `E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA` in `error_policies.py`
  (CONFLITTO_STATO → 409): senza, `test_error_codes_db_policy_guardrail` è rosso dopo l'apply.
* **Locales**: `vendite.ordini.data_consegna_confermata_reason.riga_spedita` (it, en), o
  `scripts/check_i18n_keys.py` (controllo 4) è rosso.
* **Il verbo per riga** (`cambia_data_consegna_confermata`) spegne il pulsante dalla colonna
  `data_consegna_confermata_blocco` della riga, accanto al flag di documento.

* **Un'utility parametrica per colonna**, «Aggiorna date di consegna», sui documenti di vendita:
  ordine (data richiesta e data confermata), preventivo (data richiesta). L'elenco delle colonne
  per documento è l'unica cosa che l'utility sa del documento.
* **Attivazione** (D-3), dalle capability che il DB già manda:
  * data richiesta → `can_edit_righe` (solo bozza);
  * data confermata → `can_edit_righe` **oppure** `can_edit_data_consegna_confermata` (che è
    `false` in bozza di proposito: lì la data si scrive modificando la riga).
* **Un solo `UPDATE`, in una transazione**, non un ciclo di chiamate:
  `SET <colonna> = :data WHERE <fk_testata> = :id AND attivo`, più `AND <colonna> IS NULL` in
  modalità «solo non valorizzate», più — per la data confermata —
  `AND script.fn_check_ordine_riga_data_consegna_confermata(id) = '[]'::jsonb` (la forma è
  provata nel test 13 del pgTAP). Le righe già spedite si **saltano**, non fanno fallire il
  gesto.
  ⛔ **Superato da BF-1** (§8): quel filtro, in uno stato che non ammette la data, saltava ogni
  riga in silenzio. Il BE salta le sole righe col motivo `RIGA_SPEDITA`; il test 13 prova ora
  quella forma, e il 23 la distingue da questa (§4.7).
* **Fuori bozza si scrive solo la colonna confermata**: il lock lascia passare quella sola.
* **Ritorna** quante righe ha aggiornato e quante ha saltato perché già spedite: il FE lo dice.
* **«Tutte» sovrascrive** le date scritte: dialog di conferma col numero di righe.
* Il verbo per la singola riga e l'utility **scrivono dalla stessa funzione del repository**
  (regola del 2); il verbo per riga impara il codice nuovo del §4.2.
* Guide `gestione-ordini` e preventivi: l'utility, le due modalità, l'esempio «tutto il 20, poi
  il cliente sposta al 22».

## 6. Punto deciso dopo la prima stesura

| # | Domanda | Decisione |
| --- | --- | --- |
| **P-1** ✅ | Una riga spedita **in parte** (o rientrata con un reso da riconsegnare) tiene ferma la data confermata? | **Sì, ferma** (Tid, 2026-10-11): basta un DDT confermato, come dice D-7. Una spedizione parziale vuol dire che qualcosa è andato storto, e la data di quella riga resta quella con cui è partita. Il predicato del §4.1 **non** guarda il residuo: niente `fn_ordine_ha_residuo_evasione`, niente rientri. Il pgTAP del §4.5 lo prova con una riga spedita in parte |

## 7. Fuori da qui

* Acquisti (D-5): entra col cantiere acquisti, con lo stesso modello; la colonna
  `acquisti.ordini.data_ora_consegna_prev` (dato del trasporto, analisi-simmetria-ordini-acquisto
  ⑪) si guarda lì.
* Una data di testata, proposta o calcolata (D-1; P-6 per quella calcolata, che è già il `min` di
  `vw_ordini_lista`).

## 8. Lato BE/FE — il disegno e tre decisioni (Tid, 2026-10-12)

**Il disegno** (dichiarato prima del codice, regola del 2, ok Tid):

* **Repository** — `RigheDocumentoRepositoryMixin.scrivi_data_consegna(...)`: ogni repository
  dichiara le sue colonne (ordine: le due date, la confermata con la check di riga; preventivo: la
  sola richiesta). Un solo `UPDATE` in una CTE, ritorna `aggiornate` e `saltate_spedite`;
  `anteprima` esegue lo stesso `UPDATE` in un savepoint e lo annulla (2026-10-12, dopo la revisione:
  contare con una `SELECT` a parte non passava dai lock, e in uno stato che non ammette la colonna
  l'anteprima dava un numero e la scrittura il 409). Con una riga sola (il verbo per riga) non salta niente: parla il
  guard col codice nuovo.
* **Service** — `apps/vendite/services/_date_consegna_righe.py`, condiviso da ordini e preventivi:
  valida colonna (whitelist da `colonne_date_consegna()` del repository), data (obbligatoria) e
  modalità `TUTTE` / `SOLO_VUOTE`. Nessun pre-check di stato.
* **Endpoint** — `POST …/ordini/<id>/righe/date-consegna/`, `POST …/preventivi/<id>/righe/date-consegna/`.
* **FE** — `vendite/_shared/dateConsegna/`: il dialog `DateConsegnaRigheDialog.vue` (colonna, data,
  modalità; «Tutte» chiede l'anteprima e conferma col numero di righe), il composable
  `useDateConsegnaRighe` (l'azione «Aggiorna date di consegna» nella barra del drawer, dalle
  capability) e la factory `makeDateConsegnaApi(BASE)`, esportata dall'API di ciascun dominio. Il
  dialog **non chiama l'API**: scrive con l'azione dello store del dominio, che riceve in `invia`
  (§8.1). Il kebab di riga dell'ordine si spegne anche sul motivo di riga, con l'helper
  `motivoDaCodiceBlocco` di `bloccoMotivo.js` (seconda occorrenza dopo `DdtRigaForm`, che passa
  sull'helper nello stesso giro).

| # | Domanda | Decisione |
| --- | --- | --- |
| **BF-1** | Quali righe salta l'utility? | **Solo quelle col motivo `RIGA_SPEDITA`** (`check @> '[{"reason":"RIGA_SPEDITA"}]'`), non tutte quelle con `check <> '[]'` come diceva il §5: con lo stato che non ammette la modifica il filtro del §5 salterebbe ogni riga e risponderebbe «0 aggiornate, N spedite», falso. Così il motivo di stato va all'`UPDATE` e lo rifiuta il lock (409) |
| **BF-2** | Preventivo con una riga `PENDING` di approvazione prezzo? | Il gesto fallisce per intero col 409 di `trgfn_righe_guard_pending`: giudica il DB, e il brief salta solo le spedite |
| **BF-3** | Azione senza colonne attive? | Ordine: visibile e spenta col motivo della data confermata. Preventivo fuori bozza: non compare (`can_edit_righe` non porta un motivo), come «Nuova riga» |

### 8.1 La revisione di Tid (2026-10-12)

Tre correzioni dopo la prima scrittura. Le prime due toglievano difetti che non davano errore.

| # | Che cosa non andava | Com'è ora |
| --- | --- | --- |
| **R-1** | L'anteprima contava con una `SELECT` a parte, che non passa dai trigger. In uno stato che non ammette la colonna diceva «5 righe», e poi la scrittura prendeva il 409 | `anteprima` esegue **lo stesso `UPDATE`** in un savepoint e lo annulla: i lock e il guard girano davvero, quindi il rifiuto arriva prima della domanda di conferma, e i numeri sono quelli della scrittura. Presidi: test 7 di `tests/db/test_date_consegna_righe_db.py`, test 8 di `DateConsegnaRigheDialog.spec.js` |
| **R-2** | Il dialog chiamava l'API da sé, e lo stesso faceva `OrdineRigaDataConsegnaDialog`: dopo la scrittura le liste aperte in altre schede non venivano avvisate | Scrivono le azioni degli store, `ordini.aggiornaDateConsegna`, `ordini.cambiaDataConsegnaConfermata` e `preventivi.aggiornaDateConsegna`, che avvisano le liste (frontend-standards §«Producer cross-tab»); l'anteprima non avvisa. Il dialog riceve l'azione in `invia` |
| **R-3** | L'esito ha una chiave `data` (la data scritta), e `useApiHandler.execute` lo scambiava per un envelope: al dialog arrivava la sola data, e i conteggi andavano persi | Le azioni `aggiornaDateConsegna` degli store ritornano la **response** e non l'esito, così `execute` spacchetta l'envelope una volta sola. Presidi: test «l'esito con la chiave `data` arriva intero» del dialog e gli spec dei due store |

Verifica dopo la revisione (2026-10-12): test BE del service, sul DB vero e del service ordini, 83 verdi; spec FE di
dialog, composable, store e `bloccoMotivo`, 27 verdi.

### 8.2 ✅ L'anteprima e il diario degli errori — deciso (a), Tid 2026-10-12

L'anteprima (R-1) esegue l'`UPDATE` vero in un savepoint e lo annulla. Quando il lock o il guard
la rifiutano, il rifiuto passa da `script.fn_log_and_raise_error`, che scrive in `dbops.error_log`
con `script.fn_log_error_only` **via dblink**: quella riga sta in un'altra transazione e
**sopravvive** all'annullamento. Ogni anteprima rifiutata lascia quindi nel diario un errore
che nessuno ha davvero tentato di scrivere; la scrittura vera, se l'operatore insiste, ne lascia
un secondo.

Due strade: **(a)** si accetta, e si dichiara (il diario racconta anche le prove); **(b)** il BE
passa all'anteprima un segnale che il DB riconosce per non loggare. La (b) tocca il BB del
diario, che oggi non conosce un «modo prova»: andrebbe disegnata a parte, non qui.

**Decisione (Tid, 2026-10-12): (a).** La traccia è di un rifiuto vero, e sul modello è rara: il
pulsante si accende solo dove le capability ammettono la colonna, quindi l'anteprima viene
rifiutata solo nei casi che le capability non vedono (una riga `PENDING` del preventivo, BF-2; un
documento cambiato da un altro utente fra apertura e click). La (b) toccherebbe il BB del diario,
usato da tutti i guard, e un segnale che spegne il log va disegnato perché non diventi il modo di
nascondere errori veri. Nessuna ricaduta sul DB. Se il rumore nel diario diventerà un problema,
la (b) si apre come brief a sé.

### 8.3 ✅ Collaudo a video — riuscito (Tid, 2026-10-13)

Dodici casi, tutti come atteso:

* **ordine** — in `DRAFT` tutte e due le date, nelle due modalità, con la conferma col numero di
  righe prima di sovrascrivere; in `CONFERMATO` la sola confermata; in `PARZIALMENTE_EVASO` le
  righe spedite saltate e contate nella conferma e nell'esito, e il kebab della riga spedita
  spento col motivo di riga; in `EVASO`/`ANNULLATO` l'azione visibile e spenta col motivo (BF-3);
* **preventivo** — in bozza la sola data richiesta; fuori bozza l'azione non compare (BF-3); una
  riga `PENDING` di approvazione prezzo fa fallire il gesto per intero (BF-2);
* **revisione (§8.1)** — le liste aperte in un'altra scheda si aggiornano (R-2); con l'ordine
  annullato da un'altra scheda il rifiuto arriva dall'anteprima, prima della domanda di
  conferma (R-1).
