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

1. **DB (team DB)** — 🔴 DA FARE. Brief di correzione per §3a: cambiare `codice` →
   `codice_interno` nelle 16 occorrenze (focus pipeline `fn_list_*_da_pushare` +
   `config.sorgenti`). Le tabelle hanno già `codice_interno` con gli stessi valori →
   cambio meccanico, basso rischio. Brief pronto: `brief-db-hardcode-codice-pipeline.md`.
2. **BE (backend agent)** — ✅ FATTO (2026-06-28, 359 test verdi): §3b 5 punti corretti.
   NB: #21 risolto su `schema_db` (non `codice_interno`) — vedi nota §3b.
3. **Decisione Tid** — §4: per `profili_accesso`/`email_account`/`categorie_clienti`
   scegliere *aggiungi `codice_interno`* vs *lock `codice` come chiave-di-sistema*.
   Il cluster `SUPER_ADMIN` è il più urgente (security).
4. **Sistemico** — §7: valutare esposizione `*_codice_interno` sulle viste-lista (allineato
   al follow-up del brief naming).

---

*Analisi hardcode `codice` vs `codice_interno` — ZeroERP 2026-06-28. Complementare a
`brief-naming-stato-codice-interno.md` (✅ risolto 2026-06-28). 21 BUG_DUAL + 7 CANDIDATE_ADD_CI
confermati.*
