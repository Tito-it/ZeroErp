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
>
> ✅ **Riordinato il 2026-09-20** — come nel gemello lato DB. Le voci **chiuse**
> sono uscite da §3 e sono tutte in fondo, in **§9 «Attività svolte»**: quelle
> chiuse per intero (D4, D6, D8, D11, D13, D14, D15) e le parti chiuse di quelle
> che hanno ancora un lavoro vivo (D1, D2, D3, D7, D9, D10). Per questi ultimi
> numeri la voce compare **due volte** — in §3 il lavoro che resta, in §9 quello
> fatto — e la tabella in testa a §3 dice riga per riga dove sta cosa.
>
> ✅ **Riallineato il 2026-09-26** sul repo: passate in §9 le voci chiuse dopo
> il riordino — D1-d-bis (23-09), D5 (25-09), la schermata di D7 e D13-quater
> (26-09) — e la metà sicurezza di D3-b. Lo stesso giorno il registro
> drf-spectacular di D3-b è andato a zero (`W001` 54 → 0, `W002` 73 → 0): D3-b
> resta in §3 solo per la decisione sulla CI. In §3 restano **D1-f, D2-b, D3-b,
> D3-c, D9-a, D10-bis, D12**.
>
> ✅ **Riallineato il 2026-09-28** sulle liste: il registro delle `DataTable`
> grezze è sceso da 45 a **33** (+3 standard) e quelle senza motivazione da 33 a
> **12**, con la riclassificazione del 26-09 e il
> [brief delle liste grezze](../work-done/brief-db-liste-datatable-grezze.md)
> chiuso il 28-09 (D10, §9). Riletti con la loro data i numeri di §2 (presidi
> FE da 6 a 13, file `.spec.js` da 3 a 57) e di D9 (test sul DB vero da 22 a
> 82 file). Corretto il rimando di D2-b: la riga sull'`assert` sta in
> `PROJECT_CONTEXT.md`, non in `AGENTS.md`. Le voci aperte restano le stesse.

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
(§9 D6) è come **controesempio**, mai come motivo.

**Perimetro**: `backend/` (951 file Python, ~258.000 righe) e `frontend/` (390
`.vue` + 290 `.js`, ~117.000 righe), più i cancelli di CI e i presidi che li
riguardano. Il database compare **solo** dove è il capo opposto di un contratto
applicativo (catalogo dei codici errore, delle aree funzionali, dei messaggi).

---

## 1. Il dichiarato, riletto — ✅ chiuso il 2026-09-09

Sette righe dei quattro documenti di contesto obbligatorio erano invecchiate,
cinque su sette **verso il pessimismo** (capacità costruite e non registrate).
Tutte chiuse il 2026-09-09:

| Voce                                                                                                          | Com'è stata chiusa                                                                                                                                                                                |
| ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Stack frontend in tre sedi (`AGENTS.md`, `PROJECT_CONTEXT.md`, `frontend-standards.md`)                       | **Tolto**, non aggiornato: fonte unica `frontend/package.json`, i documenti rimandano. Sanato anche il residuo fuori tabella (`frontend-standards.md` §Tab-View, riscritto su *quale API* si usa) |
| `PROJECT_CONTEXT.md` elencava 10 app su 17                                                                    | Elenco completo; `ai_assistant` entra in `api.md` §Endpoint attivi **con il difetto D5 scritto accanto**                                                                                          |
| `api.md`: `ui_action` «non letto», §Test «due livelli»                                                        | `ui_action` con il conto per valore; §Test a **tre** livelli, con quali girano in CI                                                                                                              |
| `AGENTS.md`: `unittest.TestCase` e `SimpleTestCase` come alternative                                          | Riscritta l'11-09 con D9-b                                                                                                                                                                        |
| `api.md`: `hint` «il frontend non lo legge»                                                                   | Chiusa **rendendo vero il codice** (D4), non riscrivendo la frase                                                                                                                                 |
| `api.md`: «la testata ha la RLS, il figlio no» in **cinque** voci dell'inventario (segnalato da Tid il 12-09) | Stantie dal D2 del gemello (`20260909-27` ÷ `20260910-33`; una da **luglio**). Corrette il 2026-09-13: il fatto sta ora in **una** sede (§Enforcement RLS) e le cinque voci ci rimandano          |

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
workflow. Al 2026-09-12 i file `.spec.js` erano **tre** (`useApiHandler`,
`useNotify`, `ramoBannerLotto`): il valore è il contratto dell'envelope che
fissano, non la superficie coperta. ⭐ Dal **2026-09-23** provano anche i
**componenti** (D1-d-bis chiusa): il DOM si accende per file
(`// @vitest-environment jsdom`), non globalmente, così i test puri — che
restano la maggioranza — non pagano l'ambiente di chi monta. Al **2026-09-28**
i file `.spec.js` in git sono **57**, e otto accendono il DOM.

### 2.2 Analisi statica del backend — `ruff`, dal 2026-09-09

`ruff.toml` alla radice, hook pre-commit `ruff-check` che gira anche in CI.
Selezione `F`, `E9`, `T20`, `C4`, `A`, `PIE`, `G`, `LOG`; ogni gruppo acceso a
**registro zero** dopo aver misurato e sanato. ⭐ Le regole **non** accese (`E`,
`B`, `B904`) e il formattatore **spento** sono decisioni scritte con il perché
dentro `ruff.toml`: quella è la sede, non questo documento. Manca il **type
checker** (D2-b).

### 2.3 Il contratto del codice errore, lato backend, è chiuso a chiave

|                                                       |               |
| ----------------------------------------------------- | ------------- |
| Codici a catalogo (`error_policies_generated.py`)     | 852           |
| di cui ritirati (`CODICI_RITIRATI`)                   | 89            |
| **Codici vivi**                                       | **763**       |
| Codici vivi **senza** frase di ripiego                | **0**         |
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
`DrawerTabLista` (rilette il **2026-09-28**: **71** file montano
`<ListaConfigurabile>` e **21** `<DrawerTabLista>`). `bersagli.js` trasforma i `targets` di un errore in un
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

### 2.7 I presidi scritti apposta per il frontend, in CI — 13 al 2026-09-28

Raccolti in `npm run guards` (`run-s guard:*`): chi ne aggiunge uno lo trova in
CI senza toccare il workflow. Erano sei al 09-10; lo **scopo** di ognuno sta in
testa al suo file in `frontend/scripts/`, e la tabella dice solo cosa tiene.

