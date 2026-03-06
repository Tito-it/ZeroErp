# API Permessi Effettivi (Core Django)

## Scopo

Esporre un endpoint diagnostico che restituisce i permessi effettivi risolti per un utente,
iterando tutte le aree funzionali attive e mostrando il livello di accesso, le azioni
consentite e lo stato del profilo reparto.

## Contesto

View in `apps/core/api/views.py`:
- `ApiPermessiEffettivi` — logica base
- `ApiPermessiEffettiviV1` — versione protetta JWT

L'endpoint utilizza `PermissionResolver` per risolvere la catena completa
(ruolo_sistema → override utente → profilo reparto → BLOCCATO) su ogni area funzionale
attiva in `config.aree_funzionali`. Serve a rendere trasparente la risoluzione permessi
per diagnostica e onboarding.

## Endpoint

```http
GET /api/v1/core/users/{user_id}/permessi-effettivi/
```

Richiede autenticazione JWT.

## Input

Path parameter:

| Parametro | Tipo | Obbligatorio | Note                                     |
|-----------|------|:------------:|------------------------------------------|
| `user_id` | int  | Sì           | ID `auth_user` dell'utente da consultare |

## Output

```json
{
  "data": {
    "user_id": 1,
    "username": "mario.rossi",
    "ruolo_sistema": "OPERATIVO",
    "unita_organizzativa_id": 10,
    "aree": [
      {
        "codice": "VENDITE",
        "schema_db": "vendite",
        "descrizione": "Vendite",
        "livello": "TUTTO",
        "azioni_consentite": ["add", "change", "delete", "view"],
        "has_profilo_reparto": true
      },
      {
        "codice": "ACQUISTI",
        "schema_db": "acquisti",
        "descrizione": "Acquisti",
        "livello": "BLOCCATO",
        "azioni_consentite": [],
        "has_profilo_reparto": false
      }
    ],
    "emittenti_ids": [1, 3, 5]
  },
  "meta": {"request_id": "..."}
}
```

Campi risposta:

| Campo                   | Tipo          | Note                                                      |
|-------------------------|---------------|-----------------------------------------------------------|
| `user_id`               | int           | ID utente consultato                                      |
| `username`              | string        | Username Django                                           |
| `ruolo_sistema`         | string\|null  | `ADMIN`, `OPERATIVO`, `DISABILITATO` o `null` (no bridge) |
| `unita_organizzativa_id`| int\|null     | Reparto dell'utente (da `risorse_umane`)                  |
| `aree`                  | array         | Livello effettivo per ogni area funzionale attiva         |
| `aree[].codice`         | string        | Codice area (es. `VENDITE`)                               |
| `aree[].schema_db`      | string        | Schema DB corrispondente                                  |
| `aree[].livello`        | string        | `TUTTO`, `LETTURA` o `BLOCCATO`                           |
| `aree[].azioni_consentite` | array      | Azioni CRUD consentite dal livello                        |
| `aree[].has_profilo_reparto` | bool     | `true` se il reparto ha un profilo per questa area        |
| `emittenti_ids`         | array\|null   | ID emittenti autorizzati, `null` = nessuna restrizione    |

## Regole

- Solo utenti con `ruolo_sistema = ADMIN` o `is_superuser = True` possono consultare i permessi
  di **altri** utenti. Un utente OPERATIVO puo' consultare solo i propri.
- Se `user_id` non esiste, restituisce errore `E_CORE_VALIDATION` (400).
- Se l'utente non ha il permesso di consultare altri, restituisce `E_PERMESSO_NEGATO` (403).
- Per utenti `ADMIN`: tutte le aree risultano `TUTTO`.
- Per utenti `DISABILITATO`: tutte le aree risultano `BLOCCATO`.
- `has_profilo_reparto = false` con `livello = BLOCCATO` indica che il reparto non ha ancora
  un profilo configurato (diverso da un profilo che imposta esplicitamente BLOCCATO).
- `emittenti_ids = null` significa nessuna restrizione ambito emittente (l'utente vede tutto).

## Dipendenze DB

- `config.aree_funzionali` — iterazione aree attive
- `anagrafiche.risorse_umane_auth_user` — ruolo_sistema e ponte utente-risorsa
- `anagrafiche.risorse_umane` — unita_organizzativa_id
- `config.user_override_aree` — override individuali area
- `config.profili_reparto_aree` — profili reparto ereditati
- `config.user_emittenti_fiscali` — ambito emittente fiscale

## Codici errore

| Codice              | HTTP | Causa                                        |
|---------------------|------|----------------------------------------------|
| `E_PERMESSO_NEGATO` | 403  | Utente non autorizzato a consultare altri     |
| `E_CORE_VALIDATION` | 400  | `user_id` non trovato                        |
| `E_GENERICO`        | 500  | Errore imprevisto                            |
