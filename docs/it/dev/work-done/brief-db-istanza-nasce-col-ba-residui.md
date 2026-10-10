# Brief DB — I residui di «l'istanza nasce col billing account»

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-10.
> **A chi:** team DB; team FE per il §4 (una chiave da togliere dai locales); team BE solo per una
> riga di documentazione (§4).
> **Origine:** i debiti che `work-done/brief-db-istanza-nasce-col-ba.md` ha lasciato alla sua
> chiusura (2026-10-10), elencati in `.codex/PROJECT_CONTEXT.md` § «Aperto — Media priorità»:
> il resolver `script.fn_get_billing_account_by_istanza` senza più consumatori (§6.12.3 di quel
> brief) e il ramo morto `PREVENTIVO_SENZA_BILLING_ACCOUNT` delle capability del preventivo
> (§6.10.3). Registro: **D25** di `migliorie-generali-da-test-valutazione.md`.
> **Stato:** ✅ **chiuso e archiviato il 2026-10-10.** `20261010-50` … `-59` **applicati da Tid** il
> 2026-10-10 (15:14, tutti `EXECUTED` in `databasechangelog`), pgTAP verdi su dbdev e su
> `zeroerp_ci` (il rosso della fixture del pgTAP nuovo, corretto lo stesso giorno, è verde nella
> baseline CI: §6). D-1 … D-5 decise da Tid lo stesso giorno e fatte. Le due richieste del §4 (la
> chiave nei locales, FE; una riga di documentazione, BE) fatte il 2026-10-10.
> **Da leggere per primo:** §3.1 e §5 per cosa è cambiato a DB, §4 per FE e BE.

## 1. Che cosa resta, sul modello

Dal 2026-10-08 un'istanza nasce col suo billing account (BA), e sul preventivo `billing_account_id`
e `utility_id` sono `NOT NULL`, legati all'istanza dalla FK composta `fk_preventivi_ba_coppia`.
Un'istanza può avere più utility, ognuna col suo BA (D-5), e un BA ha un solo cliente (D-6).

Da queste regole discendono due pulizie che il brief chiuso aveva rimandato:

* **«Qual è il BA dell'istanza?» non è più una domanda.** Ha una risposta solo se l'istanza ha un
  BA; con due utility ne ha due. Il cliente di cui si parla lo dice il documento o la pratica
  (`pratiche.pratiche.billing_account_id`, D-9), non l'istanza. Il resolver
  `script.fn_get_billing_account_by_istanza` era già stato ridotto a «il BA, se è uno» e
  dichiarato in ritiro; il backend non lo chiama più. Si cancella.
* **Un preventivo con la testata incompleta non esiste.** La capability del push a commessa aveva
  un motivo apposta (`PREVENTIVO_SENZA_BILLING_ACCOUNT`, «manca il cliente») che oggi non può
  uscire: il preventivo senza BA non nasce (errore `23502`). Lo stesso caso impossibile era
  scritto in altri due punti, come filtro: il residuo commessa e la lista del push chiedevano
  ancora `billing_account_id IS NOT NULL AND utility_id IS NOT NULL`. Erano tre copie della
  stessa idea, e si ritirano insieme: una lasciata in piedi continuerebbe a raccontare a chi
  legge che il caso esiste.

⚠️ Il motivo per cui si tolgono è il **contratto** (`NOT NULL` e FK composta), non il fatto che
oggi nessun preventivo sia senza BA: se le colonne fossero nullable, i rami servirebbero anche a
zero occorrenze.

## 2. Censimento (fatti datati, dbdev, 2026-10-10)

