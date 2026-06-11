# API Soggetti (Anagrafiche)

## Scopo

Endpoint REST per la gestione completa dei soggetti anagrafici: persone fisiche (PF),
persone giuridiche (PG) ed enti. Copre CRUD soggetti, contatti, indirizzi, ruoli
e utility di validazione/generazione codice fiscale.

## Contesto

Tutti gli endpoint risiedono sotto `/api/v1/anagrafiche/soggetti/`.
L'autenticazione avviene tramite token JWT (`Authorization: Bearer <token>`).
Le risposte seguono l'envelope standard `{"data": ...}`.
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
| `search` | string | No | Testo libero per ricerca su ragione sociale, cognome, nome, CF, P.IVA |
| `tipo_soggetto_dettaglio_id` | int | No | Filtra per tipo soggetto (PF, SRL, SPA, ecc.) |
| `limit` | int | No | Numero massimo di risultati per pagina (default: 25) |
| `offset` | int | No | Offset per paginazione |
| `order_by` | string | No | Campo di ordinamento (default: `ragione_sociale_completa`) |
| `order_dir` | string | No | Direzione ordinamento: `asc` o `desc` |

### Risposta (200)

```json
{
  "data": {
    "results": [
      {
        "id": "a1b2c3d4-...",
        "codice": "S000001",
        "ragione_sociale_completa": "Rossi Mario",
        "codice_fiscale": "RSSMRA80A01H501Z",
        "partita_iva": null,
        "tipo_soggetto_dettaglio": "Persona Fisica",
        "stato_iso2": "IT"
      }
    ],
    "total": 42,
    "page": 1,
    "limit": 25
  }
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
| `partita_iva` | string | No | Partita IVA |
| `stato_iso2` | string | No | Codice ISO2 dello stato (default: `IT`) |
| `data_nascita` | string (ISO) | No | Data di nascita (PF), formato `YYYY-MM-DD` |
| `sesso` | string | No | `M` o `F` (PF, default: `M`) |
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
      "email": "mario.rossi@example.com",
      "telefono": "0212345678"
    },
    "indirizzo": {
      "tipo_indirizzo_codice": "SEDE",
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
        "tipo_indirizzo_codice": "SEDE",
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

Restituisce il soggetto completo con contatti, indirizzi, ruoli e dati societari.

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
    "codice": "S000001",
    "ragione_sociale_completa": "Rossi Mario",
    "codice_fiscale": "RSSMRA80A01H501Z",
    "partita_iva": null,
    "tipo_soggetto_dettaglio_id": 1,
    "stato_iso2": "IT",
    "tipi_modificabili_ids": [1, 2],
    "non_editable_fields": ["codice_fiscale"],
    "contatti": [
      {
        "id": 1,
        "nominativo": "Rossi Mario",
        "email": "mario.rossi@example.com",
        "telefono": "0212345678"
      }
    ],
    "indirizzi": [
      {
        "id": 1,
        "tipo_indirizzo_codice": "SEDE",
        "indirizzo_normalizzato": "Via Garibaldi 10, 20100 Milano MI"
      }
    ],
    "ruoli": [
      {
        "soggetto_ruolo_id": 1,
        "codice": "CL",
        "descrizione": "Cliente"
      }
    ],
    "dati_societari": null
  }
}
```

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

Inviare solo i campi che si intende modificare.

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
| `tipo_contatto_id` | int | No | ID tipo contatto |
| `unita_organizzativa_id` | int | No | ID unita' organizzativa |
| `note` | string | No | Note |

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

Inviare solo i campi da modificare (stessi campi della creazione).

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
        "tipo_indirizzo_codice": "SEDE",
        "indirizzo_dettaglio_id": 100,
        "indirizzo_normalizzato": "Via Garibaldi 10, 20100 Milano MI",
        "indirizzo_libero": null
      }
    ]
  }
}
```

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
| `tipo_indirizzo_codice` | string | Si | Codice tipo indirizzo (es. `SEDE`, `SPED`, `AMMI`) |
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
    "tipo_indirizzo_codice": "SPED",
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
    "tipo_indirizzo_codice": "SEDE",
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
    "tipo_indirizzo_codice": "SEDE",
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
        "codice_ruolo": "CLI",
        "descrizione": "Cliente"
      }
    ]
  }
}
```

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
| `codice_ruolo` | string | Si | Codice del ruolo da assegnare (es. `CLI`, `FOR`, `VET`) |

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
  -d '{"codice_ruolo": "FOR"}'
