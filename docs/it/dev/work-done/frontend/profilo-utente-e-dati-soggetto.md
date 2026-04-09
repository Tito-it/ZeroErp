# Profilo Utente e Dati Soggetto — Piano di Implementazione (COMPLETATO)

> Documento di lavoro per l'implementazione dell'esposizione dei dati soggetto
> (utente e ditta/emittente fiscale) nel frontend Vue.
>
> Data inizio: 2026-03-09
> Data completamento: 2026-03-10
> Stato: **COMPLETATO** — tutte le fasi implementate e testate funzionalmente

---

## Obiettivo

Esporre nel frontend i dati del **soggetto** associato all'utente loggato e i dati della
**ditta** (emittente fiscale) a cui l'utente e' associato.

Entrambi i contesti (utente e ditta) espongono dati di un **soggetto** con ruolo diverso:
servono componenti e API generiche che, dato un ruolo, restituiscano i dati fondamentali
del soggetto, includendo `dati_societari` quando il soggetto e' una partita IVA.

---

## Stato Attuale

### Cosa esiste gia'

| Elemento                                                                                           | Stato | Dove                                         |
| -------------------------------------------------------------------------------------------------- | ----- | -------------------------------------------- |
| Catena DB `auth_user -> risorse_umane_auth_user -> risorse_umane -> soggetti_ruoli -> soggetti`    | OK    | Schema `anagrafiche`                         |
| Whitelist emittenti per utente                                                                     | OK    | `config.user_emittenti_fiscali`              |
| Funzioni permessi (`fn_get_ruolo_sistema`, `fn_get_emittenti_scope`)                               | OK    | Schema `script`                              |
| Viste aggregate (`vw_soggetti_ruoli_dettaglio`, `vw_risorse_umane_dettaglio`, `vw_dati_societari`) | OK    | Schema `anagrafiche`                         |
| Funzioni contatti/indirizzi (`fn_get_contatti`, `fn_get_indirizzi_by_soggetto/ruolo`)              | OK    | Schema `script`                              |
| `PermissionResolver` Python                                                                        | OK    | `apps/core/services/permissions_resolver.py` |
| Store auth Pinia con `fetchProfile()`                                                              | OK    | `frontend/src/stores/auth.js`                |
| Interceptor Axios con refresh token                                                                | OK    | `frontend/src/core/api.js`                   |

### Cosa manca

| Elemento                                       | Note                                                                            |
| ---------------------------------------------- | ------------------------------------------------------------------------------- |
| Funzione DB generica "dati soggetto per ruolo" | Nessuna funzione unifica soggetto + dati_societari dato un `soggetto_ruolo_id`  |
| Funzione DB "profilo utente completo"          | Nessuna funzione aggrega dati utente + soggetto + emittente dato `auth_user_id` |
| Endpoint `GET /api/v1/core/me/`                | Il frontend lo chiama ma non esiste — fallisce silenziosamente                  |
| Mappatura risposta nello store auth            | Lo store salva `user` ma il payload atteso non e' definito                      |

---

## Catena Dati nel DB

```
auth_user (id, username, first_name, last_name, email)
  |
  +--[1:1]--> risorse_umane_auth_user (id, risorsa_umana_id, auth_user_id, ruolo_sistema)
  |              |
  |              +--[N:1]--> risorse_umane (id, soggetto_id, soggetto_ruolo_id, qualifica_id,
  |                            |             unita_organizzativa_id, attivo, valido_dal/al)
  |                            |
  |                            +--[N:1]--> soggetti_ruoli (id, soggetto_id, tipo_ruolo_id, meta)
  |                                          |
  |                                          +--[N:1]--> soggetti (id=UUID)
  |                                          |   (codice, nome, cognome, ragione_sociale,
  |                                          |    ragione_sociale_completa, codice_fiscale,
  |                                          |    partita_iva, id_fiscale_univoco_cf_piva,
  |                                          |    sesso, data_nascita, stato_id, comune_id,
  |                                          |    titolo_cortesia_id, tipo_soggetto_dettaglio_id,
  |                                          |    default_contatto_id, attivo)
  |                                          |
  |                                          +-- tipo_ruolo_id --> config.tipi_ruoli
  |                                          |   (id, codice, codice_interno, descrizione)
  |                                          |
  |                                          +--[0:1]--> dati_societari (id, soggetto_id)
  |                                              (forma_giuridica_id, id_prov_iscri_rea,
  |                                               iscrizione_rea, capitale_sociale,
  |                                               socio_unico, liquidazione,
  |                                               destinatario_fe, pec_fatturazione,
  |                                               codice_sdi, data_costituzione)
  |
  +--[0:N]--> config.user_emittenti_fiscali (id, auth_user_id, emittente_fiscale_id)
                 |
                 +--[N:1]--> emittenti_fiscali (id, uid, soggetto_ruolo_id, codice)
                                |  (descrizione, attivo, regime_fiscale_rf,
                                |   bollo_auto, bollo_soglia, rounding_policy,
                                |   brand_meta, valuta_id)
                                |
                                +--[N:1]--> soggetti_ruoli (tipo_ruolo = EMITTENTE_FISCALE)
                                              |
                                              +--[N:1]--> soggetti (ragione_sociale ditta)
                                              |
                                              +--[0:1]--> dati_societari
```

---

## Piano di Implementazione — Step dettagliati

### Fase 1 — DB: Funzione generica `script.fn_get_soggetto_dati_by_ruolo`

**Scopo**: dato un `soggetto_ruolo_id`, restituire un record composito con i dati
fondamentali del soggetto e, se presenti, i dati societari. Tutti gli ID delle tabelle
collegate sono inclusi per consentire navigazione e lookup dal frontend.

**Modello di riferimento**: combina le colonne di `vw_soggetti_ruoli_dettaglio` e `vw_dati_societari`.

**Input**: `p_soggetto_ruolo_id BIGINT`

**Output** (colonne — RETURNS TABLE):