| Oggetto | Chi lo usa | Esito |
| --- | --- | --- |
| `script.fn_get_billing_account_by_istanza(bigint)` | nessuna funzione (`pg_proc.prosrc`), nessuna vista, nessuna dipendenza (`pg_depend`); nel backend nessun chiamante (resta un commento storico in `pratiche/tests/db/test_pratica_billing_account_db.py`); nessun changeSet di `80_data`/`90_end` la nomina | si cancella, il DROP sta in `20_code` |
| | pgTAP: `script/test-fn-get-billing-account-by-istanza.sql` (dedicato), test 8-9 di `anagrafiche/test-un-ba-un-cliente-v1.sql` | il dedicato si cancella; 8-9 diventano un presidio del ritiro |
| | doc: `script/manual/fn_get_billing_account_by_istanza.md`; `docs/it/backend/pratiche/manual/api_pratiche_list.md` (la dice «in ritiro») | la pagina `manual/` si cancella; la riga BE è nel §4 |
| ramo `PREVENTIVO_SENZA_BILLING_ACCOUNT` di `script.fn_available_actions_preventivo` | backend: nessun riferimento al codice; frontend: la chiave `vendite.preventivi.push_commessa_reason.senza_billing_account` in `it.json` e `en.json`; pgTAP: nessuno (il caso «senza BA» di `test-fn-preventivo-ha-residuo-commessa-v1` è già stato ritirato il 2026-10-08) | il ramo esce, la chiave la toglie il FE |
| filtro di testata in `vendite.fn_preventivo_ha_residuo_commessa` | capability e gate EVASO del backend | il filtro esce, e con lui il `JOIN` alla testata (§3.1, R-2) |
| filtro di testata in `vendite.fn_list_preventivi_da_pushare` | push a commessa (pipeline e pannello smistamento) | il filtro esce |

Le tre funzioni modificate sono di `titodb`, `SECURITY INVOKER`: nessun prestito di proprietà.
I corpi di partenza sono gli ultimi changeSet applicati, confrontati col vivo
(`pg_get_functiondef`) e identici.

## 3. Consegna DB

### 3.1 ChangeSet

| R | ChangeSet | Cosa fa |
| --- | --- | --- |
| **R-1** | `20_code/script/20261010-50-update-fn-available-actions-preventivo-senza-ramo-ba` | via il ramo «testata incompleta» del motivo del push, le due variabili che lo alimentavano e le due colonne della `SELECT … INTO`. Restano tre motivi, nello stesso ordine: `PREVENTIVO_STATO_CHIUSO` → `PREVENTIVO_NON_ACCETTATO` → `PREVENTIVO_NESSUNA_RIGA_COMMESSA` |
| **R-2** | `20_code/vendite/20261010-51-update-fn-preventivo-ha-residuo-commessa-senza-testata` | via i due predicati e il `JOIN` a `vendite.preventivi`, che serviva solo a loro. ⚠️ Non era un filtro nascosto: la vista `vw_preventivi_righe_smistabili_commessa` fa già lo stesso `JOIN` ed è `security_invoker`, quindi la RLS di chi chiama sulla testata resta identica. La funzione torna simmetrica alla gemella `fn_preventivo_ha_residuo_ordine` |
| **R-3** | `20_code/vendite/20261010-52-update-fn-list-preventivi-da-pushare-senza-testata` | via i due predicati. `CREATE OR REPLACE`: firma e `RETURNS TABLE` invariate (stessi tipi ancorati del `20260803-02`), privilegi e dipendenze restano |
| **R-4** | `20_code/script/20261010-53-drop-fn-get-billing-account-by-istanza` | `DROP FUNCTION`, con una `preCondition` `HALT`: nessun'altra funzione la nomina (provata su dbdev: `0`) |
| **D-3** | `00_schema/anagrafiche/20261010-54-drop-uq-gestori-singleton` | `ALTER TABLE … DROP CONSTRAINT IF EXISTS uq_gestori_singleton` (§5, D-3) |
| **D-1, D-2** | `20_code/vendite/20261010-55-update-fn-list-contratti-da-pushare-stato-obbligatorio` | stato `ATTIVO` assente → `E_CODICE`; via il filtro `IS NOT NULL` sul BA (§5) |
| **D-1** | `20_code/vendite/20261010-56-update-fn-list-ordini-da-pushare-senza-filtro-ba` | via il filtro `IS NOT NULL` sul BA (§5) |
| **D-5** | `20_code/script/20261010-57-create-fn-get-ba-emittente-sr-id-installazione` | BB nuovo: l'azienda di un BA per l'installazione (§5) |
| **D-5** | `20_code/anagrafiche/20261010-58-update-fn-guard-istanza-ba-gestore-globale-senza-sessione` | la coppia mista dell'istanza si cerca col BB (§5) |
| **D-5** | `20_code/anagrafiche/20261010-59-update-fn-guard-albero-ba-gestore-globale-senza-sessione` | la coppia mista dell'albero si cerca col BB; `search_path` con `pg_temp` (§5) |

