# Endpoint GET /api/v1/core/me/ — Profilo utente corrente

## Scopo

Restituisce il profilo completo dell'utente autenticato: dati anagrafici (soggetto),
risorse umane, ruolo_sistema/ruolo_applicativo, dati emittente fiscale associato
e **dettaglio dell'identita digitale del JWT corrente** (multi-face auth §8.3.6).

## Contesto

Il frontend chiama questo endpoint dopo il login (via `fetchProfile()` nello store auth)
per popolare i dati utente visibili in topbar, sidebar e componenti profilo.

Il payload e' prodotto principalmente dalla funzione DB `script.fn_get_user_profile(auth_user_id)`,
che a sua volta riusa `script.fn_get_soggetto_dati_by_ruolo(soggetto_ruolo_id)` per i blocchi
soggetto utente e soggetto emittente. Il backend arricchisce il payload con:

- `is_admin_globale` — derivato da regola Q1 refactor operatore-emittenti
- `is_super_admin` — da `PermissionResolver.is_super_admin` (fallback se fn DB non lo popola)
- `ruolo_applicativo` — da `PermissionResolver.get_ruolo_applicativo` (fallback)
- `identita` — dettaglio dell'identita specifica del JWT corrente (§8.3.6 multi-face).
  Post modello 1:N, un auth_user puo' avere piu' identita attive (es. OPERATORE +
  CLIENTE_PORTALE); il JWT indica quale "veste" stai usando, e /me/ deve riflettere
  ESATTAMENTE quella (non una a caso).

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
| `ruolo_sistema` | string/null | **LEGACY** — ADMIN, OPERATIVO, DISABILITATO o null. Ricostruito da `is_super_admin + ruolo_applicativo`. Nuovi consumer usino i due campi nativi |
| `is_super_admin` | boolean | True se l'utente ha binding attivo al profilo SUPER_ADMIN (id 9100) **sulla veste OPERATORE** (§8.3.7 filtro DB). Letto via `PermissionResolver.is_super_admin` |
| `ruolo_applicativo` | string/null | Ruolo applicativo dell'identita attiva del JWT: `OPERATORE` \| `CLIENTE_PORTALE` \| `FORNITORE_PORTALE` \| `SHOP_CUSTOMER` \| `API_CLIENT` \| `DISABILITATO` \| null |
| `risorse_umane` | object | risorsa_umana_id, qualifica, UO, validita', attivo |
| `soggetto` | object | Dati soggetto completi da `fn_get_soggetto_dati_by_ruolo` (identita', dati_societari) |
| `emittente` | object/null | Dati emittente fiscale + soggetto ditta (null se non associato) |
| `is_admin_globale` | boolean | True se l'utente e' admin globale (ruolo_sistema=ADMIN + nessuna riga in `user_emittenti_fiscali`). Refactor operatore-emittenti Q1 |
| `identita` | object/null | **§8.3.6 multi-face** — dettaglio dell'identita digitale specifica del JWT corrente: `id`, `soggetto_ruolo_id`, `ruolo_applicativo`, `attivo`, `valido_dal`, `valido_al`, `invito_inviato_at`. `null` per token pre-refactor (JwtAuditAuthentication §8.3.4 li rifiuta gia' con 401; caso difensivo) |
| `permessi_area` | object | Mappa livello accesso per area funzionale: `{schema_db: "TUTTO"\|"LETTURA"\|"BLOCCATO"}`. Prodotta da `fn_get_user_permissions_map` |

### Esempio risposta

