# API Ordini di vendita `vendite.ordini`

## Scopo

CRUD operativo (scheletro) degli **ordini di vendita**, documento del ciclo
attivo che raccoglie le righe articolo da evadere/fatturare. Espone testata,
**righe** con **componenti BoM** (modello unificato), **conferma**
(`DRAFT -> CONFERMATO`) e **push singolo a commessa** (chiusura del giro
ordine → attività fatturabili → pipeline lotto → fattura), oltre a **lista
configurabile DEF-8** + export e **note partizionate**.

Clone strutturale della famiglia vendite (preventivi/offerte) — regola del 2:
pricing via `PricingService`, componenti via `fn_ordine_riga_componenti_*`,
note via `PartitionedNoteRepository`, lista/export via `ListaExportService`.
Rispetto a preventivi/offerte l'ordine **non ha revisioni** né listino in testata.

> Stato: **scheletro BE** (analisi
> [analisi-ordini-vendita.md](../../../dev/work-in-progress/analisi-ordini-vendita.md)
> §5). Fuori scope per ora: fulfillment/DDT, indirizzi, conversione
> preventivo/offerta→ordine (che *userà* le colonne origine A1 già predisposte).

### Modello

- **Identità**: `(anno, serie, numero)` + `uid`. Il `numero` è generato dal
  trigger `trgfn_ordini_gen_codice` (BEFORE INSERT) via
  `script.fn_generate_codice('ordine')` — **valorizzato già in BOZZA**, immutabile
  dopo (lock colonne). Il campo `numero` **non va nel payload**.
- **Stato iniziale** `DRAFT` (risolto dal service via
  `config.stati_doc_ordini.codice_interno`).
- **`fatturazione_trigger`** (`CONFERMATO` | `SPEDITO` | `CONSEGNATO`): governa
  *quando* l'ordine pusha a commessa. Default ereditato da
  `billing_account.fatturazione_ordini` (trigger `trgfn_ordini_normalize`);
  sovrascrivibile sul payload.
- **`canale_origine`** (`ADMIN` | `PORTALE` | `SHOP`): immutabile post-INSERT; in
  back-office sempre `ADMIN`.
- **Estensioni modello 2026-06-03**: **agente** (`agente_soggetto_ruolo_id`,
  nullable) ed **origine documento** (A1: `documento_origine_tipo` ∈
  {`PREVENTIVO`,`OFFERTA`} + `documento_origine_id`, **senza UNIQUE** → una
  origine può generare più ordini). Lo scheletro **non valorizza** le colonne
  origine (le userà la conversione upstream, step successivo).
- **Pagamento/valuta**: `modalita_pagamento_id`, `termine_pagamento_id`,
  `valuta_id`, `tasso_cambio` (default 1). `giorni_pagamento`/`fine_mese` e i
  campi trasporto **non sono in testata** (droppati `20251027-01`; vivono su
  BA / DDT a valle).

### State machine

| Da    | A          | Chi la innesca           | Effetto |
| ----- | ---------- | ------------------------ | ------- |
| DRAFT | CONFERMATO | operatore (`/conferma/`) | Abilita il push a commessa (se `fatturazione_trigger=CONFERMATO`) |

La transizione è **autoritativa lato DB** (trigger
`trgfn_ordini_guard_transizione_approvazione` sull'UPDATE di
`stato_doc_ordine_id`): il service applica solo il guard applicativo «origine
DRAFT + almeno una riga». I codici `E_ORDINE_*` sollevati dai trigger sono
**estratti dal MESSAGE** via regex (`_DB_ERROR_CODE_RE`) e propagati come
`ServiceError.code` originale (routing UI specifico), con fallback
`E_VENDITE_VALIDATION`.

## Input

Tutti gli endpoint sotto `DomainAPIView` (`area_funzionale='vendite'`, JWT +
`ZeroERPPermission`). Liste/export con `is_search_endpoint=True`.

### Lista ordini `GET /api/v1/vendite/ordini/`

Lista paginata dalla vista canonica `vendite.vw_ordini_lista` (DEF-8, lista
configurabile `vendite.ordini`). Scope emittente automatico (RLS +
`fn_get_emittenti_scope_pk_ids` su `emittente_fiscale_id`).

| Query param | Tipo | Note |
| --- | --- | --- |
| `search` | str | min 3 char; ILIKE su `numero`, `ragione_sociale_completa`, `ba_codice`, `id_fiscale_univoco_cf_piva` |
| `stato_codice_interno` | str | `codice_interno` stato (`DRAFT` | `CONFERMATO` | …) |
| `billing_account_id` | int | cliente |
| `utility_id` | int | |
| `data_da` / `data_a` | str ISO | filtro su `data` (default lato UI, non backend) |
| `order_by` | str | whitelist: `numero | data | ragione_sociale_completa | ba_codice | utility_codice | totale_doc | fatturazione_trigger | stato_descrizione | stato_codice_interno | data_insert`. Default `data` |
| `order_dir` | str | `asc | desc` (default `desc`), tiebreaker `id` |
| `limit` / `offset` | int | paginazione (limit cap 200) |

