# Personalizzazioni liste — Piano operativo sviluppi differiti

**Modulo:** UI / Presentazione
**Riferimento principale:** [sviluppo-personalizzazioni-liste.md](sviluppo-personalizzazioni-liste.md)
**Stato Blocco F:** Fase 1 ATTERRATA 2026-05-08 (preset + permessi colonne in `/config/personalizzazioni-liste`). Fase 2 = DEF-5 residuo (vedi sotto).
**Aggiornato:** 2026-05-08

Questo documento e' la **roadmap operativa** degli sviluppi non implementati: per ogni DEF c'e' stato corrente, decisioni operative da chiudere prima di partire, struttura tecnica, dipendenze e stima sforzo. Quando un DEF atterra completamente va rimosso o spostato in changelog del WIP principale.

**Convenzione stima sforzo** (sviluppatore singolo, sessione full-stack):

- **S** = mezza giornata (~3-4h)
- **M** = 1 giornata (~6-8h)
- **L** = 2-3 giornate
- **XL** = oltre 3 giornate (richiede split o pianificazione approfondita)

**Convenzione stato:**

- 🔴 **Todo** — non iniziato
- 🟡 **Parziale** — qualcosa esiste (DB / BE / FE) ma incompleto
- 🟢 **Done** — implementato (item da rimuovere o archiviare)

---

## Sintesi roadmap

| # | Item | Stato | Sforzo | Priorita' | Dipende da |
|---|---|---|---|---|---|
| DEF-5b | Fase 2 Blocco F (CRUD `lista_definizione` + `lista_colonna` + `etichetta_i18n_key` UX) | 🟢 Done 2026-05-10 | L | — | — |
| DEF-8 | Estendere parametrizzazione ad altre liste (incrementale) | 🟡 Parziale (1/N done) | S per lista | **Alta** | Blocco F Fase 1 done |
| DEF-1 | Export CSV/Excel con metadati filtri | 🟢 Done 2026-05-10 | M | — | — |
| DEF-2 | Notifica "preset aggiornato" | 🟡 Parziale (DB pronto) | S | Media | Blocco D done |
| DEF-10 | Pattern formalizzato colonne composte FE-only | 🟡 Parziale (esiste come trick) | S | Media | DEF-5b o standalone |
| DEF-6 | Layout mobile / card list responsive | 🔴 Todo | M | Bassa | Blocco D done |
| DEF-3 | Viste nominate multiple per utente | 🔴 Todo | L | Bassa | Migration `lista_preferenza_utente` |
| DEF-4 | Condivisione viste tra utenti | 🔴 Todo | M | Bassa | DEF-3 |
| DEF-7 | Colonne calcolate lato client (`tipo_colonna='calcolata'`) | 🔴 Todo | L | Futura | Contratto formula stabile |

**Ordine consigliato di esecuzione**: DEF-8 (incrementale) → DEF-2 (chiude UX preset) → DEF-1 (export) → resto in base a richieste utenti. (DEF-5b atterrato 2026-05-10).

---

## DEF-1 — Export CSV/Excel con metadati filtri

**Stato:** 🟢 Done — atterrata 2026-05-10
**Sforzo:** M (consuntivo coerente con stima)

### Sintesi delivery

- **DB**: nessuna modifica.
- **Dipendenze**:
  - `openpyxl>=3.1` aggiunto a `backend/requirements.in` (autorizzazione Tid 2026-05-10), `requirements.txt` rigenerato via `pip-compile`.
  - Niente nuove dipendenze npm (riusa axios + composable core).
- **BE**:
  - 3 nuovi codici errore: `E_UI_EXPORT_LIMIT_EXCEEDED` (422), `E_UI_EXPORT_FORMAT_INVALID` (400), `E_UI_EXPORT_FAILED` (500).
  - Nuovo `apps/ui/services/lista_export_service.py` — **renderer puro no-fetch**: riceve righe + config colonne + filtri applicati, produce bytes CSV/XLSX. Filtri colonne automatici (escluse `tipo_colonna='azione'` e `esportabile=false`), ordina per `ordine_default`, hard cap `EXPORT_MAX_ROWS=10_000`. CSV con BOM UTF-8 + header `# Filtri applicati: {...}` JSON; XLSX con foglio "Dati" + foglio "Filtri applicati".
  - `ApiClientiExportView` (`apps/anagrafiche/api/views_clienti.py`): endpoint `GET /api/v1/anagrafiche/clienti/export/?format=csv|xlsx`. Riusa `ClientiService.list_clienti` con `limit=EXPORT_MAX_ROWS+1`, intercetta overflow pre-render via `total_count` window function, carica catalogo colonne da `UiRepository.list_colonne_by_codice('anagrafiche.clienti')` per coerenza con DataTable.
  - 12 test unit del renderer (`test_lista_export_service.py`): format invalido, hard cap, filtro azioni/non-esportabili, ordinamento, header filtri serializzato, BOM UTF-8, formati bool/None, fogli XLSX, filename safe.