Il `-52` porta anche D-2 per i preventivi (stato `ACCETTATO` assente → `E_CODICE`).

Ogni `COMMENT ON FUNCTION` porta la riga di revisione col suo numero.

⚠️ **Numerazione:** `-41` e `-42` di oggi li ha presi un'altra sessione mentre scrivevo (presidio
in `dbops`, non committato). Per non contendere i numeri successivi ho preso il blocco
`-50…-59`; `-43…-49` restano liberi.

### 3.2 pgTAP e documentazione

* `anagrafiche/test-un-ba-un-cliente-v1.sql`: i test 8-9 («istanza con due BA → NULL», «con un BA
  → quel BA») diventano un solo test 8, `hasnt_function` sul resolver, nella stessa forma dei
  presidi di ritiro 9-10 (ex 10-11). `plan` 13 → 12, numerazione e indice aggiornati.
  ⚠️ **Prima dell'apply il test 8 è rosso** per costruzione (la funzione c'è ancora).
* `script/test-fn-get-billing-account-by-istanza.sql`: **cancellato** (provava solo il resolver).
* `manual/`: cancellata `script/manual/fn_get_billing_account_by_istanza.md`; aggiornate
  `script/manual/fn_available_actions_preventivo.md` (tabella dei motivi, allineata anche al
  contratto vivo: mancava `PREVENTIVO_STATO_CHIUSO` e le chiavi avevano ancora la radice
  `preventivi.*` di prima del 2026-07-19), `vendite/manual/fn_preventivo_ha_residuo_commessa.md`,
  `vendite/manual/fn_list_preventivi_da_pushare.md`.
* La doc auto-generata (`funzioni/`, `index.*`) si riallinea alla prossima rigenerazione.

### 3.3 Come è stato provato (2026-10-10, dbdev, da owner, fuso `Pacific/Kiritimati`)

* **SQL estratto** dai quattro changeSet (`changes[].sql.sql` via `yaml.safe_load`) in una
  transazione con `ROLLBACK` e vincoli differiti, come Liquibase. La `preCondition` del `-53`
  eseguita a parte sul database che la incontrerà: `0`.
* **Equivalenza prima/dopo** sulla popolazione di dbdev — è una prova di non regressione, non un
  argomento per la modifica (§1): capability uguali su 168 preventivi su 168, residuo commessa
  uguale su tutti, lista del push uguale (15 righe, differenza simmetrica vuota). Con `-55` e
  `-56`: liste dei contratti (3 righe) e degli ordini (16) identiche; `plpgsql_check` pulito sulle
  tre liste.
