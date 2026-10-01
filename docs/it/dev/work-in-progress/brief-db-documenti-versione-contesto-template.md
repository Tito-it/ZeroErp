# Brief DB + BE — Documenti: il patto fra la versione di un template e la forma dei dati che legge

> **Chi scrive:** team DB (`dev/db-tid`), 2026-09-29. **A chi:** team DB e backend
> (`dev/backend-tid`); Tid per le decisioni di §7.
> **Origine:** §9.8.4 di [brief-db-liste-righe-documento.md](brief-db-liste-righe-documento.md)
> (la stampa della fattura dalla lista delle righe).
> **Stato:** ✅ **lato DB APPLICATO su dbdev il 2026-09-30, pgTAP verdi (corsa di Tid)**
> (`20260930-14 → -21` + codici 1169-1170). ✅ **Giro BE/FE fatto il 2026-09-30** (§12: R-1 … R-5,
> test Django verdi anche sul DB vero). ✅ **Fattura alla forma 2 a codice il 2026-09-30** (§13:
> builder, ritiro di `list_fattura_righe`, corpo della v4 nel repo). ⏳ Resta a Tid: riavviare il backend,
> poi creare la BOZZA v4 dall'app e pubblicarla (§13.2, in quest'ordine). ✅ Decisione di Tid
> (2026-09-29): si fa tutto, per TUTTI i documenti; ✅ D-C1 → D-C4 accettate il 2026-09-29 (§7).
>
> **Da leggere per primo: §8 (che cosa è stato scritto, e dove si discosta da §4) e §10 (le richieste
> al BE, che dopo l'apply sono BLOCCANTI: la pubblicazione e la creazione di una versione dal
> backend muoiono finché non le fa).**
>
> **In una riga:** oggi una versione di template può leggere dati di una forma diversa da quella
> che il backend le prepara, e stampare un documento **incompleto senza nessun errore**. Ogni
> versione dichiara la forma che legge, e il sistema rifiuta di stampare se la forma non torna.

---

## 1. Il problema, in parole semplici

Un PDF nasce da due pezzi:

* il **template**, il modello grafico, salvato a DB e **versionato**
  (`documenti.template_documenti_versioni`);
* il **contesto**, i dati che un builder del backend prepara (testata, righe, totali…).

Il template legge i dati **aspettandosi una certa forma**. Se la forma cambia e il template no,
Jinja non si lamenta: le chiavi che non trova diventano vuote. Il PDF esce, e mancano dei pezzi.

**Il caso che l'ha fatto emergere** (brief liste, §9.8.4): la versione 3 del template «Fattura»
scorre le righe **in fila** e riconosce un componente di kit da `tipo_riga`. La lista delle righe
della fattura oggi le dà **ad albero** (il kit con i componenti dentro). Se il PDF passasse a
quella forma, la versione 3 stamperebbe la fattura **senza i componenti dei kit**: un documento
fiscale incompleto, senza un segnale.

⚠️ **Non è un caso isolato, è il modello.** Il preventivo è già passato una volta dalla forma 1
alla forma 2 (gli indirizzi a slot, `work-done/brief-db-template-preventivo-slot.md`), e
l'allineamento fra builder e template l'ha fatto una persona, a mano. Con i template
**personalizzati per azienda** ogni installazione avrà le sue versioni, scritte sulla forma di
quando sono nate: il caso diventa la norma.

## 2. Cosa c'è oggi — letto dalla struttura (2026-09-29)

* Ogni builder scrive `_meta.context_version` nel contesto (`apps/vendite/services/*_document_context_builder.py`):
  la **forma che produce**. Fatto datato: fattura `1`; preventivo, ordine, DDT, contratto,
  offerta `2`.
* `template_documenti_versioni.context_schema jsonb NOT NULL DEFAULT '{}'`, con il solo
  `CHECK` «è un oggetto». **Nessuno lo legge né lo controlla.**
* ⚠️ **Una regola decisa e mai costruita**: le decisioni 35-36 del 2026-04-29
  (`work-done/sviluppo-documenti.md`) volevano `context_schema` «contratto leggero delle
  variabili attese», **validato prima della pubblicazione** di una versione. Non esiste la
  validazione, e il campo è vuoto su tutte le versioni.
