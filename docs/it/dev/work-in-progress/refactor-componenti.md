# Refactor Componenti BoM — Piano operativo BE/FE

> **Scope**: piano operativo corrente. Nessuna decisione di dominio
> qui — quelle stanno nel modello.
>
> **Riferimenti obbligatori**:
>
> - Modello logico: [`manual/modello-componenti-bom.md`](../manual/modello-componenti-bom.md)
> - Changelog decisioni: [`manual/changelog-decisioni-componenti.md`](../manual/changelog-decisioni-componenti.md)
> - Brief DB principale: [`brief-db-componenti-modello-unificato.md`](brief-db-componenti-modello-unificato.md)
> - Brief DB fix operatore JSONB: [`brief-db-fix-jsonb-key-exists-init-componenti.md`](brief-db-fix-jsonb-key-exists-init-componenti.md)

## 1. Stato corrente (snapshot 2026-05-13)

### DB ✅

- Atterrate migration 20260513-01..24 (modello unificato): rollback gate `esposto_in_fattura`, rilassamento CHECK `<> 0`, guard obbligatorio non disattivabile, errore `E_DOC_COMPOSITO_BOM_VUOTA`, coerenza IVA padre-figli (trigger catalogo), tabella `vendite.listini_righe_componenti`, resolver bundle-aware `fn_resolve_prezzo_listino_v2(... p_articolo_padre_contesto)`, DEPRECATION `fn_resolve_prezzo_composito` (COMMENT only, no DROP)
- Atterrate migration 20260513-29..32: fix operatore JSONB `?` (era `??`) + default `attivo=TRUE` sempre nelle 4 fn `*_init` (decisione "BoM contratto immutabile" 2026-05-13)
- Backfill: BoM IVA incoerenti + righe listino su compositi pre-esistenti applicato
- pgTAP per i 4 nuovi guard in esecuzione

### BE preventivi ✅

- Repository: `init_componenti_riga` accetta `componenti_attivazioni` + `componenti_overrides`; `preview_componenti_riga` proietta `obbligatorio` + `esposto_in_fattura`; `list_componenti_riga(solo_attivi=True/False)` con JOIN `articoli_componenti`; helper `is_articolo_composito` per default prezzo padre composito
- Service `gestisci_riga`: prezzo padre composito = `Decimal(0)` placeholder (trigger DB ricalcola); `aggiorna_riga` rifiuta con 422 payload con `componenti_*`; nuovo `_normalize_componenti_attivazioni` bool-only
- API: endpoint POST riga estende schema con `componenti_overrides` + `componenti_attivazioni`; GET componenti riga accetta `?solo_attivi=false`
- Tests: 677/677 verdi (+11 nuovi cumulativi B+C+D+E)

### FE preventivi ✅

- `ComponentiDialog.vue` building block in `vendite/_shared/componenti/` (riusabile dalle 4 sorgenti via prop `apiPreview` + `documentoId`); i18n namespace `vendite.componenti.*` shared; summary scalato live con `qtaPadre` snapshot
- Integrato in `PreventiviRigaForm.vue`: auto-open Dialog su lookup composito + bottone "Modifica componenti" per revisioni; bottoni Salva/Annulla del PreventiviDrawer testata si nascondono durante edit-riga via emit `form-aperto` (pattern distinta base BoM)
- `PreventiviRigaComponentiPanel.vue` (EDIT): 3 colonne nuove (Obbligatorio tag, Attivo checkbox toggle, In fattura Sì/No tag); cella prezzo Column 260px + InputNumber 200px (no più sovrapposizione con Origine); validazione FE prezzo=0 obbligatori; loading guard durante PATCH; `LISTINO_BUNDLE` mappato in severity + i18n; `PRICE_EPSILON` centralizzato

### Expansion BE→commessa ✅

