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
| `rel`        | string  | Si           | —             | Relazione config (es. `config.stati_sdi`)         |
| `search`     | string  | No           | —             | Testo ILIKE su `codice` o `descrizione`           |
| `order_col`  | string  | No           | `descrizione` | Valori ammessi: `codice`, `descrizione`           |
| `order_dir`  | string  | No           | `asc`         | Valori ammessi: `asc`, `desc`                     |
| `attivo_only`| bool    | No           | `true`        | Se `false`, include anche record non attivi       |
| `page`       | int     | No           | `1`           | Pagina (>= 1)                                     |
| `page_size`  | int     | No           | `50`          | Righe per pagina (1-200)                          |

### Validazione Python dei parametri

Prima di invocare il repository DB, il service layer (`apps/core/services/lookup_service.py`)
valida i seguenti parametri con `ErrorManager.require`:

- **`rel`**: deve essere presente nella whitelist `_REL_CONSENTITE` (frozenset nel repository).
- **`order_col`**: deve appartenere al set `{"codice", "descrizione"}`.
- **`order_dir`**: deve appartenere al set `{"asc", "desc"}`.
- **`page`**: deve essere >= 1.
- **`page_size`**: deve essere compreso tra 1 e 200.

Qualsiasi valore fuori range genera errore `E_CORE_VALIDATION` (HTTP 400) prima che la query
raggiunga il database.

## Output

```json
{
  "data": {
    "count": 3,
    "page": 1,
    "page_size": 50,
    "total_pages": 1,
    "results": [
      {"id": 1, "codice": "SDI_OK",  "codice_interno": "001", "descrizione": "Consegnato"},
      {"id": 2, "codice": "SDI_ERR", "codice_interno": "002", "descrizione": "Errore consegna"},
      {"id": 3, "codice": "SDI_ATT", "codice_interno": "003", "descrizione": "In attesa"}
    ]
  },
  "meta": {"request_id": "..."}
}
```

### Campi risultato

| Campo            | Tipo    | Note                                                         |
|------------------|---------|--------------------------------------------------------------|
| `id`             | int     | ID del record                                                |
| `codice`         | string  | Codice alfanumerico della voce                               |
| `codice_interno` | string  | Codice interno (puo` essere null se la tabella non lo ha)    |
| `descrizione`    | string  | Descrizione leggibile                                        |
| `attivo`         | bool    | Stato attivo/inattivo del record                             |

## Regole

- `rel` deve essere nella whitelist `_REL_CONSENTITE` (errore `E_CORE_VALIDATION` se assente).
- `search` vuoto o assente equivale a nessun filtro testo.
- `attivo_only=true` applica `WHERE attivo IS TRUE` tramite la funzione DB (solo se la tabella
  ha colonna `attivo boolean`).
- Ordinamento limitato a `codice` / `descrizione` per sicurezza (la funzione DB valida internamente).
- `order_col` e `order_dir` sono validati a livello Python **prima** della chiamata DB;
  non vengono passati come parametri SQL (`%s`) ma inseriti nel testo della query solo dopo
  la validazione contro whitelist.
- Paginazione gestita esternamente via SQL wrapper; il limit interno alla funzione DB è 10000
  (limite pratico sufficiente per tutte le tabelle config).

## Relazioni consentite (whitelist attuale)

Include tutte le tabelle con struttura `id / codice / descrizione` distribuite su 6 schemi.
La funzione DB `fn_get_lookup_codici` valida ulteriormente la struttura reale delle colonne
e solleva errore se mancante.

Totale: **68 tabelle**.

### config (50)

```text
config.ambiti                       config.stati
config.aree_funzionali              config.stati_assets
config.aspetti_beni                 config.stati_cliente
config.assets_ownership             config.stati_doc_contratti
config.canali_pratiche              config.stati_doc_ddt
config.categoria_accisa             config.stati_doc_fiscale
config.causali_trasporto            config.stati_doc_ordini
config.classi_utenze                config.stati_doc_preventivi
config.conti_contabili              config.stati_flussi_pratiche
config.forme_giuridiche             config.stati_pdp
config.iva                          config.stati_pratiche
config.iva_assoggettamenti          config.stati_sdi
config.iva_natura                   config.termini_pagamento
config.lingue                       config.tipi_allegato
config.modalita_addebito_trasporto  config.tipi_attivita
config.modalita_pagamento           config.tipi_contatti
config.note_stili                   config.tipi_doc_fiscale
config.priorita_pratiche            config.tipi_documenti
config.qualifiche                   config.tipi_evento_assets
config.sistema_codici               config.tipi_indirizzi
config.sorgenti                     config.tipi_nota
                                    config.tipi_ruoli
                                    config.tipi_soggetto_dettaglio
                                    config.tipi_ubicazione
                                    config.tipi_utenze
                                    config.titoli_cortesia
                                    config.unita_organizzative
                                    config.utilities
                                    config.valute
```

### catalogo (1)

```text
catalogo.unita_misura
```

### magazzino (4)

```text
magazzino.ambito_causale            magazzino.magazzini
magazzino.causali                   magazzino.ubicazioni
```

### pagamenti (4)

```text
pagamenti.centri_riscossione        pagamenti.vendite_contabili_righe_stati
pagamenti.enti_incasso              pagamenti.vendite_contabili_stati
```

### pratiche (3)

```text
pratiche.handler_flussi             pratiche.tipi_prestazione
pratiche.template_flussi
```

### vendite (6)

```text
vendite.area_geografica_fatturazione  vendite.articoli_tipologie
vendite.articoli_gruppi               vendite.stati_commessa
vendite.articoli_spesa                vendite.tipi_fondi_fattura
```

Per aggiungere una nuova relazione: inserire la stringa `schema.tabella` in `_REL_CONSENTITE`
in `backend/apps/core/db/dbops_repository.py`.

## Dipendenze DB

- `dbops.fn_get_lookup_codici(p_rel, p_order_col, p_order_dir, p_attivo_only, p_limit, p_offset)`
  -- funzione generica lookup con validazione interna colonne e tipo id.

## Codici errore

| Codice              | HTTP | Causa                                          |
|---------------------|------|------------------------------------------------|
| `E_CORE_VALIDATION` | 400  | `rel` fuori whitelist, parametri non validi    |
| `E_GENERICO`        | 500  | Errore imprevisto (anche da funzione DB)       |
