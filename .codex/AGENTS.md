# AGENTS.md

## ⛔ Regola zero — le misure non disegnano il progetto

> **Le misure servono a trovare gli errori, non a disegnare il progetto.**
> Un dato del DB può solo **smentire** una regola: non decide mai la forma, il
> perimetro o la priorità di ciò che si costruisce.
> **Si sviluppa sul modello, non sulle righe di oggi.**

Questa è la prima cosa da leggere, ogni volta. Vale per DB, backend e frontend.

**Cosa può fare una misura**: portare un **controesempio**. «Questo caso esiste
ed è gestito male» è un fatto, e va corretto. È l'unico uso legittimo.

**Cosa NON può fare una misura** — e sono tutti argomenti da rifiutare, anche
quando li sto scrivendo io:

* ⛔ *«sono 168 su 349, non è un caso di nicchia»* → la frequenza non decide se
  una cosa va fatta. Se la regola è giusta vale anche a 1 su 349;
* ⛔ *«oggi non capita mai»* → **zero occorrenze non significa che il caso non
  esiste**: significa che non c'è ancora un controesempio. Un guard non si
  restringe perché il ramo oggi è irraggiungibile;
* ⛔ *«oggi 1 riga su 3, domani tutte»* → è una previsione sui dati travestita
  da progetto. La ragione dev'essere sul modello, o non è una ragione;
* ⛔ *«oggi vince la commessa perché 13 < 15»* → un comportamento che dipende
  da un ID esistente è un'ambiguità del modello, non una scelta;
* ⛔ *«il test è verde»*, quando è verde **perché i dati di oggi non sanno
  produrre il caso**. Non prova niente: è un presidio, e va dichiarato tale.

**Il segnale d'allarme, mentre scrivo**: se in un brief compare
*«misurato: … quindi facciamo così»*, la misura sta guidando il progetto. La
misura entra nel documento come **fatto datato**, mai come **motivo**. Il motivo
si riscrive sul modello — e se sul modello non regge, non era una ragione.

⚠️ Corollario per i documenti: un numero misurato invecchia in silenzio. Va
scritto **con la data e con il contesto** in cui è stato preso, e non va mai
usato come premessa di una decisione strutturale.

### ⭐ Come si distingue, in pratica: struttura contro popolazione

Non tutto ciò che si legge dal database è una «misura». Il discriminante e' se
si sta guardando il **progetto** o il suo **contenuto**:

| Cosa si legge | Che natura ha | Decide? |
| --- | --- | --- |
| Nullabilita' di una colonna, `CHECK`, chiavi, FK, RLS, GRANT, volatilita' e corpo di una funzione, seed in `80_data`, contratto di un endpoint | **contratto**: e' il progetto, scritto | ✅ si' — e' la sorgente giusta |
| `count(*)`, «zero righe in quello stato», «N su M hanno il padre valorizzato», distribuzione dei valori | **istantanea**: la fotografia di una macchina | ⛔ no |

Leggere la struttura non e' «misurare»: e' leggere il progetto, e va fatto — anzi
va fatto sulla **doc auto-gen** e non dagli YAML, che sono quasi sempre stantii.
La domanda che decide resta **«il modello lo ammette?»**: se una colonna e'
nullable, il NULL e' un caso da gestire anche quando in questo momento non ce
n'e' nemmeno uno.

### ⚠️ La prova del nove, su ogni riga che scrivo

**Togli la misura.** Se l'argomento resta in piedi identico, era **colore** — e
va dichiarato tale. Se l'argomento si affloscia, era **appoggiato alla cosa
sbagliata** e va riscritto sulla struttura.

⭐ Il caso peggiore non e' la conclusione sbagliata: e' la conclusione **giusta**
appoggiata a un conteggio. Li' non c'e' niente da correggere nel risultato, e la
misura sta occupando il posto dell'argomento — un documento cosi' scade con la
macchina su cui e' stato scritto.

### ⛔ Corollario sui test, ed e' dove il difetto rientra dalla finestra

Una prova che confronta il risultato nuovo con i **dati esistenti** non prova la
regola: prova i soli casi che quella popolazione **per caso** contiene. Un ramo
che si distingue solo quando una colonna opzionale e' valorizzata si prova
**costruendo** quel caso in un pgTAP, non confrontando una popolazione.

⚠️ E un test che itera su cio' che c'e' passa **a vuoto** su un database
ricostruito da zero — cioe' in CI: e' la forma classica del «verde per
sottrazione», che passa smettendo di verificare. O si dichiara con uno `skip()`
motivato, o si sostituisce con un test che i soggetti se li fabbrica.

## Quick Start per AI Agent

- Progetto: ERP Django + PostgreSQL, open-source GPL v3
- Stack: Python 3.14, Django 6.01, Liquibase 5, PostgreSQL 18, pgTAP per test DB
- Prima di implementare: leggi docs in `docs/it/` pertinenti
- Struttura: backend in `backend/`, DB migrations in `db/changelog/migrations_v2/`
- Filosofia: **DB-first** — la logica di business sta in PostgreSQL; Django orchestra e espone API; Vue (futuro) solo presentazione
- **Metodologia di sviluppo**: seguire sempre il modello concentrico descritto in:
  - `docs/it/sviluppo-concentrico.md` — principi e fasi dello sviluppo concentrico
  - `docs/it/mappa-concentrica.md` — mappa delle dipendenze e ordine di costruzione

## Scope

- Repo: ZeroErp
- Default language: it-IT (docs, commenti Python e SQL)
- Follow docs in `docs/it/linee-guida-sql.md`, `docs/it/linee-guida-trigger.md`, `docs/it/liquibase-setup-workflow.md`

## Dipendenze e versioni runtime

- Prima di sviluppare, consultare le dipendenze correnti:
  - **Backend Python**: `backend/requirements.in` (dipendenze dirette) e `backend/requirements.txt` (lock file generato)
  - **Strumenti dev**: `requirements.txt` nella root (mkdocs, pre-commit, ecc.)
- **Liquibase 5** + **PostgreSQL 18**: usare sintassi e funzionalità compatibili con queste versioni (es. SQL/JSON standard ISO, funzioni PG 18)
- Non aggiungere dipendenze Python senza conferma dell'utente

## Ambiente di sviluppo

- **Due server separati**: un server DB (PostgreSQL) e un server backend (Django, accessibile via VSCode SSH)
- Il branch centrale di integrazione è `Tito-dev`; i branch di lavoro sono `dev/db-tid` (DB) e `dev/backend-tid` (backend)
- Le PR vanno da branch di lavoro → `Tito-dev` → poi a `main`
- Non eseguire migrazioni DB senza conferma esplicita dell'utente (vedi Workflow Safety)