- `BoMComponentExpander`: snapshot loader preventivi via `list_componenti_riga(solo_attivi=True)` (modello unificato: filtra opzionali disattivati); `esposto_in_fattura` letto dalla proiezione reale (era hardcoded `True`); commenti CASO A/B aggiornati
- `resolve_prezzo_composito` (repo + service): DEPRECATED + `DeprecationWarning` runtime + TODO rimozione Fase G
- Cache `_resolve_cached` include `uom_id` nella key (bug pre-esistente latente fixato)

### Altre sorgenti (ordini / contratti / ddt)

- DB tabelle + trigger + fn `_init`/`_preview` atterrate (simmetria modello unificato)
- BE: non avviato (Fase G)
- FE: non avviato (Fase G)

## 2. Piano operativo per fasi

### Fase A — Brief DB modello unificato ✅ done 2026-05-13

Migration `20260513-01..24` applicate dal team DB. Sbloccate tutte le fasi successive.

### Fase B — BE preventivi ✅ done 2026-05-13

`componenti_overrides` + `componenti_attivazioni` su `init_componenti_riga`; preview con `obbligatorio` + `esposto_in_fattura`; guard 422 su PATCH riga; +6 test.

### Fase C — FE preventivi nuovo `ComponentiDialog.vue` ✅ done 2026-05-13

Dialog building block in `vendite/_shared/componenti/`; i18n `vendite.componenti.*`; integrato in `PreventiviRigaForm`. Tabella inline preview rimossa.

### Fase D — EDIT path `PreventiviRigaComponentiPanel.vue` ✅ done 2026-05-13

3 colonne nuove (Obbligatorio/Attivo/Esposto), validazione FE prezzo=0 obbligatori, delete diventa toggle attivo, `solo_attivi=false` per mostrare opzionali disattivati. Bottoni testata drawer si nascondono durante edit-riga via emit `form-aperto`.

**Decisione aperta non implementata**: gating L1 su `componenti_attivazioni` (oggi nessun check permessi su attiva/disattiva opzionali, solo guard DB su obbligatori). Lasciato non implementato — è decisione operativa non economica.

### Fase E — Censimento + expansion BE→commessa ✅ done 2026-05-13

`BoMComponentExpander` allineato al modello unificato: snapshot loader filtra `attivo=TRUE`, `esposto_in_fattura` letto reale, `resolve_prezzo_composito` legacy DEPRECATED. Cache key fixata con `uom_id`. Pipeline `fatture_righe` da `commesse_attivita` invariata (verifica in Fase F).

### Fase F — Smoke UI utente §3.4 — APERTA

**Blocco corrente**: il path overrides è bloccato dal bug DB `??` → `?` operatore JSONB nelle 4 fn `*_init` (vedi [`brief-db-fix-jsonb-key-exists-init-componenti.md`](brief-db-fix-jsonb-key-exists-init-componenti.md)). Smoke completi possibili solo dopo fix DB.

Workaround: scenari senza override (resolver pricing valorizza tutto) funzionano oggi.

4 scenari pianificati su `sviluppo-listini-v5-test-ui.md` §3.4:

- F.1 — padre con solo obbligatori, tutti con listino → save senza override
- F.2 — padre con obbligatori + opzionali, operatore attiva 1 opzionale, prezzo manuale su 1 obbligatorio → save con `componenti_overrides` + `componenti_attivazioni`  *(richiede fix DB JSONB)*
- F.3 — padre con BoM scaduta → errore parlante `E_DOC_COMPOSITO_BOM_VUOTA`
- F.4 — listino bundle vs standalone: due preventivi a date diverse mostrano prezzi diversi se cambia `listini_righe_componenti`

Stima: 1 sessione (post fix DB).

### Fase G — Replicazione 4 sorgenti (ordini / contratti / ddt) — PARZIALE

Pattern preventivi replicato simmetricamente. Una sessione per sorgente:

- BE: repo + service + API + types + tests
- FE: riuso `ComponentiDialog.vue` con `apiPreview` sorgente-specific; drawer riga sorgente segue stesso pattern preventivi
- Smoke specifico per sorgente

