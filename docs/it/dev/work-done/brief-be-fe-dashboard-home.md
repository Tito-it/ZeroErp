# Brief BE/FE — Dashboard home: card KPI configurabili

> **Tipo**: brief BE/FE · **Target**: `dev/backend-tid` + FE · **Data**: 2026-07-21
> · **Owner**: Tid · **Priorità**: 🟠 ALTA
> **Stato**: ☐ DA REALIZZARE — **bloccato** sull'apply del prerequisito DB
> [brief-db-dashboard-home.md](brief-db-dashboard-home.md) (tabelle `ui.widget`,
> `ui.dashboard_*`, `ui.fn_resolve_dashboard_config`). Non iniziare prima che il
> DB abbia fatto apply e comunicato firma funzione + forma JSONB (§5 di quel brief).
> **Origine**: revisione home page. Sostituisce le 4 card statiche `Dash 1..4` di
> `HomeView.vue` con card KPI vive, configurabili per utente e persistite a DB.

## 1. Scopo e confine di v1

Sostituire le 4 card placeholder della home con una **griglia di card KPI**:
ogni card mostra un **conteggio**, ha un **semaforo** (neutro in v1) e
**deep-linka** al cruscotto/vista relativo in stato preimpostato. Selezione e
ordine delle card sono scelti dall'utente e persistiti a DB, con un default per
ruolo. Nessuna azione di business in home — vale la grammatica launcher già
validata in [brief-fe-home-operatore-launcher.md](../work-done/brief-fe-home-operatore-launcher.md) §2.2.

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

⚠️ Firma esatta e nomi dei campi **vanno confermati dal DB dopo l'apply**: qui
sono l'atteso derivato dal mirror liste, non un dato certo. Prima riga di lavoro
BE = allineare a ciò che il DB ha effettivamente prodotto.

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
  [gestione-code-lavori-stampa](../work-done/brief-be-fe-gestione-code-lavori-stampa.md),
  BE+FE completi) e deep-linkare a `/strumenti/code-lavoro` (dominio FE
  «Strumenti» già esistente). Mai una seconda query sulle code.
- **No N chiamate**: mai un endpoint-per-widget al load della home.

**3.3 — Seed catalogo** (§5). Migrazione dati BE/seed, non DDL.

## 4. Piano Frontend

**4.1 — `useDashboardConfig`** (mirror di `useListaConfig`): load config risolta,
save preferenza (PUT + Idempotency-Key), reset. Basso rischio, copia strutturata.

**4.2 — Grammatica deep-link** (net-new — il vero peso FE)
Oggi `navigation.js` persiste **solo una path stringa**: i widget "in stato
preimpostato" sono territorio nuovo. Definiamo un formato posseduto dal FE:
```json
{ "route": { "name": "dashboard-competenza", "params": {}, "query": {} } }
```
- v1: i 3 widget usano solo `name` (i cruscotti non prendono params).
- Progettato per espansione: `params`/`query` servono ai futuri widget che
  deep-linkano a **liste in stato preimpostato** (concentrico).
- Resolver `navigateToWidget(deep_link)` — evoluzione di `navigateToFavorite`
  (`useNavigationFavorites.js`), che oggi apre tab+sidebar coerenti ma senza
  stato. Riusare quella logica, aggiungere il passaggio di params/query.

**4.3 — Grammatica soglia** (prevista, vuota in v1)
Formato posseduto dal FE, es. `{ "warn": 10, "danger": 30, "dir": "asc" }`. Il
`KpiCard` la valuta per scegliere il colore. In v1 `soglia = {}` → semaforo
neutro. Il codice di valutazione esiste già dal giorno uno, non si allarga dopo.

**4.4 — `KpiCard`** — estrarre in `core/components/dash/KpiCard.vue`
Numero + etichetta i18n + semaforo (da soglia) + click → `navigateToWidget`.
⚠️ **Regola del 2**: le card KPI oggi sono CSS inline in `DashboardCompetenzaView`,
`DashboardBacklogView`, `SituazioneApertaView` — è oltre la seconda occorrenza,
l'estrazione è dovuta. Dichiarare l'estrazione a chat e attendere ok prima di
rifattorizzare le tre view esistenti (o farlo in slice separata dopo la home).

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

- `KpiCard`, `useDashboardConfig`, la modale personalizzazione, il resolver
  deep-link: tutti da estrarre/ricalcare, non duplicare. Prima di estrarre il
  `KpiCard` toccando le 3 view esistenti → dichiarare a chat (regola del 2).
- Modello di riferimento vivo: `useListaConfig`, `lista_preferenza_service.py`,
  modale colonne liste, `useNavigationFavorites.navigateToFavorite`,
  `DashEmptyState` (empty-state onesto), `usePagedDashFetch`.

## 7. Avanzamento

| # | Step | Stato |
| --- | --- | --- |
| 0 | Apply DB fatto + firma/JSONB confermati (§2) | ☐ (blocca) |
| 1 | BE: config endpoint + service (mirror liste) | ☐ |
| 2 | BE: endpoint contatori batch (envelope per-key, riuso riepiloghi) | ☐ |
| 3 | BE: seed catalogo 4 widget + preset sistema/ruolo (§5) | ☐ |
| 4 | FE: `useDashboardConfig` + grammatica deep-link + resolver | ☐ |
| 5 | FE: `KpiCard` estratto (regola del 2 → dichiarare) | ☐ |
| 6 | FE: modale personalizzazione + HomeView griglia risolta | ☐ |
| 7 | Verifica E2E: home vuota-safe, permessi, personalizza+salva+reload | ☐ |

## 8. Riferimenti

- Prerequisito DB: [brief-db-dashboard-home.md](brief-db-dashboard-home.md)
- Visione: `docs/it/dev/work-in-progress/frontend/layout-menu-navigazione.md` §9
- Grammatica launcher: `docs/it/dev/work-done/brief-fe-home-operatore-launcher.md` §2.2
- Modello liste da ricalcare: `frontend/src/core/composables/useListaConfig.js`,
  `backend/apps/ui/services/lista_preferenza_service.py`
- Cruscotti KPI v1: `frontend/src/vendite/views/{SituazioneAperta,DashboardCompetenza,DashboardBacklog}View.vue`
  + `docs/it/backend/vendite/manual/api_dashboard_{aperto,competenza,backlog}.md`
- Home attuale: `frontend/src/core/views/HomeView.vue`,
  `frontend/src/stores/navigation.js`,
  `frontend/src/core/composables/useNavigationFavorites.js`
