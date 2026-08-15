# Brief DB — Lista configurabile + estensione modello `vendite.ordini` (DB-ORD)

> **Branch**: `dev/db-tid`. **Destinatario**: team DB.
> **Natura**: brief DB derivato dall'analisi [analisi-ordini-vendita.md](analisi-ordini-vendita.md)
> (l'analisi è l'input; questo brief ne è il **changeset eseguibile** lato DB —
> memoria `feedback_db_actions_passaggio_team`). Precede l'**analisi critica di
> verifica** (§1, condotta sul DDL/trigger/seed reali il 2026-06-03): l'analisi è
> solida ma ha **tre punti da correggere** prima di toccare il DB.
> **Template DB 1:1**: [db-brief-lista-preventivi-offerte.md](./db-brief-lista-preventivi-offerte.md)
> (DEF-8, atterrato 2026-06-03) + [refactor-lista-contratti.md](./refactor-lista-contratti.md).
> **Vincolo**: ZeroErp NON in produzione → breaking ammessi, ma la consegna DB
> resta **non-breaking** verso il BE (BE/FE partono a DB consegnato — memoria
> `feedback_be_fe_attende_prerequisiti_db`).

---

## ✅ STATO: DB ATTERRATO + pgTAP VERDI (2026-06-03)

Lotto DB-ORD (changeset `20260603-11..15`) applicato su `dev/db-tid`, pgTAP verdi
(`test-lista-ordini-seed` 17/17, `test-ordini-modello-ext` 11/11). `changelog-autogen.yaml`
rigenerato (`--strict`, zero collisioni). **Doc manuale aggiornata**:
`manual/vw_ordini_lista.md` (nuova) + `manual/ordini.md` (agente E + documento origine A1
+ FK) + `manual/ordini_righe.md` (bug check risolto + co-presenza).

**Resta aperto (NON DB)**: BE/FE scheletro (analisi §5/§6) + conversione upstream
(§7.4). Auto-gen `tabelle/`/`views/` dbzero da rigenerare con `gen_db_docs.py` (wiring
include manuale + refresh campi/vincoli dal DB live).

---

## 0. TL;DR — cosa esegue questo lotto

Il modello `vendite.ordini` è **sostanzialmente completo** (testata + righe +
componenti BoM + note + push commessa + RLS). Per accendere la **lista DEF-8** e lo
scheletro applicativo mancano pochi artefatti DB:

| Artefatto | Tipo | Stato |
| --- | --- | --- |
| Vista `vendite.vw_ordini_lista` | NUOVA (`20_code/vendite`) | da creare |
| `ui.lista_definizione` id=7 + catalogo (lista_colonna) + preset + `priorita` | seed (CSV + changelog) | da appendere |
| **FIX check** `chk_ordini_v_r_qta_pos` → `quantita > 0` | ALTER (`00_schema/vendite`) | bug confermato |
| **DDL E** — `agente_soggetto_ruolo_id` | ALTER additivo (`00_schema/vendite`) | ratificato |
| **DDL A** — link documento di origine (`documento_origine_tipo` + `_id`) | ALTER additivo (`00_schema/vendite`) | **ratificato A1** (Tid, 2026-06-03) |
| pgTAP seed lista + modello esteso (check + E + A) | test | da creare |

> **Decisione A — ratificata A1 (Tid, 2026-06-03)**: link origine via **FK tipizzata
> dedicata, SENZA UNIQUE** → un preventivo/offerta può generare **più ordini**. La
> verifica (§1.A) ha scartato «A2» (riuso `sorgente_*`) perché collide con l'UNIQUE
> `uq_ordini_v_sorgente_fk` (imporrebbe 1 origine → 1 ordine) e sovraccarica la
> semantica `scope` di `config.sorgenti`. A1 è additivo e a costo equivalente → **entra
> in questo lotto** insieme a E. La **conversione** preventivo/offerta→ordine che
> *usa* questa colonna resta lo step successivo (analisi §7.4); qui si predispone solo
> la colonna + la sua esposizione in vista.

---

