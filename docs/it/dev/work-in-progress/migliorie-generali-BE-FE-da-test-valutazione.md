# Migliorie generali BE / FE da test valutazione

> Valutazione dello strato **applicativo** — backend Django e frontend Vue —
> presa il **2026-09-09** sul commit `c1f9e571e` (`dev/backend-tid`), sullo
> **schema OpenAPI generato** (`manage.py spectacular`, 615 path / 815
> operazioni), sui due workflow di CI, sull'esito di `manage.py check --deploy`
> e su una corsa di CI misurata da GitHub Actions (`34343449743`). È il gemello
> di [migliorie-generali-da-test-valutazione.md](migliorie-generali-da-test-valutazione.md),
> che copre il solo strato DB e a cui questo documento rimanda per tutto ciò che
> sta dentro PostgreSQL.
>
> ⚠️ **Sfoltito il 2026-09-12.** Le voci chiuse portano **solo la data e la
> forma della chiusura**, con il rimando al documento o al file in cui il
> dettaglio vive oggi; lo stato precedente non è più descritto qui. Chi vuole il
> *prima* di una voce lo trova nella storia git di questo file (versioni fino
> all'11-09). Le voci aperte restano per intero: sono l'unico contenuto ancora
> «attuale».

---

## 0. Come si legge

Vale il metodo del documento gemello: **una media su dodici aree è lo strumento
sbagliato**, perché tratta «i nomi dei file» e «cosa impedisce a una regressione
di entrare» come due addendi dello stesso peso. Perciò il documento separa ciò
che **è stato costruito** (§2) da ciò che **non tiene** (§3), ordina i difetti
per **conseguenza**, dichiara ciò che **non è un difetto** (§4), dà una
scorecard **pesata** (§5) e dichiara ciò che **non ha potuto misurare** (§7).

⚠️ Tutte le misure sono **letture di struttura** — quali file esistono, cosa
dichiara un `paths:`, quale classe eredita una view, cosa dice uno schema
OpenAPI — e sono **fatti datati**. Dove compare un conteggio di comportamento
(§3 D6) è come **controesempio**, mai come motivo.

**Perimetro**: `backend/` (951 file Python, ~258.000 righe) e `frontend/` (390
`.vue` + 290 `.js`, ~117.000 righe), più i cancelli di CI e i presidi che li
riguardano. Il database compare **solo** dove è il capo opposto di un contratto
applicativo (catalogo dei codici errore, delle aree funzionali, dei messaggi).

---

## 1. Il dichiarato, riletto — ✅ chiuso il 2026-09-09

Sette righe dei quattro documenti di contesto obbligatorio erano invecchiate,
cinque su sette **verso il pessimismo** (capacità costruite e non registrate).
Tutte chiuse il 2026-09-09:

| Voce | Com'è stata chiusa |
| --- | --- |
| Stack frontend in tre sedi (`AGENTS.md`, `PROJECT_CONTEXT.md`, `frontend-standards.md`) | **Tolto**, non aggiornato: fonte unica `frontend/package.json`, i documenti rimandano. Sanato anche il residuo fuori tabella (`frontend-standards.md` §Tab-View, riscritto su *quale API* si usa) |
| `PROJECT_CONTEXT.md` elencava 10 app su 17 | Elenco completo; `ai_assistant` entra in `api.md` §Endpoint attivi **con il difetto D5 scritto accanto** |
| `api.md`: `ui_action` «non letto», §Test «due livelli» | `ui_action` con il conto per valore; §Test a **tre** livelli, con quali girano in CI |
| `AGENTS.md`: `unittest.TestCase` e `SimpleTestCase` come alternative | Riscritta l'11-09 con D9-b |
| `api.md`: `hint` «il frontend non lo legge» | Chiusa **rendendo vero il codice** (D4), non riscrivendo la frase |
| `api.md`: «la testata ha la RLS, il figlio no» in **cinque** voci dell'inventario (segnalato da Tid il 12-09) | Stantie dal D2 del gemello (`20260909-27` ÷ `20260910-33`; una da **luglio**). Corrette il 2026-09-13: il fatto sta ora in **una** sede (§Enforcement RLS) e le cinque voci ci rimandano |

⭐ Le due regole che restano da qui: *un numero scritto in due posti ne ha sempre
uno stantio, e si toglie invece di aggiornarlo*; *un documento che dice il vero
su un difetto non si corregge: si rende falso chiudendo il difetto*.

---

## 2. Cosa è stato costruito — stato al 2026-09-12

### 2.1 Due catene di verifica, una per metà del prodotto

**Backend — `ci-validate.yaml`**: gira su ogni push a `Tito-dev` e su ogni PR
verso `Tito-dev` o `main` che tocchi `backend/`, `db/`, `requirements/` o
`scripts/`, senza `continue-on-error`. Dentro, in ordine: pre-commit sui file
cambiati (con `ruff`, dal 09-09), sette guardrail statici, il migrate Liquibase
completo, il provisioning dei ruoli, `manage.py check`, il guardrail dei
riferimenti morti compilati con `plpgsql_check`, la suite Django.
Misurato dalla CI (corsa `34343449743`, 2026-09-09): **4.565 test trovati /
4.560 eseguiti, OK, 6 saltati, 33,1 s** di suite su un job di 5m20s.
⚠️ Il rovescio dei 33 secondi è D9: una suite così veloce è quasi interamente
mockata.

**Frontend — `ci-frontend.yaml`** (✅ nato il 2026-09-09, merge #1547; workflow
suo, perché una modifica al CSS non ha bisogno di Postgres e Liquibase): `npm ci`
· `npm run lint` (oxlint + eslint, **senza `--fix`**; la comodità sta in
`npm run fix`, che di proposito non si chiama `lint:*`) · `npm run guards` · test
`vitest` · `npm run build` · `scripts/check_i18n_keys.py`. Durata ~47 s. Node
risolto da `engines.node` di `package.json`, nessun numero ricopiato nel
workflow. Al 2026-09-12 i file `.spec.js` sono **tre** (`useApiHandler`,
`useNotify`, `ramoBannerLotto`): il valore è il contratto dell'envelope che
fissano, non la superficie coperta — vedi D1-d-bis.

### 2.2 Analisi statica del backend — `ruff`, dal 2026-09-09

`ruff.toml` alla radice, hook pre-commit `ruff-check` che gira anche in CI.
Selezione `F`, `E9`, `T20`, `C4`, `A`, `PIE`, `G`, `LOG`; ogni gruppo acceso a
**registro zero** dopo aver misurato e sanato. ⭐ Le regole **non** accese (`E`,
`B`, `B904`) e il formattatore **spento** sono decisioni scritte con il perché
dentro `ruff.toml`: quella è la sede, non questo documento. Manca il **type
checker** (D2-b).

### 2.3 Il contratto del codice errore, lato backend, è chiuso a chiave

| | |
| --- | --- |
| Codici a catalogo (`error_policies_generated.py`) | 852 |
| di cui ritirati (`CODICI_RITIRATI`) | 89 |
| **Codici vivi** | **763** |
| Codici vivi **senza** frase di ripiego | **0** |
| Frasi di ripiego **orfane** / con `%s` non riempibile | **0** / **0** |

Presidiato da `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego` a ogni corsa.
La classe non si deriva dallo status e viceversa; `UI_ACTION_PER_CLASSE` porta
scritto perché su `DATO_ERRATO` il default è il banner e non l'evidenziazione.

### 2.4 Le base view: una catena sola, e la si vede

448 view ereditano `DomainAPIView`, 75 `AdminAPIView`; le **11** su `APIView`
nudo sono tutte e sole quelle pre-autenticazione (§4). 109 endpoint dichiarano
`is_search_endpoint`, 68 un `post_permission`, 63 un `model_permission`, 56
`require_idempotency_key=True`. ⭐ Il reset dei GUC di identità in
`JwtAuditMiddleware.process_request` è incondizionato e **fail-closed**: se
fallisce, la richiesta non viene servita.

### 2.5 Il frontend è un sistema di building block

83 composable, 97 componenti core, 48 moduli API, 7 store globali, 16 utility.
**Un solo** file importa `axios` (`src/core/api.js`); `v-html` a zero;
`console.log` a zero; 63 view su `<ListaConfigurabile>` più 8 su
`DrawerTabLista`. `bersagli.js` trasforma i `targets` di un errore in un
pulsante e degrada in modo esplicito (tipo senza destinazione, area BLOCCATA, id
non convertibile ⇒ nessun pulsante).

### 2.6 Il multilingua del frontend è fatto, non «possibile»

4.697 chiavi in `it.json` e `en.json`, **zero** presenti in una sola lingua,
346 `.vue` su 390 usano `useI18n`, zero stringhe cablate nel template.
Presidiato da `scripts/check_i18n_keys.py` (pre-commit **e** `ci-frontend`), con
53 chiavi costruite dinamicamente dichiarate come punto cieco.
⛔ La condotta `Accept-Language` → GUC `myapp.user_language` → messaggio nella
lingua giusta è **completa**, e il seed `config/messaggi_errore.csv` ha 846
righe `it` e **1** `en`: il consumatore esiste e aspetta il catalogo (gemello
§2.3).

### 2.7 Sei presidi scritti apposta per il frontend, in CI

Raccolti in `npm run guards` (`run-s guard:*`): chi ne aggiunge uno lo trova in
CI senza toccare il workflow.

| Presidio | Cosa tiene |
| --- | --- |
| `check-liste-configurabili.mjs` | contratto `@row-click` |
| `check-pinia-user-scoped-reset.mjs` | reset degli store al logout |
| `check-drawer-width.mjs` | chiavi `DRAWER_WIDTH` |
| `check-primeicons-codepoints.mjs` | codepoint cablati + baseline anti-drift |
| `check-keepalive-onactivated.mjs` (09-10, D8) | una view sotto `<KeepAlive>` ha un `onActivated`, suo o di un composable — criterio derivato dal router e risolto transitivamente |
| `check-datatable-baseline.mjs` (09-10, D10) | il registro delle `DataTable` grezze **può solo calare** |

### 2.8 La convenzione `# Scopo:` è reale

3.809 commenti `# Scopo:` su 3.815 `def` nei sorgenti non-test: il 99%.

---

## 3. I difetti, in ordine di conseguenza — stato al 2026-09-12

| | Difetto | Stato |
| --- | --- | --- |
| D1 | Il frontend non ha nessun cancello | ✅ 09-09 · aperti D1-d-bis, D1-f |
| D2 | Backend senza analisi statica | ✅ 09-09/10 · aperto D2-b |
| D3 | Lo schema OpenAPI si dichiara anonimo; `check --deploy` fuori dalla CI | 🟠 D3-a ✅ 09-09 · aperti D3-b, D3-c |
| D4 | `hint` trasportato e mai reso a video | ✅ 09-09 |
| D5 | `area_funzionale = "ai_assistant"` non a catalogo | 🔵 brief scritto 09-11, **attende il DB** |
| D6 | Il `count` che è un'eco | ✅ 09-10 |
| D7 | Endpoint senza consumatore | ✅ decisione 09-11 · 🔵 schermata email log aperta |
| D8 | View sotto `KeepAlive` che caricano solo in `onMounted` | ✅ 09-10 |
| D9 | Suite larga e poco profonda; smoke non lanciati | 🟡 aperto D9-a · D9-b ✅ 09-11 |
| D10 | I registri di debito non hanno un verso | ✅ in parte 09-10 · aperto D10-bis |
| D11 | Quattro app scheletro | ✅ deciso 09-11 |
| D12 | Portali costruiti a DB, senza porte | 🟡 cantiere dichiarato |
| D13 | Job notturno rotto da quattro notti | ✅ 09-09 · D13-bis ✅ 09-11 |
| D14 | «Inviata» detto di una mail mai partita | ✅ 09-11 |
| D15 | `skip_area_check` è **muto** su 15 view; sei scrivono senza permesso | ✅ 09-12, tutte e 15 |

### D1 — Il frontend non aveva nessun cancello

✅ **Chiuso il 2026-09-09**: `ci-frontend.yaml` (§2.1), i sette errori `oxlint`
sanati **prima** di accenderlo, `--fix` tolto dagli script `lint:*`, i guard in
`npm run guards`, `vitest` con il primo file provato **per mutazione** (quattro
mutazioni, quattro rossi). Il guard i18n gira dove il frontend cambia, invece
di svegliarsi solo quando il commit toccava anche il backend.

✅ **D1-e, stesso giorno**: `scripts/check_license.py` era verde in ogni corsa di
CI **per il motivo sbagliato** (leggeva il solo indice staged, vuoto dopo un
checkout). Ora distingue la modalità **range** (`PRE_COMMIT_FROM_REF`/`TO_REF`,
la forma della CI) dall'indice staged; `sys.argv` si usa solo per intersecare,
così il cricchetto resta sui soli file **aggiunti**. `verbose: true` perché il
verde dica su quanti file.

**Residui aperti:**

* **D1-d-bis** — il primo test di **componente** (`ListaConfigurabile`, 63 file
  la usano). Vuole `@vue/test-utils` + `jsdom`, da aggiungere **quel giorno**;
  e vuole che qualcuno decida *cosa* deve asserire.
* **D1-f** — ✅ le due vulnerabilità (`browserslist` alta,
  `baseline-browser-mapping` moderata, entrambe di sola **build**) sanate il
  2026-09-13 su segnalazione di Tid dagli avvisi Dependabot: **nessun
  override e nessuna dipendenza nuova** — i range già dichiarati (`^4.24.0`,
  `^2.10.38`) ammettevano le versioni corrette, è bastato aggiornare i due
  pacchetti nel lock (4.28.9 e 2.11.23). `npm audit` a **zero**; lint, guard,
  44 test e build verdi. ⚠️ **Resta la decisione**: il difetto non era la
  vulnerabilità, è che nessuno lancia `npm audit` — oggi il registro è a zero,
  cioè l'unico momento in cui un cancello nasce senza arretrato
  (`npm audit --audit-level=high` nel job `ci-frontend`).
  ⭐ **E il quarto avviso Dependabot era del backend**: `weasyprint 69.0`
  (`< 70.0`, SSRF su `url_fetcher`, CVE-2026-55073). L'11-09 non si poteva
  sanare — la 70.0 era uscita l'8-09 e il pin `<70` la escludeva. Chiuso il
  2026-09-13: tetto a `<71`, `pip-compile --upgrade-package weasyprint` (una
  riga nel lock), nessun altro pin mosso, fattura vera stampata con la 70
  **identica** check per check alla 69, `apps.documenti` 252 e suite 4.652
  verdi. ⚠️ **Residuo dichiarato**: la 70 avvisa che il ripiego su fontTools
  per il subsetting dei font *«will be unsupported in future versions»* —
  `libharfbuzz-subset0` manca nel `Dockerfile` e sulle macchine di sviluppo,
  e va aggiunto **prima** della 71 (INFRA-2).

### D2 — 258.000 righe di Python senza analisi statica

✅ **Chiuso il 2026-09-09** (`F`+`E9`, 136 rilievi sanati prima di accendere) e
**allargato il 2026-09-10** (`T20`, `C4`, `A`, `PIE`, `G`, `LOG`): §2.2 e
`ruff.toml`. L'allargamento ha trovato due difetti veri: `B017` (due
`assertRaises(Exception)`, ora pretendono tipo **e** codice) e `PIE794`
(`stato_codice_interno` dichiarato due volte in `OffertaRow`). Rimosso
`_check_fn_tmp.py` (ok di Tid).

