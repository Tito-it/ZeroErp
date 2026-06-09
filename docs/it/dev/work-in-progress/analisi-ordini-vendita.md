# Analisi — Ordine di vendita (OdV): scheletro CRUD + lista configurabile + chiusura giro

> **Branch lavoro**: `dev/backend-tid` (BE/FE) + brief DB → `dev/db-tid`.
> **Natura**: documento di analisi operativo. La **strada implementativa DB**
> (changeset, vista, seed catalogo, ordine seed) la sceglie il team DB nel
> rispetto dei pattern già rodati (memoria `feedback_db_actions_passaggio_team`);
> BE/FE partono **solo** a DB consegnato (`feedback_be_fe_attende_prerequisiti_db`).
> **Origine**: richiesta Tid 2026-06-03 — dopo preventivi/listini/offerte/contratti
> si passa agli **ordini di vendita**, riusando al massimo le skill replicabili.
> **Template 1:1**: famiglia vendite già atterrata —
> [offerte](../../../../frontend/src/vendite/offerte/) (più recente, testata+righe),
> [preventivi](../../../../frontend/src/vendite/preventivi/) (righe+componenti BoM+integrazione),
> [lista-offerte-comm.md](../work-done/lista-offerte-comm.md) / [lista-preventivi.md](../work-done/lista-preventivi.md)
> (DEF-8 lista configurabile).

---

## 0. Obiettivo in una frase

Portare l'**ordine di vendita** da «schema DB pronto, zero applicativo» a
**dominio gestibile end-to-end**: scheletro CRUD (testata + righe + componenti
BoM + note), **lista configurabile DEF-8 costruita direttamente responsive**
(niente lista grezza da rifattorizzare dopo — inutile), e **chiusura del giro**
fino alla fattura riusando la pipeline esistente. Tutto clonando i building block
della famiglia vendite — **regola del 2** a tappeto (memoria
`feedback_regola_del_2_estrai_bb`).

---

## 1. Stato di partenza — cosa esiste e cosa manca

### ✅ DB — sostanzialmente COMPLETO (schema `vendite`)
Modello quasi pronto: serve la vista lista (§3) **+ una piccola estensione
additiva di 2 colonne** ratificata il 2026-06-03 (link documento di origine +
agente — §1.bis). Già presenti e operativi:

| Oggetto | Note |
| --- | --- |
| [vendite.ordini](../../dbzero/vendite/manual/ordini.md) (testata) | identità `(anno,serie,numero)`+`uid`, stato `config.stati_doc_ordini`, totali, `fatturazione_trigger`, `canale_origine`, `utility_id`, `emittente_fiscale_id` NOT NULL |
| `vendite.ordini_righe` | articolo+qta+prezzo+sconto+iva, `qta_operativa`/`uom_operativa_id`, propagazione qta componenti |
| `vendite.ordini_righe_componenti` | BoM compositi (modello unificato 13-05, `fn_ordine_riga_componenti_init`/`preview` già a DB) |
| `vendite.ordini_righe_fulfillment` | tracciamento evadibilità (downstream DDT — **fuori scope scheletro**) |
| `vendite.ordini_indirizzi` | snapshot indirizzi consegna (downstream — fuori scope scheletro) |
| `vendite.note_ordini` | partizione note (pattern `PartitionedNoteRepository`) |
| Trigger testata | default emittente, normalize, gen codice, guard emittente↔BA, guard scope, lock `numero`, immutabilità `canale_origine`, sync canali |
| RLS 3 facce | `rls_ordini_ef_whitelist` (OPERATORE) / `rls_ordini_cliente_ownership` (PORTALE) / `rls_ordini_shop` (SHOP) — già attiva |
| **Push a commessa** | `fn_list_ordini_da_pushare` (batch + singolo `p_ordine_id`) + `HandlerOrdini` (sorgente `ORDINE_VENDITA`) in [commesse_source_handlers.py:509](../../../../backend/apps/vendite/services/commesse_source_handlers.py) — **già testato** |
| PDF | tipo documento `ORDINE_VENDITA` seedato 2026-06-04 (vedi §12; la dicitura `ORDINE_CLIENTE` era stale) |

### ❌ Backend applicativo — QUASI NULLA
Esiste solo l'aggancio commesse (push). **Mancano**: `ordini_repository.py`,
`ordini_service.py`, `views_ordini.py`/`urls_ordini.py`, serializer/validator,
istanza note ordini in [note_views.py](../../../../backend/apps/vendite/api/note_views.py)
(il commento in quel file dichiara già «aggiungere ordini si riduce a clonare 3 righe»).

### ❌ Frontend — ZERO
Nessuna `src/vendite/ordini/`. **Vantaggio**: non c'è lista grezza pregressa →
la lista nasce **direttamente** `<ListaConfigurabile>` (vedi §6.1), saltando lo
step grezza→refactor che è costato a contratti/preventivi/offerte.

### Specificità OdV vs preventivi/offerte (rilevanti per il design)
1. **Niente revisioni** (`rev`) né **storico revisioni**: più semplice di
   preventivi/offerte. Niente toggle «mostra storico».
2. **Niente listino in testata** (l'ordine fissa i prezzi alla conferma sulle
   righe, non eredita una versione listino come offerta/contratto). Niente colonna
   listino composita.
3. **`numero` valorizzato già all'INSERT in BOZZA** (verificato sul DDL reale,
   2026-06-03): il trigger BEFORE INSERT `trgfn_ordini_gen_codice` genera
   `numero` via `script.fn_generate_codice('ordine')` se NULL/vuoto → **mai NULL**.
   Il lock (`trg_ordini_a10_lock_columns_upd` su `numero`) lo rende immutabile dopo.
   → lista espone `numero` nudo, nessun fallback (decisione §8.1). *(Il manuale
   `manual/ordini.md` afferma erroneamente «numerazione durante la conferma» →
   stale, da allineare, vedi §1.ter.)*
4. **`fatturazione_trigger`** (CONFERMATO/SPEDITO/CONSEGNATO): nuovo asse, governa
   **quando** scatta il push a commessa. Ereditato da `billing_account.fatturazione_ordini`.
5. **`canale_origine`** (ADMIN/PORTALE/SHOP): immutabile post-INSERT; in
   back-office è sempre ADMIN.
6. **Logistica/trasporto NON è in testata ordine** — non per omissione ma per
   **scelta di modello già attuata**: la migration `20251027-01-ordini-refactor-testata`
   ha **droppato** (`dropColumn`) `causale_trasporto_id`, `aspetto_bene_id`,
   `vettore_soggetto_ruolo_id`, `modalita_addebito_trasporto_id` dalla testata
   ordine (vivono/vivranno sul DDT a valle). → **fuori scope scheletro**, nessun
   campo trasporto nel drawer. *(Il manuale `manual/ordini.md` elenca ancora quei
   campi tra FK e «vedi anche» → stale, da allineare, §1.ter.)*
7. **Pagamento/valuta testata snella**: la stessa migration ha droppato anche
   `giorni_pagamento` e `fine_mese` (ora derivati da `billing_account`). Restano
   in testata `modalita_pagamento_id`, `termine_pagamento_id`, `valuta_id`,
   `tasso_cambio` (default 1). → drawer espone modalità/termine/valuta; **`tasso_cambio`
   fuori dal drawer** (default 1, non gestito in UI scheletro — decisione Tid).

---

## 1.bis. Estensioni di modello ratificate (2026-06-03)

Analisi del modello (richiesta Tid): la testata ordine ha **due lacune** che
conviene chiudere **prima** dello scheletro, perché aggiungerle dopo significa
rifare vista lista + serializer + drawer + test (lavoro doppio — memoria
`feedback_simmetria_modello_no_meta_scope` + `feedback_no_quick_fix_soluzione_assoluta`).
Ratificate per l'integrazione **A** e **E**; B/C/D/F rimandate (vedi §8.bis).

### A — Link documento di origine (preventivo/offerta → ordine) ✅ RATIFICATO
Oggi `vendite.ordini` ha solo `sorgente_tipo_id`/`sorgente_uid` (meccanismo
**generico pensato per import CRM esterno**, FK `config.sorgenti`): **non** è un
link interno tipizzato al documento commerciale da cui l'ordine nasce. Senza,
l'ordine «nasce dal nulla» e la conversione preventivo/offerta→ordine perde
provenienza/tracciabilità.

- **Requisito**: link **interrogabile** documento commerciale upstream → ordine.
  Due strade valutate:
  - **(A1) — RATIFICATA (Tid, 2026-06-03)**: FK tipizzata dedicata
    `documento_origine_tipo` (lookup/enum `PREVENTIVO`/`OFFERTA`/…) +
    `documento_origine_id bigint`, **senza UNIQUE**.
  - **(A2) — SCARTATA**: riuso di `sorgente_tipo_id`/`sorgente_uid` come link
    interno, estendendo `config.sorgenti` con i tipi documento interni.
- **Perché A1 e non A2** (rettifica post-verifica DDL 2026-06-03, vedi
  [db-brief-ordini-vendita.md §1.A](../work-done/db-brief-ordini-vendita.md)): A2 sembrava più
  «simmetrica» con le righe (che usano `sorgente_*` con UQ di idempotenza import), ma
  la verifica ha scoperto che quella simmetria è **fuorviante**. ① L'UQ
  `uq_ordini_v_sorgente_fk` su `(sorgente_tipo_id, sorgente_uid)` imporrebbe in testata
  l'invariante **«1 preventivo/offerta → 1 ordine»**, bloccando riordini e consegne
  parziali (regola di dominio implicita, non voluta). ② `config.sorgenti` ha già
  `PREVENTIVO`/`OFFERTA_COMMERCIALE` con `scope=PUSH_*` (registry handler), semantica
  **diversa** dalla provenienza → riusarli sovraccarica la colonna. A1 modella la
  provenienza in modo esplicito, senza UNIQUE → **più ordini da una stessa origine**;
  costo equivalente (memoria `feedback_no_quick_fix_soluzione_assoluta` +
  `feedback_simmetria_modello_no_meta_scope`).
- **(A1-bis) — REVERSAL PARZIALE per `OFFERTA` (RATIFICATA Tid, 2026-06-07/08)**:
  il «senza UNIQUE» resta valido per `PREVENTIVO` (**1:N** — riordini/consegne
  parziali, modello split per riga in
  [brief-preventivi-ordini.md](brief-preventivi-ordini.md)), ma **NON** per
  `OFFERTA`. L'offerta è una condizione quadro **atomica** (nessuna riga
  selezionabile) → genera **al massimo UN ordine** (1:1 di testata), imposto da
  un **UNIQUE parziale** `uq_ordini_v_documento_origine_offerta`
  `WHERE documento_origine_tipo = 'OFFERTA'` + guard BE
  `E_ORD_OFFERTA_GIA_CONVERTITA`. Inoltre contratto e ordine generati da
  un'offerta sono **mutuamente esclusivi** (XOR permanente, recupero = nuova
  offerta): vedi
  [brief-db-univocita-offerta-ordine.md](../work-done/brief-db-univocita-offerta-ordine.md).
