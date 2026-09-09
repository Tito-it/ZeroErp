# Migliorie generali BE / FE da test valutazione

> Valutazione dello strato **applicativo** — backend Django e frontend Vue — al
> **2026-09-09**. È il gemello di
> [migliorie-generali-da-test-valutazione.md](migliorie-generali-da-test-valutazione.md),
> che copre il solo strato DB e a cui questo documento rimanda per tutto ciò che
> sta dentro PostgreSQL.
>
> **Sorgenti**: il repo al commit `c1f9e571e` su `dev/backend-tid`; lo **schema
> OpenAPI generato** (`manage.py spectacular`, 615 path / 815 operazioni); i due
> file di CI; l'esito di `manage.py check --deploy`; una corsa di CI misurata da
> GitHub Actions (`34343449743`). Nessun conteggio di righe di lavoro è usato
> come argomento.

---

## 0. Come si legge

Vale il metodo del documento gemello, e per le stesse ragioni: **una media su
dodici aree è lo strumento sbagliato**, perché tratta «i nomi dei file» e «cosa
impedisce a una regressione di entrare» come due addendi dello stesso peso.

Questo documento perciò:

* separa ciò che **è stato costruito** (§2) da ciò che **non tiene** (§3);
* ordina i difetti per **conseguenza**, non per area;
* dichiara ciò che **non è un difetto** (§4);
* dà una scorecard **pesata** (§5);
* e chiude dichiarando ciò che **non ha potuto misurare** (§7) — perché un
  documento che tace su una misura mancata sembra completo e non lo è.

⚠️ Tutte le misure sono **letture di struttura** — quali file esistono, cosa
dichiara un `paths:` di un workflow, quale classe eredita una view, cosa contiene
un `package.json`, cosa dice uno schema OpenAPI — e sono **fatti datati
2026-09-09**. Dove compare un conteggio di comportamento (una volta sola, §3 D6)
è come **controesempio**: «questo caso esiste ed è gestito male».

### Perimetro

`backend/` (951 file Python, ~258.000 righe) e `frontend/` (390 `.vue` + 290
`.js`, ~117.000 righe), più i cancelli di CI e i presidi che li riguardano. Il
database compare **solo** dove è il capo opposto di un contratto applicativo (il
catalogo dei codici errore, il catalogo delle aree funzionali, il catalogo dei
messaggi). Non è valutato: lo è nel documento gemello.

---

## 1. Il dichiarato, riletto

Non c'è una valutazione precedente da rileggere. C'è però il **dichiarato**: i
quattro documenti che ogni sessione deve leggere prima di toccare il codice. Sono
il contratto con cui si lavora, e vanno riletti come si rilegge un giudizio.

| Dove                                      | Cosa diceva                                                            | Cosa risulta al 2026-09-09                                                                                                                                                                                                   | Esito                                                                       |
| ----------------------------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| `.codex/AGENTS.md` · `PROJECT_CONTEXT.md` | «Vite 7, PrimeVue 4.5, **Pinia 3**, Vue Router 5, **vue-i18n 10**»     | `package-lock.json`: **Vite 8.2.2**, PrimeVue 4.5.5, **Pinia 4.0.3**, Vue Router 5.3.1, **vue-i18n 11.4.10**. Due salti di **major** che nessun documento registrava                                                         | ✅ **chiuso**                                                                |
| `frontend-standards.md` §Stack            | «Vite **8.x**, Pinia **3.x**, vue-i18n **10.x**»                       | Terza versione della stessa riga, terza volta sbagliata in modo diverso. ⭐ Ed era il documento che aveva ragione su Vite: il difetto non era l'ignoranza, era che **lo stesso fatto stava in tre sedi che non si conoscono** | ✅ **chiuso**                                                                |
| `api.md` §Envelope                        | «`ui_action` … ⚠️ **il frontend non lo legge ancora**»                  | Falso: `useApiHandler` lo legge (`azioneUi`) e `useForzaturaConfermata` ci ramifica sopra. La frase era invecchiata verso il pessimismo                                                                                      | ✅ **chiuso**                                                                |
| `api.md` §Envelope                        | «`hint` … ⚠️ il frontend non lo legge ancora»                           | Vero la mattina del 2026-09-09 (**zero** occorrenze in `frontend/src`), **falso la sera**: il toast lo rende sotto il messaggio                                                                                              | ✅ **chiuso — rendendo falsa la frase, non correggendola** (D4)              |
| `api.md` §Test                            | «Test progressivi, **due livelli**: unit service mockati · smoke curl» | **Superato in meglio**: esiste un terzo livello, `tests/db/` con `richiedi_db_provvisto` — **19 file**, 34 punti di chiamata, acceso in CI da `ZEROERP_TEST_DB_E2E=1`                                                        | ✅ **chiuso**                                                                |
| `PROJECT_CONTEXT.md` §Struttura           | elenca 10 app Django                                                   | Le app sono **17**. Mancava fra le altre `ai_assistant`: 24 file, 18 tool registrati, 2 endpoint documentati, **assente da tutti e quattro** i documenti di contesto obbligatorio                                            | ✅ **chiuso**                                                                |
| `AGENTS.md` §Smoke                        | «**undici** script … nessuno li lancia»                                | Oggi sono **sedici**. La seconda metà della frase regge: la CI non li nomina                                                                                                                                                 | ✅ **chiuso**                                                                |

⭐ **Il verso in cui invecchiavano diceva qualcosa.** Cinque righe su sette
descrivevano il progetto **peggio** di com'è: capacità costruite e non
registrate. È il segno di un progetto che corre più veloce della propria
documentazione — un problema migliore del contrario, ma pur sempre un problema,
perché un agente che legge quei documenti a inizio sessione **riparte da una
fotografia sbiadita**.

### ✅ Com'è finita, il 2026-09-09

Sei righe su sette chiuse in giornata. ⭐ **E la parte che conta non è che sono
state corrette: è come.**

Le tre righe sullo stack **non sono state aggiornate — sono state tolte.**
Ricopiare i numeri giusti avrebbe ricreato la stessa divergenza al prossimo
`npm update`, e stavolta con tre documenti che *sembrano* appena revisionati.
Vale invece il precedente già in uso per Python (`.python-version`): **fonte
unica di verità `frontend/package.json`**, e i documenti ci rimandano. In
`frontend-standards.md` la colonna «Versione» è sparita e resta quella «Ruolo»,
che è la parte che non invecchia; nei due file `.codex/` resta un rimando e la
nota datata di *cosa* diceva prima, perché una correzione senza il suo motivo si
riapre da sola.

⚠️ **Un residuo trovato togliendo, e sanato**: `frontend-standards.md` §Tab-View
diceva «Siamo su **PrimeVue 4.5**» **fuori** dalla tabella dello stack — cioè la
stessa duplicazione, in una sede che nessuno avrebbe guardato correggendo la
tabella. ⭐ Riscritta su ciò che quella sezione fissa davvero, che è **quale API
si usa** (`Tabs` e non `TabView`): un'informazione che non cambia con la patch.

Le quattro righe di merito sono state riscritte, non ritoccate: `ui_action` ha
ora il suo terzo aggiornamento datato (uno su sette consumatori, con il conto
esplicito degli altri sei); §Test ha una tabella a **tre** livelli che dice
anche **quali girano in CI**; l'elenco delle app è completo e marca i quattro
scheletri; `ai_assistant` entra nell'inventario endpoint di `api.md` **con il
suo difetto D5 scritto accanto**, perché registrare una funzione senza dire che
il suo gate non si può aprire sarebbe stato registrare metà del fatto.

⛔ **La riga su `hint` era rimasta**, unica delle sette. Correggerla avrebbe
significato correggere il documento **sbagliato**: le è stata aggiunta la data di
riverifica e la ragione per cui pesava — la stessa mossa del D1-bis del gemello:
*«non ha senso correggere il documento: ha senso rendere vero ciò che dice»*.

✅ **E la sera del 2026-09-09 è caduta anche quella**, nel modo che era stato
dichiarato: non ritoccando la frase, ma **chiudendo il difetto** (D4). ⭐ Sette
righe su sette, e la settima è l'unica che è costata codice invece che
riscrittura — che è esattamente la differenza fra un documento invecchiato e un
documento che dice il vero su una cosa che manca.

---

## 2. Cosa è stato costruito, e va detto

### 2.1 ⭐ La catena di verifica del backend è un cancello vero

`ci-validate.yaml` gira su ogni push a `Tito-dev` e su ogni PR verso `Tito-dev` o
`main` che tocchi `backend/`, `db/`, `requirements/` o `scripts/`, e **non ha
nessun `continue-on-error`**. Dentro, in ordine: pre-commit sui file cambiati,
sette guardrail statici, il migrate Liquibase completo, il provisioning dei
ruoli, `manage.py check`, il guardrail dei riferimenti morti compilati con
`plpgsql_check`, e la suite Django.

**Misurato dalla CI** (corsa `34343449743`, 2026-09-09 11:08 UTC, su un database
ricostruito da Liquibase):

|                         |                    |
| ----------------------- | ------------------ |
| Test trovati / eseguiti | 4.565 / 4.560      |
| Esito                   | **OK** (6 saltati) |
| Durata della suite      | **33,1 secondi**   |
| Durata del job intero   | 5m20s              |

⭐ **È l'esatto opposto della situazione dello strato DB prima del 2026-09-09**:
là la suite girava e il suo esito veniva buttato via; qui il rosso ferma il
merge, e lo fa da sempre.

**E la stessa suite, misurata in locale sul database di sviluppo** la sera del
2026-09-09 (la misura che §7 aveva dovuto dichiarare mancante):

|               | CI (DB da Liquibase) | Locale (DB di sviluppo)                   |
| ------------- | -------------------- | ----------------------------------------- |
| Test eseguiti | 4.560                | **4.530**                                 |
| Durata        | 33,1 s               | **21,6 s**                                |
| Esito         | ✅ OK (6 saltati)     | 🟠 **30 errori**, 0 fallimenti, 17 saltati |

⚠️ **I 30 errori non contraddicono il verde della CI**, e la differenza dice una
cosa utile: stanno **tutti in un file solo**,
`apps/vendite/tests/services/test_dashboard_competenza_service.py`, e sono un
`IndexError: tuple index out of range` su `vendite_repository.py:2308`
(`row[32]` su una riga più corta) — cioè un **cantiere aperto** sulla dashboard
competenza, dove la riga finta del test e il `SELECT` vero si sono sfilati. Il
file ha un test che presidia esattamente questo
(`test_larghezza_riga_finta_uguale_al_select`), ed è fra i 30.

⭐ **La suite locale vede un cantiere che la CI non vede**, perché la CI gira sul
commit integrato e qui c'è lavoro in volo. Non è un difetto della CI: è la
ragione per cui le due misure vanno tenute distinte invece di sceglierne una.

⚠️ Il rovescio di quei 33 secondi è in §3 D9: una suite così veloce è una suite
quasi interamente **mockata**, e un mock non attraversa mai una giuntura.

### 2.2 ⭐ Il contratto del codice errore, lato backend, è chiuso a chiave

Il catalogo lo scrive il DB; il backend lo **riceve** e lo presidia. Verificato
sul modulo generato e sul suo compagno di ripiego:

|                                                   |         |
| ------------------------------------------------- | ------- |
| Codici a catalogo (`error_policies_generated.py`) | 852     |
| di cui ritirati (`CODICI_RITIRATI`)               | 89      |
| **Codici vivi**                                   | **763** |
| Codici vivi **senza** frase di ripiego            | **0**   |
| Frasi di ripiego **orfane** (nessun codice)       | **0**   |
| Frasi di ripiego con un `%s` non riempibile       | **0**   |

⭐ Zero su tre righe consecutive non è un caso: è
`test_ogni_codice_vivo_ha_un_messaggio_di_ripiego` che gira a ogni corsa. E il
modulo generato porta scritto in testa **perché non si tocca a mano** e da dove
si rigenera.

⭐ La classe non si deriva dallo status e viceversa: `UI_ACTION_PER_CLASSE` ha
accanto il commento che spiega **perché** su `DATO_ERRATO` il default è il banner
e non l'evidenziazione del campo — «promettere un campo da evidenziare che non
esiste è peggio del contrario». È una decisione motivata sull'asimmetria del
danno, non una preferenza.

### 2.3 ⭐ Le base view: una catena sola, e la si vede

448 view ereditano `DomainAPIView`, 75 `AdminAPIView`. Le **11** view che
ereditano `APIView` nudo sono tutte e sole quelle **pre-autenticazione** (reset
password, attivazione portale/shop, check email, stato AI): non sono eccezioni
dimenticate, sono il perimetro che una base class autenticata non può coprire.

Sopra: 109 endpoint dichiarano `is_search_endpoint = True` (throttling), 68
dichiarano un `post_permission` (azione di processo), 63 un `model_permission`
(livello oggetto), 56 `require_idempotency_key=True`.

⭐ **E il reset dei GUC è fail-closed.** `JwtAuditMiddleware.process_request`
azzera i cinque GUC di identità all'**inizio** di ogni richiesta `/api/`,
incondizionatamente, e se il reset fallisce la richiesta **non viene servita**.
Su connessioni persistenti con la RLS accesa, è la riga che separa
«defense-in-depth» da «leak fra richieste».

### 2.4 ⭐ Il frontend è un sistema di building block, non un insieme di pagine

83 composable, 97 componenti core, 48 moduli API, 7 store globali, 16 utility.
E i numeri che contano non sono questi, sono questi altri:

|                                        |                                                      |
| -------------------------------------- | ---------------------------------------------------- |
| File che importano `axios`             | **1** (`src/core/api.js`)                            |
| Occorrenze di `v-html`                 | **0**                                                |
| Occorrenze di `console.log`            | **0** (restano 8 `console.error`, 17 `console.warn`) |
| View montate su `<ListaConfigurabile>` | 63 file, più 8 su `DrawerTabLista`                   |
| `DataTable` grezza                     | **48** — era 57 il 2026-08-30, 48 il 2026-08-03      |

