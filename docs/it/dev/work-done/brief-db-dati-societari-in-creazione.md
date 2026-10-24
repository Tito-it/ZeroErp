# Brief DB — Dati societari in creazione: la porta di creazione non scrive tutta la sezione

## ⏭️ Chi riparte — aggiornato al 2026-10-22

**Riparte: nessuno. ✅ Chiuso e archiviato il 2026-10-22: DB il 19-10, BE/FE e collaudo il 22-10.**

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ~~Tid~~ | ~~decide E-1~~ ✅ **(a)**, 2026-10-19 | §4 | — |
| 2 | ~~team DB~~ | ~~changeSet `20261020-01…03`, pgTAP, manuali~~ ✅ 2026-10-19 | §5 | — |
| 3 | ~~Tid~~ | ~~apply e corsa pgTAP~~ ✅ 2026-10-19 (dbdev e scratch, pgTAP verde) | §5.1 | — |
| 4 | ~~sessione BE/FE~~ | ~~`crea_soggetto_pg` / `_create_pf`, via la prop `showDataCostituzione`~~ ✅ 2026-10-22 | §6.1 | — |
| 5 | ~~Tid~~ | ~~collaudo a video: SC e DI create con la sezione intera~~ ✅ 2026-10-22 | §6 | — |
| 6 | ~~chi chiude~~ | ~~archiviazione, riga di PROJECT_CONTEXT, D34 nel registro DB~~ ✅ 2026-10-22 | — | — |

Decisioni aperte di Tid: nessuna (D-1 in §3.1 applicata; il BB BE di §6.1 ha l'ok di Tid del 2026-10-22). Lavoro da committare: il giro BE/FE (§6.1) e la chiusura, su `dev/backend-tid`.

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-14, chiudendo
> `work-done/brief-db-dati-fiscali-e-societari-del-soggetto.md` (§9.5, richiesta della sessione BE).
> **A chi:** team DB; poi BE/FE (§6).
> **Stato:** ✅ lato DB chiuso il 2026-10-19 (E-1 (a)): applicato su dbdev e scratch, pgTAP verde.
> ✅ BE/FE il 2026-10-22 (§6.1); collaudo di Tid riuscito e chiusura lo stesso giorno.

## 1. Il difetto, sul modello

Dal 2026-10-10 la sezione «dati societari» ha **una porta sola**, il verbo
`anagrafiche.fn_scrivi_dati_societari`, che riceve lo **stato intero** (B-1, B-2, B-4 del brief
d'origine). In modifica la sezione arriva intera. **In creazione no**, per due strade:

| Natura | Porta di creazione | Cosa si perde |
| --- | --- | --- |
| SP, SC, ENC | `anagrafiche.fn_crea_soggetto_pg` | la **data di costituzione**: la funzione chiama il verbo con `p_data_costituzione := NULL` e non ha un parametro per riceverla |
| DI (ditta individuale, `dati_societari_policy = OPTIONAL`) | `anagrafiche.fn_crea_soggetto_pf` | **tutta la sezione**: la funzione non conosce i dati societari |

Fonti: corpo vivo di `fn_crea_soggetto_pg` (rev `20261011-01`) e firma di `fn_crea_soggetto_pf` (rev
`20261009-26`), doc auto-gen letta il 2026-10-14. Riletto il 2026-10-19: le due funzioni sono state
riscritte il 18-10 per lo stato (`20261018-89` pf, `-91` pg), il difetto è lo stesso; corpo vivo =
YAML su dbdev e sullo scratch.

### 1.1 Ditta individuale: la sezione si perde in silenzio

Il FE mostra la sezione quando la natura non la esclude (`useSoggettoForm.showDatiSocietari`:
policy diversa da `NONE`), quindi anche per la DI. In creazione `SoggettoDrawer.handleSave` mette
`dati_societari` nel payload. Ma `SoggettiService.create_soggetto` manda la DI in `_create_pf`, che
la chiave non la legge, e `fn_crea_soggetto_pf` non ha parametri per riceverla. L'operatore compila
forma, REA, canale FE e PEC, legge «creato», e alla riapertura la sezione è vuota.

Lo stesso difetto che la Parte B del brief d'origine ha chiuso in modifica («salvato», e alla
riapertura i valori vecchi). In creazione è rimasto aperto sulla porta delle persone fisiche.

### 1.2 Data di costituzione: oggi il FE la nasconde

Per non perderla in silenzio, il FE offre la data **solo in modifica** (`DatiSocietariForm.vue`,
prop `showDataCostituzione`). È un ripiego: la regola «in creazione questo campo non c'è» non è del
dominio, è un limite della porta.

## 2. Che cosa NON cambia

- Il verbo resta l'unica sede della scrittura e non cambia firma. Le regole (forma ammessa dalla
  natura, REA e capitale per policy, canale FE) restano nei suoi trigger.