- **Nota di confine**: A *abilita* la conversione preventivo/offerta→ordine (oggi
  inesistente) ma **non** la implementa in questo scheletro — la conversione è uno
  step successivo (§7.4). Qui si predispone solo la colonna + la valorizzazione in
  CREATE quando l'ordine arriva da un upstream.

### E — Agente/venditore ✅ RATIFICATO
Colonna `agente_soggetto_ruolo_id bigint NULL` FK `anagrafiche.soggetti_ruoli`
(ruolo agente/commerciale), per provvigioni e reporting commerciale. Display in
vista: `agente_denominazione` (via SR). Nullable (non tutti gli ordini hanno
agente).

> Entrambe sono **azioni DDL** → entrano nel **brief DB-ORD** (§3.0) come
> prerequisito; BE/FE attendono la consegna (memoria
> `feedback_be_fe_attende_prerequisiti_db`). Sono additive e nullable → nessun
> impatto sui trigger/RLS esistenti.

---

## 1.ter. Allineamento documentazione stale (verifiche 2026-06-03) — ✅ CHIUSO

> **✅ RISOLTO (verifica 2026-06-04)**: i disallineamenti sotto sono **già stati
> corretti** dal team DB nella consegna DB-ORD. `manual/ordini.md` ora descrive
> correttamente colonne trasporto rimosse, numerazione all'INSERT, agente (E) +
> documento_origine (A1); `manual/ordini_righe.md` marca il check
> `chk_ordini_v_r_qta_pos` come **corretto** (`20260603-11`). La tabella sotto è
> ormai **storia** (cosa era stale e cosa si è corretto), non un TODO aperto.

Verifica su DDL/trigger reali → il manuale **`manual/ordini.md`** descriveva uno
stato **pre-refactor**, corretto per coerenza (richiesta Tid). Disallineamenti
(tutti sanati):

| Punto manuale stale | Realtà DDL/trigger | Azione |
| --- | --- | --- |
| «Aggiornamento numerazione possibile solo da trigger durante la **conferma**» | `trgfn_ordini_gen_codice` genera `numero` **all'INSERT** (BOZZA) se NULL | correggere prosa numerazione |
| Sezione «Trasporto e consegna» + FK `causale_trasporto_id`/`aspetto_bene_id`/`vettore_soggetto_ruolo_id`/`modalita_addebito_trasporto_id` + link «vedi anche» | colonne **droppate** da `20251027-01-ordini-refactor-testata` | rimuovere sezione/FK/link trasporto |
| `giorni_pagamento`/`fine_mese` tra i campi pagamento | **droppati** (ora da BA) | rimuovere dai campi pagamento |

E **`manual/ordini_righe.md`** già autodocumenta il **bug del check** (`chk_ordini_v_r_qta_pos`
replica `prezzo` invece di `quantita > 0`) → la correzione va nel brief (§3.0).

> Nota perimetro: la correzione del **manuale dbzero** è documentazione (la faccio
> contestualmente); la correzione del **check DDL** è azione DB (brief, team DB).

---

## 2. Standard e building block governanti (vincolanti)

Il lavoro NON inventa pattern: applica quelli già scritti (CLAUDE.md). In sintesi
(dettaglio identico a [lista-preventivi.md §1](../work-done/lista-preventivi.md)):

- **Backend** — [api.md](../api.md): `DomainAPIView` (`area_funzionale='vendite'`),
  `parse_list_params`, envelope `success_response`+`paginated_envelope`, tiebreaker
  `id`, `is_search_endpoint=True` su list+export, scope emittente
  `get_scope_user_id`→`script.fn_get_emittenti_scope_pk_ids` (**PK reale**, non
  sr_id — memoria `feedback_emittente_pk_vs_soggetto_ruolo`), `ServiceError`/
  `ErrorManager` (mai `try/except Exception` in view), `handle_post_json`,
  `PayloadValidator` + `map_integrity_error` (memoria `feedback_payload_helpers_duplicati`),
  pricing via `PricingService` (memoria `feedback_pricing_centralizzato`), export
  via `apps.ui.api.export_helpers` + `ListaExportService` (param `formato`, mai
  `format` — memoria `feedback_drf_format_magic_param`; rispetta ordine/visibilità/
  permessi — `feedback_export_lista_rispetta_preferenza`).
- **Frontend** — [frontend-standards.md](../frontend/frontend-standards.md):
  toolbar UNICA caller (memoria `feedback_lista_pattern_standard`),
  `<ListaConfigurabile>` + `useListaConfigurabilePage` + `CellaConfigurabile`
  (formatter built-in `currency_eur`/`date_short`/`datetime_short`),
  `useResponsiveColumns` (ritiro dinamico, ereditato), `RowActionsMenu` (memoria
  `feedback_row_actions_menu`), drawer autonomi + readonly (`feedback_drawer_readonly`),
  `if (result !== null)` (`feedback_drawer_result_check`), store `userScoped:true`
  (`feedback_pinia_userscoped`), blob fuori da `useApiHandler`
  (`feedback_blob_download_no_useapihandler`), i18n `$t()` namespace `vendite.ordini.*`.
- **Building block riusati** (cataloghi BB BE/FE): `PartitionedNoteRepository`,
  `PricingService`, `ListaExportService`, `UiService.get_lista_config`;
  `ListaConfigurabile`, `useListaConfigurabilePage`, `CellaConfigurabile`,
  `PageActionsBar`, `ReadonlyBadge`, `AccessoBloccatoPanel`, `ExportDialog`,
  `LookupSelect`, `UtilityPerRuoloSelect`, `RowActionsMenu`, componenti
  ComponentiPanel/Dialog (da preventivi).

---

## 3. Workstream DB (input per il team DB su `dev/db-tid`) — attende delivery

> **Nota di processo (Tid, 2026-06-03)**: non si scrive un brief separato.
> **Questa analisi è l'input**: il team DB ne deriva il proprio changeset/brief
> (vista, seed, DDL A+E, fix check) scegliendo la strada implementativa nel
> rispetto dei pattern (memoria `feedback_db_actions_passaggio_team`). Le voci §3.x
> descrivono il *cosa serve*, non il *come* (changelog/ordine seed = scelta DB).

`priorita` (DB-A) **già atterrato** con i refactor lista contratti/preventivi →
qui serve il workstream **DB-ORD**: **estensione modello A+E** (§3.0) + vista lista
+ definizione + catalogo + preset. Righe/componenti/note già esistono.

### 3.0 Estensione modello testata (A+E) — DDL additivo

Changeset additivo/correttivo (additive+nullable → no impatto trigger/RLS):
- **A — link origine (A1 ratificata, §1.bis)**: FK tipizzata dedicata
  `documento_origine_tipo` (vocabolario PREVENTIVO/OFFERTA — enum o lookup, scelta DB)
  + `documento_origine_id bigint`, **entrambe nullable, senza UNIQUE** (più ordini da
  una stessa origine — **eccetto `OFFERTA`**, 1:1 con UNIQUE parziale per il reversal
  A1-bis §1.bis). **NON** riusare `config.sorgenti`/`sorgente_*` (A2 scartata:
  l'UQ `uq_ordini_v_sorgente_fk` imporrebbe l'1:1 e lo `scope` PUSH_* ha altra
  semantica — vedi [db-brief §1.A](../work-done/db-brief-ordini-vendita.md)). Riferimento
  polimorfo (preventivo *o* offerta secondo il tipo): integrità garantita alla
  valorizzazione (conversione §7.4), non con FK fisica unica.
- **E — agente**: `agente_soggetto_ruolo_id bigint NULL` FK
  `anagrafiche.soggetti_ruoli` (+ guard `child_requires_active_parent` coerente
  con gli altri FK della testata).
