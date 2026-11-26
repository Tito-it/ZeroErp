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
        "tipo_indirizzo_codice_interno": "FATT",
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
| `tipo_indirizzo_codice_interno` | string | Si` | Codice interno del tipo indirizzo (es. `RES`, `FATT`); validato dal trigger guard vs matrice ammessi |
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

*La forma la decide il database da ciò che arriva (dal 2026-11-26 il service non
la anticipa più, §21.7 di brief-db-revisione-anagrafiche): senza dettaglio,
senza civico e senza una via (né `stradario_id`, né toponimo e nome di una via
nuova) è un indirizzo libero, anche se il testo è vuoto, e lo giudica il
trigger della tabella; una via nuova a cui manca il toponimo, il nome, il comune
o il CAP la rifiuta `fn_create_indirizzo` sul campo che manca (guida
[gestione-degli-indirizzi](../../../guide/gestione-degli-indirizzi.md), R3). Il service controlla solo che gli id della via,
quando ci sono, siano interi positivi. Stringhe vuote e
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
| `E_ANAG_VALIDAZIONE` | 400 | `tipo_indirizzo_codice_interno` mancante; un id della via (`stradario_id`, `toponomastica_id`, `comune_id`, `codice_postale_id`) presente e non intero positivo |
| `E_INDIRIZZO_VIA_NUOVA_INCOMPLETA` | 400 | Via nuova senza uno dei quattro campi: la rifiuta `anagrafiche.fn_create_indirizzo`, `error.fields` = il campo che manca (dal 2026-11-26 il service non la anticipa più) |
| `E_INDIRIZZO_LIBERO_INCOMPLETO` | 400 | Elemento senza via, senza dettaglio e senza testo: per il DB è un indirizzo libero, e lo rifiuta il guard della forma libera sul campo `indirizzo_libero` |
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
| `E_ANAG_VALIDAZIONE` | 400 | Chiave fuori dall'elenco sopra; corpo vuoto (dal 2026-10-20: prima 404) |
| `E_ANAG_NOT_FOUND` | 404 | Indirizzo inesistente o di un altro ruolo |
| `E_INDIRIZZO_OBBLIGATORIO_MANCANTE` | 400 | Il cambio di tipo toglie al ruolo un indirizzo obbligatorio, e non c'è il ripiego (giudicato al commit) |
| `E_INDIRIZZO_RUOLO_TITOLARE_IMMUTABILE` | 409 | Il ruolo di un indirizzo non cambia: la colonna non è fra quelle del body, il lucchetto resta come presidio |

### Regole

- Ownership check: `soggetto_ruolo_id` deve corrispondere
- Solo i campi inviati vengono aggiornati (delta update); le stringhe vuote dei campi nullable valgono `NULL`
- Il `PATCH` non risolve una via nuova in un dettaglio: per cambiare l'indirizzo fisico con la via e il civico si usa
  la sostituzione (§3-bis)

---

## 3-bis. Sostituisci indirizzo ruolo

| | |
|---|---|
| **Metodo** | `PUT` |
| **URL** | `/api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/indirizzi/{indirizzo_id}/` |

La «modifica» del form: cancella l'indirizzo e scrive il nuovo con la madre
(`anagrafiche.fn_crea_indirizzo_ruolo`), in **una** transazione. Gemello del `PUT` dell'indirizzo del soggetto
([api_soggetti.md](api_soggetti.md)).

### Body (JSON)

Lo stesso della creazione (§2), `istanza_utility_id` compreso.

### Risposta (200)

La riga scritta, come la creazione (§2).

### Errori

Quelli della creazione (§2), più:

| Codice | HTTP | Causa |
|---|---|---|
| `E_ANAG_NOT_FOUND` | 404 | Indirizzo inesistente o di un altro ruolo |
| `E_INDIRIZZO_OBBLIGATORIO_MANCANTE` | 400 | Lo stato finale manca di un obbligatorio del ruolo (per esempio il tipo nuovo è un altro) |

### Regole

- Il guard degli obbligatori è differito: giudica lo stato finale al commit, quindi sostituire l'unico indirizzo
  obbligatorio con uno dello stesso tipo passa
- ⛔ Non si compone con `DELETE` + `POST` in due richieste: la `DELETE` dell'unico obbligatorio, giudicata da sola,
  è rifiutata

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
- L'unico indirizzo di un tipo obbligatorio per il ruolo, senza il ripiego → 400 `E_INDIRIZZO_OBBLIGATORIO_MANCANTE`,
  al commit. Per cambiarlo si usa la sostituzione (§3-bis)
- Ownership check: `soggetto_ruolo_id` deve corrispondere
- Solo indirizzi livello ruolo sono eliminabili (fonte `istanza` o `ruolo`)
- Indirizzi soggetto (fonte `soggetto`) non sono raggiungibili da questo endpoint

---

## 5. Copia indirizzo ruolo («Copia come…»)

Copia un indirizzo del ruolo in uno o più tipi, sulla **chiave di destinazione** indicata nel
corpo: il ruolo, o una sua istanza. La sorgente può stare in qualunque chiave del ruolo (il ruolo
o un'altra istanza). Tutto o niente. Il frontend manda la chiave su cui l'operatore sta lavorando.

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/indirizzi/{indirizzo_id}/copia/` |
| **Verbo DB** | `anagrafiche.fn_copia_indirizzo_ruolo` |