```

### 9.3 Lookup ricco soggetti-ruoli (selezione contesto pratica)

Ricerca cross-dominio per autocomplete: restituisce **una riga per
`soggetto_ruolo`** ("Rossi Srl — Cliente", "Rossi Srl — Fornitore" come
opzioni distinte) piu' **una riga "senza ruolo"** (`soggetto_ruolo_id` e
`ruolo_codice` NULL) per i soggetti privi di qualunque ruolo — i prospect
puri delle utility, che hanno solo istanze (il ruolo CL nasce col BA, vedi
[guide/generazione-cliente.md](../../../guide/generazione-cliente.md)).
Consumato dal drawer pratiche per valorizzare `(soggetto_id,
soggetto_ruolo_id)` in una selezione sola.

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/soggetti-ruoli/lookup/` |

### Query params

| Param | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `q` | string | Si | Termine di ricerca (min 2 char). Matcha ragione sociale, CF, P.IVA |
| `tipo_ruolo` | string | No | Filtra per codice tipo ruolo (`CL`, `FO`, ...). Esclude le righe "senza ruolo" |
| `limit` | int | No | Max risultati (default 20, max 50) |

### Risposta (200)

```json
{
  "data": {
    "results": [
      {
        "soggetto_id": "a1b2c3d4-...",
        "soggetto_ruolo_id": 165,
        "ruolo_codice": "CL",
        "ruolo_descrizione": "Cliente",
        "ragione_sociale_completa": "Azienda ConTutto",
        "id_fiscale": "01234567890",
        "soggetto_codice": "SOG-00042",
        "n_istanze": 1,
        "istanza_unica_id": 197,
        "istanza_unica_codice": "IFO-0000051"
      },
      {
        "soggetto_id": "b2c3d4e5-...",
        "soggetto_ruolo_id": null,
        "ruolo_codice": null,
        "ruolo_descrizione": null,
        "ragione_sociale_completa": "Prospect Senza Ruolo",
        "id_fiscale": "PRSPCT80A01H501U",
        "soggetto_codice": "SOG-00043",
        "n_istanze": 2
      }
    ],
    "total_count": 2,
    "limit": 20
  }
}
```

Note:

- `n_istanze`: perimetro per riga — righe "senza ruolo" = tutte le istanze
  del soggetto; righe con ruolo = SOLO le istanze legate a quel ruolo via
  `clienti` (le forniture del cliente/BA; per i ruoli non-CL e' 0). Il FE lo
  usa per decidere se proporre il campo "Istanza utility" (lookup
  `/anagrafiche/istanze-utility/lookup/?soggetto_id=...&soggetto_ruolo_id=...`,
  filtrato con lo stesso perimetro).
- `istanza_unica_id` / `istanza_unica_codice`: valorizzati SOLO se il
  conteggio di cui sopra e' 1 — per il ruolo CL il FE auto-deriva l'istanza e
  nasconde il picker (pattern preventivi "istanza da BA"); con piu' istanze
  restano NULL e la scelta e' dell'operatore (combo ristretta alle forniture
  del cliente).
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

Risposta: stessa shape della riga di `results` in 9.3 (incl. `n_istanze`).
Errori: `E_ANAG_VALIDAZIONE` (zero o due chiavi, UUID malformato, id non
positivo), `E_ANAG_NOT_FOUND` (record inesistente).

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
| `sesso` | string | Si | `M` o `F` |
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
| `tipo_ruolo_codice` | string | Codice del tipo ruolo (es. `CL`, `FO`, `EF`). Case insensitive. |

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
        "dati_societari_policy": "NONE"
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
| `E_ANAG_NOT_FOUND` | 404 | `tipo_ruolo_codice` non corrisponde a nessun `config.tipi_ruoli` attivo |

### Esempio config-resolver

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/ruoli/CL/config-resolver/"
```

---

## Regole trasversali

- **Autenticazione**: tutti gli endpoint richiedono `Authorization: Bearer <token>`.
- **Envelope**: tutte le risposte sono racchiuse in `{"data": ...}`.
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