```json
{
  "data": {
    "utente": { "auth_user_id": 1, "username": "mtitini", "first_name": "Michele", "last_name": "Titini", "email": "m@example.com" },
    "ruolo_sistema": "ADMIN",
    "is_super_admin": true,
    "ruolo_applicativo": "OPERATORE",
    "risorse_umane": { "risorsa_umana_id": 5, "qualifica_codice": "DEV", "unita_organizzativa_codice": "IT" },
    "soggetto": { "soggetto_id": "019...", "nome": "Michele", "cognome": "Titini" },
    "emittente": { "emittente_fiscale_id": 1, "ragione_sociale_completa": "Azienda SRL" },
    "is_admin_globale": true,
    "identita": {
      "id": 5,
      "soggetto_ruolo_id": 12,
      "ruolo_applicativo": "OPERATORE",
      "attivo": true,
      "valido_dal": "2024-01-01",
      "valido_al": null,
      "invito_inviato_at": null
    },
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

### Multi-face: stesso auth_user, veste diversa

Se l'utente `mtitini` avesse anche un'identita `CLIENTE_PORTALE` (id=2, scenario
teorico di auto-invito), chiamando /me/ con JWT ottenuto via `/admin/token/`:

- `identita.id` sarebbe **5** (veste OPERATORE), **non** 2
- `identita.ruolo_applicativo` sarebbe `"OPERATORE"`
- `is_super_admin` sarebbe `true` (il filtro DB e' su veste OPERATORE)

Con JWT ottenuto via `/portale/token/` (se portale fosse attivo):

- `identita.id` sarebbe **2**
- `identita.ruolo_applicativo` sarebbe `"CLIENTE_PORTALE"`
- `is_super_admin` sarebbe `false` (binding SUPER_ADMIN e' legato a OPERATORE)

Il FE usa `identita.ruolo_applicativo` per decidere la UI della veste attiva.

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
| `apps/core/api/me_view.py` | `UserProfileView(DomainAPIView)` — GET con JWT + `@extend_schema` + helper `_identita_del_jwt` per blocco `identita` |
| `apps/core/db/core_repository.py` | `CoreRepository.get_user_profile()` — chiama la fn DB |
| `apps/core/db/auth_repository.py` | `AuthRepository.get_identita_dettaglio(identita_id, auth_user_id)` — query identita con guard anti-tampering (filtra anche auth_user_id) |
| `apps/core/services/permissions_resolver.py` | `PermissionResolver.is_super_admin` / `get_ruolo_applicativo` — fallback se `fn_get_user_profile` non popola |
| `apps/core/services/auth_constants.py` | `JWT_CLAIM_IDENTITA_ID = "identita_id"` — usato in `_identita_del_jwt` |
| `apps/core/api/urls_v1.py` | Rotta `me/` registrata |
| `apps/core/services/error_policies.py` | Policy `E_CORE_PROFILE_NOT_FOUND` (HTTP 404) |
| `apps/core/tests/api/test_me_view.py` | Test unitari (mock DB + mock AuthRepository, incluso `IdentitaDelJwtTests` per §8.3.6) |

## Errori

| Codice | HTTP | Quando |
|---|---|---|
| `E_CORE_PROFILE_NOT_FOUND` | 404 | Utente senza `risorse_umane_auth_user` o funzione DB restituisce NULL |
| `E_JWT_SENZA_IDENTITA` | 401 | JWT senza claim `identita_id` (token pre-§8.3.2) — intercettato da `JwtAuditAuthentication` a monte della view |
| `E_IDENTITA_NON_ATTIVA` | 401 | Claim `identita_id` non corrisponde a identita attiva (revocata dopo emissione JWT) — intercettato a monte |
| `E_AUTHENTICATION_FAILED` | 401 | JWT scaduto, invalido o non fornito |
| eccezione PL/pgSQL | 400/500 | Guard nella funzione DB (auth_user_id non valido) — gestito dal middleware |

## Note di migrazione

- L'endpoint dipende dalle funzioni DB `fn_get_user_profile` e `fn_get_soggetto_dati_by_ruolo` create nelle migrazioni:
  - `20260309-01-create-fn-get-soggetto-dati-by-ruolo-mctit.yaml`
  - `20260309-02-create-fn-get-user-profile-mctit.yaml`
- Le funzioni devono essere deployate sul DB prima di attivare l'endpoint
- **§8.3.6 multi-face** (post migration `20260420-01..11`): il campo `identita` viene
  popolato dal backend leggendo `request.auth.get("identita_id")` (claim JWT iniettato
  da `MultiVesteTokenSerializer` §8.3.2) e delegando a `AuthRepository.get_identita_dettaglio`.
  Post-cutover, i JWT senza `identita_id` sono gia' rifiutati a monte da
  `JwtAuditAuthentication.authenticate()` con `E_JWT_SENZA_IDENTITA` (401) —
  quindi il caso `identita: null` e' puramente difensivo.
- `ruolo_sistema` resta esposto per retrocompat FE; nuovi consumer usino
  `is_super_admin` + `ruolo_applicativo` + `identita.ruolo_applicativo`.
