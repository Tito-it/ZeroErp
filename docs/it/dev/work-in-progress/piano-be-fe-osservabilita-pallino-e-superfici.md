# Piano BE/FE — Osservabilità, l'ultimo miglio: il pallino dei presidi, il giornale degli errori, la consultazione di `error_log`

> **Chi scrive:** backend/frontend (`dev/backend-tid`), 2026-09-18.
> **Origine:** [analisi-osservabilita-log.md](analisi-osservabilita-log.md) — a
> Passo D chiuso (18-09) restavano **B** intero, la sorgente «lotto fermo» di
> **C**, **R-6**, la **#8** e il brief della #14; Tid ha chiesto *«un brief
> apposito con piano di sviluppo»*. La **#8 è decisa** lo stesso giorno (§2.1).
> I prerequisiti DB stanno in
> [brief-db-osservabilita-lotto-fermo-r6-indici.md](brief-db-osservabilita-lotto-fermo-r6-indici.md)
> (P-1 … P-3). La #14 **non è qui**: resta il debito dichiarato che è.
> **Stato:** 🔵 **scritto il 2026-09-18**. Il pezzo **P** non aspetta nessuno;
> **E** e **G** aspettano gli indici (P-3), **G** anche R-6 (P-2); **V** aspetta
> il verdetto a DB (P-1). Nessuna riga di codice scritta.
>
> **In una riga.** Il piano dell'osservabilità è a cinque passi su sette; questo
> documento chiude gli altri due con **quattro pezzi**: un **pallino in topbar**
> che dice «i presidi sono a posto» anche quando la posta tace (P — la #8); il
> **giornale degli errori** trasversale, cioè la Storia di tutte le entità
> insieme filtrata per gravità (G — metà di B); la **consultazione di
> `error_log`** per i tecnici, dietro permesso (E — l'altra metà di B); e il
> **verdetto «lotto fermo» che nasce a DB** e da lì alimenta banner, digest e
> pallino con una sede sola (V — la sorgente di C). L'altra metà di B — «UI sugli
> endpoint orfani» — è **chiusa per decisione** dall'11-09 (§1.7), non da fare.
>
> ⛔ **Niente misure come motivo.** I numeri di questo documento (righe di
> `error_log`, viste `ZERO` a catalogo) sono **fatti datati** e servono a
> scegliere una cadenza o a stimare un costo: nessuna forma qui sotto dipende da
> essi. Si progetta sul modello.

---

## 0-bis. Stato di avanzamento

> Una riga per pezzo. ✅ fatto · 🟡 in parte · ⏳ in attesa di un prerequisito
> · 🔵 da fare.

| Pezzo | Stato | Prerequisito | Dove |
| --- | --- | --- | --- |
| **P** — il pallino dei presidi in topbar (BE + FE) | 🔵 | **nessuno** | §2 |
| **E** — consultazione `error_log` (BE + FE, amministrazione) | ⏳ | P-3 (indici) | §4 |
| **G** — il giornale degli errori trasversale (BE + FE, vendite) | ⏳ | P-3 (indici) + P-2 (R-6) | §3 |
| **V** — il verdetto «lotto fermo» letto dal DB (BE) | ⏳ | P-1 | §5 |
| ~~B6~~ — UI sugli endpoint orfani | ✅ chiusa **per decisione** (11-09) | — | §1.7 |

---

## 1. Il terreno, verificato sul codice (2026-09-18)

### 1.1 La topbar ha già una cassetta per questo genere di segnale

`AppTopbar.vue`, gruppo `.topbar-actions-inline`: il **badge delle code** —
icona `pi-inbox`, due segmenti (`lavoriVivi` info · `stampaVive` warn), icona in
warn se `workerOk === false`, click → `ui.openCodeDrawer()`, voce gemella nel
kebab utente su mobile. Lo alimenta `useQueueCountsPolling` (core), che dal
27-08 è **solo dominio** — endpoint, lettura dei conteggi, politica sugli errori
— sopra il BB `useRefreshPeriodico` (timer, sospensione a tab nascosta, ripresa
immediata, `abilitato` per lo spegnimento **definitivo** su 403/401,
`subitoAlMount`). Cadenza 60s, motivata dal drenatore (~1/min).

### 1.2 I presidi hanno già repository, testata ed endpoint

- `PresidiRepository.stato_presidi()` (`apps/core/db/presidi_repository.py`):
  legge dal catalogo `dbops.presidi` le sole viste di natura **`ZERO`**, conta
  con `dbops.fn_conta_presidio` (attraversa la RLS, applica la coppia
  `colonna_stato`/`stato_atteso`), chiede le **prime righe** solo se il
  conteggio è > 0 e solo a perimetro `LIBERO`, isola l'errore **per presidio**
  (`conteggio: None`, `errore`, `da_guardare: True`).
- `ProcessiService.stato_presidi()` (`apps/core/services/processi_service.py`)
  ci mette la **testata**: `{presidi, con_righe, non_letti}`.
- `GET /api/v1/amm-software/processi/presidi/` — `ProcessiPresidiView`,
  **`AdminAPIView`** (le viste nominano tutte le aziende: vincolo del Passo A
  applicato a un aggregato). FE: `getProcessiPresidi()` in
  `amministrazione/api/amministrazione.js`, consumato da
  `ProcessiAutomaticiListView.vue` (rotta `amm-software-processi-automatici`,
  icona `NAV_ICONS.PROCESSI_AUTOMATICI`).

⭐ **La testata è già il pallino**: `con_righe` è il numero rosso, `non_letti` il
numero che «chiede un occhio» senza essere un guasto. Manca solo una lettura
**leggera** (senza le prime righe) e un consumatore in topbar.

### 1.3 Il giornale ha una vista sola e due lettori, entrambi per entità

`script.vw_giornale_entita` (`security_invoker`): `UNION ALL` di quattro registri
(`event_log`, `fatture_log`, `fatturazione_lotti_log`,
`fatturazione_lotti_task_runs`) in forma normalizzata — `riga_key`, `registro`,
`riga_id`, `quando`, `entity_type`, `entity_id`, `gravita`, `cosa`, `tx_id`,
`correlation_id`, `auth_user_id`, `user_insert`, `disabilitato`. Lettori:
`list_giornale_entita` (fattura) e `list_giornale_lotto` in
`vendite_repository.py`, entrambi sopra il privato `_list_giornale` /
`_conta_giornale`; endpoint `/vendite/fatture/<id>/giornale/` e
`/vendite/lotti/<id>/giornale/`; FE la scheda «Storia» (`FatturaDrawer`, lotto),
gravità resa con `gravitaGiornaleSeverity` (`core/utils/severity.js`).
⛔ **Il cancello dei due endpoint è la testata** (la fattura o il lotto, sotto
RLS): la vista da sola tornerebbe zero righe fuori scope, che si legge «non è
successo niente». Una lettura **senza** testata (§3) non ha quel cancello: il
perimetro lo fa la RLS dei quattro registri, e va **provato**, non dedotto (R-4:
il perimetro del giornale non è mai stato esercitato).
⚠️ Indici per **tempo**: su `event_log` solo `(entity_type, entity_id,
event_time)` e `(correlation_id, event_time)` — nessuno sul solo tempo o sulla
gravità; **nessuno** per tempo su `fatture_log` (`data_ora`),
`fatturazione_lotti_log` (`data_ora`), `task_runs` (`started_at`). Una lettura
«tutti gli errori dell'ultimo mese» oggi non ha un indice da cui partire → P-3.
⚠️ **R-6** è ancora vero: la riga `TASK_RUN` esce con `quando =
COALESCE(tr.ended_at, tr.started_at)` → P-2.

### 1.4 `dbops.error_log` si può leggere, ma non ha da dove partire

Colonne: `occurred_at`, `area`, `function_name`, `messaggio_errore_id` (FK →
`config.messaggi_errore`, che porta `codice` → `config.codici_errore`, `causa`,
`soluzione`), `context jsonb`, `tx_id`, `cleanup_at`. Indici: pk,
`messaggio_errore_id`, `cleanup_at` — **niente** su `occurred_at`, `area`,
`function_name`, `tx_id` → P-3. Privilegi (letti sul DB, 18-09): `zeroerp_app`
ha `SELECT` e non `DELETE` (postura append-only, corretta: la consultazione è
una lettura). ⛔ **Vincolo del Passo A** (Tid, 24-08): un diario tecnico nasce
**dietro un permesso dichiarato**, per i tecnici — oggi quel permesso è
`AdminAPIView`, lo stesso di `audit-log` ed `email/log` che già stanno in
amministrazione.

### 1.5 Il gesto «vai a quella cosa» ha un resolver solo

`core/bersagli.js` → `DESTINAZIONI`: da `(entity_type, entity_id)` alla
destinazione raggiungibile, con la regola «irraggiungibile → nessun pulsante».
`TASK_RUN` è a catalogo e **non** raggiungibile, deliberatamente. Il giornale
trasversale non inventa un secondo resolver: usa questo.

### 1.6 Il verdetto «lotto fermo» oggi vive in Python

`LottoSegnalazioniService.evaluate_lotto_status` (`apps/vendite/services/`):
`is_error = blocks_next_step = critical_count > 0 or
fatture_stato_esecuzione_errore_count > 0 or esiti_stato_esecuzione_errore_count
> 0`, con i conteggi da `vendite.fn_get_lotto_segnalazioni_summary` — la cui
`COMMENT` dice testualmente *«blocks_next_step resta in Python»*. Il banner FE
(`scegliRamoBanner`, `vendite/_shared/lotti/`) è **totale** su quel verdetto.
⇒ Un presidio «lotto fermo» scritto a DB sarebbe la **seconda sede** dello
stesso predicato, e le due divergerebbero al primo addendo nuovo — il banner
direbbe «fermo» e il digest «tutto a posto», o il contrario. La forma giusta è
**una sede a DB e il BE che trasporta** (P-1 del brief DB, §5 qui).

### 1.7 Gli «endpoint orfani» di B non sono più una cosa da fare

Il §4 Passo B del brief madre elenca «UI sugli endpoint orfani (`job-runs`,
`job-summary`)» e la nota ⏱️ 12-09 «più i quattro endpoint ancora orfani». Ma
[piano-be-fe-endpoint-senza-porta.md](piano-be-fe-endpoint-senza-porta.md)
(decisione di Tid, **2026-09-11**) ha già risposto per ciascuno: `domini-task`,
`task-registry`, `task-implementations` sono **servizio** (configurazione del
motore, nessuna porta); `job-summary` è **candidato al ritiro** — la stessa
domanda ha due risposte migliori (pannello code, digest). ⇒ **B6 chiude per
decisione**, e il brief madre va aggiornato (fatto nello stesso giro, ⏱️ 18-09).

---

## 2. Pezzo P — il pallino dei presidi in topbar *(BE + FE, nessun prerequisito)*

### 2.1 ✅ La decisione #8 *(Tid, 2026-09-18)*

**Sì al pallino in-app**, e sta in **topbar accanto al badge delle code** — non
accanto alle iniziali dell'operatore. Le ragioni, in ordine:

1. **È lo stesso genere di segnale del badge code**: contatore ambientale, letto
   a cadenza lenta, spento su 403, click verso una superficie che esiste già.
   Messi vicini si leggono come una coppia — *lavoro in corso* · *allarmi* — e
   formano il gruppo «salute del sistema».
2. **Accanto alle iniziali direbbe la cosa sbagliata**: lì stanno «chi sei» e
   «che giorno è»; un pallino attaccato alle iniziali si legge «notifiche per
   te». Questo parla del sistema.
3. **Deve dire anche «tutto ok»**: è il motivo per cui la #8 esiste — la
   giornaliera a zero righe **tace per scelta**, e il silenzio è ambiguo. Il
   pallino è sempre visibile per chi ha il permesso: **verde a zero, rosso col
   numero**; il tooltip porta l'ora dell'ultima lettura.
4. **Click → «Processi automatici»**, che c'è già. Nessuna schermata nuova.

**Chi lo vede.** Chi vede il pannello — oggi `AdminAPIView`. Per chi non ha il
permesso l'endpoint risponde 403 e il pallino **non compare**, come il badge
code per chi non ha l'area core. ⚠️ Se un giorno lo si vorrà anche per
l'operatore, è una decisione di **permessi sui presidi** (le viste nominano
tutte le aziende), non di UI: il pallino è già pronto. Resta nel §8 come
decisione rimandata, dichiarata.

### 2.2 BE — `GET /api/v1/amm-software/processi/presidi/conteggi/`

`AdminAPIView`, nella stessa famiglia di `processi/presidi/`. ⚠️ **Registrata
prima di `<str:codice>/`** in `amm_software/api/urls_v1.py`, per la stessa
ragione scritta lì per `presidi/`: Django la leggerebbe come il codice di un
processo che si chiama «presidi».

Risposta:

```json
{ "data": { "totale": 21, "con_righe": 1, "non_letti": 0 } }
```

- `PresidiRepository.conteggi_presidi() -> list[dict]`: lo stesso giro di
  `stato_presidi()` **senza `prime_righe`** — per ogni `ZERO`: `conta()`,
  isolamento per presidio, `conteggio: None` + `errore` se non letta. ⭐ La sede
  del «quali viste» resta il catalogo, come là: qui non nasce nessun elenco.
- ⭐ **Regola del 2, dichiarata prima di scrivere**: `con_righe` e `non_letti`
  oggi si calcolano dentro `ProcessiService.stato_presidi()`; il nuovo endpoint
  li ricalcolerebbe identici. Si estrae **una** funzione di testata
  (`_testata_presidi(righe) -> {totale, con_righe, non_letti}`) usata da
  entrambi: due copie di due `sum(...)` divergono alla prima modifica del
  predicato «chiede un occhio». *Si aspetta l'ok di Tid sull'estrazione*
  (memoria: regola del 2, dichiarare prima).
- `ProcessiService.conteggi_presidi()` → `_testata_presidi(self._presidi.conteggi_presidi())`.
- `@extend_schema` con `inline_serializer` (tre `IntegerField`).
- Errori: nessun codice nuovo. Un presidio che non si legge **non è un errore
  dell'endpoint**: è `non_letti + 1`, per contratto.

**Cadenza — decisa sul modello, non su una misura.** 300 s, non 60 come le code.
Il badge code segue il drenatore (~1/min); qui la sorgente **più rapida** a
catalogo ha soglie di **un'ora** (le tre viste delle code) e il canale di
riferimento è la giornaliera delle 07:00. Cinque minuti dicono la stessa cosa a
un quinto del costo, e il costo non è nullo: ogni tick sono N `SELECT
count(*)` su viste che scandiscono cataloghi. ⚠️ La cadenza sta **nel
composable**, in una costante con questa motivazione accanto.

**Test (`SimpleTestCase`, repository mockato):** testata su un elenco misto
(conteggio > 0, = 0, `None` con `errore`); route che risolve a
`ProcessiPresidiConteggiView` e **non** a `ProcessiDetailView` con
`codice="presidi"`; 403 per non-admin (stesso stampo dei test esistenti delle
view admin). ⚠️ Il test dell'estrazione: **una** funzione, due chiamanti,
`assertIs` sul callable — il modo in cui si vede che non è stata ricopiata.

### 2.3 FE — `usePresidiPolling` e il pulsante

**Chiamata.** `getPresidiConteggi()` in `amministrazione/api/amministrazione.js`,
accanto a `getProcessiPresidi()`.

**Composable.** `core/composables/usePresidiPolling.js` — gemello di
`useQueueCountsPolling`, **solo dominio** sopra `useRefreshPeriodico`:

- `abilitato: () => disponibile.value !== false` — su 403/401 `disponibile =
  false`, spegnimento **definitivo** (il BB non riparte al rientro in primo
  piano, che è il motivo per cui `abilitato` esiste);
- `subitoAlMount: true` (un contatore nasce vuoto);
- errori di rete transitori: si tiene l'ultimo valore, niente toast;
- espone `{ totale, conRighe, nonLetti, lettoAlle, disponibile, refresh }`;
- ⭐ **la resa del pallino è una funzione pura con la sua spec**, come
  `scegliRamoBanner`: `statoPallino({conRighe, nonLetti, disponibile}) →
  {segmenti: [{valore, severity}], ok: bool}`. Tre rami che non falliscono se
  sbagliati — mostrano il colore sbagliato — e una spec con un caso per ramo:
  tutto a zero (verde, `0`); solo allarmi (danger, N); solo non letti (warn,
  M); entrambi (due segmenti, ordine fisso: prima gli allarmi).
- ⚠️ `core` che importa da `amministrazione/api/` è un'eccezione **dichiarata
  nel commento in testa**, dello stesso genere dei componenti geografici che
  importano store da `anagrafiche/`: la topbar è core, l'endpoint è
  amministrazione, e duplicare la chiamata in `core/api/` sarebbe peggio.

**Pulsante.** In `AppTopbar.vue`, dentro `.topbar-actions-inline`, **subito
dopo** il pulsante code:

- icona `NAV_ICONS.PROCESSI_AUTOMATICI` (`pi pi-cog`): è la destinazione del
  click, e il nome dell'icona vive in **una** sede (frontend-standards §«Dove
  vive il NOME di un'icona»);
- `<Badge>` per segmento, classi `topbar-presidi-badge` gemelle di
  `topbar-code-badge` (stesso posizionamento, in `main.css` accanto);
- a zero: **un** badge `severity="success"` con `0` — la forma visibile del
  «visto e vuoto»; `v-if="disponibile"` sull'intero pulsante;
- tooltip `t('amministrazione.processi.presidi_badge_tooltip', {allarmi,
  non_letti, ora})` — l'ora formattata con il formatter di locale già in uso in
  topbar (`formattedDate` usa il suo), **non** un `toLocaleTimeString` inline;
- click → `router.push({ name: 'amm-software-processi-automatici' })`;
- voce gemella nel kebab utente (ramo mobile), come per le code, sotto
  `if (presidiDisponibile.value)`.

**Rinfresco dal pannello.** `ProcessiAutomaticiListView`, quando ricarica i
presidi (mount, «Ricarica»), chiama `refresh()` del composable — lo stesso patto
di `CodeLavoroDrawer` col badge code: chi ha appena letto il dato vero non lascia
il pallino a raccontare quello di quattro minuti fa.

**i18n.** Chiavi in `amministrazione.processi.*` (il namespace della schermata:
`presidi_badge_tooltip`, `presidi_badge_ok`, `presidi_badge_menu`), in `it.json`
**e** `en.json`; `python3 scripts/check_i18n_keys.py` verde.

**Header di licenza** su `usePresidiPolling.js` e sulla spec (file nuovi).

---

## 3. Pezzo G — il giornale degli errori, trasversale *(BE + FE, dopo P-2 e P-3)*

> «Cosa è andato storto, su tutto, nell'ultimo periodo» — la Storia di tutte le
> entità insieme, filtrata per gravità. È la «vista errori trasversale (non
> legata al mese di competenza), con salto al lotto e alla commessa» del Passo
> B, costruita sulla **stessa vista** del Passo A e non su un aggregato nuovo.

### 3.1 BE — `GET /api/v1/vendite/giornale/`

`DomainAPIView`, `area_funzionale = "vendite"`, `is_search_endpoint = True`.
Envelope paginato standard (`paginated_envelope`, page-based, `validate_pagination`).

**Filtri (query params), tutti in whitelist e tutti provati:**

| Param | Tipo | Default | Note |
| --- | --- | --- | --- |
| `gravita` | lista di `ERROR`/`WARN`/`INFO` (csv) | `ERROR` | ⚠️ `NULL` è «la riga che dichiara un difetto» (perimetro del pannello lotto): con `ERROR` **si include** il `NULL`, come là |
| `registro` | `EVENT_LOG`/`FATTURA_LOG`/`LOTTO_LOG`/`TASK_RUN` | tutti | vocabolario della vista |
| `entity_type` | codice di `config.tipi_entita` | tutti | |
| `data_da` / `data_a` | date | **floor standard**: oggi−60gg al 1° del mese | è consultazione, non coda di lavoro: il floor si applica (memoria filtro data) |
| `correlation_id` / `tx_id` | uuid | — | il «filo» (R-2: filtrare per filo tiene `event_log` + `task_run` e butta le righe scritte per una persona — il default **non** filtra per filo) |
| `solo_vive` | bool | `true` | esclude `disabilitato = true` (segnalazioni ritirate) |
| `order_by` | `quando` (default `DESC`), `gravita` | | `sql_order_clause` con tiebreak `riga_id`, come i due lettori esistenti |

**Repository.** Un terzo lettore sopra il privato `_list_giornale`: il ramo
«senza entità» è un `WHERE` in meno, non una query in più — se `_list_giornale`
oggi presuppone la coppia `(entity_type, entity_id)`, si generalizza **lì**
(un parametro opzionale), non si copia. ⭐ **Al terzo consumatore il lettore del
giornale esce da `vendite_repository.py`**: il commento in testa dice già *«al
SECONDO dominio va spostato in `core`»* — il dominio è ancora `vendite`, quindi
non ancora; ma si dichiara qui, perché il prossimo (pratiche) lo sposta.

**Display fields via JOIN, nel BE** (memoria: liste API → display dal BE, mai
lookup client-side): `entita_display` = codice del lotto / numero (e natura) del
documento, con `LEFT JOIN` condizionati su `entity_type`; `cosa_descrizione`
dal catalogo dei codici evento (JOIN), non da un dizionario FE. ⚠️ I due JOIN
attraversano tabelle in RLS: fuori scope danno `NULL`, e fuori scope la riga
**non c'è** (la vista è `security_invoker`) — coerente, ma va nel test.

**Il perimetro si prova, non si deduce (R-4).** Test sul DB provvisto
(`richiedi_db_provvisto`, `ZEROERP_TEST_DB_E2E=1`) che **costruisce** righe di
giornale per due emittenti coi builder pgTAP-like del backend e legge con il
contesto del solo primo: la seconda **non compare**, e il conteggio dice il
numero **visto**, non il totale. È il presidio che il Passo A non ha mai avuto.

**EXPLAIN prima di consegnare** (memoria: ciò che il contratto dichiara ammesso
si prova per intero): ogni filtro della whitelist, da solo e con `data_da`, sul
DB vero, dopo P-3. Un piano che scandisce un registro intero è un 500 differito,
non un dato.

⛔ **Niente `context`/`payload` in questa lista**: espone le stesse colonne della
Storia e nient'altro. Gli appunti forensi restano nella Storia dell'entità
(vincolo del Passo A), che è già dietro il permesso dell'area.

**Export**: `ListaExportService` + `get_lista_config` (rispetta la preferenza
colonne), date via `locale_formatters`.

### 3.2 FE — la view e la lista

- Rotta `vendite/giornale`, voce di menu «Giornale» sotto **Vendite ›
  Fatturazione** (accanto a lotti e code: è lo stesso mestiere visto dagli
  errori), `navigation.js` con icona sua in `NAV_ICONS`.
- `<ListaConfigurabile codice="vendite.giornale">` — seed con
  `scripts/gen_seed_lista.py` (una riga `lista_definizione` + colonne: `quando`,
  `gravita` (Tag via `gravitaGiornaleSeverity`), `registro`, `entity_type`
  (etichetta da `config.tipi_entita.<codice>`, chiave dichiarata dal DB),
  `entita_display`, `cosa`, `cosa_descrizione`, `user_insert`, `tx_id`,
  `correlation_id`). È dato, non DDL: **non aspetta nessuno**.
- Toolbar: `FiltroToggle` «solo errori» (default acceso ⇒ `gravita=ERROR`;
  spento ⇒ `ERROR,WARN`), select `registro` ed `entity_type`, filtro data
  standard, campo `tx_id`/`correlation_id` (un campo, «filo») — tutto via
  `useStoreFilterBindings`, `PageActionsBar` con export.
- Kebab riga (`RowActionsMenu`, `MANAGE_ICONS.KEBAB`):
  - **«Apri …»** → `core/bersagli.js` `DESTINAZIONI` su `(entity_type,
    entity_id)`: `LOTTO` e `FATTURA` raggiungibili, `TASK_RUN` no ⇒ **nessun
    pulsante**, per la regola scritta; la **commessa** è a catalogo (`COMMESSA`)
    — se non è in `DESTINAZIONI`, si aggiunge **una riga lì** (è così che si
    aggiunge un tipo raggiungibile), non un `if` nel giornale;
  - **«Storia»** → il drawer dell'entità sulla scheda Storia (il pezzo forense
    completo, con `context`), dove il drawer la espone.