**Aperto — D2-b**: decidere **se** il progetto vuole un type checker. Se sì,
`python.analysis.typeCheckingMode` nel repo o `mypy --follow-imports=skip` sui
soli `apps/*/services/`; se no, togliere da `AGENTS.md` la riga sull'`assert`
«per aiutare il type checker», che oggi chiede un lavoro a beneficio di nessuno.
⚠️ È la metà che vedrebbe i difetti di giuntura che una suite mockata (D9) non
può vedere.

### D3 — Lo schema OpenAPI e il ramo `--deploy`

✅ **D3-a, chiuso il 2026-09-09**: `apps/core/api/openapi_extensions.py`
(`OpenApiAuthenticationExtension` per `JwtAuditAuthentication`, registrata per
import in `CoreConfig.ready()`). `components.securitySchemes` presente,
`security:` su tutte le 815 operazioni, `check --deploy` da 677 a **124**
problemi, i 607 `W001` a zero.

**Aperto — D3-b**: `manage.py check --deploy` **non gira in CI**, e
drf-spectacular aggancia i propri controlli a quel ramo: la CI lancia `check`
liscio e non ne vede nessuno. Restano **66 `W002`** (view senza `@extend_schema`
su qualche metodo — violano una regola scritta in `AGENTS.md`), **54 collisioni
di `operationId`** (`…_retrieve` / `…_retrieve_2`, prima invisibili sotto i
607) e `mail.E001` (in CI va impostato il backend di posta giusto, non
silenziato). Non è configurazione: è aprire un registro da 66 e dargli un verso.

