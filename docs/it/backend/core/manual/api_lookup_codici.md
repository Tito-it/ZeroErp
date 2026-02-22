# API Lookup Codici Generica

## Scopo

Espone una ricerca generica su tabelle di configurazione con struttura `id / codice / descrizione`.
Permette autocompletamento e ricerca ILIKE da UI senza dover creare endpoint dedicati per ogni
tabella config.

## Contesto

Utilizza la funzione DB `dbops.fn_get_lookup_codici` come sorgente dati generica, wrappandola
con un filtro ILIKE e paginazione esterna. La funzione DB resta generica; il filtro testo e la
paginazione finale vivono nel layer Python/SQL del repository.

La relazione interrogabile è controllata da una whitelist Python (`_REL_CONSENTITE` in
`apps/core/db/dbops_repository.py`). Per aggiungere una nuova tabella config basta inserirla
nella whitelist, senza modificare il DB.

## Endpoint

```http
GET /api/v1/core/lookup/codici/
```

Richiede autenticazione JWT.

## Input

Query string:

| Parametro    | Tipo    | Obbligatorio | Default       | Note                                              |
|--------------|---------|:------------:|---------------|---------------------------------------------------|
| `rel`        | string  | Sì           | —             | Relazione config (es. `config.stati_sdi`)         |
| `search`     | string  | No           | —             | Testo ILIKE su `codice` o `descrizione`           |
| `order_col`  | string  | No           | `descrizione` | Valori ammessi: `codice`, `descrizione`           |
| `order_dir`  | string  | No           | `asc`         | Valori ammessi: `asc`, `desc`                     |
| `attivo_only`| bool    | No           | `true`        | Se `false`, include anche record non attivi       |
| `page`       | int     | No           | `1`           | Pagina (>= 1)                                     |
| `page_size`  | int     | No           | `50`          | Righe per pagina (1–200)                          |

## Output

```json
{
  "data": {
    "count": 3,
    "page": 1,
    "page_size": 50,
    "total_pages": 1,
    "results": [
      {"id": 1, "codice": "SDI_OK",  "descrizione": "Consegnato"},
      {"id": 2, "codice": "SDI_ERR", "descrizione": "Errore consegna"},
      {"id": 3, "codice": "SDI_ATT", "descrizione": "In attesa"}
    ]
  },
  "meta": {"request_id": "..."}
}
```

## Regole

- `rel` deve essere nella whitelist `_REL_CONSENTITE` (errore `E_CORE_VALIDATION` se assente).
- `search` vuoto o assente equivale a nessun filtro testo.
- `attivo_only=true` applica `WHERE attivo IS TRUE` tramite la funzione DB (solo se la tabella
  ha colonna `attivo boolean`).
- Ordinamento limitato a `codice` / `descrizione` per sicurezza (la funzione DB valida internamente).
- Paginazione gestita esternamente via SQL wrapper; il limit interno alla funzione DB è 10000
  (limite pratico sufficiente per tutte le tabelle config).

## Relazioni consentite (whitelist attuale)

Include tutte le tabelle `config.*` con struttura `id / codice / descrizione`.
La funzione DB `fn_get_lookup_codici` valida ulteriormente la struttura reale delle colonne
e solleva errore se mancante.

```text
config.ambiti                       config.stati
config.aspetti_beni                 config.stati_assets
config.assets_ownership             config.stati_cliente
config.categoria_accisa             config.stati_doc_contratti
config.causali_trasporto            config.stati_doc_ddt
config.classi_utenze                config.stati_doc_fiscale
config.conti_contabili              config.stati_doc_ordini
config.forme_giuridiche             config.stati_doc_preventivi
config.iva                          config.stati_pdp
config.iva_assoggettamenti          config.stati_pratiche
config.iva_natura                   config.stati_sdi
config.lingue                       config.termini_pagamento
config.modalita_addebito_trasporto  config.tipi_attivita
config.modalita_pagamento           config.tipi_contatti
config.note_stili                   config.tipi_doc_fiscale
config.qualifiche                   config.tipi_documenti
config.sistema_codici               config.tipi_evento_assets
config.sorgenti                     config.tipi_indirizzi
                                    config.tipi_ruoli
                                    config.tipi_soggetto_dettaglio
                                    config.tipi_ubicazione
                                    config.tipi_utenze
                                    config.unita_organizzative
                                    config.utilities
                                    config.valute
```

Per aggiungere una nuova relazione: inserire la stringa `schema.tabella` in `_REL_CONSENTITE`
in `backend/apps/core/db/dbops_repository.py`.

## Dipendenze DB

- `dbops.fn_get_lookup_codici(p_rel, p_order_col, p_order_dir, p_attivo_only, p_limit, p_offset)`
  — funzione generica lookup con validazione interna colonne e tipo id.

## Codici errore

| Codice              | HTTP | Causa                                          |
|---------------------|------|------------------------------------------------|
| `E_CORE_VALIDATION` | 400  | `rel` fuori whitelist, parametri non validi    |
| `E_GENERICO`        | 500  | Errore imprevisto (anche da funzione DB)       |