- Store Pinia `vendite/stores/giornale.js` dalla factory dei search store,
  **`userScoped: true`**; `useSearchTable(store)`; `KeepAlive` con
  `onActivated` idempotente (deep-link `?tx_id=` dal Pezzo E, §4.2).
- i18n in `vendite.giornale.*`; parità it/en; `check_i18n_keys.py` verde.

---

## 4. Pezzo E — la consultazione di `error_log` *(BE + FE, amministrazione, dopo P-3)*

> Per i tecnici, dietro il permesso dichiarato: «quale funzione ha sollevato
> quale codice, quando, in quale transazione». La lista che chiude il §4 Passo B
> terzo punto — e il ponte verso il giornale: dal `tx_id` di un errore tecnico
> alla storia di dominio della stessa transazione (§3).

### 4.1 BE — `GET /api/v1/amm-software/error-log/`

`AdminAPIView` (vincolo del Passo A — oggi il permesso dei tecnici è questo,
come per `audit-log` ed `email/log`), `is_search_endpoint = True`, envelope
paginato standard.

**Repository.** `DbopsRepository.list_error_logs` in
`apps/core/db/dbops_repository.py`, **accanto** a `list_audit_logs` e nella sua
stessa forma (whitelist colonne, `sql_order_clause`, `conta_con_perimetro` se il
perimetro scarta righe). `JOIN config.messaggi_errore m ON m.id =
e.messaggio_errore_id` per esporre `codice`, `messaggio`, `causa`, `soluzione`
(la frase e la soluzione **a catalogo**, non ricostruite).

