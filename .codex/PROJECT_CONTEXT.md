# ZeroErp — Contesto di Progetto per Sessioni AI

> Questo file è pensato per essere letto all'inizio di ogni sessione Claude Code,
> su qualsiasi server (DB o backend). Integra AGENTS.md con lo stato corrente del progetto.
>
> Ultima revisione: 2026-10-25.

## Identità del Progetto

- Nome: ZeroErp
- Tipo: ERP open-source (GPL v3), progetto serio orientato alla produzione
- Autore: Tid (Michele Carlo Titini) — 30+ anni di esperienza ERP (AS/400)
- Repo: https://github.com/Tito-it/ZeroErp
- Lingua doc/commenti: it-IT

## Filosofia Architetturale (NON negoziabile)

1. **DB-first**: tutta la logica di business vive in PostgreSQL (funzioni, trigger, viste)
2. **Django**: orchestrazione, API REST, e logica che non può stare nel DB
3. **Vue**: SOLO presentazione — zero logica business nel frontend
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
| Python | da `.python-version` | Fonte unica di verità per la versione |
| Django | da `backend/requirements.in` | DRF, SimpleJWT, drf-spectacular; versioni esatte nel lock `requirements.txt` |
| PostgreSQL | 18 (CI) | PostGIS 3.6, pgTAP, pgAgent |
| Liquibase | 5 Community | Migrazioni YAML in `db/changelog/migrations_v2/` |
| Frontend Vue | da `frontend/package.json` | **Fonte unica di verità per le versioni** (Vue, Vite, PrimeVue, Pinia, Vue Router, vue-i18n, Axios; Node in `engines.node`): ⛔ non ricopiarle qui. Standard: `docs/it/dev/frontend/frontend-standards.md` + catalogo BB FE |

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
│   │   ├── magazzino/        # 🔵 CANTIERE APERTO (idem) — Lotti 1-2 chiusi; Lotti 3 e 3-bis fatti, da collaudare a video
│   │   ├── storico/          # ⚠️ scheletro (13 file, 23 righe, 0 test) — nessuna decisione presa
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

## Schemi DB

| Schema | Scopo |
|---|---|
| `anagrafiche` | Soggetti, indirizzi, contatti, ruoli, emittenti fiscali |
| `catalogo` | Articoli, UoM, distinte base |
| `config` | Dati di riferimento (stati, nazioni, termini pagamento, regimi fiscali…) e credenziali |
| `vendite` | Ciclo vendite: preventivi→ordini→DDT→fatture + pipeline fatturazione |
| `acquisti` | Ciclo acquisti |
| `magazzino` | Movimenti, giacenze, lotti, seriali |
| `pagamenti` | Scadenze, riconciliazioni, contabili |
| `documenti` | Motore documentale: template versionati, documenti generati, ristampa fedele |
| `pratiche` | Motore di workflow versionato |
| `ui` | Liste configurabili (la configurazione è dato) |
| `shop` | Veste SHOP_CUSTOMER |
| `contabilita` | ⛔ **VUOTO e fuori perimetro**: zero tabelle, funzioni e viste. Se servirà sarà un **aggancio a una contabilità esterna**, con la forma dettata dal sistema di destinazione |
| `storico` | Audit temporale (storicizzazione tabelle) |
| `dbops` | Strumenti DBA, registry task, presidi, FK policy |
| `script` | Viste e funzioni applicative riusabili (building block, risoluzione permessi) |
| `maintenance` | Job schedulati (pgAgent) |
| `django` | Tabelle di Django (auth, sessioni) |
| `public` | Estensioni (`dblink`, `unaccent`, `postgis`, `plpgsql_check`, `btree_gist`), **nessuna tabella**. Per la versione applicata: `DATABASECHANGELOG` |

Schemi non applicativi presenti su dbdev: `topology` (PostGIS), `pgagent` (scheduler),
`data_conversion`, `internal`, `test`.

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
assert value is not None  # sempre dopo require, per il type checker (mypy, in CI dal 2026-10-08)

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

## Stato del Progetto — cantieri

> Lo stato reale sta nei documenti di `docs/it/dev/work-in-progress/` e nel repo; qui solo
> le decisioni di rotta e una riga per cantiere aperto.

### ⛔ Fermo dei temi trasversali sui documenti di vendita (Tid, 2026-10-21; allentato il 2026-10-25)

Il modello del documento di vendita è scritto:
[guida del modello](../docs/it/guide/modello-documento-di-vendita.md). Il fermo resta, **allentato**
(Tid, 2026-10-25, scelta C):

- ✅ un tema nuovo che tocca tutti i documenti di vendita (preventivo, offerta, contratto, ordine,
  DDT, reso, commessa, fattura, listino) è ammesso **se poggia su un pezzo comune già fatto** (un
  building block montato su tutte le testate, come la nascita nello stato iniziale) e rispetta la
  guida;
- ⛔ resta fermo il tema che andrebbe **ricopiato documento per documento** (nelle capability, nei
  guard, nei verbi di ciascuno): aspetta che il cantiere porti quei documenti al modello.

Si correggono i difetti; i brief già in esecuzione arrivano in fondo. Il perché, con i fatti datati,
sta nel §1 di `work-done/brief-modello-documento-vendita.md`. La regola generale «un tema, un
brief» è in `.codex/AGENTS.md`.

### 🔵 Il cantiere principale — `acquisti` e `magazzino` (decisione di Tid, 2026-09-11)

Le due app sono il cantiere in corso (voce D11 di
[migliorie-generali-BE-FE-da-test-valutazione.md](../docs/it/dev/work-done/migliorie-generali-BE-FE-da-test-valutazione.md)).
`magazzino` ha il comportamento dei Lotti 1-2; `acquisti` ha il solo modello DB.

⭐ **Ogni decisione presa su `vendite` è presa anche per `acquisti`** — envelope,
capability di riga, scope emittente, ordinamento, export, drawer autonomi,
`ListaConfigurabile`. Quando un'asimmetria fra i due domini emerge, si chiude
**subito**, non in una «fase due».

⚠️ `storico` **resta senza decisione** e `contabilita` resta **fuori perimetro**:
non sono la stessa cosa e non vanno letti insieme ai due sopra.

- **Magazzino, Lotti 1 e 2: chiusi** (`work-done/brief-db-magazzino-lotto-1-terreno-vuoto.md`,
  `work-done/brief-db-magazzino-lotto-2-motore.md`, `work-done/piano-be-fe-magazzino-lotto-2-motore.md`;
  API in `docs/it/backend/magazzino/manual/api_magazzino.md`). ⏳ Collaudo a video di Tid:
  `work-in-progress/collaudo-in-app-magazzino-inventario-e-rettifica.md`.
- ⏳ **Magazzino, Lotti 3 e 3-bis — la merce esce con la bolla e rientra col reso**: DB applicato
  (28/29-09), BE/FE fatto il 2026-10-13; i due brief DB **chiusi il 2026-10-14**
  (`work-done/brief-db-magazzino-lotto-3-scarico-da-ddt.md`, `work-done/brief-db-magazzino-lotto-3-bis-carico-da-reso.md`).
  Aperto in un solo documento, `work-in-progress/piano-be-fe-magazzino-lotto-3.md` (§5 i residui: CI da zero,
  vista della merce in viaggio, pgTAP kit/seriali col runner); ⏳ collaudo a video di Tid:
  `work-in-progress/collaudo-in-app-magazzino-bolla-e-reso.md`. Il difetto DB dei motivi della «Conferma» del reso
  è chiuso il 2026-10-14 (`work-done/brief-db-reso-motivi-conferma-con-valori.md`), a video al §5.3/§5.7 del collaudo.
- 📝 **Magazzino: tutte le scritture dal verbo**
  (`work-in-progress/brief-db-magazzino-tutte-le-scritture-dal-verbo.md`): bozza, cinque decisioni di Tid (§3).
- **`acquisti`**: le due date di `acquisti.ordini_righe` sono a DB **senza consumatore** (nessun
  repository di righe, nessuna chiave i18n). Alla ripartenza: quali articoli ammettono le righe
  d'acquisto è rinviato a `work-done/brief-db-articoli-ammessi-per-documento.md` §8.4 (D-5).

