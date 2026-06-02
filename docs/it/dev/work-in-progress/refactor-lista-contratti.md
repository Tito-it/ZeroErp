# Brief DB — Lista contratti configurabile + attributo colonna `priorita` per ritiro dinamico

> **Branch**: `dev/db-tid`. **Destinatario**: team DB.
> **Natura**: brief di **logica e requisiti**, NON specifica implementativa. Qui c'è *cosa* serve e *perché*; la **strada implementativa (struttura changeset, ordine seed, nomi changelog) la sceglie il team DB**, nel rispetto del pattern liste già rodato.
> **Origine**: refactor UX "niente scrollbar orizzontale quando si apre la sidebar". Decisione Tid 2026-06-02: la riduzione dinamica delle colonne deve passare dalla migrazione della lista contratti nel sistema liste configurabili (no logica ad-hoc su `<DataTable>` grezza) + **un solo attributo nuovo** (`priorita`) nel catalogo colonne (la larghezza riusa lo standard `larghezza_default` già esistente).
> **Architettura di riferimento**: [sviluppo-personalizzazioni-liste.md](sviluppo-personalizzazioni-liste.md) (modello a 3 livelli, tabelle `ui.*`, `fn_resolve_lista_config`), [sviluppo-personalizzazioni-liste_def.md](sviluppo-personalizzazioni-liste_def.md) (DEF-8 — pattern di migrazione di una lista, precedente più vicino: **fornitori** 2026-05-24).
> **Vincolo**: ZeroErp NON in produzione → breaking change ammessi, niente migrazione dati su tabella popolata in prod. Convenzione: `[VERIFICATO]` su codice attuale; `[DA VERIFICARE SU DB]` = introspezione runtime non disponibile dall'analisi.

---

## 0. Obiettivo in una frase

Far sì che la lista contratti **riduca dinamicamente le colonne** (ritirandole in una riga di espansione, zero dati persi) quando lo spazio si stringe — tipicamente all'apertura della sidebar — invece di attivare la scrollbar orizzontale. Perché la logica viva nel layer condiviso `<ListaConfigurabile>` e non come pezza locale, la lista contratti va **portata nel sistema liste configurabili** (oggi ne è fuori), e il catalogo colonne va arricchito con una **priorità di ritiro** (la soglia di larghezza riusa lo standard `larghezza_default` esistente — niente colonna nuova per quello).

Tutta la logica FE/BE a valle (composable ResizeObserver, migrazione `ContrattiSearchTable`, serializer del nuovo attributo) **attende la consegna DB** — vedi §5.

---

## 1. Due workstream DB

| ID | Cosa | Impatta |
|---|---|---|
| **DB-A** | **Un** attributo nuovo (`priorita`) sul catalogo colonne (`ui.lista_colonna`) + esposizione nell'output di `fn_resolve_lista_config` | TUTTE le liste configurabili (trasversale) |
| **DB-B** | Migrazione della lista `vendite.contratti` nel sistema configurabile (vista + definizione + catalogo + preset) | Solo dominio vendite |

DB-A è prerequisito logico di DB-B (il seed catalogo contratti userà il nuovo attributo), ma può atterrare nello stesso lotto.

---

## 2. DB-A — Attributo colonna `priorita` per il ritiro dinamico

### 2.1 Una colonna nuova su `ui.lista_colonna`

- **`priorita`** — intero. **Semantica: peso di permanenza. Più alto = la colonna resta più a lungo; le colonne a priorità più bassa si ritirano per prime** quando lo spazio non basta. Default sensato `100`. Le colonne `tipo_colonna IN ('identificatore','azione')` e quelle `fissata` non si ritirano mai (priorità implicita infinita, indipendente dal valore). A **parità di priorità** il FE usa `ordine_default` come tiebreaker (si ritira prima la colonna più a destra). Questo rende il comportamento sensato anche per le liste esistenti che restano a default, senza obbligo di backfill differenziato.

**Niente `larghezza_min`** (decisione Tid 2026-06-02): la soglia "sotto questa larghezza la colonna si ritira" **riusa `larghezza_default`**, lo standard larghezza già esistente e seedato per le liste anagrafiche. Le colonne restano alla loro `larghezza_default` e, quando la somma non entra, si ritirano le meno prioritarie — senza compressione intermedia. Una sola colonna nuova, massimo riuso dello standard.

Nessun CHECK particolare richiesto oltre alla coerenza di dominio (`priorita >= 0`). La scelta tipo (SMALLINT vs INTEGER), default e changeset è del team DB.