## 1. Analisi critica — verifiche su DDL/trigger/seed reali (2026-06-03)

L'analisi è stata verificata punto per punto contro le migrazioni, la doc
auto-generata e i seed. **Confermata nella sostanza**; tre punti vanno corretti.

### 1.✅ Confermato (l'analisi ha ragione)
- **Bug check riga**: `chk_ordini_v_r_qta_pos` controlla davvero `prezzo_unitario >= 0`
  invece di `quantita > 0` (origine baseline `00_bootstrap/20250907-02-create_vendite_ordini_righe`).
  Esiste già un check gemello corretto sul prezzo (`chk_ordini_v_r_prezzo_pos`,
  stessa espressione) → il guard sulla **quantità base** manca del tutto. **Fix in §5.**
- **`numero` valorizzato all'INSERT** (anche in BOZZA), non «durante la conferma»:
  un trigger `BEFORE INSERT` lo genera via `script.fn_generate_codice('ordine')` se
  NULL → decisione §8.1 dell'analisi («`numero` nudo, niente fallback») **valida**.
  L'indice `uq_ordini_v_anno_serie_numero` è parziale su `numero IS NOT NULL`.
- **Testata snella confermata**: colonne trasporto (`causale_trasporto_id`,
  `aspetto_bene_id`, `vettore_soggetto_ruolo_id`, `modalita_addebito_trasporto_id`)
  e `giorni_pagamento`/`fine_mese` **droppate** da `20251027-01-ordini-refactor-testata`.
  Nessun listino in testata. Restano `modalita_pagamento_id`, `termine_pagamento_id`,
  `valuta_id`, `tasso_cambio` (default 1), `fatturazione_trigger` (default `CONFERMATO`,
  ereditato da BA), `canale_origine` (default `ADMIN`), `utility_id`,
  `emittente_fiscale_id` NOT NULL.
- **Building block a valle pronti**: `fn_ordine_riga_componenti_init`/`_preview`
  (BoM), `fn_list_ordini_da_pushare(p_competenza_mese, p_billing_account_id, p_limit,
  p_ordine_id)` con **push singolo** via `p_ordine_id`, `HandlerOrdini` (sorgente
  `ORDINE_VENDITA`) in [commesse_source_handlers.py:509](../../../../backend/apps/vendite/services/commesse_source_handlers.py).
- **Righe**: `qta_operativa`/`uom_operativa_id`/`quantita` presenti; co-presenza UoM
  oggi garantita dal trigger `trgfn_qta_from_operativa`, **non** da un CHECK.
- **`sorgente_tipo_id`/`sorgente_uid` + UQ** presenti sia in testata
  (`uq_ordini_v_sorgente_fk`) sia su righe (`uq_ordini_righe_v_sorgente_fk`).

### 1.🔴 A — Link documento di origine: **A2 NON era fattibile come raccomandato → A1**

La prima stesura dell'analisi raccomandava **A2** = riuso di
`sorgente_tipo_id`/`sorgente_uid` in testata come link interno al preventivo/offerta
d'origine, perché «simmetrico con le righe». **La verifica DDL ha smentito la
fattibilità** su due fronti (l'analisi §1.bis è stata poi corretta a A1):

1. **Collisione UNIQUE.** `uq_ordini_v_sorgente_fk` è
   `UNIQUE (sorgente_tipo_id, sorgente_uid) WHERE sorgente_tipo_id IS NOT NULL`.
   Se `sorgente_uid` = uid del preventivo e `sorgente_tipo_id` = PREVENTIVO, allora
   **un preventivo può generare al massimo UN ordine**: il secondo ordine dallo
   stesso preventivo viola il vincolo. Questa è una **regola di dominio implicita
   non dichiarata** — va decisa, non subìta. In pratica commerciale è comune che un
   preventivo accettato generi **più ordini** (consegne parziali, riordini).
2. **Sovraccarico semantico.** `config.sorgenti` esiste già con `PREVENTIVO`(id=2,
   `scope=PUSH_COMMESSA`) e `OFFERTA_COMMERCIALE`(id=14, `scope=PUSH_CONTRATTO`): il
   campo `scope` qui significa «questa sorgente **pusha** verso commessa/contratto»
   (registry handler), non «questo documento è **l'origine** di quell'ordine».
   Riusare quegli id per il link-origine **confonde due concetti diversi** sulla
   stessa colonna.

> **Conseguenza**: la simmetria testata/riga invocata dall'analisi è apparente —
> sulle **righe** `sorgente_*` serve all'**idempotenza import** (una riga-preventivo
> → al più una riga-ordine), che è proprio ciò che in testata diventa il limite
> «1 preventivo → 1 ordine». Sono lo stesso meccanismo con conseguenze opposte.

