# Analisi — Hardcode di valori contro la colonna `codice` (mutabile) invece di `codice_interno`

> **Tipo**: analisi/audit (DB → team DB; BE → backend agent). · **Priorità**: 🔴 alta (bug
> logici latenti, stessa famiglia del brief naming). · **Data**: 2026-06-28.
> **Origine**: dubbio di Tid durante l'esecuzione di `brief-naming-stato-codice-interno.md`.
> Quel brief copre il **mislabel di alias** (`codice_interno AS *_codice`). Questa analisi
> copre una **classe DIVERSA**: literali hardcoded confrontati **direttamente** contro la
> colonna `codice` (mutabile) — es. `WHERE s.codice = 'PREVENTIVO'` — dove la logica
> dovrebbe usare `codice_interno`.

---

## 1. La classe di bug

Le tabelle `config.stati_*` / lookup hanno **due** colonne (cfr. brief naming §1):

| Colonna | Natura | Uso corretto |
| --- | --- | --- |
| `codice_interno` | **immutabile** (lock `trgfn_lock_columns`) | **logica**: confronti, filtri, state-machine, mapping, seed-by-code |
| `codice` | **mutabile** dall'utente | solo **display** |

**Il bug**: risolvere/filtrare per `codice = 'LITERALE'` (la colonna mutabile) anziché
`codice_interno = 'LITERALE'`. Funziona *per caso* finché nessuno rinomina il `codice`;
il giorno in cui l'utente cambia (es.) `PREVENTIVO`→`PREV`, **tutta la pipeline si rompe in
silenzio** (lookup che ritorna 0 righe, stato non risolto, documento che non si genera).

**Differenza dal brief naming**: il brief sistema gli *alias bugiardi* nelle proiezioni
(`codice_interno AS stato_codice`). Qui il valore *letto* è proprio la colonna `codice` e
viene usato come **chiave di join/filtro logico** → è un bug a sé.

## 2. Metodo

Audit multi-superficie (workflow dinamico, 6 scanner + verifica avversariale per-finding):

- **DB vivo**: SQL autogen in `docs/it/dbzero/*/funzioni|views/*.md` (DDL viva, non i
  changelog storici).
- **Backend**: `backend/apps/**/*.py` (repository + service).
- **Frontend**: `frontend/src/**/*.{vue,js,ts}`.

Discriminante: per ogni hit risolto l'alias→tabella (dal `FROM`/`JOIN`) e verificata la
presenza di `codice_interno` nel doc tabella `docs/it/dbzero/*/tabelle/*.md`.

**Esclusi per regola** (generici già conformi): `dbops.fn_get_lookup_codici`,
`script.fn_get_entita_ruolo_detail`. Esclusi i campi non-config (`codice_fiscale`,
`codice_ba`, `codice_destinatario`, `codice_iva`, `codice_errore`, `codice_articolo`, `lista.codice`…).

---

## 3. 🔴 `BUG_DUAL` — tabella HA `codice_interno`, logica usa `codice` → **migrare a `codice_interno`**

Tutti confermati (alias risolto + `codice_interno` presente + uso logico). `codice_interno`
disponibile in tutte queste tabelle.

### 3a. DB — funzioni/trigger/viste (→ team DB)

