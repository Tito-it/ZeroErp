# Profilo Utente e Dati Soggetto — Piano di Implementazione (WIP)

> Documento di lavoro per l'implementazione dell'esposizione dei dati soggetto
> (utente e ditta/emittente fiscale) nel frontend Vue.
>
> Data inizio: 2026-03-09

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
                                |   esigibilita_iva_default, split_payment_default,
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

| Step | Azione                                                            | Stato       |
| ---- | ----------------------------------------------------------------- | ----------- |
| 3.1  | Aggiungere metodo `get_user_profile()` nel repository core        | **Da fare** |
| 3.2  | Creare `me_view.py` con `UserProfileView`                         | **Da fare** |
| 3.3  | Aggiungere `@extend_schema` con response schema JSONB documentato | **Da fare** |
| 3.4  | Registrare rotta in `urls_v1.py`                                  | **Da fare** |
| 3.5  | Scrivere test Django (mock DB, verifica struttura risposta)       | **Da fare** |
| 3.6  | Smoke test manuale con curl/httpie                                | **Da fare** |

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

| Step | Azione                                                           | Stato       |
| ---- | ---------------------------------------------------------------- | ----------- |
| 4.1  | Aggiornare `fetchProfile()` nello store auth per chiamare `/me/` | **Da fare** |
| 4.2  | Mappare risposta JSONB nello stato del store                     | **Da fare** |
| 4.3  | Mostrare nome utente e ragione_sociale emittente nella topbar    | **Da fare** |
| 4.4  | Aggiungere chiavi i18n (`it.json`, `en.json`)                    | **Da fare** |
| 4.5  | Verificare che il fallback (emittente null) non rompa la UI      | **Da fare** |
| 4.6  | Test manuale end-to-end (login -> profilo visibile)              | **Da fare** |

---

## Decisioni Aperte

| #   | Domanda                                                 | Opzioni                                                                 | Decisione                                                             |
| --- | ------------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------------- |
| 1   | Output `fn_get_user_profile`: JSONB o record composito? | JSONB (flessibile, facile da estendere) vs RECORD (tipizzato, validato) | **JSONB** — scelto per flessibilita' e facilita' di estensione futura |
| 2   | Emittente multipli: quale mostrare?                     | Primo attivo dalla whitelist / emittente selezionabile / tutti          | **Da decidere**                                                       |
| 3   | Caching frontend del profilo                            | Salvare in localStorage? Refresh a ogni login?                          | **Da decidere**                                                       |
| 4   | Mostrare pannello profilo utente?                       | Solo topbar/sidebar o anche pagina dedicata `/profilo`?                 | **Da decidere**                                                       |

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
[Fase 3] Endpoint /api/v1/core/me/ (Backend) — dipende da Fase 2
  Step 3.1 → 3.6
    |
    v
[Fase 4] Store + UI (Frontend) — dipende da Fase 3
  Step 4.1 → 4.6
