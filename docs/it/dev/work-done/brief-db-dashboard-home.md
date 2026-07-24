# Brief DB — Dashboard home: catalogo widget + preferenza utente

> **Tipo**: brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-19
> (agg. 2026-07-22) · **Owner**: Tid · **Priorità**: ✅ ASSOLTA — era il
> prerequisito bloccante del lavoro BE/FE sulla home: **il blocco non esiste più**.
> **Stato**: ✅ **CHIUSO (verificato 2026-07-22)** — nulla di aperto lato DB.
> Struttura (enum `ui.tipo_widget` + 6 tabelle), funzione
> `ui.fn_resolve_dashboard_config`, trigger `z90`, seed `dashboard_definizione`
> 'home', fk-index policy, codice errore `E_UI_DASHBOARD_NON_TROVATA` (555), FK
> `auth_user` in 90_end e resync sequenze: **migrations `20260721-12..24`
> applicate, pgTAP `plan(12)` verde, doc auto-gen `dbzero/ui` rigenerata,
> committato in `26bc562d2`** su `dev/db-tid` (migrations + pgTAP + doc + manual
> nello stesso commit). Decisioni §3 prese (2026-07-21) e verifiche §3b/§3e
> confermate sul codice. Comunicazione §5 recepita in
> [brief-be-fe-dashboard-home.md](brief-be-fe-dashboard-home.md) (contratto
> funzione e forma JSONB riportati in §5 / §6-Note).
>
> ⚠️ **Palla a BE/FE.** Il brief a valle è fermo allo step 0 con un header che lo
> dichiara ancora «bloccato sull'apply del prerequisito DB» — presupposto ormai
> superato: i suoi 7 step sono sbloccati.
>
> 📁 Resta in `work-in-progress/` per non rompere i due link relativi same-folder
> del brief BE/FE; spostarlo in `work-done/` richiede prima di correggerli.
>
> **Origine**: revisione della home page. Le 4 card `Dash 1..4` di
> `HomeView.vue` sono placeholder statici dal giorno uno; la visione già scritta
> in [layout-menu-navigazione.md §9.2](../work-in-progress/frontend/layout-menu-navigazione.md)
> («la home diventerà una dashboard personalizzata per utente, composta da card
> configurabili») non è mai stata istruita perché manca ogni struttura di
> persistenza.

## 1. Cosa serve (NON come)

Serve **persistere a DB quali card KPI un utente vede in home, in che ordine**,
con un default sensato per chi non ha mai personalizzato nulla.

Tre capacità, in ordine di dipendenza:

1. **Un catalogo dei widget disponibili**, censiti a sistema — non un elenco
   hardcodato nel frontend. Ogni widget è una card KPI: un numero, una soglia di
   attenzione, e un deep-link a una vista in stato preimpostato.
2. **Un default per ruolo**: quali widget vede un utente che non ha mai toccato
   la home. Deve poter variare per veste applicativa (chi lavora le pratiche non
   vede le stesse card di chi fattura).
3. **Un override per utente**: selezione e ordine scelti dall'utente, che
   vincono sul default.

Il tutto risolto da **una singola funzione di lettura** che, dato un utente,
ritorna la configurazione effettiva della sua home — già filtrata per i permessi
di quell'utente, senza che il BE debba ricomporre nulla.

### Vincolo forte: nessuna home vuota

Un utente nuovo, senza preferenza e senza preset di ruolo applicabile, **deve
comunque ricevere una home popolata**. Una home vuota al primo accesso è peggio
delle 4 card placeholder di oggi. La risoluzione deve degradare fino al
catalogo grezzo, mai a lista vuota.

### Vincolo: i widget sono filtrati dai permessi

Un widget che deep-linka a una vista che l'utente non può aprire **non deve
comparire**, né come card né nel pool selezionabile della personalizzazione. Il
filtro è responsabilità della risoluzione lato DB, non del frontend: il FE non
deve mai ricevere un widget che poi nasconde.

### Fuori dal perimetro di questo brief

- **Quali KPI** entrano nel catalogo iniziale e con che soglie: si decide nel
  brief BE/FE, non qui. Al DB serve che il catalogo *esista*, popolarlo è un
  seed successivo.
- **Come si calcola** ciascun contatore: sono query/endpoint BE sui domini già
  esistenti (pratiche, lenti fatturazione, resi, push commessa). Nessuna
  materializzazione, nessun job.