**Aperto — D3-c**: `SECURE_HSTS_SECONDS` e `SECURE_SSL_REDIRECT` assenti dal
ramo non-debug di `settings.py` (l'effetto lo decide il reverse proxy: da
concordare con chi gestisce nginx); **nessuna CSP**, né in `settings.py` né in
`index.html`, con i due token JWT in `localStorage`. La postura regge perché
`v-html` è a zero e `axios` sta in un file solo — cioè perché **non c'è
superficie** — ma nessun presidio la verifica. O si aggiunge la CSP, o si scrive
perché no.

### D4 — Il terzo lato del contratto d'errore

✅ **Chiuso il 2026-09-09**. `hint` arriva a video in **un** posto:
`useApiHandler` lo espone come `soluzione`, il toast lo rende nel `detail`
sotto il messaggio; chi usa `execute` ce l'ha senza modifiche. La condizione che
lo rende mostrabile sta nel backend: `_apply_policy` lo toglie sui tre codici di
`is_technical_code`, dove il canale `HINT` porta il testo di PostgreSQL e non la
soluzione a catalogo — regola **diversa** da quella del bersaglio, provata nei
test. Il blob `errore` del 200 del `pipeline_runner` passa ora da
`to_api_error` invece di leggere `exc.hint`/`exc.targets` diretti (due regole per
lo stesso nome). Le sei `ui_action` non ramificate sono **dichiarate servite**
dal default (decisione di Tid): tabella per valore in `api.md`.
Dettaglio: `api.md` §Envelope, `frontend-standards.md` §La soluzione.
⚠️ Chi chiama `notify.error(...)` a mano resta fuori: il canale è `execute`.

✅ **Stesso giorno, il building block che otto punti riscrivevano a mano**: otto
coercizioni `jsonb` manuali portate su `jsonb_out` (non `coerce_jsonb_dict`: su
`registra_tentativo_login` il ripiego a `{}` sarebbe stato un fail-open), con
due presidi — `test_coercizione_jsonb_dal_bb` (la forma, registro a zero) e
`tests/db/test_jsonb_stringa_negli_otto_lettori` (il comportamento).

### D5 — `area_funzionale = "ai_assistant"`: un cancello che non si può aprire

🔵 **Aperto, attende il DB.** `AIQueryView` dichiara `area_funzionale =
"ai_assistant"` e il catalogo `config.aree_funzionali` (13 righe) non la
contiene: per `script.fn_resolve_livello_area` un'area fuori catalogo è
**`BLOCCATO`** per tutti tranne `SUPER_ADMIN`, e **nessuno può concedere il
permesso** perché non esiste la riga a cui appenderlo. Il 403 è indistinguibile
da «non hai il permesso». Oggi la rotta è dietro `AI_ENABLED=0`; il giorno in
cui si accende, si accende rotta per tutti tranne uno.