⭐ **I domini nuovi nascono con il permesso applicato dal DB**
(`work-done/brief-db-permesso-nel-verbo-di-scrittura.md`, D-1 → D-5 di Tid). Il modello è
«una scrittura = un verbo»: una funzione DB che nella prima riga chiama un guard —
`script.fn_guard_azione` (azione di processo), `script.fn_guard_livello` (livello sull'oggetto)
o `script.fn_guard_super_admin` (gestione accessi) — e l'app che perde la scrittura diretta sulle
tabelle che il verbo protegge (guida `architettura-permessi-e-autorizzazioni.md` §7.4-7.5).
`magazzino` e `acquisti` nascono così; gli altri domini ci passano quando un cantiere tocca le loro
scritture. Il limite è scritto: il modello protegge da un backend che **sbaglia**, non da uno
**manomesso** (l'identità la dichiara il backend). Già su verbo: le poste di inventario e
rettifica (`registra_magazzino`), il pannello di configurazione (`config.fn_pannello_scrivi`, lista
in `config.tabelle_gestibili`; `config.aree_funzionali` in sola lettura per l'app).

### 🟡 Altri cantieri aperti

- ✅ **Il modello del documento di vendita: chiuso il 2026-10-31**
  (`work-done/brief-modello-documento-vendita.md`): un giro per documento (DDT, preventivo, ordine, contratto,
  offerta, commessa, fattura, versione di listino), poi gli stati con un significato dal vocabolario (cessazione,
  accettazione) e l'arco della revisione nel lineage. Prove a video di Tid tutte ok. La guida è
  `docs/it/guide/modello-documento-di-vendita.md`. I residui sono in § «Aperto — Media priorità».
- ✅ **Il reso costruito nei pgTAP: chiuso il 2026-10-25** (`work-done/brief-db-pgtap-reso-costruito.md`,
  seguito di `work-done/brief-db-pgtap-bolla-e-reso-costruiti`): i pgTAP non ricopiano più la strada del reso
  confermato, della bolla di ri-consegna, dell'ordine con righe, della bolla senza ordine e dell'attività fatturata;
  ognuna ha il suo builder in `dbops` (`fn_pgtap_crea_reso`, `_ddt_riconsegna`, `_ordine_con_righe`,
  `_ddt_senza_ordine`, `fn_pgtap_fattura_attivita`). DB `20261025-05`, `-06`, `-31…-36`; pgTAP portati: 29 nel
  giro del reso, 64 nel D-4; verdi come app.
- ✅ **Una sola grammatica per i tipi di documento: chiuso il 2026-10-25**
  (`work-done/brief-db-grammatica-unica-documenti.md`): un tipo di documento ha un nome solo, il codice di
  `config.sorgenti` (e di `config.tipi_entita` per ciò che si può indicare, come le note), senza ponti né
  traduzioni. Lotti 0 … 3 su DB, BE e FE (testate, origine e destinazione, numeratori, aree, chiavi del push, le
  quattro tabelle delle note con `target_tipo` lungo e la FK). Lotto 4, il presidio:
  `config/test-grammatica-presidio-tipo-documento-v1` — ogni colonna che porta un tipo di documento (riconosciuta
  dal nome) ha la FK verso il catalogo, è lunga come il codice e non ha un `CHECK` con l'elenco; le eccezioni
  stanno nel test col motivo. L4-1 (Tid): la FK lega il nome, non l'accensione, e resta così. I due residui
  passati al brief del modello del documento (§10, D-G1 e D-G2).
- **Type checker del backend (D2-b): chiuso il 2026-10-09** (`work-done/piano-be-type-checker.md`;
  `0ffe7b7c3`, `ebc54fc56`): mypy col plugin Django in CI, a cricchetto (`backend/mypy.ini`,
  `backend/mypy.baseline.json`, `scripts/check_mypy_baseline.py`; sede `docs/it/dev/sicurezza-e-qualita-statica.md`
  §mypy). Registro **620 → 0** il 2026-10-09; gli envelope JSON sono `dict[str, Any]`; BB
  `utente_autenticato`/`utente_autenticato_id`. Trovati e corretti difetti veri (fra cui i 500 di riallinea/sblocca
  prezzo e l'alert scadenze listini sempre in 400). Chiuso il 2026-10-09
  `work-done/brief-db-riga-listino-propagata-dalla-commessa` (la riga di listino che ha dato il prezzo a una
  commessa è «propagata», e la regola ha una sede sola, il guard DB; il seguito D-3, chiuso il 2026-10-17, in
  `work-done/brief-db-coerenza-listino-della-riga-di-commessa`, il ritiro di `E_VENDITE_RIGA_GIA_PROPAGATA`, chiuso, in
  `work-done/brief-db-ritiro-codice-riga-gia-propagata`; e — decisione B di Tid, 2026-10-09 — la riga di listino si cita solo
  se il prezzo viene davvero da lì: il push non la scrive più, la provenienza dovrà viaggiare col prezzo dal
  documento, `brief-db-provenienza-prezzo-segue-il-prezzo`, BE in attesa). Chiuso il 2026-10-09
  `work-done/brief-db-valore-numerico-non-finito-nei-documenti` (gli ultimi 2 rilievi; deciso C, la generazione
  si ferma: CHECK «finito» su tutte le 170 colonne numeric, `20261009-10…-18`; il BE solleva il codice TECNICO
  `E_DOCUMENTI_VALORE_NUMERICO_NON_FINITO` col campo, registro mypy a 0). Chiuso il 2026-10-09
  `work-done/brief-be-db-fe-un-solo-fuso-aziendale` (un solo fuso, quello dell'azienda, su DB, BE e FE:
  `fn_fuso_operativo` e i confini del giorno, «oggi» aziendale ovunque, fase `70_dati_sistema`; BB BE
  `fuso_aziendale` e `predicato_giorno_operativo`, `TIME_ZONE = 'UTC'`, log in UTC con `Z`, ruff `DTZ`, timer
  systemd con `ExecCondition` (T-9); `date.js` nel fuso dell'azienda; CI ostile sui tre lati (T-5)). Ne eredita
  una voce `brief-db-corsa-saltata-non-e-una-corsa`: la riga di skip di `fn_job_run_start` contava
  come corsa riuscita, e le sveglie calendariali potevano saltare un periodo. DB applicato e BE/FE fatti il
  2026-10-10 (colonna `saltata`, la skip senza esito); chiuso e archiviato in `work-done/` lo stesso giorno,
  il residuo sta in § «Aperto — Media priorità». Stub `types-bleach`/`types-openpyxl`
  installati il 2026-10-09 (ok di Tid): mypy controlla anche le chiamate a quelle due librerie.
- **I presidi parlano a chi deve agire: chiuso** (`work-done/brief-db-presidi-cosa-significa-cosa-fare.md`,
  archiviato il 2026-10-06): `dbops.presidi_testi` (significato + azione, per lingua) e `chi_agisce` su
  `dbops.presidi`; il pannello mostra azione → significato → a chi tocca, il digest raggruppa per chi agisce.
  Collaudo a video di Tid superato. I residui sono in § «Aperto — Media priorità».
- **Il presidio dei processi dà il rimedio per causa: chiuso** (`work-done/brief-db-presidio-processi-testo-per-causa.md`,
  archiviato il 2026-10-10): la causa è una colonna del panorama dei processi, `dbops.presidi_cause`
  (causa → chi agisce) e `presidi_testi.variante` danno testo e destinatario per causa, il conteggio per
  causa ha sede in `dbops.fn_conta_presidio_per_variante` (`fn_conta_presidio` ne è la somma). Il pannello
  mostra ogni causa col suo conteggio e il suo rimedio; il digest manda ogni causa a chi deve agire.
  Collaudo a video di Tid superato. Il residuo è in § «Aperto — Media priorità».
- **Il presidio dei job falliti dice a chi tocca: chiuso** (`work-done/brief-db-presidio-job-run-a-chi-tocca.md`,
  archiviato il 2026-10-18): ogni riga di `maintenance.vw_job_run_da_guardare` porta una causa (corsa appesa o
  SQLSTATE dell'ambiente → `AMBIENTE`, poi la causa del codice d'errore, poi quella del processo), e il digest la
  manda a chi deve agire. Lato BE: `registered_job` scrive SQLSTATE e codice `E_` dei `P0001` (§4.2), e una corsa
  che lascia indietro elementi senza registro chiude rossa con `E_JOB_ELEMENTI_NON_COMPLETATI` (D9, BB
  `chiudi_se_elementi_non_completati`). Collaudo DB e BE di Tid superati. I residui sono in § «Aperto — Media priorità».
- **Il verde di un verdetto completo spegne la spia: chiuso** (`work-done/brief-db-intermittente-e-verdetto-completo.md`,
  archiviato il 2026-10-18): `dbops.processi.corsa_verdetto_completo` dichiara i processi il cui ogni giro ricontrolla
  tutto il perimetro (lo smoke notturno, le automazioni, il digest). Per loro `maintenance.vw_job_run_da_guardare` dà
  «intermittente» solo se il lavoro è ricaduto (due tratti rossi nei sette giorni, D4 = B): un solo tratto rosso esce
  al primo verde, e una corsa in corso da meno di un'ora non è un verdetto. Per gli altri processi niente cambia.
  Lato BE solo i commenti di `smoke_notturno.py`. Nessun residuo.
- **Una credenziale senza veste si elimina dall'applicazione: chiuso** (`work-done/brief-db-elimina-credenziale-senza-veste.md`,
  archiviato il 2026-10-07): verbo `script.fn_elimina_credenziale` + check derivata da `pg_constraint` e fail-closed senza
  il ponte django, traccia in `config.credenziali_eliminate`, all'app tolto il `DELETE` su `django.auth_user`; BE/FE
  «Elimina accesso» in kebab e drawer di «Altri accessi». Collaudo a video di Tid superato. Il residuo (D-4) sta nella
  voce ❓ sul ponte django, sotto.
- **Accessi: una credenziale, più vesti** (`work-in-progress/piano-be-fe-accessi-credenziale-e-vesti.md`):
  resta R-4, che vuole un brief DB non ancora scritto. ✅ L-6 (date della veste) fatto il 2026-10-07,
  DB e BE/FE (`work-done/brief-db-veste-utilizzabile.md`; giro 3 chiuso: «Valido al» del drawer operatore
  modificabile, spento col motivo per l'ultimo SUPER_ADMIN senza data di fine, `null` toglie la data): la regola «veste
  utilizzabile» sta in un BB a DB (`script.fn_veste_utilizzabile`), letto da tutte le sedi DB e dai
  cinque punti del BE; per l'operatore contano anche le date del rapporto; l'ultimo SUPER_ADMIN non
  scade e il batch notturno accende oltre che spegnere. ✅ L-4 fatto il 2026-10-06: portale e shop entrano con
  l'email, il reset accetta nome utente o email. Chiuso il 2026-10-03
  `work-done/brief-db-credenziale-verbi-amministratore.md` (motivo del blocco dal DB, verbi
  dell'amministratore che rifiutano le credenziali di sistema).
- **Kit in fattura: chiuso** (`work-done/brief-db-esposizione-componenti-kit-in-fattura.md`, archiviato
  il 2026-10-04): tre modi di esporre un componente (NASCOSTO, DESCRITTIVO, VALORIZZATO), DB, BE e FE
  fatti; §9.1 e §9.2 confermati da Tid, l'ordine della tendina resta quello del lookup. ✅ Chiuso il 2026-10-04
  `work-done/brief-db-bom-flag-quantita-e-kit-in-fattura.md`: flag della distinta ritirati, quantità
  e UoM del padre congelate in fattura, plafond sul **netto** della fattura (decisione C), una
  fattura che ha consumato plafond non si disfa più (strada A), proiezione del risolutore ritirata.
  Template fattura v7 pubblicato.
- **Un'esclusione del contratto non si modifica: chiuso** (`work-done/brief-db-contratto-esclusione-non-modificabile.md`,
  decisione di Tid del 2026-10-04): DB applicato il 2026-10-04 (`20261004-12…-14`, lock su
  `contratti_righe.tipo_eccezione`, due codici nuovi), pgTAP senza regressioni; BE/FE in `dda5bda1d` (§7).
  Il §7.1 l'ha chiuso il brief dell'erogazione obbligatoria. Archiviato il 2026-10-04.
- **Una riga che si fattura dice come si eroga: chiuso** (`work-done/brief-db-erogazione-obbligatoria-righe-fatturate.md`,
  archiviato il 2026-10-06): `tipo_erogazione` obbligatoria su OVERRIDE/AGGIUNTA di contratto e offerta
  (`20261004-30…-33`, codice `E_RIGA_EROGAZIONE_OBBLIGATORIA`), BE/FE in `dda5bda1d`. L'ultimo avviso l'ha chiuso
  `brief-db-righe-esclusione-solo-non-si-vende` (`20261004-40`).
- **L'esclusione è solo «non si vende», contratto e offerta con le stesse regole: chiuso**
  (`work-done/brief-db-righe-esclusione-solo-non-si-vende.md`, decisione di Tid del 2026-10-04): DB
  applicato (`20261004-40…-49`, `-70…-76`), pgTAP verdi. BE/FE primo giro fatto il 2026-10-04 (§9). Secondo giro
  DB **scritto** il 2026-10-05 (§10: `20261005-10…-19`, lista `vendite.offerta_righe` 106; la revisione copia i
  componenti, gemelle con gli stessi tipi, lock «solo in bozza» sui componenti col building block a livello RIGA —
  i rientri del reso ritirano la loro copia), applicato il 2026-10-05. BE/FE secondo giro fatto il 2026-10-05 (§11):
  endpoint della lista 106, drawer dell'offerta sui verbi del DB col BB `RigheEccezioniDrawer` condiviso col
  contratto (regola del 2, ok Tid), niente toggle «attivo». Archiviato il 2026-10-08 (§14): i trovati DB del
  §10.8 sono il brief `work-done/brief-db-righe-e-componenti-le-altre-famiglie.md`; il ricollaudo di
  C5/C3 è il §D.5 di `brief-db-offerta-emissione-ed-erogazione`.
- **Righe e componenti di preventivo, ordine e DDT allineati a contratto e offerta: chiuso il 2026-10-08**
  (`work-done/brief-db-righe-e-componenti-le-altre-famiglie.md`, `20261008-30` … `-35`, applicati, pgTAP verdi):
  la revisione del preventivo porta anche i componenti spenti (D-1 di Tid) e li lega per identità; componenti
  di preventivo, ordine e DDT solo in bozza; `user_update NOT NULL` su righe e componenti; CHECK `_nz`.
- **Righe e componenti: i tre debiti rimasti — chiuso il 2026-10-09** (`work-done/brief-db-righe-e-componenti-debiti-residui.md`,
  D20): righe d'ordine e di preventivo chiuse fuori bozza sulle tre porte (sull'ordine aperta la sola
  `data_consegna_confermata` in `CONFERMATO`/`PARZIALMENTE_EVASO`), `user_update NOT NULL` ovunque col presidio,
  lo spento in attesa si copia senza marca nella revisione. DB `20261008-80` … `-94` e `20261009-03`, pgTAP verdi
  anche su `zeroerp_ci`. Lato BE (§5): test e smoke già in forma bozza → righe → transizione; il verbo della data
  passa al brief sotto; i debiti stanno in § «Aperto — Media priorità».
- **La partita merce e il push dei DDT non leggono più tutte le attività: chiuso il 2026-10-10**
  (`work-done/brief-db-segment-base-commesse-attivita.md`, `20261010-80…-84`, applicati): colonna generata
  `commesse_attivita.segment_base` (uguaglianza indicizzabile sotto RLS anche nel piano generico) e
  `plan_cache_mode = force_generic_plan` sulla capability e sul lister dei DDT. Capability su tutti i DDT
  ~2,1 → ~0,6 s. Nello stesso giorno: `COST 5000` sulle funzioni di policy (`20261010-77`, `-79`,
  linee-guida-sql §10.3). Debito residuo: ✅ **D26-2, chiuso il 2026-10-18**
  (`work-done/brief-db-plancache-funzioni-con-query-incorporate.md`): resi col piano generico
  (`20261011-42`), lister dei DDT senza filtri (`20261012-03`, 1135 → 154 ms), pannello e liste nel brief
  della lineage; il verbo dell'accredito ~115 → 50,6 ms con `segment_base` (`20261018-15`), il perimetro
  dell'operatore calcolato **una volta per istruzione** in tutte le policy ef_whitelist
  (`fn_scope_ef_perimetro` + `fn_get_emittenti_scope_pk_ids` in una sottoquery, emittente della riga da
  `fn_resolve_emittente_fiscale_id` DEFINER; `20261018-16…-33`, `-48…-51`; regola in linee-guida-sql
  §10.3) e il `tx_id` sulla connessione di log persistente (`20261018-52`, 12 → 1,3 ms a transazione).
  Residuo D36 chiuso il 2026-10-21 (sotto).
- ✅ **I ruoli di sistema: chiuso il 2026-10-15** (`work-done/brief-db-ruoli-di-sistema.md`): nomi fissi
  (`zeroerp_owner` proprietario di tutto, `zeroerp_job` per pgAgent, `zeroerp_app`, `zeroerp_log`),
  password senza default, un provisioning solo (`scripts/sql/provision_zeroerp.sql`, fasi `ruoli`/`pre`/`post`)
  per CI, scratch e installazione. dbdev convertito (`converti_db_al_modello_ruoli.sql`: `titodb` lavora
  come `zeroerp_owner` con `SET role`), pgAgent come `zeroerp_job` sulle procedure dei job `DEFINER`, il
  giornale registra il ruolo di ogni corsa (presidio `vw_job_run_da_superuser`). Ritirati `zeroerp_batch_fatturazione`,
  `pgagent`, `zeroerp` e `zeroerp_ci` (`scripts/ritira_ruoli_dismessi.sh`). Guida: `installazione.md`, «Il database».
  Il debito residuo (D35: `zeroerp_log` nella fase `ruoli`) è chiuso lo stesso giorno
  (`work-done/brief-db-zeroerp-log-nella-fase-ruoli.md`).
- ✅ **Le statistiche delle tabelle: un job notturno (D15) — chiuso il 2026-10-15**
  (`work-done/brief-db-statistiche-tabelle-job-notturno.md`): verbo `maintenance.fn_analyze_statistiche` con
  autoverifica (`reltuples < 0`, `MAINTAIN`, errore `E_STATISTICHE_MANCANTI`), procedura dal giornale, riga in
  `dbops.processi` con `ci_ordine` ultimo (in CI gira nella convergenza di `ci_apply`), job pgAgent alle 02:30
  (`20261014-50…-54`). Provato su dbdev il 15-10: corsa notturna riuscita e corsa di pgAgent come `zeroerp_job`
  riuscita. Guida: `guide/statistiche-del-planner.md`.
- ✅ **Un cliente manuale per soggetto, utility e azienda (D33) — chiuso il 2026-10-15**
  (`work-done/brief-db-cliente-manuale-uno-per-soggetto-e-utility.md`): fra le istanze fittizie un cliente solo
  per soggetto + utility + azienda emittente nello stesso periodo, controllato al COMMIT (`E_CLIENTE_STESSA_CHIAVE`,
  predicato unico `anagrafiche.fn_clienti_stessa_chiave`); grafo degli stati in `config.transizioni_stati_cliente`
  (un chiuso non si riapre, ogni stato pretende la sua data, `data_chiusura` di un chiuso ferma); «attivo» = il
  periodo anche per il PDP, la disdetta e `ha_ba_attivo` (`20261014-08…-20`). BE: rifiuto al COMMIT, smoke clienti
  verde il 15-10. I residui (§7 del brief: avviso del pre-contrattuale, PDP libero il giorno della chiusura, pgTAP
  del PDP sul periodo, data di attivazione di un chiuso) fanno parte dello sviluppo delle utility (Tid, 15-10).
- ✅ **La lineage dei documenti si costruisce per il documento: chiuso il 2026-10-11**
  (`work-done/brief-db-lineage-seminata-per-chiave.md`): grafo seminato per chiave (`fn_documento_lineage_nodi`,
  `_archi`, `_sintesi`), le sette viste di lista senza il grafo e `vw_documento_lineage` ritirata
  (`20261011-62…-67`, `-92…-99`, pgTAP verdi). BE (B1): liste, export e drawer leggono le colonne del grafo
  dalla sintesi dopo la paginazione (BB `unisci_sintesi_lineage`). Chiusa con lui anche la D-5 del brief
  plancache (lista offerte letta per id). Nello stesso giro i codici di `config.sorgenti` in un posto solo
  (`apps/config/sorgenti.py`) e un solo lookup per codice (`SorgentiRepository`).
- ✅ **Offerta: emissione ed erogazione: chiuso il 2026-10-22**
  (`work-done/brief-db-offerta-emissione-ed-erogazione.md`, dal collaudo del drawer del 2026-10-07): la versione
  di listino la congela il DB all'emissione; erogazione e fonte le eredita la riga dall'articolo, dentro il
  perimetro della utility; la quantità segue la fonte (DERIVATA_COMPONENTI ritirata, il kit si vende solo FISSA);
  le righe già scritte le intercetta il primo passo che le usa (emissione, push, genera ordine, attivazione:
  `E_DOC_RIGA_NON_AMMESSA`); «Genera ordine» è il verbo DB `fn_genera_ordine_da_offerta`; un'offerta ACCETTATA
  si annulla se non ha documenti vivi a valle. DB `20261021-44…-61`, BE/FE §J, collaudo di Tid ok. Proposta
  aperta, non bloccante: il «perché» nel tooltip di `RIGA_NON_AMMESSA` (§J.4).
- ✅ **Quali articoli ammette un documento: chiuso il 2026-10-23**
  (`work-done/brief-db-articoli-ammessi-per-documento.md`): una regola sola per il picker e per il guard. La sede
  unica del picker è `catalogo.fn_articoli_ammessi`, che giudica con la stessa check dei guard di riga
  (`script.fn_check_articolo_riga_su_contesto`); a video l'escluso resta in elenco, spento, col motivo
  (`ArticoloLookup` con `documento`). L'articolo usato non cambia struttura se non con la correzione del
  SUPER_ADMIN, nel PATCH e in una transazione (R-BE-1), con le colonne lette dalla sede
  (`fn_articolo_colonne_struttura`) e il rifiuto se rende non valide righe aperte (A-11). DB Lotti 1-5 e
  `20261018-70…-74`, BE/FE §9.7 e §9.8.7, collaudo di Tid ok. Restano fuori: il ponte di
  `fn_articolo_riga_contesto` (brief della grammatica unica), D-5 (righe d'acquisto, col cantiere `acquisti`).
- 📝 **Canone, orario e consumo del contratto in commessa**
  (`work-in-progress/brief-db-contratto-righe-periodiche-in-commessa.md`, D31, 2026-10-13): il push dei
  contratti manda solo le righe UNA_TANTUM, col giorno di attivazione (`20261013-24`, D-1/D-2 di Tid); la
  generazione per periodo del canone e le quantità di orario e consumo dalle loro fonti: aperto, non
  iniziato (G-1…G-4). Nello stesso giorno `tipo_consumo` ritirato dalla catena del push (`20261013-16…-23`).
- 📝 **Dove si addebita il trasporto di un ordine fatturato alla conferma**
  (`work-in-progress/brief-db-addebito-trasporto-ordine.md`, da A-9 del brief sopra): aperto, non iniziato.
- ✅ **Codici d'errore per email, «accesso riservato» e «non trovato» del dettaglio ricerca: chiuso il 2026-10-10**
  (`work-done/brief-db-codici-non-trovato-email-e-permessi.md`, voci E-4/E-5/E-10 dell'analisi della doc API core):
  R-1…R-4 e R-5…R-9 applicati, pgTAP verdi (`20261010-08…-15`: regola unica di chi si vede nella ricerca su
  `tipi_ruoli.entita_esistenza`, ritiro di `p_emittente_ids`, builder `dbops.fn_pgtap_crea_cliente`, quattro codici);
  BE fatto (§9, §15).
- ✅ **Ricerca universale senza tetto: chiuso il 2026-10-10**
  (`work-done/brief-db-ricerca-universale-tetto-10000.md`, D23): il tetto della lista era un `LIMIT` senza
  `ORDER BY`. Pagina sulle righe semplici, aggregati solo per la pagina, via l'ordinamento per utility (nessun
  tetto). DB `20261010-16`; BE/FE il 2026-10-10 (§7.4), con l'e2e che tiene allineato il mirror delle colonne
  ordinabili (`test_search_ordinamento_db`).
- ✅ **L'istanza nasce col billing account, sempre: chiuso il 2026-10-10** (`work-done/brief-db-istanza-nasce-col-ba.md`,
  D10-bis): DB `20261008-50…-76`, BE/FE il 2026-10-08 (§7: la pratica sceglie la fornitura, cioe' il BA — D-10).
  Collaudo del preventivo superato; quello delle pratiche è in § «Aperto — Media priorità».
- ✅ **I residui di «l'istanza nasce col billing account»: chiuso il 2026-10-10**
  (`work-done/brief-db-istanza-nasce-col-ba-residui.md`, D25): via `script.fn_get_billing_account_by_istanza` e il
  motivo `PREVENTIVO_SENZA_BILLING_ACCOUNT` coi suoi due filtri gemelli (residuo commessa, lista del push); liste del
  push senza il filtro inutile sul BA, lo stato assente ferma invece di aprire; ritirato `uq_gestori_singleton`;
  lo spostamento dell'azienda predefinita non dipende più da chi lo fa (BB `script.fn_get_ba_emittente_sr_id_installazione`).
  DB `20261010-50…-59`, pgTAP verdi anche su `zeroerp_ci`; FE la chiave tolta dai locales, BE una riga di doc.
- ✅ **La data minima del filtro «ritardo» delle dashboard: chiuso il 2026-10-10**
  (`work-done/brief-db-parametro-data-minima-ritardo-dashboard.md`): parametro `VENDITE_DASHBOARD_RITARDO_DATA_MINIMA`,
  un solo controllo nel BE per le due dashboard, collaudo di Tid superato.
- ✅ **Ordine, DDT e reso: il cliente come su preventivo, offerta e contratto: chiuso il 2026-10-10**
  (`work-done/brief-db-esecutivi-ba-coppia.md`, D21): l'ordine ha sempre il BA, il DDT lo vuole all'emissione
  se la causale manda merce a un cliente, il reso ha quello del suo DDT; utility e ruolo legati al BA, un solo
  BA lungo la catena, BA/destinatario/emittente fermi dopo la bozza. DB `20261009-62…-92` e `20261010-02…-07`,
  BE/FE §12. Collaudo a video dei form di DDT e ordine da fare (Tid). Ciò che la chiusura ha trovato è D27 (sotto).
- ✅ **Gli indirizzi del documento seguono il cliente: chiuso il 2026-10-19**
  (`work-done/brief-db-indirizzi-documento-seguono-il-cliente.md`, D27): un indirizzo preso dall'anagrafica e'
  del cliente del documento. Nel DB: slot di default come dato, guard d'origine sulle `*_indirizzi`, al cambio di
  cliente in bozza il DB toglie gli indirizzi del cliente di prima e riempie lo slot dal nuovo, scheda di
  fornitura che segue il cliente (offerta, contratto), emittente e utility ferme anche in bozza su preventivo,
  offerta e contratto (lock di testata «ferma sempre»). BE/FE: helper ritirati, rifiuto delle colonne ferme sul
  campo (`rifiuta_colonne_ferme`), chiavi ignote rifiutate sui PATCH di preventivo e DDT, il cambio di cliente
  in modifica si salva subito con conferma (`useCambioClienteDocumento`), lookup del cliente ricostruito
  (`ripristinaBillingAccount`). Collaudo di Tid superato (2026-10-19). Nato nel collaudo e fatto lo stesso giorno,
  fuori dal brief: «Attiva» del contratto spento sopra un contratto vincolante sovrapposto (DB `161ac98af`, BE/FE
  `d54d67041`), collaudato da Tid il 2026-10-19.
- ✅ **Le righe di un DDT nato da un ordine: chiuso il 2026-10-11**
  (`work-done/brief-db-ddt-righe-evase-dall-ordine.md`, D28): la riga evasa (da ordine o da reso da
  ri-consegnare) e' ferma, la quantita' si corregge solo dal verbo `vendite.fn_ddt_riga_correggi_qta_evasa`,
  si cancella in bozza ritirando i legami, e l'annullo di una bolla con legami li ritira con conferma
  (`vendite.fn_annulla_ddt`). DB `20261011-05 … -20`, `-34`, `-35`; BE/FE §10; collaudo di Tid superato.
  Nessun residuo: il cambio di stato del DDT dal verbo resta nel Lotto 3 (sopra).
- ✅ **Annullare un documento con legami: chiuso il 2026-10-11**
  (`work-done/brief-db-annullo-documento-con-legami.md`, D29): bolla, ordine, preventivo e contratto si
  annullano dal loro verbo (`vendite.fn_annulla_<documento>`) con l'avviso `E_DOC_ANNULLO_CON_LEGAMI`, la
  finestra di conferma comune (lettore unico `vendite.fn_documento_legami`) e la dichiarazione dei legami
  visti; l'origine si riapre (ordine da evadere, reso da ri-consegnare, preventivo di nuovo ACCETTATO,
  offerta di nuovo trasformabile: unicita' sui soli vivi). DB `20261011-68 … -91` + caso 1 del giro D28;
  BE/FE §9; collaudo di Tid superato. Il verso dalla commessa e' D30 (sotto).
- ✅ **Tornare indietro: annullare a valle riapre a monte — chiuso il 2026-10-13**
  (`work-done/brief-db-annullo-a-valle-riapre-a-monte.md`, D30): la commessa si annulla dal verbo
  (`vendite.fn_annulla_commessa`) con la finestra comune di D29; preventivo, ordine, contratto, bolla, reso e
  consumi si riaprono, gli oneri si annullano. Una riga di commessa ANNULLATA non occupa piu' il documento
  (D-5); «Evaso» dell'ordine = solo bolle (D-6); il documento con righe in una commessa viva non emesse si
  annulla con conferma (D-8); il verso in avanti verso la commessa sta tutto nel DB (D-10). Il link
  documento → commessa resta come storia, una sola commessa aperta per documento, lo scrive la madre
  `fn_upsert_commessa_attivita` (D-12, D-13); il lineage dice quando il legame e' ritirato
  (`is_legame_ritirato`, a tre stati, D-15). DB `20261012-08 … -24`, `-27 … -29`, `-43 … -47`,
  `20261013-69 … -72`; BE/FE §9, §10.8, §11.6; collaudo di Tid superato. ⚠️ `dev/db-tid` (`-69 … -72`) va
  mergiato prima del BE/FE del §11.6. Il residuo (la commessa vuota del push batch) e' in § «Aperto — Media
  priorità».
- ✅ **L'emittente del documento e' quello del cliente: chiuso il 2026-10-10**
  (`work-done/brief-db-guard-emittente-ba-unico.md`, D22): il guard emittente <-> BA estratto in un BB
  (`script.trgfn_doc_guard_emittente_ba`), un codice e una frase leggibile; DB `20261010-17…-19`, BE §9. Il seguito
  e' **D24** del registro DB (`migliorie-generali-da-test-valutazione.md`): la vista del presidio C2 non vede i BB
  trigger col codice in `TG_ARGV`, e il BE tiene un'esenzione su `E_DOC_EMITTENTE_BA_INCOERENTE` finche' non la vede.
- ✅ **Il documento dopo la bozza: che cosa si cambia ancora — chiuso il 2026-10-11** (`work-done/brief-db-testata-dopo-emissione.md`,
  D26, 2026-10-10): oggi la regola completa sta solo nel backend («solo in DRAFT»); il DB ne blocca dei pezzi.
  Colonne divise in famiglie (identità, stampato, arriva dopo, note, condizioni commerciali). Decisioni chiuse
  il 2026-10-10: decide il DB, il BE toglie i suoi «solo in DRAFT»; documento chiuso = tutto fermo (D-8).
  Fasi 1 e 2 applicate (2026-10-10), BE/FE fatti. Giro R-DB (§11, 2026-10-11, D-11/D-12/D-13 di Tid) applicato:
  lock «solo in bozza» su indirizzi e fornitura dei documenti, cliente della bolla dal guard, regole del listino
  sotto le righe a DB per contratto e offerta, congelamento del listino provato. BE/FE fatti (§12) e collaudo a
  video di Tid superato il 2026-10-11; `E_CONTRATTO_NON_MODIFICABILE` ritirato. Archiviato il 2026-10-11.
- ✅ **Un testo non si riempie di spazi: chiuso il 2026-10-10** (`work-done/brief-db-character-n-spazi-di-riempimento.md`):
  colonne `character(n)` a lunghezza variabile portate a `varchar` (`20261010-26…-40`), sigla di provincia con la
  sua regola, `destinatario_fe` diventato il canale FE (P/C) che pretende il suo recapito; BE/FE e collaudo a video
  superati. Regola nuova: §7e di `linee-guida-sql.md`, presidio `test-character-n-v1`. BB FE `InputMaiuscolo`.
- ✅ **Il perimetro una volta per istruzione: chiuso il 2026-10-21** (`work-done/brief-db-perimetro-una-volta-famiglie-residue.md`,
  D36): nessuna policy calcola più per riga ciò che dipende solo da chi guarda. Vesti di controparte
  (cliente portale, shop, fornitore) con `fn_get_identita_sr_perimetro` + `fn_resolve_controparte_sr_id` +
  `fn_scope_sr_perimetro`; email con `fn_scope_email_ambito_perimetro`; note e coppia dell'operatore nella
  forma già pronta. `20261021-24…-43`; regola in linee-guida-sql §10.3; presidio senza eccezioni.
- ✅ **Dati societari in creazione: chiuso il 2026-10-22** (`work-done/brief-db-dati-societari-in-creazione.md`,
  D34): le due porte di creazione ricevono la sezione intera, data di costituzione compresa, e la ditta
  individuale non la perde più; quando scriverla lo decide il BB `fn_scrivi_dati_societari_alla_nascita`,
  e una sezione passata a un privato si rifiuta (`20261020-01…03`). BE: binding della sezione in un BB del
  repository (catalogo BB «Anagrafiche — Soggetti»), contratto della PATCH anche in creazione; FE: data di
  costituzione anche in creazione. Collaudo di Tid riuscito il 22-10.
- ✅ **Dati fiscali e societari del soggetto: chiuso il 2026-10-14** (`work-done/brief-db-dati-fiscali-e-societari-del-soggetto.md`,
  2026-10-10): (A) «Cliente PA» e «Split payment» ammessi per ogni natura, anche per un privato; (B) in modifica i
  dati societari non si salvano, serve il verbo di scrittura (decisione di Tid); (C) la forma giuridica non è legata
  alla natura, e il drawer la mostra vuota; (D) un titolo IVA si registra su qualunque soggetto (assorbito
  `brief-db-regime-fiscale-per-natura-soggetto`, rimando cancellato il 2026-10-12). ✅ Lato DB applicato e verde il 2026-10-10 (§8):
  verbo `fn_scrivi_dati_societari` unica porta, regole per natura su flag, titoli e forma. ✅ BE/FE scritti e verdi
  il 2026-10-10 (§9) e collaudati in-app il 2026-10-11, con due difetti trovati e corretti: il lookup delle forme
  falliva sempre (colonna inesistente) e il cambio di natura in modifica non arrivava al DB. Archiviato il
  2026-10-14: la data di costituzione in creazione è nel brief qui sopra, gli altri residui in § «Aperto — Media priorità».
- **Quali processi sono accesi: per ambiente, a mano, i non spegnibili: chiuso**
  (`work-done/brief-db-processi-accensione-per-ambiente.md`, archiviato il 2026-10-19): l'ambiente
  dell'installazione è un dato del DB (`dbops.installazione`, scelto al provisioning, immutabile, lettori
  `script.fn_ambiente_installazione()` / `fn_ambiente_dichiarato()`); default per ambiente e «spegnibile» in
  `dbops.processi` (sette mai spegnibili), scelta a mano in `dbops.processi_accensione`, cancello
  `maintenance.fn_sveglia_accesa` su pgAgent e systemd, stato `SPENTO` nel panorama. Dati di sviluppo dal verbo
  `fn_provisiona_dati_di_sviluppo` con le etichette (rifiutati in `PRODUZIONE`), `smoke` → `dev.smoke`. Strada (b):
  prima i building block, poi le copie del backend ritirate (emittente, cliente, fornitore, veste portale,
  magazzino, profilo e legami, override, emittente attivo, indirizzi singolari e plurali). Ultimi giri: registro
  delle fatture che nasce con l'emittente (R-BE-14), profilo SUPER_ADMIN da un lettore (R-BE-11), l'istanza di
  indirizzi, contatti e conti del ruolo è del soggetto del ruolo e il soggetto di un ruolo non cambia (R-BE-15).
  Fuori da qui: i template di default dell'emittente, in `brief-db-modelli-documento-standard`.
- ✅ **I modelli di documento standard: un emittente nuovo emette dal primo giorno — chiuso il 2026-10-21**
  (`work-done/brief-db-modelli-documento-standard.md`): un modello standard per tipo di documento, di
  sistema (emittente NULL, flag `standard`, scritto solo dai changeSet), usato come ripiego quando
  l'azienda non ha modelli suoi che stampano (strada B). Una porta sola per «con che modello e che
  versione si stampa», anche col modello indicato (`documenti.fn_risolvi_template_applicabile`), «può
  stampare» in una vista sola (`vw_template_versioni_stampabili`), «personalizza» e la copia di una
  versione come funzioni del DB, lo scarto delle copie dallo standard da cui derivano. Nello stesso
  brief: i parametri d'importo per utility con un valore di sistema (`config.utilities`) e una
  catena sola per riga e totale (`fn_parametri_importo_riga`), la sede legale del cedente pretesa
  all'uscita dalla bozza. BE/FE in `7385889b9`: la lista Modelli documento dice con che cosa stampa
  ogni azienda, lo standard si apre in sola lettura e si personalizza. Collaudo di Tid superato. I
  residui sono in § «Aperto — Media priorità».
- ✅ **Gli utenti di sviluppo: forniti da un verbo, etichettati, mai in produzione — chiuso il 2026-10-22**
  (`work-done/brief-be-utenti-di-sviluppo.md`): gli utenti `dev.*` (smoke, lettura, bloccato, emittente, portali,
  fornitore, multiveste) e i soggetti di prova (emittenti DEVA/DEVB, clienti, fornitore) li crea
  `fn_provisiona_dati_di_sviluppo` (command `provision_utenti_sviluppo`), riconosciuti dall'etichetta; la lista
  Operatori li nasconde di default. Gli smoke Python si **costruiscono** la materia dalle radici di prova
  (BB `scripts/tests/_smoke_fatturazione.py`) e dai builder `dbops.fn_pgtap_crea_*`, che accettano `dev.smoke`
  sull'emittente scelto: niente più «l'ultima riga che c'è». Giro degli smoke da 20 a 2 non-verdi (2026-10-18 → 10-22), tutti e due
  dei resi. Trovati e chiusi col DB lungo la strada: il listino che non si spegneva (guard orfani; un listino con
  storia si spegne solo con la fine validità, `E_LISTINO_CON_STORIA_NON_SPEGNIBILE`, toggle dal DB
  `fn_listino_ha_storia`), il rilancio del lotto che prendeva l'emittente predefinito, la riga di fattura senza
  IVA (`E_FATTURA_RIGA_IVA_MANCANTE` entrando in EMESSA), il contratto dell'attività coerente col BA
  (`E_ATTIVITA_CONTRATTO_INCOERENTE`). Collaudo di Tid superato. Nessun residuo.
- 📝 **La catena delle istanze su un PDP** (`work-in-progress/brief-db-catena-istanze-pdp.md`, D18 del registro DB):
  proposta da analizzare, cinque decisioni di Tid.
- **Le liste di documento erano lente: chiuso** (`work-done/brief-db-liste-documento-lineage-lenta.md`, archiviato
  il 2026-10-05): sotto RLS la lineage si ricalcolava per ogni riga della lista. `20261005-20` (lineage calcolata una
  volta per query) e `-21` (archi: tre letture una volta sola), applicati: le sette liste ~0,18 s la pagina (preventivi
  da ~6 s), l'albero del drawer 1,1 → 0,2-0,3 s, righe identiche. Nessun lavoro BE/FE.
- **GUIDA roll-out multi-dominio** (`work-in-progress/brief-design-guida-rollout-multidominio.md`):
  deciso, si parte da OFFERTA.
- **PrimeVue 5** (`work-in-progress/piano-migrazione-primevue-5.md`): leggere prima il §1-bis, il
  cambio di licenza.

### Aperto — Media priorità
- **Residui di `work-done/brief-modello-documento-vendita.md`** (ereditati il 2026-10-31 dalla chiusura, §18.6),
  nessuno bloccante:
  - **i permessi `emetti_offerta`, `emetti_contratto`, `emetti_ordine`, `attiva_listino` ai profili** su dbdev:
    al 2026-10-26 nessun profilo li aveva, e senza nessuno emette, attiva o cessa quei documenti. Di Tid;
  - **due rami del preventivo senza strada dall'interfaccia** (§18.4): la riaccettazione di un preventivo già
    accettato (aggiorna la sola modalità di fatturazione) e «Genera pratica» (`genera_pratica`). Ritirarli o dar
    loro un accesso. Di Tid;
  - **`DocumentoDrawerHost` tace sul drawer che non si carica** (`catch { return }`): il click su una tappa dei
    «Passaggi» non fa niente, senza avviso né console (visto a video il 2026-10-31). Proposto un avviso. FE, con
    l'ok di Tid.
- **Residui di `work-done/collaudo-in-app-capability-annidata-e-prezzi-autorizzati.md`** (ereditati il
  2026-10-24 dal collaudo passato, §3):
  - **il reset del rifiuto sta solo nel BE del preventivo** (`preventivi_service.py` `aggiorna_riga`,
    «Auto-reset stato approvazione»), nessun trigger a DB: una correzione del prezzo che non passa da lì
    lascia la riga `REJECTED` e il documento bloccato. Su contratto e offerta un reset equivalente non
    risulta: asimmetria del modello. Da decidere, di Tid, se la regola vada a DB, simmetrica su tutti i
    documenti; brief DB nuovo;
  - **la riga `test-preventivi-approvazione-prezzo.sql`** è ancora in `db/pgtap/baseline-rossi-ci.tsv`
    (`ERRORE_FIXTURE`): si toglie dopo la corsa CI su `Tito-dev` (`scripts/pgtap-baseline-ci-rientrati.sh`).
    Team DB.
- **Residui di `work-done/brief-db-modelli-documento-standard.md`** (ereditati il 2026-10-21 dalla
  chiusura, §11.5.4 e riga 10):
  - **il giro degli smoke su `dev.smoke`** (§7, B-11): DEVA emette con lo standard e chiude una
    fattura. Non fatto: il brief si è chiuso col collaudo a video. BE;
  - **B-8, la matrice utility dell'emittente**: mostra solo l'override grezzo. Mettere nei suoi campi
    i parametri di sistema li farebbe leggere come override; la forma proposta sono due campi
    «effettivo» da `anagrafiche.fn_parametri_importo_utility` e una colonna FE accanto. Da decidere,
    di Tid;
  - **la numerazione della versione nuova** di un template: la versione scritta da zero la numera il
    BE (`next_versione_num`, MAX+1), la copia la numera il DB (`fn_crea_bozza_da_versione`). Due sedi
    dello stesso numero; si chiude con un verbo DB per la versione nuova. Brief nuovo se Tid vuole;
  - **`vendite.fatture.utility_id NOT NULL`** (§10.9, facoltativa): l'unico creatore applicativo la
    pretende già, molte fixture pgTAP inseriscono fatture senza. Di Tid.
- **Residui di `work-done/brief-db-presidio-job-run-a-chi-tocca.md`** (ereditati il 2026-10-18 dalla chiusura),
  nessuno bloccante:
  - **errori lato client senza SQLSTATE** (§12): una connessione che cade dentro un command arriva come
    `OperationalError` senza SQLSTATE e va a `PROGRAMMA`. Se servirà, la strada è riconoscere la classe Python
    (`OSError`, `ConnectionError`), che è la tassonomia lasciata al BE dal §4.2. BE;
  - **`SMOKE_GIRO_FALLITO`** copre sia il tetto di tempo sia lo script uscito con 2 (§12): si separa quando lo
    smoke avrà un caso reale da instradare diversamente. BE;
  - **`error_detail` con la riga `CONTEXT:`** (§5, visto nel collaudo del 2026-10-18): per un errore PL/pgSQL
    `registered_job` scrive `str(exc)`, che porta il `CONTEXT` del driver su una riga nuova, e il digest stampa la
    voce spezzata. BE;
  - **il `%TYPE` mancato del giro 1** (§10.1-bis): debito noto, deciso di non riscrivere (Tid, 2026-10-16). DB.
- **Residui di `work-done/brief-db-dati-fiscali-e-societari-del-soggetto.md`** (ereditati il 2026-10-14 dalla
  chiusura):
  - **D-4, che cosa registra il titolo IVA `COOPERATIVA`** (§4): l'aliquota agevolata delle cooperative sociali
    riguarda di solito le prestazioni rese **dalla** cooperativa, ma il titolo sta sul cliente. Finché non è
    chiarito, `COOPERATIVA` non ha righe nella matrice `config.tipi_titolo_iva_tipi_soggetto_dettaglio`, e quindi
    non è ammesso su nessun soggetto. Se la risposta è «titolare il cliente», basta una riga nel CSV. Altrimenti il
    titolo è nella tabella sbagliata. Da decidere, di Tid;
  - **censimento dei titoli IVA fuori regola** (§8.2, query pronta): la deve lanciare Tid **come owner**, perché
    come app la RLS non mostra nessun titolo. I titoli fuori regola non bloccano niente, ma alla prossima
    modifica il guard li rifiuta;
  - **`SGT-0000121` con `cliente_pa = 'S'`** (§8.1): un privato, il caso della segnalazione. Il guard lo rifiuterà
    alla prossima modifica dei flag o della natura. Da riportare a `N` a mano (Tid);
  - **`anagrafiche.fornitori.split_payment`** (§7): nullable, senza regola sulla natura, senza lettori oltre
    `vw_fornitori_dettaglio`. Sul passivo la scissione dipende dall'emittente, non dal fornitore: forse è nella
    sede sbagliata. Da verificare; se confermato, brief suo.
- **La commessa vuota lasciata dal push batch** (DB + BE, ereditata il 2026-10-13 dalla chiusura di
  `work-done/brief-db-annullo-a-valle-riapre-a-monte.md` §10.8): nel push batch (`pr_run_commesse_push`,
  best-effort per riga) la commessa nasce prima che il batch delle righe le accetti; se una riga e'
  rifiutata, per qualunque causa, la commessa resta vuota e aperta e il ponte di emittibilita' scrive un
  errore nel report. Strade di modello: (a) il fan-out chiede al DB la commessa aperta del documento prima di
  crearne una; (b) le righe di un documento si scrivono dentro il suo savepoint; (c) il DB non crea la
  commessa vuota. Da decidere, di Tid con il team DB.
- **Residui di `work-done/brief-db-istanza-nasce-col-ba.md`** (ereditati il 2026-10-10 dalla chiusura):
  - ⏭️ **collaudo a video delle pratiche** (§7.4): la tendina della fornitura (una riga per fornitura, con la
    utility), nessun campo fornitura su chi non è cliente, offerta e contratto col cliente ereditato dalla
    pratica. Rimandato da Tid: si fa alla ripresa del cantiere pratiche;
  - ✅ **il resolver per istanza e il motivo «senza billing account»**: chiusi e archiviati il 2026-10-10
    (`work-done/brief-db-istanza-nasce-col-ba-residui.md`, D25; voce in § «Altri cantieri aperti»).
- **La coerenza tra codice fiscale e sesso ha una sede sola, e parziale** (DB + BE, ereditata il 2026-10-10
  dalla chiusura di `work-done/brief-db-sesso-senza-default.md`, D5, rimandata da Tid il 2026-10-09): la
  controlla solo `SoggettiService._valida_cf_congruenza`, e solo nella **creazione** di una persona fisica.
  Una modifica (`PATCH`) di sesso o CF, o chi scrive senza passare dal BE, può mettere un CF da donna con
  sesso `M`. `X` e i CF esteri non si possono confrontare. Da decidere, di Tid: se la regola scende nel
  guard del DB, o resta nel BE estesa alla modifica.
- **La corsa appesa non è «in corso» nella liveness del BE** (BE/FE, ereditata il 2026-10-10 dalla chiusura
  di `work-done/brief-db-corsa-saltata-non-e-una-corsa.md` §8.7): una corsa col processo vivo che tiene il
  lock, seguita da skip, ha come riga più recente la skip, chiusa; `job_liveness`/`list_job_summary` dicono
  `in_corso = false`, e badge e digest non la mostrano. Il caso lo vede `maintenance.vw_job_run_da_guardare`
  («presa e mai chiusa»), coerente con D3 di quel brief. Se la si vuole anche nel BE: `in_corso` dall'ultima
  corsa **vera**, con la sua data di avvio — un campo in più nella forma condivisa con la coda lavori. Da
  decidere, di Tid.
- **La lista dei processi non dice se un processo gira adesso** (ereditato il 2026-10-10 dalla chiusura di
  `work-done/brief-db-presidio-processi-testo-per-causa.md` §6.6): «Attivo» è il flag del catalogo, «Esito»
  quello dell'ultima corsa registrata (per un servizio `SESSIONE`, l'avvio). Lo stato vivo (`OK`, `MUTO`,
  `JOB_SPENTO`…) lo calcola già `dbops.vw_processi_programmazione`: una colonna «Stato» in `amm.processi`
  vuole la riga nel seed della lista (DB) e la lettura nel repository. Proposta, da decidere di Tid.
- **Presidi, i residui del brief dei testi per chi agisce** (ereditati il 2026-10-06 dalla chiusura di
  `work-done/brief-db-presidi-cosa-significa-cosa-fare.md`):
  - ✅ **due nomi di schermata sbagliati nel CSV** `80_data/sql/dbops/presidi_testi.csv` (§9.3): corretti nel
    giro di `work-done/brief-db-elimina-credenziale-senza-veste.md` (§7.2), applicati il 2026-10-07;
  - **D-4**, le quattro misure larghe per costruzione (`vw_codici_errore_forme_condizione`,
    `vw_codici_errore_da_dichiarare`, `vw_punti_primo_motivo`, `vw_punti_canale_campo`): il pannello le mostra
    come un numero da guardare. O diventano `INVENTARIO`, o la natura del pannello si separa da quella del
    cancello (§7, decisione del team DB e di Tid);
  - la **postura in sola lettura** di `dbops.presidi` e `dbops.presidi_testi` per l'app (§8.1): oggi il loop
    dei grant di `ci_apply` dà anche la scrittura. Non chiesta, da decidere.
- **`HTML_MARKDOWN_BLOCKS` si sceglie ma non fa niente** (BE `documenti`, ereditato il 2026-10-04
  dalla chiusura di `work-done/brief-db-vocabolari-versione-template.md` §5.6): il valore sta nel
  vocabolario `documenti.formati_template` (la Decisione 4, «markdown solo per blocchi controllati»),
  ma il render tratta ogni versione come HTML e non legge `markdown_template`. Da decidere se
  implementarlo o ritirarlo, quando si tocca il trattamento del markdown.
- **Le versioni pubblicate stampano coi margini delle colonne (15 mm), non coi 18/16 mm del loro
  CSS** (dal 2026-10-04, R-BE-V2a di Tid: la pagina la decidono le colonne). Per tornare ai 18/16 mm
  servono versioni nuove con i margini nelle colonne; l'`@page` di formato e margini nel loro CSS
  non ha più effetto (restano i piè di pagina). Le ristampe dei documenti già emessi escono coi 15 mm.
- 🟡 **L'editor dei workflow perde le righe in compilazione senza chiedere** (FE, ereditato il
  2026-10-03 dalla chiusura di `work-done/analisi-fe-chrome-drawer.md`, D-13): `DefinizioneEditorView`
  e i pannelli di passi e archi (`useEditableCollection`) non tengono la fotografia del form di riga,
  quindi cambiare riga o uscire butta cio' che si e' scritto. Il rimedio esiste ed e' provato sui
  documenti: fotografia nel form (`useDrawerFormPreserve`) + `confermaCambio` di `useFormInline`.
  Non fatto con il resto perche' non e' un drawer documento e ha form propri: un giro a se'.
- **`E_ATTIVO_REQUIRE` è TECNICO anche quando il dato l'ha scelto una persona**
  (DB, `dbops`; residuo di `work-done/brief-db-modifiche-certe-ciclo-vendita-e-articolo.md`): il
  codice del require generato dal framework ATTIVO è candidato allo split, per **tutte** le coppie
  ATTIVO: oggi un riferimento a un dato disattivato scelto dall'operatore esce come 500, lo
  stesso codice di un trigger montato male. Cantiere `dbops`, non di dominio; intanto il BE
  pre-verifica «attivo» e risponde 400 col campo (§5.5 nota 2 e tabella dei residui, voce 4).
- 🟡 **IVA per cassa: i residui del cantiere** (DB, ereditati il 2026-10-03 dalla chiusura
  di `work-done/brief-db-esigibilita-iva-per-cassa-emittente.md` §12):
  **R-DB-1** — i riepiloghi IVA **memorizzati** dei preventivi non si ricalcolano
  quando cambia la regola che li produce (rimandato da Tid, SQL a mano nel §9.5;
  si riapre al prossimo cambio della regola: ricalcolo del pregresso o riepilogo
  derivato come ordini e DDT); **storicità del regime** dell'emittente (D-8,
  oggi senza validità nel tempo); **domande al consulente** (§9.4: RF16, catalogo
  RF, DDT senza cliente); **annotazioni future** (scissione, inversione
  contabile, RF19) come righe di `vendite.fn_annotazioni_fattura`.
- 🟡 **Le variabili di una versione di template non si validano alla pubblicazione**
  (DB + BE, ereditata il 2026-10-01 dalla chiusura di
  `work-done/brief-db-documenti-versione-contesto-template.md`, D-C3 §7 e §14): le
  decisioni 35-36 del 2026-04-29 (`work-done/sviluppo-documenti.md`) volevano
  `context_schema` «contratto leggero delle variabili attese», validato prima di
  pubblicare; il campo è ancora `'{}'` ovunque e nessuno lo legge. Il caso grave
  (pezzi mancanti in silenzio per un cambio di forma) lo chiude già
  `versione_contesto`; questo è il raffinamento per variabile. Sede naturale: la
  pubblicazione, la stessa della verifica degli asset citati
  (`work-done/brief-be-documenti-risorse-esterne-render-pdf.md` §5.3). Con la stessa
  chiusura, facoltativa al team DB: la colonna «Forma dei dati»
  (`versione_contesto`) nella lista configurabile `documenti.template_versioni`
  (88) — il campo viaggia già nelle righe (§12.1 del brief).
- ⏳ **«Annulla» e «Porta a Bozza» sulle distinte non manuali: spenti col motivo**
  (DB poi BE/FE, ereditata il 2026-09-30 dalla chiusura di
  `work-done/brief-db-righe-distinta-annullata-fuori-dalle-code.md`, R-3 + D-6 §11.3-§11.4,
  D-6 approvata da Tid). Oggi le due voci si propongono accese su una GENERATA
  e finiscono in 409 (`E_CONTABILE_ANNULLO_NON_MANUALE`,
  `E_CONTABILE_RIAPERTURA_NON_MANUALE`): le regole vivono solo nel corpo del
  guard `trgfn_vendite_contabili_guard_validazione` e non c'è una check da
  leggere. ⏳ Al team DB: `script.fn_check_contabile_transizione` + il guard che
  la chiama (P-9 … P-12). Poi il BE espone `transizioni_blocco` e il drawer spegne
  le voci col motivo.
- 🟡 **Colori PrimeVue ancora scritti nei componenti** (FE, registrato il
  2026-09-26 alla chiusura di `work-done/analisi-fe-regole-standard-violate-dal-codice.md`
  R-3): circa 60 `var(--p-*)` — `primary-700/500/50`, `yellow-*`, `blue-*`,
  `surface-200/400`, `border-radius-sm`… — che non hanno ancora un token
  `--app-*` perché il loro **significato** non è nominato. Si decide caso per
  caso cosa dicono (il nome è il significato, non la tinta), poi un guard che
  tenga lo zero. Regola: frontend-standards § «Stili CSS».
- 🟡 **`djangorestframework-simplejwt` senza un manutentore certo** (BE, sicurezza;
  registrato il 2026-10-03): siamo alla 5.5.1 (21-07-2025), ultima release;
  PyPI dichiara il supporto solo fino a Django 5.2 (noi siamo su 6.1). Il
  repo sta ancora su `jazzband/`, ma Jazzband ha annunciato la chiusura il
  14-03-2026, coi progetti da trasferire. Oggi va bene così: la crittografia è
  di PyJWT (mantenuto a parte) e la configurazione è prudente (access token da
  10 minuti, rotazione e blacklist del refresh). Le condizioni: i test su login,
  refresh, rotazione e blacklist vanno fatti girare a ogni salto di Django o DRF;
  poi va seguito dove finisce il repo, l'eventuale nuova release con Django 6 e
  gli advisory. **Da decidere prima della produzione**, se il manutentore non si
  è chiarito: sostituirlo con un nostro strato sopra PyJWT, cioè una dipendenza
  in meno e del codice nostro in più. È una scelta di Tid.
- ❓ **Le FK verso `django.auth_user` non nascono su un'installazione nuova**
  (DB, domanda di forma per Tid, ereditata il 2026-09-27 dalla chiusura di
  `work-done/brief-db-blocco-login-per-credenziale.md`, §11.5): con
  `onFail: MARK_RAN` il changeSet del «ponte django» si segna quando Liquibase
  gira prima di `manage.py migrate` (la tabella non esiste ancora) e non si
  riprova più. In CI nessuna FK del ponte esiste e
  `config/test-fk-auth-user-ponte-django-v1` salta. L'indice sull'email (D-B5 di
  quel brief) usa invece `onFail: CONTINUE`, che salta senza segnare e riprova al
  migrate successivo. Da decidere se portare a `CONTINUE` tutte le FK del ponte
  (le 18 storiche e `20260925-22`/`-23`): è un cambio della forma di casa, del
  team DB. ⚠️ Dal 2026-10-06 ha un effetto visibile: senza il ponte
  `script.fn_elimina_credenziale` rifiuta sempre (fail-closed,
  `E_CREDENZIALE_STORIA_NON_VERIFICABILE`, D-4 del brief elimina-credenziale),
  quindi su un'installazione nuova nessuna credenziale si elimina (brief archiviato in `work-done/`).
- 🟡 **Tetto d'area dei permessi — due decisioni residue di Tid**, non
  bloccanti (brief §9.6). Il cantiere è ✅ **chiuso il 2026-10-06** (DB
  `20261004-50 → -59`, BE/FE in `b8ac544fe`, collaudo a video verde):
  `work-done/brief-db-permessi-tetto-area.md`. Restano: ritiro del parametro
  morto `p_area_schema_db` da `fn_resolve_livello_oggetto` (raccomandato:
  tenerlo finché un cantiere non tocca quella firma) e raggruppamento
  «Trasversali» delle aree (servirebbe una colonna su `aree_funzionali`, brief
  al team DB)
- **Il `codice` delle sei famiglie di documento di seed si perde al migrate**
  (DB, ereditata il 2026-09-24 dalla chiusura di
  `work-done/brief-be-ricerca-full-liste-residue.md`, §13.5): dal 24-09 il
  `codice` dell'operatore si modifica dal CRUD, ma il mirror del CSV
  `vendite.famiglie_documento` lo riscrive a ogni migrate, come già la
  `descrizione`. Una modifica dal CRUD dura fino al migrate successivo. Da
  decidere col team DB se il mirror debba smettere di riscrivere le colonne che
  l'operatore può cambiare
- **Righe di listino: la gamba dei compositi bundle non è provata sul DB**
  (BE, stessa origine, §13.3 g): la ricerca libera di `vendite.listini_righe`
  è una condizione sola sulla CTE `unione`, ma
  `vendite/tests/db/test_ricerca_liste_db` costruisce solo la riga standalone
  (la fixture di una BoM con prezzo bundle è pesante). Su quella gamba la
  ricerca non ha un rosso che la presidi
- **La matrice di `stato_lotto` in due sedi che dissentono** (BE + DB,
  ereditata il 2026-09-23 dalla chiusura di
  `work-done/brief-db-annullamento-chiude-la-vita.md`, §9.3): il BE ammette
  `COMPLETATO → ERRORE`, `vendite.fn_set_fatturazione_lotto_stato` no — e
  quella funzione è di fatto **morta**, il runner scrive `stato_lotto` con un
  `UPDATE` diretto (è per questo che la guardia su `COMPLETATO` sta su un
  trigger della colonna). Da decidere quale sia la sede unica della matrice e
  ritirare l'altra. Cantiere a sé
- **La porta dell'esito ancora aperta** (DB, stessa origine, §9.9): un
  documento marcato `ERRORE` su un lotto **già** `COMPLETATO` produce la
  contraddizione «COMPLETATO con documenti in errore» senza toccare
  `stato_lotto`, quindi la guardia del trigger non la vede. Oggi la sorveglia
  il presidio a catalogo `dbops.vw_lotti_chiusi_con_errori_da_guardare` (deve
  restare vuoto); chiuderla a DB è una decisione a sé, di Tid
- **`zeroerp_log` in CI non ha `USAGE` su `dbops`: ogni test Django lavora con
  `tx_id = uuid_nil`** (DB+CI, ereditata il 2026-09-19 dalla chiusura di
  `work-done/brief-db-privilegio-app-job-run-log.md`, §5). La sede del
  privilegio esiste — `scripts/sql/provision_dblink_log_channel.sql` — ma la CI
  non la esegue (il vecchio changeSet `90_end/20260205-42`, `context:
  disabled`, è stato ritirato il 2026-10-15), il bootstrap di `ci-validate.yaml` crea il ruolo e il
  DSN senza concedergli niente su `dbops`, e `90_end/20260905-38` gli dà
  `maintenance`, non `dbops`. Su dev il grant c'è, a mano (§11.9, stessa
  forma). Effetto: `fn_get_or_create_session_tx_id` ripiega su `uuid_nil`
  (progettato apposta, non fa fallire nulla), quindi ogni asserzione sul
  `tx_id` reale in CI è verde per sottrazione e l'audit non correla. Fatto
  datato: 16 114 righe `permission denied for schema dbops` nel log Postgres
  della corsa verde `35451924195`. Due strade, **decisione a Tid**: un passo
  in `ci-validate.yaml` che lancia `provision_dblink_log_channel.sql` dopo il
  bootstrap, oppure un changeSet `90_end` gemello di `20260905-38` per
  `dbops`. Tocca il workflow, condiviso BE/DB. In coda allo stesso brief due
  code minori: `maintenance.test_pgagent_log` con `zeroerp_app=r` a mano su
  dev e senza lettore (§3.3, `REVOKE` + pin nel pgTAP, o un lettore da
  trovare) e `check_db_role_access.sql` che esclude `maintenance` per intero
  (§3.4, da verificare)
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
  non passerebbero. ✅ **DECISA da Tid il 2026-09-18 sera: strada A, il
  `CHECK` che rifiuta.** Da domanda a lavoro del team DB (`pagamenti`,
  un changeSet); nessun impatto BE/FE — il FE arrotonda già ai centesimi
