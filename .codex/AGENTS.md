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

| Cosa si legge                                                                                                                                  | Che natura ha                                 | Decide?                       |
| ---------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- | ----------------------------- |
| Nullabilita' di una colonna, `CHECK`, chiavi, FK, RLS, GRANT, volatilita' e corpo di una funzione, seed in `80_data`, contratto di un endpoint | **contratto**: e' il progetto, scritto        | ✅ si' — e' la sorgente giusta |
| `count(*)`, «zero righe in quello stato», «N su M hanno il padre valorizzato», distribuzione dei valori                                        | **istantanea**: la fotografia di una macchina | ⛔ no                          |

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

## ⭐ Regola del 2 — alla seconda copia si estrae un building block

Vale per DB, backend e frontend. È il criterio con cui nascono i building block
(BB) che i due cataloghi elencano
([backend](../docs/it/dev/backend/catalogo-building-block-backend.md),
[frontend](../docs/it/dev/frontend/catalogo-building-block-frontend.md)).

* **La prima occorrenza** di una logica resta **dove serve**, scritta sul posto.
  Un BB con un solo consumatore non centralizza niente: sposta il codice e
  costringe chi legge ad aprire un altro file.
* **Alla seconda occorrenza** la logica si **estrae** in un BB condiviso, nella
  sede comune (`apps/core/…` lato BE, `src/core/…` lato FE, lo schema `script`
  o `dbops` lato DB), e si **registra nel catalogo** nello stesso giro.
* ⛔ **Le copie si ritirano nello STESSO giro dell'estrazione, non «dopo».** Un
  BB accanto alle copie che doveva sostituire è una terza versione della stessa
  logica, non una sede.
* ⭐ **Il criterio è il SIGNIFICATO, non il testo.** Due righe uguali che dicono
  cose diverse non sono una copia; due righe diverse che dicono la stessa cosa
  lo sono. Il rischio che la regola previene è la **divergenza**: due copie
  della stessa regola prima o poi rispondono in due modi diversi, senza che
  nessun test se ne accorga.
* Prima di scrivere, **si cerca nel catalogo**: la seconda occorrenza spesso è
  la propria, e la prima esiste già. Lato BE/FE si parte dall'**indice** del
  catalogo (`indice-building-block-*.md`, accanto a ciascun catalogo), che si
  legge per intero; è generato da `scripts/gen_indice_bb.py` e si rigenera
  nello stesso giro in cui si tocca il catalogo.
* Un'estrazione che tocca più domini si concorda con Tid («ok Tid» nel catalogo).

Esempi applicati: `frontend-standards.md` §«Dove vive il NOME di un'icona»
(la regola applicata al significato) e le voci «regola del 2» dei due cataloghi.

## ⏭️ Ogni brief dice in cima chi riparte

Vale per ogni brief e piano in `docs/it/dev/work-in-progress/` (DB, BE, FE).
Chi lo apre deve sapere **a chi tocca** senza leggerlo tutto.

* Subito sotto il titolo c'è il blocco **«⏭️ Chi riparte — aggiornato al
  AAAA-MM-GG»**: una riga che risponde da sola («Riparte: …»), poi una tabella
  `# | Chi | Che cosa | Dove | Aspetta`, un passo per riga, fino
  all'archiviazione. In fondo: le **decisioni aperte di Tid** (o «nessuna») e
  se il lavoro fatto è ancora da committare.
* **Si aggiorna nello stesso momento** in cui si chiude un giro o Tid prende
  una decisione, insieme alla data. Un blocco con la data vecchia è peggio di
  nessun blocco: dice a qualcuno che tocca a lui quando non è vero.
* Il blocco dice **chi** e **dove**: il dettaglio resta nella sua sezione, non
  si ricopia qui.

Esempio:
[brief-db-indirizzi-documento-seguono-il-cliente](../docs/it/dev/work-done/brief-db-indirizzi-documento-seguono-il-cliente.md).

## ⛔ Un tema, un brief — prima di aprirne uno si cercano i vicini

Vale per DB, backend e frontend (Tid, 2026-10-21). Due brief aperti sullo stesso tema, o sugli
stessi oggetti, si pestano i piedi: riscrivono la stessa funzione per ragioni diverse, a pochi
giorni di distanza, e ognuno lascia all'altro un pezzo da rifare.

* **Prima di aprire un brief** si cercano in `docs/it/dev/work-in-progress/` (brief, piani,
  analisi) quelli che toccano **lo stesso tema** o **gli stessi oggetti** (tabelle, funzioni,
  documenti, endpoint), anche se il titolo parla d'altro.
* Se uno copre il tema, o un lavoro **complementare** sugli stessi oggetti, il lavoro nuovo va
  **lì**, come sezione o giro in più, e non in un brief nuovo. Se i due vanno fusi, lo decide Tid.