**Decisione di Tid, 2026-09-11**: l'assistente lo devono poter usare **anche gli
operatori** ⇒ riga a catalogo, strada `AdminAPIView` esclusa. Brief:
[brief-db-area-funzionale-assistente-ai.md](brief-db-area-funzionale-assistente-ai.md),
che chiede anche di correggere il `COMMENT` della tabella (*«ogni area corrisponde
a uno schema DB»*: già falso per `core` e `strumenti`). Il backend non ha niente
da cambiare nel codice; appena la riga c'è, scrive il **presidio** che manca —
un test su DB provvisto che confronta le `area_funzionale` dichiarate dalle view
con i codici a catalogo, derivando l'elenco dalle view.

### D6 — Il `count` che è un'eco

✅ **Chiuso il 2026-09-10.** Nei lookup con `LIMIT` il `count` era
`len(results)` — un numero che conferma il troncamento invece di rivelarlo. Il
rimedio è una **sonda `+1`** nel repository (che è l'unico a conoscere
`safe_limit`), building block `fetch_con_sonda` in `apps/core/db/_helpers.py`,
e `troncato` nell'envelope; l'helper unico è diventato due
(`_collezione_completa` senza `LIMIT`, `_lookup_response` con), perché la forma
sbagliata e quella giusta erano la stessa riga di codice. `troncato` arriva a
video da `useAutocompleteRefineHint`, lo stesso che serve gli altri lookup ricchi.
Presidio sul **DB vero** (`apps/catalogo/tests/db/test_lookup_troncamento.py`),
provato con tre mutazioni. ⭐ Il consumatore vivo era **l'assistente AI**
(`CercaArticoliTool`, che avrebbe detto «ho trovato 10 articoli» su 257);
`fn_lookup_unita_misura` è stata **cancellata** perché nessun endpoint la
raggiungeva (le UoM passano dal lookup generico).
⚠️ Residuo, dichiarato: `count: len(...)` sulle collezioni **senza** `LIMIT` è
numericamente giusto, ma nessun cancello impedisce a un `LIMIT` di comparirci
sopra un giorno.

### D7 — Endpoint costruiti, documentati, mai raggiunti da una schermata