- Nessuna regola nuova, nessun codice di errore nuovo.

## 3. Che cosa si propone

**Per `fn_crea_soggetto_pg`:** un parametro `p_data_costituzione` **in coda**, con `DEFAULT NULL`,
passato al verbo al posto del `NULL`. Tipo ancorato alla colonna
(`anagrafiche.dati_societari.data_costituzione%TYPE`, §7e di `linee-guida-sql.md`).

⚠️ Per il team DB: cambia la firma, quindi `CREATE OR REPLACE` non basta. Serve `DROP FUNCTION` della
firma vecchia e `CREATE`; altrimenti nascono due overload e una chiamata con i soli parametri vecchi
diventa ambigua. Dopo il `DROP` vanno rimessi `COMMENT` e privilegi. Censire i chiamanti: il BE
(`soggetti_repository.py`, parametri nominati) e 4 pgTAP (`test-soggetti-sesso-policy-v1`,
`test-fn-scrivi-dati-societari-v1`, `test-emittenti-fiscali`, `dbops/test-character-n-v1`). Nessuna
funzione del DB la chiama (doc auto-gen, 2026-10-14).

**Per la ditta individuale:** E-1 (a), decisa da Tid il 2026-10-19 (§4).

### 3.1 D-1 della sessione: la regola «quando si scrive alla nascita» diventa un BB

`fn_crea_soggetto_pg` decide da sé se chiamare il verbo: policy `REQUIRED`, oppure `OPTIONAL` con almeno
un campo della sezione. Con E-1 (a) la stessa decisione serve a `fn_crea_soggetto_pf`: è la **seconda
copia**, e per la regola del 2 si estrae nello stesso giro in
**`anagrafiche.fn_scrivi_dati_societari_alla_nascita`** (`20261020-01`), che le due porte chiamano al
posto del verbo. Il BB non aggiunge regole: legge la policy del soggetto e, se la sezione va scritta,
passa lo stato intero al verbo.

- **La sezione «c'è»** quando almeno un campo ha un valore: forma, provincia o numero REA, capitale,
  canale FE, PEC, codice SDI, data di costituzione. I testi vuoti non contano, perché il verbo li
  scriverebbe comunque `NULL`. Socio unico e liquidazione da soli **non** contano: hanno sempre un
  valore (default dai parametri) e il form li manda anche quando la sezione è vuota. È la regola già
  in uso in `fn_crea_soggetto_pg`, a cui si aggiunge la data.
- **`REQUIRED`** → si scrive sempre (senza forma, la riga la rifiuta il `NOT NULL` della forma, come oggi).
- **Sezione passata a una natura `NONE`** → si scrive, e la rifiuta il guard della natura
  (`E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO`). ⚠️ Per `fn_crea_soggetto_pg` è un **cambio**: oggi
  scarta la sezione in silenzio. Il seed non ha nature PG `NONE` (dato del 2026-10-19), ma il modello
  le ammette, e scartare in silenzio è il difetto di §1.1. Una regola sola per le due porte.

## 4. Decisioni attese da Tid

| # | Domanda | Proposta della sessione DB |
| --- | --- | --- |
| **E-1** ✅ (a), Tid 2026-10-19 | **Dove si scrive la sezione di una DI che nasce.** | **(a)** `fn_crea_soggetto_pf` riceve i dati societari, con parametri in coda, e chiama il verbo come `fn_crea_soggetto_pg` (B-4): la creazione è **una** chiamata, atomica nel DB, e le due porte si comportano allo stesso modo. **(b)** Il BE, nella stessa transazione, crea la persona fisica e poi chiama il verbo: niente firma nuova, ma la creazione di una DI diventa un'orchestrazione del BE, e le due porte divergono. ⭐ Proposta: **(a)**. È la stessa scelta già fatta per le società, e il «soggetto più la sua sezione» resta una sola operazione del DB. |

## 5. Lavoro DB (dopo E-1)

- changeSet `20_code/anagrafiche`: `fn_crea_soggetto_pg` con `p_data_costituzione` (§3);
- con E-1 (a): changeSet `20_code/anagrafiche` per `fn_crea_soggetto_pf`, con i parametri della
  sezione in coda e la chiamata al verbo, solo se la natura ammette i dati societari e i parametri
  sono passati (la regola `REQUIRED`/`NONE` resta al guard `trgfn_soggetti_guard_dati_societari_required`);
- pgTAP: SC creata con data di costituzione, letta dalla tabella; DI creata con forma «Ditta
  individuale» e canale FE; DI creata **senza** sezione (policy `OPTIONAL`); PR con la sezione →
  rifiuto dal guard della natura, come oggi in modifica;