| # | Oggetto (file dbzero) | Riga | Tabella | Literale(i) | Uso |
| --- | --- | --- | --- | --- | --- |
| 1 | `vendite/funzioni/fn_cambia_stato_preventivo` | 79 | `config.stati_doc_preventivi` | `p_nuovo_stato` + `DRAFT/EMESSO/ANNULLATO` | state-machine entrypoint |
| 2 | `vendite/funzioni/fn_crea_revisione_preventivo` | 94 (+110) | `config.stati_doc_preventivi` | `DRAFT` | filtro revisione |
| 3 | `vendite/funzioni/fn_list_preventivi_da_pushare` | 80 | `config.sorgenti` | `PREVENTIVO` | risoluzione sorgente |
| 4 | `vendite/funzioni/fn_list_preventivi_da_pushare` | 92 | `config.stati_doc_preventivi` | `ACCETTATO` | risoluzione stato |
| 5 | `vendite/funzioni/fn_list_ordini_da_pushare` | 32 | `config.sorgenti` | `ORDINE_VENDITA` | risoluzione sorgente |
| 6 | `vendite/funzioni/fn_list_ordini_da_pushare` | 44 | `config.stati_doc_ordini` | `CONFERMATO` | risoluzione stato |
| 7 | `vendite/funzioni/fn_list_contratti_da_pushare` | 32 | `config.sorgenti` | `CONTRATTO` | risoluzione sorgente |
| 8 | `vendite/funzioni/fn_list_contratti_da_pushare` | 44 | `config.stati_doc_contratti` | `ATTIVO` | risoluzione stato |
| 9 | `vendite/funzioni/fn_list_ddt_da_pushare` | 31 | `config.sorgenti` | `DDT_VENDITA` | risoluzione sorgente |
| 10 | `vendite/funzioni/fn_list_ddt_da_pushare` | 107 | `config.stati_doc_ddt` | `SPEDITO`,`CONSEGNATO` | filtro stato (IN) |
| 11 | `vendite/funzioni/fn_list_consumi_da_pushare` | 34 | `config.sorgenti` | `ATTIVITA_CONSUMI` | risoluzione sorgente |
| 12 | `vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa` | 71 | `config.sorgenti` | `COMMESSA` | risoluzione sorgente |
| 13 | `vendite/funzioni/trgfn_documenti_sync_canali` | 47-50 | `config.sorgenti` | `PREVENTIVO/ORDINE_VENDITA/DDT_VENDITA/CONTRATTO` | CASE mapping id |
| 14 | `vendite/funzioni/fn_set_documento_canale_stato` | 67 | `config.sorgenti` | `v_canale` + `DIRETTO` | risoluzione canale |
| 15 | `anagrafiche/funzioni/fn_lookup_utilities_per_ba` | 93 | `config.tipi_ruoli` | `EF` | JOIN logico |
| 16 | `vendite/views/vw_preventivi_pratiche` | 23 | `config.sorgenti` | `PREVENTIVO` | JOIN-filtro vista |

> **Pattern dominante**: la pipeline **commesse→push→fatturazione** risolve sorgenti e
> stati per `codice` letterale (`config.sorgenti`, `config.stati_doc_*`). È la stessa
> famiglia di funzioni `fn_list_*_da_pushare` — vanno corrette insieme. `config.sorgenti`
> compare 8 volte: è l'oggetto più esposto.

### 3b. Backend Python (→ backend agent) — ✅ FATTO (2026-06-28, 359 test verdi)

| # | File | Riga | Tabella | Literale | Fix applicato |
| --- | --- | --- | --- | --- | --- |
| 17 | `backend/apps/documenti/db/documenti_repository.py` | 1109 | `config.sorgenti` | (per `codice`) | ✅ `WHERE codice` → `codice_interno` (`get_sorgente_tipo_id_by_codice`) |
| 18 | `backend/apps/documenti/db/documenti_repository.py` | 1085 | `documenti.tipi_file_documento` | `PDF_FINALE`/`ALLEGATO` | ✅ `WHERE codice` → `codice_interno` (`get_tipo_file_documento_by_codice`) |
| 19 | `backend/apps/documenti/services/render_service.py` | 60 | `documenti.render_engine_documento` | `WEASYPRINT` | ✅ whitelist engine su `render_engine_codice_interno` (+ projection espone il campo, +`types.py`, +fixture test) |
| 20 | `backend/apps/vendite/services/approvazioni_prezzo_service.py` | 216 | `pratiche.tipi_prestazione` | `APPROVAZIONE_PREZZO` | ✅ `WHERE codice` → `codice_interno` (`_get_tipo_prestazione_id`) |
| 21 | `backend/apps/amm_software/db/amm_software_repository.py` | 1182 | `config.aree_funzionali` | `a['codice']` (dinamico) | ✅ **vedi nota — fix su `schema_db`, non `codice_interno`** |

> **Pre-check seed**: verificato che `codice_interno == codice` per tutti i literali
> coinvolti (`PREVENTIVO`, `PDF_FINALE`, `ALLEGATO`, `WEASYPRINT`, `APPROVAZIONE_PREZZO`)
> → switch a rischio zero. Test SQL-string + fixture allineati.
>
> **⚠️ #21 — RICLASSIFICATO: non era codice→codice_interno, ma "colonna sbagliata".**
> `script.fn_resolve_livello_area` matcha su **`config.aree_funzionali.schema_db`**
> (param `p_area_schema_db`, `JOIN ... af.schema_db = p_area_schema_db`), **non** su
> `codice` né `codice_interno`. Il DDL è esplicito: *«schema_db è separato da codice per
> consentire rinomina della label»*. Il codice passava `a['codice']` → funzionava **solo
> perché oggi `codice == schema_db`**; se un domani si rinomina il `codice` di un'area, la
> matrice permessi crollerebbe in silenzio. **Fix corretto sul merito**: ora passa
> `a['schema_db']` alla funzione; l'alias colonna resta `area_<codice>` (il FE mappa le
> colonne con la lista `aree`, nessun cambio FE). Aggiunti `schema_db` + `codice_interno`
> alla SELECT di `list_aree_funzionali`. `aree_funzionali` ha **tre** colonne rilevanti
> (`codice` mutabile / `codice_interno` immutabile / `schema_db` chiave tecnica della fn).