**Decisione ratificata (Tid, 2026-06-03): A1 — FK tipizzata dedicata**
(`documento_origine_tipo` lookup/enum interno + `documento_origine_id bigint`,
**senza** UNIQUE), che modella esplicitamente la provenienza e **non** impone il
vincolo 1:1 (memoria `feedback_no_quick_fix_soluzione_assoluta` +
`feedback_simmetria_modello_no_meta_scope`). La simmetria «giusta» non è col
meccanismo import delle righe ma con un link di provenienza tipizzato. **A1 ≠ più
lavoro**: due colonne nullable + un piccolo vocabolario tipi, niente seed
`config.sorgenti` da reinterpretare.

→ **A1 entra in questo lotto** (additivo, costo equivalente a E): DDL colonne + vista
che le espone (§3) + colonna catalogo (§4). La **conversione** che le valorizza
(`crea_ordine_da_preventivo`/`_da_offerta`) resta lo step successivo allo scheletro
(analisi §7.4) — qui non si chiude la porta, si predispone soltanto.

### 1.🟡 B — `manual/ordini.md` risulta GIÀ allineato (§1.ter dell'analisi è stale)

L'analisi §1.ter prescrive di correggere tre punti «stale» in
[manual/ordini.md](../../dbzero/vendite/manual/ordini.md). La verifica del file
**reale** mostra che è **già aggiornato**: la numerazione è descritta «già
all'INSERT, anche in BOZZA», le colonne trasporto sono indicate come «rimosse» dal
refactor `20251027-01`, e `giorni_pagamento`/`fine_mese` come «non più in testata».
→ **Non rifare la correzione prosa**: verificare e basta. Resta valido solo il punto
su [manual/ordini_righe.md](../../dbzero/vendite/manual/ordini_righe.md), che
**correttamente** documenta il bug check e raccomanda il CHECK di co-presenza UoM
(la correzione è il DDL §5, non la prosa).

### 1.🟡 C — Note di naming/seed (rettifiche post-verifica DDL tabella)
- **Trigger gen codice** (rettifica): la tabella reale ha **entrambi** i trigger —
  `trg_ordini_a10_gen_codice_ins_upd` → `trgfn_ordini_gen_codice()` (genera `numero`
  via `fn_generate_codice` se NULL) e `trg_ordini_normalize_ins_upd` →
  `trgfn_ordini_normalize()` (`20260225-34`, eredita `fatturazione_trigger` da
  `billing_account.fatturazione_ordini`). Quindi **l'analisi era corretta** a citare
  `trgfn_ordini_gen_codice` per la numerazione; nessuna ambiguità da risolvere.
- **RLS**: le 3 policy esistono; RLS è `ENABLE` (Ondata 2, `20260601-39`), **non
  `FORCE`**. La vista usa `security_invoker=on` → le policy delle tabelle base si
  applicano comunque.
- **`tipo_dato='integer'` NON esiste** nell'ENUM `ui.tipo_dato`
  (`{string,numeric,date,datetime,boolean,enum}`): `anno` nel catalogo §4 è `numeric`
  (recepito; stesso fix già fatto per `rev`/`revisione_numero`).
- **RLS**: le 3 policy (`rls_ordini_ef_whitelist`/`_cliente_ownership`/`_shop`)
  esistono; RLS è `ENABLE` (Ondata 2, `20260601-39`), **non `FORCE`**. L'analisi dice
  «già attiva»: vero in lettura. La vista lista usa `security_invoker=on` → le policy
  delle tabelle base si applicano comunque.