## Versione Python

- **Fonte unica di verità**: `.python-version` nella root del repo (es. `3.14.2`)
- CI (`ci.yaml`, `ci-validate.yaml`) leggono da `.python-version` automaticamente
- `Dockerfile` usa `ARG PYTHON_VERSION` passato dalla CI; default nell'ARG allineato alla major.minor
- `backend/requirements.txt` è generato da pip-compile: editare `backend/requirements.in` e rieseguire:
  `pip-compile backend/requirements.in --output-file backend/requirements.txt`
- `requirements.txt` radice = strumenti dev (mkdocs, pre-commit…), gestito con `pip freeze` via `scripts/update-venv.sh`
- Per aggiornare la versione Python: modificare solo `.python-version`, poi rigenerare `backend/requirements.txt`

## Backend (Django)

- Codice backend in `backend/`
- **Documento di riferimento obbligatorio**: `docs/it/dev/api.md` — leggere PRIMA di qualsiasi intervento su endpoint, repository o service
- Versioni: Python 3.14, Django 6.01
- Evitare API/metodi deprecati; seguire best practice Django
- Accesso webserver configurato: test migrazione solo su richiesta
- Per i file Python **generati** aggiungere sempre l'header standard in `templates/python-header.txt`.
- Per ogni nuovo file Python (non generato da Django) aggiungere l'header standard di `templates/python-header.txt` e un breve commento iniziale sullo scopo.
  ⭐ **È un cricchetto, e la parola «nuovo» è la regola**: `scripts/check_license.py`
  (hook pre-commit) guarda i file **aggiunti**, non quelli modificati — toccare un
  file vecchio senza header non blocca il commit.
  ⚠️ Perché: l'hook ha girato per la **prima volta** il 2026-08-26 (`pre-commit`
  non era installato su nessuna macchina, quindi la configurazione esisteva e non
  presidiava niente), e quel giorno erano **2042 file su 5189** senza header — il
  39% del repo, **579 su 605** sotto `frontend/src`. Con i modificati dentro il
  perimetro, qualunque lavoro sul frontend si sarebbe bloccato al primo commit, e
  la reazione ovvia sarebbe stata spegnere l'hook. *Un presidio che blocca tutto
  viene disattivato, e allora non presidia più nemmeno i casi per cui era nato.*
  ⛔ Quei 2042 sono un **registro del debito** e devono calare — ma per decisione,
  non per attrito.
  ✅ **Vale anche per `.js`/`.vue`** (Tid, 2026-08-26): la regola e i due
  template stanno nella sezione Frontend qui sotto. Il filtro dell'hook
  (`py|js|vue|yaml`) resta quello che era: non e' stato allargato, e' stato
  finalmente **acceso**.
- Nei file Python aggiungere un commento sintetico (`# Scopo: ...`) prima di ogni funzione/metodo (`def`/`async def`), in italiano.
- Per funzioni/metodi che orchestrano processi complessi (pipeline, transazioni, dispatch task, integrazioni esterne), rendere il commento `Scopo` iniziale piu` dettagliato: obiettivo, perimetro e risultato atteso.
- Nei file Python aggiungere commenti sintetici nei blocchi non banali (orchestrazione, transazioni, mapping task/SQL), scritti in italiano.
- Dopo un `ErrorManager.require(... is not None ...)` aggiungere sempre l'`assert` corrispondente per aiutare il type checker.
- Dopo `row = cursor.fetchone()` aggiungere guard (`if not row`) oppure `assert row is not None` prima di usare `row[...]`.
- Nei servizi/classi Python usare nomi metodo espliciti e orientati al dominio (es. `run_pipeline`), evitando nomi generici/ambigui come `run`.
- Per error handling servizi/API usare helper centralizzato in `apps/core/services/error_manager.py`, evitando logica duplicata nei moduli dominio.
- Il mapping `codice errore -> HTTP status -> azione UI` deve essere centralizzato in `apps/core/services/error_policies.py`.
- Struttura consigliata: project config in `backend/zeroerp_backend/`, app in `backend/apps/`
- App per dominio (es. `vendite`, `anagrafiche`), non per dettaglio tecnico; se uno schema DB coincide con un dominio stabile, la cartella app puo` allinearsi allo schema
- Orchestrazione in `apps/<dominio>/services/` (o `usecases/`); accesso DB/SQL in `apps/<dominio>/db/` o `repositories/`
- API in `apps/<dominio>/api/` o `views.py` + `urls.py`; modelli ORM solo dove utili, altrimenti `managed = False`

### Naming convention repository e service per app dominio

Ogni app puo' contenere piu' repository e service. La regola di naming e' basata sul **perimetro semantico**:

| Tipo | Nome file | Contenuto |
| --- | --- | --- |
| Generico schema | `<schema>_repository.py` | List, query, CRUD su entita' dello schema senza logica specifica (es. `vendite_repository.py`) |
| Sottodominio specializzato | `<sottodominio>_repository.py` | Operazioni di un processo autonomo con logica propria (es. `pipeline_repository.py`) |
| Generico schema | `<schema>_service.py` | Facade per operazioni generiche (es. `vendite_service.py`) |
| Sottodominio specializzato | `<sottodominio>_service.py` | Facade per il sottodominio (es. `pipeline_service.py`) |

**Regola pratica:**

- Usare `<schema>` (es. `vendite`) per operazioni che non appartengono a nessun sottodominio specifico: elenchi, ricerche, lettura stato entita'.
- Creare un file `<sottodominio>_*` **solo** quando il sottodominio ha logica orchestrata autonoma (runner, executor, tracing, saga): non per singoli metodi.
- Non frammentare in file per ogni entita': tre metodi su `fatture` e due su `lotti` stanno in `vendite_repository.py`, non in file separati.
- Esempio per `vendite`: `vendite_repository.py` (list lotti, list fatture, decodifiche), `pipeline_repository.py` (step, task run, job stato, pipeline config).
- Per endpoint API usare il pattern core `handle_post_json(...)` (`apps/core/api/endpoint_helpers.py`) per parsing/error envelope uniforme.
- Evitare `try/except Exception` generici nelle view API dominio: usare `ServiceError` nei service e lasciare fallback al middleware `apps/core/middleware/api_exception_middleware.py`.
- Il middleware eccezioni API si applica solo a `/api/*` e resta disattivabile via `DJANGO_API_EXCEPTION_MIDDLEWARE_ENABLED`.
- Per nuove API lista/search applicare la policy `docs/it/dev/Policy-ricerca-e-paginazione(API-DB).md` e usare gli helper core (`apps/core/api/pagination.py`, `apps/core/api/search_validators.py`).
- Per endpoint search impostare `is_search_endpoint = True` per attivare throttling DRF (`apps/core/api/throttling.py`).