* `plpgsql_check`: pulite capability e lista. Sul residuo resta l'avviso «STABLE ma espressione
  VOLATILE» (la `PERFORM` di `fn_log_and_raise_error` nel guard dell'id), **presente identico sul
  vivo**: non è di questo giro.
* Nessun corpo vivo nomina più `SENZA_BILLING_ACCOUNT`; il resolver non c'è più; i tre `COMMENT`
  portano la revisione.
* **pgTAP concatenati** all'SQL estratto, ciascuno nella sua transazione, confrontati con la corsa
  senza: `test-un-ba-un-cliente-v1` 13/13 → 12/12; `test-fn-preventivo-ha-residuo-commessa-v1`
  12/12; `test-fn-available-actions-preventivo-v1` 8/8; `test-capability-motivi-e-nessuna-azione-v1`
  13/13; `test-push-list-gia-inviato-v1` 10/10 — uguali con e senza.
* Le funzioni vive confrontate (md5 di `pg_get_functiondef`) prima e dopo ogni prova: invariate.
* Guardrail statici sui quattro file (`run_on_change`, `precondition_seed`,
  `ddl_su_trigger_automazione`, `grant_ruolo_batch`): verdi.
* ⚠️ Non provato: la corsa **come app** (la RLS), che arriva solo dopo l'apply.

## 4. Richieste a FE e BE

| R | A chi | Cosa |
| --- | --- | --- |
| **R-FE-1** | FE | togliere `vendite.preventivi.push_commessa_reason.senza_billing_account` da `frontend/src/locales/it.json` e `en.json`, **dopo** l'apply del `-50`. Prima dell'apply la chiave serve ancora, in teoria: il ramo è irraggiungibile, ma il codice c'è |
| **R-BE-1** | BE (doc) | `docs/it/backend/pratiche/manual/api_pratiche_list.md`, riga sul `billing_account_id`: `script.fn_get_billing_account_by_istanza` non è più «in ritiro» ma ritirata (2026-10-10). Nessuna modifica di codice |

✅ **Fatte il 2026-10-10** (sessione BE/FE, `dev/backend-tid`): R-FE-1 tolta la chiave da `it.json` e
`en.json`, `scripts/check_i18n_keys.py` pulito; R-BE-1 la riga di `api_pratiche_list.md` dice
«ritirata il 2026-10-10». Il commento storico in `pratiche/tests/db/test_pratica_billing_account_db.py`
resta: racconta cosa il test sostituisce, non chiama la funzione.

Nessun endpoint cambia forma: il blob della capability ha le stesse chiavi, e
`can_push_commessa_reason` resta uno dei tre motivi che già esce.

## 5. Trovati nel censimento, da decidere (Tid)

Non sono residui di `brief-db-istanza-nasce-col-ba`, ma li ha mostrati la lettura dei gemelli di
R-3. Non li ho corretti in questo giro: il primo tocca liste di altri cantieri aperti, il secondo
cambia un comportamento.

* ✅ **D-1 — Lo stesso filtro tautologico su ordini e contratti: tolto** (decisione di Tid,
  2026-10-10). `vendite.fn_list_ordini_da_pushare` e `vendite.fn_list_contratti_da_pushare`
  filtravano `billing_account_id IS NOT NULL`, e sulle due tabelle la colonna è `NOT NULL` (vivo,
  2026-10-10): il filtro non scartava niente. Fatto: `20261010-56` (ordini) e `20261010-55`
  (contratti, insieme a D-2). ⚠️ Se il cantiere `brief-db-esecutivi-ba-coppia` (D21) facesse
  tornare nullable il BA dell'ordine, il filtro tornerebbe necessario: lo dicono l'intestazione
  del `-56` e il `manual/` della funzione.
* ✅ **D-2 — Il filtro di stato era fail-open: ora lo stato è obbligatorio** (decisione di Tid,
  2026-10-10). In `fn_list_preventivi_da_pushare` e `fn_list_contratti_da_pushare` lo stato di
  partenza si cerca nel catalogo per `codice_interno` (`ACCETTATO`, `ATTIVO`), e il filtro era
  `(v_stato_…_id IS NULL OR stato = v_stato_…_id)`: se la riga di catalogo mancava o era spenta il
  filtro **cadeva**, e il push listava documenti in qualunque stato, in silenzio. Ora, come per
  la sorgente poche righe sopra, lo stato assente solleva `E_CODICE` («il codice ATTIVO non è
  stato trovato nella tabella config.stati_doc_contratti»), e il filtro è un'uguaglianza. Fatto:
  nel `20261010-52` per i preventivi (non ancora applicato, quindi nello stesso changeSet: due
  changeSet nello stesso giorno sulla stessa funzione sono la forma che si riscrive a vicenda) e
  nel `20261010-55` per i contratti. La lista degli ordini non ha questo difetto: lo stato lì è un
  `JOIN` al catalogo che esclude bozza, annullato e fatturato.
  * **pgTAP:** `vendite/test-push-list-stato-obbligatorio-v1.sql` (plan 3), **sulla forma, e
    dichiarato tale**: nessuna `fn_list_*_da_pushare` ha la forma `v_stato_…_id IS NULL OR`, e
    le due liste hanno il rifiuto `E_CODICE` col loro catalogo. Il caso vero (stato spento) è
    raggiungibile sul modello — basta che nessun documento sia in quello stato — ma un test non
    lo costruisce in modo deterministico: `trgfn_prevent_deactivate_if_children` non lascia
    spegnere uno stato che un documento usa (provato il 2026-10-10 su dbdev: rifiutato su
    entrambi), e le strade che lo forzerebbero (trigger disattivato, GUC di bypass) non si usano
    in un pgTAP. Il test **sa fallire**: sul vivo, prima dell'apply, è 0/3.

Altri due debiti del brief chiuso (§6.10.3 e §6.12.3) non avevano una sede: né un brief aperto né
una riga in PROJECT_CONTEXT. Li porto qui perché non si perdano.

* ✅ **D-3 — `uq_gestori_singleton` non vincola niente: ritirato** (decisione di Tid,
  2026-10-10). Era un vincolo `EXCLUDE USING gist (id WITH =) WHERE id IS NOT NULL` (nato nella
  prima generazione, `baseline/101-others-anagrafiche`): vietava due righe con lo stesso `id`,
  cioè ripeteva `pk_gestori`. Il nome prometteva «un solo gestore», la definizione no. Un solo
  gestore lo impone il guard `anagrafiche.trgfn_gestori_guard` (regola 1,
  `E_GESTORE_SINGLETON_VIOLATO`), un gestore per ruolo `uq_gestori_soggetto_ruolo`.
  Fatto: `20261010-54`. Prova: SQL estratto in transazione ritirata, restano `pk_gestori` e
  `uq_gestori_soggetto_ruolo`; `anagrafiche/create-soggetto-gestori.sql` 5/5 col vincolo tolto
  (il suo test 4 prova che un secondo gestore è respinto, cioè il guard). Aggiornate le pagine
  `manual/` di `gestori` (lo descriveva come la garanzia del singleton) e di
  `fn_pgtap_crea_gestore`. Censimento: nessun changeSet di `80_data`/`90_end`, nessun pgTAP,
  nessun riferimento nel backend.
* ✅ **D-4 — Lo spostamento dell'azienda predefinita ha il suo pgTAP** (decisione di Tid,
  2026-10-10). `anagrafiche/test-istanza-ba-gestore-globale-v1.sql`, plan 5: un'istanza con due
  BA sull'azienda del mondo; da operatore si toglie il collegamento del secondo (lecito); poi,
  come **super admin senza azienda**, spostare la predefinita su un'altra azienda dà
  `E_ISTANZA_EMITTENTI_DIVERSI` e la frase nomina l'istanza costruita (non un BA misto già nei
  dati); spostarla sull'azienda del BA collegato passa. Il nodo «non si costruisce» lo aveva già
  sciolto il gemello sull'albero (`test-guard-albero-ba-omogeneo-v1`, test 10-11): il super admin
  non ha un'azienda, quindi nel suo contesto il BA scollegato ricade sulla predefinita. Nessun
  builder nuovo. Prova (dbdev, owner, `Pacific/Kiritimati`): 5/5; **con il guard svuotato** in
  transazione ritirata i test 2 e 3 vanno rossi, quindi il test sa fallire. Aggiornati
  l'intestazione di `test-istanza-nasce-col-ba-v1` (lo dichiarava «non provato») e il `manual/`
  del guard (§ «Come si prova»).