- **`tipo_dato='integer'` NON esiste** nell'ENUM `ui.tipo_dato`
  (`{string,numeric,date,datetime,boolean,enum}`): il catalogo §4 dell'analisi marca
  `anno` come `integer` → **va `numeric`** (stesso errore già corretto per
  `rev`/`revisione_numero` nel brief preventivi/offerte). **Recepito in §4.**

---

## 2. Lotto changeset (numerazione globale per data — memoria `feedback_liquibase_numerazione_globale_per_data`)

Il 2026-06-03 i NN `09`/`10` sono stati occupati dai **drop differiti** delle viste
preventivi/offerte (`20260603-09-drop-vw-preventivi-list`, `…-10-drop-vw-offerte-
commerciali-list`), quindi il max NN reale è **`10`**. Il lotto DB-ORD usa il blocco
contiguo **`11`–`15`** (in ordine di fase). Stato catalogo `ui.*`: `lista_definizione`
max id=**6**, `lista_colonna` max id=**103**, `lista_preset` max id=**6**,
`lista_preset_colonna` max id=**70**.

| File | Fase | Cosa |
| --- | --- | --- |
| `20260603-11-fix-chk-ordini-righe-qta-pos-mctit.yaml` | `00_schema/vendite` | DROP+ADD `chk_ordini_v_r_qta_pos` → `quantita > 0` + CHECK co-presenza UoM (§5) |
| `20260603-12-alter-ordini-add-agente-sr-mctit.yaml` | `00_schema/vendite` | DDL **E** `agente_soggetto_ruolo_id bigint NULL` FK `soggetti_ruoli` |
| `20260603-13-alter-ordini-add-documento-origine-mctit.yaml` | `00_schema/vendite` | DDL **A1** `documento_origine_tipo varchar` + `documento_origine_id bigint`, 2 CHECK, **SENZA UNIQUE** |
| `20260603-14-create-vw-ordini-lista-mctit.yaml` | `20_code/vendite` | vista canonica `vw_ordini_lista` (`security_invoker=on`, self-contained; espone agente + origine) |
| `20260603-15-seed-ui-lista-colonna-priorita-ordini-mctit.yaml` | `80_data/changelog` | UPDATE `priorita` dominio `vendite.ordini` (pattern `20260603-07/08`) |
| append `lista_definizione.csv` | `80_data/sql/ui` | id=**7** `vendite.ordini` → `vw_ordini_lista` |
| append `lista_colonna.csv` | `80_data/sql/ui` | id **104–127** (24 colonne, §4) |
| append `lista_preset.csv` | `80_data/sql/ui` | id=**7** `ordini_default` |
| append `lista_preset_colonna.csv` | `80_data/sql/ui` | id **71–81** (11 righe: 10 visibili + `stato_codice_interno` nascosta) |
| `db/pgtap/ui/test-lista-ordini-seed.sql` | pgtap | seed lista (17 test) |
| `db/pgtap/vendite/test-ordini-modello-ext.sql` | pgtap | fix check + E + A1 + co-presenza (11 test) |

> **A1 = un solo changeset** (`-13`): nessun vocabolario/lookup separato. Il tipo usa
> il pattern `varchar + CHECK IN (...)` **già presente nella stessa tabella** per
> `fatturazione_trigger` (regola del 2) → niente enum/tabella nuova. **5 changeset**
> totali (11–15) + 4 append CSV + 2 pgTAP. I changeset `00_schema`/`20_code` sono
> registrati in `changelog-autogen.yaml` (rigenerato con `gen_master_autogen.py
> --strict`, zero collisioni); il seed `priorita` (`80_data`) entra via `includeAll`.