- **FIX check riga (punto verificato 2026-06-03)**: `chk_ordini_v_r_qta_pos` oggi
  replica `prezzo_unitario >= 0` → **correggere a `quantita > 0`** (su un ordine la
  riga a quantità 0 non ha senso; l'omaggio è `quantita > 0` + `prezzo 0`).
  Valutare anche il CHECK di co-presenza `(uom_operativa_id IS NULL) =
  (qta_operativa IS NULL)` raccomandato da `manual/ordini_righe.md`. Additivo/
  correttivo, basso rischio → incluso nel lotto per evitare un giro di ritorno.
- pgTAP: presenza colonne A+E + FK + nullability; `quantita > 0` rifiutato; co-presenza UoM.

### 3.1 Vista canonica `vendite.vw_ordini_lista` (NUOVA)

Non esiste alcuna vista lista per ordini → si crea **da zero** già canonica
(convenzione `vw_<entita>_lista`, `security_invoker=on`, self-contained), con i
nomi **canonici** richiesti da DEF-8 (combaciano col `campo_sorgente` del catalogo,
trigger B2). Espone:

- `ragione_sociale_completa` (cliente via istanza/SR — stessa logica
  soggetto-via-istanza delle altre liste vendite, 1 join, valorizzato anche per
  prospect; memoria `feedback_display_fields_backend` + `feedback_cliente_billing_account`)
- `id_fiscale_univoco_cf_piva`
- `ba_codice` (alias legittimo per evitare collisione `codice`)
- `stato_descrizione`, `stato_codice_interno` (per Tag severity FE)
- `numero`, `serie`, `anno`, `data`, `totale_doc` (+ `imponibile_tot`, `iva_tot`,
  `sconto_tot`), `utility_codice`, `utility_descrizione`,
  `fatturazione_trigger`, `canale_origine`, `modalita_pagamento_codice`,
  `termine_pagamento_codice`, `valuta_codice`, `emittente_fiscale_id`/`_codice`,
  `data_insert`, `billing_account_id`, `soggetto_ruolo_id`, `id`, `uid`
- **`documento_origine_tipo`/`documento_origine_codice`** (A — provenienza
  upstream, es. `PREVENTIVO · P-2026/123`) e **`agente_denominazione`** (E — via
  SR agente)
- `numero` esposto **nudo** (sempre valorizzato dal trigger gen codice, anche in
  BOZZA — decisione §8.1; niente `numero_display`).

> Lezione DEF-8 (ripetuta perché è il punto che si sbaglia sempre): nomi
> cliente/id.fiscale **canonici** in vista, `sensibile=false` su tutte le colonne,
> ogni `campo_sorgente` esiste come colonna della vista (anti-typo, trigger B2 + pgTAP).

### 3.2 Entry `ui.lista_definizione` (seed CSV)

```
id=7, codice='vendite.ordini', descrizione='Ordini di vendita',
schema_dati='vendite', vista_sql='vw_ordini_lista', attivo=t
```
(id progressivo dopo `vendite.offerte`=6; il trigger `valida_vista_sql` richiede
la vista già esistente al seed → vista prima della definizione.)

### 3.3 Catalogo colonne `ui.lista_colonna` (lista_id=7) + preset di sistema

Catalogo §4. Seed gemello offerte/preventivi:
- `ui.lista_colonna` — preset + extra opt-in (`priorita` + `larghezza_default`).
- `ui.lista_preset` — `ordini_default`, `ambito='sistema'`, `is_default=t`,
  `pagina_dimensione=25`, `ordinamento_default=[{"col":"data","dir":"desc"}]`.
- `ui.lista_preset_colonna` — colonne visibili di default (§4 «Preset ✓»); extra
  con `visibile=false`.
- `priorita` seedata via changelog dedicato (pattern `20260602-16`).
- Resync sequenze IDENTITY `ui.*` già risolto a monte da `20260602-17` (`runAlways`).

### 3.4 (Eventuale) note ordini
Lo schema `vendite.note_ordini` esiste già: nessun lavoro DB. L'aggancio è solo
backend (§5.4, istanza `PartitionedNoteRepository`).

---

## 4. Catalogo colonne proposto (`vendite.ordini`, lista_id=7)

> Due assi (come famiglia): `ordine_default` = ordine visivo; `priorita` = peso di
> permanenza nel ritiro dinamico (più alto = si ritira per ultima); `largh_def` =
> `larghezza_default` (standard + soglia packing-a-somma).

**Colonne preset (visibili):**

| ord | codice | campo_sorgente | tipo_colonna | tipo_dato | formato | largh | priorita | gruppo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | numero | numero | identificatore | string | — | 130 | 100 (max) | Identificazione |
| 20 | data | data | informazione | date | date_short | 110 | 60 | Identificazione |
| 30 | ragione_sociale_completa | ragione_sociale_completa | informazione | string | — | 200 | 95 | Cliente |
| 40 | ba_codice | ba_codice | informazione | string | — | 120 | 40 | Cliente |
| 50 | id_fiscale | id_fiscale_univoco_cf_piva | informazione | string | — | 140 | 75 | Cliente |
| 60 | utility_codice | utility_codice | informazione | string | — | 100 | 70 | Fornitura |
| 70 | totale_doc | totale_doc | informazione | numeric | currency_eur | 130 | 80 | Importi |
| 80 | fatturazione_trigger | fatturazione_trigger | informazione | string | — | 120 | 30 | Ciclo vita |
| 90 | stato | stato_descrizione | informazione | string | — | 130 | 90 | Stato |
| 100 | azioni | (NULL) | azione | string | — | 60 | 100 (max) | — |

**Colonne tecniche nascoste (preset ✗, servono al FE):**

| ord | codice | campo_sorgente | note |
| --- | --- | --- | --- |
| 110 | stato_codice_interno | stato_codice_interno | severity Tag (`statoOrdineSeverity`); `ordinabile=f` `ricercabile_full=f` |

**Colonne extra opt-in (`visibile=false` nel preset):**

| ord | codice | campo_sorgente | tipo_dato | formato | priorita | gruppo |
| --- | --- | --- | --- | --- | --- | --- |
| 120 | utility_descrizione | utility_descrizione | string | — | 10 | Fornitura |
| 130 | canale_origine | canale_origine | string | — | 12 | Ciclo vita |
| 140 | imponibile_tot | imponibile_tot | numeric | currency_eur | 18 | Importi |
| 150 | iva_tot | iva_tot | numeric | currency_eur | 18 | Importi |
| 160 | modalita_pagamento | modalita_pagamento_codice | string | — | 15 | Pagamento |
| 170 | termine_pagamento | termine_pagamento_codice | string | — | 12 | Pagamento |
| 180 | valuta | valuta_codice | string | — | 12 | Importi |
| 190 | emittente_fiscale_codice | emittente_fiscale_codice | string | — | 15 | Emittente |
| 200 | anno | anno | integer | — | 10 | Identificazione |
| 210 | serie | serie | string | — | 10 | Identificazione |
| 215 | documento_origine | documento_origine_codice | string | — | 22 | Origine |
| 218 | agente | agente_denominazione | string | — | 20 | Commerciale |
| 220 | data_insert | data_insert | datetime | datetime_short | 5 | Audit |

**Note di dominio:**
- `numero` = unico `identificatore` (frozen). **Sempre valorizzato** dal trigger
  gen codice, anche in BOZZA (decisione §8.1) → nessun fallback. Niente colonna
  `rev` (gli ordini non hanno revisioni).
- `ricercabile_full=t` su `numero`, `ragione_sociale_completa`, `ba_codice`,
  `id_fiscale` (allineato alla ricerca repo).
- `stato` reso via slot `#cell-stato` (Tag severity) — **niente badge scaduta**
  (concetto offerta-specifico, non applicabile a ordini).
- `fatturazione_trigger` in preset perché è l'asse OdV-specifico che spiega il
  comportamento di fatturazione (CONFERMATO/SPEDITO/CONSEGNATO); priorità bassa
  (30) → si ritira presto se manca spazio.
- `totale_doc` e date via formatter built-in `CellaConfigurabile`.

---

## 5. Workstream Backend (`apps/vendite/` + `apps/ui/`) — attende DB

Gemello `offerte_*`/`preventivi_*`. Differenze: **niente revisioni** (più
semplice), **niente listino testata**, **+`fatturazione_trigger`**.

### 5.1 Repository — `ordini_repository.py` (NUOVO)
Clone strutturale di [offerte_repository.py](../../../../backend/apps/vendite/db/offerte_repository.py)
/ [preventivi_repository.py](../../../../backend/apps/vendite/db/preventivi_repository.py):
- `list_ordini(...)`: legge da **`vw_ordini_lista`**; filtri stato/utility/data
  (`data_da` default anno-1, memoria `feedback_filtro_data_liste`), scope emittente
  `fn_get_emittenti_scope_pk_ids`, ricerca ILIKE su `numero`/`ragione_sociale_completa`
  (+ `ba_codice`/`id_fiscale`). `order_by`/`order_dir` con whitelist
  `_ORDER_COLS_ORDINI` = `numero | data | ragione_sociale_completa | ba_codice |
  utility_codice | totale_doc | stato_codice_interno`. Tiebreaker `v.id` SEMPRE.
  **Niente `solo_attiva`** (non c'è storico revisioni).
- `get_ordine(id)` + `_SELECT_COLS_ORDINE` (testata completa per il detail).
- CRUD testata+righe: `upsert_ordine`, `upsert_riga`, `delete_riga`,
  componenti via `fn_ordine_riga_componenti_init`/`_preview` (clone preventivi).
- **Doppia quantità operativa/base** (verificato: `ordini_righe` ha
  `qta_operativa`/`uom_operativa_id`, `quantita` derivata via `factor_to_base`,
  trigger `trgfn_qta_from_operativa`): **riusare la logica standard già fatta in
  preventivi/contratti** (clone 1:1) — input con **priorità all'operativa**, GET
  restituisce **entrambe**, pricing/totali girano su `quantita` base. Verificare
  che `OrdiniRigaForm`/`upsert_riga` siano allineati al pattern esistente, non
  reinventati (regola del 2).
- Guard post-`fetchone()` (`if not row: raise ServiceError`).

### 5.2 Service — `ordini_service.py` (NUOVO)
Clone di [offerte_service.py](../../../../backend/apps/vendite/services/offerte_service.py)
/ `preventivi_service.py`:
- `list_ordini(...)` propaga `order_by`/`order_dir`.
- CRUD testata (`create_ordine`/`update_ordine`) con `PayloadValidator`
  (validazione campi, `null_vs_empty`→NULL memoria `feedback_null_vs_empty`),
  default emittente/utility/valuta via resolver esistenti (memoria
  `feedback_utility_da_istanza`), pricing righe via `PricingService.resolve_prezzo`.
- `resolve_filtri_export_label(...)` per la riga «filtri applicati» dell'export.
- **`fatturazione_trigger`**: default ereditato da BA (già fa il trigger DB
  `trgfn_ordini_normalize`); il service espone override esplicito sul payload.
- **`agente_soggetto_ruolo_id`** (E): campo opzionale sul payload testata, lookup
  SR ruolo agente.
- **`documento_origine_*`** (A): valorizzato dal service quando l'ordine nasce da
  un upstream (predisposto ora; la conversione vera è §7.4). In CREATE diretto
  resta NULL.

### 5.3 View/API — `views_ordini.py` + `urls_ordini.py` (NUOVI)
Clone di [views_offerte.py](../../../../backend/apps/vendite/api/views_offerte.py)
/ [urls_offerte.py](../../../../backend/apps/vendite/api/urls_offerte.py):
- `GET /api/v1/vendite/ordini/` (list, `is_search_endpoint`, `order_by`/`order_dir`,
  default `data`), `GET /{id}/` (detail), `POST /` (create), `PUT/PATCH /{id}/`,
  `DELETE /{id}/` (vietato se confermato/collegato a DDT — guard DB già presente).
- Righe: `POST/PUT/DELETE /{id}/righe/...` + componenti (clone preventivi).
- **`ApiOrdiniExportView`** → `GET /api/v1/vendite/ordini/export/?formato=csv|xlsx`:
  `DomainAPIView`, `is_search_endpoint=True`, `parse_export_format`,
  `ListaExportService` con `lista_codice='vendite.ordini'`, cap `EXPORT_MAX_ROWS`,
  `build_export_response`, `@extend_schema`.
- `_LISTA_CODICE_ORDINI = 'vendite.ordini'`.
- Azioni di stato (§7): `POST /{id}/conferma/` (+ eventuale `POST /{id}/push/`).

### 5.4 Note ordini — 3 righe in `note_views.py`
Aggiungere l'istanza `_ORDINI_REPO = PartitionedNoteRepository(schema='vendite',
tabella='note_ordini', target_col='ordine_id', ...)` e cablare le rotte note
ordini, esattamente come PREVENTIVO/CONTRATTO/OFFERTA (il file lo dichiara già).

### 5.5 Test BE
- `tests/api/test_ordini_api.py`: list (scope, filtri, ordinamento whitelist),
  CRUD testata+righe, componenti, export (csv/xlsx, cap, magic param `formato`),
  conferma+push (§7). Mock DB (regole CI AGENTS.md).
- Verde `./manage-test.sh apps.vendite.tests -v 2` + `apps.ui.tests`.

---

## 6. Workstream Frontend (`src/vendite/ordini/` — NUOVO albero) — attende DB

Clone dell'albero [preventivi/](../../../../frontend/src/vendite/preventivi/)
(ha righe+componenti+integrazione) con la **lista già DEF-8** (niente grezza).

### 6.1 Lista — `OrdiniSearchTable.vue` direttamente `<ListaConfigurabile>`
**Nessuna lista grezza intermedia** (richiesta Tid: il refactor successivo è
inutile). Si nasce gemelli di
[ContrattiSearchTable.vue](../../../../frontend/src/vendite/components/ContrattiSearchTable.vue):
- `<ListaConfigurabile codice="vendite.ordini">` + scaffolding
  **`useListaConfigurabilePage(store, {...})`**: `exportFn: exportOrdini`,
  `getExportParams: buildExportParams`, `newTooltipKey:'vendite.ordini.nuovo_ordine'`,
  `onNew: () => emit('new')`, `searchTableOptions:{ defaultSortField:'data',
  defaultSortOrder:'desc' }`.
- **Toolbar caller** (UNICA esterna): filtri stato (`LookupSelect` su
  `config.stati_doc_ordini`, value `codice_interno`) + utility (`UtilityPerRuoloSelect`)
  + data Dal/Al. **Niente toggle storico revisioni** (non esiste per ordini).
  `PageActionsBar` con suffix Tag dirty/salvata + `ReadonlyBadge`.
- **Slot `#cell-stato`**: `<Tag :value="data.stato_descrizione"
  :severity="statoOrdineSeverity(data.stato_codice_interno)" />`.
- **Slot `#actions`**: `RowActionsMenu` → PDF (tipo `ORDINE_VENDITA`, disabilitato in
  BOZZA via `stato_codice_interno`) + gestisci note (`OrdineNoteDrawer`) +
  **conferma/push** (§7) come azione di riga condizionale. `:force-compact`.
