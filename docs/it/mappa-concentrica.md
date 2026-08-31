# Mappa Concentrica — Stato dello Sviluppo ZeroERP

> Documento vivo. Aggiornare ad ogni milestone significativa.
>
> Riferimento metodologico: [sviluppo-concentrico.md](sviluppo-concentrico.md)

*Ultimo aggiornamento: **30 agosto 2026** — venti giorni in **nove temi**. **Anello 3 (vendite)**: la **nota di credito** chiude il ramo morto degli accrediti e la genealogia si chiude con l'arco reso→NC; la **data del documento** smette di essere un effetto collaterale (numerazione governata dal registro, limite di emissione, registro visibile in lista) e il 30 si decide il **trasloco sui registri**; il **lavoro rimasto indietro** ha un verbo («Riporta da emettere») e «Rendi definitive» torna sulla lista Lotti. **Anello 1+3**: l'**IVA ha un risolutore** e i **titoli IVA del soggetto** hanno una sede — lato DB chiuso, consumatori applicativi dopo. **Anello 3 (`pagamenti`)**: il **posting esiste** (contabile, saldo rata, sistemazioni, RLS sui canali di incasso) — ⛔ ma è provato il *percorso*, mai l'*esito*: zero righe, collaudo aperto. **Anello 0**: l'errore porta un **bersaglio** e la riga di `event_log` dice *per chi*; i presidi pgTAP escono dal ramo cieco e il debito passa **da 86/442 a 19/551**. **Anello 1 (`ui`)**: la regola della lista si è spostata dove si legge — ⚠️ e il numero che era risalito (48 → 57) conta i **file con `DataTable` grezza**, non le liste: sono quasi tutti drawer e dialog. Dettaglio per tema nel [changelog della mappa](dev/mappa-concentrica-changelog.md).*
>
> *Aggiornamenti precedenti: vedi [changelog della mappa](dev/mappa-concentrica-changelog.md).*
>
> **Come è fatto questo documento.** §1 la **forma** del sistema (anelli, natura,
> dipendenze) — cambia di rado. §2 lo **stato corrente** per anello — cambia a
> ogni milestone. §3 la **roadmap**: solo lavori in corso o previsti, mai storia.
> §4 le **lezioni metodologiche**, che spiegano *perché* la mappa è fatta così.
> La cronologia datata sta **solo** nel changelog.

---

## 1 · La forma del sistema

## Visione d'insieme

```
                    ┌─────────────────────────────────────────────┐
                    │           ANELLO 3 — PROCESSI               │
                    │                                             │
                    │   vendite    acquisti    magazzino          │
                    │   pagamenti  contabilita                    │
                    │                                             │
                    │  ┌───────────────────────────────────────┐  │
                    │  │    ANELLO 2 — ORCHESTRAZIONE          │  │
                    │  │                                       │  │
                    │  │      pratiche      documenti          │  │
                    │  │    (workflow, giornale,               │  │
                    │  │     generazione, handler,             │  │
                    │  │     sospensioni, calcoli tempo;       │  │
                    │  │     template, asset, PDF generati)    │  │
                    │  │                                       │  │
                    │  │  ┌─────────────────────────────────┐  │  │
                    │  │  │  ANELLO 1 — DATI BASE           │  │  │
                    │  │  │                                 │  │  │
                    │  │  │  config  anagrafiche  catalogo  │  │  │
                    │  │  │                 ui              │  │  │
                    │  │  │  ┌───────────────────────────┐  │  │  │
                    │  │  │  │  ANELLO 0 — NUCLEO        │  │  │  │
                    │  │  │  │                           │  │  │  │
                    │  │  │  │  core (infrastruttura)    │  │  │  │
                    │  │  │  │  dbops, script            │  │  │  │
                    │  │  │  │                           │  │  │  │
                    │  │  │  └───────────────────────────┘  │  │  │
                    │  │  └─────────────────────────────────┘  │  │
                    │  └───────────────────────────────────────┘  │
                    └─────────────────────────────────────────────┘
```

**Regola fondamentale**: ogni anello dipende solo dagli anelli interni. Mai dipendenze inverse o laterali.

## Cronologia aggiornamenti

La storia datata (cosa e' atterrato, quando, con quale impatto sulla mappa) vive **solo** in [mappa-concentrica-changelog.md](dev/mappa-concentrica-changelog.md). Qui c'e' lo **stato corrente** per anello (§2) e cio' che e' aperto (§3).

⚠️ **Non aggiungere cronologia a questo documento.** E' la deriva che lo ha gonfiato in passato: ogni riga «fatto il giorno X» che entra nelle tabelle di stato le trasforma in un secondo changelog, meno curato del primo.

## Natura degli anelli (post-aggiornamento manifesto §III bis)

Ogni anello e' classificato come **autocontenuto** o **di servizio**. La distinzione non riguarda la direzione delle dipendenze (sempre verso l'interno), ma l'**ordine di costruzione** raccomandato.

| Tipo              | Significato                                                                                       | Costruzione                                                                                                                                                                                        |
| ----------------- | ------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Autocontenuto** | Ha un end-to-end di valore proprio (es. "gestisco anagrafica clienti"). Validabile in isolamento. | Si puo' costruire e dichiarare operativo da solo.                                                                                                                                                  |
| **Di servizio**   | Motore/infrastruttura per altri anelli. Senza consumatori esterni reali e' un'astrazione teorica. | Va costruito **dopo o in parallelo** ai consumatori, mai prima. Resta "predisposto, in attesa di validazione" finche' almeno due consumatori reali non l'hanno esercitato (manifesto principio 7). |

| Anello                                       | Natura                       |
| -------------------------------------------- | ---------------------------- |
| 0 — Nucleo Infrastrutturale                  | **Di servizio**              |
| 1 — Dati Base                                | **Autocontenuto**            |
| 2 — Orchestrazione (`pratiche`, `documenti`) | **Di servizio**              |
| 3 — Processi Operativi                       | **Autocontenuti** (ciascuno) |

---

## 2 · Stato corrente per anello

## Anello 0 — Nucleo Infrastrutturale

> **Natura: di servizio.** Il protocollo operativo del sistema. Si tocca solo per correggere limiti reali.

| Componente    | Tipo       | Stato     | Descrizione                                                                                                                                                                               |
| ------------- | ---------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `core`        | App Django | Operativo | error_manager, middleware, permissions, endpoint_helpers, pagination, throttling, tracciamento processi/job, audit sessioni, request log                                                  |
| `dbops`       | Schema DB  | Operativo | fn_run_automations, apply_fk_index_policy, registry task, vw_duplicate_indexes, audit_log, sessioni_utente, request_log, **automazione daterange**, **anti-overlap parametrico** (`automazione_overlap`: `where_predicate`/`key_expressions` + runner notturno auto-guarigione), **chiusura parametrica per scadenza**, **coda lavori generica** (`coda_lavori`: job queue DB-native transazionale, senza broker) |
| `script`      | Schema DB  | Operativo | fn_log_and_raise_error (**il codice errore viaggia nel campo strutturato `CONSTRAINT` su `P0001`**, non nel testo), viste e funzioni riusabili, helpers generici trigger (guard coerenza BoM, immutabilità), `fn_get_conto_bancario_predefinito` |
| `public`      | Schema DB  | Operativo | version_info                                                                                                                                                                              |
| `maintenance` | Schema DB  | Operativo | Job schedulati pgAgent, job_run_log                                                                                                                                                       |

### Cosa fornisce agli anelli esterni

