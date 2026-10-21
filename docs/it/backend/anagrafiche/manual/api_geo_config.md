# API Configurazione Geografica

## Scopo

API per la gestione delle tabelle di configurazione geografica: stati, regioni, province, comuni, toponomastica e codici postali. Ogni entita` segue un pattern uniforme CRUD con lista paginata e, dove previsto, endpoint lookup per dropdown.

## Contesto

Le tabelle geografiche formano una gerarchia: Stato > Regione > Provincia > Comune > Codice Postale. La toponomastica (Via, Piazza, Corso, ecc.) e` trasversale. Queste tabelle alimentano lo stradario e gli indirizzi dettaglio.

Tutte le richieste richiedono autenticazione JWT (header `Authorization: Bearer <token>`).

---

## Parametri comuni per le liste paginate

Tutti gli endpoint di lista accettano i seguenti query parameters:

| Parametro  | Tipo   | Obbligatorio | Default      | Descrizione                              |
|------------|--------|--------------|--------------|------------------------------------------|
| search     | string | no           | —            | Ricerca full guidata dal catalogo lista (colonne e soglia minima di caratteri). Sotto soglia la ricerca non si applica: nessun 400 |
| limit      | int    | no           | 25           | Righe per pagina (1–200)                 |
| offset     | int    | no           | 0            | Offset per la paginazione                |
| order_by   | string | no           | descrizione  | Colonna di ordinamento, dalla whitelist dell'entita' (vedi sezioni). Valore fuori whitelist → **400** `E_VALIDATION_INPUT` (dal 2026-10-20) |
| order_dir  | string | no           | asc          | `asc` o `desc`                           |

## Formato risposta comune

Tutte le risposte usano l'envelope standard `{"data": ..., "meta": {"request_id": "..."}}`.

Le liste paginate restituiscono:

```json
{
  "data": {
    "count": 250,
    "page": 1,
    "page_size": 25,
    "total_pages": 10,
    "results": [ ... ]
  },
  "meta": { "request_id": "..." }
}
```

I lookup restituiscono `{"data": {"results": [ ... ]}, "meta": {...}}`, senza
paginazione; i campi di ogni riga sono indicati per entita'.

Creazione (`POST`): restituisce la riga creata riletta dalla stessa sorgente di
lista e dettaglio (con le descrizioni dei JOIN). Aggiornamento (`PATCH`):
restituisce `{"data": {"updated": true}}`. Dal 2026-10-20 i campi si leggono per
presenza: una chiave presente si scrive, anche `null`, che svuota un campo nullable
(ISO2/ISO3, sigla, telefono e continente dello stato; la regione della provincia);
`null` o `""` su un campo obbligatorio → 400. Una chiave fuori elenco e un corpo
senza campi → 400 `E_ANAG_VALIDAZIONE` (prima: ignorata, e 404 come un id
inesistente). Duplicati → 409 `E_ANAG_DUPLICATO`; descrizione/campi obbligatori
mancanti → 400 `E_ANAG_VALIDAZIONE`.

In caso di errore: `{"error": {"code": "...", "message": "..."}, "meta": {...}}`.

---

## 1. Stati (Nazioni)

### 1.1 Lista stati

```
GET /api/v1/anagrafiche/stati/
```

Restituisce la lista paginata degli stati (`config.stati`). Accetta i parametri comuni.

Campi riga (lista e dettaglio): `id`, `descrizione`, `sigla_stato`, `codice_iso2`,
`codice_iso3`, `codice_telefonico`, `continente`.

`order_by` ammessi: `descrizione`, `sigla_stato`, `codice_iso2`, `codice_iso3`, `continente`.

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/stati/?search=ital&limit=10"
```

### 1.2 Crea stato

```
POST /api/v1/anagrafiche/stati/
```

| Campo             | Tipo   | Obbligatorio | Descrizione                  |
|-------------------|--------|--------------|------------------------------|
| descrizione       | string | si           | Nome dello stato             |
| codice_iso2       | string | no           | Codice ISO 3166-1 alpha-2    |
| codice_iso3       | string | no           | Codice ISO 3166-1 alpha-3    |
| sigla_stato       | string | no           | Sigla stato                  |
| codice_telefonico | string | no           | Prefisso telefonico (es. +39)|
| continente        | string | no           | Continente di appartenenza   |

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"descrizione": "Italia", "codice_iso2": "IT", "codice_iso3": "ITA", "codice_telefonico": "+39", "continente": "Europa"}' \
  "https://host/api/v1/anagrafiche/stati/"
```

### 1.3 Dettaglio stato

```
GET /api/v1/anagrafiche/stati/{pk}/
```

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/stati/1/"
```

### 1.4 Aggiorna stato

```
PATCH /api/v1/anagrafiche/stati/{pk}/
```

Accetta gli stessi campi della creazione, tutti opzionali. Inviare solo i campi da modificare.

```bash
curl -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"codice_telefonico": "+39"}' \
  "https://host/api/v1/anagrafiche/stati/1/"
