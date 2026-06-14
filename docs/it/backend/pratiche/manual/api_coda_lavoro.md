# API coda_lavoro (Django)

## Scopo

Esporre via HTTP la coda di lavoro dell'operatore autenticato, organizzata su tre livelli di priorita': flussi assegnati, flussi per competenza, flussi del reparto.

## Contesto

Endpoint di sola lettura che alimenta la sidebar della dashboard pratiche. Risolve automaticamente l'operatore dall'utente JWT autenticato tramite la tabella bridge `anagrafiche.risorse_umane_auth_user`, con cache per-request per evitare query ripetute. Delega alla funzione DB `pratiche.fn_coda_lavoro_operatore` che classifica i flussi in un singolo passaggio (CTE + CASE WHEN).

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/pratiche/coda-lavoro/`
- Header: `Authorization: Bearer <access_token>`
- Query params:
  - `emittente_fiscale_id` (int, obbligatorio) — segregazione multi-company

## Output

### 200:
```json
{
  "data": {
    "results": [
      {
        "livello": "ASSEGNATO",
        "flusso_id": 10,
        "pratica_id": 1,
        "pratica_codice": "PRA-0000001",
        "pratica_descrizione": "Assistenza tecnica",
        "priorita_codice": "ALTA",
        "tipo_prestazione_codice": "ASSISTENZA_TECNICA",
        "template_flusso_codice": "VALUTAZIONE",
        "template_flusso_desc": "Valutazione iniziale",
        "stato_flusso_codice": "DA_ESEGUIRE",
        "sequenza": 10,
        "data_scadenza": "2026-04-15",
        "risorsa_assegnata": null
      }
    ]
  }
}
```

### Livelli

| Livello | Significato | Stato flusso |
|---------|-------------|--------------|
| `ASSEGNATO` | Flussi assegnati direttamente all'operatore | DA_ESEGUIRE, IN_CORSO |
| `COMPETENZA` | Flussi non assegnati, operatore ha competenza attiva | DA_ESEGUIRE |
| `REPARTO` | Flussi del reparto dell'operatore (visibilita') | DA_ESEGUIRE, IN_CORSO |

Ogni flusso appare in un solo livello (quello piu' alto applicabile). Il campo `risorsa_assegnata` e' valorizzato solo per livello REPARTO (mostra chi ha il flusso).

### Errori

- `400`: `emittente_fiscale_id` mancante o non valido (`E_PRATICA_VALIDATION`)
- `400`: Operatore non associato a una risorsa umana (`E_PRATICA_VALIDATION`)
- `401`: JWT mancante o non valido

## Regole

- L'operatore e' determinato automaticamente dal JWT, non dal payload.
- `emittente_fiscale_id` obbligatorio per la segregazione multi-company.
- Il risultato e' ordinato per: livello → priorita' (DESC) → scadenza (NULLS LAST) → sequenza.
- La competenza dell'operatore e' definita nella tabella `pratiche.competenze_flussi`.
- I flussi di **pratiche terminali** (stato senza transizioni di stato in uscita
  attive, es. `CHIUSA`/`ANNULLATA`) sono **esclusi** dalla coda: sono lavoro
  concluso, non da fare (allineato col guard `trgfn_flussi_guard_pratica_terminale`).

## Dipendenze DB

- `pratiche.fn_coda_lavoro_operatore(risorsa_umana_id, emittente_fiscale_id)` — funzione SQL
- `pratiche.competenze_flussi` — matrice competenze operatore
- `pratiche.flussi` — flussi pendenti
- `pratiche.pratiche` — testata pratica con display fields
- `anagrafiche.risorse_umane_auth_user` — bridge utente → risorsa umana

## Note di migrazione

- Funzione DB creata in migration `20260329-14-create-fn-coda-lavoro-operatore-mctit.yaml`.
- Helper `get_risorsa_umana_id` in `apps/core/api/endpoint_helpers.py` con cache per-request.
- (14 giugno 2026) `20260614-02`: la funzione esclude i flussi delle pratiche terminali.