⭐ **Un solo punto di ingresso HTTP in tutto il frontend.** Vuol dire che
l'interceptor della lingua, il refresh del token e la traduzione dell'errore
stanno in un posto e non in 48.

⭐ **E `bersagli.js` merita una riga a sé**: la mappa tipo → destinazione che
trasforma il `targets` di un errore in un pulsante è corta *perché le chiavi di
`DOCUMENTO_DRAWER_TIPI` sono già i `codice_interno` di `config.tipi_entita`* —
non era da inventare, era da riconoscere. E degrada in modo esplicito: tipo senza
destinazione, area BLOCCATA, id non convertibile ⇒ nessun pulsante, mai uno che
porta in un vicolo cieco.

### 2.5 ⭐ Il multilingua del frontend è **fatto**, non «possibile»

|                                        |                                                 |
| -------------------------------------- | ----------------------------------------------- |
| Chiavi in `it.json` / `en.json`        | 4.697 / **4.697**                               |
| Chiavi presenti solo in una delle due  | **0**                                           |
| Valori identici fra le due lingue      | 155 (**3%**, e sono `email`, `username`, `no`…) |
| File `.vue` che usano `useI18n`        | 346 su 390                                      |
| Chiamate `t(`                          | ~4.200                                          |
| Stringhe visibili cablate nel template | **0** trovate                                   |

⭐ Presidiato da `scripts/check_i18n_keys.py` in pre-commit: chiavi rotte, parità
it/en, radici dei namespace, chiavi **emesse dal DB** non risolvibili, chiavi
definite due volte. Oggi verde, con **53 chiavi costruite dinamicamente**
dichiarate come punto cieco — dichiarate, non nascoste.

⛔ **E qui si vede una cosa che il documento sul DB non poteva vedere.** Il
frontend manda `Accept-Language` a ogni richiesta, il backend lo gira sulla GUC
`myapp.user_language`, il DB sceglie il messaggio nella lingua giusta: **la
condotta è costruita per intero**. Dall'altro capo, il seed
`config/messaggi_errore.csv` ha **846 righe `it` e 1 `en`**. ⇒ Un operatore che
mette l'interfaccia in inglese ottiene un'applicazione inglese **e messaggi
d'errore italiani**. Il documento gemello lo classifica come «una capacità, non
un fatto» (§2.3); da questa parte si vede meglio: **il consumatore esiste,
è completo, e aspetta**.

### 2.6 ⭐ Quattro presidi scritti apposta per il frontend

`frontend/scripts/`: `check-liste-configurabili.mjs` (contratto `@row-click`),
`check-pinia-user-scoped-reset.mjs` (9 verifiche sul reset al logout, e sa contro
quale Pinia gira), `check-drawer-width.mjs` (chiavi `DRAWER_WIDTH`),
`check-primeicons-codepoints.mjs` (codepoint cablati + baseline anti-drift).

**Lanciati oggi, uno per uno: tutti e quattro verdi, exit 0.** Sono presidi seri,
scritti da chi conosceva il difetto che volevano fermare.

⛔ **E non li lancia nessun automatismo** — vedi D1. Compaiono solo nei brief,
come cose fatte a mano.

### 2.7 ⭐ La convenzione `# Scopo:` è reale

**3.809 commenti `# Scopo:` su 3.815 `def` nei sorgenti non-test: il 99%.** Una
convenzione dichiarata in `AGENTS.md` e rispettata a quel livello non è una
convenzione: è il modo in cui il progetto scrive.

---

## 3. I difetti che pesano oggi, in ordine di conseguenza

### 🔴 D1 — Il frontend non ha nessun cancello

Sono **117.000 righe**, 390 componenti, 73 rotte: l'intera superficie che un
operatore tocca. Verificato sui due workflow, sul `package.json`, sul `Dockerfile`
e su tutto il repo:

| Cosa                                                                                         | Stato                                                                 |
| -------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `frontend/**` nei `paths:` di `ci-validate.yaml` (il cancello vero: push su `Tito-dev` + PR) | ⛔ **assente**                                                         |
| `frontend/**` nei `paths:` di `ci.yaml` (che comunque gira solo su `main`)                   | ⛔ **assente**                                                         |
| La stringa `frontend` in `.github/workflows/`                                                | ⛔ **zero occorrenze**                                                 |
| File di test (`*.spec.*`, `*.test.*`) in `frontend/src`                                      | ⛔ **0**                                                               |
| Script `test` in `package.json`                                                              | ⛔ **assente**                                                         |
| Framework di test fra le `devDependencies`                                                   | ⛔ **nessuno** (né vitest, né jest, né @vue/test-utils, né playwright) |
| `vite build` in CI                                                                           | ⛔ mai                                                                 |
| Il frontend nel `Dockerfile`                                                                 | ⛔ `COPY backend/ .` — l'immagine non lo contiene                      |
| Uno script di build/deploy del frontend nel repo                                             | ⛔ nessuno (solo due `update-npm.sh`)                                  |

⇒ **Nessun controllo del frontend — build, lint, test — viene eseguito da una
macchina prima che il codice arrivi su `Tito-dev`.** L'unica eccezione sono due
hook di chiavi i18n e header di licenza, e si accendono a intermittenza: vedi
subito sotto.

⚠️ **L'unica rete che esiste sta sul portatile di chi committa** — e si sveglia
per caso. Due hook pre-commit toccano il frontend: `check-i18n-keys` (globale, e
ottimo) e `check-license-header`. `ci-validate.yaml` li rilancia sui file
cambiati, **ma solo se quella push ha già svegliato il workflow**, cioè se tocca
anche `db/`, `backend/`, `requirements/` o `scripts/`. ⇒ Una push che tocca
**solo** `frontend/` non fa girare nemmeno quelli.

⛔ **È la forma peggiore di copertura**: non «assente», ma **dipendente da cosa
altro c'era nello stesso commit**. Un lavoro di frontend puro passa senza
controlli; lo stesso identico lavoro, se il commit tocca anche una riga di
backend, li incontra tutti. E localmente valgono solo per chi ha `pre-commit`
installato — che, per stessa ammissione di `AGENTS.md`, **non lo era su nessuna
macchina fino al 2026-08-26**.

⛔ **E oggi c'è già un rosso che nessuno vede.** `npm run lint` è
`run-s lint:*`, cioè oxlint **e poi** eslint. Lanciati adesso:

|                     |                                                                                                 |
| ------------------- | ----------------------------------------------------------------------------------------------- |
| `eslint . --no-fix` | ✅ verde, exit 0                                                                                 |
| `oxlint .`          | ⛔ **exit 1** — 7 errori: 4 `unicorn(no-useless-fallback-in-spread)`, 3 `eslint(no-unused-vars)` |
| `vite build`        | ✅ verde in 2,2s (avvisa su un chunk da 822 kB e su un import dinamico inefficace)               |

⇒ Il comando di lint che il progetto si è dato **fallisce oggi**, e non se n'è
accorto nessuno perché non lo lancia niente.

⚠️ **Nota su come sono scritti gli script**: `lint:oxlint` è `oxlint . --fix` e
`lint:eslint` è `eslint . --fix --cache`. Un comando che **modifica i file** non è
un cancello: è un formattatore. Un cancello di CI vuole la forma senza `--fix`,
altrimenti in CI riscriverebbe il sorgente e passerebbe.

⭐ **La cosa da non fare è mettere tutto in un colpo.** La lezione del §D1 del
documento gemello vale identica: un cancello che nasce con un registro lungo
protegge solo il residuo. Qui il registro è corto — 7 errori di lint — quindi
l'ordine giusto è: prima il cancello di build+lint (economico, e già quasi
verde), poi i test, che sono un cantiere.

### ✅ Com'è finita, il 2026-09-09 — il cancello esiste

**Nato `.github/workflows/ci-frontend.yaml`**, un workflow suo e non due righe
nei `paths:` di `ci-validate`: quello tira su Postgres, Java, Liquibase e
l'intero migrate — cinque minuti — e una modifica al CSS non ha bisogno di un
database. I due cancelli restano indipendenti, e un rosso dice subito **da che
parte guardare**.

| Passo                                                     | Esito locale |
| --------------------------------------------------------- | ------------ |
| `npm ci` (fallisce se `package.json` e il lock divergono) | ✅            |
| `npm run lint` — oxlint + eslint, **senza `--fix`**       | ✅            |
| `npm run guards` — i quattro presidi FE                   | ✅            |
| `npm run build` (vite)                                    | ✅            |
| `scripts/check_i18n_keys.py`                              | ✅            |

### ✅✅ E il 2026-09-09 sera **ha girato per davvero**

Merge #1547 su `Tito-dev`. Non è più «provato in locale»: è un cancello che ha
fatto un giro completo su GitHub Actions, **due volte** (sulla PR e sul push),
con **tutti** i passi verdi.

| | |
| --- | --- |
| Durata del job | **47 s** (51 s e 55 s le due corse) |
| Passi | checkout · Setup Node · `npm ci` · lint · guard · build · Setup Python · guard i18n — **tutti `success`** |
| Node risolto | `Resolved frontend/package.json as ^24.0.0` → **v24.20.0** |

⭐ **La riga sul Node è quella che valeva la pena verificare**: dimostra che la
«fonte unica di verità» non è un'intenzione scritta nei commenti ma un
meccanismo che funziona — nessun numero di versione è ricopiato nel workflow, e
la CI prende quello giusto da `package.json`. Lo stesso vale per `oxlint .` nel
log, **senza `--fix`**: è un cancello, non un formattatore.

⭐ **Nasce verde, di proposito.** I sette errori `oxlint` preesistenti sono stati
sanati **prima** di accenderlo: quattro `no-useless-fallback-in-spread`
(`{...(x || {})}` e `{...x}` sono identici su ogni valore falsy) e tre parametri
`searchTerm` mai usati, rinominati `_searchTerm` invece che tolti — la firma del
building block resta documentata. *Un cancello che nasce rosso viene spento, e un
presidio spento è peggio di uno assente.*

⭐ **E il guard i18n smette di svegliarsi per caso.** Era un hook pre-commit
`pass_filenames: false`, quindi globale per costruzione — ma su una push di solo
frontend `ci-validate` non si sveglia, e con lui non si svegliava neanche il
guard. Ora gira nel workflow del frontend, **dove il frontend cambia**.

### ✅ E il 2026-09-09 sera è arrivato anche il primo test

`vitest` (**solo lui**, 1 pacchetto: `@vue/test-utils` e `jsdom` si aggiungeranno
il giorno in cui si monterà un componente, non prima). Legge lo stesso
`vite.config.js` della build, quindi non c'è una seconda configurazione da
tenere allineata.

| | |
| --- | --- |
| Primo file provato | `src/core/composables/useApiHandler.spec.js` — **18 test**, 199 ms |
| Nel job | passo `Test (vitest)`, prima della build |

⭐ **Il file non è scelto a caso, ed è il punto.** `useApiHandler` è l'**unico**
posto in cui il frontend legge una risposta del backend — `axios` è importato in
un file solo. Quello che i 18 test fissano non è «il composable funziona»: è il
**contratto dell'envelope** di `api.md` — `fields`, `targets`, `ui_action`,
`message` e i suoi tre ripieghi — cioè metà del lavoro che il backend ha
costruito (D4) e che a video si perde se qualcuno rinomina un campo.

⭐ **E i test sono stati provati al contrario.** Un test che nasce verde non ha
ancora dimostrato di misurare qualcosa: quattro mutazioni del sorgente, quattro
rossi.

| Mutazione | Esito |
| --- | --- |
| `azioneUi` smette di leggere `ui_action` | **2 rossi** |
| tolto l'azzeramento di `campiErrati` fra due chiamate | **1 rosso** |
| `CODICI_SENZA_TOAST` da `Set` a oggetto letterale (eredita dal prototipo) | **1 rosso** |
| tolto il primo ripiego del messaggio | **1 rosso** |

⭐ **E il cancello ha preso subito un difetto mio**: la riga
`const inTest = !!process.env.VITEST` aggiunta a `vite.config.js` ha fatto
scattare `eslint` — *«`process` is not defined»* — perché i globals di Node la
configurazione li dà ai soli `scripts/**`. Corretto con un `import process from
'node:process'` esplicito, che funziona a prescindere da come è configurato il
linter. *Il primo giorno di vita, e ha già fermato qualcosa.*

⚠️ **Due residui, dichiarati:**

* la **copertura** è un file su 680: il valore di questi 18 test è il contratto
  che fissano, non la superficie che coprono. I test di **componente**
  (`ListaConfigurabile`, i drawer) restano da fare e vogliono due pacchetti in
  più — è `§6 D1-d-bis`;