- `totale_doc` e date: formatter built-in. `numero` plain (sempre valorizzato,
  decisione §8.1). `AccessoBloccatoPanel` + `useInjectBlocked`.

### 6.2 Drawer — `OrdiniDrawer.vue` (testata + righe + componenti + note)
Clone di `PreventiviDrawer.vue`:
- Tab **Testata**: cliente (`billing_account` lookup ricco, memoria
  `feedback_billing_account_lookup` + `feedback_autocomplete_restore`), utility,
  emittente fiscale (default), data, valuta, modalità/termine pagamento,
  **`fatturazione_trigger`** (select CONFERMATO/SPEDITO/CONSEGNATO, default da BA),
  **agente** (E — lookup SR agente, opzionale), `canale_origine` read-only (ADMIN
  in back-office). Se l'ordine ha provenienza (A), banner/chip read-only
  «origine: {documento_origine_codice}». `useInjectReadonly`.
- **Fuori dal drawer** (decisione Tid 2026-06-03): `tasso_cambio` (default 1, non
  gestito in UI scheletro); `giorni_pagamento`/`fine_mese` **non esistono in
  testata** (droppati, §1.7) → derivano da `billing_account`, nessun campo.
- Tab **Righe**: `OrdiniRigheTable` + `OrdiniRigaForm` (master-detail inline,
  memoria `feedback_master_detail_inline`) + `OrdiniRigaComponentiPanel` (BoM,
  clone preventivi).
- Pattern create auto-save BOZZA (memoria `feedback_drawer_create_autosave_bozza`)
  se Tid lo conferma per gli ordini; altrimenti CREATE classico.
- `if (result !== null)` su save; `DrawerFooter`.

### 6.3 Store + API FE
- `stores/ordini.js` (`userScoped:true`): `fetchList` con `order_by`/`order_dir`/
  filtri; `fetch/create/update/remove`, righe, componenti, `conferma`/`push`.
- `api/ordiniApi.js`: CRUD + `exportOrdini(params)` →
  `api.get('${BASE}/export/', { params, responseType:'blob' })` (blob fuori da
  `useApiHandler`, memoria `feedback_blob_download_no_useapihandler`).
- `views/OrdiniView.vue` (caller lista+drawer), `constants.js` (severity stato,
  costanti fatturazione_trigger), eventuale `OrdineNoteDrawer.vue`.

### 6.4 i18n
Namespace `vendite.ordini.*`; chiavi colonne `vendite.ordini.col_*` da
`etichetta_i18n_key` del catalogo; export/dialog da `lista_config.*` + `common.*`.
Verificare assenza orfane. Attenzione `@` letterale → `{'@'}` (memoria
`feedback_vue_i18n_linked_escape`).

### 6.5 Build FE verde
`./node_modules/.bin/vite build` (via nvm).

---

## 6.bis. Pricing e articoli compositi — RIUSO BB obbligatorio (regola del 2)

Punto critico (richiesta Tid): preventivi/offerte/contratti hanno **già** un
metodo condiviso sia per il **pricing** sia per gli **articoli compositi (BoM)**.
Ordini **non reinventa nulla** — consuma gli stessi building block (memoria
`feedback_regola_del_2_estrai_bb` + `feedback_pricing_centralizzato`).

### 6.bis.1 Pricing — `PricingService` + `_pricing_gate_helpers` (BE)
- **`PricingService.resolve_prezzo()`** ([pricing_service.py](../../../../backend/apps/vendite/services/pricing_service.py)):
  wrapper 1:1 su `fn_resolve_prezzo_listino_v2`, gestisce anche il **prezzo del
  componente nel contesto del padre composito** via `p_articolo_padre_contesto`.
  **Mai** lookup diretto su `listini_righe`/contratti (memoria
  `feedback_pricing_centralizzato`).
- **`_pricing_gate_helpers.py`** ([_pricing_gate_helpers.py](../../../../backend/apps/vendite/services/_pricing_gate_helpers.py)):
  orchestratore gate prezzi (L1/L2/L3, override/check) condiviso da
  preventivi/offerte/contratti. Il pattern `resolve_or_check_override_prezzo_riga_*`
  + `_apply_pricing_gate_riga` (vedi `contratti_service.py`/`offerte_service.py`)
  si **clona** per ordini → `resolve_or_check_override_prezzo_riga_ordine`, **non**
  si riscrive la logica.
- **Livello gate applicabile agli ordini — da allineare alla famiglia**: l'ordine
  fissa i prezzi alle righe (no listino in testata, §1.2). Va deciso se l'ordine
  usa il pricing **stile preventivo** (resolve + override semplice) o eredita anche
  il gate L2/L3 stile contratti. In ogni caso **passa dai BB sopra**, non da query
  dirette. *(Decisione di dominio da chiudere prima del BE — §8.bis.)*

### 6.bis.2 Articoli compositi (BoM) — BB già estratti
**Backend**:
- DB già pronto: `fn_ordine_riga_componenti_init` / `_preview` (gemelli
  `fn_preventivo_*`/`fn_contratto_*`), modello unificato componenti 13-05 (3 livelli:
  struttura/listino/documento — memoria `feedback_listini_immutabilita`).
- Prezzo componenti via `PricingService.resolve_prezzo(p_articolo_padre_contesto=…)`
  (sopra). Espansione per il push commessa via `BoMComponentExpander`
  ([commesse_source_handlers.py](../../../../backend/apps/vendite/services/commesse_source_handlers.py)),
  già usata da `HandlerOrdini`.

**Frontend — NON creare nuovi componenti**: i BB compositi sono **già estratti** in
[src/vendite/_shared/componenti/](../../../../frontend/src/vendite/_shared/componenti/):
- `ComponentiPanel.vue`, `ComponentiDialog.vue`, `ComponentiCreateActionsPanel.vue`,
  `useComponentiDialog.js`, `rowComponenti.js`.
- composable core: [useRigaComponenti.js](../../../../frontend/src/core/composables/useRigaComponenti.js)
  + api [componentiBom.js](../../../../frontend/src/core/api/componentiBom.js).
- `PreventiviRigaComponentiPanel.vue` è solo un **thin wrapper** sul BB condiviso →
  per ordini al massimo un `OrdiniRigaComponentiPanel.vue` analogo (poche righe),
  **non** una nuova implementazione. Pattern auto-open CREATE + expansion lista già
  rodato (handoff `20260527_offerta_componenti_bom`).

> In sintesi: per pricing e compositi il lavoro ordini è **cablaggio del doc-type
> «ordine» sui BB esistenti**, non sviluppo. Se durante il clone emerge la
> tentazione di copiare logica invece di riusare il BB, è il segnale (regola del 2)
> di fermarsi e riusare.

---

## 6.ter. FE scheletro — stato consegnato + scelte deliberate (2026-06-03)

Albero `src/vendite/ordini/` creato e **build FE verde** (clone famiglia
vendite, lista DEF-8 diretta). File: `api/ordiniApi.js`, `stores/ordini.js`
(`userScoped`), `constants.js`, `views/OrdiniView.vue`, `components/`
(`OrdiniSearchTable`, `OrdiniDrawer`, `OrdiniForm`, `OrdiniRigheTable`,
`OrdiniRigaForm`, `OrdiniRigaComponentiPanel`, `OrdineNoteDrawer`). Wiring core:
`severity.statoOrdineSeverity`, `READONLY_MODELS.ORDINE`, `TAB_ENTITIES.ORDINE`,
`MANAGE_ICONS.SEND`, `NAV_ICONS.ORDINI` + voce menu + rotta, i18n `it/en`
(`vendite.ordini.*` + `col_*` allineate al catalogo `lista_id=7`).

**Riuso BB (regola del 2)**: `useListaConfigurabilePage`, `ListaConfigurabile`,
`makeComponentiBomApi`, `ComponentiPanel`, `useArticoloUomOptions`,
`VenditeNoteDrawer`, `RowActionsMenu`, `PageActionsBar`, `EmittenteFiscaleField`,
`BillingAccountLookup`. Nessuna logica nuova per pricing/componenti/note.

### Scelte deliberate / cose mancanti (scheletro)

1. **Agente (E) omesso dal form drawer — blocco di modello, non solo UI.**
   Verifica 2026-06-04: manca l'intero sottosistema agente (il ruolo `VENDITORE`
   esiste ma non ci sono soggetti, né flusso di creazione, né lookup, né guard sul
   FK). La colonna `agente_soggetto_ruolo_id` **resta nullable e non gestita**
   (decisione Tid). Tema rinviato a sviluppo dedicato →
   [analisi-ruolo-agente.md](analisi-ruolo-agente.md). La colonna
   `agente_denominazione` resta opt-in nella lista (catalogo), di fatto vuota.
2. **PDF in lista omesso.** Non c'è generazione documenti `ORDINE_VENDITA` nello
   scheletro BE (nessun endpoint `/documenti/`): la lista resta consultazione +
   note. Si aggancia `EntityPdfButton`/`PdfDocumentiSorgenteDialog` quando esisterà
   l'emissione documenti ordini → **dettaglio operativo DB/BE/FE in §12 (stampa
   ordine)**, sezione aggiunta su richiesta Tid 2026-06-04.
3. **`documento_origine` (A1)**: chip read-only nell'header del drawer quando
   valorizzato; lo scheletro non lo scrive (lo farà la conversione §7.4).
4. **Prezzo riga senza endpoint "suggerisci"**: gli ordini non hanno
   `/suggerisci-prezzo/`. Il campo prezzo è opzionale: se lasciato vuoto (e
   articolo non composito) il BE lo risolve via `PricingService` in
   `gestisci_riga`. Niente badge origine prezzo / banner L2 (pricing stile
   preventivo, gate L2/L3 = decisione aperta §8.bis).
