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

### Fase G — Replicazione 4 sorgenti (ordini / contratti / ddt) — APERTA

Pattern preventivi replicato simmetricamente. Una sessione per sorgente:

- BE: repo + service + API + types + tests
- FE: riuso `ComponentiDialog.vue` con `apiPreview` sorgente-specific; drawer riga sorgente segue stesso pattern preventivi
- Smoke specifico per sorgente

Dopo Fase G si potrà rimuovere il path legacy `resolve_prezzo_composito` (repo + service + DB DROP fn).

Stima: 4 sessioni totali (1 per sorgente, ordini → contratti → ddt → consumi se previsto).

### Fase H — Building block riusabili — APERTA

Estrazione progressiva, post replicazione 4 sorgenti:

- BE: classe base `ComponentiRepository` / `ComponentiService` parametrizzata per sorgente
- FE: `ComponentiDialog.vue` già parametrizzato; eventuale estrazione tabella in sotto-componente `ComponentiTable.vue` se EDIT panel ne riusa la struttura
- i18n: namespace `componenti.*` cross-dominio già spostato in Fase C
- DB helper: helper `script.*` già parametrizzati (TG_ARGV)
- Composable `useTokenedFetch` per i 3+ pattern `_previewToken`/`_resolverToken`

Stima: 1.5 sessione totale.

## 3. Pendenti aperti (priorità ordinata)

| # | Cosa | Owner | Stato |
| --- | --- | --- | --- |
| 1 | Fix DB operatore JSONB `??` → `?` in 4 fn `*_init` | Team DB | ✅ done 2026-05-13 (Liquibase applied) |
| 2 | Backfill DB manuale BoM IVA incoerenti + righe listino su compositi pre-esistenti | Team DB / Tid | ✅ done 2026-05-13 |
| 3 | pgTAP suite per i 4 nuovi guard (`E_DOC_COMPOSITO_BOM_VUOTA`, `E_DOC_COMPONENTE_OBBLIGATORIO`, `E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO`, `E_BOM_IVA_DISCORDANTE`) | Team DB | ⏳ in esecuzione 2026-05-13 |
| 4 | Brief DB **default `attivo=TRUE` sempre** in 4 fn `*_init` (decisione "BoM contratto immutabile" §9.3 del modello) | Team DB | ✅ done 2026-05-13 (Liquibase applied) |
| 5 | **Fase F smoke** §3.4 (4 scenari) | Tid + io | aperta — sbloccata da #1+#4 |
| 6 | Decisione gating L1 `componenti_attivazioni` (Fase D) | Tid (dominio) | ✅ chiusa con #4 — operatore non sceglie composizione, nessun gating richiesto |
| 7 | **Fase G** replicazione 4 sorgenti (ordini/contratti/ddt) | io | aperta |
| 8 | DROP `fn_resolve_prezzo_composito` + cleanup `pricing_repository.resolve_prezzo_composito` + `pricing_service.resolve_prezzo_composito` + path legacy `BoMComponentExpander._resolve_cached` + path BE dormiente `componenti_attivazioni` | Tid + team DB, post Fase G | aperta |
| 9 | **Fase H** building block (BE base class, FE `ComponentiTable`, `useTokenedFetch`) | io, post Fase G | aperta |

## 4. Stima residua

| Fase | Stato | Sessioni residue |
| --- | --- | --- |
| A — Brief DB | ✅ done | 0 |
| B — BE preventivi | ✅ done | 0 |
| C — FE Dialog | ✅ done | 0 |
| D — FE EDIT panel | ✅ done | 0 |
| E — Expansion commessa | ✅ done | 0 |
| F — Smoke §3.4 | aperta (blocco DB JSONB) | 1 |
| G — 4 sorgenti | aperta | 4 |
| H — Building block | aperta | 1.5 |
| **RESIDUO** | | **~6.5 sessioni** |

## 5. Stato lavorazione

Verificare prima di iniziare ogni fase:

- Brief DB applicato? `git log dev/db-tid` per migrazioni recenti
- Memorie aggiornate? Handoff più recente legge a quel punto
- Test BE verdi? `./manage-test.sh apps.vendite -v 1`
- Vite build? `./node_modules/.bin/vite build`
