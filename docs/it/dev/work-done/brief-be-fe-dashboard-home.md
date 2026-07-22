# Brief BE/FE — Dashboard home: card KPI configurabili

> **Tipo**: brief BE/FE · **Target**: `dev/backend-tid` + FE · **Data**: 2026-07-21
> · **Owner**: Tid · **Priorità**: 🟠 ALTA
> **Stato**: ✅ **BE+FE REALIZZATI e FUNZIONANTI (2026-07-22)** — suite verde
> (3259 test BE, build FE ok), **non committati**. Prerequisiti DB tutti
> atterrati: DDL + `ui.fn_resolve_dashboard_config` + enum + codice errore
> ([brief-db-dashboard-home.md](brief-db-dashboard-home.md)), poi
> GRANT + seed catalogo
> ([brief-db-dashboard-home-grant-seed.md](./brief-db-dashboard-home-grant-seed.md),
> chiuso). Flusso completo verificato end-to-end contro il DB reale: config,
> contatori, upsert/reset preferenza, merge widget nuovi.
>
> **Validato da Tid in-app con test UI il 2026-07-22.** Fix emersi dalla
> validazione e applicati: larghezza del drawer di personalizzazione
> (passava `DRAWER_WIDTH` intero invece di `.STANDARD`), empty-state
> differenziato fra «nessuna card attiva» e «nessuna card disponibile per il
> profilo», rimozione della card «Benvenuto»
> ([brief dedicato](brief-db-dashboard-home-rimuovi-benvenuto.md), chiuso).
>
> Decisioni collaterali: `flattenMenu` hoistata in `core/navigation.js` (ok Tid).
> Rifattorizzazione delle 3 view cruscotto sul `KpiCard`: **decisa NO** — §6.1.
>
> **Unico residuo**: il commit (working tree misto — servono `git add` espliciti).
>
> **Contratto reale verificato** (estratto da `pg_catalog`, non dal brief):
>
> - `ui.fn_resolve_dashboard_config(varchar, integer, bigint) → jsonb`
> - ritorno: `{widget[], dimensione_max, widget_nuovi, preset_aggiornato}`;
>   ogni widget: `codice, ordine, visibile, tipo_widget, etichetta,
>   etichetta_i18n_key, deep_link, contatore_key, soglia`
> - preferenza (`configurazione`):
>   `{"widget": [{codice, ordine, visibile}], "dimensione_max": N}`
>
> **Origine**: revisione home page. Sostituisce le 4 card statiche `Dash 1..4` di
> `HomeView.vue` con card KPI vive, configurabili per utente e persistite a DB.

## 1. Scopo e confine di v1

Sostituire le 4 card placeholder della home con una **griglia di card KPI**:
ogni card mostra un **conteggio**, ha un **semaforo** (neutro in v1) e
**deep-linka** al cruscotto/vista relativo in stato preimpostato. Selezione e
ordine delle card sono scelti dall'utente e persistiti a DB, con un default per
ruolo. Nessuna azione di business in home — vale la grammatica launcher già
validata in [brief-fe-home-operatore-launcher.md](./brief-fe-home-operatore-launcher.md) §2.2.

**Decisioni v1 già prese** (con Tid, 2026-07-21):

- **Valore = conteggio**, non importo. Numero di documenti, non €. Il valore
  monetario è evoluzione successiva (richiederebbe formattazione valuta +
  sensibilità importi + soglie su importo).
- **Soglie semaforo neutre**: la card mostra il numero senza colore d'allarme.
  Il campo `soglia jsonb` esiste a DB ma resta vuoto in v1; le soglie si tarano
  dopo, con dati reali. Il `KpiCard` deve però **già saper valutare** una soglia
  quando arriverà (sviluppo concentrico, non YAGNI).
- **Catalogo iniziale = 3 widget** che deep-linkano ai cruscotti esistenti
  (§5), più **1 widget di benvenuto non-gated** (vincolo "mai vuota", §5).
