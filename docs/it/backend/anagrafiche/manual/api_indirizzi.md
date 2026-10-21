# API Indirizzi Dettaglio

## Scopo

Gestione degli indirizzi dettaglio: ricerca paginata, creazione, consultazione, aggiornamento e verifica duplicati.

## Contesto

Gli indirizzi dettaglio rappresentano un indirizzo fisico completo (via, civico, scala, piano, interno) collegato allo stradario comunale. La logica di business risiede nel database PostgreSQL; il backend Django orchestra le chiamate e espone le API REST.

## Base URL

```
/api/v1/anagrafiche/indirizzi/
```

Tutte le richieste richiedono autenticazione JWT (header `Authorization: Bearer <token>`).

---

## 1. Lista indirizzi (paginata)

```
GET /api/v1/anagrafiche/indirizzi/
```

Restituisce la lista degli indirizzi dettaglio con paginazione e ricerca full-text.

### Query parameters

| Parametro   | Tipo   | Obbligatorio | Default                     | Descrizione                                      |
|-------------|--------|--------------|-----------------------------|--------------------------------------------------|
| search      | string | no           | —                           | Ricerca full guidata dal catalogo `anagrafiche.indirizzi` (campi `indirizzo_normalizzato`, `descrizione_comune`); sotto soglia non si applica, nessun 400 |
| comune_id   | int    | no           | —                           | Filtra per comune                                 |
| limit       | int    | no           | 25                          | Righe per pagina (1–200)                          |
| offset      | int    | no           | 0                           | Offset per la paginazione                         |
| order_by    | string | no           | indirizzo_normalizzato      | `indirizzo_normalizzato`, `civico`, `descrizione_comune`, `cap`, `provincia`, `attivo`, `data_insert`; fuori whitelist → **400** `E_VALIDATION_INPUT` (dal 2026-10-20) |
| order_dir   | string | no           | asc                         | `asc` o `desc`. Se omessa, `data_insert` parte `desc` |

### Risposta 200

```json
{
  "data": {
    "count": 150,
    "page": 1,
    "page_size": 25,
    "total_pages": 6,
    "results": [
      {
        "indirizzo_dettaglio_id": 42,
        "stradario_id": 5,
        "indirizzo_normalizzato": "VIA ROMA 10/A",
        "civico": 10,
        "estensione_civico": "A",
        "descrizione_comune": "Roma",
        "cap": "00100",
        "provincia": "RM",
        "attivo": true,
        "data_insert": "2026-01-15T10:30:00+01:00"
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

Sorgente: vista `anagrafiche.vw_indirizzi_dettaglio`.

### Esempio curl

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/indirizzi/?search=roma&comune_id=1&limit=10"
```

---

## 2. Crea indirizzo dettaglio

```
POST /api/v1/anagrafiche/indirizzi/
```

Crea (o ritrova: get_or_create) un indirizzo dettaglio con la funzione madre
atomica `anagrafiche.fn_create_indirizzo`, che per una via nuova fa anche l'upsert
dello stradario. Supporta due modalita`:

- **Da stradario**: fornire `stradario_id` (lo stradario contiene gia` toponomastica, via, comune e CAP).
- **Manuale**: fornire `toponomastica_id`, `descrizione_via`, `comune_id` e `codice_postale_id`.

### Body (JSON)

| Campo              | Tipo   | Obbligatorio              | Descrizione                                  |
|--------------------|--------|---------------------------|----------------------------------------------|
| stradario_id       | int    | alternativo (vedi sopra)  | ID dello stradario di riferimento            |
| toponomastica_id   | int    | alternativo (vedi sopra)  | ID della toponomastica (Via, Piazza, ecc.)   |
| descrizione_via    | string | alternativo (vedi sopra)  | Denominazione della via                      |
| comune_id          | int    | alternativo (vedi sopra)  | ID del comune                                |
| codice_postale_id  | int    | alternativo (vedi sopra)  | ID del codice postale                        |
| civico             | int    | no                        | Numero civico                                |
| estensione_civico  | string | no                        | Estensione civico (es. "A", "bis")           |
| palazzina          | string | no                        | Identificativo palazzina                     |
| scala              | string | no                        | Scala                                        |
| piano              | string | no                        | Piano                                        |
| interno            | string | no                        | Interno                                      |

### Risposta 200

Restituisce il dettaglio dell'indirizzo creato, con gli stessi campi del §3.

### Errori

| Codice | HTTP | Causa |
| --- | --- | --- |
| `E_ANAG_VALIDAZIONE` | 400 | `stradario_id` non positivo; via nuova senza tipo strada, nome via, comune o CAP |

### Esempio curl

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "stradario_id": 5,
    "civico": 10,
    "estensione_civico": "A",
    "scala": "B",
    "piano": "3",
    "interno": "12"
  }' \
  "https://host/api/v1/anagrafiche/indirizzi/"
```

---

## 3. Dettaglio indirizzo

```
GET /api/v1/anagrafiche/indirizzi/{pk}/
```

Restituisce il dettaglio completo di un indirizzo.

### Path parameters

| Parametro | Tipo | Descrizione                  |
|-----------|------|------------------------------|
| pk        | int  | ID dell'indirizzo dettaglio  |

### Risposta 200

```json
{
  "data": {
    "indirizzo_dettaglio_id": 42,
    "stradario_id": 5,
    "indirizzo_normalizzato": "VIA ROMA 10/A",
    "civico": 10,
    "estensione_civico": "A",
    "descrizione_comune": "Roma",
    "cap": "00100",
    "provincia": "RM",
    "attivo": true,
    "palazzina": null,
    "scala": "B",
    "piano": "3",
    "interno": "12"
  },
  "meta": { "request_id": "..." }
}
```

Errori: 404 `E_ANAG_NOT_FOUND` se l'indirizzo non esiste.

### Esempio curl

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://host/api/v1/anagrafiche/indirizzi/42/"
```