* `scripts/check_license.py` **non presidia niente in CI, e non solo qui.**
  ⛔ Provato il 2026-09-09: lo script non legge **mai** `sys.argv` — usa `sys`
  soltanto per `sys.exit` — e ricava l'elenco dei file da
  `git diff --cached --diff-filter=AC`, cioè dall'**indice staged**.
  Passandogli esplicitamente `frontend/src/App.vue`, che l'header non ce l'ha,
  risponde **exit 0**.
  ⇒ In qualunque modo pre-commit lo invochi passandogli dei nomi — `--all-files`
  **e** `--from-ref/--to-ref`, che è la forma usata da `ci-validate.yaml` — vede
  **zero file** e passa. Un indice staged in CI non esiste: dopo un checkout
  pulito `git diff --cached` è vuoto per costruzione.
  🔴 **Quindi non è un buco del nuovo workflow del frontend: è che quell'hook è
  verde in *ogni* corsa di CI da sempre, per il motivo sbagliato.** Funziona solo
  dove è nato, cioè al momento del commit su una macchina di sviluppo.
  ⭐ È di nuovo il §6 punto 5 della guida sui presidi — *«un cancello che passa
  perché non ha misurato niente è peggio di un cancello assente»* — e stavolta
  colto su un presidio che questo stesso documento contava fra le difese
  esistenti (§3 D1, §3 D10).

  ### ✅ Chiuso il 2026-09-09

  `scripts/check_license.py` distingue ora **due sorgenti**, e lo dice:

  | Modalità          | Da dove prende i file                                                                                       | Quando                                                                                                                                                                                    |
  | ----------------- | ----------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
  | **range**         | `git diff --diff-filter=AC <from> <to>`, con gli estremi presi da `PRE_COMMIT_FROM_REF`/`PRE_COMMIT_TO_REF` | ⭐ la forma della CI. pre-commit esporta quelle variabili **solo** con `--from-ref/--to-ref` (verificato nel suo `commands/run.py`): la loro presenza è un discriminante, non un'euristica |
  | **indice staged** | `git diff --cached --diff-filter=AC`                                                                        | il commit su una macchina di sviluppo — **invariata**                                                                                                                                     |

  ⛔ **`sys.argv` non è diventato la sorgente primaria, ed è la parte da non
  sbagliare**: pre-commit passa gli aggiunti **e i modificati**, quindi fidarsi
  di quell'elenco avrebbe rimesso dentro la `M` che il 2026-08-26 era stata
  tolta apposta — cioè avrebbe trasformato il cricchetto nel blocco totale che
  si era deciso di evitare. L'elenco passato si usa solo per **intersezione**:
  restringe, non allarga.

  **Provato in locale, prima/dopo, sulla forma esatta della CI** (commit
  `a2eedbd85`, che aggiunge `scripts/guardrail_grant_ruolo_batch.py` senza
  header):

  |                                                                     | Script vecchio       | Script nuovo                                          |
  | ------------------------------------------------------------------- | -------------------- | ----------------------------------------------------- |
  | Range con un file aggiunto **senza** header                         | ⛔ `exit 0`, silenzio | ✅ `exit 1`, nomina il file                            |
  | Range con file aggiunti **con** header                              | `exit 0`             | ✅ `exit 0`                                            |
  | Commit con un file nuovo senza header (fixture staged, poi rimossa) | `exit 1`             | ✅ `exit 1` — e anche end-to-end attraverso pre-commit |
  | `--all-files`                                                       | `Passed`             | ✅ `Passed`                                            |

  ⭐ **E il verde adesso è leggibile.** L'hook stampa quanti file ha guardato e
  **da dove li ha presi**, con `verbose: true` nella configurazione — perché
  pre-commit nasconde lo stdout di ciò che passa, ed è esattamente così che il
  difetto è rimasto invisibile per mesi. ⚠️ La riga dice «in questo lotto»
  perché pre-commit spezza l'elenco in più invocazioni: uno zero è il conto di
  quel lotto, non del totale.

  ### ✅✅ Confermato nella CI vera, la sera stessa

  Passo `pre-commit` del merge #1547 su `Tito-dev`:

  ```text
  Controlla header licenza.................................................Passed
  Header di licenza: 1 file nuovi controllati in questo lotto (range 41e99310..10ea7264).
  Header di licenza: 2 file nuovi controllati in questo lotto (range 41e99310..10ea7264).
  ```

  ⭐ **Tre file nuovi effettivamente controllati, dove prima ne guardava zero** —
  e il numero si legge nel log, che era il secondo scopo della correzione. Il
  «Passed» di ieri e quello di oggi si scrivono uguale e valgono cose opposte.

  ⚠️ **Un difetto del METODO, non del codice, trovato durante la prova e vale
  più della correzione**: il primo caso che avevo scelto (`693e4b258`) sembrava
  un file aggiunto senza header e non lo era. Quel commit è un **merge**, e
  `git diff-tree` su un merge mostra il diff *combinato* mentre `git diff A~1 A`
  mostra quello col primo genitore: i due elenchi divergono legittimamente. Lo
  script aveva ragione e il mio caso di prova torto. ⇒ *Un banco di prova va
  verificato con lo stesso comando che usa il codice sotto prova*, o si finisce
  a inseguire un difetto che non c'è.

---

### 🔴 D2 — 258.000 righe di Python senza analisi statica. E il frontend ce l'ha e non la lancia

Cercati nel repo: `pyproject.toml`, `setup.cfg`, `ruff.toml`, `.ruff.toml`,
`mypy.ini`, `tox.ini`. **Nessuno esiste.** Cercati nei due `requirements`:
`ruff`, `mypy`, `black`, `flake8`, `pylint`, `bandit`, `pip-audit`. **Nessuno
compare.** In `.vscode/settings.json` non c'è `python.analysis.typeCheckingMode`.

⇒ **Sul backend non gira nessun linter, nessun formattatore, nessun type
checker.** Né in CI, né in pre-commit, né come impostazione di repo.

⛔ **E una regola del progetto presuppone il contrario.** `AGENTS.md` prescrive:
*«Dopo un `ErrorManager.require(... is not None ...)` aggiungere sempre l'`assert`
corrispondente **per aiutare il type checker**»*. È una convenzione scritta a
beneficio di uno strumento che **nel repo non è configurato da nessuna parte**:
esiste solo se chi legge ha, sul proprio editor, un'impostazione che il repo non
chiede e non verifica.

⚠️ **La conseguenza non è cosmetica, ed è dove si somma con D9.** La suite Django
è veloce **perché** è mockata: 6.578 fra `patch(` e `MagicMock` in 261 file di
test su 309. Un mock non può accorgersi che un chiamante passa una `str` dove il
service dichiara un `UUID`, né che un ramo è irraggiungibile, né che un import è
morto. Quelle sono esattamente le classi che un type checker vede — e non c'è.

⭐ **L'asimmetria è la cosa da guardare, non i due fatti separati**:

|                                  | Analisi statica                          | Cancello di CI |
| -------------------------------- | ---------------------------------------- | -------------- |
| **Backend** (258k righe Python)  | ⛔ nessuna                                | ✅ duro         |
| **Frontend** (117k righe JS/Vue) | ✅ eslint + oxlint + prettier configurati | ⛔ nessuno      |

Ognuna delle due metà ha esattamente ciò che manca all'altra. Non è una
coincidenza: sono due cantieri cresciuti con due abitudini diverse e nessun
momento in cui qualcuno li ha guardati insieme.

### ✅ Com'è finita, il 2026-09-09 — l'asimmetria è chiusa da entrambi i lati

**`ruff` è entrato**, con la selezione dichiarata in un `ruff.toml` alla radice e
non negli argomenti dell'hook — un elenco di regole dentro un hook è una seconda
sorgente di verità che diverge dal `ruff check` lanciato a mano.

|                         |                                                                     |
| ----------------------- | ------------------------------------------------------------------- |
| Regole selezionate      | **`F` + `E9`** — difetti, non stile                                 |
| Registro all'accensione | 136 rilievi (126 import morti)                                      |
| Sanati con `--fix`      | **129**, su 97 file                                                 |
| Sanati **a mano**       | **7** `F841`, perché ruff non poteva sapere se la chiamata contasse |
| Stato del cancello      | **zero su tutto il repo**                                           |

⛔ **`E` non è stata selezionata, ed è la decisione che conta.** Da sola aggiunge
**5.051** rilievi, di cui **4.853 `E501`** (lunghezza riga) su un progetto che
una lunghezza di riga dichiarata non ce l'ha: il 96% sarebbe rumore. Un cancello
che nasce con 4.853 righe di registro protegge solo ciò che avanza e viene
spento al secondo blocco inutile.

⭐ **I 7 a mano sono la parte interessante**, e spiegano perché ruff li marca
«unsafe»: quattro erano *«la chiamata conta, il binding no»* — `result =
view.get_queryset()` dove l'asserzione successiva verifica **la chiamata**: lì si
toglie il binding e si tiene la riga. Tre erano morti del tutto. Nessuno strumento
poteva distinguerli.

⭐ **Il formattatore resta spento**, ed è scritto nel `ruff.toml`: riformattare
258.000 righe renderebbe illeggibile ogni `git blame`, e non è una decisione da
prendere di straforo dentro un file di configurazione.

