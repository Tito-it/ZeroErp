# API Pricing v5 (resolver + limiti L2)

## Scopo

Endpoint diagnostici e di lookup per il sistema pricing v5. Espongono il
resolver a 3 stadi (PROMO → CONTRATTO → CATEGORIA) e i limiti L2 di
variazione prezzo configurati per l'utente corrente.

Riferimento concettuale:
[sviluppo-listini-v5.md](/dev/work-done/sviluppo-listini-v5) §7
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
  - `articolo_padre_contesto` (uuid string, opzionale) — **modello unificato BoM 2026-05-13**: UUID articolo composito padre per attivare lo STADIO BUNDLE del resolver. Se fornito, il resolver cerca prima il prezzo in `vendite.listini_righe_componenti` per la coppia `(padre, figlio)` nella versione listino determinata; fallback su `listini_righe` standalone se non trovato. Quando NULL, comportamento standalone tradizionale (resolver 3 stadi promo/contratto/categoria). Usato in modo diagnostico dal TestResolverDialog FE; in produzione e' la fn `fn_preventivo_riga_componenti_preview/init` a passarlo automaticamente. Vedi `modello-componenti-bom.md` §8.
- ⚠️ `uom_id`, `ba_id`, `utility_id` sono interi positivi **obbligatori**:
  assenti, non interi o ≤ 0 → `400 E_VENDITE_VALIDATION` col campo
  (`context.field`). 2026-10-20: prima un valore assente diventava `0` e il
  resolver rispondeva «non trovato». Anche `articolo_id` e `data_riferimento`
  (ISO) assenti → `400 E_VENDITE_VALIDATION`. Senza
  `emittente_soggetto_ruolo_id` e senza emittenti autorizzati per l'operatore →
  `400 E_VENDITE_VALIDATION`.
- Output `200`: oggetto risolto con `prezzo_finale`, `prezzo_base_snapshot`, `tipo_variazione_applicata`, `valore_variazione_applicata`, `origine` (PROMO/CONTRATTO_OVERRIDE/CONTRATTO_LISTINO/CATEGORIA/**LISTINO_BUNDLE**), `listino_id`, `listino_versione_id`, `listino_riga_id`, `contratto_id`, `promo_id`, `categoria_cliente_listino_id`, `categoria_cliente_id_snapshot`, `classe_utenza_id_snapshot`, più i **campi di descrizione** accanto agli id: `listino_codice`, `listino_descrizione`, `listino_versione_codice`, `contratto_numero`, `promo_codice`, `promo_descrizione`, `categoria_cliente_codice`, `categoria_cliente_descrizione`, `classe_utenza_descrizione` (`null` quando lo stadio non li valorizza). Quando `origine='LISTINO_BUNDLE'`, `listino_riga_id` punta alla riga `listini_righe_componenti` (non `listini_righe`).
- Errori applicativi sollevati dal resolver DB (status dalla classe a catalogo,
  `error_policies_generated.py`):

  | Codice | Classe | HTTP |
  | --- | --- | --- |
  | `E_PREZZO_LISTINO_NON_TROVATO` | `NON_TROVATO` | 404 |
  | `E_PREZZO_LISTINO_RIGA_NON_TROVATA` (con `bundle_tentato` nel detail se `articolo_padre_contesto` era valorizzato) | `NON_TROVATO` | 404 |
  | `E_CATEGORIA_LISTINO_NON_MAPPATA` | `NON_TROVATO` | 404 |
  | `E_LISTINO_VERSIONE_NON_ATTIVA` | `NON_ESEGUIBILE` | 422 |
  | `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C` | `DATO_ERRATO` | 400 |
  | `E_VENDITE_PRICING_FAILED` (ripiego per ciò che il DB non ha nominato) | `DATO_ERRATO` | 400 |

---

### 1-bis. Diagnostica configurazione (`POST /api/v1/vendite/pricing/diagnose/`)

- Auth: `vendite` livello LETTURA. Nessuna scrittura.
- Body: gli **stessi** campi del resolver (stesse regole su obbligatori e `400`),
  `articolo_padre_contesto` escluso dal servizio.
- Non chiama il resolver: ispeziona la configurazione dei tre stadi per quella
  combinazione e suggerisce come sbloccarla (`PricingDiagnoseService`).
- Output `200`: `{ "ba": {trovato, categoria_id, categoria_codice,
  categoria_descrizione, categoria_partecipa_promo}, "stadio_0_promo": {...},
  "stadio_1_contratto": {...}, "stadio_2_categoria": {...}, "esito_atteso":
  {...}, "azioni_suggerite": ["..."] }` — ogni stadio porta almeno
  `applicabile` e `motivo`.

---

### 2. Limiti utente (L2 sconto/maggiorazione)

- Metodo: `GET`
- Path: `/api/v1/vendite/pricing/limiti-utente/`
- Query param opzionale: `billing_account_id` (int) — se fornito, la cascata include il livello `categoria_cliente` del BA destinatario (vedi cascata estesa sotto). Senza, il livello viene saltato. Non numerico o ≤ 0 → 400 `E_VALIDATION_INPUT`; BA inesistente o fuori dallo scope dell'operatore → 404 `E_ANAG_NOT_FOUND` (BB `categoria_cliente_da_query`, dal 2026-10-08: prima un BA malformato o che non risultava faceva saltare il livello in silenzio).
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

- Risoluzione **cascata estesa (refactor 2026-05-15)**: `user → categoria_cliente → group → emittente → session → function → default` via `ParameterService.get_defaults` con codici `VENDITE_MAX_SCONTO_PCT` + `VENDITE_MAX_MAGGIORAZIONE_PCT`. Default 0 = nessuna variazione ammessa (admin abilita override per ruolo/utente/categoria).
- Singolo round-trip DB per il batch di parametri. La risoluzione di `categoria_cliente_id` dal BA aggiunge una query extra solo se `billing_account_id` e' fornito (se il BA non risulta, 404: vedi sopra).
- Valori serializzati come stringa (envelope stabile); il FE converte in Number per interpolazione hint
- **Esempio uso FE**: il drawer riga preventivo, quando il preventivo ha un BA selezionato, chiama `GET /pricing/limiti-utente/?billing_account_id=<id>` per ottenere la soglia coerente con la categoria cliente target (es. operatore senior che fa preventivo a cliente PREMIUM vede 5% invece dei suoi 20% generici)

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