### Export lista `GET /api/v1/vendite/ordini/export/?formato=csv|xlsx`

Export DEF-1: stessi filtri della lista, `ListaExportService` + catalogo colonne
`vendite.ordini` (ordine/visibilità/permessi utente rispettati). Cap
`EXPORT_MAX_ROWS`. Parametro **`formato`** (italiano), MAI `format`.
Errori: `E_UI_EXPORT_FORMAT_INVALID` (400), `E_UI_EXPORT_LIMIT_EXCEEDED` (422).

### Create testata `POST /api/v1/vendite/ordini/`

Crea un ordine in `DRAFT`. `handle_post_json`.

| Campo | Tipo | Note |
| --- | --- | --- |
| `billing_account_id` | int | cliente; se presente, `soggetto_ruolo_id` è derivato dal BA |
| `soggetto_ruolo_id` | int | alternativa al BA (NOT NULL in testata) |
| `utility_id` | int | |
| `emittente_fiscale_id` | int | opzionale; se omesso, trigger lo valorizza da GUC |
| `valuta_id`, `modalita_pagamento_id`, `termine_pagamento_id` | int | opzionali |
| `fatturazione_trigger` | str | opzionale; default ereditato da BA |
| `agente_soggetto_ruolo_id` | int | opzionale (E) |
| `data` | str ISO | opzionale (default `CURRENT_DATE`) |
| `meta` | obj | opzionale |

`numero`/`canale_origine`/`stato_doc_ordine_id` **non** vanno nel payload.
Ritorna `{id, uid, numero}`.

### Detail `GET /api/v1/vendite/ordini/<id>/`

Testata (dalla vista + `meta`/`storicizza`) + capability data-driven:
`righe_count`, `can_edit_testata`, `can_edit_righe`, `can_conferma`,
`can_push_commessa`. 404 (`E_ORD_NOT_FOUND`) se inesistente o fuori scope (RLS).

### Update testata `PATCH /api/v1/vendite/ordini/<id>/`

Solo in `DRAFT`. `request.data` (non `handle_post_json`, api.md). Campi
aggiornabili: `billing_account_id`, `utility_id`, `valuta_id`,
`modalita_pagamento_id`, `termine_pagamento_id`, `fatturazione_trigger`,
`agente_soggetto_ruolo_id`, `data`, `meta`.

### Delete `DELETE /api/v1/vendite/ordini/<id>/`

Hard-delete (abbandono bozza), solo `DRAFT`. Le righe/componenti hanno
ON DELETE CASCADE; il trigger DB blocca se collegato a DDT.

### Conferma `POST /api/v1/vendite/ordini/<id>/conferma/`

`DRAFT -> CONFERMATO`. Guard: origine DRAFT + almeno una riga
(`E_ORD_NESSUNA_RIGA`). La transizione è validata dal trigger DB.

### Push singolo a commessa `POST /api/v1/vendite/ordini/<id>/push/`

Push del singolo ordine `CONFERMATO` via `fn_list_ordini_da_pushare(…, p_ordine_id)`
+ orchestratore (`pr_run_commesse_push_one`, sorgente `ORDINE_VENDITA`) →
`attivita_fatturabili`. Guard: stato `CONFERMATO` + righe eleggibili.

### Righe

| Metodo / Path | Scopo |
| --- | --- |
| `GET /<id>/righe/` | Lista righe attive (decodifiche articolo/uom/iva + `importo_riga` + `is_composito_caso_a`) |
| `POST /<id>/righe/` | Aggiunge una riga (solo DRAFT). `riga_nr` autoassegnato. Pricing auto-fill via `PricingService` se prezzo assente e articolo non composito; per articolo composito init componenti BoM |
| `PATCH /<id>/righe/<riga_id>/` | Aggiorna riga (solo DRAFT). `request.data` |
| `DELETE /<id>/righe/<riga_id>/` | Hard-delete riga (solo DRAFT) |

Payload riga (create): `articolo_id` (obbligatorio), `descrizione`, `quantita`,
`qta_operativa`, `uom_operativa_id`, `factor_to_base`, `prezzo_unitario`,
`sconto_perc`, `iva_id`, `meta`. La doppia quantità operativa/base segue il
pattern standard (input con priorità all'operativa; `quantita` base derivata dal
trigger `trgfn_qta_from_operativa`). I totali testata sono ricalcolati da trigger DB.

### Componenti BoM (CASO A)