- **Invariante permessi ↔ deep-link** (confermato): l'`area_id`/`azione_id` che
  il widget dichiara al DB **deve coincidere** con la guardia della route di
  destinazione. È un vincolo di authoring del seed, non codice: un widget non
  può essere visibile e poi portare a un vicolo cieco.

### Fuori perimetro v1

- Valore monetario sulle card; soglie tarate; widget non-KPI (grafici, liste
  embedded); dashboard diverse da `home` (backlog/fatturazione restano viste
  analitiche fisse, non griglie-card — vedi nota §3a del brief DB).
- Migrazione dei preferiti-route (localStorage → DB): refactor a sé, non blocca.

## 2. Dipendenza dal DB (contratto atteso)

Dal brief DB §3.ter/§5, il BE consuma:

- `ui.fn_resolve_dashboard_config(codice, auth_user_id, emittente_fiscale_id)`
  → JSONB `{ widget[], dimensione_max, widget_nuovi, preset_aggiornato }`, già
  filtrato per permessi (il FE non filtra). Ogni elemento `widget[]` porta:
  `codice`, `etichetta_i18n_key`, `tipo_widget`, `deep_link` (jsonb opaco),
  `contatore_key`, `soglia` (jsonb opaco), `ordine`, `visibile`.
- Preferenza utente in `ui.dashboard_preferenza_utente` (JSONB che referenzia i
  `codice` widget) — è ciò che il FE scrive al salva.

✅ **Confermato il 2026-07-22** estraendo la firma e il corpo della funzione da
`pg_catalog` (non dal brief): l'atteso qui sopra combacia con quanto il DB ha
prodotto. Contratto reale riportato in testata.

Un'avvertenza di metodo emersa qui e utile oltre questo caso: `information_schema`
**è filtrata per privilegi**, quindi finché mancavano i GRANT le tabelle
risultavano *inesistenti* invece che *inaccessibili*. Per verificare che un apply
sia passato va interrogato `pg_catalog`, che non filtra.

## 3. Piano Backend

Ricalca la catena delle liste (`lista_preferenza_service.py` → API `ui/liste`),
più un pezzo net-new (contatori).

**3.1 — Config endpoint** (mirror di `useListaConfig`/`ui/liste`)
`/api/v1/ui/dashboard/{codice}/config/`
- `GET` → chiama `fn_resolve_dashboard_config` per l'utente corrente, ritorna il
  JSONB in envelope standard.
- `PUT` → salva la preferenza utente (upsert su `auth_user_id + dashboard_id`),
  con `Idempotency-Key` come le liste.
- `DELETE` (o `POST reset`) → azzera la preferenza, torna al default di ruolo.
Service `dashboard_preferenza_service.py` per analogia a
`lista_preferenza_service.py` — **ma** attenzione alle divergenze note (brief DB
§5): widget globale via JOIN `dashboard_widget`, niente tabella permessi.

**3.2 — Endpoint contatori** (net-new, è il pezzo di sostanza)
Un **solo endpoint batch**: riceve le `contatore_key` (della config risolta) e
ritorna i numeri in un colpo. Requisiti non negoziabili:
- **Envelope per-key**: `{ "vendite.backlog.documenti_fermi": {"valore": 8, "ok": true}, ... }`.
  Se un contatore fallisce/timeouta, quella key torna `{"ok": false}` e la card
  degrada — **non** salta l'intera home. Un contatore rotto non deve mai
  oscurare gli altri.
- **Riuso degli aggregati esistenti**: i 3 KPI v1 deep-linkano a cruscotti che
  **hanno già un numero di testata** (endpoint riepilogo, `useDashRiepilogo`).
  Il contatore riusa quell'aggregato, non una query nuova — così card e cruscotto
  non divergono mai. Registry `contatore_key → callable` nel BE.
- **Raccordo cantiere code (2026-07-21, unificazione Tid)**: un eventuale
  widget «Processi in coda» dovrà registrare come callable
  `apps.core.services.coda_lavori.gestione_service.conteggi_code` (già scoped
  per operatore + liveness worker — brief
  [gestione-code-lavori-stampa](./brief-be-fe-gestione-code-lavori-stampa.md),
  BE+FE completi) e deep-linkare a `/strumenti/code-lavoro` (dominio FE
  «Strumenti» già esistente). Mai una seconda query sulle code.