| #   | Colonna                               | Tipo    | Fonte                                                     |
| --- | ------------------------------------- | ------- | --------------------------------------------------------- |
|     | **— Identita' ruolo —**               |         |                                                           |
| 1   | `soggetto_ruolo_id`                   | BIGINT  | `soggetti_ruoli.id` (= input)                             |
| 2   | `soggetto_id`                         | UUID    | `soggetti.id`                                             |
| 3   | `tipo_ruolo_id`                       | INTEGER | `soggetti_ruoli.tipo_ruolo_id`                            |
| 4   | `tipo_ruolo_codice`                   | VARCHAR | `config.tipi_ruoli.codice`                                |
| 5   | `tipo_ruolo_codice_interno`           | VARCHAR | `config.tipi_ruoli.codice_interno`                        |
| 6   | `tipo_ruolo_descrizione`              | VARCHAR | `config.tipi_ruoli.descrizione`                           |
|     | **— Dati anagrafici soggetto —**      |         |                                                           |
| 7   | `soggetto_codice`                     | VARCHAR | `soggetti.codice`                                         |
| 8   | `ragione_sociale`                     | VARCHAR | `soggetti.ragione_sociale`                                |
| 9   | `ragione_sociale_completa`            | VARCHAR | `soggetti.ragione_sociale_completa` (generato)            |
| 10  | `cognome`                             | VARCHAR | `soggetti.cognome`                                        |
| 11  | `nome`                                | VARCHAR | `soggetti.nome`                                           |
| 12  | `codice_fiscale`                      | VARCHAR | `soggetti.codice_fiscale`                                 |
| 13  | `partita_iva`                         | VARCHAR | `soggetti.partita_iva`                                    |
| 14  | `id_fiscale_univoco_cf_piva`          | VARCHAR | `soggetti.id_fiscale_univoco_cf_piva` (generato)          |
| 15  | `sesso`                               | CHAR(1) | `soggetti.sesso`                                          |
| 16  | `data_nascita`                        | DATE    | `soggetti.data_nascita`                                   |
| 17  | `soggetto_attivo`                     | BOOLEAN | `soggetti.attivo`                                         |
|     | **— FK e ID collegati al soggetto —** |         |                                                           |
| 18  | `stato_id`                            | INTEGER | `soggetti.stato_id` (FK config.stati — nazione)           |
| 19  | `comune_id`                           | INTEGER | `soggetti.comune_id` (FK config.comuni)                   |
| 20  | `titolo_cortesia_id`                  | INTEGER | `soggetti.titolo_cortesia_id` (FK config.titoli_cortesia) |
| 21  | `tipo_soggetto_dettaglio_id`          | BIGINT  | `soggetti.tipo_soggetto_dettaglio_id`                     |
| 22  | `default_contatto_id`                 | BIGINT  | `soggetti.default_contatto_id`                            |
|     | **— Tipo soggetto (risolto) —**       |         |                                                           |
| 23  | `tipo_soggetto_id`                    | VARCHAR | `config.tipi_soggetto.id` (PF/PG/ENTE)                    |
| 24  | `tipo_soggetto_descrizione`           | VARCHAR | `config.tipi_soggetto.descrizione`                        |
| 25  | `tipo_soggetto_codice_interno`        | VARCHAR | `config.tipi_soggetto_dettaglio.codice_interno`           |
|     | **— Titolo cortesia (risolto) —**     |         |                                                           |
| 26  | `titolo_cortesia_descrizione`         | VARCHAR | `config.titoli_cortesia.descrizione`                      |
| 27  | `titolo_cortesia_descrizione_breve`   | VARCHAR | `config.titoli_cortesia.descrizione_breve`                |
|     | **— Dati societari (nullable) —**     |         |                                                           |
| 28  | `has_dati_societari`                  | BOOLEAN | `dati_societari.id IS NOT NULL`                           |
| 29  | `dati_societari_id`                   | BIGINT  | `dati_societari.id` (nullable)                            |
| 30  | `forma_giuridica_id`                  | INTEGER | `dati_societari.forma_giuridica_id` (nullable)            |
| 31  | `forma_giuridica_codice`              | VARCHAR | `config.forme_giuridiche.codice` (nullable)               |
| 32  | `forma_giuridica_descrizione`         | VARCHAR | `config.forme_giuridiche.descrizione` (nullable)          |
| 33  | `id_prov_iscri_rea`                   | INTEGER | `dati_societari.id_prov_iscri_rea` (nullable)             |
| 34  | `provincia_iscri_rea_sigla`           | VARCHAR | `config.province.sigla` (nullable)                        |
| 35  | `iscrizione_rea`                      | VARCHAR | `dati_societari.iscrizione_rea` (nullable)                |
| 36  | `capitale_sociale`                    | NUMERIC | `dati_societari.capitale_sociale` (nullable)              |
| 37  | `socio_unico`                         | VARCHAR | `dati_societari.socio_unico` (nullable)                   |
| 38  | `liquidazione`                        | VARCHAR | `dati_societari.liquidazione` (nullable)                  |
| 39  | `destinatario_fe`                     | VARCHAR | `dati_societari.destinatario_fe` (nullable)               |
| 40  | `pec_fatturazione`                    | VARCHAR | `dati_societari.pec_fatturazione` (nullable)              |
| 41  | `codice_sdi`                          | VARCHAR | `dati_societari.codice_sdi` (nullable)                    |
| 42  | `data_costituzione`                   | DATE    | `dati_societari.data_costituzione` (nullable)             |

**Join** (stessa strategia delle viste esistenti):

```
soggetti_ruoli sr
  INNER JOIN soggetti s                        ON s.id = sr.soggetto_id
  INNER JOIN config.tipi_ruoli tr              ON tr.id = sr.tipo_ruolo_id
  LEFT  JOIN config.tipi_soggetto_dettaglio td ON td.id = s.tipo_soggetto_dettaglio_id
  LEFT  JOIN config.tipi_soggetto ts           ON ts.id = td.tipo_soggetto_id
  LEFT  JOIN config.titoli_cortesia tc         ON tc.id = s.titolo_cortesia_id
  LEFT  JOIN dati_societari ds                 ON ds.soggetto_id = s.id
  LEFT  JOIN config.forme_giuridiche fg        ON fg.id = ds.forma_giuridica_id
  LEFT  JOIN config.province pr                ON pr.id = ds.id_prov_iscri_rea
```

**Step di sviluppo Fase 1**:

| Step | Azione                                                                                                | Stato          |
| ---- | ----------------------------------------------------------------------------------------------------- | -------------- |
| 1.1  | Creare file migrazione Liquibase per la funzione                                                      | **Completato** |
| 1.2  | Scrivere la funzione SQL `RETURNS TABLE` con tutti i join                                             | **Completato** |
| 1.3  | Applicare migrazione su DB dev e verificare output                                                    | **Completato** |
| 1.4  | Scrivere test pgTAP (PF senza dati societari, PG con dati societari, ruolo inesistente, guard NULL/0) | **Completato** |
| 1.5  | Scrivere documentazione manuale                                                                       | **Completato** |

**File migrazione**: `db/changelog/migrations_v2/20_code/script/20260309-01-create-fn-get-soggetto-dati-by-ruolo-mctit.yaml`
**File test pgTAP**: `db/pgtap/script/test-fn-get-soggetto-dati-and-user-profile.sql`
**Doc manuale**: `docs/it/dbzero/script/manual/fn_get_soggetto_dati_by_ruolo.md`