**Filtri:** `area` (select dal catalogo `config.aree_funzionali` via
`lookupCodici` — whitelist, nessun endpoint dedicato), `function_name` (prefisso,
`ILIKE 'x%'`), `codice` (esatto), `tx_id` (esatto), `data_da`/`data_a` su
`occurred_at` (floor standard), `order_by` `occurred_at DESC` con tiebreak `id`.

**`context`** si espone **com'è**: qui il lettore è il tecnico e il `context`
sono i suoi appunti — «non va ripulito o riscritto per renderlo presentabile»
(brief madre, Passo A). ⛔ Nessun tentativo di renderlo «leggibile»: quello è il
loop che il vincolo esiste per spezzare.

**EXPLAIN** su ogni filtro della whitelist dopo P-3, come per G.

**Export**: sì, stesso BB.

**Test** (`SimpleTestCase`, cursor mockato): whitelist dell'`order_by` (un nome
fuori whitelist → 400 `E_VALIDATION`, non SQL), composizione `WHERE` per ogni
filtro, ripiego dei default. Un test sul DB provvisto legge una riga vera
(`richiedi_db_provvisto`) e verifica il JOIN col catalogo.

### 4.2 FE — `ErrorLogListView`

- Rotta `amm-software/error-log`, voce di menu accanto a «Log di audit» ed
  «Email log» (stessa famiglia), `<ListaConfigurabile codice="dbops.error_log">`
  seedata via `gen_seed_lista.py`: `occurred_at`, `area`, `function_name`,
  `codice`, `messaggio`, `tx_id`, più `context` **non** come colonna ma come
  dettaglio (sotto).
