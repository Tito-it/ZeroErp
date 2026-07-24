# API commessa_attivita (Django)

## Scopo

Esporre via HTTP la lista paginata delle attività (`commesse_attivita`) di una commessa,
con filtri opzionali per stato emissione, stato approvazione e mese di competenza.

## Contesto

Endpoint applicativo che invoca il servizio Python `fn_list_commessa_attivita`
(`apps.vendite.services.commesse_service`), il quale delega a
`CommesseRepository.list_commessa_attivita()` che chiama la funzione DB
`vendite.fn_list_commessa_attivita`.

View: `ApiCommessaAttivita` `ApiCommessaAttivita` (`apps.vendite.api.views`).

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/vendite/commesse/<commessa_id>/attivita/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Parametri path:
  - `commessa_id` (int) — ID della commessa
- Query params (tutti opzionali):
  - `stato_emissione` (string) — filtro stato emissione (es. `NON_EMESSA`, `EMESSA`)
  - `stato_approvazione` (string) — filtro stato approvazione (es. `BOZZA`, `APPROVATA`)
  - `competenza_mese` (date `YYYY-MM-DD`) — filtro mese di competenza (normalizzato al primo del mese dal DB)
  - `limit` (int) — righe per pagina (default 50, range 1-200)
  - `offset` (int) — offset paginazione (default 0)

## Output

- `200`: lista attività

```json
{
  "data": {
    "commessa_id": 1,
    "count": 3,
    "rows": [
      {
        "id": 100,
        "commessa_id": 1,
        "segment_key": "PREV:abc123:ITEM:1",
        "articolo_id": "550e8400-e29b-41d4-a716-446655440000",
        "istanza_utility_id": 5,
        "data_attivita": "2026-02-15",
        "uom_id": 1,
        "quantita": "10.00",
        "competenza_mese": "2026-02-01",
        "competenza_dal": "2026-02-01",
        "competenza_al": "2026-02-28",
        "prezzo_snapshot": "25.50",
        "prezzo_bloccato": false,
        "prezzo_da_riallineare": false,
        "stato_approvazione": "APPROVATA",
        "stato_emissione": "NON_EMESSA",
        "sorgente_tipo_id": 1,
        "sorgente_codice": "PREVENTIVO",
        "meta": {},
        "data_update": "2026-02-26T10:00:00+00:00"
      }
    ]
  },
  "meta": { ... }
}
```

- `400`: parametri non validi (`E_COMMESSA_VALIDATION`) — es. `limit` fuori range 1-200
- `404`: commessa non trovata (gestito dalla funzione DB)

## Regole

- Endpoint read-only, nessuna `Idempotency-Key` richiesta.
- Endpoint v1 richiede JWT.
- `commessa_id` deve essere > 0, altrimenti errore di validazione.
- `limit` validato nel service: deve essere compreso tra 1 e 200.
- `competenza_mese` parsata via `optional_iso_date` e passata come `date` al repository.
- La funzione DB normalizza `competenza_mese` al primo del mese (`date_trunc`).
- JOIN su `config.sorgenti` per risolvere `sorgente_codice` (evita N+1 lato client).
- `count` indica il numero di righe restituite nella pagina corrente, non il totale globale.
- Funzione DB STABLE (read-only).

## Dipendenze DB

- `vendite.fn_list_commessa_attivita(p_commessa_id, p_stato_emissione, p_stato_approvazione, p_competenza_mese, p_limit, p_offset)` — funzione principale, restituisce TABLE con 20 colonne
- `vendite.commesse_attivita` — tabella dati
- `config.sorgenti` — JOIN per `sorgente_codice`

---

## Azione APPROVA — righe di una commessa (A-1, cockpit fatturazione)

### Scopo

Portare le attività della commessa da `stato_approvazione = BOZZA` ad `APPROVATA`
(prerequisito di riga per l'emissione verso `attivita_fatturabili`). È il verbo
**Approva** del cockpit Dashboard Competenza a grana riga/commessa
(design: `brief-design-gestione-processi-fatturazione.md` §3, decisione D-3).

### Input

- Metodo: `POST`
- Path: `/api/v1/vendite/commesse/<commessa_id>/attivita/approva/`
- Header: `Authorization: Bearer <token>` + `Idempotency-Key` (obbligatoria)
- Permesso: azione di processo **`approva_attivita_commessa`** (`post_permission`)
- Body JSON:
  - `righe_ids` (int[], opzionale) — righe da approvare; **assente = tutte** le
    righe `NON_EMESSA` in `BOZZA` della commessa. Lista vuota = `400` (per
    "tutte" omettere il campo).

### Output

- `200`: `{ "data": { "commessa_id": 42, "approvate": 5 } }` — `approvate` è il
  numero di righe effettivamente transitate (già `APPROVATA` = non contate:
  la fn DB è **idempotente**, seconda invocazione → 0).
- `400`: `E_COMMESSA_VALIDATION` — `commessa_id`/`righe_ids` non validi
- `403`: azione di processo non abilitata
- `404`: `E_COMMESSA_NOT_FOUND` — commessa inesistente

### Regole

- View `ApiCommessaAttivitaApprova` → service `approva_commessa_attivita` →
  `CommesseRepository.approva_commessa_attivita` → fn DB.
- Il service verifica l'esistenza della commessa prima della fn (404 parlante).
- La fn approva solo righe `BOZZA` **e** `NON_EMESSA`: le emesse non sono toccate.

### Dipendenze DB

- `vendite.fn_approva_commessa_attivita(p_commessa_id, p_righe_ids, p_user)`

---

## Azione APPROVA massiva per competenza (A-2, cockpit fatturazione)

### Scopo

Approvare in un colpo **tutte le attività in stadio `DA_APPROVARE` di un mese di
competenza** — esattamente la popolazione che la card `DA_APPROVARE` della
Dashboard Competenza mostra (stessa vista del drill-down, WYSIWYG). Verbo
**Approva** a grana mese (D-3).

### Input

- Metodo: `POST`
- Path: `/api/v1/vendite/fatturazione/approva-competenza/`
- Header: `Authorization: Bearer <token>` + `Idempotency-Key` (obbligatoria)
- Permesso: azione di processo **`approva_attivita_commessa`**
- Body JSON:
  - `competenza_mese` (date `YYYY-MM-DD`, **obbligatoria**) — normalizzata al 1° del mese
  - `commessa_ids` (int[], opzionale) — restringe al subset di commesse del mese

### Output

- `200`: `{ "data": { "competenza_mese": "2026-07-01", "commesse": 2, "approvate": 3 } }`
  — perimetro vuoto = contatori a zero (non è un errore).
- `400`: `E_COMMESSA_VALIDATION` — mese mancante / liste non valide
- `403`: azione di processo non abilitata

### Regole

- View `ApiFatturazioneApprovaCompetenza` → service `approva_attivita_competenza`.
- Popolazione da `vendite.vw_dash_competenza_attivita` (`stadio = 'DA_APPROVARE'`,
  `competenza_mese = M`): **scope emittente applicato in-vista** (GUC
  `app.current_user_id`, `security_invoker`) — l'operatore approva solo il suo
  perimetro, per costruzione.
- **All-or-nothing**: il loop per commessa gira in UNA `transaction.atomic()`
  (guardrail «una azione = una unità atomica»); un errore su una commessa
  annulla tutto. Il retry è innocuo (fn idempotente).

### Dipendenze DB

- `vendite.vw_dash_competenza_attivita` (read, selezione popolazione)
- `vendite.fn_approva_commessa_attivita` (write, per commessa)