* Un brief nuovo dichiara in testata **«Brief vicini verificati»**: quelli trovati e perché non
  bastano, oppure «nessuno».
* Un tema che tocca **tutti i documenti di una famiglia** (tutti i documenti di vendita, tutti
  quelli di magazzino…) non si apre senza l'ok esplicito di Tid.
* Prima di proporre un cambio di **modello**, si cerca la decisione esistente (brief in
  `work-done/`, guide, `git log -S`): la proposta dice se è nuova, se completa una decisione
  presa o se ne **revoca** una, citandola con la data.

## Dove sta cosa

AGENTS.md tiene solo le regole **trasversali**. Il dettaglio di ogni materia sta
in **un** documento, e si legge lì: una regola ricopiata qui diverge dalla sua
sede al primo aggiornamento, e allora questo file diventa fuorviante.

| Materia | Documento |
| --- | --- |
| Architettura, stato, priorità aperte | [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) |
| Metodo di sviluppo (anelli, ordine di costruzione) | `docs/it/sviluppo-concentrico.md`, `docs/it/mappa-concentrica.md` |
| Backend: view, service, repository, errori, **test Django e smoke** | [api.md](../docs/it/dev/api.md), [catalogo BB backend](../docs/it/dev/backend/catalogo-building-block-backend.md) |
| Frontend: componenti, liste, CSS, i18n, build | [frontend-standards.md](../docs/it/dev/frontend/frontend-standards.md), [catalogo BB frontend](../docs/it/dev/frontend/catalogo-building-block-frontend.md) |
| SQL: naming, chiavi, audit, indici, RLS, divieti dei changeSet (§11), prestazioni (§13) | [linee-guida-sql.md](../docs/it/linee-guida-sql.md); il metodo in [Un database che resta veloce](../docs/it/guide/database-che-resta-veloce.md) |
| Trigger | [linee-guida-trigger.md](../docs/it/linee-guida-trigger.md) |
| Liquibase: struttura, master, naming dei file | [liquibase-setup-workflow.md](../docs/it/liquibase-setup-workflow.md) |
| Sicurezza e qualità statica: strumenti (ruff, mypy, gitleaks, audit, `check --deploy`), segreti e `.env`, mappa dei presidi a runtime | [sicurezza-e-qualita-statica.md](../docs/it/dev/sicurezza-e-qualita-statica.md) |
| Qualità BE/FE nel tempo: lezioni, indicatori (`scripts/indicatori-qualita-be-fe.sh`), scorecard pesata | [qualita-be-fe-indicatori.md](../docs/it/dev/qualita-be-fe-indicatori.md); il punto d'incontro con il DB è la mappa concentrica §4 |
| Qualità del database nel tempo: lezioni, indicatori (`scripts/indicatori-qualita-db.sh`, `--catalogo` per dbdev), scorecard pesata | [qualita-db-indicatori.md](../docs/it/dev/qualita-db-indicatori.md); il gemello applicativo è qualita-be-fe-indicatori |
| Codici e messaggi di errore | [Messaggi di Errore e Generazione Log](../docs/it/guide/Messaggi-di-Errore-e-Generazione-Log.md) |
| pgTAP: template, preambolo, baseline, CI | [pgtap-come-si-scrive-un-test](../docs/it/guide/pgtap-come-si-scrive-un-test.md) |
| Guide, pagine `manual/`, build della doc | [standard-guide.md](../docs/it/dev/standard-guide.md) |

## Progetto

- ERP open-source AGPL v3 con doppia licenza (commerciale per chi la acquista; contributi esterni solo con [CLA](../CLA.md)). **DB-first**: la logica di business sta in PostgreSQL;
  Django orchestra ed espone le API; Vue fa solo presentazione.
- Struttura: `backend/`, `frontend/`, migrazioni DB in `db/changelog/migrations_v2/`, pgTAP in `db/pgtap/`.
- Lingua: it-IT per documentazione e commenti (Python, SQL, JS).
- Stack: Python + Django, PostgreSQL 18, Liquibase 5, pgTAP, Vue 3.
  ⛔ **Le versioni non si ricopiano nei documenti**: si leggono dalla fonte.
  *Un numero scritto in due posti ne ha sempre uno stantio, e quello senza
  presidio è il documento.*

| Cosa | Fonte unica |
| --- | --- |
| Python | `.python-version` (la leggono CI e `Dockerfile`) |
| Dipendenze backend | `backend/requirements.in`; il lock `backend/requirements.txt` si rigenera con `pip-compile backend/requirements.in --output-file backend/requirements.txt` |
| Strumenti di sviluppo del backend (mypy e stub) | `backend/requirements-dev.in` → `requirements-dev.txt`, vincolato al lock del backend; stessa venv, **fuori** dall'immagine Docker. I due lock li aggiorna insieme `backend/scripts/update-venv.sh` |
| Strumenti dev e doc | `requirements.txt` in radice (`scripts/update-venv.sh`) |
| Frontend e Node | `frontend/package.json` (`engines.node`, via nvm) |