* `documenti.documenti_generati` congela per ogni stampa `context_json` (col suo `_meta`) e
  `template_versione_id`: la **ristampa fedele** rilegge quelle due cose, quindi è coerente per
  costruzione se lo era la prima stampa.

## 3. Il patto

1. Ogni **versione di template dichiara la forma che legge**: un numero, «versione del contesto».
2. Il **builder dichiara la forma che produce** (lo fa già: `_meta.context_version`).
3. **Si stampa solo se i due numeri coincidono.** Altrimenti un errore parlante — «questa
   versione del template legge la forma N, i dati sono nella forma M» — e **nessun PDF**.
4. Lo stesso controllo **alla pubblicazione** di una versione: non si pubblica una versione che
   dichiara una forma che il builder non produce.

Vale per **tutti** i tipi di documento, anche per quelli che oggi non cambiano forma.

## 4. Lato DB (proposta)

> ⚠️ **Proposta del 29-09.** Quello che è stato scritto il 30-09 è in §8: il nome del guard e
> il controllo alla pubblicazione sono diversi da qui.

* **Una colonna tipizzata, non una chiave nel jsonb**: `template_documenti_versioni.versione_contesto
  integer NOT NULL`, `CHECK (versione_contesto >= 1)`. Un numero che decide se si stampa deve
  potersi vincolare e leggere con una query, non stare dentro un oggetto libero.
* **La regola in un posto solo**: una `documenti.fn_check_versione_contesto(template_versione_id,
  versione_contesto)` che risponde, e la chiamano **tutti e due**:
  - il **backend**, prima del render (niente PDF da buttare);
  - un **guard** sull'INSERT di `documenti_generati`, che confronta il
    `_meta.context_version` del contesto congelato con la versione del template: una stampa
    incoerente non si registra, qualunque strada l'abbia prodotta.
* **Il codice d'errore**, registrato (nome da decidere, p.es. `E_DOC_VERSIONE_CONTESTO_DIVERSA`).
* ⛔ **Il backfill non è «le vecchie valgono 1»** (la proposta di §9.8.4): cinque builder su sei
  producono già la forma 2, e le versioni pubblicate che la leggono diventerebbero
  **non stampabili** il giorno dopo. Il valore di ogni versione esistente va **stabilito
  leggendola** (quali chiavi usa), versione per versione: è un dato di catalogo, non una regola.
  Chi lo stabilisce è una decisione (§7).
* `context_schema` resta dov'è; se la validazione delle variabili (decisione 35-36) si fa, si
  appoggia sullo stesso momento della pubblicazione (§7, D-C3).

## 5. Lato BE (per sapere cosa serve)

* il controllo prima del render e alla pubblicazione, chiamando la funzione del DB;
* il campo nell'amministrazione delle versioni di template (a video: «legge la forma N»);
* la versione del builder resta nel codice del builder (è un fatto del codice): una costante per
  builder, da cui escono sia `_meta.context_version` sia il confronto;
* poi, **per la fattura**: il contesto in forma 2 dalla lettura completa di
  `vw_fattura_righe_lista`, la **versione 4 del template** che scorre `riga.componenti`, e il
  ritiro di `VenditeRepository.list_fattura_righe` (l'ultima proiezione Python delle righe,
  brief liste §9.8.4, punto 3). Nello stesso giro, gli altri documenti le cui righe sono già
  liste (preventivo, ordine, DDT, reso, contratto) passano alla stessa lettura se la loro forma
  cambia — con il loro numero di forma.

### 5.3 Legame con `brief-be-documenti-risorse-esterne-render-pdf.md` (segnalato da Tid il 30-09)