- **I preferiti-route attuali** (localStorage, `navigation.js`): restano dove
  sono. Migrarli a DB è coerente ma è un refactor a sé che non blocca la home.
- Widget non-KPI (grafici, liste embedded): non ora.

## 2. Il precedente da ricalcare

Il meccanismo esiste già, applicato a un problema quasi identico: la
personalizzazione delle liste, schema `ui`.

| Liste (esistente) | Dashboard (da fare) |
| --- | --- |
| `ui.lista_definizione` — catalogo liste | catalogo dashboard (oggi una sola: `home`) |
| `ui.lista_colonna` — catalogo elementi selezionabili | catalogo widget |
| `ui.lista_preset` + `lista_preset_colonna` — default per ambito `sistema`/`ruolo`/`emittente_fiscale` | default dashboard per ambito |
| `ui.lista_colonna_permesso` — livello accesso per profilo | filtro permessi dei widget (vedi §3) |
| `ui.lista_preferenza_utente` — override utente in JSONB | override utente |
| `ui.fn_resolve_lista_config` — cascata + merge + normalizzazione | risoluzione dashboard |

**La raccomandazione è di restare nello schema `ui` e replicare questa
famiglia**, non di creare una `config.user_preferences` generica. Motivi di
merito, non di comodità:

- La cascata di `fn_resolve_lista_config` è già collaudata e risolve esattamente
  i problemi che si ripresentano qui: preferenza utente prima, poi ruolo (con
  `profili_accesso.priorita` a rompere i pareggi), poi emittente, poi sistema,
  poi catalogo grezzo come rete di sicurezza.
- Il merge automatico degli **elementi nuovi** (step 3 di quella funzione:
  colonne apparse in catalogo dopo che l'utente ha salvato la sua preferenza,
  aggiunte con `visibile=FALSE` e conteggiate in `colonne_nuove`) serve
  identico qui: quando aggiungeremo un widget al catalogo, chi ha già
  personalizzato la home non deve restare cieco né vedersela riscritta.
- Il flag `preset_aggiornato` + `preset_aggiornato_ignored_at` risolve il caso
  "il default di ruolo è cambiato, avviso l'utente che ha un override": vale
  tale e quale.
- Una tabella chiave/valore generica non avrebbe niente di tutto questo, e ce lo
  ritroveremmo da riscrivere a mano nel BE.

Sono agganci da valutare, non un vincolo: se il team DB vede una ragione per
divergere, la decisione è sua — purché le tre capacità di §1 e i due vincoli
restino soddisfatti.

## 3. Punti che chiedono una decisione esplicita — **DECISI (2026-07-21)**

Sono i punti dove la simmetria con le liste non è ovvia, e dove una scelta presa
distrattamente costa cara dopo. Sotto ogni punto, la decisione presa e la
motivazione.

**3a — Il widget appartiene alla dashboard o è globale?**
In `ui`, una colonna appartiene a una lista (`lista_colonna.lista_id`). Per i
widget la simmetria non è scontata: «resi da accreditare» ha senso in home oggi
e potrebbe averlo in una dashboard di magazzino domani. Le due strade sono
widget-per-dashboard (simmetrico, semplice, duplicazione se il widget serve
altrove) o widget globale + tabella di composizione (più flessibile, una FK in
più).

→ **DECISO: widget GLOBALE + tabella di composizione.** Non c'è "una sola
dashboard": home è la prima, ma **backlog** e **fatturazione** (le lenti di
`brief-design-fatturazione-due-lenti.md`) sono già dashboard a modello. Con più
dashboard in arrivo, modellare il widget come globale è la scelta onesta:
`ui.widget` (catalogo globale, `codice` unico) + `ui.dashboard_widget`
(`dashboard_id`, `widget_id`, `ordine_default`) come pool candidato per
dashboard. Evita di duplicare la definizione di un KPI il giorno in cui serve su
due superfici, e la definizione duplicata driftrebbe. Costo: una tabella e un
JOIN in più — accettato perché il bisogno è reale, non ipotetico.
> Nota: se backlog/fatturazione resteranno **viste analitiche fisse** (non
> griglie-card personalizzabili per utente) non entrano in
> `ui.dashboard_definizione`; la struttura regge comunque entrambi i casi.

**3b — Come si filtrano i permessi dei widget.**
Le liste hanno una tabella dedicata (`ui.lista_colonna_permesso`, livello per
profilo) perché una colonna può essere in sola lettura o mascherata. Un widget
non ha stati intermedi: **o lo vedi o non lo vedi**. Replicare la tabella
sarebbe sovradimensionato.

