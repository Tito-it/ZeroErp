# API Indirizzi Ruolo (Anagrafiche)

## Scopo

Endpoint REST per la gestione degli indirizzi a livello ruolo con supporto
istanza. Implementa la cascata a 3 livelli: istanza specifica, ruolo generico,
soggetto (fallback readonly).

## Contesto

Gli indirizzi a livello ruolo risiedono nella tabella `anagrafiche.indirizzi`
(distinta da `anagrafiche.indirizzi_soggetti` che contiene quelli a livello soggetto).
La colonna `istanza_utility_id` (nullable, bigint FK → `anagrafiche.istanze_utilities`)
consente indirizzi specifici per istanza di servizio
(es. fatturazione GAS Corridonia diversa da fatturazione GAS Civitanova).

L'autenticazione avviene tramite token JWT. Le risposte seguono l'envelope
standard `{"data": ...}`. I vincoli di unicita` e la validazione
`tipo_indirizzo_id` sono gestiti dal DB (trigger guard + partial unique index).

## Base URL

```
/api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/indirizzi/
```

---

## 1. Lista indirizzi ruolo (cascata 3 livelli)

Restituisce gli indirizzi del ruolo con cascata per `tipo_indirizzo_id`.

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/indirizzi/` |

### Parametri query

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `istanza_utility_id` | int | No | Se presente, attiva il livello 1 (istanza specifica) |

### Cascata di risoluzione

| Priorita` | Livello | Condizione | `fonte` | Editabile |
|---|---|---|---|---|
| 1 | Istanza | `istanza_utility_id = X` | `istanza` | Si` |
| 2 | Ruolo generico | `istanza_utility_id IS NULL`, tipo non coperto da L1 | `ruolo` | Si` |
| 3 | Soggetto | Tipo non coperto da L1+L2 | `soggetto` | No (readonly) |

Senza `istanza_utility_id`, la cascata parte dal livello 2.

### Risposta (200)

```json
{
  "data": {
    "indirizzi_ruolo": [
      {
        "id": 1,
        "soggetto_ruolo_id": 64,
        "istanza_utility_id": 100,
        "tipo_indirizzo_id": 1,
        "tipo_indirizzo_codice": "FAT",
        "tipo_indirizzo_descrizione": "Fatturazione",
        "is_normalizzato": true,
        "indirizzo_dettaglio_id": 100,
        "indirizzo_display": "Via Roma 1, 20100 Milano MI",
        "indirizzo_libero": null,
        "comune_id": 5,
        "comune_descrizione": "Milano",
        "cap": "20100",
        "provincia_sigla": "MI",
        "stato_id": null,
        "stato_descrizione": null,
        "stato_iso2": null,
        "codice_postale_id": 10,
        "cap_codice": "20100",
        "det_comune_id": 5,
        "descrizione_comune": "Milano",
        "stradario_id": 7,
        "stradario_display": "VIA ROMA",
        "civico": 1,
        "estensione_civico": null,
        "palazzina": null,
        "scala": null,
        "piano": null,
        "interno": null,
        "utility_codice": "GAS",
        "fonte": "istanza"
      }
    ],
    "indirizzi_soggetto": [
      {
        "...": "stessa struttura, fonte='soggetto'"
      }
    ]
  }
}
```

`det_comune_id` e `descrizione_comune` sono alias di `comune_id` e
`comune_descrizione`; `stradario_display` e' la via normalizzata (`via_norm`).
`utility_codice` e' la utility dell'istanza (da `istanze_dati_precontrattuali` o,
in mancanza, dal billing account dell'istanza), `null` senza istanza.

`istanza_utility_id` non intero → 400.

### Dipendenze DB

- Vista `anagrafiche.vw_indirizzi_resolved_ruolo` (con `istanza_utility_id`)
- Vista `anagrafiche.vw_indirizzi_resolved_soggetto` (fallback)

---

## 2. Crea indirizzo ruolo

Crea un indirizzo associato al ruolo (anche di un'istanza) con la madre del DB
`anagrafiche.fn_crea_indirizzo_ruolo`. Il tipo si indica per codice; l'indirizzo
in una di tre forme: libera, dettaglio gia' risolto, via da risolvere.

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/indirizzi/` |

