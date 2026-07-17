# Indice attività aperte — PREVENTIVI

> Generato il 2026-07-11 da una ricognizione dei documenti in `work-in-progress/`
> (più i doc recenti in `work-done/` sul tema) incentrati sui preventivi.
> Ordinato per importanza decrescente.
>
> **Revisione 2026-07-16**: ricognizione completa, ogni voce verificata contro il
> **DB vivo e il codice** (non contro gli YAML). Esito: **niente più di importanza
> ALTA**, e 4 item risultavano chiusi da tempo senza che l'indice lo sapesse —
> l'ex punto 1 (revisione attiva nei cruscotti, ora al punto 4), l'indice
> `((uid::text))`, l'R1 `flusso_id`, il prerequisito flusso `60 ← 50`.
>
> **Cosa resta davvero aperto** (nessuna voce bloccante):
>
> 1. Preventivi **acquisti** (punto 1) — greenfield, ma **parcheggiato per scelta**
>    (vedi nota sotto): non è in coda.
> 2. **Validazione E2E in-app di MOSTRA** su PREVENTIVI (punto 2) — non verificabile
>    da codice.
> 3. **Nota di stato del brief-padre** da aggiornare (punto 3) — doc-only.
> 4. 🔴 **`flusso_id` sui link COLLEGATO: capability dormiente** (punto 3) — emersa
>    **durante questa ricognizione**, non era tracciata da nessuna parte. Il DB
>    accetta e scrive `flusso_id`, ma nessun chiamante lo passa → **0 su 39** link
>    COLLEGATO valorizzati. Da decidere/cablare al roll-out dei resolver
>    ordine/commessa.
>
> ⚠️ **Lezione, in due direzioni**: l'indice era **più pessimista della realtà** su 4
> voci già chiuse, ma anche **più ottimista** su una — nessuno aveva notato che
> `flusso_id` sui COLLEGATO non arriva mai. Una firma pronta in DB non significa
> feature attiva: verificare sempre **anche i dati**, non solo la definizione.

## Importanza ALTA

