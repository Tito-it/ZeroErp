# Endpoint GET /api/v1/core/me/ — Profilo utente corrente

## Scopo

Restituisce il profilo completo dell'utente autenticato: dati anagrafici (soggetto),
risorse umane, is_super_admin/ruolo_applicativo, dati emittente fiscale associato
e **dettaglio dell'identita digitale del JWT corrente** (multi-face auth §8.3.6).

## Contesto

Il frontend chiama questo endpoint dopo il login (via `fetchProfile()` nello store auth)
per popolare i dati utente visibili in topbar, sidebar e componenti profilo.

Il payload e' prodotto principalmente dalla funzione DB `script.fn_get_user_profile(auth_user_id)`,
che a sua volta riusa `script.fn_get_soggetto_dati_by_ruolo(soggetto_ruolo_id)` per i blocchi
soggetto utente e soggetto emittente. `is_super_admin` e `ruolo_applicativo` arrivano
sempre dal top-level della funzione DB (GUC-aware), senza ripieghi lato Python. Il backend
arricchisce il payload con:

- `is_admin_globale` — derivato da regola Q1 refactor operatore-emittenti
- `emittente_attivo` — l'emittente dentro cui lavora la sessione (dal claim JWT), da `EmittenteAttivoService.descrivi`
- `fuso_aziendale` — il nome IANA del fuso dell'azienda, dal BB `fuso_aziendale` (dal 2026-10-09)
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
| `is_super_admin` | boolean | True se l'utente ha binding attivo al profilo SUPER_ADMIN (id 9100) **sulla veste OPERATORE** (§8.3.7 filtro DB). Emesso da `fn_get_user_profile` |
| `ruolo_applicativo` | string/null | Ruolo applicativo dell'identita attiva del JWT: `OPERATORE` \| `CLIENTE_PORTALE` \| `FORNITORE_PORTALE` \| `SHOP_CUSTOMER` \| `API_CLIENT` \| null (`DISABILITATO` non e' piu' un tipo di veste dal 2026-10-02) |
| `risorse_umane` | object | risorsa_umana_id, soggetto_ruolo_id, qualifica (id/codice/codice_interno/descrizione), UO (id/codice/codice_interno/descrizione), validita', attivo |
| `soggetto` | object | Dati soggetto completi da `fn_get_soggetto_dati_by_ruolo` (identita', dati_societari) |
| `emittente` | object/null | Dati emittente fiscale (`emittente_fiscale_id`, `emittente_codice`, `emittente_descrizione`, `user_emittente_fiscale_id`, ...) + soggetto ditta (null se non risolto) |
| `is_admin_globale` | boolean | True se `is_super_admin` e `emittente.user_emittente_fiscale_id` e' NULL (nessuna riga in `user_emittenti_fiscali`). Calcolato in Python. Refactor operatore-emittenti Q1 |
| `emittente_attivo` | object | Emittente di sessione: `emittente_fiscale_id` (dal claim JWT), `puo_scegliere`, `deve_scegliere`, `modalita_globale`, ... Vedi `/me/emittente-attivo/` sotto |
| `identita` | object/null | **§8.3.6 multi-face** — dettaglio dell'identita digitale specifica del JWT corrente: `id`, `soggetto_ruolo_id`, `ruolo_applicativo`, `attivo`, `valido_dal`, `valido_al`, `invito_inviato_at`. `null` per token pre-refactor (JwtAuditAuthentication §8.3.4 li rifiuta gia' con 401; caso difensivo) |
| `permessi_area` | object | Mappa livello accesso per area funzionale: `{schema_db: "TUTTO"\|"LETTURA"\|"BLOCCATO"}`. Prodotta da `fn_get_user_permissions_map` |
| `azioni_abilitate` | object | Mappa azioni abilitate, da `fn_get_user_actions_map` |
| `permessi_oggetto` | object | Mappa permessi per oggetto, da `fn_get_user_object_permissions_map` |
| `deve_cambiare_password` | boolean | Flag della **credenziale** (default false): la password e' una sola, l'obbligo vale per tutte le vesti (D-7) |
| `fuso_aziendale` | string | Nome IANA del fuso dell'azienda (es. `Europe/Rome`): parametro `SYSTEM_FUSO_ORARIO` letto da `script.fn_fuso_operativo()` tramite il BB `apps/core/services/fuso_aziendale` (cache di processo). Il frontend lo usa per l'«oggi» e per le ore a video: un solo fuso in tutta l'applicazione, non quello del browser (dal 2026-10-09, brief un-solo-fuso-aziendale B-1/T-1). Un cambio del parametro vale dal riavvio del backend |
| `obblighi_pendenti` | array | Gli obblighi della credenziale che il cancello fa rispettare, nell'ordine in cui si chiudono: `CAMBIO_PASSWORD`, `SECONDO_FATTORE` (dal 2026-10-02, `cancello_obblighi.obblighi_in_vigore`). Il frontend porta alla pagina del primo. Il profilo risponde anche con un obbligo pendente (`obblighi_ammessi`) |

