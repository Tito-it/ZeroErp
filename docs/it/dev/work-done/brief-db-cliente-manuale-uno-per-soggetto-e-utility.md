# Brief DB — Un cliente manuale per soggetto e utility

## ✅ Chiuso il 2026-10-15

| # | Chi | Che cosa | Dove |
| --- | --- | --- | --- |
| 1 | ✅ Tid | decisioni C-1…C-9 (C-1…C-5 il 2026-10-13, C-6…C-9 il 2026-10-14) | §4, §4-bis |
| 2 | ✅ team DB | changeSet `20261014-08` … `-20`, CSV, pgTAP e doc, provati sullo scratch il 2026-10-14 | §5-bis |
| 3 | ✅ Tid | bonifica a mano del doppione 115/121; apply e pgTAP senza regressioni (2026-10-14) | §5-bis.3, §5-bis.4 |
| 4 | ✅ BE | il rifiuto al COMMIT della creazione manuale, `ha_ba_attivo` sul periodo, i codici (2026-10-15) | §6-bis |
| 5 | ✅ BE | `smoke-test-clienti.sh` verde (16 OK, 2026-10-15), fuori da `baseline-smoke.tsv` | §6-bis |
| 6 | ✅ team DB | l'archivio; i residui passano allo sviluppo delle utility (Tid, 2026-10-15) | §7, §8 |

Residui (§7): fanno parte dello sviluppo delle utility (Tid, 2026-10-15); la catena sul PDP resta in [brief-db-catena-istanze-pdp](../work-in-progress/brief-db-catena-istanze-pdp.md) (D18).

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-13. **A chi:** Tid, poi il team DB.
> **Origine:** lo smoke `smoke-test-clienti.sh` del giro notturno (commit BE `b3e35f899`), il passo
> lasciato rosso come «DOMANDA APERTA» (registro `backend/scripts/tests/baseline-smoke.tsv`). Tid,
> 2026-10-13: **va impedito**. Registro: **D33** di
> [migliorie-generali-da-test-valutazione](../work-in-progress/migliorie-generali-da-test-valutazione.md).

## 1. Il caso

La creazione manuale del cliente (utility con `config.utilities.richiede_pdp = false`) crea **ogni
volta** un'istanza fittizia nuova (`ClientiRepository.create_istanza_fittizia`: un `INSERT` in
`anagrafiche.istanze_utilities` con `fittizia = true`), poi il suo billing account e il cliente. Con
lo stesso soggetto e la stessa utility, la seconda richiesta risponde 200 e nasce un **secondo
cliente**, indistinguibile dal primo.

## 2. Perché è un difetto del modello

* Per le utility con PDP l'identità della fornitura è il **punto fisico**: due GAS dello stesso soggetto
  sono due contatori, due istanze, due clienti, ed è giusto. La protezione è
  `ex_clienti_no_overlap_stesso_pdp`.
* L'istanza fittizia **non rappresenta niente di fisico**: è un «contenitore tecnico trasparente»
  ([gestione-delle-istanze-utility](../../guide/gestione-delle-istanze-utility.md), §Istanze fittizie
  nella creazione manuale). Senza punto fisico, ciò che distingue una fornitura resta soggetto, utility
  e azienda emittente: due istanze fittizie con gli stessi tre valori sono la stessa fornitura scritta
  due volte.
* La guida dice che il UNIQUE sul billing account «basta» per le fittizie
  (`uq_clienti_billing_account`). Basta contro due clienti sullo **stesso** BA, ma non contro una
  seconda istanza col suo BA nuovo, che è proprio quello che fa la creazione manuale.

## 3. I fatti di struttura (2026-10-13)

* `anagrafiche.istanze_utilities`: `soggetto_id`, `fittizia`, nessuna utility e nessun emittente;
  l'unico UNIQUE è `codice`.
* `anagrafiche.billing_account`: `istanza_utility_id`, `soggetto_ruolo_id`, `utility_id`, `validita`;
  `uq_billing_instance_utility (istanza_utility_id, utility_id)`.
* L'emittente del BA sta nel ponte `emittenti_fiscali_billing_account`; un'istanza non ha BA di due
  emittenti (`E_ISTANZA_EMITTENTI_DIVERSI`). Lo stesso soggetto può quindi essere cliente di due
  aziende per la stessa utility, su due istanze: la chiave deve contenere l'emittente.
* La regola tocca quattro tabelle (istanza per `fittizia`, cliente per `periodo` e utility, BA, ponte
  per emittente): non sta in un indice, si controlla **alla conferma** dell'operazione, come
  `E_ISTANZA_SENZA_BA`. È la sorella di `ex_clienti_no_overlap_stesso_pdp`: là il perno è il PDP, qui
  soggetto + utility + emittente.