- **FE**:
  - `exportClienti(params)` in `frontend/src/anagrafiche/api/anagrafiche.js` (axios `responseType: 'blob'`).
  - Nuovo composable `core/composables/useFileDownload.js` — building block riusabile per DEF-8: estrae filename da Content-Disposition (RFC 5987 + filename="..."), triggera download via `<a>` sintetico + `URL.createObjectURL/revokeObjectURL`, gestisce loading + errori via `useApiHandler`.
  - `ClientiSearchTable.vue` esteso: 2 nuove azioni `kind: 'utility'` nel `PageActionsBar` ("Esporta CSV", "Esporta Excel") con icone `pi pi-file` / `pi pi-file-excel`, riusano i filtri attivi (search/utility_id/stato_cliente_id). Su touch/tablet entrano nel kebab compact.
  - i18n IT+EN: 5 chiavi nuove in `lista_config` (`export_csv`, `export_csv_tooltip`, `export_xlsx`, `export_xlsx_tooltip`, `export_success`).
- **Doc**: `api_clienti.md` da estendere con endpoint export. `_def.md` DEF-1 → done.

### Decisioni operative chiuse 2026-05-10 (allineate alle raccomandazioni)

1. **Libreria Excel**: openpyxl. Tid autorizza l'aggiunta a `requirements.in`.
2. **Endpoint shape**: dedicato per dominio (`/anagrafiche/clienti/export/`). Refinement architetturale: il modulo `ui` espone solo il **renderer generico** (no SQL dinamico sulla `vista_sql` per evitare rischi injection); ogni dominio adotta il pattern estendendo il proprio repository esistente. Coerente con la decisione "endpoint dedicato" + più sicuro + riusabile in DEF-8.
3. **Limite righe**: hard cap sincrono 10.000. Async polling rinviato a DEF separato se emerge esigenza enterprise.
4. **Filtri leggibili**: raw JSON nell'header CSV (`# Filtri applicati: {...}`) e nel foglio "Filtri applicati" del XLSX. Dispatcher per tipo (es. `stato_id=3 → "ATTIVO"`) rinviato.

### Note implementative

- Il renderer è **no-fetch**: separa rendering da query. Il dominio (clienti, fornitori, articoli, ...) chiama il proprio repository per ottenere righe, poi delega a `ListaExportService.render(...)`. Niente SQL dinamico, zero rischio injection.
- Per estendere l'export ad altre liste in DEF-8 basta replicare il pattern di `ClientiExportView` (~30 righe per lista) + bottoni nel componente search table (~10 righe).
- Il pre-check overflow via `total_count` window function evita di serializzare 10.001+ righe per poi rifiutare: il check è sull'integer ritornato dalla query stessa, costo zero.
- BOM UTF-8 nel CSV è critico per evitare mojibake al doppio click su Windows (Excel di default decodifica come Windows-1252).

---

## DEF-2 — Notifica "preset aggiornato"

**Stato:** 🟡 Parziale — DB completamente pronto, manca BE + FE
**Sforzo:** S

### Cosa serve

Quando un admin modifica un preset di base (sistema/ruolo/emittente), gli utenti che hanno una preferenza salvata da quel preset devono vedere un banner non intrusivo: *"La configurazione del tuo ruolo e' stata aggiornata. Vedi novita'?"*. Click → modale personalizzazione con colonne nuove evidenziate.

### Stato attuale

- ✅ DB: campo `lista_preferenza_utente.preset_base_data_update` (snapshot) + trigger `trg_ui_lista_preferenza_utente_z90_clear_preset_base_ts_upd` (azzera lo snapshot quando cambia il `preset_base_id`) — landed Blocco B/F.2.
- ✅ BE write: `ListaPreferenzaService.upsert` calcola e salva lo snapshot a ogni save (vedi `apps/ui/db/ui_repository.py:get_preset_base_snapshot`).
- ❌ BE read: `ui.fn_resolve_lista_config` (o `UiService.get_lista_config`) NON espone oggi il flag `preset_aggiornato` nella response.
- ❌ FE: nessun banner.