⭐ **E l'hook ha girato davvero, non solo la configurazione.**
`pre-commit run ruff-check --all-files` → **Passed** in 5,9 s (compreso lo
scaricamento dell'ambiente pinnato a `v0.16.6`, poi in cache), e
`pre-commit run --all-files` → i **tre** hook verdi in 1,3 s.
⚠️ Correzione a una riga scritta poche ore prima in questo stesso documento:
*«`pre-commit` non è installato su questa macchina»* era **falso**. È installato
in `~/.venvs/zeroerp-tools` — il percorso che `scripts/update-venv.sh` documenta
— e `.git/hooks/pre-commit` lo punta già. Non lo trovavo perché quel venv non era
sul `PATH`. ⭐ La correzione conta: senza, il punto sarebbe rimasto «scritto e mai
provato», che è esattamente lo stato che questo documento contesta agli altri.

✅✅ **E in CI ha girato**: nel passo `pre-commit` del merge #1547,
`ruff check ... Passed`. Il cancello non è più solo configurato.

**Controllo prima/dopo, perché 131 file toccati vogliono una prova:**
suite Django a database irraggiungibile, `4530 test` — *prima*: 27 fallimenti,
194 errori, 17 saltati; *dopo*: **identici**, e verificati **per nome**, non solo
per conteggio (221 righe `ERROR:`/`FAIL:`, `diff` vuoto). Più `manage.py check`
pulito e `spectacular` che rigenera 815 operazioni — cioè tutte le view si
importano ancora.

---

### 🟠 D3 — Lo schema OpenAPI pubblicato dichiara che l'API è anonima. E il controllo che lo direbbe non lo lancia nessuno

Generato lo schema (`manage.py spectacular`, 2026-09-09): **615 path, 815
operazioni**. Dentro `components:` c'è **solo `schemas:`**.

⛔ **`securitySchemes` non esiste.** Le uniche `security:` presenti sono 17
`- {}`, cioè le operazioni dichiarate esplicitamente pubbliche. Su tutte le
altre 798 lo schema non dice **niente** — che in OpenAPI significa «nessuna
autenticazione richiesta».

**Conseguenza concreta, non teorica**: su `/api/docs/` (Swagger UI) non c'è il
pulsante *Authorize*, quindi nessuna chiamata autenticata è provabile dalla
documentazione; e qualunque client generato dallo schema parte **senza header
`Authorization`**, cioè prende 401 su ogni rotta e sembra che sia rotto il
backend.

**La causa è una classe che manca**, e lo dice il controllo stesso: 607 avvisi
identici — *«could not resolve authenticator `JwtAuditAuthentication`. There was
no `OpenApiAuthenticationExtension` registered for that class»*. Una sottoclasse
di venti righe chiude tutti e 607.

#### ⛔ E qui c'è il difetto vero, che è di cancello e non di schema

| Comando                                       | Esito 2026-09-09                                    |
| --------------------------------------------- | --------------------------------------------------- |
| `manage.py check` — **quello che gira in CI** | «System check identified **no issues**», exit **0** |
| `manage.py check --deploy`                    | **677 problemi**, `SystemCheckError`, exit 1        |

I 677: **607** `drf_spectacular.W001` (l'autenticatore irrisolto), **66**
`drf_spectacular.W002` («unable to guess serializer» — view senza `@extend_schema`
su qualche metodo), 3 `security.W00x`, 1 `mail.E001`.

⛔ **drf-spectacular aggancia i propri controlli al ramo `--deploy`.** La CI lancia
`check` liscio, quindi **non ne vede nemmeno uno**. È un cancello che passa perché
non ha misurato niente — il §6 punto 5 della guida sui presidi, in un'altra sede.

⚠️ E i 66 `W002` violano una regola **scritta**: `AGENTS.md` dice *«ogni `APIView`
esposta su `/api/v1/` deve avere `@extend_schema` su ogni metodo HTTP pubblico,
**per evitare warning drf-spectacular in CI**»*. La regola nomina il warning che
la CI non guarda.

⚠️ **Dei 3 `security.W00x`, due sono di struttura** (`SECURE_HSTS_SECONDS` e
`SECURE_SSL_REDIRECT` non impostati in `settings.py`) e uno è di macchina
(`SECRET_KEY` di sviluppo): il terzo non va contato, i primi due sì. Non c'è
nessuna CSP, né in `settings.py` né in `index.html` — e i due token JWT
(**access e refresh**) vivono in `localStorage`. ⭐ La postura oggi regge perché
`v-html` è a zero e `axios` sta in un file solo, cioè perché **non c'è
superficie**; ma la difesa è tutta lì, e nessun presidio la verifica.

### ✅ Com'è finita, il 2026-09-09 — mezzo difetto chiuso, e l'altro mezzo si vede meglio

Nata `apps/core/api/openapi_extensions.py`: una `OpenApiAuthenticationExtension`
che dichiara `JwtAuditAuthentication` come Bearer JWT, registrata per **import**
in `CoreConfig.ready()` (è il meccanismo di drf-spectacular: la sottoclasse si
registra alla definizione).

|                                          | Prima                  | Dopo            |
| ---------------------------------------- | ---------------------- | --------------- |
| Problemi di `check --deploy`             | **677**                | **124**         |
| `W001` «could not resolve authenticator» | 607                    | **0**           |
| `components.securitySchemes`             | ⛔ assente              | ✅ `bearerAuth`  |
| Operazioni con `security:`               | 17 (le sole pubbliche) | **815** — tutte |

⭐ **La dichiarazione è onesta rispetto al codice**: il protocollo è quello di
SimpleJWT, e ciò che la nostra sottoclasse aggiunge — la propagazione dei GUC di
identità al database — non cambia **come ci si autentica**, quindi non cambia lo
schema.

⚠️ **E adesso si vede una cosa che prima era sepolta.** I `W001` residui sono
**54**, e non sono più autenticatori: sono **collisioni di `operationId`**
(`amm_software_operatori_retrieve` per `/operatori/` e `/operatori/{id}/`,
risolte da drf-spectacular con un suffisso numerico). Non sono un difetto grave —
un client generato prende `..._retrieve` e `..._retrieve_2` — ma erano
**invisibili sotto i 607**. È il modo tipico in cui un registro lungo nasconde le
sue righe più utili.

⛔ **`D3-b` resta aperto e non è diventato più facile**: portare `check --deploy`
in CI significa ancora chiudere `mail.E001` e aprire un registro da **66 `W002`**
più questi 54. Il rimedio di oggi ha tolto il rumore, non il cantiere.

---

### 🟠 D4 — Il terzo lato del contratto d'errore: quello che il backend manda e nessuno legge

Il documento gemello (§2.3) descrive il contratto a tre lati: `codice` → backend,
`context->>'campo'` → frontend, `VARIADIC valori` → operatore. Il backend lo ha
esteso di due campi — `hint` (2026-08-18) e `targets` (2026-08-24) — con lavoro
consistente: cinque punti di traduzione allineati, un building block
`diagnostica_db()`, un test per punto.

**Cosa ne arriva a video**, verificato su `frontend/src`:

| Campo dell'envelope      | Letto dal frontend?                                                     |
| ------------------------ | ----------------------------------------------------------------------- |
| `fields` → `campiErrati` | ⭐ **sì**, e bene: 268 binding in 65 file                                |
| `targets` → `bersagli`   | ⭐ **sì**: 127 occorrenze in 16 file, con il gesto composto da `execute` |
| `ui_action` → `azioneUi` | ⚠️ **letto, ma quasi mai usato** — vedi sotto                            |
| `hint`                   | ⛔ **zero occorrenze in tutto `frontend/src`**                           |
| `retryable`              | ⚠️ 1 occorrenza                                                          |

⛔ **`hint` è la `soluzione` che il team DB scrive a catalogo per ogni codice** —
*«se il documento non è ancora numerato, la strada è il reset del lotto…»*, cioè
**l'unica frase che dice all'operatore cosa fare adesso**. Viaggia dal DB al
`ServiceError` all'envelope. E si ferma lì.

⚠️ **E su `ui_action` la copertura è una su sette.** Il backend ne emette sette
valori distinti (`highlight_form_fields` su 129 codici, `show_error_banner`,
`show_toast_error`, `redirect_login`, `show_retry_dialog`, `confirm_and_retry`,
`show_info_banner`), più i due default per classe. Il frontend ne ramifica
**uno**: `confirm_and_retry`, in `useForzaturaConfermata`. Gli altri sei
arrivano e non muovono niente.

⭐ **È la regola che `api.md` scrive di suo pugno, applicata a sé stessa**:
*«prima di dichiarare fatta una capability, verificare che il client la LEGGA.
Un campo dichiarato e mai letto sembra presidiato e non presidia niente.»* Vale
per `hint` esattamente come valeva per `fields` nel 2026.

**Rimedio**, ed è piccolo: `hint` ha già un consumatore naturale dichiarato nei
brief (la coda accrediti, dove distingue «non si può» da «resetta il lotto, ma
sappi che la nota si rigenera»). Un posto solo dove mostrarlo — sotto il
messaggio, quando c'è — e il campo smette di essere una promessa.

### ✅ Com'è finita, la sera del 2026-09-09 — il campo si vede

**Un posto solo, ed è quello previsto.** `useApiHandler` estrae `error.hint` e
lo espone come **`soluzione`**; il toast lo rende **sotto il messaggio**, nel
`detail` di PrimeVue. ⭐ Come per il gesto, **non c'è niente da scrivere nei
componenti**: chi usa `execute` ce l'ha senza una riga di modifica, e i tre rami
del toast (sistema · con gesto · normale) lo portano tutti e tre.

⭐ **La riga che rendeva il campo mostrabile non era nel frontend, ed è la parte
che la stima non conteneva.** `_apply_policy` ricopiava `hint` **sempre**, anche
sui tre codici di `is_technical_code` — dove il canale `HINT` non porta la
`soluzione` di nessun catalogo, ma il testo che PostgreSQL scrive per lo
**sviluppatore**, in inglese (*«Perhaps you meant to reference the column …»*).
⛔ Mostrarlo così avrebbe chiuso D4 **introducendo** un difetto: un'istruzione in
inglese, su un oggetto che l'operatore non conosce, sotto un messaggio che nel
frattempo la policy ha già sostituito. ⇒ Il filtro sta a monte, in **una sede
sola**, dove sta già la regola gemella del bersaglio.

⚠️ **E le due regole DIVERGONO, di proposito.** Il bersaglio guarda anche lo
status (`is_technical or policy.http_status >= 500`), la soluzione **no**: su un
codice di classe `TECNICO` **registrato a catalogo** la frase esce. *Su un 500
non c'è nessun gesto da offrire, ma «segnalare al supporto citando il
request_id» è esattamente ciò che chi legge può fare.* Due campi, due regole, e
la differenza è provata nei casi 5 e 6 di `test_error_translator_soluzione.py`
invece che spiegata in un commento.

**Cosa è stato toccato**, ed è poco per costruzione:

| Dove | Cosa |
| --- | --- |
| `error_translator._apply_policy` | `hint=None if is_technical else …` — la condizione perché il campo sia mostrabile |
| `test_error_translator_soluzione.py` | **7 test**, gemello di `test_error_translator_campi`; provati per **mutazione** (spento il guard, ne cadono 3) |
| `useApiHandler` | estrae `soluzione`, la azzera come gli altri, la passa ai tre rami del toast |
| `useNotify` | `error` / `systemError` / `errorConAzioni` prendono la soluzione e la mettono nel `detail` |
| `App.vue` | il gruppo `azioni` ha un template suo: lì la soluzione va scritta a mano, **fra** il testo e i pulsanti |
| `constants.js` | `TOAST_DURATION.ERROR_CON_SOLUZIONE` |
| `useApiHandler.spec.js` | da 18 a **23** test; il nuovo contratto è fissato il giorno in cui viene reso, non prima |
| `pipeline_runner` | 🔴 il blob `errore` del **200** leggeva `exc.hint`/`exc.targets` diretti: stesso nome dell'envelope, **regola diversa**. Ora passa da `to_api_error` |
| `test_pipeline_runner` | il presidio di quella regola, nei due versi (tecnico → niente; rimediabile → entrambi) |
| `useNotify.spec.js` | **6 test** nuovi: la rete sotto la de-duplicazione dei tre toast d'errore |

### 🔴 Il difetto trovato rendendo il campo, ed è il pezzo che vale

**Il blob d'errore dentro il 200 del runner non passava dalla policy.** Gli
endpoint di pipeline rispondono 200 anche quando la catena si ferma — il
fallimento è un campo del payload — e quel campo veniva composto leggendo
`exc.hint` ed `exc.targets` **diretti**. L'envelope invece li fa passare da
`_apply_policy`, che su un codice tecnico li toglie.

⛔ **Due regole per lo stesso nome, ed è peggio di due nomi diversi**: due nomi
si notano leggendo, due regole no. Da quella strada uscivano un **bersaglio su
un guasto** — un pulsante che il contratto vieta — e il `HINT` grezzo di
PostgreSQL.

⭐ **Il difetto era vivo da prima del 2026-09-09**, ed è diventato visibile solo
perché il frontend ha cominciato a *rendere* il suggerimento: *un campo che
nessuno mostra non ha comportamenti sbagliati, ne ha di invisibili.* È la stessa
lezione di D4 letta dall'altro capo — e il motivo per cui rendere un campo a
video vale più di trasportarlo bene.

⚠️ **La correzione non ricopia la regola**: chiede i due valori a
`ErrorTranslator.to_api_error`, che è chi la possiede. `message` e `detail`
restano invece grezzi, perché quel blob alimenta il pannello di diagnostica di
un lotto — la differenza è voluta ed è scritta lì.

### ✅ E il building block che otto punti riscrivevano a mano

Trovato tirando il filo del `dict(riga[0])` che aveva fatto fallire il job
notturno per quattro notti: **altri otto punti** facevano la stessa coercizione
`jsonb` a mano — `ui/db/{ui,dashboard}_repository`,
`core/db/{auth,search,email}_repository`, `invito_operatore_service`. Non erano
rotti; erano otto copie di un BB che esiste dal 2026-06-11.

⛔ **E non era un find-and-replace, ed è il punto.** I building block sono
**due** e non sono intercambiabili: `coerce_jsonb_dict` ripiega a `{}`,
`jsonb_out` fa esplodere. Su `auth_repository.registra_tentativo_login` — che
torna `{bloccato, …}` e viene letto con `result.get("bloccato")` — il ripiego
avrebbe dato `None`, cioè **account non bloccato**: un fail-OPEN silenzioso su
un percorso di autenticazione. ⇒ Tutti e otto adottano **`jsonb_out`**, che
conserva la semantica che avevano.

⚠️ **La conversione era CIECA, e l'ha detto una mutazione.** Spegnendo
`jsonb_out` cadevano otto test — e nessuno dei quali toccava questi otto punti:
erano tutti consumatori storici del BB. *Un cambiamento che nessun test vede non
è verificato dal fatto che la suite resti verde.* ⇒ Sono stati aggiunti i due
presidi che mancavano, e coprono cose diverse:

| Presidio | Cosa tiene |
| --- | --- |
| `test_coercizione_jsonb_dal_bb` | la **forma**: tre regex vietano di riscrivere i BB a mano, registro a **zero** — nasce senza arretrato, come il cancello di `ruff` |
| `tests/db/test_jsonb_stringa_negli_otto_lettori` | il **comportamento**: la stringa entra, un dict esce, per tutti e otto (più il verso opposto, che si accorge se un lettore sparisce) |

⭐ Il primo è il presidio che a quel call site sarebbe servito: era stato scritto
**dopo** l'estrazione del BB e non l'aveva cercato — la forma esatta di
*«un BB unifica la lettura, ma i punti che la riscrivono si cercano»*.

⭐ **La durata è una decisione, e ha una ragione dichiarata** (Tid, 2026-09-09):
il toast con la soluzione dura **di più perché il testo è il doppio**, non
perché l'errore sia più grave. ⛔ E **non** è persistente come quello col gesto:
la soluzione è a catalogo *per ogni codice*, quindi `life: 0` avrebbe fatto di
**ogni** errore di dominio un toast da chiudere a mano. *Un gesto ha un pulsante
da premere e può aspettare; una frase si legge e se ne va.*

⚠️ **Chi chiama `notify.error(...)` a mano resta fuori**, ed è la stessa
asimmetria che vale già per il gesto: il canale è `execute`. Non è un residuo
nascosto — è scritto in `frontend-standards` §La soluzione, con la domanda che
va fatta a una schermata che mostra un errore senza passare di qui.

⚠️ **E un consumatore che di proposito NON la mostra**: il rifiuto confermabile
(`useForzaturaConfermata`). Lì la frase «cosa fare adesso» **è il dialog che sta
comparendo**, e ripeterla sotto direbbe due volte la stessa cosa.

### ✅ E la seconda metà: le sei `ui_action`, dichiarate

**Decisione di Tid, 2026-09-09: si dichiara la copertura.** Il default del
client serve **sei valori su sette**, e non per rassegnazione — `campiErrati`
serve `highlight_form_fields` (ed è l'unica forma in cui quella richiesta è
azionabile), lo **status 401** serve `redirect_login` prima ancora che il codice
si legga, il **toast** serve gli altri quattro. Ramificarli oggi comprerebbe
zero.

⚠️ **La condizione per accendere il settimo resta scritta e invariata**: le
**176 righe di override** vanno riguardate **prima**, non dopo — sono state
decise quando nessuno poteva verificarle a video. La tabella per valore sta in
`api.md` §Cosa cambia davvero lo status.

---

### 🟠 D5 — `area_funzionale = "ai_assistant"`: un cancello che non si può aprire

`AIQueryView` (`apps/ai_assistant/api/views.py`) è una `DomainAPIView` e dichiara
`area_funzionale = "ai_assistant"`.

Il catalogo delle aree è
`db/changelog/migrations_v2/80_data/sql/config/aree_funzionali.csv`, e contiene
**tredici** righe: `anagrafiche`, `vendite`, `acquisti`, `catalogo`,
`contabilita`, `magazzino`, `pagamenti`, `storico`, `config`, `core`, `pratiche`,
`documenti`, `strumenti`.

⛔ **`ai_assistant` non c'è.**

Letta la catena dalla doc auto-generata (`script.fn_resolve_livello_area`), il
percorso per un'area che il catalogo non nomina è: nessun `user_override_aree`
(il `JOIN` su `config.aree_funzionali` non trova nulla), nessun profilo per la
stessa ragione ⇒ **passo 5, `RETURN 'BLOCCATO'`**.

⇒ L'assistente è raggiungibile **solo da chi ha `SUPER_ADMIN`**, che al passo 2
ottiene `TUTTO` prima ancora che l'area venga cercata. **A nessun altro operatore
il permesso può essere concesso**, perché non esiste la riga a cui appenderlo.

⚠️ **Non è un buco: è il suo opposto**, e questo lo rende peggio da trovare. La
catena è fail-closed e si comporta esattamente come deve; il difetto è che il
403 è **indistinguibile** da «non hai il permesso», mentre la verità è «il
permesso non esiste e nessuno può dartelo». Chi indaga cercherà nei profili di
accesso, e lì non troverà niente da sistemare.

⚠️ **Oggi la rotta è dietro `AI_ENABLED`, che vale `0` di default** e non monta
nemmeno le URL. ⛔ Ma «oggi non capita mai» è uno degli argomenti che la Regola
zero rifiuta per nome: il giorno in cui la funzione si accende, si accende **rotta
per tutti tranne uno**. Fra le nove aree dichiarate nel backend, **è l'unica
fuori catalogo**: le altre otto combaciano.

**Rimedio**: una riga nel CSV delle aree (brief al team DB), oppure —
se l'assistente è deliberatamente admin-only — `AdminAPIView`, che dice a chi
legge il codice la stessa cosa che oggi dice il silenzio.

✅ **Registrato il 2026-09-09**, e non è il rimedio: `api.md` §Endpoint attivi
ora nomina l'app **con questo difetto scritto accanto**. ⭐ Il criterio è che
registrare una funzione tacendo che il suo gate non si può aprire sarebbe stato
registrare **metà** del fatto — e la metà rassicurante. Il difetto resta aperto.

---

### 🟠 D6 — Il `count` che è un'eco, e stavolta il caso esiste

`api.md` scrive dal 2026-09-02, dopo averlo visto rotto due volte in un giorno:
*«⛔ Il `count` non si deriva MAI dalle righe che stai consegnando. `len(results)`
non è un conteggio: è un'eco.»*

Cercata la forma vietata nel backend, esclusi i test: **8 occorrenze vive**, e la
buona notizia è che sono **concentrate in due helper** (`_build_results_response`
in `catalogo_service.py` e in `listini_service.py`) più sei siti diretti in
`pagamenti`, `vendite`, `core` e `ai_assistant`. Si sanano in due punti, non in
otto.

⛔ **E c'è un caso vero, non un'ipotesi** — è l'unica misura di comportamento di
questo documento, e vale come controesempio:

```python
def fn_lookup_articoli(*, search=None, ..., limit: int = 20) -> dict[str, object]:
    _validate_lookup_limit(limit, max_limit=50, ...)
    results = repository.lookup_articoli(..., limit=limit)
    return _build_results_response(results)      # {"count": len(results), ...}
```

⇒ Sull'autocomplete degli articoli — **la ricerca più usata dell'applicazione**,
quella che apre ogni riga di ogni documento — una ricerca con più di venti
risultati risponde `count: 20` su venti righe. Il conteggio **conferma il
troncamento** invece di rivelarlo. Stessa forma su `fn_lookup_unita_misura`
(`limit=200`).

⚠️ **E la forma che mente è identica a quella che non mente.** Lo stesso helper
serve anche `fn_list_componenti`, `fn_list_uom_operative`, `fn_list_note_articolo`
— che un `limit` non ce l'hanno, e lì `len()` è numericamente giusto. Chi legge
il codice non ha modo di distinguere i due casi: il commento sopra l'helper dice
*«collezioni figlie non paginate»*, ed è vero per metà dei chiamanti.

⚠️ Il difetto è **latente** perché a valle c'è un autocomplete, e un autocomplete
il `count` non lo guarda. ⛔ Ma `<ListaConfigurabile :paginata="false">` **lo
guarda**: confronta `rows.length` con `total` e si rifiuta di disegnare la tabella
se divergono. Il giorno in cui una di queste risposte finisce lì, il guard
confronta un numero con sé stesso e tace.

---

### 🟡 D7 — Endpoint costruiti, documentati, e mai raggiunti da nessuna schermata

Confrontati i 615 path dello schema OpenAPI con tutte le chiamate `api.*` del
frontend (risolvendo le costanti di percorso), e **verificati a mano** i residui
per non contare le famiglie che il frontend chiama per parametro:

| Famiglia                                                                                      | Endpoint | Nel frontend                                                                  |
| --------------------------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------- |
| `/core/email/` — outbox, prepare, allegati, log operatore                                     | **10**   | ⛔ `email/outbox`, `email/prepare`, `email/allegati`, `email/log` → **0 file** |
| `/core/tracciamento/` — `domini-task`, `job-summary`, `task-registry`, `task-implementations` | 4        | ⛔ 0 file                                                                      |
| `/core/users/{id}/permessi-effettivi/` · `/permessi-audit/`                                   | 2        | ⛔ 0 file                                                                      |
| `/vendite/commesse/push/run/` · `/push/{id}/`                                                 | 2        | ⛔ 0 file                                                                      |
| `/vendite/.../rettifica-controllata/` (N6 dei listini)                                        | 1        | ⛔ 0 file                                                                      |
| `/vendite/pipeline/run-until-done/`                                                           | 1        | ⛔ 0 file                                                                      |
| `/anagrafiche/utilities/manual-lookup/`                                                       | 1        | ⛔ 0 file                                                                      |
| `/shop/register/check-email/`                                                                 | 1        | ⛔ 0 file                                                                      |

⛔ **Il caso che vale più degli altri è l'ultimo della prima riga.** Ci sono
**due** viste sulla stessa tabella `config.email_log`:

* `EmailLogListView` — `AdminAPIView`, `/amm-software/email-log/` → **il frontend
  la usa** (store `emailLogs`, `EmailLogsListView`);
* `EmailLogOperatoreListView` — `DomainAPIView`, `/core/email/log/` → **nessuno la
  chiama**.

⇒ La versione **con lo scope dell'operatore** — cioè quella che serve a una
persona normale per vedere le proprie mail — non ha una schermata. Vede il
registro solo chi è amministratore.

⚠️ E l'outbox è un flusso **completo e chiuso a chiave** (`prepare_draft` →
`add_attachment` → `confirm_and_send` / `cancel`, più il download degli allegati),
con il suo service, il suo repository e la sua voce nel catalogo BB: **otto
endpoint e nessuna porta**.

⭐ **Non tutti e otto sono lo stesso caso**, e la distinzione è quella che decide
cosa farne: `run-until-done`, `permessi-audit` e `manual-lookup` possono
legittimamente essere API di servizio o superate; `email/outbox` e
`/core/email/log/` sono **funzioni finite per un utente che non le raggiunge**.
La domanda per ciascuno è una sola — *«questa la deve poter usare una persona?»*
— e la risposta va **scritta**, perché oggi le due categorie si leggono uguali.

---

### 🟡 D8 — Undici view di amministrazione sotto `KeepAlive` che caricano solo in `onMounted`

`AppLayout.vue` monta le view di dominio dentro `<KeepAlive :max="10">`. Una view
tenuta in cache **non ri-esegue `onMounted`** quando ci si torna: ri-esegue
`onActivated`.

Misurato su `frontend/src`: **16** file `*View.vue` su 63 usano `onMounted` senza
`onActivated`. Cinque sono fuori dal layout (login, cambio password, le tre
attivazioni) e sono legittimamente esenti. **Gli altri undici sono tutti in
`amministrazione/views/`**: operatori, emittenti fiscali, famiglie documento,
reparti, processi automatici, audit log, i tre pannelli email, le due definizioni
di workflow.

⇒ Si apre la lista operatori, si crea un operatore da un'altra scheda, si torna:
la lista è quella di prima. Nessun errore, nessun log.

⛔ **E il `:max="10"` rende il difetto intermittente**, che è la parte peggiore:
con undici o più view visitate, la LRU ne sfratta una — quella rimontata **si
ricarica e sembra corretta**, quella ancora in cache no. Un difetto che si
riproduce a giorni alterni non viene creduto.

⭐ La forma giusta è già scritta e commentata nel repo
(`SessioniAttivePanel.vue`: *«`onActivated` oltre a `onMounted`: la home vive
sotto KeepAlive»*) e in memoria: il caricamento va reso **idempotente** e messo
in `onActivated`, non spostato.

---

### 🟡 D9 — La suite è larga e poco profonda, e il livello che va in profondità nessuno lo lancia

4.560 test in **33 secondi** non è un vanto: è una descrizione. 261 file di test
su 309 usano `unittest.mock`, con 6.578 fra `patch(` e `MagicMock`. Ciò che la
suite verifica sono i **service con i repository finti**, ed è il livello giusto
per validazione, dedup e not-found.

⭐ **Il livello che attraversa la giuntura esiste ed è cresciuto**: 19 file di
test usano `richiedi_db_provvisto` (34 punti di chiamata) e girano contro il
database costruito da Liquibase, accesi in CI da `ZEROERP_TEST_DB_E2E=1`. Fra
questi i guardrail sui codici errore, sull'envelope, sui tipi di handler della
coda e sull'ordine dei gruppi di lotto. ✅ **`api.md` §Test lo registra dal
2026-09-09**: la tabella ha tre livelli e dichiara, per ciascuno, se gira in CI —
prima ne elencava due e il terzo esisteva già da mesi.

⛔ **Il terzo livello, gli smoke, non lo lancia niente.** Sedici script in
`backend/scripts/tests/`, ognuno in `transaction.atomic()` + `set_rollback(True)`,
quindi eseguibili senza lasciare traccia — ed è proprio la proprietà che
renderebbe banale metterli in CI. La CI non nomina la parola «smoke». Il registro
`baseline-smoke.tsv` ha **due** righe (`smoke-fatturazione-render-stampa.py`
FIXTURE_DERIVATA, `smoke-nota-credito-resi.py` ERRORE): un registro corto, che è
la condizione migliore per accendere un cancello.

⭐ **Lanciati la sera del 2026-09-09**, appena il database è tornato: `2 non-verdi
su 16, entrambi già noti in baseline, nessuna regressione` (exit 0, ~4 min). ⇒ Il
registro **non è cresciuto** da quando è stato preso, e i sedici script fanno il
loro mestiere. È la conferma che il problema non è la loro qualità: è che li
lancia una persona quando se ne ricorda.

⚠️ **E resta vero che in CI non si possono mettere così** (§8): cercano i soggetti
nei dati esistenti, e su un database ricostruito da zero uscirebbero quasi tutti
`SENZA_MATERIA`. Le due frasi non si contraddicono — dicono che il valore di
questi script è legato al **database di sviluppo**, e che portarli in CI vuol dire
prima insegnargli a fabbricarsi i soggetti.

⚠️ E resta vero ciò che `AGENTS.md` documenta: **il codice di uscita di uno smoke
non dice la verità** — ce n'è uno che stampa «ESITO: FALLITO» e esce `0`. Chi li
lancia a mano con `&&` legge verde su un rosso.

⚠️ **Un'osservazione sulla regola dei test, che oggi regge per metà.**
`AGENTS.md` dice: *«usare `unittest.TestCase` (o `django.test.SimpleTestCase`)»*,
come se fossero equivalenti. Non lo sono: **`SimpleTestCase` blocca l'accesso al
database** (`DatabaseOperationForbidden`), `unittest.TestCase` no — lo *permette*
soltanto.

| Forma                                           | Classi al 2026-09-09 | Blocca il DB?                                        |
| ----------------------------------------------- | -------------------- | ---------------------------------------------------- |
| `unittest.TestCase` (53 qualificate + 447 nude) | **500**              | ⛔ no                                                 |
| `SimpleTestCase`                                | **201**              | ✅ sì                                                 |
| `django.test.TestCase`                          | 0                    | (creerebbe un DB usa-e-getta per **tutta** la suite) |

⇒ Un test scritto come `unittest.TestCase` a cui sfugge un mock parla col
database vero senza che niente protesti — e il rapporto è **due a uno** a favore
della forma che non presidia. Le due opzioni della regola non fanno la stessa
cosa, e la regola non lo dice.

⚠️ Resta vera, e va tenuta, la dipendenza implicita che `AGENTS.md` documenta
bene: **nessun test dichiara un database**, quindi il runner salta la creazione
del DB usa-e-getta e i 19 file di `tests/db/` trovano lo schema Liquibase
completo. Il primo test che dichiarerà `databases = [...]` li romperà tutti e
diciannove, in una PR che non c'entra nulla.

---

### 🟡 D10 — I registri di debito non hanno un verso

Stato al 2026-09-09, per il solo perimetro applicativo:

| Registro                                                            | Oggi                                   | Chi lo abbassa                                                                                                                                       |
| ------------------------------------------------------------------- | -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DataTable` grezza in una view                                      | **48** file (57 il 30-08, 48 il 03-08) | dichiarato, con la regola in cima ad `AGENTS.md`                                                                                                     |
| …di cui **senza** il commento di motivazione richiesto dalla regola | **34**                                 | ⛔ nessuno: la regola chiede il motivo scritto sopra l'import                                                                                         |
| File `frontend/src` senza header di licenza                         | **576 su 680** (85%)                   | ⚠️ l'hook guarda `--diff-filter=AC`: solo i file **aggiunti**. Il pregresso cala solo se riscritto                                                    |
| File tracciati senza header (filtro dell'hook, escluso `docs/`)     | **1.169 su 5.729**                     | ⭐ erano **2.042 su 5.189** il 2026-08-26: **cala davvero**                                                                                           |
| `skip_area_check = True`                                            | 81 occorrenze in 24 file               | ⚠️ `api.md` lo ammette «solo per endpoint cross-dominio»; in `core/api/` è la regola, in `anagrafiche/`, `catalogo/`, `pagamenti/`, `ui/` va guardato |
| `"count": len(...)`                                                 | 8 (D6)                                 | ⛔ nessun cancello                                                                                                                                    |
| `baseline-smoke.tsv`                                                | 2 su 16                                | ⛔ nessuno lo esegue                                                                                                                                  |
| Errori `oxlint`                                                     | 7                                      | ⛔ nessuno lo esegue                                                                                                                                  |

⭐ **La riga dell'header di licenza è l'unica fatta bene**, ed è istruttiva: cala
di 873 file in due settimane **perché l'hook non blocca il pregresso**. Un
presidio che avesse preteso tutto e subito sarebbe stato spento al primo commit
sul frontend — e allora non presidierebbe più nemmeno i casi per cui è nato. È
esattamente il criterio da applicare al cancello del frontend (D1).

⛔ **Le altre righe non hanno un verso**: nessuna dice chi la abbassa, di quanto,
entro quando. Un registro senza verso è una lista, e una lista lunga non la legge
nessuno.

---

### 🟡 D11 — Quattro app scheletro, e il debito che cresce da solo

| App Django            | File | Righe   | Test     | Cartella FE |
| --------------------- | ---- | ------- | -------- | ----------- |
| `acquisti`            | 13   | 26      | 0        | 2 file      |
| `magazzino`           | 13   | 26      | 0        | 2 file      |
| `storico`             | 13   | 26      | 0        | —           |
| `contabilita`         | 13   | 26      | 0        | 2 file      |
| `vendite` (confronto) | 248  | 115.550 | 108 file | 178 file    |

⛔ **`contabilita` è fuori perimetro per decisione** e va bene così (§4). Le altre
tre no: `acquisti` e `magazzino` hanno un **modello DB curato** — il documento
gemello (§3 D8) conta 26 tabelle e 71 CHECK su `magazzino`, 9 tabelle e 42 FK su
`acquisti` — e **zero comportamento**, su tre strati invece che su uno.

⚠️ **E l'asimmetria si aggrava da sola**, in modo che si vede meglio da qui che
dal DB: ogni decisione presa su `vendite` — envelope, capability di riga, scope
emittente, ordinamento, export, drawer autonomi, `ListaConfigurabile` — è una
decisione presa **anche** per `acquisti`, che qui non è scritta. Più cresce
`vendite`, più cresce il debito di `acquisti` senza che nessuno lo tocchi. Il
rimedio non è scriverli: è **decidere se sono un cantiere aperto o congelato, e
scriverlo**.

---

### 🟡 D12 — La superficie dei portali esiste a database e non ha porte

`PortaleAPIView` e `ShopAPIView` sono due base class documentate in `api.md` come
namespace **Attivi**. Contate le sottoclassi nel repo: **1** e **0**. Contate le
rotte: `/api/v1/portale/` ne ha **3**, `/api/v1/shop/` ne ha **3** — e sono tutte
e sei di **attivazione o registrazione**. Nessun dato di dominio.

⚠️ Il documento gemello (§2.1, 2026-09-08) conta invece, a database, **13 policy
RLS** per le tre vesti non-OPERATORE: 8 `CLIENTE_PORTALE`, 3 `SHOP_CUSTOMER`,
2 `FORNITORE_PORTALE`.

⇒ **Il perimetro è costruito, la porta no.** `api.md` lo dichiara onestamente
(«MVP dati Stage C», «catalogo/checkout Stage D»), quindi non è un difetto
nascosto: è un cantiere dichiarato. ⚠️ Va però tenuto d'occhio per una ragione
precisa — **una policy RLS che nessun endpoint esercita non è mai stata provata
dall'uso**, esattamente come il perimetro di `script.vw_giornale_entita` prima
del suo primo consumatore. Il giorno dello Stage C, quelle 13 policy vanno
considerate non collaudate.

---

### 🟠 D13 — Un building block esisteva, il punto di chiamata non l'ha cercato — e il presidio che lo direbbe non lo legge nessuno

> Trovato la sera del **2026-09-09**, lanciando i controlli appena il database è
> tornato raggiungibile. ⭐ Non è un difetto strutturale come gli altri dodici:
> è un **bug vivo**, e sta qui perché è la prova migliore di due cose che questo
> documento e il gemello affermano in astratto.

`dbops.vw_coda_lavori_da_guardare` — la vista che il gemello (§3 D8/D10) cita
come esempio di presidio che funziona e che nessuno guarda — conteneva **sei**
righe il 2026-09-09 mattina. La sera stessa ne conteneva **otto**:

|                                  |                                                                                 |
| -------------------------------- | ------------------------------------------------------------------------------- |
| Job                              | `CHIUSURA_SCADENZE`, **quattro notti consecutive** (5, 6, 7, 8 settembre)       |
| Per notte                        | due, uno per emittente (`EMITEST`, `PGTAPEF202`)                                |
| Stato                            | `ERRORE`, `tentativi 3/3`, «fallito: tentativi esauriti»                        |
| Errore, identico su tutti e otto | `ValueError: dictionary update sequence element #0 has length 1; 2 is required` |

**La causa, riprodotta in transazione con rollback** —
`apps/core/services/coda_lavori/chiusura_scadenze_handler.py:60`:

```python
esito: dict[str, Any] = dict(riga[0]) if riga and riga[0] else {}
```

`dbops.fn_apply_chiusura_scadenze()` dichiara `RETURNS jsonb` e costruisce un
oggetto JSON ben formato. Ma **il backend Django per psycopg 3 non decodifica i
`jsonb` fuori dall'ORM**: su un cursor raw quel valore arriva come **`str`**.
⇒ `dict("{\"_total\": 0, ...}")` itera i **caratteri**, e ogni carattere è una
sequenza di lunghezza 1 dove ne servono 2. Da qui, alla lettera, il messaggio.

⛔ **E il rimedio esisteva già, scritto e documentato, tre mesi prima.**
`apps/core/db/_helpers.py` contiene `coerce_jsonb_dict`, la cui docstring dice
esattamente questo — *«Coercion difensiva jsonb → dict (il driver puo'
restituire jsonb come str). Promozione regola-del-2 del clone nato in
`pratiche_repository` (2026-06-11) e replicato in `ui_admin`/`vendite`»* — e
accanto `jsonb_out`, che apre con *«Il backend Django per psycopg 3 NON decodifica
i jsonb fuori dall'ORM»*.

⭐ **Ed è l'unico punto in tutto il backend che sbaglia così**: cercata la forma
`= dict(riga[n])` su tutti i sorgenti non-test, **una sola occorrenza**, questa.
Non è un pattern diffuso: è un punto di chiamata scritto dopo l'estrazione del
building block, che non l'ha cercato.

**Le due cose che questo caso dimostra, e che valgono più del bug:**

1. ⛔ **Il catalogo dei building block è la prima difesa, e funziona solo se lo
   si apre.** Qui il BB c'era, aveva il nome giusto, e la sua docstring
   descriveva **la condizione esatta** in cui questo codice si sarebbe rotto.
2. ⛔ **Un presidio senza destinatario non presidia.** La vista si chiama
   `vw_coda_lavori_**da_guardare**`, ha fatto il suo mestiere quattro notti di
   fila, e nessuno l'ha letta: il conto è passato da 6 a 8 **mentre si scriveva
   questo documento**. È il D10 del gemello, colto sul fatto.

### ✅ Chiuso il 2026-09-09, alle 22:40 — un'ora prima del giro successivo

`chiusura_scadenze_handler.py:60` usa ora `coerce_jsonb_dict(riga[0])`.

⭐ **E il test che c'era è la parte che vale.** Esisteva già
`apps/core/tests/services/test_chiusura_scadenze_handler.py`: cinque test, ben
commentati, con in testa la nota giusta — *«Database MOCKATO: qui si prova ciò
che l'handler DECIDE»* — e la delega esplicita del binding a un guardrail su DB
vero. Era **verde mentre il job falliva da quattro notti**.

⛔ **Il difetto non era la mancanza di un test: era la forma che il mock
fingeva.** La riga finta conteneva un `dict` (`({"vendite.contratti": 4},)`); il
driver consegna una `str`. ⇒ *Un mock non sbaglia mai da solo — sbaglia quando la
forma che finge non è quella vera, e allora presidia il contrario di ciò per cui
è stato scritto.* Fra «cosa l'handler decide» e «il binding col catalogo» c'era
una terza cosa, **la forma del valore che torna**, e non la guardava nessuno.

**Provato nei tre modi che servono**, perché una riga sola merita più di un
verde:

| Prova | Esito |
| --- | --- |
| I due test nuovi (`str` e `dict`, più il JSON malformato) | ✅ 5 test OK |
| **Mutazione**: rimesso `dict(riga[0])` | ⛔ rosso, con **esattamente** `ValueError: dictionary update sequence element #0 has length 1; 2 is required` — la stessa stringa delle 8 righe in coda |
| **End-to-end** sul database vero, in transazione annullata | ✅ `chiusure` è un `dict`, nessuna eccezione |
| Suite backend completa sul DB vero | ✅ **4533 test, OK** |

⚠️ **Restano le 8 righe vecchie** in `vw_coda_lavori_da_guardare`: sono
fallimenti storici a tentativi esauriti, e non si sanano da sé. Vanno **rimesse
in coda** (`requeue/`) o **archiviate** — è una decisione operativa, non una
conseguenza della correzione. ⛔ E finché quel registro non torna a zero, la
vista continua a non poter fare il suo mestiere: una lista sempre lunga smette di
essere letta (D13-bis).

---

## 4. Cosa NON è un difetto

* ⛔ **`contabilita` vuoto su tutti e tre gli strati.** Fuori perimetro per
  decisione: se servirà sarà un aggancio a una contabilità esterna, con la forma
  dettata dal sistema di destinazione. Uno scheletro di 26 righe non è debito.
* ⛔ **Le 11 view che ereditano `APIView` nudo.** Sono tutte e sole quelle
  pre-autenticazione. Una base class autenticata lì sarebbe sbagliata.
* ⛔ **I 48 file con `DataTable` grezza, come numero.** Il difetto è che 34 non
  dicono **perché** (D10); e uno dei casi — la matrice slot/override — è un
  debito già dichiarato con la sua decisione aperta nel piano PrimeVue 5.
* ⚠️ **I 200+ file `.vue` che non usano `useI18n`.** Sono 64, e sono componenti
  di presentazione senza testo proprio. Un componente senza stringhe non ha
  bisogno di tradurne.
* ⚠️ **La suite Django veloce.** 33 secondi non sono un difetto: sono la
  conseguenza corretta della scelta «unit test mockati». Il difetto sarebbe
  crederli una copertura d'integrazione — vedi D9.
* ⚠️ **`SECRET_KEY` segnalato da `check --deploy`.** È il valore di sviluppo
  letto dall'ambiente, non una riga del repo. È una misura di **macchina** e non
  va contata.
* ⚠️ **Il chunk da 822 kB segnalato da `vite build`.** È un avviso di soglia
  predefinita su un'applicazione gestionale con code-splitting già attivo (i due
  bundle di locale sono separati, i domini sono lazy). Non è una misura di
  qualità finché nessuno ha dichiarato un budget.