**Priorita' rivista 2026-05-14**: contratti anticipato (Tid lo chiede prima),
ordini e ddt a seguire. Riordino: contratti -> ordini -> ddt -> consumi.

**Scope esteso** (decisione Tid 2026-05-14): EDIT panel post-save replicato
per ogni sorgente, NON solo preview pre-save. Estrazione building block FE
`ComponentiPanel.vue` anticipata gia' in fase G-contratti (vedi Fase H).

**Decisione 2026-05-14 (post commit G-contratti)**: ordini/ddt **rinviati a
data da definirsi**. Scoperta in fase di kickoff Fase G-ordini: i moduli
Python ed Vue per `ordini` e `ddt` **non esistono nel codebase**. Le tabelle
DB e le fn `_init`/`_preview` sono state atterrate dal team DB nelle scorse
sessioni (vedi `docs/it/dbzero/vendite/funzioni/` + `tabelle/`), ma non c'e'
ancora il modulo BE base (CRUD testata, righe, indirizzi, fulfillment, stati)
ne' il modulo FE base (SearchTable, Drawer, store, API client).

Costruire ordini/ddt da zero non e' scope "Fase G componenti BoM": e'
un sotto-progetto autonomo che richiede decisioni di dominio aperte
(stati ordine, modalita' pricing, integrazione preventivo→ordine,
ordine→commessa, fulfillment, ciclo DDT). Stima realistica del solo
modulo base BE+FE: ~7 sessioni totali (2 BE ordini + 2 FE ordini +
1.5 BE ddt + 1.5 FE ddt) prima ancora di toccare i componenti BoM.

Quando i moduli ordini/ddt esisteranno, l'aggiunta dei componenti BoM
sara' di ~30 min repo + 1h service+API per ogni sorgente grazie al
`ComponentiRepositoryMixin` e a `ComponentiPanel`/`ComponentiDialog` FE
(Fase H atterrata).

Dopo Fase G **completa** si potra' rimuovere il path legacy
`resolve_prezzo_composito` (repo + service + DB DROP fn). **Oggi resta
attivo** finche' ordini/ddt non sono riallineati.

Stima residua componenti BoM (post sotto-progetto ordini/ddt):
~2 sessioni per replicare il pattern (1 per sorgente).

#### Fase G-contratti — IN_CORSO 2026-05-14

Due sub-sessioni:

- **G-contratti-BE** (sessione corrente):
  - `contratti_repository.py`: metodi `init_componenti_riga` / `list_componenti_riga` /
    `get_componente` / `update_componente` / `delete_componente` / `purge_componenti_riga`
    su `vendite.contratti_righe_componenti` con whitelist `_COMPONENTE_UPDATE_ALLOWED`
  - `contratti_service.py`: `preview_riga_componenti` (per ComponentiDialog FE),
    CRUD componente, auto-init in `crea_riga` quando `articolo.is_composito`
    (transazione atomica)
  - `contratti_views.py` + `contratti_urls`: 4 endpoint
    (`POST /righe/preview-componenti/`, `GET/PATCH/DELETE /righe/<rid>/componenti/...`)
  - `types.py`: `ContrattoRigaComponenteRow` TypedDict
  - Test unit service mockati
  - Doc `api_contratti.md` aggiornata
- **G-contratti-FE** (sessione successiva):
  - `contratti.js`: client API
  - `ContrattoRigheDrawer.vue`: detection `is_composito` al lookup, riuso
    `ComponentiDialog`, bridge `componenti_overrides` al save riga, mostra
    `ComponentiPanel` building block sotto la riga in edit
  - **Building block FE `ComponentiPanel.vue`** estratto durante questa sessione
    (anticipo Fase H): generalizza `PreventiviRigaComponentiPanel.vue` rendendolo
    parametrico per `sorgente` (preventivo/contratto/ordine/ddt). Migrazione
    `PreventiviRigaComponentiPanel` → wrapper thin sul building block.

### Fase H — Building block riusabili — IN_CORSO (anticipata 2026-05-14)

