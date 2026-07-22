# Brief DB — Dashboard home: GRANT mancanti + seed catalogo widget

> **Tipo**: mini-brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-22
> · **Owner**: Tid · **Priorità**: 🔴 era BLOCCANTE
> **Stato**: ✅ **CHIUSO (2026-07-22)** — GRANT e seed applicati dal team DB,
> verificati end-to-end lato BE. Vedi §5 per esito e risposta alla domanda
> aperta del team DB.
> **Origine**: chiusura BE/FE di
> [brief-be-fe-dashboard-home.md](brief-be-fe-dashboard-home.md). L'apply del
> [brief DB](brief-db-dashboard-home.md) ha portato DDL, funzione,
> enum e codice errore, ma mancavano i privilegi e il seed.

## 1. GRANT mancanti (blocco duro)

Le 6 tabelle nuove hanno **zero privilegi** per il ruolo applicativo
`zeroerp_app`, mentre tutte le `lista_*` gemelle hanno
`SELECT/INSERT/UPDATE/DELETE`. Verificato sul DB `zeroerp` di sviluppo:

| Tabella | Privilegi `zeroerp_app` |
| --- | --- |
| `ui.widget` | **(nessuno)** |
| `ui.dashboard_definizione` | **(nessuno)** |
| `ui.dashboard_widget` | **(nessuno)** |
| `ui.dashboard_preset` | **(nessuno)** |
| `ui.dashboard_preset_widget` | **(nessuno)** |
| `ui.dashboard_preferenza_utente` | **(nessuno)** |
| `ui.lista_*` (tutte, per confronto) | `DELETE,INSERT,SELECT,UPDATE` |

L'`EXECUTE` su `ui.fn_resolve_dashboard_config` **c'è**, ma la funzione è
invoker: legge tabelle che il chiamante non può toccare. Errore a runtime:

```text
ProgrammingError: permesso negato per la tabella dashboard_definizione
CONTEXT: istruzione SQL "SELECT id FROM ui.dashboard_definizione WHERE codice = ..."
```

**Cosa serve**: i privilegi allineati alle `lista_*` (lettura per il catalogo e
i preset, scrittura per la preferenza utente), più `USAGE` sulle sequence
identity delle tabelle con `id`. Il pattern del progetto è una migration
dedicata in `90_end/` (`*-grant-*-app-mctit.yaml`).

⚠️ Nota di metodo: il difetto è sfuggito anche a una verifica iniziale perché
`information_schema.tables` **è filtrata per privilegi** — a `zeroerp_app` le
tabelle risultavano *inesistenti*, non *inaccessibili*. Solo `pg_catalog` (non
filtrato) ha rivelato che erano lì, di proprietà di `titodb`. Se in futuro un
apply "non risulta", vale la pena controllare i GRANT prima di sospettare che
il DDL non sia passato.

## 2. Seed catalogo widget (senza, la home resta vuota)

Nel progetto i seed si fanno via migration Liquibase in `80_data/` (precedente
diretto: `20260507-06-seed-ui-lista-definizione-mctit.yaml`), quindi è lavoro
DB, non BE.

Serve seedare, per la dashboard di codice **`home`**:

| `codice` widget | etichetta | `etichetta_i18n_key` | `contatore_key` | `deep_link` | gate |
| --- | --- | --- | --- | --- | --- |
| `home.benvenuto` | Benvenuto | `home.widget_benvenuto` | *(NULL)* | *(NULL)* | **area/azione NULL** |
| `home.situazione_aperta` | Situazione aperta | `home.widget_situazione_aperta` | `vendite.situazione_aperta.totale_aperto` | `{"path": "/vendite/situazione-aperta"}` | area vendite |
| `home.competenza` | Da fatturare | `home.widget_competenza` | `vendite.competenza.da_fatturare` | `{"path": "/vendite/dashboard-competenza"}` | area vendite |
| `home.backlog` | Documenti fermi | `home.widget_backlog` | `vendite.backlog.documenti_fermi` | `{"path": "/vendite/dashboard-backlog"}` | area vendite |