**Ordinamento vincolato** (come brief preventivi/offerte): la **vista** (20_code) è
applicata prima del seed `lista_definizione` (80_data) → soddisfa il trigger
`trg_ui_lista_definizione_a10_valida_vista_sql_ins_upd` (la vista deve esistere). Il
seed `priorita` (file `…-13-…`) ordina **dopo** il loader `lista_colonna`
(`20260507-07…`) per nome file. **Nessun nuovo loader CSV**: i loader esistenti sono
`runOnChange:true` + `loadUpdateData` (UPSERT su PK) → si appendono solo righe.
Resync sequenze IDENTITY `ui.*` (`20260602-17`, `runAlways`) si riallinea da sé.

---

## 3. Vista `vendite.vw_ordini_lista` (NUOVA)

Non esiste alcuna vista lista ordini → si crea **da zero**, canonica e
**self-contained** (template diretto: `vw_offerte_commerciali_lista`,
`20260603-06` — anch'essa self-contained, perché ordini non ha una vista
intermedia tipo `vw_preventivi`). Vincoli: `WITH (security_invoker = on)`, nomi
**canonici** combacianti col `campo_sorgente` del catalogo (anti-typo, trigger
`trg_ui_lista_colonna_a10_valida_campo_sorgente`), `sensibile=false` su tutte.

**Più semplice di preventivi/offerte**: niente `rev`/storico revisioni (no
`is_attiva`/`has_next_revisione`), niente listino in testata, niente `is_scaduta`
(concetto offerta-specifico).

Colonne esposte:
- `ragione_sociale_completa`, `id_fiscale_univoco_cf_piva` (cliente via
  `istanze_utilities`→`soggetti`, valorizzato anche per prospect — stessa logica
  delle altre liste vendite; memoria `feedback_display_fields_backend`)
- `ba_codice` (alias legittimo, eccezione al «no alias `ba_*`»)
- `stato_descrizione`, `stato_codice_interno` (severity Tag FE; `ordinabile=f`,
  `ricercabile_full=f`)
- `numero`, `serie`, `anno`, `data`, `totale_doc`, `imponibile_tot`, `iva_tot`,
  `sconto_tot`, `utility_codice`, `utility_descrizione`, `fatturazione_trigger`,
  `canale_origine`, `modalita_pagamento_codice`, `termine_pagamento_codice`,
  `valuta_codice`, `emittente_fiscale_id`, `emittente_fiscale_codice`,
  `agente_denominazione` (E — via `soggetti_ruoli`→`soggetti`),
  `documento_origine_tipo`, `documento_origine_codice` (A — provenienza upstream,
  es. `PREVENTIVO · P-2026/123`), `data_insert`, `billing_account_id`,
  `soggetto_ruolo_id`, `id`, `uid`
- `numero` **nudo** (sempre valorizzato dal trigger gen codice, anche in BOZZA —
  decisione §8.1; niente `numero_display`).

> **A — risoluzione polimorfa** (`documento_origine_codice`): il link è tipizzato
> (`documento_origine_tipo` ∈ {PREVENTIVO, OFFERTA}) + `documento_origine_id`, quindi
> il codice leggibile si risolve **per tipo** — due `LEFT JOIN` (preventivi / offerte)
> + `CASE`/`COALESCE`. Forma esatta a scelta del team DB; entrambe le colonne sono
> NULL quando l'ordine nasce diretto (non da upstream).

---

## 4. Catalogo colonne (`lista_id=7`) — recepiti i fix §1.🟡C