Estrazione progressiva, **anticipata** rispetto al piano (originariamente
post-Fase G completa). Decisione 2026-05-14: con 2 sample (preventivi +
contratti) il design del BB e' gia' sufficientemente vincolato. Estrarre
ora evita di scrivere ordini/ddt copiando codice gia' duplicato.

**Atterrato sessione 2026-05-14 (BE)**:

- ✅ `backend/apps/vendite/db/_componenti_repo_mixin.py`:
  `ComponentiRepositoryMixin` parametrico su `_componenti_table_name` e
  `_componenti_fk_riga`. Espone 5 metodi `list_componenti_riga` /
  `get_componente` / `update_componente` (con costante `COMPONENTE_UPDATE_ALLOWED`
  module-level) / `delete_componente` / `purge_componenti_riga`.
- ✅ `backend/apps/vendite/services/_componenti_service_helpers.py`: 4 pure
  functions parametrizzabili su `error_code`: `normalize_componenti_overrides`
  (con check `is_finite()` per Infinity/NaN), `normalize_componenti_attivazioni`,
  `resolve_emittente_sr_id_safe`, `resolve_emittente_sr_id_for_testata`.
- ✅ `PreventiviRepository` e `ContrattiRepository` ereditano dal mixin.
  Aliases backward-compat `_normalize_componenti_overrides` /
  `_normalize_componenti_attivazioni` / `_resolve_emittente_sr_id_safe`
  nel `preventivi_service` per mantenere stabili i mock dei test esistenti
  (~20 punti di patch evitati). Aliases nel `contratti_service` per i test
  della classe `ContrattiService`. Rimuovere aliases nel prossimo refactor
  test mirato.

**`listini_righe_componenti` esplicitamente FUORI dal mixin**: pattern
strutturalmente diverso (tabula rasa idempotente per immutabilita' v5, no
CRUD per-componente). `ListiniRepository.upsert_bundle_componenti` segue
una propria strategia. Documentato nel docstring del mixin.

**Riduzione codice**: ~200 righe rimosse fra `preventivi_repository`,
`contratti_repository`, `preventivi_service`, `contratti_service` (vs stima
iniziale ~400: 200 di queste sono nei service helpers e potrebbero ridursi
ulteriormente al refactor dei test).

**Pendenti FE Fase H** (sessione successiva FE contratti + estrazione BB):

- `ComponentiPanel.vue` (estratto da `PreventiviRigaComponentiPanel.vue`):
  parametrico su `sorgente`. Migrazione `PreventiviRigaComponentiPanel` →
  wrapper thin.
- `useTokenedFetch` composable per i 3+ pattern `_previewToken`/
  `_resolverToken`.