| Presidio                                      | Cosa tiene                                                                                                                        |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `check-liste-configurabili.mjs`               | contratto `@row-click`                                                                                                            |
| `check-pinia-user-scoped-reset.mjs`           | reset degli store al logout                                                                                                       |
| `check-drawer-width.mjs`                      | chiavi `DRAWER_WIDTH`                                                                                                             |
| `check-primeicons-codepoints.mjs`             | codepoint cablati + baseline anti-drift                                                                                           |
| `check-keepalive-onactivated.mjs` (09-10, D8) | una view sotto `<KeepAlive>` ha un `onActivated`, suo o di un composable — criterio derivato dal router e risolto transitivamente |
| `check-datatable-baseline.mjs` (09-10, D10)   | il registro delle `DataTable` grezze **può solo calare**                                                                          |
| `check-dialog-chrome.mjs` (09-18)             | il chrome delle dialog modali in una sede sola (`DIALOG_CHROME`, `AppDialog`, `useConfirmAction`)                                 |
| `check-filtri-lista.mjs` (09-22)              | `<FiltriLista>` è la sede dei filtri; registro `filtri-lista.baseline.json` a cricchetto, a **zero** su tutte e tre le voci dal 09-23 |
| `check-capability-contratto.mjs` (09-23)      | ogni campo `capabilities.*` letto dal frontend è emesso davvero da una `fn_available_actions_*`                                   |
| `check-api-componenti.mjs` (09-26)            | un componente non parla HTTP: l'URL vive in un modulo `api/` o dietro uno store                                                   |
| `check-confini-domini.mjs` (09-26)            | `core/` non importa un dominio; ciò che un dominio aggiunge passa dai registri                                                     |
| `check-lista-stato-esposto.mjs` (09-26)       | uno store su `useListaEmptyStateFetch` ne espone lo stato **intero**                                                              |
| `check-media-soglie.mjs` (09-26)              | una soglia `@media` è una di `BREAKPOINTS`, in forma canonica                                                                     |

### 2.8 La convenzione `# Scopo:` è reale

3.809 commenti `# Scopo:` su 3.815 `def` nei sorgenti non-test: il 99%.

---

## 3. I difetti **aperti**, in ordine di conseguenza — stato al 2026-09-12

> ✅ **Le voci chiuse non stanno qui**: sono in **§9 «Attività svolte»**, con la
> data e il rimando. La tabella dice riga per riga **che cosa resta in §3** e
> **che cosa è passato in §9** — e quando una voce ha due facce il suo numero
> compare in tutti e due i posti: `D1`, `D2`, `D3`, `D9`, `D10` (`D7` fino al 26-09).
> Le voci aperte, in ordine di ritorno, sono elencate anche in §8.

|     | Difetto                                                                | Stato                                                                                           |
| --- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| D1  | Il frontend non ha nessun cancello                                     | ✅ 09-09 e D1-d-bis 23-09 — **in §9** · resta la **decisione di D1-f**                           |
| D2  | Backend senza analisi statica                                          | ✅ 09-09/10 — **in §9** · resta **D2-b** (type checker)                                          |
| D3  | Lo schema OpenAPI si dichiara anonimo; `check --deploy` fuori dalla CI | ✅ D3-a e la metà sicurezza di D3-b — **in §9** · restano **D3-b** (registro a zero dal 26-09; resta la decisione su `check --deploy` completo in CI), **D3-c** |
| D4  | `hint` trasportato e mai reso a video                                  | ✅ 09-09 — **in §9**                                                                             |
| D5  | `area_funzionale = "ai_assistant"` non a catalogo                      | ✅ 09-25 — **in §9**                                                                             |
| D6  | Il `count` che è un'eco                                                | ✅ 09-10 — **in §9**                                                                             |
| D7  | Endpoint senza consumatore                                             | ✅ decisione 09-11 e schermata 09-26 — **in §9**                                                 |
| D8  | View sotto `KeepAlive` che caricano solo in `onMounted`                | ✅ 09-10 — **in §9**                                                                             |
| D9  | Suite larga e poco profonda; smoke non lanciati                        | ✅ D9-b 09-11 — **in §9** · resta **D9-a**                                                       |
| D10 | I registri di debito non hanno un verso                                | ✅ la parte con un cricchetto — **in §9** · resta **D10-bis** (la tabella qui sotto è lo stato)  |
| D11 | Quattro app scheletro                                                  | ✅ deciso 09-11 — **in §9**                                                                      |
| D12 | Portali costruiti a DB, senza porte                                    | 🟡 **cantiere dichiarato**                                                                       |
| D13 | Job notturno rotto da quattro notti                                    | ✅ 09-09 · D13-bis 09-11 · D13-quater 09-26 — **in §9**                                          |
| D14 | «Inviata» detto di una mail mai partita                                | ✅ 09-11 — **in §9**                                                                             |
| D15 | `skip_area_check` è **muto** su 15 view; sei scrivono senza permesso   | ✅ 09-12, tutte e 15 — **in §9**                                                                 |

### D1 — Il frontend non aveva nessun cancello — chiusa (§9), resta D1-f

**Aperto — D1-f**: la **decisione** se `npm audit --audit-level=high` entra nel
job `ci-frontend`. Il difetto non erano le due vulnerabilità di build (sanate il
13-09, §9), è che nessuno lancia `npm audit`: il registro è a zero dal 13-09,
cioè l'unico momento in cui un cancello nasce senza arretrato. ⭐ Il gemello
backend c'è dal 2026-09-26: `pip-audit` in `ci-validate.yaml`, acceso a zero —
oggi i due lati sono asimmetrici. Sede della decisione:
[sicurezza-e-qualita-statica.md](../sicurezza-e-qualita-statica.md) §Aperto.

### D2 — 258.000 righe di Python senza analisi statica — chiusa il 09-10 (§9), resta D2-b

**Aperto — D2-b**: decidere **se** il progetto vuole un type checker. Se sì,
`python.analysis.typeCheckingMode` nel repo o `mypy --follow-imports=skip` sui
soli `apps/*/services/`; se no, togliere da `PROJECT_CONTEXT.md` §«Error
handling» la riga `assert value is not None  # sempre dopo require, per il type
checker`, che oggi chiede un lavoro a beneficio di nessuno. (Fino al 28-09 qui
c'era scritto `AGENTS.md`, dove la riga non c'è.)
⚠️ È la metà che vedrebbe i difetti di giuntura che una suite mockata (D9) non
può vedere.

### D3 — Lo schema OpenAPI e il ramo `--deploy` — D3-a chiuso il 09-09 (§9), restano D3-b e D3-c

**D3-b, la metà drf-spectacular — registro a zero il 2026-09-26; resta la
decisione sulla CI** (sotto). La metà sicurezza è chiusa lo stesso giorno (§9).
drf-spectacular aggancia i propri controlli al ramo `--deploy`,
e il passo di CI gira `--tag security`, quindi non ne vede nessuno.
Rimisurato il **2026-09-26** con l'ambiente del job CI (`check --deploy`
completo, 130 rilievi):

| Rilievo                    | 09-09 | 09-26 (inizio) | 09-26 (fine) | Cosa                                                                                                        |
| -------------------------- | ----- | -------------- | ------------ | ----------------------------------------------------------------------------------------------------------- |
| `drf_spectacular.W002`     | 66    | 73             | **0**        | view per cui lo schema non trova il serializer (violano la regola `@extend_schema` di `AGENTS.md`)         |
| `drf_spectacular.W001`     | 54    | 54             | **0**        | collisioni di `operationId` (lista e dettaglio sullo stesso `…_retrieve`, risolte con `…_retrieve_2`)      |
| `mail.E001`                | 1     | 1              | 1            | backend di posta di sviluppo: in CI va impostato quello giusto, non silenziato                             |
| `security.W004` / `W008`   | —     | 1 + 1          | 1 + 1        | accettati dal cricchetto: sono D3-c                                                                         |
| **Totale `check --deploy`** | —    | 130            | **3**        | nessun rilievo drf-spectacular rimasto                                                                      |