Più: `ui.dashboard_definizione` (codice `home`), la composizione
`ui.dashboard_widget` per i 4, e i preset — **sistema** col solo
`home.benvenuto`, **ruolo vendite** con tutti e 4.

`soglia` resta **NULL/vuota** su tutti: le soglie semaforo sono neutre in v1 per
decisione presa (si tarano dopo, sui dati reali). Il FE valuta già la soglia
quando arriverà: basterà popolare il campo, senza toccare il frontend.

### Vincoli sul seed (non cosmetici)

1. **`home.benvenuto` deve restare non-gated** (`area_id`/`azione_id` entrambi
   NULL). È la garanzia "mai una home vuota" del brief DB §3.bis: il filtro
   permessi è ortogonale alla cascata e senza almeno un widget non-gated può
   svuotare la home a un utente senza area vendite.
2. **`deep_link.path` deve coincidere con la voce di menu** di destinazione. Il
   FE risolve il deep-link cercando la voce con quel `to` in `core/navigation.js`
   (righe 174-176 per i tre cruscotti) per aprire tab e sidebar coerenti. Una
   path che non corrisponde a nessuna voce dà una card **non cliccabile** —
   volutamente, invece di un tab orfano.
3. **L'area dichiarata dal widget deve essere quella che guarda la rotta di
   destinazione** (invariante confermato). Un widget visibile che porta a una
   rotta bloccata sarebbe un vicolo cieco.
4. **`contatore_key` deve combaciare** con le chiavi del registry BE
   (`apps/ui/services/dashboard_contatori_service.py::CONTATORI_REGISTRY`): le
   tre in tabella sono già implementate e testate. Una key seedata senza
   callable degrada la card (`ok:false`) e logga un warning — non rompe la home,
   ma la card resta senza numero.

## 3. Verifica attesa

Dopo GRANT + seed, questi devono passare (sono i casi §4 del brief DB, ora
esercitabili davvero):

1. `SELECT ui.fn_resolve_dashboard_config('home', <user_id>, NULL)` non solleva
   e ritorna `{widget[], dimensione_max, widget_nuovi, preset_aggiornato}`.
2. Utente **senza preferenza e senza preset di ruolo** → riceve comunque widget.
3. Utente **senza area vendite** → riceve **solo** `home.benvenuto` (mai vuoto).
4. `GET /api/v1/ui/dashboard/home/config/` e
   `GET /api/v1/ui/dashboard/home/contatori/` rispondono 200.
5. `PUT .../preferenza/` salva, e un reload riflette selezione e ordine.

## 4. Stato del lavoro BE/FE (già fatto, in attesa)

Tutto scritto e con suite verde (**3259 test BE**, build FE ok). In attesa solo
di questi due pezzi:

- BE: repository, service lettura/scrittura, registry contatori + endpoint
  batch, 4 rotte sotto `/api/v1/ui/dashboard/<codice>/`, codice errore
  `E_UI_DASHBOARD_NON_TROVATA` registrato nelle policy.
- FE: `useDashboardConfig`, `useWidgetNavigation` (grammatica deep-link),
  `KpiCard`, `DashboardWidgetModal`, `HomeView` con griglia risolta, i18n it/en.

I tre contatori sono stati eseguiti contro il DB reale e non sollevano.

## 5. Esito (2026-07-22) — CHIUSO

### 5.1 Cosa ha applicato il team DB

- **GRANT**: `90_end/20260722-06-grant-ui-dashboard-app-mctit.yaml` — blocco `DO`
  idempotente, difensivo, valido fuori `ci_apply` (pattern `20260615-12`).
- **Seed**: `80_data/changelog/20260722-02..05` — dashboard `home`, i 4 widget,
  la composizione e i preset sistema/ruolo.

### 5.2 Perimetro concesso — più stretto della richiesta, ed è giusto così