- **Su quale documento si può registrare un incasso** (DB, **Q-4**, ereditata
  il 2026-09-18 dallo stesso brief, registro del 18-09): Tid vuole nel picker
  delle rate «solo le definitive, inviate a SDI — ma faremo poi». È un
  predicato di **dominio** e la sede è **una**, a DB, letta dalla lista **e**
  dal guard della riga: oggi `trgfn_vendite_contabili_righe_guard_rata` non
  chiede lo stato del documento (la rata di una bozza si abbina) e il filtro
  `solo_numerate` di `GET /pagamenti/rate/` è presentazione, non cancello. Si
  apre con la **persistenza dell'esito SDI** (voce sotto), che è ciò che
  «inviata» significa; nessun changeSet chiesto prima. ✅ **DECISA da Tid il
  2026-09-18 sera: si aspetta SDI** («a breve farò lo sviluppo SDI») — niente
  passo intermedio «solo numerati» a DB; il filtro BE sulle bozze resta
  presentazione, e il buco (la rata di una bozza è abbinabile per vie diverse
  dal picker) è **dichiarato**, non dimenticato: si chiude nel cantiere SDI
  con la regola intera «definitiva e inviata», in una sede, letta da lista e
  guard. ⚠️ **Aggiornamento 2026-09-23 (Tid), che NON cambia la decisione**:
  `solo_numerate` era scritto nel **frontend** (nei `filterDefaults` del picker)
  e da quel giorno il suo default vive nel **backend**
  (`saldi_service.list_rate` / `list_rate_paginata`, `= True`; l'assenza del
  parametro significa «applica la regola»). ⭐ Resta **presentazione, non
  cancello** — il guard della riga non chiede ancora lo stato del documento e il
  buco dichiarato è intatto: cambia solo che la regola non dipende più dal client
  che si ricorda di mandarla. Regola generale in
  [api.md §«Un PERIMETRO non è un filtro»](../docs/it/dev/api.md)
