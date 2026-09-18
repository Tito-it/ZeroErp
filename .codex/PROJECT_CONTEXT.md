# ZeroErp — Contesto di Progetto per Sessioni AI

> Questo file è pensato per essere letto all'inizio di ogni sessione Claude Code,
> su qualsiasi server (DB o backend). Integra AGENTS.md con lo stato corrente del progetto.

## Identità del Progetto

- Nome: ZeroErp
- Tipo: ERP open-source (GPL v3), progetto serio orientato alla produzione
- Autore: Tid (Michele Carlo Titini) — 30+ anni di esperienza ERP (AS/400)
- Repo: https://github.com/Tito-it/ZeroErp
- Lingua doc/commenti: it-IT

## Filosofia Architetturale (NON negoziabile)

1. **DB-first**: tutta la logica di business vive in PostgreSQL (funzioni, trigger, viste)
2. **Django**: orchestrazione, API REST, e logica che non può stare nel DB
3. **Vue** (futuro): SOLO presentazione — zero logica business nel frontend
4. **No logica duplicata** tra livelli: se è nel DB non va replicata in Python, e viceversa
5. ⛔ **Si progetta sul modello, mai su una fotografia**: le misure sui *dati* del DB
   di sviluppo (`count(*)`, «zero righe in quello stato», «N su M») non decidono
   nulla — decide ciò che il modello **ammette**. Le misure sulla *struttura*
   (nullabilità, CHECK, RLS, GRANT, corpo di una funzione) sì: quelle sono il
   progetto, non il contenuto. Regola completa, con il corollario sui test, in
   [AGENTS.md § «Regola zero — le misure non disegnano il progetto»](AGENTS.md)

## Stack Tecnico

| Componente | Versione | Note |
|---|---|---|
| Python | 3.14 (da `.python-version`) | Fonte unica di verità per versione |
| Django | 6.01 | DRF 3.16, SimpleJWT, drf-spectacular |
| PostgreSQL | 18 (CI) | PostGIS 3.6, pgTAP, pgAgent |
| Liquibase | 5 Community | Migrazioni YAML in `db/changelog/migrations_v2/` |
| Frontend Vue | da `frontend/package.json` | **Fonte unica di verità per le versioni** (Vue, Vite, PrimeVue, Pinia, Vue Router, vue-i18n, Axios; Node in `engines.node`). ⛔ Non ricopiarle qui: il 2026-09-09 questa riga, `AGENTS.md` e `frontend-standards.md` dicevano tre cose diverse e tutte e tre sbagliate. **Frontend sviluppato e in uso**, non più placeholder. Standard: `docs/it/dev/frontend/frontend-standards.md` + catalogo BB FE |

## Infrastruttura di Sviluppo

- **Server DB**: PostgreSQL su server dedicato
- **Server backend**: Django, accessibile via VSCode SSH
- **Branch centrale**: `Tito-dev` (integrazione); branch di lavoro: `dev/db-tid` e `dev/backend-tid`
- **Flusso PR**: branch lavoro → `Tito-dev` → `main`
- **CI**: due workflow — `ci.yaml` (build+docker+docs) e `ci-validate.yaml` (test backend+DB)

## Struttura Repository