### Decisioni operative aperte

1. **Logica calcolo flag**: lato fn DB (modifica `fn_resolve_lista_config` per JOIN su `lista_preset.data_update` + confronto) oppure lato Python (`UiService.get_lista_config` aggiunge il campo dopo che la fn ha risolto)? La prima e' coerente col pattern DB-first, la seconda e' piu' veloce da implementare.
2. **Comportamento dopo click "Vedi novita'"**: l'utente vede le colonne nuove nella modale; al save l'`preset_base_data_update` si riallinea al `lista_preset.data_update` corrente. Se preme "Ignora": resettiamo lo snapshot? (Pro: badge non riappare. Contro: utente puo' perdere visibilita' su altre future modifiche del preset.) Proposta: "Ignora" salva un timestamp tombstone separato (campo nuovo `preset_aggiornato_ignored_at`) per non confondere lo snapshot funzionale. Decidere.
3. **UX banner**: posizione (top toolbar / dentro modale toolbar / toast)? PrimeVue `Message` inline o componente custom?

### Architettura

- **DB**: opzionalmente nuovo campo `preset_aggiornato_ignored_at TIMESTAMP NULL` su `lista_preferenza_utente` se decidiamo di tracciare l'ignore (vedi decisione 2). Brief team DB minimo. Aggiornare `ui.fn_resolve_lista_config` se decidiamo opzione 1 (decisione 1).
- **BE**: estendere il JSONB di response con `preset_aggiornato: bool`. Guard: `preferenza.preset_base_id IS NOT NULL AND preferenza.preset_base_data_update IS NOT NULL AND preset_corrente.data_update > preferenza.preset_base_data_update`.
- **FE**: composable `useListaConfig` espone `presetAggiornato`. `ListaConfigurabile` (o caller) renderizza un banner con CTA. Modale "Personalizza colonne" evidenzia le colonne aggiunte/modificate dopo lo snapshot.

### Dipendenze

- Blocco F.2 atterrato (snapshot trigger) — done.
- Blocco D (modale personalizzazione) — done.

---

## DEF-3 — Viste nominate multiple per utente

**Stato:** 🔴 Todo
**Sforzo:** L

### Cosa serve

Oggi `lista_preferenza_utente` ha `UNIQUE (auth_user_id, lista_id)` → 1 sola preferenza per lista. Vogliamo permettere viste nominate ("Clienti morosi", "Clienti TOP", "Vista rapida") con switch rapido.

### Decisioni operative aperte

1. **Schema migration**: aggiungere colonne `nome VARCHAR(80)` + `is_attiva BOOLEAN` su `lista_preferenza_utente`. Sostituire UNIQUE con `(auth_user_id, lista_id, nome)` + partial UNIQUE `is_attiva=TRUE` per coppia `(auth_user_id, lista_id)`. Dati esistenti: backfill `nome='Default'`, `is_attiva=true`.
2. **Limite viste**: hard cap (es. 10 per lista per utente)? Soft warning?
3. **Pattern UX**: selettore viste `<Select>` nella toolbar, accanto al bottone Personalizza? Salvataggio rapido "Salva come..." con copia profonda?

### Architettura

- **DB**: migration `lista_preferenza_utente` (aggiunge colonne + cambia UNIQUE + backfill). Brief team DB significativo.
- **BE**: nuovi endpoint `GET/POST/PUT/DELETE /api/v1/ui/liste/{codice}/preferenze[/{id}]`. Endpoint config attuale serve la vista attiva.
- **FE**: selettore viste in toolbar (probabilmente building block nuovo `ListaViewSelect.vue`). Drawer "Salva come..." con campo nome.

### Dipendenze

- Migration tabella popolata in produzione → richiede pianificazione attenta.

---

## DEF-4 — Condivisione viste tra utenti

**Stato:** 🔴 Todo
**Sforzo:** M

### Cosa serve

Un team lead crea una vista personalizzata e la condivide con i colleghi del reparto. I colleghi possono "adottarla" (copia personale modificabile).

### Decisioni operative aperte

1. **Scope condivisione**: solo reparto (`unita_organizzativa_id`) o anche per profilo accesso? O entrambi?
2. **Modifica vista condivisa**: solo l'autore puo' modificarla? O anche admin del reparto? Quando l'autore modifica, le copie adottate cambiano automaticamente o restano fissate al momento dell'adozione?
3. **Visibilita' della vista in dismissione**: se l'autore lascia il reparto, le viste condivise restano? Trasferite a chi?