- manuali `fn_crea_soggetto_pg`, `fn_crea_soggetto_pf`, `dati_societari`.

### 5.1 Fatto (2026-10-19)

| changeSet | Cosa |
| --- | --- |
| `20_code/anagrafiche/20261020-01-create-fn-scrivi-dati-societari-alla-nascita` | il BB della nascita (§3.1), `SECURITY INVOKER`, scrive col verbo; nello stesso changeSet il COMMENT del verbo (fra i chiamanti il BB al posto di `fn_crea_soggetto_pg`), che il rollback ripristina |
| `…/20261020-02-update-fn-crea-soggetto-pg-data-costituzione` | `p_data_costituzione` in coda, Step 3 dal BB; DROP della firma vecchia (preCondition: 16 argomenti) |
| `…/20261020-03-update-fn-crea-soggetto-pf-dati-societari` | i dieci campi in coda, stessi nomi di pg; Step 3 dal BB dopo il contatto; DROP della firma vecchia (preCondition: 11 argomenti) |

Il 20-10 perché il 19 era pieno fino al `-99`. Corpo dagli YAML del 18-10 (`-91`/`-89`),
verificati identici al vivo (`prosrc`) su dbdev e scratch; firma, `RETURNS`, `DECLARE`, `DROP` e
`COMMENT` ancorati con `%TYPE`; nessuna clausola `SET`/`COST` da ripetere; nessun GRANT da rimettere
(INVOKER, mai GRANT espliciti, come `20261009-26`).

**pgTAP nuovo:** `db/pgtap/anagrafiche/test-dati-societari-alla-nascita-v1.sql` (plan 18): struttura
(nessun overload, INVOKER, parametri in coda, regola del 2 sul corpo), il BB sul soggetto, SRL con
la data, ente con i soli socio/liquidazione senza riga, DI con la sezione intera, DI senza sezione,
testi vuoti, atomicità (canale C senza SDI → il soggetto non nasce), sezione senza forma (23502),
PR con la sezione → `E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO`, PR senza sezione.
⚠️ Il PR del test 17 passa la sola data: con una forma parlerebbe prima il guard BEFORE ROW della
forma (`E_FORMA_GIURIDICA_NON_AMMESSA_PER_TIPO_SOGGETTO`, ordine per nome). Il rifiuto c'è in
entrambi i casi.

**Prova pre-apply** (scratch `zeroerp_ruoli`, owner, SQL ESTRATTO dagli YAML in transazione
annullata, md5 di corpo e COMMENT controllati dopo: scratch pulito):
- il pgTAP nuovo: **18/18** con l'SQL estratto; senza, 5 rossi e la corsa si ferma (vede il difetto);
- regressione, senza/con, su 31 pgTAP che chiamano le due porte, `fn_crea_operatore*` o il verbo,
  più `dbops/test-riferimenti-morti-v1` (plpgsql_check su ogni funzione): **identici** prima e dopo.
  Rossi preesistenti e uguali nelle due corse: `test-fn-scrivi-dati-societari-v1` #22 e
  `test-soggetti-titoli-iva-tipo-soggetto-v1` #14 (rossi da owner, dichiarati),
  `test-identita-digitali-guard-coerenza` (in baseline, la fixture muore prima: cieco qui);