```
ZeroErp/
├── backend/                  # Django project
│   ├── zeroerp_backend/      # Config Django (settings, urls, wsgi)
│   ├── apps/                 # App per dominio — 17, elenco COMPLETO (2026-09-09)
│   │   ├── core/             # Utilities trasversali (error_manager, middleware, throttling)
│   │   ├── ai_assistant/     # Assistente AI: 18 tool, provider pluggabile. Dietro AI_ENABLED
│   │   ├── amm_software/     # Amministrazione software (AdminAPIView, SUPER_ADMIN)
│   │   ├── anagrafiche/
│   │   ├── catalogo/
│   │   ├── config/
│   │   ├── documenti/        # Motore documentale parametrico + ristampa fedele
│   │   ├── pagamenti/
│   │   ├── portale/          # Veste CLIENTE_PORTALE / FORNITORE_PORTALE (auth + attivazione)
│   │   ├── pratiche/         # Motore di workflow versionato
│   │   ├── shop/             # Veste SHOP_CUSTOMER (auth + attivazione)
│   │   ├── ui/               # Liste configurabili: la configurazione è DATO, non DDL
│   │   ├── vendite/          # App più attiva — pipeline fatturazione
│   │   ├── acquisti/         # 🔵 PROSSIMO CANTIERE (Tid, 2026-09-11) — modello a DB, comportamento da scrivere
│   │   ├── magazzino/        # 🔵 PROSSIMO CANTIERE (idem) — modello a DB curato, 0 test
│   │   ├── storico/          # ⚠️ scheletro (13 file, 26 righe, 0 test) — nessuna decisione presa
│   │   └── contabilita/      # ⛔ scheletro vuoto — schema DB vuoto, fuori perimetro per decisione
│   ├── requirements.in       # Dipendenze dirette (editare qui)
│   └── requirements.txt      # Generato da pip-compile (non editare)
├── db/
│   └── changelog/migrations_v2/  # Tutte le migrazioni Liquibase
│       ├── 00_schema/        # DDL tabelle
│       ├── 20_code/          # Funzioni, trigger, viste
│       ├── 80_data/          # Seed dati
│       └── 90_end/           # Indici FK (apply_fk_index_policy)
├── db/pgtap/                 # Test DB con pgTAP
├── docs/it/                  # Documentazione MkDocs
│   ├── linee-guida-sql.md    # LEGGERE prima di scrivere SQL
│   ├── linee-guida-trigger.md
│   ├── guide/                # Guide operative (fatturazione, pagamenti, ecc.)
│   ├── dbzero/<schema>/      # Doc auto-generata (NON modificare)
│   └── dbzero/<schema>/manual/  # Doc manuale (modificare qui)
├── .codex/AGENTS.md          # Istruzioni per agenti AI
├── .codex/PROJECT_CONTEXT.md # Questo file
└── .python-version           # Fonte unica versione Python
```

## Schemi DB (13 totali)

| Schema | Scopo |
|---|---|
| `anagrafiche` | Soggetti, indirizzi, contatti, ruoli |
| `catalogo` | Articoli, listini, UoM, distinte base |
| `config` | Dati di riferimento (stati, nazioni, termini pagamento) |
| `vendite` | Ciclo vendite: preventivi→ordini→DDT→fatture + pipeline fatturazione |
| `acquisti` | Ciclo acquisti |
| `magazzino` | Movimenti, giacenze, lotti, seriali |
| `pagamenti` | Scadenze, riconciliazioni, contabili |
| `contabilita` | ⛔ **VUOTO e fuori perimetro** — zero tabelle, funzioni e viste (verificato 01-09-2026). ⚠️ Diceva «piano conti, registrazioni, partite»: non esistono. `backend/apps/contabilita/` è uno scheletro vuoto. Se servirà sarà un **aggancio a una contabilità esterna**, con la forma dettata dal sistema di destinazione |
| `storico` | Audit temporale (storicizzazione tabelle) |
| `dbops` | Strumenti DBA, registry task, FK policy |
| `script` | Viste e funzioni applicative riusabili (incl. risoluzione permessi) |
| `maintenance` | Job schedulati (pgAgent) |
| `public` | Estensioni (`dblink`, `unaccent`, `postgis`, `plpgsql_check`), **nessuna tabella**. ⛔ `version_info` — una riga, zero lettori — è stata **droppata il 2026-09-12** (decisione Tid, `90_end/20260912-29`, nel provisioning perché lì era nata). Per la versione applicata usare `DATABASECHANGELOG`. Fino a quel giorno questa riga la dava «esiste, decisione aperta»: analisi-software-per-dati-morti §2.6 |

## Struttura App Django (pattern per ogni dominio)