## Frontend (Vue)

### ⛔ Una lista si monta con `<ListaConfigurabile>`, mai con una `DataTable` grezza

**Regola, non preferenza:** ogni lista passa da
`<ListaConfigurabile codice="...">`. Importare `primevue/datatable` in una view
è l'**eccezione**, e va motivata in un commento sopra l'import.

Le uniche due eccezioni: le **righe di un documento** dentro il suo master
(→ `RigheMasterDetailTable` / `SearchDetailTable`) e una tabella di **anteprima**
dentro un dialog, non paginata e non configurabile.
⛔ Non sono eccezioni: «è piccola», «è solo per l'admin», «faccio prima».

⛔ **Nemmeno «è dentro un drawer»** (2026-09-01). Una lista su un tab di drawer
è una lista: le manca il paginator, non la natura. Si monta con
`useDrawerTabLista` + `<DrawerTabLista>`. 🔴 L'unico caso oggi **senza casa** è
la **matrice slot/override** (editing inline, popolazione dal catalogo): resta
`DataTable` grezza col debito dichiarato nel piano PrimeVue 5 §Gruppo B, dove
sta anche il criterio in tre domande e la decisione aperta.

La configurazione della lista è **dato, non DDL** — una riga in
`ui.lista_definizione` più N in `ui.lista_colonna`, create dall'amministrazione
in-app o con `scripts/gen_seed_lista.py`. **Non serve un brief e non si aspetta
nessuno.**

⚠️ **Perché sta qui, in cima:** fino al 2026-08-30 questa regola **non era
scritta in nessun documento letto a inizio sessione**, mentre
`frontend-standards.md` spiegava *come* configurare una `DataTable`. Risultato
misurato: i file con `DataTable` grezza, scesi a 48 il 03-08, erano **risaliti a
57**. Una regola che non sta dove si legge non esiste.

**Verifica prima di dire che una view è finita** — se il numero sale, hai
aggiunto una lista fuori standard:

```bash
grep -rl "from 'primevue/datatable'" frontend/src --include=*.vue | wc -l
```

Dettaglio e motivazioni: `docs/it/dev/frontend/frontend-standards.md`
§«Regola zero della lista».

- Codice frontend in `frontend/`
- **Documento di riferimento obbligatorio**: `docs/it/dev/frontend/frontend-standards.md` — leggere PRIMA di qualsiasi intervento sul frontend
- **Guida sviluppo frontend**: `docs/it/dev/work-in-progress/frontend/guida-sviluppo-frontend.md` — convenzioni componenti, composable, routing, CSS, pattern operativi
- Stack: Vue 3.5, Vite 7, PrimeVue 4.5, Pinia 3, Vue Router 5, vue-i18n 10, Axios
- Runtime: Node.js 24 LTS (gestito via nvm)
- Dipendenze: `frontend/package.json`
- Non aggiungere dipendenze npm senza conferma dell'utente
- Filosofia: **zero logica business nel frontend** — solo presentazione, validazione UX e orchestrazione chiamate API
- Struttura cartelle allineata ai domini DB (es. `src/vendite/`, `src/anagrafiche/`)
- Moduli condivisi in `src/core/` — mai duplicare configurazioni, costanti o liste tra componenti
- La navigazione (domini, icone, rotte sidebar) e' centralizzata in `src/core/navigation.js`
- Le costanti UI (larghezze drawer, durata toast, paginazione) sono in `src/core/constants.js`
- Sicurezza: route guard su tutte le rotte (default protette), token refresh automatico, no `window.location` per redirect
- Multilingua: ogni testo visibile all'utente usa `$t()` — mai stringhe hardcoded nei componenti
- Build: `./node_modules/.bin/vite build` (richiede nvm per caricare Node)
- **Header di licenza obbligatorio sui file nuovi**, come per il backend
  (decisione di Tid, 2026-08-26): `templates/javascript-header.txt` per i `.js`,
  `templates/vue-header.txt` per i `.vue`. Presidiato da `scripts/check_license.py`
  (hook pre-commit), che guarda i file **aggiunti** — il pregresso non blocca.
  ⚠️ In un `.vue` l'header va **prima di `<script setup>`** e in commento HTML:
  e' l'unica forma valida in cima a un Single File Component, e il presidio legge
  le prime 10 righe del file. Lo `Scopo:` invece **non** sta li': resta un
  commento `// Scopo: ...` dentro `<script setup>`, dov'e' gia' la convenzione e
  dove lo trova chi legge il codice.
  ⚠️ **Non e' una regola nuova: era gia' in vigore di fatto e non scritta.**
  L'hook include `js|vue` da sempre, ma non ha mai girato (`pre-commit` non era
  installato), e i 26 file frontend che l'header ce l'hanno usano gia' esattamente
  questa forma — i template la mettono per iscritto, non la inventano.

## Liquibase v2 Workflow

- New work only in `db/changelog/migrations_v2/`
- File extension: `.yaml` only
- File naming: `YYYYMMDD-NN-<tipo>-<descrizione>.yaml`
- One changeSet per file
- Always set `logicalFilePath`
- `00_schema` and `20_code` are included via `migrations_v2/changelog-autogen.yaml` (autogen script)
- `80_data`, `85_pgagent`, `90_end` are included via `includeAll` in master
- **MAI modificare changelog già mergiati/pushati su GitHub** — si rompe la sequenza Liquibase dei checksum. Per aggiornare una funzione/trigger, creare SEMPRE un nuovo file con numerazione successiva (es. `20260225-37-update-...`). Ripristinare (`git checkout --`) i file originali se modificati per errore.

### ⛔ `runOnChange: true` è VIETATO in `00_schema` e `20_code`

Presidiato da `scripts/guardrail_run_on_change.py` (CI, `ci-validate.yaml`): un
changeSet di schema o di codice che lo dichiara fa fallire la build.

**Perché**, ed è una cosa che si vede solo in CI. La pipeline invoca Liquibase
**due volte** sullo stesso changelog (`--contexts="!provision"`, poi
`--contexts=ci_apply`). Un changeSet `runOnChange: true` ri-esegue nella seconda
passata **fuori dall'ordine di timeline**, quindi riscrive il proprio corpo
*sopra* le revisioni più recenti — che sono `runOnChange: false` e non
ri-eseguono. Su un DB di sviluppo non si vede: l'invocazione è una sola.