| Metodo / Path | Scopo |
| --- | --- |
| `POST /<id>/righe/preview-componenti/` | Preview read-only dei componenti BoM (pre-save). Payload: `articolo_id`, `uom_operativa_id`, `quantita` |
| `GET /<id>/righe/<riga_id>/componenti/` | Lista componenti persistiti (`?solo_attivi=true`) |
| `PATCH /<id>/righe/<riga_id>/componenti/<componente_id>/` | Aggiorna componente (solo DRAFT): `prezzo_unitario`, `attivo`, `esposto_in_fattura`, `meta` |
| `DELETE /<id>/righe/<riga_id>/componenti/<componente_id>/` | Soft-delete componente (`attivo=FALSE`, solo DRAFT) |

### Note `GET/POST /<id>/note/` + `GET/PATCH/DELETE /<id>/note/<note_id>/`

Note partizionate (`vendite.note_ordini`, `target_tipo='ORDINE'`) via building
block `PartitionedNoteRepository` + `make_note_views`. Contratto identico alle
note preventivo/contratto/offerta (testata + riga via `target_riga_id`).

## Output

Envelope standard `success_response` (`{"data": …, "meta": {request_id}}`).
Liste: `paginated_envelope` (`count`, `page`, `page_size`, `total_pages`,
`results`).

## Regole

- **Modifiche** (testata/righe/componenti) ammesse **solo in `DRAFT`**
  (`E_ORD_STATO_TRANSIZIONE`).
- **Pricing** sempre via `PricingService.resolve_prezzo` (BB condiviso, mai query
  dirette su listini). Il gate prezzi L2/L3 stile contratti è una decisione di
  dominio **aperta** (analisi §8.bis): lo scheletro usa il pricing stile
  preventivo (resolve + prezzo dal caller).
- **Scope emittente**: la vista è `security_invoker=on` (RLS attiva sulla tabella
  base); il filtro applicativo `fn_get_emittenti_scope_pk_ids` si somma
  (defense-in-depth). Un detail fuori scope torna **404**.
- **Numero**: generato dal trigger all'INSERT (mai NULL), immutabile dopo.

## Codici errore

| Codice | HTTP | Quando |
| --- | --- | --- |
| `E_ORD_NOT_FOUND` | 404 | ordine/riga/componente inesistente o fuori scope |
| `E_ORD_VALIDAZIONE` | 400 | payload non valido (cliente mancante, campi vuoti, ecc.) |
| `E_ORD_STATO_TRANSIZIONE` | 409 | operazione non ammessa nello stato corrente |
| `E_ORD_NESSUNA_RIGA` | 409 | conferma/push senza righe eleggibili |
| `E_VENDITE_DUPLICATO` / `E_VENDITE_FK` | 409 / 400 | violazione UNIQUE/FK (via `map_integrity_error`) |
| `E_ORDINE_*` | varia | codici sollevati dai trigger DB (estratti via regex) |
| `E_UI_EXPORT_FORMAT_INVALID` / `E_UI_EXPORT_LIMIT_EXCEEDED` | 400 / 422 | export |

Tutti registrati in `error_policies.py` (gli `E_VENDITE_*` e gli `E_UI_*`
preesistono; gli `E_ORD_*` aggiunti con questo scheletro).

## Dipendenze DB

- Vista lista: `vendite.vw_ordini_lista` (`20260603-14`, `security_invoker=on`,
  espone agente + origine polimorfa).
- Catalogo lista: `ui.lista_definizione` id=7 `vendite.ordini` + colonne/preset
  (`20260603-15` + seed).
- Funzioni: `fn_ordine_riga_componenti_init` / `_preview` (BoM),
  `fn_list_ordini_da_pushare(…, p_ordine_id)` (push singolo).
- Trigger testata: `trgfn_ordini_gen_codice`, `trgfn_ordini_normalize`,
  `trgfn_ordini_default_emittente`, `trgfn_ordini_guard_emittente_ba`,
  `trgfn_ordini_guard_transizione_approvazione`, lock numero, immutabilità
  `canale_origine`.
- Modello esteso: `agente_soggetto_ruolo_id` (`20260603-12`),
  `documento_origine_tipo`/`_id` (`20260603-13`), fix `chk_ordini_v_r_qta_pos`
  → `quantita > 0` (`20260603-11`).
- RLS: 3 policy (`rls_ordini_ef_whitelist` / `_cliente_ownership` / `_shop`).

## Riferimenti

- Analisi BE/FE: [analisi-ordini-vendita.md](../../../dev/work-in-progress/analisi-ordini-vendita.md)
- Brief DB: [db-brief-ordini-vendita.md](../../../dev/work-done/db-brief-ordini-vendita.md)
- Tabella testata: [vendite.ordini](../../../dbzero/vendite/manual/ordini.md)
- Linee guida API: [api.md](../../../dev/api.md)
