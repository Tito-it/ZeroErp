# Refactor Componenti BoM — Piano operativo BE/FE

> **Scope**: piano operativo corrente. Nessuna decisione di dominio
> qui — quelle stanno nel modello.
>
> **Riferimenti obbligatori**:
>
> - Modello logico: [`manual/modello-componenti-bom.md`](../manual/modello-componenti-bom.md)
> - Changelog decisioni: [`manual/changelog-decisioni-componenti.md`](../manual/changelog-decisioni-componenti.md)
> - Brief DB attivo: [`brief-db-componenti-modello-unificato.md`](brief-db-componenti-modello-unificato.md)

## 1. Stato corrente (snapshot 2026-05-12 sera)

### DB

- Atterrate: 5 tabelle `*_righe_componenti` (preventivi/ordini/ddt/contratti + helper `script.*`), trigger guard BoM, trigger `_z90_ricalcola_padre`, fn `_init` + fn `_preview` (4 sorgenti), errore `E_DOC_COMPONENTE_LISTINO_MANCANTE`
- Pendenti (brief attivo): rollback gate `esposto_in_fattura`, rilassamento CHECK `<> 0`, guard obbligatorio non disattivabile, errore `E_DOC_COMPOSITO_BOM_VUOTA`, coerenza IVA padre-figli (trigger catalogo), tabella `vendite.listini_righe_componenti`, resolver bundle-aware via `p_articolo_padre_contesto`, deprecazione `fn_resolve_prezzo_composito`

### BE preventivi

- Atterrate: repository (`init_componenti_riga`, `preview_componenti_riga`), service (gating L1, `_normalize_componenti_overrides`, `_resolve_emittente_sr_id_for_preventivo`), API (`ApiPreventivoRigaPreviewComponenti`), types, +16 test
- Pendenti: nuova mappa `componenti_attivazioni` per opzionali; field aggiuntivi `obbligatorio` + `esposto_in_fattura` nella proiezione preview; integrazione con `p_articolo_padre_contesto` per pricing bundle (post-DB)

### FE preventivi

- Atterrate: nuovo flusso form atomic (preview inline), Dialog assente, `isPadreComposito` helper, gating UI override, debounce preview
- Pendenti: sostituzione tabella inline con `ComponentiDialog.vue`, EDIT panel coerente (colonne nuove), riepilogo sintetico nel drawer riga padre

### Altre sorgenti (ordini / contratti / ddt)

- DB tabelle + trigger atterrate (simmetria 5 tabelle 2026-05-11)
- BE: non avviato
- FE: non avviato

## 2. Piano operativo per fasi

### Fase A — Brief DB modello unificato (team DB su `dev/db-tid`)

Vedi [`brief-db-componenti-modello-unificato.md`](brief-db-componenti-modello-unificato.md).
Sblocca tutte le fasi successive.

### Fase B — BE preventivi (post DB)

Sequenza:

1. `apps/vendite/db/preventivi_repository.py`: aggiornare proiezione `preview_componenti_riga` con `obbligatorio` + `esposto_in_fattura`; aggiornare `init_componenti_riga` per accettare nuovo arg `componenti_attivazioni` (mappa `componente_id -> bool`)
2. `apps/vendite/services/preventivi_service.py`: estendere `gestisci_riga` per accettare `componenti_attivazioni` nel payload; rimuovere helper legacy `_can_force_componenti_manuale` se residuo
3. `apps/vendite/api/preventivi_views.py`: accettare `componenti_attivazioni` nel payload riga
4. `apps/vendite/types.py`: aggiungere campi a `PreventivoRigaComponentePreviewRow`
5. Tests: conservare 16 form atomic, aggiungere 4 nuovi (`bom_vuota`, `attivazioni_passate`, `obbligatorio_disattivazione_bloccata`, `obbligatorio_prezzo_zero`)

Stima: 0.5 sessione.

### Fase C — FE preventivi nuovo `ComponentiDialog.vue`

Sequenza:

1. Creare `frontend/src/vendite/preventivi/components/ComponentiDialog.vue`: PrimeVue Dialog 90vw, props `articolo`, `preventivoId`, `uomOperativaId`, `quantita`; v-model payload con `componenti_overrides` + `componenti_attivazioni`; tabella editabile con colonne aggiunte (obbligatorio + attivo + esposto in fattura)
2. Rimuovere blocco preview inline da `PreventiviRigaForm.vue` (linee correnti ~675-737): tutto migra nella Dialog. Sostituire con riepilogo `{n componenti — totale stimato €X}` + bottone "Modifica componenti"
3. Apertura Dialog automatica al lookup di articolo composito (watch su `articoloObj.is_composito`)
4. `isPadreComposito`: semantica unificata, basta `articoloObj.is_composito === true` (niente piu' CASO A/B)
5. `canSave` richiede `componentiPayload != null` per i compositi
6. i18n: aggiungere `componenti_dialog_*`, `componenti_summary`, `componenti_modifica`, `componenti_col_attivo`, `componenti_col_esposto`. Rimuovere chiavi inline preview obsolete

Stima: 0.8 sessione.

### Fase D — EDIT path coerenza (`PreventiviRigaComponentiPanel.vue`)

- Aggiungere colonne `obbligatorio` (icona), `attivo` (checkbox disabilitato per obbligatori), `esposto_in_fattura` (tag)
- Validazione: blocco UPDATE `prezzo = 0` su obbligatori (defense-in-depth oltre al DB)
- Riusare componenti tabella della Dialog se possibile (TODO building block §5)

Stima: 0.3 sessione.

### Fase E — Censimento + aggiornamento expansion BE→commessa

- Censimento fn DB/Python che fanno expansion `<sorgente>_righe + componenti` → `commesse_attivita`
- Verificare filtro `esposto_in_fattura`: rimuoverlo (tutti i figli passano in commessa)
- Eventuale aggiornamento `BoMComponentExpander` Python o omologhi
- Verificare generazione `fatture_righe` da `commesse_attivita`: padre con totale + figli esposti come righe descrittive

Stima: 1 sessione.

### Fase F — Smoke UI utente §3.4 rivisto

3 scenari aggiornati per nuovo modello:

- F.1 — padre con solo obbligatori, tutti con listino → save senza override
- F.2 — padre con obbligatori + opzionali, operatore attiva 1 opzionale, prezzo manuale su 1 obbligatorio → save con `componenti_overrides` + `componenti_attivazioni`
- F.3 — padre con BoM scaduta → errore parlante `E_DOC_COMPOSITO_BOM_VUOTA`
- F.4 (nuovo) — listino bundle vs standalone: due preventivi a date diverse mostrano prezzi diversi se cambia il `listini_righe_componenti`

Aggiornare `sviluppo-listini-v5-test-ui.md` §3.4 con questi scenari.

Stima: 1 sessione.

### Fase G — Replicazione 4 sorgenti (ordini / contratti / ddt)

Pattern preventivi replicato simmetricamente. Una sessione per sorgente:

- BE: repo + service + API + types + tests
- FE: riuso `ComponentiDialog.vue` + adapter per sorgente; nuovo drawer riga sorgente segue stesso pattern preventivi
- Smoke specifico per sorgente

Stima: 4 sessioni totali (1 per sorgente).

### Fase H — Building block riusabili

Estrazione progressiva, post replicazione 4 sorgenti:

- BE: classe base `ComponentiRepository` / `ComponentiService` parametrizzata per sorgente
- FE: `ComponentiDialog.vue` gia' parametrizzato; eventuale estrazione tabella in sotto-componente `ComponentiTable.vue`
- i18n: namespace `componenti.*` cross-dominio (separato dai `<sorgente>.componenti_*` specifici)
- DB helper: helper `script.*` gia' parametrizzati (TG_ARGV)

Stima: 1.5 sessione totale.

## 3. Ordine consigliato

```text
A (DB)  →  B (BE prev)  →  C (FE Dialog)  →  D (FE EDIT panel)  →  F (smoke)
                                  ↓
                              E (expansion commessa)
                                  ↓
                              G (4 sorgenti replicate)
                                  ↓
                              H (building block)
```

Step A blocca tutto il resto. B, C, D paralleli dopo A. E indipendente
da C/D ma serve prima del push commessa effettivo. G replica solo dopo
che F (smoke preventivi) e' verde.

## 4. Stima totale

| Fase | Sessioni |
| --- | --- |
| A — Brief DB | 1 (team DB) |
| B — BE preventivi | 0.5 |
| C — FE Dialog | 0.8 |
| D — FE EDIT panel | 0.3 |
| E — Expansion commessa | 1 |
| F — Smoke §3.4 | 1 |
| G — 4 sorgenti | 4 |
| H — Building block | 1.5 |
| **TOTALE** | **~10 sessioni** |

## 5. Stato lavorazione

Verificare prima di iniziare ogni fase:

- Brief DB applicato? `git log dev/db-tid` per migrazioni recenti
- Memorie aggiornate? Handoff piu' recente legge a quel punto
- Test BE verdi? `./manage-test.sh apps.vendite -v 1`
- Vite build? `./node_modules/.bin/vite build`
