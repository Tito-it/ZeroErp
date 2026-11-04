# API Soggetti (Anagrafiche)

## Scopo

Endpoint REST per la gestione completa dei soggetti anagrafici: persone fisiche (PF),
persone giuridiche (PG) ed enti. Copre CRUD soggetti, contatti, indirizzi, ruoli
e utility di validazione/generazione codice fiscale.

## Contesto

Tutti gli endpoint risiedono sotto `/api/v1/anagrafiche/soggetti/`.
L'autenticazione avviene tramite token JWT (`Authorization: Bearer <token>`).
Le risposte seguono l'envelope standard `{"data": ..., "meta": {...}}`.
Permesso: `model_permission = ("anagrafiche", "soggetto")` sugli endpoint
`soggetti/...` (lista, dettaglio, export, contatti, indirizzi, ruoli); i lookup
`soggetti-ruoli/...` e `istanze-utility/...` hanno `skip_area_check` con scope emittente.
La logica di business e i default (stato IT, socio unico, liquidazione) sono gestiti
dal DB tramite funzioni e trigger; il backend orchestra e valida.

## Base URL

```
/api/v1/anagrafiche/soggetti/
```

---

## 1. Lista soggetti

Restituisce l'elenco paginato dei soggetti con ricerca full-text e filtro per tipo.

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/soggetti/` |

### Parametri query

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `search` | string | No | Ricerca libera sulle colonne che il catalogo della lista `anagrafiche.soggetti` accende per l'operatore (le decide il catalogo, non il codice: `ricerca_full` nella configurazione della lista). Sotto 3 caratteri non filtra (nessun 400). Vale anche per l'export |
| `tipo_soggetto_dettaglio_id` | int | No | Filtra per tipo soggetto (PF, SRL, SPA, ecc.) |
| `limit` | int | No | Righe per pagina (default 25, max 200) |
| `offset` | int | No | Offset per paginazione |
| `order_by` | string | No | `codice`, `ragione_sociale_completa` (default), `id_fiscale_univoco_cf_piva`, `tipo_descrizione`, `data_insert`; fuori whitelist → **400** `E_VALIDATION_INPUT` (dal 2026-10-20) |
| `order_dir` | string | No | `asc` o `desc`. Se omessa: `asc`, salvo `data_insert` che parte `desc` |

### Risposta (200)

```json
{
  "data": {
    "count": 42,
    "page": 1,
    "page_size": 25,
    "total_pages": 2,
    "results": [
      {
        "id": "a1b2c3d4-...",
        "codice": "S000001",
        "ragione_sociale_completa": "Rossi Mario",
        "codice_fiscale": "RSSMRA80A01H501Z",
        "partita_iva": null,
        "id_fiscale_univoco_cf_piva": "RSSMRA80A01H501Z",
        "cognome": "Rossi",
        "nome": "Mario",
        "ragione_sociale": null,
        "tipo_descrizione": "Privato",
        "tipo_soggetto_dettaglio_id": 1,
        "natura_soggetto": "PF",
        "ruoli": [
          { "soggetto_ruolo_id": 1, "codice": "CL", "descrizione": "Cliente" }
        ]
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

### Esempio

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/soggetti/?search=rossi&limit=10"
```

---

## 2. Creazione soggetto

Crea un soggetto completo (PF o PG) in una singola transazione. Il tipo di soggetto
determina il percorso: PF richiede cognome/nome/CF, PG richiede ragione sociale.
Il DB risolve automaticamente i default (stato IT, socio unico, liquidazione) dalla
tabella `config.parameters`.

Se `auto_clone` e' `true` (default), il primo indirizzo fornito viene clonato per tutti
i tipi indirizzo obbligatori non compilati, secondo la matrice indirizzi del tipo soggetto.

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/anagrafiche/soggetti/` |

### Body (JSON)

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `tipo_soggetto_dettaglio_id` | int | Si | ID del tipo soggetto (PF, SRL, SPA, ecc.) |
| `cognome` | string | Si (PF) | Cognome della persona fisica |
| `nome` | string | Si (PF) | Nome della persona fisica |
| `ragione_sociale` | string | Si (PG) | Ragione sociale della persona giuridica |
| `codice_fiscale` | string | Si (PF), facoltativo (PG) | Codice fiscale — validato per congruenza (PF) |
| `partita_iva` | string | No | Partita IVA — anche per la ditta individuale (PF), dove la pretende il DB |
| `stato_iso2` | string | No | Codice ISO2 dello stato (default: `IT`) |
| `data_nascita` | string (ISO) | No | Data di nascita (PF), formato `YYYY-MM-DD` |
| `sesso` | string | Secondo il tipo | `M`, `F` o `X` («serve, ma non si puo' stabilire»); vuoto = non indicato. **Nessun default**: quando serve lo dice `sesso_policy` del tipo (vedi sotto) |
| `auto_clone` | bool | No | Clona indirizzo per tipi obbligatori mancanti (default: `true`) |
| `contatto` | object | Si | Contatto principale (vedi sotto) |
| `contatto.nominativo` | string | Si | Nome del contatto |
| `contatto.email` | string | No | Email |
| `contatto.telefono` | string | No | Telefono |
| `contatto.cellulare` | string | No | Cellulare |
| `contatto.pec` | string | No | PEC |
| `contatto.tipo_contatto_id` | int | Si | ID tipo contatto |
| `contatto.unita_organizzativa_id` | int | No | ID unita' organizzativa |
| `contatto.note` | string | No | Note |

> **Regola contatto inline (refactor 28-04-2026)**: il backend applica
> `classify_contatto_payload` su `contatto`. Stati possibili:
>
> - `EMPTY` (nessun campo del contatto valorizzato) → vietato per il
>   soggetto, solleva `E_CONTATTO_INCOMPLETO` (il contatto e' obbligatorio
>   sempre per il soggetto)
> - `PARTIAL` (almeno un campo valorizzato MA mancano `nominativo` e/o
>   `tipo_contatto_id`) → solleva `E_CONTATTO_INCOMPLETO` con
>   `context.missing` (lista campi mancanti) per highlight UI
> - `VALID` (`nominativo` + `tipo_contatto_id` presenti) → procede

> **Sesso e natura (brief-db-sesso-senza-default, 2026-10-09)**: il backend
> non controlla il sesso e non lo inventa. Una persona fisica nasce con il
> **tipo scelto** (privato `PR` o ditta individuale `DI`) e la sua partita IVA:
> fino a quella data nasceva sempre `PR` e la P.IVA si perdeva. La regola la
> tiene il guard `anagrafiche.trgfn_soggetti_guard_sesso_policy`, che legge
> `config.tipi_soggetto_dettaglio.sesso_policy`:
>
> | `sesso_policy` | Tipi | Sesso vuoto | `M`/`F`/`X` |
> | --- | --- | --- | --- |
> | `REQUIRED` | privato | `E_SESSO_OBBLIGATORIO` (400) | ✅ |
> | `OPTIONAL` | ditta individuale | ✅ | ✅ |
> | `NONE` | societa', enti | ✅ | `E_SESSO_NON_AMMESSO` (400) |
>
> I due rifiuti portano `error.fields = ["sesso"]`; valgono anche sulla `PATCH`.
| `dati_societari` | object | No | Dati societari (solo PG, vedi sotto) |
| `dati_societari.forma_giuridica_id` | int | No | ID forma giuridica |
| `dati_societari.id_prov_iscri_rea` | int | No | Provincia iscrizione REA |
| `dati_societari.iscrizione_rea` | string | No | Numero iscrizione REA |
| `dati_societari.capitale_sociale` | decimal | No | Capitale sociale |
| `dati_societari.socio_unico` | string | No | `SU` o `SM` (default da config) |
| `dati_societari.liquidazione` | string | No | `LS` o `LN` (default da config) |
| `dati_societari.destinatario_fe` | string | No | Destinatario fatturazione elettronica |
| `dati_societari.pec_fatturazione` | string | No | PEC per fatturazione |
| `dati_societari.codice_sdi` | string | No | Codice SDI |
| `indirizzi` | array | No | Lista indirizzi (vedi sezione Indirizzi) |
| `indirizzo` | object | No | Indirizzo singolo (alternativa a `indirizzi`) |

### Risposta (200)

```json
{
  "data": {
    "id": "a1b2c3d4-..."
  }
}
```

### Esempio — Persona Fisica

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://host/api/v1/anagrafiche/soggetti/" \
  -d '{
    "tipo_soggetto_dettaglio_id": 1,
    "cognome": "Rossi",
    "nome": "Mario",
    "codice_fiscale": "RSSMRA80A01H501Z",
    "data_nascita": "1980-01-01",
    "sesso": "M",
    "contatto": {
      "nominativo": "Rossi Mario",
      "tipo_contatto_id": 1,
      "email": "mario.rossi@example.com",
      "telefono": "0212345678"
    },
    "indirizzo": {
      "tipo_indirizzo_codice_interno": "SEDE",
      "toponomastica_id": 1,
      "descrizione_via": "Garibaldi",
      "civico": 10,
      "comune_id": 1234,
      "codice_postale_id": 5678
    }
  }'
```

### Esempio — Persona Giuridica

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://host/api/v1/anagrafiche/soggetti/" \
  -d '{
    "tipo_soggetto_dettaglio_id": 10,
    "ragione_sociale": "Acme SRL",
    "codice_fiscale": "01234567890",
    "partita_iva": "01234567890",
    "contatto": {
      "nominativo": "Ufficio Amministrazione",
      "tipo_contatto_id": 1,
      "email": "admin@acme.it",
      "pec": "acme@pec.it"
    },
    "dati_societari": {
      "forma_giuridica_id": 2,
      "capitale_sociale": 10000.00,
      "codice_sdi": "ABCDEFG"
    },
    "indirizzi": [
      {
        "tipo_indirizzo_codice_interno": "SEDE",
        "toponomastica_id": 1,
        "descrizione_via": "Roma",
        "civico": 42,
        "comune_id": 1234,
        "codice_postale_id": 5678
      }
    ]
  }'
```

---

## 3. Dettaglio soggetto

Restituisce il soggetto completo con contatti, indirizzi, ruoli, dati societari,
conti bancari e titoli IVA (tutti, senza paginazione). I ruoli CL sono filtrati per
scope emittente dell'operatore.

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/soggetti/{soggetto_id}/` |

### Parametri path

| Parametro | Tipo | Descrizione |
|---|---|---|
| `soggetto_id` | string (UUID) | Identificativo del soggetto |

### Risposta (200)

```json
{
  "data": {
    "id": "a1b2c3d4-...",
    "ragione_sociale_completa": "Rossi Mario",
    "codice_fiscale": "RSSMRA80A01H501Z",
    "partita_iva": null,
    "cognome": "Rossi",
    "nome": "Mario",
    "ragione_sociale": null,
    "split_payment": "N",
    "cliente_pa": "N",
    "sesso": "M",
    "data_nascita": "1980-01-01",
    "comune_nascita_id": 1234,
    "comune_nascita_descrizione": "Roma",
    "comune_nascita_provincia_sigla": "RM",
    "tipo_soggetto_dettaglio_id": 1,
    "tipo_descrizione": "Privato",
    "natura_soggetto": "PF",
    "tipi_modificabili_ids": [1, 2],
    "contatti": [
      {
        "id": 1,
        "nominativo": "Rossi Mario",
        "email": "mario.rossi@example.com",
        "telefono": "0212345678",
        "cellulare": null,
        "pec": null,
        "note": null,
        "tipo_contatto_id": 1,
        "tipo_contatto_descrizione": "Principale",
        "unita_organizzativa_id": null
      }
    ],
    "indirizzi": [
      { "...": "stessa forma della lista indirizzi (§7.1)" }
    ],
    "ruoli": [
      {
        "id": 1,
        "tipo_ruolo_id": 3,
        "ruolo_codice_interno": "CL",
        "ruolo_descrizione": "Cliente"
      }
    ],
    "dati_societari": null,
    "conti_bancari": [],
    "titoli_iva": [],
    "non_editable_fields": ["codice_fiscale"]
  },
  "meta": { "request_id": "..." }
}
```

Il dettaglio non porta `codice` ne' `stato_iso2`. `conti_bancari` ha la forma
dei legami soggetto-conto (`id`, `conto_bancario_id`, `uso`, `predefinito`,
`valido_dal`, `valido_al`, `intestazione_dichiarata`, `verificato`, `bloccato` e i
dati del conto); `titoli_iva` la forma della lista titoli IVA
([api_titoli_iva_soggetto.md](api_titoli_iva_soggetto.md)). Soggetto inesistente → 404
`E_ANAG_NOT_FOUND`.

### Campi meta-info edit (refactor 28-04-2026)

| Campo | Tipo | Descrizione |
| --- | --- | --- |
| `tipi_modificabili_ids` | int[] | ID dei `tipi_soggetto_dettaglio` ammessi in edit per questo soggetto (stessa natura del corrente). Il frontend filtra la dropdown con questa lista invece di ricostruire la regola `natura_soggetto`. |
| `non_editable_fields` | string[] | Lista dei campi anagrafici NON modificabili nello stato corrente (es. `["codice_fiscale", "partita_iva"]` se valorizzati). Il frontend deriva `cfDisabled`/`pivaDisabled` da questa lista. Vuoto = niente bloccato. |

> **Nota**: questi campi sono backend-driven per evitare drift della
> regola di immutabilita'/mutabilita' tra layer. Estendibili senza
> rilascio frontend (es. nuovo campo immutabile post stato avanzato).

### Esempio

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/soggetti/a1b2c3d4-.../"
```

---

## 4. Aggiornamento soggetto

Aggiorna uno o piu' campi del soggetto. Invia solo i campi da modificare.

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/anagrafiche/soggetti/{soggetto_id}/` |

### Parametri path

| Parametro | Tipo | Descrizione |
|---|---|---|
| `soggetto_id` | string (UUID) | Identificativo del soggetto |

### Body (JSON)

| Campo | Tipo | Descrizione |
|---|---|---|
| `cognome` | string | Cognome (PF) |
| `nome` | string | Nome (PF) |
| `ragione_sociale` | string | Ragione sociale (PG) |
| `codice_fiscale` | string | Codice fiscale |
| `partita_iva` | string | Partita IVA |
| `sesso` | string | `M`, `F`, `X`; vuoto = `NULL`. Lo giudica il guard secondo `sesso_policy` (vedi la creazione) |
| `data_nascita`, `comune_nascita_id` | string (ISO) / int | Dati di nascita (PF) |
| `cliente_pa`, `split_payment` | string | `S` / `N` (minuscole e spazi normalizzati). Ammessi solo dove la natura lo dice (`cliente_pa_ammesso`, `split_payment_ammesso` del lookup dei tipi): altrimenti `E_CLIENTE_PA_NON_AMMESSO` / `E_SPLIT_PAYMENT_NON_AMMESSO` (400, `error.fields` = il flag) |
| `tipo_soggetto_dettaglio_id` | int | La natura di dettaglio (fra i `tipi_modificabili_ids`). Cosa la natura nuova ammette — flag, forma giuridica, titoli IVA in vigore — lo giudicano i guard del DB |
| `dati_societari` | object | La sezione dati societari, **stato intero**: crea o aggiorna la riga col verbo `anagrafiche.fn_scrivi_dati_societari`. Chiavi: `forma_giuridica_id`, `id_prov_iscri_rea`, `iscrizione_rea`, `capitale_sociale`, `socio_unico`, `liquidazione`, `destinatario_fe`, `pec_fatturazione`, `codice_sdi`, `data_costituzione`. Una chiave assente vale `null` |

Inviare solo i campi che si intende modificare. Una chiave fuori dall'elenco
sopra → 400 `E_ANAG_VALIDAZIONE`; un corpo vuoto (o con `dati_societari: {}`) →
400 `E_ANAG_VALIDAZIONE` (dal 2026-10-20: prima 404, come un soggetto inesistente). ⚠️ Fa eccezione `dati_societari`:
se c'e', porta la sezione **intera** (il verbo non distingue «non toccare» da
«svuota»).

**Ordine e atomicita'** (dal 2026-10-10, brief-db-dati-fiscali-e-societari-del-soggetto):
prima l'UPDATE del soggetto, poi il verbo dei dati societari, nella **stessa
transazione**. Natura e forma giuridica si cambiano cosi' nello stesso
salvataggio: il guard della forma la confronta con la natura nuova, e il guard
al COMMIT (`trgfn_soggetti_guard_forma_giuridica_natura`) vede le due
scritture insieme. Con i soli `dati_societari` il soggetto non si tocca, e un
soggetto inesistente risponde `E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO` (404).

**Rifiuti dei guard, col campo da accendere** (`error.fields`):

| Codice | Status | Campo |
| --- | --- | --- |
| `E_FORMA_GIURIDICA_NON_AMMESSA_PER_TIPO_SOGGETTO` | 400 | `forma_giuridica_id` |
| `E_TIPO_SOGGETTO_FORMA_GIURIDICA_NON_AMMESSA` | 400 | `forma_giuridica_id` (natura cambiata, forma no) |
| `E_REA_OBBLIGATORIO` / `E_REA_NON_AMMESSO` | 400 | `iscrizione_rea` |
| `E_CAPITALE_SOCIALE_OBBLIGATORIO` / `E_CAPITALE_SOCIALE_NON_AMMESSO` | 400 | `capitale_sociale` |
| `E_DATI_SOCIETARI_CODICE_SDI_*`, `E_DATI_SOCIETARI_PEC_FATTURAZIONE_MANCANTE` | 400 | `codice_sdi` / `pec_fatturazione` |
| `E_CLIENTE_PA_NON_AMMESSO` / `E_SPLIT_PAYMENT_NON_AMMESSO` | 400 | `cliente_pa` / `split_payment` |
| `E_TIPO_SOGGETTO_CON_TITOLI_IVA_NON_AMMESSI` | 409 | — (chiudere prima il titolo in vigore) |

### Risposta (200)

```json
{
  "data": {
    "updated": true
  }
}
```

### Esempio

```bash
curl -s -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://host/api/v1/anagrafiche/soggetti/a1b2c3d4-.../" \
  -d '{"cognome": "Bianchi"}'
```

---

## 5. Contatti del soggetto

### 5.1 Lista contatti

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/soggetti/{soggetto_id}/contatti/` |

### Risposta (200)

```json
{
  "data": {
    "results": [
      {
        "id": 1,
        "nominativo": "Rossi Mario",
        "email": "mario.rossi@example.com",
        "telefono": "0212345678",
        "cellulare": null,
        "pec": null,
        "tipo_contatto_id": null,
        "note": null
      }
    ]
  }
}
```

### Esempio

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/soggetti/a1b2c3d4-.../contatti/"
```

### 5.2 Creazione contatto

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/anagrafiche/soggetti/{soggetto_id}/contatti/` |

### Body (JSON)

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `nominativo` | string | Si | Nome del contatto |
| `email` | string | No | Email |
| `telefono` | string | No | Telefono |
| `cellulare` | string | No | Cellulare |
| `pec` | string | No | PEC |
| `tipo_contatto_id` | int | Si | ID tipo contatto (uno per tipo sul soggetto) |
| `unita_organizzativa_id` | int | No | ID unita' organizzativa |
| `note` | string | No | Note |

> **Rifiuti (dal 2026-10-09, BB `crea_contatto_validato`)**: il contatto deve
> essere valido (`nominativo` + `tipo_contatto_id`), altrimenti
> `400 E_CONTATTO_INCOMPLETO` con i campi mancanti in `error.fields`. Un
> contatto per tipo: un secondo contatto con lo stesso tipo risponde
> `409 E_ANAG_DUPLICATO` col campo `tipo_contatto_id`. Fino a quella data
> entrambi uscivano come `400 E_DATABASE` generico.

### Risposta (200)

```json
{
  "data": {
    "id": 2
  }
}
```

### Esempio

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://host/api/v1/anagrafiche/soggetti/a1b2c3d4-.../contatti/" \
  -d '{
    "nominativo": "Ufficio Acquisti",
    "tipo_contatto_id": 2,
    "email": "acquisti@acme.it",
    "telefono": "0298765432"
  }'
```

---

## 6. Modifica ed eliminazione contatto

### 6.1 Aggiornamento contatto

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/anagrafiche/soggetti/{soggetto_id}/contatti/{contatto_id}/` |

### Parametri path

| Parametro | Tipo | Descrizione |
|---|---|---|
| `soggetto_id` | string (UUID) | Identificativo del soggetto |
| `contatto_id` | int | Identificativo del contatto |

### Body (JSON)

Inviare solo i campi da modificare (stessi campi della creazione). Una chiave
fuori da quell'elenco → 400 `E_ANAG_VALIDAZIONE`.

### Risposta (200)

```json
{
  "data": {
    "updated": true
  }
}
```

### Esempio

```bash
curl -s -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://host/api/v1/anagrafiche/soggetti/a1b2c3d4-.../contatti/1/" \
  -d '{"email": "nuova@email.it"}'
```

### 6.2 Eliminazione contatto

| | |
|---|---|
| **Metodo** | `DELETE` |
| **URL** | `/api/v1/anagrafiche/soggetti/{soggetto_id}/contatti/{contatto_id}/` |

### Risposta (200)

```json
{
  "data": {
    "deleted": true
  }
}
```

### Esempio

```bash
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/soggetti/a1b2c3d4-.../contatti/1/"
```

---

## 7. Indirizzi del soggetto

### 7.1 Lista indirizzi

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/soggetti/{soggetto_id}/indirizzi/` |

### Risposta (200)

```json
{
  "data": {
    "results": [
      {
        "id": 1,
        "tipo_indirizzo_id": 2,
        "tipo_indirizzo_descrizione": "Sede legale",
        "tipo_indirizzo_codice_interno": "SEDELEG",
        "indirizzo_dettaglio_id": 100,
        "indirizzo_libero": null,
        "stato_id": null,
        "comune_id": null,
        "indirizzo_display": "VIA GARIBALDI 10",
        "stradario_id": 7,
        "civico": 10,
        "estensione_civico": null,
        "palazzina": null,
        "scala": null,
        "piano": null,
        "interno": null,
        "stradario_display": "VIA GARIBALDI",
        "det_comune_id": 1234,
        "descrizione_comune": "Milano"
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

`indirizzo_display` e' l'indirizzo libero se c'e', altrimenti l'indirizzo
normalizzato del dettaglio; `det_comune_id`/`descrizione_comune` sono il comune
dello stradario. Ordinati per tipo indirizzo.

### Esempio

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/soggetti/a1b2c3d4-.../indirizzi/"
```

### 7.2 Creazione indirizzo soggetto

Crea un nuovo indirizzo associato al soggetto. Il payload supporta due modalita':

- **Indirizzo strutturato**: specificare `indirizzo_dettaglio_id` (se gia' esistente)
  oppure i campi via (toponomastica, descrizione, civico, comune, CAP) per creare
  automaticamente stradario e dettaglio.
- **Indirizzo libero**: specificare `indirizzo_libero` (testo libero, per indirizzi esteri).

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/anagrafiche/soggetti/{soggetto_id}/indirizzi/` |

### Body (JSON)

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `tipo_indirizzo_codice_interno` | string | Si | Codice tipo indirizzo (es. `SEDE`, `SPED`, `AMMI`) |
| `indirizzo_dettaglio_id` | int | No | ID indirizzo dettaglio esistente |
| `toponomastica_id` | int | No | ID tipo strada (Via, Piazza, ecc.) |
| `descrizione_via` | string | No | Nome della via |
| `civico` | int | No | Numero civico |
| `estensione_civico` | string | No | Estensione civico (es. `/A`, `bis`) |
| `comune_id` | int | No | ID comune |
| `codice_postale_id` | int | No | ID codice postale |
| `palazzina` | string | No | Palazzina |
| `scala` | string | No | Scala |
| `piano` | string | No | Piano |
| `interno` | string | No | Interno |
| `indirizzo_libero` | string | No | Indirizzo in testo libero (indirizzi esteri) |
| `stato_id` | int | No | ID stato (per indirizzo libero) |

### Risposta (200)

```json
{
  "data": {
    "id": 2
  }
}
```

### Esempio — Indirizzo strutturato (nuova via)

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://host/api/v1/anagrafiche/soggetti/a1b2c3d4-.../indirizzi/" \
  -d '{
    "tipo_indirizzo_codice_interno": "SPED",
    "toponomastica_id": 1,
    "descrizione_via": "Mazzini",
    "civico": 5,
    "comune_id": 1234,
    "codice_postale_id": 5678
  }'
```

### Esempio — Indirizzo libero (estero)

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://host/api/v1/anagrafiche/soggetti/a1b2c3d4-.../indirizzi/" \
  -d '{
    "tipo_indirizzo_codice_interno": "SEDE",
    "indirizzo_libero": "123 Main Street, New York, NY 10001",
    "stato_id": 42
  }'
```

---

## 8. Sostituzione ed eliminazione indirizzo

### 8.1 Sostituzione indirizzo

Sostituisce un indirizzo soggetto esistente. Funzionalmente e' una modifica, ma
internamente elimina il vecchio collegamento e ne crea uno nuovo (perche' il dettaglio
indirizzo e' condiviso tra soggetti).

| | |
|---|---|
| **Metodo** | `PUT` |
| **URL** | `/api/v1/anagrafiche/soggetti/{soggetto_id}/indirizzi/{indirizzo_soggetto_id}/` |

### Parametri path

| Parametro | Tipo | Descrizione |
|---|---|---|
| `soggetto_id` | string (UUID) | Identificativo del soggetto |
| `indirizzo_soggetto_id` | int | Identificativo dell'associazione indirizzo-soggetto |

### Body (JSON)

Stessi campi della creazione indirizzo (sezione 7.2).

### Risposta (200)

```json
{
  "data": {
    "id": 3
  }
}
```

### Esempio

```bash
curl -s -X PUT -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://host/api/v1/anagrafiche/soggetti/a1b2c3d4-.../indirizzi/1/" \
  -d '{
    "tipo_indirizzo_codice_interno": "SEDE",
    "toponomastica_id": 1,
    "descrizione_via": "Verdi",
    "civico": 20,
    "comune_id": 1234,
    "codice_postale_id": 5678
  }'
```

### 8.2 Eliminazione indirizzo

| | |
|---|---|
| **Metodo** | `DELETE` |
| **URL** | `/api/v1/anagrafiche/soggetti/{soggetto_id}/indirizzi/{indirizzo_soggetto_id}/` |

### Risposta (200)

```json
{
  "data": {
    "deleted": true
  }
}
```

### Esempio

```bash
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/soggetti/a1b2c3d4-.../indirizzi/1/"
```

---

## 9. Ruoli del soggetto

### 9.1 Lista ruoli

Restituisce i ruoli assegnati al soggetto (es. Cliente, Fornitore, Vettore).

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/soggetti/{soggetto_id}/ruoli/` |

### Risposta (200)

```json
{
  "data": {
    "results": [
      {
        "id": 1,
        "tipo_ruolo_id": 3,
        "ruolo_codice_interno": "CL",
        "ruolo_descrizione": "Cliente"
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

`id` e' il `soggetto_ruolo_id`; `ruolo_codice_interno` e' il codice interno del tipo ruolo
(o il codice, se manca). Ordinati per descrizione; il ruolo CL e' filtrato per
scope emittente.

### Esempio

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/soggetti/a1b2c3d4-.../ruoli/"
```

### 9.2 Assegnazione ruolo

Assegna un ruolo al soggetto. L'operazione e' idempotente: se il ruolo e' gia'
assegnato, non viene duplicato.

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/anagrafiche/soggetti/{soggetto_id}/ruoli/` |

### Body (JSON)

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `codice_ruolo` | string | Si | Codice (`GESTORE`) o codice interno (`GE`) del tipo ruolo |
| `indirizzi` | array | Secondo il ruolo | Indirizzi **del ruolo**, stessa forma della creazione soggetto. Necessari per i ruoli con indirizzi obbligatori (`config.tipi_ruolo_tipi_indirizzo`, es. GE) |

> **Ruoli con un flusso dedicato (dal 2026-10-09)**: `CL`, `FO`, `EF` e
> `RIS_UMANA` non si assegnano da qui: `400 E_ANAG_VALIDAZIONE` sul campo
> `codice_ruolo`, con il rimando al flusso (Clienti, Fornitori, Emittenti
> fiscali, Risorse umane). Il ruolo è solo il primo anello della loro catena:
> un CL nasce con la prima istanza e il suo billing account, e creato «nudo»
> da qui non aveva clienti né era visibile a un operatore con emittente.

> **Indirizzi del ruolo (dal 2026-10-09)**: gli obbligatori del ruolo (per GE
> la sede legale `SEDELEG` e la fatturazione `FATT`) sono indirizzi del **ruolo**, non
> del soggetto: li pretende il guard differito
> `anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required` al commit. Ruolo e
> indirizzi nascono nella stessa transazione, con `create_indirizzi_ruolo`
> (come nei flussi clienti e fornitori): il primo indirizzo viene clonato per
> ogni obbligatorio mancante. Senza `indirizzi`, un ruolo che ne ha di
> obbligatori risponde `E_INDIRIZZO_OBBLIGATORIO_MANCANTE` (prima di questa
> data l'endpoint non li accettava, quindi per quei ruoli rispondeva sempre
> così). Ogni indirizzo deve essere ammesso anche per il tipo soggetto
> (`config.tipi_soggetto_dettaglio_tipi_indirizzo`).

### Risposta (200)

```json
{
  "data": {
    "id": 2
  }
}
```

### Esempio

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://host/api/v1/anagrafiche/soggetti/a1b2c3d4-.../ruoli/" \
  -d '{"codice_ruolo": "GESTORE", "indirizzi": [{"tipo_indirizzo_codice_interno": "SEDELEG", "indirizzo_dettaglio_id": 123}]}'
```

### 9.3 Lookup ricco soggetti-ruoli (selezione contesto pratica)

Ricerca cross-dominio per autocomplete: restituisce **una riga per
`soggetto_ruolo`** ("Rossi Srl — Cliente", "Rossi Srl — Fornitore" come
opzioni distinte) piu' **una riga "senza ruolo"** (`soggetto_ruolo_id` e
`ruolo_codice_interno` NULL) per i soggetti privi di qualunque ruolo — per esempio
appena censiti. Non hanno istanze: l'istanza nasce col suo billing account, e il
ruolo CLIENTE con la prima istanza (vedi
[guide/generazione-cliente.md](../../../guide/generazione-cliente.md)).
Consumato dal drawer pratiche per valorizzare `(soggetto_id,
soggetto_ruolo_id)` in una selezione sola, e dai campi del DDT che salvano un
`soggetto_ruolo_id` (destinatario, vettore, mittente) con `con_ruolo=true`: li'
una riga "senza ruolo" non ha niente da salvare.

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/soggetti-ruoli/lookup/` |

### Query params

| Param | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `q` | string | Si | Termine di ricerca (min 2 char). Matcha ragione sociale, CF, P.IVA |
| `tipo_ruolo` | string | No | Filtra per codice tipo ruolo (`CL`, `FO`, ...). Esclude le righe "senza ruolo" |
| `con_ruolo` | bool | No | `true`: solo righe con un ruolo, di qualunque tipo (esclude le righe "senza ruolo"). Assente o `false`: nessun filtro. Valore non riconosciuto: 400 `E_VALIDATION_INPUT` |
| `limit` | int | No | Max risultati (default 20, max 50) |

### Risposta (200)

```json
{
  "data": {
    "results": [
      {
        "soggetto_id": "a1b2c3d4-...",
        "soggetto_ruolo_id": 165,
        "ruolo_codice_interno": "CL",
        "ruolo_descrizione": "Cliente",
        "ragione_sociale_completa": "Azienda ConTutto",
        "id_fiscale": "01234567890",
        "soggetto_codice": "SOG-00042",
        "n_billing_account": 1,
        "billing_account_unico_id": 412,
        "billing_account_unico_codice": "BA-0000412"
      },
      {
        "soggetto_id": "b2c3d4e5-...",
        "soggetto_ruolo_id": null,
        "ruolo_codice_interno": null,
        "ruolo_descrizione": null,
        "ragione_sociale_completa": "Soggetto Senza Ruolo",
        "id_fiscale": "SGGSNZ80A01H501U",
        "soggetto_codice": "SOG-00043",
        "n_billing_account": 0,
        "billing_account_unico_id": null,
        "billing_account_unico_codice": null
      }
    ],
    "total_count": 2,
    "limit": 20
  }
}
```

Note:

- `n_billing_account`: le **forniture** del ruolo, cioe' i suoi billing
  account (uno per coppia istanza+utility), con o senza la riga cliente. Per i
  ruoli non-CL e per le righe "senza ruolo" e' 0: un BA e' sempre di un ruolo
  CLIENTE, e la pratica lo accetta solo dal suo ruolo
  (`E_PRATICHE_BA_NON_COERENTE`). Il FE lo usa per decidere se proporre il
  campo "Fornitura" (lookup
  `/anagrafiche/istanze-utility/lookup/?soggetto_id=...&soggetto_ruolo_id=...`,
  una riga per BA, filtrato con lo stesso perimetro).
- `billing_account_unico_id` / `billing_account_unico_codice`: valorizzati SOLO
  se il conteggio e' 1 — il FE auto-deriva il BA della pratica e nasconde il
  picker; con piu' BA restano NULL e la scelta e' dell'operatore.
- ⚠️ Fino al 2026-10-08 i campi erano `n_istanze` / `istanza_unica_*` e
  contavano le istanze legate al ruolo via `clienti`: un ruolo col BA e senza
  la riga cliente risultava senza forniture, e un'istanza con due utility
  contava uno (brief-db-istanza-nasce-col-ba, D-9).
- Scope emittente sul ruolo CL: stesso comportamento della lista ruoli (un
  operatore scoped vede il CL solo se il soggetto ha un cliente su un BA dei
  suoi emittenti). Le righe "senza ruolo" non sono scoped.
- Endpoint di ricerca (`is_search_endpoint`): throttling dedicato, JWT.

### 9.4 Restore by-id del lookup

Ricostruisce la riga lookup gia' selezionata quando un form riapre in edit
(pattern restore AutoComplete, gemello di `billing-account/<id>/lookup/`).
Chiavi **alternative** in query string — esattamente una delle due:

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/soggetti-ruoli/lookup-by-id/` |

| Param | Tipo | Descrizione |
|---|---|---|
| `soggetto_ruolo_id` | int | Restore di una riga ruolo |
| `soggetto_id` | string (UUID) | Restore di una riga "senza ruolo" |

Risposta: stessa shape della riga di `results` in 9.3 (incl. `n_billing_account`).
Errori: `E_ANAG_VALIDAZIONE` (zero o due chiavi, UUID malformato, id non
positivo), `E_ANAG_NOT_FOUND` (record inesistente **o fuori scope**).

**Perimetro**: la stessa **regola** di scope emittente della ricerca 9.3,
non lo stesso insieme di righe.

* **Riga ruolo** (`soggetto_ruolo_id`): identica alla ricerca — vale la regola
  del ruolo CL.
* **Riga «senza ruolo»** (`soggetto_id`): il soggetto è restituito se
  **nessuno** dei suoi ruoli è fuori scope (lo scope tocca solo il ruolo CL).
  ⚠️ È **più largo** della ricerca, di proposito: la ricerca propone la riga
  «senza ruolo» solo ai soggetti privi di qualunque ruolo, il restore
  ricostruisce una selezione già fatta, e il soggetto può aver preso ruoli
  dopo. Un soggetto scelto quando non aveva ruoli resta ricostruibile dopo che
  è diventato cliente, ma solo da chi quel cliente lo vede; con soli ruoli
  diversi da CL, da chiunque.

Un id fuori scope risponde come un id inesistente: non rivela di esistere. ⛔ Fino al 2026-10-08 il restore non
applicava nessuno scope (la view ha `skip_area_check`).

### 9.5 Restore by-id del lookup forniture (istanze utility)

Ricostruisce la riga del lookup forniture (`/anagrafiche/istanze-utility/lookup/`,
citato in 9.3) quando un form che conosce solo l'id dell'istanza riapre in edit
(es. preventivo aperto da una pratica senza BA).

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/istanze-utility/{istanza_utility_id}/lookup/` |
| **View** | `IstanzaUtilityLookupByIdView` — `skip_area_check`, JWT |

Nessun parametro query, nessun corpo.

### Risposta (200)

```json
{
  "data": {
    "id": 100,
    "codice": "IU-0000100",
    "fittizia": false,
    "soggetto_id": "a1b2c3d4-...",
    "ragione_sociale_completa": "Azienda ConTutto",
    "id_fiscale": "01234567890",
    "indirizzo_dettaglio_id": 42,
    "indirizzo_display": "VIA ROMA 10",
    "pdp_id": 7,
    "pdp_codice": "IT001E00000000",
    "billing_account_id": 412,
    "billing_account_codice": "BA-0000412",
    "utility_id": 1,
    "utility_codice": "EE",
    "utility_descrizione": "Energia elettrica"
  },
  "meta": { "request_id": "..." }
}
```

I campi del billing account (`billing_account_*`, `utility_*`) sono valorizzati
solo se l'istanza ha **un solo** BA; con piu' BA (piu' utility) restano `null`.

**Perimetro**: lo stesso scope emittente della ricerca; un id fuori scope
risponde come un id inesistente.

### Errori

| Codice | HTTP | Causa |
|---|---|---|
| `E_ANAG_VALIDAZIONE` | 400 | `istanza_utility_id` non positivo |
| `E_ANAG_NOT_FOUND` | 404 | Istanza inesistente o fuori scope emittente |

---

## 10. Validazione CF e P.IVA

Verifica la congruenza del codice fiscale con i dati anagrafici e segnala
eventuali duplicati nel sistema. Per la P.IVA, verifica solo i duplicati.
Restituisce `errors` (bloccanti) e `warnings` (informativi).

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/anagrafiche/soggetti/valida-cf-piva/` |

### Body (JSON)

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `codice_fiscale` | string | No | Codice fiscale da validare (16 caratteri per congruenza) |
| `partita_iva` | string | No | Partita IVA da verificare per duplicati |
| `sesso` | string | No | `M` o `F` — per congruenza CF |
| `data_nascita` | string (ISO) | No | Data di nascita — per congruenza CF |
| `comune_nascita_id` | int | No | ID comune di nascita — per congruenza CF (codice catastale) |

### Risposta (200)

```json
{
  "data": {
    "errors": [
      {
        "field": "codice_fiscale",
        "message": "Il sesso nel CF non corrisponde al sesso indicato."
      }
    ],
    "warnings": [
      {
        "field": "partita_iva",
        "message": "P.IVA gia' presente: Acme SRL (S000010)"
      }
    ]
  }
}
```

### Esempio

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://host/api/v1/anagrafiche/soggetti/valida-cf-piva/" \
  -d '{
    "codice_fiscale": "RSSMRA80A01H501Z",
    "sesso": "M",
    "data_nascita": "1980-01-01",
    "comune_nascita_id": 1234
  }'
```

---

## 11. Generazione codice fiscale

Genera il codice fiscale italiano a partire dai dati anagrafici della persona fisica.
Tutti i campi sono obbligatori.

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/anagrafiche/soggetti/genera-cf/` |

### Body (JSON)

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `cognome` | string | Si | Cognome |
| `nome` | string | Si | Nome |
| `data_nascita` | string (ISO) | Si | Data di nascita, formato `YYYY-MM-DD` |
| `sesso` | string | Si | `M` o `F`. Con `X` il calcolo e' rifiutato (`E_ANAG_VALIDAZIONE`, campo `sesso`): il codice fiscale codifica solo M e F |
| `comune_nascita_id` | int | Si | ID del comune di nascita (per ricavare il codice catastale) |

### Risposta (200)

```json
{
  "data": {
    "codice_fiscale": "RSSMRA80A01H501Z"
  }
}
```

### Esempio

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://host/api/v1/anagrafiche/soggetti/genera-cf/" \
  -d '{
    "cognome": "Rossi",
    "nome": "Mario",
    "data_nascita": "1980-01-01",
    "sesso": "M",
    "comune_nascita_id": 1234
  }'
```

---

## 12. Config resolver per tipo ruolo

Restituisce la configurazione per il SoggettoResolver frontend: nature
ammesse, tipi soggetto dettaglio compatibili, default e parametri UX.
Usato per adattare ricerca soggetti e form di creazione al ruolo target
(cliente, fornitore, emittente fiscale, ecc.).

| | |
| --- | --- |
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/ruoli/{tipo_ruolo_codice}/config-resolver/` |

### Parametri path

| Parametro | Tipo | Descrizione |
| --- | --- | --- |
| `tipo_ruolo_codice` | string | Codice interno del tipo ruolo (`codice_interno`, es. `CL`, `FO`, `EF`). Confronto **esatto**: `cl` non trova `CL` (404), come nelle rotte `lookup/tipi-ruolo/{codice}/…`. Fino al 2026-11-04 era case insensitive. |

### Risposta (200)

```json
{
  "data": {
    "tipo_ruolo": "CL",
    "tipo_ruolo_descrizione": "Cliente",
    "nature_ammesse": ["PF", "PG", "ENTE"],
    "tipi_soggetto_dettaglio": [
      {
        "id": 1,
        "codice_interno": "PR",
        "descrizione": "Privato",
        "natura_soggetto": "PF",
        "cf_obbligatorio": true,
        "piva_obbligatoria": false,
        "formato_cf": "ALFANUM_16",
        "formato_piva": "NON_APPLICABILE",
        "dati_societari_policy": "NONE",
        "sesso_policy": "REQUIRED",
        "cliente_pa_ammesso": false,
        "split_payment_ammesso": false
      }
    ],
    "default_tipo_soggetto_dettaglio_id": 1,
    "min_search_length": 3
  }
}
```

### Campi aggiunti nel refactor 27-04-2026

| Campo | Tipo | Descrizione |
| --- | --- | --- |
| `default_tipo_soggetto_dettaglio_id` | int / null | ID del tipo dettaglio di default per questo ruolo, risolto via `config.parameters` (chiave `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_<RUOLO>`). Override per emittente supportato dalla catena `script.fn_get_parameter_full`. `null` se non configurato — il frontend fa fallback al primo elemento di `tipi_soggetto_dettaglio`. |
| `min_search_length` | int | Lunghezza minima della search bar resolver (default `3`). Backend-driven per evitare cablato frontend. |

### Errori

| Codice | HTTP | Causa |
| --- | --- | --- |
| `E_ANAG_NOT_FOUND` | 404 | `tipo_ruolo_codice` non corrisponde a nessun `config.tipi_ruoli` (confronto esatto sul codice interno; non filtra su `attivo`) |

### Esempio config-resolver

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/ruoli/CL/config-resolver/"
```

---

## Regole trasversali

- **Autenticazione**: tutti gli endpoint richiedono `Authorization: Bearer <token>`.
- **Envelope**: tutte le risposte sono racchiuse in `{"data": ..., "meta": {...}}`.
- **Errori**: in caso di errore viene restituito `{"error": {"code": "...", "message": "..."}}` con HTTP status appropriato (400, 404, 409, 500).
- **UUID**: l'identificativo `soggetto_id` e' di tipo UUID (stringa).
- **Ownership**: le operazioni su contatti e indirizzi verificano che la risorsa appartenga al soggetto indicato nel path.
- **Idempotenza**: l'assegnazione ruolo e' idempotente; la creazione soggetto con CF/PIVA duplicata restituisce errore.
- **Transazionalita'**: la creazione soggetto (con contatto e indirizzi) avviene in una singola transazione atomica. I trigger DEFERRED verificano i vincoli al COMMIT.

## Dipendenze DB

- `anagrafiche.soggetti` — tabella principale soggetti
- `anagrafiche.contatti_soggetto` — contatti associati
- `anagrafiche.indirizzi_soggetto` — associazione soggetto-indirizzo
- `anagrafiche.indirizzi_dettaglio` — dettaglio indirizzo condiviso
- `anagrafiche.soggetti_ruoli` — ruoli assegnati
- `anagrafiche.dati_societari` — dati societari PG
- `anagrafiche.stradario_generale` — stradario condiviso
- `config.parameters` — default (stato, socio unico, liquidazione)
- `config.matrice_indirizzi` — tipi indirizzo obbligatori per tipo soggetto
