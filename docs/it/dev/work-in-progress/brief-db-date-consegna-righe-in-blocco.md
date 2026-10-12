# Brief DB — Le date di consegna delle righe, aggiornate in blocco

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-11, su decisione di Tid. **A chi:** team DB
> (§4), poi BE/FE (§5).
> **Stato:** ✅ **lato DB applicato, pgTAP verdi** (Tid, 2026-10-12; §4.6): quattro changeSet
> `20261012-04 … -07`, il codice nuovo nei due CSV, un pgTAP nuovo e due adeguati. Ora tocca a
> BE/FE (§5).
> Decisioni D-1 … D-7 e P-1 prese da Tid il 2026-10-11 (§3, §6). Resta una scelta per Tid sulla
> regola del 2 (§4.1, ⚠️).
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
* ⚠️ **Regola del 2 — scelta per Tid.** Quell'espressione ora vive in **due** sedi
  (`fn_partite_merce` e il lettore nuovo). La regola vuole l'estrazione in un BB comune e il
  ritiro della copia nello stesso giro; non l'ho fatto qui perché `fn_partite_merce` è dentro la
  catena che il cantiere `brief-db-plancache-funzioni-con-query-incorporate` sta toccando adesso
  (`fn_ddt_push_diagnosi` → `fn_partite_merce`, changeSet `20261012-*` di un'altra sessione), e
  la sua forma è sensibile al piano. Due strade: **(a)** estrarre ora un BB (per esempio una
  vista degli stati DDT «merce partita») e ritirare la copia in `fn_partite_merce` in accordo
  con quel cantiere; **(b)** lasciarlo a quel cantiere, con una voce nel suo brief.

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
premessa corretta e due test nuovi (4, 5) sulle proprietà invisibili della cura. Da applicare. Gli avvisi `fn_log_error_only … fk_error_log_messaggio_errore_id` della prova sono
dell'estratto: il log via dblink non vede la riga di catalogo non committata.

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
