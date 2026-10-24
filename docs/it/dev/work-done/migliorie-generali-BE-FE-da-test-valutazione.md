# Migliorie generali BE / FE da test valutazione

## ⏭️ Chi riparte — aggiornato al 2026-10-23

**Riparte: nessuno. ✅ Archiviato il 2026-10-23** (decisione di Tid). L'unica voce
rimasta aperta, **D12** (i portali), è un cantiere con la sua sede:
[sviluppo-portale-shop.md](../work-in-progress/sviluppo-portale-shop.md).
Le lezioni, gli indicatori e la scorecard di §5 continuano in una sede viva:
[qualita-be-fe-indicatori.md](../qualita-be-fe-indicatori.md), con lo script
`scripts/indicatori-qualita-be-fe.sh`. Decisioni aperte di Tid: **nessuna** su questo documento.

--- | --- | --- | --- | --- |
| 1 | Tid | Decidere se archiviare il documento in `work-done/`: §3 tiene solo D12, e D12 vive già nel suo cantiere | qui, §3 D12 | — |
| 2 | chi riallinea | Rileggere i registri di §3 D10 e la scorecard di §5 al prossimo giro | §3 D10, §5 | — |

Decisioni aperte di Tid: **l'archiviazione** (passo 1); le nove `DataTable` senza motivazione
aspettano le decisioni del [piano PrimeVue 5](../work-in-progress/piano-migrazione-primevue-5.md) §«Gruppo B», non
questo documento. Lavoro da committare: il riallineamento del 2026-10-23.

---

> Valutazione dello strato **applicativo** — backend Django e frontend Vue —
> presa il **2026-09-09** sul commit `c1f9e571e` (`dev/backend-tid`), sullo
> **schema OpenAPI generato** (`manage.py spectacular`, 615 path / 815
> operazioni), sui due workflow di CI, sull'esito di `manage.py check --deploy`
> e su una corsa di CI misurata da GitHub Actions (`34343449743`). È il gemello
> di [migliorie-generali-da-test-valutazione.md](../work-in-progress/migliorie-generali-da-test-valutazione.md),
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
> grezze è sceso da 45 a **33** e quelle senza motivazione da 33 a **12**, con
> la riclassificazione del 26-09 e il
> [brief delle liste grezze](brief-db-liste-datatable-grezze.md)
> — e il 29-09 a **31** (+2 standard), senza motivazione **11**, col lotto C del
> [brief righe documento](brief-db-liste-righe-documento.md)
> chiuso il 28-09 (D10, §9). Riletti con la loro data i numeri di §2 (presidi
> FE da 6 a 13, file `.spec.js` da 3 a 57) e di D9 (test sul DB vero da 22 a
> 82 file). Corretto il rimando di D2-b: la riga sull'`assert` sta in
> `PROJECT_CONTEXT.md`, non in `AGENTS.md`. Le voci aperte restano le stesse.
>
> ✅ **Riallineato il 2026-10-04** sul repo: **D3-c** (chiusa il 28-09 ma
> rimasta descritta in §3) passa in §9. Il
> [brief righe documento](brief-db-liste-righe-documento.md) è
> **chiuso** (04-10) e il registro delle `DataTable` grezze scende a **30**
> (senza motivazione resta **11**). Riletti con la data i numeri di §2.1
> (`.spec.js` 93), §2.3 (codici) e D9 (96 file sul DB vero). In §3 restano
> **D1-f, D2-b, D3-b, D9-a, D10-bis, D12**, tutte invariate nel merito.
>
> ✅ **Riallineato il 2026-10-08** sul repo: le sei voci aperte sono
> **invariate nel merito**, verificate ognuna sul file che le tiene. Il
> registro delle `DataTable` grezze scende a **28** e quelle senza motivazione
> a **9** (§3 D10): `PermessiRiepilogoView` è ritirata il 06-10, e
> `OffertaEccezioniDrawer` è diventata `OffertaRigheDrawer` il 05-10. Riletti
> con la data i numeri di §2.1 (`.spec.js` 102), §2.3 (codici) e D9 (104 file
> sul DB vero). In D9-a la frase «lo smoke che esce `0`» non dice **quale**:
> letti i sorgenti, tutti e diciassette hanno un'uscita d'errore, quindi lo si
> trova solo lanciandoli.
> ✅ Lo stesso giorno **D10-bis** chiude la sua parte di lettura (§9): le 52
> letture con lo skip, un difetto vero (i restore per id fuori scope), un BB e
> un [brief DB](brief-db-istanza-nasce-col-ba.md). In §3 restano **D1-f, D2-b,
> D3-b, D9-a, D10-bis** (la sola baseline smoke), **D12**.
> ✅ Lo stesso giorno chiude **D1-f** (§9): `npm audit --audit-level=high` nel
> job `ci-frontend`, acceso a zero. E chiude **D3-b** (§9): `check --deploy`
> **completo** in CI, con `mail.E001` silenziato per progetto (Django non
> spedisce posta). In §3 restano **D2-b, D9-a, D10-bis, D12**.
> ⭐ Su **D2-b** Tid ha deciso **sì**, a cricchetto: piano in
> [piano-be-type-checker.md](piano-be-type-checker.md).
> ✅ **Riallineato il 2026-10-09**: **D2-b chiude** (§9) — `mypy` col plugin
> Django in CI, a cricchetto. In §3 restano **D9-a, D10-bis, D12**. Lo
> smaltimento del registro (lotti L2, L3+) vive nel piano, non qui.
> ✅ **Riallineato il 2026-10-14**: **D9-a chiude** (§9, decisione di Tid) col
> giro del 13-10 — il runner lancia anche i 35 smoke bash, e il **giro
> notturno** (`smoke_notturno`, solo sviluppo) porta le regressioni nel digest
> delle 7. Non è la CI che D9-a chiedeva: è una terza strada, e il perché sta
> in §9. Con lei chiude **D10-bis**: la baseline degli smoke ha un lettore ogni
> notte. In §3 resta **D12**. Corrette anche le date di D2-b scritte «10-08».
> ✅ **Riallineato il 2026-10-23** sul repo: **nessuna voce cambia stato**, D12
> resta l'unica aperta e invariata nel merito. Riletti con la data i numeri di
> §2 (`.spec.js` 140, codici vivi 1.006, base view, liste, chiavi i18n), di §3
> D10 (baseline smoke **7 → 2**; `DataTable` ferme a 28 e 9 dal 06-10) e di §4.
> **Scorecard rivista** (§5): tolti i due «voto da rivedere» e rivotate le aree
> mosse dal 14-10. Entra il fatto nuovo di un documento vicino:
> [brief-be-verifica-documentazione-api.md](brief-be-verifica-documentazione-api.md)
> ha portato la copertura della doc API sotto presidio (722/722 rotte, 0
> fantasmi) e ha aperto per il team DB tre difetti dell'idempotenza forte (§D5-D7
> di quel brief): stanno **lì**, e qui pesano solo sul voto. Aggiunto il blocco
> «⏭️ Chi riparte», che mancava.

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
i file `.spec.js` in git sono **57**, e otto accendono il DOM; al
**2026-10-04** sono **93**, e 27 accendono il DOM; al **2026-10-08** sono **102**;
al **2026-10-23** sono **140**, e 53 accendono il DOM.

