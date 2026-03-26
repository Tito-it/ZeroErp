# API Conti Bancari Ruolo (Anagrafiche)

## Scopo

Endpoint REST per la gestione dei conti bancari a livello ruolo con supporto
istanza. La lista implementa la cascata a 3 livelli: istanza specifica,
ruolo generico, soggetto (fallback readonly).

## Contesto

I legami ruolo ↔ conto sono nella tabella `anagrafiche.soggetti_ruoli_conti_bancari`.
La colonna `istanza_utility_id` (nullable, bigint FK → `anagrafiche.istanze_utilities`)
consente conti specifici per istanza di servizio
(es. conto INCASSO GAS Corridonia diverso da INCASSO GAS Civitanova).

Il registro IBAN (`anagrafiche.conti_bancari`) e` condiviso: il legame punta
a un conto del registro tramite `conto_bancario_id`. La creazione usa
get_or_create per evitare duplicati IBAN.

L'autenticazione avviene tramite token JWT. Le risposte seguono l'envelope
standard `{"data": ...}`.

## Base URL

```
/api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/conti-bancari/
```

---

## 1. Lista conti bancari ruolo (cascata 3 livelli)

Restituisce i conti del ruolo con cascata per `uso`.

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/conti-bancari/` |

### Parametri query

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `istanza_utility_id` | int | No | Se presente, attiva il livello 1 (istanza specifica) |

### Cascata di risoluzione

| Priorita` | Livello | Condizione | `fonte` | Editabile |
|---|---|---|---|---|
| 1 | Istanza | `istanza_utility_id = X` | `istanza` | Si` |
| 2 | Ruolo generico | `istanza_utility_id IS NULL`, uso non coperto da L1 | `ruolo` | Si` |
| 3 | Soggetto | Uso non coperto da L1+L2 | `soggetto` | No (readonly) |

Senza `istanza_utility_id`, la cascata parte dal livello 2.

### Risposta (200)

```json
{
  "data": {
    "conti_ruolo": [
      {
        "id": 1,
        "conto_bancario_id": 10,
        "uso": "INCASSO",
        "predefinito": true,
        "valido_dal": "2026-01-01",
        "valido_al": null,
        "intestazione_dichiarata": null,
        "verificato": true,
        "bloccato": false,
        "istanza_utility_id": 100,
        "iban": "IT60X0542811101000000123456",
        "bic_swift": "BPPIITRRXXX",
        "intestatario_predefinito": "Mario Rossi",
        "paese": "IT",
        "conto_attivo": true,
        "bank_branch_id": 1,
        "filiale_nome": "Banca Popolare Milano",
        "bank_code": "05428",
        "branch_code": "11101",
        "fonte": "istanza"
      }
    ],
    "conti_ereditati": [
      {
        "...": "stessa struttura, fonte='soggetto'"
      }
    ]
  }
}
```

### Dipendenze DB

- Tabella `anagrafiche.soggetti_ruoli_conti_bancari` (con `istanza_utility_id`)
- Tabella `anagrafiche.soggetti_conti_bancari` (fallback soggetto)
- Tabella `anagrafiche.conti_bancari` (registro IBAN)
- Tabella `anagrafiche.istanze_utilities` (FK istanza)

---

## 2. Crea legame ruolo ↔ conto

Associa un conto al ruolo. Se l'IBAN non esiste nel registro, viene creato
(get_or_create atomico).

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/conti-bancari/` |

### Body (JSON)

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `iban` | string | Si`* | IBAN (15-34 char alfanumerici, normalizzato uppercase) |
| `bic_swift` | string | No | BIC/SWIFT |
| `bank_branch_id` | int | Si`* | ID filiale bancaria |
| `conto_bancario_id` | int | No* | ID diretto dal registro (bypass IBAN resolution) |
| `uso` | string | No | `INCASSO`, `PAGAMENTO`, `RIMBORSO`, `GENERICO` (default) |
| `predefinito` | bool | No | Se predefinito per questo uso |
| `istanza_utility_id` | int | No | Se presente, legame specifico per istanza |
| `valido_dal` | date | No | Data inizio validita` |
| `valido_al` | date | No | Data fine validita` |

*`iban` + `bank_branch_id` oppure `conto_bancario_id` (mutualmente esclusivi).

### Risposta (200)

```json
{
  "data": {
    "id": 20,
    "conto_bancario_id": 10,
    "uso": "INCASSO",
    "predefinito": true,
    "istanza_utility_id": 100
  }
}
```

### Regole

- Vincolo UNIQUE parziale: un solo legame per `(soggetto_ruolo_id, istanza_utility_id, conto_bancario_id, uso)`
- Un solo predefinito per `(soggetto_ruolo_id, istanza_utility_id, uso)`
- `istanza_utility_id = NULL` crea un legame generico del ruolo

---

## 3. Aggiorna legame ruolo ↔ conto

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/conti-bancari/{cb_id}/` |

### Body (JSON) — campi opzionali

| Campo | Tipo | Descrizione |
|---|---|---|
| `uso` | string | Cambia tipo d'uso |
| `predefinito` | bool | Segna/rimuovi come predefinito |
| `istanza_utility_id` | int/null | Assegna/cambia/rimuovi istanza |
| `valido_dal` | date | Inizio validita` |
| `valido_al` | date | Fine validita` |
| `intestazione_dichiarata` | string | Intestazione dichiarata |
| `verificato` | bool | Flag verifica |
| `bloccato` | bool | Flag blocco |

### Risposta (200)

```json
{ "data": { "updated": true } }
```

---

## 4. Elimina legame ruolo ↔ conto

| | |
|---|---|
| **Metodo** | `DELETE` |
| **URL** | `/api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/conti-bancari/{cb_id}/` |

### Risposta (200)

```json
{ "data": { "deleted": true } }
```

---

## Dipendenze DB

| Oggetto | Schema | Tipo | Ruolo |
|---|---|---|---|
| `anagrafiche.soggetti_ruoli_conti_bancari` | anagrafiche | tabella | Legami ruolo con istanza |
| `anagrafiche.soggetti_conti_bancari` | anagrafiche | tabella | Fallback soggetto |
| `anagrafiche.conti_bancari` | anagrafiche | tabella | Registro IBAN condiviso |
| `anagrafiche.bank_branches` | anagrafiche | tabella | Filiali bancarie |
| `anagrafiche.istanze_utilities` | anagrafiche | tabella | FK istanza_utility_id |

## Note di migrazione

- Changeset DB: `20260325-03-replace-utility-with-istanza-src-bancari-mctit.yaml` (schema)
- Changeset DB: `20260325-05-recreate-conti-bancari-chain-istanza-mctit.yaml` (vista + funzione)
- Le viste non espongono piu` `utility_codice` — il frontend lo ha dal payload cliente
- Campo `fonte` nella risposta lista: `istanza`, `ruolo`, `soggetto`