### Esempio risposta

```json
{
  "data": {
    "utente": { "auth_user_id": 1, "username": "mtitini", "first_name": "Michele", "last_name": "Titini", "email": "m@example.com" },
    "is_super_admin": true,
    "ruolo_applicativo": "OPERATORE",
    "risorse_umane": { "risorsa_umana_id": 5, "qualifica_codice": "DEV", "unita_organizzativa_codice": "IT" },
    "soggetto": { "soggetto_id": "019...", "nome": "Michele", "cognome": "Titini" },
    "emittente": { "emittente_fiscale_id": 1, "emittente_descrizione": "Azienda SRL", "user_emittente_fiscale_id": null },
    "is_admin_globale": true,
    "fuso_aziendale": "Europe/Rome",
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
- Se l'utente non ha un'identita' digitale OPERATORE (`identita_digitali`) associata, la funzione DB solleva `E_ADMIN_VALIDAZIONE` (400)
- Veste non utilizzabile (spenta o fuori dalle sue date, o rapporto non attivo o fuori date: `script.fn_veste_utilizzabile`): `E_UTENTE_DISABILITATO` (403). I codici delle date `E_UTENTE_NON_ATTIVO` / `E_UTENTE_SCADUTO` sono ritirati dal 2026-10-07 (brief-db-veste-utilizzabile D-4)
- Emittente: si prende il primo emittente attivo della whitelist `user_emittenti_fiscali` (ordine per id); se la whitelist non ne da', il gestore globale (`emittenti_fiscali_billing_account` con billing account NULL e `is_default = true`), con `user_emittente_fiscale_id` NULL
- Se nessuno dei due si risolve, la sezione `emittente` e' `null`

## Dipendenze DB

| Funzione/Tabella | Schema | Ruolo |
|---|---|---|
| `fn_get_user_profile(INTEGER)` | `script` | Funzione principale — compone il JSONB profilo |
| `fn_get_soggetto_dati_by_ruolo(BIGINT)` | `script` | Sub-funzione — dati soggetto + dati_societari |
| `auth_user` | Django | Dati autenticazione |
| `identita_digitali` | `anagrafiche` | Identita' OPERATORE dell'utente → `risorse_umane` per `soggetto_ruolo_id` (⚠️ fino al 2026-09-12 questa riga nominava la vista `risorse_umane_auth_user`, nome vecchio del ponte in ritiro (analisi-software-per-dati-morti §2.1)) |
| `risorse_umane` | `anagrafiche` | Qualifica, UO, validita' |
| `soggetti_ruoli` | `anagrafiche` | Ruolo soggetto |
| `soggetti` | `anagrafiche` | Dati anagrafici |
| `dati_societari` | `anagrafiche` | Dati societari (opzionale) |
| `emittenti_fiscali` | `anagrafiche` | Emittente fiscale |
| `user_emittenti_fiscali` | `config` | Whitelist emittenti per utente |
| `fn_get_user_permissions_map(INTEGER)` | `script` | Mappa permessi per area funzionale — JSONB `{area: livello}` |
| `fn_fuso_operativo()` | `script` | Il fuso dell'azienda (`fuso_aziendale`), letto una volta per processo |

## File backend

| File | Ruolo |
|---|---|
| `apps/core/api/me_view.py` | `UserProfileView(DomainAPIView)` — GET con JWT + `@extend_schema` + helper `_identita_del_jwt` per blocco `identita` |
| `apps/core/db/core_repository.py` | `CoreRepository.get_user_profile()` — chiama la fn DB |
| `apps/core/db/auth_repository.py` | `AuthRepository.get_identita_dettaglio(identita_id, auth_user_id)` — query identita con guard anti-tampering (filtra anche auth_user_id) |
| `apps/core/services/fuso_aziendale.py` | BB del fuso dell'azienda — campo `fuso_aziendale` |
| `apps/core/services/emittente_attivo_service.py` | `EmittenteAttivoService` — blocco `emittente_attivo` e logica di `/me/emittente-attivo/` |
| `apps/core/services/auth_constants.py` | `JWT_CLAIM_IDENTITA_ID = "identita_id"` — usato in `_identita_del_jwt` |
| `apps/core/api/urls_v1.py` | Rotta `me/` registrata |
| `apps/core/services/error_policies_generated.py` | Classe di `E_CORE_PROFILE_NOT_FOUND` (NON_TROVATO, HTTP 404) |
| `apps/core/tests/api/test_me_view.py` | Test unitari (mock DB + mock AuthRepository, incluso `IdentitaDelJwtTests` per §8.3.6) |

## GET / POST `/api/v1/core/me/emittente-attivo/` — l'emittente di sessione

La combo di topbar con cui il super admin sceglie **dentro quale emittente
lavorare** (impersonazione di scope).

| metodo | fa |
|---|---|
| `GET` | le opzioni selezionabili per l'utente corrente: `{"data": {"opzioni": [...]}}` (per l'operatore al piu' una, per il super admin tutti gli attivi) |
| `POST` | cambia l'emittente attivo **e riemette i token** — body: `emittente_fiscale_id` (opzionale: assente/null/"" = torna alla vista completa); il refresh token corrente arriva dal cookie HttpOnly `zeroerp_refresh` (**obbligatorio**). Risposta `{"data": {"emittente_attivo": {...}, "access": "..."}}`; il refresh col claim aggiornato e' riscritto nel `Set-Cookie` (solo se 200) |

⭐ **Perche' il POST riemette i token invece di limitarsi a salvare la scelta.**
La verita' della richiesta in corso e' il **claim JWT**, da cui nasce la GUC
`app.current_emittente_id` che restringe i dati a database. Senza token nuovi la
scelta avrebbe effetto solo al login successivo: la combo cambierebbe e i dati
no — cioe' il difetto peggiore di tutti, **l'interfaccia che mente**.

La scelta viene salvata **prima** della riemissione dei token: se il token fallisce,
la preferenza resta comunque salvata.

Errori specifici:

- `E_EMITTENTE_ATTIVO_NON_VALIDO` (403) — emittente inesistente, disattivato o fuori dal perimetro dell'utente
- `E_EMITTENTE_ATTIVO_TOKEN` (400) — cookie `zeroerp_refresh` assente, refresh non valido/scaduto, o di un utente diverso da quello autenticato

Il refresh viaggia nel cookie, mai nel corpo, in entrata e in uscita (dal
2026-09-28; attributi del cookie in
[api_multi_veste_token.md](api_multi_veste_token.md#cookie-di-refresh)). Non
serve l'header anti-CSRF: l'endpoint pretende gia' il Bearer.

## Errori

| Codice | HTTP | Quando |
|---|---|---|
| `E_CORE_PROFILE_NOT_FOUND` | 404 | La funzione DB restituisce NULL o nessuna riga |
| `E_ADMIN_VALIDAZIONE` | 400 | Utente senza identita' digitale OPERATORE o senza risorsa umana (guard in `fn_get_user_profile`) |
| `E_UTENTE_DISABILITATO` | 403 | Veste spenta o fuori dalle sue date, oppure rapporto non attivo o fuori date (`script.fn_veste_utilizzabile`) |
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
- `ruolo_sistema` non e' piu' emesso (rimosso dalla funzione DB in Fase 7): i consumer usano
  `is_super_admin` + `ruolo_applicativo` + `identita.ruolo_applicativo`.