### Architettura

- **DB**: aggiungere `autore_auth_user_id`, `visibile_reparto BOOLEAN`, `unita_organizzativa_id` (nullable) a `lista_preferenza_utente`.
- **BE**: logica visibilita' (read-only sulle viste pubbliche del reparto) + endpoint "adotta" (copia profonda).
- **FE**: sezione "Viste condivise" nella modale + flag "Condividi con il reparto" sul save.

### Dipendenze

- **DEF-3** (viste nominate) e' prerequisito hard.

---

## DEF-5 — Admin UI per gestione preset e catalogo (assorbito da Blocco F)

**Stato Fase 1:** 🟢 Done — atterrata 2026-05-08 (preset + permessi colonne sotto `/config/personalizzazioni-liste`)
**Stato Fase 2:** 🔴 Todo — vedere **DEF-5b** sotto.

Il piano dettagliato vive in [sviluppo-personalizzazioni-liste.md §11.F](sviluppo-personalizzazioni-liste.md). Il paragrafo originale di DEF-5 e' archiviato; questo item esiste oggi solo per la **parte Fase 2** non ancora implementata, riformulata come DEF-5b.

---

## DEF-5b — Fase 2 Blocco F: CRUD `lista_definizione` + `lista_colonna`

**Stato:** 🟢 Done — atterrata 2026-05-10
**Sforzo:** L (consuntivo coerente con stima)

### Sintesi delivery