Il 2026-08-06 questo meccanismo riportava indietro **49 funzioni** a ogni build,
fra cui `dbops.trgfn_tx_id_managed`, le sei `vendite.vw_*_lista` e i cinque
`vendite.fn_list_*_da_pushare`. Il sintomo era un guardrail rosso su codici
errore ritirati; le funzioni regredite in silenzio erano il vero danno.

⚠️ **Il corollario è che un changeSet successivo NON supera automaticamente un
`runOnChange: true` precedente.** Vale solo fra changeSet spenti.

Dove resta **lecito**: mirror CSV di `80_data` (`loadData`/`loadUpdateData`), job
`85_pgagent`, resync/grant di `90_end`. Lì la ri-esecuzione è il comportamento
voluto.

⚠️ **`validCheckSums` — al PLURALE.** `validCheckSum` (singolare) è una chiave
che Liquibase ignora: l'`ANY` non vale niente. Il refuso è in centinaia di file
e non si nota finché `runOnChange` è `true` (il checksum si ricalcola comunque);
diventa un migrate fallito nel momento in cui lo si spegne. Chi spegne un
`runOnChange` deve correggere anche la chiave.

### ⛔ Una `preCondition` di `00_schema`/`20_code` NON interroga il contenuto di `80_data`

Presidiato da `scripts/guardrail_precondition_seed.py` (CI, `ci-validate.yaml`).
Regola estesa e casistica: [linee-guida-sql.md §11.4](../docs/it/linee-guida-sql.md).