- i18n namespace `componenti.*` cross-dominio (gia' spostato in Fase C).

**Pendenti BE Fase H residui**:

- Fix #2 (3 query→1 JOIN in `_load_componente_for_modification`): rinviato.
  Richiede ~4 attributi configurabili sul mixin (tabella riga padre,
  FK padre, tabella testata, stato JOIN). Beneficio reale basso (operazioni
  manuali non hot path). Da valutare quando ordini/ddt arriveranno: se
  emerge un design naturale, applicare; altrimenti accettare le 3 query.
- Estrarre `is_articolo_composito` e `get_emittente_sr_id_by_fiscale_id`
  in `catalogo_repository` / `anagrafiche_repository` (helper cross-dominio):
  oggi duplicati nei 2 repo sorgenti. Refactor minore.

Stima residua: 1 sessione FE (BB FE + composable) — molto meno della
stima originale 1.5 grazie all'anticipo BE.

## 3. Pendenti aperti (priorità ordinata)

| # | Cosa | Owner | Stato |
| --- | --- | --- | --- |
| 1 | Fix DB operatore JSONB `??` → `?` in 4 fn `*_init` | Team DB | ✅ done 2026-05-13 (Liquibase applied) |
| 2 | Backfill DB manuale BoM IVA incoerenti + righe listino su compositi pre-esistenti | Team DB / Tid | ✅ done 2026-05-13 |
| 3 | pgTAP suite per i 4 nuovi guard (`E_DOC_COMPOSITO_BOM_VUOTA`, `E_DOC_COMPONENTE_OBBLIGATORIO`, `E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO`, `E_BOM_IVA_DISCORDANTE`) | Team DB | ⏳ in esecuzione 2026-05-13 |
| 4 | Brief DB **default `attivo=TRUE` sempre** in 4 fn `*_init` (decisione "BoM contratto immutabile" §9.3 del modello) | Team DB | ✅ done 2026-05-13 (Liquibase applied) |
| 5 | **Fase F smoke** §3.4 (4 scenari) | Tid + io | aperta — sbloccata da #1+#4 |
| 6 | Decisione gating L1 `componenti_attivazioni` (Fase D) | Tid (dominio) | ✅ chiusa con #4 — operatore non sceglie composizione, nessun gating richiesto |
| 7 | **Fase G** replicazione 4 sorgenti (ordini/contratti/ddt) | io | ⏸️ parziale: preventivi+contratti done 2026-05-14; ordini+ddt rinviati (moduli BE/FE inesistenti — sotto-progetto autonomo) |
| 8 | DROP `fn_resolve_prezzo_composito` + cleanup `pricing_repository.resolve_prezzo_composito` + `pricing_service.resolve_prezzo_composito` + path legacy `BoMComponentExpander._resolve_cached` + path BE dormiente `componenti_attivazioni` | Tid + team DB, post Fase G completa | bloccata da #7 (ordini+ddt) |
| 9 | **Fase H** building block (BE mixin/helper, FE `ComponentiPanel` + `useTokenedFetch` + `useRigaComponenti`) | io | ✅ done 2026-05-14 (BE + FE atterrati nel commit `b8068878f`) |
| 10 | Esporre `is_composito` denormalizzato in proiezione `contratti_righe` (BE) per consentire detection FE in EDIT senza round-trip extra | io | ✅ done (proiettato in `contratti_repository`, `a.is_composito AS is_composito`) |
| 11 | Estrarre `is_articolo_composito` + `get_emittente_sr_id_by_fiscale_id` in helper cross-dominio (`catalogo_repository`/`anagrafiche_repository`) | io | aperta (cleanup Fase H residue) |
| 12 | Rimozione ~20 aliases backward-compat `_normalize_*` / `_resolve_emittente_sr_id_safe` in preventivi/contratti service + refactor mock test verso `_componenti_service_helpers` | io | aperta (cleanup Fase H residue) |
| 13 | Fix #2 (`_load_componente_for_modification`: 3 query → 1 JOIN) | io | rinviato — beneficio basso, non hot path |

## 4. Stima residua

| Fase | Stato | Sessioni residue |
| --- | --- | --- |
| A — Brief DB | ✅ done | 0 |
| B — BE preventivi | ✅ done | 0 |
| C — FE Dialog | ✅ done | 0 |
| D — FE EDIT panel | ✅ done | 0 |
| E — Expansion commessa | ✅ done | 0 |
| F — Smoke §3.4 | aperta | 1 (Tid + io quando ha tempo) |
| G — 4 sorgenti | parziale: preventivi+contratti done. Ordini+ddt rinviati (moduli base inesistenti) | ~2 sessioni quando i moduli ordini/ddt esisteranno (oggi blocked) |
| H — Building block | ✅ done 2026-05-14 (BE+FE) | 0 |
| Cleanup residue (#10-#13) | aperto | ~0.5 sessioni totali |
| **RESIDUO immediato (escluso sotto-progetto ordini/ddt)** | | **~1.5 sessioni** |

## 5. Stato lavorazione

Verificare prima di iniziare ogni fase:

- Brief DB applicato? `git log dev/db-tid` per migrazioni recenti
- Memorie aggiornate? Handoff più recente legge a quel punto
- Test BE verdi? `./manage-test.sh apps.vendite -v 1`
- Vite build? `./node_modules/.bin/vite build`