### 2.2 Analisi statica del backend — `ruff`, dal 2026-09-09

`ruff.toml` alla radice, hook pre-commit `ruff-check` che gira anche in CI.
Selezione `F`, `E9`, `T20`, `C4`, `A`, `PIE`, `G`, `LOG`; ogni gruppo acceso a
**registro zero** dopo aver misurato e sanato. ⭐ Le regole **non** accese (`E`,
`B`, `B904`) e il formattatore **spento** sono decisioni scritte con il perché
dentro `ruff.toml`: quella è la sede, non questo documento. Il **type
checker** (`mypy`, a cricchetto) c'è dal 2026-10-08 (D2-b, §9).

### 2.3 Il contratto del codice errore, lato backend, è chiuso a chiave

|                                                       |               |
| ----------------------------------------------------- | ------------- |
| Codici a catalogo (`error_policies_generated.py`)     | 852           |
| di cui ritirati (`CODICI_RITIRATI`)                   | 89            |
| **Codici vivi**                                       | **763**       |
| Codici vivi **senza** frase di ripiego                | **0**         |
| Frasi di ripiego **orfane** / con `%s` non riempibile | **0** / **0** |

Riletto il **2026-10-04**: **975** a catalogo, **99** ritirati, **876** vivi (in
`apps/core/services/error_policies_generated.py`); il **2026-10-08** **991**,
**103** e **888**; il **2026-10-23** **1.126**, **120** e **1.006**. Gli zeri li
tiene il test.
Presidiato da `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego` a ogni corsa.
La classe non si deriva dallo status e viceversa; `UI_ACTION_PER_CLASSE` porta
scritto perché su `DATO_ERRATO` il default è il banner e non l'evidenziazione.

### 2.4 Le base view: una catena sola, e la si vede

448 view ereditano `DomainAPIView`, 75 `AdminAPIView`; le **11** su `APIView`
nudo sono tutte e sole quelle pre-autenticazione (§4). 109 endpoint dichiarano
`is_search_endpoint`, 68 un `post_permission`, 63 un `model_permission`, 56
`require_idempotency_key=True`. Riletto il **2026-10-23** contando le
dichiarazioni `class …(…)` fuori dai test: **505** su `DomainAPIView`, **89** su
`AdminAPIView`, **8** su `APIView` nudo (più la base `_ApiViewBase`), sempre e
solo pre-autenticazione (§4). ⭐ Il reset dei GUC di identità in
`JwtAuditMiddleware.process_request` è incondizionato e **fail-closed**: se
fallisce, la richiesta non viene servita.

### 2.5 Il frontend è un sistema di building block

83 composable, 97 componenti core, 48 moduli API, 7 store globali, 16 utility.
**Un solo** file importa `axios` (`src/core/api.js`); `v-html` a zero;
`console.log` a zero; 63 view su `<ListaConfigurabile>` più 8 su
`DrawerTabLista` (rilette il **2026-09-28**: **71** file montano
`<ListaConfigurabile>` e **21** `<DrawerTabLista>`; il **2026-10-23** **75** e
**24**; `axios` è ancora importato dal solo `src/core/api.js`, più due `.spec.js`
che lo fingono). `bersagli.js` trasforma i `targets` di un errore in un
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
Riletto il **2026-10-23**: **5.819** chiavi per lingua, zero in una sola; 375
`.vue` su 458 usano `useI18n`; il seed ha **1.120** righe `it` e **2** `en`.

### 2.7 I presidi scritti apposta per il frontend, in CI — 13 al 2026-09-28 (invariati al 2026-10-23)

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
⚠️ **Corretto il 2026-10-23**: quel conto contava i commenti nel file, compresi
quelli sulle classi. Contando per `def`, come chiede `api.md`, sono **3.978 su
4.593** (87%). Era la misura a essere sbagliata, non la convenzione a essere
peggiorata ([indicatori](../qualita-be-fe-indicatori.md) §2).

---

## 3. I difetti **aperti**, in ordine di conseguenza — stato al 2026-09-12