* ✅ **D-5 — Spostata da chi ha un'azienda in sessione, la predefinita passava sopra una coppia
  mista: corretto, strada a** (decisione di Tid, 2026-10-10). Trovato scrivendo D-4 e provato lo
  stesso giorno: i guard dello spostamento risolvevano il BA scollegato con
  `script.fn_get_ba_emittente_sr_id`, che in sessione risponde «l'azienda di chi agisce» prima della
  predefinita. Per un utente con la sua azienda il BA scollegato «restava» lì, e lo spostamento
  passava; a sessione finita (un job, un altro utente) quel BA era della nuova predefinita e
  l'istanza o l'albero su due aziende. La tabella non ha RLS, quindi lo spostamento non era
  riservato al super admin.
  * **La forma.** La domanda del movimento è sul modello: «dopo lo spostamento, di chi è ogni BA
    per l'installazione?». La risponde un building block nuovo,
    `script.fn_get_ba_emittente_sr_id_installazione` (`20261010-57`): il collegamento, altrimenti la
    predefinita, senza il livello «chi agisce». Non è una copia del risolutore: risponde a
    un'altra domanda, e condivide solo le due letture di riga. I due guard del movimento,
    `fn_guard_istanza_ba_gestore_globale` (`-58`) e il gemello sull'albero
    `fn_guard_albero_ba_gestore_globale` (`-59`, che aveva lo stesso punto cieco: provato), cercano
    la prima coppia mista con quel building block e sollevano lo stesso rifiuto dei guard per BA
    (stesso codice, stessi valori nella frase, stesse chiavi di contesto). I guard per BA restano
    com'erano: servono ai movimenti 1-3 (collegare, cambiare, togliere un collegamento), dove la
    sessione è quella giusta da guardare. Il `-59` porta anche `pg_temp` nel `search_path` (D6-bis):
    la soglia del test 4 di `dbops/test-security-definer-search-path-v1` scende da 17 a 16.
  * **Caso di bordo, dichiarato.** Senza riga predefinita un BA scollegato non ha un'azienda per
    l'installazione (`NULL`), e il guard lo tratta come diverso dal fratello collegato: rifiuto
    (fail-closed). Non si presenta nel percorso del backend: la riga predefinita non si cancella
    (la protegge il guard del default; test 14 di `test-ba-cambio-emittente-storia-v1`) e il
    backend la crea solo quando manca.
  * **pgTAP.** `anagrafiche/test-istanza-ba-gestore-globale-v1` ora ha plan 8 e prova il rifiuto
    **da operatore con la sua azienda** sull'istanza (test 3) e sull'albero (test 6), oltre che da
    super admin (test 4), più il building block (test 2). Prova del 2026-10-10 (dbdev, owner, SQL
    estratto `-50…-59`): 8/8; **con tutto tranne `-58`/`-59`**, cioè col difetto, i test 3 e 6 sono
    rossi. Invariati con e senza: `test-guard-albero-ba-omogeneo-v1` 12/12,
    `test-istanza-nasce-col-ba-v1` 13/13, `test-ba-cambio-emittente-storia-v1` 14/14,
    `test-billing-account-auto-link-ef` 4/4, `test-emittenti-fiscali` 14/14,
    `test-fn-get-emittente-fiscale-pk` 10/10, `script/test-ba-emittente-risoluzione-v1` 14/14;
    `dbops/test-riferimenti-morti-v1` 9/9, `script/test-rubinetto-primo-motivo-v1` 7/7,
    `dbops/test-security-definer-search-path-v1` 5/5 (col `-59`; senza, il 4 è rosso per la soglia
    abbassata). `plpgsql_check` pulito sui due guard; sui dati di dbdev nessuno dei due solleva
    senza spostamento.