- Error handling centralizzato (`ServiceError`, `ErrorManager.require`)
- Middleware API (exception handling, JWT audit, request context, request log)
- Pattern uniformi: `handle_post_json`, paginazione, throttling, search validators
- Automazioni DB: audit fields, tx_id, storicizzazione, lock colonne, protezione attivo, **`validita` STORED generated** (PG 18, nessun trigger), chiusura parametrica per scadenza (`dbops.fn_apply_chiusura_scadenze`)
- **Coda lavori generica** (`dbops.coda_lavori`): esecuzione asincrona di job per qualsiasi dominio — accodamento transazionale nella stessa transazione che genera il lavoro, worker che drena, idempotenza. Fondazione async dell'ERP: primo consumatore il giro fatturazione on-demand. Guida: [gestione-code-di-lavoro.md](guide/gestione-code-di-lavoro.md)
- **Errore di dominio come contratto** (agosto 2026): il codice viaggia in un **campo strutturato** dell'eccezione (`SQLSTATE P0001` + `CONSTRAINT`), letto in **un solo punto** lato backend. Il suo **significato** — la `classe` — sta a catalogo in Anello 1; status HTTP e `ui_action` si derivano. Due registri del debito (`dbops.codici_errore_senza_policy`, `dbops.messaggi_errore_codici_legacy`) restano **a zero righe**, come presidio di ciò che arriverà
- **Presidio dei riferimenti morti** (agosto 2026): un riferimento a un oggetto DB che non esiste più non arriva al merge. ⚠️ Il guardrail gira **dopo** `manage.py migrate`
- **Il bersaglio dell'errore**: oltre a *cosa* è successo, un errore dichiara **su quale entità** — una coordinata che il backend porta nell'envelope (`targets`) e il frontend trasforma in un gesto («vai lì»). Convenzione unica su tutti e tre i canali di `fn_log_and_raise_error`, presidiata in CI (`dbops.vw_bersagli_non_dichiarati` vuota)
- **Tracciamento processi e job**: API per audit log, task registry multi-dominio, job run log (6 endpoint REST, 27 test)
- **Audit sessioni**: login/refresh JWT tracciati in `dbops.sessioni_utente` con IP, user_agent, request_id (19 test)
- **Request logging**: ogni request `/api/*` registrata in `dbops.request_log` con metodo, path, status, durata
- **Token blacklist**: refresh token rotation con blacklist automatica (SimpleJWT `token_blacklist`)
- Policy indici FK automatica
- Logging e raise errori DB (`script.fn_log_and_raise_error`)

### Audit sessioni, request logging e token blacklist

Implementato il 6 marzo 2026 (vedi `docs/it/dev/work-done/Audit-logging-sessionii-request-token.md`):

| Capacita'                         | Componente DB               | Componente Backend                                                             | Stato     |
| --------------------------------- | --------------------------- | ------------------------------------------------------------------------------ | --------- |
| Audit sessioni (login/refresh)    | `dbops.sessioni_utente`     | `session_audit_service` + `AuditTokenObtainPairView` / `AuditTokenRefreshView` | Operativo |
| Request logging (chi chiama cosa) | `dbops.request_log`         | `RequestLogMiddleware`                                                         | Operativo |
| Token blacklist e revoca          | SimpleJWT `token_blacklist` | Settings `ROTATE_REFRESH_TOKENS` + `BLACKLIST_AFTER_ROTATION`                  | Operativo |

Estensioni non-breaking: nuove tabelle in `dbops`, nuovo middleware in `core`, override view JWT. Nessun contratto esistente modificato. Gli anelli esterni ne beneficiano automaticamente senza alcuna modifica al proprio codice.

### 🔴 I test girano come l'applicazione (dal 7 agosto 2026)

Cambio di regime, non una rifinitura: il runner pgTAP di default è l'**utente
applicativo**, non l'owner. **Le policy RLS sono esercitate a ogni corsa.**

| | |
| --- | --- |
| Conseguenza | un rosso può essere un **permesso** o una **policy**, non solo una fixture; una fixture che scrive dove l'applicazione non scrive **non passa più** |
| Eccezioni | 29 file marcati `owner`, ognuno **con la ragione scritta** |
| In CI | sempre sulle PR verso `main`; sui push a `Tito-dev` solo se toccano `db/` o `scripts/`. Baseline **separata**: il DB della CI è ricostruito da zero, quello di sviluppo ha dati veri — i rossi sono **popolazioni diverse** |
| Preambolo obbligatorio | `BEGIN`, riga di contesto, `SET CONSTRAINTS ALL IMMEDIATE` — presidiato da un cancello. Senza, un file diventa **verde per sottrazione** |
| Debito noto | **19 rossi** su **551 file** (era 86 su 442 al 10 agosto). È un registro che deve calare, non una lista di eccezioni |

### Stabilita'

Stabile. Modifiche solo per correzioni o estensioni non-breaking (nuove policy, nuovi middleware).

---

## Anello 1 — Dati Base e Configurazione

> **Natura: autocontenuto.** Entita' di riferimento condivise da tutti i processi. Vocabolario comune del sistema.

