# WIP — Gestione Articoli e Listini: Backend + Frontend

> Stato: DA IMPLEMENTARE
>
> Data: aprile 2026
>
> Prerequisiti DB:
>
> * Schema `catalogo` operativo: articoli, articoli_componenti, articoli_uom_operativa, unita_misura, unita_misura_conversioni, note (partitioned)
> * Schema `vendite` operativo per listini: listini, listini_versioni, listini_righe, listini_associazioni
> * Funzioni DB operative: `fn_get_uom_base`, `fn_get_uom_factor`, `fn_resolve_prezzo_listino`, `fn_resolve_commessa_prezzi`
> * Viste DB operative: `vw_articoli_dettaglio`, `vw_articoli_componenti_dettaglio`, `vw_articoli_note`, `vw_articoli_componenti_note`
>
> Riferimenti:
>
> * [gestione-listini.md](gestione-listini.md) — decisioni architetturali pricing, resolver, rettifiche
> * [docs/it/dbzero/catalogo/](../../dbzero/catalogo/) — documentazione schema catalogo
> * [docs/it/dbzero/vendite/tabelle/listini.md](../../dbzero/vendite/tabelle/listini.md) — schema listini
> * [docs/it/dev/api.md](../api.md) — linee guida API

---

## Contesto

Lo schema DB `catalogo` e' maturo: 6 tabelle core, 4 funzioni, 4 viste, 40+ trigger di integrita'. Lo schema `vendite` per i listini e' completo fino a DB-L3 (resolver + integrazione commessa). Manca interamente il layer backend (API REST) e frontend per entrambi i domini.

Questo documento copre **solo articoli e listini**. Le commesse e le rettifiche prezzi (DB-L4) restano fuori scope.

Il contenuto seguente va letto in due modi distinti:

1. come **specifica target** del risultato finale (repository, service, API, frontend)
2. come **backlog da eseguire in ordine concentrico**, privilegiando prima i contratti minimi di `catalogo`, poi le estensioni, infine `listini`

---

## 1. Perimetro funzionale

### 1.1 Articoli (catalogo)

1. CRUD articoli con filtri, ricerca, paginazione
2. Gestione UoM operative per articolo (assegnazione, conversione, flag vendita/acquisto/logistica)
3. Gestione distinta base (BoM) con versionamento temporale
4. Note articolo e note componenti
5. Lookup articoli per autocomplete (uso cross-dominio: ordini, preventivi, listini)
6. Lookup UoM per autocomplete

### 1.2 Listini (vendite)

