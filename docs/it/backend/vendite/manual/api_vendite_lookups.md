# API Vendite Lookups (enum statici di dominio)

## Scopo

Endpoint **lookup statici** per gli enum di dominio vendite (Fase 2 refactor
frontend vendite): tipi variazione (contratto/promo), ambiti contratto, più
il lookup dinamico dei listini selezionabili. Eliminano i magic string cablati
nei drawer Vue (`'PERCENTUALE'`, `'COMMODITY'`, ecc.) e li espongono come
risorse REST con cache modulo-level lato FE (`useGlobalLookup`).

Riferimento concettuale:
[analisi-refactor.frontend-vendite.md §A7](/dev/work-done/analisi-refactor.frontend-vendite#a7-enum-tipo_variazione-promo-e-contrattilistini-da-lookup-statico).

## Contesto

I valori sono **enum tecnici Python**, non tabelle DB di config. La single
source of truth è `apps/vendite/services/vendite_lookups_service.py`:

- `_TIPI_VARIAZIONE_CONTRATTO` — `PERCENTUALE` (solo: la variazione **globale**
  della testata contratto è solo percentuale, decisione 2026-05-18;
  `VALORE_FISSO` resta ammesso unicamente come override di singola riga)
- `_TIPI_VARIAZIONE_PROMO` — `PERCENTUALE`, `VALORE_FISSO`, `PREZZO_FISSO`
- `_AMBITI_CONTRATTO` — `COMMODITY`, `COMMERCIO`

I valori sono allineati ai CHECK constraint DB di `vendite.contratti`,
`vendite.promo_articoli`. Aggiungere/cambiare un codice senza propagarlo
al DB rompe il salvataggio: i lookup sono solo UI.

Pattern modello: `catalogo.api.views.ApiUomRoundingModesLookup` /
`fn_list_uom_rounding_modes`.

## Endpoints

I tre enum statici condividono la stessa shape:

- Metodo: `GET`
- Auth: `vendite` LETTURA (JWT obbligatorio)
- Query params: nessuno
- Output `200`:

```json
{
  "data": [
    {"codice": "PERCENTUALE", "descrizione": "Percentuale (es. -10%)", "ordering": 1}
  ],
  "meta": { "request_id": "uuid-..." }
}
```

> ⛔ **`data` E' UNA LISTA NUDA QUI, ED E' UN'ECCEZIONE — non copiarla.**
> La forma normale di un lookup e' `{"data": {"results": [...]}}`: la assumono
> **di default** i due composable del frontend (`useLookup`, `useGlobalLookup`),
> che trasformano ogni risposta con `r.data.data.results`.
>
> ⚠️ Su una lista nuda quella espressione vale `undefined`, e il difetto **non
> da' nessun errore**: il `ref` delle opzioni passa da `[]` a `undefined`, il
> primo `.map()` solleva, Vue svuota il sottoalbero e la schermata resta
> **bianca** — con il backend a `200`, i log puliti e la suite verde. E'
> successo davvero il 2026-09-08 sul lookup delle famiglie documento, e il
> drawer dei registri di numerazione si apriva vuoto.
>
> ⇒ Questi tre endpoint restano com'erano per ragioni storiche, e **chi li
> consuma deve passare il transform esplicito**:
> `:transform="(r) => r.data.data"` — tutti e 6 i call site lo fanno
> (verificato il 2026-09-08). **Un endpoint nuovo usa `{"results": [...]}`** e
> non ha bisogno di nessun transform da ricordarsi.
> Regola completa: [api.md §Lookup](/dev/api#lookup--due-pattern-una-regola).

| Path | Codici esposti | Consumer FE |
| --- | --- | --- |
| `/api/v1/vendite/lookup/tipi-variazione-contratto/` | `PERCENTUALE` | `TipoVariazioneSelect scope="contratto"` (in `ContrattoDrawer.vue`) |
| `/api/v1/vendite/lookup/tipi-variazione-promo/` | `PERCENTUALE`, `VALORE_FISSO`, `PREZZO_FISSO` | `TipoVariazioneSelect scope="promo"` (in `PromoArticoloDrawer.vue`) |
| `/api/v1/vendite/lookup/ambiti-contratto/` | `COMMODITY`, `COMMERCIO` | `AmbitoContrattoSelect` (in `ContrattoDrawer.vue`) |

⛔ **`/api/v1/vendite/lookup/modalita-pricing-contratto/` (`A`/`B`/`C`) non
esiste piu'**, rimosso col refactor modalita del 2026-05-15 e verificato sul
codice il 2026-08-19: nessuna rotta lo serve e `vendite/api/lookup.js` lo
dichiara morto in un commento. Nel modello unificato la «modalita» **non e' piu'
una scelta dell'operatore ma una forma derivata dai dati**: `listino_id`
valorizzato (con o senza variazione globale) = *con listino*, `listino_id` NULL =
*interamente negoziato*. Il `SelectButton` A/B/C nel `ContrattoDrawer.vue` e'
stato sostituito da due campi opzionali (Listino + Variazione globale) e da un
badge «forma derivata» che mostra l'esito dopo il salvataggio.

### I listini che un documento può scegliere `GET /api/v1/vendite/lookup/listini-selezionabili/`

Dal 2026-10-08 (F-2 di brief-db-offerta-emissione-ed-erogazione): l'unico lookup
**dinamico** del modulo, la tendina del listino di **contratto e offerta**.
Prende il posto di `lookup/listini-selezionabili-contratto/`, che proponeva ogni
listino con «almeno una versione ATTIVA», di qualunque utility (filtro ritirato
col D.4.3: in bozza un listino senza versione in vigore si sceglie, lo rifiutano
attivazione ed emissione).

Auth: area `vendite` LETTURA **e** permesso modello `("vendite", "listino")`
(`model_permission`): senza, `403`.

| Query param | Tipo | Note |
| --- | --- | --- |
| `utility_id` | int | La utility del **form**. Assente: nessun listino |
| `emittente_fiscale_id` | int | L'emittente fiscale del **form** (id di `anagrafiche.emittenti_fiscali`). Assente: nessun listino |

Sui valori del form e non sull'id del documento, perché in creazione il
documento non esiste. Un valore non numerico → 400 `E_VALIDATION_INPUT`.

```json
{ "data": { "results": [ { "id": 100, "codice": "LST-GAS-2026", "descrizione": "Gas 2026" } ] } }
```

⭐ Envelope **normale** dei lookup (`{"results": [...]}`), non l'eccezione dei tre
enum statici sopra. ⛔ Il backend la trasporta, non la deduce: è
`vendite.fn_listini_selezionabili(utility, emittente_fiscale_id)`, i listini
attivi su cui `script.fn_check_listino_documento` non ha motivi — lo stesso
predicato del guard che al salvataggio rifiuta un listino di un'altra utility
(`E_DOC_LISTINO_UTILITY_DIVERSA`) o di un'altra azienda
(`E_DOC_LISTINO_EMITTENTE_DIVERSO`). La tendina non propone ciò che il DB
rifiuterebbe. Sotto RLS: chi agisce vede i listini del suo perimetro.

Consumer FE: `ListinoDocumentoSelect` (in `ContrattoDrawer.vue` e
`OffertaDrawer.vue`), che si ricarica al cambio di utility o emittente e tiene
fra le opzioni il listino già scritto sul documento.

### Nota PREZZO_FISSO

`PREZZO_FISSO` è ammesso **solo** per le promo articoli (resolver STADIO 0).
Gli endpoint contratto / listini non lo espongono perché i CHECK constraint
DB lo rifiutano in quei contesti. Aggiungerlo a `_TIPI_VARIAZIONE_CONTRATTO`
romperebbe la coerenza: il test `test_tipi_variazione_promo_coverage` blocca
il drift in CI.

## Errori

Gli endpoint non sollevano errori di dominio (gli enum sono read-only su
strutture in memoria; i listini sono una lettura). Errori possibili:

| HTTP | Codice | Quando |
| --- | --- | --- |
| 400 | `E_VALIDATION_INPUT` | `utility_id` o `emittente_fiscale_id` non numerico (solo listini sceglibili) |
| 401 | — | JWT mancante o invalido |
| 403 | `E_PERMESSO_NEGATO` | Utente con `vendite = BLOCCATO`; sui listini selezionabili anche senza il permesso modello `("vendite", "listino")` |
| 429 | — | Rate limit (improbabile su endpoint stabili) |

## Test

| Tipo | File | Cosa verifica |
| --- | --- | --- |
| Service | `apps/vendite/tests/services/test_vendite_lookups_service.py` | Coverage `lookup.codici == service.whitelist` (CI guard contro drift) |
| API | `apps/vendite/tests/api/test_lookups_api.py` | Smoke 200 sugli enum statici, JWT mocked, codici minimi presenti, 401 senza auth; listini sceglibili: envelope `results`, parametri passati al service, assenti → `None`, non numerici → 400 |
| DB | `apps/vendite/tests/db/test_listini_selezionabili_db.py` | Binding reale di `vendite.fn_listini_selezionabili` sul mondo costruito (ordine dei parametri provato per mutazione) e trasporto del rifiuto 1222 col campo `listino_id` dai PATCH di contratto e offerta |

## Riferimenti

- Backend service: `apps/vendite/services/vendite_lookups_service.py`
- Backend views: `apps/vendite/api/views_lookups.py`
- Backend routes: `apps/vendite/api/urls_v1.py` (`# --- Lookup statici ---`)
- Frontend client: `frontend/src/vendite/api/lookup.js`
- Frontend wrapper: `frontend/src/vendite/components/{TipoVariazioneSelect,AmbitoContrattoSelect,ListinoDocumentoSelect}.vue`
- Catalogo BB backend: vedi `vendite_lookups_service` + `Api*Lookup`
- Catalogo BB frontend: vedi `lookupTipiVariazione*`, `TipoVariazioneSelect`, `AmbitoContrattoSelect`