## 3-bis. Analisi: chiudere, riaprire, «attivo» (2026-10-13)

> Fatti datati, letti dal codice e dalla doc auto-generata. Servono a trovare dove il codice si
> separa dal modello, non a decidere la forma.

### Chi chiude e chi riapre, oggi

| Passo | Dove | Che cosa fa |
| --- | --- | --- |
| disdetta | `script.fn_disdetta_cliente` | solo da `AT`: `data_chiusura` + stato `CH` |
| subentro | `script.fn_subentro_cliente` | chiude il cliente precedente **sul PDP**; il nuovo nasce su istanza, BA e cliente nuovi (`parent_istanza_id`) |
| sospensione e riattivazione | — | **nessuno scrive** `clienti.data_sospensione` / `data_riattivazione` (rettifica del 2026-10-14: `pratiche.trgfn_sospensioni_riattiva` sospende e riapre la **pratica** e i suoi flussi, non il cliente). Le leggono solo `fn_get_evento_stato_corrente_cliente` e `fn_get_search_detail` |
| **riapertura di un chiuso** | — | **non esiste**: nessuna funzione DB, nessun endpoint BE (la PATCH del cliente non accetta stato e date) |

⚠️ Nemmeno disdetta e subentro hanno un chiamante nel backend o nel frontend: oggi l'app **crea**
clienti (sempre `AT` con la data operativa) ma non li chiude. La chiusura vive solo nelle due funzioni
DB.

La riapertura è quindi un passo del modello ancora da scrivere, non un comportamento da conservare.
Lo storico del cliente esiste già (`storico.clienti`): ogni versione della riga resta leggibile.

### Cinque definizioni di «cliente attivo»

| Lettore | Criterio | Dove si separa dal periodo |
| --- | --- | --- |
| `ex_clienti_no_overlap_stesso_pdp` | `periodo` (date; `AN` → NULL) | è il riferimento |
| `script.fn_subentro_cliente` | non `AN`, `data_attivazione < nuova`, `data_chiusura IS NULL OR >= nuova` | coerente con il periodo |
| `anagrafiche.trgfn_clienti_sync_stato_pdp` | **lo stato**, e solo `AT`/`CH` | `CW` (chiuso per switch) non libera il PDP; una chiusura con data futura lo libera subito |
| `script.fn_disdetta_cliente` | stato `AT` | un sospeso (`SF`/`SC`/`RS`) non si può disdire |
| BE `PraticheRepository.ha_ba_attivo` | `data_attivazione NOT NULL AND data_chiusura IS NULL` | una chiusura con data futura vale «non attivo» già oggi; un `CH` senza data vale «attivo» |

Sono tre misure diverse (periodo, stato, «data di chiusura vuota») per la stessa domanda. La regola di
questo brief deve usarne una, il periodo; le altre sono il debito da riallineare (vedi §5).

### Chi legge «il cliente del BA» (per C-5)

I documenti non portano un `cliente_id`: preventivi, ordini, DDT, contratti, fatture e commesse puntano
al **BA**. Il cliente si ritrova dal BA, contando su `uq_clienti_billing_account`:

* DB (doc auto-generata): `vendite.fn_resolve_termini_pagamento` (termine e modalità di pagamento
  della fattura), `script.fn_get_cliente_testata_documento`, `script.fn_get_search_detail`,
  `vendite.fn_get_contratto_attivo`, `fn_contratto_sovrapposto`, `fn_get_commessa_stato`,
  `fn_get_or_create_commessa`, `fn_list_commesse_emittibili`, `fn_list_consumi_da_pushare`,
  `fn_list_contratti_da_pushare`, `anagrafiche.fn_guard_ba_gestore_globale_storia`; le viste
  `vw_clienti_lista`, `vw_clienti_codice_ba`, `vw_pdp`, `vw_contratti_lista`,
  `vw_dash_fatturazione_contratti`, `dbops.vw_diag_v_clienti_links`;
* BE: `preventivi_repository`, `pricing_diagnose_repository`.

Con la decisione C-5 (strada c) nessuno di questi lettori cambia: un BA resta con un cliente solo.

## 4. Decisioni di Tid

* ✅ **C-1 — la chiave** (Tid, 2026-10-13): **soggetto + utility + azienda emittente**, fra le istanze
  fittizie. Due clienti con la stessa chiave e periodi sovrapposti sono un doppione; con un'altra
  utility o un'altra azienda emittente sono due forniture.