_Nessuna._ (l'ex punto 1 — revisione attiva nei cruscotti — è chiuso: vedi punto 4)

## Importanza MEDIA


NOta su acquisti ora non è in previsione di fare sviluppo dominio acquisti.
### 1. [sviluppo-preventivi-acquisti.md](sviluppo-preventivi-acquisti.md)

**Descrizione**: specifica di sviluppo (scorporata il 2026-06-03) della direzione **acquisto** (RFQ, `acquisti.preventivi`): tabelle DB, macchina a stati, flusso verso ordine fornitore, backend e frontend. Feature greenfield interamente da avviare (la direzione vendita è completata e archiviata).

**Attività aperte** (tutto "DA IMPLEMENTARE"):

- DB: `acquisti.preventivi`, `preventivi_righe`, `preventivi_indirizzi`, `note_preventivi`
- `config.stati_doc_preventivi_acq` + macchina a stati (BOZZA/INVIATA/RICEVUTA/ACCETTATA/RIFIUTATA/SCADUTA/ANNULLATA)
- Viste `vw_preventivi`/`vw_preventivi_list` con `is_attiva` + `fn_crea_revisione_preventivo_acq`
- Backend Django `apps/acquisti/` + endpoint `/api/v1/acquisti/preventivi/…` (incl. genera-ordine, genera-pratica)
- Frontend `src/acquisti/preventivi/` (List, Form, RigheTable, Drawer, StatoBadge, View)
- Flusso downstream ACCETTATA → ordine fornitore + `PREVENTIVO_ACQ` in `config.sorgenti`

## Importanza BASSA (residui minori su doc trasversali)

### 2. [brief-design-proiezione-stato-dominio.md](brief-design-proiezione-stato-dominio.md) — solo parte preventivi

**Descrizione**: brief proiezione stato dominio; PREVENTIVI è il pilota, con MOSTRA e GUIDA già implementate. Restano solo residui minori lato preventivi (il resto del doc riguarda altri domini).

**Attività aperte (solo preventivi)**:

- Validazione E2E in-app di MOSTRA su PREVENTIVI ← **unico residuo reale**; non verificabile da codice (attività in-app)
- ~~Indice a espressione `((uid::text))` su `preventivi.uid`~~ → ✅ **CHIUSO** (verificato 2026-07-16): l'indice esiste in DB — `ix_preventivi_uid_text ON vendite.preventivi USING btree (((uid)::text))`

### 3. [brief-design-guida-rollout-multidominio.md](brief-design-guida-rollout-multidominio.md) — solo parte preventivi

**Descrizione**: brief roll-out GUIDA multidominio; il pilota PREVENTIVI è dichiarato chiuso ed E2E-verde. Restano item di coordinamento/pulizia firma.

**Attività aperte (solo preventivi)**:

- ~~R1: progettare da subito la firma della funzione madre di push con `flusso_id`~~ → ✅ **CHIUSO come formulato** (verificato 2026-07-16). R1 chiedeva di **progettare la firma** per evitare un secondo `DROP FUNCTION`: obiettivo raggiunto. `fn_push_preventivo_a_ordine` ha già `p_flusso_id bigint DEFAULT NULL` in firma e il corpo lo scrive sul link COLLEGATO (`INSERT INTO pratiche.pratiche_sorgenti (…, ruolo_link, flusso_id) VALUES (…, 'COLLEGATO', p_flusso_id)`). Il rischio strutturale è scongiurato.
- 🔴 **NUOVO — `flusso_id` sui COLLEGATO è una capability DORMIENTE** (scoperto 2026-07-16, vedi §nota sotto). Il DB è pronto ma **nessun chiamante passa il parametro**: `push_a_ordine` in `preventivi_repository.py` non ha proprio l'argomento e invoca la fn con **4 parametri su 5** → `p_flusso_id` cade sul DEFAULT NULL. **Riscontro sui dati**: `pratiche_sorgenti` ha **39 link COLLEGATO, 0 con `flusso_id`** (i ROOT: 13 su 45). G-est.2 è quindi implementato lato DB ma **inefficace end-to-end**. Non è un residuo di R1: è l'item **(b)** delle «Note per il roll-out» del brief-padre, che va deciso e cablato quando arrivano i resolver ordine/commessa.
- Aggiornare la nota di stato del brief-padre (doc-only). Confermato stale il 2026-07-16: l'header dice ancora _"fase MOSTRA implementata su PREVENTIVI"_, ma `script.vw_stato_sorgente` unisce già **4 domini** (`vw_stato_sorgente_preventivo` / `_offerta` / `_ordine` / `_contratto`) → il livello di lettura DB è generico, non più solo-preventivi

## Conclusi (storico, in work-done — nessun lavoro sostanziale aperto)

### 4. [brief-db-preventivi-revisione-attiva-dashboard.md](../work-done/brief-db-preventivi-revisione-attiva-dashboard.md) — ✅ CHIUSO (verificato 2026-07-16)

**Era**: importanza ALTA. Bug di vista — la vecchia revisione EMESSO riemergeva come "documento
aperto" fantasma nei cruscotti fatturazione (Backlog + Situazione aperta).

**Esito**: applicata l'**Opzione A** (fix sulla vista), e l'**Opzione B è stata scartata di
proposito, non rinviata**. Motivo di modello, ora documentato in
[gestione-preventivi §4.3](../../guide/gestione-preventivi.md): sui preventivi **non deve esistere**
uno stato `SUPERATO`, perché chiuderebbe la revisione precedente e romperebbe il ritorno voluto
_"annullo la bozza di revisione → la rev emessa torna da sola quella valida"_. L'asimmetria con le
offerte (che usano `SUPERATA`) è **corretta**: l'offerta è un documento a sé per revisione, il
preventivo versiona lo stesso numero.

**Chiusura dei 5 item aperti** (tutti verificati contro il DB vivo, non contro gli YAML):

| Item del brief | Esito |
| --- | --- |
| Scegliere/applicare il fix | ✅ Opzione A — migration `20260708-06-update-vw-dash-fatturazione-preventivi-solo-rev-attiva`. La vista legge ora `FROM vendite.vw_preventivi … WHERE p.is_attiva` (confermato dalla doc auto-gen `dbzero/vendite/views/vw_dash_fatturazione_preventivi.md`) |
| Backfill dei 3 casi → SUPERATO | ⚪ **Decaduto**: era necessario solo per l'Opzione B. Con A i 3 casi sono già corretti senza toccare i dati |
| Verificare `vw_dash_competenza_*` (Lente 1) | ✅ **Non affetta**: legge `vendite.commesse` / `commesse_attivita` / `attivita_fatturabili`, non condivide la sorgente preventivi |
| Uniformare la semantica "abortito" | ✅ Risolto per chiarimento: non era un'incoerenza ma **due concetti distinti e legittimi** — `is_abortito` (solo ANNULLATO = abbandono, la rev rifluisce al predecessore) vs `esito='NEGATIVO'` (verdetto: RIFIUTATO/SCADUTO/ANNULLATO). Post-fix compongono correttamente; documentato in §4.3 |
| Test pgTAP di non-regressione | ✅ `db/pgtap/vendite/test-vw-dash-preventivi-revisione-attiva.sql` — 13 test, 4 scenari (A/B/C/D) + invariante generale "nessuna rev non-attiva nella union dashboard" |

**Bonus emerso dal pgTAP (scenario B) — bug ulteriore trovato e chiuso**: migration
`20260708-07-update-vw-preventivi-is-attiva-self-abortito`. `is_attiva` guardava **solo verso
l'alto** ("nessuna rev superiore non-abortita"), quindi una rev ANNULLATA **in cima** alla catena si
dichiarava attiva → `is_attiva` non era univoco (due rev attive per `rev0 EMESSO + rev1 ANNULLATO`),
contro la garanzia dichiarata nel create originale. Aggiunto il termine sul **proprio** stato:
attiva = _(stato non abortito)_ AND _(nessuna rev superiore non-abortita)_. Conseguenza di dominio:
un ANNULLATO singola-rev diventa non-attivo (visibile solo in "mostra storico").

**Follow-up BE del changelog 07** — anch'esso già chiuso: `preventivi_repository.py` non duplica più
la subquery `NOT EXISTS`, consuma direttamente `v.is_attiva IS TRUE` da `vw_preventivi_lista`.
(L'`EXISTS` ancora presente è `has_next_revision`, predicato diverso e voluto.)

**Verifica in DB del test §7 del brief** (2026-07-16, sola lettura, contesto RLS operatore) —
combacia esattamente con l'atteso post-fix:

| numero | atteso | rilevato (backlog / aperto) |
| --- | --- | --- |
| PRV0000038 | 0 righe | ✅ 0 / 0 |
| PRV0000061 | 1 riga (era 4) | ✅ 1 / 1 |
| PRV0000065 | 1 riga (era 2) | ✅ 1 / 1 |

Migration e pgTAP sono **committati** (`fd89c25d8`). Doc spostato in `work-done/` il 2026-07-16.

### 5. [piano-be-fe-uniformita-pratica-preventivi.md](../work-done/piano-be-fe-uniformita-pratica-preventivi.md)

**Descrizione**: piano BE/FE uniformità pratica preventivi ↔ programma standalone. **✅ COMPLETO (2026-07-02)**: Fasi 0–4 + ritiro handler monolitico, smoke E2E verde.
**Residuo unico** → ✅ **CHIUSO** (verificato in DB 2026-07-16): il prerequisito flusso `60 ← 50` **è già raddrizzato**, non è più `60 ← 40`. In `pratiche.template_flussi_prerequisiti` la catena 9009-9014 è ora lineare: `20←10`, `30←20`, `40←30`, `50←40`, **`60 INVIO_COMMESSA ← 50 CONFERMA_ORDINE`**. Nessun residuo.

### 6. [analisi-uniformita-pratica-preventivi.md](../work-done/analisi-uniformita-pratica-preventivi.md)

**Descrizione**: analisi delle divergenze pratica preventivi vs standalone, razionale del piano al punto 5. **✅ CHIUSA (2026-07-02)**, bug §3.1.1–§3.1.4 chiusi.
**Residui**: il micro-punto DB `60 ← 50` → ✅ **CHIUSO** (stessa verifica del punto 5). Resta solo il backfill `data_apertura`, **rinvio esplicito e consapevole**, non un pendente da recuperare (vedi [nota-be-backfill-data-apertura-pratiche.md](../work-done/nota-be-backfill-data-apertura-pratiche.md), spostata in `work-done/` il 2026-07-11).
