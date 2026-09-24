# API Lookup Codici Generica

## Scopo

Espone una ricerca generica su tabelle di configurazione con struttura `id / codice / descrizione`.
Permette autocompletamento e ricerca ILIKE da UI senza dover creare endpoint dedicati per ogni
tabella config.

## Contesto

Utilizza la funzione DB `dbops.fn_get_lookup_codici` come sorgente dati generica, wrappandola
con un filtro ILIKE e paginazione esterna. La funzione DB resta generica; il filtro testo e la
paginazione finale vivono nel layer Python/SQL del repository.

La relazione interrogabile è controllata da una whitelist Python (`REL_CONSENTITE` in
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
| `search`     | string  | No           | —             | ILIKE su `codice`/`codice_interno`/`descrizione`  |
| `order_col`  | string  | No           | `descrizione` | Valori ammessi: `codice`, `descrizione`           |
| `order_dir`  | string  | No           | `asc`         | Valori ammessi: `asc`, `desc`                     |
| `attivo_only`| bool    | No           | `true`        | Se `false`, include anche record non attivi       |
| `includi_obsoleti`| bool | No        | `true`        | Se `false`, esclude le voci obsolete (`obsoleto_dal <= oggi`) |
| `page`       | int     | No           | `1`           | Pagina (>= 1)                                     |
| `page_size`  | int     | No           | `50`          | Righe per pagina (1-200)                          |

### Validazione Python dei parametri

Prima di invocare il repository DB, il service layer (`apps/core/services/lookup_service.py`)
valida i seguenti parametri con `ErrorManager.require`:

- **`order_col`**: deve appartenere al set `{"codice", "descrizione"}`.
- **`order_dir`**: deve appartenere al set `{"asc", "desc"}`.
- **`page`**: deve essere >= 1.
- **`page_size`**: deve essere compreso tra 1 e 200.

La whitelist di **`rel`** (`REL_CONSENTITE`) la controlla invece il repository
(`DbopsRepository.list_lookup_codici`), prima di qualunque query.

Qualsiasi valore fuori range genera errore `E_CORE_VALIDATION` (HTTP 400) prima che la query
raggiunga il database. Un `page` o `page_size` **non numerico** e' rifiutato gia' dalla view,
con `E_VALIDATION_INPUT` (HTTP 400).

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
| `codice_stabile` | string  | `COALESCE(codice_interno, codice)` — chiave stabile FE       |

Per le relazioni **specializzate** (vedi sotto) il payload include **una colonna
in piu`** oltre al contratto generico.

⚠️ Difetto noto (F-8): una pagina oltre l'ultima risponde `results: []` con
`count: 0` e `total_pages: 0` — il totale si legge dalle righe della pagina, e
una pagina vuota non ne ha. Vedi [analisi difetti](../../../dev/work-in-progress/analisi-be-difetti-emersi-verifica-doc-api-core.md).

## Lookup specializzati (colonna extra)

Alcune relazioni estendono il contratto generico con una colonna aggiuntiva che
il frontend usa per filtri/raggruppamenti, senza endpoint dedicati. Sono
gestite da un handler parametrico unico (`_list_lookup_specializzato`,
config `_LOOKUP_SPECIALIZZATE` in `dbops_repository.py` — regola del 2,
2026-07-02): stesso contratto, stessi filtri `attivo_only`/`includi_obsoleti`
(quest'ultimo solo se la tabella ha `obsoleto_dal`), stessa ricerca ILIKE.

| `rel`                          | Colonna extra             | Uso FE                                       |
|--------------------------------|---------------------------|----------------------------------------------|
| `catalogo.unita_misura`        | `tipo_uom_id`             | Filtro conversioni same-type (`filterField`) |
| `config.esiti_flussi_pratiche` | `selezionabile_operatore` | Filtro Select esiti FlussoDrawer             |
| `config.tipi_titolo_iva`       | `ha_plafond`              | Mostra il campo plafond solo dove un tetto esiste (D10 titoli IVA) |
| `pratiche.tipi_prestazione`    | `categoria`               | Raggruppamento tile della home pratiche      |
| `config.registri_giornale`     | `etichetta_key`           | Tendina e colonna «Registro» del giornale trasversale: l'indirizzo i18n **dichiarato dal DB**, reso con `labelOrCode` (2026-09-19). ⚠️ **Senza `attivo`** (`has_attivo: False`): `attivo` arriva `NULL` e `attivo_only` non filtra — un consumatore che filtrasse `attivo === true` non vedrebbe niente |

Il nome API della colonna extra può differire dalla colonna fisica
(`extra_expr`): es. `selezionabile_operatore` è derivato da `is_verdetto`
(true = verdetto dell'operatore, false = esito di ramo calcolato dal dominio)
— il contratto parla la lingua del consumer, la verità memorizzata resta una.

Per aggiungere una relazione specializzata: una riga di config in
`_LOOKUP_SPECIALIZZATE` (`extra_col`, opz. `extra_expr`, `has_codice_interno`,
`has_obsoleto`, opz. `has_attivo` — default `True`) — niente nuovo SQL.

⚠️ **`has_attivo` esiste dal 2026-09-19, e prima il contratto mentiva**:
l'handler scriveva `t.attivo` fisso, quindi una tabella senza quella colonna
— `config.registri_giornale`, un vocabolario che nessuno «assegna» e che si
ritira con `obsoleto_dal`, come `tipi_entita` ed `eventi_dominio` — sarebbe
stata un **500** alla prima chiamata con la rel dichiarata in whitelist. A
`False` il payload porta `attivo = NULL`, la stessa cosa che
`dbops.fn_get_lookup_codici` fa sul percorso generico. ⭐ E **nessun test
attraversava le specializzate sul database**: `core/tests/db/test_lookup_specializzate.py`
ora le prova **tutte** sul DB provvisto (il contratto dichiarato si prova per
intero), oltre alla composizione con e senza il flag.

## Lookup a matrice — endpoint dedicati

Tre lookup **non** passano da `rel`, e non e' un'eccezione arbitraria: non
servono una tabella codice/descrizione, servono una **matrice** (quali
indirizzi per quale tipo, quali utility per quale ruolo). Il contratto generico
non saprebbe esprimere il vincolo, quindi hanno un path proprio.

| endpoint | risponde |
|---|---|
| `GET /api/v1/core/lookup/tipi-soggetto-dettaglio/{tipo_soggetto_dettaglio_id}/indirizzi/` | tipi indirizzo **ammessi e obbligatori** per quel tipo soggetto dettaglio |
| `GET /api/v1/core/lookup/tipi-ruolo/{tipo_ruolo_codice}/indirizzi/` | idem, ma per **tipo ruolo** (chiave = `codice_interno`, non id) |
| `GET /api/v1/core/lookup/tipi-ruolo/{tipo_ruolo_codice}/utilities/` | utility ammesse per quel ruolo, filtro strict su `config.utilities_tipi_ruolo` |

Risposta: envelope standard con `results`. Nessun parametro di query: la
matrice si chiede per intero, e il FE la usa per costruire i form indirizzo
giusti **prima** che l'operatore sbagli.

⚠️ **Le due matrici indirizzi sono governate da tabelle diverse e non vanno
confuse**: quella per tipo soggetto e'
`config.tipi_soggetto_dettaglio_tipi_indirizzo`, quella per ruolo e'
`config.tipi_ruolo_tipi_indirizzo`. Hanno guard distinti a DB e, dal
2026-08-19, **codici errore distinti** — prima ne condividevano uno e il
messaggio mandava a cercare nella tabella sbagliata.

⭐ Tutti e tre dichiarano `skip_area_check = True`: sono lookup cross-dominio,
letti da form di aree diverse. Lo scope resta quello del repository — vedi
`api_routing_core.md`.

## Regole

- `rel` deve essere nella whitelist `REL_CONSENTITE` (errore `E_CORE_VALIDATION` se assente).
- `search` vuoto o assente equivale a nessun filtro testo.
- `attivo_only=true` applica `WHERE attivo IS TRUE` tramite la funzione DB (solo se la tabella
  ha colonna `attivo boolean`).
- `includi_obsoleti=false` esclude le voci con `obsoleto_dal <= CURRENT_DATE` (solo se la
  tabella ha la colonna `obsoleto_dal date`; introspezione opzionale come `attivo`). Il default
  è `true` (mostra tutto) per non cambiare i contesti storico/filtro: è la **selezione per il
  nuovo** (es. tipo nuova pratica) a passare `false`. Pattern riusabile cross-catalogo.
- Ordinamento limitato a `codice` / `descrizione` per sicurezza (la funzione DB valida internamente).
- `order_col` e `order_dir` sono validati a livello Python **prima** della chiamata DB;
  non vengono passati come parametri SQL (`%s`) ma inseriti nel testo della query solo dopo
  la validazione contro whitelist.
- Paginazione gestita esternamente via SQL wrapper; il limit interno alla funzione DB è 10000
  (limite pratico sufficiente per tutte le tabelle config).

## Relazioni consentite (whitelist attuale)

Include tutte le tabelle con struttura `id / codice / descrizione` distribuite su 9 schemi.
La funzione DB `fn_get_lookup_codici` valida ulteriormente la struttura reale delle colonne
e solleva errore se mancante.

Totale: **87 tabelle** (elenco generato dal codice, 2026-09-14; 2026-09-21: **via `config.stati` e `config.titoli_cortesia`** — senza `codice`/`codice_interno`, `fn_get_lookup_codici` le rifiutava con `E_LOOKUP_STRUTTURA_TABELLA_INVALIDA`: erano dichiarate ammesse ed erano un 500, trovato dal presidio `apps/core/tests/db/test_config_panel_registro_db.py`; le nazioni hanno `GET /anagrafiche/stati/lookup/`).

⭐ L'ultima entrata è `config.modi_approvvigionamento` (Blocco B di
`brief-db-modifiche-certe-ciclo-vendita-e-articolo`): il modo di approvvigionamento
dell'articolo è **una riga qui e non un endpoint** — è un vocabolario
codice/descrizione come `config.nature_vendita`, il suo modello dichiarato, e il
drawer articolo lo monta con `<LookupSelect rel="config.modi_approvvigionamento">`.
⚠️ L'ordine è quello del contratto generico (`order_col` = `codice` | `descrizione`),
**non** la colonna `ordine` del vocabolario: vale per tutte le decodifiche, e se un
giorno l'ordine di presentazione conterà è un'estensione di questo lookup, non un
endpoint dedicato.

### anagrafiche (1)

```text
anagrafiche.categorie_clienti
```

### catalogo (2)

```text
catalogo.unita_misura  catalogo.uom_tipi
```

### config (61)

```text
config.ambiti                       config.stati_doc_contratti
config.aree_funzionali              config.stati_doc_ddt
config.aspetti_beni                 config.stati_doc_fiscale
config.assets_ownership             config.stati_doc_offerte
config.canali_pratiche              config.stati_doc_ordini
config.categoria_accisa             config.stati_doc_preventivi
config.causali_trasporto            config.stati_doc_reso
config.classi_utenze                config.stati_flussi_pratiche
config.conti_contabili              config.stati_fornitore
config.email_account                config.stati_pdp
config.esiti_flussi_pratiche        config.stati_pratiche
config.forme_giuridiche             config.stati_sdi
config.iva                          config.termini_pagamento
config.iva_assoggettamenti          config.tipi_allegato
config.iva_natura                   config.tipi_attivita
config.lingue                       config.tipi_contatti
config.listini_tipologie            config.tipi_doc_fiscale
config.modalita_addebito_trasporto  config.tipi_documenti
config.modalita_pagamento           config.tipi_evento_assets
config.modi_approvvigionamento      config.tipi_indirizzi
config.nature_doc_fiscale           config.tipi_nota
config.nature_vendita               config.tipi_reso
config.note_stili                   config.tipi_ruoli
config.priorita_pratiche            config.tipi_soggetto_dettaglio
config.profili_accesso              config.tipi_titolo_iva
config.qualifiche                   config.tipi_ubicazione
config.registri_giornale            config.tipi_utenze
config.sistema_codici               config.unita_organizzative
config.sorgenti                     config.utilities
config.stati_assets                 config.valute
config.stati_cliente
```

### documenti (4)

```text
documenti.render_engine_documento  documenti.tipi_documento_output
documenti.tipi_asset_documento     documenti.tipi_file_documento
```

### magazzino (3)

```text
magazzino.causali  magazzino.magazzini
magazzino.ubicazioni
```

### pagamenti (4)

```text
pagamenti.centri_riscossione  pagamenti.vendite_contabili_righe_stati
pagamenti.enti_incasso        pagamenti.vendite_contabili_stati
```

### pratiche (3)

```text
pratiche.handler_flussi   pratiche.tipi_prestazione
pratiche.template_flussi
```

### ui (1)

```text
ui.lista_definizione
```

### vendite (8)

```text
vendite.area_geografica_fatturazione  vendite.famiglie_documento
vendite.articoli_gruppi               vendite.listini
vendite.articoli_spesa                vendite.stati_commessa
vendite.articoli_tipologie            vendite.tipi_fondi_fattura
```

Per aggiungere una nuova relazione: inserire la stringa `schema.tabella` in `REL_CONSENTITE`
in `backend/apps/core/db/dbops_repository.py`.
## Dipendenze DB

- `dbops.fn_get_lookup_codici(p_rel, p_order_col, p_order_dir, p_attivo_only, p_limit, p_offset, p_includi_obsoleti)`
  -- funzione generica lookup con validazione interna colonne e tipo id. Il 7° parametro
  `p_includi_obsoleti boolean DEFAULT true` filtra `obsoleto_dal` per introspezione (opzionale).

## Codici errore

| Codice              | HTTP | Causa                                          |
|---------------------|------|------------------------------------------------|
| `E_CORE_VALIDATION` | 400  | `rel` fuori whitelist, parametri non validi    |
| `E_VALIDATION_INPUT` | 400 | `page` / `page_size` non numerici              |
| `E_LOOKUP_STRUTTURA_TABELLA_INVALIDA` | 500 | `fn_get_lookup_codici` rifiuta la struttura della tabella (colonne mancanti) |
| codice del DB / `E_DATABASE` | secondo il catalogo | altri rifiuti della funzione DB: passa il codice applicativo se il DB lo dichiara, altrimenti `E_DATABASE` (400) o `E_DATABASE_RETRYABLE` (409) |
| `E_GENERICO`        | 500  | Errore imprevisto non di database              |
