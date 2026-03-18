# Endpoint GET /api/v1/core/me/ — Profilo utente corrente

## Scopo

Restituisce il profilo completo dell'utente autenticato: dati anagrafici (soggetto),
risorse umane, ruolo_sistema e dati emittente fiscale associato.

## Contesto

Il frontend chiama questo endpoint dopo il login (via `fetchProfile()` nello store auth)
per popolare i dati utente visibili in topbar, sidebar e componenti profilo.

Il payload e' prodotto interamente dalla funzione DB `script.fn_get_user_profile(auth_user_id)`,
che a sua volta riusa `script.fn_get_soggetto_dati_by_ruolo(soggetto_ruolo_id)` per i blocchi
soggetto utente e soggetto emittente.

Il backend non contiene logica business: orchestra la chiamata DB e restituisce il JSONB.

## Input

- **Autenticazione**: JWT Bearer token (header `Authorization: Bearer <access_token>`)
- **Parametri**: nessuno — l'endpoint usa `request.user.id` dall'autenticazione JWT

## Output

Envelope standard `{ "data": {...}, "meta": {...} }`.

Il blocco `data` contiene il JSONB dalla funzione DB con le sezioni:

| Sezione | Tipo | Contenuto |
|---|---|---|
| `utente` | object | auth_user_id, username, first_name, last_name, email |
| `ruolo_sistema` | string/null | ADMIN, OPERATIVO, DISABILITATO o null |
| `risorse_umane` | object | risorsa_umana_id, qualifica, UO, validita', attivo |
| `soggetto` | object | Dati soggetto completi da `fn_get_soggetto_dati_by_ruolo` (identita', dati_societari) |
| `emittente` | object/null | Dati emittente fiscale + soggetto ditta (null se non associato) |
| `permessi_area` | object | Mappa livello accesso per area funzionale: `{schema_db: "TUTTO"\|"LETTURA"\|"BLOCCATO"}`. Prodotta da `fn_get_user_permissions_map` |

### Esempio risposta

```json
{
  "data": {
    "utente": { "auth_user_id": 1, "username": "mtitini", ... },
    "ruolo_sistema": "ADMIN",
    "risorse_umane": { "risorsa_umana_id": 5, "qualifica_codice": "DEV", ... },
    "soggetto": { "soggetto_id": "019...", "nome": "Michele", "cognome": "Titini", ... },
    "emittente": { "emittente_fiscale_id": 1, "ragione_sociale_completa": "Azienda SRL", ... },
    "permessi_area": {
      "anagrafiche": "TUTTO",
      "vendite": "LETTURA",
      "contabilita": "BLOCCATO",
      "catalogo": "TUTTO",
      "acquisti": "LETTURA",
      "magazzino": "TUTTO",
      "pagamenti": "BLOCCATO"
    }
  },
  "meta": { "request_id": "..." }
}
```

## Regole

- L'endpoint restituisce sempre i dati dell'utente **autenticato** — non e' possibile consultare il profilo di altri utenti (per quello usare `/users/<id>/permessi-effettivi/`)
- Se l'utente non ha una `risorse_umane_auth_user` associata, la funzione DB solleva eccezione e l'API restituisce 404
- Se l'utente non ha emittenti associati, la sezione `emittente` e' `null`
- Se l'utente ha piu' emittenti nella whitelist, viene restituito il primo attivo
- Se la whitelist emittenti e' vuota e c'e' un solo emittente attivo, viene restituito quello

## Dipendenze DB

| Funzione/Tabella | Schema | Ruolo |
|---|---|---|
| `fn_get_user_profile(INTEGER)` | `script` | Funzione principale — compone il JSONB profilo |
| `fn_get_soggetto_dati_by_ruolo(BIGINT)` | `script` | Sub-funzione — dati soggetto + dati_societari |
| `auth_user` | Django | Dati autenticazione |
| `risorse_umane_auth_user` | `anagrafiche` | Ponte utente → risorsa umana |
| `risorse_umane` | `anagrafiche` | Qualifica, UO, validita' |
| `soggetti_ruoli` | `anagrafiche` | Ruolo soggetto |
| `soggetti` | `anagrafiche` | Dati anagrafici |
| `dati_societari` | `anagrafiche` | Dati societari (opzionale) |
| `emittenti_fiscali` | `anagrafiche` | Emittente fiscale |
| `user_emittenti_fiscali` | `config` | Whitelist emittenti per utente |
| `fn_get_user_permissions_map(INTEGER)` | `script` | Mappa permessi per area funzionale — JSONB `{area: livello}` |

## File backend

| File | Ruolo |
|---|---|
| `apps/core/api/me_view.py` | `UserProfileView(APIView)` — GET con JWT + `@extend_schema` |
| `apps/core/db/core_repository.py` | `CoreRepository.get_user_profile()` — chiama la fn DB |
| `apps/core/api/urls_v1.py` | Rotta `me/` registrata |
| `apps/core/services/error_policies.py` | Policy `E_CORE_PROFILE_NOT_FOUND` (HTTP 404) |
| `apps/core/tests/api/test_me_view.py` | 6 test unitari (mock DB, no dipendenze esterne) |

## Errori

| Codice | HTTP | Quando |
|---|---|---|
| `E_CORE_PROFILE_NOT_FOUND` | 404 | Utente senza `risorse_umane_auth_user` o funzione DB restituisce NULL |
| eccezione PL/pgSQL | 400/500 | Guard nella funzione DB (auth_user_id non valido) — gestito dal middleware |

## Note di migrazione

- L'endpoint dipende dalle funzioni DB `fn_get_user_profile` e `fn_get_soggetto_dati_by_ruolo` create nelle migrazioni:
  - `20260309-01-create-fn-get-soggetto-dati-by-ruolo-mctit.yaml`
  - `20260309-02-create-fn-get-user-profile-mctit.yaml`
- Le funzioni devono essere deployate sul DB prima di attivare l'endpoint
