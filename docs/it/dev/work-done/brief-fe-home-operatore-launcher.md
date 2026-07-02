# Brief FE — Home operatore pratiche (launcher «comincia / continua»)

> **Tipo**: brief FE (+ un prerequisito BE puro) · **Data**: 2026-07-01
> **Owner**: Tid · **Stato**: ✅ **CHIUSO 2026-07-02** (spostato in `work-done/`):
> **P1 + B1–B6 fatti** (lookup BE con `categoria` smoke-testato live; deep-link, filtro
> tipo, preset "Nuova pratica", home launcher, route/menu) **+ review critica passata**
> (§8, 2026-07-02), committato e mergiato (PR #910). La verifica in-app (acceptance §7)
> si completa in esercizio.
>
> **Origine**: voce **V11** di
> [analisi-pratiche-valutazione-stato.md](../work-in-progress/analisi-pratiche-valutazione-stato.md)
> (Home operatore / launcher, modello menu AS/400). Le decisioni di design sono
> state prese in sessione con l'owner il 2026-07-01 e **correggono** l'idea
> originale della riga V11 (vedi §2.3).
>
> **Documenti collegati**:
> [brief-fe-percorso-narrativo-operatore.md](brief-fe-percorso-narrativo-operatore.md) (V1 — il
> «racconto» che la home introduce), [Guida Gestione Pratiche](../../guide/gestione-pratiche.md).

---

## 1. Problema

Il dominio pratiche non ha una pagina d'atterraggio pensata per l'operatore: si entra
dritti nella **dashboard-lista** ([PraticheDashboard.vue](../../../../frontend/src/pratiche/views/PraticheDashboard.vue)),
che è una superficie di *consultazione/ricerca* (SearchTable + percorso), con la coda
lavoro relegata a rail collassato di lato. I due gesti che aprono la giornata
dell'operatore — **«comincia»** (avvia una nuova attività di tipo X) e **«continua»**
(riprendi il lavoro in coda) — non hanno una superficie dedicata: il primo è sepolto nel
pulsante "Nuova pratica" della toolbar, il secondo in un rail chiuso di default.

## 2. Principio e decisioni chiuse (2026-07-01)

### 2.1 La forma: due gesti affiancati

La home è **due colonne a pari dignità**: *Comincia* (tile data-driven da
`tipi_prestazione`, raggruppate per categoria) e *Continua* (la coda lavoro, riusata dal
BB esistente, come superficie protagonista — non rail). Distinta dalla dashboard-lista,
che resta il "tutte le pratiche" (consultazione/ricerca).

### 2.2 La grammatica: la home è un launcher puro

**Ogni elemento della home fa la stessa e sola cosa: deep-link alla dashboard in uno
stato preimpostato.** Nessuna azione di business vive nella home; la dashboard resta
l'unico posto dove si lavora (unico wiring di percorso/drawer — zero duplicazione).
È il modello menu AS/400: *menu → programma → il crea sta dentro il programma (F6)*.

### 2.3 La tile è un contesto, non un verbo ⚠️ correzione a V11

La riga V11 originale prevedeva «tile → crea pratica di tipo X col drawer preimpostato».
**Deciso diversamente**: il click sulla tile apre la **dashboard con il filtro tipo
prestazione attivo**; da lì il pulsante **"Nuova pratica" pre-imposta il tipo dal filtro**
(2 click invece di 1). Motivi:

- coerenza con la grammatica §2.2 (il click-coda fa già deep-link);
- prima di creare, l'operatore quasi sempre vuole vedere *se esiste già* una pratica per
  quel cliente — il create diretto favorisce doppioni;
- molte pratiche nascono **generate** (regole di generazione, cascata): la creazione
  manuale è il gesto minoritario e non merita il click principale.

Il create diretto **non si perde, si rimanda**: se l'uso mostrerà creazioni frequenti per
certi tipi, si aggiunge una micro-azione «+» sull'angolo della tile che apre il drawer
create direttamente (il drawer è già autonomo). Espansione compatibile, non cambio di
architettura (`feedback_concentrico_no_yagni`).

### 2.4 Click sulla coda dalla home

Deep-link alla dashboard con **pratica selezionata e flusso evidenziato** (percorso
caricato). Il *prendi in carico* resta disponibile anche dalla home: è un'azione della
coda (store action già esistente), non wiring nuovo.

### 2.5 Icone e raggruppamento tile

**Mappa FE `categoria → icona`** con default; nessuna dipendenza DB. `categoria` è già a
modello (`tipi_prestazione.categoria`, nullable) e già popolata nei seed
(es. `COMMERCIALE`); i tipi con categoria `NULL` finiscono in un gruppo «Altre».
Un'eventuale icona per-tipo (colonna o `meta` jsonb) si valuta solo se emergerà il
bisogno reale.

## 3. Ricognizione (fatti verificati sul codice, 2026-07-01)

| Fatto | Stato | Riferimento |
| --- | --- | --- |
| BE lista pratiche accetta `tipo_prestazione_id` | ✅ pronto | [views.py:47](../../../../backend/apps/pratiche/api/views.py#L47) |
| FE SearchTable: **filtro** per tipo prestazione | ❌ manca (la *colonna* c'è) | [PraticheSearchTable.vue:202](../../../../frontend/src/pratiche/components/PraticheSearchTable.vue#L202) |
| Pulsante "Nuova pratica" in toolbar lista | ✅ esiste | PraticheSearchTable.vue (tooltip `pratiche.nuova_pratica`) |
| `PraticheCodaLavoro` BB presentazionale (items + emit) | ✅ riusabile as-is | [PraticheCodaLavoro.vue](../../../../frontend/src/pratiche/components/PraticheCodaLavoro.vue) |
| `pratiche.tipi_prestazione` in whitelist `lookupCodici` | ✅ già whitelisted | [dbops_repository.py:108](../../../../backend/apps/core/db/dbops_repository.py#L108) |
| Il lookup espone `categoria` | ❌ contratto generico id/codice/descrizione | precedente lookup specializzato: `catalogo.unita_misura` + `tipo_uom_id` |
| Seed `tipi_prestazione.categoria` popolata | ✅ (`COMMERCIALE`) | migrations `20260608-06`, `20260422-05` |
| Menu/navigazione | ✅ FE-driven (`navigation.js`), non DB | [navigation.js:170-172](../../../../frontend/src/core/navigation.js#L170-L172) |
| `PraticaDrawer` create con `tipo_prestazione_id` nel form | ✅ preset banale | [PraticaDrawer.vue:63](../../../../frontend/src/pratiche/components/PraticaDrawer.vue#L63) |
| Permesso di creazione **per-tipo** | ❌ non esiste (permessi v3 futuri) | degrado: gate d'area (readonly pratiche) |

**→ Nessuna attività DB richiesta**: niente DDL, niente seed, niente funzioni. Tutto il
lavoro è FE + un prerequisito **BE puro** (P1, §5).

## 4. Sketch

```text
┌───────────────────────── Pratiche — Home ─────────────────────────┐
│                                                                    │
│  COMINCIA                        │  CONTINUA — Le mie attività     │
│  ─────────                       │  ───────────────────────────    │
│  Commerciale                     │  Da fare (3)                    │
│   [📄 Preventivo]                │   PRA-0000216                   │
│   [🧾 Offerta commerciale]       │    Fai il preventivo      [▶]   │
│                                  │  Da prendere (2)                │
│  Altre                           │   PRA-0000220  [Prendi]         │
│   [⚙ Approvazione prezzo]       │  Reparto (5)                    │
│                                  │   …                             │
│  ──────────────────────────      │                                 │
│  → Tutte le pratiche             │                                 │
└────────────────────────────────────────────────────────────────────┘

click tile      → dashboard con filtro tipo attivo → "Nuova pratica" già col tipo
click attività  → dashboard con pratica selezionata + flusso evidenziato + percorso
```

## 5. Deliverable

**BE (prerequisito, puro, agent-doable — nessun team DB):**

- **P1 — Lookup tipi con categoria**: lookup specializzato per
  `pratiche.tipi_prestazione` che aggiunge `categoria` al contratto generico
  id/codice/descrizione, sul pattern già esistente di `catalogo.unita_misura`
  (`_list_lookup_catalogo_unita_misura` in `dbops_repository.py`). Solo tipi attivi.

**FE:**

- **B1 — Route + view `PraticheHome.vue`**: nuova view; **la home diventa l'atterraggio
  del dominio** (`/pratiche` → home; la dashboard si sposta a `/pratiche/gestione` —
  breaking ok, non in produzione). `navigation.js`: voci `home` + `gestione` sotto il
  dominio pratiche; i18n `nav_menu.pratiche.*`.
- **B2 — Colonna *Comincia***: tile da P1, raggruppate per `categoria` (NULL → «Altre»),
  icona da mappa FE `categoria → icona` con default; click →
  `router.push` dashboard con query `tipo_prestazione_id`. Link «Tutte le pratiche»
  (dashboard senza preset). Gate: la colonna si nasconde se l'area pratiche è
  readonly per l'utente (`useReadonlyMode` / `READONLY_DOMAINS.PRATICHE`).
- **B3 — Colonna *Continua***: riuso di `PraticheCodaLavoro` **as-is** (BB
  presentazionale) in contenitore largo (non il rail collassabile); items da
  `store.loadCodaLavoro()`; `select-flusso` → deep-link dashboard con
  `pratica_id` + `flusso_id`; `prendi-in-carico` → store action esistente + reload.
  Gate: come `MieAttivitaPanel` (`isOperatore`, emittente 1-a-1); non-operatore →
  empty-state, la colonna Comincia resta.
- **B4 — Deep-link dashboard**: `PraticheDashboard` legge i query param all'ingresso:
  `tipo_prestazione_id` → applica il filtro tipo e lancia la ricerca;
  `pratica_id` (+`flusso_id`) → seleziona la pratica, evidenzia il flusso, carica il
  percorso (riusa `onCodaSelectFlusso`/`loadPercorsoPratica` esistenti).
- **B5 — Filtro tipo nella SearchTable**: `Select` tipo prestazione accanto ai filtri
  esistenti (stato/priorità/date), opzioni via `lookupCodici('pratiche.tipi_prestazione')`
  (già whitelisted), wiring su `store.filters.tipo_prestazione_id` (BE già pronto).
- **B6 — Preset "Nuova pratica" dal filtro**: se il filtro tipo è valorizzato, il drawer
  create parte con quel `tipo_prestazione_id` pre-impostato (**modificabile** — è un
  default, non un lock); filtro vuoto → comportamento attuale.

## 6. Vincoli e non-obiettivi

- **Nessuna azione di business nella home** (§2.2): niente drawer, niente percorso,
  niente completamenti montati in home. Solo navigazione + prendi-in-carico (azione
  della coda, non della home).
- **Nessuna duplicazione del wiring dashboard**: se in futuro si volesse "lavorare dalla
  home", prima si estrae il wiring come BB (regola del 2), non si copia.
- **Non è l'ispettore di configurazione** (V4/V5) e **non tocca il motore**.
- Il filtro per **permesso di creazione per-tipo** resta fuori: oggi non esiste nel
  modello permessi; si degrada al gate d'area (B2). Si riapre con permessi v3.
- La micro-azione «+» sulla tile (create diretto) è **espansione futura** (§2.3), non in
  questo brief.

## 7. Piano

Ordine pensato per consegnare valore anche prima della home:

1. **Fase 0 — P1** (BE lookup categoria). Nessun gate DB.
2. **Fase 1 — B4 + B5 + B6** (deep-link + filtro tipo + preset "Nuova"): la dashboard
   guadagna il filtro tipo e il preset **anche senza home**; il deep-link è testabile da
   URL.
3. **Fase 2 — B1 + B2 + B3** (la home vera e propria).

**Acceptance**: dall'atterraggio su `/pratiche` l'operatore, senza leggere codici né
gergo, (a) clicca «Preventivo» e si ritrova la lista filtrata sui preventivi con "Nuova
pratica" che parte già sul tipo giusto; (b) clicca un'attività della coda e si ritrova
sulla pratica giusta col percorso aperto; (c) un non-operatore vede solo la colonna
Comincia; (d) un utente readonly sull'area vede solo la colonna Continua.

---

## 8. Review critica e hardening (2026-07-02)

Review multi-angolo (8 finder + verifica) sull'intero diff non committato
(launcher + cantiere V1). Bug **corretti**:

1. **KeepAlive rompeva il deep-link** *(il bug più grave del launcher)*:
   `AppLayout` monta le view in `<KeepAlive :max="10">` con key sul *path* →
   la dashboard cached non ri-eseguiva setup/onMounted e i deep-link
   funzionavano **solo al primo mount**. Fix: applicazione dei deep-link in
   `onActivated` (idempotente, `applyTipoDeepLink`/`applyPraticaDeepLink`),
   sync del Select filtro via watch in SearchTable, ricarica percorso e coda
   ad ogni ri-attivazione, fallback percorso su remount post-eviction.
2. **Meccanismo deep-link unificato**: anche "Tutte le pratiche" usa il query
   param (`tipo_prestazione_id=0` = azzera la lente) invece di mutare lo store
   direttamente — un solo contratto, documentato in testa a `PraticheHome`.
3. **`_queryId` robusto**: param ripetuto in URL (array da vue-router) non
   produce più `NaN`-silenzioso.
4. **Home mai vuota**: testata con titolo + "Tutte le pratiche" sempre
   raggiungibile; utente readonly senza coda → empty-state esplicito
   (`home_solo_consultazione`) invece di pagina bianca.
5. **Preset "Nuova pratica" validato**: il filtro lista include gli obsoleti,
   il Select del drawer no → un preset fuori opzioni veniva salvato invisibile.
   Ora il preset si applica solo se presente nel lookup no-obsoleti.
6. **Barra contesto**: pratica deep-linkata fuori dai filtri lista → fallback
   codice `#id` (prima label vuota).

Dedup/convenzioni (regola del 2, autorizzata):
`usePrendiInCarico` composable condiviso home+dashboard; lookup specializzati
BE unificati in `_list_lookup_specializzato` config-driven
(`_LOOKUP_SPECIALIZZATE`); toggle collassa/espandi come classe condivisa
`.app-collapse-toggle` (main.css) + coppia `MANAGE_ICONS.EXPAND/COLLAPSE` sul
percorso; icone tile da `NAV_ICONS` (niente literal); dedup in-flight su
`loadCodaLavoro`; coda della home su `onActivated` (freshness sotto KeepAlive).

Fuori perimetro launcher ma corretti nella stessa review (cantiere V1):
whitelist lookup `config.esiti_flussi_pratiche` mancante (Select esiti vuoto →
completamento manuale impossibile), guard BE esiti di ramo + nuovo
[brief-db-esiti-flussi-selezionabilita.md](brief-db-esiti-flussi-selezionabilita.md)
(poi ✅ chiuso il 2026-07-02 con riuso `is_verdetto`),
fasce del Percorso (istanza aperta sempre in ADESSO), Ripeti/Apri sulla card
ADESSO — dettaglio nel brief V1 §testata.

Scelte **non** cambiate (valutate e mantenute): filtro tipo della SearchTable
con obsoleti inclusi (consultazione storica legittima → cache key separata dal
set tile/drawer); ricerca ILIKE `%term%` del lookup (catalogo piccolo; un
indice pg_trgm si valuta a catalogo cresciuto); gate `isOperatore` duplicato
con MieAttivitaPanel (estrazione in auth store rinviata: superficie condivisa
col team, serve ok esplicito).

*Brief vivo: a chiusura spostare in `work-done/` e aggiornare la riga V11 di
[analisi-pratiche-valutazione-stato.md](../work-in-progress/analisi-pratiche-valutazione-stato.md).*