---

### Fase 2 — DB: Funzione `script.fn_get_user_profile`

**Scopo**: dato `auth_user_id`, restituire il profilo completo dell'utente con i dati
del suo soggetto, della risorsa umana, e della ditta/emittente associata.
Output JSONB per massima flessibilita' e facile estendibilita' futura.

**Input**: `p_auth_user_id INTEGER`

**Output** (JSONB):

```json
{
  "utente": {
    "auth_user_id": 1,
    "username": "mtitini",
    "first_name": "Michele",
    "last_name": "Titini",
    "email": "m@example.com"
  },
  "ruolo_sistema": "ADMIN",
  "risorse_umane": {
    "risorsa_umana_id": 5,
    "risorse_umane_auth_user_id": 3,
    "soggetto_ruolo_id": 12,
    "qualifica_id": 2,
    "qualifica_codice": "DEV",
    "qualifica_descrizione": "Sviluppatore",
    "unita_organizzativa_id": 3,
    "unita_organizzativa_codice": "IT",
    "unita_organizzativa_descrizione": "Information Technology",
    "valido_dal": "2024-01-01",
    "valido_al": null,
    "attivo": true
  },
  "soggetto": {
    "soggetto_id": "019...",
    "soggetto_ruolo_id": 12,
    "tipo_ruolo_id": 4,
    "tipo_ruolo_codice": "RU",
    "tipo_ruolo_codice_interno": "RISORSA_UMANA",
    "tipo_ruolo_descrizione": "Risorsa Umana",
    "soggetto_codice": "S00001",
    "ragione_sociale_completa": "Titini Michele",
    "cognome": "Titini",
    "nome": "Michele",
    "codice_fiscale": "TTNMCL...",
    "partita_iva": null,
    "id_fiscale_univoco_cf_piva": "TTNMCL...",
    "sesso": "M",
    "data_nascita": "1970-01-15",
    "soggetto_attivo": true,
    "stato_id": 1,
    "comune_id": 42,
    "titolo_cortesia_id": 1,
    "tipo_soggetto_dettaglio_id": 1,
    "default_contatto_id": 7,
    "tipo_soggetto_id": "PF",
    "tipo_soggetto_descrizione": "Persona Fisica",
    "titolo_cortesia_descrizione": "Signore",
    "has_dati_societari": false,
    "dati_societari_id": null
  },
  "emittente": {
    "emittente_fiscale_id": 1,
    "emittente_fiscale_uid": "019...",
    "emittente_codice": "EF01",
    "emittente_descrizione": "Emittente Principale",
    "user_emittente_fiscale_id": 8,
    "regime_fiscale_rf": "RF01",
    "valuta_id": 1,
    "soggetto_id": "019...",
    "soggetto_ruolo_id": 25,
    "tipo_ruolo_id": 7,
    "tipo_ruolo_codice_interno": "EMITTENTE_FISCALE",
    "soggetto_codice": "S00010",
    "ragione_sociale_completa": "Azienda SRL",
    "partita_iva": "01234567890",
    "codice_fiscale": "01234567890",
    "id_fiscale_univoco_cf_piva": "01234567890",
    "tipo_soggetto_id": "PG",
    "tipo_soggetto_descrizione": "Persona Giuridica",
    "soggetto_attivo": true,
    "has_dati_societari": true,
    "dati_societari_id": 3,
    "forma_giuridica_id": 2,
    "forma_giuridica_codice": "SRL",
    "forma_giuridica_descrizione": "Societa' a responsabilita' limitata",
    "capitale_sociale": 10000.00,
    "destinatario_fe": "ABCDEFG",
    "pec_fatturazione": "azienda@pec.it",
    "codice_sdi": "ABCDEFG",
    "iscrizione_rea": "MI-1234567",
    "id_prov_iscri_rea": 15,
    "provincia_iscri_rea_sigla": "MI"
  }
}
```

**Logica**:

1. Leggere `auth_user` (id, username, first_name, last_name, email)
2. Risolvere `risorse_umane_auth_user` -> `risorse_umane` (con qualifica e UO)
3. Dal `soggetto_ruolo_id` della risorsa umana, chiamare `fn_get_soggetto_dati_by_ruolo()` per i dati soggetto utente
4. Risolvere emittente: da `config.user_emittenti_fiscali` (primo attivo), oppure emittente unico se whitelist vuota e ce n'e' solo uno attivo
5. Se emittente trovato: leggere `emittenti_fiscali` (id, uid, codice, descrizione, regime_fiscale_rf, valuta_id), poi chiamare `fn_get_soggetto_dati_by_ruolo(ef.soggetto_ruolo_id)` per i dati soggetto ditta
6. Comporre il JSONB di risposta aggregando i blocchi

**Step di sviluppo Fase 2**:

| Step | Azione                                                                 | Stato          |
| ---- | ---------------------------------------------------------------------- | -------------- |
| 2.1  | Creare file migrazione Liquibase per la funzione                       | **Completato** |
| 2.2  | Scrivere la funzione SQL che orchestra le sub-query e compone JSONB    | **Completato** |
| 2.3  | Guard: `auth_user_id` non nullo e > 0, utente esistente                | **Completato** |
| 2.4  | Guard: risorsa_umana_auth_user deve esistere, altrimenti errore chiaro | **Completato** |
| 2.5  | Gestire caso "nessun emittente": sezione `emittente` = `null`          | **Completato** |
| 2.6  | Applicare migrazione su DB dev e verificare output                     | **Completato** |
| 2.7  | Scrivere test pgTAP (profilo completo, blocchi JSONB, guard errore)    | **Completato** |
| 2.8  | Scrivere documentazione manuale                                        | **Completato** |

**File migrazione**: `db/changelog/migrations_v2/20_code/script/20260309-02-create-fn-get-user-profile-mctit.yaml`
**File test pgTAP**: `db/pgtap/script/test-fn-get-soggetto-dati-and-user-profile.sql` (condiviso con Fase 1)
**Doc manuale**: `docs/it/dbzero/script/manual/fn_get_user_profile.md`

---

### Fase 3 — Backend Django: Endpoint `GET /api/v1/core/me/`

**Scopo**: esporre il profilo utente completo via API REST.

**Implementazione**:

| File                                      | Azione       | Dettaglio                                                                |
| ----------------------------------------- | ------------ | ------------------------------------------------------------------------ |
| `backend/apps/core/db/core_repository.py` | **Modifica** | Aggiungere metodo `get_user_profile(auth_user_id)` — chiama la fn DB     |
| `backend/apps/core/api/me_view.py`        | **Nuovo**    | `UserProfileView(APIView)` — GET con JWT                                 |
| `backend/apps/core/api/urls_v1.py`        | **Modifica** | Aggiungere `path("me/", UserProfileView.as_view(), name="user-profile")` |