- **No N chiamate**: mai un endpoint-per-widget al load della home.

**3.3 — Seed catalogo** (§5). ⚠️ **Non è lavoro BE**, contrariamente a quanto
questa riga diceva in prima stesura: nel progetto i seed si fanno via migration
Liquibase in `80_data/` (precedente: `20260507-06-seed-ui-lista-definizione`),
quindi è passato al team DB ed è stato applicato lì
(`80_data/changelog/20260722-02..05`).

## 4. Piano Frontend

**4.1 — `useDashboardConfig`** (mirror di `useListaConfig`): load config risolta,
save preferenza (PUT + Idempotency-Key), reset. Basso rischio, copia strutturata.

**4.2 — Grammatica deep-link** (net-new — il vero peso FE) — `useWidgetNavigation.js`
Oggi `navigation.js` persiste **solo una path stringa**: i widget "in stato
preimpostato" sono territorio nuovo. Formato posseduto dal FE (il DB lo conserva
opaco, brief DB §3f):

```json
{ "path": "/vendite/dashboard-competenza", "query": { "classe": "FERMO" } }
```

- **`path` è canonico, NON `route.name`** — divergenza voluta dalla prima
  stesura di questo brief, che proponeva `{"route": {"name", "params", "query"}}`.
  Motivo: `path` è ciò che tutta la navigazione dell'app già parla — le voci di
  menu si identificano con `to`, i preferiti persistono path, e il resolver deve
  comunque trovare la voce di menu per aprire tab e sidebar coerenti. Risolvere
  per nome avrebbe imposto un doppio mapping `nome → path → voce` senza alcun
  guadagno. **Il seed a DB usa questa forma.**
- v1: i 3 widget usano solo `path` (i cruscotti non prendono stato).
- `query` è previsto fin da ora anche se inutilizzato: serve ai widget futuri che
  deep-linkano a **liste in stato preimpostato** (concentrico, non YAGNI). Entra
  nel `fullPath`, che è l'identità del tab — due stati preimpostati della stessa
  lista non si sovrascrivono.
- Resolver `navigateToWidget(deep_link)` — stessa sequenza di
  `navigateToFavorite` (apri tab → `nav.setDomain` → `router.push`), con in più
  la query. Se la path non corrisponde a nessuna voce di menu, o la voce non è
  permessa, ritorna `false` e la card resta **non cliccabile**: meglio di un tab
  orfano senza dominio né etichetta.

**4.3 — Grammatica soglia** (prevista, vuota in v1)
Formato posseduto dal FE, es. `{ "warn": 10, "danger": 30, "dir": "asc" }`. Il
`KpiCard` la valuta per scegliere il colore. In v1 `soglia = {}` → semaforo
neutro. Il codice di valutazione esiste già dal giorno uno, non si allarga dopo.

**4.4 — `KpiCard`** — `core/components/dash/KpiCard.vue` (fatto)
Numero + etichetta i18n + semaforo (da soglia) + click → `navigateToWidget`.
Perimetro volutamente stretto: **una** metrica, un semaforo, una navigazione.
Le tre view cruscotto esistenti **non** vengono rifattorizzate su questo
componente — motivazione in §6.1.

**4.5 — Modale di personalizzazione** — mirror della modale colonne liste:
lista dei widget del pool (già filtrata da permessi lato DB), toggle
visibile/nascosto, riordino drag&drop, cap `dimensione_max`. Riusare i pattern
della personalizzazione liste.

**4.6 — `HomeView.vue`** — sostituire `dashCards` (righe 27-32) e la
`.dashboard-grid` statica con la griglia risolta da `useDashboardConfig`, card =
`KpiCard`. Il pannello "I tuoi preferiti" (route bookmark) **resta invariato**:
è un meccanismo distinto e ortogonale, non lo tocchiamo.

## 5. Seed catalogo v1 (concreto)

**4 widget** in `ui.widget` (globali) + composizione su dashboard `home`:

