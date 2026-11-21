# API run_commesse_push (Django)

> **Ultimo aggiornamento**: 21 novembre 2026

## Scopo

Esporre via HTTP l'avvio dell'orchestratore push commesse, che sincronizza documenti sorgente
(preventivi, ordini, contratti, DDT, consumi) verso `commesse` e `commesse_attivita`.

## Contesto

Endpoint applicativo che invoca il servizio Python `pr_run_commesse_push`
(`apps.vendite.services.commesse_service`), il quale istanzia `CommessaPushOrchestrator`
con gli handler sorgente attivi (letti dinamicamente da `config.sorgenti`) e ne esegue il metodo `run()`.

View: `ApiRunCommessePush` `ApiRunCommessePush` (`apps.vendite.api.views`).

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/vendite/commesse/push/run/`
- Header richiesto: `Idempotency-Key`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Permesso: area `vendite` + `post_permission = "run_commesse_push"` (senza → `403 E_PERMISSION_DENIED`)
- Body JSON (tutti i campi opzionali):
  - `source_types` (list[string]) — filtro sorgenti da processare (es. `["PREVENTIVO", "ORDINE_VENDITA"]`). Se omesso processa tutte le sorgenti attive in `config.sorgenti`.
  - `dry_run` (bool) — `true` = simula senza effetti reali (default `false`)
- L'utente JWT viene propagato automaticamente al DB via middleware `JwtAuditMiddleware` → GUC `app.jwt_user`, registrato nei campi audit `user_insert`/`user_update`.

## Output

- `200`: esecuzione completata (o skippata per lock occupato)

```json
{
  "data": {
    "stato": "COMPLETATO",
    "dry_run": false,
    "push_log_id": 10,
    "durata_ms": 150,
    "handlers": [
      {
        "handler_name": "HandlerPreventivi",
        "created": 2,
        "updated": 0,
        "skipped": 0,
        "errors": []
      }
    ],
    "commesse_ids": [812, 813],
    "emittibilita_errors": [],
    "emittibilita_tipo_doc_mancante": []
  },
  "meta": { ... }
}
```

- `commesse_ids`: commesse toccate dal giro.
- `emittibilita_errors`: un messaggio per commessa (`commessa_id=<id>: <errore>`) il cui passaggio a emittibile è fallito. Best-effort per commessa (una rotta non blocca le altre); ognuna lascia anche un evento `EMITTIBILITA_FALLITA` sul giornale della commessa. Vuoto in `dry_run`.
- `emittibilita_tipo_doc_mancante`: sottoinsieme degli id falliti per `tipo_doc_fiscale_id` mancante sulle righe.
- `200` con `stato: "SKIPPED"`: advisory lock occupato, nessuna esecuzione.
- `400`: payload non valido o errore applicativo (`E_COMMESSA_VALIDATION`).

## Regole

- Implementa il pattern standard core `handle_post_json(...)`.
- Endpoint write protetto con obbligo `Idempotency-Key`.
- Endpoint v1 richiede JWT.
- Concorrenza gestita via `pg_try_advisory_lock(hashtext('commesse_push_orchestrator'))`:
  lock occupato → `stato: "SKIPPED"` (HTTP 200, non errore).
- `source_types` validati contro le sorgenti attive in `config.sorgenti` (`scope = 'PUSH_COMMESSA'`, `attivo = true`). Codici non riconosciuti o inattivi restituiscono `E_COMMESSA_VALIDATION` con l'elenco delle sorgenti attive.
- La lista delle sorgenti processabili è dinamica: attivazione/disattivazione gestita in `config.sorgenti` senza deploy backend.
- Il risultato per handler include contatori `created`, `updated`, `skipped` e lista `errors`.

## Comportamento snapshot pricing v5 + fan-out compositi (2026-06)

Il push, oltre a creare commessa e righe, arricchisce e materializza:

- **La provenienza del prezzo** (dal 2026-11-14, brief della provenienza del prezzo, K-1 e
  K-2) — per ogni riga il push copia su `commesse_attivita` la provenienza della riga del
  documento, **così com'è**: `origine_prezzo`, `listino_versione_id`, `listino_riga_id`,
  `prezzo_base_snapshot`, la variazione applicata, `promo_id`, `contratto_id`,
  `categoria_cliente_id_snapshot`, `classe_utenza_id_snapshot`. Le restituiscono tutti i
  lister `fn_list_*_da_pushare` (obbligatorie in `_PUSHABLE_SHARED_COLS`; i consumi vuote,
  il loro prezzo lo dà il listino più tardi). Caratteristiche:
  - **niente ricostruzione**: il push non chiede al resolver da dove *verrebbe* oggi il
    prezzo (`_resolve_pricing_audit`, ritirato); cita la riga di listino solo se il prezzo
    è venuto davvero da lì;
  - **un elenco solo di origini** (`vendite.fn_origine_prezzo_ammessa`): `LISTINO_BUNDLE` e
    `COMPONENTI` entrano in commessa, niente più normalizzazione a `NULL`;
  - i **componenti BoM** portano la **loro** provenienza (colonne `prov_*` del loader),
    non quella del padre e non più dal `meta`;
  - **propagazione a valle**: la pull `fn_emit_attivita_fatturabili_da_commessa` copia la
    provenienza su `attivita_fatturabili`, fino al livello di emissione.
- **Fan-out compositi (modello unico)** — un articolo composito entra in commessa come
  N righe componente, leggendo i componenti negoziati dalla rispettiva tabella
  `*_righe_componenti`. Vale ora per **tutte** le sorgenti documento (preventivi,
  ordini, contratti, DDT) tramite lo stesso `BoMComponentExpander` + loader snapshot.
- **Consumi utility (gas/energia/acqua/…)**: la decomposizione tariffaria
  (energia/trasporto/oneri/…) è **rimandata** (decisione 2026-06-16); un consumo entra
  in commessa come **riga singola** (nessun fan-out).
- **Punto d'innesto fasi di lavorazione**: `BaseSourceHandler._pre_commessa_hook(row)`
  (default identity) è il gancio dove una futura fase di lavorazione precederebbe la
  creazione commessa; oggi nessun effetto.

> Nessuna modifica al **contratto HTTP** (input/output invariati): cambia solo il
> contenuto materializzato a valle.

## Dipendenze DB

- `vendite.fn_list_preventivi_da_pushare`
- `vendite.fn_list_ordini_da_pushare`
- `vendite.fn_list_contratti_da_pushare`
- `vendite.fn_list_ddt_da_pushare`
- `vendite.fn_list_consumi_da_pushare`
- `vendite.fn_get_or_create_commessa`
- `vendite.fn_upsert_commessa_attivita` (riceve le 8 colonne snapshot audit)
- `vendite.fn_resolve_prezzo_listino_v2` (via `PricingService`, per l'audit snapshot v5)
- `vendite.commesse_push_log` (log esecuzione)
- Advisory lock: `pg_try_advisory_lock(hashtext('commesse_push_orchestrator'))`
- A valle (pull, non chiamata dal push): `vendite.fn_emit_attivita_fatturabili_da_commessa`
  propaga le 8 colonne audit su `attivita_fatturabili` (changeset `20260616-01`).
