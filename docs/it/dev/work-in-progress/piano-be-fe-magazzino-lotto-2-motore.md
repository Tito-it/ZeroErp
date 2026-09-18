# Piano BE/FE — magazzino, Lotto 2: il motore arriva a video

> **Chi scrive:** backend/frontend (`dev/backend-tid`), 2026-09-18.
> **Origine:** [brief-db-magazzino-lotto-2-motore.md](brief-db-magazzino-lotto-2-motore.md)
> — lato DB **chiuso il 18-09** (22 changeSet `EXECUTED`, PR #1605 già in
> `Tito-dev`), che lascia a BE/FE **due richieste minime** (§4.9, §4.10 — la CI
> è rossa finché non arrivano) e rimanda a *«un brief BE/FE suo»* il resto:
> *«il primo endpoint, il drawer dell'inventario, la lista movimenti — nasce
> quando questa primitiva esiste»*. Esiste.
> **Prerequisiti DB nuovi:** [brief-db-magazzino-lotto-2-bis-be-fe.md](brief-db-magazzino-lotto-2-bis-be-fe.md)
> (R-1 … R-5): solo il **Pezzo 3** li aspetta, tutto il resto no.
> **Stato:** 🔵 scritto, nessuna riga di codice. ✅ **Le cinque domande di §10
> sono decise da Tid il 2026-09-18** (tutte sulla raccomandazione): resta
> aperto solo ciò che aspetta il DB (R-1, R-2, R-3). Lo stato per pezzo è in §0-bis.
>
> **In una riga.** Cinque pezzi, in ordine di dipendenza: **0** chiude la CI
> (le due richieste del brief DB, stesso giro di PR); **1** apre il dominio
> (app Django montata, cartella FE, rotte, navigazione); **2** è il BE del
> *documento interno* — inventario e rettifica come **una** implementazione
> con due configurazioni, perché il DB le ha già fatte una famiglia; **3** è il
> FE dello stesso documento (lista, drawer, righe, piano, registra); **4** è la
> consultazione (disponibilità e registro dei movimenti). Il primo carico in
> assoluto si fa **dall'inventario**, ed è il collaudo che dice che il motore
> gira da video.

---

## 0-bis. Stato di avanzamento

> Una riga per pezzo. ✅ fatto · 🟡 in parte · ⏳ in attesa di un prerequisito
> · 🔵 da fare.

| Pezzo | Stato | Prerequisito | Che cosa consegna |
| --- | --- | --- | --- |
| **0** — le due richieste del brief DB | 🟡 | nessuno | ✅ **i messaggi (18-09 sera)**: 27 codici nel modulo generato (867 → 894, zero classi mosse) + 27 ripieghi; 13 `reason_key` nei locales (radice `magazzino`). 🔵 resta `requires_lotto` BE+FE (§2.1, §2.2) — stesso commit. **CI verde** |
| **1** — il terreno dell'app | 🔵 | nessuno (R-3 per il gate di `registra`: fail-closed finché non c'è) | `urls_v1` montato, repository/service/types, cartella FE, rotte, voci L2, `READONLY_DOMAINS`/`TAB_ENTITIES`, i18n `magazzino.*` |
| **2** — BE documento interno (inventario + rettifica) | 🔵 | R-2 per il duplicato di posizione (mappa a un codice a catalogo); Q-1 ✅ | lista + export, crea/dettaglio/PATCH/DELETE, `stato/`, `registra/`, `piano/`, righe CRUD + lista + export, lookup di riga, `righe/motivi/` |
| **3** — FE documento interno | ⏳ **R-1** per la barra delle azioni | R-1 (capability), R-3; Q-1/Q-3/Q-4/Q-5 ✅ | lista, `ApriDocumentoInternoDialog`, drawer con righe (`DrawerTabLista` + form), piano in dialog, registra con conferma |
| **4** — consultazione | 🔵 | nessuno | `disponibilita/` (+ per articolo, + blocchi), `movimenti/` (+ export); due viste FE; deep-link dal documento POSTED |

---

## 1. Il terreno, misurato sul codice (2026-09-18)