Tutti e due parlano di **che cosa una versione di template si aspetta di trovare al render**:
qui la *forma dei dati*, là le *risorse esterne* (asset, `url_fetcher`). Non si bloccano a
vicenda. Il punto in comune è il **momento della pubblicazione** come controllo: se là nasce
`asset:<codice>`, la verifica «gli asset citati esistono e sono dell'emittente» ha la stessa sede
naturale di questo patto (`fn_pubblica_template_documento_versione`, o il service che la chiama).
La domanda §5.3 di quel brief (chiave stabile dell'asset) resta indipendente.

### 5.4 ⚠️ Tre changeSet di agosto dormienti (dichiarato, voluto)

`80_data` `20260805-09`, `20260816-01` (creano BOZZE con `INSERT` esplicito, senza la colonna) e
`20260805-10`, `20260816-02` (pubblicano con la firma a tre) sono `onFail: CONTINUE`: su un
database dove non sono passati si rivalutano a **ogni** migrate. Su dbdev sono `EXECUTED`; su un
DB da zero saltano finché non trovano i template di sviluppo che cercano (`test`, `ord-ven`…).
Se un giorno li trovassero, morirebbero su `23502` o `42883` invece di creare/pubblicare una
versione che non dichiara la forma. È il comportamento giusto, ed è scritto qui perché non
sorprenda: non si toccano (mergiati).

## 6. L'ordine

1. DB: colonna, funzione, guard, codice; backfill **verificato** delle versioni esistenti.
2. BE: controllo al render e alla pubblicazione; campo a video.
3. Da lì in poi ogni cambio di forma è: forma N+1 nel builder **e** versione nuova del template
   che la dichiara, nello stesso giro. La ristampa dei documenti già emessi non cambia.
4. Fattura: forma 2 + template versione 4 + ritiro di `list_fattura_righe`.

## 7. Decisioni per Tid

✅ **Tutte e quattro accettate da Tid il 2026-09-29, come proposte.**

| # | Domanda | Proposta |
| --- | --- | --- |
| D-C1 | Chi stabilisce la forma di ogni versione esistente (il backfill)? | Il team BE, leggendo ogni versione (sono poche), con la tabella nel brief prima del changeSet |
| D-C2 | Il controllo anche come guard sulle stampe registrate, o solo nel backend? | **Anche il guard**: una funzione sola, due chiamanti. Protegge da una strada di stampa che dimentica il controllo |
| D-C3 | La validazione delle variabili decisa ad aprile (35-36): si fa ora o resta fuori? | Fuori da questo giro, dichiarata: il numero di forma chiude il caso grave (pezzi mancanti in silenzio); la validazione delle singole variabili è un raffinamento |
| D-C4 | Una versione **in bozza** può dichiarare una forma che il builder non produce ancora? | Sì: è così che si prepara la versione 4 mentre il builder è ancora a 1. Il controllo vale alla pubblicazione e alla stampa |

## 8. Che cosa è stato scritto (2026-09-30)

| changeSet | cosa |
| --- | --- |
| `00_schema/documenti/20260930-14` | colonna `versione_contesto integer` (nullable) + `CHECK >= 1` + COMMENT |
| `00_schema/documenti/20260930-15` | backfill per **chiave naturale** (codice_interno del template, versione): tabella sotto |
| `00_schema/documenti/20260930-16` | `SET NOT NULL` dietro cancello fail-closed (`expectedResult: 0`, HALT): una versione non nominata dal backfill ferma il migrate |
| `20_code/documenti/20260930-17` | `versione_contesto` entra nell'`UPDATE OF` del guard A1: da PUBBLICATA non si cambia (DROP + CREATE del trigger, scritto a mano) |
| `20_code/documenti/20260930-18` | `documenti.fn_guard_versione_contesto(p_template_versione_id, p_versione_contesto)` |
| `20_code/documenti/20260930-19` | `documenti.trgfn_documenti_generati_guard_versione_contesto()` |
| `20_code/documenti/20260930-20` | trigger `trg_documenti_generati_a10_guard_versione_contesto_ins` (BEFORE INSERT) |
| `20_code/documenti/20260930-21` | `fn_pubblica_template_documento_versione`: **nuovo parametro obbligatorio** `p_versione_contesto`, chiama il guard; firma nuova (DROP + CREATE), md5 del vivo ancorato |
| `80_data/sql/config/messaggi_errore.csv` 1169-1170, `codici_errore.csv` | `E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA` (`CONFLITTO_STATO`), `E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE` (`TECNICO`) |

Firme, `RETURNS TABLE` e `DECLARE` ancorati con `%TYPE` (anche nelle firme di `COMMENT`/`DROP`);
risolvono agli stessi tipi del vivo (`bigint, date, integer, date`), nessun overload.

### 8.1 Dove si discosta da §4, e perché

* **`fn_guard_…`, non `fn_check_…`**: solleva, quindi è un guard (linee-guida-sql §5). Nessuna
  capability a DB: la forma del builder è un fatto del codice e il DB non la conosce.
* **Il controllo alla pubblicazione sta nel verbo**, non solo nel backend: la stessa ragione di
  D-C2 per le stampe (una strada che dimentica il controllo non pubblica). Il DB riceve la forma
  del builder come parametro **obbligatorio**; niente `DEFAULT NULL`, che sarebbe la porta per
  saltarlo. Costo dichiarato: la firma cambia (R-1).
* **Due codici, non uno**: forme diverse (`CONFLITTO_STATO`, rimedia chi amministra i template) e
  forma non dichiarata (`TECNICO`: solo un builder rotto la produce). Nome della famiglia
  `E_DOCUMENTI_*`, non `E_DOC_*`.
* **Nessun default** sulla colonna, né ora né dopo: un default è una forma dichiarata da nessuno.
* **Forma «non intera»** (`"2"` stringa, `2.5`, `null`) = non dichiarata, non un `22P02`.

### 8.2 La tabella del backfill (D-C1) — letta il 2026-09-30 dal team DB

Criterio: la forma 2 di ogni builder aggiunge (o cambia) una chiave; una versione legge la
forma 2 se usa quella chiave. Letto dall'`html_template` di ognuna delle 20 versioni su dbdev.
⚠️ D-C1 assegnava la lettura al BE: l'ha fatta il DB perché è un confronto meccanico di chiavi;
**R-5 chiede al BE di confermarla**.

| template (`codice_interno`) | forma 2 del builder | v1 | v2 | v3 | v4 |
| --- | --- | --- | --- | --- | --- |
| `test` (Preventivo) | `indirizzi` a slot (16-08) | 1 (lista) | 1 (lista) | 1 (lista) | **2** (`indirizzi.consegna`) |
| `contratto` | + `indirizzi` (05-08) | 1 | 1 | **2** | — |
| `off-comm` | + `indirizzi` (05-08) | 1 | 1 | **2** | — |
| `ord-ven` | + `indirizzi` (05-08) | 1 | 1 | 1 | **2** |
| `ddt-ven` | + `indirizzi` (13-07) | 1 | **2** | **2** | — |
| `fattura` | (forma 1) | 1 | 1 | 1 | — |

Tutte le PUBBLICATE coincidono con la forma di oggi del loro builder. **Verifica, non motivo**
(fatto datato 30-09): nessuna delle 210 stampe registrate su dbdev ha un `_meta.context_version`
diverso dal valore assegnato alla sua versione — la tabella non ha controesempi.

## 9. Prova (2026-09-30) — in transazione ritirata, su dbdev, da owner

> ✅ **Superata dall'apply**: migrazione applicata e pgTAP verdi col runner (Tid, 2026-09-30),
> quindi anche come app. Il resto della sezione resta come storia della prova pre-apply.

SQL **estratto** dagli YAML `-14 → -21` + le righe nuove dei due CSV simulate con `INSERT`, dentro
`BEGIN … ROLLBACK` (colonna assente sul vivo dopo, verificato).

* tutto il blocco applica; backfill: 0 versioni senza forma; firme risolte come sopra;
* `plpgsql_check` sulle tre funzioni nuove/riscritte: nessun errore;
* pgTAP, ciascuno nella sua transazione con l'estratto in testa:

| file | esito |
| --- | --- |
| `documenti/test-documenti-versione-contesto-v1.sql` (**nuovo**) | 15/15 |
| `documenti/test-fn-pubblica-template-documento-versione-v1.sql` (firma a 4, +test 8-11) | 11/11 |
| `documenti/test-documenti-template-versioni.sql` (+test 10-11) | 11/11 |
| `documenti/test-documenti-generati.sql` (fixture allineata) | 10/10 |
| `documenti/test-documenti-generati-file.sql` (fixture allineata) | 8/8 |
| `documenti/test-documenti-generati-eventi.sql` (fixture allineata) | 15/16 — il 16 (RLS → `42501`) è rosso **da owner per costruzione**, identico sul file di HEAD senza modifiche |
| `rls/test-rls-documenti-satelliti.sql` (fixture allineata) | 13/13 |
| `dbops/test-punti-canale-campo-v1.sql` (presidio che nomina `fn_pubblica_…`) | 16/16 |

* cancelli statici: `guardrail_run_on_change`, `_sql_letterali`, `_precondition_seed`,
  `_ddl_su_trigger_automazione`, `_grant_ruolo_batch`, `_timestamp_senza_fuso`,
  `_pgtap_preambolo`: verdi.
* ⚠️ **Non provato qui**: la RLS come app (arriva dalla corsa di Tid), i presidi trasversali col
  runner (`dbops/test-riferimenti-morti-v1`: provato solo `plpgsql_check` sulle tre funzioni).

⛔ **L'apply e la corsa pgTAP sono di Tid.** Documentazione manuale aggiornata: `documenti/manual/`
`template_documenti_versioni`, `documenti_generati`, `fn_pubblica_…`, `trgfn_…_protect_pubblicata`,
e le due pagine nuove `fn_guard_versione_contesto`, `trgfn_documenti_generati_guard_versione_contesto`.

## 10. Richieste al BE (dopo l'apply sono bloccanti)

| # | Cosa | Perché si rompe senza |
| --- | --- | --- |
| **R-1** | `documenti_repository.pubblica_versione`: passare `p_versione_contesto => <costante del builder del tipo di documento del template>` | la firma a tre non esiste più: `42883` |
| **R-2** | `create_versione` / whitelist INSERT (e ogni «duplica versione»): `versione_contesto` obbligatorio; al duplicare si copia dalla sorgente; a video «legge la forma N», modificabile solo in BOZZA | `23502` su ogni versione nuova |
| **R-3** | prima del render (generazione **e** anteprima di una versione pubblicata): `SELECT documenti.fn_guard_versione_contesto(%s, %s)` con la costante del builder; una costante per builder, da cui esce anche `_meta.context_version` (§5) | senza, il PDF si genera e poi l'INSERT della stampa viene rifiutato: PDF da buttare |
| **R-4** | rigenerare `error_policies_generated.py` per i due codici nuovi; test Django che scrivono versioni o stampe (in `documenti/tests/…`, `core/tests/db/test_date_validita_guard_comune_db.py`, `ai_assistant/tests/…`, `core/tests/services/test_payload_helpers.py`): versione con `versione_contesto`, contesto con `_meta.context_version` | rossi su `23502` / codice nuovo |
| **R-5** | confermare la tabella §8.2 (D-C1) | è un dato di catalogo letto da noi |

Poi §5 ultimo punto e §6 punto 4: la fattura alla forma 2 con la **versione 4** del template che
scorre `riga.componenti`, pubblicata con `p_versione_contesto = 2`, e il ritiro di
`VenditeRepository.list_fattura_righe`.

## 11. La versione 4 del template Fattura — NON ancora scritta (2026-09-30)

Su dbdev il template `fattura` ha v1 (OBSOLETA), v2 (OBSOLETA), v3 (PUBBLICATA), **tutte
`versione_contesto = 1`**: la v3 scorre le righe **in fila** e riconosce il componente di kit da
`tipo_riga`. Nessuna bozza v4 esiste.

Per chiudere §6 punto 4 servono, **nello stesso giro**:

1. **BE** — il builder fattura alla forma 2: righe dalla lettura completa di
   `vw_fattura_righe_lista` (**ad albero**: il kit con `riga.componenti`), `_meta.context_version = 2`,
   ritiro di `VenditeRepository.list_fattura_righe`;
2. **template v4** — una BOZZA che dichiara `versione_contesto = 2` e scorre `riga.componenti`
   invece di riconoscere i componenti da `tipo_riga`; si può scrivere **prima** del builder (D-C4);
3. **pubblicazione** — `fn_pubblica_template_documento_versione(v4, <data>, 2, NULL)`, solo quando il
   builder produce la 2: prima, il verbo la rifiuta con `E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA`.

⚠️ **Chi scrive il corpo della v4 è da decidere.** Il precedente (preventivo a slot, 16-08) era
BOZZA + pubblicazione in `80_data` con ancore verificate sul corpo vivo, ma i template non sono a
seed: su un DB da zero quei changeSet saltano. La forma del contesto ad albero la conosce il BE che
scrive il builder: la strada più corta è che il BE fissi la forma 2 e che la v4 nasca da lì
(dall'amministrazione dei template o da un changeSet `80_data` che la duplica dalla v3 con le
sostituzioni ancorate).

**Proposta del team DB (30-09, in attesa del via di Tid):** appena il BE ha fissato le chiavi della
forma 2 (R-3 e il builder), il DB prepara la **BOZZA v4** come changeSet `80_data` che duplica la v3
e riscrive il solo ciclo delle righe su `riga.componenti`, con ancore verificate sul corpo vivo e
`versione_contesto = 2` (stampo: `20260816-01`). La **pubblicazione** resta un passo separato, da
fare quando il builder produce la 2.

## 12. Esito del giro BE/FE (2026-09-30, `dev/backend-tid`)

| # | Esito | Dove |
| --- | --- | --- |
| **R-1** | ✅ `pubblica_versione` passa `p_versione_contesto` per nome (firma a quattro); il service lo prende dal builder **del template** (`context_builder_code` → registry → `CONTEXT_VERSION`). Builder non registrato = 400 `E_DOCUMENTI_VALIDATION` dal registry, prima del verbo | `documenti_repository.pubblica_versione`, `template_versioni_admin_service.pubblica_versione` |
| **R-2** | ✅ `versione_contesto` nelle whitelist INSERT/UPDATE e nella proiezione (lista e dettaglio); **obbligatoria** in create (400 col campo, nessun default), modificabile solo in BOZZA (pre-check di stato già esistente + trigger A1), **copiata** dal clone. A video: campo «Legge i dati nella forma» nel form della versione, precompilato con la forma di oggi, e le due forme nel dialog di pubblicazione | service versioni, `TemplateVersioniSection.vue`, `TemplateDocumentoDrawer.vue` |
| **R-3** | ✅ Una costante per builder, `CONTEXT_VERSION` su `DocumentContextBuilder`, da cui escono `_meta.context_version` e il controllo; `register_builder` rifiuta un builder senza forma. Prima di costruire il contesto e di renderizzare, **generazione e anteprima** chiamano `fn_guard_versione_contesto(versione, CONTEXT_VERSION)`, tradotto in `ServiceError` (409 col codice e la frase del catalogo; lo legge anche il worker della coda di stampa). La ristampa fedele non ricontrolla: la coppia congelata l'ha verificata il trigger | `context_builders/`, i sei `*_document_context_builder.py`, `document_generation_service` |
| **R-4** | ✅ `error_policies_generated.py` già rigenerato coi due codici; ripieghi senza segnaposto aggiunti in `error_messages_fallback.py`. Test allineati (versione con `versione_contesto`, contesto con `_meta.context_version`, template di prova col builder vero) e nuovi: registry, service, generazione, e `documenti/tests/db/test_versione_contesto_db.py` sul DB vero (binding delle due funzioni, 409 con le due forme nella frase, bozza per la forma successiva che si pubblica solo dopo averla riportata alla forma del builder) | `documenti/tests/…`, `core/tests/db/test_date_validita_guard_comune_db.py` |
| **R-5** | ✅ **Confermata** la tabella §8.2: riletti i corpi delle 20 versioni su dbdev, la chiave della forma 2 (`indirizzi.consegna`; per il preventivo v1-3 il ciclo su `indirizzi` come lista) compare esattamente nelle versioni a cui il backfill ha dato 2 | — |

Il dettaglio del template porta ora `versione_contesto_builder` (la forma che il builder produce oggi,
`null` se il builder non è registrato): non è una colonna, lo legge il backend dal registry.

### 12.1 Richiesta al team DB (facoltativa, non bloccante)

La lista delle versioni è la configurabile `documenti.template_versioni` (88): il campo
`versione_contesto` viaggia già nelle righe, ma a video non c'è la colonna finché il catalogo non la
dichiara. Se utile, una riga in `ui.lista_colonna` (`campo_sorgente = versione_contesto`, intestazione
«Forma dei dati») con la chiave i18n che il team preferisce.

### 12.2 Test

Suite Django intera con `ZEROERP_TEST_DB_E2E=1` al 30-09: 5894 test, **3 rossi estranei a questo
giro** (`vendite.test_commesse_repository` ×2, chiave `rows`; `core.test_config_panel_registro_db`,
etichetta `config_panel.campi.causale_magazzino` assente in it.json). Frontend: lint, `npm run guards`,
`check_i18n_keys.py` verdi. ⚠️ **Non provato a video**: il form della versione non è stato aperto in-app.

## 13. La fattura alla forma 2 e la versione 4 (2026-09-30, `dev/backend-tid`)

✅ **Decisione di Tid (30-09): la v4 la scrive il BE**, nello stesso giro del builder — chi fissa la forma
ad albero scrive il ciclo che la legge — e nasce dall'app, non da un changeSet `80_data` (i template non
sono seed: su un DB da zero quel changeSet salterebbe comunque, e le ancore sul corpo vivo sono fragili).
La traccia rivedibile è il file nel repo.

