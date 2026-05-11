# Refactor Componenti BoM CASO A — Piano di Sviluppo BE/FE

> **Stato**: aperto 2026-05-11. Primo del pattern, sorgente PREVENTIVI.
> **Brief DB collegato**: [brief-db-preventivi-righe-componenti-override.md](brief-db-preventivi-righe-componenti-override.md).
> **Pattern**: replicabile su 4 sorgenti future (ordini, contratti, DDT, consumi).

## 1. Contesto e obiettivo

Bug logico del modello scoperto allo smoke §3.4 del 2026-05-11: per
articoli compositi con componenti `esposto_in_fattura = TRUE` (CASO A),
il prezzo della riga padre del documento sorgente e' un **dato fantasma**:
al push viene ignorato silenziosamente perche' il resolver risolve N
prezzi per i componenti dal listino. Se uno dei listini manca, il push
esplode dopo l'accettazione del preventivo.

**Soluzione** (decisione di dominio 2026-05-11): ogni componente esposto
diventa una riga negoziabile a se' stante con prezzo proprio (suggerito
dal resolver + override manuale ammesso via L1). La riga padre diventa
contenitore con prezzo calcolato come SUM(componenti × coeff_qta) via
trigger DB. Al push i prezzi sono propagati ai componenti
`commesse_attivita` **senza ri-chiamare il resolver** (snapshot
pricing immutabile post-accettazione).

Strategia "5 tabelle simmetriche + helper `script.*`": 5 nuove tabelle
`<sorgente>_righe_componenti` con FK reali, logica trigger DRY tramite 4
fn generiche in `script.*` parametrizzate via TG_ARGV. Vedi brief DB per
dettagli completi.

## 2. Stato dipendenze

| Componente | Stato | Owner |
| --- | --- | --- |
| Brief DB preventivi + helper `script.*` | Atterrato 2026-05-11 (non committato) | DB team |
| Brief DB ordini/contratti/DDT/consumi | Da inviare dopo merge preventivi | DB team |
| Fix all-or-nothing push singolo | Atterrato 2026-05-11 | BE |
| Guida `gestione-listini.md` aggiornata §5.2.1 + §6.2 | Atterrato 2026-05-11 | BE |
| Test plan §3.4 esteso 3 scenari | Atterrato 2026-05-11 | BE |
| Implementazione BE preventivi (Fasi 1-4) | In corso | BE |
| Implementazione FE preventivi (Fase 5) | Bloccato in attesa BE | FE |

## 2.1 Delta DB rispetto al brief originale (recepito 2026-05-11)

Modifiche fatte dal team DB rispetto al brief inviato:

| Elemento | Brief proposto | DB team ha implementato |
| --- | --- | --- |
| Colonna FK articolo componente | `articolo_id` | `componente_id` (no ambiguita' con padre) |
| CHECK origine_prezzo | 6 valori (LISTINO incluso) | **5 valori**: `PROMO`, `CONTRATTO_OVERRIDE`, `CONTRATTO_LISTINO`, `CATEGORIA`, `MANUALE` (no `LISTINO`) |
| `fn_resolve_prezzo_composito` | 7 colonne in return | 8 colonne (aggiunta `origine_prezzo` finale) |
| Trigger calcola_quantita | `_a20_` | `_m50_` (fase intermedia valida) |
| Trigger propaga_qta su preventivi_righe | `_a30_` | `_z90_` (e' effetto AFTER, ordine lessicografico < ricalcola) |
| Trigger guard_pending componenti | Non incluso | **Aggiunto** `trgfn_preventivi_righe_componenti_guard_pending` (simmetrico a riga padre) |
| `trgfn_preventivi_guard_transizione_approvazione` | Non toccato | **Esteso** per controllare anche componenti PENDING |

**Impatto su Fase 1 (Repository)**:

- Query Python su `vendite.preventivi_righe_componenti` usa `componente_id`
  (NON `articolo_id`).
- `pricing_repository.resolve_prezzo_composito` deve aggiornare il `SELECT`
  per includere `origine_prezzo` (8a colonna).
- TypedDict `PreventivoRigaComponenteRow` ha campo `componente_id: UUID`.

**Impatto su Fase 2 (Service)**:

- Validazione `origine_prezzo` su `PayloadValidator.optional_*`: whitelist
  5 valori (NON 6).

**Impatto su Fase 5 (FE)**:

- Badge icone origine_prezzo: 5 (PROMO 🎁, CONTRATTO_OVERRIDE 📃, CONTRATTO_LISTINO 📋, CATEGORIA 📋, MANUALE ✏️). Niente icona "LISTINO" generica.

## 3. Cosa posso iniziare ORA (pre-merge DB)

Lavori indipendenti dalla tabella nuova, da fare in parallelo al team DB:

### 3.1 Documentazione guida `gestione-listini.md`
- §5.2: aggiungere paragrafo "Componenti CASO A nel ciclo preventivo
  -> commessa" con la regola del nuovo modello.
- §6: aggiungere eccezione "su compositi CASO A l'override L1 si
  applica sui singoli componenti, non sul padre".
- Nuova sottosezione §6.2 con esempio del flusso UX (3 scenari A/B/C
  dal mock).

### 3.2 Test plan smoke §3.4 esteso
- Aggiornare `sviluppo-listini-v5-test-ui.md` §3.4 con i 3 scenari:
  - **3.4.A** Tutto da listino (path felice)
  - **3.4.B** Componente con listino mancante + override manuale
  - **3.4.C** Sconto commerciale puntuale su un componente

### 3.3 Scaffolding FE (mock-driven)
- Composable `usePreventivoRigaComponenti.js` con API stub (404 finche'
  il BE non c'e') — pronto a essere "cablato" al merge BE.
- Bozza dei tipi TS/JSDoc per `RigaComponente` (id, articolo_componente_id,
  prezzo_unitario, origine_prezzo, listino_suggerito, warnings).
- Estensione `PreventiviRigheTable.vue` con prop `expanderEnabled` (default false): l'expander resta nascosto finche' la riga padre non ha `is_composito_caso_a = true` (flag derivato dal detail).

### 3.4 Mock test BE
- Skeleton di test unitari per `preventivi_service.crea_riga` /
  `gestisci_riga` / `update_componente` / `delete_componente` con mock
  repository — testano la logica di service, non l'integrazione DB.

### 3.5 Riprenotare risorse per smoke
- Verificare che il preventivo PRV0000034 (legacy ACCETTATO pre-fix
  EVASO) sia ancora utilizzabile come fixture, o crearne uno nuovo
  ad-hoc post-merge.

## 4. Cosa devo aspettare (post-merge DB)

Tutto cio' che tocca la nuova tabella + fn dominio:

- Repository BE reale (cursor con SELECT/INSERT/UPDATE su
  `preventivi_righe_componenti`)
- Service che chiama `fn_preventivo_riga_componenti_init` (DB)
- API view nidificata reali (CRUD componenti)
- `BoMComponentExpander` rewrite (legge da tabella invece di chiamare
  resolver al push)
- Test integrazione + smoke utente

## 5. Fasi PREVENTIVI (post-DB)

### Fase 1 — Repository

File: `backend/apps/vendite/db/preventivi_repository.py` (estendere)

Nuovi metodi su `PreventiviRepository`:
- `init_componenti(riga_padre_id, emittente_sr_id, data_riferimento) -> int`
  wrapper su `vendite.fn_preventivo_riga_componenti_init`. Ritorna numero
  componenti inseriti.
- `list_componenti(riga_padre_id) -> list[ComponenteRow]` (SELECT con JOIN
  ad `articoli_componenti` + `articoli` per display fields)
- `update_componente(componente_id, payload) -> ComponenteRow` (UPDATE
  prezzo + origine_prezzo + meta + prezzo_resolver_context)
- `delete_componente(componente_id) -> bool` (soft delete: `attivo = FALSE`)
- `get_componente(componente_id) -> ComponenteRow | None` (lookup singolo)

TypedDict nuovo in `types.py`: `PreventivoRigaComponenteRow`.

Test repository: con mock cursor, copertura CRUD + edge case (id non esistente, riga padre non composita).

### Fase 2 — Service

File: `backend/apps/vendite/services/preventivi_service.py` (estendere)

**Modifica `crea_riga`** (post-INSERT della riga padre):
- Se `articolo.is_composito = TRUE` e CASO A (almeno 1 componente esposto):
  chiama `repo.init_componenti(riga_padre_id, emittente_sr_id, data_riferimento)`.
- Il prezzo della riga padre verra' immediatamente sovrascritto dal trigger
  DB di ricalcolo — niente azione esplicita lato Python.

**Modifica `gestisci_riga` / `aggiorna_riga`**:
- Se cambia `articolo_id` su una riga esistente e l'articolo nuovo e' di
  natura diversa (composito CASO A ↔ semplice / CASO B): DELETE
  componenti esistenti + init se il nuovo e' CASO A.
- Se l'articolo padre resta lo stesso CASO A: niente azione (i componenti
  restano stabili).

**Nuovo `update_componente(componente_id, payload, auth_user_id)`**:
- Estrae `prezzo_unitario` + `meta` dal payload
- Calcola `prezzo_suggerito` dal `prezzo_resolver_context` del componente
- Se prezzo nuovo != suggerito: applica L1 (`prezzo_override_manuale`)
- Applica L2 (limiti % `VENDITE_MAX_SCONTO_PCT` ecc.) — stesso helper di oggi
- Applica L3 (richiesta_approvazione → crea pratica APPROVAZIONE_PREZZO
  se violazione L2) — stesso helper
- UPDATE via repo

**Nuovo `delete_componente(componente_id)`**:
- Soft delete (attivo=false). Il trigger DB ricalcola il padre.
- Guard: stato preventivo modificabile (DRAFT/EMESSO).

**Nuovo `list_componenti(riga_padre_id)`**:
- Wrapper su repo per la view di lettura.

Test service: 15+ test nuovi con mock repository (creazione composito,
update componente con override autorizzato/negato, delete idempotente,
guard stato).

### Fase 3 — API view

File: `backend/apps/vendite/api/preventivi_views.py` + `urls_v1.py`

Endpoint nidificati sotto la riga padre:

- `GET /api/v1/vendite/preventivi/<id>/righe/<riga_id>/componenti/`
- `PATCH /api/v1/vendite/preventivi/<id>/righe/<riga_id>/componenti/<componente_id>/`
- `DELETE /api/v1/vendite/preventivi/<id>/righe/<riga_id>/componenti/<componente_id>/`

`POST` (init) non e' esposto come endpoint dedicato: l'init avviene
automaticamente dentro `crea_riga` e `gestisci_riga`. Se in futuro
serve un "rinegozia componenti" esplicito (re-init forzato), si potra'
aggiungere.

Tutti i POST/PATCH/DELETE richiedono `Idempotency-Key` (policy progetto).

`@extend_schema` inline per OpenAPI. Test API: 8+ test (CRUD + auth + scope + idempotency).

### Fase 4 — `BoMComponentExpander` rewrite

File: `backend/apps/vendite/services/commesse_source_handlers.py`

Modificare `BoMComponentExpander._expand_rows`:
- Se `sorgente_codice = 'PREVENTIVO'` e la riga padre ha componenti in
  `preventivi_righe_componenti` (CASO A): bypassa resolver, legge
  direttamente i componenti dalla tabella. Costruisce le PushableRow
  usando `prezzo_unitario`, `quantita`, `articolo_id` di ogni componente.
- Status quo per CASO B (resolver al push) e per gli altri 4 sorgenti
  che non hanno ancora la propria tabella componenti — verra' esteso
  alla loro PR.

Cache modulo-level `is_caso_a` invalidata al boot (TTL 5 min come
`is_composito_cache` esistente).

Test BE: 5+ test su `BoMComponentExpander` con scenari CASO A vs CASO B.

### Fase 5 — Frontend

File:
- `frontend/src/vendite/preventivi/components/PreventiviRigheTable.vue`
- `frontend/src/vendite/preventivi/components/PreventiviRigaForm.vue`
- `frontend/src/vendite/preventivi/api/preventiviApi.js` (estendere)
- `frontend/src/vendite/preventivi/stores/preventivi.js` (azioni componenti)
- `frontend/src/core/composables/usePreventivoRigaComponenti.js` (nuovo)
- `frontend/src/locales/it.json` + `en.json` (chiavi nuove)

**Tabella righe (`PreventiviRigheTable.vue`)**:
- PrimeVue DataTable expander per righe con `is_composito_caso_a = true`
- Sotto-righe componenti renderizzate con indent `├─ └─`
- Icone origine prezzo (📋 LISTINO, ✏️ MANUALE, 🎁 PROMO, 📃 CONTRATTO)
- ⚠ accanto a icona se warning su listino mancante

**Form editing riga (`PreventiviRigaForm.vue`)**:
- Sezione "Componenti esposti in fattura" sotto il form padre
- Prezzo padre readonly (= "calcolato da componenti")
- Per ogni componente: prezzo editabile, badge origine, prezzo suggerito
  visibile, warning inline su listino mancante
- L1/L2/L3 indicators sui singoli componenti

**Composable (`usePreventivoRigaComponenti.js`)**:
- `load(rigaPadreId)` → list componenti
- `updateComponente(componenteId, payload)` → PATCH + reload
- `deleteComponente(componenteId)` → DELETE + reload
- Cache locale per non rifare fetch alla riapertura del drawer

**i18n keys nuove** (IT + EN):
- `preventivi.componenti.section_title` "Componenti esposti in fattura"
- `preventivi.componenti.prezzo_suggerito` "Suggerito da listino"
- `preventivi.componenti.listino_mancante` "Nessuna mappa listino"
- `preventivi.componenti.origine_*` (LISTINO/MANUALE/PROMO/CONTRATTO/CATEGORIA)
- `preventivi.componenti.l1_richiede_autorizzazione` "Richiede autorizzazione `prezzo_override_manuale`"

Test FE: smoke manuale + eventuale snapshot test se appropriate al progetto.

### Fase 6 — Smoke utente §3.4 end-to-end

Aggiornare `sviluppo-listini-v5-test-ui.md` §3.4 con i 3 scenari A/B/C
gia' definiti nei mock UX (sessione 2026-05-11).

Acceptance criteria:
- §3.4.A — tutte le mappe listino popolate → push OK, fattura con prezzi
  identici al preventivo
- §3.4.B — listino mancante su 1 componente → operatore inserisce manuale
  con autorizzazione L1, push OK, fattura riporta il prezzo manuale
- §3.4.C — sconto puntuale su 1 componente → push OK, fattura riporta
  il prezzo scontato

## 6. Stima effort PREVENTIVI

| Fase | Effort | Bloccato da |
| --- | --- | --- |
| 0 (pre-DB, ora) | 0.5gg | nulla |
| 1 (Repository) | 0.5gg | DDL DB merged |
| 2 (Service) | 1gg | Fase 1 + fn DB init merged |
| 3 (API) | 0.5gg | Fase 2 |
| 4 (Expander) | 0.5gg | Fase 1 |
| 5 (FE) | 1.5gg | Fase 3 |
| 6 (Smoke) | 0.5gg | Fase 5 |
| **Totale** | **5gg** | |

Tempi reali dipendono da quanto velocemente il team DB consegna il DDL +
fn helper + fn dominio init.

## 7. Pattern replicabile sui 4 sorgenti futuri

Per ognuno dei 4 sorgenti (ORDINI, CONTRATTI, DDT, CONSUMI):

### Cambia per sorgente

- Nome tabella (`<sorgente>_righe_componenti`)
- Nome FK padre (`riga_<sorgente>_id`)
- Nome tabella testata (`<sorgente>` / `contratti` / `attivita_consumi`)
- Colonna data riferimento (`data` / `valido_dal` / `data_lettura`)
- Fn helper dominio init (`fn_<sorgente>_riga_componenti_init`)
- Repository + Service di dominio (`ordini_service`, `contratti_service`, ecc.)
- API view nidificata sotto la testata del sorgente
- Componenti FE (`<Sorgente>RigheTable.vue`, `<Sorgente>RigaForm.vue`)
- Store + composable FE

### NON cambia (riusato dal pattern preventivi)

- 4 helper trigger function in `script.*` (gia' generiche con TG_ARGV)
- 3 codici errore `E_DOC_COMPONENTE_*` cross-dominio (gia' nel pattern)
- `BoMComponentExpander` logic: dispatch su `sorgente_codice` per leggere
  dalla tabella corretta (la logica espansione resta uguale)
- Pattern UX espander tabella + sezione componenti drawer
- Pattern L1/L2/L3 sui singoli componenti (stessi parametri di sistema)

### Differenze per sorgente da chiarire prima di iniziare la PR

- **ORDINI**: pattern identico a preventivi. Verificare nomi colonna testata.
- **CONTRATTI**: pricing modalita' A/B/C (vedi §3 `gestione-listini.md`) puo'
  richiedere logica init diversa. In modalita' B alcuni componenti potrebbero
  arrivare gia' con override sulla riga contratto — l'init deve rispettarli.
  Brief specifico da inviare prima della PR.
- **DDT**: se il DDT eredita da un ordine, i componenti potrebbero essere
  copiati dall'ordine senza re-init. Da decidere: cascata automatica o
  init separato sul DDT?
- **CONSUMI**: verificare se esistono articoli compositi CASO A nei consumi.
  Probabilmente raro (i consumi sono letture per UoM, non aggregati). Se non
  esiste use case reale, possiamo skippare la PR consumi.

### Stima effort per sorgente (post-preventivi)

~3gg a sorgente (DB merge da team in 0.5gg + BE+FE ~2.5gg).
Totale 4 sorgenti = ~12gg.

## 8. Decisioni di dominio gia' chiuse (riferimento)

Da non riaprire — gia' concordate con Tid:

1. Solo CASO A (componenti `esposto_in_fattura = TRUE`)
2. Stessi parametri L1/L2/L3 della riga padre — niente parametri dedicati
3. Quantita padre ≠ 1 ammessa: `quantita_componente_in_preventivo =
   coeff_qta × 1`, propagazione moltiplicativa al push
   (`quantita_in_commessa = quantita_componente × quantita_padre`)
4. 5 tabelle simmetriche con FK reali, NO tabella polimorfica
5. Helper trigger DRY in `script.*` parametrizzate via TG_ARGV
6. Push singolo all-or-nothing (gia' atterrato 2026-05-11): se anche
   un solo componente fallisce in fase di push, rollback totale

## 9. Riferimenti

- Brief DB: [brief-db-preventivi-righe-componenti-override.md](brief-db-preventivi-righe-componenti-override.md)
- Guida: `docs/it/guide/gestione-listini.md`
- Test UI: `docs/it/dev/work-in-progress/sviluppo-listini-v5-test-ui.md`
- WIP push singolo (handoff): `docs/it/dev/work-in-progress/sviluppo-push-singolo-preventivo.md`
- Memoria progetto: `feedback_bug_logici_modello`, `feedback_concentrico_no_yagni`
- Mock UX (sessione 2026-05-11, in chat): 3 scenari A/B/C