1. CRUD listini (anagrafica: codice, descrizione, dominio UTILITY/COMMERCIO)
2. Gestione versioni listino (ciclo di vita BOZZA → ATTIVA → CHIUSA, date validita')
3. Gestione righe prezzo per versione (dimensioni: articolo + UoM + contesto opzionale)
4. Gestione associazioni listino a perimetri (BA/utility/emittente con priorita')
5. Test resolver prezzo da UI (verifica prezzo risolto per combinazione dimensionale)

### 1.3 Fuori scope

1. Commesse e integrazione pricing commessa (DB-L3 gia' fatto, backend/frontend separato)
2. Rettifiche prezzi manuali/automatiche (DB-L4 non ancora implementato)
3. Formula engine e scaglioni (v2 pricing)
4. Import/export massivo articoli o listini

---

## 2. Decisioni architetturali

### 2.1 Separazione app Django

1. Articoli, UoM, BoM e note → `apps/catalogo/` (schema `catalogo`)
2. Listini, versioni, righe, associazioni → `apps/vendite/` (schema `vendite`, file dedicati `listini_*`)

Motivazione: rispetta l'allineamento app-schema gia' stabilito. I listini vivono in `vendite` perche' il resolver prezzo e' integrato con il ciclo vendita.

### 2.2 Repository pattern

1. `catalogo_repository.py` — CRUD articoli, list, search, lookup, decodifiche
2. `catalogo_uom_repository.py` — UoM operative, conversioni, lookup UoM
3. `catalogo_bom_repository.py` — BoM (componenti), versionamento temporale, note componenti
4. `listini_repository.py` (in `apps/vendite/db/`) — CRUD listini, versioni, righe, associazioni, test resolver

Motivazione: segue la regola di naming per sottodominio specializzato (AGENTS.md §Naming convention). La BoM ha logica autonoma (overlap temporale, guard composito/solo-componente) che giustifica il file separato.

### 2.3 Service pattern

1. `catalogo_service.py` — orchestrazione CRUD articoli, validazioni cross-entita'
2. `listini_service.py` (in `apps/vendite/services/`) — orchestrazione listini, validazione ciclo versioni, test resolver

### 2.4 Viste DB come sorgente per le liste

1. Le API lista usano le viste `vw_articoli_dettaglio` e `vw_articoli_componenti_dettaglio` per evitare JOIN nel codice Python
2. Le API lista listini usano JOIN diretti (4 tabelle con relazione gerarchica semplice)

### 2.5 Lookup articoli cross-dominio

1. Endpoint lookup dedicato `/api/v1/catalogo/articoli/lookup/` con search su codice + descrizione
2. Restituisce: `id, codice, descrizione, uom_codice, uom_descrizione, is_composito, voce_utility, attivo`
3. Filtri opzionali: `voce_utility=true/false`, `attivo=true`, `is_composito=true/false`
4. Usato da: drawer righe ordine, drawer righe preventivo, drawer righe listino

### 2.6 Sequenza esecutiva ottimizzata

L'implementazione **non** va affrontata come costruzione parallela di tutti i blocchi. In coerenza con `sviluppo-concentrico.md` e `mappa-concentrica.md`, l'ordine corretto e':

1. partire da `catalogo` backend, perche' e' Anello 1 e fornisce lookup e contratti riusabili agli anelli esterni
2. stabilizzare i contratti API minimi prima del frontend
3. chiudere il frontend `catalogo` solo dopo avere backend e naming consolidati
4. passare a `vendite/listini` solo quando articoli e UoM sono gia' consumabili

### 2.7 Fasi operative

#### Fase 1 — Catalogo backend minimo (contratti base)

Obiettivo: sbloccare i consumatori cross-dominio e fissare i contratti API di base.

Da implementare per primi:

- [x] `apps/catalogo/db/catalogo_repository.py`
- [x] `apps/catalogo/services/catalogo_service.py`
- [x] `apps/catalogo/api/views.py`
- [x] `apps/catalogo/api/urls.py`

Endpoint inclusi:

- [x] `GET /api/v1/catalogo/articoli/`
- [x] `GET /api/v1/catalogo/articoli/{id}/`
- [x] `GET /api/v1/catalogo/articoli/lookup/`
- [x] lookup UoM via endpoint generico `GET /api/v1/core/lookup/codici/?rel=catalogo.unita_misura` (gia' in whitelist)

Note operative:

1. usare solo building block core gia' esistenti (`DomainAPIView`, `parse_list_params`, `qp_*`, `validate_order_params`, `success_response`, `paginated_envelope`)
2. partire da lista, dettaglio e lookup prima del CRUD completo
3. i test Django devono essere unitari con mock accesso DB, compatibili CI

#### Fase 2 — Catalogo backend CRUD articolo

Obiettivo: rendere gestibile l'entita' principale senza introdurre ancora sottodomini secondari.

Endpoint inclusi:

- [x] `POST /api/v1/catalogo/articoli/`
- [x] `PATCH /api/v1/catalogo/articoli/{id}/`
- [x] `POST /api/v1/catalogo/articoli/{id}/disattiva/`

Note operative:

1. mantenere `codice` immutabile e lasciare i guard critici al DB
2. tradurre gli errori applicativi tramite `ErrorManager` e policy core, senza logica duplicata nelle view

#### Fase 3 — Catalogo backend esteso (UoM, BoM, note)

Obiettivo: completare il dettaglio articolo e chiudere il perimetro di Anello 1.

Da introdurre in questa fase:

- [x] `apps/catalogo/db/catalogo_uom_repository.py`
- [x] `apps/catalogo/db/catalogo_bom_repository.py`
- [x] metodi aggiuntivi in `catalogo_service.py`
- [x] endpoint UoM, componenti e note

Note operative:

1. la separazione in repository specializzati resta valida e va mantenuta
2. questa fase viene dopo il CRUD base per evitare di aprire troppi fronti contemporaneamente

#### Fase 4 — Frontend catalogo

Obiettivo: costruire la UI su contratti backend gia' stabili.

Da implementare:

- [x] API client `frontend/src/catalogo/api/catalogo.js` (20 funzioni)
- [x] store Pinia `frontend/src/catalogo/stores/articoli.js`
- [x] store Pinia `frontend/src/catalogo/stores/unitaMisura.js`
- [x] lista articoli (`ArticoliSearchTable.vue`) con 7 filtri + empty state
- [x] drawer articolo (`ArticoloDrawer.vue`) con 3 tab in edit
- [x] tab secondarie (`ArticoloUomTab.vue`, `ArticoloBomTab.vue`, `ArticoloNoteTab.vue`)
- [x] `ArticoloLookup.vue` in `core/components/` (building block cross-dominio)
- [x] CRUD unita' di misura (`UnitaMisuraSearchTable.vue`, `UnitaMisuraDrawer.vue`, `UnitaMisuraView.vue`)
- [x] backend UoM CRUD (5 metodi repository + 5 funzioni service + 3 view + 3 rotte)
- [x] `navigation.js`: 2 voci L2 catalogo (Articoli, Unita' di Misura)
- [x] `router/index.js`: 2 rotte (`catalogo-articoli`, `catalogo-unita-misura`)
- [x] i18n `locales/it.json`: sezione `catalogo` (76 chiavi) + `nav_menu.catalogo` + `common.all/active/inactive`
- [x] lookup UoM via `lookupCodici('catalogo.unita_misura')` (gia' in whitelist, rimosso endpoint dedicato)

Regole seguite:

1. riusato `useSearchTable`, `useDrawerState`, `useTabFreshness`, `NewButton`, `DrawerFooter`, `SearchHint`
2. `ArticoloBomTab` usa `ArticoloLookup` (BB cross-dominio) invece di autocomplete raw
3. UoM lista carica subito (tabella piccola), articoli con empty state
4. PATCH usa `request.data` (non `handle_post_json`)
5. tutti i testi via `$t()`, nessun hardcoded

#### Fase 5 — Backend listini

Obiettivo: costruire `vendite/listini` sopra lookup articoli e UoM gia' disponibili.

Da implementare:

- [x] `apps/vendite/db/listini_repository.py` (19 metodi: listini CRUD, versioni CRUD+stato+count righe, righe CRUD, associazioni CRUD, validazione articolo/UoM, test resolver)
- [x] `apps/vendite/services/listini_service.py` (18 funzioni fn_*: listini, versioni, righe, associazioni, cambio stato, test resolver)
- [x] `apps/vendite/api/views_listini.py` (10 classi view, 18 metodi HTTP)
- [x] `apps/vendite/api/urls_listini.py` (10 rotte, incluso sotto `api/v1/vendite/listini/`)
- [x] lista + dettaglio listini (con count versioni e associazioni)
- [x] CRUD anagrafica listino
- [x] versioni (CRUD + cambio stato BOZZA→ATTIVA→CHIUSA con guard almeno 1 riga)
- [x] righe prezzo (CRUD con display fields articolo/UoM/BA/utility/emittente via JOIN)
- [x] associazioni (CRUD con display fields BA/utility/emittente via JOIN)
- [x] test resolver prezzo (wrapper `fn_resolve_prezzo_listino` con arricchimento codici)
- [x] codici errore in `error_policies.py` (E_VENDITE_VALIDATION, _LISTINO_NOT_FOUND, _VERSIONE_NOT_FOUND, _RIGA_NOT_FOUND, _ASSOCIAZIONE_NOT_FOUND)
- [x] PATCH usa `request.data` (non `handle_post_json`)
- [x] test service (8 test) + test API (21 test) = 29 test verdi

Note operative seguite:

1. `DomainAPIView` con `area_funzionale = "vendite"` su tutte le 10 view
2. `is_search_endpoint = True` sulla lista
3. `@extend_schema` su tutti i 18 metodi HTTP
4. helper condivisi `_prepare_insert_parts` e `_prepare_update_parts` nel repository (riduce duplicazione)
5. validazione articolo/UoM in un solo round-trip (`get_articolo_uom_validation`)
6. display fields via JOIN diretti (non lookup client-side)

#### Fase 6 — Frontend listini

Obiettivo: chiudere il dominio di Anello 3 sfruttando building block e lookup gia' operativi.

Da implementare:

- [x] API client `vendite/api/listini.js` (17 funzioni)
- [x] store Pinia `vendite/stores/listini.js`
- [x] `ListiniSearchTable.vue` (filtri dominio + attivo, empty state)
- [x] `ListinoDrawer.vue` (COMPLEX 800px, 2 tab + pulsante test resolver)
- [x] `ListinoVersioniTab.vue` (lista versioni, creazione inline, azioni stato, click apre VersioneDrawer)
- [x] `ListinoAssociazioniTab.vue` (CRUD inline con display fields)
- [x] `VersioneDrawer.vue` (sub-drawer dettaglio versione + righe prezzo con CRUD inline, guard BOZZA)
- [x] `TestResolverDialog.vue` (dialog modale con `ArticoloLookup` BB, output match level)
- [x] `ListiniView.vue`
- [x] `navigation.js`: voce L2 vendite (Listini)
- [x] `router/index.js`: rotta `vendite-listini`, `vendite` in `domainsWithRoutes`
- [x] i18n `listini` (62 chiavi) + `nav_menu.vendite`
- [x] build frontend OK, 78 test backend verdi, nessun testo hardcoded

Regole seguite:

1. riusato `useSearchTable`, `useDrawerState`, `useTabFreshness`, `useApiHandler`, `useInjectReadonly`, `useLookup`
2. `VersioneDrawer` e `TestResolverDialog` usano `ArticoloLookup` BB cross-dominio
3. lookup UoM via `lookupCodici('catalogo.unita_misura')` (generico, non dedicato)
4. righe prezzo CRUD solo su versioni in stato BOZZA (guard `isBozza`)
5. PATCH backend usa `request.data`
6. tutti i testi via `$t()`, nessun hardcoded

#### Fase 7 — Consolidamento e test di flusso

Obiettivo: verificare coerenza tra anelli, non solo correttezza locale.

Checklist finale:

- [ ] test unitari backend per repository/service/view con mock
- [ ] verifica envelope API, naming campi e ordinamenti whitelist
- [ ] verifica lookup articoli riusabile da frontend `catalogo` e `vendite`
- [ ] verifica permessi, readonly mode e pattern tab/drawer
- [ ] aggiornamento documentazione tecnica se durante l'implementazione emergono contratti diversi dal piano

---

## 3. Backend — Catalogo (articoli)

### 3.1 Repository: `apps/catalogo/db/catalogo_repository.py`

| # | Metodo | SQL | Note |
| --- | --- | --- | --- |
| 3.1.1 | `list_articoli()` | SELECT da `vw_articoli_dettaglio` con filtri, search ILIKE, paginazione, order_by | Filtri: `attivo`, `is_composito`, `voce_utility`, `tipo_voce_id`, `gruppo_voce_id`, `search`, `data_da/data_a` |
| 3.1.2 | `get_articolo()` | SELECT da `vw_articoli_dettaglio` WHERE id | Singolo articolo con dati arricchiti |
| 3.1.3 | `create_articolo()` | INSERT INTO `catalogo.articoli` | Campi: codice, descrizione, descrizione_breve, uom_id, tipo_voce_id, gruppo_voce_id, spesa_id, iva_id, conti contabili, is_composito, voce_utility, requires_serial |
| 3.1.4 | `update_articolo()` | UPDATE `catalogo.articoli` SET ... WHERE id | Codice immutabile (trigger DB). Tutti gli altri campi editabili |
| 3.1.5 | `deactivate_articolo()` | UPDATE `catalogo.articoli` SET attivo=false WHERE id | Il trigger DB blocca se ci sono figli attivi (27 guard) |
| 3.1.6 | `lookup_articoli()` | SELECT id, codice, descrizione, uom da `vw_articoli_dettaglio` con search | Per autocomplete cross-dominio. Limit 50, filtri opzionali |
| 3.1.7 | `count_articoli()` | COUNT da `vw_articoli_dettaglio` con stessi filtri di list | Per paginazione |

### 3.2 Repository: `apps/catalogo/db/catalogo_uom_repository.py`

| # | Metodo | SQL | Note |
| --- | --- | --- | --- |
| 3.2.1 | `list_uom_operative()` | SELECT da `catalogo.articoli_uom_operativa` JOIN `unita_misura` WHERE articolo_id | UoM assegnate a un articolo con dettagli |
| 3.2.2 | `create_uom_operativa()` | INSERT INTO `catalogo.articoli_uom_operativa` | Constraint UNIQUE(articolo_id, uom_id) gestito da DB |
| 3.2.3 | `update_uom_operativa()` | UPDATE `catalogo.articoli_uom_operativa` SET ... WHERE id | Flag, factor_to_base, arrotondamento |
| 3.2.4 | `delete_uom_operativa()` | DELETE FROM `catalogo.articoli_uom_operativa` WHERE id | Guard DB se in uso |
| 3.2.5 | `lookup_unita_misura()` | SELECT id, codice, descrizione FROM `catalogo.unita_misura` WHERE attivo=true | Per dropdown/autocomplete |
| 3.2.6 | `get_uom_base()` | SELECT `catalogo.fn_get_uom_base(p_articolo_id)` | Wrapper funzione DB |
| 3.2.7 | `get_uom_factor()` | SELECT `catalogo.fn_get_uom_factor(p_articolo_id, p_uom_id)` | Wrapper funzione DB |

### 3.3 Repository: `apps/catalogo/db/catalogo_bom_repository.py`

| # | Metodo | SQL | Note |
| --- | --- | --- | --- |
| 3.3.1 | `list_componenti()` | SELECT da `vw_articoli_componenti_dettaglio` WHERE prodotto_id | BoM di un articolo con dettagli componente |
| 3.3.2 | `create_componente()` | INSERT INTO `catalogo.articoli_componenti` | Guard DB: prodotto must be is_composito, not is_solo_componente |
| 3.3.3 | `update_componente()` | UPDATE `catalogo.articoli_componenti` SET ... WHERE id | coeff_qta, flag, date validita' |
| 3.3.4 | `delete_componente()` | DELETE FROM `catalogo.articoli_componenti` WHERE id | Guard DB su note figlie |
| 3.3.5 | `list_note_articolo()` | SELECT da `vw_articoli_note` WHERE target_id | Note articolo |
| 3.3.6 | `create_nota_articolo()` | INSERT INTO `catalogo.note` con target_tipo='ARTICOLI' | |
| 3.3.7 | `update_nota()` | UPDATE `catalogo.note` SET ... WHERE id | |
| 3.3.8 | `delete_nota()` | DELETE FROM `catalogo.note` WHERE id | |

### 3.4 Service: `apps/catalogo/services/catalogo_service.py`

| # | Metodo | Orchestrazione |
| --- | --- | --- |
| 3.4.1 | `list_articoli()` | Delega a repository con validazione filtri |
| 3.4.2 | `get_articolo()` | Dettaglio + UoM operative + componenti (se composito) + note |
| 3.4.3 | `crea_articolo()` | Validazione input, INSERT, risposta con dati arricchiti |
| 3.4.4 | `aggiorna_articolo()` | Validazione input, UPDATE, risposta con dati arricchiti |
| 3.4.5 | `disattiva_articolo()` | Deactivate con gestione errore guard DB (27 FK) |
| 3.4.6 | `gestisci_uom_operativa()` | CRUD UoM operativa per articolo |
| 3.4.7 | `gestisci_componente()` | CRUD componente BoM per articolo |
| 3.4.8 | `gestisci_nota()` | CRUD nota articolo/componente |

### 3.5 API: `apps/catalogo/api/views.py`

| # | Metodo | Path | Scopo |
| --- | --- | --- | --- |
| 3.5.1 | GET | `/api/v1/catalogo/articoli/` | Lista paginata con search e filtri |
| 3.5.2 | POST | `/api/v1/catalogo/articoli/` | Crea articolo |
| 3.5.3 | GET | `/api/v1/catalogo/articoli/{id}/` | Dettaglio con UoM + BoM + note |
| 3.5.4 | PATCH | `/api/v1/catalogo/articoli/{id}/` | Aggiorna articolo |
| 3.5.5 | POST | `/api/v1/catalogo/articoli/{id}/disattiva/` | Disattiva articolo |
| 3.5.6 | GET | `/api/v1/catalogo/articoli/lookup/` | Lookup per autocomplete cross-dominio |
| 3.5.7 | GET | `/api/v1/catalogo/articoli/{id}/uom/` | Lista UoM operative dell'articolo |
| 3.5.8 | POST | `/api/v1/catalogo/articoli/{id}/uom/` | Aggiungi UoM operativa |
| 3.5.9 | PATCH | `/api/v1/catalogo/articoli/{id}/uom/{uom_op_id}/` | Aggiorna UoM operativa |
| 3.5.10 | DELETE | `/api/v1/catalogo/articoli/{id}/uom/{uom_op_id}/` | Rimuovi UoM operativa |
| 3.5.11 | GET | `/api/v1/catalogo/articoli/{id}/componenti/` | Lista BoM dell'articolo |
| 3.5.12 | POST | `/api/v1/catalogo/articoli/{id}/componenti/` | Aggiungi componente BoM |
| 3.5.13 | PATCH | `/api/v1/catalogo/articoli/{id}/componenti/{comp_id}/` | Aggiorna componente |
| 3.5.14 | DELETE | `/api/v1/catalogo/articoli/{id}/componenti/{comp_id}/` | Rimuovi componente |
| 3.5.15 | GET | `/api/v1/catalogo/articoli/{id}/note/` | Lista note articolo |
| 3.5.16 | POST | `/api/v1/catalogo/articoli/{id}/note/` | Crea nota articolo |
| 3.5.17 | PATCH | `/api/v1/catalogo/note/{nota_id}/` | Aggiorna nota |
| 3.5.18 | DELETE | `/api/v1/catalogo/note/{nota_id}/` | Elimina nota |
| 3.5.19 | GET | `/api/v1/catalogo/unita-misura/lookup/` | Lookup UoM attive |

### 3.6 URL routing: `apps/catalogo/api/urls.py`

Registrare tutte le rotte in `urls.py` e includerle nel router principale `zeroerp_backend/urls.py` sotto `api/v1/catalogo/`.

---

## 4. Backend — Listini (vendite)

### 4.1 Repository: `apps/vendite/db/listini_repository.py`

| # | Metodo | SQL | Note |
| --- | --- | --- | --- |
| 4.1.1 | `list_listini()` | SELECT da `vendite.listini` con filtri, search, paginazione | Filtri: `dominio`, `attivo`, `search` su codice+descrizione |
| 4.1.2 | `get_listino()` | SELECT listino + count versioni + count associazioni | Dettaglio singolo |
| 4.1.3 | `create_listino()` | INSERT INTO `vendite.listini` | codice, descrizione, dominio |
| 4.1.4 | `update_listino()` | UPDATE `vendite.listini` SET ... WHERE id | descrizione, dominio, attivo |
| 4.1.5 | `list_versioni()` | SELECT da `vendite.listini_versioni` WHERE listino_id ORDER BY valido_dal DESC | Con conteggio righe per versione |
| 4.1.6 | `get_versione()` | SELECT singola versione | |
| 4.1.7 | `create_versione()` | INSERT INTO `vendite.listini_versioni` | valido_dal, valido_al, priorita, stato=BOZZA. No-overlap gestito da constraint GIST |
| 4.1.8 | `update_versione()` | UPDATE `vendite.listini_versioni` SET ... WHERE id | Date, priorita'. Stato gestito da azione dedicata |
| 4.1.9 | `cambia_stato_versione()` | UPDATE `vendite.listini_versioni` SET stato WHERE id | Transizioni ammesse: BOZZA→ATTIVA, ATTIVA→CHIUSA |
| 4.1.10 | `list_righe()` | SELECT da `vendite.listini_righe` JOIN articoli JOIN unita_misura WHERE versione_id | Con display fields articolo e UoM |
| 4.1.11 | `create_riga()` | INSERT INTO `vendite.listini_righe` | articolo_id, uom_id, prezzo, contesto opzionale (BA, utility, emittente) |
| 4.1.12 | `update_riga()` | UPDATE `vendite.listini_righe` SET ... WHERE id | prezzo, contesto |
| 4.1.13 | `delete_riga()` | DELETE FROM `vendite.listini_righe` WHERE id | |
| 4.1.14 | `list_associazioni()` | SELECT da `vendite.listini_associazioni` WHERE listino_id | Con display fields BA, utility, emittente |
| 4.1.15 | `create_associazione()` | INSERT INTO `vendite.listini_associazioni` | perimetro (BA, utility, emittente), priorita' |
| 4.1.16 | `update_associazione()` | UPDATE `vendite.listini_associazioni` SET ... WHERE id | |
| 4.1.17 | `delete_associazione()` | DELETE FROM `vendite.listini_associazioni` WHERE id | |
| 4.1.18 | `test_resolver()` | SELECT `vendite.fn_resolve_prezzo_listino(...)` | Wrapper per test prezzo da UI. Restituisce prezzo, match_level, listino/versione usati |

### 4.2 Service: `apps/vendite/services/listini_service.py`

| # | Metodo | Orchestrazione |
| --- | --- | --- |
| 4.2.1 | `list_listini()` | Delega con validazione filtri |
| 4.2.2 | `get_listino_dettaglio()` | Listino + versioni + associazioni |
| 4.2.3 | `crea_listino()` | Validazione codice univoco, INSERT |
| 4.2.4 | `aggiorna_listino()` | UPDATE con validazione |
| 4.2.5 | `gestisci_versione()` | CRUD versione con validazione no-overlap |
| 4.2.6 | `cambia_stato_versione()` | Transizione stato con guard: BOZZA→ATTIVA (deve avere almeno 1 riga), ATTIVA→CHIUSA |
| 4.2.7 | `gestisci_riga()` | CRUD riga con validazione articolo attivo e UoM coerente |
| 4.2.8 | `gestisci_associazione()` | CRUD associazione con validazione perimetro |
| 4.2.9 | `test_resolver_prezzo()` | Chiama `fn_resolve_prezzo_listino`, formatta risultato per UI |

### 4.3 API: `apps/vendite/api/views_listini.py`

| # | Metodo | Path | Scopo |
| --- | --- | --- | --- |
| 4.3.1 | GET | `/api/v1/vendite/listini/` | Lista listini paginata |
| 4.3.2 | POST | `/api/v1/vendite/listini/` | Crea listino |
| 4.3.3 | GET | `/api/v1/vendite/listini/{id}/` | Dettaglio listino |
| 4.3.4 | PATCH | `/api/v1/vendite/listini/{id}/` | Aggiorna listino |
| 4.3.5 | GET | `/api/v1/vendite/listini/{id}/versioni/` | Lista versioni del listino |
| 4.3.6 | POST | `/api/v1/vendite/listini/{id}/versioni/` | Crea versione |
| 4.3.7 | GET | `/api/v1/vendite/listini/{id}/versioni/{ver_id}/` | Dettaglio versione |
| 4.3.8 | PATCH | `/api/v1/vendite/listini/{id}/versioni/{ver_id}/` | Aggiorna versione |
| 4.3.9 | POST | `/api/v1/vendite/listini/{id}/versioni/{ver_id}/stato/` | Cambia stato versione |
| 4.3.10 | GET | `/api/v1/vendite/listini/{id}/versioni/{ver_id}/righe/` | Lista righe prezzo della versione |
| 4.3.11 | POST | `/api/v1/vendite/listini/{id}/versioni/{ver_id}/righe/` | Crea riga prezzo |
| 4.3.12 | PATCH | `/api/v1/vendite/listini/{id}/versioni/{ver_id}/righe/{riga_id}/` | Aggiorna riga |
| 4.3.13 | DELETE | `/api/v1/vendite/listini/{id}/versioni/{ver_id}/righe/{riga_id}/` | Elimina riga |
| 4.3.14 | GET | `/api/v1/vendite/listini/{id}/associazioni/` | Lista associazioni |
| 4.3.15 | POST | `/api/v1/vendite/listini/{id}/associazioni/` | Crea associazione |
| 4.3.16 | PATCH | `/api/v1/vendite/listini/{id}/associazioni/{assoc_id}/` | Aggiorna associazione |
| 4.3.17 | DELETE | `/api/v1/vendite/listini/{id}/associazioni/{assoc_id}/` | Elimina associazione |
| 4.3.18 | POST | `/api/v1/vendite/listini/test-prezzo/` | Test resolver prezzo |

### 4.4 URL routing

File `apps/vendite/api/urls_listini.py`, incluso da `urls_v1.py` sotto `api/v1/vendite/listini/`.

---

## 5. Frontend — Articoli

### 5.1 Struttura file

```
frontend/src/catalogo/
├── api/
│   └── catalogo.js                  # Funzioni API (list, get, create, update, lookup, uom, bom, note)
├── stores/
│   └── articoli.js                  # Store Pinia: articoli + stato drawer
├── components/
│   ├── ArticoliSearchTable.vue      # Lista articoli con filtri e search
│   ├── ArticoloDrawer.vue           # Drawer crea/modifica articolo (dati principali)
│   ├── ArticoloUomTab.vue           # Tab UoM operative dell'articolo
│   ├── ArticoloBomTab.vue           # Tab distinta base (componenti)
│   ├── ArticoloNoteTab.vue          # Tab note articolo
│   └── ArticoloLookup.vue           # Componente autocomplete riutilizzabile
├── views/
│   └── ArticoliView.vue             # Pagina completa con SearchTable + Drawer
└── composables/
    └── useArticoloForm.js           # Logica form condivisa (validazione, default, submit)
```

### 5.2 ArticoliSearchTable

| Colonna | Sorgente | Note |
| --- | --- | --- |
| Codice | `codice` | Link che apre il drawer |
| Descrizione | `descrizione` | |
| UoM base | `uom_ref_codice` | Da vista `vw_articoli_dettaglio` |
| Tipologia | `tipologia_ref_descrizione` | |
| Gruppo | `gruppo_ref_descrizione` | |
| IVA | `iva_ref_aliquota_iva` | Formattato % |
| Composito | `is_composito` | Badge Si/No |
| Utility | `voce_utility` | Badge Si/No |
| Attivo | `attivo` | Badge stato |

Filtri:

1. `search` — ILIKE su codice + descrizione (trigram)
2. `attivo` — dropdown (Tutti / Si / No), default Si
3. `is_composito` — dropdown (Tutti / Si / No)
4. `voce_utility` — dropdown (Tutti / Si / No)
5. `tipo_voce_id` — lookup da `vendite.articoli_tipologie`
6. `gruppo_voce_id` — lookup da `vendite.articoli_gruppi`

### 5.3 ArticoloDrawer — Dati principali

Form con campi:

| Campo | Tipo | Note |
| --- | --- | --- |
| `codice` | InputText | Obbligatorio, readonly in modifica (lock DB) |
| `descrizione` | InputText | Obbligatorio |
| `descrizione_breve` | InputText | Facoltativo |
| `uom_id` | Select (lookup UoM) | Obbligatorio — UoM base |
| `tipo_voce_id` | Select (lookup tipologie) | Facoltativo |
| `gruppo_voce_id` | Select (lookup gruppi) | Facoltativo |
| `spesa_id` | Select (lookup spesa) | Facoltativo |
| `iva_id` | Select (lookup IVA) | Facoltativo |
| `conto_contabile_vendita_id` | Select (lookup conti) | Facoltativo |
| `conto_contabile_acquisto_id` | Select (lookup conti) | Facoltativo |
| `is_composito` | ToggleSwitch | Default false |
| `is_solo_componente` | ToggleSwitch | Default false. Mutually exclusive con is_composito (se solo_componente, non puo' essere prodotto in BoM) |
| `voce_utility` | ToggleSwitch | Default false |
| `requires_serial` | ToggleSwitch | Default false |

In modalita' modifica: 4 tab sotto il form principale:

1. **UoM operative** (ArticoloUomTab)
2. **Distinta base** (ArticoloBomTab) — visibile solo se `is_composito = true`
3. **Note** (ArticoloNoteTab)
4. **Informazioni** — campi audit (data_insert, user_insert, data_update, user_update)

### 5.4 ArticoloUomTab

DataTable inline con le UoM operative dell'articolo:

| Colonna | Tipo | Note |
| --- | --- | --- |
| UoM | Select (lookup) | `uom_id` |
| Fattore | InputNumber | `factor_to_base` (default 1) |
| Base | Checkbox readonly | `is_base` calcolato |
| Vendita | Checkbox | `is_sell_uom` |
| Acquisto | Checkbox | `is_purchase_uom` |
| Logistica | Checkbox | `is_logistic_uom` |
| Decimali max | InputNumber | `max_decimals` (default 6) |
| Azioni | Bottoni edit/delete | |

Bottone "Aggiungi UoM" in testa.

### 5.5 ArticoloBomTab

DataTable inline con i componenti della distinta base:

| Colonna | Tipo | Note |
| --- | --- | --- |
| Componente | AutoComplete articoli | `componente_id` — filtra `is_solo_componente=false` per evitare self-reference |
| Coefficiente | InputNumber | `coeff_qta` (default 1) |
| Partecipa Qta' | Checkbox | `partecipa_qta` |
| Determina Qta' Padre | Checkbox | `determina_qta_padre` |
| Obbligatorio | Checkbox | `obbligatorio` |
| Valido dal | Calendar | `valido_dal` (obbligatorio) |
| Valido al | Calendar | `valido_al` (facoltativo, open-ended) |
| Azioni | Bottoni edit/delete | |

### 5.6 ArticoloLookup (building block riutilizzabile)

Componente `ArticoloLookup.vue` basato su server-side autocomplete (`useServerAutocomplete`):

- Endpoint: `/api/v1/catalogo/articoli/lookup/`
- Display: `codice — descrizione`
- Props: `voceUtility` (bool, filtro opzionale), `soloAttivi` (bool, default true)
- Emette: `@select` con oggetto articolo selezionato
- Salva `_obj` nel form per restore (pattern `feedback_autocomplete_restore`)

---

## 6. Frontend — Listini

### 6.1 Struttura file

```
frontend/src/vendite/
├── api/
│   └── listini.js                    # Funzioni API listini
├── stores/
│   └── listini.js                    # Store Pinia listini
├── components/
│   ├── ListiniSearchTable.vue        # Lista listini con filtri
│   ├── ListinoDrawer.vue             # Drawer crea/modifica listino
│   ├── ListinoVersioniTab.vue        # Tab versioni del listino
│   ├── ListinoRigheTab.vue           # Tab righe prezzo di una versione
│   ├── ListinoAssociazioniTab.vue    # Tab associazioni perimetro
│   ├── VersioneDrawer.vue            # Sub-drawer crea/modifica versione
│   ├── RigaListinoDrawer.vue         # Sub-drawer crea/modifica riga prezzo
│   └── TestResolverDialog.vue        # Dialog test resolver prezzo
├── views/
│   └── ListiniView.vue               # Pagina completa
└── composables/
    └── useListinoForm.js             # Logica form listino
```

### 6.2 ListiniSearchTable

| Colonna | Sorgente | Note |
| --- | --- | --- |
| Codice | `codice` | Link che apre il drawer |
| Descrizione | `descrizione` | |
| Dominio | `dominio` | Badge UTILITY / COMMERCIO |
| Versioni attive | count | Numero versioni in stato ATTIVA |
| Attivo | `attivo` | Badge stato |

Filtri:

1. `search` — ILIKE su codice + descrizione
2. `dominio` — dropdown (Tutti / UTILITY / COMMERCIO)
3. `attivo` — dropdown (Tutti / Si / No), default Si

### 6.3 ListinoDrawer — Dati principali

Form con campi:

| Campo | Tipo | Note |
| --- | --- | --- |
| `codice` | InputText | Obbligatorio |
| `descrizione` | InputText | Obbligatorio |
| `dominio` | Select | UTILITY / COMMERCIO |

In modalita' modifica: 3 tab sotto il form:

1. **Versioni** (ListinoVersioniTab)
2. **Associazioni** (ListinoAssociazioniTab)
3. **Informazioni** — campi audit

Pulsante globale "Test prezzo" che apre il TestResolverDialog.

### 6.4 ListinoVersioniTab

DataTable con le versioni del listino selezionato:

| Colonna | Note |
| --- | --- |
| Stato | Badge BOZZA (giallo) / ATTIVA (verde) / CHIUSA (grigio) |
| Valido dal | Data |
| Valido al | Data o "—" (open-ended) |
| Priorita' | Numerico |
| Righe | Count righe prezzo |
| Azioni | Apri dettaglio, cambia stato |

Click su riga → apre VersioneDrawer con dentro ListinoRigheTab (righe prezzo della versione).

### 6.5 VersioneDrawer

| Campo | Tipo | Note |
| --- | --- | --- |
| `stato` | Badge readonly | Visualizzazione. Cambio stato via azione dedicata |
| `valido_dal` | Calendar | Obbligatorio |
| `valido_al` | Calendar | Facoltativo |
| `priorita` | InputNumber | Default 0 |

Azioni stato nella toolbar:

- BOZZA → "Attiva" (guard: almeno 1 riga)
- ATTIVA → "Chiudi"
- CHIUSA → nessuna azione

Tab interna: **Righe prezzo** (ListinoRigheTab).

### 6.6 ListinoRigheTab

DataTable con le righe prezzo della versione selezionata:

| Colonna | Note |
| --- | --- |
| Articolo | codice + descrizione (da JOIN) |
| UoM | codice UoM |
| Prezzo | Formattato con fino a 10 decimali |
| BA | codice BA (se presente) |
| Utility | descrizione utility (se presente) |
| Emittente | descrizione emittente (se presente) |
| Azioni | Modifica, elimina |

Bottone "Aggiungi riga" → apre RigaListinoDrawer.

### 6.7 RigaListinoDrawer

| Campo | Tipo | Note |
| --- | --- | --- |
| `articolo_id` | ArticoloLookup | Obbligatorio — building block riutilizzabile §5.6 |
| `uom_id` | Select | Popolato dalle UoM operative dell'articolo selezionato |
| `prezzo` | InputNumber | Obbligatorio, precision 10 decimali |
| `billing_account_id` | AutoComplete BA | Facoltativo |
| `utility_id` | Select utility | Facoltativo |
| `emittente_soggetto_ruolo_id` | AutoComplete emittente | Facoltativo |

Regola UX: quando l'utente seleziona un articolo, il dropdown UoM si popola automaticamente con le UoM operative di quell'articolo (chiamata a `/api/v1/catalogo/articoli/{id}/uom/`).

### 6.8 ListinoAssociazioniTab

DataTable con le associazioni del listino:

| Colonna | Note |
| --- | --- |
| BA | codice BA (se presente) |
| Utility | descrizione utility (se presente) |
| Emittente | descrizione emittente (se presente) |
| Priorita' | Numerico |
| Valido dal | Data |
| Valido al | Data o "—" |
| Azioni | Modifica, elimina |

Form inline per aggiunta rapida (stesso pattern contatti/conti nel ClienteDrawer).

### 6.9 TestResolverDialog

Dialog modale per testare il resolver prezzo:

| Campo input | Tipo | Note |
| --- | --- | --- |
| `articolo_id` | ArticoloLookup | Obbligatorio |
| `uom_id` | Select UoM | Obbligatorio, popolato da articolo |
| `data_riferimento` | Calendar | Obbligatorio, default oggi |
| `billing_account_id` | AutoComplete BA | Facoltativo |
| `utility_id` | Select | Facoltativo |
| `emittente_soggetto_ruolo_id` | AutoComplete | Facoltativo |

Output:

| Campo | Note |
| --- | --- |
| Prezzo risolto | Formattato con decimali |
| Match level | 1-7 con descrizione del livello |
| Listino usato | Codice + descrizione |
| Versione usata | Date validita' + priorita' |
| Associazione | Dettaglio perimetro |

Errori visualizzati: `E_PREZZO_LISTINO_NON_TROVATO`, `E_PREZZO_LISTINO_AMBIGUO` con messaggio leggibile.

---

## 7. Navigazione e routing

### 7.1 Sidebar

Aggiungere in `src/core/navigation.js`:

| Dominio | Icona | Label | Rotta |
| --- | --- | --- | --- |
| Catalogo | `pi-box` | Articoli | `catalogo-articoli` |
| Vendite | `pi-tag` | Listini | `vendite-listini` |

### 7.2 Rotte

| Nome rotta | Path | Componente |
| --- | --- | --- |
| `catalogo-articoli` | `/catalogo/articoli` | `ArticoliView` |
| `vendite-listini` | `/vendite/listini` | `ListiniView` |

---

## 8. Test

### 8.1 Test Django — Catalogo

| File | Contenuto |
| --- | --- |
| `apps/catalogo/tests/services/test_catalogo_service.py` | CRUD articolo, disattivazione con guard, gestione UoM, gestione BoM, gestione note |
| `apps/catalogo/tests/api/test_articoli_api.py` | Endpoint lista, dettaglio, creazione, aggiornamento, lookup, UoM CRUD, BoM CRUD, note CRUD |

Stima: ~40 test case.

### 8.2 Test Django — Listini

| File | Contenuto |
| --- | --- |
| `apps/vendite/tests/services/test_listini_service.py` | CRUD listino, ciclo versioni, righe, associazioni, test resolver |
| `apps/vendite/tests/api/test_listini_api.py` | Tutti gli endpoint §4.3 |

Stima: ~35 test case.

### 8.3 Strategia mock

Tutti i test usano `unittest.TestCase` con mock DB per compatibilita' CI (nessun DB reale). Pattern:

```python
@patch.object(CatalogoRepository, 'list_articoli', return_value=(...))
def test_list_articoli(self, mock_list):
    ...
```

---

## 9. Fasi di sviluppo

### Fase 1 — Backend Catalogo (articoli)

| # | Task | Stima |
| --- | --- | --- |
| 1.1 | Repository `catalogo_repository.py` (7 metodi) | |
| 1.2 | Repository `catalogo_uom_repository.py` (7 metodi) | |
| 1.3 | Repository `catalogo_bom_repository.py` (8 metodi) | |
| 1.4 | Service `catalogo_service.py` (8 metodi) | |
| 1.5 | API views + urls (19 endpoint) | |
| 1.6 | Test service + API (~40 test) | |

### Fase 2 — Backend Listini (vendite)

| # | Task | Stima |
| --- | --- | --- |
| 2.1 | Repository `listini_repository.py` (18 metodi) | |
| 2.2 | Service `listini_service.py` (9 metodi) | |
| 2.3 | API views + urls (18 endpoint) | |
| 2.4 | Test service + API (~35 test) | |

### Fase 3 — Frontend Articoli

| # | Task | Stima |
| --- | --- | --- |
| 3.1 | API functions + Store Pinia | |
| 3.2 | ArticoliSearchTable + ArticoliView | |
| 3.3 | ArticoloDrawer (form principale) | |
| 3.4 | ArticoloUomTab | |
| 3.5 | ArticoloBomTab | |
| 3.6 | ArticoloNoteTab | |
| 3.7 | ArticoloLookup (building block) | |
| 3.8 | i18n chiavi `catalogo.*` | |

### Fase 4 — Frontend Listini

| # | Task | Stima |
| --- | --- | --- |
| 4.1 | API functions + Store Pinia | |
| 4.2 | ListiniSearchTable + ListiniView | |
| 4.3 | ListinoDrawer (form + tab) | |
| 4.4 | VersioneDrawer + ListinoRigheTab | |
| 4.5 | RigaListinoDrawer | |
| 4.6 | ListinoAssociazioniTab | |
| 4.7 | TestResolverDialog | |
| 4.8 | i18n chiavi `listini.*` | |

### Fase 5 — Integrazione e test end-to-end

| # | Task | Stima |
| --- | --- | --- |
| 5.1 | Navigazione sidebar + routing | |
| 5.2 | Test UI reale articoli (CRUD, UoM, BoM, note) | |
| 5.3 | Test UI reale listini (CRUD, versioni, righe, associazioni) | |
| 5.4 | Test resolver prezzo da dialog | |
| 5.5 | Smoke test bash (opzionale) | |

---

## 10. Building block riutilizzabili prodotti

Questa fase produce building block consumabili da altri domini:

| Componente | Tipo | Consumatori previsti |
| --- | --- | --- |
| `ArticoloLookup.vue` | Componente Vue | Righe ordine, righe preventivo, righe listino, righe fattura |
| `useArticoloLookup.js` | Composable | Qualsiasi form che necessita selezione articolo |
| `/api/v1/catalogo/articoli/lookup/` | API REST | Frontend e integrazioni esterne |
| `/api/v1/catalogo/articoli/{id}/uom/` | API REST | Drawer righe documento (popola dropdown UoM) |
| `/api/v1/catalogo/unita-misura/lookup/` | API REST | Qualsiasi form con selezione UoM |
| `/api/v1/vendite/listini/test-prezzo/` | API REST | Verifica pricing cross-dominio |

---

## 11. Dipendenze esterne (lookup da altri domini)

I form di listini necessitano lookup da domini esterni gia' operativi:

| Lookup | Endpoint esistente | Usato in |
| --- | --- | --- |
| Billing Account | Da verificare (anagrafiche) | RigaListinoDrawer, AssociazioniTab |
| Utility | `/api/v1/core/lookup/codici/?rel=config.utilities` | RigaListinoDrawer, AssociazioniTab |
| Emittente fiscale | Da verificare (anagrafiche) | RigaListinoDrawer, AssociazioniTab |
| IVA | `/api/v1/core/lookup/codici/?rel=config.iva` | ArticoloDrawer |
| Tipologia articolo | `/api/v1/core/lookup/codici/?rel=vendite.articoli_tipologie` | ArticoloDrawer, filtro lista |
| Gruppo articolo | `/api/v1/core/lookup/codici/?rel=vendite.articoli_gruppi` | ArticoloDrawer, filtro lista |
| Spesa | `/api/v1/core/lookup/codici/?rel=vendite.articoli_spesa` | ArticoloDrawer |
| Conti contabili | `/api/v1/core/lookup/codici/?rel=config.conti_contabili` | ArticoloDrawer |

Nota: verificare che le tabelle `vendite.articoli_tipologie`, `vendite.articoli_gruppi`, `vendite.articoli_spesa` siano gia' registrate nella whitelist lookup generico. Se no, aggiungerle.

---

## 12. Checklist operativa

### Fase 1 — Catalogo backend minimo (contratti base)

- [x] `catalogo_repository.py` (7+ metodi: list, get, create, update, deactivate, lookup_articoli + CRUD UoM)
- [x] `catalogo_service.py` (fn_list_articoli, fn_get_articolo, fn_lookup_articoli + fn_*_unita_misura)
- [x] `views.py` (ApiArticoliList, ApiArticoloDetail, ApiArticoliLookup + ApiUnitaMisuraList/Detail/Disattiva)
- [x] `urls.py` registrato in `zeroerp_backend/urls.py` sotto `api/v1/catalogo/`
- [x] `GET /api/v1/catalogo/articoli/`
- [x] `GET /api/v1/catalogo/articoli/{id}/`
- [x] `GET /api/v1/catalogo/articoli/lookup/`
- [x] lookup UoM via endpoint generico `GET /api/v1/core/lookup/codici/?rel=catalogo.unita_misura`

### Fase 2 — Catalogo backend CRUD articolo

- [x] `POST /api/v1/catalogo/articoli/` (fn_create_articolo + handle_post_json)
- [x] `PATCH /api/v1/catalogo/articoli/{id}/` (fn_update_articolo + request.data)
- [x] `POST /api/v1/catalogo/articoli/{id}/disattiva/` (fn_disattiva_articolo)
- [x] codice immutabile (guard DB)
- [x] codici errore in `error_policies.py` (E_CATALOGO_VALIDATION, E_CATALOGO_ARTICOLO_NOT_FOUND)

### Fase 3 — Catalogo backend esteso (UoM, BoM, note)

- [x] `catalogo_uom_repository.py` (7 metodi: list, get, create, update, delete, get_uom_base, get_uom_factor)
- [x] `catalogo_bom_repository.py` (12 metodi: componenti CRUD + note CRUD + resolve_nota)
- [x] metodi aggiuntivi in `catalogo_service.py` (fn_*_uom_operativa x4, fn_*_componente x4, fn_*_nota x4)
- [x] endpoint UoM (GET/POST lista, PATCH/DELETE dettaglio)
- [x] endpoint componenti (GET/POST lista, PATCH/DELETE dettaglio)
- [x] endpoint note (GET/POST per articolo, PATCH/DELETE per nota)
- [x] codici errore (E_CATALOGO_UOM_NOT_FOUND, E_CATALOGO_COMPONENTE_NOT_FOUND, E_CATALOGO_NOTA_NOT_FOUND)
- [x] `_sql_write_helpers.py` condiviso (JSONB cast)
- [x] test service (25 test) + test API (26 test) = 51 test verdi

### Fase 4 — Frontend catalogo

- [x] API client `catalogo/api/catalogo.js` (20 funzioni)
- [x] store Pinia `catalogo/stores/articoli.js` + `unitaMisura.js`
- [x] `ArticoliSearchTable.vue` (7 filtri, empty state, lookup generico per tipologie/gruppi)
- [x] `ArticoloDrawer.vue` (COMPLEX 800px, 3 tab in edit: UoM, BoM, Note)
- [x] `ArticoloUomTab.vue` (CRUD inline, lookup UoM via `lookupCodici`)
- [x] `ArticoloBomTab.vue` (CRUD inline, usa BB `ArticoloLookup`)
- [x] `ArticoloNoteTab.vue` (CRUD inline)
- [x] `ArticoloLookup.vue` in `core/components/` (building block cross-dominio)
- [x] `UnitaMisuraSearchTable.vue` + `UnitaMisuraDrawer.vue` + `UnitaMisuraView.vue`
- [x] backend UoM CRUD (repository + service + view + rotte)
- [x] `navigation.js` + `router/index.js` (2 voci L2, 2 rotte, `catalogo` in `domainsWithRoutes`)
- [x] i18n `catalogo` (76 chiavi) + `nav_menu.catalogo` + `common.all/active/inactive`
- [x] build frontend OK, 49 test backend verdi

### Fase 5 — Backend listini

- [x] `listini_repository.py` (19 metodi: listini, versioni, righe, associazioni, validazione, resolver)
- [x] `listini_service.py` (18 funzioni fn_*)
- [x] `views_listini.py` (10 classi, 18 metodi HTTP) + `urls_listini.py` (10 rotte)
- [x] lista + dettaglio listini (con count versioni/associazioni)
- [x] CRUD listino + versioni (con cambio stato BOZZA/ATTIVA/CHIUSA)
- [x] righe prezzo (CRUD con display fields via JOIN)
- [x] associazioni (CRUD con display fields via JOIN)
- [x] test resolver prezzo (wrapper fn_resolve_prezzo_listino)
- [x] codici errore (E_VENDITE_VALIDATION, 4x NOT_FOUND)
- [x] PATCH usa `request.data` (corretto da `handle_post_json`)
- [x] test service (8) + test API (21) = 29 test verdi

### Fase 6 — Frontend listini

- [x] API client `vendite/api/listini.js` (17 funzioni)
- [x] store Pinia `vendite/stores/listini.js`
- [x] `ListiniSearchTable.vue` + `ListiniView.vue`
- [x] `ListinoDrawer.vue` (tab versioni + associazioni + pulsante test resolver)
- [x] `ListinoVersioniTab.vue` (lista, crea inline, azioni stato, apre VersioneDrawer)
- [x] `ListinoAssociazioniTab.vue` (CRUD inline)
- [x] `VersioneDrawer.vue` (sub-drawer con righe prezzo CRUD, guard BOZZA)
- [x] `TestResolverDialog.vue` (dialog modale con ArticoloLookup BB)
- [x] `navigation.js` (voce L2 vendite) + `router/index.js` (rotta vendite-listini)
- [x] i18n `listini` (62 chiavi) + `nav_menu.vendite`
- [x] build OK, 78 test verdi, nessun hardcoded

### Fase 7 — Consolidamento e test di flusso

- [x] test unitari backend catalogo (49 test) + listini (29 test) = 78 test verdi
- [x] verifica envelope API, naming campi e ordinamenti whitelist (conforme a api.md)
- [x] verifica lookup articoli riusabile da frontend `catalogo` e `vendite` (ArticoloLookup BB in core/)
- [x] verifica PATCH usa `request.data` su tutti gli endpoint (catalogo + vendite)
- [x] navigazione sidebar + routing (catalogo 2 voci, vendite 1 voce, 3 rotte)
- [x] registrazione whitelist lookup: `catalogo.unita_misura` gia' in whitelist, tipologie/gruppi/spesa gia' presenti
- [ ] verifica permessi, readonly mode e pattern tab/drawer (da testare su UI reale)
- [ ] documentazione API (`docs/it/backend/catalogo/manual/`)
- [ ] documentazione API (`docs/it/backend/vendite/manual/`)

---

*WIP — Gestione Articoli e Listini — ZeroERP (aprile 2026)*
