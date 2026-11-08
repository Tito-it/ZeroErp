# API pratica_detail (Django)

## Scopo

Esporre via HTTP il dettaglio e l'aggiornamento di una singola pratica.

## Contesto

GET restituisce la pratica dal repository. PATCH delega a `pratiche_service.aggiorna_pratica` che verifica esistenza e aggiorna solo i campi consentiti. Entrambi i metodi operano su `pratiche.pratiche`.

## Input

### GET — Dettaglio pratica

- Metodo: `GET`
- Path canonico: `/api/v1/pratiche/<pratica_id>/`
- Header sicurezza: `Authorization: Bearer <access_token>`

### PATCH — Aggiornamento pratica

- Metodo: `PATCH`
- Path canonico: `/api/v1/pratiche/<pratica_id>/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body (campi aggiornabili):
  - `descrizione` (string, opzionale)
  - `data_scadenza` (date, opzionale)
  - `soggetto_id` (UUID, opzionale)
  - `risorsa_umana_id` (int, opzionale)
  - `unita_organizzativa_id` (int, opzionale)
  - `meta` (dict, opzionale)

## Output

### GET 200:
```json
{
  "data": {
    "id": 1,
    "emittente_fiscale_id": 10,
    "tipo_prestazione_id": 5,
    "soggetto_id": "…uuid…",
    "soggetto_ruolo_id": 100,
    "istanza_utility_id": 42,
    "billing_account_id": 7,
    "stato_id": 1,
    "priorita_id": 2,
    "risorsa_umana_id": null,
    "unita_organizzativa_id": null,
    "pratica_padre_id": null,
    "flusso_origine_id": null,
    "canale_origine_id": null,
    "codice": "PRA-0000001",
    "descrizione": "Pratica di esempio",
    "data_apertura": "2026-03-04",
    "data_scadenza": null,
    "meta": {},
    "data_insert": "2026-03-04T10:00:00+00:00",
    "user_insert": "zeroerp",
    "tipo_prestazione_codice": "…",
    "tipo_prestazione_descrizione": "…",
    "stato_codice_interno": "APERTA",
    "stato_descrizione": "Aperta",
    "priorita_codice_interno": "NORMALE",
    "priorita_descrizione": "Normale",
    "soggetto_display": "Rossi Mario",
    "soggetto_id_fiscale": "…",
    "risorsa_umana_display": null,
    "unita_organizzativa_descrizione": null,
    "doc_risolto": null, "…": "gli altri campi doc_* (sotto)"
  }
}
```

Stessa proiezione della riga di lista (`_PRATICA_SELECT`). ⛔ Non esiste un campo `solo_interna`.
`billing_account_id` è la colonna della pratica (vedi
[api_pratiche_list.md](api_pratiche_list.md)).

### PATCH 200:
```json
{ "data": { "status": "ok" } }
```

- `400`: JSON non valido
- `401`: JWT mancante o non valido
- `404`: pratica non trovata (`E_PRATICA_NOT_FOUND`)

### Descrittore documento sorgente `doc_*` (2026-07-02, proiezione V10)

Il payload (GET e lista) espone i display fields `doc_*` del documento sorgente
della pratica: `doc_risolto`, `doc_stato_codice_interno`,
`doc_stato_descrizione`, `doc_fase`, `doc_esito`, `doc_terminale`,
`doc_sorgente_descrizione`. Semantica dei valori in `api_percorso.md`
(proiezione read-time, nessun mirror: il documento resta l'unica verità).

⛔ **Non è il documento `ROOT`, e questa riga lo diceva.** L'àncora a livello
pratica è `script.vw_pratica_doc_sorgente` (roll-out offerte/ordini/contratti,
D3b): **una riga per pratica**, scelta fra *tutti* i link — `ROOT` **e**
`COLLEGATO` — con l'ordine `risolto` → **non-terminale** → `ROOT` → link più
recente. ⇒ Su una pratica evoluta preventivo→ordine il `ROOT` è spesso già
terminale (`EVASO`) e **vince l'ordine `COLLEGATO` vivo**: leggere il solo `ROOT`
avrebbe mostrato uno stato morto. Il `ROOT` è il **terzo** criterio, cioè un
tiebreak.

🔴 **E dal 2026-09-07 i `doc_*` dipendono da CHI LEGGE.** La vista è
`security_invoker` (changeSet `20260907-04`): il descrittore di un documento
**fuori dal perimetro emittente** di chi chiama non è leggibile, quindi quel link
risulta `doc_risolto = false` con i `doc_stato_*` a `null`.
⭐ **E può cambiare il documento scelto**, non solo nasconderne i campi:
l'ordinamento è proprio su `risolto` e `terminale`. Un `ROOT` fuori perimetro
perde contro un `COLLEGATO` visibile — che è corretto, non si sceglie un'àncora
guardando dati che non si possono vedere, ma è un **cambio di comportamento**.
⚠️ Su dati coerenti non si vede nulla: pratica e documenti passano dallo stesso
`fn_scope_ef_whitelist`. Ma il modello la divergenza **la ammette**
(`pratiche_sorgenti` non ha nessun vincolo che leghi la sorgente all'emittente
della pratica, e `sorgente_uid` è polimorfa senza FK).
Presidio: `backend/scripts/tests/smoke-pratica-doc-sorgente-cross-emittente.py`,
che costruisce il caso invece di aspettarlo.

⚠️ **Il ramo PER-FLUSSO è un'altra cosa**: `api_percorso.md` e
`api_coda_lavoro.md` ancorano per `flusso_id` dentro un solo flusso, con
`script.vw_flusso_doc_sorgente` (dal 2026-11-08: `ROOT` → risolto → non
terminale → più recente). Due àncore, due domande diverse.

⚠️ **`doc_*` tutti `null` non vuol dire «pratica fuori perimetro»**: significa
che la pratica non ha link. Fuori perimetro la pratica **non si vede affatto** —
il `404` nasce da `pratiche.pratiche`, che ha la RLS; la vista, che
`pratiche.pratiche` non la legge, non c'entra.

## Regole

- GET: se la pratica non esiste → `E_PRATICA_NOT_FOUND` (404).
- PATCH: solo i campi nella whitelist sono aggiornabili (`descrizione`, `data_scadenza`, `soggetto_id`, `risorsa_umana_id`, `unita_organizzativa_id`, `meta`). Dal 2026-10-20 una chiave fuori whitelist e un corpo vuoto sono un 400 `E_PRATICA_VALIDATION`: prima la chiave si ignorava e il corpo vuoto rispondeva 200 senza scrivere.
- PATCH: `pratica_id` deve essere > 0, altrimenti → `E_INVALID_ID` (400).
- PATCH: verifica esistenza pratica prima dell'update.
- PATCH: wrappato in `@transaction.atomic()`.
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `pratiche.pratiche` (tabella principale)

## Note di migrazione

- Update dinamico con SET costruito da whitelist (`PraticheRepository.update_pratica`).
- Campo `meta` serializzato come `jsonb`.