```

### 1.5 Lookup stati

```
GET /api/v1/anagrafiche/stati/lookup/
```

Lista per dropdown (senza paginazione), ordinata per `descrizione`. Campi:
`id`, `descrizione`, `codice_iso2`, `catalogo_comuni_completo` (forma
dell'indirizzo libero in quello stato: comune e CAP da elenco se `true`, localita'
altrimenti), `proposto` (`true` sullo stato da preselezionare, da
`script.fn_stato_proposto_id`, parametro `STATO_PROPOSTO_ISO2`).

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/stati/lookup/"
```

---

## 2. Regioni

### 2.1 Lista regioni

```
GET /api/v1/anagrafiche/regioni/
```

Oltre ai parametri comuni, accetta:

| Parametro | Tipo | Obbligatorio | Descrizione          |
|-----------|------|--------------|----------------------|
| stato_id  | int  | no           | Filtra per stato     |

Campi riga (lista e dettaglio, da `config.vw_regioni_lista`): `id`, `descrizione`,
`stato_id`, `stato_descrizione`.

`order_by` ammessi: `descrizione`, `stato_descrizione`.

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/regioni/?stato_id=1&search=lomb"
```

### 2.2 Crea regione

```
POST /api/v1/anagrafiche/regioni/
```

| Campo       | Tipo   | Obbligatorio | Descrizione            |
|-------------|--------|--------------|------------------------|
| descrizione | string | si           | Nome della regione     |
| stato_id    | int    | no           | ID dello stato padre   |

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"descrizione": "Lombardia", "stato_id": 1}' \
  "https://host/api/v1/anagrafiche/regioni/"
```

### 2.3 Dettaglio regione

```
GET /api/v1/anagrafiche/regioni/{pk}/
```

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/regioni/1/"
```

### 2.4 Aggiorna regione

```
PATCH /api/v1/anagrafiche/regioni/{pk}/
```

Campi aggiornabili: `descrizione`, `stato_id` (tutti opzionali).

```bash
curl -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"descrizione": "Lombardia"}' \
  "https://host/api/v1/anagrafiche/regioni/1/"
```

### 2.5 Lookup regioni

```
GET /api/v1/anagrafiche/regioni/lookup/
```

Lista per dropdown, ordinata per `descrizione`. Accetta filtro opzionale
`stato_id`. Campi: `id`, `descrizione`, `stato_id`.

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/regioni/lookup/?stato_id=1"
```

---

## 3. Province

### 3.1 Lista province

```
GET /api/v1/anagrafiche/province/
```

Oltre ai parametri comuni, accetta:

| Parametro   | Tipo | Obbligatorio | Descrizione          |
|-------------|------|--------------|----------------------|
| regione_id  | int  | no           | Filtra per regione   |

Campi riga (lista e dettaglio, da `config.vw_province_lista`): `id`, `descrizione`,
`sigla`, `regione_id`, `regione_descrizione`.

`order_by` ammessi: `descrizione`, `sigla`, `regione_descrizione`.

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/province/?regione_id=3&search=mil"
```

### 3.2 Crea provincia

```
POST /api/v1/anagrafiche/province/
```

| Campo       | Tipo   | Obbligatorio | Descrizione              |
|-------------|--------|--------------|--------------------------|
| descrizione | string | si           | Nome della provincia     |
| sigla       | string | si           | Sigla provincia (es. MI) |
| regione_id  | int    | no           | ID della regione padre   |

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"descrizione": "Milano", "sigla": "MI", "regione_id": 3}' \
  "https://host/api/v1/anagrafiche/province/"
```

### 3.3 Dettaglio provincia

```
GET /api/v1/anagrafiche/province/{pk}/
```

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/province/1/"
```

### 3.4 Aggiorna provincia

```
PATCH /api/v1/anagrafiche/province/{pk}/
```

Campi aggiornabili: `descrizione`, `sigla`, `regione_id` (tutti opzionali).

```bash
curl -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sigla": "MI"}' \
  "https://host/api/v1/anagrafiche/province/1/"
```

### 3.5 Lookup province

```
GET /api/v1/anagrafiche/province/lookup/
```

Lista per dropdown (senza paginazione, senza filtri), ordinata per `descrizione`.
Campi: `id`, `sigla`, `descrizione`, `regione_descrizione`.

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/province/lookup/"
```

---

## 4. Comuni

### 4.1 Lista comuni

```
GET /api/v1/anagrafiche/comuni/
```

Accetta i parametri comuni.

Campi riga (da `config.vw_comuni_lista`): `id`, `descrizione`, `provincia_id`,
`provincia_sigla`, `provincia_descrizione`, `regione_id`, `regione_descrizione`.