```
apps/<dominio>/
├── api/
│   ├── views.py       # ViewSet / APIView
│   └── urls.py        # Route
├── services/          # Orchestrazione business logic
├── db/ o repositories/ # Accesso DB/SQL (cursor, funzioni PG)
├── models.py          # Minimale, managed=False dove possibile
└── tests/
    ├── api/
    └── services/
```

## Pattern Backend Chiave

### Error handling
```python
# In services: usa ServiceError
from apps.core.services.error_manager import ErrorManager, ServiceError

# Guard su valori richiesti:
ErrorManager.require(value is not None, "CODICE_ERRORE", "messaggio")
assert value is not None  # sempre dopo require, per il type checker

# In views: NON catturare Exception generici
# Il middleware apps/core/middleware/api_exception_middleware.py gestisce il fallback
```

### Endpoint API (pattern uniforme)
```python
from apps.core.api.endpoint_helpers import handle_post_json

# Usa handle_post_json per parsing input + error envelope uniforme
```

### Accesso DB
```python
# Dopo fetchone() aggiungere sempre guard:
row = cursor.fetchone()
if not row:
    raise ServiceError(...)
# oppure: assert row is not None
```

### Commenti Python (obbligatori)
```python
# Scopo: descrizione sintetica della funzione/metodo
def nome_metodo(self, ...):
    ...

# Per metodi complessi (pipeline, transazioni, dispatch):
# Scopo: obiettivo, perimetro e risultato atteso dettagliati
```

## Stato del Progetto — istantanea aprile 2026 (storica)

> ⚠️ **Questa sezione è ferma ad aprile 2026 e non riflette lo stato corrente.** Da allora
> sono arrivati (fra gli altri) frontend Vue completo, multi-face auth, RLS operatori,
> personalizzazioni liste, motore documentale, commesse/DDT/resi e il cockpit fatturazione.
> Per lo stato reale usare, in quest'ordine: l'handoff più recente in memoria, i documenti in
> `docs/it/dev/work-in-progress/`, e il repo. Le voci sotto restano perché descrivono
> fondamenta ancora valide, non perché siano l'ultima parola.

### Completato ✅ (al netto della nota sopra)
- Refactor permessi (08-03-2026): 9 funzioni risoluzione permessi spostate da `config` a `script` — migrations `20260308-01..12`, Python backend + pgTAP test + doc aggiornati
- Pipeline fatturazione: `vendite.fatturazione_pipeline` + runner Django (`LottoPipelineRunner`)
- Lotti massivi e giornalieri con stati (DRAFT→EMESSA→DEFINITIVA)
- Registry task DB multi-dominio (`dbops.domini_task`, `pipeline_task_registry`, `pipeline_task_registry_impl`)
- Dispatch task con `implementation_key` controllato (no dynamic import)
- Log fatture e flag `critical` (`vendite.fatture_log`)
- Refactor fondi fattura (contabili/righe)
- Refactor saldo fattura (residuo + saldo contabile postabile)
- Payload SDI preparato (`fn_prepare_sdi_payload`)
- Runtime task tracing: `vendite.fatturazione_pipeline_task_policy` + `vendite.fatturazione_lotti_task_runs`
- Test pgtap runtime task + test Django pipeline runner
- **Listini v3 completo** (12-04-2026): Sprint B-v3 — N8a variazione % massa, N2 alert scadenze, N6 rettifica controllata, N5 riallineamento prezzo, N7 variazione eccezionale + sblocco, trigger DB guard, 6 endpoint API, 24 test, doc API
- **Migrazione daterange** (12-04-2026): 18 tabelle migrate a `daterange`/`tstzrange` nativo, `script.trgfn_set_validita()`, backend ottimizzato con `@>`, linee guida SQL §7b
- **Pricing commesse** (12-04-2026): riallineamento prezzo, variazione eccezionale, sblocco — 3 endpoint API con lock FOR UPDATE e audit trail

### 🔵 Il prossimo cantiere — `acquisti` e `magazzino` (decisione di Tid, 2026-09-11)