## 4. 🟡 `CANDIDATE_ADD_CI` — logica su `codice` ma la tabella **NON ha** `codice_interno`

Qui non c'è (ancora) la colonna immutabile. **Decisione richiesta**: aggiungere
`codice_interno` (coerenza col modello + difesa dai rename) **oppure** dichiarare il
`codice` chiave-di-sistema immutabile (lock esplicito) e accettarlo.

### 4a. Cluster `config.profili_accesso` — literale `SUPER_ADMIN` (🔴 security-sensitive)

Stesso literale hardcoded ripetuto su **guardie critiche** (ultimo super-admin attivo):

| File / oggetto | Riga | Tipo |
| --- | --- | --- |
| `script/funzioni/fn_check_almeno_un_super_admin_attivo` | 30 | fn guard |
| `config/funzioni/trgfn_profili_accesso_bindings_guard_ultimo_super_admin` | 40 | trigger guard |
| `anagrafiche/funzioni/trgfn_identita_digitali_guard_ultimo_super_admin` | 43 | trigger guard |
| `backend/apps/amm_software/db/amm_software_repository.py` | 280, 292, 411 | INSERT/DELETE/COUNT binding |

> `config.profili_accesso` ha **solo** `codice`. `SUPER_ADMIN` regge una catena di sicurezza:
> se rinominato, le guardie smettono di proteggere. **Raccomandazione**: aggiungere
> `codice_interno` (o un flag dedicato `is_super_admin`) e lockarlo. *Nota: il verifier ha
> classificato l'occorrenza 411 come benigna — incoerenza interna; vanno trattate come un
> unico cluster.*

### 4b. Altri singoli

| Oggetto | Riga | Tabella | Literale | Nota |
| --- | --- | --- | --- | --- |
| `config/funzioni/fn_resolve_email_account` | 77 | `config.email_account` | `SISTEMA` | fallback account di sistema (logico) |
| `backend/apps/anagrafiche/db/clienti_repository.py` | 132 | `anagrafiche.categorie_clienti` | `STANDARD` | `get_categoria_cliente_id_by_codice` (default categoria) |

> **NB su `clienti_repository.py`**: il file è anche tra quelli modificati dal brief naming
> (per `stato_codice`), ma **questa** riga (categorie, 132) è una *concern diversa* e **non**
> è coperta dal brief.

## 5. ⚪ Falsi positivi / OK (verificati, **nessuna azione**)

| Oggetto | Riga | Perché OK |
| --- | --- | --- |
| `vendite/views/vw_ordini_lista` | 45 | `oc.codice` è il codice *proprio* del documento offerta (display nel CASE origine), non un lookup config |
| `backend/.../pipeline_repository.py` | 348 | `dbops.domini_task` (infra) ha solo `codice`, chiave-di-sistema accettata |
| `backend/.../soggetti_repository.py` | 680 | usa `COALESCE(codice_interno, codice)` — preferisce già l'immutabile (fallback tollerato) |
| `backend/.../soggetti_service.py` | 605 | catena ancorata a `codice_interno` (alias `codice` fuorviante ma corretto) |
| `backend/.../clienti_repository.py` | 150 | usa `codice_interno = 'AT'` — **esempio conforme** |
| `frontend/.../PraticaDrawer.vue` | 87/97/408 | `ruolo_codice` proviene dal lookup che espone **`codice_interno`** (CL), non il mutabile |
| `frontend/.../stores/context.js` | 44/48 | `tipo_ruolo_codice` usato per icone/severity di display |

## 6. ✅ Già coperto/risolto dal brief naming (NON ripetuto qui)

Questi sono in carico a `brief-naming-stato-codice-interno.md` (✅ RISOLTO 2026-06-28:
BE/FE migrate, oggetti DB swept, guardrail CI attivo). Elencati per completezza:

**Oggetti DB (mislabel alias, swept dal brief):** `vw_contratti_lista`,
`fn_available_actions_contratto`, `vw_clienti_lista`, `vw_clienti_codice_ba`,
`vw_fornitori_dettaglio`, `fn_coda_lavoro_operatore`, `vw_istanze_utilities_dettaglio`,
`vw_indirizzi_resolved_base`, `fn_get_search_detail`, `dbops.vw_diag_v_clienti_links`.

**File BE migrati a `*_codice_interno` (uncommitted):** `clienti_repository.py`*,
`fornitori_repository.py`, `contratti_repository.py`, `contratti_service.py`,
`views_contratti.py`, `contratto_document_context_builder.py`, `types.py` (vendite/pratiche),
`vendite_tools.py`. *(\*tranne la riga 132 categorie — vedi §4b).*

