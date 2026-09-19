# API Lookup Risorse Umane — il picker delle persone interne

## Scopo

Restituire le **risorse umane attive** — id, nome della persona, qualifica e
reparto — per i campi in cui un documento di dominio assegna una **persona
interna**. Primo consumatore: il campo «responsabile» del drawer commessa
(`responsabile_risorsa_umana_id`, Blocco C di
`brief-db-modifiche-certe-ciclo-vendita-e-articolo`).

## Contesto

`anagrafiche.risorse_umane` **non ha `codice` né `descrizione`**: il lookup
generico (`GET /core/lookup/codici/?rel=…`) non la può servire, e l'unico altro
elenco di persone in esercizio — `GET /pratiche/operatori/` — è **per reparto**
e sta sull'area `pratiche`. Serviva un lookup dedicato, ed è la forma prevista
da [api.md §Lookup dedicato](/dev/api): JOIN e campi che non si riducono a
`id, codice, descrizione`.

⭐ **Legge la vista modello `anagrafiche.vw_risorse_umane_dettaglio`** (risorsa,
soggetto, qualifica e unità organizzativa) e **non** ricompone la catena
`risorse_umane → soggetti_ruoli → soggetti` nel repository: il nome della
persona è la `ragione_sociale_completa` del soggetto, e il modo di arrivarci
vive nella vista. Il dettaglio commessa (`responsabile_display`) legge la
**stessa** vista con un `LEFT JOIN`, così picker e dettaglio chiamano la
persona nello stesso modo per costruzione.

⚠️ La vista legge il soggetto da `risorse_umane.soggetto_id`, che
`trgfn_risorse_umane_guard_ruolo` tiene uguale a quello del `soggetto_ruolo`:
è la stessa persona senza passare da `soggetti_ruoli`.

## Endpoint

```http
GET /api/v1/anagrafiche/risorse-umane/lookup/
GET /api/v1/anagrafiche/risorse-umane/lookup/?search=bia
```

View: `RisorseUmaneLookupView` (`apps.anagrafiche.api.views_risorse_umane`),
`DomainAPIView` con **`skip_area_check = True`** (pattern «lookup top-level
liberato» del catalogo BB, come `BillingAccountLookupView`): lo consuma il
drawer commessa di `vendite`, e chiuderlo sull'area `anagrafiche` spegnerebbe
il campo per chi non ha quell'area, in silenzio. Restano JWT e throttling
(`is_search_endpoint = True`). Sola lettura di dati non sensibili.

## Input

| Parametro | Tipo | Obbligatorio | Note |
| --- | --- | --- | --- |
| `search` | string | no | ricerca `ILIKE` sul nome della persona (`ragione_sociale_completa`). **Min 3 caratteri**: più corto → `400` `E_SEARCH_VALIDATION`. Assente o vuoto = tutte le attive |

Nessuna paginazione: come gli altri lookup dedicati, la lista si chiede per intero.

## Output

Envelope standard `{"data": {"results": [...]}}`, ordinato per nome e poi per
id:

```json
{
  "data": {
    "results": [
      {
        "id": 7,
        "display": "Bianchi Anna",
        "attivo": true,
        "qualifica_descrizione": "Impiegato tecnico",
        "unita_organizzativa_descrizione": "Ufficio tecnico"
      }
    ]
  }
}
```

| Campo | Da dove |
| --- | --- |
| `id` | `risorse_umane.id` (`risorsa_umana_id` nella vista) |
| `display` | `ragione_sociale_completa` del soggetto |
| `attivo` | `risorse_umane.attivo` — nell'elenco è sempre `true`, serve al lettore per id (sotto) |
| `qualifica_descrizione`, `unita_organizzativa_descrizione` | le due decodifiche, per distinguere due omonimi |

## Regole

- **Solo le attive**: il lookup elenca le risorse con `attivo = true`. Una
  persona disattivata che è già responsabile di una commessa la aggiunge il
  drawer come voce **non selezionabile**, col nome che arriva dal dettaglio
  (`responsabile_display`), così la select non mostra un vuoto al posto del
  nome. ⚠️ «Assente dalle attive» si dice solo a lookup **caricato**: mentre
  carica, `items` è vuoto e ogni responsabile sembrerebbe disattivato.
- **La stessa query per l'elenco e per il singolo id**:
  `AnagraficheService.get_risorsa_umana_lookup(id)` (repository
  `_risorse_umane_lookup`) è la forma con cui un service di dominio verifica
  «la persona è attiva» **prima** dell'`UPDATE`. ⚠️ A DB lo rifiuterebbe comunque
  il require sul figlio nato da `ci_apply`
  (`trg_commesse_a10_risorse_umane_require_attivo_ins_upd`) — ma con
  `E_ATTIVO_REQUIRE`, di classe `TECNICO` (500), che parla di trigger: per
  l'operatore è un dato sbagliato, non un guasto. Il service risponde `400` col
  campo; il guard DB resta l'autorità.
- Il **rovescio** sta sul padre: una persona responsabile di una commessa —
  anche chiusa, perché `commesse` non ha `attivo` — **non si disattiva**
  (`trg_risorse_umane_a10_commesse_block_deact_upd`, generato dal framework
  ATTIVO). È il quarto block della sua specie su `risorse_umane`, accanto a
  `pratiche`, `flussi` e `competenze_flussi`.

## Dipendenze DB

- `anagrafiche.vw_risorse_umane_dettaglio` — la vista modello (risorsa,
  soggetto, qualifica, unità organizzativa)
- `anagrafiche.risorse_umane` — `attivo`, il require e il block ATTIVO
  generati da `ci_apply`

## Riferimenti

- Repository: `apps/anagrafiche/db/anagrafiche_repository.py` —
  `list_risorse_umane_lookup`, `get_risorsa_umana_lookup`, `_risorse_umane_lookup`
- Service: `apps/anagrafiche/services/anagrafiche_service.py`
- Test: `apps/anagrafiche/tests/api/test_risorse_umane_lookup_api.py` (rotta,
  envelope, area non pretesa, ricerca corta, passaggio al repository)
- Consumatore: [api_commessa_stato.md](/backend/vendite/manual/api_commessa_stato)
  — `PATCH /vendite/commesse/<id>/`