- non provato: `test-soggetti-indirizzi-required` (quattro transazioni nel file, la composizione
  con l'SQL estratto non si fa alla cieca) → lo dice la corsa di Tid;
- firme dopo l'SQL estratto: una funzione per nome; il rollback del `-01` toglie il BB e rimette
  il COMMENT del verbo;
- guardrail del repo: verdi sui file nuovi (`pgtap_preambolo` è rosso per un file già committato
  e non di questo cantiere, `dbops/test-automazioni-guasto-ambiente-rilanciato-v1.sql`).

⚠️ Il rollback di `-02`/`-03` è forward-only (`SELECT 1`, come `20261009-26`): tornando indietro
da qui pg e pf resterebbero col corpo nuovo e, dopo il rollback del `-01`, senza il BB.

## 6. Ricadute BE/FE (dopo l'apply)

- **BE:** `crea_soggetto_pg` e `_create_pg` passano `data_costituzione` (`p_data_costituzione`).
  Con E-1 (a), `_create_pf` legge la chiave `dati_societari` (stesso contratto di
  `_valida_dati_societari`) e la passa a `crea_soggetto_pf` con parametri nominati: **gli stessi
  nomi** di `fn_crea_soggetto_pg` (`p_forma_giuridica_id`, `p_id_prov_iscri_rea`, `p_iscrizione_rea`,
  `p_capitale_sociale`, `p_socio_unico`, `p_liquidazione`, `p_destinatario_fe`, `p_pec_fatturazione`,
  `p_codice_sdi`, `p_data_costituzione`). Test sul DB vero: SC con data, DI con la sezione.
  Le chiamate di oggi restano valide anche prima dell'allineamento (parametri nuovi con DEFAULT).
- **BE, da sapere:** una sezione inviata per un privato (natura `NONE`) ora si **rifiuta**
  (`E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO`, già a catalogo) invece di sparire. Il FE oggi non
  la mostra per il privato; se il payload la porta lo stesso con i soli socio unico e liquidazione
  di default, quei due **non** fanno la sezione e non si rifiuta niente.
- **FE:** via la prop `showDataCostituzione` (il campo si mostra sempre, come gli altri della
  sezione). Il ramo di creazione di `handleSave` già manda la sezione: niente da cambiare.
- ✅ Il DB è pronto dal 2026-10-19 (`20261020-01…03` applicati): BE/FE possono partire.

### 6.1 Fatto (2026-10-22, `dev/backend-tid`)

- **Repository** (`soggetti_repository.py`): BB della regola del 2, ok Tid 2026-10-22. Il binding
  dei dieci parametri della sezione (`_SQL_PARAMETRI_DATI_SOCIETARI` + `_parametri_dati_societari`,
  chiavi in `DATI_SOCIETARI_COLS`) era scritto due volte (pg e verbo), la DI ne avrebbe aggiunto una
  terza: ora lo usano `crea_soggetto_pg`, `crea_soggetto_pf` e `scrivi_dati_societari`, che ricevono
  la sezione come un dict (`dati_societari`). Registrato nel catalogo BB backend
  (§«Anagrafiche — Soggetti»).
- **Service** (`soggetti_service.py`): `_create_pf` e `_create_pg` leggono la sezione con
  `_dati_societari_in_creazione` → `_valida_dati_societari`, lo stesso contratto della PATCH
  (chiave assente = nessuna sezione). ⚠️ Per la PG è un cambio: una chiave ignota, un `null` o un
  valore malformato prima passavano o sparivano, ora sono 400 `E_ANAG_VALIDAZIONE`. La PF legge
  anche il REA duplicato (`uq_ds_prov_cea` → campo `iscrizione_rea`), come la PG.
- **FE**: via la prop `showDataCostituzione` da `DatiSocietariForm.vue` e dal `SoggettoDrawer`;
  `handleSave` invariato. Nel collaudo, su richiesta di Tid, il layout: forma giuridica e data di
  costituzione affiancate, canale FE con accanto la PEC o il codice SDI che il canale chiede
  (`DatiSocietariForm.vue`); cognome e nome affiancati, sesso, data e comune di nascita su una riga
  (~25/30/45, `SoggettoForm.vue`).
- **Test**: `test_soggetti_service` 40-43 (sezione intera alla porta pg con la data, DI con la
  sezione, chiave assente → `None`, contratto in creazione per PF e PG); `test_dati_fiscali_societari_db`
  17-19 sul DB vero (SC creata con la data, DI con la sezione intera, PR con la sezione →
  `E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO`). `apps.anagrafiche` con `ZEROERP_TEST_DB_E2E=1`:
  549 verdi; mypy senza rilievi nuovi; ruff ed eslint puliti; vitest `src/anagrafiche` 24/24.

## 7. Registro

| Data | Cosa |
| --- | --- |
| 2026-10-14 | Aperto chiudendo `brief-db-dati-fiscali-e-societari-del-soggetto` (§9.5, richiesta della sessione BE sulla data di costituzione). Rileggendo la creazione: anche la DI perde la sezione (§1.1), entra qui. In attesa di E-1. |
| 2026-10-19 | Tid decide E-1 (a) e dà il via. Ripreso dalle revisioni del 18-10 (`20261018-89`/`-91`, stato dal BB). D-1 della sessione (§3.1): la regola della nascita va in un BB, `20261020-01`; `-02` pg, `-03` pf. |
| 2026-10-19 | Lato DB scritto e provato pre-apply (§5.1): `20261020-01…03`, pgTAP nuovo 18/18, regressione identica su 32 file. Riparte Tid per l'apply. |
| 2026-10-19 | Tid applica `20261020-01…03` (dbdev 16:59:25, scratch 16:59:46, `databasechangelog`: EXECUTED) e la corsa pgTAP è verde. Lato DB finito; riparte BE/FE (§6). |
| 2026-10-22 | Giro BE/FE (§6.1): BB del binding della sezione nel repository (ok Tid), contratto unico in creazione, via `showDataCostituzione`; test BE sul DB vero verdi. Riparte Tid per il collaudo. |
| 2026-10-22 | Collaudo di Tid riuscito (SC e DI create con la sezione intera; layout del form rivisto). Chiuso: archiviato in `work-done/`, riga di PROJECT_CONTEXT, D34 chiuso nel registro DB. |