Le due app **non sono scheletri congelati: sono il prossimo cantiere**, e la
decisione è stata presa il 2026-09-11 rispondendo alla voce D11 di
[migliorie-generali-BE-FE-da-test-valutazione.md](../docs/it/dev/work-in-progress/migliorie-generali-BE-FE-da-test-valutazione.md).

Oggi hanno un **modello DB curato e zero comportamento applicativo**: 26 tabelle
e 71 CHECK su `magazzino`, 9 tabelle e 42 FK su `acquisti`, 13 file Python e 0
test per ciascuna.

⭐ **Cosa comporta, ed è la ragione per cui sta scritto qui e non in un piano:**
ogni decisione che si prende lavorando su `vendite` — envelope, capability di
riga, scope emittente, ordinamento, export, drawer autonomi,
`ListaConfigurabile` — è una decisione presa **anche per `acquisti`**. Finché
erano dichiarati «scheletri», quel debito cresceva in silenzio; da adesso chi
decide su `vendite` sa di star decidendo per due domini.
⇒ Ne discende la regola operativa: quando un'asimmetria fra i due domini emerge,
si chiude **subito**, non in una «fase due» — una simmetria rimandata è un debito
che nessuno rilegge.

⚠️ `storico` **resta senza decisione** e `contabilita` resta **fuori perimetro**
(schema DB vuoto, verificato 01-09-2026): non sono la stessa cosa e non vanno
letti insieme ai due sopra.

✅ **Il prerequisito è consegnato** (2026-09-14, brief chiuso in
`work-done/brief-db-modifiche-certe-ciclo-vendita-e-articolo.md`): le date di
consegna sulle righe (vendite **e** acquisti), `config.modi_approvvigionamento`,
`articoli.gestito_a_magazzino`/`lead_time_giorni`, la commessa leggibile,
`famiglie_documento` senza BA obbligatorio — DB, BE e FE. **Tre cose il cantiere
le eredita, e sono scritte nel riquadro «CHIUSO» di quel brief:**

- 🔴 il **presidio di prontezza** su `articoli.gestito_a_magazzino` (vista
  `dbops` a una riga `MARCATI`/`NESSUNO_MARCATO`, `ZERO`, `stato_atteso =
  MARCATI` in `presidi.csv`) — deciso da Tid il 14-09: si scrive **qui**, col
  primo carico (analisi carico e scarico §8), non prima: al rilascio tutti gli
  articoli sono `false` e nessun rosso lo dice;
- le due date di `acquisti.ordini_righe` sono a DB **senza consumatore**
  (nessun repository di righe, nessuna chiave i18n);
- `E_ATTIVO_REQUIRE`, il codice del require generato dal framework ATTIVO, è
  **TECNICO** anche quando il dato l'ha scelto una persona: candidato allo split,
  per **tutte** le coppie — cantiere `dbops`, non di dominio.