→ **DECISO: nessuna tabella permessi; riuso dei resolver esistenti.**
Verificato sul codice che il filtro è interrogabile dalla funzione di
risoluzione (`STABLE`, GUC-aware, fail-closed sulla veste non-`OPERATORE`):

- `script.fn_resolve_livello_area(auth_user_id, schema_db) → config.livello_accesso`
- `script.fn_check_azione_processo(auth_user_id, permission_codename) → boolean`
- mappe aggregate `script.fn_get_user_permissions_map` / `fn_get_user_actions_map`
  (JSONB), pattern "resolve once" come `fn_resolve_lista_config`.

Sono **esattamente** ciò che il FE usa per nascondere le voci di menu
(`auth.isAreaBlocked(schemaDb)` + `isActionAllowed(codename)` in
`isMenuItemAllowed`): il widget dichiara la stessa cosa che la rotta di
destinazione dichiara. Ogni widget porta `area_id` (FK `config.aree_funzionali`)
e/o `azione_id` (FK `config.azioni_processo`), entrambi **nullable**. Visibile ⇔
`(area IS NULL OR livello_area <> 'BLOCCATO') AND (azione IS NULL OR azione_abilitata)`.
La risoluzione chiama le due mappe una volta e filtra in-memory.

**3c — Quante card in home.**
Oggi sono 4 e i preferiti hanno `FAVORITES_PER_DOMAIN_MAX = 4`: due limiti
scorrelati che coincidono per caso. Se il layout ha un massimo, va fissato
esplicitamente come dato (sul preset, come `lista_preset.pagina_dimensione`),
non lasciato implicito nel CSS del frontend.

→ **DECISO: `dimensione_max` sul preset** (mirror di `pagina_dimensione`),
risolta nella cascata e restituita nel JSONB. Seed del preset di sistema = **8**
(respiro oltre le 4 attuali, tunabile per ruolo/emittente). Il pool selezionabile
resta comunque limitato da catalogo + permessi.

**3d — Chiavi funzionali stabili.**
Convenzione già viva nello schema `ui`: i JSONB di configurazione referenziano
il `codice` stringa, mai l'`id` numerico, per resistere ai cross-ambiente.

→ **DECISO: confermato.** Il JSONB della preferenza referenzia il `codice`
widget. I riferimenti a permessi nel *catalogo* (`area_id`, `azione_id`) sono FK
a `config` — integrità DB-interna, non JSONB cross-ambiente: la convenzione §3d
riguarda il JSONB, non i FK interni del catalogo.

**3e — FK verso `django.auth_user`.**
Come `ui.lista_preferenza_utente`, va aggiunta in fase `90_end` perché
`auth_user` è creata da Django migrate dopo Liquibase.

→ **DECISO: confermato.** Pattern identico già presente in
`90_end/20260506-08-fk-ui-preferenza-auth-user-mctit.yaml` (preCondition
`tableExists django.auth_user` + `onFail: MARK_RAN`). Si replica tale e quale.

**3f — Forma di deep-link, KPI e soglia (emerso in analisi).**
Il deep-link oggi lato FE è **solo una path stringa** (`stores/navigation.js`):
nessun params/query persistito, quindi i widget con "stato preimpostato" sono
territorio nuovo.

→ **DECISO: campi opachi al DB.** `deep_link jsonb` (grammatica route+stato
posseduta dal FE), `contatore_key varchar` (quale KPI — il *come si calcola* è
BE, §Fuori perimetro), `soglia jsonb` (come/quando allarmare). Il DB non
interpreta né valuta nulla di questi tre: li conserva e li restituisce.

### 3.bis — Nodo critico: "mai vuota" vs filtro permessi (emerso in analisi)

C'è una tensione reale tra il **vincolo "nessuna home vuota"** (§1: degradare al
catalogo grezzo) e il **caso §4.5** (widget senza permesso non compare). La
degradazione garantisce non-vuoto **prima** del filtro permessi; ma il filtro è
ortogonale e può legittimamente svuotare la home (utente senza permesso su
*nessuna* area dei widget seedati). La struttura DB **non può inventare
permessi**. Conseguenza: la garanzia "mai vuota" è realmente onorata solo se il
seed del catalogo include **almeno un widget non-gated** (`area_id`/`azione_id`
entrambi NULL, es. card di benvenuto). È una condizione di **seed**, non di
struttura — fuori dal perimetro DDL, ma da comunicare a chi popola il catalogo
(vedi §5).