**Perché**, ed è l'altra cosa che si vede solo in CI. Il changelog esegue
`00_schema` + `20_code` (mescolati per numero dall'autogen) e **poi** `80_data`.
Quindi un `sqlCheck` che pretende una riga di seed — un codice errore, una
`config.sorgenti`, uno stato a catalogo — viene valutato quando quella riga non
esiste ancora: la corsa che la **introduce** è esattamente quella in cui il
cancello non la trova, e il migrate muore con
`SQL Precondition failed. Expected '1' got '0'`. Su un DB di sviluppo la riga c'è
da settimane e il cancello passa.

Il 2026-09-02, ripartita la CI dopo giorni di fermo, il migrate si è fermato su
`20260820-12-update-fn-available-actions-reso-accrediti`; dietro c'erano altre
**quindici** mine identiche già committate, una build ciascuna per scoprirle.

Non serve, ed è il punto: un codice errore o una sorgente si nominano come
**stringa** e si risolvono **a runtime**, quando `80_data` è passato da un pezzo.
Ciò che il cancello voleva difendere («se il `codice_interno` cambiasse, il
`CASE` smetterebbe di agganciarsi in silenzio») è un presidio **pgTAP**.

✅ Restano leciti: le preCondition sullo **schema** (`tableExists`,
`columnExists`, `viewExists`, `pg_proc`, arità), un `sqlCheck` con
`expectedResult: 0` («nessuna riga cattiva»), e un `onFail` diverso da `HALT`
(i backfill del pregresso, che su un DB nuovo si segnano da soli).
⚠️ Il verso opposto va invece tenuto: un changeSet di `80_data` **deve**
precondizionare su `tableExists`.

### ⛔ Niente DDL né `preCondition` su un trigger che nasce da `ci_apply`

Presidiato da `scripts/guardrail_ddl_su_trigger_automazione.py` (CI, `ci-validate.yaml`).
Regola estesa: [linee-guida-sql.md §11.5](../docs/it/linee-guida-sql.md).

I trigger di **audit**, **`tx_id`** e **storico** non li scrive nessun changeSet:
li genera il framework delle automazioni con `--contexts=ci_apply`, cioè la
**seconda** invocazione di Liquibase. Durante la prima passata una tabella appena
creata **non li ha ancora**: un `ALTER TRIGGER … RENAME` o un `DROP TRIGGER` senza
`IF EXISTS` su quei nomi passa in sviluppo — dove esistono da settimane — e in CI
muore con `trigger "…" does not exist`.

Il 2026-09-02 è successo su `20260822-25-rename-compensazioni-in-sistemazioni`,
che aveva il fatto **scritto nella propria intestazione** due paragrafi sopra il
difetto.

⭐ E in quel mondo l'operazione non serviva: le automazioni lavorano **per
pattern**, quindi genereranno già il nome nuovo. L'operazione è legittimamente
**condizionale** ⇒ va in un changeSet suo, **uno per trigger**, con
`onFail: MARK_RAN` + un `sqlCheck` su `pg_trigger`.
⛔ Mai una preCondition sul changeSet intero: `MARK_RAN` salterebbe anche la
rinomina della tabella, in silenzio.

⚠️ **Seconda faccia, stessa causa**: anche una `preCondition` che **conta** quei
trigger in `pg_trigger` e ne pretende un numero muore in CI — il 2026-09-02
`20260831-71` chiedeva «i sei guard di disattivazione sono montati», e su un DB
nuovo non ce n'è nemmeno uno. ⭐ Lì il rimedio è **toglierla**: era un doppione
del test 6 del suo pgTAP, che fa la stessa identica query e gira a `ci_apply`
avvenuto. *Una preCondition guarda ciò che viene prima; un invariante si
asserisce in pgTAP.*

### ⛔ In `80_data` convivono catalogo e dati di macchina — si dichiarano

Regola estesa e censimento: [linee-guida-sql.md §11.7](../docs/it/linee-guida-sql.md).

**Catalogo** = parte del contratto del software, vale identico su ogni
installazione, il codice lo nomina per `codice_interno`. **Macchina** = descrive
*questa* installazione. ⭐ Il discriminante si deriva: un seed è di macchina se
**valorizza una FK verso `anagrafiche.*`** — quelle righe nascono dall'uso, e su
un database ricostruito da zero non esistono.

Un seed di macchina si marca `context: dati_macchina`.
🔴 **Ma provato il 2026-09-02: `--contexts="!provision"` NON lo filtra** — quel
filtro esclude ciò che è `provision`, non ciò che ha un contesto qualsiasi. Serve
esplicito, in `ci.yaml` e in produzione: `--contexts="!provision and !dati_macchina"`.
Finché quella riga non c'è, il contesto è documentazione, non un cancello.
⭐ Per i **mirror CSV** c'è una via che non dipende dal contesto: **svuotare il
file** (sola intestazione). Carica zero righe ovunque e non cancella niente dove
quelle righe già esistono. Il contesto serve per i seed scritti in **SQL**.
⛔ I **backfill** che nominano un'anagrafica NON si marcano: su un DB vuoto sono
`UPDATE` su zero righe, quindi innocui.

### ⛔ I privilegi dei ruoli batch stanno nel provisioning, mai in un changeSet

Presidiato da `scripts/guardrail_grant_ruolo_batch.py` (CI, `ci-validate.yaml`).
Regola estesa: [linee-guida-sql.md §11.6](../docs/it/linee-guida-sql.md).

I ruoli `zeroerp_batch_*` hanno `BYPASSRLS`, che vuole **superuser**: Liquibase
gira come `zeroerp` e non può crearli. Li crea
`scripts/sql/provision_db_role_batch_<job>.sql` come `postgres`, **dopo** le
migrazioni standard (concede sul perimetro, e il perimetro deve esistere).
⇒ Per tutto il migrate quel ruolo **non esiste**, e un `GRANT` che lo nomina
ferma la pipeline con `role "..." does not exist`. In sviluppo il ruolo c'è e il
GRANT passa.

⭐ **Ed è inutile**: il provisioning fa `GRANT SELECT/EXECUTE ON ALL … IN SCHEMA`
sui 14 schemi applicativi più `ALTER DEFAULT PRIVILEGES`, quindi copre anche gli
oggetti che nascono dopo. Il rimedio è **togliere la riga**.

⚠️ Il `GRANT` a `zeroerp_app` accanto **resta**: è la riga da cui quella
sbagliata viene copiata — adiacenti e identiche tranne il nome del ruolo.
⛔ Se serve un privilegio *in più* del perimetro ampio, si aggiunge al
provisioning e si rilancia.

### ⛔ I dati di `80_data` si cambiano dal CSV, non con `UPDATE` diretti

La sede di una tabella di configurazione è il suo CSV in `80_data/sql/...`, letto
da un mirror `loadUpdateData`. Un `UPDATE`/`INSERT` SQL sulla stessa tabella crea
una **seconda sorgente di verità**, e le due divergono fra dev e CI: il mirror è
`runOnChange` e ri-esegue a ogni migrate, l'SQL spesso no, quindi su dev vince il
CSV e su un DB ricostruito da zero vince l'SQL (che nella timeline sta dopo).

Successo reale: `20260430-60` faceva `SET meta = '{...}'` sulla matrice dei
preventivi e in CI cancellava `outlined`/icona dell'annullamento,
`requires_righe` su DRAFT→EMESSO e il namespace i18n `vendite.preventivi.*`.

- **Modifica di un valore esistente** → si edita il CSV. Il mirror è
  `runOnChange` + `validCheckSums: ANY` apposta: ri-legge e riallinea.
- **Riga nuova** → append al CSV. Mai un `INSERT` a parte.
- **Cancellazione** → `loadUpdateData` non cancella: lì il `DELETE` SQL
  forward-only è legittimo, ed è l'unica eccezione.
- Se un SQL storico sovrascrive un CSV e non si può cancellare (mergiato):
  spegnerlo **non basta** — su un DB nuovo applica comunque, e comunque dopo il
  loader. Serve un mirror **ri-ancorato** più avanti nella timeline (esempi:
  `20260806-13`, `20260806-14`).

## Regole Documentazione

- I contenuti concettuali principali sono nella documentazione dell'area tecnica (guide).
- Prima di strutturare una soluzione, consultare le guide pertinenti (es. soggetti → guida soggetti e ruoli anagrafici).
- Gli script aggiornati per tabelle/views/funzioni si trovano in `<schema>/tabelle`, `<schema>/views`, `<schema>/funzioni`.
- Non modificare questi file auto-generati: servono solo come riferimento.
- Scrivere o aggiornare solo la documentazione concettuale in `<schema>/manual`.
- Per la documentazione backend (Django), usare sempre una struttura standard nei file manuali:
  - Scopo
  - Contesto
  - Input
  - Output
  - Regole
  - Dipendenze DB
  - Note di migrazione (se applicabile)
- Template di riferimento: `docs/it/backend/_templates/manual-standard.md`

### Build docs (Zensical) - prerequisiti obbligatori

- Stack docs corrente: `zensical==0.0.57` (con `deepmerge==3.0`) + tooling Python in `requirements.txt`.
  ⚠️ Le versioni **si leggono da `requirements.txt`**, non da questa riga: al 2026-08-26 diceva
  `0.0.24`/`2.0` mentre il lock era gia' a `0.0.57`/`3.0`. Un numero scritto in due posti ne ha
  sempre uno stantio, e questo e' quello senza presidio.
- Non usare piu` `mkdocs build` come comando primario di progetto.
- Build docs locale/CI: `python scripts/build_docs_zensical.py`
  - lo script preprocessa `docs/` in `.tmp/zensical_docs`
  - espande i tag `{% include-markdown "..." %}`
  - riscrive i link markdown root `](/dbzero/...)` in `](/it/dbzero/...)`
  - genera config temporanea `mkdocs.zensical.yml`
  - produce output in `site-zensical/`
- Serve locale docs: `bash scripts/serve_docs.sh`.
  - Comando unico: build + server statico su `127.0.0.1:8010`.
  - La preview locale scrive solo in `/tmp/zeroerp-docs-preview` (non modifica file tracciati del repo).
- Se nei markdown si documenta la sintassi include come esempio, evitare placeholder non reali in forma attiva (es. `"..."`) oppure metterli in blocchi codice, per non generare warning del preprocess.

## SQL Conventions

- Schemas/tables/columns naming per `linee-guida-sql.md`
- Prefer UUID for master entities; SERIAL/IDENTITY for technical tables
- Use `tx_id UUID` when required by transaction-id policy
- Audit fields: `data_insert`, `user_insert`, `data_update`, `user_update` (⚠️ `data_`, non `date_`: nel DB sono 806 colonne e nessuna usa `date_`)
- Index naming: `ix_<table>_<column>`; check duplicates via `dbops.vw_duplicate_indexes`
- FK index policy applied in `90_end` with `dbops.apply_fk_index_policy()`
- FK index: non crearli manualmente; se necessari, rispettare il naming di policy e registrare in `dbops.fk_index_policy` (consentito true/false) tramite `dbops.fn_seed_fk_index_policy()` o `dbops.fn_populate_fk_index_policy()`
- Per variabili PL/pgSQL che riflettono colonne, usare `%TYPE` della colonna (es. `v_uom_base_id catalogo.unita_misura.id%TYPE`)
- Nei blocchi SQL di funzioni/trigger inserire commenti sintetici sullo scopo e sulle regole principali.
- In script complessi con molti filtri/parametri, e per evitare duplicazioni di logica, e` consentito usare SQL dinamico (con attenzione alla sicurezza).
- **REGOLA OBBLIGATORIA — DDL/definizioni dalla doc auto-gen, MAI dagli YAML.** Per
  capire o **modificare** una tabella/funzione/trigger ESISTENTE, prendere la
  definizione corrente SEMPRE dalla documentazione auto-generata in
  `docs/it/dbzero/<schema>/tabelle/<nome>.md` e `docs/it/dbzero/<schema>/funzioni/<nome>.md`
  (riflette l'oggetto **vivo** nel DB). **NON** ricostruire il DDL/corpo da un file
  YAML di migration: una funzione viene riscritta da changeSet successivi con
  numerazione più alta, quindi un singolo YAML è quasi sempre **stale** — spesso
  ce ne sono cinque o sei che definiscono lo stesso oggetto, e solo l'ultimo
  conta. Per un `CREATE OR REPLACE` di una funzione esistente: copiare
  il corpo dalla doc auto-gen, applicarvi sopra la modifica, e creare un nuovo file
  con numerazione successiva. Partire dallo YAML rischia di **regredire** silenziosamente
  le revisioni intermedie.
- Nelle funzioni SQL, per parametri numerici di tipo ID applicare guard di validazione esplicita: errore se `NULL` o `<= 0` (non normalizzare silenziosamente).

## Trigger Conventions

- Trigger name: `trg_<schema_opzionale>_<tabella>_<fase>_<descrizione>_<eventi>`
- Phases: `_a10_` for guard/block, `_z90_` for final/deferrable
- Event suffixes: `_ins/_upd/_dlt` (combine if needed)
- Use `UPDATE OF colonna` when logic is column-specific
- Errors via `script.fn_log_and_raise_error(...)`

## Guard vs Check Functions

- `fn_check_*`: pure checks returning boolean, no raise
- `fn_guard_*`: fail-fast, can raise/log

### ⛔ Sollevare un errore: tre canali, tre destinatari

`script.fn_log_and_raise_error(area, funzione, codice, context, tx_id, VARIADIC valori)`
parla a **tre** interlocutori, e confonderli e' il difetto piu' facile da non vedere:

| Cosa | A chi parla |
| --- | --- |
| `codice` | il **backend** — status HTTP e `ui_action`. Registrato a catalogo, con la sua classe. Mai `E_GENERICO` |
| `context ->> 'campo'` | il **frontend** — quale campo accendere. Il nome della colonna, mai il valore |
| `VARIADIC valori` | **l'operatore** — riempie i `%s`, cioe' **compone la frase che una persona legge** |


### ⭐ Due funzioni per sollevare, e a scegliere non sei tu

Dal 2026-09-08 i punti che sollevano il **codice del primo motivo** di una
`script.fn_check_*` non compongono piu' la coda a mano: chiamano
`script.fn_raise_primo_motivo_se_presente`. La domanda che decide e' **una**, e
si vede nella riga che stai scrivendo:

> **Il codice che sollevo lo sto LEGGENDO da un array di motivi, o lo sto
> SCRIVENDO come letterale?**

| Quello che scrivi | Cosa chiami |
| --- | --- |
| `'E_QUALCOSA'` — un letterale | `script.fn_log_and_raise_error` |
| `v_motivi -> 0 ->> 'codice'` | `script.fn_raise_primo_motivo_se_presente` |

⭐ **Sbagliare funzione non compila**: i tipi non legano (`42883` in un verso,
`22P02` nell'altro). L'unico modo di sbagliare e' **non usarla** — ricopiare la
coda — e quello e' silenzioso: lo presidia `db/pgtap/script/test-rubinetto-primo-motivo-v1.sql`.

⛔ **L'array non lo costruisci tu.** Se stai scrivendo
`jsonb_build_array(jsonb_build_object('codice', 'E_X', ...))` per poter usare
l'helper, stai usando l'attrezzo sbagliato: quel motivo lo conosci gia', e il
`-> 0` non sceglie niente.

⚠️ **E c'e' un caso in cui l'helper NON si usa anche se hai i motivi**: quando
la `fn_check_*` **non emette `valori`**. Li' la frase la compone il chiamante
dai propri dati, e delegare la spezzerebbe — uscirebbero i `%s` grezzi a video.
Sono tredici siti, dichiarati come debito nel presidio.

⭐ **La domanda che viene PRIMA**, quando scrivi un guard nuovo, non e' quale
funzione chiamare: e' **«questa regola deve anche accendere o spegnere un
pulsante nel frontend?»**. Se si', il predicato va in una `fn_check_*` e il
guard la CHIAMA (§12.5.2) — e allora ti ritrovi i motivi in mano. Se no,
valuti li' e sollevi il codice diretto.

Brief: `docs/it/dev/work-done/brief-db-coda-primo-motivo-in-un-posto-solo.md`.

⛔ **Nel `VARIADIC` non entra mai il nome di un parametro PL/pgSQL o di una
colonna.** Un codice registrato con dentro `'p_centro_riscossione_id (obbligatorio,
> 0)'` passa **tutti** i cancelli — guardrail dei codici, rubinetto degli
accumulatori, rigenerazione delle policy — e produce un messaggio di qualita'
`E_GENERICO`. *Il codice sceglie la frase, ma il valore che ci si infila dentro lo
sceglie chi solleva.*

⭐ E il valore decide anche **quale codice serve**: la domanda «riuso o conio?» si
risponde su **chi puo' rimediare**, non sulla condizione. Si guarda **parametro
per parametro**, non funzione per funzione:

| Il dato lo fornisce… | Codice | Classe |
| --- | --- | --- |
| una **persona**, in un form | di dominio, frase che **nomina il dato** | `DATO_ERRATO` (400) |
| solo un **chiamante rotto** (`id <= 0` dove il `NULL` e' ammesso, enum vuoto) | di dominio, messaggio che **nomina il parametro** | `TECNICO` (500) |

⛔ **Nella seconda riga NON si riusa `E_PARAMETRO_INVALIDO`**, ed e' la scelta che
sembra ovvia: quel codice e' un **debito, non una sede**. La D11 di
`work-done/brief-db-be-classe-codici-errore.md` lo dichiara **split rimandato**
(«denominatore sicuro + note, e cantiere suo»), e la §9.1 dice che *«rincorrere
gli esistenti senza chiudere il rubinetto e' la forma in cui questi registri non
calano mai»*. Sopravvive perche' il BE deve gestire le funzioni vecchie.
⭐ Precedente: `E_VENDITE_PRICING_ESITO_ASSENTE` (2026-08-19, TECNICO) nasce
perche' il rubinetto B-7 respinse `E_PARAMETRO_INVALIDO` — *«li' non c'e' nessun
parametro invalido, c'e' un'invariante rotta»*.
⚠️ E su un `TECNICO` la chiave `campo` **esce** dal contesto: su un 500 non c'e'
nessun campo da accendere.

⚠️ **Ma un messaggio puo' nominare una colonna DI PROPOSITO**, quando il lettore e'
uno sviluppatore e la colonna e' l'informazione utile (*«Movimento incoerente con
la riga %s: %s vale %s, mentre la riga dice %s»*). La domanda non e' «c'e' un nome
di colonna?» ma **«l'ho messo perche' serve a chi legge, o perche' non avevo
voglia di scrivere una frase?»**.

⛔ **Non c'e' un cancello automatico, ed e' una scelta.** Misurato il 2026-08-21 su
`pg_proc`: 265 valori sospetti su 1469, in **157 funzioni** — e' lo stile in cui il
progetto e' cresciuto, non una svista isolata. Un controllo euristico sbaglierebbe
proprio sul caso legittimo, e vale il criterio gia' scritto per il rubinetto degli
accumulatori: *un cancello che capisce un caso su cinque boccia a caso e passa a
caso; dopo due blocchi sbagliati qualcuno lo spegne, e un presidio spento e' peggio
di uno assente*. Il presidio praticabile e' **per caso**, con un `throws_like` nel
pgTAP dove la frase e' la posta in gioco.
⚠️ Corollario operativo: toccando una funzione **vecchia**, il messaggio va
guardato — non dato per buono perche' il codice e' registrato.

Regola completa, esempi e criterio «riuso o conio un codice?»:
[Messaggi di Errore e Generazione Log](../docs/it/guide/Messaggi-di-Errore-e-Generazione-Log.md).

## Workflow Safety

- Ask before running DB migrations locally
- ⛔ **E dal 2026-08-15 non e' piu' una raccomandazione: e' un cancello.**
  `scripts/guardrail_no_db_migrate.py`, agganciato come hook `PreToolUse` su
  Bash in `.claude/settings.json`, **blocca** `liquibase update` /
  `rollback` / `changelogSync` e `make db-migrate|db-ci-apply|db-setup`.
  Restano liberi `status`, `validate`, `updateSQL` (che non applica) e i pgTAP,
  che girano in transazione.
  **Perche' esiste**: la regola qui sopra c'era gia', ed e' stata infranta lo
  stesso — un «fai tutto il possibile lato DB» letto come autorizzazione a
  migrare. Un'istruzione in un documento e' una raccomandazione; l'hook gira nel
  harness e non dipende da come il modello interpreta una frase.
  ⚠️ **«procedi», «vai avanti», «fai tutto il possibile» NON autorizzano una
  migrazione**: autorizzano il lavoro, non l'applicazione. L'autorizzazione si
  chiede per **quel** comando, e la da' l'utente a parole.
  Non disattivare l'hook per far passare un comando: e' l'unica cosa che non
  va fatta.
- Avoid destructive commands without explicit approval
- **Bug di dati in sviluppo**: prima di sviluppare fix software per correggere dati errati, chiedere all'utente se è più veloce correggere/cancellare i dati manualmente. I fix software per problemi di dati creano strati di codice inutili che poi vanno rimossi.

## Test (pgtap)

- Test DB: pgtap
- Percorso: `db/pgtap/`
- Nei file di test, all'inizio inserire un indice dei test eseguiti nei commenti.
- Nei file di test Python/Django, inserire all'inizio un breve indice dei test previsti (nome test/caso).
- Negli smoke test bash (`backend/scripts/smoke-test-*.sh`), inserire un blocco `# Indice test (0..N):` dopo l'header, elencando ogni sezione di test.

### ⚠️ Gli smoke: nessuno li lancia, e per un giorno erano rotti in sei

`backend/scripts/tests/smoke-*.py` — undici script che parlano col database di
sviluppo, ognuno in `transaction.atomic()` + `set_rollback(True)`, quindi
**eseguibili senza lasciare niente**.

⛔ **Non li raccoglie il runner Django** (stanno fuori da `apps/`, hanno il
trattino nel nome e il pattern di scoperta e' `test*.py`) e **non li esegue la
CI**. Il 2026-08-27 sei degli undici erano rossi **da un giorno** senza che
nessuno se ne accorgesse: `vendite.attivita_fatturabili.fatturato` era diventata
`GENERATED` e le fixture continuavano a scriverla. Il difetto veniva da un
cantiere che quei file non li aveva nemmeno aperti.

```bash
scripts/smoke-baseline.sh                   # tutti, ~4 min
scripts/smoke-baseline.sh fattura-scadenze  # solo quelli col nome dato
scripts/smoke-baseline.sh --update          # rigenera il registro dei noti
```

Stessa forma di `pgtap-baseline.sh`: non-verde **noto** → silenzio, non-verde
**nuovo** → `exit 1`, noto rientrato → lo segnala. Registro in
`backend/scripts/tests/baseline-smoke.tsv`, che e' un **debito** e deve calare.

⛔ **Il codice di uscita di uno smoke non dice la verita'**: ce n'e' uno che
stampa «ESITO: FALLITO» e esce **0**. Chi li lancia a mano con `&&` legge verde
su un rosso — lo script classifica dall'**output**, ed e' il motivo per cui
esiste invece di essere un `for`.

⚠️ **Gli esiti sono TRE.** Oltre a verde e rosso c'e' `SENZA_MATERIA`: lo script
si ferma su una precondizione assente e lo **dichiara** (`raise SystemExit`).
Non e' un difetto, ma la copertura di quel giro vale **zero**, non «parziale»:
va vista, non nascosta fra i verdi.
- Struttura test Django per app: `apps/<schema>/tests/` con sottocartelle minime `api/` e `services/`.
- Esempio esecuzione test Django: `./manage-test.sh apps.core.tests.api -v 2`
- Smoke test API docs/schema: vedi `apps/core/tests/api/test_diagnostics_api.py` (endpoint `/api/docs/` e `/api/schema/`).

### ⭐ Prima di scrivere un test: il template e la guida

```bash
cp db/pgtap/_TEMPLATE.sql.txt db/pgtap/<schema>/test-<cosa>.sql
```

Guida: [pgtap-come-si-scrive-un-test](../docs/it/guide/pgtap-come-si-scrive-un-test.md).

⚠️ **Dal 2026-08-07 i test girano come l'APPLICAZIONE** (`zeroerp_app` +
contesto operatore), non piu` come owner: **le policy RLS sono attive a ogni
corsa**. Un rosso puo` essere un **permesso** o una **policy**, non solo una
fixture — e una fixture che scrive dove l'applicazione non scrive **non passa
piu`**. Se trovi un documento che dice «il pgTAP gira come owner», e` vecchio.

Tre righe di preambolo sono obbligatorie e presidiate da
`scripts/guardrail_pgtap_preambolo.py` (CI): `BEGIN;`, la riga di contesto,
`SET CONSTRAINTS ALL IMMEDIATE`. Senza, il file diventa **verde per
sottrazione** — passa smettendo di verificare. Le esclusioni si **dichiarano**
(`-- pgtap-contesto: escluso — …`), non si spiegano solo in prosa.

⚠️ E `throws_ok(sql, NULL, NULL, …)` accetta **qualunque** errore: passare
sempre lo SQLSTATE (`'P0001'` per un errore di dominio) o usare `throws_like`
sulla frase. Il cancello presidia questo debito **a soglia**: puo` solo calare.

### ⚠️ La suite ha rossi preesistenti: usare la baseline

Una parte dei pgTAP e` rossa da prima (fixture rimaste indietro rispetto a guard
entrati dopo). **Non attribuire un rosso alla propria modifica senza verificare.**

```bash
scripts/pgtap-baseline.sh vendite          # confronta col noto (solo gli schemi toccati)
scripts/pgtap-baseline.sh                  # tutta la suite (~7 min)
scripts/pgtap-baseline.sh --update vendite # dopo aver sanato dei file
```

Lo script distingue **regressioni** (rosso nuovo → exit 1) da **rossi gia` noti**
(silenzio) e segnala i **rientrati** (ora verdi, da togliere dalla baseline).
Registro: `db/pgtap/baseline-rossi.tsv`, con la causa classificata.

⚠️ **In CI la suite gira**: sempre sulle PR verso `main`, e sui push a
`Tito-dev` **solo se toccano `db/` o `scripts/`** (costa ~7 min, e Tito-dev e'
anche il ramo di scambio BE/DB: 107 commit su 656 negli ultimi 30gg toccano solo
`backend/`). Sulle PR verso Tito-dev gira il solo cancello statico. E usa una baseline **sua**,
`db/pgtap/baseline-rossi-ci.tsv`: il database della CI e` ricostruito da zero,
quello di sviluppo ha dati veri, quindi i rossi sono popolazioni diverse. **Un
rosso in CI non e` automaticamente un rosso da te**: guarda quale baseline lo
conosce prima di inseguirlo.

⚠️ La baseline e` un **registro di debito, non una lista di eccezioni**: deve
calare. Un file che fallisce nel *fixture* non esegue **nessuna** asserzione — la
sua copertura vale zero, non "parziale", ed e` un'area che *sembra* coperta.
Bonifica in corso: `docs/it/dev/work-done/brief-db-bonifica-pgtap-sorgente-polimorfa.md`.

### Regole test Django per compatibilità CI

I test Django devono funzionare in CI (GitHub Actions) **senza dipendere da un DB reale accessibile**:

- **Usare `unittest.TestCase`** (o `django.test.SimpleTestCase`) per test unitari con mock. **Non** usare `django.test.TestCase` a meno che il test non necessiti realmente del database.
- ⚠️ **Quella regola oggi regge una seconda cosa, non dichiarata: leggere prima di infrangerla.**
  Django crea il database di test usa-e-getta **solo se almeno un test dichiara di
  averne bisogno** (`django.test.TestCase`, `TransactionTestCase`, o `databases = [...]`).
  Oggi in `backend/apps` **nessuno lo dichiara** (114 `unittest.TestCase`, 86
  `SimpleTestCase`, zero `django.test.TestCase`), quindi il runner stampa
  «Skipping setup of unused database(s)» e la connessione dei test resta quella
  **configurata**, cioe' un DB con lo schema Liquibase completo.
  Ci si appoggiano i 3 test end-to-end di
  `apps/core/tests/services/test_db_error_fields.py` (attivi con
  `ZEROERP_TEST_DB_E2E=1`, accesi in CI), che interrogano funzioni PL/pgSQL vere,
  e il cancello del terzo lato `apps/core/tests/test_error_codes_db_policy_guardrail.py`
  (stessa opt-in), che legge `dbops.vw_codici_errore_da_dichiarare`.
  **Il primo test che dichiarera' un database fara' creare al runner un DB vuoto
  per TUTTA la suite**: li' `script.fn_log_and_raise_error` non esiste e quei tre
  falliranno con «la funzione non esiste», in una PR che non c'entra nulla. Non e'
  un divieto — e' che, se lo fai, quei tre vanno adeguati nello stesso commit.
  ⚠️ Il cancello del terzo lato in quel caso **salta** (guard sullo schema in
  `setUpClass`) invece di fallire — ma un cancello che salta non presidia niente:
  se un giorno la suite creera' davvero un DB usa-e-getta, va riportato su un DB
  provvisto da Liquibase, non lasciato skippato.
- **Mockare ogni accesso DB**: se il codice sotto test usa `django.db.connection` (cursor, advisory lock, query dirette), mockare quei metodi nel test. Non fare affidamento sul DB di sviluppo.
- **Pattern consigliato** per metodi che accedono al DB (es. advisory lock, cursor raw):

  ```python
  def setUp(self):
      patcher = patch.object(MyClass, "_metodo_che_usa_db", return_value=valore)
      self._mock = patcher.start()
      self.addCleanup(patcher.stop)
  ```

- **Endpoint API con `@extend_schema`**: ogni `APIView` esposta su `/api/v1/` deve avere il decoratore `@extend_schema` su ogni metodo HTTP pubblico (`get`, `post`), per evitare warning drf-spectacular in CI e generare documentazione OpenAPI corretta.
- **Verifica locale pre-push**: eseguire `./manage-test.sh -v 2` per confermare che tutti i test passano. Per simulare l'ambiente CI (senza DB), usare:

  ```bash
  DB_HOST=localhost DB_PORT=5432 DB_NAME=zeroerp DB_USER=zeroerp DB_PASSWORD=secret \
  DJANGO_SECRET_KEY=ci-placeholder DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1" DJANGO_DEBUG=0 \
  .venv/bin/python manage.py test -v 2
  ```