### 13.1 Che cosa è stato fatto

* **Builder** `FatturaDocumentContextBuilder`: `CONTEXT_VERSION = 2`; `righe` dalla lettura completa di
  `vw_fattura_righe_lista` (`FattureRepository.list_righe`): solo il primo livello (NORMALE,
  PARTE_PLAFOND, KIT_PADRE), i componenti esposti di un kit **dentro** la riga (`riga.componenti`, lista
  di dict con la quantità formattata; `[]` fuori dai kit; il jsonb arriva come testo e si decodifica con
  `jsonb_out`). Chiavi di riga: quelle della vista; via `id`, `livello`,
  `riga_rettificata_fattura_numero` della forma 1 (la v3 non le leggeva).
* **Ritirata** `VenditeRepository.list_fattura_righe` col suo test; chiuse le eccezioni dichiarate in
  `ApiFatturaDetail`, `FatturaDrawer.vue`, `api_fattura_dettaglio.md` e brief liste §9.8.
* **Corpo della v4**: [`template-fattura-v4.html`](template-fattura-v4.html) = il corpo vivo della v3
  (id 75, letto il 30-09) col **solo** ciclo delle righe riscritto: niente più riconoscimento del
  componente da `tipo_riga`, un ciclo interno su `r.componenti` sotto ogni riga, con la classe
  `row-componente` già nel CSS della v3. Il CSS non cambia (lo copia il clone). ⚠️ Una differenza
  voluta: sui componenti la v3 stampava anche l'IVA, la v4 la lascia vuota come prezzo e importo — il
  valore del componente è già nel totale del padre, e l'IVA del kit è una sola.
