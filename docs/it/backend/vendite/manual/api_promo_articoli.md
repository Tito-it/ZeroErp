# API Promo articoli `vendite.promo_articoli`

## Scopo

CRUD admin per l'overlay promo temporale **STADIO 0** del resolver prezzi v5:
una promo attiva per `(articolo, uom)` in un periodo batte qualunque prezzo
da listino o matrice categoria. E' l'unico livello che ammette
`tipo_variazione = PREZZO_FISSO` (prezzo assoluto sostitutivo, vietato
in listini e matrice categoria).

Riferimento concettuale:
[sviluppo-listini-v5.md](/dev/work-done/sviluppo-listini-v5) §6.

## Contesto

Il resolver `fn_resolve_prezzo_listino_v2` consulta `promo_articoli` come
primo stadio se la categoria del BA ha `partecipa_promo = TRUE`. L'EXCLUDE
`ex_promo_articoli_no_overlap` garantisce al massimo una promo attiva per
`(articolo, uom)` per periodo — il resolver non ha bisogno di tie-break.

## Autorizzazione

Area `vendite` **e** permesso modello `("vendite", "promo_articolo")`
(`model_permission`) su lista e dettaglio: senza, `403`.

## Input

### Query params lista (`GET /api/v1/vendite/promo-articoli/`)

| Parametro | Tipo | Descrizione |
|---|---|---|
| `search` | string | Ricerca libera: le colonne le decide il catalogo della lista `vendite.promo_articoli` (`ricerca_full` nella configurazione). Sotto 3 caratteri il termine si ignora (nessun `400`) |
| `attivo` | bool | `true`/`false`/assente |
| `articolo_id` | UUID | Filtro articolo |
| `uom_id` | int | Filtro unita' di misura |
| `tipo_variazione` | string | `PERCENTUALE \| VALORE_FISSO \| PREZZO_FISSO` |
| `valid_at` | date ISO | Filtra righe la cui `validita` daterange contiene la data |
| `limit` | int | 25 default, max 200 |
| `offset` | int | Paginazione |
| `order_by` | string | `codice \| descrizione \| articolo_codice \| articolo_descrizione \| uom_codice \| valido_dal \| valido_al \| attivo \| data_insert \| data_update` |
| `order_dir` | string | `asc \| desc`; assente = `desc` (default `valido_dal DESC`) |

### Payload create (`POST`)

```json
{
  "codice": "PROMO-BLACKFRIDAY",
  "descrizione": "Promo Black Friday 2026",
  "articolo_id": "019bac81-3f96-7ce8-a086-7e0bd0a2fec1",
  "uom_id": 3,
  "tipo_variazione": "PREZZO_FISSO",
  "valore_variazione": "9.99",
  "valido_dal": "2026-11-24",
  "valido_al": "2026-11-30",
  "meta": {"campagna": "BF26"},
  "attivo": true
}
```

Tutti i campi sono obbligatori tranne `meta` e `attivo` (default DB `'{}'` / `true`).

### Payload patch (`PATCH /{record_id}/`)

Mutabili: `descrizione`, `tipo_variazione` + `valore_variazione` (coppia),
`valido_dal`, `valido_al`, `meta`, `attivo`.

**Immutabili**: `codice`, `articolo_id`, `uom_id` — queste identificano
semanticamente la promo. Per cambiarle: disattivare la riga e crearne una
nuova.

## Regole

### Vincoli di integrita' (propagati dal DB)