5. **Componenti compositi: ~~niente `ComponentiDialog` pre-save in CREATE~~ →
   ECCEZIONE RIMOSSA (2026-06-05).** *(Stato iniziale scheletro: `gestisci_riga`
   non accettava `componenti_overrides`, componenti inizializzati ai prezzi
   risolti, editabili solo in EDIT — divergenza voluta da preventivi/contratti.)*
   Su richiesta Tid l'ordine è stato **allineato al pattern famiglia**:
   `gestisci_riga` ora accetta `componenti_overrides` (gate L1
   `validate_componenti_overrides_authorization` + `normalize_componenti_overrides`
   → `fn_ordine_riga_componenti_init`, lo stesso path già usato dalla conversione
   offerta→ordine) e `OrdiniRigaForm` apre la `ComponentiDialog` pre-save riusando
   i BB `useComponentiDialog`/`ComponentiDialog`/`ComponentiCreateActionsPanel`
   (regola del 2, zero componenti nuovi). L'editing in EDIT via
   `OrdiniRigaComponentiPanel` resta. Override prezzo richiede permesso
   `prezzo_override_manuale`; la fn DB rifiuta prezzo 0 su componente obbligatorio.
6. **Conferma/push via `useConfirmAction`** (no `AppDialog`): sono sì/no puri →
   lo standard preferisce `useConfirmAction`. Push singolo con toast
   differenziato per `report.stato` (gemello `PreventiviIntegrazione`).
7. **Cliente immutabile post-creazione** (lock FE `billing_account_id` quando
   `hasDetail`): vedi bug BE sotto.

### ✅ Bug logico BE — CHIUSO (2026-06-04, `feedback_bug_logici_modello`)

**Era**: `ordini_service.aggiorna_ordine` aveva `billing_account_id` nella whitelist
`_UPDATE_KEYS_ORDINE` ma **non ri-derivava `soggetto_ruolo_id`** (lo fa solo
`crea_ordine`) → cambiare BA in update lasciava `soggetto_ruolo_id` stantio,
**incoerenza cliente↔soggetto** (verificato: `vendite.ordini` denormalizza sia
`billing_account_id` sia `soggetto_ruolo_id` NOT NULL, e **nessun trigger DB li
ri-sincronizza** su UPDATE — `trgfn_ordini_normalize` tocca solo
`fatturazione_trigger`).

**Fix applicato — opzione (a) "cliente immutabile"**: `billing_account_id`
**rimosso** da `_UPDATE_KEYS_ORDINE` + guard in `aggiorna_ordine` che **rifiuta
esplicitamente** (`E_ORD_VALIDAZIONE`) un tentativo di *cambiare* il BA, mentre
**tollera** il BA invariato re-inviato dal form FE (no silent-ignore). Scelta
coerente con preventivi/offerte (che NON denormalizzano `soggetto_ruolo_id` e
trattano cliente/utility come immutabili post-create) e con il lock FE già
presente. Test: `test_ordini_service.py` (cambio BA rifiutato / BA invariato
tollerato / payload senza BA aggiorna) — 12/12 verdi + `test_ordini_api` 9/9.

**Difesa DB autoritativa — ✅ ATTERRATA (DB-ORD-LOCK, 2026-06-04)**, con
**scostamenti dal brief iniziale** (brief
[db-brief-ordini-lock-cliente.md](../work-done/db-brief-ordini-lock-cliente.md)):

- meccanismo via **registro data-driven** `dbops.automation_lock_columns` (2
  righe → trigger generato `trg_ordini_a10_lock_columns_upd`), **non** trigger
  scritti a mano come ipotizzato nella prima stesura;
- codice errore **dedicato `E_ORD_CLIENTE_IMMUTABILE`** (id DB 469), scartato il
  generico `CODICE_NON_MODIFICABILE`;
- **deliverable extra non previsto**: cleanup di `trgfn_ordini_normalize` →
  eredità `fatturazione_trigger` ora **solo su INSERT** (il ramo UPDATE era logica
  morta, contraddittoria col lock). Cambio di comportamento esplicito ratificato.

**Hand-off BE completato (2026-06-04)**: `E_ORD_CLIENTE_IMMUTABILE` registrato in
`error_policies.py` (400); il guard BE `aggiorna_ordine` ora solleva **lo stesso
codice** (unificato service↔DB — estratto da `_db_errors` su UPDATE diretta che
bypassa il service). Guard BE = defense-in-depth + messaggio parlante.

### BB guardia empty-state estratto + adottato (regola del 2, OK Tid 2026-06-03)

La guardia empty-state di `fetchList` (search<3, no-filtri→vuoto, svuota→reset)
era **identica in 3 store** (`offerte`, `preventivi`, `ordini`). Estratta in
[`useListaEmptyStateFetch`](../../../../frontend/src/core/composables/useListaEmptyStateFetch.js):
stato lista + guardia + orchestrazione loading/response nel BB; `hasActiveFilters`,
`buildParams` (la mappatura filtri→query, che **diverge** legittimamente: vedi
paginazione sotto), `fetchPage` iniettati. Adottato nei 3 store. Build verde.

**Convergenza con `createCrudListStore`** (factory store CRUD-semplice, adottata
da clienti/fornitori/soggetti/articoli): a refactor factory concluso (OK Tid), la
factory ora **delega la guardia a `useListaEmptyStateFetch`** → gate
**single-source** per entrambe le famiglie. Layering: `useListaEmptyStateFetch`
= primitiva gate; la factory ci costruisce sopra (param-builder generico 1:1 +
`limit/offset` + `extraActions: fn(id)`) per il CRUD-semplice; i 3 store-documento
vendite (offerte/preventivi/ordini), "ricchi" (transizioni + righe + componenti +
push; param non-1:1: offerte rinomina `data_da`→`validita_dal_min`, preventivi usa
`page/page_size`; azioni righe multi-arg), usano il composable **direttamente**.
Build verde su entrambe le famiglie.

### Paginazione FE↔BE riallineata allo standard (RISOLTO 2026-06-03)

Lo **standard** è `limit`/`offset`: l'helper BE `parse_list_params`
(`apps/core/api/payload_validators.py`) legge `limit`/`offset` e calcola `page`
internamente. Lo usano clienti, soggetti, categorie_clienti, contratti,
**offerte**, **ordini**. **`preventivi` era l'unico outlier** (BE leggeva
`page`/`page_size`, FE convertiva `offset`→`page`). **Riallineato (OK Tid)**:
- **BE** `preventivi_views.py::get` ora usa `parse_list_params` + chiama
  direttamente `list_preventivi_rows` (limit/offset, primitiva già esistente,
  gemella di `list_ordini_rows`) + `paginated_envelope` — mirror esatto della
  view ordini. `order_dir` mantiene il default di dominio `desc`. Schema
  OpenAPI: `page`/`page_size` → `limit`/`offset`.
- **FE** `stores/preventivi.js` invia `limit`/`offset` (rimossa la conversione).
- **Wrapper interno** `preventivi_service.list_preventivi(page, page_size)`
  **invariato** (lo usano AI tool `vendite_tools` + 3 test service, paging-based
  legittimo): il riallineamento tocca solo la superficie HTTP, non il contratto
  Python interno.
- Verifica: 129 test `apps.vendite.tests.*preventiv*` verdi, build FE verde.
  Nota: il test API lista è uno smoke di route (401/403, non esercita la logica);
  la logica limit/offset è coperta da `list_preventivi_rows` (test service) +
  parità costruttiva con la view ordini testata.

---

## 7. Chiudere il giro — ordine → commessa → fattura

Il valore di filiera: a valle dell'ordine **è già tutto cablato e collaudato**.
L'unico applicativo nuovo è **conferma + push UI**; il resto è riuso puro.

```
Ordine BOZZA ──[CONFERMA]──► (stato CONFERMATO)
            └─ fatturazione_trigger = CONFERMATO ──► push a commessa
                                                      (fn_list_ordini_da_pushare
                                                       + HandlerOrdini, già testato)
                                                          └─► attivita_fatturabili
                                                                  └─► pipeline lotto
                                                                       (LottoPipelineRunner,
                                                                        DRAFT→EMESSA→DEFINITIVA)
                                                                          └─► Fattura
            └─ fatturazione_trigger = SPEDITO/CONSEGNATO ──► l'ordine NON pusha;
                                                              pusha il DDT (fn_list_ddt_da_pushare)
                                                              [fase DDT, fuori scope scheletro]
```

### 7.1 Conferma ordine (applicativo NUOVO, minimo)
- **BE**: `POST /api/v1/vendite/ordini/{id}/conferma/` → service cambia stato a
  CONFERMATO (il trigger DB gen codice valorizza `numero`, lock su `numero`).
  Guard data-driven sullo stato (le transizioni ammesse le decide il DB; il BE
  non hardcoda — memoria `feedback_no_hardcoded_ids`).
- **FE**: azione di riga/drawer «Conferma ordine» (eventuale dialog di conferma
  semplice). Gemello del pattern azione-stato già usato in offerte/contratti
  (memoria `feedback_stato_terminale_con_data` per la struttura pulsante+dialog,
  qui senza data).

### 7.2 Push a commessa — singolo on-demand (riuso, INCLUSO nello scheletro)
Decisione §8.3: **stesso pattern attuale di preventivi/offerte = push singolo**
(non batch). Incluso nello scheletro, non rimandato.
- **BE**: endpoint `POST /api/v1/vendite/ordini/{id}/push/` che invoca
  `HandlerOrdini`/orchestratore con `sorgente_uid` del singolo ordine, su
  `fn_list_ordini_da_pushare(p_ordine_id := ...)` (già esistente, precedente
  [sviluppo-push-singolo-preventivo.md](sviluppo-push-singolo-preventivo.md)).
- **FE**: dialog «push a commessa» clone 1:1 di
  [OffertaPushDialog.vue](../../../../frontend/src/vendite/offerte/components/dialogs/OffertaPushDialog.vue)
  (pattern idempotenza: seconda push fallisce con errore controllato).