- Toolbar: `area` (select whitelist), `function_name` (testo), `codice` (testo),
  `tx_id` (testo), filtro data standard; `PageActionsBar` con export.
- Il `context` si apre dal kebab riga («Dettaglio») nello **stesso** componente
  con cui `AuditLogView` mostra il proprio payload JSON — se oggi quel render
  vive dentro `AuditLogView`, al secondo consumatore si estrae (regola del 2,
  **dichiarazione**: sarà `core/components/JsonDettaglioDrawer` o il nome che
  quel componente già porta; si chiede l'ok prima).
- Kebab riga: **«Giornale di questa transazione»** → `vendite/giornale?tx_id=…`
  (deep-link al Pezzo G, `onActivated` lo legge) — visibile solo se l'utente
  raggiunge l'area vendite (è un'offerta, non una promessa); **«Copia tx_id»**.
- Store `amministrazione/stores/errorLog.js` (`userScoped: true`), i18n in
  `amministrazione.error_log.*`.

---

## 5. Pezzo V — il verdetto «lotto fermo» nasce a DB *(BE, dopo P-1)*

Quando il team DB consegna P-1 (la colonna `fermo` nel riepilogo, o il predicato
che il brief DB sceglierà), il BE **smette di decidere**:

- `LottoSegnalazioniService.evaluate_lotto_status` legge `fermo` dal riepilogo e
  lo mette in `is_error`/`blocks_next_step`; i tre conteggi **restano** — sono
  per la frase del banner, non per la decisione (è ciò che la `COMMENT` della
  funzione dice già dei suoi ultimi tre numeri);
