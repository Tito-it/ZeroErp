# API Conti Bancari Soggetto e lookup IBAN/filiali (Anagrafiche)

## Scopo

Endpoint REST per i conti bancari a livello **soggetto** (lista, creazione,
modifica, eliminazione del legame) e per i due autocomplete che servono a
compilarli: il registro IBAN e le filiali bancarie.

## Contesto

I legami soggetto ↔ conto stanno in `anagrafiche.soggetti_conti_bancari`; il
registro IBAN (`anagrafiche.conti_bancari`) è condiviso con i legami di ruolo
([api_conti_bancari_ruolo.md](api_conti_bancari_ruolo.md)). Il conto del
soggetto è anche il **livello 3** della cascata dei conti di ruolo: quando un
ruolo non ha un conto per un certo `uso`, la lista del ruolo mostra quello del
soggetto, in sola lettura.

Tutte le rotte sono di area `anagrafiche`, oggetto permessi
`("anagrafiche", "conto_bancario")`, JWT obbligatorio. Risposte nell'envelope
standard `{"data": ...}`.

Guida funzionale: [gestione-conti-bancari](../../../guide/gestione-conti-bancari.md).

## Base URL

```
/api/v1/anagrafiche/soggetti/{soggetto_id}/conti-bancari/
/api/v1/anagrafiche/conti-bancari/lookup/
/api/v1/anagrafiche/bank-branches/lookup/
```

`soggetto_id` è l'UUID del soggetto.

---

## 1. Lista conti del soggetto

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/soggetti/{soggetto_id}/conti-bancari/` |

Nessun parametro. Ordine: `uso`, poi il predefinito prima, poi `id`.

### Risposta (200)

```json
{
  "data": {
    "results": [
      {
        "id": 5,
        "conto_bancario_id": 10,
        "uso": "INCASSO",
        "predefinito": true,
        "valido_dal": "2026-01-01",
        "valido_al": null,
        "intestazione_dichiarata": null,
        "verificato": true,
        "bloccato": false,
        "iban": "IT60X0542811101000000123456",
        "bic_swift": "BPPIITRRXXX",
        "intestatario_predefinito": "Mario Rossi",
        "paese": "IT",
        "conto_attivo": true,
        "bank_branch_id": 1,
        "filiale_nome": "Banca Popolare Milano",
        "bank_code": "05428",
        "branch_code": "11101"
      }
    ]
  }
}
```

Le colonne del conto (`iban` … `branch_code`) vengono dal registro e dalla
filiale, con la stessa proiezione della lista di ruolo.

---

## 2. Crea legame soggetto ↔ conto

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/anagrafiche/soggetti/{soggetto_id}/conti-bancari/` |

