# Brief DB — Espansione righe offerta (listino + eccezioni) → ordine-ready

> ✅ **COMPLETATO (DB) — 2026-06-04.** Core `fn_espandi_listino_versione` +
> refactor `fn_contratto_righe_preview` sul core + `fn_offerta_righe_espanse`
> (ordine-ready) + pgTAP + doc manuale. Migration `20260604-02/03/04`. Migrate +
> pgTAP eseguiti e verdi; regressione drawer contratti verificata. **Resta solo**:
> commit/PR (S8, attende "procedi") e hand-off BE (S9, fuori scope DB).
>
> **Branch**: `dev/db-tid`. **Destinatario**: team DB.
> **Natura**: prerequisito DB per la **conversione offerta → ordine** (§7.4
> [analisi-ordini-vendita.md](analisi-ordini-vendita.md)). BE/FE attendono
> (`feedback_be_fe_attende_prerequisiti_db`). Consegna **additiva, sola lettura**.
> ZeroErp non in produzione.
>
> ⚙️ **Questo brief riscrive la richiesta BE** (`Brief DB — Espansione righe
> offerta`) recependo 3 rilievi da analisi critica sul codice (2026-06-04):
> (1) **no clone** di `fn_contratto_righe_preview` → core condiviso (regola del 2);
> (2) output **ordine-ready** (IVA/sconto/uom), non solo prezzi da drawer, per non
> spostare logica nel BE (DB-first); (3) distinguere proiezione *drawer* da
> proiezione *ordine*.

---

## 1. Problema

`vendite.offerte_commerciali` modella i prezzi come **listino base + variazione
globale + eccezioni** (`offerte_commerciali_eccezioni`,
`OVERRIDE`/`ESCLUSIONE`/`AGGIUNTA`, mirror di `contratti_righe`). Non esiste una
lista piatta di articoli/prezzi effettivi. Per generare un ordine servono le
**righe effettive** = listino risolto **+** eccezioni applicate:

- `AGGIUNTA` → riga in più (articolo non a listino);
- `ESCLUSIONE` → riga di listino rimossa;
- `OVERRIDE` → riga di listino con prezzo/condizioni sostituiti.

Copiare solo le eccezioni sarebbe scorretto (perderebbe il listino base e le
`ESCLUSIONE`). A differenza dei **preventivi**, le cui righe (`preventivi_righe`)
sono **già piatte e materializzate** (copia 1:1 → ordine banale), le offerte
richiedono un'**espansione**.

## 2. Stato verificato (2026-06-04)

| Fatto | Esito |
| --- | --- |
| Esiste la preview contratti `vendite.fn_contratto_righe_preview(bigint)` | ✅ UNION 4 parti, ritorna righe piatte + `componenti jsonb` |
| `offerte_commerciali_eccezioni` mirror di `contratti_righe` (+ `_componenti`, `_utilities`) | ✅ |
| `offerte_commerciali`: `listino_id` **NOT NULL**, `listino_versione_id`, `tipo/valore_variazione_globale`, `valuta_id`, stato con `ACCETTATA` | ✅ |
| `vendite.ordini.documento_origine_tipo` ammette `'OFFERTA'` (CHECK) | ✅ |
| `ordini_righe` richiede `iva_id`/`iva_perc`, `sconto_perc`, `uom_operativa_id`/`factor_to_base`/`qta_operativa`, `descrizione`, `prezzo_unitario` | ✅ (vedi §4) |
| `fn_contratto_righe_preview` ritorna `iva`/`sconto`/`uom_operativa` | ❌ **NO** (serve al drawer, non alla conversione) |
| `listini_righe` porta l'IVA | ❌ **NO** → IVA va risolta dall'**articolo** |

## 3. Cosa serve — e come (raccomandazione architetturale)

Una funzione che, dato un `offerta_id`, ritorni le **righe effettive
ordine-ready** (listino + variazione globale + eccezioni, con BoM per i
compositi). MA **non clonando** la preview contratti.

### 3.1 No clone — estrarre un core condiviso (regola del 2)

`fn_contratto_righe_preview` e la futura espansione offerta condividono la
**Parte 1** (espansione listino: standalone + bundle da
`listini_righe`/`listini_righe_componenti`, applicazione `variazione globale`,
aggregazione BoM in `componenti jsonb`) — **byte-identica**, perché entrambe
leggono lo stesso listino. Differiscono **solo** nella tabella eccezioni
(`contratti_righe` vs `offerte_commerciali_eccezioni`, + `_componenti`).

> Clonare ~300 righe di risoluzione pricing/eccezioni/BoM tra due funzioni che
> dovranno restare sincronizzate ad ogni cambio (pricing v5, BoM, variazione) è
> esattamente la duplicazione che la regola del 2 vieta (`feedback_regola_del_2_estrai_bb`).

**Direzione raccomandata** (forma esatta = scelta team DB,
`feedback_db_actions_passaggio_team`):