> `anno` → **`numeric`** (non `integer`, non esiste nell'ENUM). `agente` (E) e
> `documento_origine` (A1) entrano **entrambi** in questo lotto (extra opt-in).

**Preset (visibili) — preset_colonna id 71–80:**

| ord | codice | campo_sorgente | tipo_colonna | tipo_dato | formato | priorita | gruppo |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | numero | numero | identificatore | string | — | 100 | Identificazione |
| 20 | data | data | informazione | date | date_short | 60 | Identificazione |
| 30 | ragione_sociale_completa | ragione_sociale_completa | informazione | string | — | 95 | Cliente |
| 40 | ba_codice | ba_codice | informazione | string | — | 40 | Cliente |
| 50 | id_fiscale | id_fiscale_univoco_cf_piva | informazione | string | — | 75 | Cliente |
| 60 | utility_codice | utility_codice | informazione | string | — | 70 | Fornitura |
| 70 | totale_doc | totale_doc | informazione | numeric | currency_eur | 80 | Importi |
| 80 | fatturazione_trigger | fatturazione_trigger | informazione | string | — | 30 | Ciclo vita |
| 90 | stato | stato_descrizione | informazione | string | — | 90 | Stato |
| 100 | azioni | (NULL) | azione | string | — | 100 | — |

**Tecnica nascosta (preset ✗):**

| ord | codice | campo_sorgente | note |
| --- | --- | --- | --- |
| 110 | stato_codice_interno | stato_codice_interno | severity Tag; `ordinabile=f`, `ricercabile_full=f` |

**Extra opt-in (`visibile=false`):**

| ord | codice | campo_sorgente | tipo_dato | formato | priorita | gruppo |
| --- | --- | --- | --- | --- | --- | --- |
| 120 | utility_descrizione | utility_descrizione | string | — | 10 | Fornitura |
| 130 | canale_origine | canale_origine | string | — | 12 | Ciclo vita |
| 140 | imponibile_tot | imponibile_tot | numeric | currency_eur | 18 | Importi |
| 150 | iva_tot | iva_tot | numeric | currency_eur | 18 | Importi |
| 160 | modalita_pagamento | modalita_pagamento_codice | string | — | 15 | Pagamento |
| 170 | termine_pagamento | termine_pagamento_codice | string | — | 12 | Pagamento |
| 180 | valuta | valuta_codice | string | — | 12 | Importi |
| 190 | emittente_fiscale_codice | emittente_fiscale_codice | string | — | 15 | Emittente |
| 200 | anno | anno | **numeric** | — | 10 | Identificazione |
| 210 | serie | serie | string | — | 10 | Identificazione |
| 215 | documento_origine | documento_origine_codice | string | — | 22 | Origine |
| 218 | agente | agente_denominazione | string | — | 20 | Commerciale |
| 220 | data_insert | data_insert | datetime | datetime_short | 5 | Audit |

→ **24 colonne** (id 104–127). `ricercabile_full=t` su `numero`,
`ragione_sociale_completa`, `ba_codice`, `id_fiscale` (decisione §8.5). `numero`
`fissata=true`. Le 10 colonne visibili nel preset restano invariate (origine e agente
sono extra opt-in).

**Preset `ordini_default`**: `ambito='sistema'`, `is_default=t`,
`pagina_dimensione=25`, `ordinamento_default=[{"col":"data","dir":"desc"}]`.

---

## 5. FIX check riga + (opzionale) co-presenza UoM — `00_schema/vendite`

> ⚠️ Il check originale vive in un changelog **già mergiato** (`00_bootstrap/…`):
> **non modificarlo** (memoria regola «mai toccare changelog pushati»). Nuovo
> changeset con DROP+ADD.

```sql
ALTER TABLE vendite.ordini_righe DROP CONSTRAINT IF EXISTS chk_ordini_v_r_qta_pos;
ALTER TABLE vendite.ordini_righe ADD  CONSTRAINT chk_ordini_v_r_qta_pos CHECK (quantita > 0);
-- (opzionale, raccomandato da manual/ordini_righe.md — additivo, low-risk):
-- ALTER TABLE vendite.ordini_righe ADD CONSTRAINT chk_ordini_v_r_uom_qta_operativa_copresenza
--   CHECK ((uom_operativa_id IS NULL) = (qta_operativa IS NULL));
```

- **Precondizione dati**: prima di aggiungere `quantita > 0`, verificare assenza di
  righe `quantita = 0`/`< 0` (in dev correggere/cancellare il dato a mano è più
  veloce di un fix software — memoria `feedback_no_quick_fix_soluzione_assoluta` /
  Workflow Safety AGENTS.md). Stessa precondizione per il co-presenza.
- L'**omaggio** resta esprimibile: `quantita > 0` + `prezzo_unitario = 0` (coperto da
  `chk_ordini_v_r_prezzo_pos`). Nessun conflitto.
- Il prezzo era già coperto dal check gemello: il fix **aggiunge** il guard mancante
  sulla quantità, non lo sposta.