**Dettagli `UserProfileView`**:
- Metodo: `GET` (autenticazione JWT richiesta)
- Chiama `SELECT script.fn_get_user_profile(%s)` via repository
- Restituisce il JSONB dalla funzione DB
- Decoratore `@extend_schema` con schema response documentato
- Nessuna logica business nel backend — solo orchestrazione

**Dettagli repository**:

```python
# Scopo: recuperare il profilo completo dell'utente dal DB via fn_get_user_profile
def get_user_profile(self, auth_user_id: int) -> dict:
    with connection.cursor() as cursor:
        cursor.execute("SELECT script.fn_get_user_profile(%s)", [auth_user_id])
        row = cursor.fetchone()
        assert row is not None
        return row[0]  # JSONB -> dict Python
```

**Step di sviluppo Fase 3**:

| Step | Azione                                                            | Stato          |
| ---- | ----------------------------------------------------------------- | -------------- |
| 3.1  | Aggiungere metodo `get_user_profile()` nel repository core        | **Completato** |
| 3.2  | Creare `me_view.py` con `UserProfileView`                         | **Completato** |
| 3.3  | Aggiungere `@extend_schema` con response schema JSONB documentato | **Completato** |
| 3.4  | Registrare rotta in `urls_v1.py`                                  | **Completato** |
| 3.5  | Scrivere test Django (mock DB, verifica struttura risposta)       | **Completato** |
| 3.6  | Smoke test manuale con curl/httpie                                | **Completato** |

**File creati/modificati Fase 3**:

- `backend/apps/core/db/core_repository.py` — **Nuovo** — metodo `get_user_profile(auth_user_id)`
- `backend/apps/core/api/me_view.py` — **Nuovo** — `UserProfileView(APIView)` con `@extend_schema`
- `backend/apps/core/api/urls_v1.py` — **Modificato** — aggiunta rotta `me/`
- `backend/apps/core/tests/api/test_me_view.py` — **Nuovo** — 5 test (3 view + 2 repository)

---

### Fase 4 — Frontend: Store e UI

**Scopo**: consumare `/api/v1/core/me/` e mostrare i dati nell'interfaccia.

| File                                          | Azione                   | Dettaglio                                                                      |
| --------------------------------------------- | ------------------------ | ------------------------------------------------------------------------------ |
| `frontend/src/stores/auth.js`                 | **Modifica**             | Mappare risposta `/me/` a `user` con struttura completa (soggetto + emittente) |
| `frontend/src/core/components/AppTopbar.vue`  | **Modifica**             | Mostrare ragione_sociale emittente (ditta)                                     |
| `frontend/src/core/components/AppSidebar.vue` | **Modifica** (opzionale) | Mostrare nome utente nel footer                                                |
| `frontend/src/locales/it.json`                | **Modifica**             | Aggiungere chiavi i18n per labels profilo                                      |
| `frontend/src/locales/en.json`                | **Modifica**             | Aggiungere chiavi i18n per labels profilo                                      |

**Struttura dati nello store auth** (riflette il JSONB dalla Fase 2):

```javascript
user: {
  // -- blocco utente --
  auth_user_id: Number,
  username: String,
  first_name: String,
  last_name: String,
  email: String,
  ruolo_sistema: String,           // "ADMIN" | "OPERATIVO" | "DISABILITATO"

  // -- blocco risorse_umane --
  risorse_umane: {
    risorsa_umana_id: Number,
    risorse_umane_auth_user_id: Number,
    soggetto_ruolo_id: Number,
    qualifica_id: Number,
    qualifica_codice: String,
    qualifica_descrizione: String,
    unita_organizzativa_id: Number | null,
    unita_organizzativa_codice: String | null,
    unita_organizzativa_descrizione: String | null,
    valido_dal: String,            // ISO date
    valido_al: String | null,
    attivo: Boolean,
  },

  // -- blocco soggetto (dati identita' utente) --
  soggetto: {
    soggetto_id: String,           // UUID
    soggetto_ruolo_id: Number,
    tipo_ruolo_id: Number,
    tipo_ruolo_codice_interno: String,
    soggetto_codice: String,
    ragione_sociale_completa: String,
    cognome: String,
    nome: String,
    codice_fiscale: String,
    partita_iva: String | null,
    id_fiscale_univoco_cf_piva: String,
    sesso: String,
    data_nascita: String | null,
    soggetto_attivo: Boolean,
    stato_id: Number | null,
    comune_id: Number | null,
    titolo_cortesia_id: Number | null,
    tipo_soggetto_dettaglio_id: Number | null,
    default_contatto_id: Number | null,
    tipo_soggetto_id: String,      // "PF" | "PG" | "ENTE"
    tipo_soggetto_descrizione: String,
    has_dati_societari: Boolean,
    // ... dati_societari se presenti (tutti i campi della Fase 1)
  },

  // -- blocco emittente (dati ditta/emittente fiscale) — null se non associato --
  emittente: {
    emittente_fiscale_id: Number,
    emittente_fiscale_uid: String,   // UUID
    emittente_codice: String,
    emittente_descrizione: String,
    user_emittente_fiscale_id: Number,
    regime_fiscale_rf: String,
    valuta_id: Number,
    // ... tutti i campi soggetto da fn_get_soggetto_dati_by_ruolo
    soggetto_id: String,
    soggetto_ruolo_id: Number,
    ragione_sociale_completa: String,
    partita_iva: String,
    has_dati_societari: Boolean,
    forma_giuridica_codice: String,
    codice_sdi: String,
    pec_fatturazione: String,
    // ... etc.
  } | null
}
```

**Step di sviluppo Fase 4**:

| Step | Azione                                                           | Stato          |
| ---- | ---------------------------------------------------------------- | -------------- |
| 4.1  | Aggiornare `fetchProfile()` nello store auth per chiamare `/me/` | **Completato** |
| 4.2  | Mappare risposta JSONB nello stato del store                     | **Completato** |
| 4.3  | Mostrare nome utente e ragione_sociale emittente nella topbar    | **Completato** |
| 4.4  | Aggiungere chiavi i18n (`it.json`, `en.json`)                    | **Completato** |
| 4.5  | Verificare che il fallback (emittente null) non rompa la UI      | **Completato** |
| 4.6  | Test manuale end-to-end (login -> profilo visibile)              | **Completato** |

---

## Decisioni Aperte