* ✅ **C-2 — nel tempo** (Tid, 2026-10-13): **non ne possono essere attivi due**. La misura è quella
  che il modello usa già per il PDP: **`clienti.periodo`** (`[data_attivazione, data_chiusura)`,
  scritto da `anagrafiche.trgfn_clienti_set_periodo`), non lo stato e non la `validita` del BA. Lo
  stato entra attraverso il periodo:

  | Stato | Periodo | Occupa la chiave? |
  | --- | --- | --- |
  | `AT`, `RS`, `SF`, `SC` (attivo, sospeso) | `[attivazione, ∞)` | sì: un sospeso è ancora la fornitura |
  | `CH`, `CW` (chiuso) | `[attivazione, chiusura)` | solo fino alla chiusura: dopo si apre una catena nuova (C-5) |
  | `AN` (annullato) | `NULL` (il trigger azzera date e periodo) | no |
  | `PR` (pre-contrattuale) | `NULL` finché non c'è `data_attivazione` | no: vedi C-4 |

* ✅ **C-5 — un cliente chiuso non si riapre** (Tid, 2026-10-13). Vale per tutte le utility, con e
  senza PDP. Sullo stesso cliente si ammettono **solo sospensione e riattivazione**. Per tornare si
  apre una **catena nuova**: istanza nuova (collegata alla precedente con `parent_istanza_id`), BA
  nuovo, cliente nuovo, come nel subentro sul PDP. Scartate: (a) riaccendere lo stesso cliente; (b) un
  cliente nuovo sullo stesso BA, che avrebbe tolto «un BA, un cliente» (R-8 di
  [brief-db-istanza-nasce-col-ba](brief-db-istanza-nasce-col-ba.md)) e costretto ogni
  lettore del §3-bis a scegliere fra più clienti. Conseguenze:
  * `uq_clienti_billing_account` resta com'è; il vecchio BA vive per fatture finali e conguagli;
  * **chiuso è uno stato finale**: da `CH`/`CW` non si esce, e `data_chiusura` di un chiuso non si
    cambia. Oggi nessuno lo impedisce (non c'è un grafo delle transizioni del cliente): la riapertura
    non esiste perché nessuno la scrive, non perché il DB la vieti;
  * la guida «Policy sul billing account dopo la disdetta» cita «eventuali riattivazioni future» del
    BA: va riscritta (il BA chiuso non si riattiva; restano fatture finali e conguagli).
* ✅ **C-4 — il pre-contrattuale** (Tid, 2026-10-13): **non blocca**. Un cliente `PR` non ha periodo:
  si può preparare anche mentre un altro con la stessa chiave è attivo (è il caso della catena nuova
  preparata prima della chiusura della vecchia), e il blocco scatta all'**attivazione**. Ma quando lo
  si prepara serve un **avviso, solo avviso**: «esiste già un cliente per questo soggetto, servizio e
  azienda», col codice del suo BA.
  * ⚠️ Un avviso `W_` del catalogo **non basta**: va solo nel log (`script.fn_log_error_only`),
    l'operatore non lo vede. Serve una **lettura** che il BE chiama e il FE mostra, sul modello del
    controllo degli indirizzi duplicati (`useIndirizzoDuplicato`).
  * ⭐ Il DB consegna **una** funzione «clienti con la stessa chiave» (codice BA, stato, periodo), e la
    usano **tutti e due**: il guard che rifiuta (C-2) e la lettura che avvisa. Un predicato solo: se
    fossero due, prima o poi l'avviso direbbe una cosa e il guard un'altra.
* ✅ **C-3 — la creazione manuale davanti a un doppione** (Tid, 2026-10-13): il rifiuto porta nel
  messaggio il **codice del cliente esistente**, cioè il codice del suo BA (il cliente non ha un codice
  suo: lo identifica il BA, `vw_clienti_codice_ba`). Il segnaposto lo riempie il DB; il BE non
  aggiunge niente. Il pulsante «Apri il cliente esistente» resta un possibile passo FE successivo,
  senza ricadute sul DB.

### ⚠️ Il buco sotto la regola: un chiuso senza data di chiusura

`chk_clienti_date_coerenti` controlla solo `data_chiusura >= data_attivazione` quando ci sono
entrambe, e `trgfn_clienti_set_periodo` dice nel commento che in `CH` la data di chiusura «deve
essere valorizzata» ma non lo controlla. Un cliente `CH` con `data_chiusura` NULL ha periodo
`[attivazione, ∞)`: per la regola resta **attivo per sempre** e impedisce la catena nuova. Vale già
oggi per il PDP (`ex_clienti_no_overlap_stesso_pdp`). Si chiude in questo cantiere: stato chiuso
⇒ `data_chiusura` obbligatoria (censire prima i chiusi senza data).

## 4-bis. Seconda analisi e decisioni del 2026-10-14

> Trovate rileggendo il catalogo e i trigger prima di scrivere il codice (team DB, 2026-10-14).

### I fatti di struttura che il §4 non vedeva

* `config.stati_cliente` ha **undici** stati, non otto: oltre a quelli del §4 ci sono `CM` (chiuso
  per morosità), `CF` (chiuso e fatturato) e `AG` (aggregante). La colonna `codice` li raggruppa in
  famiglie (`CH`, `AT`, `SM`, `AN`, `IS`), ma è l'etichetta **modificabile** (linee-guida-sql §6c):
  la logica usa liste di `codice_interno`.
* `trgfn_clienti_set_periodo` controlla le date solo per `CH` (chiusura ≥ attivazione) e `AT`
  (attivazione obbligatoria); gli altri chiusi non hanno nessun controllo.
* Nessuno scrive le date di sospensione e riattivazione del cliente (§3-bis, rettifica).
* L'azienda di un BA, per una regola che non deve dipendere da chi guarda, si legge con
  `script.fn_get_ba_emittente_sr_id_installazione` (collegamento del BA, altrimenti la
  predefinita), come fa già `anagrafiche.fn_guard_istanza_ba_gestore_globale`. ⚠️ Ne segue che la
  chiave di un BA **senza collegamento** cambia se si sposta l'azienda predefinita: la regola va
  controllata anche sui movimenti di `emittenti_fiscali_billing_account` (le stesse quattro
  famiglie di movimento di `trgfn_efba_guard_istanza_emittente`), non solo sulle scritture del
  cliente.
* `istanze_utilities.fittizia` non ha un lock: un'istanza che diventa fittizia porta i suoi clienti
  dentro la regola, e va controllata anche lei.
* `anagrafiche.trgfn_clienti_set_parent_istanza` **azzera** `parent_istanza_id` per ogni cliente
  senza PDP: il collegamento della catena nuova di C-5 sulle fittizie verrebbe cancellato (C-9).

### Le decisioni

* ✅ **C-6 — gli stati e le loro date** (Tid, 2026-10-14). Chiusi sono **`CH`, `CM`, `CW`, `CF`**.
  Da `CH`, `CM`, `CW` si va solo a **`CF`**; `CF` è **terminale** (si determinerà dall'ultima fattura,
  in un cantiere successivo; un'azienda senza utility può fermarsi a `CH` e non usarlo mai). Fra
  attivo e sospeso si va nei due versi. **Ogni stato pretende la sua data.** Il grafo proposto dal
  team DB, ⏳ **da confermare**:

  | Da | A | Data che lo stato d'arrivo pretende |
  | --- | --- | --- |
  | `PR` | `AT`, `AN` | `AT`: `data_attivazione` |
  | `AT` | `RS`, `SF`, `SC`, `CH`, `CM`, `CW`, `AN` | `SF`/`SC`: `data_sospensione`; i chiusi: `data_chiusura` |
  | `RS` | `AT`, `SF`, `SC` | — (`RS` è ancora attivo: tiene `data_attivazione`) |
  | `SF`, `SC` | `AT` (riattivazione), l'altro sospeso, `CH`, `CM`, `CW` | `AT` dopo una sospensione: `data_riattivazione` |
  | `CH`, `CM`, `CW` | `CF` | `data_chiusura` resta quella: **immutabile** da quando il cliente è chiuso |
  | `CF`, `AN` | — | terminali |

  Proposte dentro la tabella, da guardare: `AT → AN` (annullare un attivo azzera le sue date, come
  fa già il trigger del periodo); `RS → AT` (richiesta di sospensione respinta); un sospeso che si
  chiude senza passare da `AT`.
* ✅ **C-7 — `AG`, aggregante** (Tid, 2026-10-14): resta a catalogo come promemoria. Nel sistema
  precedente era il padre dei BA (oggi lo fa il BA padre o di fallback), non una fornitura di una
  utility, ed era escluso dalle statistiche. Per questa regola **non occupa la chiave** e non entra
  nel grafo: la regola conta gli stati per **elenco** (`AT`, `RS`, `SF`, `SC` e i quattro chiusi),
  non per esclusione.
* ✅ **C-8 — le cinque definizioni di «attivo» si riallineano qui** (Tid, 2026-10-14), sul
  periodo: `trgfn_clienti_sync_stato_pdp`, `fn_disdetta_cliente` (che col grafo di C-6 chiude anche
  un sospeso) e, al BE, `PraticheRepository.ha_ba_attivo` (§6). `fn_subentro_cliente` è già
  coerente.
* ✅ **C-9 — la catena delle fittizie** (Tid, 2026-10-14, proposta del team DB). Il predecessore di
  un'istanza fittizia è l'istanza dell'ultimo cliente con la **stessa chiave** (C-1), letta dalla
  stessa funzione del guard e dell'avviso; `set_parent_istanza` si riscrive in questo cantiere, e
  [brief-db-catena-istanze-pdp](../work-in-progress/brief-db-catena-istanze-pdp.md) (D18, che riscrive lo stesso
  trigger per il PDP) lo eredita. Rettifica del fatto del §4-bis: il trigger non **azzerava** il
  parent delle fittizie, **non scattava** (`WHEN pdp_id IS NOT NULL`): l'effetto era lo stesso,
  nessuna catena.
* ✅ **Grafo di C-6 confermato** da Tid il 2026-10-14, compresi i tre passaggi proposti dal team DB.

## 5. Consegna DB (dopo le decisioni)

* la regola (guard alla conferma, sul modello di `E_ISTANZA_SENZA_BA`) e un codice d'errore registrato;
* ⛔ **censimento prima del vincolo**: lo smoke ha creato doppioni su dbdev a ogni giro. Il vincolo
  nuovo va provato contro i dati esistenti e la bonifica scritta prima, altrimenti l'apply si ferma;
* il grafo degli stati e le date che ogni stato pretende (C-5, C-6): da un chiuso si va solo a `CF`,
  `data_chiusura` immutabile, col censimento delle righe fuori regola prima del vincolo;
* la regola controllata anche sui movimenti dell'azienda del BA e su `fittizia` (§4-bis);
* le definizioni di «attivo» del DB (§3-bis) riallineate sul periodo (C-8);
* la catena delle fittizie, se C-9 resta qui;
* la funzione «clienti con la stessa chiave» (C-4), letta dal guard e dall'avviso;
* pgTAP: un secondo cliente manuale con la stessa chiave è rifiutato; con un altro emittente o
  un'altra utility passa; un sospeso blocca; dopo la chiusura la catena nuova (istanza, BA, cliente)
  passa; riportare un chiuso ad attivo è rifiutato; l'annullato non blocca; un `CH` senza data è
  rifiutato.

## 5-bis. Consegna DB scritta (team DB, 2026-10-14)

### 5-bis.1 I changeSet

| changeSet | Che cosa |
| --- | --- |
| `00_schema/config/20261014-08` | nasce `config.transizioni_stati_cliente` (il grafo di C-6) |
| `80_data/changelog/20261014-09` | seed del grafo, `transizioni_stati_cliente.csv` (25 passaggi; chiave del mirror la coppia di stati) |
| `20_code/anagrafiche/20261014-10` | `anagrafiche.fn_clienti_stessa_chiave` (C-4): il predicato unico, DEFINER |
| `20_code/anagrafiche/20261014-11` | `fn_guard_cliente_chiave_unica` (E_CLIENTE_STESSA_CHIAVE) e i due lettori dei movimenti (`_di`, `_gestore_globale`) |
| `20_code/anagrafiche/20261014-12` | constraint trigger al COMMIT su `clienti` (movimento 1) |
| `20_code/anagrafiche/20261014-13` | constraint trigger al COMMIT sul collegamento BA → azienda (movimenti 2 e 4) |
| `20_code/anagrafiche/20261014-14` | constraint trigger al COMMIT su `istanze_utilities.fittizia` (movimento 3) |
| `20_code/anagrafiche/20261014-15` | `trgfn_clienti_guard_stato_date` (BEFORE, `a10`): grafo, chiusura ferma da chiuso, data per stato |
| `20_code/anagrafiche/20261014-16` | `trgfn_clienti_set_periodo` deriva soltanto: via le due copie (E_DATA_APERTURA, E_DATA_CHIUSURA) |
| `20_code/anagrafiche/20261014-17` | `trgfn_clienti_set_parent_istanza`: la catena delle fittizie per chiave (C-9); WHEN nuovo |
| `20_code/anagrafiche/20261014-18` | `fn_check_pdp_occupato` + `trgfn_clienti_sync_stato_pdp` sul periodo (C-8); eventi con le date |
| `20_code/script/20261014-19` | `fn_disdetta_cliente` delega al grafo: chiude anche un sospeso; via E_CLIENTE_NON_ATTIVO |
| `20_code/dbops/20261014-20` | `dbops.fn_pgtap_crea_cliente` scrive le date per stato (anche la sospensione), per `codice_interno` |

Codici nuovi (CSV `codici_errore`/`messaggi_errore`, id 1308-1311): `E_CLIENTE_STESSA_CHIAVE`,
`E_CLIENTE_STATO_TRANSIZIONE_INVALIDA`, `E_CLIENTE_STATO_SENZA_DATA`,
`E_CLIENTE_DATA_CHIUSURA_IMMUTABILE`. Riscritta la frase di `E_DATA_CHIUSURA` (ora la solleva il
guard, per ogni stato, col codice del BA). Ritirati (`obsoleto_dal` 2026-10-14):
`E_DATA_APERTURA`, `E_CLIENTE_NON_ATTIVO` — nessun punto del database li solleva più.
`E_DATA_CESSAZIONE_INVALIDA` resta: parla del parametro della disdetta prima che diventi
`data_chiusura`.

Scelte di forma, dichiarate:

* **niente CHECK sulle date per stato**: lo stato è una FK verso il catalogo, e un CHECK non legge
  un'altra tabella; la regola sta nel guard BEFORE. Quindi l'apply **non** rilegge il pregresso:
  una riga fuori regola resta finché qualcuno non la scrive, e allora viene rifiutata;
* **l'INSERT non passa dal grafo** (linee-guida-sql §7c punto 6): un cliente nasce in qualunque
  stato, con le date che quello stato pretende;
* **AG** non entra nel grafo né nella chiave (C-7); da AG non si esce e ad AG non si arriva con un
  UPDATE;
* il PDP ora va ad ATT **solo da DISP**, e torna DISP **solo da ATT**: DTEC e DISM non si toccano
  (prima un AT portava ad ATT da qualunque stato, anche DISM, contro il commento della funzione).

### 5-bis.2 La prova (scratch `zeroerp_ci`, 2026-10-14)

SQL estratto dai changeSet (i `createTable`/`loadUpdateData` resi con `updateSQL` offline, senza
preCondition) + i mirror completi di `classi_errore`, `codici_errore`, `messaggi_errore` (upsert di
**tutte** le righe, §11.2), dentro una transazione annullata, da owner:

* `anagrafiche/test-cliente-manuale-chiave-unica-v1.sql` (nuovo): **29/29**;
* 100 pgTAP che toccano clienti, istanze, BA, collegamenti BA → azienda, codici d'errore, più i
  presidi trasversali (`riferimenti-morti`, `catalogo-messaggi-errore-completo`,
  `vw-codici-errore-*`, `storico-scope-policy`, `stati-check-scrittori`), ognuno **senza e con**
  l'SQL in testa: identici in 99; il centesimo, `rls/test-rls-clienti.sql`, moriva nella fixture
  col rifiuto nuovo (costruiva due clienti attivi dello stesso soggetto, utility e azienda: il
  doppione che la regola vieta). Corretto il file: la scheda SHOP va su un'altra utility, che al
  test 9 non cambia niente (serve lo stesso proprietario con due canali). Ora 13/13 prima e dopo.
  I 24 rossi di partenza sono gli stessi prima e dopo;
* il builder `fn_pgtap_crea_cliente` crea un cliente in tutti gli undici stati; i suoi quattro
  consumatori verdi;
* cancelli statici della CI (letterali, runOnChange, preCondition, timestamp, DDL su trigger
  generati, preambolo pgTAP, v1, GRANT batch): verdi.

⚠️ Non provato prima dell'apply: la corsa **come app** (la prova gira da owner, senza RLS); il
riallineamento del PDP sul periodo (`sync_stato_pdp`, C-8) non ha un pgTAP suo (§7).

### 5-bis.3 Il censimento e la bonifica

La regola è un trigger: l'apply non si ferma sui dati vecchi. Le righe fuori regola vengono
rifiutate alla **prossima scrittura**. Visto come app su dbdev (perimetro dell'operatore pgTAP, fatto
datato del 2026-10-14): nessun cliente fuori dalle date, **un doppione** — clienti 115 e 121, BA
`TST-BA-UPOL-004` e `TST-BA-UP4-927C`, dati di prova. Il censimento completo va fatto **da owner**:

```sql
-- doppioni (C-1, C-2)
SELECT a.id, b.id, ba_a.codice, ba_b.codice, a.periodo, b.periodo
  FROM anagrafiche.clienti a
  JOIN anagrafiche.clienti b
    ON a.id < b.id AND a.soggetto_ruolo_id = b.soggetto_ruolo_id
   AND a.utility_id = b.utility_id AND a.periodo && b.periodo
  JOIN anagrafiche.istanze_utilities ia ON ia.id = a.istanza_utility_id AND ia.fittizia
  JOIN anagrafiche.istanze_utilities ib ON ib.id = b.istanza_utility_id AND ib.fittizia
  JOIN config.stati_cliente sa ON sa.id = a.stato_cliente_id
  JOIN config.stati_cliente sb ON sb.id = b.stato_cliente_id
  JOIN anagrafiche.billing_account ba_a ON ba_a.id = a.billing_account_id
  JOIN anagrafiche.billing_account ba_b ON ba_b.id = b.billing_account_id
 WHERE sa.codice_interno IN ('AT','RS','SF','SC','CH','CM','CW','CF')
   AND sb.codice_interno IN ('AT','RS','SF','SC','CH','CM','CW','CF')
   AND script.fn_get_ba_emittente_sr_id_installazione(a.billing_account_id)
       IS NOT DISTINCT FROM script.fn_get_ba_emittente_sr_id_installazione(b.billing_account_id);

-- stati senza la loro data (C-6)
SELECT c.id, sc.codice_interno, c.data_attivazione, c.data_sospensione, c.data_chiusura
  FROM anagrafiche.clienti c JOIN config.stati_cliente sc ON sc.id = c.stato_cliente_id
 WHERE (sc.codice_interno IN ('AT','RS','SF','SC','CH','CM','CW','CF') AND c.data_attivazione IS NULL)
    OR (sc.codice_interno IN ('SF','SC') AND c.data_sospensione IS NULL)
    OR (sc.codice_interno IN ('CH','CM','CW','CF') AND c.data_chiusura IS NULL)
    OR c.data_chiusura < c.data_attivazione;
```

Bonifica proposta (dati di sviluppo, a mano, decide Tid): il secondo cliente di ogni coppia va
annullato (`AN`, il trigger del periodo ne azzera le date) o chiuso il giorno prima che l'altro
cominci. Lo smoke continuerà a crearne fino al giro BE (§6): dopo l'apply il suo passo viene
rifiutato, che è l'esito atteso.

### 5-bis.4 I pgTAP per Tid

✅ Apply e corsa di Tid del 2026-10-14: nessuna regressione.


* nuovo: `db/pgtap/anagrafiche/test-cliente-manuale-chiave-unica-v1.sql` (plan 29);
* corretto: `db/pgtap/rls/test-rls-clienti.sql` (la fixture, vedi 5-bis.2);
* da guardare nella corsa: il movimento 4 (test 25) passa dal cancello della storia e dai guard
  dell'istanza e dell'albero, che guardano **tutti** i BA scollegati: un dato già fuori regola
  lo fermerebbe con un altro codice (stesso limite di `test-istanza-ba-gestore-globale-v1`).

## 6. Ricaduta BE/FE

* `ClienteService`: `E_CLIENTE_STESSA_CHIAVE` (classe `CONFLITTO_STATO`, 409) col messaggio del DB,
  che porta già il codice del BA del cliente esistente (C-3). ⚠️ Arriva **al COMMIT** (constraint
  trigger differito, come `E_ISTANZA_SENZA_BA`), non all'`INSERT` del cliente: va mappato dove la
  transazione della creazione si chiude. Nessun pre-check nel BE: la regola ha una sede sola;
* **avviso del pre-contrattuale (C-4)**: dove si prepara un cliente `PR` (oggi dalla pratica), il BE
  chiama `anagrafiche.fn_clienti_stessa_chiave(soggetto_ruolo_id, utility_id,
  emittente_soggetto_ruolo_id)` — l'azienda è quella del BA per l'installazione
  (`script.fn_get_ba_emittente_sr_id_installazione`) — e tiene le righe col periodo che contiene
  oggi o che comincia dopo; il FE mostra l'avviso col codice del BA senza bloccare, come per gli
  indirizzi duplicati. ⚠️ La funzione è DEFINER: il BE la chiama con l'azienda del BA in lavorazione,
  mai con un'azienda scelta dal client;
* **`PraticheRepository.ha_ba_attivo` sul periodo** (C-8): oggi legge «`data_attivazione NOT NULL
  AND data_chiusura IS NULL`»; la misura del modello è `clienti.periodo @> script.fn_data_operativa()`;
* **codici**: tre nuovi oltre al primo (`E_CLIENTE_STATO_TRANSIZIONE_INVALIDA`,
  `E_CLIENTE_STATO_SENZA_DATA` col campo, `E_CLIENTE_DATA_CHIUSURA_IMMUTABILE`); `E_DATA_APERTURA` e
  `E_CLIENTE_NON_ATTIVO` ritirati: vanno tolti da `error_messages_fallback.py` e
  `error_ui_overrides.py`, e `error_policies_generated.py` si rigenera;
* **nessun percorso di riapertura** (C-5): se un giorno il BE esporrà disdetta e subentro, il «torna»
  del cliente è una catena nuova (istanza, BA, cliente), mai un cambio di stato del chiuso;
* `smoke-test-clienti.sh`: il passo oggi in «DOMANDA APERTA» si aspetta il rifiuto
  (`E_CLIENTE_STESSA_CHIAVE`), ed esce da `baseline-smoke.tsv`.

## 6-bis. Giro BE fatto (2026-10-15)

* **`E_CLIENTE_STESSA_CHIAVE`**: nessuna modifica al service. L'errore del constraint trigger esce
  dal `transaction.atomic()` di `ClientiService.crea_cliente` al COMMIT e passa dalla traduzione
  generica degli errori DB: 409 col messaggio del DB, che porta il codice del BA esistente (C-3).
  Nessun pre-check. Provato sul DB vero: `anagrafiche/tests/db/test_cliente_stessa_chiave_db.py`
  (il COMMIT simulato con `SET CONSTRAINTS ALL IMMEDIATE`);
* **`PraticheRepository.ha_ba_attivo`** legge `cl.periodo @> script.fn_data_operativa()` (C-8).
  Provato sul DB vero: `pratiche/tests/db/test_ha_ba_attivo_db.py` (attivo oggi, attivazione
  futura, chiusura futura, chiuso ieri, annullato); col criterio vecchio vanno rossi i due casi in
  cui i criteri divergono;
* **codici**: `error_policies_generated.py` rigenerato (i quattro nuovi più `E_STATISTICHE_MANCANTI`
  di un altro cantiere, i due ritirati in `CODICI_RITIRATI`); i ripieghi dei cinque codici vivi
  nuovi in `error_messages_fallback.py`. ⚠️ **Scostamento dal §6, confermato da Tid il
  2026-10-15**: `E_DATA_APERTURA` ed `E_CLIENTE_NON_ATTIVO` **restano** nel ripiego e negli
  override. Un codice ritirato continua a risolvere, perché le sue righe in `dbops.error_log`
  devono restare leggibili; il presidio delle promesse `highlight` esclude i ritirati per
  costruzione;
* **avviso del pre-contrattuale (C-4)**: non fatto, per decisione di Tid del 2026-10-15. Oggi nessuno
  prepara un cliente `PR` (il BE crea sempre `AT`, la pratica non crea clienti, a DB lo scrive solo
  il builder pgTAP): l'avviso non ha un punto in cui agganciarsi. Passa ai residui (§7);
* **smoke**: il passo 8 di `smoke-test-clienti.sh` si aspetta il 409 (commit `78b243f0f`). Verde il
  2026-10-15, 16 OK su 16, dopo il reload dei worker (senza, il backend in esecuzione aveva il
  modulo generato vecchio e rispondeva 400: il codice non era a catalogo per lui). Uscito da
  `baseline-smoke.tsv`;
* test: `apps.anagrafiche`, `apps.pratiche`, `apps.core` con `ZEROERP_TEST_DB_E2E=1`, 2731 verdi
  (1 skip); ruff pulito; mypy senza rilievi nuovi.

## 7. Residui — parte dello sviluppo delle utility (Tid, 2026-10-15)

* **l'avviso del pre-contrattuale (C-4)** nasce col percorso che prepara un cliente `PR`, che
  arriverà con le pratiche (Tid, 2026-10-15). Il BE chiamerà `anagrafiche.fn_clienti_stessa_chiave`
  con l'azienda del BA in lavorazione e il FE mostrerà l'avviso senza bloccare (§6); la funzione a
  DB c'è già e oggi non ha un chiamante;

* **il PDP libero alla data di chiusura**: `sync_stato_pdp` ricalcola quando si scrive il cliente;
  una chiusura con data futura libera il PDP alla prossima scrittura, non quel giorno. Serve un giro
  per data (job notturno o estensione del framework delle chiusure per scadenza);
* **un pgTAP per il PDP sul periodo** (C-8): vuole una utility con PDP e il suo punto;
* **la catena sul PDP** resta con i difetti di D18 (l'annullo non ricalcola, un anello solo, la
  lettura sotto RLS): [brief-db-catena-istanze-pdp](../work-in-progress/brief-db-catena-istanze-pdp.md) eredita anche
  il ramo delle fittizie;
* **la data di attivazione di un chiuso** non è ferma (C-5 ha fermato la chiusura): cambiandola si
  sposta l'inizio del periodo di un cliente storico. Da decidere, di Tid.

## 8. Archiviazione (2026-10-15)

Archiviato dal team DB dopo il giro BE (§6-bis, commit `8aaf95296`). I residui del §7 non hanno un
brief loro: per decisione di Tid del 2026-10-15 fanno parte dello sviluppo delle utility, e lì si
riprendono. La catena sul PDP resta in
[brief-db-catena-istanze-pdp](../work-in-progress/brief-db-catena-istanze-pdp.md) (D18) col ramo delle
fittizie. D33 chiusa in [migliorie-generali-da-test-valutazione](../work-in-progress/migliorie-generali-da-test-valutazione.md) §7.