---

## 4. Aggiorna indirizzo

```
PATCH /api/v1/anagrafiche/indirizzi/{pk}/
```

Aggiorna parzialmente un indirizzo dettaglio esistente. Inviare solo i campi da modificare.

### Path parameters

| Parametro | Tipo | Descrizione                  |
|-----------|------|------------------------------|
| pk        | int  | ID dell'indirizzo dettaglio  |

### Body (JSON)

| Campo              | Tipo    | Descrizione                          |
|--------------------|---------|--------------------------------------|
| civico             | int     | Numero civico                        |
| estensione_civico  | string  | Estensione civico                    |
| palazzina          | string  | Identificativo palazzina             |
| scala              | string  | Scala                                |
| piano              | string  | Piano                                |
| interno            | string  | Interno                              |
| attivo             | boolean | Flag attivo/disattivo (booleano JSON; altro tipo → 400 `E_VALIDATION_INPUT`) |

`stradario_id` non e' modificabile. Dal 2026-10-20 (brief-be-verifica-documentazione-api
§A2, §B2, §B3):

- una chiave presente si scrive, anche `null`, che **svuota** il campo; una chiave
  assente non si tocca (prima `null` voleva dire «non toccare», e svuotare la
  palazzina non scriveva niente);
- una chiave fuori elenco → 400 `E_ANAG_VALIDAZIONE` (prima era ignorata);
- un corpo senza campi → 400 `E_ANAG_VALIDAZIONE` (prima 404, come un id inesistente);
- `attivo` vuole un booleano JSON: `null` → 400 (prima spegneva l'indirizzo).

### Risposta 200

```json
{
  "data": { "updated": true },
  "meta": { "request_id": "..." }
}
```

### Esempio curl

```bash
curl -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"civico": 10, "estensione_civico": "B"}' \
  "https://host/api/v1/anagrafiche/indirizzi/42/"
```

---

## 5. Verifica duplicato indirizzo

```
POST /api/v1/anagrafiche/indirizzi/check-duplicato/
```

Verifica se esiste gia` un indirizzo identico o simile nel database, invocando la funzione PostgreSQL `script.fn_check_indirizzo_duplicato`. Utilizzato dal frontend per mostrare un warning prima della creazione.

Due flussi:

- **A**: `stradario_id` (stradario locale);
- **B**: `stradario_generale_id` + `comune_id` (+ `codice_postale_id` opzionale).

Senza `stradario_id` ne' la coppia `stradario_generale_id` + `comune_id` la
verifica non si fa: risposta con `warnings` vuoto.

### Body (JSON)

| Campo                 | Tipo   | Obbligatorio | Descrizione                         |
|-----------------------|--------|--------------|-------------------------------------|
| stradario_id          | int    | flusso A     | ID dello stradario locale           |
| stradario_generale_id | int    | flusso B     | ID dello stradario generale         |
| comune_id             | int    | flusso B     | ID del comune                       |
| codice_postale_id     | int    | no           | CAP (flusso B)                      |
| civico                | int    | no           | Numero civico                       |
| estensione_civico     | string | no           | Estensione civico                   |
| palazzina             | string | no           | Palazzina                           |
| scala                 | string | no           | Scala                               |
| piano                 | string | no           | Piano                               |
| interno               | string | no           | Interno                             |

### Risposta 200 (nessun duplicato)

```json
{
  "data": { "warnings": [] },
  "meta": { "request_id": "..." }
}
```

### Risposta 200 (duplicato trovato)

```json
{
  "data": {
    "warnings": [
      {
        "field": "indirizzo",
        "message": "Indirizzo gia' presente: VIA ROMA 10/A, Roma",
        "indirizzo_dettaglio_id": 42,
        "exact_match": true
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

### Regole

- Il campo `exact_match` indica se la corrispondenza e` esatta (`true`) o parziale (`false`).
- Il campo `indirizzo_dettaglio_id` contiene l'ID dell'indirizzo esistente solo se `exact_match = true` (altrimenti `null`); il messaggio e' «Indirizzo gia' presente: ...» o «Indirizzo simile trovato: ...».
- `field` vale sempre `indirizzo`.
- L'endpoint non blocca la creazione: il frontend decide se procedere o meno.

### Esempio curl

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"stradario_id": 5, "civico": 10}' \
  "https://host/api/v1/anagrafiche/indirizzi/check-duplicato/"
```

---

## Dipendenze DB

- `anagrafiche.indirizzi_dettaglio` -- tabella principale
- `anagrafiche.vw_indirizzi_dettaglio` -- vista di lista e dettaglio
- `anagrafiche.stradario` -- collegamento via/comune/CAP
- `config.toponomastica` -- tipo via (Via, Piazza, Corso, ecc.)
- `config.codici_postali` -- CAP
- `config.comuni` -- comuni
- `anagrafiche.fn_create_indirizzo` -- funzione madre di creazione
- `script.fn_check_indirizzo_duplicato` -- funzione verifica duplicati

## Note

- Tutti gli endpoint restituiscono l'envelope standard `{"data": {...}, "meta": {...}}`.
- In caso di errore: `{"error": {"code": "...", "message": "..."}, "meta": {...}}`.
- La chiave dell'indirizzo nelle risposte e' `indirizzo_dettaglio_id` (non `id`).