| #   | Domanda                                                 | Opzioni                                                                 | Decisione                                                             |
| --- | ------------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------------- |
| 1   | Output `fn_get_user_profile`: JSONB o record composito? | JSONB (flessibile, facile da estendere) vs RECORD (tipizzato, validato) | **JSONB** — scelto per flessibilita' e facilita' di estensione futura |
| 2   | Emittente multipli: quale mostrare?                     | Primo attivo dalla whitelist / emittente selezionabile / tutti          | **Primo attivo dalla whitelist** — fallback: se nessuna riga in whitelist e un solo emittente attivo, usa quello; se multipli senza whitelist → null |
| 3   | Caching frontend del profilo                            | Salvare in localStorage? Refresh a ogni login?                          | **Solo in-memory Pinia** — token in localStorage, profilo solo nello state Pinia. Ri-caricato al login e al navigation guard se assente |
| 4   | Mostrare pannello profilo utente?                       | Solo topbar/sidebar o anche pagina dedicata `/profilo`?                 | **Solo topbar/sidebar** — emittente in AppTopbar, nome utente in HomeView. Nessuna pagina dedicata per ora |

---

## Sequenza di Sviluppo

```
[Fase 1] fn_get_soggetto_dati_by_ruolo (DB)              ✅ COMPLETATA
  Step 1.1 → 1.5
    |
    v
[Fase 2] fn_get_user_profile (DB) — dipende da Fase 1    ✅ COMPLETATA
  Step 2.1 → 2.8
    |
    v
[Fase 3] Endpoint /api/v1/core/me/ (Backend)              ✅ COMPLETATA
  Step 3.1 → 3.6
    |
    v
[Fase 4] Store + UI profilo (Frontend)                    ✅ COMPLETATA
  Step 4.1 → 4.6
```

Le fasi sono sequenziali: ogni livello dipende dal precedente.
Totale: **25 step** (5 + 8 + 6 + 6). Completati: **25/25** — tutte le fasi completate e testate.

---

## Riferimenti

- Vista modello soggetti+ruoli: `anagrafiche.vw_soggetti_ruoli_dettaglio` — colonne soggetto + tipo_ruolo + titolo_cortesia
- Vista modello dati societari: `anagrafiche.vw_dati_societari` — colonne societarie + forma_giuridica + provincia REA
- Vista modello risorse umane: `anagrafiche.vw_risorse_umane_dettaglio` — colonne risorsa + soggetto + qualifica + UO
- Funzione contatti: `script.fn_get_contatti` — recupero contatti multilivello (per estensione futura)
- Funzione indirizzi: `script.fn_get_indirizzi_by_soggetto/ruolo` — indirizzi per livello (per estensione futura)
- Guida soggetti e ruoli: `docs/it/dbzero/anagrafiche/manual/soggetti.md`
- Guida emittenti fiscali: `docs/it/dbzero/anagrafiche/manual/emittenti_fiscali.md`
- Guida risorse umane: `docs/it/dbzero/anagrafiche/manual/risorse_umane_auth_user.md`
- Permission resolver: `backend/apps/core/services/permissions_resolver.py`
- Store auth frontend: `frontend/src/stores/auth.js`
- Frontend standards: `docs/it/frontend/frontend-standards.md`

---

### Fase 5 — Gestione Sessioni Attive (Sicurezza)

**Scopo**: permettere all'utente di visualizzare le proprie sessioni attive e revocare
quelle sospette. Funzionalita' tipica di sicurezza ERP: l'utente verifica se ci sono
sessioni non riconosciute (accessi non autorizzati) e puo' disconnetterle.

Il backend identifica la sessione corrente confrontando il JTI del token della request
e la **esclude** dalla lista restituita dall'API. L'endpoint `GET /me/sessioni/` restituisce
quindi solo le **altre** sessioni attive. Il pannello nella HomeView e' visibile solo se la
lista non e' vuota (almeno 1 sessione diversa dalla corrente). Ogni riga ha pulsante "Revoca".

#### 5.1 Infrastruttura gia' presente

| Elemento                                    | Stato | Dove                                                          |
| ------------------------------------------- | ----- | ------------------------------------------------------------- |
| Tabella `dbops.sessioni_utente`             | OK    | Eventi: LOGIN, REFRESH, LOGOUT, SCADENZA, REVOCA              |
| Registrazione LOGIN/REFRESH automatica      | OK    | `AuditTokenObtainPairView`, `AuditTokenRefreshView`           |
| Tracciamento IP, User-Agent, JTI            | OK    | `session_audit_service.py` + `request_context.py`             |
| Token blacklist SimpleJWT                   | OK    | `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True` |
| Correlazione `request_id` con `request_log` | OK    | Join per timeline completa                                    |
| Indici per query per utente e cronologiche  | OK    | `ix_sessioni_utente_auth_user_id`, `ix_sessioni_utente_jti`   |
| `REFRESH_TOKEN_LIFETIME = 1 day`            | OK    | `zeroerp_backend/settings.py` — definisce il TTL sessione     |

#### 5.2 Cosa manca

| Elemento                                               | Note                                                                                 |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| Determinazione "sessione attiva"                       | Serve logica: LOGIN/REFRESH senza successivo LOGOUT/REVOCA/SCADENZA, entro TTL token |
| `record_logout()` e `record_revoca()`                  | Funzioni da aggiungere al service — non richiamate da nessun endpoint                |
| Endpoint `POST /api/v1/auth/logout/`                   | Blacklista token corrente + registra evento LOGOUT                                   |
| Endpoint `GET /api/v1/core/me/sessioni/`               | Lista sessioni attive per utente corrente                                            |
| Endpoint `POST /api/v1/core/me/sessioni/<jti>/revoca/` | Revoca sessione specifica (blacklist + evento REVOCA)                                |
| Query sessioni attive nel repository                   | CTE aggregata con stato derivato (no vista DB — logica nel repository Python)        |
| UI frontend pannello sessioni nella HomeView           | Pannello condizionale: visibile solo se ci sono sessioni diverse dalla corrente      |

#### 5.3 Decisioni architetturali Fase 5

| #   | Domanda                                 | Decisione                                                                                        |
| --- | --------------------------------------- | ------------------------------------------------------------------------------------------------ |
| 5   | TTL sessione attiva                     | **Allineato a `REFRESH_TOKEN_LIFETIME` (1 giorno)** — la query filtra `data_insert > now() - interval '1 day'` |
| 6   | Parsing User-Agent                      | **Lato frontend (JS)** — il backend restituisce il raw user_agent, il frontend fa parsing leggero per mostrare browser/OS |
| 7   | Batch "disconnetti tutte le altre"      | **Fase successiva** — per ora solo revoca singola sessione                                       |
| 8   | Vista DB vs query nel repository        | **Query nel repository** — nessun sviluppo DB richiesto; la CTE vive nel metodo Python           |
| 9   | Dove mostrare le sessioni               | **HomeView** — pannello visibile solo se l'API restituisce 1+ sessioni (la corrente e' gia' esclusa dal backend) |