- ⛔ **Nessuna dipendenza nuova** (Python o npm) senza conferma dell'utente.
- **Header di licenza sui file nuovi** (`.py`, `.js`, `.vue`, `.yaml`), dai
  template in `templates/`. Lo presidia `scripts/check_license.py` (pre-commit)
  sui file aggiunti. Dettaglio: api.md e frontend-standards.

## Ambiente e branch

- Due server: uno PostgreSQL, uno backend (Django, via VSCode SSH).
- Branch di lavoro `dev/db-tid` (DB) e `dev/backend-tid` (backend) → `Tito-dev`
  (integrazione) → `main`.

## Workflow Safety

- ⛔ **Nessuna migrazione DB senza conferma esplicita per QUEL comando.**
  `scripts/guardrail_no_db_migrate.py`, hook `PreToolUse` su Bash in
  `.claude/settings.json`, **blocca** `liquibase update` / `rollback` /
  `changelogSync` e `make db-migrate|db-ci-apply|db-setup`. Restano liberi
  `status`, `validate`, `updateSQL` (che non applica) e i pgTAP, che girano in
  transazione.
  ⚠️ «procedi», «vai avanti», «fai tutto il possibile» **non** autorizzano una
  migrazione: autorizzano il lavoro, non l'applicazione. Non si disattiva l'hook
  per far passare un comando.
- Niente comandi distruttivi senza approvazione esplicita.
- **Bug di dati in sviluppo**: prima di scrivere un fix software per dati
  sbagliati, chiedere se è più veloce correggerli a mano. Un fix per un problema
  di dati lascia codice che poi va tolto.

## Database e Liquibase — le regole che si rompono solo in CI

- Lavoro nuovo solo in `db/changelog/migrations_v2/`, file `.yaml`, un changeSet
  per file, `logicalFilePath` sempre.
- ⛔ **Mai modificare un changelog già mergiato o pushato**: si rompe la
  catena dei checksum. Per cambiare una funzione o un trigger si crea un file
  nuovo con numerazione successiva.
- ⛔ **Il DDL e il corpo di un oggetto esistente si prendono dalla doc
  auto-generata** (`docs/it/dbzero/<schema>/…`), mai da uno YAML: ce ne sono
  spesso cinque o sei per lo stesso oggetto, e ripartire da uno vecchio fa
  regredire in silenzio le revisioni intermedie.

La pipeline invoca Liquibase **due volte** su un database ricostruito da zero
(`!provision`, poi `ci_apply`), e ogni regola qui sotto passa sul DB di sviluppo
e muore in CI. Il perché e i casi reali sono in
[linee-guida-sql.md §11](../docs/it/linee-guida-sql.md):

| Divieto | § | Presidio CI |
| --- | --- | --- |
| `runOnChange: true` in `00_schema`/`20_code` (e `validCheckSums` al plurale) | 11.1 | `guardrail_run_on_change.py` |
| cambiare un dato di `80_data` con un `UPDATE` invece che dal CSV | 11.2 | — |
| una `preCondition` di `00_schema`/`20_code`/`70_dati_sistema` sul contenuto di `80_data` | 11.4 | `guardrail_precondition_seed.py` |
| DDL o `preCondition` su un trigger generato da `ci_apply` | 11.5 | `guardrail_ddl_su_trigger_automazione.py` |
| `GRANT` a un ruolo batch in un changeSet | 11.6 | `guardrail_grant_ruolo_batch.py` |
| un seed di macchina non dichiarato (`context: dati_macchina`) | 11.7 | — |
| un `REVOKE` a `zeroerp_app` fuori dal loop dei grant | 11.8 | pgTAP di postura |
| un privilegio dato a mano su una sola macchina | 11.9 | pgTAP di postura |
| un file della prima generazione (`baseline/`, `migrations/`) aggiunto, tolto o modificato | 11.11 | `guardrail_v1_congelato.py` |

## Documentazione

- La doc auto-generata (`<schema>/tabelle`, `/views`, `/funzioni`) si legge e non
  si modifica: si scrive solo in `<schema>/manual`.
- Una guida (`docs/it/guide/`) descrive lo **stato attuale**: niente changelog,
  niente SQL nel corpo, un solo posto per il contratto di un oggetto (la doc
  auto-generata). Checklist, header e area tecnica:
  [standard-guide.md](../docs/it/dev/standard-guide.md).
