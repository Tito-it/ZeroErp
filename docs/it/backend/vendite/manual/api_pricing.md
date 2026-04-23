# API Pricing v5 (resolver + limiti L2)

## Scopo

Endpoint diagnostici e di lookup per il sistema pricing v5. Espongono il
resolver a 3 stadi (PROMO → CONTRATTO → CATEGORIA) e i limiti L2 di
variazione prezzo configurati per l'utente corrente.

Riferimento concettuale:
[sviluppo-listini-v5.md](/dev/work-in-progress/sviluppo-listini-v5) §7
(resolver) e §14.5 (Sprint D autorizzazioni L2).

## Contesto

- Il **resolver** (`POST /pricing/resolve/`) è invocato dal FE per pre-compilare
  il prezzo riga preventivo all'apertura del drawer e dai tool diagnostici di
  smoke test. Pura lettura, zero side-effect.
- I **limiti L2** (`GET /pricing/limiti-utente/`) sono usati dal FE per
  mostrare hint "sconto max ammesso: X%" sotto il campo prezzo riga senza
  round-trip a ogni modifica (composable `useLimitiPricing` cache modulo).

## Endpoint

### 1. Resolve prezzo (resolver 3 stadi)

- Metodo: `POST`
- Path: `/api/v1/vendite/pricing/resolve/`
- Auth: `vendite` livello LETTURA
- Body JSON:
  - `articolo_id` (uuid string, **obbligatorio**)
  - `uom_id` (int, **obbligatorio**)
  - `data_riferimento` (date ISO, **obbligatorio**)
  - `ba_id` (int, **obbligatorio**) — billing account
  - `utility_id` (int, **obbligatorio**)
  - `classe_utenza_id` (int, opzionale)
  - `emittente_soggetto_ruolo_id` (int, opzionale) — override esplicito; se assente, derivato dal JWT operatore
- Output `200`: oggetto risolto con `prezzo_finale`, `prezzo_base_snapshot`, `tipo_variazione_applicata`, `valore_variazione_applicata`, `origine` (PROMO/CONTRATTO_OVERRIDE/CONTRATTO_LISTINO/CATEGORIA), `listino_id`, `listino_versione_id`, `listino_riga_id`, `contratto_id`, `promo_id`, `categoria_cliente_listino_id`, `categoria_cliente_id_snapshot`, `classe_utenza_id_snapshot`
- Errori applicativi sollevati dal resolver DB: `E_PREZZO_LISTINO_NON_TROVATO`, `E_CATEGORIA_LISTINO_NON_MAPPATA`, `E_PREZZO_LISTINO_RIGA_NON_TROVATA`, `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C` (tutti 403/404 con detail dal DB), fallback `E_VENDITE_PRICING_FAILED` (500)

---

### 2. Limiti utente (L2 sconto/maggiorazione)

- Metodo: `GET`
- Path: `/api/v1/vendite/pricing/limiti-utente/`
- Auth: `vendite` livello LETTURA
- Output `200`:

```json
{
  "data": {
    "max_sconto_pct": "10.00",
    "max_maggiorazione_pct": "5.00"
  },
  "meta": { "request_id": "..." }
}
```

- Risoluzione cascata: `user → group → emittente → default` via `ParameterService.get_defaults` con codici `VENDITE_MAX_SCONTO_PCT` + `VENDITE_MAX_MAGGIORAZIONE_PCT`. Default 0 = nessuna variazione ammessa (admin abilita override per ruolo/utente).
- Singolo round-trip DB (entrambi i parametri risolti in una query)
- Valori serializzati come stringa (envelope stabile); il FE converte in Number per interpolazione hint

---

## Pattern d'uso FE

### Auto-fill prezzo riga preventivo

L'endpoint `8b. Suggerisci prezzo riga` (vedi `api_preventivi.md`) wrappa
internamente il resolver derivando contesto da BA+utility+data della testata
preventivo. È il pattern preferito; `/pricing/resolve/` è per diagnostica.

### Hint L2 nel drawer riga

Il FE chiama `GET /pricing/limiti-utente/` una sola volta per sessione (cache
modulo-level via `useLimitiPricing` in `frontend/src/vendite/composables/`).
I valori restano disponibili in tutti i drawer che mostrano l'hint
"sconto/maggiorazione max ammesso". Refresh esplicito necessario solo dopo
cambio override admin.

## Riferimenti

- Service backend: [pricing_service.md](pricing_service.md)
- Catalogo Building Block: [BoMComponentExpander, PricingService](../../../dev/backend/catalogo-building-block-backend) sezione "Vendite — Pricing v5"
- L1 override autorizzato: `prezzo_override_manuale` (azioni_processo id 9)
- L2 limite: parametri `VENDITE_MAX_SCONTO_PCT` / `VENDITE_MAX_MAGGIORAZIONE_PCT`
- L3 workflow approvazione: vedi [api_approvazioni_prezzo.md](api_approvazioni_prezzo.md) (Sprint E)