| `codice` | etichetta | `contatore_key` | `deep_link.route.name` | area/azione |
| --- | --- | --- | --- | --- |
| `home.benvenuto` | Benvenuto | *(nessuno)* | *(help/guida o nessuno)* | **NULL/NULL** (non-gated) |
| `home.situazione_aperta` | Situazione aperta | `vendite.situazione_aperta.totale_aperto` | `situazione-aperta` | area vendite |
| `home.competenza` | Da fatturare | `vendite.competenza.da_fatturare` | `dashboard-competenza` | area vendite |
| `home.backlog` | Documenti fermi | `vendite.backlog.documenti_fermi` | `dashboard-backlog` | area vendite |

- **Widget benvenuto non-gated** = garanzia "mai vuota" (brief DB §3.bis): senza
  di lui, un utente senza permessi vendite avrebbe la home vuota. Non ha
  contatore; è una card statica di benvenuto/orientamento.
- **Preset di sistema** = solo `home.benvenuto` (default universale minimo).
- **Preset di ruolo vendite** = i 4 widget (benvenuto + 3 KPI). I nomi `route` e
  le `contatore_key` sono da confermare contro il codice al momento del seed.
- `dimensione_max` seed = 8 (dal brief DB §3c): margine, non vincolo a 4.

## 6. Riuso / regola del 2

- `useDashboardConfig`, la modale personalizzazione, il resolver deep-link:
  ricalcati sui gemelli delle liste, non duplicati.
- `flattenMenu`: era duplicata fra `useNavigationFavorites` e
  `useWidgetNavigation` (seconda occorrenza) → **hoistata** in
  `core/navigation.js` ed esportata, entrambi i composable la importano
  (fatto 2026-07-22, ok Tid).
- Modello di riferimento vivo: `useListaConfig`, `lista_preferenza_service.py`,
  modale colonne liste, `useNavigationFavorites.navigateToFavorite`,
  `DashEmptyState` (empty-state onesto), `usePagedDashFetch`.

### 6.1 Le 3 view cruscotto NON vengono rifattorizzate sul `KpiCard` — perché

**Decisione presa il 2026-07-22 (Tid). Correzione di una raccomandazione
precedente di questo stesso brief**, che dava l'estrazione per "dovuta" in base
alla regola del 2. Guardato il codice reale delle tre view, non lo è.

#### Non sono lo stesso componente

| View | Contenuto della card | Semantica del click |
| --- | --- | --- |
| `SituazioneApertaView` | titolo + tooltip hint + **`<DonutFasi>`** — nessun numero in chiaro, le misure stanno dentro il grafico | toggle filtro **locale** sulla lista sotto |
| `DashboardBacklogView` | `<Tag severity>` + n documenti + sub + valore € + unità ferme + anzianità con icona — **5 slot di misura** | toggle filtro **locale** |
| `DashboardCompetenzaView` | titolo + n attività + sub + valore € + **pulsanti-verbo di business** (APPROVA / FATTURA / RENDI DEFINITIVE) con `@click.stop` | toggle filtro **locale** |
| `KpiCard` (home) | etichetta + **una** metrica + semaforo | **naviga via** verso un'altra vista |

Due divergenze sono strutturali, non cosmetiche:

1. **Il click significa cose opposte.** Nelle tre view seleziona/deseleziona un
   filtro e accende `is-selected` restando nella pagina; nella home porta
   altrove. Un componente che fa entrambe è un componente con una modalità.
2. **Il contenuto non è una metrica.** Una card ospita un grafico, un'altra
   cinque misure eterogenee, una terza dei pulsanti che eseguono azioni fiscali.
   Il `KpiCard` è progettato attorno a *un numero*.

#### Ciò che condividono è già fattorizzato

Il linguaggio visivo comune non è nei componenti, è nel **CSS globale**:
`.app-dash-cards`, `.app-dash-card`, `.app-dash-card-title`, `.app-dash-stat-n`,
`.app-dash-stat-euro`, `.app-dash-stat-sub`, `.app-dash-ritardo` vivono in
`assets/main.css` e sono già usate da tutte e quattro (`KpiCard` incluso). Quella
che il brief aveva letto come duplicazione da estrarre era in larga parte CSS —
e il CSS era già centralizzato. La regola del 2 era già rispettata: sul CSS.