---

## 6. DDL E — agente/venditore (ratificato) — `00_schema/vendite`

```sql
ALTER TABLE vendite.ordini
  ADD COLUMN agente_soggetto_ruolo_id bigint NULL
    REFERENCES anagrafiche.soggetti_ruoli (id);
```

- Nullable (non tutti gli ordini hanno agente) → **nessun backfill**, nessun impatto
  su trigger/RLS esistenti (additivo).
- Coerenza FK con la testata: applicare lo stesso **guard `child_requires_active_parent`**
  usato dagli altri FK soggetto-ruolo della testata (verificare il pattern esistente,
  non reinventarlo — regola del 2). Indice FK: **non** crearlo a mano →
  `dbops.apply_fk_index_policy()` (`90_end`); se serve, registrarlo in
  `dbops.fk_index_policy`.
- Display in vista: `agente_denominazione` (via SR→soggetto).

---

## 6.A DDL A — link documento di origine (ratificato A1) — `00_schema/vendite`

Decisione di design (regola del 2): il tipo usa il pattern **già presente in questa
tabella** per `fatturazione_trigger` (`varchar` + CHECK su vocabolario chiuso), **non**
un enum/lookup separato → A1 è **un solo changeset**, niente nuovo tipo/tabella e
**niente** riuso di `config.sorgenti` (scope `PUSH_*`, altra semantica — §1.A).

```sql
ALTER TABLE vendite.ordini
  ADD COLUMN documento_origine_tipo VARCHAR(20) NULL,
  ADD COLUMN documento_origine_id   BIGINT      NULL;
ALTER TABLE vendite.ordini
  ADD CONSTRAINT chk_ordini_documento_origine_tipo
  CHECK (documento_origine_tipo IS NULL OR documento_origine_tipo IN ('PREVENTIVO','OFFERTA'));
ALTER TABLE vendite.ordini
  ADD CONSTRAINT chk_ordini_documento_origine_copres
  CHECK ((documento_origine_tipo IS NULL) = (documento_origine_id IS NULL));
```

- **Niente UNIQUE** sul link → un preventivo/offerta può generare **più ordini**
  (regola §1.A). Entrambe nullable (ordine diretto = NULL) → nessun backfill, nessun
  impatto trigger/RLS.
- `documento_origine_id` è un riferimento **polimorfo** (preventivo *o* offerta secondo
  il tipo): niente FK fisica unica (punterebbe a due tabelle). L'integrità si garantisce
  alla **valorizzazione** (service di conversione, analisi §7.4); lo scheletro non
  valorizza mai queste colonne, quindi un guard non è urgente.
- Display in vista: `documento_origine_tipo` + `documento_origine_codice` (risoluzione
  polimorfa per tipo: `preventivi.numero` | `offerte_commerciali.codice`, §3).

---

## 7. pgTAP

**`test-lista-ordini-seed.sql`** (gemello `test-lista-contratti/preventivi/offerte-seed`):
- `vw_ordini_lista` esiste, `security_invoker=on`, espone **ogni** `campo_sorgente`
  del catalogo (incl. `stato_codice_interno`) — anti-typo gemello trigger B2;
- `lista_definizione` `vendite.ordini` attiva, `vista_sql='vw_ordini_lista'`,
  risolve via `fn_resolve_lista_config`;
- 24 colonne attive nel catalogo; preset `ordini_default` `is_default=true`,
  `ambito='sistema'`, `pagina_dimensione=25`; 10 colonne visibili nel preset;
  `numero` `fissata=true`; `priorita` di dominio applicata; **nessuna** colonna
  `sensibile=true` (no filtro SUPER_ADMIN).

**`test-ordini-modello-ext.sql`**:
- `chk_ordini_v_r_qta_pos` rifiuta `quantita = 0` e accetta `quantita > 0` con
  `prezzo_unitario = 0` (omaggio);
- (se incluso) co-presenza UoM: `(qta_operativa NULL, uom_operativa NOT NULL)`
  rifiutata;