> ✅ **Le voci chiuse non stanno qui**: sono in **§9 «Attività svolte»**, con la
> data e il rimando. La tabella dice riga per riga **che cosa resta in §3** e
> **che cosa è passato in §9** — e quando una voce ha due facce il suo numero
> compare in tutti e due i posti (`D7` fino al 26-09, `D1` e `D3` fino all'08-10, `D2` fino al 09-10, `D9` e `D10` fino al 14-10).
> Le voci aperte, in ordine di ritorno, sono elencate anche in §8.

|     | Difetto                                                                | Stato                                                                                           |
| --- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| D1  | Il frontend non ha nessun cancello                                     | ✅ 09-09, D1-d-bis 23-09 e D1-f 08-10 — **in §9**                                                |
| D2  | Backend senza analisi statica                                          | ✅ 09-09/10 e D2-b 08-10 (`mypy` in CI, registro a zero il 09-10) — **in §9**                |
| D3  | Lo schema OpenAPI si dichiara anonimo; `check --deploy` fuori dalla CI | ✅ D3-a 09-09, D3-c 28-09, D3-b 08-10 (`check --deploy` completo in CI) — **in §9** |
| D4  | `hint` trasportato e mai reso a video                                  | ✅ 09-09 — **in §9**                                                                             |
| D5  | `area_funzionale = "ai_assistant"` non a catalogo                      | ✅ 09-25 — **in §9**                                                                             |
| D6  | Il `count` che è un'eco                                                | ✅ 09-10 — **in §9**                                                                             |
| D7  | Endpoint senza consumatore                                             | ✅ decisione 09-11 e schermata 09-26 — **in §9**                                                 |
| D8  | View sotto `KeepAlive` che caricano solo in `onMounted`                | ✅ 09-10 — **in §9**                                                                             |
| D9  | Suite larga e poco profonda; smoke non lanciati                        | ✅ D9-b 09-11, D9-a 14-10 (giro notturno degli smoke) — **in §9**                                |
| D10 | I registri di debito non hanno un verso                                | ✅ i cricchetti, D10-bis 08-10 e 14-10 — **in §9** (la tabella qui sotto resta lo stato)          |
| D11 | Quattro app scheletro                                                  | ✅ deciso 09-11 — **in §9**                                                                      |
| D12 | Portali costruiti a DB, senza porte                                    | 🟡 **cantiere dichiarato**                                                                       |
| D13 | Job notturno rotto da quattro notti                                    | ✅ 09-09 · D13-bis 09-11 · D13-quater 09-26 — **in §9**                                          |
| D14 | «Inviata» detto di una mail mai partita                                | ✅ 09-11 — **in §9**                                                                             |
| D15 | `skip_area_check` è **muto** su 15 view; sei scrivono senza permesso   | ✅ 09-12, tutte e 15 — **in §9**                                                                 |

### D10 — I registri di debito: lo stato — tutti con un verso dal 2026-10-14 (§9)

Un registro è una buona invenzione **a condizione che scenda**. La voce è
chiusa (§9); la tabella resta qui perché è lo **stato** dei registri, e si
rilegge a ogni riallineamento:

| Registro                               | Valore                      | Il suo verso                                                                                                                                                                                                                                                         |
| -------------------------------------- | --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Errori `oxlint`                        | **0**                       | ✅ cancello in CI (`npm run lint`, senza `--fix`), dal 09-09                                                                                                                                                                                                          |
| Rilievi `ruff`                         | **0**                       | ✅ cancello in pre-commit e CI, dal 09-09                                                                                                                                                                                                                             |
| `DataTable` grezza in una view         | **28** grezze (+2 standard), invariato al 23-10 (registro fermo dal 06-10); erano 30 il 04-10, 31 il 29-09, 33 il 28-09, 45 il 09-10 | ✅ **cricchetto dal 09-10**: `check-datatable-baseline.mjs` + registro `frontend/scripts/datatable.baseline.json` che **elenca i file**. Rosso se cresce, rosso **anche se cala** senza riscrivere il registro. ⭐ **Cala davvero dal 26-09** (§9 D10)                  |
| …di cui senza commento di motivazione  | **9**, 08-10 e 23-10; erano 11 il 29-09 e il 04-10, 12 il 28-09, 33 prima | ✅ seconda soglia dello stesso cricchetto (finestra: quattro righe sopra l'import). Otto delle 9 sono **decisioni di Tid aperte** ([brief delle liste grezze](brief-db-liste-datatable-grezze.md) §5); le righe di `FatturaDrawer` sono uscite il 29-09 col lotto C del [brief righe documento](brief-db-liste-righe-documento.md) (con `ArticoloBomDrawer` fra le grezze), e `ContrattoRigheDrawer` il 04-10 alla chiusura dello stesso brief. Il 05-10 `OffertaEccezioniDrawer` è diventata `OffertaRigheDrawer` ([brief righe esclusione](brief-db-righe-esclusione-solo-non-si-vende.md)), e il 06-10 `PermessiRiepilogoView` è stata ritirata: il riepilogo è un interruttore della lista operatori ([brief riepilogo permessi](brief-db-riepilogo-permessi-lista-operatori.md)). Gli step di `PraticaFlussiTab` sono Gruppo B per il piano e manca solo il commento |
| Filtri di lista scritti a mano         | **0** su tre voci, dal 09-23 | ✅ cricchetto `check-filtri-lista.mjs` + `filtri-lista.baseline.json` (blocchi grezzi, larghezze inline, coppie di date a mano)                                                                                                                                        |
| File tracciati senza header di licenza | 1.169 su 5.787 (09-10); **non riletto** il 23-10 | ✅ cala davvero (erano 2.042 il 08-26); l'hook guarda i soli file aggiunti, per scelta                                                                                                                                                                                |
| `baseline-smoke.tsv`                   | **2** su 51 (23-10: 17 Python + 34 bash — `smoke-nota-credito-resi.py` `SENZA_MATERIA`, `smoke-test-resi-vendita.sh` `ASSERZIONE`); erano **7** su 52 il 14-10, 2 su 16 Python il 09-09 | ✅ **letto ogni notte dal 2026-10-13** (D9-a, §9): `smoke-baseline.sh` nel giro `smoke_notturno`; un non-verde nuovo è una corsa `ok=false` nel digest delle 7. Un rientrato è segnalato (`RIENTRATO`), non rosso: il verso in discesa resta a chi legge il riepilogo |
| `skip_area_check = True`               | 73 view (09-12); 78 (08-10); **74** righe `skip_area_check = True` fuori dai test (23-10, `grep`: il metodo delle date prima non è scritto, quindi il confronto non vale) | ✅ **presidio dal 09-12** (D15): chi **scrive** con lo skip dichiara un `<metodo>_permission` o sta in un registro motivato; le 15 **mute** sono un registro a cricchetto. ✅ Le **letture** lette una per una il 2026-10-08 (D10-bis, §9) |

✅ **D10-bis chiusa**: le letture cross-dominio con lo skip il 2026-10-08, la
baseline degli smoke il 2026-10-14 con D9-a (§9).

⚠️ **Le `DataTable` grezze non sono in D10-bis**: il registro ha un verso e
cala, e ciò che lo tiene sopra zero sono quasi solo decisioni, non letture.
L'unica lettura rimasta è il commento che manca su `PraticaFlussiTab` (tabella
degli step). La sede di
quelle decisioni è il registro del
[piano PrimeVue 5](../work-in-progress/piano-migrazione-primevue-5.md) (§«Gruppo B»), non questo
documento. ✅ Il passo che era dichiarato qui —
[brief-db-liste-righe-documento.md](brief-db-liste-righe-documento.md),
le righe di un documento su `<ListaConfigurabile>` — è **chiuso il
2026-10-04**: righe di preventivo, ordine, DDT, reso, fattura, contratto e
distinta base sono liste configurabili (97-103).

### D12 — La superficie dei portali esiste a database e non ha porte

🟡 **Cantiere dichiarato**, non difetto nascosto. `PortaleAPIView` e
`ShopAPIView` hanno **1** e **0** sottoclassi; `/api/v1/portale/` e
`/api/v1/shop/` hanno tre rotte ciascuno, tutte di attivazione o registrazione.
A database ci sono **13 policy RLS** per le vesti non-OPERATORE (8
`CLIENTE_PORTALE`, 3 `SHOP_CUSTOMER`, 2 `FORNITORE_PORTALE`) che **nessun
endpoint esercita**: il giorno dello Stage C vanno considerate non collaudate.

Riletto il **2026-10-23**: invariato. `PortaleAPIView` ha ancora una sola
sottoclasse (`ProfileActivateShopView`), `ShopAPIView` nessuna; nessun commit sul
tema dal 14-10 oltre alla doc API. Il conto delle policy è del 09-09 e non è
stato riletto: è roba del gemello DB.

---

## 4. Cosa NON è un difetto

* ⛔ **`contabilita` vuoto su tutti e tre gli strati.** Fuori perimetro per
  decisione: se servirà sarà un aggancio a una contabilità esterna.
* ⛔ **BE e FE di `acquisti`/`magazzino` indietro rispetto al DB.** È la
  conseguenza di una scelta (Tid, chiarita il 2026-10-04): un anno sul solo DB
  per fissarne nomi, trigger e regole, e poi BE e FE. Senza consumatori, i
  refactor pesanti del modello — rinomine di colonne, la ripartenza in
  `migrations_v2` — costavano un changeSet; con BE e FE già scritti, molti non
  si sarebbero fatti, e il modello se li sarebbe tenuti. Il rovescio è che da
  quando BE e FE esistono non ci sono stati refactor grandi del modello. Che un
  dominio modellato aspetti il suo turno è l'ordine di costruzione, e
  l'ordine non si vota (§5).
* ⛔ **Le view che ereditano `APIView` nudo** (11 il 09-09, **8** il 2026-10-23).
  Tutte e sole quelle pre-autenticazione (reset password, attivazione della
  veste, check email dello shop, stato AI, secondo passo del login).
* ⛔ **Le `DataTable` grezze, come numero.** Il difetto è quante non dicono
  **perché** (D10); la matrice slot/override è un debito già dichiarato nel
  piano PrimeVue 5.
* ⚠️ **I `.vue` che non usano `useI18n`** (64 il 09-09, **83** il 2026-10-23).
  Componenti di presentazione senza testo proprio; il guard i18n tiene comunque
  lo zero di stringhe cablate.
* ⚠️ **La suite Django veloce.** Conseguenza corretta della scelta «unit test
  mockati»; il difetto sarebbe crederla una copertura d'integrazione (D9).
* ⚠️ **`SECRET_KEY` segnalato da `check --deploy`.** Valore di sviluppo letto
  dall'ambiente: misura di macchina.
* ⚠️ **Il chunk da 822 kB segnalato da `vite build`.** Soglia predefinita su
  un gestionale con code-splitting già attivo; non è una misura finché nessuno
  dichiara un budget.

---

## 5. Scorecard — pesata, non mediata (stato al 2026-09-11, voti rivisti al 2026-10-23)

Il peso è **la conseguenza di un difetto in quell'area**, non la sua estensione.
La colonna «Era» dice il voto del 2026-09-26 (o della data indicata): un voto che
si muove porta il suo perché, uno fermo dice che cosa lo tiene fermo.

| Area                                    | Peso    | Voto       | Era      | Cosa regge il voto                                                                                                                                                                                                     |
| --------------------------------------- | ------- | ---------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Catena di verifica — frontend**       | 🔴 alto  | **7,5/10** | 7        | Cancello in CI dal 09-09 (§2.1), test di componente dal 23-09 (D1-d-bis), `npm audit` dal 08-10 (D1-f). Sale per il metodo, non per il conto: i test di componente sono diventati la norma (53 file col DOM il 23-10). Non è 9: nessuna prova del percorso a video (end-to-end), e nessuna misura di copertura (§7) |
| **Analisi statica — backend**           | 🔴 alto  | **8,5/10** | 6,5      | `ruff` a registro zero dal 09-09 (§2.2); `mypy` col plugin Django in CI dall'08-10, registro **a zero** dal 09-10 e ancora a zero il 23-10 (D2-b) — e prima di accendersi ha trovato un 500 vero. Non è 10: `E`/`B` di `ruff` spenti per scelta scritta, `mypy` non in modalità `strict` |
| **Catena di verifica — backend**        | 🔴 alto  | **8,5/10** | 8        | Cancello duro, guardrail, `plpgsql_check`, `check --deploy` completo in CI (D3-b). Sale perché gli smoke hanno un lettore **ogni notte** dal 13-10 (D9-a) e il livello sul DB vero cresce (file con `richiedi_db_provvisto`: 123 il 14-10, 140 il 23-10). Resta sotto 9: la suite è in maggioranza mockata, e gli smoke non sono un cancello **prima** del merge (§8) |
| **Contratto API pubblicato**            | 🟠 medio | **9,5/10** | 9        | `securitySchemes` e `security:` su tutte le operazioni (D3-a); `W001`/`W002` a zero con cricchetto per nome (D3-b); dal 21-10 la **documentazione** delle rotte è sotto presidio (`core/tests/test_copertura_doc_api.py`: 722/722, 0 fantasmi — [brief vicino](brief-be-verifica-documentazione-api.md) §E). Il mezzo punto che manca: il contratto dell'idempotenza forte ha tre difetti aperti al team DB (quel brief, §D5-D7) |
| **Contratto d'errore — lato backend**   | 🟠 medio | **9/10**   | 9        | 1.006 codici vivi il 23-10, zero senza ripiego, zero orfani (§2.3). Fermo: un codice con la classe sbagliata (`E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE` TECNICO per un errore d'input, brief vicino §D1) e la `soluzione` del catalogo che non arriva per gli errori sollevati in Python (stesso brief, §D4) |
| **Contratto d'errore — arrivo a video** | 🟠 medio | **8/10**   | 8        | `fields`, `targets`, `hint` a video (D4). Fermo: chi chiama `notify.error` a mano resta fuori, e per i codici del backend la frase all'operatore è un ripiego del FE (`SOLUZIONI_AZIONE_UI`) |
| **Perimetro e permessi (applicativo)**  | 🟠 medio | **8/10**   | 7,5      | Catena unica, fail-closed, reset GUC incondizionato; D5 e D15 chiusi e presidiati. Sale per D10-bis (08-10): le 52 letture con lo skip lette una per una, i due restore per id fuori scope chiusi, BB `richiedi_se_stesso_o_amministratore`. Non sale oltre: il controllo nel corpo resta invisibile al presidio (D10-bis), e la chiave d'idempotenza non è legata a utente ed endpoint (brief vicino §D7, dichiarato minore) |
| **Correttezza dei contratti di lista**  | 🟠 medio | **8/10**   | 8        | Lookup con `troncato`, presidiato sul DB vero (D6). Fermo: nessun cancello sui `count: len()` senza `LIMIT` |
| **Simmetria del dominio**               | 🟠 medio | **non votata** (04-10) | 4 fino al 04-10 | Che `acquisti` e `magazzino` abbiano BE e FE indietro rispetto al DB è l'**ordine di costruzione** scelto, non un difetto (§4). Ciò che si presidia è la regola: *ogni decisione presa su `vendite` vale anche per `acquisti`* |
| **Building block — frontend**           | 🟡 basso | **9/10**   | 9        | Un solo punto HTTP (presidiato anche nei componenti dal 26-09), `bersagli`, contratto KeepAlive presidiato (D8), 13 guard. `DataTable` grezze **28** e senza motivo **9**, fermi dal 06-10: aspettano decisioni di Tid nel piano PrimeVue 5 |
| **Multilingua**                         | 🟡 basso | **9/10**   | 9        | Parità perfetta e guard in CI. Fermo: il catalogo a monte è monolingue (2 righe `en` su 1.122 il 23-10, §2.6) |
| **Gestione del debito**                 | 🟡 basso | **8,5/10** | 8        | Dal 14-10 nessun registro è senza verso, e il registro degli smoke è sceso davvero (7 → 2). Non 9: il registro delle `DataTable` non si muove da diciassette giorni, e una decisione che nessuno prende costa zero e resta ferma lo stesso (§5, lezioni) |
| **Documentazione di contesto**          | 🟡 basso | **9/10**   | 9        | Sette righe su sette chiuse (§1); dal 21-10 la doc API ha un presidio di copertura. Fermo: questo stesso documento non aveva il blocco «⏭️ Chi riparte» che `AGENTS.md` chiede (aggiunto il 23-10) |

