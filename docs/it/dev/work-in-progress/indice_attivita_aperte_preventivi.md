# Indice attività aperte — PREVENTIVI

> Generato il 2026-07-11 da una ricognizione dei documenti in `work-in-progress/`
> (più i doc recenti in `work-done/` sul tema) incentrati sui preventivi.
> Ordinato per importanza decrescente.

## Importanza ALTA

### 1. [brief-db-preventivi-revisione-attiva-dashboard.md](brief-db-preventivi-revisione-attiva-dashboard.md)

**Descrizione**: brief DB (2026-07-08) su un bug attivo: la vecchia revisione EMESSO di un preventivo riemerge come "documento aperto" fantasma nei cruscotti fatturazione (Backlog + Situazione aperta), perché `vendite.vw_dash_fatturazione_preventivi` legge la tabella grezza senza filtrare la revisione attiva. Le offerte usano già il pattern corretto (rev superata → SUPERATA).

**Attività aperte**:

- Scegliere/applicare il fix: Opzione A tattica (vista su `vw_preventivi WHERE is_attiva`) oppure **Opzione B di merito, raccomandata** (stato terminale `SUPERATO` + transizione in `fn_crea_revisione_preventivo`, come il trigger offerte)
- Backfill dei 3 casi esistenti: PRV0000038 rev0, PRV0000061 rev0/1/2, PRV0000065 rev0 → SUPERATO
- Verificare se `vendite.vw_dash_competenza_*` (Lente 1) condivide la stessa sorgente ed è affetta
- Uniformare l'incoerenza semantica "abortito" (`is_abortito` vs `esito='NEGATIVO'`)
- Test pgTAP di non-regressione (nessuna rev non-attiva nelle viste dashboard)

## Importanza MEDIA

### 2. [sviluppo-preventivi-acquisti.md](sviluppo-preventivi-acquisti.md)

**Descrizione**: specifica di sviluppo (scorporata il 2026-06-03) della direzione **acquisto** (RFQ, `acquisti.preventivi`): tabelle DB, macchina a stati, flusso verso ordine fornitore, backend e frontend. Feature greenfield interamente da avviare (la direzione vendita è completata e archiviata).

**Attività aperte** (tutto "DA IMPLEMENTARE"):

- DB: `acquisti.preventivi`, `preventivi_righe`, `preventivi_indirizzi`, `note_preventivi`
- `config.stati_doc_preventivi_acq` + macchina a stati (BOZZA/INVIATA/RICEVUTA/ACCETTATA/RIFIUTATA/SCADUTA/ANNULLATA)
- Viste `vw_preventivi`/`vw_preventivi_list` con `is_attiva` + `fn_crea_revisione_preventivo_acq`
- Backend Django `apps/acquisti/` + endpoint `/api/v1/acquisti/preventivi/…` (incl. genera-ordine, genera-pratica)
- Frontend `src/acquisti/preventivi/` (List, Form, RigheTable, Drawer, StatoBadge, View)
- Flusso downstream ACCETTATA → ordine fornitore + `PREVENTIVO_ACQ` in `config.sorgenti`

## Importanza BASSA (residui minori su doc trasversali)

### 3. [brief-design-proiezione-stato-dominio.md](brief-design-proiezione-stato-dominio.md) — solo parte preventivi

**Descrizione**: brief proiezione stato dominio; PREVENTIVI è il pilota, con MOSTRA e GUIDA già implementate. Restano solo residui minori lato preventivi (il resto del doc riguarda altri domini).

**Attività aperte (solo preventivi)**:

- Validazione E2E in-app di MOSTRA su PREVENTIVI
- Indice a espressione `((uid::text))` su `preventivi.uid` al crescere dei volumi (i resolver castano a text e non usano il btree)

### 4. [brief-design-guida-rollout-multidominio.md](brief-design-guida-rollout-multidominio.md) — solo parte preventivi

**Descrizione**: brief roll-out GUIDA multidominio; il pilota PREVENTIVI è dichiarato chiuso ed E2E-verde. Restano item di coordinamento/pulizia firma.

**Attività aperte (solo preventivi)**:

- R1: progettare da subito la firma della funzione madre di push con `flusso_id` (`fn_push_preventivo_a_ordine` oggi non lo riceve; aggiungerlo dopo costringerebbe a un secondo `DROP FUNCTION`) — coordinato con `analisi-fix-transazioni`
- Aggiornare la nota di stato del brief-padre (MOSTRA non è più "solo PREVENTIVI": livello lettura DB generico su 4 domini)

## Conclusi (storico, in work-done — nessun lavoro sostanziale aperto)

### 5. [piano-be-fe-uniformita-pratica-preventivi.md](../work-done/piano-be-fe-uniformita-pratica-preventivi.md)

**Descrizione**: piano BE/FE uniformità pratica preventivi ↔ programma standalone. **✅ COMPLETO (2026-07-02)**: Fasi 0–4 + ritiro handler monolitico, smoke E2E verde.
**Residuo unico (non bloccante)**: 🟡 prerequisito flusso `60 ← 50` (INVIO_COMMESSA dopo CONFERMA_ORDINE) vs attuale `60 ← 40` — da raddrizzare per pulizia di modello.

### 6. [analisi-uniformita-pratica-preventivi.md](../work-done/analisi-uniformita-pratica-preventivi.md)

**Descrizione**: analisi delle divergenze pratica preventivi vs standalone, razionale del piano al punto 5. **✅ CHIUSA (2026-07-02)**, bug §3.1.1–§3.1.4 chiusi.
**Residui (non bloccanti)**: stesso micro-punto DB `60 ← 50` del punto 5; backfill `data_apertura` esplicitamente rinviato (vedi [nota-be-backfill-data-apertura-pratiche.md](../work-done/nota-be-backfill-data-apertura-pratiche.md), spostato in `work-done/` il 2026-07-11).
