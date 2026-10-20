# API competenze_flussi (Django)

## Scopo

Esporre via HTTP la gestione della matrice competenze flussi: per ogni tipo di flusso e reparto, quali operatori sono abilitati a eseguire il flusso. Configurazione statica, scrivibile da chi ha il livello d'area `pratiche` richiesto dal metodo (nessun controllo «admin» in più).

## Contesto

CRUD semplice sulla tabella `pratiche.competenze_flussi`. La matrice competenze e' usata da:

- `fn_coda_lavoro_operatore`: per il livello COMPETENZA (flussi che l'operatore puo' prendere in carico)
- `fn_prendi_in_carico_flusso`: per la verifica di abilitazione alla presa in carico

## Input

### Lista competenze

- Metodo: `GET`
- Path canonico: `/api/v1/pratiche/competenze-flussi/`
- Header: `Authorization: Bearer <access_token>`

### Crea competenza

- Metodo: `POST`
- Path canonico: `/api/v1/pratiche/competenze-flussi/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body:
  - `template_flusso_id` (int, obbligatorio) — FK a `pratiche.template_flussi`
  - `unita_organizzativa_id` (int, obbligatorio) — FK a `config.unita_organizzative`
  - `risorsa_umana_id` (int, obbligatorio) — FK a `anagrafiche.risorse_umane`
  - `attivo` (booleano JSON `true`/`false`, opzionale, default `true`) — competenza attiva/sospesa; una stringa o un numero è `400 E_VALIDATION_INPUT`

### Elimina competenza

- Metodo: `DELETE`
- Path canonico: `/api/v1/pratiche/competenze-flussi/<competenza_id>/`
- Header: `Authorization: Bearer <access_token>`

## Output

### GET 200:
```json
{
  "data": {
    "results": [
      {
        "id": 1,
        "template_flusso_id": 5,
        "unita_organizzativa_id": 3,
        "risorsa_umana_id": 100,
        "attivo": true,
        "template_flusso_codice": "VALUTAZIONE",
        "template_flusso_descrizione": "Valutazione iniziale",
        "unita_organizzativa_descrizione": "Reparto Tecnico",
        "risorsa_umana_display": "Mario Rossi"
      }
    ]
  }
}
```

### POST 200:
```json
{ "data": { "competenza_id": 42, "status": "ok" } }
```

### DELETE 200:
```json
{ "data": { "deleted": true } }
```

### Errori

- `400`: ID obbligatorio assente dal corpo o <= 0 (`E_INVALID_ID`, col campo)
- `404`: Competenza non trovata per DELETE (`E_FLUSSO_COMPETENZA_NOT_FOUND`)
- `400`: Violazione unique constraint (stessa terna template+UO+risorsa)
- `401`: JWT mancante o non valido

## Regole

- Permesso: solo il livello dell'area `pratiche` (`DomainAPIView`, `area_funzionale = "pratiche"`).

- La terna `(template_flusso_id, unita_organizzativa_id, risorsa_umana_id)` deve essere unica (constraint DB `uq_competenze_flussi`).
- Il flag `attivo = false` sospende la competenza senza rimuovere la configurazione (utile per assenze temporanee).
- La GET lista include display fields da JOIN: codice/descrizione template flusso, descrizione UO, ragione sociale operatore.
- La lista e' ordinata per: template flusso → unita' organizzativa → nome operatore.
- L'eliminazione e' fisica (DELETE), non logica. Per disattivazione temporanea usare `attivo = false` via PATCH (non ancora implementato, futuro).

## Dipendenze DB

- `pratiche.competenze_flussi` (CRUD)
- `pratiche.template_flussi` (JOIN display)
- `config.unita_organizzative` (JOIN display)
- `anagrafiche.risorse_umane` → `anagrafiche.soggetti_ruoli` → `anagrafiche.soggetti` (JOIN display risorsa_umana_display)

## Note di migrazione

- Tabella creata in migration `20260329-13-create-competenze-flussi-mctit.yaml`.
- FK rinominate con naming standard in `20260329-16-fix-fn-prendi-in-carico-race-condition-mctit.yaml`.