### Il giudizio, al 2026-09-12 (riletto il 2026-10-23)

⭐ **Il backend è costruito con lo stesso metodo del database**: contratto
d'errore chiuso a chiave, catena dei permessi in una sede sola, reset GUC
fail-closed, building block estratti alla seconda occorrenza, 99% di `# Scopo:`.
Le due lacune strutturali del 09-09 — il frontend senza nessun cancello, il
backend senza nessuna analisi statica — erano economiche e sono chiuse.

⚠️ **La frase sulla «production-readiness» non cambia**: un cancello di build
prova che il codice si compila, non che faccia la cosa giusta. Resta aperto ciò
che è **cantiere** e non configurazione: la profondità della suite backend
(gli smoke girano ogni notte dal 13-10, ma sul DB di sviluppo e non in CI: D9-a,
§9) e i portali (D12). E il perimetro dei dati — D2 e D3 del gemello — è roba di là.

✅ **Riletto il 2026-10-23**: il giudizio regge. Le aree 🔴 sono salite tutte e tre
(7,5 · 8,5 · 8,5) perché ciò che era configurazione è stato fatto; ciò che le
tiene sotto il 9 è ancora il cantiere — prove a video, suite mockata, smoke fuori
dal cancello. ⚠️ Il fatto nuovo non viene da questo documento: i difetti
dell'idempotenza forte li ha trovati la verifica della doc API, **leggendo il
codice contro la documentazione**. È la stessa lezione della prima riga qui
sotto, vista dall'altro lato: la lettura della struttura trova ciò che manca,
ma solo se si legge il contratto che conta.

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
* [x] **D1-f** — ✅ 2026-09-13: le due vulnerabilità FE sanate nel lock
      (`npm audit` a zero) e `weasyprint` a 70.0 nel backend. ✅ 2026-10-08:
      `npm audit --audit-level=high` nel job `ci-frontend`, acceso a zero.