---

## 5. Scorecard 2026-09-09 — pesata, non mediata

Il peso è **la conseguenza di un difetto in quell'area**, non la sua estensione.

| Area                                        | Peso    | Voto         | Perché                                                                                                                                                                                                                                                           |
| ------------------------------------------- | ------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Catena di verifica — frontend**           | 🔴 alto  | **7/10** ⬆⬆ | ✅ 2026-09-09: `ci-frontend.yaml` **ha girato in CI**, 47 s, tutti i passi verdi — `npm ci` · lint senza `--fix` · quattro guard · **18 test** · build · guard i18n. ⚠️ Non sale oltre perché la copertura è **un file su 680**: il cancello c'è, la rete no (D1, D1-d-bis) |
| **Analisi statica — backend**               | 🔴 alto  | **6,5/10** ⬆ | ✅ 2026-09-09: `ruff` (`F`+`E9`) in pre-commit e CI, registro sanato e cancello **nato a zero**. ⚠️ Resta senza **type checker**, che è la metà che vedrebbe i difetti di giuntura (D2)                                                                            |
| **Catena di verifica — backend**            | 🔴 alto  | **8/10**     | Cancello duro senza `continue-on-error`, 4.560 test verdi in CI, sette guardrail statici, il compilatore plpgsql. Manca la profondità (D9) e il ramo `--deploy` (D3)                                                                                             |
| **Contratto API pubblicato**                | 🟠 medio | **7/10** ⬆   | ✅ 2026-09-09: `securitySchemes` c'è, `security:` su tutte le 815 operazioni, `check --deploy` da 677 a 124 problemi. Restano 66 `W002`, 54 collisioni di `operationId` e il ramo `--deploy` fuori dalla CI (D3, D3-b)                                            |
| **Contratto d'errore — lato backend**       | 🟠 medio | **9/10**     | 763 codici vivi, zero senza ripiego, zero orfani, zero `%s`, classi motivate. Il pezzo migliore del backend                                                                                                                                                      |
| **Contratto d'errore — arrivo a video**     | 🟠 medio | **8/10** ⬆⬆  | ✅ 2026-09-09: `fields`, `targets` e ora anche **`hint`** arrivano a video — il toast lo rende sotto il messaggio, e sui tre codici tecnici il backend lo toglie perché lì non è la soluzione a catalogo. Le sei `ui_action` non ramificate sono **dichiarate servite** dal default, non ignorate. ⚠️ Non è 10: il canale è `execute`, e chi mostra un errore chiamando `notify.error` a mano resta fuori (D4) |
| **Perimetro e permessi (lato applicativo)** | 🟠 medio | **7,5/10**   | Catena unica, fail-closed, reset GUC incondizionato; un'area dichiarata e non a catalogo (D5), `skip_area_check` senza un registro (D10)                                                                                                                         |
| **Correttezza dei contratti di lista**      | 🟠 medio | **6/10**     | La regola sul `count` è scritta e ha un controesempio vivo sull'autocomplete più usato (D6); nessun cancello la difende                                                                                                                                          |
| **Simmetria del dominio**                   | 🟠 medio | **4/10**     | `acquisti` e `magazzino` modellati a DB e vuoti su BE e FE, senza una data (D11). Stesso voto del gemello, per lo stesso motivo                                                                                                                                  |
| **Building block — frontend**               | 🟡 basso | **8,5/10**   | 83 composable, 97 componenti, un solo punto HTTP, `bersagli` e `useDrawerChiusuraGlobale` sono lavoro di qualità; restano 34 `DataTable` senza motivo e 11 view fuori dal contratto KeepAlive                                                                    |
| **Multilingua**                             | 🟡 basso | **9/10**     | 4.697 chiavi in parità perfetta, guard in pre-commit, condotta `Accept-Language` completa. Il voto non è 10 perché il catalogo a monte è monolingue (§2.5)                                                                                                       |
| **Gestione del debito**                     | 🟡 basso | **5/10**     | Un registro che cala davvero (header licenza, −873 in due settimane) e sette che non hanno un verso (D10)                                                                                                                                                        |
| **Documentazione di contesto**              | 🟡 basso | **9/10** ⬆   | ✅ 2026-09-09: **sette righe su sette**. Lo stack **tolto** dalle tre sedi invece che aggiornato (fonte unica `frontend/package.json`, come `.python-version`), e l'ultima riga — quella su `hint` — chiusa **rendendola falsa** invece che riscrivendola (§1, D4) |