- **«Riavvia» un servizio dall'interfaccia** (DB + deploy + BE, **decisione
  D1 di Tid**; ereditata il 2026-09-18 dalla chiusura di
  `work-done/analisi-riavvio-processi-da-interfaccia.md`): «Esegui ora» è in
  esercizio dal 15-09 e non aveva bisogno di sapere su quale macchina gira —
  un timer è un comando che parla col DB. `systemctl restart` di un servizio
  (oggi il solo `listen_permessi`) **sì**: senza un *host* nel modello
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
- **Il Giornale eventi non è multi-emittente** (DB, **non urgente**, ereditata
  il 2026-09-19 dalla chiusura di `work-done/piano-be-fe-osservabilita-pallino-e-superfici.md`,
  §10 pezzo G): `vendite.giornale` è `multi_emittente = false` perché
  `script.vw_giornale_entita` non proietta l'emittente della riga — su «Tutti
  gli emittenti» la lista chiede di sceglierne uno (422), come `Fatture`. Per
  certificarla serve `emittente_soggetto_ruolo_id` nei **quattro rami** della
  vista (le tabelle lo hanno o lo raggiungono) + la colonna a catalogo. Il
  collaudo in-app dell'osservabilità (`work-done/collaudo-in-app-osservabilita-giornale-errori-pallino.md`,
  chiuso il 2026-10-06) lo dichiara al §3.15