| Fatto | Dove | Cosa ne discende |
| --- | --- | --- |
| Il modulo generato conosce **2** `E_MAG_*`, il catalogo **29**; `genera_error_policies --check` esce 1 | [error_policies_generated.py](../../../../backend/apps/core/services/error_policies_generated.py), `codici_errore.csv` | Pezzo 0: `test_il_file_generato_e_allineato_al_catalogo` e `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego` sono rossi **adesso** |
| `check_i18n_keys.py` fallisce con **13** chiavi emesse dal DB e assenti (`magazzino.disponibilita.blocco.*` ×2, `magazzino.riga.blocco.*` ×11) | doc auto-gen di `fn_check_disponibilita_uscita` / `fn_check_riga_magazzino` | Pezzo 0: i locales, prima di tutto |
| `requires_serial` è cablato in **quattro** punti BE (`ARTICOLI_CREATE_COLUMNS`, `ARTICOLI_DETAIL_COLUMNS`, `_ARTICOLO_FLAG_FIELDS`, serializer) e in **cinque** del drawer (default, load, due payload, template con `isFieldLocked`) | [catalogo_repository.py:88-124](../../../../backend/apps/catalogo/db/catalogo_repository.py#L88-L124), [catalogo_service.py:54](../../../../backend/apps/catalogo/services/catalogo_service.py#L54), [views.py:87](../../../../backend/apps/catalogo/api/views.py#L87), [ArticoloDrawer.vue:85-255](../../../../frontend/src/catalogo/components/ArticoloDrawer.vue#L85-L255) | `requires_lotto` è la stessa strada, **senza** il lucchetto (Lotto 1 §4.3) |
| `vw_articoli_dettaglio` ha `requires_lotto` in colonna 56; la proiezione BE è **per nome** | `ARTICOLI_DETAIL_COLUMNS` | senza la riga `a.requires_lotto` la colonna non esce |
| `apps/magazzino`: 13 file, `urlpatterns = []`, **non montata** in `zeroerp_backend/urls.py`; `src/magazzino`: due `.gitkeep`; `'magazzino': []` in `navigation.js`; il router non lo conosce (`domainsWithRoutes`) | [urls.py:126-135](../../../../backend/zeroerp_backend/urls.py#L126-L135), [navigation.js:122,227](../../../../frontend/src/core/navigation.js#L122), [router/index.js:47](../../../../frontend/src/router/index.js#L47) | Pezzo 1 è un bootstrap, non un refactor |
| Area `magazzino` **esiste** (`config.aree_funzionali` id 6); nessuna azione di processo di magazzino in `azioni_processo.csv` | seed `80_data/sql/config` | `DomainAPIView(area_funzionale="magazzino")` funziona subito; il gate del verbo irreversibile (`registra`) vuole una riga di seed → **R-3** |
| `magazzino.magazzini/ubicazioni/causali` sono nel lookup generico (`_REL_CONSENTITE`) e nel pannello config (`config-tables.js`, drawer generico); `fn_get_lookup_codici` è INVOKER ⇒ **la RLS filtra i magazzini per emittente** | [dbops_repository.py:107-109](../../../../backend/apps/core/db/dbops_repository.py#L107-L109), [config-tables.js:62-65](../../../../frontend/src/core/config-tables.js#L62-L65) | un magazzino e le sue ubicazioni si creano già in-app; il picker del magazzino è `LookupSelect rel="magazzino.magazzini"` — ma il form della riga vuole `usa_ubicazioni` ⇒ variante **specializzata** (`_LOOKUP_SPECIALIZZATE`, una colonna in più: api.md §Lookup) |
| `lotti` e `assets` **non hanno** né lookup né CRUD in-app | idem | i picker di riga (lotto, seriale) sono lookup **dedicati** (§4.3); creare un lotto in-app = `magazzino.lotti` nel pannello config (BE whitelist + una riga in `config-tables.js`); gli asset restano al lotto degli eventi asset |
| La matrice `DRAFT → CONFIRM \| CANCEL; CONFIRM → POSTED \| CANCEL \| DRAFT` vive **nel corpo del guard** (`CASE v_old …`), non in una tabella né in una `fn_available_actions_*`; `inventari`/`rettifiche` non hanno `numero`, `stato_descrizione`, né tabella di stato | [trgfn_documento_interno_guard_transizione](../../dbzero/magazzino/funzioni/trgfn_documento_interno_guard_transizione.md) | il BE **non può** leggere le transizioni senza riscriverle (seconda sede di una regola: vietato) ⇒ **R-1**. Le etichette degli stati sono chiavi i18n FE (`magazzino.documenti_interni.stato.<CODICE>`), la severity una mappa in `core/utils/severity.js` |
| `fn_posta_inventario` / `fn_posta_rettifica` sono `INVOKER`, `RETURNS TABLE (movimento_id, riga_id, qta)`, **una transazione** per costruzione; rifiutano non-`CONFIRM`, senza righe, fuori perimetro (404 no-leak) | doc manuale delle due fn | il verbo `registra/` è **una `SELECT`** (api.md §Atomicità: «una sola `SELECT fn_madre`»), niente `transaction.atomic()` |
| `fn_inventario_piano` è `STABLE INVOKER`, senza vincolo di stato; esiti `INV_INIZIALE / RETT_POS / RETT_NEG / INVARIATA / NON_CONTATA / NON_POSTABILE` + `posting_blocco_reason` / `_reason_key` | doc manuale | il BE non filtra per stato; la UI lo mostra dove decide D-L2-n (al passaggio a `CONFIRM`) e lo lascia consultare in `DRAFT` come anteprima |
| `uq_mag_inventari_righe_posizione` (UNIQUE NULLS NOT DISTINCT) rifiuta due righe sulla stessa posizione con un `23505`; **nessun `E_MAG_*` a catalogo** lo nomina | `inventari_righe`, C14 del brief | `map_integrity_error` vuole un codice registrato ⇒ **R-2** |
| Il guard delle righe ammette la scrittura **solo in `DRAFT`** (`E_MAG_DOCUMENTO_RIGHE_CONGELATE`); `DELETE` della testata solo in `DRAFT` (`E_MAG_DOCUMENTO_NON_ELIMINABILE`) | idem | il readonly del drawer è `stato !== 'DRAFT'` **provided** ai figli (frontend-standards §catena readonly); il BE **traduce e passa**, senza copia |
| `causali.RETT_NEG/RETT_POS` portano `meta.motivi_suggeriti` | `causali.csv` | il `motivo` della riga di rettifica può proporre quei valori (v1: testo libero, suggerimenti dopo) |
| `DistintaDrawer` (18/09) è il precedente più recente della forma «testata + righe come `DrawerTabLista` + form sotto + `ApriXDialog` per la creazione» | [DistintaDrawer.vue](../../../../frontend/src/pagamenti/components/DistintaDrawer.vue), [ApriDistintaDialog.vue](../../../../frontend/src/pagamenti/components/ApriDistintaDialog.vue) | la forma del drawer è quella; la creazione passa da un dialog (testata di tre campi), **non** da `useDrawerAutosaveBozza` |
| `dbops.fn_pgtap_crea_magazzino(codice, usa_ubicazioni)` e `fn_pgtap_crea_articolo(codice, gestito, requires_lotto, requires_serial)` esistono (P-9) | doc `dbops` | i test BE sul DB provvisto (`richiedi_db_provvisto` + `apri_contesto_operatore`) **costruiscono** il mondo con gli stessi helper, non lo cercano |
| `valori_check` (BB `tests/db_e2e.py`) legge i valori ammessi da un `CHECK` di appartenenza | catalogo BB | il vocabolario degli stati specchiato nel BE (`STATI_DOCUMENTO_INTERNO`) si **pinna** su `chk_mag_inventari_stato` e `chk_mag_rettifiche_stato` |

---

## 2. Pezzo 0 — le due richieste del brief DB *(BE + FE, nessun prerequisito, CI rossa oggi)*

### 2.1 BE — `requires_lotto` sull'articolo (brief §4.9)

- `ARTICOLI_CREATE_COLUMNS`: `"requires_lotto": "bool"` (eredita in `_UPDATE_COLUMNS`);
  `ARTICOLI_DETAIL_COLUMNS`: `a.requires_lotto`; `_ARTICOLO_FLAG_FIELDS`:
  `requires_lotto`; `@extend_schema`: `"requires_lotto": BooleanField(required=False)`.
- ⛔ **Non** in `non_editable_fields` / `lock_columns_conditional`: è fuori dal
  lock BoM per decisione (Lotto 1 §4.3). Il test dei flag in
  `test_catalogo_service.py` (quello che pinna `gestito_a_magazzino`) prende
  la quarta riga.

### 2.2 FE — il `ToggleSwitch` nel drawer (brief §4.9)

- `ArticoloDrawer.vue`: default `requires_lotto: false`, load `data.requires_lotto || false`,
  nei due `buildPayload`, e nel template **accanto** a `requires_serial`
  ⛔ **senza** `:disabled="isFieldLocked('requires_lotto')"` — chi copia il
  gemello a occhi chiusi eredita il lucchetto.
- i18n it/en: `catalogo.field_requires_lotto` («Richiede lotto») +
  `catalogo.hint_requires_lotto` («L'articolo si movimenta per partite: ogni
  movimento nomina un lotto»), reso come `<small class="app-text-muted mt-025">`
  come per `hint_modo_approvvigionamento`.
- La colonna di lista (`ui.lista_colonna`, lista 26) **non è richiesta** dal
  brief: se la si vuole, `attivo = t` solo se `gen_seed_lista.py --verifica
  catalogo.articoli` la vede proiettata.

### 2.3 BE — i 27 codici (brief §4.10)

- `./manage-env.sh genera_error_policies` (riscrive il modulo generato: 29
  `E_MAG_*`); poi `--check` deve uscire 0.
- **27 ripieghi** in `error_messages_fallback.py`, uno per codice, **senza
  segnaposto**, ricavati dai messaggi a catalogo (id 1075–1101) togliendo i
  valori — sul modello dei due `E_MAG_*` già presenti (righe 519-529). Sui
  `TECNICO` la frase chiude con «segnalare al supporto», sui `DATO_ERRATO`
  nomina il campo da correggere, sui `CONFLITTO_STATO` dice «rileggere lo stato».
- Presidi: `apps.core.tests` (`test_error_policies_divergenza_db`,
  `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego`, `test_error_codes_declared_guardrail`).

### 2.4 FE — le 13 `reason_key` (brief §4.10)

`it.json` + `en.json`, radice `magazzino` (area di `src/magazzino/`, frontend-standards
§Multilingua): `magazzino.disponibilita.blocco.{giacenza_insufficiente, merce_bloccata}`
e `magazzino.riga.blocco.{articolo_non_gestito, lotto_obbligatorio, lotto_non_ammesso,
lotto_di_altro_articolo, seriale_obbligatorio, seriale_non_ammesso,
seriale_di_altro_articolo, seriale_di_altro_emittente, ubicazione_obbligatoria,
ubicazione_non_ammessa, ubicazione_di_altro_magazzino}`. Testo = il messaggio a
catalogo **senza i valori** (brief §4.10). Presidio: `python3 scripts/check_i18n_keys.py` a 0.

**Verde del pezzo:** `genera_error_policies --check`, `./manage-test.sh apps.core.tests apps.catalogo.tests`,
`check_i18n_keys.py`, `npm run lint`, `npm run build`. ⚠️ Un commit solo per i
quattro punti (`feedback_commit_hook_stage_all`): l'hook gira sullo staged.

---

## 3. Pezzo 1 — il terreno dell'app *(BE + FE, nessun prerequisito)*

### 3.1 BE

| Cosa | Dove | Note |
| --- | --- | --- |
| `apps/magazzino/api/urls_v1.py` + `path("api/v1/magazzino/", include(...))` | `zeroerp_backend/urls.py` accanto a `pagamenti` | il modulo esiste vuoto: si riempie, non si crea |
| `apps/magazzino/db/magazzino_repository.py`, `services/magazzino_service.py`, `types.py` | naming AGENTS.md §repository: `<schema>_*` — un file per il dominio finché non c'è un sottodominio orchestrato | header standard + `# Scopo:` |
| `_LOOKUP_SPECIALIZZATE["magazzino.magazzini"] = {"extra_col": "usa_ubicazioni", …}` | `dbops_repository.py` | il picker del magazzino porta il flag che decide il campo ubicazione (api.md: «preferirla a un endpoint dedicato quando serve un solo campo in più») |
| `magazzino.lotti` nel pannello config | whitelist BE `CONFIG_TABLES` + riga in `config-tables.js` | senza, un articolo `requires_lotto` non ha lotti da scegliere. Drawer generico metadata-driven: bastano `articolo_id` (uuid), `codice`, `data_arrivo` |
| `STATI_DOCUMENTO_INTERNO = ("DRAFT", "CONFIRM", "POSTED", "CANCEL")`, `STATI_RICHIEDIBILI = ("CONFIRM", "CANCEL", "DRAFT")` | `magazzino_service.py` | **specchio dichiarato** del `CHECK`: test in `tests/db/` con `valori_check("magazzino.inventari", "chk_mag_inventari_stato")` e il gemello di `rettifiche`; `POSTED` fuori dai richiedibili (lo scrive solo `registra/`) |

### 3.2 FE

| Cosa | Dove |
| --- | --- |
| `src/magazzino/{api/magazzino.js, vocabolari.js, stores/, views/, components/, composables/}` | struttura di `src/pagamenti/` |
| rotte `magazzino/inventari`, `magazzino/rettifiche`, `magazzino/disponibilita`, `magazzino/movimenti` (KeepAlive, `meta.domain = 'magazzino'`) + `'magazzino'` in `domainsWithRoutes` | `router/index.js` |
| voci L2 in `navigation.js` con `NAV_ICONS` nuove (`INVENTARI`, `RETTIFICHE`, `DISPONIBILITA`, `MOVIMENTI`) + `nav.magazzino.*` it/en | ordine = **il percorso della merce**: inventario (il primo carico), rettifica, disponibilità, registro — come per gli incassi |
| `READONLY_DOMAINS.MAGAZZINO`, `TAB_ENTITIES.INVENTARIO` / `RETTIFICA` | `core/constants.js` (§Enum centralizzati: mai literal) |
| `documentoInternoSeverity()` — `DRAFT` secondary · `CONFIRM` info · `POSTED` success · `CANCEL` danger | `core/utils/severity.js` |
| radice i18n `magazzino.{inventari, rettifiche, documenti_interni, disponibilita, movimenti, piano}.*` | it/en insieme |

---

## 4. Pezzo 2 — BE del documento interno *(dopo R-2; il resto senza prerequisiti)*

### 4.1 ⭐ Regola del 2, dichiarata in progettazione — una implementazione, due configurazioni

Il DB ha già fatto di inventari e rettifiche **una famiglia**: un guard di
transizione parametrico (`TG_ARGV`), un guard di righe parametrico, due
`fn_posta_*` con la stessa forma, la stessa matrice. Le differenze sono
**tre**, tutte di dato: la riga porta `qta_contata >= 0` (inventario) o
`qta_delta <> 0` + `motivo` (rettifica); l'inventario ha il **piano**; la
sorgente si chiama `INVENTARIO_RIGA` / `RETTIFICA_RIGA`. Scrivere due
repository/service/view sarebbe la seconda copia il giorno stesso della prima
(`feedback_regola_del_2_estrai_bb`: *«seconda occorrenza = STOP»* — qui la
seconda è nota **prima** della prima, precedente `build_dash_export_response`,
estratto alla prima scrittura perché le liste erano cinque).

**Forma proposta** (stampo `approvazioni_prezzo._SORGENTE_CONFIG` + le factory
`build_passaggi_view` / `make_note_views`):

```python
# apps/magazzino/services/_documento_interno.py
@dataclass(frozen=True)
class FamigliaDocumentoInterno:
    codice: str                 # "inventari" | "rettifiche"
    tabella: str                # "magazzino.inventari"
    tabella_righe: str          # "magazzino.inventari_righe"
    fk_riga: str                # "inventario_id"
    col_stato: str              # "stato_mag_inventario"
    fn_posta: str               # "magazzino.fn_posta_inventario"
    sorgente_codice_interno: str  # "INVENTARIO_RIGA"
    colonne_riga_scrivibili: dict[str, str]   # qta_contata / qta_delta+motivo, costo, lotto, asset, ubicazione
    lista_codice: str           # "magazzino.inventari"
    lista_righe_codice: str     # "magazzino.inventario_righe"
    ha_piano: bool
FAMIGLIE = {"inventari": …, "rettifiche": …}
```

Repository e service prendono la famiglia come parametro; le view nascono da
`build_documento_interno_views(famiglia)` in `api/views.py`, che le monta
sotto `inventari/` e `rettifiche/`. Le SQL interpolano **solo** identificatori
dalla config (regex di identificatore nel `__init__`, come
`PartitionedNoteRepository`); i valori viaggiano nei `params`.
✅ **Q-1 decisa da Tid il 2026-09-18**: una famiglia parametrica. Le due copie
non si scrivono.

### 4.2 Gli endpoint (`/api/v1/magazzino/`, per ciascuna famiglia — qui `inventari/`)

| Rotta | Che cosa | Note |
| --- | --- | --- |
| `GET inventari/` · `GET inventari/export/` | lista paginata (`lista_codice = magazzino.inventari`), filtri `magazzino_id`, `stato`, `data_da`/`data_a` (floor standard, `feedback_filtro_data_liste`), `search` (descrizione) | JOIN `magazzini` (`magazzino_codice`, `magazzino_descrizione`), `righe_count` (sottoquery), `stato` grezzo (etichetta = i18n FE). Perimetro: RLS + `add_emittente_scope_condition` su `m.emittente_fiscale_id` (defense-in-depth, api.md §Enforcement RLS). `COUNT(*) OVER ()` via `fetch_paged_with_total`; `sql_order_clause` con `colonne_desc` sulle date, tiebreak `t.id`; `lista_codice = ApiInventariList.lista_codice` sulla view export (presidio delle coppie) |
| `POST inventari/` | crea la **bozza**: `{magazzino_id, data?, descrizione?}` | `Idempotency-Key`; `PayloadValidator`; `INSERT … RETURNING id` (l'app scrive le testate: sono sotto RLS + `WITH CHECK`, non dietro la porta). Torna il dettaglio |
| `GET inventari/<id>/` | dettaglio: testata + magazzino (`codice`, `descrizione`, `usa_ubicazioni`) + `righe_count` + **capabilities** (R-1) + `stato_info_key` (dal blob) + per l'inventario `piano_riepilogo` (`n_con_delta`, `n_invariate`, `n_non_contate`, `n_non_postabili` — `count(*) FILTER` su `fn_inventario_piano`) | 404 no-leak dalla testata (`E_MAG_DOCUMENTO_NON_TROVATO`) **prima** di ogni satellite (api.md: «leggi prima la testata»). ⏳ finché R-1 non c'è, `capabilities` **non si finge**: la chiave manca e il drawer non monta la barra |
| `PATCH inventari/<id>/` | testata: `data`, `descrizione` | whitelist **senza `magazzino_id`** (si sceglie alla nascita: R-4 lo difende a DB). ✅ **Q-2**: il guard di famiglia copre righe e stato, **non** `data`/`descrizione`; il BE **non conia** una regola che il DB non ha — la whitelist vale in ogni stato, e a video il form è comunque readonly fuori da `DRAFT` (§5.3). Se il DB vorrà congelarle, è un lucchetto suo (nota in R-4) |
| `DELETE inventari/<id>/` | elimina una **bozza** | il DB decide (`E_MAG_DOCUMENTO_NON_ELIMINABILE`, 409): il BE traduce e passa. `Idempotency-Key` |
| `POST inventari/<id>/stato/` | `{"stato": "CONFIRM" \| "CANCEL" \| "DRAFT"}` | `validate_enum_param` sui **richiedibili** (mai `POSTED`: risponderebbe un `TECNICO` 500); `UPDATE … SET <stato>` e il guard decide (`E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA`, 409); torna il dettaglio |
| `POST inventari/<id>/registra/` | **il posting**: `SELECT * FROM magazzino.fn_posta_inventario(%s)` | `post_permission = "registra_magazzino"` (R-3; fail-closed finché non è assegnato), `Idempotency-Key` obbligatoria (irreversibile). Risposta `{"movimenti": [{movimento_id, riga_id, qta}], "n_movimenti", "documento": <dettaglio>}`. ⛔ Nessun `transaction.atomic()`: la madre è la transazione |
| `GET inventari/<id>/piano/` · `GET …/piano/export/` | **solo inventari**: `fn_inventario_piano` paginata (`lista_codice = magazzino.inventario_piano`), decodificata con `JOIN` (articolo codice/descrizione, ubicazione codice, lotto codice, asset seriale) | `COUNT(*) OVER ()` sulla stessa query; testata prima (404); l'`esito` e la coppia `posting_blocco_reason`/`_reason_key` passano **così come sono** (famiglia «riga» di api.md §Capability di riga) |
| `GET inventari/<id>/righe/` · `…/righe/export/` | righe paginate (`lista_codice = magazzino.inventario_righe`), decodificate | ordine `id`; anche `qta_sistema` (scritta dal posting) |
| `POST …/righe/` · `PATCH …/righe/<rid>/` · `DELETE …/righe/<rid>/` | la riga: `articolo_id` (uuid), `qta_contata` (≥ 0) / `qta_delta` (≠ 0) + `motivo`, `costo_unitario` (≥ 0, nullable), `ubicazione_id`, `lotto_id`, `asset_id` (nullable) | `PayloadValidator`; `translate_db_errors` con `unique_constraints={"uq_mag_inventari_righe_posizione": ("E_MAG_INVENTARIO_RIGA_POSIZIONE_DUPLICATA", …, "articolo_id")}` (R-2) e i `CHECK` (`chk_*_qta_*`, `chk_*_costo_non_neg`, `chk_*_asset_qta_unitaria`) mappati; il guard di famiglia (`E_MAG_DOCUMENTO_RIGHE_CONGELATE`) risale tradotto. ⛔ **Il BE non ricalcola la coerenza della riga** (articolo gestito, lotto/seriale/ubicazione): il DB ha deciso (C8 b) che la riga si accetta in `DRAFT` e il piano la dichiara `NON_POSTABILE` — ✅ Q-3: passa **e** si mostra (§5.3) |
| `GET righe/motivi/?magazzino_id&articolo_id&lotto_id&asset_id&ubicazione_id` | `script.fn_check_riga_magazzino` così com'è: `{"motivi": [...]}` (array ordinato del DB) | **lettura**, per l'anteprima del form (§5.3): la stessa funzione che la primitiva e il piano usano — §12.5.2, «ciò che si vede è ciò che verrà scritto» |

**Lookup dedicati** (envelope `{"results": [...]}`, `is_search_endpoint`,
`area_funzionale = "magazzino"` — sono consumati dentro il dominio):
`GET magazzini/<id>/ubicazioni/lookup/` (attive, del magazzino),
`GET lotti/lookup/?articolo_id=&search=` (attivi, dell'articolo),
`GET assets/lookup/?articolo_id=&magazzino_id=` (attivi, dell'articolo,
**dell'emittente del magazzino** — la RLS su `assets` fa il resto). ⛔ Non il
lookup generico: il filtro per padre non è nel suo contratto.

### 4.3 Le liste a catalogo (dato, non DDL: le fa BE/FE con `scripts/gen_seed_lista.py`)

`magazzino.inventari`, `magazzino.inventario_righe`, `magazzino.inventario_piano`,
`magazzino.rettifiche`, `magazzino.rettifica_righe` — cinque righe in
`lista_definizione.csv` + colonne. Ogni lista entra in `_LISTE` di
`test_liste_configurabili_seed.py` con la propria whitelist di ordinamento
(chiavata sui `campo_sorgente` **fisici**, api.md) e passa
`test_lista_proiezione_campo_sorgente`. `stato` come colonna `formato`? No:
lo stato è un codice che il FE traduce con `labelOrCode` nello slot
`cell-stato` (un `formato` nuovo sarebbe la prima occorrenza).

### 4.4 Presidi del pezzo

- unit (`SimpleTestCase`, repository mockati): validazione payload, enum dello
  stato, 404 prima del satellite, envelope delle liste, `lista_codice` pari fra lista ed export;
- **DB provvisto** (`tests/db/`, `richiedi_db_provvisto` + `apri_contesto_operatore`,
  mondo costruito con `dbops.fn_pgtap_crea_magazzino` / `fn_pgtap_crea_articolo`):
  la catena intera — bozza → riga (10 pezzi, costo 7) → `CONFIRM` → piano
  `INV_INIZIALE` → `registra/` → 1 movimento, `POSTED`, `qta_sistema = 0`;
  riga su articolo non gestito → piano `NON_POSTABILE` e `registra/` rifiuta
  **tutto** (stato ancora `CONFIRM`); `POSTED` non si cancella; testata di un
  altro emittente → 404; duplicato di posizione → R-2. ⚠️ Sono i **soli** test
  che vedono la giuntura Python↔PL/pgSQL (api.md §Test, secondo livello);
- smoke HTTP `backend/scripts/tests/smoke-magazzino-inventario-primo-carico.py`
  (in `transaction.atomic()` + `set_rollback(True)`, indice in testa);
- `scripts/codici-errore-baseline.sh` resta verde: il BE non conia codici.

---

## 5. Pezzo 3 — FE del documento interno *(dopo R-1 per la barra; il resto subito)*

### 5.1 La lista — `InventariListView` + `InventariSearchTable` (e le gemelle)

`<ListaConfigurabile codice="magazzino.inventari">` via `useListaConfigurabilePage`,
store da `createListaStore` (`startsEmpty: false` — una lista di documenti
parte piena col floor data; `orderDirDefault: 'desc'`), filtri: magazzino
(`LookupSelect rel="magazzino.magazzini"`), stato (`Select` sul vocabolario
`STATI_DOCUMENTO_INTERNO` di `vocabolari.js`, etichette i18n), date
(`useStoreFilterBindings.bindDate`), `useTabFreshness(store, TAB_ENTITIES.INVENTARIO)`.
Azioni: `PageActionsBar` con «Nuovo» → `ApriDocumentoInternoDialog`; export.
Riga: click → drawer; kebab (`RowActionsMenu`, `#actions`): «Elimina» (danger,
`visible: stato === 'DRAFT'`, `useConfirmAction.confirmDelete`), «Movimenti»
(`visible: stato === 'POSTED'`, deep-link a `magazzino/movimenti?inventario_id=`).
`cell-stato` → `<Tag :severity="documentoInternoSeverity(...)">` con `labelOrCode`.
⭐ Le due liste (inventari, rettifiche) sono **lo stesso componente** con la
famiglia in prop (`DocumentiInterniSearchTable famiglia="inventari"`): codice
lista, store, dialog e drawer li dà `FAMIGLIE` di `vocabolari.js`.

### 5.2 La creazione — `ApriDocumentoInternoDialog` (stampo `ApriDistintaDialog`)

`AppDialog width="sm"`: magazzino (obbligatorio, `LookupSelect` specializzato →
`usa_ubicazioni` in mano al drawer), data (default oggi, `DatePicker`),
descrizione (solo inventario). Salva → `POST inventari/` → chiude e apre il
drawer in edit sull'id. ⛔ Non `useDrawerAutosaveBozza`: la testata ha tre
campi e nessuna riga si scrive senza un magazzino scelto — il dialog dà il
magazzino, e con esso il drawer nasce già «evoluto». È la strada del 18/09
(distinte), la più recente. ✅ Q-4.

### 5.3 Il drawer — `DocumentoInternoDrawer` (`DRAWER_WIDTH.WIDE`)

| Zona | Che cosa | BB |
| --- | --- | --- |
| header | `DrawerTitle`; `DrawerEntityHeader`: Tag `#id`, magazzino codice · descrizione, data, `usa_ubicazioni` come chip; `#status` Tag stato | `useDrawerDetailLoad` (404 → toast + chiusura), `useDrawerContentReady` |
| azioni | `DrawerActionsBar :info-key="detail.stato_info_key"`: `state` = `mapAvailableActionsToDrawerActions(capabilities.available_actions, permission: …)` — «Conferma», «Riapri», «Annulla» (`requires_confirm` → `useConfirmAction`); `primary` = **«Registra»** (`action: 'registra_magazzino'`, `severity: 'warn'`, conferma con il riepilogo del piano: «N righe con differenza, M non contate restano com'erano»; `enabled`/`reason` dal blob); `manage` = «Piano» (solo inventario, badge `piano_riepilogo.n_con_delta`); `secondary` = export righe | ⏳ **R-1**. Senza il blob la barra **non si monta**: niente `v-if` su `stato` scritto a mano (frontend-standards: «un `v-if` su `stato_codice_interno` nel drawer sarebbe la stessa regola scritta due volte») |
| readonly | `isReadonly = parentReadonly \|\| props.readonly \|\| stato !== 'DRAFT'` → `provide(READONLY_KEY, …)`; i figli solo `useInjectReadonly()` | §catena readonly; le azioni di stato restano cliccabili (`app-escape` automatico) |
| testata | form `data`, `descrizione` + `FormFooter` (Salva → `PATCH`), `campiErrati` legati | `useDrawerFormPreserve` (la ricarica dopo una riga non cancella una descrizione non salvata) |
| righe | `<DrawerTabLista codice="magazzino.inventario_righe">` su `useDrawerTabLista(storeRighe, { parentId, parentField: 'documentoId', fetchExtra: loadDetail })` — ricarica testata e righe insieme (il `righe_count` e il riepilogo dipendono dalle righe); azioni `extraActions`: «Nuova riga» (`visible: stato === 'DRAFT' && !formMode`); riga: click → form in edit, kebab «Elimina» | precedente `DistintaDrawer` |
| form riga | `DocumentoInternoRigaForm` sotto la lista (`v-if="formMode"`), `FormFooter close-only v-if="!formMode"`: articolo (`ArticoloLookup`), quantità (`qta_contata` ≥ 0 / `qta_delta` ≠ 0 + `motivo`), costo unitario (nullable, hint: «vuoto = alla media corrente»), ubicazione (**solo se** `magazzino.usa_ubicazioni`, lookup del magazzino), lotto (**solo se** `articolo.requires_lotto`, lookup dell'articolo), seriale (**solo se** `articolo.requires_serial`, lookup articolo+magazzino). ⭐ **Anteprima dei motivi**: al cambio di (articolo, lotto, seriale, ubicazione) chiama `righe/motivi/` e mostra il primo come `Message severity="warn"` con `labelOrCode(reason_key)` — best-effort, non blocca il Salva (✅ Q-3). `campiErrati` su ogni campo | `useFetchVersion` sull'anteprima (l'operatore cambia articolo più in fretta della risposta); la visibilità dei tre campi la decidono **i flag letti** (`usa_ubicazioni` dal magazzino, `requires_*` dall'articolo scelto — `ArticoloLookup` porta la riga intera), mai ricalcolata |
| piano | `InventarioPianoDialog` (`AppDialog width="xl"`, `DrawerTabLista codice="magazzino.inventario_piano"` con `app-dialog-lista`, `limit: PAGINATION.COMPACT_ROWS` + preset a 10): colonne posizione, contata, sistema, delta, esito (Tag: `INV_INIZIALE`/`RETT_*` info, `INVARIATA` secondary, **`NON_CONTATA` warn**, **`NON_POSTABILE` danger** con il motivo da `posting_blocco_reason_key` via `bloccoAttivo`/`motivoBloccoRiga` a prefisso `posting_blocco`); export. Si apre **da solo** dopo un `CONFIRM` riuscito, **sempre** (✅ Q-5; D-L2-n: «al passaggio a CONFIRM mostra il piano con le NON_CONTATA evidenziate») e dal pulsante «Piano» in ogni stato | `useDrawerTabLista` (terza occorrenza in un dialog: `RatePickerDialog`, `DistintaDrawer`) |
| registra | conferma → `POST registra/` → toast «Registrati N movimenti» → `@changed` (la lista si aggiorna, il drawer **resta** aperto in `POSTED`, readonly) | `useDrawerSavedListRefresh.onDrawerChanged` |

⭐ **Regola del 2 dichiarata (FE)**: drawer, dialog di apertura, form di riga e
search table sono **uno** per famiglia con `FAMIGLIE[famiglia]` in
`vocabolari.js` (`{ listaCodice, listaRigheCodice, api, store, storeRighe,
haPiano, campoQta: 'qta_contata' | 'qta_delta', conMotivo, i18n }`). Le
differenze fra le due sono tutte lì. ✅ **Q-1** vale anche qui.

### 5.4 Presidi del pezzo

`vocabolari.spec.js` (le due famiglie dichiarano tutto ciò che il drawer
legge); spec del composable se ne nasce uno; `npm run lint` (`vue/no-undef-properties`),
`check_i18n_keys.py` (le `label_key`/`reason_key` di R-1 entrano **prima** che
la doc auto-gen della capability entri nel repo), `check_classi_morte.py`,
il conteggio delle `DataTable` grezze che **non sale**, `npm run build`.
Collaudo a video: il copione in §8.

---

## 6. Pezzo 4 — consultazione *(BE + FE, nessun prerequisito)*

| Rotta / vista | Che cosa |
| --- | --- |
| `GET disponibilita/` (+ `export/`) — lista `magazzino.disponibilita` | `vw_disponibilita` JOIN `articoli` (codice, descrizione, `requires_lotto/serial`), `magazzini` (codice); filtri `articolo_id` (`ArticoloLookup`), `magazzino_id`, `solo_negativa` (disponibile < 0: le promesse non più mantenibili dopo una rettifica, D-L2-d), `solo_con_giacenza`. La vista è `security_invoker`: si legge **con la connessione dell'utente**, mai da un canale di sistema |
| `GET disponibilita/articoli/` | `vw_disponibilita_articolo` (somma sui magazzini visibili, `n_magazzini`) — seconda scheda della stessa vista FE |
| `GET disponibilita/blocchi/?articolo_id&magazzino_id` | gli attesi `APERTA` in uscita (`qta < 0`) con `soggetto_ruolo` decodificato e `nota`: il drill-down di `n_blocchi` (D-L2-j: «gratis») — in un `Popover`/dialog dalla cella |
| `GET movimenti/` (+ `export/`) — lista `magazzino.movimenti` | il registro: JOIN causali (codice, descrizione, segno), articoli, magazzini, ubicazioni, lotti, assets, `config.sorgenti` (`sorgente_codice_interno`); filtri magazzino, articolo, causale (`LookupSelect rel="magazzino.causali"`), `data_da`/`data_a` (floor standard su `data_mov`), **`inventario_id` / `rettifica_id`** (movimenti la cui sorgente è una riga di quel documento: `EXISTS` sulle righe — è il deep-link dal documento `POSTED`), `sorgente_tipo`. Ordine default `data_mov DESC, id DESC`. Sola lettura per costruzione (la porta) |
| FE `DisponibilitaView` (due schede `Tabs`: per magazzino, per articolo — `useTabDaQuery`), `MovimentiView` | `ListaConfigurabile` standard; `disponibile` negativo in rosso (`cell-disponibile`) |

Due liste a catalogo in più (`magazzino.disponibilita`, `magazzino.movimenti`).
⚠️ Il presidio di prontezza (`NESSUNO_MARCATO`) **non ha UI**: suona nel
digest settimanale finché il primo articolo non è marcato — è il caso voluto.

---

## 7. Richieste al DB — [brief-db-magazzino-lotto-2-bis-be-fe.md](brief-db-magazzino-lotto-2-bis-be-fe.md)

| # | Cosa | Chi aspetta | Perché non si fa nel BE |
| --- | --- | --- | --- |
| **R-1** | capability dei documenti interni (`fn_available_actions_inventario` / `_rettifica`, stampo `fn_available_actions_ordine`) con la matrice **estratta** dal guard in una sede letta da entrambi; `stato_info_key` per `POSTED`/`CANCEL`; le `label_key`/`reason_key` da dare al FE | Pezzo 3 (barra azioni, «Registra» spento col motivo) | la matrice sta nel corpo del guard: leggerla dal BE = riscriverla (seconda sede) |
| **R-2** | `E_MAG_INVENTARIO_RIGA_POSIZIONE_DUPLICATA` (`DATO_ERRATO`, `campo = articolo_id`) a catalogo | Pezzo 2 (righe) | il `23505` su `uq_mag_inventari_righe_posizione` va tradotto in un codice **registrato** (guardrail dei codici) |
| **R-3** | azione di processo `registra_magazzino` (area 6, `pericolosa = t`) | Pezzo 2 (gate) — fail-closed nel frattempo | seed di `config.azioni_processo` (memoria: mai seed dall'agent) |
| R-4 (opz.) | `magazzino_id` immutabile dopo l'`INSERT` su `inventari`/`rettifiche` (`dbops.lock_columns`, stampo `articoli.uom_id`) | — | il BE lo esclude dal PATCH; la difesa vera è a DB |
| R-5 (opz.) | `fn_lookup_articoli`: filtro `p_gestito_a_magazzino` | Pezzo 3 (picker di riga più pulito) | senza, il picker propone articoli che il piano marcherà `NON_POSTABILE` |

---

## 8. Ordine dei passi, con chi fa cosa

| # | Passo | Chi | Prerequisito |
| --- | --- | --- | --- |
| 1 | **Pezzo 0** — un commit, CI verde | BE/FE | — |
| 2 | brief DB (R-1 … R-5) consegnato | BE/FE → DB | — |
| 3 | **Pezzo 1** — bootstrap; `magazzino.lotti` nel pannello config | BE/FE | — |
| 4 | **Pezzo 2** — repository/service/view parametrici, liste a catalogo, test DB provvisto, smoke | BE | R-2 per la mappa del duplicato (il resto no) |
| 5 | **Pezzo 4** — disponibilità e movimenti | BE + FE | — (indipendente da R-*) |
| 6 | **Pezzo 3** senza barra — lista, dialog, drawer, righe, piano | FE | — |
| 7 | **Pezzo 3** con barra — capability, «Registra», collaudo a video | FE | **R-1**, R-3 applicati e verificati live |
| 8 | doc (§9), aggiornamento di questo piano, poi `work-done/` | BE/FE | — |

**Copione di collaudo (passo 7)**, con un magazzino **a ubicazioni** e uno
**senza**, un articolo `gestito` semplice, uno `requires_lotto`, uno **non
gestito**: (a) inventario sul magazzino senza ubicazioni, riga 10 a 7 € →
`CONFIRM` → il piano si apre da solo con `INV_INIZIALE` → «Registra» → `POSTED`,
1 movimento in `movimenti/`, `disponibilita/` a 10; (b) secondo inventario che
conta 12 in UY sul magazzino a ubicazioni con merce in UX → il piano mostra
**`NON_CONTATA` per UX** (il caso di Tid, D-L2-n); (c) riga sull'articolo non
gestito → anteprima gialla nel form, piano `NON_POSTABILE`, «Registra» spento
col motivo (R-1) e, forzando via API, rifiuto con tutto in `CONFIRM`; (d)
riga senza lotto su `requires_lotto` → `E_MAG_LOTTO_OBBLIGATORIO` con il campo
acceso; (e) rettifica −5 → alla media, `disponibilita/` a 5; (f) operatore di
un altro emittente non vede il documento (404); (g) `POSTED` non si elimina né
si modifica; `CONFIRM → DRAFT` riapre le righe.

---

## 9. Documentazione da toccare

- `docs/it/backend/magazzino/manual/api_magazzino.md` — **una pagina per il
  dominio**, come `api_pagamenti.md`: le rotte, il documento interno come
  famiglia, il verbo `registra/` («una `SELECT`, il DB è la transazione»), la
  regola «il BE non ricalcola la riga: chiede i motivi al DB».
- `docs/it/dev/api.md` — la riga dell'inventario degli endpoint (sezione
  «Endpoint attivi») e, sotto §Capability di riga, la coppia
  `posting_blocco_reason`/`_reason_key` del piano (famiglia «riga»).
- cataloghi BB BE/FE — la famiglia parametrica, `FAMIGLIE` di `vocabolari.js`,
  `documentoInternoSeverity`, i tre lookup dedicati, la variante specializzata
  di `magazzino.magazzini`.
- `.codex/PROJECT_CONTEXT.md` — la riga di `magazzino` (da «BB del Lotto 2 in
  attesa di BE/FE» a «primo carico da video»).
- 🔵 al DB (nel brief): `_dominio-magazzino.md` §«Che cosa manca» toglie la
  riga di `requires_lotto` quando Pezzo 0 è mergiato.

---

## 10. Domande — ✅ tutte decise da Tid il 2026-09-18, sulla raccomandazione

| # | Domanda | Decisione |
| --- | --- | --- |
| **Q-1** | Inventario e rettifica come **una** implementazione parametrica (BE: `FamigliaDocumentoInterno`; FE: `FAMIGLIE` + componenti unici) o due copie? | ✅ **Una**, dichiarata in §4.1/§5.3: la seconda occorrenza è nota prima della prima, e il DB le ha già fatte una famiglia |
| **Q-2** | `PATCH` della testata fuori da `DRAFT`: il DB non lo vieta (il guard copre righe e stato). Il BE rifiuta `data`/`descrizione` su `POSTED`/`CANCEL`? Con quale codice? | ✅ **Libere**: il BE non aggiunge un guard che il DB non ha. ⛔ Non `E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA` su un'altra condizione (rubinetto B-7). `data` decide `data_mov` **al posting**; a video il form è readonly fuori da `DRAFT`. Se il DB vorrà congelarle, è un lucchetto suo (R-4, nota) |
| **Q-3** | La coerenza della riga (articolo gestito, lotto/seriale/ubicazione) al **salvataggio** della riga: il BE la lascia passare (il DB l'ammette in `DRAFT`, C8 b) e il form la **mostra** come anteprima; oppure il BE chiama `fn_check_riga_magazzino` e rifiuta con il primo motivo (400 + `campo`)? | ✅ **Passa e si mostra**: è ciò che il DB ha deciso (la riga in bozza è un fatto del conteggio; il piano la dichiara `NON_POSTABILE`). Un rifiuto nel BE sarebbe una regola più stretta del modello, scritta fuori dal DB |
| **Q-4** | La creazione da **dialog** (`ApriDocumentoInternoDialog`, come le distinte) invece che con l'auto-save bozza dei documenti di vendita | ✅ **Dialog**: tre campi, il magazzino è obbligatorio e decide il resto; una BB in meno da montare |
| **Q-5** | Il piano si apre **da solo** dopo `CONFIRM` (D-L2-n) — sempre, o solo se ci sono `NON_CONTATA`/`NON_POSTABILE`? | ✅ **Sempre**: è la fotografia contro cui si conferma, e la si vede una volta |

---

## 11. Registro

| Data | Cosa |
| --- | --- |
| 2026-09-18 (sera, poi) | ✅ **Pezzo 0, i messaggi** (§2.3, §2.4): `genera_error_policies` rigenerato dopo aver verificato che i 27 codici stessero nel CSV in git (PR #1605: DB e git allineati, diff = 27 aggiunte e basta); 27 ripieghi senza segnaposto in `error_messages_fallback.py` (blocco `E_MAG_*` riordinato alfabetico, i due del Lotto 1 dentro); 13 `reason_key` in `it.json`/`en.json` sotto la radice nuova `magazzino`. Verde: `--check`, `check_i18n_keys.py` a 0, `apps.core.tests` 1113 OK con `ZEROERP_TEST_DB_E2E=1`. Resta `requires_lotto` (§2.1, §2.2) |
| 2026-09-18 (sera) | ✅ **Q-1 … Q-5 decise da Tid**, tutte sulla raccomandazione: una famiglia parametrica BE e FE; testata libera fuori da `DRAFT` (nessuna regola nel BE, nota al DB in R-4); la riga incoerente passa e il form la mostra; creazione da dialog; piano aperto sempre dopo `CONFIRM`. Propagato in §0-bis, §4, §5, §8. Restano aperte solo R-1/R-2/R-3 lato DB |
| 2026-09-18 | **Nascita.** Letti il brief DB (chiuso), il catalogo vivo (`docs/it/dbzero/magazzino`), i precedenti (`pagamenti` come dominio più recente, `DistintaDrawer` del 18/09), i presidi (liste, codici, i18n). Misurato: CI rossa su tre fronti (modulo generato, ripieghi, 13 chiavi). Cinque pezzi, tre richieste DB bloccanti per parti diverse (R-1 il drawer, R-2 le righe, R-3 il gate), due opzionali. Cinque domande aperte, con raccomandazione |