```

Le fasi sono sequenziali: ogni livello dipende dal precedente.
Totale: **25 step** (5 + 8 + 6 + 6). Fasi DB completate: **13/25**.

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

#### 5.1 Infrastruttura gia' presente

| Elemento                                    | Stato | Dove                                                          |
| ------------------------------------------- | ----- | ------------------------------------------------------------- |
| Tabella `dbops.sessioni_utente`             | OK    | Eventi: LOGIN, REFRESH, LOGOUT, SCADENZA, REVOCA              |
| Registrazione LOGIN/REFRESH automatica      | OK    | `AuditTokenObtainPairView`, `AuditTokenRefreshView`           |
| Tracciamento IP, User-Agent, JTI            | OK    | `session_audit_service.py` + `request_context.py`             |
| Token blacklist SimpleJWT                   | OK    | `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True` |
| Correlazione `request_id` con `request_log` | OK    | Join per timeline completa                                    |
| Indici per query per utente e cronologiche  | OK    | `ix_sessioni_utente_auth_user_id`, `ix_sessioni_utente_jti`   |

#### 5.2 Cosa manca

| Elemento                                               | Note                                                                                 |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| Determinazione "sessione attiva"                       | Serve logica: LOGIN/REFRESH senza successivo LOGOUT/REVOCA/SCADENZA, entro TTL token |
| `record_logout()` e `record_revoca()`                  | Funzioni definite nel service ma non richiamate da nessun endpoint                   |
| Endpoint `POST /api/v1/auth/logout/`                   | Blacklista token corrente + registra evento LOGOUT                                   |
| Endpoint `GET /api/v1/core/me/sessioni/`               | Lista sessioni attive per utente corrente                                            |
| Endpoint `POST /api/v1/core/me/sessioni/{jti}/revoca/` | Revoca sessione specifica (blacklist + evento REVOCA)                                |
| Vista DB o funzione per sessioni attive                | Query aggregata con stato derivato                                                   |
| UI frontend pannello sessioni                          | Dialog/pagina con lista sessioni e azione revoca                                     |

#### 5.3 DB: Vista `dbops.vw_sessioni_utente_attive`

**Scopo**: esporre le sessioni considerate "attive" per un utente. Una sessione e' attiva
se l'ultimo evento per quel `jti` e' LOGIN o REFRESH e il token non e' scaduto.

**Logica**:
```sql
-- Per ogni jti, trovare l'ultimo evento
-- Se ultimo evento IN ('LOGIN', 'REFRESH') AND data_insert > now() - refresh_ttl
-- => sessione attiva
WITH ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY jti ORDER BY data_insert DESC) AS rn
      FROM dbops.sessioni_utente
     WHERE jti IS NOT NULL
)
SELECT auth_user_id, jti, evento, ip_address, user_agent, data_insert
  FROM ranked
 WHERE rn = 1
   AND evento IN ('LOGIN', 'REFRESH')
   AND data_insert > now() - INTERVAL '1 day';  -- allineato a REFRESH_TOKEN_LIFETIME