- **Tendine del lookup generico senza `page_size`** (FE, residuo di
  `work-done/brief-db-registri-giornale-catalogo.md` §5.1): i siti che chiamano
  `lookupCodici(rel)` senza `page_size` ricevono la pagina di default (50) e la
  tendina si tronca in silenzio — da rivedere uno per uno, o da far passare da
  `useLookupCodici`
- **Registry runtime Python multi-dominio**: modello DB pronto, ma la mappa Python per tutti i domini non è completa
- **Builder XML SDI**: payload pronto, ma generazione file FatturaPA non ancora implementata. ⚠️ Sospeso per decisione (Tid, 2026-08-05); raccoglie anche `EsigibilitaIVA`, `DatiContratto` e le righe spezzate dal plafond (`vw_fattura_righe_esposte`, `PARTE_PLAFOND`) — dettagli in `work-done/fatturazione-roadmap.md` §9
- **Persistenza esito SDI**: `vendite.fatture_sdi` e `vendite.fatture_sdi_eventi` da popolare
- **La promessa di consegna dopo la conferma** (BE, decisione di Tid del 14-09): dal
  `20261008-90` il DB lascia aperta la sola `data_consegna_confermata` in `CONFERMATO`/`PARZIALMENTE_EVASO`;
  il verbo che la cambia è nella fase 1 (§5-bis) di `work-done/brief-db-testata-dopo-emissione.md`
  (prima la capability a DB, decisione di Tid del 2026-10-09). ✅ Fatto e collaudato il 2026-10-11