- colonna `agente_soggetto_ruolo_id` presente, nullable, FK verso `soggetti_ruoli`;
  insert con agente valido OK, con id inesistente KO.
- **A**: colonne `documento_origine_tipo`/`documento_origine_id` presenti, nullable,
  **nessun UNIQUE** sul link; due ordini con stesso (tipo, id) origine → **entrambi
  ammessi** (regola «più ordini da una origine»); co-presenza tipo↔id (se CHECK incluso)
  rispettata.
- Fixture: pattern memoria `feedback_pgtap_patterns` (BEGIN; + CF validi fissi);
  per la testata seguire `feedback_pgtap_preventivi_fixtures` (emittente fiscale +
  iva obbligatori) — `vendite.ordini` ha `emittente_fiscale_id` NOT NULL.

---

## 8. Decisioni ratificate (Tid, 2026-06-03)

**Link documento di origine (A) → A1 ✅** (chiusa il 2026-06-03 dopo la verifica
§1.A): FK tipizzata dedicata `documento_origine_tipo` + `documento_origine_id`,
**senza** UNIQUE → un preventivo/offerta può generare **più** ordini. Scartata «A2»
(riuso `sorgente_*`): l'UQ `uq_ordini_v_sorgente_fk` imporrebbe l'1:1 e
sovraccaricherebbe lo `scope` di `config.sorgenti`. A1 entra in **questo** lotto
(§2, §6.A).

> Tutto il resto delle decisioni §8 dell'analisi (numero nudo, auto-save BOZZA, push
> singolo, `fatturazione_trigger` visibile, ricerca estesa) è **confermato dalla
> verifica** e recepito in questo brief.

---

## 9. Sequenza di sviluppo (piano)

1. **Lotto DB-ORD** (§2): fix check + E + **A1** + vista + catalogo/preset/priorita +
   pgTAP verde su `dev/db-tid`.
2. **Consegna DB** → sblocca BE/FE (memoria `feedback_be_fe_attende_prerequisiti_db`).
3. **BE scheletro** (analisi §5): `ordini_repository.py`/`ordini_service.py`/
   `views_ordini.py`+`urls_ordini.py` (clone offerte/preventivi, **niente revisioni**),
   note ordini (3 righe in `note_views.py`), export, conferma + push singolo, test
   verdi. Pricing/BoM via BB condivisi (`PricingService`, `_pricing_gate_helpers`,
   `fn_ordine_riga_componenti_*`) — **regola del 2**, mai query dirette.
4. **FE scheletro** (analisi §6): `src/vendite/ordini/` con lista **direttamente
   `<ListaConfigurabile>`** (niente grezza) + drawer + store/api + i18n; build verde.
5. **Chiusura giro** (analisi §7): conferma ordine → push → `attivita_fatturabili` →
   pipeline lotto → fattura (riuso ~90%); smoke E2E.
6. **Conversione upstream** (analisi §7.4, step successivo allo scheletro): service
   `crea_ordine_da_preventivo`/`_da_offerta` che copia testata+righe+componenti e
   **valorizza** `documento_origine_tipo`/`_id` (colonne già pronte dal lotto §2) +
   FE «genera ordine» sul documento upstream. Qui si usa A1, non si crea.

---

## 10. Stato famiglia liste/domini vendite DEF-8

| Dominio | DB lista | BE/FE | Doc |
| --- | --- | --- | --- |
| `vendite.contratti` | ✅ (`1cc906377`) | ✅ | [refactor-lista-contratti.md](./refactor-lista-contratti.md) |
| `vendite.preventivi` | ✅ 2026-06-03 | ⏳ attende | [db-brief-lista-preventivi-offerte.md](./db-brief-lista-preventivi-offerte.md) |
| `vendite.offerte` | ✅ 2026-06-03 | ⏳ attende | [db-brief-lista-preventivi-offerte.md](./db-brief-lista-preventivi-offerte.md) |
| **`vendite.ordini`** | ✅ atterrato 2026-06-03 (`20260603-11..15`) | ⏳ attende (analisi §5/§6) | [analisi-ordini-vendita.md](analisi-ordini-vendita.md) |
