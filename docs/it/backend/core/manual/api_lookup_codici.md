# API Lookup Codici Generica

## Scopo

Espone una ricerca generica su tabelle di configurazione con struttura `id / codice / descrizione`.
Permette autocompletamento e ricerca ILIKE da UI senza dover creare endpoint dedicati per ogni
tabella config.

## Contesto

Utilizza la funzione DB `dbops.fn_get_lookup_codici` come sorgente dati generica, wrappandola
con un filtro ILIKE e paginazione esterna. La funzione DB resta generica; il filtro testo e la
paginazione finale vivono nel layer Python/SQL del repository.

La relazione interrogabile è una riga di [`config.tabelle_gestibili`](/dbzero/config/tabelle/tabelle_gestibili)
con `lookup = true` (dal 2026-09-25; prima era la costante Python `REL_CONSENTITE`). La stessa
tabella dice quali relazioni si modificano dal pannello di configurazione (`pannello`): una
sede sola per le tendine, il pannello e il suo verbo di scrittura.

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
| `limit`      | int     | No           | `25`          | Righe per pagina, max 200                         |
| `offset`     | int     | No           | `0`           | Righe da saltare                                  |

⛔ `page`/`page_size` in query sono un 400 `E_VALIDATION_INPUT` dal 2026-10-21
(prima erano il contratto di questa lookup). La risposta porta ancora `page` e
`page_size`, ricavati dall'offset (`envelope_da_offset`).

### Validazione Python dei parametri

Prima di invocare il repository DB, il service layer (`apps/core/services/lookup_service.py`)
valida i seguenti parametri con `ErrorManager.require`:

- **`order_col`**: deve appartenere al set `{"codice", "descrizione"}`.
- **`order_dir`**: deve appartenere al set `{"asc", "desc"}`.

La lista di **`rel`** (`config.tabelle_gestibili`, colonna `lookup`) la controlla invece il
repository (`DbopsRepository.list_lookup_codici`), prima di qualunque query sulla tabella.

Un ordinamento fuori whitelist genera errore `E_CORE_VALIDATION` (HTTP 400) prima che la
query raggiunga il database. La finestra la legge la view con `pagina_da_query`: un `limit` o
`offset` **non intero** e' un `E_VALIDATION_INPUT` (HTTP 400), e dal 2026-10-21 anche un
valore fuori limiti (`limit` fuori da 1..200: `limit_fuori_limiti_1_200`; `offset` negativo:
`offset_negativo`), che prima si riportava nei limiti in silenzio.

## Output

```json
{
  "data": {
    "count": 3,
    "page": 1,
    "page_size": 25,
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

Una pagina oltre l'ultima risponde `results: []` col **`count` vero**: la pagina
passa dal BB `fetch_paged_with_total`, e quando è vuota il totale lo ricalcola il
conteggio di ripiego sullo stesso frammento FROM+WHERE. Vale per il ramo generico e
per gli specializzati. Fino al 2026-09-28 rispondeva `count: 0` e `total_pages: 0`
(F-8 dell'[analisi difetti](../../../dev/work-done/analisi-be-difetti-emersi-verifica-doc-api-core.md)).

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
| `config.esposizioni_componente` | `etichetta_key`           | I tre modi di esporre in fattura un componente di kit (NASCOSTO / DESCRITTIVO / VALORIZZATO): la tendina della distinta e il modo per esteso nei componenti di riga, resi dal composable FE `useEsposizioniComponente` (2026-10-02). Chiave del valore: `codice_interno`. ⚠️ **Senza `attivo` né `obsoleto_dal`**: i tre valori sono la semantica di `vw_fattura_righe_esposte`, non una configurazione |

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

- `rel` deve essere una riga di `config.tabelle_gestibili` con `lookup = true` (errore `E_CORE_VALIDATION` se assente).
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

## Relazioni consentite

⛔ L'elenco **non si ricopia qui**: e' la tabella `config.tabelle_gestibili`
(colonna `lookup`), e una copia in questa pagina sarebbe la prima ad
invecchiare. Si legge sul DB o nel suo seed
(`db/changelog/migrations_v2/80_data/sql/config/tabelle_gestibili.csv`).

Per aggiungere una relazione: una riga nel CSV del seed, con l'**oggetto** a cui
la tabella appartiene (`app_label`, `model_name`: la convenzione e'
`(schema, nome tabella)`) e i due flag `lookup` / `pannello`. ⚠️ E' lavoro del
**team DB** (l'app ha solo `SELECT` sulla lista: e' una porta, perche' il verbo
del pannello scrive come proprietario su ogni tabella che vi compare). Una
tabella con RLS puo' stare nel lookup ma non nel pannello.

⚠️ L'ordine è quello del contratto generico (`order_col` = `codice` | `descrizione`),
**non** la colonna `ordine` del vocabolario: vale per tutte le decodifiche, e se un
giorno l'ordine di presentazione conterà è un'estensione di questo lookup, non un
endpoint dedicato.

## Dipendenze DB

- `dbops.fn_get_lookup_codici(p_rel, p_order_col, p_order_dir, p_attivo_only, p_limit, p_offset, p_includi_obsoleti)`
  -- funzione generica lookup con validazione interna colonne e tipo id. Il 7° parametro
  `p_includi_obsoleti boolean DEFAULT true` filtra `obsoleto_dal` per introspezione (opzionale).

## Codici errore

| Codice              | HTTP | Causa                                          |
|---------------------|------|------------------------------------------------|
| `E_CORE_VALIDATION` | 400  | `rel` fuori lista, parametri non validi        |
| `E_VALIDATION_INPUT` | 400 | `limit` / `offset` non interi o fuori limiti, `page` / `page_size` presenti, flag non booleani |
| `E_LOOKUP_STRUTTURA_TABELLA_INVALIDA` | 500 | `fn_get_lookup_codici` rifiuta la struttura della tabella (colonne mancanti) |
| codice del DB / `E_DATABASE` | secondo il catalogo | altri rifiuti della funzione DB: passa il codice applicativo se il DB lo dichiara, altrimenti `E_DATABASE` (400) o `E_DATABASE_RETRYABLE` (409) |
| `E_GENERICO`        | 500  | Errore imprevisto non di database              |
