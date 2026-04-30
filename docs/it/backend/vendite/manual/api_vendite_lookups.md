# API Vendite Lookups (enum statici di dominio)

## Scopo

Endpoint **lookup statici** per gli enum di dominio vendite (Fase 2 refactor
frontend vendite): tipi variazione (contratto/promo), ambiti contratto,
modalità pricing contratto. Eliminano i magic string cablati nei drawer
Vue (`'PERCENTUALE'`, `'COMMODITY'`, `'A'`, ecc.) e li espongono come
risorse REST con cache modulo-level lato FE (`useGlobalLookup`).

Riferimento concettuale:
[analisi-refactor.frontend-vendite.md §A7](/dev/work-done/analisi-refactor.frontend-vendite#a7-enum-tipo_variazione-promo-e-contrattilistini-da-lookup-statico).

## Contesto

I valori sono **enum tecnici Python**, non tabelle DB di config. La single
source of truth è `apps/vendite/services/vendite_lookups_service.py`:

- `_TIPI_VARIAZIONE_CONTRATTO` — `PERCENTUALE`, `VALORE_FISSO`
- `_TIPI_VARIAZIONE_PROMO` — `PERCENTUALE`, `VALORE_FISSO`, `PREZZO_FISSO`
- `_AMBITI_CONTRATTO` — `COMMODITY`, `COMMERCIO`
- `_MODALITA_PRICING_CONTRATTO` — `A`, `B`, `C`

I valori sono allineati ai CHECK constraint DB di `vendite.contratti`,
`vendite.promo_articoli`. Aggiungere/cambiare un codice senza propagarlo
al DB rompe il salvataggio: i lookup sono solo UI.

Pattern modello: `catalogo.api.views.ApiUomRoundingModesLookup` /
`fn_list_uom_rounding_modes`.

## Endpoints

Tutti i 4 endpoint condividono la stessa shape:

- Metodo: `GET`
- Auth: `vendite` LETTURA (JWT obbligatorio)
- Query params: nessuno
- Output `200`:

```json
{
  "data": [
    {"codice": "PERCENTUALE", "descrizione": "Percentuale (es. -10%)", "ordering": 1},
    {"codice": "VALORE_FISSO", "descrizione": "Valore fisso (es. -2,50 €)", "ordering": 2}
  ],
  "meta": { "request_id": "uuid-..." }
}
```

| Path | Codici esposti | Consumer FE |
| --- | --- | --- |
| `/api/v1/vendite/lookup/tipi-variazione-contratto/` | `PERCENTUALE`, `VALORE_FISSO` | `TipoVariazioneSelect scope="contratto"` (in `ContrattoDrawer.vue`) |
| `/api/v1/vendite/lookup/tipi-variazione-promo/` | `PERCENTUALE`, `VALORE_FISSO`, `PREZZO_FISSO` | `TipoVariazioneSelect scope="promo"` (in `PromoArticoloDrawer.vue`) |
| `/api/v1/vendite/lookup/ambiti-contratto/` | `COMMODITY`, `COMMERCIO` | `AmbitoContrattoSelect` (in `ContrattoDrawer.vue`) |
| `/api/v1/vendite/lookup/modalita-pricing-contratto/` | `A`, `B`, `C` | `ContrattoDrawer.vue` direct (`SelectButton`) |

### Nota PREZZO_FISSO

`PREZZO_FISSO` è ammesso **solo** per le promo articoli (resolver STADIO 0).
Gli endpoint contratto / listini non lo espongono perché i CHECK constraint
DB lo rifiutano in quei contesti. Aggiungerlo a `_TIPI_VARIAZIONE_CONTRATTO`
romperebbe la coerenza: il test `test_tipi_variazione_promo_coverage` blocca
il drift in CI.

### Nota Modalita Pricing A/B/C

La modalità pricing **non è una colonna DB** ma un'astrazione UI derivata da
`listino_id` + `tipo_variazione_globale`:

- `A` — listino vincolante + variazione globale (PERCENTUALE/VALORE_FISSO)
- `B` — listino + override righe (no variazione globale)
- `C` — interamente negoziato (no listino)

Il lookup espone i tre codici come single source of truth lato API, ma la
**derivazione** dal contratto resta in `ContrattoDrawer.deriveModalita`
(FE-only). Sviluppo futuro: BE espone `pricing_modalita` direttamente nel
detail (vedi WIP §A3).

## Errori

Gli endpoint non sollevano errori di dominio (sono read-only su strutture
in memoria). Errori possibili:

| HTTP | Codice | Quando |
| --- | --- | --- |
| 401 | — | JWT mancante o invalido |
| 403 | `E_PERMESSO_NEGATO` | Utente con `vendite = BLOCCATO` |
| 429 | — | Rate limit (improbabile su endpoint stabili) |

## Test

| Tipo | File | Cosa verifica |
| --- | --- | --- |
| Service | `apps/vendite/tests/services/test_vendite_lookups_service.py` | Coverage `lookup.codici == service.whitelist` (CI guard contro drift) |
| API | `apps/vendite/tests/api/test_lookups_api.py` | Smoke 200 per i 4 endpoint, JWT mocked, codici minimi presenti, 401 senza auth |

## Riferimenti

- Backend service: `apps/vendite/services/vendite_lookups_service.py`
- Backend views: `apps/vendite/api/views_lookups.py`
- Backend routes: `apps/vendite/api/urls_v1.py` (`# --- Lookup statici ---`)
- Frontend client: `frontend/src/vendite/api/lookup.js`
- Frontend wrapper: `frontend/src/vendite/components/{TipoVariazioneSelect,AmbitoContrattoSelect}.vue`
- Catalogo BB backend: vedi `vendite_lookups_service` + `Api*Lookup`
- Catalogo BB frontend: vedi `lookupTipiVariazione*`, `TipoVariazioneSelect`, `AmbitoContrattoSelect`