### Body (JSON)

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `tipo_indirizzo_codice` | string | Si` | Codice interno del tipo indirizzo (es. `RES`, `FATT`); validato dal trigger guard vs matrice ammessi |
| `istanza_utility_id` | int | No | Se presente, indirizzo specifico per istanza |
| **Forma libera** | | | |
| `indirizzo_libero` | string | * | Testo libero dell'indirizzo |
| `stato_id` | int | No | Stato |
| `comune_id`, `codice_postale_id` | int | No | Comune e CAP da catalogo (stato con catalogo comuni completo) |
| `administrative_area`, `locality`, `sublocality`, `postal_code` | string | No | Forma estera: per uno stato senza catalogo dei comuni |
| **Dettaglio gia' risolto** | | | |
| `indirizzo_dettaglio_id` | int | * | ID dettaglio per indirizzo normalizzato |
| **Via da risolvere** | | | |
| `stradario_id` | int | * | Via esistente dello stradario |
| `toponomastica_id`, `descrizione_via`, `comune_id`, `codice_postale_id` | | * | Via nuova (tutti obbligatori se manca `stradario_id`) |
| `civico`, `estensione_civico`, `palazzina`, `scala`, `piano`, `interno` | | No | Dati civico |

*Senza `indirizzo_libero` ne' `indirizzo_dettaglio_id` vale la forma «via da
risolvere»: serve `stradario_id` oppure i quattro campi della via nuova. La
forma dell'indirizzo libero la giudica il trigger della tabella. Stringhe vuote e
`null` valgono assenti; una chiave estranea la rifiuta il DB
(`E_CAMPO_NON_AMMESSO`).

### Risposta (200)

```json
{
  "data": {
    "id": 50,
    "soggetto_ruolo_id": 64,
    "administrative_area": null,
    "codice_postale_id": null,
    "comune_id": null,
    "indirizzo_dettaglio_id": 100,
    "indirizzo_libero": null,
    "istanza_utility_id": 100,
    "locality": null,
    "postal_code": null,
    "stato_id": null,
    "sublocality": null,
    "tipo_indirizzo_id": 1
  },
  "meta": { "request_id": "..." }
}
```

### Errori

| Codice | HTTP | Causa |
|---|---|---|
| `E_ANAG_VALIDAZIONE` | 400 | `tipo_indirizzo_codice` mancante; via da risolvere incompleta |
| `E_ANAG_DUPLICATO` | 409 | Indirizzo con questo tipo gia' presente per il ruolo/istanza |

### Regole

- Il trigger `trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo` valida il
  tipo contro la matrice `config.tipi_ruolo_tipi_indirizzo`
- Vincolo UNIQUE parziale: un solo indirizzo per `(soggetto_ruolo_id, istanza_utility_id, tipo_indirizzo_id)`
- `istanza_utility_id` assente crea un indirizzo generico del ruolo

---

## 3. Aggiorna indirizzo ruolo

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/indirizzi/{indirizzo_id}/` |

### Body (JSON) — campi opzionali

| Campo | Tipo | Descrizione |
|---|---|---|
| `tipo_indirizzo_id` | int | Cambia tipo |
| `istanza_utility_id` | int/null | Assegna/cambia/rimuovi istanza |
| `indirizzo_dettaglio_id` | int | Cambia indirizzo fisico |
| `indirizzo_libero` | string | Cambia testo libero |
| `stato_id` | int | Cambia stato |
| `comune_id` | int | Cambia comune |
| `codice_postale_id` | int | Cambia CAP |
| `administrative_area` | string | Forma estera |
| `locality` | string | Forma estera |
| `sublocality` | string | Forma estera |
| `postal_code` | string | Forma estera |

### Risposta (200)

```json
{ "data": { "updated": true } }
```

### Errori

| Codice | HTTP | Causa |
|---|---|---|
| `E_ANAG_VALIDAZIONE` | 400 | Chiave fuori dall'elenco sopra |
| `E_ANAG_NOT_FOUND` | 404 | Indirizzo inesistente o di un altro ruolo; corpo vuoto |

### Regole

- Ownership check: `soggetto_ruolo_id` deve corrispondere
- Solo i campi inviati vengono aggiornati (delta update); le stringhe vuote dei campi nullable valgono `NULL`

---

## 4. Elimina indirizzo ruolo

| | |
|---|---|
| **Metodo** | `DELETE` |
| **URL** | `/api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/indirizzi/{indirizzo_id}/` |

### Risposta (200)

```json
{ "data": { "deleted": true } }
```

### Regole

- Indirizzo inesistente o di un altro ruolo → 404 `E_ANAG_NOT_FOUND`

- Ownership check: `soggetto_ruolo_id` deve corrispondere
- Solo indirizzi livello ruolo sono eliminabili (fonte `istanza` o `ruolo`)
- Indirizzi soggetto (fonte `soggetto`) non sono raggiungibili da questo endpoint

---

## Dipendenze DB

| Oggetto | Schema | Tipo | Ruolo |
|---|---|---|---|
| `anagrafiche.indirizzi` | anagrafiche | tabella | Dati indirizzi livello ruolo |
| `anagrafiche.indirizzi_soggetti` | anagrafiche | tabella | Fallback livello soggetto |
| `anagrafiche.vw_indirizzi_resolved_ruolo` | anagrafiche | vista | Lista resolved con istanza |
| `anagrafiche.vw_indirizzi_resolved_soggetto` | anagrafiche | vista | Fallback soggetto |
| `anagrafiche.istanze_utilities` | anagrafiche | tabella | FK istanza_utility_id |
| `config.tipi_ruolo_tipi_indirizzo` | config | tabella | Matrice tipi ammessi |

## Note di migrazione

- Changeset DB: `20260325-02-replace-utility-with-istanza-indirizzi-mctit.yaml` (schema)
- Changeset DB: `20260325-04-recreate-indirizzi-chain-istanza-mctit.yaml` (viste + funzioni)
- Le viste non espongono `utility_codice`: la GET lo risolve per riga dall'istanza (vedi §1)