| Vincolo | Tipo | Effetto UI |
|---|---|---|
| `uq_promo_articoli_codice` | UNIQUE | `E_VENDITE_DUPLICATO` — "Esiste gia' una promo con questo codice." |
| `fk_promo_articoli_articolo` | FK | `E_VENDITE_FK` — "Articolo inesistente." |
| `fk_promo_articoli_uom` | FK | `E_VENDITE_FK` — "Unita' di misura inesistente." |
| `chk_promo_articoli_tipo_variazione` | CHECK | `E_VENDITE_VALIDATION` — enum ammesso solo `{PERCENTUALE, VALORE_FISSO, PREZZO_FISSO}` (anticipato service). |
| guard comune delle date (`trg_promo_articoli_a10_date_validita_ins_upd`) | TRIGGER | `E_DATA_AL_MINORE_DAL` (400, campo `valido_al`) — `valido_al < valido_dal`. Il service non lo anticipa (dal 2026-09-23). |
| `chk_promo_articoli_valore` | CHECK | `E_VENDITE_VALIDATION` — `PERCENTUALE`/`VALORE_FISSO` richiedono `valore > 0`; `PREZZO_FISSO` richiede `>= 0` (anticipato service). |
| `ex_promo_articoli_no_overlap` | EXCLUDE gist | `E_VENDITE_PROMO_OVERLAP` — due righe attive si sovrappongono su `(articolo, uom)` nello stesso periodo. |

### Campo `validita` (daterange)

Colonna **generata** dal database da `valido_dal`/`valido_al`. Non scrivibile via API; il contratto espone
`valido_dal`/`valido_al`.

## Endpoint

| Metodo | URL | Scopo | Permesso |
|---|---|---|---|
| `GET` | `/api/v1/vendite/promo-articoli/` | Lista paginata + filtri | Admin |
| `POST` | `/api/v1/vendite/promo-articoli/` | Crea promo | Admin |
| `GET` | `/api/v1/vendite/promo-articoli/{id}/` | Dettaglio + capabilities | Admin |
| `PATCH` | `/api/v1/vendite/promo-articoli/{id}/` | Aggiorna (chiavi identificative immutabili) | Admin |

### Capabilities nel detail (Fase 1.B3 refactor frontend vendite)

Il dettaglio espone capability data-driven da `script.fn_capability_promo_articolo`
nella chiave `capabilities`, non fuse nella testata (dal 2026-09-23, [api.md §«Il blob sta SOTTO `capabilities`»](../../../dev/api.md)). Modello **data-driven puro**: nessun stato
persistito, nessuna `available_actions` (le promo non hanno transizioni manuali).

| Campo | Tipo | Significato |
| --- | --- | --- |
| `stato_temporale` | string | `FUTURA` (oggi < valido_dal) / `INIZIATA` (valido_dal ≤ oggi ≤ valido_al) / `SCADUTA` (oggi > valido_al). Calcolato da CURRENT_DATE |
| `can_update` | bool | `false` solo in SCADUTA |
| `can_update_reason` | string\|null | Codice tecnico (es. `PROMO_SCADUTA_IMMUTABILE`); FE compone la chiave i18n via `t('vendite.promo_articoli.update_reason.<lower>')` |
| `min_valido_dal` | date\|null | Vincolo minDate per il DatePicker valido_dal nello stato corrente |
| `min_valido_al` | date\|null | Vincolo minDate per il DatePicker valido_al |
| `non_editable_fields[]` | string[] | Whitelist immutabili: in INIZIATA include codice/articolo_id/uom_id/tipo_variazione/valore_variazione/valido_dal/attivo (solo descrizione+valido_al modificabili); in SCADUTA include tutto |

Specchio esatto del trigger `trgfn_promo_articoli_guard_data_driven`: il FE
disabilita i campi proattivamente, il trigger DB e' la difesa finale.

## Dipendenze DB

* Tabella: `vendite.promo_articoli` (migrazione `20260414-13`)
* FK verso: `catalogo.articoli`, `catalogo.unita_misura`
* Ordine delle date: guard comune `script.trgfn_guard_date_validita`
  (automazione `DATE_VALIDITA`), che risponde `E_DATA_AL_MINORE_DAL`
* Extension: `btree_gist`

Validazione payload e traduzione vincoli DB delegate al building block
`apps.core.services.payload_helpers`. Vedi
[catalogo-building-block-backend.md](/dev/backend/catalogo-building-block-backend).