**File FE migrati (uncommitted):** `ClienteDrawer.vue`, `ClientiSearchTable.vue`,
`FornitoreDrawer.vue`, `FornitoriSearchTable.vue`, `ClientiView.vue`,
`SearchDetailTable.vue`, `PraticheCodaLavoro.vue`, `ContrattiBillingAccountDrawer.vue`,
`ContrattiSearchTable.vue`, `ContrattoDrawer.vue`, `ContrattiListView.vue`.

## 7. Nota sistemica (dal sweep DB-viste)

Molte viste-lista (`vw_*_lista`, `vw_istanze_*`, ecc.) proiettano `xx.codice AS *_codice`
**senza** esporre in parallelo `*_codice_interno` (`vw_ordini_lista` invece lo fa già).
A livello DB sono display (OK), ma **post-brief** diventano superficie di rischio FE: un
consumer che confronta quei `*_codice` contro literali userebbe l'etichetta mutabile.
**Raccomandazione**: dare al FE la chiave stabile aggiungendo `*_codice_interno` a queste
viste-lista (completamento della stessa logica del brief naming §9 follow-up).

## 8. Prossimi passi proposti

1. **DB (team DB)** — ✅ FATTO (vedi §9 piano). §3a corretto e applicato: lotti A–D
   (`20260628-12..22`, 16 occorrenze) + lotto E `tipi_ruoli`/`fn_lookup_utilities_per_ba`
   (`20260629-01`, §9.5 — bug reale, +riga 84 mancata dall'audit). Anti-regressione pgTAP
   aggiunta ai test esistenti. NB: per i lotti A–D il cambio era meccanico (codice ==
   codice_interno); per il lotto E era un fix di comportamento (codice != codice_interno).
2. **BE (backend agent)** — ✅ FATTO (2026-06-28, 359 test verdi): §3b 5 punti corretti.
   NB: #21 risolto su `schema_db` (non `codice_interno`) — vedi nota §3b.
3. **§4 CANDIDATE_ADD_CI** — ✅ DECISO + DB FATTO (2026-06-29, vedi §10): #1 `profili_accesso`
   via enum `tipo` (no colonna); #2 `email_account` + #3 `categorie_clienti` con `codice_interno`;
   #4 `domini_task` lock `codice`. pgTAP esistenti adeguati (vedi §11.2).
4. **Sistemico** — §7: valutare esposizione `*_codice_interno` sulle viste-lista (allineato
   al follow-up del brief naming). Follow-up FE, non bloccante.
5. **Dedup (regola del 2)** — ✅ FATTO (2026-06-28): estratto BB
   `apps/core/db/_helpers.resolve_config_id_by_codice_interno` (generalizza
   `pratiche_repository._resolve_stato`) e fatti convergere i lookup
   `SELECT id … WHERE codice_interno = %s AND attivo` della "Famiglia A — risolvi
   id o solleva `E_CONFIG_MANCANTE`": pratiche (`_resolve_stato` +
   `create_nota`/`create_allegato`) e `approvazioni_prezzo_service`
   (`tipi_prestazione`, `priorita_pratiche`). Registrato nel catalogo BB.
   La "Famiglia B — id o `None`" (`ordini`/`note_stili`) **non** unificata
   (decisione: solo A).

> **🟢 Lato DB l'intero documento è COMPLETO** (§3a A–E + §4 #1–#4 scritti, applicati e
> testati; pgTAP esistenti adeguati). Quanto resta è **lato BE**: consolidato in **§11**.

---

## 9. Piano di sviluppo DB — §3a BUG_DUAL (in corso)

> **Scope**: SOLO modifiche DB. Avviato 2026-06-28 (team DB, `dev/db-tid`). Sostituzione
> `<alias>.codice → <alias>.codice_interno` (literale invariato) sugli oggetti §3a.
> Sorgente DDL: **doc autogen** (`docs/it/dbzero/...`), MAI gli YAML storici. Ogni oggetto =
> nuovo file `runOnChange: true`, `CREATE OR REPLACE`, un changeSet/file, `logicalFilePath`,
> suffisso `-mctit`. Numerazione globale per data: si parte da `20260628-12`.

### 9.1 Analisi critica — rettifiche all'audit §3a

1. **Pre-check seed (CSV = dati reali)**: `codice == codice_interno` confermato per **tutte**
   le righe `config.sorgenti` e per i literali stati (`DRAFT/EMESSO/ACCETTATO/ANNULLATO/
   CONFERMATO/ATTIVO/SPEDITO/CONSEGNATO`) in `stati_doc_preventivi/ordini/contratti/ddt`.
   → item 1–14, 16: switch **a rischio zero** (valori identici).