### 3.ter — Struttura decisa (schema `ui`)

Mirror della famiglia liste, con la composizione §3a:

| Tabella / funzione | Ricalca | Note |
| --- | --- | --- |
| `ui.dashboard_definizione` | `lista_definizione` | Senza `vista_sql` (una dashboard non ha vista sorgente unica). Seed: `home`. |
| `ui.widget` | `lista_colonna` (ma **globale**) | `codice` unico globale; `etichetta`/`etichetta_i18n_key`, `tipo_widget` (enum `ui.tipo_widget`, oggi `kpi`), `deep_link jsonb`, `contatore_key`, `soglia jsonb`, `area_id`, `azione_id`, `attivo`. |
| `ui.dashboard_widget` | *(nuova, §3a)* | Composizione `dashboard_id`↔`widget_id` + `ordine_default`. PK `(dashboard_id, widget_id)`. È il pool candidato + sorgente di "catalogo grezzo"/merge. |
| `ui.dashboard_preset` + `ui.dashboard_preset_widget` | `lista_preset` (+ `_colonna`) | Riuso enum `ui.ambito_preset` + indice unique-parziale sul default. `dimensione_max` ← `pagina_dimensione`. Preset-widget: `ordine` + `visibile`. |
| `ui.dashboard_preferenza_utente` | `lista_preferenza_utente` | JSONB + `preset_base_id`/`preset_base_data_update` + `preset_aggiornato_ignored_at` + trigger `z90` clear-ts identico. `uq(auth_user_id, dashboard_id)`. |
| `ui.fn_resolve_dashboard_config(codice, auth_user_id, emittente_fiscale_id)` | `fn_resolve_lista_config` | Cascata → merge nuovi (`widget_nuovi`) → **filtro permessi** → JSONB `{ widget[], dimensione_max, widget_nuovi, preset_aggiornato }`. Più semplice: niente livelli per-elemento, niente normalizzazione `esportabile`. Sorgente catalogo/merge = `dashboard_widget ⋈ widget` per `dashboard_id`. |

