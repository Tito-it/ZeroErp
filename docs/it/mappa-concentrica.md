# Mappa Concentrica — Stato dello Sviluppo ZeroERP

> Documento vivo. Aggiornare ad ogni milestone significativa.
>
> Riferimento metodologico: [sviluppo-concentrico.md](sviluppo-concentrico.md)

*Ultimo aggiornamento: 29 maggio 2026 — Anello 3 (vendite): contratti passati al modello unificato (drop modalità A/B/C, eccezioni `tipo_eccezione`, snapshot versione listino all'attivazione, lock post-attivazione, stato ANNULLATO); nuovo documento **offerte commerciali** (proposta di condizioni quadro → push 1:1 a contratto) sviluppato DB+BE+FE con generazione PDF e allegati; componenti BoM compositi estesi a offerte; valuta su documenti vendite. Vedi [Gestione Offerte commerciali](guide/gestione-offerte-commerciali.md) e [Gestione Contratti](guide/gestione-contratti.md).*
>
> *Aggiornamento precedente: 6 maggio 2026 — aggiunto componente `ui` in Anello 1 (metadato di presentazione: liste configurabili, personalizzazione colonne, preset per profilo/emittente). Stato allora: Da fare → **ora Operativo** (vedi tabelle Anello 1). Architettura completa in [sviluppo-personalizzazioni-liste.md](dev/work-in-progress/sviluppo-personalizzazioni-liste.md).*

---

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

## Aggiornamenti ricostruiti dal 26 aprile al 29 maggio 2026

Questa sezione registra solo evidenze presenti nel repository locale: commit e documentazione `docs/it/dev/work-done/` o `docs/it/dev/work-in-progress/`. Dove la documentazione indica test UI o working tree non ancora consolidato, lo stato resta esplicitamente marcato come tale.

| Data         | Evidenza                                                                                                                                             | Impatto sulla mappa                                                                                    |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| 26 aprile    | `dbops.automazione_chiusura_scadenze` chiuso come framework parametrico dopo due consumatori reali (`vendite.listini_versioni`, `vendite.contratti`) | Anello 0 cresce per uso osservato, non per astrazione preventiva.                                      |
| 27 aprile    | Contratti: Profilo A, immutabilita' post-DRAFT, cessazione data-driven, righe-preview                                                                | Vendite rafforza il sottodominio contratti e consuma il framework di chiusura a scadenza.              |
| 28 aprile    | Refactor frontend/backend catalogo completato Fasi 1-8, test BE 83/83 e build Vite verdi                                                             | Catalogo resta operativo ma con contratti API/metadata piu' maturi.                                    |
| 29-30 aprile | Refactor amm-software completato per matrici, operatori, permessi, emittenti e policy admin                                                          | Anello 1 amministrativo consolidato; le matrici diventano riferimento UI per configurazioni complesse. |
| 1 maggio     | Refactor vendite chiuso DB+BE+FE, modello documentato con 1406 test BE e build Vite verde                                                            | Vendite aggiornata a pattern data-driven per lookup, defaults, capability e azioni.                    |
| 2 maggio     | Preventivi rev2 landed: `emittente_fiscale_id` persistito, `istanza_utility_id` obbligatoria, guard coerenza utility/istanza, 4 codici errore        | Preventivi diventano piu' rigorosi sul contesto emittente/utility.                                     |
| 3 maggio     | Scenario preventivi 2.1 chiuso end-to-end, UI revisioni e riepilogo IVA                                                                              | Vendite avanzata su flusso preventivo operativo.                                                       |
| 3-4 maggio   | Motore documentale parametrico: DB Fase A, backend Tranche A-K, frontend Tranche L-M; test UI dedicato avviato                                       | Nuovo componente `documenti` in Anello 2, operativo tecnicamente ma ancora in test UI.                 |
| 13 maggio    | BoM modello unificato + simmetria listino; componenti BoM (CASO A) estesi a preventivi/ordini/ddt/contratti                                          | I documenti vendite condividono lo stesso modello componenti a 3 livelli (struttura, listino, documento). |
| 15-21 maggio | Refactor contratti: modello unificato (drop modalità A/B/C, eccezioni `tipo_eccezione`, snapshot versione listino all'attivazione, lock post-attivazione, stato ANNULLATO + overlap parziale) | Il sottodominio contratti diventa simmetrico ai preventivi e pronto a ricevere l'offerta come sorgente. |
| 24-27 maggio | Offerte commerciali (DB): testata + eccezioni delta-listino + componenti BoM + utility, 6 stati, `fn_push_offerta_a_contratto` idempotente, vista `is_attiva`, azioni data-driven | Nuovo documento pre-contrattuale in Anello 3 (vendite): la proposta di condizioni quadro che genera il contratto. |
| 28-29 maggio | Offerte commerciali (BE+FE): risoluzione prezzo come contratti, generazione documento offerta con allegati, UI uniformata a contratti                | Offerta operativa end-to-end DB+BE+FE; in consolidamento/test UI.                                       |
| 29 maggio    | Valuta su documenti vendite (`valuta_id` su offerte/contratti/preventivi, default da resolver gestore); guida offerte commerciali pubblicata          | Coerenza valuta cross-documento; documentazione di dominio allineata allo stato reale.                  |

### Natura degli anelli (post-aggiornamento manifesto §III bis)

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

## Anello 0 — Nucleo Infrastrutturale

> **Natura: di servizio.** Il protocollo operativo del sistema. Si tocca solo per correggere limiti reali.

| Componente    | Tipo       | Stato     | Descrizione                                                                                                                                                                               |
| ------------- | ---------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `core`        | App Django | Operativo | error_manager, middleware, permissions, endpoint_helpers, pagination, throttling, tracciamento processi/job, audit sessioni, request log                                                  |
| `dbops`       | Schema DB  | Operativo | fn_run_automations, apply_fk_index_policy, registry task, vw_duplicate_indexes, audit_log, sessioni_utente, request_log, **automazione daterange**, **chiusura parametrica per scadenza** |
| `script`      | Schema DB  | Operativo | fn_log_and_raise_error, viste e funzioni riusabili, helpers generici trigger (guard coerenza BoM, immutabilita`)                                                                          |
| `public`      | Schema DB  | Operativo | version_info                                                                                                                                                                              |
| `maintenance` | Schema DB  | Operativo | Job schedulati pgAgent, job_run_log                                                                                                                                                       |

### Cosa fornisce agli anelli esterni

- Error handling centralizzato (`ServiceError`, `ErrorManager.require`)
- Middleware API (exception handling, JWT audit, request context, request log)
- Pattern uniformi: `handle_post_json`, paginazione, throttling, search validators
- Automazioni DB: audit fields, tx_id, storicizzazione, lock colonne, protezione attivo, **`validita` STORED generated** (PG 18, nessun trigger), chiusura parametrica per scadenza (`dbops.fn_apply_chiusura_scadenze`)
- **Tracciamento processi e job**: API per audit log, task registry multi-dominio, job run log (6 endpoint REST, 27 test)
- **Audit sessioni**: login/refresh JWT tracciati in `dbops.sessioni_utente` con IP, user_agent, request_id (19 test)
- **Request logging**: ogni request `/api/*` registrata in `dbops.request_log` con metodo, path, status, durata
- **Token blacklist**: refresh token rotation con blacklist automatica (SimpleJWT `token_blacklist`)
- Policy indici FK automatica
- Logging e raise errori DB (`script.fn_log_and_raise_error`)

### Audit sessioni, request logging e token blacklist

Implementato il 6 marzo 2026 (vedi [Audit-logging-sessionii-request-token.md](dev/work-done/Audit-logging-sessionii-request-token.md)):

| Capacita'                         | Componente DB               | Componente Backend                                                             | Stato     |
| --------------------------------- | --------------------------- | ------------------------------------------------------------------------------ | --------- |
| Audit sessioni (login/refresh)    | `dbops.sessioni_utente`     | `session_audit_service` + `AuditTokenObtainPairView` / `AuditTokenRefreshView` | Operativo |
| Request logging (chi chiama cosa) | `dbops.request_log`         | `RequestLogMiddleware`                                                         | Operativo |
| Token blacklist e revoca          | SimpleJWT `token_blacklist` | Settings `ROTATE_REFRESH_TOKENS` + `BLACKLIST_AFTER_ROTATION`                  | Operativo |

Estensioni non-breaking: nuove tabelle in `dbops`, nuovo middleware in `core`, override view JWT. Nessun contratto esistente modificato. Gli anelli esterni ne beneficiano automaticamente senza alcuna modifica al proprio codice.

### Stabilita'

Stabile. Modifiche solo per correzioni o estensioni non-breaking (nuove policy, nuovi middleware).

---

## Anello 1 — Dati Base e Configurazione

> **Natura: autocontenuto.** Entita' di riferimento condivise da tutti i processi. Vocabolario comune del sistema.

| Componente     | Tipo       | DB        | Backend   | Frontend  | Descrizione                                                                                                                |
| -------------- | ---------- | --------- | --------- | --------- | -------------------------------------------------------------------------------------------------------------------------- |
| `config`       | App Django | Operativo | Operativo | Operativo | Stati, nazioni, UO, termini pagamento, priorita', canali; policy operative trasversali; impostazioni parametri multi-scope |
| `anagrafiche`  | App Django | Operativo | Operativo | Operativo | Soggetti, indirizzi, contatti, risorse umane, emittenti fiscali, billing account                                           |
| `catalogo`     | App Django | Operativo | Operativo | Operativo | Articoli (CRUD, UoM, BoM, note) — **completato e testato** (work-done/gestione-articoli.md)                                |
| `amm-software` | App Django | Operativo | Operativo | Operativo | Gestione operatori, permessi riepilogo, profili reparto, audit log (solo ADMIN), drawer dedicato gestione permessi         |
| `ui`           | App Django | Operativo | Operativo | Operativo | Metadato di presentazione: liste configurabili, preset per profilo/emittente/sistema, preferenze utente. Di servizio. Schema, app Django e componenti FE implementati (primi consumatori: liste clienti/fornitori). |

> **Multi-Face Auth — COMPLETATO (22-04-2026):** `anagrafiche` usa il bridge generalizzato `identita_digitali` (SSO multi-veste, cutover 19-04-2026). `amm-software` supporta operatori, portale clienti/fornitori e shop B2C. **Infrastruttura auth predisposta per tutte le vesti; le API di dominio portale/shop (fatture, ordini, catalogo B2C) non sono ancora sviluppate e saranno affrontate quando il business lo richiedera'.** Dettaglio: [pr-b-shop-b2c-cambio-modello.md](dev/work-done/pr-b-shop-b2c-cambio-modello.md). Guida: [architettura-multi-face-auth v2.0](guide/architettura-multi-face-auth.md).

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
| UI — Liste (Frontend)           | Operativo  | `ListaConfigurabile.vue`, `ListaColonneModal.vue`, `useListaConfig` + viste admin (Gestione/Personalizzazioni liste). Primi consumatori: liste clienti/fornitori.                           |

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

Riferimento architetturale: [sviluppo-personalizzazioni-liste.md](dev/work-in-progress/sviluppo-personalizzazioni-liste.md). Sviluppi differiti: [sviluppo-personalizzazioni-liste_def.md](dev/work-in-progress/sviluppo-personalizzazioni-liste_def.md).

### Stabilita'

Stabile. Cresce per aggiunta di nuove tabelle config (es. `config.canali_pratiche` aggiunta per pratiche) senza rompere quanto esistente.

---

## Anello 2 — Orchestrazione di Dominio

> **Natura: di servizio.** Motore trasversale che gli anelli esterni usano per tracciare, orchestrare e automatizzare.
>
> ⚠️ **Validazione esterna: in corso.** Per `pratiche`, il motore e' stato dichiarato Operativo su DB+BE+FE prima che un processo di Anello 3 lo consumasse realmente. Stato attuale: **predisposto, in attesa di validazione** dal primo consumatore reale (vendite). Vedi [Caso di studio: pratiche prima di vendite](#caso-di-studio-pratiche-prima-di-vendite). Per `documenti`, il primo consumatore reale e' `vendite.preventivi`, ma la validazione resta in test UI. Solo dopo che almeno due processi di Anello 3 avranno usato questi motori end-to-end le loro astrazioni si potranno considerare *contratti* nel senso del manifesto principio 1; fino a quel momento sono *proposte* (manifesto principio 7) e modificabili senza il rigore di un nucleo stabile.

| Componente  | Tipo       | DB        | Backend   | Frontend   | Descrizione                                                                                                                                                          |
| ----------- | ---------- | --------- | --------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pratiche`  | App Django | Operativo | Operativo | Operativo  | Workflow engine, giornale, generazione cross-pratica, handler dispatch, sospensioni, calcoli tempo, macchina a stati, note, allegati                                 |
| `documenti` | App Django | Operativo | Operativo | In test UI | Motore documentale parametrico: template versionati, asset documentali, render PDF WeasyPrint, archivio documenti generati, lista/download da preventivo come pilota |

### Cosa fornisce agli anelli esterni

- **Pratiche**: contenitore tracciabile per qualsiasi processo (onboarding cliente, gestione ordine, assistenza tecnica)
- **Flussi**: step operativi con prerequisiti, esiti, scadenze, assegnazione risorse
- **Giornale di bordo**: audit trail immutabile, append-only, con correlazione `tx_id`
- **Generazione cross-pratica**: un flusso completato puo' generare automaticamente nuove pratiche
- **Handler dispatch**: mapping `handler_key` → classe Python per automazione step
- **Canali**: visibilita' dei flussi su sorgenti esterne (WEB_CLIENTI, APP_TECNICA, PORTALE_FORNITORI)
- **Sospensioni**: fermo temporaneo pratica/flusso con propagazione automatica e riattivazione (manuale o pgAgent)
- **Calcoli tempo**: tracking tempi netti tra coppie di flussi (formula da/a), con esclusione giorni sospensione
- **Macchina a stati rigida**: transizioni ammesse validate da trigger DB (config-driven)
- **API interna**: `pratiche_service` come facade per gli anelli esterni
- **Documenti parametrici**: template e versioni separati dai dati, asset per emittente fiscale, PDF finale archiviato con hash, utente e data generazione
- **Render PDF**: backend con Jinja2 + WeasyPrint, storage configurato via parametri, generazione/lista/download esercitati dal preventivo come primo consumatore

### Perche' e' un anello separato (non anello 1)

`pratiche` non e' un dato di riferimento statico — e' un **motore di orchestrazione con stato e ciclo di vita**. Dipende da anello 1 (config, anagrafiche) per le FK, ma fornisce capacita' operative che gli anelli esterni consumano. E' il cuore operativo del sistema: ogni evento significativo (nuovo cliente, nuovo ordine, nuova assistenza) genera una pratica con il suo giornale.

### Perche' non e' anello 3 (processi)

Non e' un processo di business specifico (come vendite o acquisti). E' l'**infrastruttura di processo** che tutti i domini usano. E' al servizio dei processi, non un processo in se'.

### Stato sviluppo dettagliato

**v1 (4-6 marzo 2026):**

| Fase                       | Stato | Riferimento                                                   |
| -------------------------- | ----- | ------------------------------------------------------------- |
| DB-1..DB-7                 | FATTO | Tabelle, funzioni, trigger, seed, test pgTAP                  |
| BE-1..BE-5                 | FATTO | App setup, repository, service, API (19 endpoint), 90 test    |
| BE-6 Sospensioni + Calcoli | FATTO | Service, repository, API, 26 test unitari, 18 smoke test curl |
| BE-7 Macchina a stati      | FATTO | Transizioni validate da trigger DB (config-driven)            |

**v2 (28-29 marzo 2026):**

| Fase                           | Stato | Riferimento                                                                       |
| ------------------------------ | ----- | --------------------------------------------------------------------------------- |
| DB: collegamento ruolo/istanza | FATTO | ALTER + trigger guard contesto + codice PRA via sistema_codici                    |
| BE: JOIN display fields        | FATTO | list/get pratiche e flussi con 7 JOIN, named columns (no indici posizionali)      |
| BE: contesto anagrafico        | FATTO | soggetto_id + soggetto_ruolo_id + istanza_utility_id, validazione coerenza        |
| BE: guard pre/post-attivazione | FATTO | Verifica stato BA del soggetto per tipo prestazione                               |
| BE: order_by + search          | FATTO | Ordinamento dinamico con whitelist, ricerca ILIKE su codice/descrizione/soggetto  |
| BE: filtro data                | FATTO | data_da/data_a con default anno-1                                                 |
| BE: note CRUD                  | FATTO | 4 endpoint (GET/POST/PATCH/DELETE), 6 test, giornale trigger                      |
| BE: allegati CRUD              | FATTO | 3 endpoint (GET/POST/DELETE, immutabili), 4 test, giornale trigger                |
| FE: lista pratiche             | FATTO | SearchTable con filtri (stato, priorita', data_da/data_a, search), display fields |
| FE: drawer dettaglio           | FATTO | 5 tab (Dati, Flussi, Note, Allegati, Giornale), azioni stato, severity            |
| FE: drawer creazione           | FATTO | Soggetto opzionale (SoggettoResolver), ruolo, tipo prestazione, priorita'         |
| FE: tab flussi                 | FATTO | Lista compatta, crea/avvia/completa flusso inline                                 |
| FE: tab note                   | FATTO | Form inline crea + lista con edit/delete                                          |
| FE: tab allegati               | FATTO | Lista metadati con delete (upload posticipato)                                    |
| FE: tab giornale               | FATTO | Timeline audit con icone/severity per tipo azione                                 |
| Test totali                    | 115   | 105 Django (mock CI) + 25 smoke test bash                                         |

Documentazione: [gestione-pratiche-v2.md](dev/work-in-progress/gestione-pratiche-v2.md) | API: [api_pratiche_list](backend/pratiche/manual/api_pratiche_list) | [api_pratiche_note](backend/pratiche/manual/api_pratiche_note) | [api_pratiche_allegati](backend/pratiche/manual/api_pratiche_allegati)

Piano v1 (storico): [work-done/piano-gestione-pratiche.md](dev/work-done/piano-gestione-pratiche.md)

---

## Anello 3 — Processi Operativi

> **Natura: autocontenuti (ciascuno).** Cicli di business che usano anelli interni. Ogni processo e' autonomo ma condivide vocabolario e infrastruttura.

| Componente    | Tipo       | DB        | Backend   | Descrizione                                                                                                                                                                   |
| ------------- | ---------- | --------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `vendite`     | App Django | Operativo | Operativo | Ciclo attivo: preventivi rev2, contratti, ordini, DDT, fatture, pipeline fatturazione, lotti, commesse, **listini v3**, generazione PDF preventivo via `documenti` in test UI |
| `acquisti`    | App Django | Operativo | Stub      | Ciclo passivo: richieste offerta, ordini, DDT, fatture                                                                                                                        |
| `magazzino`   | App Django | Operativo | Stub      | Movimenti, giacenze, lotti, seriali                                                                                                                                           |
| `pagamenti`   | App Django | Operativo | Stub      | Scadenze, riconciliazioni                                                                                                                                                     |
| `contabilita` | App Django | Operativo | Stub      | Piano conti, registrazioni, partite                                                                                                                                           |
| `storico`     | App Django | Operativo | Stub      | Audit temporale, storicizzazione                                                                                                                                              |

### Dipendenze verso anelli interni

```
vendite ──────► config (stati_doc_fiscale, termini_pagamento)
              ► anagrafiche (soggetti, emittenti_fiscali)
              ► catalogo (articoli, UoM, listini)
              ► core (error_manager, endpoint_helpers)
              ► documenti (generazione/lista/download PDF preventivo)
              ► pratiche (FUTURO — giornale, workflow)

acquisti ─────► stesse dipendenze di vendite
              ► pratiche (FUTURO)
```

### Integrazione futura con pratiche

`pratiche` e' operativo a livello DB+BE+FE, ma resta da validare come servizio consumato da processi di Anello 3. I processi di anello 3 potranno:

1. **Creare pratiche** per i propri eventi (`pratiche_service.crea_pratica`)
2. **Alimentare il giornale** con eventi di dominio (nuovo cliente → PRATICA_CREATA)
3. **Usare flussi** per step operativi tracciati (approvazione ordine, sopralluogo, collaudo)
4. **Sfruttare generazione cross-pratica** (ordine completato → genera pratica assistenza)

I processi **massivi** (lotto fatturazione, import batch) mantengono la propria infrastruttura di tracking (pipeline, task runs, log fatture) perche' hanno requisiti diversi (parallelismo, resume per singola fattura, tracing per step). Il giornale di pratiche traccia eventi a livello di **processo singolo**, non di batch.

### Stato sviluppo vendite (app leader)

| Area                                    | Stato                                                                         |
| --------------------------------------- | ----------------------------------------------------------------------------- |
| Pipeline fatturazione                   | Operativo                                                                     |
| Lotti massivi/giornalieri               | Operativo                                                                     |
| Registry task DB multi-dominio          | Operativo                                                                     |
| Dispatch task con implementation_key    | Operativo                                                                     |
| Runtime task tracing                    | Operativo                                                                     |
| Builder XML SDI                         | In corso (payload pronto, generazione XML da fare)                            |
| Persistenza esito SDI                   | Da fare                                                                       |
| Commesse (push, orchestrator, handlers) | Operativo                                                                     |
| Listini v3 (N2/N5/N6/N7/N8a)            | Operativo — Sprint B-v3 completato (aprile 2026)                              |
| Pricing commesse (N5/N7/N7-sblocco)     | Operativo — riallineamento, variazione, sblocco                               |
| Contratti (modello unificato)           | Operativo — drop modalità A/B/C, eccezioni `tipo_eccezione`, snapshot versione listino, lock post-attivazione, stato ANNULLATO |
| Offerte commerciali                     | Operativo (DB+BE+FE), in consolidamento — proposta condizioni quadro → push 1:1 a contratto; componenti BoM; generazione documento + allegati |
| Componenti BoM compositi (vendite)      | Operativo — modello a 3 livelli condiviso da preventivi/contratti/offerte/ordini/ddt |
| Valuta su documenti                     | Operativo (DB) — `valuta_id` su offerte/contratti/preventivi, default da resolver gestore |
| Preventivi rev2                         | Operativo — emittente persistito, istanza obbligatoria, guard utility/istanza |
| Revisioni preventivo + riepilogo IVA    | Operativo — scenario 2.1 chiuso end-to-end                                    |
| Generazione PDF preventivo              | In test UI — primo consumatore del motore `documenti`                         |

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
vendite          usa     usa      usa      usa    (futuro)     usa          -
acquisti         usa     usa      usa      usa    (futuro)   (futuro)      -
magazzino        usa     usa      usa       -     (futuro)      -           -
pagamenti        usa     usa       -        -     (futuro)      -           -
contabilita      usa     usa       -        -     (futuro)      -           -
```

Nessuna dipendenza inversa. Nessuna dipendenza laterale tra processi di anello 3.

Gli anelli esterni possono dipendere direttamente da anelli non adiacenti — vendite usa `core` e `config` senza passare per `pratiche`. Questo non viola la direzione delle dipendenze, sempre dall'esterno verso l'interno: descrive semplicemente come certi tipi di informazione attraversano il tronco (la linfa, nella metafora del vocabolario).

---

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

- **Marcatura onesta**: pratiche resta Operativo a livello tecnico, ma nella mappa e' classificata "predisposta, validazione in corso con vendite" (vedi Anello 2).
- **Prima integrazione concreta**: scegliere il primo evento di vendite che vale la pena tracciare in pratiche (probabilmente "ordine creato" o "preventivo accettato") e farlo end-to-end. Da li', osservare cosa serve davvero e cosa non serve.
- **Riconciliazione con vendite-pipeline**: dopo la prima integrazione, decidere se i due motori si fondono, restano paralleli per scope diversi (single-process vs batch), o se uno assorbe l'altro. La decisione va **rinviata**, non presa adesso senza dati.
- **Riserva di modifica**: finche' la validazione non e' completa, pratiche puo' essere modificata senza il rigore previsto per il nucleo (manifesto principio 1). I test attuali sono base di regressione, non sono contratto.

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

Riferimento implementazione: [WIP automazione-chiusure-scadenze.md](dev/work-done/automazione-chiusure-scadenze.md).

---

## Evoluzione prevista

### Completato (marzo 2026)

- ~~Completamento BE-1..BE-5 per `pratiche`~~ — **FATTO** (4 marzo 2026)
- ~~Sospensioni, calcoli tempo, macchina a stati (BE-6..BE-7)~~ — **FATTO** (6 marzo 2026)
- `pratiche` e' consumabile dagli anelli esterni (19 endpoint REST, 90 test unitari, 18 smoke test)
- ~~Audit sessioni, request logging, token blacklist~~ — **FATTO** (6 marzo 2026)
- Anello 0 traccia sessioni JWT, request API e supporta revoca token (19 test unitari)
- ~~Frontend Sprint 1: layout applicativo~~ — **FATTO** (marzo 2026)
  - AppLayout responsive (sidebar morfica, content tabs, breadcrumb, shortcut tastiera)
  - Ricerca universale soggetti con dettaglio parametrico per ruolo
- ~~Frontend Sprint 2: Amm. Software~~ — **FATTO** (marzo 2026)
  - Lista operatori con filtri, creazione/modifica operatore, profili reparto
  - Building block repository core (52 test)
- ~~Frontend Sprint 3: Building block riutilizzabili~~ — **FATTO** (marzo 2026)
  - SoggettoForm universale PF/PG/ENTE, AuthUserForm, ComuneAutocomplete, StradarioAutocomplete
  - Composable core: useLookup, useServerAutocomplete, useSoggettoForm, useAuthUser
  - CSS utility classes: app-page, app-datatable, form-grid, app-drawer-content
- ~~Frontend Sprint 4: Gestione Geografica~~ — **FATTO** (15 marzo 2026)
  - 7 tab CRUD: indirizzi, toponomastica, comuni, CAP, province, regioni, stati
  - 21 endpoint API con autorizzazione area `anagrafiche`, 657 test backend
  - Composable centralizzati: useSearchTable, useDrawerState, useTabFreshness, DrawerFooter, NewButton
- ~~Frontend Sprint 5: Gestione Soggetti~~ — **FATTO** (15 marzo 2026)
  - Soggetti PF/PG/ENTE end-to-end: 4 fasi, 3 building block, 11 endpoint, CF validator IT con omocodia
  - Building block riutilizzabili: ContattoForm, IndirizzoSoggettoForm, DatiSocietariForm + composable
  - Ruoli: assegnazione da drawer, lookup filtrato per natura, preparazione domini futuri
  - Pannello config generico: 67 tabelle CRUD con drawer dinamico metadata-driven
  - Code review: fix race condition watcher, cleanup timeout, eliminato doppio fetchList
  - 686 test backend, 471 moduli frontend
- ~~Frontend Sprint 6: Fix indirizzi + contatti soggetto~~ — **FATTO** (16 marzo 2026)
  - Fix gestione contatti (combo unita' organizzative, validazione email/PEC)
  - Fix gestione indirizzi soggetto (pre-populate replace, civico/estensione)
- ~~Refactor v3: Riallineamento modello concentrico~~ — **FATTO** (18 marzo 2026)
  - Logica duplicato centralizzata in `fn_check_indirizzo_duplicato` (DB)
  - CAP risolto via `fn_resolve_codice_postale` (DB)
  - `useIndirizzoBase.js` composable condiviso (elimina duplicazione IndirizzoDrawer/IndirizzoSoggettoForm)
  - `via_obj` unificato (elimina stradario_obj + stradario_generale_obj)
  - Default soggetti spostati da hardcode Python a `config.parameters` (DB source of truth)
  - Ordinamento tabelle config funzionante (order_by/order_dir)
  - 689 test backend
- ~~Refactor v4: Completamento modello concentrico~~ — **FATTO** (18 marzo 2026)
  - Auto-clone indirizzi spostato da frontend a backend (`_apply_auto_clone`)
  - `_buildNominativo` spostato nel service Python
  - `addressNotFound` centralizzato in `useIndirizzoBase`
  - Payload replace semplificato (usa `indirizzo_dettaglio_id` diretto)
- ~~Modalita' sola lettura~~ — **FATTO** (18 marzo 2026)
  - Pattern protect provide/inject: 11 drawer, 3 view, 2 componenti core auto-hide
  - DB: `fn_get_user_permissions_map`, `/me/` arricchito con `permessi_area`
- ~~Documentazione API~~ — **FATTO** (18 marzo 2026)
  - 57 endpoint documentati: soggetti, indirizzi, geo config, amm. software
  - 3 doc esistenti aggiornate: lookup codici, user profile, api overview

- ~~Frontend Sprint 7: Amm. Software completa + Permessi Livello 1+2~~ — **FATTO** (20 marzo 2026)
  - Area Amm. Software: 4 pagine operative (operatori, profili reparto, permessi riepilogo, audit log)
  - Refactor naming utenti→operatori su tutto lo stack (backend, frontend, test, doc, smoke test)
  - Livello 1 consolidato: useReadonlyMode su tutte le view, app-readonly su tutti i drawer
  - Livello 2 azioni processo: prop `action` su NewButton/DrawerFooter, composable useActionPermission
  - DB: fn_get_user_actions_map + fn_get_user_profile arricchito con azioni_abilitate
  - Costanti enum centralizzate in core/constants.js (RUOLO_SISTEMA, LIVELLO_ACCESSO)
  - Helper severity riutilizzabili, useConfirmAction (confirmSave/Delete/Action), displayTimestamp
  - Audit qualita': fix race condition, null safety, SQL validation, toast validazione
  - Sort default: soggetti (ragione_sociale), operatori (cognome), audit (timestamp DESC)

- ~~Frontend Split View (tab affiancate)~~ — **FATTO** (29 marzo 2026)
  - Split view read-only via provide/inject (stessa sola lettura degli operatori LETTURA)
  - Bottone "Affianca" sulla barra ContentTabs, Popover selettore tab
  - Responsive: solo desktop >= 1280px, chiusura automatica sotto soglia
- ~~Frontend Pratiche v2~~ — **FATTO** (29 marzo 2026)
  - Lista con display fields (7 JOIN backend), filtri (stato, priorita', data_da/data_a, search)
  - Drawer creazione con SoggettoResolver + selezione ruolo + cascata
  - Drawer dettaglio con 5 tab: Dati (azioni stato), Flussi, Note, Allegati, Giornale
  - Backend: 26 endpoint REST, 115 test Django, 25 smoke test
  - Collegamento anagrafico 3 livelli: soggetto → ruolo → istanza (guard DB + service)
  - Guard pre/post-attivazione tipo prestazione
- ~~Topbar: logout, badge iniziali utente, icone coerenti~~ — **FATTO** (29 marzo 2026)
- ~~Sidebar mobile: drawer collassato (solo icone)~~ — **FATTO** (29 marzo 2026)

### Completato (aprile 2026)

- ~~Integrazione AI v1~~ — **FATTO** (31 marzo 2026)
  - Anello 4 — strato di interazione intelligente sopra le API esistenti
  - 9 tool (6 lettura + 3 scrittura con conferma), widget flottante non modale
  - Contesto documentale statico, multi-tool chaining, timeout 30s
  - Shortcut Ctrl+., tema scuro, responsive, 61 test unitari
- ~~Gestione Autenticazioni fasi 1-3~~ — **FATTO** (1 aprile 2026)
  - Email building block: account multipli, template Jinja, log, risoluzione mittente per contesto
  - Token monouso: creazione, validazione, consumo, invalidazione, crittografia Fernet
  - Reset password self-service, invito operatore, cambio password obbligatorio al primo accesso
  - Frontend: 5 pagine auth (login, reset, invito, cambio pw), 890 test backend
  - Fase 4 (2FA TOTP) rimandata — pianificata in WIP
- ~~Refactor E_GENERICO~~ — **FATTO** (2 aprile 2026)
  - Deprecato codice errore generico `E_GENERICO` su tutto il DB
  - Sostituito con codici specifici per schema: `E_PARAMETRO_INVALIDO`, `E_PREZZO_LISTINO_NON_TROVATO`, `E_PREZZO_LISTINO_AMBIGUO`, ecc.
  - Tutte le funzioni PL/pgSQL ora usano codici identificabili per frontend/monitoring
- ~~Gestione Clienti v1~~ — **FATTO** (marzo 2026)
  - CRUD completo: creazione manuale, drawer con contatti/indirizzi/conti a 2 livelli
  - Catena automatica: istanza fittizia + billing account + cliente
  - 5 endpoint API, 29 test service, drawer frontend con sotto-drawer
  - v2 (subentro, disdetta, BA parent/child) pianificata in WIP
- ~~Gestione Articoli e Listini~~ — **FATTO** (3 aprile 2026)
  - Catalogo: backend 3 repository (articoli, UoM, BoM) + 19 funzioni service + 19 endpoint API
  - UoM CRUD: backend completo + frontend (lista, drawer, route)
  - Listini: backend 19 metodi repository + 18 funzioni service + 18 endpoint API
  - Frontend catalogo: ArticoliSearchTable, ArticoloDrawer (3 tab), UnitaMisuraView, ArticoloLookup BB
  - Frontend listini: ListiniSearchTable, ListinoDrawer (2 tab), VersioneDrawer (righe prezzo), TestResolverDialog
  - Building block: `LookupSelect` generico (29 Select sostituiti in 15 file), `ArticoloLookup` cross-dominio
  - Severity centralizzate: `statoVersioneListinoSeverity`, `dominioListinoSeverity`
  - 77 test backend, build frontend OK

### Completato (5-7 aprile 2026)

- ~~Catalogo Articoli~~ — **COMPLETATO E TESTATO** (5 aprile 2026)
  - Backend + frontend chiusi, 49 test verdi, doc consolidata in [work-done/gestione-articoli.md](dev/work-done/gestione-articoli.md)
  - Building block prodotti: `ArticoloLookup.vue` cross-dominio + endpoint lookup
- ~~Consolidamento WIP listini~~ — **FATTO** (6 aprile 2026)
  - I due vecchi WIP `gestione-articoli-listini.md` + `gestione-listini.md` consolidati in sviluppo-listini.md (ora in [work-done](dev/work-done/sviluppo-listini-v1.md), superseded da [sviluppo-listini-v3.md](dev/work-done/sviluppo-listini-v3.md))
  - Estratte rettifiche prezzi (DB-L4) in [sviluppo-rettifiche.md](dev/work-in-progress/sviluppo-rettifiche.md)
- ~~Drawer dedicato gestione permessi operatore~~ — **FATTO** (6 aprile 2026)
  - `OperatorePermessiTab` reso riutilizzabile (watch su `authUserId`)
  - Nuovo `OperatorePermessiDrawer.vue` richiamabile dalla riga lista operatori
- ~~Parametri di sistema multi-scope~~ — **FATTO** (5-6 aprile 2026)
  - Drawer override con selettore scope (Personale/Emittente) visibile solo agli admin
  - Backend: `upsert_emittente_override` + check `IsAdminZeroERP`, fallback emittente "gestore di default"
  - Fix constraint v3 (`uq_overrides_full_scope_v3`) e fn `get_emittente_fiscale_id_for_user` allineata a `script.fn_get_emittenti_scope`
  - Costante condivisa `PARAMETER_SCOPE` come unica fonte di verita' frontend
- ~~AI tool catalogo + billing account~~ — **FATTO** (7 aprile 2026)
  - Nuovo `cerca_articoli` (dominio catalogo) — sblocca "cerca articolo X" via AI
  - Nuovo `cerca_billing_account` (dominio anagrafiche) — wrappa la ricerca dedicata BA con scope emittente
  - System prompt esteso con glossario di dominio italiano (cliente=BA, articolo=catalogo)
  - Tool registrati totali: **11** (era 9)
- ~~Logo brand ottimizzato~~ — **FATTO** (5 aprile 2026)
  - Master 1640x1640 → versioni ottimizzate 512/256/32 px per frontend, favicon (PNG+ICO), docs

### Completato (8-12 aprile 2026)

- ~~Migrazione `daterange` nativo PostgreSQL~~ — **FATTO** (12 aprile 2026)
  - Infrastruttura originale: `dbops.automazione_overlap` + `script.trgfn_set_validita()` (trigger generico, poi rimosso con PG18)
  - Fase 1: 5 tabelle con GIST migrate (listini_versioni, listini_associazioni, uom_conversioni, contratti, articoli_componenti) + `fn_resolve_prezzo_listino` aggiornata
  - Fase 2: 11 tabelle config/anagrafiche migrate + 5 funzioni permessi semplificate con `@>`
  - Fase 3: 2 tabelle pratiche con `tstzrange`
  - Backend: ottimizzazione query repository (`validita @>` al posto dei doppi confronti)
  - Linee guida SQL: sezione 7b aggiunta
  - Analisi: [migrazione-daterange.md](dev/work-done/migrazione-daterange.md)
- ~~Listini v3 — Sprint B completo~~ — **FATTO** (12 aprile 2026)
  - **N8a** Variazione % massa su BOZZA (backend + frontend dialog + 9 test)
  - **N2** Alert scadenze versioni (backend + frontend widget badge + 2 test)
  - **N6** Rettifica controllata riga ATTIVA non propagata (backend + trigger DB defense-in-depth + 4 test)
  - **N5** Riallineamento prezzo commessa (backend + 3 test)
  - **N7** Variazione prezzo eccezionale commessa + sblocco (backend + 6 test)
  - Avviso UX programmazione chiusura versione ATTIVA (`ProgrammaChiusuraDialog.vue`)
  - Documentazione: N3 lifecycle preventivo→commessa, N4 nota match_level 3, N8b guida "listino post-it"
  - 2 doc API create/aggiornate, error policies registrate, 1231 test totali
  - Analisi: [sviluppo-listini-v3.md](dev/work-done/sviluppo-listini-v3.md)
- ~~Emittenti fiscali CRUD + BA mapping + Utilities~~ — **FATTO** (8 aprile 2026)
  - Admin CRUD + sub-resource mapping BA + matrice utilities slot/override
  - BB `list_entity_utility_matrix` + `UtilityPerRuoloSelect`, validazione P.IVA
- ~~Matrice utilities tipi ruolo~~ — **FATTO** (8 aprile 2026)
  - CRUD admin `config.utilities_tipi_ruolo`, app config attivata, drawer tab usage
- ~~Refactor operatore-emittenti 1-a-1~~ — **FATTO** (9 aprile 2026)
  - `JwtAuditAuthentication` Option A pura, GUC session-scoped
  - BE fasi 2-4 + FE completa + 7 fix critici review
- ~~Refactor invariante univocita' listini~~ — **FATTO** (10 aprile 2026)
  - Drop `priorita` da versioni e associazioni, constraint GIST cross-listino
  - Permessi v2: 6 fasi, `model_permission` su 33 view, `IvaSelect`/`ContoContabileSelect`

### Completato (26 aprile - 4 maggio 2026)

- ~~Framework chiusura per scadenza~~ — **FATTO** (26 aprile 2026)
  - `dbops.automazione_chiusura_scadenze`, `dbops.fn_apply_chiusura_scadenze()`, job pgAgent unico
  - Promozione al nucleo dopo due consumatori reali: versioni listino e contratti
- ~~Refactor catalogo~~ — **FATTO** (28 aprile 2026)
  - Fasi 1-8 DB+BE+FE chiuse, lookup/defaults/capability spostati su contratti API/backend, 83/83 test BE e build Vite verdi
- ~~Refactor amm-software~~ — **FATTO** (29-30 aprile 2026)
  - Operatori/admin, permessi, emittenti fiscali e matrici riallineati ai building block e agli standard frontend
- ~~Refactor vendite~~ — **FATTO** (1 maggio 2026)
  - DB+BE+FE chiusi, lookup/form-defaults/capability/azioni data-driven; documentazione API aggiornata
- ~~Preventivi rev2~~ — **FATTO** (2 maggio 2026)
  - `emittente_fiscale_id` persistito e immutabile, `istanza_utility_id` obbligatoria, guard coerenza utility/istanza, errori strutturati
- ~~Preventivi scenario 2.1~~ — **FATTO** (3 maggio 2026)
  - Revisione preventivo, riepilogo IVA e test end-to-end documentati dai commit locali
- ~~Motore documentale parametrico — DB/BE/FE~~ — **FATTO tecnico, test UI in corso** (4 maggio 2026)
  - DB Fase A, backend Tranche A-K, frontend Tranche L-M
  - Configurazione modelli documenti e asset documentali, render PDF WeasyPrint, generazione/lista/download PDF da preventivo

### In corso

- **Gestione Soggetti**: backend + frontend completati — in fase di test UI
- **Gestione Geografica**: operativo — UI da migliorare
- **Gestione Clienti/Fornitori**: drawer end-to-end operativo, v2 (subentro/disdetta) pianificata
- **Gestione Pratiche v2**: frontend operativo — in fase di test UI
- **Motore documentale parametrico**: end-to-end tecnico completato, suite manuale `sviluppo-documenti-test-ui.md` da eseguire/chiudere
- **Integrazione AI v2**: evoluzione con contesto dinamico e nuovi tool — WIP
- **Autenticazione 2FA**: fase 4 TOTP — WIP
- **Permessi v2**: livello oggetto e granularita' fine — in corso (33 view gia' configurate)
- **Rettifiche prezzi (DB-L4)**: motore delta + canali manuale/automatico — pianificato in WIP dedicato

### Breve termine

- Test UI reali su Articoli, UoM, Pratiche, Soggetti, Clienti, Fornitori e motore documentale preventivo
- Seed azioni processo per nuovi domini (catalogo, vendite) + prop `action` sui componenti
- Upload file allegati pratiche (storage filesystem/object storage)
- **Schema `ui` — Blocchi A+B**: DDL tabelle + trigger validazione + `fn_resolve_lista_config` (DB)
- **Schema `ui` — Blocchi C+D**: app Django `ui`, 4 endpoint REST, `<ListaConfigurabile>` + modale personalizzazione (BE+FE)
- **Schema `ui` — Blocco E**: seed catalogo `anagrafiche.clienti` + migrazione primo componente lista — validazione del nucleo su caso reale

### Medio termine

- Integrazione `vendite` → `pratiche`: eventi di vendita generano pratiche con giornale
- Integrazione `anagrafiche` → `pratiche`: onboarding cliente/fornitore tracciato
- Attivazione handler flusso per automazioni specifiche
- pgAgent job riattivazione automatica sospensioni

### Lungo termine

- Tutti i processi di anello 3 usano `pratiche` per tracciabilita' e orchestrazione
- Il giornale di bordo diventa la vista unificata sulle attivita' dell'azienda
- Canali esterni (portale clienti, app tecnica) operano tramite flussi con visibilita' controllata

---

## Come aggiornare questo documento

1. **Nuovo componente**: aggiungere nella tabella dell'anello corretto, con stato DB e Backend
2. **Cambio stato**: aggiornare la colonna Stato (Stub → DA FARE → Operativo)
3. **Nuova dipendenza**: aggiungere nella matrice e verificare che rispetti la direzione degli anelli
4. **Nuovo anello**: se emerge un livello intermedio, inserirlo e ri-numerare

> La mappa deve riflettere la realta', non le intenzioni. Aggiornare solo quando qualcosa cambia concretamente.

---

*Mappa Concentrica — ZeroERP (4 maggio 2026)*