### 2.2 Backfill liste esistenti — NON obbligatorio

Le 3 liste già migrate (`anagrafiche.clienti/soggetti/fornitori`) **non richiedono backfill differenziato**: con `priorita` a default + tiebreaker `ordine_default`, il ritiro parte naturalmente da destra, che è il comportamento atteso. Il backfill mirato (priorità custom) si fa solo dove serve preservare una colonna fuori ordine — per ora solo contratti (DB-B). Se il team DB preferisce popolare comunque un valore esplicito per pulizia, va bene, ma non è un requisito.

### 2.3 Esposizione nell'output di `fn_resolve_lista_config` — **necessario**

Il FE costruisce le colonne dal JSONB di `fn_resolve_lista_config` (endpoint `GET /config`), **non** dal catalogo grezzo (che è lazy, caricato solo all'apertura della modale). Perché il ritiro dinamico funzioni al primo render, il nuovo attributo deve arrivare **per ogni colonna** nell'output della fn, accanto a `ordine`/`larghezza`/`visibile`/`fissata`/`esportabile`/`tipo_colonna` (`larghezza` già c'è e fa anche da soglia di ritiro):

```jsonc
{
  "codice": "stato",
  "ordine": 12,
  "larghezza": 120,           // già presente — usata anche come soglia di ritiro
  "priorita": 90,             // ← nuovo
  "visibile": true,
  "fissata": false,
  "esportabile": true,
  "tipo_colonna": "informazione"
}
```

Il campo `priorita` diventa **parte del contratto API** (come già `esportabile`/`tipo_colonna`). Aggiornare di conseguenza i test pgTAP della fn.

> `[DA VERIFICARE SU DB]` se la fn legge il catalogo con `SELECT *` o con lista campi esplicita: nel secondo caso il nuovo campo va aggiunto anche lì.

---

## 3. DB-B — Lista contratti nel sistema configurabile

Replica del pattern DEF-8 (precedente **fornitori** 2026-05-24, il più vicino perché legge da vista anziché da repo con alias).

### 3.1 Vista sorgente `vendite.vw_contratti_lista` — **da creare (non esiste)** `[VERIFICATO]`

Oggi i dati lista vengono da una SELECT con JOIN in `ContrattiRepository.list_contratti` ([contratti_repository.py:267-377](../../../../backend/apps/vendite/db/contratti_repository.py)); **nessuna vista** `vw_contratti*` esiste. Serve una vista di **pura denormalizzazione** (JOIN + campi display), **senza** filtri/scope/paginazione: scope emittente, filtri e `LIMIT/OFFSET` restano nel repository consumer (BE, a valle). Campi e JOIN da replicare (sorgente: la SELECT del repository sopra):

**Campi richiesti nella vista** (almeno questi — superset ammesso):

| Campo vista | Sorgente | Note |
|---|---|---|
| `id`, `uid`, `numero` | `contratti` | identificativi |
| `billing_account_id`, `ba_codice` | `contratti` / `billing_account.codice` | |
| `ragione_sociale_completa` | `vw_soggetti_ruoli_dettaglio.ragione_sociale_completa` (BA → soggetto cliente) | **nome cliente** — la vista espone il campo col nome sorgente, **senza alias `ba_*`**, identico a `vw_fornitori_dettaglio` (vedi §3.4) |
| `id_fiscale_univoco_cf_piva` | `vw_soggetti_ruoli_dettaglio.id_fiscale_univoco_cf_piva` | **colonna unificata CF/P.IVA** — nome sorgente senza alias, identico a fornitori/soggetti (vedi §3.4) |
| `emittente_fiscale_id`, `emittente_fiscale_codice`, `emittente_fiscale_descrizione` | `contratti` / `emittenti_fiscali` / soggetto EF | extra opt-in |
| `utility_id`, `utility_codice`, `utility_descrizione` | `contratti` / `config.utilities` | |
| `ambito` | `contratti` | enum COMMODITY/COMMERCIO |
| `data`, `valido_dal`, `valido_al` | `contratti` | date |
| `stato_doc_contratto_id`, `stato_codice`, `stato_descrizione` | `contratti` / `config.stati_doc_contratti` | `stato_codice` = `codice_interno` (per severity Tag FE) |
| `listino_id`, `listino_codice`, `listino_descrizione` | `contratti` / `vendite.listini` | LEFT (NULL = senza_listino) |
| `listino_versione_id`, `listino_versione_codice` | `contratti` / `listini_versioni` | extra opt-in |
| `tipo_variazione_globale`, `valore_variazione_globale` | `contratti` | extra opt-in |
| `categoria_cliente_id_snapshot`, `categoria_cliente_snapshot_codice`, `categoria_cliente_snapshot_descrizione` | `contratti` / `categorie_clienti` | snapshot |
| `valuta_id`, `valuta_codice`, `valuta_descrizione` | `contratti` / `config.valute` | extra opt-in |
| `data_insert`, `user_insert`, `data_update`, `user_update` | `contratti` | audit |

JOIN esatti già noti (riportati nel repository sopra). `parent_contratto_id` e `meta` non servono in lista.

> **Nota forward-compat RLS** (allineamento col workstream parallelo [analisi-attivazione-rls-db.md](../work-done/analisi-attivazione-rls-db.md) §8): se possibile creare la vista già con `security_invoker=on`, così è pronta per la futura RLS sulla tabella base senza essere "RLS cosmetica". Decisione finale al team DB.

### 3.2 Entry `ui.lista_definizione`

Una riga (seed CSV, pattern fornitori):

```
codice='vendite.contratti', descrizione='Contratti', schema_dati='vendite',
vista_sql='vw_contratti_lista', attivo=true
```

Il trigger `valida_vista_sql` impone che la vista esista già al momento dell'INSERT → la vista (§3.1) va nel changeset **prima** del seed definizione.

### 3.3 Catalogo colonne `ui.lista_colonna` + preset di sistema

Proposta di catalogo in §4 (con `priorita` valorizzata; `larghezza_default` come standard). Da seedare come il pattern fornitori:

- `ui.lista_colonna` — tutte le colonne del catalogo (visibili nel preset + extra opt-in).
- `ui.lista_preset` — preset `contratti_default`, `ambito='sistema'`, `is_default=true`, `pagina_dimensione=25`, `ordinamento_default` = `[{"col":"data","dir":"desc"}]` (o `numero` desc — decisione di dominio, propongo `data` desc).
- `ui.lista_preset_colonna` — le colonne visibili di default (vedi colonna "Preset" in §4); le extra restano nel catalogo con `visibile=false` (pool attivabile dall'utente).

### 3.4 Lezioni DEF-8 da applicare da subito

Dalle note smoke soggetti/fornitori ([_def.md §DEF-8](sviluppo-personalizzazioni-liste_def.md)):

1. **Nomi campo cliente / id.fiscale — copiati ALLA LETTERA da fornitori** (è il punto che si sbaglia ogni volta). Righe seed di riferimento `ui.lista_colonna` per `anagrafiche.fornitori` (`lista_id=3`):
   - cliente → `codice='ragione_sociale_completa'`, `campo_sorgente='ragione_sociale_completa'`, `tipo_colonna='informazione'`
   - id.fiscale → `codice='id_fiscale'`, `campo_sorgente='id_fiscale_univoco_cf_piva'`, `tipo_colonna='informazione'`
   - stato → `codice='stato'`, `campo_sorgente='stato_descrizione'`

   La vista `vw_contratti_lista` deve quindi esporre le colonne col **nome sorgente senza alias** (`ragione_sociale_completa`, `id_fiscale_univoco_cf_piva`, `stato_descrizione`), NON con alias `ba_ragione_sociale`/`id_fiscale`. Il `campo_sorgente` del catalogo è validato contro la vista dal trigger B2: se i nomi non combaciano, il seed fallisce.
2. **`sensibile=false` ovunque**: `fn_resolve_lista_config` filtra fuori le colonne `sensibile=true` senza grant esplicito **anche per SUPER_ADMIN**. Nessuna colonna contratti richiede restrizione reale per profilo in questa fase → tutte `sensibile=false`. (Se in futuro servirà nascondere p.es. `valore_variazione_globale` a certi profili, si seederà il grant insieme al flag.)
3. **`campo_sorgente` validato contro la vista**: ogni `campo_sorgente` del catalogo deve esistere come colonna di `vw_contratti_lista` (trigger B2). Allineare i nomi.

---

## 4. Proposta catalogo colonne contratti

> Proposta di dominio — il team DB la ratifica/aggiusta.
>
> **⚠️ Due assi DISTINTI, non confonderli:**
> - **`ordine_default`** = ordine visivo. Qui è **identico alla lista contratti attuale e funzionante** (numero, cliente, codice, id.fiscale, utility, ambito, cat.cliente, listini, valido dal, valido al, data, stato, + azioni). **NON riordinare**: ogni refactor di questo tipo tende a perdere/spostare colonne, qui si preserva 1:1 ciò che esiste.
> - **`priorita`** = peso di **ritiro dinamico** (più alto = si ritira per ultima). È indipendente dall'ordine: `stato` resta in fondo come ora (ordine 12) ma ha priorità alta (non sparisce).
>
> `largh_def` = colonna `larghezza_default` **già esistente** (lo standard larghezza delle liste anagrafiche): fa sia da larghezza a video sia da soglia di ritiro. "Preset" = visibile di default nel preset di sistema (✓) o solo nel pool attivabile (—).

**Set attuale da preservare: 12 colonne + colonna azioni (che ospita 3 azioni di riga in `RowActionsMenu`).**

| ordine | codice | campo_sorgente | tipo_colonna | tipo_dato | formato | largh_def | priorita | Preset | gruppo |
|---|---|---|---|---|---|---|---|---|---|
| 1  | numero | numero | identificatore | string | — | 140 | (max impl.) | ✓ | Identificazione |
| 2  | ragione_sociale_completa | ragione_sociale_completa | informazione | string | — | 220 | 95 | ✓ | Cliente |
| 3  | ba_codice | ba_codice | informazione | string | — | 120 | 40 | ✓ | Cliente |
| 4  | id_fiscale | id_fiscale_univoco_cf_piva | informazione | string | — | 140 | 75 | ✓ | Cliente |
| 5  | utility_codice | utility_codice | informazione | string | — | 100 | 70 | ✓ | Fornitura |
| 6  | ambito | ambito | informazione | string | — | 120 | 50 | ✓ | Fornitura |
| 7  | categoria_cliente_snapshot | categoria_cliente_snapshot_codice | informazione | string | — | 120 | 30 | ✓ | Cliente |
| 8  | listino_codice | listino_codice | informazione | string | — | 160 | 45 | ✓ | Pricing |
| 9  | valido_dal | valido_dal | informazione | date | date_short | 110 | 65 | ✓ | Validità |
| 10 | valido_al | valido_al | informazione | date | date_short | 110 | 60 | ✓ | Validità |
| 11 | data | data | informazione | date | date_short | 110 | 25 | ✓ | Identificazione |
| 12 | stato | stato_descrizione | informazione | string | — | 120 | 90 | ✓ | Stato |
| 13 | azioni | (NULL) | azione | string | — | 60 | (max impl.) | ✓ (3 azioni) | — |

Colonne **extra opt-in** (nel catalogo ma `visibile=false` nel preset → l'utente le attiva dalla modale; `ordine_default` ≥ 20 per stare dopo le visibili):

| ordine | codice | campo_sorgente | tipo_colonna | tipo_dato | formato | largh_def | priorita | gruppo |
|---|---|---|---|---|---|---|---|---|
| 20 | emittente_fiscale_codice | emittente_fiscale_codice | informazione | string | — | 120 | 20 | Emittente |
| 21 | listino_versione | listino_versione_codice | informazione | string | — | 120 | 20 | Pricing |
| 22 | tipo_variazione_globale | tipo_variazione_globale | informazione | string | — | 130 | 15 | Pricing |
| 23 | valore_variazione_globale | valore_variazione_globale | informazione | numeric | — | 110 | 15 | Pricing |
| 24 | valuta | valuta_codice | informazione | string | — | 90 | 10 | Pricing |
| 25 | utility_descrizione | utility_descrizione | informazione | string | — | 160 | 10 | Fornitura |
| 26 | data_insert | data_insert | informazione | datetime | datetime_short | 150 | 5 | Audit |
| 27 | data_update | data_update | informazione | datetime | datetime_short | 150 | 5 | Audit |

**Note di dominio sul catalogo:**

- `numero` = unico `identificatore` (sempre visibile + frozen). `ragione_sociale_completa` (cliente) resta `informazione` come fornitori, ma con priorità 95 → non si ritira mai dinamicamente; resta nel preset visibile, quindi **non si perde**.
- `stato` usa `campo_sorgente='stato_descrizione'` (come fornitori) per il testo; il Tag con severity lo rende una cella custom FE che legge `stato_codice` dalla stessa riga (la vista lo espone). Stesso discorso opzionale per `ambito` (Tag COMMODITY/COMMERCIO).
- **Logica del ritiro che ne deriva** (sidebar aperta, spazio insufficiente): si ritirano per prime `data` (25) e `categoria` (30), poi `ba_codice` (40), `listino` (45), `ambito` (50)… mentre `numero`, `cliente` (95) e `stato` (90) resistono fino all'ultimo. `numero` (identificatore) e `azioni` non si ritirano mai. **L'ordine visivo resta quello attuale**: il ritiro nasconde colonne dal layout esistente, non lo riordina.

---

## 5. Cosa NON è nello scope DB (a valle, ATTENDE la consegna DB)

Per memoria `feedback_be_fe_attende_prerequisiti_db`: il BE/FE parte **solo** a DB consegnato. Lo annoto qui per chiarezza, non per chiedere lavoro al team DB:

- **BE** (`apps/ui/`): estendere `UiRepository.list_colonne_by_codice` (SELECT del nuovo campo `priorita`) + `ListaColonnaAdminService`/`ui_admin_repository` (whitelist `priorita` nel CRUD admin DEF-5b). Estendere il repository/export contratti per leggere da `vw_contratti_lista` con scope+filtri+paginazione.
- **FE** (`src/core/`): composable `useResponsiveColumns` (ResizeObserver sul container DataTable) dentro `<ListaConfigurabile>`; ritiro delle colonne sotto-soglia in una **expansion row** (`MANAGE_ICONS.EXPAND/COLLAPSE`, zero dati persi); reattivo a viewport **e** apertura sidebar. Migrazione `ContrattiSearchTable.vue` → `<ListaConfigurabile codice="vendite.contratti">` (elimina i 12 `width:Npx` inline che violano [frontend-standards §"Pattern lista"](frontend/src/...)). Azioni di riga in `RowActionsMenu`.
- **Doc**: nota in `frontend-standards` che motiva la deroga "CSS-first" per il ResizeObserver (le media query non vedono la sidebar — vedi §appendice).
- **Admin UI** (DEF-5b): aggiungere il campo `priorita` al `ListaColonnaDrawer` (sotto-tab "Layout").

---

## 6. Test pgTAP (cosa verificare, non come)

1. **DB-A**: `ui.lista_colonna` ha la colonna nuova `priorita` col default atteso; `fn_resolve_lista_config` ritorna `priorita` per ogni colonna nell'output JSONB (estendere i test esistenti della fn).
2. **DB-B**: la vista `vw_contratti_lista` esiste ed espone tutti i `campo_sorgente` del catalogo (anti-typo, gemello del check trigger B2); `lista_definizione` `vendite.contratti` risolve via `fn_resolve_lista_config` con catalogo grezzo coerente; preset di sistema `contratti_default` applicato a un utente senza preferenza ritorna le 13 colonne `Preset=✓` nell'ordine atteso; le extra opt-in compaiono con `visibile=false` (pool).
3. **Anti-regressione `sensibile`**: nessuna colonna contratti viene filtrata fuori per SUPER_ADMIN (tutte `sensibile=false`).

---

## 7. Sequenza consigliata

1. **DB-A**: ALTER `ui.lista_colonna` (+ default) → update `fn_resolve_lista_config` (output JSONB) → pgTAP fn.
2. **DB-B**: vista `vw_contratti_lista` (security_invoker se possibile) → seed `lista_definizione` → seed `lista_colonna` (con `priorita`) → seed `lista_preset` + `lista_preset_colonna` → pgTAP seed.
3. Consegna su `dev/db-tid` + nota di atterraggio.
4. **→ sblocca** BE/FE (§5), che parte dopo.

> Tutte le scelte di dominio (quali colonne core, priorità, ordinamento default) sono in §3-§4; quelle implementative (changeset, tipi, struttura seed) sono del team DB. Per ogni `[DA VERIFICARE SU DB]` il team DB ha l'ultima parola.

---

## Appendice — perché il ritiro è JS (ResizeObserver) e non CSS

Lo standard FE impone "responsive CSS-first, niente JS di detection". Qui serve una **deroga motivata** (ammessa se documentata): le media query CSS reagiscono solo a `window.innerWidth`. Ma quando l'operatore **apre la sidebar**, la finestra non cambia larghezza — si restringe solo l'area contenuto. Le media query sono quindi **cieche** a questo evento, e la scrollbar appare proprio lì. L'unico modo per reagire alla larghezza *reale del contenitore* (che cambia sia col viewport sia con la sidebar) è osservarla con un `ResizeObserver`. Non è una scelta di comodo: l'alternativa puramente-CSS per questo caso non esiste.