✅ **Il Lotto 1 di magazzino («il terreno vuoto») è CHIUSO e archiviato**
(`work-done/brief-db-magazzino-lotto-1-terreno-vuoto.md`, 2026-09-17): DB
mergiato il 15-09 (PR #1593), le richieste BE/FE chiuse lo stesso giorno
(PR #1595: `E_MAG_*` rigenerati coi ripieghi, `ambito_causale` via da
`_REL_CONSENTITE`/`CONFIG_TABLES`), CI verde. Il **Lotto 2** («il motore»: primitiva DEFINER + porta sul
ledger, check di disponibilità condivisa, inventario e rettifica,
`vw_disponibilita`, orfani, presidio di prontezza, `requires_lotto` in UI) ha
il suo brief dal **17-09** — `work-in-progress/brief-db-magazzino-lotto-2-motore.md`,
✅ **quattordici D-L2 tutte decise da Tid il 17-09** (fra cui `magazzini.usa_ubicazioni`, `trasferimenti` = trasferimento interno, via `COUNTING`), 🔵 **nessun changeSet: si parte da P-0** — e parte da
`analisi-db-magazzino-carico-e-scarico.md` §8 e dalle sei lezioni in coda a §5
del brief del Lotto 1. Il prerequisito deciso da Tid il 15-09 —
`brief-db-emittente-di-default-un-bb-solo.md`, l'emittente di default come
**building block unico** in `script`, montato su `magazzini`/`assets` e **al
posto delle quattro copie di vendite**, ritirate nello stesso giro — è
**CHIUSO anch'esso il 17-09** (`work-done/brief-db-emittente-di-default-un-bb-solo.md`:
`20260915-36 → -46` applicati, undici trigger sul BB e zero copie a DB vivo,
commit `e98cf2469` + PR #1598, BE allineato con `E_EMITTENTE_NON_RISOLTO`).
⭐ La regola che ne discende, e vale per ogni cantiere: *quando
emerge un BB generico, i duplicati esistenti si ritirano subito — non c'è
produzione, non c'è niente da aspettare.*

### Aperto — Media priorità
- **La distinta del fondo fattura fuori lotto** (DB, ereditata il 2026-09-17
  dalla chiusura di `work-done/brief-db-distinta-numerata-sul-registro.md`,
  §4-bis.19): `fn_sync_contabili_fondo_fattura` passa `p_lotto_id = NULL` se la
  fattura non è in nessun lotto, e la distinta del fondo cade al **livello 3**
  di `fn_get_emittente_distinta` (l'emittente di chi agisce) invece che a
  quello della fattura — per l'admin globale in «tutti» è un
  `E_CONTABILE_EMITTENTE_OBBLIGATORIO` in mezzo alla pipeline. La strada è che
  la madre dei fondi passi `p_emittente_fiscale_id` dall'emittente della
  **fattura**. Da decidere con Tid, un changeSet
- **`runOnChange` + `dbms:` in `80_data`/`90_end`: la ri-esecuzione una-tantum**
  (DB, ereditata il 2026-09-17 dalla chiusura di
  `work-done/brief-db-distinta-numerata-sul-registro.md`, §9 riga del 17-09
  pomeriggio): in Liquibase 5.0.4 un `runOnChange` con un change `dbms:` viene
  ri-eseguito **una volta** all'update successivo alla prima esecuzione — il
  filtro ricalcola il checksum senza `Database` nello `Scope` e salta il
  change, quindi il checksum salvato non torna (`exectype = RERAN`, poi
  stabile). In CI cade nella **seconda** invocazione (`ci_apply`), **fuori
  ordine** rispetto a `80_data`: è così che `20260831-03` è morto dopo il
  merge di PR #1598 (corretto: cancello per nome, `237ea2939`). Sono 28
  changeSet in `80_data`/`90_end`, tolleranti tranne quel cancello. Da
  decidere: togliere `dbms:` dai 28 (checksum deterministico, niente
  ri-esecuzione) o accettare la ri-esecuzione e censire ogni `sqlCheck` con
  `HALT` sul **contenuto**; e riscrivere la nota del guardrail `runOnChange`
  in `ci-validate.yaml`, che nomina `runOnChange` come causa quando la causa è
  `runOnChange` **+ `dbms:`**. Cantiere `dbops`, non di dominio
- **La scala di `vendite_contabili_righe.importo`** (DB, **P-8**, ereditata il
  2026-09-18 dalla chiusura di `work-done/brief-db-distinta-ricerca-rate.md`,
  §4-bis.10): la colonna è `numeric` **senza scala** (`20260213-10`), quindi una
  riga con quattordici decimali — la sottrazione in virgola mobile di un client —
  entra com'è, e il guard di capienza la rifiuta su un importo che *era* lo
  spazio. Il FE arrotonda ai centesimi dal 17-09, ma la regola vale per
  **qualunque** client. Raccomandazione scritta nel brief: un
  `CHECK (importo = round(importo, 2))` che **rifiuta** (AGENTS.md: «non
  normalizzare silenziosamente»), non un typmod `numeric(18,2)` che arrotonda
  in silenzio; `fatture_scadenze.importo` resta `numeric(18,6)` come i totali di
  documento. Un changeSet `00_schema` con `expectedResult: 0` sulle righe che
  non passerebbero. Decisione di Tid
- **Su quale documento si può registrare un incasso** (DB, **Q-4**, ereditata
  il 2026-09-18 dallo stesso brief, registro del 18-09): Tid vuole nel picker
  delle rate «solo le definitive, inviate a SDI — ma faremo poi». È un
  predicato di **dominio** e la sede è **una**, a DB, letta dalla lista **e**
  dal guard della riga: oggi `trgfn_vendite_contabili_righe_guard_rata` non
  chiede lo stato del documento (la rata di una bozza si abbina) e il filtro
  `solo_numerate` di `GET /pagamenti/rate/` è presentazione, non cancello. Si
  apre con la **persistenza dell'esito SDI** (voce sotto), che è ciò che
  «inviata» significa; nessun changeSet chiesto prima
- **«Riavvia» un servizio dall'interfaccia** (DB + deploy + BE, **decisione
  D1 di Tid**; ereditata il 2026-09-18 dalla chiusura di
  `work-done/analisi-riavvio-processi-da-interfaccia.md`): «Esegui ora» è in
  esercizio dal 15-09 e non aveva bisogno di sapere su quale macchina gira —
  un timer è un comando che parla col DB. `systemctl restart` di un servizio
  (oggi il solo `listen_cambio_reparto`) **sì**: senza un *host* nel modello
  il pulsante riavvia «un host a caso» alla seconda macchina, in silenzio.
  Cancello: **D1** — forma A (`ZEROERP_HOST` dichiarato in `env.sh`, `host`
  obbligatorio nella richiesta, claim del drenatore filtrato) o B (registro
  `dbops.host` + `abilita` per host); l'analisi raccomanda **A subito, con
  `host` obbligatorio dal primo giorno**. Poi D2…D8 (§7) e la sequenza §9:
  colonna sul claim, tipo `RIAVVIA_UNIT` (`attivo = false`), azione
  `unit_riavvia`, `sudoers` **reso** da `sveglie.json` in `install-timers.sh`,
  handler a lista senza shell, run **non** contato come segno di vita del
  processo riavviato (D6). Zero righe scritte al 18-09, per scelta. Sta anche
  fra le «Decisioni aperte» della mappa concentrica
- **Registry runtime Python multi-dominio**: modello DB pronto, ma la mappa Python per tutti i domini non è completa
- **Builder XML SDI**: payload pronto, ma generazione file FatturaPA non ancora implementata. ⚠️ Sospeso per decisione (Tid, 2026-08-05); raccoglie anche `EsigibilitaIVA`, `DatiContratto` e le righe spezzate dal plafond (`vw_fattura_righe_esposte`, `PARTE_PLAFOND`) — dettagli in `work-done/fatturazione-roadmap.md` §9
- **Persistenza esito SDI**: `vendite.fatture_sdi` e `vendite.fatture_sdi_eventi` da popolare
- **La promessa di consegna dopo la conferma** (BE, decisione di Tid; ereditata
  il 2026-09-14 dal brief «modifiche certe», voce 1-bis): le righe d'ordine si
  scrivono solo in `DRAFT` (`_STATI_RIGHE_MODIFICABILI`), ma
  `data_consegna_confermata` si decide **alla conferma** e può cambiare dopo. Il
  DB non mette guard di stato di proposito: serve un verbo suo (stampo: gli
  override di prezzo) o il dialog di conferma che la raccolga
- **Pratica di approvazione prezzo su revisione superata** (BE,
  `work-done/refactor-prezzi.md` §4.7, residuo differito dal 2026-06-01): dal
  2026-09-14 (`20260914-14`) riguarda anche i **preventivi** — la rev N+1
  ricopia `stato_approvazione_prezzo` e la pratica 1:1, e una riga `PENDING`
  può trovarsi con la pratica già chiusa sulla rev N

**Residui della roadmap fatturazione** (archiviata il 2026-09-12 in
`docs/it/dev/work-done/fatturazione-roadmap.md`, dove sta il *perché* di
ciascuna; qui solo la riga, perché un promemoria di stato lungo marcisce —
lezione della §Nota di metodo di quel file):

- **Esercizio fiscale come entità** (roadmap #3): zero occorrenze di `esercizio`/`anno_fiscale` in `migrations_v2` e nel backend; l'esercizio è l'anno solare derivato da `fatture.data`. Serve al primo **bilancio**, non al primo ciclo — la numerazione con reset annuale è coperta
- **Vista push** (roadmap #5): `vendite.commesse_push_log` non ha una UI di lista/ultimo run per sorgente; i contatori `created/updated/skipped/errors` esistono nel payload e nessuno li rende — l'operatore riceve un `push_log_id` in un toast e non ha modo di aprirlo
- **Alerting sui dati** (roadmap #6): la vitalità dei **processi** è coperta (sveglia, `dbops.processi`, digest); manca la query su `vendite.event_log` per severity/finestra con un canale d'uscita — casa: `work-in-progress/analisi-osservabilita-log.md`
- **Diagrammi di stato** (roadmap #8): zero `stateDiagram-v2` nel repo per lotto e task_run; la sostanza è già in prosa in `guide/fatturazione.md` — è trasposizione, non analisi
- **Preview di fatturazione del contratto** (roadmap #10): non esiste il punto in cui l'operatore veda *«su questa competenza fatturerà queste righe, per X»*; il dato lo produce `fn_list_contratti_da_pushare`. ⚠️ Non è `/contratti/<id>/righe-preview/`, che è la preview di **pricing**

### Note operative
- `config.stati_doc_fiscale.chiude_lotto = true` → unico meccanismo di chiusura lotto (nessun hardcode)
- Reset lotto MASSIVO: ammesso in DRAFT; la DEFINITIVA fa resume per fattura (non reset globale)
- La procedura SQL `pr_run_lotto_pipeline` è stata **rimossa** (non in `pg_proc`, verificato 2026-09-12); l'orchestrazione è in Django (`run_lotto_pipeline`). Fino a quel giorno questa riga la dava «deprecata e in fase di rimozione»

## File Django Chiave (vendite)

```
apps/vendite/
├── services/
│   ├── pipeline_runner.py          # LottoPipelineRunner — orchestrazione step pipeline
│   ├── pipeline_step_executor.py   # Esecuzione singolo step + dispatch task
│   └── fatture_righe_service.py    # Generazione righe fattura
├── db/ o repositories/
│   └── vendite_pipeline_repository.py  # Lookup registry DB, fn SQL
├── types.py                        # TypedDict per pipeline/lotto
└── tests/
    ├── services/
    │   ├── test_pipeline_runner.py
    │   └── test_pipeline_step_executor.py
    └── api/
        ├── test_pipeline_api.py
        └── test_reset_lotto_*.py
```

## Comandi Utili

```bash
# Test Django (dalla root backend/)
./manage-test.sh apps.vendite.tests.services -v 2
./manage-test.sh apps.vendite.tests.api -v 2
./manage-test.sh apps.core.tests.api -v 2

# Test DB (pgtap)
scripts/testpgtap.sh db/pgtap/<schema>/<test-file>.sql

# Aggiornare dipendenze backend
pip-compile backend/requirements.in --output-file backend/requirements.txt

# Aggiornare strumenti dev (mkdocs, pre-commit, ecc.)
scripts/update-venv.sh

# Liquibase locale
make db-migrate       # applica migrazioni
make db-ci-apply      # applica automazioni CI
make db-setup         # entrambi
```

## Documentazione di Riferimento Rapido

- Convenzioni SQL: `docs/it/linee-guida-sql.md`
- Convenzioni trigger: `docs/it/linee-guida-trigger.md`
- Guida fatturazione: `docs/it/guide/fatturazione.md`
- WIP pipeline: `docs/it/dev/work-done/fatturazione-attivita-progetto.md`
- Domini engine (archiviato 2026-08-22, con la verifica dei concetti in testa): `docs/it/dev/work-done/pipeline-domini-engine.md`
- Template doc backend: `docs/it/backend/_templates/manual-standard.md`