| Componente     | Tipo       | DB        | Backend   | Frontend  | Descrizione                                                                                                                |
| -------------- | ---------- | --------- | --------- | --------- | -------------------------------------------------------------------------------------------------------------------------- |
| `config`       | App Django | Operativo | Operativo | Operativo | Stati, nazioni, UO, termini pagamento, priorita', canali; policy operative trasversali; impostazioni parametri multi-scope; **catalogo dei codici errore** (`classi_errore` 10 classi; 831 righe nel seed al 30-08, erano 690 il 10-08) — il **significato** di un errore è un dato di riferimento, lo status HTTP no; **nature del documento fiscale** (`nature_doc_fiscale`) e **tipi di titolo IVA** (`tipi_titolo_iva`) |
| `anagrafiche`  | App Django | Operativo | Operativo | Operativo | Soggetti, indirizzi, contatti, risorse umane, emittenti fiscali, billing account; **titoli IVA del soggetto** (`soggetti_titoli_iva` + ambiti + registro movimenti **append-only**, dove anche l'annullo di una forzatura è un movimento) — è da qui, e non da un default sul cliente, che il soggetto influenza l'IVA |
| `catalogo`     | App Django | Operativo | Operativo | Operativo | Articoli (CRUD, UoM, BoM, note) — **completato e testato** (work-done/gestione-articoli.md)                                |
| `amm-software` | App Django | Operativo | Operativo | Operativo | Gestione operatori, permessi riepilogo, profili reparto, audit log (solo ADMIN), drawer dedicato gestione permessi         |
| `ui`           | App Django | Operativo | Operativo | Operativo | Metadato di presentazione: liste configurabili + **dashboard home** (catalogo widget, composizione, preferenza utente), preset per profilo/emittente/sistema. Di servizio. **Due famiglie di consumatori reali**: liste (clienti/fornitori/contratti…) e home a card KPI (`fn_resolve_dashboard_config`). |

> **Multi-Face Auth — COMPLETATO (22-04-2026, agg. RLS operatori 04-06-2026):** `anagrafiche` usa il bridge generalizzato `identita_digitali` (SSO multi-veste, cutover 19-04-2026). `amm-software` supporta operatori, portale clienti/fornitori e shop B2C. **RLS attiva per gli operatori interni** con scope emittente fiscale: `ENABLE` su 10 tabelle documentali (fatture, scadenze, lotti fatturazione, ordini, preventivi, contratti, offerte commerciali, documenti generati, pratiche, billing account — 02-06-2026) e copertura scrittura `FOR ALL` + `WITH CHECK` (04-06-2026, migration `20260603-16..25`); lato BE reset GUC d'identita' fail-closed a inizio richiesta. **Infrastruttura auth predisposta per tutte le vesti; le policy RLS portale/shop restano dry-run e le API di dominio portale/shop (fatture, ordini, catalogo B2C) non sono ancora sviluppate — saranno affrontate quando il business lo richiedera'.** Dettaglio: `docs/it/dev/work-done/pr-b-shop-b2c-cambio-modello.md`, `analisi-attivazione-rls-operatori*.md`, `db-brief-rls-ondata2-insert-bloccati.md`. Guida: [architettura-multi-face-auth v2.0 §14](guide/architettura-multi-face-auth.md).

### Frontend Anello 1 — Stato dettagliato

| Area                            | Stato      | Note                                                                                                                                                                    |
| ------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Gestione Geografica             | Operativo  | 7 tab: indirizzi, toponomastica, comuni, CAP, province, regioni, stati — CRUD completo. UI da migliorare                                                                |
| Gestione Soggetti               | In test UI | PF/PG/ENTE end-to-end, 3 building block, ruoli, CF validator IT con omocodia                                                                                            |
| Pannello Config                 | Operativo  | 67 tabelle CRUD generiche con drawer dinamico, metadata-driven                                                                                                          |
| Building block soggetto         | Operativo  | SoggettoForm, ContattoForm, IndirizzoSoggettoForm, DatiSocietariForm, ComuneAutocomplete, StradarioAutocomplete, StradarioGeneraleAutocomplete                          |
| Modalita' sola lettura          | Operativo  | Pattern protect CSS + provide/inject: tutti i drawer con app-readonly, 2 componenti core auto-hide (NewButton, DrawerFooter)                                            |
| Azioni processo (Livello 2)     | Operativo  | Prop `action` su NewButton/DrawerFooter, composable useActionPermission, mappa da /me/                                                                                  |
| Amm. Software — Operatori       | Operativo  | Lista con filtri/sort, drawer crea/modifica unificato, tab permessi override, rename utenti→operatori                                                                   |
| Amm. Software — Profili         | Operativo  | Lista reparti, drawer editor aree (Select livello) + azioni (ToggleSwitch), confirm save                                                                                |
| Amm. Software — Permessi        | Operativo  | Matrice operatori × aree con Tag colorati, colonne dinamiche, filtri reparto/ruolo                                                                                      |
| Amm. Software — Audit Log       | Operativo  | Timeline globale 6 tabelle storico, paginazione lazy, sort server-side, filtro tipo                                                                                     |
| Amm. Software — Drawer Permessi | Operativo  | Drawer dedicato gestione permessi richiamabile dalla riga lista operatori; `OperatorePermessiTab` riusabile reattivo a `authUserId`                                     |
| Catalogo — Articoli             | Operativo  | Lista con 7 filtri, drawer 3 tab (UoM, BoM, note), `ArticoloLookup` BB cross-dominio. **Completato e testato**                                                          |
| Catalogo — Unita' di Misura     | Operativo  | Lista, drawer CRUD, conversioni UoM, lookup generico whitelist                                                                                                          |
| Impostazioni Parametri          | Operativo  | Lista multi-scope (default/emittente/gruppo/utente), drawer override con selettore scope (Personale/Emittente) per admin, `PARAMETER_SCOPE` come unica fonte di verita' |
| UI — Liste (DB/BE)              | Operativo  | Schema ui (changeset atterrati): catalogo colonne, preset sistema/profilo/EF, preferenze utente. App Django `ui` con repository, servizi (incl. admin + export) ed endpoint REST.                       |
| UI — Liste (Frontend)           | Operativo  | `ListaConfigurabile.vue`, `ListaColonneModal.vue`, `useListaConfig` + viste admin: **53 file montano il building block**. ⚠️ **Il contatore del presidio conta i file con `DataTable` grezza, non le liste**, e al 30-08 dice **57** (48 il 3 agosto). Classificati: **26 drawer/dialog**, 15 pannelli o tab annidati, **6 sono i wrapper stessi**, 5 `*SearchTable` di dominio e **5 view di lista**. Le prime due categorie sono l'**eccezione ammessa** da `AGENTS.md`, non debito. La **regola zero della lista** è stata spostata in cima ad `AGENTS.md` (30-08), dove si legge a inizio sessione |
| UI — Dashboard home             | Operativo  | Card KPI configurabili: catalogo widget + composizione per profilo/emittente + preferenza utente (`ui.fn_resolve_dashboard_config`), filtro sui permessi dell'operatore, drawer di personalizzazione. Validata in-app (luglio 2026). |

### Cosa fornisce agli anelli esterni

- Entita' master referenziate via FK: soggetti, emittenti, risorse umane
- Tabelle config condivise: stati (doc fiscale, pratiche, flussi), priorita', canali
- Lookup e decodifiche centralizzate
- **Policy operative trasversali**: configurazioni che governano il comportamento del sistema su piu' domini e non appartengono a nessun dominio specifico (es. `user_emittenti_fiscali` — ambito operativo per emittente)
- **Gestione geografica completa**: indirizzi, toponomastica, comuni, province, regioni, stati — API + UI con autorizzazione per area `anagrafiche`
- **Building block frontend riutilizzabili**: composable centralizzati (useSearchTable, useDrawerState, useTabFreshness, useReadonlyMode, useActionPermission), componenti atomici (SoggettoForm, AuthUserForm, autocomplete, NewButton, DrawerFooter con prop `action`), CSS utility classes
- **Sistema permessi a 3 livelli**: Livello 1 area (TUTTO/LETTURA/BLOCCATO) + Livello 2 model/oggetto (override granulare per singola entita') + Livello 3 azioni processo (abilitata/negata), con enforcement backend (ZeroERPPermission) e auto-hide frontend (prop `action`, `useReadonlyMode`)
- **Metadato di presentazione** (quando `ui` sara' operativo): configurazione colonne per ogni lista, cascata preset sistema/profilo/emittente, preferenze personali utente — leggibile da qualsiasi lista di qualsiasi anello esterno tramite `GET /api/v1/ui/liste/{codice}/config`

### Regola di posizionamento in `config`

`config` e' l'unico schema di Anello 1 con natura cross-schema. Ospita due categorie distinte:

1. **Cataloghi condivisi**: dati di riferimento statici usati come vocabolario comune (stati, priorita', canali, UO, termini pagamento)
2. **Policy operative trasversali**: configurazioni che descrivono regole di governo applicabili a piu' processi, quando non esiste uno schema di dominio piu' appropriato

Una tabella appartiene alla seconda categoria se: (a) non descrive un'entita' di business ma una regola di visibilita' o operativita', e (b) la regola vale trasversalmente su piu' schemi di Anello 3. In assenza di uno schema dedicato, `config` e' la collocazione meno artificiale — non `dbops` (infrastruttura tecnica) ne' `anagrafiche` (entita' anagrafiche).

### Posizionamento schema `ui`

`ui` e' il terzo schema di Anello 1 con natura cross-dominio, accanto a `config` e `amm-software`. Ospita esclusivamente **metadato di presentazione**: non contiene logica di business, non ha dipendenze da Anello 2 o 3, dipende solo da `config.profili_accesso` e `anagrafiche.emittenti_fiscali` (Anello 1) e `django.auth_user` (Anello 0).

E' classificato **di servizio** all'interno di Anello 1: il suo end-to-end richiedeva almeno un consumatore reale (prima lista migrata a `<ListaConfigurabile>`). Questo è avvenuto: le liste clienti e fornitori usano il componente configurabile, quindi il nucleo è stato **validato su casi reali** e si considera operativo. La lezione metodologica del caso pratiche (non completare prima della validazione su un caso reale) è stata rispettata.

Con la **dashboard home** (luglio 2026) `ui` acquisisce la **seconda famiglia di consumatori**: stesso impianto a cascata (sistema → profilo → emittente → utente), stessa forma di risoluzione lato DB (`fn_resolve_dashboard_config` accanto a quella delle liste), stesso filtro sui permessi dell'operatore. È la conferma richiesta dal principio 7 sull'asse "metadato di presentazione": il pattern non è stato inventato per la home, è stato **riusato** perché già decantato dalle liste.

Riferimento architetturale: `docs/it/dev/work-done/sviluppo-personalizzazioni-liste.md`. Sviluppi differiti: `docs/it/dev/work-in-progress/sviluppo-personalizzazioni-liste_def.md`.

> 🚨 **Il piano PrimeVue 5 non è più una questione tecnica (agosto 2026).**
> `primevue`, `@primeuix/themes` e `primeicons` erano **MIT** e passano tutti e
> tre alla **licenza PrimeUI** (community/commerciale, con chiave) dalla nuova
> major. ZeroErp è **GPL v3 pubblica**: è una **decisione di licenza**, e non la
> prende un piano operativo. Il disaccoppiamento tecnico è chiuso e resta valido
> con qualunque esito — è il motivo per cui conviene averlo fatto prima.
> Vedi [piano-migrazione-primevue-5.md](dev/work-in-progress/piano-migrazione-primevue-5.md) §1-bis.

### Stabilita'

Stabile. Cresce per aggiunta di nuove tabelle config (es. `config.canali_pratiche` aggiunta per pratiche) senza rompere quanto esistente.

---

## Anello 2 — Orchestrazione di Dominio

> **Natura: di servizio.** Motore trasversale che gli anelli esterni usano per tracciare, orchestrare e automatizzare.
>
> ✅ **`pratiche`: validata con il primo consumatore (2026-06-12).** Il giro pratica PREVENTIVI (vendite) e' stato eseguito end-to-end runtime — handler `CONFERMA_VENDITA` con split per natura, giornale `DOMINIO_*`, gate EVASO, generazione cross-pratica, permessi da operatore reale — vedi `dev/work-in-progress/analisi-pratiche-domini-anello3.md` §8.5 (Fase E) e `dev/work-done/analisi-pratiche-workflow-v2.md` (estensione: ripetibilita', bivi condizionali, lenti contesto, guard chiusura). Stato attuale: **validata con primo consumatore (vendite), pronta per il secondo** (Fase F: candidata assistenza/CRM). Resta vero il principio: solo dopo il **secondo** consumatore le astrazioni si promuovono a *contratti* (manifesto principio 1); fino ad allora restano *proposte* (principio 7).
>
> ✅ **`documenti`: validato su 6 consumatori reali (2026-07).** Il motore documentale e' passato dal pilota (`vendite.preventivi`) a **6 domini** — preventivi, offerte, contratti, ordini, DDT e **fatture** — e con le fatture ha dovuto reggere anche la **stampa massiva** (render fuori dalla transazione che tiene il lock del registro fiscale). Le sue astrazioni sono quindi *contratti*, non piu' *proposte*: template versionato, asset per emittente e `pdf_mode` data-driven sono stati esercitati da domini con esigenze diverse.

| Componente  | Tipo       | DB        | Backend   | Frontend   | Descrizione                                                                                                                                                          |
| ----------- | ---------- | --------- | --------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pratiche`  | App Django | Operativo | Operativo | Operativo  | Workflow engine, giornale, generazione cross-pratica, handler dispatch, sospensioni, calcoli tempo, macchina a stati, note, allegati; **assegnazione flusso operatore/reparto + coda lavoro** (pannello "Le mie attività"), **esito configurabile flussi**, **aggancio documento↔flusso**, **audit utente reale** |
| `documenti` | App Django | Operativo | Operativo | Operativo  | Motore documentale parametrico: template versionati, asset documentali, render PDF WeasyPrint, archivio documenti generati. **6 domini consumatori** (preventivi, offerte, contratti, ordini, DDT, **fatture**); con le fatture arriva anche la **stampa massiva via coda** (task che accoda → worker che drena, fuori dal lock del registro fiscale). ⭐ **Tre percorsi di stampa distinti** (agosto 2026): *genera nuovo* (modello e dati di oggi), *scarica originale* (il file su storage), **ristampa fedele** (ri-renderizza com'era: versione di template pinnata anche OBSOLETA + contesto congelato, senza persistere nulla) |

### Cosa fornisce agli anelli esterni

- **Pratiche**: contenitore tracciabile per qualsiasi processo (onboarding cliente, gestione ordine, assistenza tecnica)
- **Flussi**: step operativi con prerequisiti, esiti, scadenze, assegnazione risorse
- **Assegnazione e coda lavoro operatore**: flusso assegnabile a operatore/reparto (policy reparto-first), coda a 4 livelli (`fn_coda_lavoro_operatore`: ASSEGNATO/COMPETENZA/REPARTO/LIBERO), presa in carico (`fn_prendi_in_carico_flusso`); consumer FE pannello "Le mie attività"
- **Esito configurabile dei flussi**: MANUALE / AUTOMATICO / CONTESTUALE con `esito_default`
- **Giornale di bordo**: audit trail immutabile, append-only, con correlazione `tx_id` e **utente reale** (`user_update`/`data_update`)
- **Generazione cross-pratica**: un flusso completato puo' generare automaticamente nuove pratiche
- **Handler dispatch**: mapping `handler_key` → classe Python per automazione step
- **Canali**: visibilita' dei flussi su sorgenti esterne (WEB_CLIENTI, APP_TECNICA, PORTALE_FORNITORI)
- **Sospensioni**: fermo temporaneo pratica/flusso con propagazione automatica e riattivazione (manuale o pgAgent)
- **Calcoli tempo**: tracking tempi netti tra coppie di flussi (formula da/a), con esclusione giorni sospensione
- **Macchina a stati rigida**: transizioni ammesse validate da trigger DB (config-driven)
- **API interna**: `pratiche_service` come facade per gli anelli esterni
- **Documenti parametrici**: template e versioni separati dai dati, asset per emittente fiscale, PDF finale archiviato con hash, utente e data generazione
- **Render PDF**: backend con Jinja2 + WeasyPrint, storage configurato via parametri, generazione/lista/download esercitati da 6 domini (preventivi, offerte, contratti, ordini, DDT, fatture)
- **Stampa massiva disaccoppiata**: il documento di massa si **accoda** e un worker lo renderizza fuori dalla transazione che detiene il lock del registro fiscale — pattern nato sulle fatture, riusabile da ogni dominio che stampi in lotto

### Perche' e' un anello separato (non anello 1)

`pratiche` non e' un dato di riferimento statico — e' un **motore di orchestrazione con stato e ciclo di vita**. Dipende da anello 1 (config, anagrafiche) per le FK, ma fornisce capacita' operative che gli anelli esterni consumano. E' il cuore operativo del sistema: ogni evento significativo (nuovo cliente, nuovo ordine, nuova assistenza) genera una pratica con il suo giornale.

### Perche' non e' anello 3 (processi)

Non e' un processo di business specifico (come vendite o acquisti). E' l'**infrastruttura di processo** che tutti i domini usano. E' al servizio dei processi, non un processo in se'.

### Riferimenti

Documentazione: `docs/it/dev/work-done/gestione-pratiche-v2.md` — API:
[api_pratiche_list](backend/pratiche/manual/api_pratiche_list) ·
[api_pratiche_note](backend/pratiche/manual/api_pratiche_note) ·
[api_pratiche_allegati](backend/pratiche/manual/api_pratiche_allegati).
Piano v1 (storico): `docs/it/dev/work-done/piano-gestione-pratiche.md`.

ℹ️ Il dettaglio fase-per-fase di v1 (marzo 2026) e v2 (marzo 2026) — 115 test,
19 endpoint, le tabelle con le righe «FATTO» — è **storia** e vive nel
[changelog](dev/mappa-concentrica-changelog.md). Qui resta lo stato: operativo su
DB, backend e frontend, **validato dal primo consumatore**, in attesa del
secondo.

---

## Anello 3 — Processi Operativi

> **Natura: autocontenuti (ciascuno).** Cicli di business che usano anelli interni. Ogni processo e' autonomo ma condivide vocabolario e infrastruttura.

| Componente    | Tipo       | DB        | Backend   | Descrizione                                                                                                                                                                   |
| ------------- | ---------- | --------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `vendite`     | App Django | Operativo | Operativo | Ciclo attivo: preventivi rev2, offerte, contratti, **ordini operativi**, DDT, **resi**, fatture e **note di credito**, pipeline fatturazione (**batch automatico a corsie + cockpit di azione dalle tre lenti**), lotti, commesse multi-sorgente (quantità immutabili + **porta oneri**), **listini v3**, **pratica PREVENTIVI** (primo consumatore del motore `pratiche`), stampa PDF di 6 domini via `documenti` (fatture con **stampa massiva a coda**), **numerazione governata dal registro** |
| `acquisti`    | App Django | Parziale  | Stub      | ⚠️ **Modello disegnato, non in esercizio** (misurato 21-08-2026): ordini, righe, DDT, indirizzi e ponte di fulfillment esistono con vincoli e trigger, ma **tutte le tabelle sono a 0 righe** — nessun documento di acquisto è mai stato creato. La struttura è lo **specchio** del ciclo vendite; ⚠️ la simmetria dei nomi non garantisce quella delle colonne (il progetto ha già pagato un `sorgente_uid` che significava due cose diverse). Doc concettuale completata 21-08-2026 |
| `magazzino`   | App Django | Parziale  | Stub      | ⚠️ **Modello disegnato, non in esercizio** (misurato 21-08-2026): ledger movimenti, costo medio, inventari, rettifiche, trasferimenti, prenotazioni, ubicazioni e asset esistono con vincoli e trigger, ma **tutte le tabelle operative sono a 0 righe**; popolati solo i due vocabolari da seed (`ambito_causale` 6, `causali` 10). 🔴 Il dominio era **privo di qualunque pgTAP**, e il CHECK `chk_mag_movimenti_da_destinazione_distinti` rendeva inseribili **solo i trasferimenti** (corretto da `20260821-10`, presidiato dal primo test della tabella). ⚠️ Resta aperto: `causali.segno` non è legato al segno di `movimenti.qta`, e `vw_giacenza` somma senza guardarlo. Doc concettuale completata 21-08-2026 |
| `pagamenti`   | App Django | Parziale  | Parziale  | ⭐ **Il posting esiste** (agosto 2026): registrazione della contabile, saldo della rata, guard di transizione e di capienza, **sistemazione delle eccedenze**, distinta di correzione, RLS sui canali di incasso (`enti_incasso` non ne aveva: l'IBAN di ogni emittente era visibile a tutti). Era la misura di apertura del cantiere — *nessuna funzione, in tutto il database, scriveva `vendite_movimenti`*. ⛔ **Provato il percorso, mai l'esito**: lo schema ha ancora 0 righe transazionali e il **collaudo in-app è aperto** |
| `contabilita` | App Django | Operativo | Stub      | Piano conti, registrazioni, partite                                                                                                                                           |
| `storico`     | App Django | Operativo | Stub      | Audit temporale, storicizzazione                                                                                                                                              |

### Dipendenze verso anelli interni

```
vendite ──────► config (stati_doc_fiscale, termini_pagamento)
              ► anagrafiche (soggetti, emittenti_fiscali)
              ► catalogo (articoli, UoM, listini)
              ► core (error_manager, endpoint_helpers, coda lavori generica)
              ► documenti (generazione/lista/download PDF su 6 domini + stampa massiva fatture)
              ► pratiche (OPERATIVO — pratica PREVENTIVI: handler, giornale, azioni di processo)

acquisti ─────► stesse dipendenze di vendite
              ► pratiche (FUTURO)
```

### Integrazione con pratiche

`pratiche` e' stata validata dal primo consumatore reale: la pratica PREVENTIVI di `vendite` (giugno 2026) esercita creazione pratica, flussi con handler (`CONFERMA_VENDITA`), giornale `DOMINIO_*`, azioni di processo e generazione cross-pratica. Gli altri processi di Anello 3 potranno:

1. **Creare pratiche** per i propri eventi (`pratiche_service.crea_pratica`)
2. **Alimentare il giornale** con eventi di dominio (nuovo cliente → PRATICA_CREATA)
3. **Usare flussi** per step operativi tracciati (approvazione ordine, sopralluogo, collaudo)
4. **Sfruttare generazione cross-pratica** (ordine completato → genera pratica assistenza)

I processi **massivi** (lotto fatturazione, import batch) mantengono la propria infrastruttura di tracking (pipeline, task runs, log fatture) perche' hanno requisiti diversi (parallelismo, resume per singola fattura, tracing per step). Il giornale di pratiche traccia eventi a livello di **processo singolo**, non di batch.

### Stato sviluppo vendite (app leader)

| Area                                    | Stato                                                                         |
| --------------------------------------- | ----------------------------------------------------------------------------- |
| Pipeline fatturazione                   | Operativo — **batch automatico end-to-end** (driver CRON `run-until-done`, discovery a corsie `(emittente, tipo_doc, utility)`, **sync stato fattura per-step `1→2→8`**, run headless in `job_run_log`) (giugno 2026) |
| Cockpit processi fatturazione           | Operativo — dalle tre lenti si **agisce**: «Fattura adesso» (giro on-demand su lotto o perimetro), «Riporta da emettere» (recupero dei residui, agosto 2026), stampa/ristampa massiva; atterraggio contestuale dal pannello errori e dal breakdown FATTURATA (l'invio SDI non è esposto). ⚠️ **«Rendi definitive» NON è più fra questi**: dal 26 agosto 2026 vive sulla **lista Lotti**, dove sta l'elenco del suo oggetto — dalla card `Fatturate` resta il rimando filtrato. Guida [cruscotti-fatturazione.md](guide/cruscotti-fatturazione.md) §7 (luglio 2026) |
| Stampa massiva fatture (outbox)         | Operativo — la stampa **accoda** (`vendite.fatture_stampa_coda` + `fn_accoda_stampe_lotto`), un **worker drena** e renderizza fuori dal lock del registro fiscale; numerazione garantita in stampa da backstop idempotente. La fattura è il **6° dominio del motore documentale** (luglio 2026) |
| Lotti massivi/giornalieri               | Operativo — stato documentale fattura allineato per-step (giornaliero unificato a `1→2→8`) |
| Registry task DB multi-dominio          | Operativo                                                                     |
| Dispatch task con implementation_key    | Operativo                                                                     |
| Runtime task tracing                    | Operativo                                                                     |
| Satelliti della fattura                 | Operativo — **cantiere chiuso su tutte le fasi** (agosto 2026): **piano rate** (`fatture_scadenze`, generato nello step EMESSA dopo il ricalcolo IVA, idempotente, con snapshot del termine in testata), snapshot di **intestazione** e **indirizzi**, **drawer di consultazione** in un round-trip sugli stessi lettori del PDF, **note fattura** (6° dominio del BB note), ritiro del generatore di righe SQL |
| Emissione mirata + ritorno a DRAFT      | Operativo — il giro accetta un perimetro ristretto ai **gruppi fatturabili** (stesso verbo, assente = giro di massa invariato); il lotto può **tornare a DRAFT** per rifare un giro andato storto (agosto 2026) |
| Il lavoro che non torna indietro        | Operativo — le tre porte di reset (elimina fattura, riporta il lotto a DRAFT, annulla il lotto) non disfano più una riga già accreditata: era una violazione di chiave esterna **a metà lavoro**, ora è un rifiuto motivato. Il lavoro rimasto indietro ha un verbo, **«Riporta da emettere»**, con la card spezzata in due per non promettere una fattura che non c'è (agosto 2026) |
| Nota di credito sui resi                | Operativo — il **ramo economico** dei resi: il reso portava indietro merce e motivo e nessun valore. Righe di accredito (`resi_righe_accrediti`), nature del documento fiscale a catalogo, DB+BE+FE chiusi e **collaudo in-app superato** (agosto 2026) |
| Numerazione: data documento e registro  | Operativo — la data e la sequenza di un documento fiscale sono una **decisione del registro**, non un effetto del giro: **limite di emissione** (il documento nasce già conforme invece di scoprirsi non più trasmissibile) e **registro + data prevista visibili in lista**, prima di generare. ⭐ Decisione del 30-08: la commessa passa sul **motore dei registri**, e la periodicità dentro `config.sistema_codici` **non si fa più** |
| IVA di riga: risolutore a due stadi     | Operativo (DB) — l'IVA la decideva l'articolo e nessun altro, e il regime fiscale del cliente era scritto e **letto da nessuno**. Ora c'è un risolutore, e l'influenza del soggetto passa **sempre da un titolo registrato e documentato** (Anello 1, `anagrafiche`), mai da un default sul cliente. Al 30-08 il lato DB è chiuso; i consumatori applicativi vengono dopo |
| Builder XML SDI                         | In corso (payload pronto, generazione XML da fare). ⚠️ Il blocco **`2.4 DatiPagamento`** non è generato: `fn_prepare_sdi_payload` non nomina né le scadenze né il blocco |
| Persistenza esito SDI                   | Da fare                                                                       |
| Commesse (push, orchestrator, handlers) | Operativo — multi-sorgente (1 ROOT + N COLLEGATO), push idempotente, snapshot pricing v5 nel push, capability azioni stato **con motivo**, pull→`attivita_fatturabili` agganciata agli step DRAFT, **guard di uscita** (niente chiusura/annullo con righe ancora fatturabili), RLS scope emittente anche in scrittura |
| Quantità immutabili + porta oneri       | Operativo — quantità già fatturate immutabili (guard `commesse_attivita`/`attivita_fatturabili`, cod. 550/551); oneri manuali via `config.causali_onere` + modello **articolo↔causale 1:1** (ogni onere porta la propria IVA), madre `fn_aggiungi_onere_commessa` con log (cod. 552-554, race `segment_key` chiusa a 557→409) (luglio 2026) |
| Guard `tipo_doc_fiscale` emittibile     | Operativo — normalize all'upsert (default da `config.sorgenti`) + guard di riga `APPROVATA+NON_EMESSA ⇒ tipo_doc NOT NULL` (cod. 497) + CHECK backstop: niente "fatturato perso in silenzio" (giugno 2026) |
| Ordini di vendita                       | Operativo — CRUD, lista DEF-8, conferma, EVASO automatico, stampa PDF, conversione preventivo/offerta→ordine, lock cliente (giugno 2026) |
| DDT di vendita                          | Operativo — documento di trasporto: evasione ordine→DDT (1:N, residuo per riga append-only) o standalone, stati data-driven `DRAFT→EMESSO→SPEDITO→CONSEGNATO` (+RESO/ANNULLATO), numero all'emissione, righe con prezzo opzionale (solo-trasporto), push a commessa (sorgente `DDT_VENDITA`), emittente memorizzato + RLS (§15), stampa PDF (5° dominio documenti), riepilogo IVA, export lista (luglio 2026) |
| Resi di vendita                         | Operativo — documento di rientro merce nato dal DDT, **senza valori economici** (ramo nota di credito rinviato): conferma (riapre il residuo ordine, flip DDT→RESO se totale), annullo come storno, **ri-consegna** (`fn_genera_ddt_riconsegna`, parziale e multipla), **rinuncia** con reso DEFINITIVO, due code di lavoro (da accreditare / da ri-consegnare), azioni data-driven (luglio 2026) |
| Fatturazione DDT/resi a contatore       | Operativo — **contatore di merce** per riga d'ordine (spedito − reso) al posto del flag logistico `riapre_residuo`: chiusi due bug di doppia fatturazione, lenti Situazione aperta/Backlog estese a DDT e resi, coda accrediti con quantità (DL-19..28, luglio 2026) |
| Lineage documenti (genealogia)          | Operativo — `vw_documento_lineage_nodi`/`archi` + `fn_documento_lineage`; pannello «Passaggi» nei drawer documento e colonne pratica/fase/transito nelle liste. ⭐ **Il grafo non si ferma più sul reso** (agosto 2026): l'arco reso→nota di credito chiude i due rami di ritorno — la merce che torna e il valore che torna — e con lui sono caduti i residui del `root` che dipendeva dagli id, della commessa senza origine e della nota di credito che in lista si chiamava «Fattura» |
| Indirizzi documento (UX v2)             | Operativo — building block cross-dominio sui 5 domini vendite (preventivi/offerte/contratti/ordini/DDT): sezione inline + drawer gestione, snapshot indirizzo di consegna congelato all'emissione, auto-assegnazione default (luglio 2026) |
| Pratica PREVENTIVI (integrazione pratiche) | Operativo — handler `CONFERMA_VENDITA`, split per natura merce→ordine / servizi→commessa, smistamento riga-per-riga, gate EVASO (giugno 2026) |
| Listini v3 (N2/N5/N6/N7/N8a)            | Operativo — Sprint B-v3 completato (aprile 2026)                              |
| Pricing commesse (N5/N7/N7-sblocco)     | Operativo — riallineamento, variazione, sblocco                               |
| Contratti (modello unificato)           | Operativo — drop modalità A/B/C, eccezioni `tipo_eccezione`, snapshot versione listino, lock post-attivazione, stato ANNULLATO |
| Offerte commerciali                     | Operativo (DB+BE+FE), in consolidamento — proposta condizioni quadro → push 1:1 a contratto; componenti BoM; generazione documento + allegati |
| Componenti BoM compositi (vendite)      | Operativo — modello a 3 livelli condiviso da preventivi/contratti/offerte/ordini/ddt (i resi non hanno componenti) |
| Valuta su documenti                     | Operativo (DB) — `valuta_id` su offerte/contratti/preventivi, default da resolver gestore |
| Preventivi rev2                         | Operativo — emittente persistito, istanza obbligatoria, guard utility/istanza |
| Revisioni preventivo + riepilogo IVA    | Operativo — scenario 2.1 chiuso end-to-end                                    |
| Generazione PDF documenti               | Operativo — 6 domini serviti dal motore `documenti` (preventivi, offerte, contratti, ordini, DDT, fatture); i resi non generano PDF in questa slice |

---

## Matrice delle dipendenze

```
                 core   config   anagr.   catal.   pratiche   documenti   vendite
core              -       -        -        -        -          -           -
config           usa      -        -        -        -          -           -
anagrafiche      usa      -        -        -        -          -           -
catalogo         usa      -        -        -        -          -           -
pratiche         usa     usa      usa       -        -          -           -
documenti        usa     usa      usa       -        -          -           -
vendite          usa     usa      usa      usa      usa        usa          -
acquisti         usa     usa      usa      usa    (futuro)   (futuro)      -
magazzino        usa     usa      usa       -     (futuro)      -           -
pagamenti        usa     usa       -        -     (futuro)      -           -
contabilita      usa     usa       -        -     (futuro)      -           -
```

Nessuna dipendenza inversa. Nessuna dipendenza laterale tra processi di anello 3.

Gli anelli esterni possono dipendere direttamente da anelli non adiacenti — vendite usa `core` e `config` senza passare per `pratiche`. Questo non viola la direzione delle dipendenze, sempre dall'esterno verso l'interno: descrive semplicemente come certi tipi di informazione attraversano il tronco (la linfa, nella metafora del vocabolario).

---

## 3 · Roadmap

> **Regole di questa sezione**, per non farla tornare com'era:
>
> 1. solo lavori **in corso o previsti** — ciò che è finito esce e va nel
>    [changelog](dev/mappa-concentrica-changelog.md);
> 2. un'area **operativa con rifiniture aperte** non è un lavoro in corso: la
>    rifinitura si annota nella tabella del suo anello, non qui;
> 3. ogni voce di «In corso» ha un **documento vivo**. Senza documento non è in
>    corso: è un'intenzione, e va sotto «Previsti».

### 🔨 In corso — con cantiere aperto

| Cosa | Dove sta | Stato |
| --- | --- | --- |
| **Incassi e contabili di pagamento** | [brief-incassi…](dev/work-in-progress/brief-incassi-riconciliazione-rate-promemoria.md) · [DB](dev/work-in-progress/brief-db-posting-e-abbinamento-rata.md) · [BE/FE](dev/work-in-progress/brief-be-fe-posting-e-abbinamento-rata.md) | **Posting, abbinamento e sistemazioni scritti** (agosto). ⛔ Resta il [collaudo in-app](dev/work-in-progress/collaudo-in-app-incassi-distinte-e-sistemazioni.md): dello schema è provato il *percorso*, mai l'*esito* — zero righe |
| **Numerazione: il trasloco sui registri** | [analisi due motori](dev/work-done/analisi-db-numerazione-documenti-e-due-motori.md) | Decisioni prese il 30-08 (la commessa va sui registri; niente periodicità nel sistema codici), piano scritto. Perimetro secco: **cambia solo l'algoritmo di assegnazione del numero** |
| **Fondo fattura — ricalcolo e governo** | [brief-db-fondo-fattura…](dev/work-in-progress/brief-db-fondo-fattura-ricalcolo-e-governo.md) | Cantiere **aperto**, con il suo piano in §8: la finestra non la apre il primo incasso, la apre il primo che scrive righe contabili |
| **Fan-out isolato / esito parziale** | [brief-be-fan-out…](dev/work-in-progress/brief-be-fan-out-isolato-e-esito-parziale.md) | Codice eseguito; ciò che resta sono **collaudi a video**, raccolti in §13 |
| **Fatturazione elettronica SDI** | payload pronto | Builder XML + persistenza esito. Dipende dal blocco `2.4`, che dipende dalle rate: ora esistono |
| **Liste configurabili / PrimeVue** | [piano-migrazione-primevue-5.md](dev/work-in-progress/piano-migrazione-primevue-5.md) | Disaccoppiamento **chiuso**; l'upgrade è fermo su una **decisione di licenza** (vedi Anello 1) |
| **Diagnostica di produzione senza accesso al DB** | [analisi-diagnostica…](dev/work-in-progress/analisi-diagnostica-produzione-senza-accesso-db.md) | Analisi aperta: comporre le fondamenta già esistenti, non fondarne di nuove |
| **Integrazione AI v2** | [integrazione-ai-sviluppo-v2.md](dev/work-in-progress/integrazione-ai-sviluppo-v2.md) | Contesto dinamico e nuovi tool |

### 🎯 Previsti — decisi ma non aperti

- **Secondo consumatore di `pratiche`** (Fase F, candidata assistenza/CRM): è ciò
  che promuove le sue astrazioni da *proposte* a *contratti* (manifesto §7)
- **Rettifiche prezzi (DB-L4)**: motore delta + canali manuale/automatico
- **Permessi v3** — sotto-oggetti padre/figlio (v2 a livello oggetto è operativa)
- **Autenticazione 2FA + provider esterni**
- **CRUD dei registri di numerazione**: `vendite.registri_fatturazione` non ha
  né rotta né maschera — per farne uno a mano serve una migrazione
- **Upload file allegati pratiche** (storage filesystem/object storage)

### 🧭 Decisioni aperte — non sono lavori

Stanno qui perché **bloccano** o **riorientano** dei lavori, e nessun piano
operativo può prenderle al posto di una persona.

| Decisione | Cosa blocca |
| --- | --- |
| 🚨 **Licenza PrimeVue** (MIT → PrimeUI su `primevue`, `@primeuix/themes`, `primeicons`) contro **GPL v3 pubblica** | l'upgrade a PrimeVue 5. Il lavoro tecnico è già fatto e vale con qualunque esito |
| **API di dominio portale/shop** (fatture, ordini, catalogo B2C) | l'infrastruttura auth è pronta e le policy RLS sono in dry-run: si apre «quando il business lo richiederà» |
| **Riconciliazione pratiche ↔ pipeline vendite** | i due motori di orchestrazione convivono per scope diversi; la decisione resta **rinviata**, non dimenticata |

### 🧹 Debito dichiarato — deve calare, e si misura

- **pgTAP**: **19 rossi noti** su 551 file (erano 86 su 442 il 10 agosto).
  ⚠️ Un file che fallisce nel *fixture* non esegue nessuna asserzione: la sua
  copertura vale **zero**, non «parziale», ed è un'area che *sembra* coperta
- **`DataTable` grezze**: **57 file** al 30-08, erano 48 il 3 agosto.
  ⚠️ **Il contatore non misura le liste**: 41 dei 57 sono drawer, dialog e
  pannelli annidati — l'eccezione che `AGENTS.md` ammette — e 6 sono i wrapper
  stessi. Il debito vero sta nelle **5 view di lista** e nelle 5 `*SearchTable`
  di dominio che non passano dal building block. ⛔ Il presidio a un numero solo
  non sa distinguerli: finché resta così, misura la crescita del frontend più
  del debito
- **Collaudi in-app aperti**: il giro incassi (`pagamenti` a zero righe),
  l'esito parziale del pull da commessa, le due voci residue dell'area RESI.
  ⚠️ Di quei percorsi è provato il *cammino*, mai l'*esito*
- **Debito documentale**: le 8 guide dei satelliti fattura; `pagamenti.sepa_mandati`
  senza `manual` e fuori dall'elenco della sua guida
- **Test UI reali** su Articoli, UoM, Pratiche, Soggetti, Clienti, Fornitori
- **Smoke UI end-to-end** del giro pratica PREVENTIVI (accettazione →
  smistamento → ordine/commessa)
- **Seed azioni di processo** per i domini ancora scoperti (vendite e pratiche
  sono seedate)

### 🌅 Lungo termine

- Tutti i processi di anello 3 usano `pratiche` per tracciabilita' e orchestrazione
- Il giornale di bordo diventa la vista unificata sulle attivita' dell'azienda
- Canali esterni (portale clienti, app tecnica) operano tramite flussi con visibilita' controllata

---
## 4 · Lezioni metodologiche

> Perché la mappa è fatta così. Non è stato: è l'**anticorpo** per chi
> costruirà il prossimo anello. Si legge una volta, non a ogni consultazione.

## Caso di studio: pratiche prima di vendite

> Lezione retrospettiva sull'ordine di costruzione (aggiunta 2026-04-25 dopo riflessione metodologica).
>
> Questa sezione esiste per dare al lettore futuro l'anticorpo che e' mancato a chi ha costruito ZeroERP. Non e' un'autocritica: e' documentazione di un pattern ricorrente che il manifesto in versione iniziale non descriveva.

### Cosa e' successo

L'ordine cronologico effettivo dello sviluppo e' stato:

1. **`pratiche` (Anello 2)** dichiarata Operativo su DB+BE+FE: 19 endpoint, 115 test, sospensioni, calcoli tempo, macchina a stati, giornale di bordo. Aprile 2026 con avvio in marzo.
2. **Nessun processo di Anello 3** consuma ancora pratiche. La matrice dipendenze segna `pratiche (FUTURO)` per vendite, acquisti, magazzino, pagamenti, contabilita'.
3. **`vendite` ha sviluppato infrastruttura propria di orchestrazione** (pipeline fatturazione, lotti, registry task DB multi-dominio, dispatch task con `implementation_key`, runtime task tracing) **in parallelo a pratiche**, senza usarla. Risultato: due motori di orchestrazione paralleli, due vocabolari, un'integrazione futura ancora da disegnare.
4. **L'autore ha riconosciuto il problema** mentre lavorava su listini → contratti → preventivi: "sto facendo questi sviluppi per avere aree dove iniziare ad applicare le pratiche". Cioe': costruire i consumatori per validare l'astrazione, l'inverso del workflow ipotizzato dal manifesto v1.

### Perche' e' successo

Il manifesto v1 prescriveva "cresci un anello per volta" e "ogni incremento chiude un percorso end-to-end reale". Applicato letteralmente a un anello **di servizio** come pratiche, questa regola produce **invenzioni**: un motore di workflow completo, perfettamente formato, ma con astrazioni decise a priori e mai esercitate dal dominio reale.

Pratiche **non ha un end-to-end suo** — il suo end-to-end richiede un consumatore di Anello 3. Senza quel consumatore, le decisioni di design (cosa mette nel giornale, come modella un flusso, quali handler espone, cosa significa "sospensione") sono ipotesi del progettista, non risposte a esigenze osservate.

### Conseguenze concrete

- **Doppia infrastruttura di orchestrazione** in coesistenza: pratiche (giornale + flussi + macchina a stati) e vendite-pipeline (task runs + registry + dispatch). Nate per esigenze diverse, ma con sovrapposizione concettuale che andra' riconciliata. Costo nascosto del modello concentrico applicato troppo presto.
- **Vocabolario non condiviso**: pratiche parla di "flusso/step/handler_key/canali", vendite parla di "lotto/task/registry_impl/runtime tracing". Quando si dovra' integrare, si scoprira' che lo stesso concetto ha due nomi e due forme.
- **Test contro un'idea, non contro un caso d'uso**: i 115 test di pratiche verificano che il motore funzioni come progettato, non che risolva problemi reali della prima vendita o del primo onboarding.

### Cosa avremmo dovuto fare

Lo schema corretto per anelli di servizio e':

1. Aprire pratiche come **stub minimo** (modello dati base + servizio facade vuoto), Stato "Predisposto".
2. Aprire **vendite** o un altro processo di Anello 3 con un caso d'uso concreto end-to-end.
3. Quando vendite genera il primo evento da tracciare (es. "ordine creato"), **far emergere** il giornale di pratiche per servirlo. Il giornale nasce come risposta a una domanda concreta.
4. Quando un secondo processo (es. acquisti) chiede di tracciare i suoi eventi, **promuovere al nucleo di pratiche** le astrazioni che si ripetono, scartare quelle specifiche di vendite.
5. Solo dopo questo passaggio (manifesto principio 7) le astrazioni di pratiche diventano *contratti*; prima sono *proposte*.

### Come uscirne ora

Pratiche e' costruita. Disfarla sarebbe spreco. La via realistica:

- **Marcatura onesta**: ✅ percorso completato (2026-06-12) — pratiche e' passata da "predisposta" a **"validata con primo consumatore (vendite)"** (vedi Anello 2). La validazione ha confermato la lezione: l'uso reale ha scovato bug invisibili ai test (handler_params persi, fn di push con NOT NULL violabili, generazione non idempotente, azioni di processo mai seedate) che la "completezza tecnica" non aveva intercettato.
- **Prima integrazione concreta**: ✅ fatta — pratica PREVENTIVI end-to-end (accettazione M2, handler CONFERMA_VENDITA, giornale, sorgenti).
- **Riconciliazione con vendite-pipeline**: la decisione resta **rinviata** — i due motori convivono per scope diversi (pratica = processo singolo guidato dall'operatore; pipeline = batch fatturazione); il punto di contatto validato e' la commessa resa emittibile dal push.
- **Riserva di modifica**: con UN consumatore validato la riserva si restringe ma non decade: le astrazioni si promuovono a contratto solo col **secondo** consumatore (Fase F). Fino ad allora pratiche resta modificabile con prudenza (i test — 144 BE + 43 pgTAP workflow v2 — sono base di regressione solida, non ancora contratto).

### Lezione metodologica

**Per ogni anello classificato "di servizio" nella mappa, non costruirlo prima dei suoi consumatori.** Aprilo come stub se serve un punto di aggancio, ma non investire in completezza tecnica finche' non c'e' uso reale che lo eserciti. La completezza senza uso e' debito tecnico travestito da progresso.

### Esempio virtuoso opposto: framework `dbops.automazione_chiusura_scadenze` (26-04-2026)

Il caso pratiche e' istruttivo perche' mostra cosa succede applicando il manifesto v1 a un anello di servizio. Per contrasto, il framework `dbops.automazione_chiusura_scadenze` e' l'**applicazione corretta del principio 7** appena introdotto.

**Cronologia**:

1. **24-04-2026 — primo caso reale**: implementato il pattern "ciclo stato + finestra di validita'" per `vendite.listini_versioni` come componente specifico del dominio (funzione `vendite.fn_listini_versioni_close_scadute()` + job pgAgent dedicato + guard transizione hardcoded). Nessuna astrazione prematura.
2. **25-26-04-2026 — secondo consumatore**: emerge la stessa esigenza per `vendite.contratti` (cessazione data-driven). I requisiti sono **strutturalmente identici** al caso listini, salvo la differenza VARCHAR vs FK come tipo di colonna stato.
3. **26-04-2026 — promozione al nucleo**: con due consumatori reali (non ipotetici), il pattern viene **estratto in `dbops`** come framework parametrico:
   - tabella di configurazione `dbops.automazione_chiusura_scadenze` con discriminator `tipo_stato` (VARCHAR/FK)
   - funzione motore `dbops.fn_apply_chiusura_scadenze()` con SQL dinamico + pre-check + audit
   - job pgAgent unico `chiusura_scadenze_daily` che sostituisce il job specifico precedente
   - vecchia funzione `fn_listini_versioni_close_scadute` droppata
4. **Aggiunte future**: una nuova tabella al pattern non richiede piu' nuovo codice DB — basta una INSERT seed nella tabella di configurazione.

**Differenza con il caso pratiche**:

| Aspetto                      | Pratiche (errore v1)                              | Framework chiusura (corretto v2)                                |
| ---------------------------- | ------------------------------------------------- | --------------------------------------------------------------- |
| Quando e' stato astratto     | Prima di qualunque consumatore reale              | Dopo due consumatori reali con requisiti identici               |
| Generalita' delle astrazioni | Decise dal progettista a priori                   | Decantate dal pattern emerso dai due casi                       |
| Validazione                  | Test contro un'idea progettuale                   | Test contro casi d'uso reali (listini + contratti)              |
| Costo se non si usa          | Spreco di lavoro, doppia infrastruttura parallela | Nullo (stub minimale solo se serve, oppure non si fa fino a 2°) |

**Cosa cambia nei tre piani della mappa**:

- Anello 0 cresce per *uso esterno*, non per *progetto interno*: la riga `dbops.automazione_chiusura_scadenze` aggiunta a "Cosa fornisce agli anelli esterni" deriva da bisogni concreti dei processi.
- Anello 3 (vendite) acquisisce un secondo punto di chiusura per scadenza (contratti) **senza dover scrivere infrastruttura propria**: usa il framework gia' validato.
- La promozione e' *non-breaking*: il job specifico precedente e' rimosso, ma il comportamento esterno (versioni listino chiuse a scadenza) e' identico — solo il motore sotto e' cambiato.

**Lezione metodologica generalizzata**:

> **La differenza non sta nel "se astrarre", ma nel "quando".** Astrarre prima di vedere e' progetto; astrarre dopo aver visto e' sintesi. Il manifesto §7 codifica questa distinzione perche' la prima e' debito travestito da architettura, la seconda e' architettura genuina.

Riferimento implementazione: `docs/it/dev/work-done/automazione-chiusure-scadenze.md`.

---


## 5 · Come aggiornare questo documento

1. **Nuovo componente**: aggiungere nella tabella dell'anello corretto (§2), con stato DB e Backend
2. **Cambio stato**: aggiornare la colonna Stato (Stub → Parziale → Operativo)
3. **Nuova dipendenza**: aggiungere nella matrice (§2) e verificare che rispetti la direzione degli anelli
4. **Nuovo anello**: se emerge un livello intermedio, inserirlo e ri-numerare
5. **Milestone datata**: riscrivere «Ultimo aggiornamento» in testa e **spostare il precedente nel [changelog](dev/mappa-concentrica-changelog.md)** — la storia vive lì, non qui

### ⚠️ Le tre derive che hanno gonfiato questo documento

Sono già successe. Riconoscerle costa meno che disfarle.

| Deriva | Come si riconosce | Dove va invece |
| --- | --- | --- |
| **Cronologia nelle tabelle di stato** | righe con una data e la parola «fatto» | nel changelog |
| **Rifiniture spacciate per lavori in corso** | «operativo — UI da migliorare» dentro la roadmap | nella tabella del suo anello |
| **Voci senza documento** | una riga di roadmap che nessun brief sostiene | sotto «Previsti», o via |

> La mappa deve riflettere la **realtà**, non le intenzioni — e nemmeno il
> **ricordo**. Se una voce non si può verificare oggi contro il codice o un
> documento vivo, non è stato: è memoria.

---

*Mappa Concentrica — ZeroERP (30 agosto 2026)*