- **Idempotenza via stato `EVASO` — ✅ CABLATA (2026-06-08)**: l'idempotenza
  «seconda push fallisce» era specificata qui ma non implementata (l'ordine
  restava `CONFERMATO` e il push era ripetibile all'infinito, no-op silenzioso).
  Risolto come per il preventivo ([brief-db-stato-preventivo-evaso.md](../work-done/brief-db-stato-preventivo-evaso.md)):
  nuovo stato terminale **`EVASO`** (DB, team) + transizione auto
  `CONFERMATO→EVASO` (`meta.manuale=false`); `ordini_service.push_a_commessa`
  fa `update_stato(EVASO)` su esito `COMPLETATO` (specchio
  `preventivi_service`). Da `EVASO` il guard `_STATI_PUSHABILI={CONFERMATO}`
  blocca il re-push (`E_ORD_STATO_TRANSIZIONE`) e la capability nasconde il
  bottone (reason `ORDINE_GIA_EVASO`). FE invariato (data-driven + `loadDetail`).
- **Nota architetturale** (tensione segnalata da Tid): la capacità **batch**
  resta a DB (`fn_list_ordini_da_pushare` senza `p_ordine_id` +
  `fatturazione_trigger`), ma la UX adottata in tutta la famiglia è il **push
  singolo manuale**. «Per ora si fa lo stesso»; un eventuale ripensamento
  batch-vs-singolo riguarderebbe l'intera famiglia, non solo ordini.

### 7.3 A valle — nessun lavoro
`attivita_fatturabili` → pipeline lotto → fatture → PDF/SDI: **interamente
esistente e collaudato** (PROJECT_CONTEXT «Pipeline fatturazione»). Lo scheletro
ordine + conferma chiude quindi un **giro vendita→fattura end-to-end** riusando
~90% di codice.

### 7.4 A monte — conversione preventivo/offerta → ordine

**Preventivo → ordine: ✅ FATTO (2026-06-04).**

- **BE**: `ordini_service.crea_ordine_da_preventivo(preventivo_id)` — guard stato
  `ACCETTATO` (`E_ORD_ORIGINE_NON_CONVERTIBILE` se no, `E_PREV_NOT_FOUND` se
  inesistente), copia testata (BA/utility/valuta/termine/emittente) + righe 1:1
  (prezzi **congelati**; rename `sconto_percentuale`→`sconto_perc`) + componenti
  BoM (struttura ri-inizializzata ai prezzi correnti — vedi caveat sotto), e
  valorizza `documento_origine = ('PREVENTIVO', preventivo_id)` via
  `repo.set_documento_origine` (UPDATE mirato, non tocca le colonne lockate dal
  DB-ORD-LOCK). Orchestrazione Python riusando `crea_ordine` + `gestisci_riga` in
  una transazione. Provenienza senza UNIQUE (A1) → più ordini da uno stesso
  preventivo (riordini). Endpoint `POST /api/v1/vendite/preventivi/<id>/genera-ordine/`
  (`ApiPreventivoGeneraOrdine`). Test 3/3 (ok/stato/not-found).
- **FE**: azione statica «Genera ordine» in `PreventiviDrawer` (gated su
  `ACCETTATO`, nascosta in readonly) → `generaOrdineFromPreventivo` + toast col
  numero ordine + `emitDataChanged(ORDINE)`.
- **Caveat componenti** (v1): per le righe composite la struttura BoM è copiata
  ma i prezzi componente sono **ri-risolti all'ordine** (`gestisci_riga` re-init),
  non congelati dal preventivo. Coerente con "ordine a prezzi correnti"; copia
  fedele dei prezzi componente = enhancement futuro (l'override-map di
  `init_componenti_riga` chiavia per id sorgente↔target in modo non banale).

**Offerta → ordine: ✅ FATTO (2026-06-04, prerequisito DB atterrato).** L'offerta
non ha righe materializzate (listino + eccezioni OVERRIDE/ESCLUSIONE/AGGIUNTA): le
righe «effettive» sono prodotte dalla **fn DB `fn_offerta_righe_espanse`**
(ordine-ready: listino + variazione + eccezioni, con BoM, IVA/uom risolte; core
condiviso `fn_espandi_listino_versione`, refactor preview contratti senza
regressione). Brief atterrato:
[db-brief-offerta-righe-espanse.md](../work-done/db-brief-offerta-righe-espanse.md).

- **BE**: `OfferteRepository.list_righe_espanse` (wrapper fn) +
  `ordini_service.crea_ordine_da_offerta` (guard `ACCETTATA` →
  `E_ORD_ORIGINE_NON_CONVERTIBILE`; not-found `E_VENDITE_NOT_FOUND`). **Prezzi
  negoziati PRESERVATI** (l'offerta è accettata): non-composito = prezzo congelato;
  composito = componenti via `componenti_overrides` dal jsonb della fn → il trigger
  `trgfn_componenti_ricalcola_padre` ricompone il prezzo padre dai prezzi negoziati.
  *(Caveat: la fn DB `fn_ordine_riga_componenti_init` rifiuta un override prezzo 0;
  un componente negoziato a 0 è escluso dagli override e ricade sul resolver
  corrente — limitazione nota del vincolo override DB, raro nei bundle.)*
  *(Asimmetria voluta col preventivo, che ri-prezza i componenti correnti — vedi
  caveat sopra; l'offerta accettata richiede fedeltà.)* Testata: BA/utility/
  emittente/valuta (offerta non ha termine/modalità pagamento). Helper testata
  condiviso `_crea_testata_ordine_da_origine` (regola del 2 con preventivo).
  Endpoint `POST /api/v1/vendite/offerte/<id>/genera-ordine/`
  (`ApiOffertaGeneraOrdine`). Test 4/4 (ok/stato/not-found/override-coercion).
- **FE**: azione statica «Genera ordine» su `OffertaDrawer` (gated su `ACCETTATA`,
  nascosta in readonly) → store `generaOrdine` (emette evento tab ordini) +
  `generaOrdineFromOfferta` api + toast col numero. Build verde.

---

## 8. Decisioni RATIFICATE (Tid, 2026-06-03)

1. **`numero` sempre presente** ✅: la numerazione è valorizzata dal trigger DB
   (`trgfn_ordini_gen_codice`) **già in BOZZA** → `numero` non è mai NULL. Niente
   `numero_display`/fallback `(bozza)`: la vista espone `numero` nudo, il FE lo
   rende plain. *(Nota: l'indice `uq_ordini_v_anno_serie_numero` è parziale su
   `numero IS NOT NULL`, ma di fatto la colonna è sempre valorizzata.)*
2. **Auto-save BOZZA in CREATE** ✅ (memoria `feedback_drawer_create_autosave_bozza`):
   **stesso pattern di offerte/preventivi** — create auto-save al primo set di campi
   minimi → «edit-evolved» interno, abbandono con confirm + DELETE.
3. **Push singolo on-demand** ✅: **stesso pattern attuale di preventivi/offerte**
   (oggi il push è fatto singolo, non batch). → dialog push singolo clone di
   `OffertaPushDialog` incluso nello scheletro (§7.2), non rimandato. *(Tensione
   segnalata da Tid: la capacità batch resta a livello DB via
   `fn_list_ordini_da_pushare`/`fatturazione_trigger`, ma la UX adottata è il push
   singolo per coerenza con la famiglia. «Per ora si fa lo stesso».)*
4. **`fatturazione_trigger` colonna visibile** ✅ (provvisorio): resta nel preset
   con priorità bassa (30) → visibile ma si ritira presto. Spiegazione semantica
   fornita a Tid (CONFERMATO=fattura alla conferma / SPEDITO/CONSEGNATO=fattura al
   DDT, default ereditato da `billing_account.fatturazione_ordini`). Tid può
   spostarla in opt-in se la ritiene troppo di nicchia.
5. **Ricerca estesa** ✅: `ba_codice`/`id_fiscale` inclusi in `ricercabile_full`
   (oltre `numero`/`ragione_sociale_completa`).

### Estensioni di modello — esito ratifica (2026-06-03)

✅ **Integrate ora** (brief DB-ORD §3.0): **A** link documento di origine
(**variante A1** — FK dedicata senza UNIQUE, ratificata dopo verifica DDL; A2
scartata, §1.bis), **E** agente/venditore.

### 8.bis. Rimandate (registrate, basso costo futuro)

Non integrate ora per non gonfiare lo scheletro; **additive e nullable** → si
aggiungono in futuro senza churn dei trigger/RLS (la vista/serializer vanno scritti
lasciando spazio, memoria `feedback_concentrico_no_yagni`):

- **B — Riferimento ordine cliente** (`numero_ordine_cliente` + `data_ordine_cliente`):
  da stampare su DDT/fattura. Quando emergerà il fabbisogno fiscale a valle.
- **C — Date di consegna** (`data_consegna_richiesta`/`_confermata`, probabilmente
  a livello **riga**): da affrontare con la fase **fulfillment/DDT** (è lì che ha
  senso pieno).
- **D — Revisione ordine** (`numero`+`rev` come preventivi/offerte): **solo se** il
  business ri-emette la conferma d'ordine al cliente dopo modifica (altrimenti
  `storico` copre l'audit). Decisione di dominio aperta.
- **F — Tipo/causale ordine** (enum `tipo_ordine` default STANDARD): quando entrano
  reso/RMA, campione, conto-deposito.

**Decisione di dominio — ✅ CHIUSA (di fatto presa allo scheletro BE):**

- **Livello pricing dell'ordine** (§6.bis.1): **adottato il pricing stile
  preventivo** — `ordini_service._resolve_prezzo_riga` usa
  `PricingService.resolve_prezzo` (resolve semplice via BB condiviso, mai query
  dirette), **senza** gate L2/L3 stile contratti (`_pricing_gate_helpers`). Niente
  banner L2 / badge origine prezzo (coerente con §6.ter punto 4). Scelta ratificata
  a posteriori sul codice scritto (verifica 2026-06-04); un eventuale upgrade al
  gate L2/L3 resterebbe additivo e passerebbe comunque dagli stessi BB.

---

## 9. Sequenza consigliata

> **Stato avanzamento (verifica 2026-06-04)**: passi 1-5 ✅ **FATTI**; restano
> aperti la chiusura-giro/smoke (6-7) e gli item residui raccolti in §9.bis.

1. ✅ **Ratifica decisioni §8** (Tid).
2. ✅ **Consegna al team DB** (`dev/db-tid`): brief eseguibile
   [db-brief-ordini-vendita.md](../work-done/db-brief-ordini-vendita.md) —
   **estensione modello A+E**, **fix check** `chk_ordini_v_r_qta_pos` →
   `quantita > 0`, vista `vw_ordini_lista` canonica, `ui.lista_definizione` id=7 +
   catalogo + preset `ordini_default` + `priorita` + pgTAP. **DB ATTERRATO + pgTAP
   verdi** (changeset `20260603-11..15`).
3. ✅ **Attendere consegna DB** (memoria `feedback_be_fe_attende_prerequisiti_db`).
4. ✅ **BE scheletro** (§5): repository (list+CRUD+componenti) + service + view/urls
   (`ordini_repository.py`/`ordini_service.py`/`views_ordini.py`/`urls_ordini.py`) +
   export + note (istanza `PartitionedNoteRepository` in `note_views.py`) +
   conferma/push. *(Resta il bug BA-update §9.bis #1.)*
5. ✅ **FE scheletro** (§6): albero `src/vendite/ordini/` con lista DEF-8 diretta +
   drawer (testata+righe+componenti) + store/api + i18n; build verde. *(Picker
   agente E omesso, §6.ter.1.)*
6. ⏳ **Chiusura giro** (§7): conferma ordine end-to-end + push singolo;
   smoke ordine→commessa→fattura.
7. ⏳ **Smoke E2E**: lista carica/filtri/ritiro colonne/personalizzazione/export
   CSV-XLSX rispetta ordine-visibilità, CRUD testata+righe+componenti, note,
   PDF `ORDINE_VENDITA` (§12 — da fare), conferma→push→attività fatturabile generata.
8. Riepilogo a video + attesa OK Tid (memoria `feedback_memoria_solo_su_richiesta`).

## 9.bis. Item residui aperti (verifica 2026-06-04)

Cosa resta **davvero da fare** dopo lo scheletro BE+FE:

1. ✅ **Bug BE BA-update** — **CHIUSO 2026-06-04** (§"Bug logico BE — CHIUSO"):
   `billing_account_id` rimosso dalla whitelist update + guard cambio BA. **Difesa
   DB lock-columns atterrata** (DB-ORD-LOCK, con scostamenti dal brief: registro
   `automation_lock_columns`, codice dedicato `E_ORD_CLIENTE_IMMUTABILE`, cleanup
   `trgfn_ordini_normalize` INSERT-only). Codice **unificato service↔DB**. Test verdi.
2. ✅ **Stampa PDF** (§12) — **COMPLETA 2026-06-04** (anteprima on-demand,
   §12.4a): tipo documento `ORDINE_VENDITA` seedato (DB), context builder + view
   documenti + route (BE), `EntityPdfButton` nel drawer + client/costanti/i18n
   (FE). **Template HTML + versione PUBBLICATA creati** → stampa end-to-end
   (l'anteprima rende il PDF).
3. ⛔ **Agente (E)** (§6.ter.1): **NON è solo un picker mancante** — manca l'intero
   sottosistema. Il ruolo `VENDITORE` esiste in tassonomia, ma non ci sono soggetti
   con quel ruolo, né flusso di creazione, né lookup, né guard sul FK (accetta
   qualsiasi ruolo — difetto logico). **Decisione Tid 2026-06-04**: colonna
   `agente_soggetto_ruolo_id` **resta nullable e non gestita**; il tema è oggetto
   di analisi/sviluppo dedicato → [analisi-ruolo-agente.md](analisi-ruolo-agente.md).
4. 🟢 **Conversione upstream** (§7.4): **preventivo → ordine** e **offerta → ordine**
   entrambe **FATTE 2026-06-04** (BE service + endpoint `genera-ordine` + test, FE
   azione sui rispettivi drawer, `documento_origine` valorizzato). L'offerta usa la
   fn DB `fn_offerta_righe_espanse` (atterrata) con prezzi negoziati preservati.
5. 🟡 **Smoke E2E** (passo 7) non ancora eseguito.

---

## 10. Test (cosa verificare)

- **pgTAP**: vista `vw_ordini_lista` espone tutti i `campo_sorgente` del catalogo
  (incl. `stato_codice_interno`); `lista_definizione` `vendite.ordini` risolve via
  `fn_resolve_lista_config`; preset di sistema ritorna le colonne visibili
  nell'ordine atteso + tecniche nascoste; extra opt-in `visibile=false`; nessuna
  colonna filtrata per SUPER_ADMIN (`sensibile=false`).
- **BE Django**: list (scope emittente, filtri, ordinamento whitelist, tiebreaker),
  CRUD testata+righe+componenti, export csv/xlsx + cap + magic param `formato`,
  note, conferma (transizione stato + gen numero), push (idempotenza), guard delete
  su ordine confermato.
- **FE**: build verde + smoke §9.7.

---

## 11. Stato famiglia liste/domini vendite

| Dominio | Lista DEF-8 | CRUD/drawer | Doc |
| --- | --- | --- | --- |
| `vendite.contratti` | ✅ atterrato (`1cc906377`) | ✅ | [refactor-lista-contratti.md](../work-done/refactor-lista-contratti.md) |
| `vendite.preventivi` | ✅ completato 2026-06-03 | ✅ | [lista-preventivi.md](../work-done/lista-preventivi.md) |
| `vendite.offerte` | ✅ completato 2026-06-03 | ✅ | [lista-offerte-comm.md](../work-done/lista-offerte-comm.md) |
| **`vendite.ordini`** | ✅ **BE+FE scheletro 2026-06-03** (lista DEF-8 + CRUD + conferma + push) | ✅ (vedi §6.ter scelte deliberate + bug BE BA-update) | questo doc |

---

## 12. Stampa documento ordine (PDF) — DB / BE / FE

> **Origine**: richiesta Tid 2026-06-04 — la stampa non era stata prevista nello
> scheletro (§6.ter punto 2). Si usa **lo stesso sistema** del modulo `documenti`
> ([guide/documenti-e-stampe.md](../../guide/documenti-e-stampe.md)) già adottato
> da **preventivi**, **offerte commerciali** e **contratti**: tipo documento →
> template versionato (HTML/CSS) → context builder per dominio → render WeasyPrint
> → `documenti_generati` + file archiviato. **Niente nuovo motore, niente nuova
> infrastruttura**: ordini è il **quarto dominio cablato** sugli stessi BB (regola
> del 2 — memoria `feedback_regola_del_2_estrai_bb`). Il lavoro è clone +
> wiring, non sviluppo.

### 12.0 Modello già rodato — i due codici che devono allinearsi

La generazione passa per **due lookup per codice** (mai ID hardcoded, memoria
`feedback_no_hardcoded_ids`) che il seed DB deve far combaciare con BE:

1. **`config.sorgenti.codice`** → risolto a runtime da
   [`resolve_contesto_documentale`](../../../../backend/apps/documenti/api/contesto_helpers.py)
   (`DocumentiRepository.get_sorgente_tipo_id_by_codice`). Per gli ordini **esiste
   già**: `ORDINE_VENDITA` (usato da `HandlerOrdini` push, canali
   `trgfn_documenti_sync_canali`, `fn_resolve_termini_pagamento`). → la view ordini
   userà `_CODICE_SORGENTE_ORDINE = "ORDINE_VENDITA"`.
2. **`documenti.template_documenti.context_builder_code`** (colonna NOT NULL) →
   dispatch del builder via
   [`registry.get_builder(code)`](../../../../backend/apps/documenti/services/context_builders/registry.py)
   dentro `document_generation_service._build_context_for_sorgente`. Il seed del
   **template** ordine deve impostare `context_builder_code = "ORDINE_VENDITA"`,
   uguale al `CODE` del builder BE (§12.2). *(Convenzione famiglia: preventivo usa
   `PREVENTIVO`, offerta `OFFERTA_COMMERCIALE`, contratto `CONTRATTO` — per ordini
   il codice naturale è `ORDINE_VENDITA`, **ratificato dal team DB 2026-06-04**.)*

> **⚠️ Rettifica 2026-06-04 (verifica team DB)**: il tipo documento per ordini è
> **`ORDINE_VENDITA`**, *non* `ORDINE_CLIENTE` (codice scelto coerente con la
> sorgente `config.sorgenti='ORDINE_VENDITA'` e col `context_builder_code` — tutta
> la famiglia usa `tipo documento = nome sorgente`). La voce §1 «tipo documento
> `ORDINE_CLIENTE` configurato» era **stale**: la verifica ha trovato
> `documenti.tipi_documento_output` con solo PREVENTIVO/CONTRATTO/OFFERTA_COMMERCIALE
> (nessuna riga ordine). Il team DB ha **seedato** `ORDINE_VENDITA` (id=4) →
> §12.1. Resta il **template + versione PUBBLICATA** con l'HTML del layout, che
> per scelta Tid si crea **manualmente** (non via seed Liquibase, come per gli
> altri tre domini): senza versione PUBBLICATA la generazione fallisce
> (`documenti-e-stampe.md` §2.3).

### 12.1 Workstream DB — ✅ EVASO (team DB, 2026-06-04, brief dedicato)

> **Brief DB**: «Brief DB — Stampa documento ordine (PDF)» (team DB, `dev/db-tid`).
> Esito: il workstream DB si riduce a **un solo seed di lookup** (il tipo
> documento), **già fatto e pgTAP verde**; i template sono gestione manuale.

Decisioni team DB (ratificate Tid 2026-06-04):

1. **Tipo documento → seedato.** Riga `ORDINE_VENDITA` (id=4) aggiunta a
   `documenti.tipi_documento_output` (`codice=codice_interno=ORDINE_VENDITA`,
   attivo). Era **assente** (il CSV aveva solo PREVENTIVO/CONTRATTO/OFFERTA). Seed
   via il changeset base `20260429-58-upsert-documenti-seed-base` (`runOnChange`+
   `loadUpdateData` upsert per `id`, progettato per la crescita del lookup). pgTAP
   `test-documenti-tipo-ordine-vendita.sql` verde (presenza+attivo+sorgente+no
   duplicati). **EVASO**, resta solo commit/PR su `dev/db-tid`.
2. **Sorgente → riuso.** `config.sorgenti` `codice='ORDINE_VENDITA'` (id=6) già
   presente e attiva (push/canali) → nessuna nuova riga.
3. **Template + versione PUBBLICATA → gestione MANUALE** ✅ **FATTO 2026-06-04**: si
   creano a mano (`documenti.template_documenti` + `template_documenti_versioni`,
   `context_builder_code='ORDINE_VENDITA'`, `is_default=true` per
   `(ORDINE_VENDITA, sorgente, emittente)`), **non** via seed Liquibase — come già
   fatto per preventivo/offerta/contratto. HTML conferma d'ordine: clone layout
   preventivo/offerta, adattato (niente revisioni, niente listino testata,
   **+`fatturazione_trigger`**, eventuali chip `documento_origine`/`agente`).
   `BOZZA` → `PUBBLICATA` via `fn_pubblica_template_documento_versione`. → **fuori
   dal workstream DB seed**, è un passo di configurazione operativa.
4. **Asset** — riuso degli asset emittente già caricati (logo/carta intestata/
   firma): nessun nuovo asset se il layout usa i codici stabili esistenti.

> **Nota**: tutto §12.1 è **configurazione/seed dati**, non modello (le tabelle
> `documenti.*` esistono e sono collaudate da preventivi/offerte/contratti). È
> indipendente dall'estensione modello A+E (§3.0). **Prerequisito BE/FE
> soddisfatto** dal seed del tipo documento; la creazione del template manuale può
> avvenire in parallelo allo sviluppo BE/FE (serve per il primo render reale).

### 12.2 Workstream Backend (`apps/vendite/` + `apps/documenti/`) — attende DB

Clone 1:1 della catena preventivi
([preventivi_documenti_views.py](../../../../backend/apps/vendite/api/preventivi_documenti_views.py),
[preventivo_document_context_builder.py](../../../../backend/apps/vendite/services/preventivo_document_context_builder.py)).
Nessuna logica nuova nel servizio centrale
[document_generation_service.py](../../../../backend/apps/documenti/services/document_generation_service.py):
ordini si limita a fornire **builder + view + route + repo-getters**.

1. **Context builder (NUOVO)** —
   `apps/vendite/services/ordine_document_context_builder.py`, clone di
   `preventivo_document_context_builder.py`:
   - `class OrdineDocumentContextBuilder(DocumentContextBuilder)` con
     `CODE = "ORDINE_VENDITA"` (= `context_builder_code` del template, §12.0).
   - `build_context(sorgente_id, *, auth_user_id=None, locale="it-IT")` legge da
     `ordini_repository` testata + righe + riepilogo IVA + indirizzi e restituisce
     il dict `{ordine, cliente, righe, riepilogo_iva, indirizzi, _meta}`. Il
     template **non interroga mai il DB** (`documenti-e-stampe.md` §3) — il builder
     è single source del contesto.
   - **Registrazione** in
     [apps/vendite/apps.py](../../../../backend/apps/vendite/apps.py) `ready()`:
     aggiungere l'import `ordine_document_context_builder` accanto agli altri 3
     (side-effect `register_builder()`).
2. **Repo getters** — assicurare in `ordini_repository.py` i metodi che il builder
   consuma (clone preventivi): `get_for_documento_generation(ordine_id)` (ritorna
   `id`/`uid`/`emittente_fiscale_id`/`stato` — usato da
   `resolve_contesto_documentale`), `get_ordine`, `list_righe`, `list_indirizzi`,
   `list_riepilogo_iva`. Molti esistono già dallo scheletro CRUD (§5.1) → aggiungere
   solo i mancanti.
3. **View documenti (NUOVO)** — `apps/vendite/api/ordini_documenti_views.py`, clone
   di `preventivi_documenti_views.py`. Classi `DomainAPIView`
   (`area_funzionale='vendite'`), `_CODICE_SORGENTE_ORDINE = "ORDINE_VENDITA"`,
   helper `_resolve_contesto_ordine(ordine_id)` →
   `resolve_contesto_documentale(...)`:
   - `ApiOrdineDocumentoGenera` — `POST .../documenti/genera/` (genera + persiste).
   - `ApiOrdineDocumentoAnteprima` — `POST .../documenti/anteprima/` (render senza
     persist; tipicamente in BOZZA).
   - `ApiOrdineDocumentiList` — `GET .../documenti/` (lista paginata generati per
     sorgente).
   - `ApiOrdineDocumentoFile` — `GET .../documenti/{documento_id}/file/`
     (download PDF + evento `SCARICATO`).
   - `ApiOrdineDocumentoAllegati` — `GET/POST .../documenti/{documento_id}/allegati/`
     (lista/append allegati — opzionale per lo scheletro stampa).
   - *(Eventuale)* `ApiOrdineEmetti` — `POST .../emetti/` se si vuole la transizione
     di stato atomica + generazione, come preventivi/offerte. **Per la sola stampa
     può bastare `genera` on-demand** senza nuova transizione di stato (l'ordine ha
     già `numero` in BOZZA, §8.1). Decisione di processo §12.4.
4. **Route** — in
   [urls_ordini.py](../../../../backend/apps/vendite/api/urls_ordini.py) aggiungere
   le 5 path `documenti/...` (clone di
   [preventivi_urls.py](../../../../backend/apps/vendite/api/preventivi_urls.py)
   §172-200), nomi route `vendite-ordini-documenti-*`.
5. **Test BE** — `tests/api/test_ordini_documenti.py` (clone preventivi):
   genera (template default risolto, context builder invocato, record
   `documenti_generati` + file), anteprima (no persist), list, download (evento
   SCARICATO), guardia sorgente non attiva / emittente mancante. Mock DB (CI
   AGENTS.md). Verde `./manage-test.sh apps.vendite.tests` + `apps.documenti.tests`.

### 12.3 Workstream Frontend (`src/vendite/ordini/` + `src/documenti/`) — attende BE

Riuso **totale** dei BB documenti già estratti (regola del 2): **nessun nuovo
componente di stampa**. Si registra solo il nuovo sorgente.

1. **Costante sorgente** — in
   [src/documenti/constants.js](../../../../frontend/src/documenti/constants.js)
   aggiungere `SORGENTE_CODES.ORDINE_VENDITA = 'ORDINE_VENDITA'` (= codice DB/BE).
2. **Client API sorgente** — in
   [src/documenti/api/documentiPerSorgente.js](../../../../frontend/src/documenti/api/documentiPerSorgente.js)
   aggiungere il client `ordineDocumenti = buildSorgenteClient((id) =>
   `/vendite/ordini/${id}/documenti`)` e registrarlo nella
   `SORGENTE_CLIENT_MAP` accanto a preventivo/offerta/contratto. Download/anteprima
   già `responseType:'blob'` nel factory (memoria
   `feedback_blob_download_no_useapihandler` — il blob NON passa da
   `useApiHandler`). Lo store
   [stores/documentiPerSorgente.js](../../../../frontend/src/documenti/stores/documentiPerSorgente.js)
   è generico: nessuna modifica oltre la entry in mappa.
3. **Wiring drawer** — in
   [OrdiniDrawer.vue](../../../../frontend/src/vendite/ordini/components/OrdiniDrawer.vue)
   (header) montare
   [`EntityPdfButton`](../../../../frontend/src/documenti/components/EntityPdfButton.vue),
   gemello di `PreventiviDrawer`/`OffertaDrawer`:

   ```vue
   <EntityPdfButton
     :sorgente-code="SORGENTE_CODES.ORDINE_VENDITA"
     :entity-id="effectiveOrdineId"
     :stato-codice="detail.stato_codice_interno"
     :stati-preview="STATI_ORDINE_ANTEPRIMA_PDF"
     :stati-con-documento="STATI_ORDINE_CON_DOCUMENTO"
     i18n-prefix="vendite.ordini.pdf"
   />
   ```

   Il bottone è **state-aware**: in BOZZA → modalità anteprima; in stati
   "con documento" → apre
   [`PdfDocumentiSorgenteDialog`](../../../../frontend/src/documenti/components/PdfDocumentiSorgenteDialog.vue)
   (lista generati + download). Costanti stato in
   `src/vendite/ordini/constants.js` (`STATI_ORDINE_ANTEPRIMA_PDF`,
   `STATI_ORDINE_CON_DOCUMENTO`) — gli stati ammessi li detta il modello stati
   ordine, **data-driven**, non hardcodati a casaccio (memoria
   `feedback_no_hardcoded_ids`).
4. **Wiring lista (azione di riga)** — opzionale ma coerente con la famiglia: voce
   `RowActionsMenu` (memoria `feedback_row_actions_menu`) «Stampa/Documenti» che
   apre lo stesso `PdfDocumentiSorgenteDialog` per la riga, disabilitata in BOZZA
   via `stato_codice_interno` (la colonna tecnica è già nel catalogo §4). Rimuove la
   limitazione registrata in §6.ter punto 2.
5. **i18n** — chiavi `vendite.ordini.pdf.*` (label/tooltip anteprima/scarica) in
   `it`/`en`; verifica assenza orfane. `@` letterale → `{'@'}` (memoria
   `feedback_vue_i18n_linked_escape`).
6. **Build FE verde** — `./node_modules/.bin/vite build`.

### 12.4 Decisione di processo — ✅ CHIUSA: adottata (a) anteprima on-demand

- **`genera` on-demand vs `emetti` con transizione di stato.** Preventivi/offerte
  legano la prima generazione a una transizione (BOZZA→EMESSO/A) atomica
  (render+stato+allegati). L'ordine ha già `numero` in BOZZA (§8.1) e la sua
  transizione chiave è **CONFERMA** (§7.1, che governa il push commessa). Due
  strade:
  - **(a)** Stampa **disaccoppiata** dallo stato: `genera`/`anteprima` on-demand a
    qualsiasi stato consultabile, senza nuova transizione. Più semplice, allineato
    al fatto che la conferma d'ordine è già un PDF ristampabile.
  - **(b)** Generazione **agganciata alla CONFERMA** (`POST .../conferma/` produce
    anche il PDF conferma d'ordine in transazione atomica, stile `emetti`).
  → **Adottata (a)** (2026-06-04). Implementazione: `EntityPdfButton` nel drawer
  usa **solo** l'anteprima on-demand (`STATI_ORDINE_ANTEPRIMA_PDF` = tutti gli
  stati consultabili; `STATI_ORDINE_CON_DOCUMENTO` = `[]`). Il BB non ha un
  trigger `genera`: usare la modalità "scarica dall'archivio" senza un punto di
  persistenza darebbe un dialog vuoto → si parte anteprima-only. Gli endpoint BE
  `genera`/lista/download/allegati **esistono già** (pronti per l'archivio): quando
  servirà l'aggancio (b) (conferma = atto formale che archivia il PDF), basta
  abilitare gli stati `con-documento` + un trigger di generazione. La (a) non
  preclude la (b) (`feedback_no_quick_fix_soluzione_assoluta`).

### 12.5 Sintesi effort

| Layer | Cosa | Clone da | Effort | Stato |
| --- | --- | --- | --- | --- |
| DB | seed tipo documento `ORDINE_VENDITA` + pgTAP | seed-base documenti | banale | ✅ **fatto** (applicato al DB di lavoro 2026-06-04; commit/PR su `dev/db-tid`) |
| DB/config | template + versione PUBBLICATA (HTML) — **manuale** | template preventivo/offerta | **medio** (layout HTML) | ✅ **fatto 2026-06-04** |
| BE | context builder + registrazione `ready()` | `preventivo_document_context_builder.py` | basso | ✅ **fatto** (`ordine_document_context_builder.py`, CODE=ORDINE_VENDITA) |
| BE | view documenti (4 classi) + route | `preventivi_documenti_views.py` / `preventivi_urls.py` | basso | ✅ **fatto** (`ordini_documenti_views.py`; no `emetti`, §12.4a) |
| BE | repo getter `get_for_documento_generation` | `preventivi_repository.py` | basso | ✅ **fatto** |
| BE | test documenti ordine | `test` preventivi documenti | basso | ✅ **fatto** (`test_ordine_document_context_builder.py` 5/5; suite ordini 17/17 + api 9/9) |
| FE | costante + client API + entry mappa | `documentiPerSorgente.js` | banale | ✅ **fatto** (`ordineDocumenti` + `SORGENTE_CODES.ORDINE_VENDITA`) |
| FE | `EntityPdfButton` nel drawer | `PreventiviDrawer.vue` | basso | ✅ **fatto** (drawer; azione lista omessa, opzionale) |
| FE | i18n `vendite.ordini.pdf.*` + context_builder | preventivi | banale | ✅ **fatto** (it/en; `ORDINE` placeholder → `ORDINE_VENDITA` registered) |

> **Stampa COMPLETA end-to-end 2026-06-04** (anteprima on-demand, §12.4a): BE+FE
> con **template HTML/versione PUBBLICATA creati** (§12.1.3). Build FE verde. Tutto
> cablaggio del doc-type «ordine» sull'infrastruttura documenti esistente. Stampa
> = **quarto giro** sullo stesso BB, **zero infrastruttura nuova**.