- **DB**: nessuna modifica (tabelle / ENUM / trigger / CHECK gia' pronti dal Blocco A + F.2).
- **BE** (`apps/ui/`):
  - 6 nuovi codici errore in `error_policies.py`: `E_UI_DEFINIZIONE_VALIDAZIONE` / `_NON_TROVATA` / `_IN_USO`, idem per colonna.
  - `ui_admin_repository.py` esteso: `list_definizioni_admin`, `get_definizione_admin`, `create/update/delete_definizione`, `list_colonne_by_lista_admin`, `get_colonna_admin`, `create/update/delete_colonna`, `count_preferenze_referenced_by_colonna`.
  - `lista_definizione_admin_service.py` esteso con CRUD Fase 2 (read Fase 1 invariata).
  - `lista_colonna_admin_service.py` nuovo file con UX vincoli (silently force `esportabile=false` su `tipo_colonna='azione'`, soft-block DELETE su preferenze utente).
  - `views_admin.py` esteso: `ApiAdminListaDefinizioneAdmin{Detail,}View` + `ApiAdminListaColonna{List,Detail}View` su base `AdminAPIView`.
  - `urls.py`: 4 route nuove (`/admin/definizioni/`, `/admin/definizioni/<id>/`, `/admin/definizioni/<lista_id>/colonne/`, `/admin/colonne/<id>/`).
  - 39 test unit aggiunti (16 definizione + 23 colonna). Suite ui: 93/93 verdi.
- **FE** (`src/ui/`):
  - 8 nuovi endpoint client in `core/api/ui-admin-api.js`.
  - 2 store Pinia user-scoped: `uiDefinizioneAdmin.js`, `uiColonnaAdmin.js`.
  - 4 componenti: `ListaDefinizionePanel.vue`, `ListaDefinizioneDrawer.vue`, `ListaColonnaPanel.vue`, `ListaColonnaDrawer.vue` (drawer colonna split 3 sotto-tab Generale/Comportamento/Layout).
  - 1 view contenitore: `PersonalizzazioniListeTecnicheView.vue` con TabView lazy.
  - Rotta `/amm-software/personalizzazioni-liste-tecniche` + voce sidebar `adminOnly: true`.
  - 2 nuovi `TAB_ENTITIES` (`UI_DEFINIZIONE`, `UI_COLONNA`).
  - i18n IT+EN: 56 chiavi nuove (testata + sidebar + enum tipo_colonna/tipo_dato/allineamento).
- **Doc**: `api_ui_admin_personalizzazioni.md` esteso con endpoint §12-§21 + nota di migrazione Fase 2.

### Decisioni operative chiuse 2026-05-10 (allineate al piano originale)

1. **Validazione `vista_sql` (originale)**: Opzione A — niente relax trigger, workflow draft "vista DDL prima, registra dopo" supportato nativamente dal trigger (skippa quando `attivo=false` o `vista_sql=null`).
2. **Cancellazione con preferenze attive (originale)**: errore parlante via FK RESTRICT (`E_UI_DEFINIZIONE_IN_USO`) + soft-disable disponibile via PATCH `attivo=false`.
3. **UX `etichetta_i18n_key` (originale)**: due input separati `etichetta` (fallback letterale) + `etichetta_i18n_key`. Autocomplete chiavi rinviato a DEF-9b.
4. **Permesso CRUD (originale)**: SUPER_ADMIN unico via `IsAdminZeroERP` (`AdminAPIView`). Niente nuove azioni di processo.
5. **DELETE colonna con preferenze**: soft-block applicativo (count JSONB `configurazione->colonne` per codice) — bloccare con `E_UI_COLONNA_IN_USO`, soft-disable raccomandato.
6. **CHECK `azione_non_esportabile`**: drawer disabilita e forza off il toggle `esportabile` quando `tipo_colonna='azione'`; service silently normalizza in create+update per evitare errore tardivo dal CHECK DB.
7. **Editing `vista_sql` su lista esistente**: ammesso (no blocco), il trigger fa il check sulla nuova vista in pg_catalog.
8. **Riordino colonne**: drawer split in 3 sotto-tab (Generale / Comportamento / Layout) per gestire i 17 campi senza affollare il form. Riordino via `ordine_default` editabile (drag&drop futuro).

### Cosa serve

Permettere a SUPER_ADMIN di gestire via UI le 2 tabelle tecniche dello schema `ui`:

- `ui.lista_definizione` — registra le liste configurabili (codice, descrizione, schema_dati, vista_sql, attivo)
- `ui.lista_colonna` — catalogo colonne disponibili per ogni lista (etichetta, etichetta_i18n_key, campo_sorgente, tipo_colonna enum, tipo_dato enum, formato, larghezza_default, ordine_default, allineamento, gruppo, gruppo_ordine, filtrabile, ordinabile, esportabile, ricercabile_full, sensibile, attivo)

Oggi entrambe sono gestite solo via seed CSV → ogni nuova lista richiede un PR DB. Con questo CRUD un super-admin puo' aggiungere una colonna nuova o registrare una nuova vista SQL senza deploy.

### Decisioni operative aperte

1. **Validazione `vista_sql`**: il trigger DB `trgfn_ui_lista_definizione_a10_valida_vista_sql` blocca se la vista non esiste. Workflow proposto:
   - Opzione A: il super-admin crea la vista SQL DIRETTAMENTE in DB (script di migrazione separato), poi registra il record `lista_definizione` via UI. Niente relax del trigger.
   - Opzione B: relax temporaneo del trigger (skip su `attivo=false`) per permettere `INSERT` come "draft" + UPDATE successivo. Piu' permissivo ma rischia stati incoerenti.
   - **Raccomandazione**: A (defense-in-depth, vista SQL e' DDL e va in changeset Liquibase).

2. **Cancellazione `lista_definizione` con preferenze utente attive**:
   - Verificare DDL Blocco A: oggi probabilmente RESTRICT su `lista_preferenza_utente`. Se RESTRICT, l'admin non puo' eliminare → soft-disable via `attivo=false` e basta? Oppure cascade delete con avviso?
   - **Raccomandazione**: bloccare DELETE se `EXISTS preferenze` con messaggio parlante "Lista in uso da N utenti, prima resetta le loro preferenze o disattiva la lista". Aggiunta soft-disable via `attivo=false`.

3. **Gestione `etichetta_i18n_key` nel form `lista_colonna`** (DEF-9 candidato — vedi sotto):
   - Opzione A: due input separati `etichetta` (italiana letterale, fallback) + `etichetta_i18n_key` (chiave i18n testo libero).
   - Opzione B: solo `etichetta_i18n_key` con autocomplete dalle chiavi esistenti nei locales `it.json`/`en.json`. Manca un'API che le esponga.
   - **Raccomandazione**: A in Fase 2 (semplice). B come DEF separato dopo se serve UX.

4. **Permesso CRUD definizioni**: SUPER_ADMIN unico (`IsAdminZeroERP`) o nuova azione di processo `ui_definizione_manage` per delegare a "tecnici" non super-admin?
   - **Raccomandazione**: SUPER_ADMIN unico in Fase 2 (le viste SQL sono comunque DDL, deve farle un super-admin). Eventuale split successivo se emerge esigenza.

### Architettura

- **DB**: nessuna modifica. Le tabelle esistono dal Blocco A. `etichetta_i18n_key` aggiunta in Blocco F.2.
- **BE** (`apps/ui/`):
  - `services/lista_definizione_admin_service.py` — CRUD su `lista_definizione` con `PayloadValidator`, mapping IntegrityError per UNIQUE codice, RESTRICT su DELETE con preferenze
  - `services/lista_colonna_admin_service.py` — CRUD su `lista_colonna` con whitelist enum (`tipo_colonna`, `tipo_dato`, `allineamento`), gestione `campo_sorgente=NULL` per colonne calcolate FE
  - `db/ui_admin_repository.py` esteso con metodi su `lista_definizione` + `lista_colonna`
  - `api/views_admin.py` esteso: 8-10 endpoint nuovi (`/admin/definizioni/`, `/admin/definizioni/<id>/`, `/admin/definizioni/<id>/colonne/`, `/admin/colonne/<id>/`)
  - Permission `IsAdminZeroERP` (nessun nuovo `*_permission`)
  - Test unitari in `apps/ui/tests/services/`
- **FE** (`src/ui/` esteso):
  - `views/PersonalizzazioniListeTecnicheView.vue` (sotto amm-software) con TabView 2 tab "Definizioni" + "Catalogo colonne", master-detail su definizione corrente
  - `components/ListaDefinizionePanel.vue` + `ListaDefinizioneDrawer.vue` (testata definizione)
  - `components/ListaColonnaPanel.vue` + `ListaColonnaDrawer.vue` (catalogo colonne filtrato per definizione_id, drawer ricco con tutti i 17 campi di `lista_colonna`)
  - Stores Pinia: `uiDefinizioneAdmin.js` + `uiColonnaAdmin.js`
  - i18n IT/EN: ~30 chiavi nuove
  - Voce sidebar `amm-software/personalizzazioni-liste-tecniche` (`adminOnly: true`)
  - Rotta `/amm-software/personalizzazioni-liste-tecniche`

### Dipendenze

- Blocco F Fase 1 atterrato — done.
- Etichetta_i18n_key landed Blocco F.2 — done.

### Note implementative

- I trigger DB B1/B2 (`trgfn_*_a10_valida_vista_sql`, `trgfn_*_a10_valida_campo_sorgente`) restano la guardia finale. Niente validazione Python aggiuntiva.
- L'attuale `defineExpose` con auto-unwrap (vedi memoria post Blocco F): nei nuovi componenti rispettare il pattern senza `.value` extra dal parent.

---

## DEF-6 — Layout mobile / card list responsive

**Stato:** 🔴 Todo
**Sforzo:** M

### Cosa serve

`<ListaConfigurabile>` oggi e' DataTable desktop. Su viewport stretto (mobile/tablet portrait) una tabella con 8+ colonne e' inutilizzabile. Servirebbe modalita' card list automatica.

### Decisioni operative aperte

1. **Breakpoint switch**: < 640px? < 768px? Configurabile in `BREAKPOINTS` di `constants.js`?
2. **Quali colonne mostrare nella card**: solo `tipo_colonna='identificatore'` + prime N (configurabile)? O lasciare all'utente via modale separata?
3. **Personalizzazione colonne su mobile**: drag&drop non e' fattibile su touch, restano solo toggle visibilita'?

### Architettura

- **DB/BE**: nessuno.
- **FE**: nuova modalita' di rendering in `<ListaConfigurabile>` (computed `useCardLayout = ui.isMobile`). CSS responsive in `main.css`. Modale personalizzazione semplificata (solo toggle, no riordino).

### Dipendenze

- Blocco D done.

---

## DEF-7 — Colonne calcolate lato client

**Stato:** 🔴 Todo
**Sforzo:** L

### Cosa serve

Alcune informazioni utili non esistono come colonne nella view SQL ma si derivano (es. "giorni alla scadenza" = `CURRENT_DATE - data_scadenza`). Pattern proposto: nuovo `tipo_colonna='calcolata'` + campo `formula_client VARCHAR` con chiave funzione registrata nel composable Vue.

### Decisioni operative aperte

1. **Contratto formula stabile**: come si registrano le formule? Mappa centralizzata `formulaRegistry = { 'giorni_scadenza': (row) => ..., 'mesi_attivo': (row) => ... }`? Per dominio? Globale?
2. **Esportabilita'**: le calcolate sono esportabili? Se si', la formula va valutata anche in BE (replicarla? troppo costoso). Se no, comportamento simmetrico a `tipo_colonna='azione'`.
3. **Ordinabilita'**: se i dati sono lato FE-only, ordinare richiede calcolare per tutte le pagine — non scalabile su LIMIT/OFFSET. Ipotesi: calcolate `ordinabile=false` per default.

### Architettura

- **DB**: aggiungere `tipo_colonna='calcolata'` al CHECK enum, aggiungere colonna `formula_client VARCHAR(80) NULL` a `lista_colonna`.
- **BE**: nessuna nuova logica (la fn DB include la riga; il rendering e' tutto FE).
- **FE**: registry formule per dominio, `<ListaConfigurabile>` riconosce `tipo_colonna='calcolata'` e applica la formula.

### Dipendenze

- DEF-5b atterrato (per editare le calcolate via UI; altrimenti solo via seed CSV).

### Note di sovrapposizione con DEF-10

DEF-10 propone formalizzazione di **colonne composte FE-only** (`campo_sorgente=NULL`, `tipo_colonna='informazione'`) — pattern leggermente diverso ma sovrapposto. Da fondere o tenere distinti dopo decisioni:

- DEF-7: colonna nuova creata FE da formula (es. "giorni scadenza")
- DEF-10: colonna FE che fonde 2+ campi BE in una resa custom (es. `sosp_riatt` clienti)

Differenza chiave: DEF-7 calcola, DEF-10 compone. Implementativamente entrambi finiscono nello slot `cell-{codice}` del caller. Forse fonderli in **DEF-7+10 unico** con due sotto-categorie (`'calcolata'` e `'composta'`) e' piu' pulito.

---

## DEF-8 — Seed catalogo per altre liste (incrementale)

**Stato:** 🟡 Parziale — 1 lista migrata su N
**Sforzo:** S per lista

### Cosa serve

Estendere il pattern Blocco E (atterrato per `anagrafiche.clienti`) ad altre liste del frontend. Per ogni lista:

1. CSV seed `ui.lista_colonna` (catalogo colonne)
2. CSV seed `ui.lista_preset` + `ui.lista_preset_colonna` (preset di sistema con visibilita' di default)
3. Backend: aggiungere `etichetta_i18n_key` ai metadati colonna (gia' lo fa post-F.2)
4. Frontend: migrare `<DataTable>` statico a `<ListaConfigurabile>` con paginator-options pattern + slot custom per celle complesse

### Stato attuale liste

| Lista | Componente attuale | Migrata? |
|---|---|---|
| `anagrafiche.clienti` | ClientiSearchTable.vue | 🟢 Done (Blocco E5) |
| `anagrafiche.fornitori` | FornitoriSearchTable.vue | 🔴 Todo |
| `anagrafiche.soggetti` | SoggettiSearchTable.vue | 🔴 Todo |
| `anagrafiche.indirizzi` | IndirizziSearchTable.vue | 🔴 Todo |
| `catalogo.articoli` | ArticoliSearchTable.vue | 🔴 Todo |
| `catalogo.unita-misura` | UnitaMisuraSearchTable.vue | 🔴 Todo |
| `vendite.preventivi` | PreventiviSearchTable.vue | 🔴 Todo |
| `vendite.contratti` | ContrattiSearchTable.vue | 🔴 Todo |
| `vendite.listini` | ListiniSearchTable.vue | 🔴 Todo |
| `vendite.promo-articoli` | PromoArticoliListView.vue | 🔴 Todo |
| `vendite.approvazioni-prezzo` | ApprovazioniPrezzoSearchTable.vue | 🔴 Todo |
| `pratiche` | PraticheDashboard.vue | 🔴 Todo |

12 liste residue. Ordine suggerito per impatto utente:
1. `anagrafiche.fornitori` (gemello di clienti, codice gia' rodato)
2. `catalogo.articoli` (lista molto frequente)
3. `vendite.contratti` (operatori vendita la usano spesso)
4. `vendite.preventivi`
5. Resto in ordine di ticket / richieste utenti

### Decisioni operative aperte (per ogni lista)

1. **Etichette i18n**: riusare chiavi i18n esistenti (es. `fornitori.col_*`) o crearne nuove `lista.{codice}.col_*`?
2. **Preset di sistema**: quale set di colonne visibili di default (vedi pattern clienti)?
3. **Backend espone tutti i campi necessari?**: alcuni campi calcolati (es. `id_fiscale_univoco_cf_piva` dei clienti) potrebbero richiedere modifica al SELECT del repository.

### Architettura per ogni lista

- **DB**: 1 brief team DB per CSV seed `lista_colonna` + `lista_preset_colonna` di sistema. Pattern rodato post Blocco F.2.
- **BE**: eventuale aggiunta campi composti al SELECT del repository (es. `id_fiscale_univoco_cf_piva`).
- **FE**: refactor SearchTable component:
  - Usa `<ListaConfigurabile>` con `paginator-options="paginatorProps"` di `useSearchTable`
  - Espone `openModal` via `defineExpose`-unwrap pattern (memoria sessione precedente)
  - Toolbar esterna unica con `PageActionsBar` (refresh + personalizza-colonne + nuovo + altre azioni dominio)
  - Slot `cell-{codice}` per celle complesse (Tag stato severity, fallback CF/PIVA, date composte)

### Dipendenze

- Blocco F Fase 1 atterrato — done.
- Per liste con campi calcolati: DEF-7+10 (oppure soluzione ad-hoc come `sosp_riatt`).

---

## DEF candidati emersi durante Blocco F (2026-05-08)

Sviluppi nuovi proposti durante l'implementazione Blocco F. Da promuovere a DEF numerati o assorbire in DEF esistenti.

### DEF-9 candidato — UX `etichetta_i18n_key` nel form admin

**Contesto:** Blocco F.2 ha aggiunto `ui.lista_colonna.etichetta_i18n_key`. Oggi e' valorizzato solo via seed CSV. Quando arriva DEF-5b (CRUD `lista_colonna`), serve UX coerente per il super-admin.

**Proposta:** assorbire in DEF-5b, decisione operativa 3.

**Piu' avanzato:** API che espone le chiavi i18n disponibili (`GET /api/v1/core/i18n/keys?prefix=clienti.col_`) con autocomplete nel drawer. Item separato (DEF-9b?) se emerge necessita'.

### DEF-10 candidato — Pattern formalizzato colonne composte FE-only

**Contesto:** la colonna `sosp_riatt` di `anagrafiche.clienti` e' una composta FE-only (`campo_sorgente=NULL`, slot custom `cell-sosp_riatt` calcola da 2 date). Trigger guard ammette `campo_sorgente IS NULL` post Blocco F.2.

**Proposta:** vedere sezione "Note di sovrapposizione con DEF-10" in DEF-7. Decidere se fondere (DEF-7+10) o tenere distinti.

---

## Convenzioni acquisite durante Blocco F (memoria)

Pattern e regole emersi durante Blocco F + refactor toolbar 2026-05-08, da rispettare nei prossimi DEF:

1. **Pattern lista standard** (frontend-standards.md §"Pattern lista") + `<ListaConfigurabile>`:
   - Toolbar UNICA esterna del caller con `PageActionsBar` (no toolbar interna del componente)
   - `paginatorOptions="paginatorProps"` di `useSearchTable` (paginator top, JumpToPageDropdown, 1/N, rowsPerPageOptions)
   - Slot `cell-{codice}` per celle custom; default formatter da `formato` per i tipi standard

2. **`<defineExpose>` auto-unwrap**: i ref esposti via `defineExpose({ config, dirty })` sono auto-unwrappati dal parent. NO `.value` extra: `listaRef.value.config`, NON `listaRef.value.config.value`.

3. **Catalogo eager**: `useListaConfig.load()` carica config + catalogo in parallelo. Senza catalogo le etichette/i18n/`campo_sorgente` non sono disponibili al primo render.

4. **i18n etichette**: `etichetta_i18n_key` nel catalogo + risoluzione FE con `t() || etichetta || codice` (cascata fallback safe). Le keys vivono in `clienti.col_*`, `lista.{codice}.*`, `common.*` a seconda del contesto.

5. **Pattern responsive azioni**: tutte le azioni di lista (refresh, personalizza colonne, ecc.) vanno nel `PageActionsBar` con `kind: 'utility'`. Su touch/tablet vanno nel kebab compact automaticamente. Solo `kind: 'primary'` (es. "Nuovo") resta sempre visibile.

6. **Drift risk enum DB ↔ Python**: `_AMBITI_AMMESSI` / `_LIVELLI_AMMESSI` etc. duplicano enum DB per filtro early. DB e' single source di verita' (FK enum guard finale).

7. **`user_label` helper condiviso**: estratto in `apps/ui/services/_audit.py` per audit fields `user_insert`/`user_update` (riusabile da nuovi service admin).

8. **Decisione 1 entry-point UI in Fase 1**: la pagina `/config/personalizzazioni-liste` e' unica. Quando atterra Fase 2 (DEF-5b), si crea view dedicata sotto `/amm-software/personalizzazioni-liste-tecniche` separata semanticamente.