2. **Item #15 `tipi_ruoli` 'EF' — ESCLUSO da questo giro (brief separato).** Qui i due valori
   **differiscono**: `codice_interno = 'EF'`, `codice = 'EMITT_FISC'`. Il literale `'EF'` è in
   realtà un `codice_interno`; `tr_ef.codice = 'EF'` non matcha alcuna riga nel seed → non è un
   cambio meccanico. Inoltre la **riga 84** (`tr_sogg.codice = p_ruolo_codice_soggetto`) è la
   stessa classe di bug, mancata dall'audit, e dipende dal chiamante. Rimandato a brief dedicato
   con verifica live + decisione sul parametro.
3. **`fn_cambia_stato_preventivo`**: correggere **tutto il corpo** (SELECT `sdp.codice`→
   `codice_interno`, `%TYPE` dichiarato, resolve `p_nuovo_stato`, rami `IF ... = 'DRAFT'`). Il
   `RETURNS TABLE` espone i codici → diventa l'identificatore immutabile (oggi valori identici;
   segnalato al BE).
4. **Anello canali**: `trgfn_documenti_sync_canali` (scrive `canale_codice` via CASE su `codice`)
   e `fn_set_documento_canale_stato` (rilegge `s.codice = v_canale`) vanno corretti **insieme**.
   Il literale `'DIRETTO'` è un sentinel (non è una sorgente) → invariato.