### Il giudizio, in una frase

⭐ **Il backend è costruito con lo stesso metodo del database, e si vede**: il
contratto d'errore chiuso a chiave, la catena dei permessi in una sede sola, il
reset dei GUC fail-closed, i building block estratti alla seconda occorrenza, il
99% di `# Scopo:`. È lavoro sopra la media del settore, come lo è quello del
DB.

⛔ **E il frontend, che è metà del prodotto, non aveva nessun controllo
automatico.** Non un test rotto: **nessun test**. Non un cancello permissivo:
**nessun cancello**. Le 117.000 righe che l'operatore vede tutti i giorni
arrivavano su `Tito-dev` verificate da una persona che guardava lo schermo — e i
quattro presidi scritti apposta per il frontend, buoni e verdi, li lanciava la
stessa persona quando se ne ricordava.

⚠️ **E la seconda metà del difetto era simmetrica e opposta**: il backend, che il
cancello ce l'ha, non aveva nessuno strumento che guardasse il codice **senza
eseguirlo**. 4.560 test in 33 secondi coprono i service con i repository finti;
un errore di tipo su una giuntura, un ramo morto, un import fantasma non li
vedeva nessuno.

### ✅ Il giudizio, riletto la sera del 2026-09-09

⭐ **Le due lacune erano davvero economiche, ed è la cosa più utile che questo
documento abbia prodotto**: due mezze giornate hanno portato il frontend da
**zero** controlli a cinque (`npm ci`, lint, quattro guard, build, chiavi i18n) e
il backend alla sua **prima** analisi statica, nata a registro zero. Nessuna delle
due era un cantiere: erano due cose che nessuno aveva guardato insieme.