```

**Colonne esposte**:

| Colonna              | Tipo        | Note                                                 |
| -------------------- | ----------- | ---------------------------------------------------- |
| `auth_user_id`       | INTEGER     | Utente proprietario                                  |
| `jti`                | TEXT        | Identificativo sessione (JWT ID)                     |
| `ultimo_evento`      | TEXT        | LOGIN o REFRESH                                      |
| `ip_address`         | INET        | IP ultimo evento                                     |
| `user_agent`         | TEXT        | Browser/device ultimo evento                         |
| `data_inizio`        | TIMESTAMPTZ | Primo LOGIN per quel jti                             |
| `data_ultimo_evento` | TIMESTAMPTZ | Ultimo LOGIN/REFRESH                                 |
| `is_current`         | BOOLEAN     | Utile nel frontend per evidenziare "questa sessione" |

#### 5.4 Backend: API sessioni

**Endpoint `POST /api/v1/auth/logout/`**:
- Blacklista il refresh token corrente (SimpleJWT `token.blacklist()`)
- Registra evento LOGOUT in `sessioni_utente`
- Restituisce 204 No Content

**Endpoint `GET /api/v1/core/me/sessioni/`**:
- Query su `vw_sessioni_utente_attive` filtrata per `request.user.id`
- Aggiunge flag `is_current` confrontando il JTI del token della request
- Restituisce lista sessioni con IP, User-Agent, data

**Endpoint `POST /api/v1/core/me/sessioni/{jti}/revoca/`**:
- Verifica che il JTI appartenga all'utente corrente (guard)
- NON permettere revoca della sessione corrente (usare logout per quello)
- Blacklista il token via `OutstandingToken` + `BlacklistedToken`
- Registra evento REVOCA in `sessioni_utente`
- Restituisce 204 No Content

| File                                                  | Azione                                                                  |
| ----------------------------------------------------- | ----------------------------------------------------------------------- |
| `backend/apps/core/api/logout_view.py`                | **Nuovo** — `LogoutView(APIView)`                                       |
| `backend/apps/core/api/sessioni_view.py`              | **Nuovo** — `SessioniAttivaListView`, `SessioneRevocaView`              |
| `backend/apps/core/api/urls_v1.py`                    | **Modifica** — aggiungere rotte                                         |
| `backend/apps/core/services/session_audit_service.py` | **Modifica** — aggiungere `record_logout()`, `record_revoca()`          |
| `backend/apps/core/db/session_audit_repository.py`    | **Modifica** — aggiungere `list_sessioni_attive()`, `revoca_sessione()` |

#### 5.5 Frontend: Pannello Sessioni

**Componente**: `frontend/src/core/components/SessioniAttiveDialog.vue`

**UI proposta** (Dialog PrimeVue):
- Titolo: "Sessioni attive" (`$t('sessions.active_sessions')`)
- Tabella con colonne:
  - Dispositivo/Browser (parsing User-Agent)
  - Indirizzo IP
  - Ultimo accesso (data relativa: "2 ore fa", "ieri")
  - Stato: badge "Sessione corrente" (evidenziata) oppure pulsante "Disconnetti"
- Azione "Disconnetti" chiama `POST /me/sessioni/{jti}/revoca/`
- Azione "Disconnetti tutte le altre" (batch revoca) — opzionale
- Accessibile da: menu utente in sidebar/topbar o pagina `/profilo`

**Esempio UI**:
```
+--------------------------------------------------------------+
| Sessioni attive                                         [X]  |
+--------------------------------------------------------------+
| Dispositivo       | IP           | Ultimo accesso | Azione |
| ----------------- | ------------ | -------------- | ------ |
| Chrome / Linux    | 192.168.1.10 | Adesso         | (tu)   |
| Firefox / Windows | 10.0.0.55    | 3 ore fa       | [Rev]  |
| Safari / macOS    | 85.12.34.56  | ieri           | [Rev]  |
+--------------------------------------------------------------+
| [Disconnetti tutte le altre sessioni]                        |
+--------------------------------------------------------------+
```

---

## Decisioni Aperte

| #   | Domanda                                                 | Opzioni                                                                 | Decisione       |
| --- | ------------------------------------------------------- | ----------------------------------------------------------------------- | --------------- |
| 1   | Output `fn_get_user_profile`: JSONB o record composito? | JSONB (flessibile, facile da estendere) vs RECORD (tipizzato, validato) | **Da decidere** |
| 2   | Emittente multipli: quale mostrare?                     | Primo attivo dalla whitelist / emittente selezionabile / tutti          | **Da decidere** |
| 3   | Caching frontend del profilo                            | Salvare in localStorage? Refresh a ogni login?                          | **Da decidere** |
| 4   | Mostrare pannello profilo utente?                       | Solo topbar/sidebar o anche pagina dedicata `/profilo`?                 | **Da decidere** |
| 5   | TTL sessione attiva nella vista DB                      | Allineare a `REFRESH_TOKEN_LIFETIME` (1 giorno) o parametrizzare?       | **Da decidere** |
| 6   | Parsing User-Agent                                      | Lato backend (libreria Python) o lato frontend (JS)?                    | **Da decidere** |
| 7   | Batch "disconnetti tutte le altre"                      | Implementare subito o in fase successiva?                               | **Da decidere** |

---

## Sequenza di Sviluppo

```
[Fase 1] fn_get_soggetto_dati_by_ruolo (DB)
    |
    v
[Fase 2] fn_get_user_profile (DB) — dipende da Fase 1
    |
    v
[Fase 3] Endpoint /api/v1/core/me/ (Backend) — dipende da Fase 2
    |
    v
[Fase 4] Store + UI profilo (Frontend) — dipende da Fase 3
    |
    v
[Fase 5] Sessioni attive (DB + Backend + Frontend) — indipendente da Fasi 1-4
          ma logicamente collegata (pannello accessibile da UI profilo)
    5a. Vista DB vw_sessioni_utente_attive
    5b. Endpoint logout + API sessioni
    5c. Frontend: SessioniAttiveDialog
```

La Fase 5 e' **indipendente** dalle Fasi 1-4 e puo' essere sviluppata in parallelo.
L'unico punto di contatto e' l'UI: il pannello sessioni sara' accessibile dal
menu utente (topbar/sidebar) introdotto nella Fase 4.

---

## Riferimenti

- Guida soggetti e ruoli: `docs/it/dbzero/anagrafiche/manual/soggetti.md`
- Guida emittenti fiscali: `docs/it/dbzero/anagrafiche/manual/emittenti_fiscali.md`
- Guida risorse umane: `docs/it/dbzero/anagrafiche/manual/risorse_umane_auth_user.md`
- Permission resolver: `backend/apps/core/services/permissions_resolver.py`
- Store auth frontend: `frontend/src/stores/auth.js`
- Frontend standards: `docs/it/frontend/frontend-standards.md`