* [x] **INFRA-2** — ✅ 2026-09-13: `libharfbuzz-subset0` nel `Dockerfile` (una
      riga, con il perché) e installato da Tid sulla macchina di sviluppo.
      Verificato: gli avvisi di WeasyPrint nel log dello smoke render-stampa
      da **3 a 0**, PDF identico check per check. ⚠️ Su una macchina di
      sviluppo nuova va rifatto a mano: la riga è nel `requirements.in`.

### 🔴 Il backend

* [x] **D2-a** — ✅ 2026-09-09 (`F,E9`) e 2026-09-10 (allargamento): `ruff.toml`.
* [x] **D2-b** — ✅ 2026-10-08: **sì** (Tid), `mypy` col plugin Django in CI, a
      cricchetto ([piano](piano-be-type-checker.md), L1). La riga sull'`assert`
      di `PROJECT_CONTEXT.md` resta, e ora serve a qualcuno.

### 🟠 Il contratto verso chi consuma

* [x] **D3-a** — ✅ 2026-09-09: `openapi_extensions.py`.
* [x] **D3-b** — ✅ 2026-09-26: metà sicurezza in CI (`--tag security`) e
      registro drf-spectacular a **zero** con cricchetto per nome
      (`test_schema_openapi_registro.py`). ✅ 2026-10-08: `check --deploy`
      **completo** in CI, `mail.E001` silenziato per progetto (§9).
* [x] **D3-c** — `SECURE_HSTS_SECONDS` / `SECURE_SSL_REDIRECT` (con chi gestisce
      nginx) e **decidere** sulla CSP.
      Proposta pronta: [brief sicurezza](brief-be-fe-sicurezza-header-token-mfa.md) §1.
      🟡 2026-09-28: HSTS e redirect fatti, W004/W008 tolti dal cricchetto;
      ✅ 2026-09-28: CSP applicata in Nginx dopo il collaudo a video. Chiusa.
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
* [x] **D9-a** — ✅ 2026-10-14 (Tid): non in CI ma **ogni notte** sul DB di
      sviluppo — runner su tutti e 52 gli smoke, giro `smoke_notturno`, esito
      nel digest delle 7 (§9).
* [x] **D9-b** — ✅ 2026-09-11: `AGENTS.md` prescrive `SimpleTestCase` e dice perché.

### 🟡 Ordine e verità dei documenti

* [x] **D10 (in parte)** — ✅ 2026-09-10: `oxlint` e `ruff` a zero con cancello,
      `DataTable` con cricchetto.