⚠️ **Ma la frase sulla «production-readiness» non cambia**, e vale la pena dire
perché. Un cancello di *build* prova che il codice **si compila**; non prova che
faccia la cosa giusta. ⛔ **Il frontend continua a non avere un solo test**, e
`ruff --select F` vede gli import morti, non i difetti di merito. Quello che è
cambiato è che adesso esiste **un posto dove metterli** — prima non c'era, ed è
la ragione per cui non ne veniva scritto nessuno.

⚠️ Restano intere le tre ragioni del documento gemello (D1, D2, D3 di là) più la
quarta che è di qui: un prodotto la cui interfaccia non ha **nessuna prova di
comportamento** non è pronto per essere modificato da qualcuno che non sia chi
l'ha scritto — cioè non è pronto per un secondo sviluppatore, prima ancora che
per un secondo cliente.

---

## 6. Checklist, in ordine di ritorno

### 🔴 Prima di tutto il resto — accendere una luce sul frontend

* [x] **D1-a** — ✅ **fatto il 2026-09-09**, e in forma migliore: **un workflow
      suo**, `.github/workflows/ci-frontend.yaml`, invece di due righe nei
      `paths:` di `ci-validate` — che tira su Postgres, Java e Liquibase per
      cinque minuti, e a una modifica di CSS non serve un database.
* [x] **D1-b** — ✅ **fatto**: i 7 errori sanati **prima** di accendere, i
      `--fix` tolti da `lint:oxlint` e `lint:eslint`, e la comodità spostata su
      uno script `fix` a parte — che di proposito **non** si chiama `lint:*`,
      perché `run-s lint:*` lo tirerebbe dentro e il cancello tornerebbe a
      riscrivere i sorgenti.
* [x] **D1-c** — ✅ **fatto**: raccolti sotto `npm run guards` (`run-s guard:*`)
      e lanciati dal job. ⭐ Raccoglierli in uno script invece di quattro righe di
      YAML significa che chi ne aggiunge un quinto lo trova in CI **senza toccare
      il workflow**.
* [x] **D1-d (metà)** — ✅ **fatto il 2026-09-09**: `vitest` (solo lui, ok di
      Tid), 18 test su `useApiHandler`, nel job prima della build, e **provati
      per mutazione** — quattro mutazioni del sorgente, quattro rossi. ⭐ Il
      valore non è la copertura: è che da qui in poi **esiste un posto dove
      scrivere il prossimo**, che prima non c'era ed è la ragione per cui non ne
      veniva scritto nessuno.