- ⚠️ la riga del riepilogo si legge **per posizione**: la colonna nuova è in
  coda, e il `TypedDict` del BE si allunga nello stesso commit;
- test: quelli esistenti che pinnano i tre addendi passano a pinnare
  `blocks_next_step == fermo`; i tre addendi li prova il pgTAP di P-1. ⭐ Un
  test di **parità** transitorio (i tre addendi in Python ⇔ `fermo` a DB) vive
  il tempo di una PR e poi si toglie: non è un presidio, è il collaudo della
  migrazione di sede.
- FE: **niente**. `scegliRamoBanner` legge `blocks_next_step` come oggi. Il
  presidio nuovo compare da solo nel pannello «Processi automatici», nel digest
  e nel pallino (§2): è la ragione per cui il catalogo esiste.

---

## 6. Regola del 2 — le estrazioni dichiarate in questo piano

| Dove | Cosa | Perché ora |
| --- | --- | --- |
| BE §2.2 | `_testata_presidi(righe)` condivisa fra `stato_presidi` e `conteggi_presidi` | seconda occorrenza di `con_righe`/`non_letti` |
| BE §3.1 | `_list_giornale` con entità **opzionale** (generalizzazione, non copia) | terzo lettore della vista |
| FE §2.3 | `statoPallino(...)` pura + spec | tre rami senza errore possibile |
| FE §4.2 | il render del JSON di dettaglio, se oggi è dentro `AuditLogView` | secondo consumatore |