- **Pratica di approvazione prezzo su revisione superata** (BE,
  `work-done/refactor-prezzi.md` §4.7, residuo differito dal 2026-06-01): dal
  2026-09-14 (`20260914-14`) riguarda anche i **preventivi** — la rev N+1
  ricopia `stato_approvazione_prezzo` e la pratica 1:1, e una riga `PENDING`
  può trovarsi con la pratica già chiusa sulla rev N. ⚠️ **Dal 2026-09-24 il
  debito morde prima**: un prezzo non autorizzato blocca già l'**emissione**
  (building block `script.fn_check_prezzi_autorizzati`, cinque documenti di
  vendita), non più la sola accettazione — la revisione con quella riga non si
  emette, e resta solo l'annullamento. ✅ **Deciso da Tid lo stesso giorno**
  (§10 di `work-done/brief-db-preventivi-congelamento-pricing.md`,
  `20260924-33…-37`, applicati il 24-09 con test verdi; collaudo a video
  passato il 2026-10-24, `work-done/collaudo-in-app-capability-annidata-e-prezzi-autorizzati.md`):
  una revisione **non si crea** finché un
  prezzo è in attesa, quindi la riga in attesa ricopiata non può più nascere;
  approvato e rifiutato si ricopiano come prima. Resta del BE il ciclo di vita
  della pratica su una rev superata (il suo `meta` nomina la riga della rev N)
  ⚠️ **Dal 2026-10-08 anche sul preventivo annullato** (`work-done/brief-db-righe-e-componenti-debiti-residui.md`
  §4.4, §5): con le righe chiuse fuori bozza l'esito di una pratica su un preventivo annullato con una riga in
  attesa è respinto dal lock (`E_RIGA_DOC_NON_BOZZA`), e la pratica resta `APERTA` in coda. Debito dichiarato da
  Tid il 2026-10-09: si chiude con il resto del ciclo di vita della pratica