⚠️ Il **128** che il commento del passo CI riportava la mattina del 26-09 non
era il conto dei `W002`: era la somma dei rilievi drf-spectacular (73 + 54) più
uno. Il commento è stato corretto lo stesso giorno, e oggi dice «a ZERO». Il
registro era **cresciuto** di sette dal 09-09: senza un verso fa
quello che ci si aspetta.

✅ **Il verso c'è dal 2026-09-26**: `apps/core/tests/test_schema_openapi_registro.py`
genera lo schema in memoria (senza DB, rotte condizionali comprese) e confronta
i rilievi **per nome** con `openapi_schema.baseline.json` (alla nascita 73
view + 54 `operationId`; vuoto dalla sera del 26-09). Rosso su un nome nuovo, rosso su una voce sanata e non tolta,
rosso su un rilievo di forma sconosciuta. Provato per mutazione: `@extend_schema`
tolto da una view vera, voci tolte e aggiunte al registro, rotte condizionali
spente — cinque rossi. ⚠️ Limite dichiarato nel test: il `W002` è **per view**,
quindi una view ancora nel registro non è protetta sugli altri metodi.

✅ **W001: 54 → 3 lo stesso giorno.** 51 erano coppie lista/dettaglio
(`/x/` e `/x/{id}/`, entrambe `x_retrieve`: drf-spectacular toglie i parametri
dal nome e per una `APIView` in GET dice sempre `retrieve`). Le separa **una**
regola, l'hook `nomi_lista_dettaglio` in `apps/core/api/openapi_extensions.py`
(`x_list` / `x_retrieve`, solo fra operazioni già in collisione) — non 51
`operation_id` a mano, che per le 13 coppie fabbricate da factory (note,
documenti) non avrebbero avuto una sede. Test del contratto
`test_openapi_nomi_lista_dettaglio.py`; tre mutazioni, tre rossi.
✅ **Le 3 rimaste, a mano, stesso giorno → W001 a zero.** Non avevano la forma
lista/dettaglio: i due lookup (`/x/lookup/` contro `/x/{id}/lookup/`, il
parametro in mezzo) prendono `…_lookup_list` / `…_lookup_retrieve`; le tabelle
di configurazione `core_config_tables_list`, e i loro record un gruppo proprio,
`core_config_tables_records_{list,create,retrieve,partial_update}` — tutti i
verbi, non solo i GET in collisione, perché i verbi di un oggetto non si
separano. Il registro dei W001 è vuoto e resta nel file.
⚠️ Correzione: il `_2` di drf-spectacular segue l'ordine **alfabetico** dei
percorsi, non quello di lettura delle rotte — il rischio di scambio era più
piccolo di come era stato descritto, ma il nome restava un numero.

✅ **W002, lotto vendite — 73 → 42 lo stesso giorno.** 31 view di ordini, DDT,
resi e preventivi. Lo schema del corpo si **legge** dal contratto del service
(building block `_schema_da_contratto`, regola del 2, ok Tid): i dodici
`CREATE_KEYS_*`/`UPDATE_KEYS_*` sono diventati pubblici e una chiave senza tipo
ferma l'import — perché una chiave fuori contratto il service la **scarta in
silenzio**, e uno schema ricopiato resterebbe indietro senza nessun errore. Gli
schemi dei componenti (preview, elenco) sono stati estratti in
`_componenti_schema`, ritirando sei copie. I due cambi stato (ordini, DDT)
condividono `CAMBIA_STATO_REQUEST` (decisione di Tid): **vendite a zero W002**.
🔴→✅ **Trovato strada facendo, e chiuso lo stesso giorno (decisione di Tid)**:
lo schema a mano della creazione riga di **preventivi** pubblicava ancora
`iva_id` (ritirato il 2026-08-31, `I6`) e `quantita`, che il service ignorava.
Misurati tutti: **tutti e dieci** gli schemi a mano di preventivi, contratti e
offerte divergevano dal contratto (in meno: `codice_cig`/`cup`/`commessa`,
`valuta_id`, `richiesta_approvazione`, `componenti_overrides`, …). Ora si
leggono dal contratto anche loro; preventivi, che il contratto di creazione non
l'aveva (le chiavi si leggevano una per una), ha `CREATE_KEYS_PREVENTIVO` e
`CREATE_KEYS_RIGA` applicati in ingresso come in ordini. Presidio:
`vendite/tests/api/test_schema_da_contratto.py` (31 schemi confrontati coi
loro contratti).

✅ **W002, lotto core + amm_software — 40 → 17 lo stesso giorno.** Il building
block `schema_da_contratto` è **traslocato in core** (regola del 2, ok Tid) con
i tipi per dominio: vendite tiene il suo dizionario, email ne ha uno condiviso
(`core/api/schema_email.py`) fra bozze, template e account. Le due creazioni di
amm_software (account, template), che leggevano le chiavi una per una e
ignoravano le altre mentre la PATCH accanto le rifiutava, hanno ora il loro
contratto e rifiutano allo stesso modo (400 `E_EMAIL_ADMIN`). La tabella di
configurazione generica (`config/tables/<rel>/`) dichiara il corpo come oggetto
libero, con il perché nel codice: le colonne le descrive `/metadata/` a runtime.