## 6. Apply e verifica — ✅ fatti (2026-10-10)

**Apply di Tid**, 2026-10-10 alle 15:14: `20261010-50` … `-59`, tutti `EXECUTED`. Verifica sul vivo
subito dopo: `script.fn_get_billing_account_by_istanza` non c'è più, `uq_gestori_singleton` nemmeno,
`script.fn_get_ba_emittente_sr_id_installazione` c'è, e nessun corpo di funzione nomina più
`SENZA_BILLING_ACCOUNT`.

**pgTAP: verdi alla corsa di Tid.** L'elenco lanciato:

* residui del brief chiuso: `anagrafiche/test-un-ba-un-cliente-v1` (12),
  `vendite/test-fn-preventivo-ha-residuo-commessa-v1`, `script/test-fn-available-actions-preventivo-v1`,
  `script/test-capability-motivi-e-nessuna-azione-v1`, `vendite/test-push-list-gia-inviato-v1`;
  un file in meno (`script/test-fn-get-billing-account-by-istanza`, cancellato);
* gestori (D-3): `anagrafiche/create-soggetto-gestori`;
* liste del push (D-1, D-2): `vendite/test-push-list-stato-obbligatorio-v1` (nuovo, 3),
  `test-fn-list-{preventivi,contratti,ordini}-da-pushare-*`,
  `test-fatturazione-immediata-simmetria-sorgenti-v1`, `test-righe-erogazione-obbligatoria-v1`.
  ⚠️ `test-fn-list-preventivi-da-pushare-v1` e `-v2` restano rossi come prima (3 test ciascuno, in
  `baseline-rossi.tsv`, `ASSERZIONE`): non sono di questo giro;