✅ **Decisione scritta il 2026-09-11** per tutte e tredici le rotte:
[piano-be-fe-endpoint-senza-porta.md](piano-be-fe-endpoint-senza-porta.md) §1.
Due famiglie (10 rotte, `/core/email/log/` e l'outbox) sono funzioni finite
senza porta; **due sono candidate al ritiro** (`job-summary`, `manual-lookup`);
una è un cantiere dichiarato (N6 dei listini); il resto è servizio legittimo.
Corretto il docstring di `EmailLogOperatoreListView`, che prometteva un filtro
che la RLS già applica.

🔵 **Aperto — la schermata**: il registro mail dell'**operatore** (oggi lo vede
solo l'amministratore). Piano al §2 dello stesso documento; niente dal team DB
(la configurazione di lista `config.email_log` è a catalogo, id 31). Restano
client, store, view e voce di menu.

### D8 — View sotto `KeepAlive` che caricavano solo in `onMounted`

✅ **Chiuso il 2026-09-10.** Le view davvero scoperte erano **tre**
(`DefinizioneEditorView`, `DefinizioniWorkflowListView`, `RepartiProfiloView`):
le altre avevano già il rientro da `useListaConfigurabilePage` →
`useSearchTable`. Ma quella catena si spezzava un passo più in là: **otto
store** non esponevano `hasSearched`, e senza quel campo il refresh al rientro
non avveniva mai — ora lo espongono, e `useSearchTable` **avvisa in DEV** quando
manca. `OperatoriListView` e `ProcessiAutomaticiListView` caricano il dato
compagno in `onActivated` (con `force`, perché la cache di `useSetupStatus` vive
nell'istanza che KeepAlive tiene in vita). Presidio: `check-keepalive-onactivated.mjs`
(§2.7). Regola operativa: il caricamento va nel **solo** `onActivated` — *si
sostituisce, non si aggiunge* — perché sotto KeepAlive al primo montaggio
scattano entrambi.

### D9 — La suite è larga e poco profonda, e il livello profondo nessuno lo lancia

4.560 test in 33 secondi è una descrizione, non un vanto: 261 file di test su
309 usano `unittest.mock` (6.578 fra `patch(` e `MagicMock`). È il livello
giusto per validazione, dedup e not-found, non una copertura d'integrazione.

⭐ **E `smoke-baseline.sh` ha fatto il suo mestiere il 2026-09-12**: ha
segnalato come regressione `smoke-pratica-doc-sorgente-cross-emittente.py`,
scritto il 09-07 e superato dal D2 del gemello tre giorni dopo (la RLS su
`pratiche_sorgenti` rende non osservabile lo «specchio» del §6). Era lo smoke
a essere indietro, non il DB: riscritto il §6 sulla proprietà più forte (dal
perimetro estraneo la vista **non risponde**), provato per mutazione.

⭐ Il livello che attraversa la giuntura esiste e cresce da solo: **22 file** con
`richiedi_db_provvisto` (rimisurato l'11-09; erano 19 il 09-09), accesi in CI da
`ZEROERP_TEST_DB_E2E=1`, registrati in `api.md` §Test dal 09-09.

✅ **D9-b, chiuso il 2026-09-11**: `AGENTS.md` §Regole test prescrive
`SimpleTestCase` e dice perché (solo lei **impedisce** l'accesso al DB); misura
rifatta quel giorno, 506 classi che non bloccano contro 202 che bloccano.

**Aperto — D9-a**: i sedici smoke di `backend/scripts/tests/` non li lancia
niente. Sono isolati in transazione con rollback e il registro
`baseline-smoke.tsv` ha **due** righe — ma ⛔ **in CI non si possono mettere
così**: cercano i soggetti nei dati esistenti e su un DB ricostruito da zero
uscirebbero quasi tutti `SENZA_MATERIA`, cioè un cancello verde per
sottrazione. Prima serve che si fabbrichino i soggetti (o un DB di CI popolato),
e va corretto lo smoke che esce `0` su «ESITO: FALLITO».
⚠️ Resta vera la dipendenza implicita documentata in `AGENTS.md`: **nessun test
dichiara un database**, quindi i file di `tests/db/` trovano lo schema Liquibase
completo. Il primo che dichiarerà `databases = [...]` li romperà tutti.

### D10 — I registri di debito non hanno un verso

Un registro è una buona invenzione **a condizione che scenda**. Stato:

| Registro | Valore | Il suo verso |
| --- | --- | --- |
| Errori `oxlint` | **0** | ✅ cancello in CI (`npm run lint`, senza `--fix`), dal 09-09 |
| Rilievi `ruff` | **0** | ✅ cancello in pre-commit e CI, dal 09-09 |
| `DataTable` grezza in una view | **45** grezze (+3 standard) | ✅ **cricchetto dal 09-10**: `check-datatable-baseline.mjs` + registro `frontend/scripts/datatable.baseline.json` che **elenca i file**. Rosso se cresce, rosso **anche se cala** senza riscrivere il registro |
| …di cui senza commento di motivazione | **33** | ✅ seconda soglia dello stesso cricchetto (finestra: quattro righe sopra l'import) |
| File tracciati senza header di licenza | 1.169 su 5.787 (09-10) | ✅ cala davvero (erano 2.042 il 08-26); l'hook guarda i soli file aggiunti, per scelta |
| `baseline-smoke.tsv` | 2 su 16 | ⛔ nessun verso: vive o muore con D9-a |
| `skip_area_check = True` | 73 view (09-12) | ✅ **presidio dal 09-12** (D15): chi **scrive** con lo skip dichiara un `<metodo>_permission` o sta in un registro motivato; le 15 **mute** sono un registro a cricchetto. ⚠️ Resta una lettura, non un conteggio, la legittimità delle sole **letture** cross-dominio |

**Aperto — D10-bis**: la baseline degli smoke dipende da D9-a; degli
`skip_area_check` resta da leggere la sola parte che il presidio non copre, le
letture cross-dominio (le scritture e i muti sono in D15).

### D11 — Quattro app scheletro

✅ **Deciso il 2026-09-11 (Tid)**: `acquisti` e `magazzino` sono il **prossimo
cantiere**, scritto in `PROJECT_CONTEXT.md` con la conseguenza operativa — ogni
decisione presa su `vendite` è presa anche per `acquisti`, e un'asimmetria si
chiude subito. `storico` resta **senza decisione**; `contabilita` resta fuori
perimetro (§4). Il gemello DB (§3 D8) è allineato.

### D12 — La superficie dei portali esiste a database e non ha porte

🟡 **Cantiere dichiarato**, non difetto nascosto. `PortaleAPIView` e
`ShopAPIView` hanno **1** e **0** sottoclassi; `/api/v1/portale/` e
`/api/v1/shop/` hanno tre rotte ciascuno, tutte di attivazione o registrazione.
A database ci sono **13 policy RLS** per le vesti non-OPERATORE (8
`CLIENTE_PORTALE`, 3 `SHOP_CUSTOMER`, 2 `FORNITORE_PORTALE`) che **nessun
endpoint esercita**: il giorno dello Stage C vanno considerate non collaudate.

### D13 — Un building block esisteva, il punto di chiamata non l'ha cercato

✅ **Chiuso il 2026-09-09**: `chiusura_scadenze_handler.py` faceva `dict(riga[0])`
su un `jsonb` che psycopg consegna come `str` — `CHIUSURA_SCADENZE` in `ERRORE`
per quattro notti, con `coerce_jsonb_dict` che esisteva dal 2026-06-11. Ora usa
il BB; i test fissano la **forma** del valore (`str`, `dict`, JSON malformato),
provati per mutazione; il giro delle 22:05 dello stesso giorno è passato con
`tentativi = 0`. ⭐ Il test esistente era verde mentre il job falliva: *un mock
sbaglia quando la forma che finge non è quella vera.*

✅ **D13-ter**: le otto righe storiche archiviate da Tid (09-09, 21:25 UTC):
`vw_coda_lavori_da_guardare` a zero, quindi qualunque riga ora significa
«stanotte è fallito qualcosa».

✅ **D13-bis, chiuso su entrambi i lati l'11-09**: catalogo `dbops.presidi`
applicato dal team DB (`20260910-35..37`), il backend ha ritirato la riga di
debito (`_IN_ATTESA_DI_CATALOGO` a zero, e il test di ritiro è diventato rosso in
CI nominandola — il meccanismo che fa il suo mestiere), i due timer girano
(`digest-presidi-giornaliero` 07:00, `settimanale` lunedì 07:30). Brief:
[brief-db-un-destinatario-per-i-presidi.md](../work-done/brief-db-un-destinatario-per-i-presidi.md).
⚠️ **Aperto, da portare al team DB**: la prima notizia del digest è stata
rumore — `sync_auth_user_active`, processo **ritirato** il 09-07, con 31
fallimenti storici in finestra (registrato nel brief §9.5). *Un presidio che
comincia col rumore insegna a non guardarlo.*

### D14 — «Inviata» detto di una mail mai partita

✅ **Chiuso il 2026-09-11, su entrambi i lati.** Trovato **provando** la
connessione SMTP, non leggendo: su un host con `DJANGO_DEBUG=False` e l'account
`SISTEMA` sul placeholder del seed, una mail non partita finiva in
`config.email_log` con `stato = 'SENT'`. Ora `EmailDispatchService` ha tre
canali (`SMTP` · `CONSOLE` · `NON_CONFIGURATO`, che scrive `FAILED` col motivo),
`test_connection` non risponde più OK a un account che non può spedire, il
`CHECK` ammette il quinto valore **`SIMULATA`** (dice l'esito, non il canale),
`inviato_at` resta NULL, nessun backfill. Brief:
[brief-db-stato-email-console-non-e-inviata.md](../work-done/brief-db-stato-email-console-non-e-inviata.md).

### D15 — `skip_area_check` è muto su quindici view (2026-09-12)

> Trovato leggendo l'unica riga «senza verso» di D10 — gli `skip_area_check` —
> invece di contarla. È un difetto del **modello dei permessi**, e non dà
> nessun errore.

`ZeroERPPermission.has_permission` consulta `skip_area_check` **solo** nel
ramo `area_schema_db is None`, cioè solo se la view non dichiara
`area_funzionale`. Una view che dichiara **entrambi** dice due cose opposte, e
vince l'area in silenzio. Sono **15 view su 73**:

| Famiglia | Cosa dichiara | Cosa succede |
| --- | --- | --- |
| `pagamenti` (4: saldo, rate, sistemazioni, export) | un commento di otto righe motiva lo skip: *«senza questo servirebbe la LETTURA su pagamenti»* | **serve la LETTURA su `pagamenti`**: un operatore di `vendite` senza quell'area prende 403 nel drawer fattura. In dev non si vede perché nessun operatore è stretto |
| outbox email (10) | `area_funzionale = "config"` + skip, senza commento | gated da `config`. **Per fortuna**: sei di queste scrivono senza `post_permission`, e con lo skip attivo qualunque operatore autenticato potrebbe preparare e **spedire** dall'account aziendale, con allegati, verso qualsiasi indirizzo — nessuna schermata le usa (D7) |
| `RuoliConfigResolverView` (1) | `"anagrafiche"` + skip | gated da `anagrafiche` |

I test esistenti coprivano «senza area + skip» e «senza area senza skip», mai
il caso contraddittorio.

✅ **Presidio dal 2026-09-12**: `apps/core/tests/test_skip_area_check_registro.py`,
quattro test sulle view **instradate nell'URLconf**, lette con `getattr` come
le legge la catena e filtrate su chi usa `ZeroERPPermission`; provati per
mutazione (quattro mutazioni, quattro rossi col nome). ⚠️ La prima stesura
leggeva il corpo delle classi con `ast` ed era **cieca** su un'area o un
`post` ereditati e sulle view fabbricate da una factory — riscritta la sera
stessa, e la mutazione «skip su una figlia che eredita tutto dal padre» ora
fa rosso. Tre registri a cricchetto: le 15 **mute** (debito), le 12 che
scrivono senza permesso **su sé stesse** (esenzione motivata, verificata una
per una), le 6 email **in attesa di decisione** — e il quarto test pretende che
queste ultime restino coperte dall'area finché non hanno un permesso, così
«chiudere» il debito togliendo l'area fa rosso invece di aprire un relay.

✅ **Deciso e applicato lo stesso giorno (Tid, 2026-09-12), per famiglia:**

| Famiglia | Decisione | Cosa è cambiato |
| --- | --- | --- |
| `pagamenti` (4) | **vale lo skip** | tolta `area_funzionale`: un operatore senza nessun livello su `pagamenti` vede saldo, rate e sistemazioni della fattura che ha già davanti — il commento è finalmente vero |
| outbox email (10) | **vale l'area `config`** | tolto lo skip: comportamento identico, e il codice adesso lo dice (nota in testa a `email_views.py`). Aprirla oltre `config` vuole prima un'azione di processo a catalogo e la schermata di D7 |
| `RuoliConfigResolverView` (1) | **vale lo skip** | tolta `area_funzionale`: è la configurazione del `SoggettoResolver` (componente **core**, lo usano i drawer di tutti i domini), stessa famiglia dei lookup soggetti |

Provato dal **percorso reale** in `test_permissions_decisione_skip_area.py`:
le quattro view vere di `pagamenti` passano con livello `BLOCCATO` e la catena
non risolve nemmeno l'area; l'outbox vuole `LETTURA` per leggere e `TUTTO` per
spedire. Mutazione: rimessa l'area su `ApiFatturaSaldo`, due rossi col nome.
Suite completa: 4.652 verdi. Entrambi i registri di debito sono a **zero**
e restano nel file: una view che dichiara entrambi è rossa il giorno stesso.

---

## 4. Cosa NON è un difetto

* ⛔ **`contabilita` vuoto su tutti e tre gli strati.** Fuori perimetro per
  decisione: se servirà sarà un aggancio a una contabilità esterna.
* ⛔ **Le 11 view che ereditano `APIView` nudo.** Tutte e sole quelle
  pre-autenticazione (reset password, attivazione portale/shop, check email,
  stato AI).
* ⛔ **Le `DataTable` grezze, come numero.** Il difetto è quante non dicono
  **perché** (D10); la matrice slot/override è un debito già dichiarato nel
  piano PrimeVue 5.
* ⚠️ **I 64 `.vue` che non usano `useI18n`.** Componenti di presentazione senza
  testo proprio.
* ⚠️ **La suite Django veloce.** Conseguenza corretta della scelta «unit test
  mockati»; il difetto sarebbe crederla una copertura d'integrazione (D9).
* ⚠️ **`SECRET_KEY` segnalato da `check --deploy`.** Valore di sviluppo letto
  dall'ambiente: misura di macchina.
* ⚠️ **Il chunk da 822 kB segnalato da `vite build`.** Soglia predefinita su
  un gestionale con code-splitting già attivo; non è una misura finché nessuno
  dichiara un budget.

---

## 5. Scorecard — pesata, non mediata (stato al 2026-09-11)

Il peso è **la conseguenza di un difetto in quell'area**, non la sua estensione.

| Area | Peso | Voto | Cosa regge il voto |
| --- | --- | --- | --- |
| **Catena di verifica — frontend** | 🔴 alto | **7/10** | Cancello in CI dal 09-09 (§2.1). Non sale perché la rete è tre file su ~680 (D1-d-bis) |
| **Analisi statica — backend** | 🔴 alto | **6,5/10** | `ruff` a registro zero dal 09-09 (§2.2). Manca il type checker (D2-b) |
| **Catena di verifica — backend** | 🔴 alto | **8/10** | Cancello duro, 4.560 test verdi, sette guardrail, `plpgsql_check`. Manca la profondità (D9) e il ramo `--deploy` (D3-b) |
| **Contratto API pubblicato** | 🟠 medio | **7/10** | `securitySchemes` e `security:` su 815 operazioni (D3-a). Restano 66 `W002`, 54 collisioni, `--deploy` fuori CI |
| **Contratto d'errore — lato backend** | 🟠 medio | **9/10** | 763 codici vivi, zero senza ripiego, zero orfani (§2.3) |
| **Contratto d'errore — arrivo a video** | 🟠 medio | **8/10** | `fields`, `targets`, `hint` a video (D4). Non è 10: chi chiama `notify.error` a mano resta fuori |
| **Perimetro e permessi (applicativo)** | 🟠 medio | **7,5/10** | Catena unica, fail-closed, reset GUC incondizionato. D5 vivo finché la riga a catalogo non c'è. ✅ 12-09: lo skip muto (D15) deciso e chiuso su tutte e 15 le view, presidiato dagli attributi **e** dal percorso reale |
| **Correttezza dei contratti di lista** | 🟠 medio | **8/10** | Lookup con `troncato`, presidiato sul DB vero (D6). Nessun cancello sui `count: len()` senza `LIMIT` |
| **Simmetria del dominio** | 🟠 medio | **4/10** | `acquisti`/`magazzino` modellati a DB e vuoti su BE e FE. La decisione dell'11-09 dà un verso al debito, non scrive il codice: il voto si muove col comportamento |
| **Building block — frontend** | 🟡 basso | **8,5/10** | Un solo punto HTTP, `bersagli`, contratto KeepAlive presidiato (D8). Restano le `DataTable` senza motivo |
| **Multilingua** | 🟡 basso | **9/10** | Parità perfetta e guard in CI. Il catalogo a monte è monolingue (§2.6) |
| **Gestione del debito** | 🟡 basso | **8/10** | Tre registri con cancello o cricchetto (D10). Senza verso: `skip_area_check` e baseline smoke |
| **Documentazione di contesto** | 🟡 basso | **9/10** | Sette righe su sette chiuse (§1) |

### Il giudizio, al 2026-09-12

⭐ **Il backend è costruito con lo stesso metodo del database**: contratto
d'errore chiuso a chiave, catena dei permessi in una sede sola, reset GUC
fail-closed, building block estratti alla seconda occorrenza, 99% di `# Scopo:`.
Le due lacune strutturali del 09-09 — il frontend senza nessun cancello, il
backend senza nessuna analisi statica — erano economiche e sono chiuse.

⚠️ **La frase sulla «production-readiness» non cambia**: un cancello di build
prova che il codice si compila, non che faccia la cosa giusta. Resta aperto ciò
che è **cantiere** e non configurazione — i test di componente del frontend
(D1-d-bis), la profondità della suite backend e gli smoke in CI (D9-a), il type
checker (D2-b), `check --deploy` in CI (D3-b), la CSP (D3-c) — più ciò che
aspetta un'altra squadra o una decisione (D5, D7-schermata, D10-bis, il
rumore del digest). E il perimetro dei dati — D2 e D3 del gemello — è roba di là.

### Lezioni di metodo, in quattro righe

* *La lettura della struttura dice cosa manca; solo l'esecuzione dice cosa è
  rotto.* D13, il seguito di D6 e D14 li ha trovati l'uso, non la lettura.
  ⚠️ E un registro «senza verso» non si conta: si **legge** — D15 stava nella
  riga degli `skip_area_check` da tre giorni, dietro un numero.
* *Un contratto dichiarato va seguito fino all'ultimo anello* (D4 con `hint`,
  D8 con `hasSearched`, D13 col BB non cercato): un campo che nessuno legge non
  ha comportamenti sbagliati, ne ha di invisibili.
* *Un presidio che cerca una stringa nel sorgente si accende sulla spiegazione
  del difetto che deve trovare*: si legge il sorgente **senza commenti**.
* *Un lavoro che aspetta una decisione costa zero e resta fermo lo stesso finché
  nessuno fa la domanda*: il tier 🥉 di §8 è caduto in un giorno senza una riga
  di codice.

---

## 6. Checklist

### 🔴 Il frontend

* [x] **D1-a** — ✅ 2026-09-09: `ci-frontend.yaml`, workflow suo.
* [x] **D1-b** — ✅ 2026-09-09: 7 errori `oxlint` sanati, `--fix` fuori da `lint:*`.
* [x] **D1-c** — ✅ 2026-09-09: guard raccolti in `npm run guards`.
* [x] **D1-d (metà)** — ✅ 2026-09-09: `vitest`, primo file provato per mutazione.
* [x] **D1-e** — ✅ 2026-09-09: `check_license.py` in modalità range per la CI.
* [ ] **D1-d-bis** — il primo test di **componente** su `ListaConfigurabile`
      (`@vue/test-utils` + `jsdom`, da aggiungere quel giorno).
* [~] **D1-f** — ✅ 2026-09-13: le due vulnerabilità FE sanate nel lock
      (`npm audit` a zero) e `weasyprint` a 70.0 nel backend. Aperta la
      decisione se `npm audit --audit-level=high` entra nel job — ora
      nascerebbe a zero.
* [x] **INFRA-2** — ✅ 2026-09-13: `libharfbuzz-subset0` nel `Dockerfile` (una
      riga, con il perché) e installato da Tid sulla macchina di sviluppo.
      Verificato: gli avvisi di WeasyPrint nel log dello smoke render-stampa
      da **3 a 0**, PDF identico check per check. ⚠️ Su una macchina di
      sviluppo nuova va rifatto a mano: la riga è nel `requirements.in`.

### 🔴 Il backend

* [x] **D2-a** — ✅ 2026-09-09 (`F,E9`) e 2026-09-10 (allargamento): `ruff.toml`.
* [ ] **D2-b** — decidere **se** il progetto vuole un type checker; se no,
      togliere da `AGENTS.md` la riga sull'`assert` «per aiutare il type checker».

### 🟠 Il contratto verso chi consuma

* [x] **D3-a** — ✅ 2026-09-09: `openapi_extensions.py`.
* [ ] **D3-b** — `manage.py check --deploy` in CI: prima `mail.E001` nell'ambiente
      di CI, poi il registro dei 66 `W002` e delle 54 collisioni con un verso.
* [ ] **D3-c** — `SECURE_HSTS_SECONDS` / `SECURE_SSL_REDIRECT` (con chi gestisce
      nginx) e **decidere** sulla CSP.
* [x] **D4** — ✅ 2026-09-09: `hint` a video, filtro sui codici tecnici, sei
      `ui_action` dichiarate servite dal default.

### 🟠 La sostanza

* [~] **D5** — 🔵 decisione presa e brief scritto il 2026-09-11, **attende il
      DB**. Poi il presidio: test su DB provvisto che confronta le aree delle
      view con il catalogo.
* [x] **D6** — ✅ 2026-09-10: sonda `+1`, `troncato`, helper separati, test sul DB vero.
* [x] **D7 (la decisione)** — ✅ 2026-09-11: piano §1, tredici rotte, due candidate al ritiro.
* [~] **D7 (la schermata)** — 🔵 cantiere aperto il 2026-09-11: piano §2.
* [x] **D8** — ✅ 2026-09-10: tre view, otto store, guard `check-keepalive-onactivated.mjs`.
* [x] **D8-bis** — ✅ 2026-09-10: dati compagni in `onActivated`, con `force`.
* [ ] **D9-a** — gli smoke in CI: prima insegnargli a fabbricarsi i soggetti, e
      correggere lo smoke che esce `0` su «ESITO: FALLITO».
* [x] **D9-b** — ✅ 2026-09-11: `AGENTS.md` prescrive `SimpleTestCase` e dice perché.

### 🟡 Ordine e verità dei documenti

* [x] **D10 (in parte)** — ✅ 2026-09-10: `oxlint` e `ruff` a zero con cancello,
      `DataTable` con cricchetto.
* [ ] **D10-bis** — gli `skip_area_check` (da leggere uno per uno) e la baseline
      degli smoke (con D9-a).
* [x] **D11** — ✅ 2026-09-11: `acquisti`/`magazzino` prossimo cantiere, in `PROJECT_CONTEXT.md`.
* [x] **§1-a/b/c/d** — ✅ 2026-09-09 (stack tolto, app complete, `ui_action` e
      §Test) e 2026-09-11 (§1-d con D9-b). ⚠️ Resta aperto l'ingresso di
      `ai_assistant` nei due cataloghi BB: quando i tool diventano building block
      riusabili, non prima.
* [x] **D13** — ✅ 2026-09-09: `coerce_jsonb_dict`, test sulla forma, giro delle 22:05 passato.
* [x] **D13-ter** — ✅ 2026-09-09 (Tid): otto righe archiviate, vista a zero.
* [x] **D13-bis** — ✅ 2026-09-11 su entrambi i lati: catalogo `dbops.presidi`, digest attivo.
* [ ] **D13-quater** — il rumore del primo digest (`sync_auth_user_active`,
      processo ritirato in finestra): da portare al team DB (brief §9.5).
* [x] **D13-quinquies** — ✅ 2026-09-14, dalla nota DB del 14-09: il digest
      chiamava «FALLITA» la **propria** corsa in corso — `last_ok` era la riga
      più recente, cioè quella aperta (`ok` NULL). Ora `last_ok` è l'ultima
      corsa **conclusa** in entrambe le sedi (`job_liveness`,
      `list_job_summary`), `None` è reso «in corso», il messaggio del perimetro
      nomina le due cause (riga di catalogo **o** vista che risponde diverso
      per ruolo), cinque puntatori al brief spostato in `work-done/` sanati.
      Test: la corsa aperta **costruita** sul DB vero con `fn_job_run_start`,
      più la resa; tre mutazioni, tre rossi.
* [x] **INFRA-1** — ✅ 2026-09-09/11: la chiave Tailscale di `dbdev` scaduta
      aveva fermato il DB di sviluppo (e gunicorn in `SYN-SENT`, senza avvisi);
      `KeyExpiry: None` su tutti i nodi di sviluppo, verificato l'11-09.
      ⚠️ Restano scaduti `db01` e `GiacomoZ`, non di sviluppo: da rimuovere o
      riautorizzare per decisione. Il difetto di fondo — nessuno guarda se
      l'applicazione di sviluppo è viva — è chiuso dal digest dei presidi.
* [x] **D14** — ✅ 2026-09-11: tre canali di invio, `SIMULATA` a catalogo.
* [x] **D15 (il presidio)** — ✅ 2026-09-12: `test_skip_area_check_registro.py`,
      tre registri a cricchetto, provato per mutazione.
* [x] **D15 (la decisione)** — ✅ 2026-09-12: `pagamenti` vale lo skip (tolta
      l'area), email vale l'area (tolto lo skip); provato dal percorso reale.
* [x] **D15-bis** — ✅ 2026-09-12: `RuoliConfigResolverView` vale lo skip,
      come i lookup soggetti di cui è la configurazione.

---

## 7. Cosa non ho potuto misurare, e perché lo scrivo

**Una misura mancata, taciuta, diventa una misura implicita.**

| Cosa | Perché no |
| --- | --- |
| Il censimento **completo** degli endpoint senza consumatore | Uno strumento testuale non lo sa fare, per una buona proprietà del codice: le famiglie cross-dominio (`/passaggi/`, `/note/`, `/indirizzi/`, `/documenti/`, `/situazione-merce/`, `/componenti/`) sono chiamate con il **dominio come parametro**. Le tredici di D7 sono il residuo verificato uno per uno: un **limite inferiore** |
| Quanto della suite sia davvero *coperto* e non solo *nominato* | Non esiste `coverage` nel progetto. Il numero di test è un limite superiore alla copertura, non una misura |
| Se le `DataTable` senza motivazione siano eccezioni legittime | Richiede di leggere i componenti e decidere caso per caso: è il lavoro di D10, non una misura |

---

## 8. Cosa resta, per ritorno

> La classifica del 2026-09-09 è stata eseguita: il tier 🥇 (cancello FE, guard
> in CI, `ruff`, `OpenApiAuthenticationExtension`, `oxlint` a zero) e il tier 🥈
> (`hint` a video, `onActivated`, i due helper del `count`) il 09-09 e il 09-10;
> il tier 🥉 è caduto l'11-09 **senza una riga di codice applicativo**, solo con
> decisioni scritte (D5, D7, D11, D9-b, INFRA-1, D13-bis). Fuori classifica sono
> arrivati e sono stati chiusi D13 e D14, trovati dall'uso.

### Le voci aperte, in ordine di ritorno

| # | Cosa | Perché sta qui |
| --- | --- | --- |
| 1 | **D5** — la riga `ai_assistant` a catalogo | Zero sforzo lato backend, ma passa dal **team DB**; va fatta **prima** di accendere `AI_ENABLED` |
| 2 | **D13-quater** — il rumore del digest | Un presidio che comincia col rumore insegna a non guardarlo; una riga al team DB |
| 3 | **D7 (schermata)** — il registro mail dell'operatore | Cantiere piccolo (client, store, view, menu): la lista è già a catalogo |
| 4 | **D3-c** — HSTS / SSL_REDIRECT / CSP | Dieci minuti di `settings.py` più una **decisione** sulla CSP; l'effetto lo decide il reverse proxy |
| 5 | **D2-b** — type checker | Una decisione: sì (e come) o no (e si toglie la riga da `AGENTS.md`) |
| 6 | **D1-f** — `npm audit` nel job | Registro a **zero** dal 13-09: è il momento in cui un cancello nasce senza arretrato |
| 7 | **D10-bis** — le letture cross-dominio con lo skip | Lettura, non conteggio |

### ⛔ Sembrano facili e non lo sono — sono cantieri veri

* **Smoke in CI (D9-a).** Tutti e sedici cercano i soggetti nei dati esistenti:
  su un DB di CI ricostruito da zero il cancello nascerebbe verde per
  sottrazione. Prima devono fabbricarsi i soggetti.
* **`manage.py check --deploy` in CI (D3-b).** Non è configurazione: è aprire un
  registro da 66 `W002` più 54 collisioni e dargli un verso.
* **I test di componente del frontend (D1-d-bis).** Il pacchetto è la parte
  facile; la parte che non si compra è decidere **cosa** un test di
  `ListaConfigurabile` deve asserire.
* **`acquisti` / `magazzino` (D11).** La decisione è presa; il comportamento
  applicativo è il prossimo cantiere, e il voto di simmetria (§5) si muove con
  quello.

---

*Valutazione 2026-09-09 — perimetro backend + frontend; sfoltita il 2026-09-12
allo stato corrente. Le misure sono letture di struttura sul repo al commit
`c1f9e571e` (`dev/backend-tid`), sullo schema OpenAPI generato da quel commit,
sui due workflow di CI e sull'esito di `manage.py check --deploy`; i numeri
riletti dopo portano la loro data. Lo strato DB è valutato separatamente in
[migliorie-generali-da-test-valutazione.md](migliorie-generali-da-test-valutazione.md).*