### Body (JSON)

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `conto_bancario_id` | int | No* | Conto già nel registro (dall'autocomplete IBAN) |
| `iban` | string | Sì* | IBAN, 15-34 caratteri alfanumerici (spazi tolti, maiuscolo) |
| `bank_branch_id` | int | Sì* | Filiale del conto |
| `bic_swift` | string | No | Solo se l'IBAN entra nuovo nel registro |
| `intestatario_predefinito` | string | No | Solo se l'IBAN entra nuovo nel registro |
| `uso` | string | No | `INCASSO`, `PAGAMENTO`, `RIMBORSO`, `GENERICO` (default `GENERICO`); maiuscole/minuscole indifferenti |
| `predefinito` | bool | No | Predefinito per questo uso |
| `valido_dal` / `valido_al` | date | No | Validità; la fine non precede l'inizio |
| `intestazione_dichiarata` | string | No | Intestazione dichiarata |
| `verificato` | bool | No | Flag verifica |
| `bloccato` | bool | No | Flag blocco (incompatibile con `predefinito=true`) |

\*`conto_bancario_id` **vince**: se c'è, i campi del registro sono ignorati e il
conto deve esistere. Senza, servono `iban` + `bank_branch_id`, e l'IBAN si cerca
o si crea nel registro (get_or_create). Registro e legame stanno in **una**
transazione: se il legame fallisce, un IBAN nuovo non resta nel registro.

### Risposta (200)

La riga del legame creato (`id`, `conto_bancario_id`, `uso`, `predefinito`,
`valido_dal`, `valido_al`, `intestazione_dichiarata`, `verificato`, `bloccato`).

### Regole

- Un solo legame per `(soggetto, conto, uso)`.
- Un solo predefinito per `(soggetto, uso)`.
- Un conto con uso `INCASSO` appartiene a un soggetto solo (vincolo di
  esclusione `ex_scb_conto_incasso_un_solo_soggetto`): è ciò che regge il
  perimetro degli incassi.
- Soggetto e conto del registro devono essere attivi (guard DB).

---

## 3. Aggiorna legame

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/anagrafiche/soggetti/{soggetto_id}/conti-bancari/{cb_id}/` |

Campi ammessi, tutti opzionali: `uso`, `predefinito`, `valido_dal`,
`valido_al`, `intestazione_dichiarata`, `verificato`, `bloccato`. Stringa vuota
su date e intestazione = `NULL`. Una chiave fuori elenco (anche
`istanza_utility_id`, che esiste solo sul legame di ruolo) → 400; un corpo
senza campi → 400. `predefinito` e `bloccato` si controllano sommando payload e
stato corrente. Come nel POST, `uso` è portato in maiuscolo e validato dal
service: un valore fuori elenco → 400 `E_ANAG_VALIDAZIONE`, campo `uso`.

Il legame deve appartenere al soggetto del path. Risposta:
`{"data": {"updated": true}}`.

---

## 4. Elimina legame

| | |
|---|---|
| **Metodo** | `DELETE` |
| **URL** | `/api/v1/anagrafiche/soggetti/{soggetto_id}/conti-bancari/{cb_id}/` |

Risposta: `{"data": {"deleted": true}}`. Il conto resta nel registro.

---

## 5. Lookup registro IBAN

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/conti-bancari/lookup/` |

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `search` | string | Sì | Frammento di IBAN (gli spazi non contano). Sotto i 2 caratteri la lista è vuota |
| `limit` | int | No | Default 10, tetto e validazione delle liste (`parse_list_params`) |

Solo conti **attivi** del registro, ordinati per IBAN. Risposta
`{"data": {"results": [...]}}` con `id`, `iban`, `bic_swift`,
`intestatario_predefinito`, `paese`, `bank_branch_id`, `attivo`, `verificato`,
`filiale_nome`, `bank_code`, `branch_code`. L'`id` è il `conto_bancario_id` da
passare alla creazione del legame.

---

## 6. Lookup filiali bancarie

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/bank-branches/lookup/` |

Stessi parametri del lookup IBAN. La ricerca vale su nome della filiale,
codice banca (ABI), codice filiale (CAB) e BIC; solo filiali attive, ordinate
per nome e codice filiale. Risposta `{"data": {"results": [...]}}` con `id`,
`filiale_nome`, `bank_code`, `branch_code`, `bic_swift`, `attivo`.

---

## Errori

| Codice | HTTP | Quando | Sede |
|---|---|---|---|
| `E_ANAG_NOT_FOUND` | 404 | soggetto inesistente; PATCH su un legame inesistente o di un altro soggetto | service |
| `E_ANAG_VALIDAZIONE` | 400 | IBAN mancante o fuori formato; filiale mancante; `uso` fuori elenco (POST e PATCH, dal service, campo `uso`); `predefinito` e `bloccato` insieme; chiave fuori elenco o corpo vuoto in PATCH; vincolo DB non mappato | service, mappa vincoli |
| `E_DATA_AL_MINORE_DAL` | 400, campo `valido_al` | `valido_al < valido_dal` | guard comune `script.trgfn_guard_date_validita` |
| `E_CONTO_BANCARIO` | 400 | il conto del registro non è attivo | `anagrafiche.trgfn_soggetti_conti_bancari_guard` |
| `E_ANAG_DUPLICATO` | 409 | legame già presente per lo stesso conto e uso; secondo predefinito per lo stesso uso (campo `predefinito`); conto di incasso già di un altro soggetto | mappa vincoli |
| `E_ANAG_FK` | 400 | conto o soggetto inesistenti al momento della scrittura | mappa vincoli |
| `E_ANAG_CONTO_NOT_FOUND` | 404 | `conto_bancario_id` non esiste nel registro | service |
| `E_ANAG_CONTO_SOGGETTO_NOT_FOUND` | 404 | DELETE: legame inesistente o di un altro soggetto | service |
| `E_VALIDATION_INPUT` | 400 | corpo illeggibile o che non è un oggetto JSON | `handle_post_json` / `corpo_oggetto` |

La mappa vincoli è `_VINCOLI_LEGAME_SOGGETTO` di `conti_bancari_service.py`;
il presidio `anagrafiche/tests/db/test_conti_bancari_vincoli_mappati_db.py`
la confronta coi vincoli veri della tabella, nei due versi.

`E_ANAG_CONTO_NOT_FOUND` ed `E_ANAG_CONTO_SOGGETTO_NOT_FOUND` sono a catalogo
come `NON_TROVATO` dal 2026-10-07: fino ad allora uscivano **400** «Errore di
validazione.» (E-1 di [analisi-be-difetti-emersi-verifica-doc-api-core.md](../../../dev/work-done/analisi-be-difetti-emersi-verifica-doc-api-core.md)).

---

## Dipendenze DB

| Oggetto | Tipo | Ruolo |
|---|---|---|
| `anagrafiche.soggetti_conti_bancari` | tabella | Legami soggetto ↔ conto |
| `anagrafiche.conti_bancari` | tabella | Registro IBAN condiviso |
| `anagrafiche.bank_branches` | tabella | Filiali bancarie |
| `anagrafiche.soggetti` | tabella | Esistenza del soggetto |
| `anagrafiche.trgfn_soggetti_conti_bancari_guard` | trigger | Conto del registro attivo |
| `script.trgfn_guard_date_validita` | trigger | Fine validità ≥ inizio |

