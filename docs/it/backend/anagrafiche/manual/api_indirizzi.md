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
| search      | string | no           | —                           | Testo libero per ricerca sull'indirizzo           |
| comune_id   | int    | no           | —                           | Filtra per comune                                 |
| limit       | int    | no           | 25                          | Numero massimo di risultati per pagina            |
| offset      | int    | no           | 0                           | Offset per la paginazione                         |
| order_by    | string | no           | indirizzo_normalizzato      | Campo di ordinamento                              |
| order_dir   | string | no           | ASC                         | Direzione ordinamento: `ASC` o `DESC`             |

### Risposta 200

```json
{
  "status": "ok",
  "data": {
    "results": [ ... ],
    "total": 150,
    "page": 1,
    "limit": 25
  }
}
```

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

Crea un nuovo indirizzo dettaglio. Supporta due modalita`:

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

```json
{
  "status": "ok",
  "data": {
    "id": 42,
    "indirizzo_normalizzato": "Via Roma 10/A, 00100 Roma (RM)"
  }
}
```

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
  "status": "ok",
  "data": {
    "id": 42,
    "indirizzo_normalizzato": "Via Roma 10/A, 00100 Roma (RM)",
    "civico": 10,
    "estensione_civico": "A",
    "palazzina": null,
    "scala": "B",
    "piano": "3",
    "interno": "12",
    "attivo": true
  }
}
```

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
| attivo             | boolean | Flag attivo/disattivo                |

### Risposta 200

```json
{
  "status": "ok",
  "data": {
    "id": 42,
    "indirizzo_normalizzato": "Via Roma 10/B, 00100 Roma (RM)",
    "attivo": true
  }
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

Verifica se esiste gia` un indirizzo identico nel database, invocando la funzione PostgreSQL `fn_check_indirizzo_duplicato`. Utilizzato dal frontend per mostrare un warning prima della creazione.

### Body (JSON)

| Campo        | Tipo | Obbligatorio | Descrizione                       |
|--------------|------|--------------|-----------------------------------|
| stradario_id | int  | no           | ID dello stradario da verificare  |
| civico       | int  | no           | Numero civico da verificare       |

### Risposta 200 (nessun duplicato)

```json
{
  "status": "ok",
  "data": {
    "warnings": []
  }
}
```

### Risposta 200 (duplicato trovato)

```json
{
  "status": "ok",
  "data": {
    "warnings": [
      {
        "exact_match": true,
        "indirizzo_dettaglio_id": 42,
        "message": "Indirizzo duplicato trovato"
      }
    ]
  }
}
```

### Regole

- Il campo `exact_match` indica se la corrispondenza e` esatta (`true`) o parziale (`false`).
- Il campo `indirizzo_dettaglio_id` contiene l'ID dell'indirizzo esistente, utilizzabile per navigazione o selezione diretta.
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
- `anagrafiche.stradario` -- collegamento via/comune/CAP
- `anagrafiche.toponomastica` -- tipo via (Via, Piazza, Corso, ecc.)
- `anagrafiche.codici_postali` -- CAP
- `anagrafiche.comuni` -- comuni
- `anagrafiche.fn_check_indirizzo_duplicato` -- funzione verifica duplicati
- `anagrafiche.fn_build_indirizzo_normalizzato` -- funzione normalizzazione indirizzo

## Note

- Tutti gli endpoint restituiscono un envelope standard `{"status": "ok", "data": {...}}`.
- In caso di errore, la risposta contiene `{"status": "error", "error": {"code": "...", "message": "..."}}`.
- La ricerca full-text opera sull'indirizzo normalizzato.
