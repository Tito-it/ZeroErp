# Gestione Articoli — Catalogo (COMPLETATO)

> Stato: **COMPLETATO E TESTATO**
>
> Data completamento: aprile 2026
>
> Precedente file WIP: `work-in-progress/gestione-articoli-listini.md` (consolidato e diviso fra questo documento e `work-in-progress/sviluppo-listini.md`).
>
> Riferimenti:
>
> * [docs/it/dbzero/catalogo/](../../dbzero/catalogo/) — documentazione schema catalogo
> * [docs/it/dev/api.md](../api.md) — linee guida API

---

## Perimetro funzionale coperto

Il dominio `catalogo` copre articoli, unita' di misura operative, distinta base (BoM) e note tecniche:

1. CRUD articoli con filtri, ricerca, paginazione
2. Gestione UoM operative per articolo (assegnazione, conversione, flag vendita/acquisto/logistica)
3. Gestione distinta base (BoM) con versionamento temporale
4. Note articolo e note componenti
5. Lookup articoli per autocomplete (uso cross-dominio: ordini, preventivi, listini, fatture)
6. Lookup UoM via endpoint generico `core/lookup/codici`

Fuori scope (coperto altrove):

1. Listini prezzo → vedi [sviluppo-listini-v5.md](sviluppo-listini-v5.md) (il vecchio `sviluppo-listini.md` non esiste più: la specifica è stata versionata in v1..v6, la v5 è quella di riferimento)
2. Integrazione pricing commessa (DB-L3) → vedi commesse

---

## Decisioni architetturali

### Separazione app Django

1. Articoli, UoM, BoM e note → `apps/catalogo/` (schema `catalogo`)

Motivazione: rispetta l'allineamento app-schema. L'ordine di sviluppo e' stato Anello 1 (catalogo) → Anello 3 (vendite/listini) per fornire lookup e contratti agli anelli esterni.

### Repository pattern

1. `catalogo_repository.py` — CRUD articoli, list, search, lookup, decodifiche (7 metodi)
2. `catalogo_uom_repository.py` — UoM operative, conversioni, lookup UoM (7 metodi)
3. `catalogo_bom_repository.py` — BoM (componenti), versionamento temporale, note componenti (12 metodi)

Motivazione: segue la regola di naming per sottodominio specializzato (AGENTS.md §Naming convention). La BoM ha logica autonoma (overlap temporale, guard composito/solo-componente) che giustifica il file separato.

### Service pattern

1. `catalogo_service.py` — orchestrazione CRUD articoli, validazioni cross-entita' (fn_list_articoli, fn_get_articolo, fn_lookup_articoli, fn_*_unita_misura, fn_*_uom_operativa x4, fn_*_componente x4, fn_*_nota x4)

### Viste DB come sorgente per le liste

Le API lista usano le viste `vw_articoli_dettaglio` e `vw_articoli_componenti_dettaglio` per evitare JOIN nel codice Python.

### Lookup articoli cross-dominio

1. Endpoint lookup dedicato `/api/v1/catalogo/articoli/lookup/` con search su codice + descrizione
2. Restituisce: `id, codice, descrizione, uom_codice, uom_descrizione, is_composito, voce_utility, attivo`
3. Filtri opzionali: `voce_utility=true/false`, `attivo=true`, `is_composito=true/false`
4. Consumato da: drawer righe ordine, drawer righe preventivo, drawer righe listino

### Lookup UoM via endpoint generico