* [x] **D10 (le `DataTable`)** — ✅ 2026-09-26/28: riclassificazione dei 44 file
      e brief delle liste grezze chiuso; registro 45 → 33, senza motivazione
      33 → 12; il 29-09 → **31** e **11** col lotto C delle righe documento,
      il 04-10 → **30** alla chiusura di quel brief; l'08-10 → **28** e **9**.
      Le rimaste aspettano decisioni di Tid (§3 D10).
* [x] **D10-bis** — ✅ 2026-10-08: le 52 letture con lo skip lette una per una,
      i due restore per id fuori scope chiusi, BB «se stesso o amministratore»
      (§9). ✅ 2026-10-14: la baseline degli smoke, con D9-a.
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
| ~~Se le `DataTable` senza motivazione siano eccezioni legittime~~ | ✅ **Fatto il 2026-09-26**: i 44 file riclassificati uno per uno, guardando da dove arrivano le righe e non dove sta la tabella. Dieci eccezioni vere col commento, due convertite subito, le liste vere seminate e convertite col [brief delle liste grezze](brief-db-liste-datatable-grezze.md) (chiuso il 28-09) |

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
| —   | *nessuna*: le voci aperte che restano sono cantieri (qui sotto) o il cantiere dei portali (D12) | D2-b chiusa l'08-10, D9-a e D10-bis il 14-10 (§9)                                                                           |

### ⛔ Sembrano facili e non lo sono — sono cantieri veri

* **Smoke in CI.** D9-a è chiusa col giro notturno (§9), non con la CI: gli
  smoke cercano ancora i soggetti nei dati esistenti, e su un DB di CI
  ricostruito da zero il cancello nascerebbe verde per sottrazione. Portarli
  in CI resta possibile solo dopo che si fabbricano i soggetti.
* **`acquisti` / `magazzino` (D11).** Il cantiere è aperto (stato in
  `PROJECT_CONTEXT.md`): `magazzino` avanza a lotti, `acquisti` ha il solo
  modello. È un cantiere, non un difetto (§4).

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
✅ **Il cancello, 2026-10-08** (decisione di Tid): `npm audit --audit-level=high`
nel job `ci-frontend`, subito dopo `npm ci`, acceso a **zero** — il gemello di
`pip-audit` (26-09), che lasciava il rischio sorvegliato da un lato solo. Ferma
`high`/`critical`, dipendenze di sviluppo **comprese** (le due del 13-09 erano
di build). Sede: [sicurezza-e-qualita-statica.md](../sicurezza-e-qualita-statica.md)
§Dipendenze e immagine.

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

✅ **D2-b — il type checker — 2026-10-08** (decisione di Tid: sì, a cricchetto).
`mypy` con i plugin Django e DRF su tutto `apps/` e `zeroerp_backend/` (esclusi
test e migration), `check_untyped_defs`, librerie senza tipi elencate per nome
(`backend/mypy.ini`). Dipendenze in `backend/requirements-dev.in/.txt`, fuori
dall'immagine Docker. Registro per nome `backend/mypy.baseline.json` (620
rilievi alla nascita) e cancello `scripts/check_mypy_baseline.py`, nel passo
«Type checker» di `ci-validate.yaml`: rosso su un rilievo nuovo, su una voce
sanata e non tolta, su un'uscita illeggibile — provato per mutazione.
⭐ Prima ancora di accenderlo, la misura ha trovato un **500 vero**: riallinea e
sblocca prezzo di commessa chiamavano un metodo tolto da sei mesi, con il test
mockato verde. Chiuso nello stesso giro (L0 del piano). Lo smaltimento del
registro è nel [piano](piano-be-type-checker.md): ✅ **L2 e L3 fatti il 2026-10-09**, registro
**620 → 0** (gli ultimi 2, il caso NaN dei documenti, chiusi il 2026-10-09 da
`work-done/brief-db-valore-numerico-non-finito-nei-documenti`), con altri difetti veri trovati e
corretti strada facendo (alert scadenze listini sempre in 400, numero del preventivo nella pratica
di approvazione prezzo, data vuota nel pricing, `int()` grezzi). Committato in `0ffe7b7c3` e
`ebc54fc56`. Sede:
[sicurezza-e-qualita-statica.md](../sicurezza-e-qualita-statica.md) §mypy.

### ✅ D3-a — Lo schema OpenAPI si dichiara — 2026-09-09

`apps/core/api/openapi_extensions.py`: `OpenApiAuthenticationExtension` per
`JwtAuditAuthentication`, registrata per import in `CoreConfig.ready()`.
`components.securitySchemes` presente, `security:` su tutte le **815
operazioni**, `check --deploy` da 677 a **124** problemi, i **607 `W001` a zero**.

✅ **D3-b, la metà sicurezza — 2026-09-26.** Passo «Django check --deploy
(sicurezza)» in `ci-validate.yaml`: `--tag security`, chiave generata nel job,
e un cricchetto che accetta solo `W004`/`W008` (cioè D3-c).

✅ **D3-b, la metà drf-spectacular — 2026-09-26.** Lo stesso giorno il
registro è andato a **zero**: `W001` 54 → 0 (hook `nomi_lista_dettaglio` in
`openapi_extensions.py` per le 51 coppie lista/dettaglio, tre nomi a mano),
`W002` 73 → 0 (schemi dei corpi **letti dal contratto del service**, BB
`schema_da_contratto` in core — strada facendo trovati e chiusi i dieci schemi a
mano di preventivi, contratti e offerte che divergevano dal contratto). Il
verso: `apps/core/tests/test_schema_openapi_registro.py`, cricchetto **per
nome**, provato per mutazione. `check --deploy` completo da 130 a 3 rilievi.

✅ **D3-b, il passo completo — 2026-10-08** (decisione di Tid). Dei tre
rilievi rimasti, `W005`/`W021` erano già accettati per scelta; `mail.E001` si
è rivelato **non** un difetto dell'ambiente di CI, come era scritto qui, ma
una scelta del modello: la console di `MAILERS` vale in **tutti** gli ambienti,
perché Django non spedisce posta in ZeroErp (anche il reset password passa dal
servizio email e da `config.email_account`). Dargli uno SMTP vero avrebbe
aperto un secondo canale. Quindi `SILENCED_SYSTEM_CHECKS = ["mail.E001"]` in
`settings.py`, col perché accanto, e il passo «Django check --deploy
(completo)» di `ci-validate.yaml` gira **senza** `--tag security`: il grep del
cricchetto guarda ora **qualunque** famiglia di rilievi, così un controllo di
produzione nuovo portato da una libreria fa rosso da sé. Provato in locale con
l'ambiente del job: verde; rosso togliendo il silenziamento (uscita ≠ 0) e
rosso con un avviso nuovo (`security.W019`). Sede:
[sicurezza-e-qualita-statica.md](../sicurezza-e-qualita-statica.md) §check --deploy.