✅ **W002 a ZERO, stesso giorno (2026-09-26).** Ultimi lotti: anagrafiche,
pratiche, portale (POST senza corpo), ui (contratti dei tre service di
amministrazione liste, dizionario `ui/api/_schema_ui.py`; il preset in
creazione pubblica il contratto meno `lista_id`, che viene dal percorso),
magazzino (le due azioni `registra` fabbricate, e le anagrafiche: le chiavi di
creazione/modifica, calcolate dentro le funzioni, sono diventate costanti col
nome usate dal service e dallo schema). Il registro resta nel file, vuoto.
`check --deploy` completo: da **130** rilievi a **3** — nessuno di
drf-spectacular; restano `mail.E001` (backend di posta dell'ambiente) e
`security.W004`/`W008` (D3-c).

**Resta aperto — la decisione**: a registro vuoto,
decidere se il test basta o se `check --deploy` completo entra in CI (serve
anche `mail.E001` sistemato).

**Aperto — D3-c**: `SECURE_HSTS_SECONDS` e `SECURE_SSL_REDIRECT` assenti dal
ramo non-debug di `settings.py` (l'effetto lo decide il reverse proxy: da
concordare con chi gestisce nginx); **nessuna CSP**, né in `settings.py` né in
`index.html`, con i due token JWT in `localStorage`. La postura regge perché
`v-html` è a zero e `axios` sta in un file solo — cioè perché **non c'è
superficie** — ma nessun presidio la verifica. O si aggiunge la CSP, o si scrive
perché no. Proposta pronta in
[brief-be-fe-sicurezza-header-token-mfa.md](brief-be-fe-sicurezza-header-token-mfa.md)
§1 (decisione di Tid 2026-09-26: *«facciamo dopo»*); `W004`/`W008` sono
nell'elenco a cricchetto del passo `check --deploy` e si tolgono a §1 chiusa.

### D9 — La suite è larga e poco profonda, e il livello profondo nessuno lo lancia — D9-b chiuso l'11-09 (§9), resta D9-a

4.560 test in 33 secondi è una descrizione, non un vanto: 261 file di test su
309 usano `unittest.mock` (6.578 fra `patch(` e `MagicMock`). È il livello
giusto per validazione, dedup e not-found, non una copertura d'integrazione.

⭐ Il livello che attraversa la giuntura esiste e cresce da solo: **22 file** con
`richiedi_db_provvisto` (rimisurato l'11-09; erano 19 il 09-09; **82** il
2026-09-28), accesi in CI da `ZEROERP_TEST_DB_E2E=1`, registrati in `api.md`
§Test dal 09-09.

**Aperto — D9-a**: gli smoke Python di `backend/scripts/tests/` (sedici al
09-09, **diciassette** al 28-09 con quello dell'inventario di magazzino) non li
lancia niente. Sono isolati in transazione con rollback e il registro
`baseline-smoke.tsv` ha **due** righe — ma ⛔ **in CI non si possono mettere
così**: cercano i soggetti nei dati esistenti e su un DB ricostruito da zero
uscirebbero quasi tutti `SENZA_MATERIA`, cioè un cancello verde per
sottrazione. Prima serve che si fabbrichino i soggetti (o un DB di CI popolato),
e va corretto lo smoke che esce `0` su «ESITO: FALLITO».
⚠️ Resta vera la dipendenza implicita documentata in `AGENTS.md`: **nessun test
dichiara un database**, quindi i file di `tests/db/` trovano lo schema Liquibase
completo. Il primo che dichiarerà `databases = [...]` li romperà tutti.

### D10 — I registri di debito non hanno un verso — i cricchetti ci sono (§9), resta D10-bis

Un registro è una buona invenzione **a condizione che scenda**. Stato:

| Registro                               | Valore                      | Il suo verso                                                                                                                                                                                                                                                         |
| -------------------------------------- | --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Errori `oxlint`                        | **0**                       | ✅ cancello in CI (`npm run lint`, senza `--fix`), dal 09-09                                                                                                                                                                                                          |
| Rilievi `ruff`                         | **0**                       | ✅ cancello in pre-commit e CI, dal 09-09                                                                                                                                                                                                                             |
| `DataTable` grezza in una view         | **33** grezze (+3 standard), 28-09; erano 45 il 09-10 | ✅ **cricchetto dal 09-10**: `check-datatable-baseline.mjs` + registro `frontend/scripts/datatable.baseline.json` che **elenca i file**. Rosso se cresce, rosso **anche se cala** senza riscrivere il registro. ⭐ **Cala davvero dal 26-09** (§9 D10)                  |
| …di cui senza commento di motivazione  | **12**, 28-09; erano 33      | ✅ seconda soglia dello stesso cricchetto (finestra: quattro righe sopra l'import). Dieci delle 12 sono **decisioni di Tid aperte** ([brief delle liste grezze](../work-done/brief-db-liste-datatable-grezze.md) §5); le righe di `FatturaDrawer` sono nel [brief righe documento](brief-db-liste-righe-documento.md); gli step di `PraticaFlussiTab` sono Gruppo B per il piano e manca solo il commento |
| Filtri di lista scritti a mano         | **0** su tre voci, dal 09-23 | ✅ cricchetto `check-filtri-lista.mjs` + `filtri-lista.baseline.json` (blocchi grezzi, larghezze inline, coppie di date a mano)                                                                                                                                        |
| File tracciati senza header di licenza | 1.169 su 5.787 (09-10)      | ✅ cala davvero (erano 2.042 il 08-26); l'hook guarda i soli file aggiunti, per scelta                                                                                                                                                                                |
| `baseline-smoke.tsv`                   | 2 su 16                     | ⛔ nessun verso: vive o muore con D9-a                                                                                                                                                                                                                                |
| `skip_area_check = True`               | 73 view (09-12)             | ✅ **presidio dal 09-12** (D15): chi **scrive** con lo skip dichiara un `<metodo>_permission` o sta in un registro motivato; le 15 **mute** sono un registro a cricchetto. ⚠️ Resta una lettura, non un conteggio, la legittimità delle sole **letture** cross-dominio |

**Aperto — D10-bis**: la baseline degli smoke dipende da D9-a; degli
`skip_area_check` resta da leggere la sola parte che il presidio non copre, le
letture cross-dominio (le scritture e i muti sono in D15).

⚠️ **Le `DataTable` grezze non sono in D10-bis**: il registro ha un verso e
cala, e ciò che lo tiene sopra zero sono quasi solo decisioni, non letture.
L'unica lettura rimasta è il commento che manca su `PraticaFlussiTab` (tabella
degli step). La sede di
quelle decisioni è il registro del
[piano PrimeVue 5](piano-migrazione-primevue-5.md) (§«Gruppo B»), non questo
documento. Il prossimo passo dichiarato è
[brief-db-liste-righe-documento.md](brief-db-liste-righe-documento.md): le
righe di un documento, oggi eccezione **nominata** (`RigheMasterDetailTable`),
diventano `<ListaConfigurabile>` (decisione di Tid del 27-09; al 28-09 il
lavoro non è ancora avviato e ci sono sette decisioni aperte al suo §8.9).

### D12 — La superficie dei portali esiste a database e non ha porte

🟡 **Cantiere dichiarato**, non difetto nascosto. `PortaleAPIView` e
`ShopAPIView` hanno **1** e **0** sottoclassi; `/api/v1/portale/` e
`/api/v1/shop/` hanno tre rotte ciascuno, tutte di attivazione o registrazione.
A database ci sono **13 policy RLS** per le vesti non-OPERATORE (8
`CLIENTE_PORTALE`, 3 `SHOP_CUSTOMER`, 2 `FORNITORE_PORTALE`) che **nessun
endpoint esercita**: il giorno dello Stage C vanno considerate non collaudate.

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

## 5. Scorecard — pesata, non mediata (stato al 2026-09-11, voti rivisti al 2026-09-26)

Il peso è **la conseguenza di un difetto in quell'area**, non la sua estensione.

| Area                                    | Peso    | Voto       | Cosa regge il voto                                                                                                                                                                                                     |
| --------------------------------------- | ------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Catena di verifica — frontend**       | 🔴 alto  | **7/10**   | Cancello in CI dal 09-09 (§2.1), test di componente dal 23-09 (D1-d-bis). Manca `npm audit` (D1-f)                                                                                                                      |
| **Analisi statica — backend**           | 🔴 alto  | **6,5/10** | `ruff` a registro zero dal 09-09 (§2.2). Manca il type checker (D2-b)                                                                                                                                                  |
| **Catena di verifica — backend**        | 🔴 alto  | **8/10**   | Cancello duro, 4.560 test verdi, sette guardrail, `plpgsql_check`. Manca la profondità (D9); `--deploy` a 3 rilievi, resta la decisione sulla CI (D3-b)                                                                                                |
| **Contratto API pubblicato**            | 🟠 medio | **9/10**   | `securitySchemes` e `security:` su 815 operazioni (D3-a). `W002` e collisioni a zero con cricchetto per nome, schemi dei corpi letti dal contratto del service (26-09: era 7, fermo su quei due registri). Non è 10: `check --deploy` completo non è in CI (D3-b) |
| **Contratto d'errore — lato backend**   | 🟠 medio | **9/10**   | 763 codici vivi, zero senza ripiego, zero orfani (§2.3)                                                                                                                                                                |
| **Contratto d'errore — arrivo a video** | 🟠 medio | **8/10**   | `fields`, `targets`, `hint` a video (D4). Non è 10: chi chiama `notify.error` a mano resta fuori                                                                                                                       |
| **Perimetro e permessi (applicativo)**  | 🟠 medio | **7,5/10** | Catena unica, fail-closed, reset GUC incondizionato. ✅ 25-09 D5 chiuso con presidio aree/catalogo. ✅ 12-09: lo skip muto (D15) deciso e chiuso su tutte e 15 le view, presidiato dagli attributi **e** dal percorso reale |
| **Correttezza dei contratti di lista**  | 🟠 medio | **8/10**   | Lookup con `troncato`, presidiato sul DB vero (D6). Nessun cancello sui `count: len()` senza `LIMIT`                                                                                                                   |
| **Simmetria del dominio**               | 🟠 medio | **4/10**   | `acquisti`/`magazzino` modellati a DB e vuoti su BE e FE. La decisione dell'11-09 dà un verso al debito, non scrive il codice: il voto si muove col comportamento                                                      |
| **Building block — frontend**           | 🟡 basso | **9/10**   | Un solo punto HTTP (presidiato anche nei componenti dal 26-09), `bersagli`, contratto KeepAlive presidiato (D8), 13 guard. `DataTable` grezze 45 → 33 e senza motivo 33 → 12 (28-09): le rimaste aspettano una decisione di Tid (voto rivisto il 28-09; era 8,5) |
| **Multilingua**                         | 🟡 basso | **9/10**   | Parità perfetta e guard in CI. Il catalogo a monte è monolingue (§2.6)                                                                                                                                                 |
| **Gestione del debito**                 | 🟡 basso | **8/10**   | Registri con cancello o cricchetto (D10), e quello delle `DataTable` è sceso davvero il 26-28/09. Senza verso: le letture cross-dominio con `skip_area_check` e la baseline smoke                                        |
| **Documentazione di contesto**          | 🟡 basso | **9/10**   | Sette righe su sette chiuse (§1)                                                                                                                                                                                       |

### Il giudizio, al 2026-09-12 (elenco degli aperti riallineato al 26-09)

⭐ **Il backend è costruito con lo stesso metodo del database**: contratto
d'errore chiuso a chiave, catena dei permessi in una sede sola, reset GUC
fail-closed, building block estratti alla seconda occorrenza, 99% di `# Scopo:`.
Le due lacune strutturali del 09-09 — il frontend senza nessun cancello, il
backend senza nessuna analisi statica — erano economiche e sono chiuse.

⚠️ **La frase sulla «production-readiness» non cambia**: un cancello di build
prova che il codice si compila, non che faccia la cosa giusta. Resta aperto ciò
che è **cantiere** e non configurazione — la profondità della suite backend e
gli smoke in CI (D9-a) — più ciò che aspetta una decisione (D1-f, D2-b, D3-b
cioè `check --deploy` completo in CI con registro drf-spectacular già a zero,
D3-c, D10-bis). E il perimetro dei dati — D2 e D3 del gemello — è roba di là.

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

> `[ ]` = **da fare** — sono le voci di §3. `[x]` = **fatta** — resta qui perché
> una check-list completa serve a chi la scorre, e il **dettaglio** di ognuna è
> in §9 «Attività svolte».

### 🔴 Il frontend

* [x] **D1-a** — ✅ 2026-09-09: `ci-frontend.yaml`, workflow suo.
* [x] **D1-b** — ✅ 2026-09-09: 7 errori `oxlint` sanati, `--fix` fuori da `lint:*`.
* [x] **D1-c** — ✅ 2026-09-09: guard raccolti in `npm run guards`.
* [x] **D1-d (metà)** — ✅ 2026-09-09: `vitest`, primo file provato per mutazione.
* [x] **D1-e** — ✅ 2026-09-09: `check_license.py` in modalità range per la CI.
* [x] **D1-d-bis** — ✅ 2026-09-23: `@vue/test-utils` + `jsdom` aggiunti, primi
      due componenti provati (`DrawerActionsBar` 12, `ListaConfigurabile` 8),
      impalcatura in `frontend/test/montaggio.js`.
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
      togliere da `PROJECT_CONTEXT.md` la riga sull'`assert` «per il type checker».

### 🟠 Il contratto verso chi consuma

* [x] **D3-a** — ✅ 2026-09-09: `openapi_extensions.py`.
* [ ] **D3-b** — `manage.py check --deploy` in CI: prima `mail.E001` nell'ambiente
      di CI, poi il registro dei 73 `W002` e delle 54 collisioni (26-09) con un verso.
      ✅ **Il verso dal 2026-09-26**: `test_schema_openapi_registro.py`, cricchetto
      per nome. ✅ Stesso giorno W001 da 54 a **0** (hook lista/dettaglio +
      tre nomi a mano). W002 73 → **0**: registro vuoto, `check --deploy`
      completo da 130 a 3 rilievi. Resta la decisione se `check --deploy`
      completo entra in CI (serve `mail.E001` nell'ambiente di CI).
      ⭐ **Metà sicurezza chiusa il 2026-09-26**: il passo «Django check --deploy
      (sicurezza)» di `ci-validate.yaml` gira `--tag security` con un cricchetto
      (accettati solo W004/W008, cioè D3-c). Metà drf-spectacular: registro a
      zero lo stesso giorno; resta solo la decisione sulla CI (sopra).
* [ ] **D3-c** — `SECURE_HSTS_SECONDS` / `SECURE_SSL_REDIRECT` (con chi gestisce
      nginx) e **decidere** sulla CSP.
      Proposta pronta: [brief sicurezza](brief-be-fe-sicurezza-header-token-mfa.md) §1.
* [x] **D4** — ✅ 2026-09-09: `hint` a video, filtro sui codici tecnici, sei
      `ui_action` dichiarate servite dal default.

### 🟠 La sostanza

* [x] **D5** — ✅ 2026-09-25: il DB ha messo `ai_assistant` a catalogo (riga
      14) e il backend ha dato un significato ai tre livelli (brief §5.3:
      l'ingresso chiede `view`, `LETTURA` consulta e `TUTTO` agisce, letture
      in sola lettura a DB; la topbar mostra la chat solo a chi puo' usarla).
      ✅ Anche il presidio: `core/tests/db/test_aree_dichiarate_a_catalogo.py`
      confronta le aree delle view (rotte condizionali comprese) con
      `config.aree_funzionali.schema_db`.
* [x] **D6** — ✅ 2026-09-10: sonda `+1`, `troncato`, helper separati, test sul DB vero.
* [x] **D7 (la decisione)** — ✅ 2026-09-11: piano §1, tredici rotte, due candidate al ritiro.
* [x] **D7 (la schermata)** — ✅ 2026-09-26: lista del log aperta a ogni
      operatore (Strumenti › Email, voce senza area; era il dominio «Personale»), dopo la RLS per ambito.
      L'outbox resta sotto `config` e vive nel piano (§2.3 passo 5).
* [x] **D8** — ✅ 2026-09-10: tre view, otto store, guard `check-keepalive-onactivated.mjs`.
* [x] **D8-bis** — ✅ 2026-09-10: dati compagni in `onActivated`, con `force`.
* [ ] **D9-a** — gli smoke in CI: prima insegnargli a fabbricarsi i soggetti, e
      correggere lo smoke che esce `0` su «ESITO: FALLITO».
* [x] **D9-b** — ✅ 2026-09-11: `AGENTS.md` prescrive `SimpleTestCase` e dice perché.

### 🟡 Ordine e verità dei documenti

* [x] **D10 (in parte)** — ✅ 2026-09-10: `oxlint` e `ruff` a zero con cancello,
      `DataTable` con cricchetto.
* [x] **D10 (le `DataTable`)** — ✅ 2026-09-26/28: riclassificazione dei 44 file
      e brief delle liste grezze chiuso; registro 45 → 33, senza motivazione
      33 → 12. Le rimaste aspettano decisioni di Tid (§3 D10).
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
* [x] **D13-quater** — ✅ 2026-09-26: rumore uscito da solo, nessun timer
      acceso (§9).
* [x] **D13-quinquies** — ✅ 2026-09-14, dalla nota DB del 14-09: il digest
      chiamava «FALLITA» la **propria** corsa in corso — `last_ok` era la riga
      più recente, cioè quella aperta (`ok` NULL). Ora `last_ok` è l'ultima
      corsa **conclusa** in entrambe le sedi (`job_liveness`,
      `list_job_summary`), `None` è reso «in corso», il messaggio del perimetro
      nomina le due cause (riga di catalogo **o** vista che risponde diverso
      per ruolo), cinque puntatori al brief spostato in `work-done/` sanati.
      Test: la corsa aperta **costruita** sul DB vero con `fn_job_run_start`,
      più la resa; tre mutazioni, tre rossi.
      🔴 **Il seguito, stesso giorno (sera), dal DB**: quella correzione
      lasciava la **data** sulla riga più recente e prendeva l'**esito**
      dall'ultima conclusa — «`09:47:32 (ok)`», l'ora della corsa 122445 in
      esecuzione con l'ok di quella delle 07:30. Vero per i dati di oggi; sul
      modello, con la precedente fallita, lunedì «`<adesso> (FALLITA)`» con la
      mail in mano. E il test 18 era **verde per sottrazione**: costruiva un
      `last_ok: None` che il repository non emetteva più. ✅ Chiuso: `last_ok`
      **non esiste più** in nessuna delle tre sedi (`job_liveness`,
      `list_job_summary`, `summary_per_job_type`) — al suo posto `in_corso` +
      `ultima_conclusa = {started_at, ended_at, ok}` (BB `corsa_conclusa`),
      letti da righe **intere** (`DISTINCT ON`). La riga del digest dice «in
      corso (avviata …) — ultima conclusa … (ok)»; il pannello esiti rende il
      giro in corso a parte e l'esito con la sua data (e un `IN_CORSO` non è
      più «Errore»); le date del messaggio sono tutte in `TIME_ZONE`. Test: il
      caso costruito sul DB vero in **tre** sedi, il lunedì del team DB, il
      fuso, il `null` di `ok`.
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

| Cosa                                                           | Perché no                                                                                                                                                                                                                                                                                                                           |
| -------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Il censimento **completo** degli endpoint senza consumatore    | Uno strumento testuale non lo sa fare, per una buona proprietà del codice: le famiglie cross-dominio (`/passaggi/`, `/note/`, `/indirizzi/`, `/documenti/`, `/situazione-merce/`, `/componenti/`) sono chiamate con il **dominio come parametro**. Le tredici di D7 sono il residuo verificato uno per uno: un **limite inferiore** |
| Quanto della suite sia davvero *coperto* e non solo *nominato* | Non esiste `coverage` nel progetto. Il numero di test è un limite superiore alla copertura, non una misura                                                                                                                                                                                                                          |
| ~~Se le `DataTable` senza motivazione siano eccezioni legittime~~ | ✅ **Fatto il 2026-09-26**: i 44 file riclassificati uno per uno, guardando da dove arrivano le righe e non dove sta la tabella. Dieci eccezioni vere col commento, due convertite subito, le liste vere seminate e convertite col [brief delle liste grezze](../work-done/brief-db-liste-datatable-grezze.md) (chiuso il 28-09) |

---

## 8. Cosa resta, per ritorno

> La classifica del 2026-09-09 è stata eseguita: il tier 🥇 (cancello FE, guard
> in CI, `ruff`, `OpenApiAuthenticationExtension`, `oxlint` a zero) e il tier 🥈
> (`hint` a video, `onActivated`, i due helper del `count`) il 09-09 e il 09-10;
> il tier 🥉 è caduto l'11-09 **senza una riga di codice applicativo**, solo con
> decisioni scritte (D5, D7, D11, D9-b, INFRA-1, D13-bis). Fuori classifica sono
> arrivati e sono stati chiusi D13 e D14, trovati dall'uso.

### Le voci aperte, in ordine di ritorno

| #   | Cosa                                               | Perché sta qui                                                                                      |
| --- | -------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| 1   | **D1-f** — `npm audit` nel job                     | Registro a **zero** dal 13-09, e il lato backend (`pip-audit`) c'è dal 26-09                        |
| 2   | **D3-c** — HSTS / SSL_REDIRECT / CSP               | Proposta pronta (brief sicurezza §1); l'effetto lo decide il reverse proxy                          |
| 3   | **D2-b** — type checker                            | Una decisione: sì (e come) o no (e si toglie la riga da `PROJECT_CONTEXT.md`)                       |
| 4   | **D10-bis** — le letture cross-dominio con lo skip | Lettura, non conteggio                                                                              |

### ⛔ Sembrano facili e non lo sono — sono cantieri veri

* **Smoke in CI (D9-a).** Tutti e sedici cercano i soggetti nei dati esistenti:
  su un DB di CI ricostruito da zero il cancello nascerebbe verde per
  sottrazione. Prima devono fabbricarsi i soggetti.
* **`check --deploy` completo in CI (D3-b).** Il registro drf-spectacular è a
  zero dal 26-09 e il test lo tiene a zero; resta da decidere se il passo di
  CI toglie `--tag security`, e per farlo va sistemato `mail.E001`
  nell'ambiente di CI (il backend di posta giusto, non silenziato).
* **`acquisti` / `magazzino` (D11).** Il cantiere è aperto (stato in
  `PROJECT_CONTEXT.md`): `magazzino` avanza a lotti, `acquisti` è ancora a
  zero. Il voto di simmetria (§5) si muove con quello.

---

## 9. Attività svolte — cosa è stato chiuso, e con che cosa

> Il rovescio di §3: qui sta ciò che era un difetto e non lo è più. I numeri che
> compaiono in **tutti e due** i posti (`D1`, `D2`, `D3`, `D9`, `D10`) non
> sono ripetizioni — in §3 c'è **il lavoro che resta**, qui **quello fatto**.
> Il dettaglio vive nei documenti e nei file citati: qui si dice **che cosa è
> cambiato nel sistema**, non come ci si è arrivati.

### ✅ D1 — Il frontend ha un cancello — 2026-09-09

`ci-frontend.yaml` (§2.1), i sette errori `oxlint` sanati **prima** di
accenderlo, `--fix` tolto dagli script `lint:*`, i guard in `npm run guards`,
`vitest` col primo file provato **per mutazione** (quattro mutazioni, quattro
rossi); e il guard i18n gira dove il frontend cambia, invece di svegliarsi solo
quando il commit toccava anche il backend.

✅ **D1-e**, stesso giorno: `scripts/check_license.py` era verde in ogni corsa di
CI **per il motivo sbagliato** (leggeva il solo indice staged, vuoto dopo un
checkout). Ora distingue la modalità **range** della CI (`PRE_COMMIT_FROM_REF`/
`TO_REF`) dall'indice, e il cricchetto resta sui soli file **aggiunti**.

✅ **D1-f**: le due vulnerabilità di **build** (`browserslist`,
`baseline-browser-mapping`) sanate il 13-09 dagli avvisi Dependabot **senza
override e senza dipendenze nuove** — i range già dichiarati ammettevano le
versioni corrette, bastava aggiornare i due pacchetti nel lock. E il quarto
avviso era del **backend**: `weasyprint` 69 → **70** (`<71`), con una fattura
vera stampata **identica** check per check alla 69. ⚠️ Coda dichiarata:
`libharfbuzz-subset0` manca nel `Dockerfile` e sulle macchine di sviluppo, e va
aggiunto **prima** della 71 — ✅ fatto il 13-09 (INFRA-2, checklist §6).

✅ **D1-d-bis — i primi test di componente — 2026-09-23.** `@vue/test-utils` +
`jsdom` (ok di Tid, 0 vulnerabilità); provati `DrawerActionsBar` (12 test, 19
drawer lo montano) e `ListaConfigurabile` (8 test, 63 file), entrambi **per
mutazione**. ⭐ Il «cosa deve asserire» è stato deciso così: i **contratti fra
caller e BB** — non la resa grafica, non la configurazione, non ciò che è di
PrimeVue. Impalcatura in `frontend/test/montaggio.js`, DOM acceso **per file**
(`// @vitest-environment jsdom`).

### ✅ D2 — Analisi statica del backend — 2026-09-09, allargata il 10-09

`F`+`E9` (136 rilievi sanati prima di accendere) e poi `T20`, `C4`, `A`, `PIE`,
`G`, `LOG` — §2.2 e `ruff.toml`. L'allargamento ha trovato due difetti veri:
`B017` (due `assertRaises(Exception)`, ora pretendono tipo **e** codice) e
`PIE794` (`stato_codice_interno` dichiarato due volte in `OffertaRow`). Rimosso
`_check_fn_tmp.py` (ok di Tid).

### ✅ D3-a — Lo schema OpenAPI si dichiara — 2026-09-09

`apps/core/api/openapi_extensions.py`: `OpenApiAuthenticationExtension` per
`JwtAuditAuthentication`, registrata per import in `CoreConfig.ready()`.
`components.securitySchemes` presente, `security:` su tutte le **815
operazioni**, `check --deploy` da 677 a **124** problemi, i **607 `W001` a zero**.

✅ **D3-b, la metà sicurezza — 2026-09-26.** Passo «Django check --deploy
(sicurezza)» in `ci-validate.yaml`: `--tag security`, chiave generata nel job,
e un cricchetto che accetta solo `W004`/`W008` (cioè D3-c). La metà
drf-spectacular resta in §3.

### ✅ D5 — `ai_assistant` a catalogo — 2026-09-25

L'area dichiarata da `AIQueryView` non era a catalogo: `BLOCCATO` per tutti
tranne `SUPER_ADMIN`, e nessuno poteva concedere il permesso. Decisione di Tid
(11-09): l'assistente è anche per gli operatori. Il DB ha messo la riga (14), il
backend ha dato un significato ai tre livelli (l'ingresso chiede `view`,
`LETTURA` consulta, `TUTTO` agisce; letture in sola lettura a DB; la topbar
mostra la chat solo a chi può usarla). Presidio:
`core/tests/db/test_aree_dichiarate_a_catalogo.py` confronta le aree delle view
(rotte condizionali comprese) con `config.aree_funzionali.schema_db`. Dettaglio:
[brief-db-area-funzionale-assistente-ai.md](../work-done/brief-db-area-funzionale-assistente-ai.md).

### ✅ D4 — Il terzo lato del contratto d'errore — 2026-09-09

`hint` arriva a video in **un** posto — `useApiHandler` lo espone come
`soluzione`, il toast lo rende nel `detail` — e la condizione che lo rende
mostrabile sta nel backend (`_apply_policy`, che lo toglie sui codici tecnici).
Le sei `ui_action` non ramificate sono **dichiarate servite** dal default.
Stesso giorno, il building block che **otto** punti riscrivevano a mano: otto
coercizioni `jsonb` portate su `jsonb_out` (non `coerce_jsonb_dict`, che su
`registra_tentativo_login` sarebbe stato un fail-open), con due presidi.

### ✅ D6 — Il `count` che era un'eco — 2026-09-10

Nei lookup con `LIMIT` il `count` era `len(results)`: un numero che **conferma**
il troncamento invece di rivelarlo. Rimedio: sonda **`+1`** nel repository, BB
`fetch_con_sonda`, `troncato` nell'envelope e a video; l'helper unico è
diventato **due**, perché la forma sbagliata e quella giusta erano la stessa
riga di codice. Presidio sul **DB vero**, provato con tre mutazioni. ⭐ Il
consumatore vivo era **l'assistente AI** («ho trovato 10 articoli» su 257);
`fn_lookup_unita_misura` è stata **cancellata** perché nessun endpoint la
raggiungeva. ⚠️ Residuo dichiarato: sulle collezioni **senza** `LIMIT` il
`count` è giusto, ma nessun cancello impedisce a un `LIMIT` di comparirci sopra.

### ✅ D7 — Endpoint senza porta: la decisione — 2026-09-11

[piano-be-fe-endpoint-senza-porta.md](piano-be-fe-endpoint-senza-porta.md) §1,
per tutte e tredici le rotte: due famiglie (10 rotte, `/core/email/log/` e
l'outbox) sono funzioni finite senza porta, **due sono candidate al ritiro**
(`job-summary`, `manual-lookup`), una è un cantiere dichiarato (N6 dei listini),
il resto è servizio legittimo. Corretto il docstring di
`EmailLogOperatoreListView`, che prometteva un filtro che la RLS già applica.

✅ **La schermata — 2026-09-26.** Scelta (a) di Tid (25-09): gli operatori
vedono le mail del loro perimetro. Prerequisito DB chiuso il 25-09 (la RLS
applica gli ambiti `REPARTO`/`OPERATORE`), poi la lista del log con
`skip_area_check` sulla sola lettura e la schermata in Strumenti › Email
(era il dominio «Personale»). Dettaglio:
[brief-db-email-visibilita-per-ambito.md](../work-done/brief-db-email-visibilita-per-ambito.md)
§9.6. L'outbox resta sotto `config` fino all'azione `invia_email`: è nel
[piano](piano-be-fe-endpoint-senza-porta.md) §2.3 passo 5, non qui.

### ✅ D8 — Le view sotto `KeepAlive` — 2026-09-10

Le view davvero scoperte erano **tre**; la catena però si spezzava un passo più
in là — **otto store** non esponevano `hasSearched` e il refresh al rientro non
avveniva mai (ora `useSearchTable` **avvisa in DEV** quando manca). Presidio:
`check-keepalive-onactivated.mjs` (§2.7). Regola operativa: il caricamento va nel
**solo** `onActivated` — *si sostituisce, non si aggiunge*.

### ✅ D9-b — `SimpleTestCase` è la regola, e si sa perché — 2026-09-11

`AGENTS.md` §Regole test prescrive l'unica classe che **impedisce** l'accesso al
DB; misura rifatta quel giorno: **506 classi che non bloccano** contro 202 che
bloccano. ✅ Nello stesso periodo `smoke-baseline.sh` ha fatto il suo mestiere:
ha segnalato come regressione uno smoke **rimasto indietro** rispetto al D2 del
gemello (la RLS su `pratiche_sorgenti` rende non osservabile lo «specchio»),
riscritto sulla proprietà più forte — dal perimetro estraneo la vista **non
risponde** — e provato per mutazione.

### ✅ D10 — I registri che hanno un verso

Cinque dei registri di §3 hanno un **cricchetto** dal 09-10: `oxlint` **0** e
`ruff` **0** con cancello in pre-commit e CI, le `DataTable` grezze (**45** + 3
standard, di cui **33** senza motivazione) con `check-datatable-baseline.mjs`
che **elenca i file** ed è rosso **anche se cala** senza riscrivere il registro,
gli header di licenza che calano davvero (2.042 → **1.169**), e gli
`skip_area_check` con il presidio di D15. Restano senza verso la baseline degli
smoke (vive o muore con D9-a) e la lettura cross-dominio (D10-bis).

✅ **Il registro delle `DataTable` cala davvero — 2026-09-26 → 28.** Decisione
di Tid (26-09): *«correggere le DataTable grezze»*. I 44 file sono stati
riclassificati uno per uno guardando da dove arrivano le righe: dieci eccezioni
vere hanno preso il commento, due liste con seed ed endpoint già pronti sono
state convertite lo stesso giorno (`ContrattiBillingAccountDrawer`,
`UomConversioniDrawer`), e le liste vere a cui mancava il seed sono state
seminate dal team DB e convertite su `<ListaConfigurabile>` col
[brief delle liste grezze](../work-done/brief-db-liste-datatable-grezze.md),
chiuso su DB, BE e FE il 28-09. Strada facendo: `GeoSearchTable` ritirato, il
giornale di fattura e lotto su un solo componente (`GiornaleEntitaTab`, su
`vendite.giornale`), la catena delle revisioni dell'offerta a DB, e la
validazione del catalogo liste contro la vista (`schema_dati`). Registro:
**45 → 33** grezze, senza motivazione **33 → 12**. Le rimaste sono in §3 D10.

### ✅ D11 — Quattro app scheletro: la decisione — 2026-09-11

`acquisti` e `magazzino` sono il **prossimo cantiere** — scritto in
`PROJECT_CONTEXT.md`, col gemello DB allineato — con la conseguenza operativa
che questa voce cercava: *ogni decisione presa su `vendite` è presa anche per
`acquisti`*, e un'asimmetria si chiude subito. `storico` resta **senza
decisione**; `contabilita` resta fuori perimetro (§4).

### ✅ D13 — Il building block che nessuno ha chiamato — 09-09, D13-bis l'11-09

`chiusura_scadenze_handler.py` faceva `dict(riga[0])` su un `jsonb` che psycopg
consegna come `str`: `CHIUSURA_SCADENZE` in `ERRORE` per **quattro notti**, con
`coerce_jsonb_dict` che esisteva dal giugno precedente. Ora usa il BB, e i test
fissano la **forma** del valore (provati per mutazione). ⭐ *Un test era verde
mentre il job falliva: un mock sbaglia quando la forma che finge non è quella
vera.* ✅ **D13-ter**: le otto righe storiche archiviate,
`vw_coda_lavori_da_guardare` a zero. ✅ **D13-bis**: catalogo `dbops.presidi`
applicato dal team DB, la riga di debito del backend **ritirata** (e il test di
ritiro è diventato **rosso in CI nominandola** — il meccanismo che fa il suo
mestiere), i due timer in servizio (07:00 e lunedì 07:30). ✅ **D13-quater**
(il rumore del digest su `sync_auth_user_active`, processo ritirato il 07-09):
**superata** il 2026-09-26 senza intervento — l'ultima corsa è del 05-09, la
finestra di sette giorni l'ha fatta uscire e `maintenance.vw_job_run_da_guardare`
è vuota (tabella senza RLS: lo zero è un dato). Nessuna corsa del processo dopo il 05-09.

### ✅ D14 — «Inviata» detto di una mail mai partita — 2026-09-11

Trovato **provando** la connessione SMTP, non leggendo. Ora `EmailDispatchService`
ha tre canali (`SMTP` · `CONSOLE` · `NON_CONFIGURATO`, che scrive `FAILED` col
motivo), `test_connection` non risponde più OK a un account che non può
spedire, il `CHECK` ammette il quinto valore **`SIMULATA`** (dice l'**esito**,
non il canale), `inviato_at` resta NULL e non c'è nessun backfill.

### ✅ D15 — `skip_area_check` muto su 15 view — 2026-09-12

Un difetto del **modello dei permessi** che non dà nessun errore: una view che
dichiara area **e** skip dice due cose opposte, e vinceva l'area in silenzio.
✅ Presidio il 12-09 (`test_skip_area_check_registro.py`, quattro test sulle view
**instradate nell'URLconf**, provati per mutazione — e la prima stesura, che
leggeva il corpo con `ast`, era **cieca** su un'area ereditata) e **decisione per
famiglia lo stesso giorno**:

| Famiglia                      | Decisione                | Cosa è cambiato                                                                                                                                                                                                                                                           |
| ----------------------------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pagamenti` (4)               | **vale lo skip**         | tolta `area_funzionale`: un operatore senza nessun livello su `pagamenti` vede saldo, rate e sistemazioni della fattura che ha già davanti — il commento di otto righe è finalmente vero                                                                                  |
| outbox email (10)             | **vale l'area `config`** | tolto lo skip: comportamento identico, e il codice adesso lo dice. ⚠️ Era **la parte pericolosa**: sei di quelle view scrivono senza `post_permission`, e con lo skip attivo qualunque operatore autenticato avrebbe potuto preparare e **spedire** dall'account aziendale |
| `RuoliConfigResolverView` (1) | **vale lo skip**         | tolta `area_funzionale`: è la configurazione del `SoggettoResolver`, componente **core**                                                                                                                                                                                  |

Provato dal **percorso reale** (`test_permissions_decisione_skip_area.py`): le
quattro view di `pagamenti` passano con livello `BLOCCATO`, l'outbox vuole
`LETTURA` per leggere e `TUTTO` per spedire. Suite completa **4.652 verdi**; i
due registri di debito a **zero** e restano nel file — una view che dichiara
entrambi è rossa il giorno stesso.

---

*Valutazione 2026-09-09 — perimetro backend + frontend; sfoltita il 2026-09-12
allo stato corrente. Le misure sono letture di struttura sul repo al commit
`c1f9e571e` (`dev/backend-tid`), sullo schema OpenAPI generato da quel commit,
sui due workflow di CI e sull'esito di `manage.py check --deploy`; i numeri
riletti dopo portano la loro data. **Riordinato il 2026-09-20**: §3 contiene solo
i difetti aperti, le attività svolte stanno in §9 — con lo stesso numero in
entrambe le sezioni quando una voce ha due facce. **Riallineato il 2026-09-26**
(D1-d-bis, D5, D7, D13-quater e metà di D3-b in §9) e il **2026-09-28** (il
registro delle `DataTable` in D10, i numeri di §2 e D9, il rimando di D2-b). Lo
strato DB è valutato
separatamente in
[migliorie-generali-da-test-valutazione.md](migliorie-generali-da-test-valutazione.md).*