Il brief chiedeva i privilegi "allineati alle `lista_*`". Il team DB ha invece
applicato il criterio espresso a parole — *lettura per catalogo e preset,
scrittura per la preferenza utente* — e **ha fatto bene**:

| Tabelle | Privilegi `zeroerp_app` |
| --- | --- |
| `ui.widget`, `dashboard_definizione`, `dashboard_widget`, `dashboard_preset`, `dashboard_preset_widget` | `SELECT` |
| `ui.dashboard_preferenza_utente` | `SELECT, INSERT, UPDATE, DELETE` + `USAGE` sequence |

Il full-DML delle `lista_*` è verosimilmente un over-grant storico: catalogo e
preset si popolano via seed Liquibase, non dall'applicazione, quindi il ruolo
applicativo non ha ragione di scriverli. E le due direzioni non costano uguale —
allargare dopo è una riga, restringere dopo richiede di sapere chi nel frattempo
si è appoggiato al privilegio.

### 5.3 Risposta alla domanda aperta del team DB

> *Esiste in `apps/ui/` un CRUD amministrativo che scrive il catalogo widget o i
> preset dall'applicazione?*

**NO — il perimetro attuale è corretto, nessun changeset additivo necessario.**

Verificato sistematicamente su tutto il backend, non a memoria:

- Nessuna `INSERT`/`UPDATE`/`DELETE` su `ui.widget`, `dashboard_definizione`,
  `dashboard_widget`, `dashboard_preset`, `dashboard_preset_widget`.
- Gli unici verbi di scrittura del BE colpiscono `ui.dashboard_preferenza_utente`
  (upsert preferenza, tombstone banner, delete/reset).
- `apps/ui/api/views_admin.py` espone CRUD amministrativo **solo per le liste**
  (definizioni, colonne, preset, permessi): non esiste il gemello dashboard, ed
  è la ragione per cui le `lista_*` hanno full-DML e le `dashboard_*` no.

Se un domani servisse una schermata admin per comporre dashboard e widget, sarà
quel lavoro a richiedere il changeset additivo — non questo.

### 5.4 Verifica end-to-end eseguita

Tutti i casi §3 passano contro il DB reale:

| # | Caso | Esito |
| --- | --- | --- |
| 1 | `fn_resolve_dashboard_config('home', <user>, NULL)` | ✅ ritorna il contratto completo |
| 2 | Cascata senza preferenza | ✅ 4 widget dal preset, ordini 10/20/30/40, `dimensione_max=8` |
| 3 | `deep_link` dei 3 cruscotti | ✅ combaciano con `core/navigation.js:174-176` |
| 4 | Contatori batch | ✅ le 3 key risolte, `ok:true` |
| 5 | UPSERT preferenza | ✅ selezione e ordine persistiti |
| 6 | **Merge widget nuovi** | ✅ widget omesso dalla preferenza ri-aggiunto nascosto (`ordine=10020`, `widget_nuovi=1`) |
| 7 | DELETE preferenza | ✅ ritorno al preset di ruolo |

Il record di preferenza creato in verifica è stato rimosso dal DELETE finale.
Backend ricaricato (`systemctl reload zeroerp-gunicorn`) per rendere vive le
rotte nuove.

## 6. Riferimenti

- Brief DB d'origine: [brief-db-dashboard-home.md](brief-db-dashboard-home.md)
- Brief BE/FE: [brief-be-fe-dashboard-home.md](brief-be-fe-dashboard-home.md)
- DDL applicato: `db/changelog/migrations_v2/00_schema/ui/20260721-12..18-*`
- Precedente GRANT: `db/changelog/migrations_v2/90_end/*-grant-*-app-mctit.yaml`
- Precedente seed: `db/changelog/migrations_v2/80_data/changelog/20260507-06-seed-ui-lista-definizione-mctit.yaml`
- Registry contatori: `backend/apps/ui/services/dashboard_contatori_service.py`
- Voci di menu target: `frontend/src/core/navigation.js:174-176`