#### Cosa costerebbe unificare

Un componente che copra i quattro casi avrebbe una decina di prop opzionali e
tre slot, pilotato da flag, e ospiterebbe pulsanti di business dentro una card
KPI. Sarebbe **più** codice, non meno, e legherebbe l'evoluzione di tre cruscotti
indipendenti a un componente condiviso: modificare la card del backlog
richiederebbe di non rompere competenza e situazione aperta. È esattamente il
caveat di astrazione prematura che la regola del 2 porta con sé.

#### L'unico residuo reale, valutato e scartato

È davvero identico nelle tre view il **wrapper cliccabile-selezionabile**:
`role="button" tabindex="0" @click @keydown.enter` + `:class="{'is-selected': …}"`.
Sono ~8 righe per view, estraibili in un `DashCardSelezionabile` con slot di
default. Valutato e **non fatto**: il guadagno (24 righe) non ripaga
l'indirezione su tre viste stabili e già collaudate. Resta il candidato naturale
**se** nascerà una quarta vista con lo stesso pattern — a quel punto la regola
del 2 varrebbe sul comportamento, non sul CSS.

**Conseguenza pratica**: `KpiCard` resta un componente della sola home, con
perimetro stretto. Le tre view cruscotto restano invariate.

## 7. Avanzamento

| # | Step | Stato |
| --- | --- | --- |
| 0 | Apply DB + firma/JSONB confermati contro `pg_catalog` (§2) | ✅ 2026-07-22 |
| 1 | BE: config endpoint + service (mirror liste) | ✅ |
| 2 | BE: endpoint contatori batch (envelope per-key, riuso riepiloghi) | ✅ |
| 3 | BE: seed catalogo 4 widget + preset sistema/ruolo (§5) | ✅ (team DB, via Liquibase `80_data`) |
| 4 | FE: `useDashboardConfig` + grammatica deep-link + resolver | ✅ |
| 5 | FE: `KpiCard` (solo home — 3 view invariate, §6.1) | ✅ |
| 6 | FE: modale personalizzazione + HomeView griglia risolta | ✅ |
| 7 | Verifica E2E: cascata, permessi, contatori, personalizza+salva+reset, merge nuovi | ✅ |
| 8 | Validazione in-app + test UI di Tid | ✅ 2026-07-22 |
| 9 | Fix post-validazione: larghezza drawer personalizzazione, empty-state differenziato, rimozione card «Benvenuto» | ✅ 2026-07-22 |
| 10 | Commit (tree misto: `git add` espliciti) | ☐ |

Nota su §3: il seed è risultato lavoro DB e non BE — nel progetto i seed si
fanno via migration Liquibase in `80_data/`, non da management command. Il brief
inizialmente lo attribuiva al BE: corretto in corsa.

## 8. Riferimenti

- Prerequisito DB (chiuso): [brief-db-dashboard-home.md](brief-db-dashboard-home.md)
- GRANT + seed (chiuso): [brief-db-dashboard-home-grant-seed.md](./brief-db-dashboard-home-grant-seed.md)
- Visione: `docs/it/dev/work-in-progress/frontend/layout-menu-navigazione.md` §9
- Grammatica launcher: `docs/it/dev/work-done/brief-fe-home-operatore-launcher.md` §2.2
- Modello liste da ricalcare: `frontend/src/core/composables/useListaConfig.js`,
  `backend/apps/ui/services/lista_preferenza_service.py`
- Cruscotti KPI v1: `frontend/src/vendite/views/{SituazioneAperta,DashboardCompetenza,DashboardBacklog}View.vue`
  + `docs/it/backend/vendite/manual/api_dashboard_{aperto,competenza,backlog}.md`
- Home attuale: `frontend/src/core/views/HomeView.vue`,
  `frontend/src/stores/navigation.js`,
  `frontend/src/core/composables/useNavigationFavorites.js`