✅ **D3-c — HSTS, redirect e CSP — 2026-09-28.** Il difetto: `SECURE_HSTS_SECONDS`
e `SECURE_SSL_REDIRECT` assenti dal ramo non-debug di `settings.py`, nessuna
CSP, e una postura che reggeva solo perché **non c'era superficie** (`v-html` a
zero, `axios` in un file solo) senza che nessun presidio lo verificasse. Ora
HSTS e redirect sono in `settings.py` e `W004`/`W008` sono **tolti** dal
cricchetto del passo `check --deploy` (restano accettati `W005`/`W021`,
sottodomini e preload spenti per scelta); la CSP è applicata in Nginx su
`backend-dev` dopo il collaudo a video in `Report-Only`. Lo stesso brief ha
portato il refresh JWT nel cookie `HttpOnly` (28-09) e il secondo fattore
(02/03-10). Dettaglio:
[brief-be-fe-sicurezza-header-token-mfa.md](brief-be-fe-sicurezza-header-token-mfa.md)
§1.

### ✅ D5 — `ai_assistant` a catalogo — 2026-09-25

L'area dichiarata da `AIQueryView` non era a catalogo: `BLOCCATO` per tutti
tranne `SUPER_ADMIN`, e nessuno poteva concedere il permesso. Decisione di Tid
(11-09): l'assistente è anche per gli operatori. Il DB ha messo la riga (14), il
backend ha dato un significato ai tre livelli (l'ingresso chiede `view`,
`LETTURA` consulta, `TUTTO` agisce; letture in sola lettura a DB; la topbar
mostra la chat solo a chi può usarla). Presidio:
`core/tests/db/test_aree_dichiarate_a_catalogo.py` confronta le aree delle view
(rotte condizionali comprese) con `config.aree_funzionali.schema_db`. Dettaglio:
[brief-db-area-funzionale-assistente-ai.md](brief-db-area-funzionale-assistente-ai.md).

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

[piano-be-fe-endpoint-senza-porta.md](../work-in-progress/piano-be-fe-endpoint-senza-porta.md) §1,
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
[brief-db-email-visibilita-per-ambito.md](brief-db-email-visibilita-per-ambito.md)
§9.6. L'outbox resta sotto `config` fino all'azione `invia_email`: è nel
[piano](../work-in-progress/piano-be-fe-endpoint-senza-porta.md) §2.3 passo 5, non qui.

### ✅ D8 — Le view sotto `KeepAlive` — 2026-09-10

Le view davvero scoperte erano **tre**; la catena però si spezzava un passo più
in là — **otto store** non esponevano `hasSearched` e il refresh al rientro non
avveniva mai (ora `useSearchTable` **avvisa in DEV** quando manca). Presidio:
`check-keepalive-onactivated.mjs` (§2.7). Regola operativa: il caricamento va nel
**solo** `onActivated` — *si sostituisce, non si aggiunge*.

### ✅ D9-a — Gli smoke girano ogni notte — 2026-10-14

Il difetto: gli smoke di `backend/scripts/tests/` non li lanciava niente. E i
bash nemmeno il runner, che prendeva i soli `.py`: al primo giro completo, il
2026-10-12, erano rossi più della metà, da settimane.

✅ **Il giro del 2026-10-13** (`b3e35f899`, `10ee0c897`, `f6f446402`):

* `scripts/smoke-baseline.sh` lancia **tutte e due le famiglie** — 17 `.py`
  in transazione con rollback, 35 bash via HTTP che **scrivono** documenti di
  prova sull'emittente attivo dell'utente `smoke`. Un login solo per il giro,
  attesa e un nuovo tentativo sul `429`, chi non si può lanciare è stampato fra
  gli esclusi, uno smoke con dei `SKIP` è `PARZIALE`. Il codice di uscita non
  conta: si classifica dall'**output** (è così che si prende anche lo smoke che
  esce `0` su «ESITO: FALLITO»). Escluso `smoke-c9`, l'unico senza rollback.
* I bash che creano un documento prendono il cliente da tre helper
  (`_smoke_cliente.sh`, `_smoke_documenti.sh`, `_smoke_pratiche.sh`) invece di
  copiare lo stesso blocco con un id cablato.
* **Il giro notturno**: management command `smoke_notturno`, timer
  `zeroerp-smoke-notturno` (02:30, `sveglie.json`), processo `smoke_notturno`
  (riga 47 di `dbops.processi`). Con regressioni la corsa chiude `ok=false` e
  `maintenance.vw_job_run_da_guardare` la porta nel digest delle 7.
  ⛔ **Solo sviluppo**, con tre difese: sveglia spenta di default, nessun
  «Esegui ora», e il comando rifiuta di partire senza
  `SMOKE_NOTTURNO_CONSENTITO=1`.
* Ritirato `smoke-test-pratica-preventivi-conferma.sh` (`b3cdfa34e`).

⭐ **Perché chiude anche senza CI** (chiusura decisa da Tid il 2026-10-14). D9-a prevedeva due
strade per la CI: soggetti fabbricati, o un DB di CI popolato. Il giro notturno
è una terza strada: gli smoke girano **dove i dati ci sono**, e il difetto —
*nessuno li lancia* — non esiste più. Resta vero ciò che la CI avrebbe dato in
più, ed è dichiarato in §8: un cancello **prima** del merge, e un giro che non
dipende dallo stato del DB di sviluppo. La baseline è **7 su 52** (§3 D10):
registro di debito, non lista di eccezioni.

⚠️ Resta vera la dipendenza implicita documentata in `AGENTS.md`: **nessun test
dichiara un database**, quindi i file di `tests/db/` trovano lo schema Liquibase
completo. Il primo che dichiarerà `databases = [...]` li romperà tutti.
⚠️ E resta vero il fatto da cui D9 partiva: la suite Django è quasi tutta
mockata (il 09-09: 261 file di test su 309 con `unittest.mock`). Il livello che
attraversa la giuntura cresce — i file con `richiedi_db_provvisto` erano 19 il
09-09 e sono **123** il 2026-10-14, accesi in CI da `ZEROERP_TEST_DB_E2E=1` —
ma quella è la profondità, non un difetto con una chiusura.

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
`skip_area_check` con il presidio di D15. Restavano senza verso la lettura
cross-dominio (D10-bis, fatta il 2026-10-08) e la baseline degli smoke (letta
ogni notte dal 2026-10-14, con D9-a): §9.