- estrarre un **core di espansione listino** condiviso (es.
  `vendite.fn_espandi_listino_versione(p_listino_versione_id, p_tipo_var, p_valore_var)`)
  che produce le righe da listino + variazione + BoM;
- ciascun dominio applica solo il proprio **overlay eccezioni** (OVERRIDE/
  ESCLUSIONE/AGGIUNTA) sulla propria tabella;
- `fn_contratto_righe_preview` viene **rifattorizzata** per consumare il core
  (consegna a costo zero di regressione: stessi output del drawer);
- nasce `vendite.fn_offerta_righe_espanse(p_offerta_id)` che consuma il core +
  overlay su `offerte_commerciali_eccezioni`.

Se il team valuta la rifattorizzazione di `fn_contratto_righe_preview` troppo
rischiosa ora, il **minimo accettabile** è che il core di espansione listino sia
una fn unica chiamata da entrambe — **mai** due copie del medesimo SQL.

### 3.2 Output **ordine-ready** (non solo prezzi da drawer)

Punto critico: la preview contratti **non basta** per la conversione. La fn
offerta deve ritornare righe **complete e mappate su `ordini_righe`**, altrimenti
il BE dovrebbe arricchirle (risolvere l'IVA, mappare uom) → logica di business
fuori dal DB, contro il principio DB-first e in duplicazione di quanto fanno già
le righe preventivo. Colonne richieste in output (target = `ordini_righe`, vedi §4):

| Output fn | → `ordini_righe` | Risoluzione |
| --- | --- | --- |
| `articolo_id` (uuid) | `articolo_id` | da eccezione/listino |
| `descrizione` | `descrizione` (NOT NULL) | da articolo (fallback) o eccezione |
| `quantita` | `quantita` | eccezione (default 1 per righe da listino?) → **decisione §6** |
| `prezzo_unitario` | `prezzo_unitario` | = `prezzo_finale` (listino±variazione, o override) |
| `sconto_perc` | `sconto_perc` | NULL/0: l'offerta esprime lo sconto come prezzo, non come % (vedi §6) |
| **`iva_id`** | `iva_id` | **dall'articolo** (`listini_righe` non ha IVA) |
| **`iva_perc`** | `iva_perc` | dall'aliquota risolta (snapshot) |
| `uom_operativa_id` | `uom_operativa_id` | mapping da `uom_id` listino / `uom_operativa_id` eccezione |
| `qta_operativa` | `qta_operativa` | eccezione |
| `factor_to_base` | `factor_to_base` | eccezione (default 1) |
| `componenti` (jsonb) | → `ordini_righe_componenti` | BoM per compositi |
| `is_composito`, `tipo_eccezione`, `origine` | (meta/diagnostica) | per il copy BE |

> **IVA**: poiché `listini_righe` non porta l'aliquota, va risolta dall'articolo
> (es. `catalogo.articoli` default IVA / fn di risoluzione esistente). È lo stesso
> dato che `preventivi_righe.iva_id` materializza alla creazione riga. Confermare
> col team la fonte canonica di risoluzione IVA articolo (riuso, no nuova logica).

### 3.3 Semplificazione rispetto ai contratti

Le offerte hanno **`listino_id` NOT NULL**: **niente modalità C** (listino
assente). La fn offerta **non** ha il ramo `IF v_listino_id IS NULL` della
preview contratti → è più semplice. Da dichiarare nel commento.

## 4. Target copia — `vendite.ordini_righe`

Colonne NOT NULL: `articolo_id` (uuid), `descrizione`, `quantita`,
`prezzo_unitario`, `riga_nr`, `factor_to_base` (default 1). Nullable rilevanti:
`sconto_perc`, `iva_id`, `iva_perc`, `uom_operativa_id`, `qta_operativa`.
Componenti BoM → `vendite.ordini_righe_componenti`. La fn deve produrre tutto ciò
che serve a popolare queste colonne **senza** richiedere risoluzioni aggiuntive
nel BE.

## 5. pgTAP (verifica consegna) — `db/pgtap/vendite/`

- la fn esiste con la firma concordata ed è `STABLE`;
- offerta solo-listino (nessuna eccezione) → ritorna le righe del listino con
  `prezzo_finale` = listino ± variazione globale;
- `OVERRIDE` → la riga di listino esce con prezzo override;
- `ESCLUSIONE` → la riga di listino **non** compare;
- `AGGIUNTA` standalone e bundle → riga extra + componenti BoM nel jsonb;
- ogni riga ha `iva_id`/`iva_perc` valorizzati (risolti da articolo) e mapping uom
  coerente → riga copiabile in `ordini_righe` senza arricchimenti;
- core condiviso: `fn_contratto_righe_preview` continua a restituire lo stesso
  output del drawer (no regressione) se rifattorizzata sul core;
- `CASE WHEN`/`skip()` per fixture data-dependent (`feedback_pgtap_conditional_skip`).

## 6. Decisioni — risolte (Tid, 2026-06-04)

1. **Naming**: ✅ `fn_offerta_righe_espanse` (semantica ordine-ready).
2. **Fattorizzazione core**: ✅ **raccomandato** — `fn_contratto_righe_preview`
   rifattorizzata subito sul core condiviso `fn_espandi_listino_versione`.
3. **Fonte IVA articolo**: ✅ `catalogo.articoli.iva_id` → `iva_perc` da
   `config.iva.aliquota_iva`. Risolta nell'overlay di dominio (offerta), non nel
   core (il core resta neutro su iva).
4. **Quantità righe da-listino**: ✅ **default 1** per le righe da-listino senza
   eccezione.
5. **Sconto**: ✅ `sconto_perc` NULL; `prezzo_unitario` = prezzo già netto
   (lo sconto dell'offerta è espresso come prezzo override).

## 7. A valle (BE/FE, fuori da questo brief)

A fn consegnata: `OfferteRepository.list_righe_espanse(offerta_id)` (thin wrapper),
creazione ordine da offerta (guard stato `ACCETTATA`, copia testata + righe
espanse + componenti, `documento_origine = ('OFFERTA', offerta_id)`), endpoint
`POST /api/v1/vendite/offerte/<id>/genera-ordine/` e azione FE su `OffertaDrawer`.

> ⚠️ **Caveat BE da verificare**: non risulta un metodo `crea_ordine_da_preventivo`
> dedicato (solo `ordini_service.crea_ordine(payload)`). La premessa "conversione
> preventivo→ordine già fatta come copia 1:1" regge sul **modello**
> (`preventivi_righe` piatta), non su un metodo esistente. Allineare lato BE prima
> di promettere "gemello di `crea_ordine_da_preventivo`".

## 8. Riferimenti

- Analisi: [analisi-ordini-vendita.md §7.4](analisi-ordini-vendita.md).
- Preview contratti (target riuso): `vendite.fn_contratto_righe_preview`
  ([migration](../../../../db/changelog/migrations_v2/20_code/vendite/20260519-07-update-fn-contratto-righe-preview-add-qta-tipo-fonte-mctit.yaml)),
  wrapper `ContrattiRepository.list_righe_preview`
  (`backend/apps/vendite/db/contratti_repository.py`).
- Modello offerta: [offerte_commerciali](../../dbzero/vendite/tabelle/offerte_commerciali.md),
  [offerte_commerciali_eccezioni](../../dbzero/vendite/tabelle/offerte_commerciali_eccezioni.md).
- Push offerta→contratto (copia eccezioni 1:1, già a DB):
  `vendite.fn_push_offerta_a_contratto`.
- Context builder documenti offerta (stessa "fase 2", oggi mostra solo eccezioni):
  `backend/apps/vendite/services/offerta_document_context_builder.py`.
- Target copia: [ordini_righe](../../dbzero/vendite/tabelle/ordini_righe.md),
  `ordini_righe_componenti`.

## 9. Piano di lavoro a step (da evadere)

| # | Step | Tipo | Stato |
| --- | --- | --- | --- |
| S1 | Decisioni §6 | decisione | ✅ ratificate |
| S2 | Core `fn_espandi_listino_versione` — `20260604-02` | code | ✅ scritto |
| S3 | Refactor `fn_contratto_righe_preview` sul core — `20260604-03` | code (runOnChange) | ✅ scritto |
| S4 | `fn_offerta_righe_espanse` — `20260604-04` | code | ✅ scritto |
| S5 | pgTAP `test-offerta-righe-espanse.sql` (9 test) | test | ✅ scritto |
| S6 | Doc manuale (core + offerta + nota preview contratti) | docs | ✅ scritto |
| S7 | **Migrate + pgTAP** + validazione regressione drawer contratti | run | ✅ eseguito, verde (2026-06-04) |
| S8 | Commit / PR | git | ⏳ **attende "procedi"** |
| S9 | Hand-off BE (`list_righe_espanse` + crea ordine da offerta + endpoint + FE) | coordinamento | ✅ **fatto 2026-06-04** |

> ✅ **S9 — hand-off BE fatto (2026-06-04)**: `OfferteRepository.list_righe_espanse`
> (wrapper su `fn_offerta_righe_espanse`) + `ordini_service.crea_ordine_da_offerta`
> (guard `ACCETTATA`, prezzi negoziati preservati anche per i componenti via
> `componenti_overrides` → trigger ricompone il padre) + endpoint
> `POST /vendite/offerte/<id>/genera-ordine/` + azione FE su `OffertaDrawer`. Test
> BE 4/4, build FE verde. Caveat preventivo (componenti ri-prezzati) **non** si
> applica all'offerta: l'offerta accettata preserva i prezzi.

**Numerazione `NN`**: `20260604-02/03/04` (dopo `-01` del lock cliente, stesso giorno).

> ✅ **S7 — regressione verificata (2026-06-04)**: `fn_contratto_righe_preview`
> rifattorizzata sul core, output drawer righe contratti **invariato**. Quirk
> preservato: variazione globale sugli standalone, **non** sui bundle.