- **L'L3 dei componenti non esiste** (DB + BE, ereditata il 2026-10-09 dalla chiusura di
  `work-done/brief-db-righe-e-componenti-debiti-residui.md` §3): nessun verbo mette un componente in attesa
  né gli dà un esito, e non c'è il controllo L2. Dal `20261008-87`/`-88` uno spento in attesa si copia nella
  revisione senza marca: la nuova richiesta alla riaccensione è di quel ciclo. Un brief suo quando si costruisce
- **`user_update` nullable su nove tabelle senza audit** (DB, stessa origine, §2 e §4.6): `dbops.fk_index_policy`,
  `dbops.transaction_ids` e sette di `ui`. Il presidio `dbops/test-user-update-not-null-v1` le tiene a vista nel
  registro del debito; da decidere chi scrive la colonna

**Residui della roadmap fatturazione** (archiviata il 2026-09-12 in
`docs/it/dev/work-done/fatturazione-roadmap.md`, dove sta il *perché* di
ciascuna; qui solo la riga, perché un promemoria di stato lungo marcisce —
lezione della §Nota di metodo di quel file):

- **Esercizio fiscale come entità** (roadmap #3): zero occorrenze di `esercizio`/`anno_fiscale` in `migrations_v2` e nel backend; l'esercizio è l'anno solare derivato da `fatture.data`. Serve al primo **bilancio**, non al primo ciclo — la numerazione con reset annuale è coperta
- **Vista push** (roadmap #5): `vendite.commesse_push_log` non ha una UI di lista/ultimo run per sorgente; i contatori `created/updated/skipped/errors` esistono nel payload e nessuno li rende — l'operatore riceve un `push_log_id` in un toast e non ha modo di aprirlo
- **Alerting sui dati** (roadmap #6): la vitalità dei **processi** è coperta (sveglia, `dbops.processi`, digest) e dal 19-09 anche il **lotto fermo** (presidio a catalogo → digest e pallino) e la consultazione **a video** (`vendite/giornale`, «Giornale eventi»); manca ancora un **canale d'uscita** (email) per la query generica su `vendite.event_log` per severità/finestra. ⚠️ Non ha più una casa: `analisi-osservabilita-log.md` è **chiusa e archiviata** il 2026-09-19 (`work-done/`), e questa voce è uno dei residui dichiarati nel suo riquadro
- **Diagrammi di stato** (roadmap #8): zero `stateDiagram-v2` nel repo per lotto e task_run; la sostanza è già in prosa in `guide/fatturazione.md` — è trasposizione, non analisi
- **Preview di fatturazione del contratto** (roadmap #10): non esiste il punto in cui l'operatore veda *«su questa competenza fatturerà queste righe, per X»*; il dato lo produce `fn_list_contratti_da_pushare`. ⚠️ Non è `/contratti/<id>/righe-preview/`, che è la preview di **pricing**

### Note operative
- `config.stati_doc_fiscale.chiude_lotto = true` → unico meccanismo di chiusura lotto (nessun hardcode)
- Reset lotto MASSIVO: ammesso in DRAFT; la DEFINITIVA fa resume per fattura (non reset globale)
- L'orchestrazione della pipeline è in Django (`run_lotto_pipeline`), non in una procedura SQL

## File Django Chiave (vendite)

```
apps/vendite/
├── services/
│   ├── pipeline_runner.py          # LottoPipelineRunner — orchestrazione step pipeline
│   ├── pipeline_step_executor.py   # Esecuzione singolo step + dispatch task
│   └── fatture_righe_service.py    # Generazione righe fattura
├── db/
│   └── pipeline_repository.py      # Lookup registry DB, fn SQL
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

# Liquibase: wrapper scripts/liquibase5.sh (procedura in docs/it/liquibase-setup-workflow.md).
# ⛔ Le migrazioni le applica Tid: l'hook guardrail_no_db_migrate.py le blocca all'agente.
```

## Documentazione di Riferimento Rapido

- Convenzioni SQL: `docs/it/linee-guida-sql.md`
- Convenzioni trigger: `docs/it/linee-guida-trigger.md`
- Guida fatturazione: `docs/it/guide/fatturazione.md`
- WIP pipeline: `docs/it/dev/work-done/fatturazione-attivita-progetto.md`
- Domini engine (archiviato 2026-08-22, con la verifica dei concetti in testa): `docs/it/dev/work-done/pipeline-domini-engine.md`
- Template doc backend: `docs/it/backend/_templates/manual-standard.md`