* azienda predefinita (D-4, D-5): `anagrafiche/test-istanza-ba-gestore-globale-v1` (nuovo, 8),
  `anagrafiche/test-guard-albero-ba-omogeneo-v1`, `dbops/test-security-definer-search-path-v1`
  (soglia 16), e i pgTAP degli emittenti elencati in D-5.

**⚠️ Rosso solo su `zeroerp_ci` (baseline di Tid, 2026-10-10): `anagrafiche/test-istanza-ba-gestore-globale-v1`,
`ASSERZIONE` — corretto lo stesso giorno, solo il pgTAP.** Riprodotto su `zeroerp_ci` in
transazione ritirata: cadeva il solo test 0. La precondizione pretendeva che la predefinita non
fosse nessuna delle due aziende costruite dal test. Su dbdev è vero **per i dati** (la predefinita
è un'azienda vera); su un database ricostruito non c'è nessuna azienda, e il bootstrap
(`trgfn_emittenti_fiscali_default_bootstrap`) fa predefinita la **prima** creata, cioè quella del
mondo. Lì il test 7 spostava la predefinita su sé stessa e passava a vuoto. Il codice DB è
giusto: lo sbaglio era nella fixture, che presumeva un dato della macchina.
Correzione: la fixture costruisce una **terza azienda** e ci porta la predefinita prima della
scena (quando tutti i BA del test sono ancora collegati, quindi senza coppie miste); il test 0
ora pretende proprio quella. La scena è la stessa su ogni database. Riprova: 8/8 su `zeroerp_ci`
e 8/8 su dbdev, in transazione ritirata; la predefinita di dbdev è rimasta la sua e `zeroerp_ci`
è rimasto vuoto. ✅ Verde nella baseline CI di Tid (conferma del 2026-10-10).

## 7. Archiviazione

* [x] apply e pgTAP verdi su dbdev (§6, 2026-10-10);
* [x] `test-istanza-ba-gestore-globale-v1` verde anche nella baseline di `zeroerp_ci` (fixture corretta e confermata il 2026-10-10, §6);
* [x] R-FE-1 e R-BE-1 fatte (2026-10-10, §4);
* [x] D-3 e D-4 decise e fatte (2026-10-10);
* [x] D-1 e D-2 decise e fatte (2026-10-10);
* [x] D-5 decisa (strada a) e fatta (2026-10-10);
* [x] riga in `.codex/PROJECT_CONTEXT.md` da «aperto» a «chiuso», D25 spuntata nel registro,
  brief in `work-done/` (2026-10-10).