#### 5.4 Backend: Repository — Query sessioni attive e revoca

**File**: `backend/apps/core/db/session_audit_repository.py` (modifica)

**Metodo `list_sessioni_attive(auth_user_id)`**:

```python
# Scopo: Recupera le sessioni attive per un utente.
# Una sessione e' attiva se l'ultimo evento per quel jti e' LOGIN o REFRESH
# e il timestamp e' entro il TTL del refresh token (1 giorno).
def list_sessioni_attive(self, auth_user_id: int) -> list[dict[str, Any]]:
    sql = """
        WITH ranked AS (
            SELECT jti, evento, ip_address, user_agent, data_insert,
                   ROW_NUMBER() OVER (PARTITION BY jti ORDER BY data_insert DESC) AS rn
              FROM dbops.sessioni_utente
             WHERE auth_user_id = %s
               AND jti IS NOT NULL
        ),
        primo_login AS (
            SELECT jti, MIN(data_insert) AS data_inizio
              FROM dbops.sessioni_utente
             WHERE auth_user_id = %s
               AND jti IS NOT NULL
               AND evento = 'LOGIN'
          GROUP BY jti
        )
        SELECT r.jti,
               r.evento       AS ultimo_evento,
               r.ip_address::text,
               r.user_agent,
               pl.data_inizio,
               r.data_insert  AS data_ultimo_evento
          FROM ranked r
          LEFT JOIN primo_login pl ON pl.jti = r.jti
         WHERE r.rn = 1
           AND r.evento IN ('LOGIN', 'REFRESH')
           AND r.data_insert > now() - INTERVAL '1 day'
      ORDER BY r.data_insert DESC
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [auth_user_id, auth_user_id])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
```

**Nessun nuovo metodo per la revoca**: la revoca usa `log_session_event()` gia' esistente
per inserire l'evento REVOCA, piu' blacklist SimpleJWT gestita nel service/view.

#### 5.5 Backend: Service — Logout e revoca

**File**: `backend/apps/core/services/session_audit_service.py` (modifica)

Aggiungere due funzioni:

```python
# Scopo: Registra un evento LOGOUT nella tabella sessioni_utente.
# Chiamato dall'endpoint di logout dopo blacklist del token.
def record_logout(
    user_id: int,
    request: HttpRequest,
    *,
    jti: str | None = None,
    dettaglio: dict[str, Any] | None = None,
) -> None:
    _log_event(
        auth_user_id=user_id,
        evento="LOGOUT",
        request=request,
        jti=jti,
        dettaglio=dettaglio,
    )

# Scopo: Registra un evento REVOCA nella tabella sessioni_utente.
# Chiamato quando l'utente revoca una sessione remota.
def record_revoca(
    user_id: int,
    request: HttpRequest,
    *,
    jti: str | None = None,
    dettaglio: dict[str, Any] | None = None,
) -> None:
    _log_event(
        auth_user_id=user_id,
        evento="REVOCA",
        request=request,
        jti=jti,
        dettaglio=dettaglio,
    )
```

#### 5.6 Backend: API Views

**File nuovi**:

| File                                         | Classe                                          | Endpoint                                        |
| -------------------------------------------- | ----------------------------------------------- | ----------------------------------------------- |
| `backend/apps/core/api/logout_view.py`       | `LogoutView(APIView)`                           | `POST /api/v1/auth/logout/`                     |
| `backend/apps/core/api/sessioni_view.py`     | `SessioniAttiveListView(APIView)`               | `GET /api/v1/core/me/sessioni/`                 |
| `backend/apps/core/api/sessioni_view.py`     | `SessioneRevocaView(APIView)`                   | `POST /api/v1/core/me/sessioni/<jti>/revoca/`   |

**Dettaglio `LogoutView`**:

```python
class LogoutView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]

    # Scopo: Blacklista il refresh token corrente e registra evento LOGOUT.
    @extend_schema(summary="Logout utente", responses={204: None})
    def post(self, request: Request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            raise ServiceError(
                code="E_LOGOUT_NO_TOKEN",
                message="Refresh token richiesto per il logout.",
            )
        token = RefreshToken(refresh_token)
        jti = str(token.get("jti", ""))
        token.blacklist()
        session_audit_service.record_logout(
            user_id=request.user.id,
            request=request._request,
            jti=jti,
        )
        return Response(status=204)
```

**Dettaglio `SessioniAttiveListView`**:

```python
class SessioniAttiveListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]

    # Scopo: Lista le sessioni attive dell'utente corrente, escludendo quella corrente.
    # Il frontend mostra il pannello solo se la lista non e' vuota.
    @extend_schema(summary="Lista altre sessioni attive utente", responses={200: ...})
    def get(self, request: Request):
        repo = SessionAuditRepository()
        sessioni = repo.list_sessioni_attive(request.user.id)
        # Escludere la sessione corrente — il frontend mostra solo le altre
        current_jti = self._get_current_jti(request)
        altre = [s for s in sessioni if s["jti"] != current_jti]
        return success_response({"sessioni": altre, "count": len(altre)})

    @staticmethod
    def _get_current_jti(request: Request) -> str | None:
        # Il JTI e' nel payload del token JWT di accesso
        auth = request.auth  # token payload dict in SimpleJWT
        return str(auth.get("jti", "")) if auth else None
```

**Dettaglio `SessioneRevocaView`**:

```python
class SessioneRevocaView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]

    # Scopo: Revoca una sessione specifica (non la corrente) — blacklist + evento REVOCA.
    @extend_schema(summary="Revoca sessione specifica", responses={204: None})
    def post(self, request: Request, jti: str):
        # Guard: non revocare la sessione corrente
        current_jti = request.auth.get("jti", "") if request.auth else ""
        if jti == str(current_jti):
            raise ServiceError(
                code="E_SESSIONE_REVOCA_CORRENTE",
                message="Non puoi revocare la sessione corrente. Usa il logout.",
            )
        # Blacklist via OutstandingToken di SimpleJWT
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken, OutstandingToken,
        )
        try:
            outstanding = OutstandingToken.objects.get(jti=jti, user_id=request.user.id)
            BlacklistedToken.objects.get_or_create(token=outstanding)
        except OutstandingToken.DoesNotExist:
            raise ServiceError(
                code="E_SESSIONE_NOT_FOUND",
                message="Sessione non trovata o gia' revocata.",
            )
        # Registra evento REVOCA
        session_audit_service.record_revoca(
            user_id=request.user.id,
            request=request._request,
            jti=jti,
        )
        return Response(status=204)
```

**Rotte**:

```python
# In zeroerp_backend/urls.py — aggiungere sotto le rotte auth esistenti:
path("api/v1/auth/logout/", LogoutView.as_view(), name="auth-logout"),

# In apps/core/api/urls_v1.py — aggiungere:
path("me/sessioni/", SessioniAttiveListView.as_view(), name="core-v1-sessioni-attive"),
path("me/sessioni/<str:jti>/revoca/", SessioneRevocaView.as_view(), name="core-v1-sessione-revoca"),
```

#### 5.7 Backend: Error policies

**File**: `backend/apps/core/services/error_policies.py` (modifica)

```python
"E_LOGOUT_NO_TOKEN": ErrorPolicy(
    code="E_LOGOUT_NO_TOKEN",
    http_status=400,
    ui_action="show_error_banner",
    user_message="Token di refresh richiesto per il logout.",
),
"E_SESSIONE_NOT_FOUND": ErrorPolicy(
    code="E_SESSIONE_NOT_FOUND",
    http_status=404,
    ui_action="show_error_banner",
    user_message="Sessione non trovata o gia' revocata.",
),
"E_SESSIONE_REVOCA_CORRENTE": ErrorPolicy(
    code="E_SESSIONE_REVOCA_CORRENTE",
    http_status=400,
    ui_action="show_error_banner",
    user_message="Non puoi revocare la sessione corrente. Usa il logout.",
),
```

#### 5.8 Backend: Test Django (CI-compatible, mock DB)

**File**: `backend/apps/core/tests/api/test_sessioni_view.py` (nuovo)

| # | Test                                                           | Cosa verifica                                              |
|---|----------------------------------------------------------------|------------------------------------------------------------|
| 1 | `LogoutViewTests.test_logout_success`                          | POST con refresh token → 204 + blacklist + evento LOGOUT   |
| 2 | `LogoutViewTests.test_logout_no_token`                         | POST senza token → 400 E_LOGOUT_NO_TOKEN                   |
| 3 | `LogoutViewTests.test_logout_chiude_sessione`                  | record_logout chiamato con evento LOGOUT → CTE esclude jti |
| 4 | `LogoutViewTests.test_logout_token_invalido_idempotente`       | POST con token malformato/scaduto → 204 idempotente        |
| 5 | `SessioniAttiveListViewTests.test_list_sessioni_success`       | GET → 200 con lista sessioni (esclusa corrente)            |
| 6 | `SessioniAttiveListViewTests.test_list_sessioni_empty`         | GET con nessuna sessione → 200 con lista vuota             |
| 7 | `SessioneRevocaViewTests.test_revoca_success`                  | POST con jti valido → 204 + blacklist + evento REVOCA      |
| 8 | `SessioneRevocaViewTests.test_revoca_sessione_corrente`        | POST con jti corrente → 400 E_SESSIONE_REVOCA_CORRENTE     |
| 9 | `SessioneRevocaViewTests.test_revoca_sessione_not_found`       | POST con jti inesistente → 404 E_SESSIONE_NOT_FOUND        |
| 10| `SessionAuditRepositoryTests.test_list_sessioni_attive`        | Mock cursor → verifica struttura dizionari restituiti       |

**File**: `backend/apps/core/tests/services/test_session_audit_service.py` (nuovo)

| # | Test                                                          | Cosa verifica                                              |
|---|---------------------------------------------------------------|------------------------------------------------------------|
| 10 | `SessionAuditServiceTests.test_record_logout`                | record_logout() chiama _log_event con evento="LOGOUT"      |
| 11 | `SessionAuditServiceTests.test_record_revoca`                | record_revoca() chiama _log_event con evento="REVOCA"      |

#### 5.9 Frontend: Pannello sessioni in HomeView

**Componente**: `frontend/src/core/components/SessioniAttivePanel.vue` (nuovo)

**Comportamento**:
- Al mount della HomeView, chiama `GET /api/v1/core/me/sessioni/`
- L'API restituisce solo le sessioni **diverse** dalla corrente (gia' filtrate dal backend)
- Se la lista e' **vuota** → **pannello nascosto** (nessun'altra sessione attiva)
- Se la lista ha **1+ elementi** → pannello visibile, ogni riga con pulsante "Revoca"

```
+--------------------------------------------------------------+
| Altre sessioni attive (2)                                    |
+--------------------------------------------------------------+
| Dispositivo       | IP           | Ultimo accesso | Azione   |
| Firefox / Windows | 10.0.0.55    | 3 ore fa       | [Revoca] |
| Safari / macOS    | 85.12.34.56  | ieri           | [Revoca] |
+--------------------------------------------------------------+
```

**Dettagli UI (PrimeVue)**:
- Componente `DataTable` con colonne: Dispositivo, IP, Ultimo accesso, Azione
- Parsing User-Agent lato frontend: estrazione browser + OS dal raw user_agent (regex semplice, no librerie esterne)
- Data relativa: calcolo JS (`Intl.RelativeTimeFormat` o helper semplice)
- Pulsante "Revoca" su ogni riga (PrimeVue `Button`, severity="danger", size="small")
- Conferma revoca: `ConfirmDialog` PrimeVue prima di chiamare l'API
- Toast di successo dopo revoca + ricarica lista

**Store auth.js** (modifica):
- `logout()`: cambia da solo `clearTokens()` a `POST /api/v1/auth/logout/` + `clearTokens()`
- Nessun metodo sessioni nello store auth — la logica sessioni vive nel componente `SessioniAttivePanel.vue` con chiamate API dirette (scope limitato a HomeView)

**Chiavi i18n** (`it.json` / `en.json`):

```json
"sessions": {
  "other_active_sessions": "Altre sessioni attive",
  "device": "Dispositivo",
  "ip_address": "Indirizzo IP",
  "last_access": "Ultimo accesso",
  "action": "Azione",
  "revoke": "Revoca",
  "revoke_confirm_title": "Conferma revoca sessione",
  "revoke_confirm_message": "Vuoi revocare la sessione da {device} ({ip})?",
  "revoke_success": "Sessione revocata",
  "now": "Adesso",
  "minutes_ago": "{n} min fa",
  "hours_ago": "{n} ore fa",
  "yesterday": "Ieri",
  "days_ago": "{n} giorni fa"
}
```

#### 5.10 Smoke test e documentazione

**Smoke test**: `backend/scripts/tests/smoke-test-core.sh` — sezioni aggiunte:

- Test #10: lista sessioni `GET /api/v1/core/me/sessioni/` → 200
- Test #11: logout `POST /api/v1/auth/logout/` → 204 (secondo login dedicato)
- Test #12: logout idempotente (token gia' blacklistato) → 204
- (revoca non testabile facilmente in smoke test — richiede setup JTI)