Codice errore: `E_UI_DASHBOARD_NON_TROVATA` (solo **append** al CSV
`messaggi_errore.csv`, nessun nuovo loader). FK-index: seed esplicito
`consentito=true` per i nuovi FK (l'automation da sola registra `false`).

## 4. Verifica attesa

Casi che devono essere esercitati prima di dichiarare fatto — sono le
condizioni al contorno di §1, non un elenco di cortesia:

1. Utente **senza preferenza e senza preset di ruolo** → riceve comunque widget
   (degradazione al catalogo grezzo).
2. Utente con **preferenza** → la preferenza vince sul preset di ruolo.
3. Utente con **due profili di accesso** applicabili → vince quello a priorità
   più bassa, deterministicamente (stesso comportamento di
   `fn_resolve_lista_config` step 2b).
4. **Widget aggiunto al catalogo** dopo che l'utente ha salvato → compare come
   nuovo/non visibile, la preferenza esistente non viene riscritta.
5. Utente **senza permesso** sull'area di un widget → quel widget non compare né
   fra le card né nel pool selezionabile.
6. Widget **disattivato** (`attivo = FALSE`) → sparisce da tutti gli utenti,
   inclusi quelli che l'avevano in preferenza.

## 5. Cosa comunicare indietro a BE/FE

Alla chiusura servono, per poter scrivere il brief BE/FE:

- **firma della funzione di risoluzione** e **forma del JSONB** di ritorno (è il
  contratto che il FE consuma);
- **forma del JSONB** della preferenza utente (è ciò che il FE scrive al salva);
- **codice della dashboard** home e nomi delle tabelle, per il seed del catalogo
  widget che faremo subito dopo;
- eventuali **divergenze** da §2/§3: se il modello adottato non è quello delle
  liste, va detto, perché il BE riuserebbe altrimenti i pattern di
  `lista_preferenza_service.py` per analogia.

Divergenze già note dalle decisioni §3 (da riportare nel brief BE/FE):

- **Widget globale + composizione** (§3a): a differenza di `lista_colonna`
  (legata a `lista_id`), il widget è globale e la coppia dashboard↔widget vive in
  `ui.dashboard_widget`. Il BE che compone per analogia deve JOIN-are la
  composizione, non filtrare per un `dashboard_id` sul catalogo.
- **Niente tabella permessi** (§3b): il filtro non è `lista_colonna_permesso` ma
  i resolver `script.fn_resolve_livello_area` / `fn_check_azione_processo`.
- **Vincolo di seed "mai vuota"** (§3.bis): il catalogo widget deve includere
  **almeno un widget non-gated** (`area_id`/`azione_id` NULL), altrimenti il
  filtro permessi può svuotare la home a un utente senza permessi. La struttura
  non lo garantisce: è responsabilità del seed BE/FE.

Nessun adeguamento FE è pendente: oggi la home mostra card statiche, non c'è
codice da rompere. Il pattern di consumo lato FE è già maturo e riusabile
(`useListaConfig` + API `/api/v1/ui/liste/{codice}/config/`): il brief BE/FE
ricalcherà quella catena per `dashboard`.

## 6. Avanzamento

| # | Step | Stato |
| --- | --- | --- |
| 1 | Decisioni §3a–3f prese e motivate (+ nodo "mai vuota" §3.bis, struttura §3.ter) | ✅ 2026-07-21 |
| 2 | Catalogo widget globale + composizione + default per ambito + preferenza utente | ✅ 2026-07-21 (`20260721-12..18`) |
| 3 | Funzione di risoluzione con cascata, merge nuovi, filtro permessi | ✅ 2026-07-21 (`20260721-19..20`) |
| 4 | Verifica §4 (6 casi) | ✅ 2026-07-21 (pgTAP `plan(12)` verde) |
| 5 | Apply dev + rigen doc auto-gen + comunicazione §5 a BE/FE | ✅ 2026-07-21 (tutte e tre) |
| 6 | Commit su `dev/db-tid` | ✅ `26bc562d2` (migrations + pgTAP + doc auto-gen + manual) |

**Brief chiuso lato DB.** Il seguito è in
[brief-be-fe-dashboard-home.md](brief-be-fe-dashboard-home.md), che non ha più
prerequisiti pendenti. Le due responsabilità che il DB **non può** garantire e
che passano al seed BE/FE restano quelle di §3.bis e delle note qui sotto:
(a) almeno un widget non-gated, (b) resync sequenze se si seeda con id espliciti.

> **Note di realizzazione (2026-07-21).** Divergenze §2/§3 concretizzate:
> filtro permessi via mappe aggregate `script.fn_get_user_permissions_map` /
> `fn_get_user_actions_map` (pattern "resolve once", fail-closed non-OPERATORE),
> non i resolver scalari. Contratto funzione:
> `ui.fn_resolve_dashboard_config(codice, auth_user_id, emittente_fiscale_id) →
> jsonb { widget[], dimensione_max, widget_nuovi, preset_aggiornato }`; ogni
> widget porta `{codice, ordine, visibile, tipo_widget, etichetta,
> etichetta_i18n_key, deep_link, contatore_key, soglia}`. Preferenza scritta dal
> FE: `{ widget:[{codice,ordine,visibile}], dimensione_max }`. **Seed BE/FE**:
> (a) almeno un widget non-gated (§3.bis); (b) resync sequenze `ui.widget` /
> `ui.dashboard_preset` quando seedati con id espliciti (nota nel file `20260721-24`).

## 7. Riferimenti

- Visione home: `docs/it/dev/work-in-progress/frontend/layout-menu-navigazione.md` §9
  (§9.1 stato attuale, §9.2 visione futura, §Persistenza preferiti riga 527)
- Precedente di design sulla grammatica launcher:
  `docs/it/dev/work-done/brief-fe-home-operatore-launcher.md` §2.2
- Modello da ricalcare: `docs/it/dbzero/ui/` (tabelle `lista_definizione`,
  `lista_colonna`, `lista_preset`, `lista_preset_colonna`,
  `lista_colonna_permesso`, `lista_preferenza_utente`)
- Funzione di riferimento: `docs/it/dbzero/ui/funzioni/fn_resolve_lista_config.md`
  e `docs/it/dbzero/ui/manual/fn_resolve_lista_config.md`
- Consumatori attuali della home: `frontend/src/core/views/HomeView.vue`,
  `frontend/src/stores/navigation.js`,
  `frontend/src/core/composables/useNavigationFavorites.js`
- Dashboard esistenti (candidate a fornire i KPI):
  `docs/it/dev/work-in-progress/brief-design-fatturazione-due-lenti.md`