### Body (JSON)

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `tipi_indirizzo_codice_interno` | string[] | Sì | I tipi di destinazione, per codice interno. Lista non vuota |
| `istanza_utility_id` | int \| null | No | L'istanza su cui nasce la copia. Assente o `null` = il ruolo. Nessun'altra chiave ammessa |

### Risposta (200)

```json
{ "data": { "ids": [87, 88] } }
```

Gli id delle righe nuove, nell'ordine dei tipi.

### Errori

| Codice | HTTP | Quando |
|---|---|---|
| `E_ANAG_VALIDAZIONE` | 400 | Corpo sbagliato: lista assente, vuota o con voci non testuali, `istanza_utility_id` non intero positivo, o chiavi in più (`error.fields` = il campo) |
| `E_SOGGETTO_RUOLO_NON_TROVATO` | 404 | Ruolo inesistente |
| `E_INDIRIZZO_RUOLO_NON_TROVATO` | 404 | L'indirizzo non esiste o non è di quel ruolo, in nessuna sua chiave |
| `E_ISTANZA_ALTRO_SOGGETTO` | 400 | L'istanza di destinazione non è del soggetto del ruolo (guard della tabella) |
| `E_DATABASE` | 400 | L'istanza di destinazione non esiste (chiave esterna `fk_indirizzi_istanze_utilities`), come per la creazione (§2) |
| `E_TIPO_INDIRIZZO_NON_TROVATO` | 400 | Un codice che il catalogo `config.tipi_indirizzi` non ha |
| `E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE` | 400 | Un indirizzo di quel tipo c'è già sulla chiave di destinazione, anche se il tipo è ripetuto nell'elenco |
| `E_TIPO_INDIRIZZO_NON_PERMESSO` | 400 | Il tipo di ruolo non ammette quel tipo (`config.tipi_ruolo_tipi_indirizzo`) |

### Regole

- Ogni riga la scrive la singolare `anagrafiche.fn_crea_indirizzo_ruolo`, con l'istanza di
  destinazione: valgono i suoi guard, come per la creazione (§2).
- Il backend controlla solo la **forma** del corpo; tipo inesistente, ripetuto, già presente o
  non ammesso lo dice il verbo, giudicandolo sulla chiave di destinazione.
- La lista (§1) non porta un motivo di riga per la copia: se la chiave di destinazione non ammette
  nessun tipo, lo dice il picker `ruoli/{id}/indirizzi/tipi/` (nessuna riga con `ammesso`), ed è
  lo stesso per ogni riga. Il verbo non solleva `E_INDIRIZZO_COPIA_NESSUN_TIPO`.
- La copia di un indirizzo del **soggetto** sul ruolo è del §5-bis. La copia dal ruolo al soggetto
  non esiste.

---

## 5-bis. Copia sul ruolo un indirizzo del soggetto

Copia un indirizzo del **soggetto del ruolo** in uno o più tipi, sulla chiave di destinazione del
ruolo. È il gesto «Copia come…» sulle righe del livello soggetto della cascata (§1), in contesto
ruolo. Corpo, risposta e regole sono quelli del §5.

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/indirizzi-soggetto/{indirizzo_soggetto_id}/copia/` |
| **Verbo DB** | `anagrafiche.fn_copia_indirizzo_soggetto_su_ruolo` |

### Errori

Quelli del §5, con la sorgente giudicata sul soggetto:

| Codice | HTTP | Quando |
|---|---|---|
| `E_INDIRIZZO_SOGGETTO_NON_TROVATO` | 404 | L'indirizzo non esiste o non è del soggetto del ruolo |

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