Tutte e quattro **si annunciano a chat prima di scrivere** e aspettano l'ok.

---

## 7. Ordine dei passi, con chi fa cosa

| # | Chi | Cosa | Dopo |
| --- | --- | --- | --- |
| 1 | **team DB** | P-1 verdetto + presidio, P-2 R-6, P-3 indici ([brief DB](brief-db-osservabilita-lotto-fermo-r6-indici.md)) | — |
| 2 | **BE + FE** | **P** — pallino (§2) | subito, in parallelo a 1 |
| 3 | **BE + FE** | **E** — `error_log` (§4): il più piccolo, chiude il ponte `tx_id` | P-3 applicato + EXPLAIN |
| 4 | **BE + FE** | **G** — giornale (§3) | P-2 + P-3 applicati + EXPLAIN + test perimetro |
| 5 | **BE** | **V** — il verdetto dal DB (§5) | P-1 applicato |
| 6 | **BE/FE** | documentazione (§8) e aggiornamento del brief madre: B, C, R-6 chiusi | ogni pezzo |

⚠️ Le PR restano **una per pezzo**; nessuna include un commit che non compila
(memoria: l'hook gira sullo staged e non stagea).

---

## 8. Decisioni prese in questo piano *(da smentire, non da confermare)*

| # | Decisione | Alternativa scartata e perché |
| --- | --- | --- |
| D-P1 | Il pallino sta accanto al badge code, verde a zero, click → Processi automatici (#8) | accanto alle iniziali: parla di te, non del sistema; nascosto a zero: il silenzio è il problema che la #8 risolve |
| D-P2 | Cadenza 300 s | 60 s come le code: la sorgente più rapida ha soglie di un'ora, cinque volte le richieste per la stessa notizia |
| D-P3 | Il pallino segue il permesso dell'endpoint (oggi admin) | «per tutti» ora: le viste nominano tutte le aziende — è una decisione di permessi sui presidi, non di UI; **rimandata e dichiarata** |
| D-G1 | Il giornale trasversale è un terzo lettore della **stessa** vista, `DomainAPIView` vendite, sotto RLS | un aggregato nuovo / una vista nuova: il Passo A ha già la forma normalizzata, e un aggregato è la cosa che «costruita oggi sarebbe illeggibile» |
| D-G2 | Voce «Giornale» sotto Vendite › Fatturazione | sotto amministrazione: il lettore è chi lavora i lotti, sotto RLS del proprio emittente |
| D-G3 | Niente `context`/`payload` nella lista trasversale | mostrarli: vincolo del Passo A, la lista è una vetrina, la Storia è forense |
| D-E1 | `error_log` dietro `AdminAPIView`, con `context` com'è | un permesso dedicato «tecnici»: oggi non esiste come livello; si allinea a `audit-log`/`email/log`. Il giorno che nascerà, si sposta con quelli |
| D-V1 ✅ **Tid, 18-09** | Il verdetto «lotto fermo» ha **una** sede, a DB; il BE trasporta («la regola va a DB») | vista presidio che ricopia i tre addendi: due sedi, divergenza al primo addendo — il caso che «nessun test vede» |
| — | B6 chiusa per decisione dell'11-09 | — |

**Domande aperte: nessuna.** La #14 resta fuori, com'era.

---

## 9. Documentazione da toccare

- [analisi-osservabilita-log.md](analisi-osservabilita-log.md): #8 decisa (fatto,
  ⏱️ 18-09), B6 superata (fatto); a fine pezzi: B, C, R-6 ✅ e il piano a sette su
  sette.
- `docs/it/dev/api.md` §Endpoint attivi: `processi/presidi/conteggi/`,
  `vendite/giornale/`, `amm-software/error-log/`.
- `docs/it/dev/backend/catalogo-building-block-backend.md`: `_testata_presidi`,
  `list_error_logs`, il terzo lettore del giornale.
- `docs/it/dev/frontend/catalogo-building-block-frontend.md`:
  `usePresidiPolling` + `statoPallino`; `frontend-standards.md` §Topbar (che oggi
  dice ancora «badge ruolo ADMIN/OPERATIVO»: si aggiorna a ciò che c'è).
- `docs/it/guide/Messaggi-di-Errore-e-Generazione-Log.md` §Consultare i log e
  `docs/it/guide/audit-e-tracciabilita.md`: le tre superfici nuove.
- `docs/it/backend/.../manual/`: `api_giornale.md`, `api_error_log.md`,
  `api_presidi_conteggi.md` (struttura standard).

---

## 10. Registro

| Quando | Cosa |
| --- | --- |
| 2026-09-18 | Scritto. #8 decisa da Tid a chat (topbar, accanto al badge code). B6 riconosciuta chiusa dal piano «endpoint senza porta» dell'11-09. Prerequisiti DB in brief separato. Nessun codice. |
| 2026-09-18 sera | ✅ **D-V1 confermata da Tid** («la regola va a DB»): il pezzo V è definitivo, non più condizionato. |