* **Prova** (dbdev, in `ROLLBACK`, contesto di un operatore): il contesto forma 2 di una fattura reale
  con in più una riga kit **fabbricata** (su dbdev non c'è una fattura con kit: fatto datato, 30-09),
  passata dallo stesso `_shape_riga`. Resa con la v3: il kit c'è, **i due componenti no**, e nessun
  errore — il caso §1. Resa con la v4: kit e componenti, le 5 righe reali in entrambe. Il PDF esce in
  entrambi i casi (WeasyPrint).

### 13.2 I passi di Tid, in quest'ordine

⚠️ **Corretto il 2026-09-30**: la prima stesura metteva la bozza v4 PRIMA del riavvio. Non si può: il
backend in esercizio col codice vecchio non copia `versione_contesto` nel clone (NOT NULL a DB: 23502) e
pubblica con la firma a tre, che non esiste più. Il riavvio viene per primo; la finestra in cui la
fattura non stampa è il tempo dei passi 2-3.

1. **Riavvio del backend** (`kill -HUP $(pgrep -f "gunicorn zeroerp" | head -1)`, worker con l'orario
   nuovo in `ps aux`): da qui il builder produce la forma 2 e la v3 pubblicata, che legge la 1, **non
   stampa più** — 409 `E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA`, anche per la coda di stampa (le righe
   vanno in errore coi tentativi). È il patto che fa il suo mestiere.
1-bis. **Build del frontend** (`cd frontend && npm run build`, poi ricarica forzata del browser): in dev
   il frontend è servito da `frontend/dist`, senza aggiornamento automatico. ⚠️ Saltato il 30-09 sera:
   col form vecchio il campo della forma non c'era, la bozza v4 è rimasta alla forma 1 del clone e la
   pubblicazione è stata rifiutata col 409 — il patto ha fatto il suo mestiere.
2. **Bozza v4** dall'app: template «fattura» → versione 3 → «Clona»; nella bozza, l'HTML sostituito col
   contenuto di `template-fattura-v4.html` (il CSS resta quello copiato), «Legge i dati nella forma» =
   **2** (il clone copia 1 dalla v3), salva. È anche il collaudo a video del campo di R-2.
3. **Pubblicare la v4** (dal pulsante, `valido_dal` = oggi, `valido_al` vuoto): la v3 diventa OBSOLETA e
   la stampa riparte. Le righe di coda finite in errore terminale nella finestra si rimettono in coda
   dalla gestione code.

La ristampa fedele delle fatture già emesse non cambia: contesto congelato in forma 1, versione 3 fissata.