* [ ] **D1-d-bis** — il primo test di **componente**, su `ListaConfigurabile`
      (l'unico modo di montare una lista, 63 file la usano). ⛔ Vuole due
      pacchetti in più — `@vue/test-utils` e `jsdom` — e vanno aggiunti **quel
      giorno**, non prima.
* [ ] **D1-f** — ⚠️ trovato installando `vitest`: `npm audit` riporta **2
      vulnerabilità (1 alta)** su `browserslist` / `baseline-browser-mapping`,
      **preesistenti** — arrivano da `vite-plugin-vue-devtools` → babel ed erano
      già nel lock — e di sola **build**: non entrano nel bundle. ⛔ Il difetto
      non è la vulnerabilità: è che **nessuno lancia mai `npm audit`**, quindi
      non c'era modo di saperlo. Decidere se metterlo nel job, e con quale
      soglia: un `--audit-level=high` che blocca su una dipendenza di build va
      valutato, non dato per scontato.

### 🔴 E una sul backend

* [x] **D2-a** — ✅ **fatto**, con una correzione a questa stessa riga: la
      configurazione minima **non è `E,F,I`** ma **`F,E9`**. Misurato prima di
      accendere: `E` da sola apre **5.051** rilievi, di cui 4.853 `E501` di sola
      lunghezza riga. Con `F,E9` il registro era **136**, sanato per intero
      (129 con `--fix`, 7 a mano) ⇒ il cancello nasce a **zero** e non è servito
      il ripiego sul `--diff-filter=AC`. Regole in `ruff.toml`, non negli
      argomenti dell'hook.
* [ ] **D2-b** — decidere **se** il progetto vuole un type checker. Se sì,
      `python.analysis.typeCheckingMode` nel repo o `mypy` con `--follow-imports=skip`
      sui soli `apps/*/services/`; se no, **togliere da `AGENTS.md`** la riga
      sull'`assert` «per aiutare il type checker», che oggi chiede un lavoro a
      beneficio di nessuno.

### 🟠 Il contratto verso chi consuma

* [x] **D3-a** — ✅ **fatto**: `apps/core/api/openapi_extensions.py`, registrata
      per import in `CoreConfig.ready()`. 607 avvisi → **0**, `check --deploy` da
      677 a **124**, `security:` su tutte le 815 operazioni.
* [ ] **D3-b** — portare `manage.py check --deploy` in CI, **dopo** aver sanato
      D3-a e il `mail.E001` (che in CI è un backend di posta di sviluppo:
      va impostato quello giusto nell'ambiente della CI, non silenziato).
      Restano i 66 `W002`: quelli sono un registro, e va aperto con un numero.
* [ ] **D3-c** — `SECURE_HSTS_SECONDS` e `SECURE_SSL_REDIRECT` nel ramo non-debug
      di `settings.py`, e **decidere** sulla CSP: o si aggiunge, o si scrive
      perché no. Oggi la difesa contro l'XSS è «non c'è superficie», ed è vero,
      ma non è presidiato da niente.
* [x] **D4** — ✅ **fatto il 2026-09-09**: `hint` reso a video in **un** posto —
      `useApiHandler` → `soluzione` → `detail` del toast, sotto il messaggio. Con
      lui la condizione che lo rendeva mostrabile (`_apply_policy` lo toglie sui
      tre codici tecnici, dove quel canale porta il testo di PostgreSQL e non la
      soluzione a catalogo) e **7 test** nuovi lato BE, **5** lato FE. Le sei
      `ui_action` non ramificate sono **dichiarate servite** dal default
      (decisione di Tid): la tabella per valore è in `api.md`.

### 🟠 La sostanza

* [ ] **D5** — `ai_assistant` a catalogo in `config.aree_funzionali` (brief al
      team DB), **oppure** `AdminAPIView` se l'assistente è admin-only per
      decisione. ⚠️ Da fare prima di accendere `AI_ENABLED`, non dopo.
* [ ] **D6** — separare i due `_build_results_response`: quello dei **lookup**
      (con `limit`) deve dire se ha troncato — o restituire il `count(*)` vero,
      o un flag `troncato`. Quello delle **collezioni figlie** resta com'è, con
      il commento che dice perché lì `len()` è legittimo.
* [ ] **D7** — per ciascuno degli otto endpoint senza consumatore rispondere per
      iscritto a *«questa la deve poter usare una persona?»*. Il primo della
      lista è `/core/email/log/`, che oggi lascia l'operatore senza il registro
      delle proprie mail mentre l'amministratore ce l'ha.
* [ ] **D8** — portare in `onActivated` (idempotente) il caricamento delle
      **undici** view di `amministrazione/views/`. ⚠️ Non spostare: aggiungere,
      e rendere il caricamento ripetibile.
* [ ] **D9-a** — gli smoke in CI. Sono già isolati in transazione con rollback,
      il registro ha **due** righe: è il cancello più facile del repo dopo
      D1-a. ⚠️ Prima va corretto lo smoke che esce `0` su «ESITO: FALLITO».
* [ ] **D9-b** — correggere `AGENTS.md` §Regole test: `unittest.TestCase` e
      `SimpleTestCase` **non sono equivalenti** — solo la seconda impedisce a un
      test di parlare col database vero. Chi scrive un test nuovo deve saperlo.

### 🟡 Ordine e verità dei documenti

* [ ] **D10** — dare un **verso** ai sette registri senza (chi lo abbassa, di
      quanto, entro quando) o dichiararli congelati con il motivo. Il modello è
      la riga dell'header di licenza, che cala perché non blocca il pregresso.
* [ ] **D11** — decidere se `acquisti` e `magazzino` sono un cantiere **aperto o
      congelato**, e scriverlo nei documenti di contesto. È la stessa voce del
      documento gemello: la decisione è una sola per tutti e tre gli strati.
* [x] **§1-a** — ✅ **fatto il 2026-09-09**: lo stack **tolto** da tutti e tre i
      documenti, non aggiornato. `AGENTS.md` §Frontend, `PROJECT_CONTEXT.md`
      §Stack Tecnico e `frontend-standards.md` §Stack rimandano a
      `frontend/package.json`; in quest'ultimo la colonna «Versione» è sparita e
      resta quella «Ruolo». ⚠️ Sanato anche il residuo fuori tabella
      (`frontend-standards.md` §Tab-View, «Siamo su PrimeVue 4.5»), riscritto su
      **quale API si usa** invece che su quale versione.
* [x] **§1-b** — ✅ **fatto**: `PROJECT_CONTEXT.md` elenca ora tutte e **17** le
      app, marcando i quattro scheletri; `ai_assistant` entra nell'inventario
      endpoint di `api.md` **con il difetto D5 scritto accanto**.
      ⚠️ **Resta aperto** il suo ingresso nei due cataloghi BB: quello lo si fa
      quando i tool diventano building block riusabili, non prima.
* [x] **§1-c** — ✅ **fatto**: `ui_action` ha il terzo aggiornamento datato (un
      consumatore su sette valori, con il conto degli altri sei); §Test è una
      tabella a **tre** livelli che dichiara anche quali girano in CI; aggiunta
      la nota che `unittest.TestCase` e `SimpleTestCase` **non presidiano la
      stessa cosa**.
* [x] **D1-e** — ✅ **fatto il 2026-09-09**, e non con `sys.argv` come sorgente
      primaria: in modalità range l'elenco viene da
      `git diff --diff-filter=AC <from> <to>`, così restano i soli file
      **aggiunti** e il cricchetto non diventa il blocco totale. `sys.argv` si
      usa solo per intersecare. Provato prima/dopo sulla forma esatta della CI
      (rosso dove prima taceva) e sul percorso del commit (invariato), più
      `verbose: true` perché il verde dica **su cosa**.
* [x] **D13** — ✅ **fatto il 2026-09-09**: `coerce_jsonb_dict(riga[0])`, più i
      test sulla **forma** del valore (`str`, `dict`, JSON malformato). Provato
      per mutazione — col codice vecchio i test riproducono esattamente l'errore
      delle 8 righe in coda — e end-to-end sul database vero.
* [x] **D13-ter** — ✅ **fatto da Tid il 2026-09-09 alle 21:25 UTC**: le otto
      righe archiviate in un solo gesto (stesso `archiviato_il`, endpoint di
      collezione). `vw_coda_lavori_da_guardare` è a **zero** — `ERRORE` vive = 0,
      archiviate = 12.
      ⭐ **E il valore non è la pulizia**: con otto righe vecchie dentro, una riga
      nuova era indistinguibile dal fondo. Da adesso **qualunque riga significa
      «stanotte è fallito qualcosa»**. Il presidio ha riacquistato la proprietà
      per cui era stato scritto, e che non aveva.
      ⚠️ Ed è la condizione che rende leggibile la prova di D13: alle 22:05 UTC
      il produttore accoda due lavori e il drenatore li prende con la correzione
      già sul disco (il timer gira dal working tree, verificato). Domattina la
      vista dirà **0** o **2**: nessuna terza lettura possibile.
* [~] **D13-bis** — 🔵 **brief scritto il 2026-09-09, in attesa del DB**:
      [brief-db-un-destinatario-per-i-presidi.md](brief-db-un-destinatario-per-i-presidi.md).
      ⛔ Non si poteva fare tutto lato backend, e il perché è la parte utile:
      delle 31 viste `dbops.vw_*`, **14 non sono vuote ma quasi tutte sono
      inventari** — un digest ingenuo si aprirebbe con 2.035 righe di
      `vw_trigger_functions`. Servono tre nature distinte (`ZERO` · `SOGLIA` ·
      `INVENTARIO`) e **nessuna è deducibile dal nome**. ⛔ Metterle in un elenco
      Python sarebbe una seconda sorgente di verità che diverge alla
      trentaduesima vista: la classificazione è **dato**, come
      `ui.lista_definizione`. ⇒ Chiesti al DB: il catalogo `dbops.presidi` e una
      riga in `dbops.processi` (`classe=MANUTENZIONE`, quindi senza identità né
      emittente). Il backend riparte lo stesso giorno: §5 del brief.
* [ ] **INFRA-1** — 🔴 **datato e ricorrente**: la chiave del nodo Tailscale di
      `dbdev` è scaduta il **2026-09-09 alle 10:51 UTC**, e con essa il server
      backend di sviluppo ha smesso di raggiungere il database — gunicorn fermo
      in `SYN-SENT`, nessun avviso da nessuna parte. ⚠️ `backend-dev` scade il
      **2026-09-19**: lo stesso blocco arriverà dall'altro lato fra pochi giorni.
      ⇒ Su due nodi *server* il rimedio non è rinnovare a ogni scadenza ma
      **disabilitare la scadenza della chiave** dalla admin console. ⭐ Vale la
      pena tenerlo in questa lista anche se non è codice: è il caso in cui il
      presidio non manca perché è difficile da scrivere, ma perché **nessuno
      guarda** se l'applicazione di sviluppo è viva (D10 del gemello).
* [ ] **§1-d** — ⚠️ **aperto, e nato togliendo**: `AGENTS.md` §Regole test offre
      `unittest.TestCase` e `SimpleTestCase` come alternative. La differenza è
      ora scritta in `api.md`; va scritta **anche lì**, che è il documento dove
      si va a cercarla scrivendo un test (è il D9-b della lista sopra).

---

## 7. Cosa non ho potuto misurare, e perché lo scrivo

⭐ Questa sezione esiste per la stessa ragione per cui il documento gemello ha
dovuto imparare a far fallire uno strumento che non poteva misurare: **una misura
mancata, taciuta, diventa una misura implicita**.

| Cosa                                                            | Perché no                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| ~~La suite Django **su questa macchina**~~                      | ✅ **PRESA la sera del 2026-09-09**, appena riautorizzato il nodo. ⛔ La causa del blocco non era Postgres — era la chiave Tailscale di `dbdev`, scaduta quella mattina alle **10:51 UTC** (`Expired: True`, `LastHandshake` mai, nessun indirizzo corrente), mentre `backend-dev` era sano. Riprovato a DB «su» dava ancora buca, perché il blocco stava a monte del servizio. ⭐ Rimedio applicato da Tid nella forma giusta: `KeyExpiry: None`, cioè scadenza **disabilitata** e non rinnovata — su un nodo server è la differenza fra chiudere il difetto e riprogrammarlo. **Esito della misura in §2.1.** ⭐ E la diagnosi è valsa più della misura: mentre il link era giù il **gunicorn di sviluppo** era fermo in `SYN-SENT` — l'applicazione era morta e non lo diceva nessuno (D13, e D10 del gemello: *guardare non è di nessuno*) |
| Il censimento **completo** degli endpoint senza consumatore     | Uno strumento testuale non lo sa fare, e la ragione è una buona proprietà del codice: le famiglie cross-dominio (`/passaggi/`, `/note/`, `/indirizzi/`, `/documenti/`, `/situazione-merce/`, `/componenti/`) sono chiamate con il **dominio come parametro**, esattamente come `build_passaggi_view` e `make_note_views` le costruiscono lato backend. Un confronto ingenuo le conta tutte come morte (145) o nessuna (1). Gli **otto** di D7 sono il residuo che ho verificato uno per uno; è un **limite inferiore**                                                                                                                                                                                                                                                                                                                     |
| Quanto della suite sia davvero *coperto* e non solo *nominato*  | Non esiste `coverage` nel progetto (nessuna dipendenza, nessuna configurazione). Il numero di test è un limite superiore alla copertura, non una misura                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| Se i 34 `DataTable` senza motivazione siano eccezioni legittime | Richiede di leggere 34 componenti e decidere caso per caso: è il lavoro di D10, non di una misura                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |

---

## 8. La classifica per ritorno — minimo sforzo, massimo effetto

> Aggiunta il **2026-09-09**. La checklist di §6 è ordinata **per area**; questa è
> ordinata **per rapporto fra sforzo e conseguenza**, ed è la lista con cui si
> decide cosa fare lunedì mattina. Due misure prese apposta per compilarla hanno
> **spostato l'ordine** rispetto a §6, ed è la ragione per cui vale la pena
> tenerla separata invece di riordinare quella.

### Le due misure che hanno cambiato la classifica

| Misura                                               | Esito                                                                                                                                                                                                                       | Effetto sull'ordine                                                                                            |
| ---------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Il registro che aprirebbe `ruff` sul backend         | `--select F`: **136 rilievi, 129 auto-correggibili**, di cui **126 import morti**. ⛔ `--select E` da solo ne aggiunge **4853**, quasi tutti `E501` (lunghezza riga) su un progetto che una lunghezza dichiarata non ce l'ha | ⬆ **D2-a promosso**: non è un cantiere, è un pomeriggio — a condizione di **non** selezionare `E`              |
| Se gli smoke reggano un DB di CI ricostruito da zero | ⛔ **No.** In tutti e sedici i `SELECT … LIMIT 1` sui dati esistenti superano di molto gli `INSERT`, e tutti hanno guard `SENZA_MATERIA`                                                                                     | ⬇ **D9-a declassato**: su un DB vuoto il cancello nascerebbe **verde per sottrazione**, cioè peggio di assente |

## 100 SI PARTE DA QUI 

### 🥇 Il primo pomeriggio — ~2,5 ore, e cambia tre categorie

> ✅ **Eseguiti tutti e cinque il 2026-09-09**, su autorizzazione di Tid. Gli
> esiti sono nelle colonne «Cosa ha comprato» e nei blocchi «Com'è finita» di
> §3 D1, D2 e D3.

| #     | Cosa                                                           | Sforzo             | Cosa ha comprato                                                                                                                                                                | Voce |     |
| ----- | -------------------------------------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | --- |
| **1** | Cancello di build del frontend                                 | ~30 min            | Da **zero cancelli a uno** su 117k righe. ⭐ Fatto come **workflow suo** (`ci-frontend.yaml`) e non nei `paths:` di `ci-validate`: un CSS non ha bisogno di Postgres e Liquibase | D1-a | ✅   |
| **2** | I quattro guard FE nello stesso job                            | ~10 min            | Raccolti in `npm run guards`: chi ne aggiunge un quinto lo trova in CI **senza toccare il workflow**                                                                            | D1-c | ✅   |
| **3** | `ruff` (`F`+`E9`, ⛔ **non** `E`) in pre-commit + CI            | ~1 h               | La **prima** analisi statica su 258k righe. 136 rilievi sanati (129 `--fix` + 7 a mano) ⇒ cancello **nato a zero**                                                              | D2-a | ✅   |
| **4** | `OpenApiAuthenticationExtension` per `JwtAuditAuthentication`  | ~30 min, ~20 righe | `check --deploy` da **677 a 124**; `securityScheme` presente; `security:` su tutte le 815 operazioni                                                                            | D3-a | ✅   |
| **5** | 7 errori `oxlint` sanati e `--fix` tolti dagli script `lint:*` | ~20 min            | `npm run lint` da **formattatore** a **cancello**; la comodità su `npm run fix`, che di proposito non si chiama `lint:*`                                                        | D1-b | ✅   |

✅✅ **E tutti e cinque hanno girato in CI la sera del 2026-09-09** (merge #1547
su `Tito-dev`): `CI-Frontend` verde in 47 s con tutti i passi, e nel passo
`pre-commit` di `CI-Validate` sia `ruff check ... Passed` sia l'hook della
licenza che dichiara **3 file nuovi controllati**. ⇒ La riserva scritta poche ore
prima — *«scritti, non attivi: un cancello che non ha mai girato non è ancora un
cancello»* — è **caduta**.

⭐ **Due cose imparate eseguendo, che la stima non conteneva:**

1. **La configurazione minima di `ruff` non era `E,F,I`** come avevo scritto in
   §6. Misurata prima di accendere: `E` da sola vale **5.051** rilievi, il 96%
   dei quali `E501`. La riga giusta è `F,E9`. *La stima diceva «minima»; solo la
   misura ha detto **quanto**.*
2. **Sette `F841` non erano auto-correggibili per una buona ragione**: in quattro,
   la **chiamata** era ciò che l'asserzione verificava e solo il binding era
   inutile. Uno strumento non poteva distinguerli da tre assegnazioni morte —
   ed è esattamente il caso in cui `--unsafe-fixes` avrebbe rotto un test in
   silenzio.

⭐ **Perché questa e non un'altra**: 1 e 3 sono gli unici due item dell'intera
lista che portano una categoria **da 0 a 1**. Tutto il resto migliora qualcosa
che già esiste. E 2 e 5 costano quasi nulla **perché** fatti insieme all'1.

⭐ **Se se ne potesse fare uno solo: il numero 1.** Mezz'ora, e il frontend smette
di essere l'unica metà del prodotto che nessuna macchina guarda.

### 🥈 Poi — ore, ed è quello che vede l'operatore

> ✅ **Il numero 6 è stato eseguito il 2026-09-09**, su indicazione di Tid.
> L'esito è nel blocco «Com'è finita» di §3 D4. ⭐ La stima diceva ~1 h e ha
> retto, ma il pezzo che non conteneva stava nel **backend**: mostrare il campo
> senza il filtro sui tre codici tecnici avrebbe chiuso D4 introducendo un
> difetto — un'istruzione di PostgreSQL, in inglese, sotto un messaggio che la
> policy ha già sostituito.

| #   | Cosa                                                                                | Sforzo | Cosa compra                                                                                                                                           | Voce |
| --- | ----------------------------------------------------------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ---- |
| 6   | ✅ `hint` a video, in **un** posto (sotto il messaggio d'errore)                    | ~1 h   | ✅ **fatto il 2026-09-09.** L'unica frase che dice all'operatore **cosa fare adesso**: il DB la scriveva, il BE la trasportava, lo schermo la buttava | D4   |
| 7   | `onActivated` sulle 11 view di `amministrazione/`                                   | ~2 h   | Modifica meccanica identica ×11. Toglie un difetto **intermittente** — che per via del `:max="10"` è peggio di uno costante, perché non viene creduto | D8   |
| 8   | Separare i due `_build_results_response`: lookup (con `limit`) da collezioni figlie | ~1 h   | Toglie il controesempio vivo sull'**autocomplete articoli**, la ricerca più usata dell'applicazione                                                   | D6   |

### 🥉 Costano poco, ma il ritorno non dipende da chi scrive

| #   | Cosa                                                            | Perché sta qui                                                                                                                                                                                                                          |
| --- | --------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 9   | `ai_assistant` a catalogo in `config.aree_funzionali`           | 20 min di brief, ma passa dal **team DB** e la funzione è dietro un flag spento. Va fatto **prima** di accendere `AI_ENABLED`, non adesso                                                                                               |
| 10  | `SECURE_HSTS_SECONDS` / `SECURE_SSL_REDIRECT`                   | 10 min di `settings.py`, ma l'effetto lo decide il **reverse proxy**: da concordare con chi gestisce nginx                                                                                                                              |
| 11  | Gli otto endpoint senza consumatore                             | Lo sforzo non è scrivere: è **decidere**. Il primo è `/core/email/log/`, che oggi lascia l'operatore senza il registro delle proprie mail mentre l'amministratore ce l'ha                                                               |
| 12  | *Disable key expiry* sui nodi Tailscale `dbdev` e `backend-dev` | Non è codice, ed è qui perché costa **due click**: il 2026-09-09 la scadenza di `dbdev` ha fermato il database di sviluppo e con esso l'applicazione, senza che niente lo segnalasse. `backend-dev` scade il **19 settembre** (INFRA-1) |

### ⛔ Sembrano facili e non lo sono — e questa è la parte che vale

* **Smoke in CI (D9-a).** Misurato il 2026-09-09: tutti e sedici cercano i
  soggetti nei **dati esistenti** e dichiarano `SENZA_MATERIA` quando non li
  trovano. Su un database di CI ricostruito da zero uscirebbero quasi tutti senza
  materia ⇒ il cancello nascerebbe **verde per sottrazione**. Prima serve che si
  fabbrichino i soggetti, oppure un DB di CI popolato: è un cantiere, non una
  riga di YAML.
* **`manage.py check --deploy` in CI (D3-b).** Chiuso il punto 4, restano
  **66 `W002`** più `mail.E001`. Non è configurazione: è aprire un registro da 66
  e dargli un verso.
* **I test frontend (D1-d).** ✅ La prima metà è fatta il 2026-09-09 (`vitest`,
  18 test su `useApiHandler`, provati per mutazione) e la previsione ha retto:
  il *primo* test costa poco. ⚠️ **La seconda metà resta il cantiere**: il test
  di componente vuole `@vue/test-utils` + `jsdom`, e soprattutto vuole che
  qualcuno decida **cosa** un test di `ListaConfigurabile` deve asserire — che è
  la parte che non si compra con un pacchetto.
* **`acquisti` / `magazzino` (D11).** Sta qui per un motivo opposto: nella colonna
  «sforzo» è la voce **più economica di tutte** — una riga — e non è una cosa da
  *fare*, è una cosa da **dire**. Un dominio a metà senza una data è il debito che
  cresce da solo.

---

*Valutazione 2026-09-09 — perimetro backend + frontend. Le misure sono letture di
struttura sul repo al commit `c1f9e571e` (branch `dev/backend-tid`), sullo schema
OpenAPI generato da quel commit, sui due workflow di CI e sull'esito di
`manage.py check --deploy`. L'unico dato di comportamento (§3 D6) è usato come
controesempio. Lo strato DB è valutato separatamente in
[migliorie-generali-da-test-valutazione.md](migliorie-generali-da-test-valutazione.md),
al 2026-09-08.*