`order_by` ammessi: `descrizione`, `provincia_sigla`, `regione_descrizione`.

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/comuni/?search=roma&limit=10"
```

### 4.2 Crea comune

```
POST /api/v1/anagrafiche/comuni/
```

| Campo        | Tipo   | Obbligatorio | Descrizione              |
|--------------|--------|--------------|--------------------------|
| descrizione  | string | si           | Nome del comune          |
| provincia_id | int    | no           | ID della provincia padre |

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"descrizione": "Roma", "provincia_id": 58}' \
  "https://host/api/v1/anagrafiche/comuni/"
```

---

## 5. Toponomastica

### 5.1 Lista toponomastica

```
GET /api/v1/anagrafiche/toponomastica/
```

Accetta i parametri comuni.

Campi riga (lista e dettaglio): `id`, `descrizione`, `attivo`.

`order_by` ammessi: `descrizione`, `attivo`.

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/toponomastica/?search=via"
```

### 5.2 Crea toponomastica

```
POST /api/v1/anagrafiche/toponomastica/
```

| Campo       | Tipo   | Obbligatorio | Descrizione                       |
|-------------|--------|--------------|-----------------------------------|
| descrizione | string | si           | Denominazione (es. Via, Piazza)   |

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"descrizione": "Corso"}' \
  "https://host/api/v1/anagrafiche/toponomastica/"
```

### 5.3 Dettaglio toponomastica

```
GET /api/v1/anagrafiche/toponomastica/{pk}/
```

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/toponomastica/1/"
```

### 5.4 Aggiorna toponomastica

```
PATCH /api/v1/anagrafiche/toponomastica/{pk}/
```

| Campo       | Tipo    | Obbligatorio | Descrizione            |
|-------------|---------|--------------|------------------------|
| descrizione | string  | no           | Nuova denominazione    |
| attivo      | boolean | no           | Flag attivo/disattivo (booleano JSON; altro tipo → 400 `E_VALIDATION_INPUT`) |

```bash
curl -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"attivo": false}' \
  "https://host/api/v1/anagrafiche/toponomastica/1/"
```

---

## 6. Codici Postali

### 6.1 Lista codici postali

```
GET /api/v1/anagrafiche/codici-postali/
```

Oltre ai parametri comuni, accetta:

| Parametro  | Tipo | Obbligatorio | Descrizione          |
|------------|------|--------------|----------------------|
| comune_id  | int  | no           | Filtra per comune    |

L'ordinamento predefinito e` per `codice`. `order_by` ammessi: `codice`,
`comune_descrizione`, `provincia_sigla`.

Campi riga (lista e dettaglio, da `config.vw_codici_postali_lista`): `id`, `codice`,
`comune_id`, `comune_descrizione`, `provincia_id`, `provincia_sigla`.

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/codici-postali/?comune_id=1&search=001"
```

### 6.2 Crea codice postale

```
POST /api/v1/anagrafiche/codici-postali/
```

| Campo      | Tipo   | Obbligatorio | Descrizione              |
|------------|--------|--------------|--------------------------|
| codice     | string | si           | Codice postale (es. 00100)|
| comune_id  | int    | si           | ID del comune associato  |

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"codice": "00100", "comune_id": 1}' \
  "https://host/api/v1/anagrafiche/codici-postali/"
```

### 6.3 Dettaglio codice postale

```
GET /api/v1/anagrafiche/codici-postali/{pk}/
```

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/codici-postali/1/"
```

### 6.4 Aggiorna codice postale

```
PATCH /api/v1/anagrafiche/codici-postali/{pk}/
```

Campi aggiornabili: `codice`, `comune_id` (tutti opzionali).

```bash
curl -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"codice": "00118"}' \
  "https://host/api/v1/anagrafiche/codici-postali/1/"
```

---

## Dipendenze DB

- `config.stati` -- tabella stati/nazioni
- `config.regioni` -- tabella regioni (FK verso stati); vista `config.vw_regioni_lista`
- `config.province` -- tabella province (FK verso regioni); vista `config.vw_province_lista`
- `config.comuni` -- tabella comuni (FK verso province); vista `config.vw_comuni_lista`
- `config.toponomastica` -- tabella tipi via
- `config.codici_postali` -- tabella CAP (FK verso comuni); vista `config.vw_codici_postali_lista`
- `script.fn_stato_proposto_id` -- stato proposto nel lookup stati

## Note

- La gerarchia geografica e`: Stato > Regione > Provincia > Comune > Codice Postale.
- I filtri gerarchici (es. `stato_id` su regioni, `regione_id` su province, `comune_id` su codici postali) permettono di popolare dropdown a cascata nel frontend.
- Gli endpoint lookup restituiscono liste leggere senza paginazione (campi indicati per entita'), pensati per dropdown e autocomplete.
- I comuni non hanno endpoint dettaglio/update ne` lookup separati nella versione corrente.