✅ **Il registro delle `DataTable` cala davvero — 2026-09-26 → 28.** Decisione
di Tid (26-09): *«correggere le DataTable grezze»*. I 44 file sono stati
riclassificati uno per uno guardando da dove arrivano le righe: dieci eccezioni
vere hanno preso il commento, due liste con seed ed endpoint già pronti sono
state convertite lo stesso giorno (`ContrattiBillingAccountDrawer`,
`UomConversioniDrawer`), e le liste vere a cui mancava il seed sono state
seminate dal team DB e convertite su `<ListaConfigurabile>` col
[brief delle liste grezze](brief-db-liste-datatable-grezze.md),
chiuso su DB, BE e FE il 28-09. Strada facendo: `GeoSearchTable` ritirato, il
giornale di fattura e lotto su un solo componente (`GiornaleEntitaTab`, su
`vendite.giornale`), la catena delle revisioni dell'offerta a DB, e la
validazione del catalogo liste contro la vista (`schema_dati`). Registro:
**45 → 33** grezze, senza motivazione **33 → 12**; il 29-09, col lotto C del
[brief righe documento](brief-db-liste-righe-documento.md), **31** e **11**; il 04-10, alla chiusura del brief, **30** e **11**.
Le rimaste sono in §3 D10.

### ✅ D10-bis — Le letture con lo skip, lette una per una — 2026-10-08

Le view con `skip_area_check` **attivo** che servono una lettura sono **52**, prese
dal percorso reale (l'URLconf, con la stessa scansione del presidio di D15). Lette
una per una, contro la domanda *«su che cosa altro può leggere chi chiama?»*:

| Gruppo | Esito |
| --- | --- |
| Dati propri (`me/`, sessioni, emittente attivo, secondo fattore, parametri risolti) | ✅ il perimetro è l'identità |
| Cataloghi e metadati (`lookup/codici` con whitelist a DB, tipi, comuni, stradario, conti contabili, config liste, misure pagina) | ✅ nessun dato di dominio |
| Filtro per utente a DB (contatori e config dashboard, log email con RLS per ambito) | ✅ |
| Controllo nel corpo (permessi effettivi e audit, `ui/admin/liste/`) | ✅ — ⚠️ invisibile al presidio, che legge gli attributi |
| Lookup cross-dominio per testo (BA, istanze, soggetti-ruoli, utility per emittente, ricerca universale) | ✅ scope emittente |
| Decisioni già prese (`pagamenti/fatture/<id>/…` del 12-09 con la RLS su `vendite.fatture`; `RuoliConfigResolverView`) | ✅ |
| **Restore per id** di istanze e soggetti-ruoli | 🔴 → ✅ |

🔴 **Il difetto**: i due restore per id (`IstanzaUtilityLookupByIdView`,
`SoggettiRuoliLookupByIdView`) rispondevano su **qualunque** istanza o soggetto-ruolo,
fuori dallo scope emittente che la ricerca per testo applica — e su `istanze_utilities`,
`soggetti` e `soggetti_ruoli` non c'è RLS a fare da rete. Il repository lo dichiarava
(«l'autorizzazione va gestita dall'endpoint chiamante»), e l'endpoint, con lo skip, non la
gestiva: con un id si leggevano nome, CF, indirizzo e PDP di soggetti di altri emittenti,
con un 200. Il BA per id era coperto dalla RLS.
✅ **Chiuso lo stesso giorno**: il restore applica la **stessa** clausola della ricerca
(`_SCOPE_EMITTENTE_SQL` estratta in `istanze_utility_repository`, `_RUOLO_CL_SCOPE_SQL` in
`soggetti_repository`); `emittente_ids` è obbligatorio dal repository alla view; fuori scope
è `E_ANAG_NOT_FOUND` come un id inesistente. Test sul DB vero
`anagrafiche/tests/db/test_lookup_restore_scope_db.py` (mondo costruito, «altro emittente»
fabbricato); tre mutazioni, tre rossi.
⭐ **La domanda di modello che ne è uscita**: la regola «un'istanza è dell'emittente del suo
BA» ha un buco solo se l'istanza può vivere senza BA. Decisione di Tid: *istanza e BA nascono
insieme, sempre; resta differito solo il codice, prima della prima fattura*. L'applicazione la
rispetta già, il contratto del DB no → [brief-db-istanza-nasce-col-ba.md](brief-db-istanza-nasce-col-ba.md).

✅ **BB `richiedi_se_stesso_o_amministratore`** (`core/api/permissions.py`, regola del 2,
ok Tid): il «solo i propri, oppure amministratore» di permessi effettivi e audit era scritto
due volte; ora una, e «amministratore» lo decide `IsAdminZeroERP.valuta`. 🔴→✅ Trovato
strada facendo: i test delle due view mettevano il mock sul `PermissionResolver` della view,
e la decisione passava dal DB di sviluppo con un id finto — **verdi per il motivo
sbagliato**. Ora il mock sta dove il BB decide (`RichiedenteMockatoMixin`, che nega di
default; il test dichiara `richiedente_amministratore()`), separato dal resolver della view,
che risponde sull'utente **consultato**: con un mock solo un test non distingueva «chi guarda
è admin» da «chi è guardato è admin». Due mutazioni (BB sempre-sì, BB sempre-no), entrambe
rosse. Messaggio del 403 corretto: «Solo un amministratore (SUPER_ADMIN o superuser)…».

✅ **Regola del 2 sui test DB** (ok Tid, 2026-10-08): `_Annulla` era ricopiata in 22 file di
8 app e importata come nome privato in altri tre; ora `Annulla` in `core/tests/db_e2e.py`,
copie ritirate nello stesso giro.

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
registro delle `DataTable` in D10, i numeri di §2 e D9, il rimando di D2-b) e
il **2026-10-04** (D3-c in §9, brief righe documento chiuso, numeri datati), il
**2026-10-08** e **09-10** (D1-f, D3-b, D10-bis, D2-b) e il **2026-10-14** (D9-a
e con lei D10-bis) e il **2026-10-23** (numeri datati, scorecard rivotata, blocco
«⏭️ Chi riparte»). Lo
strato DB è valutato
separatamente in
[migliorie-generali-da-test-valutazione.md](../work-in-progress/migliorie-generali-da-test-valutazione.md).*