5. **Convenzione `%TYPE` su firma e `RETURNS TABLE`** (richiesta Tid): i nuovi `CREATE OR
   REPLACE` usano `tabella.colonna%TYPE` su parametri e colonne di ritorno con proiezione
   diretta da colonna; tipi espliciti solo per colonne calcolate/letterali (es.
   `emittente_soggetto_ruolo_id bigint`, `meta jsonb`, contatori). I tipi sono stati verificati
   1:1 contro le tabelle sorgente per non cambiare il return type (vincolo `CREATE OR REPLACE`).
   Nessun effetto runtime: PG risolve `%TYPE` al tipo base (l'autogen mostrerà i tipi base).

### 9.2 Lotti e tracciamento

Stato: ⬜ da fare · 🔧 in corso · ✅ scritto (non applicato) · 🧪 testato · ⛔ sospeso

| Lotto | Oggetto (file dbzero) | Occorrenze §3a | File migration | Stato |
| --- | --- | --- | --- | --- |
| **A** sorgenti | `fn_list_preventivi_da_pushare` | #3, #4 (+stato) | `20260628-12` | ✅ |
| **A** | `fn_list_ordini_da_pushare` | #5, #6 (+stato) | `20260628-13` | ✅ |
| **A** | `fn_list_contratti_da_pushare` | #7, #8 (+stato) | `20260628-14` | ✅ |
| **A** | `fn_list_ddt_da_pushare` | #9, #10 (+stato) | `20260628-15` | ✅ |
| **A** | `fn_list_consumi_da_pushare` | #11 | `20260628-16` | ✅ |
| **A** | `fn_emit_attivita_fatturabili_da_commessa` | #12 | `20260628-17` | ✅ |
| **B** canali | `trgfn_documenti_sync_canali` | #13 | `20260628-18` | ✅ |
| **B** | `fn_set_documento_canale_stato` | #14 | `20260628-19` | ✅ |
| **C** stati | `fn_cambia_stato_preventivo` | #1 | `20260628-20` | ✅ |
| **C** | `fn_crea_revisione_preventivo` | #2 | `20260628-21` | ✅ |
| **D** vista | `vw_preventivi_pratiche` | #16 | `20260628-22` | ✅ |
| **pgTAP** | anti-regressione (rename `codice` → risoluzione per `codice_interno`) aggiunta ai test ESISTENTI delle 9 funzioni/trigger | — | vedi §9.4 | ✅ scritto |
| **E** tipi_ruoli | `fn_lookup_utilities_per_ba` (#15 + riga 84) | #15 | `20260629-01` | ✅ scritto |

> Nota: gli stati dentro le `fn_list_*` (#4/#6/#8/#10) sono nella **stessa** funzione della
> sorgente corrispondente → un solo `CREATE OR REPLACE` per file copre entrambe le occorrenze.

### 9.4 pgTAP anti-regressione (estensione test ESISTENTI)

Verificato che **ogni** funzione/trigger toccato aveva già un test pgTAP → estesi i test
esistenti (no nuovi file). Pattern: dentro il `BEGIN; ... ROLLBACK;`, rename del `codice`
(mutabile) della sorgente/stato e asserzione che la funzione risolva comunque per
`codice_interno` (col vecchio codice fallirebbe: `E_CODICE` / `E_STATO_SCONOSCIUTO` /
`PREV_REVISIONE_STATO_NON_AMMESSO`).

| Test esteso | Caso aggiunto | plan |
| --- | --- | --- |
| `test-fn-list-preventivi-da-pushare-v2` | rename sorgente PREVENTIVO (+ **fix stale**: pronargs 4→5, `p_righe_ids`) | 9→10 |
| `test-fn-list-ordini-da-pushare-v2` | rename sorgente ORDINE_VENDITA | 4→5 |
| `test-fn-list-contratti-da-pushare-v2` | rename sorgente CONTRATTO | 4→5 |
| `test-fn-list-ddt-da-pushare-v2` | rename sorgente DDT_VENDITA | 4→5 |
| `test-fn-list-consumi-da-pushare-v2` | rename sorgente ATTIVITA_CONSUMI | 3→4 |
| `test-fn-emit-attivita-propaga-audit-pricing-v1` | rename sorgente COMMESSA (emit dry_run) | 5→6 |
| `test-documenti-canali-sync-v1` | rename 4 sorgenti → trigger apre comunque il canale | 14→15 |
| `test-fn-cambia-stato-preventivo` | rename stati DRAFT/EMESSO → transizione risolta | 9→10 |
| `test-fn-crea-revisione-preventivo` | rename stati EMESSO/DRAFT → revisione risolta | 9→10 |

> **Nota stale**: `test-fn-list-preventivi-da-pushare-v2` asseriva ancora `pronargs = 4`
> mentre la funzione ha 5 parametri da rev 12-06-2026 (`p_righe_ids`). Corretto a 5 (non
> correlato al fix codice_interno, ma emerso ri-lanciando i test).

### 9.5 Lotto E — `tipi_ruoli` / `fn_lookup_utilities_per_ba` (BUG REALE, non difensivo)

Trattato qui (no brief separato). **Differenza chiave dagli altri lotti**: in `config.tipi_ruoli`
`codice_interno` ≠ `codice` (es. `EF`/`EMITT_FISC`, `CL`/`CLIENTE`, `FO`/`FORNITORE`). Quindi
non è un cambio cosmetico ma un **fix di comportamento**.

**Diagnosi** (verificata su seed CSV + chiamanti):

- La funzione confronta i ruoli per la colonna **`codice` mutabile** in **due** punti:
  - riga 93: `tr_ef.codice = 'EF'` — ma nessuna riga ha `codice = 'EF'` (la riga EF ha
    `codice = 'EMITT_FISC'`, `codice_interno = 'EF'`).
  - riga 84: `tr_sogg.codice = p_ruolo_codice_soggetto` — **occorrenza mancata dall'audit §3a**.
- Il backend (`billing_account_service.py`: `_ALLOWED_RUOLI_BA = {"CL","FO","GE"}`;
  `lookup_repository.py`) passa **`CL`/`FO`/`GE`** = `codice_interno`. Quindi anche il JOIN
  soggetto non matcha (`codice` = `CLIENTE`/`FORNITORE`/`GESTORE`).
- **Conseguenza**: oggi la funzione ritorna **0 righe** per qualunque BA (entrambi i JOIN
  falliscono). Il pgTAP esistente non lo cattura (asserisce solo "le righe ritornate hanno
  `codice` valorizzato" → vero a vuoto).

**Fix DB** (`20260629-01`, solo funzione): riga 84 e riga 93 → `codice_interno`. Allinea la
funzione a ciò che il BE **già** invia (nessuna modifica BE necessaria). `u.codice`/`ORDER BY
u.codice` restano (sono il codice **dell'utility**, non del ruolo → display). `p_ruolo_codice_soggetto`
resta `text` (stabilità firma); `utility_id` resta `bigint` (cast `u.id::bigint`, `utilities.id`
è `integer` → niente %TYPE per non cambiare il return type). `p_billing_account_id` →
`billing_account.id%TYPE`.

> **Test rafforzato (FATTO)**: `test-fn-lookup-utilities-per-ba` esteso (plan 5→7). Il seed
> non mappa **nessuna** utility al ruolo EF (→ 0 righe anche col fix coi soli dati seed),
> quindi la fixture prende una utility mappata a CL e le aggiunge il mapping EF, poi asserisce
> che la funzione la ritorna passando `'CL'` (codice_interno). Col vecchio `codice` quei JOIN
> davano 0 righe → **il test 6 fallisce sulla funzione NON ancora corretta** e passa dopo
> `20260629-01` (prova reale). Test 7: rename del `codice` dei ruoli → funzione invariata.
> Soft-pass se il DB non ha un BA con emittente risolvibile.

### 9.3 Verifica post-modifica

- pgTAP / test DB verdi (applicazione lato Tid).
- Smoke pipeline push→fatturazione (`a-test-push-commesse-fatturazione.md`).
- Test anti-regressione: rinomino temporaneo di un `codice` (es. `PREVENTIVO`→`PREV`) e verifica
  che la pipeline **non** si rompa.

## 10. §4 `CANDIDATE_ADD_CI` — decisioni e deliverable (2026-06-29)

Decise con Tid. DB-first: il DB cambia, i consumer BE si adeguano dopo.

| # | Tabella | Decisione | Deliverable DB | Stato |
| --- | --- | --- | --- | --- |
| 1 | `config.profili_accesso` (`SUPER_ADMIN`) | **NON** aggiungere `codice_interno`: esiste già l'**enum stabile `tipo`** (`config.tipo_profilo_accesso`), usato dalle funzioni sorelle. Allineare i 3 guard a `pa.tipo` (elimina duplicazione). | `20260629-02` (`fn_check_almeno_un_super_admin_attivo`), `20260629-03` (`trgfn_profili_accesso_bindings_guard_ultimo_super_admin`), `20260629-04` (`trgfn_identita_digitali_guard_ultimo_super_admin`) | ✅ scritto |
| 2 | `config.email_account` (`SISTEMA`) | **(A)** aggiungere `codice_interno` + lock + migrare consumer. | `20260629-05` (add col), `20260629-07` (`fn_resolve_email_account`), seed `email_account.csv`+loader | ✅ scritto |
| 3 | `anagrafiche.categorie_clienti` (`STANDARD`) | **(A)** aggiungere `codice_interno` + lock. Nessun consumer DB (solo BE). | `20260629-06` (add col), seed `categorie_clienti.csv`+loader | ✅ scritto |
| 4 | `dbops.domini_task` | **(B)** lock esplicito di `codice` (infra, non rinominabile; nessuna nuova colonna). | riga seed `dbops/automation_lock_columns.csv` (`dbops,domini_task,codice,…,AUTO`) | ✅ scritto |

**Note tecniche:**

- `codice_interno` (#2/#3): `character varying`, backfill `= codice`, `NOT NULL` + `UNIQUE` +
  `CHECK (btrim <> '')`. Il **lock** si auto-provisiona dal runner
  `dbops.fn_run_automations_lock_columns` (90_end `runAlways`) per la sola presenza della
  colonna (linee-guida-sql §6b) — nessuna riga in `automation_lock_columns` necessaria.
- Seed (#2/#3): CSV + loader (`loadUpdateData`, `runOnChange:true`+`validCheckSums:ANY`)
  aggiornati con `codice_interno = codice`. Su build fresca il backfill è no-op (tabella vuota
  a 00_schema) e il CSV fornisce il valore; su DB esistente il backfill popola le righe correnti.
- #4: la riga `automation_lock_columns` con `exec_mode=AUTO` fa generare al runner il trigger
  `trg_domini_task_a10_protect_codice_upd` (`script.trgfn_lock_columns`).
- **BE da adeguare dopo** (fuori scope DB): `amm_software_repository.py` (#1 — ora può usare
  `tipo='SUPER_ADMIN'`), `clienti_repository.py:132` (#3 — `codice_interno`).
  Per #2 nessun consumer BE diretto noto oltre alla fn DB.

## 11. Handoff Backend (DB completo → BE può iniziare)

Tutto il lato DB è applicato e testato. Quanto segue è ciò che resta **lato backend**.
I fn DB ora risolvono internamente per `codice_interno`/enum: il BE deve allinearsi solo
dove **interroga direttamente** quelle tabelle o dove **passa** codici come parametro.

### 11.1 BE — ✅ FATTO (2026-06-29, test verdi: amm_software+anagrafiche 524, vendite 957)

| # | Origine | File:riga | Fatto | Esito |
| --- | --- | --- | --- | --- |
| BE-1 | §4 #1 `profili_accesso` | `backend/apps/amm_software/db/amm_software_repository.py` (280/292/411) | ✅ `WHERE pa.codice = 'SUPER_ADMIN'` → `WHERE pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso` (3 occorrenze: INSERT/DELETE/COUNT binding). | Allineato ai 3 guard DB. ⚠️ Nota: `tipo` è una *categoria* (non UNIQUE come `codice`); profilo SUPER_ADMIN oggi **unico** (seed idempotente) → INSERT binding corretto. |
| BE-2 | §4 #3 `categorie_clienti` | `backend/apps/anagrafiche/db/clienti_repository.py:132` (`get_categoria_cliente_id_by_codice`) | ✅ `WHERE codice = %s` → `WHERE codice_interno = %s`. | Seed `codice_interno == codice` (STANDARD); unico caller passa `'STANDARD'` (codice_interno). |
| BE-3 | §3a (verifica) | `backend/apps/vendite/db/preventivi_repository.py:630`, caller di `fn_set_documento_canale_stato` | ✅ **verificato, nessuna modifica**: `cambia_stato` passa già `nuovo_stato` come `codice_interno` (guard su `"EMESSO"/"ACCETTATO"`, modello su `stato_codice_interno`); `fn_set_documento_canale_stato` **non ha caller BE** (solo DB→DB). | Contratto già su codice_interno. |

### 11.2 Nessun intervento BE necessario (verificato)

- **§4 #2 `email_account`**: l'unico consumer della logica `SISTEMA` è il fn DB
  `fn_resolve_email_account` (già su `codice_interno`). Il BE riceve il JSON e ne relaya il
  campo `codice` (display). I mock nei test (`test_email_service.py`,
  `test_email_outbox_service.py`) ritornano `codice='SISTEMA'` come display → restano validi.
- **§4 #4 `domini_task`**: lock di `codice` (immutabile). Il BE continua a **leggere** `codice`
  normalmente (`pipeline_repository.py:348`); il lock impedisce solo i rename.
- **Lotto E `fn_lookup_utilities_per_ba`**: il BE **già** invia `CL`/`FO`/`GE` (= `codice_interno`)
  via `_ALLOWED_RUOLI_BA` (`billing_account_service.py`) → **già corretto**, nessun cambio.

### 11.3 Già fatto

- **§3b** (5 punti BE): ✅ FATTO (2026-06-28, 359 test verdi). NB #21 risolto su `schema_db`.
- **pgTAP DB adeguati** post-migration (per consapevolezza, già verdi): `test-fn-lookup-utilities-per-ba`
  (rafforzato, prova reale del fix E), `test-fn-resolve-email-account` (self-contained),
  `test-categorie-clienti-v1`, `test-parameter-overrides-categoria-cliente-v1` (incl. fix
  trigger-name generato + vincolo deferred), `test-fn-list-parameters-for-user`.

### 11.4 Follow-up non bloccanti (FE)

- §7 sistemico: esporre `*_codice_interno` sulle viste-lista che oggi proiettano solo `*_codice`,
  così i consumer FE confrontano la chiave stabile. Allineato al follow-up del brief naming.

### 11.5 BE — chiusura §11.1 + bug downstream emersi (2026-06-29)

- **BE-1** ✅ `amm_software_repository` (280/292/411): super-admin riconosciuto via **enum
  `tipo`** (`pa.tipo = %s::config.tipo_profilo_accesso`), literale `'SUPER_ADMIN'` ×3 sostituito
  dalla costante `apps.core.services.auth_constants.TIPO_PROFILO_SUPER_ADMIN` (no hardcode).
- **BE-2** ✅ `clienti_repository.get_categoria_cliente_id_by_codice`: era **codice morto**
  (zero chiamanti) → **rimosso** + corretto il commento stale in `create_billing_account`.
- **BE-3** ✅ verificato, nessuna modifica (`cambia_stato` passa già `codice_interno`).

> **🔴 Due bug downstream introdotti dalle migration §4 (NON segnalati nell'handoff DB),
> trovati in review critica e corretti**: le colonne `codice_interno NOT NULL` aggiunte
> (§4 #2 email_account `20260629-05`, §4 #3 categorie_clienti `20260629-06`) sono **senza
> default né trigger di popolamento**, ma le rispettive **create BE non scrivevano la
> colonna** → l'INSERT violava NOT NULL.
>
> - `categorie_clienti_repository.create_categoria`: ✅ ora set `codice_interno = codice`
>   (qui `codice` è già immutabile lato API → coincidono).
> - `email_repository.create_account`: ✅ ora set `codice_interno = codice` (qui `codice` è
>   **mutabile** via PATCH → `codice_interno` è la chiave stabile fissata alla create).
>
> **Lezione**: aggiungere una colonna `NOT NULL` senza default impatta **tutte le create
> applicative**, non solo i lookup. L'handoff DB aveva indicato solo il lookup (per giunta
> codice morto), mancando le due create reali ([[feedback_audit_db_preventivo_smoke]]).
> Doc API aggiornate: `api_categorie_clienti.md`, `api_email.md`.

**Test**: core + anagrafiche + amm_software = 1126 verdi.

---

*Analisi hardcode `codice` vs `codice_interno` — ZeroERP 2026-06-28. Complementare a
`brief-naming-stato-codice-interno.md` (✅ risolto 2026-06-28). 21 BUG_DUAL + 7 CANDIDATE_ADD_CI
confermati. §4 deciso e implementato 2026-06-29 (vedi §10). **Lato DB COMPLETO**; handoff BE in §11.*