**Documentazione backend**: `docs/it/backend/core/manual/`
- `api_logout.md` — endpoint logout
- `api_sessioni_attive.md` — endpoint lista sessioni + revoca

---

#### Step di sviluppo Fase 5

| Step | Azione                                                                     | Stato       |
| ---- | -------------------------------------------------------------------------- | ----------- |
| 5.1  | Aggiungere `record_logout()` e `record_revoca()` al session_audit_service | **Completato** |
| 5.2  | Aggiungere `list_sessioni_attive()` al session_audit_repository            | **Completato** |
| 5.3  | Aggiungere error policies (E_LOGOUT_NO_TOKEN, E_SESSIONE_*)               | **Completato** |
| 5.4  | Creare `logout_view.py` con `LogoutView`                                  | **Completato** |
| 5.5  | Creare `sessioni_view.py` con `SessioniAttiveListView` + `SessioneRevocaView` | **Completato** |
| 5.6  | Registrare rotte (urls.py + urls_v1.py)                                   | **Completato** |
| 5.7  | Scrivere test Django — 19 test (10 view + 9 service)                      | **Completato** |
| 5.8  | Aggiungere `logout()` con API call nello store auth.js                    | **Completato** |
| 5.9  | Creare `SessioniAttivePanel.vue` e integrarlo in HomeView                 | **Completato** |
| 5.10 | Aggiungere chiavi i18n (`it.json`, `en.json`)                             | **Completato** |
| 5.11 | Aggiornare smoke test                                                     | **Completato** |
| 5.12 | Scrivere documentazione backend (manual/)                                 | **Completato** |

**File coinvolti Fase 5**:

| File                                                         | Azione       |
| ------------------------------------------------------------ | ------------ |
| `backend/apps/core/services/session_audit_service.py`        | **Modifica** |
| `backend/apps/core/db/session_audit_repository.py`           | **Modifica** |
| `backend/apps/core/services/error_policies.py`               | **Modifica** |
| `backend/apps/core/api/logout_view.py`                       | **Nuovo**    |
| `backend/apps/core/api/sessioni_view.py`                     | **Nuovo**    |
| `backend/apps/core/api/urls_v1.py`                           | **Modifica** |
| `backend/zeroerp_backend/urls.py`                            | **Modifica** |
| `backend/apps/core/tests/api/test_sessioni_view.py`          | **Nuovo**    |
| `backend/apps/core/tests/services/test_session_audit_service.py` | **Nuovo** |
| `frontend/src/stores/auth.js`                                | **Modifica** |
| `frontend/src/core/components/SessioniAttivePanel.vue`       | **Nuovo**    |
| `frontend/src/core/views/HomeView.vue`                       | **Modifica** |
| `frontend/src/locales/it.json`                               | **Modifica** |
| `frontend/src/locales/en.json`                               | **Modifica** |
| `backend/scripts/tests/smoke-test-core.sh`                   | **Modifica** |
| `docs/it/backend/core/manual/api_logout.md`                  | **Nuovo**    |
| `docs/it/backend/core/manual/api_sessioni_attive.md`         | **Nuovo**    |

---

## Decisioni (tutte chiuse)

| #   | Domanda                                                 | Opzioni                                                                 | Decisione                                                             |
| --- | ------------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------------- |
| 1   | Output `fn_get_user_profile`: JSONB o record composito? | JSONB (flessibile, facile da estendere) vs RECORD (tipizzato, validato) | **JSONB** — scelto per flessibilita' e facilita' di estensione futura |
| 2   | Emittente multipli: quale mostrare?                     | Primo attivo dalla whitelist / emittente selezionabile / tutti          | **Primo attivo dalla whitelist** — fallback: se nessuna riga in whitelist e un solo emittente attivo, usa quello; se multipli senza whitelist → null |
| 3   | Caching frontend del profilo                            | Salvare in localStorage? Refresh a ogni login?                          | **Solo in-memory Pinia** — token in localStorage, profilo solo nello state Pinia. Ri-caricato al login e al navigation guard se assente |
| 4   | Mostrare pannello profilo utente?                       | Solo topbar/sidebar o anche pagina dedicata `/profilo`?                 | **Solo topbar/sidebar** — emittente in AppTopbar, nome utente in HomeView. Nessuna pagina dedicata per ora |
| 5   | TTL sessione attiva                                     | Allineare a `REFRESH_TOKEN_LIFETIME` (1 giorno) o parametrizzare?       | **1 giorno** — allineato a REFRESH_TOKEN_LIFETIME                     |
| 6   | Parsing User-Agent                                      | Lato backend (libreria Python) o lato frontend (JS)?                    | **Frontend (JS)** — regex semplice, no dipendenze extra               |
| 7   | Batch "disconnetti tutte le altre"                      | Implementare subito o in fase successiva?                               | **Fase successiva** — per ora solo revoca singola                     |

---

## Sequenza di Sviluppo

```
[Fase 1] fn_get_soggetto_dati_by_ruolo (DB)              ✅ COMPLETATA
  Step 1.1 → 1.5
    |
    v
[Fase 2] fn_get_user_profile (DB) — dipende da Fase 1    ✅ COMPLETATA
  Step 2.1 → 2.8
    |
    v
[Fase 3] Endpoint /api/v1/core/me/ (Backend)              ✅ COMPLETATA
  Step 3.1 → 3.6
    |
    v
[Fase 4] Store + UI profilo (Frontend)                    ✅ COMPLETATA
  Step 4.1 → 4.6
    |
    v
[Fase 5] Sessioni attive (Backend + Frontend)             ✅ COMPLETATA
  Step 5.1 → 5.12
```

Le fasi sono sequenziali: ogni livello dipende dal precedente.
Totale: **37 step** (5 + 8 + 6 + 6 + 12). Completati: **37/37** — tutte le fasi completate e testate funzionalmente.

---

## Riferimenti

- Guida soggetti e ruoli: `docs/it/dbzero/anagrafiche/manual/soggetti.md`
- Guida emittenti fiscali: `docs/it/dbzero/anagrafiche/manual/emittenti_fiscali.md`
- Guida risorse umane: `docs/it/dbzero/anagrafiche/manual/risorse_umane_auth_user.md`
- Permission resolver: `backend/apps/core/services/permissions_resolver.py`
- Store auth frontend: `frontend/src/stores/auth.js`
- Frontend standards: `docs/it/frontend/frontend-standards.md`
- Audit sessioni e request logging: `docs/it/dev/work-done/Audit-logging-sessionii-request-token.md`
- Schema tabella sessioni: `docs/it/dbzero/dbops/tabelle/sessioni_utente.md`
- Doc manuale sessioni: `docs/it/dbzero/dbops/manual/sessioni_utente.md`
