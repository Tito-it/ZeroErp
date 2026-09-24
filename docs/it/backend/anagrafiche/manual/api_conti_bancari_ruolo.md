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
| `bic_swift` | string | No | BIC/SWIFT (solo se l'IBAN entra nuovo nel registro) |
| `intestatario_predefinito` | string | No | Intestatario del conto nel registro (solo se l'IBAN entra nuovo) |
| `bank_branch_id` | int | Si`* | ID filiale bancaria |
| `conto_bancario_id` | int | No* | ID diretto dal registro (bypass IBAN resolution) |
| `uso` | string | No | `INCASSO`, `PAGAMENTO`, `RIMBORSO`, `GENERICO` (default DB); case-insensitive |
| `predefinito` | bool | No | Se predefinito per questo uso |
| `istanza_utility_id` | int | No | Se presente, legame specifico per istanza |
| `valido_dal` | date | No | Data inizio validita` |
| `valido_al` | date | No | Data fine validita`: non deve precedere `valido_dal` (vedi Errori) |
| `intestazione_dichiarata` | string | No | Intestazione dichiarata |
| `verificato` | bool | No | Flag verifica |
| `bloccato` | bool | No | Flag blocco (incompatibile con `predefinito=true`) |

\*`conto_bancario_id` **vince**: se c'e', `iban`, `bic_swift`, `bank_branch_id` e
`intestatario_predefinito` sono ignorati. Senza, servono `iban` +
`bank_branch_id`.

### Risposta (200)

La riga del legame appena creato:

```json
{
  "data": {
    "id": 20,
    "conto_bancario_id": 10,
    "uso": "INCASSO",
    "predefinito": true,
    "valido_dal": "2026-01-01",
    "valido_al": null,
    "intestazione_dichiarata": null,
    "verificato": false,
    "bloccato": false,
    "istanza_utility_id": 100
  }
}
```

### Regole

- Vincolo UNIQUE parziale: un solo legame per `(soggetto_ruolo_id, istanza_utility_id, conto_bancario_id, uso)`
- Un solo predefinito per `(soggetto_ruolo_id, istanza_utility_id, uso)`
- `istanza_utility_id = NULL` crea un legame generico del ruolo
- Il get_or_create del registro IBAN e la creazione del legame stanno in una
  sola transazione: se il legame fallisce, l'IBAN nuovo non resta nel registro
- Il conto del registro deve essere attivo (guard DB)

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
| `valido_dal` | date/null | Inizio validita` |
| `valido_al` | date/null | Fine validita`: non deve precedere `valido_dal` |
| `intestazione_dichiarata` | string | Intestazione dichiarata |
| `verificato` | bool | Flag verifica |
| `bloccato` | bool | Flag blocco |

Stringa vuota su `valido_dal`, `valido_al`, `intestazione_dichiarata`,
`istanza_utility_id` = `NULL`. Le chiavi fuori da questa tabella sono ignorate.
⚠️ A differenza del POST, qui `uso` **non** è validato né portato in maiuscolo
dal service: un valore fuori elenco lo rifiuta il `CHECK` del DB (vedi Errori).

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

## Errori

| Codice | HTTP | Quando | Sede |
|---|---|---|---|
| `E_ANAG_VALIDAZIONE` | 400 | IBAN mancante o fuori formato; `bank_branch_id` mancante; `uso` fuori elenco (solo POST); `predefinito` e `bloccato` entrambi veri (anche sommando payload e stato corrente, in PATCH) | service |
| `E_DATA_AL_MINORE_DAL` | 400, campo `valido_al` | `valido_al < valido_dal`, in POST e PATCH. Il service non lo anticipa (dal 2026-09-23) | guard comune `script.trgfn_guard_date_validita` |
| `E_CONTO_BANCARIO` | 400, campo `conto_bancario_id` | il conto del registro non è attivo | `anagrafiche.trgfn_soggetti_ruoli_conti_bancari_guard` |
| `E_ANAG_DUPLICATO` | 409 | legame già presente per lo stesso ruolo/istanza/conto/uso, o secondo predefinito per lo stesso uso. ⚠️ Vedi nota sotto | service (qualunque `IntegrityError`) |
| `E_ANAG_CONTO_NOT_FOUND` | ⚠️ 400 | `conto_bancario_id` non esiste nel registro | service |
| `E_ANAG_NOT_FOUND` | 404 | PATCH: legame inesistente o di un altro ruolo. ⚠️ Anche PATCH senza nessun campo ammesso | service |
| `E_ANAG_CONTO_SOGGETTO_NOT_FOUND` | ⚠️ 400 | DELETE: legame inesistente o di un altro ruolo | service |

⚠️ **Difetti noti (2026-09-24), non ancora corretti** — E-1 ed E-7 di [analisi-be-difetti-emersi-verifica-doc-api-core.md](../../../dev/work-in-progress/analisi-be-difetti-emersi-verifica-doc-api-core.md):

- `E_ANAG_CONTO_NOT_FOUND` e `E_ANAG_CONTO_SOGGETTO_NOT_FOUND` **non sono a
  catalogo**: il traduttore li tratta come codici sconosciuti e risponde
  **400** «Errore di validazione.» invece di un 404;
- in POST e PATCH ogni `IntegrityError` esce come `E_ANAG_DUPLICATO` («già
  associato»): anche un `uso` fuori elenco in PATCH (`CHECK`) o un
  `istanza_utility_id` inesistente (FK);
- una PATCH senza nessun campo ammesso risponde 404 «Associazione non
  trovata», anche quando il legame esiste.

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