Le UoM sono lookup generico via `GET /api/v1/core/lookup/codici/?rel=catalogo.unita_misura` (tabella gia' in whitelist). Nessun endpoint dedicato.

---

## Backend — Catalogo (articoli)

### Repository: `apps/catalogo/db/catalogo_repository.py`

| # | Metodo | SQL | Note |
| --- | --- | --- | --- |
| 1 | `list_articoli()` | SELECT da `vw_articoli_dettaglio` con filtri, search ILIKE, paginazione, order_by | Filtri: `attivo`, `is_composito`, `voce_utility`, `tipo_voce_id`, `gruppo_voce_id`, `search`, `data_da/data_a` |
| 2 | `get_articolo()` | SELECT da `vw_articoli_dettaglio` WHERE id | Singolo articolo con dati arricchiti |
| 3 | `create_articolo()` | INSERT INTO `catalogo.articoli` | Campi: codice, descrizione, descrizione_breve, uom_id, tipo_voce_id, gruppo_voce_id, spesa_id, iva_id, conti contabili, is_composito, voce_utility, requires_serial |
| 4 | `update_articolo()` | UPDATE `catalogo.articoli` SET ... WHERE id | Codice immutabile (trigger DB). Tutti gli altri campi editabili |
| 5 | `deactivate_articolo()` | UPDATE `catalogo.articoli` SET attivo=false WHERE id | Il trigger DB blocca se ci sono figli attivi (27 guard) |
| 6 | `lookup_articoli()` | SELECT id, codice, descrizione, uom da `vw_articoli_dettaglio` con search | Per autocomplete cross-dominio. Limit 50, filtri opzionali |
| 7 | `count_articoli()` | COUNT da `vw_articoli_dettaglio` con stessi filtri di list | Per paginazione |

### Repository: `apps/catalogo/db/catalogo_uom_repository.py`

| # | Metodo | SQL | Note |
| --- | --- | --- | --- |
| 1 | `list_uom_operative()` | SELECT da `catalogo.articoli_uom_operativa` JOIN `unita_misura` WHERE articolo_id | UoM assegnate a un articolo con dettagli |
| 2 | `create_uom_operativa()` | INSERT INTO `catalogo.articoli_uom_operativa` | Constraint UNIQUE(articolo_id, uom_id) gestito da DB |
| 3 | `update_uom_operativa()` | UPDATE `catalogo.articoli_uom_operativa` SET ... WHERE id | Flag, factor_to_base, arrotondamento |
| 4 | `delete_uom_operativa()` | DELETE FROM `catalogo.articoli_uom_operativa` WHERE id | Guard DB se in uso |
| 5 | `lookup_unita_misura()` | SELECT id, codice, descrizione FROM `catalogo.unita_misura` WHERE attivo=true | Per dropdown/autocomplete |
| 6 | `get_uom_base()` | SELECT `catalogo.fn_get_uom_base(p_articolo_id)` | Wrapper funzione DB |
| 7 | `get_uom_factor()` | SELECT `catalogo.fn_get_uom_factor(p_articolo_id, p_uom_id)` | Wrapper funzione DB |

### Repository: `apps/catalogo/db/catalogo_bom_repository.py`

| # | Metodo | SQL | Note |
| --- | --- | --- | --- |
| 1 | `list_componenti()` | SELECT da `vw_articoli_componenti_dettaglio` WHERE prodotto_id | BoM di un articolo con dettagli componente |
| 2 | `create_componente()` | INSERT INTO `catalogo.articoli_componenti` | Guard DB: prodotto must be is_composito, not is_solo_componente |
| 3 | `update_componente()` | UPDATE `catalogo.articoli_componenti` SET ... WHERE id | coeff_qta, flag, date validita' |
| 4 | `delete_componente()` | DELETE FROM `catalogo.articoli_componenti` WHERE id | Guard DB su note figlie |
| 5 | `list_note_articolo()` | SELECT da `vw_articoli_note` WHERE target_id | Note articolo |
| 6 | `create_nota_articolo()` | INSERT INTO `catalogo.note` con target_tipo='ARTICOLI' | |
| 7 | `update_nota()` | UPDATE `catalogo.note` SET ... WHERE id | |
| 8 | `delete_nota()` | DELETE FROM `catalogo.note` WHERE id | |

### API: `apps/catalogo/api/views.py`

| # | Metodo | Path | Scopo |
| --- | --- | --- | --- |
| 1 | GET | `/api/v1/catalogo/articoli/` | Lista paginata con search e filtri |
| 2 | POST | `/api/v1/catalogo/articoli/` | Crea articolo |
| 3 | GET | `/api/v1/catalogo/articoli/{id}/` | Dettaglio con UoM + BoM + note |
| 4 | PATCH | `/api/v1/catalogo/articoli/{id}/` | Aggiorna articolo |
| 5 | POST | `/api/v1/catalogo/articoli/{id}/disattiva/` | Disattiva articolo |
| 6 | GET | `/api/v1/catalogo/articoli/lookup/` | Lookup per autocomplete cross-dominio |
| 7 | GET | `/api/v1/catalogo/articoli/{id}/uom/` | Lista UoM operative dell'articolo |
| 8 | POST | `/api/v1/catalogo/articoli/{id}/uom/` | Aggiungi UoM operativa |
| 9 | PATCH | `/api/v1/catalogo/articoli/{id}/uom/{uom_op_id}/` | Aggiorna UoM operativa |
| 10 | DELETE | `/api/v1/catalogo/articoli/{id}/uom/{uom_op_id}/` | Rimuovi UoM operativa |
| 11 | GET | `/api/v1/catalogo/articoli/{id}/componenti/` | Lista BoM dell'articolo |
| 12 | POST | `/api/v1/catalogo/articoli/{id}/componenti/` | Aggiungi componente BoM |
| 13 | PATCH | `/api/v1/catalogo/articoli/{id}/componenti/{comp_id}/` | Aggiorna componente |
| 14 | DELETE | `/api/v1/catalogo/articoli/{id}/componenti/{comp_id}/` | Rimuovi componente |
| 15 | GET | `/api/v1/catalogo/articoli/{id}/note/` | Lista note articolo |
| 16 | POST | `/api/v1/catalogo/articoli/{id}/note/` | Crea nota articolo |
| 17 | PATCH | `/api/v1/catalogo/note/{nota_id}/` | Aggiorna nota |
| 18 | DELETE | `/api/v1/catalogo/note/{nota_id}/` | Elimina nota |
| 19 | GET | `/api/v1/catalogo/unita-misura/` + CRUD | Lista e gestione unita' di misura |

### Errori applicativi

Codici registrati in `error_policies.py`:

* `E_CATALOGO_VALIDATION`
* `E_CATALOGO_ARTICOLO_NOT_FOUND`
* `E_CATALOGO_UOM_NOT_FOUND`
* `E_CATALOGO_COMPONENTE_NOT_FOUND`
* `E_CATALOGO_NOTA_NOT_FOUND`

Helper condiviso: `_sql_write_helpers.py` (JSONB cast).

---

## Frontend — Articoli

### Struttura file

```
frontend/src/catalogo/
├── api/
│   └── catalogo.js                  # 20 funzioni API (list, get, create, update, lookup, uom, bom, note)
├── stores/
│   ├── articoli.js                  # Store Pinia articoli
│   └── unitaMisura.js               # Store Pinia unita' di misura
├── components/
│   ├── ArticoliSearchTable.vue      # Lista articoli con filtri e search
│   ├── ArticoloDrawer.vue           # Drawer crea/modifica articolo (COMPLEX 800px, 3 tab in edit)
│   ├── ArticoloUomTab.vue           # Tab UoM operative (CRUD inline)
│   ├── ArticoloBomTab.vue           # Tab distinta base (CRUD inline + ArticoloLookup)
│   ├── ArticoloNoteTab.vue          # Tab note articolo (CRUD inline)
│   ├── UnitaMisuraSearchTable.vue   # Lista unita' di misura
│   └── UnitaMisuraDrawer.vue        # Drawer CRUD unita' di misura
└── views/
    ├── ArticoliView.vue             # Pagina articoli
    └── UnitaMisuraView.vue          # Pagina unita' di misura
```

Building block cross-dominio prodotto:

* `frontend/src/core/components/ArticoloLookup.vue` — autocomplete articoli server-side riutilizzabile

### ArticoliSearchTable

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

Filtri (7):

1. `search` — ILIKE su codice + descrizione (trigram)
2. `attivo` — dropdown (Tutti / Si / No), default Si
3. `is_composito` — dropdown (Tutti / Si / No)
4. `voce_utility` — dropdown (Tutti / Si / No)
5. `tipo_voce_id` — lookup da `vendite.articoli_tipologie`
6. `gruppo_voce_id` — lookup da `vendite.articoli_gruppi`
7. range date insert

### ArticoloDrawer — Dati principali

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
| `is_solo_componente` | ToggleSwitch | Default false. Mutually exclusive con is_composito |
| `voce_utility` | ToggleSwitch | Default false |
| `requires_serial` | ToggleSwitch | Default false |

In modalita' modifica: 3 tab sotto il form principale (+ Informazioni audit):

1. **UoM operative** (ArticoloUomTab)
2. **Distinta base** (ArticoloBomTab) — visibile solo se `is_composito = true`
3. **Note** (ArticoloNoteTab)

### Building block ArticoloLookup

Componente `ArticoloLookup.vue` basato su server-side autocomplete (`useServerAutocomplete`):

* Endpoint: `/api/v1/catalogo/articoli/lookup/`
* Display: `codice — descrizione`
* Props: `voceUtility` (bool, filtro opzionale), `soloAttivi` (bool, default true)
* Emette: `@select` con oggetto articolo selezionato
* Salva `_obj` nel form per restore (pattern `feedback_autocomplete_restore`)

Consumatori cross-dominio confermati:

* `frontend/src/catalogo/components/ArticoloBomTab.vue` (componente distinta base)
* `frontend/src/vendite/components/VersioneDrawer.vue` (righe listino)
* `frontend/src/vendite/components/TestResolverDialog.vue` (test resolver prezzi)

### Navigazione e routing

`src/core/navigation.js`: 2 voci L2 sotto dominio "Catalogo":

| Voce | Icona | Rotta |
| --- | --- | --- |
| Articoli | `pi-box` | `catalogo-articoli` |
| Unita' di Misura | `pi-calculator` | `catalogo-unita-misura` |

`router/index.js`: 2 rotte, `catalogo` in `domainsWithRoutes`.

### i18n

* `locales/it.json` — sezione `catalogo` (76 chiavi) + `nav_menu.catalogo`
* `locales/en.json` — stesse chiavi tradotte
* Chiavi generiche `common.all`, `common.active`, `common.inactive`

---

## Test

Stato finale: **49 test backend verdi** (catalogo).

| File | Test | Contenuto |
| --- | --- | --- |
| `apps/catalogo/tests/services/test_catalogo_service.py` | 25 | CRUD articolo, disattivazione con guard, gestione UoM, gestione BoM, gestione note |
| `apps/catalogo/tests/api/test_articoli_api.py` | 26 | Endpoint lista, dettaglio, creazione, aggiornamento, lookup, UoM CRUD, BoM CRUD, note CRUD |

Strategia mock: tutti i test usano `unittest.TestCase` con mock DB per compatibilita' CI (nessun DB reale).

```python
@patch.object(CatalogoRepository, 'list_articoli', return_value=(...))
def test_list_articoli(self, mock_list):
    ...
```

---

## Regole seguite

Note operative confermate durante l'implementazione:

1. `DomainAPIView` con `area_funzionale = "catalogo"` su tutte le view
2. `@extend_schema` su tutti gli endpoint
3. Helper condivisi `_prepare_insert_parts` e `_prepare_update_parts` nel repository (riduce duplicazione)
4. Validazione articolo/UoM in un solo round-trip
5. Display fields via JOIN diretti (non lookup client-side)
6. PATCH usa `request.data` (non `handle_post_json`)
7. `ArticoloBomTab` usa `ArticoloLookup` (BB cross-dominio) invece di autocomplete raw
8. Tutti i testi via `$t()`, nessun hardcoded
9. Building frontend OK, nessuna regressione

---

## Building block riutilizzabili prodotti

Questa fase ha prodotto i seguenti building block consumabili da altri domini:

| Componente | Tipo | Consumatori previsti |
| --- | --- | --- |
| `ArticoloLookup.vue` | Componente Vue | Righe listino, righe ordine, righe preventivo, righe fattura |
| `/api/v1/catalogo/articoli/lookup/` | API REST | Frontend e integrazioni esterne |
| `/api/v1/catalogo/articoli/{id}/uom/` | API REST | Drawer righe documento (popola dropdown UoM) |
| `lookupCodici('catalogo.unita_misura')` | API generica | Qualsiasi form con selezione UoM |

---

## Aperto / da completare (minor)

Rimangono due voci non bloccanti, lasciate aperte volutamente:

* [ ] Documentazione API catalogo in `docs/it/backend/catalogo/manual/` (dall'OpenAPI di `@extend_schema`)
* [ ] Verifica permessi e readonly mode su UI reale (pattern tab/drawer gia' conforme al resto del progetto)

---

*Catalogo Articoli — ZeroERP — completato aprile 2026*
