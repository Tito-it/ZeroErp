# API Listini (Vendite)

## Scopo

Esporre via HTTP la gestione completa dei listini vendite: anagrafica listino,
versioni temporali e righe prezzo.

> ⚠️ **Rimossi da F2-BE-13** (verificato sul codice il 2026-08-19): le rotte
> `/associazioni/` e `/test-prezzo/`, e con loro i campi `associazioni_count` e
> `associazioni` nei payload. Nel modello v5 il listino si sceglie dalla matrice
> `categorie_clienti_listini` o dal contratto, non da una tabella di
> associazione dedicata. Le sezioni relative restano qui come **lapidi** (§5,
> §6): dicono cosa e' sparito e cosa usare al suo posto, perche' una pagina che
> descrive un endpoint inesistente e' indistinguibile da una che ne descrive uno
> vivo.

## Contesto

Tutti gli endpoint risiedono sotto `/api/v1/vendite/listini/` e sono implementati in:
- `apps/vendite/api/views_listini.py`
- `apps/vendite/services/listini_service.py`
- `apps/vendite/db/listini_repository.py`

Il backend segue il modello DB-first del progetto:
- PostgreSQL resta source of truth per vincoli, overlap temporali, unicita` e resolver prezzo;
- Django orchestra parsing HTTP, validazione applicativa minima, envelope risposta e traduzione errori.

Le API richiedono JWT (`Authorization: Bearer <token>`) e usano l'envelope standard:

```json
{
  "data": {},
  "meta": {
    "request_id": "..."
  }
}
```

## Base URL

```text
/api/v1/vendite/listini/
```

---

## 1. Lista e creazione listini

### 1.1 Lista listini

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/vendite/listini/` |

#### Query param

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `search` | string | No | Ricerca libera: le colonne le decide il catalogo della lista `vendite.listini` (`ricerca_full` nella configurazione). Sotto 3 caratteri il termine si **ignora** (nessun `400`) |
| `utility_id` | int | No | Filtro per utility (FK `config.utilities`) |
| `tipologia_id` | int | No | Filtro per tipologia listino (FK `config.listini_tipologie`) |
| `attivo` | bool | No | Filtro attivo/disattivo; parsing rigoroso |
| `in_scadenza` | bool | No | `true` = solo i listini con la versione in vigore **in scadenza senza successore**, `false` = gli altri; parsing rigoroso. La regola è del DB (§7). È il filtro del badge delle scadenze |
| `limit` | int | No | Righe per pagina, default `25`, max `200`; fuori da 1..200 → 400 `E_VALIDATION_INPUT` |
| `offset` | int | No | Scostamento, default `0` (negativo → 400); la `page` della risposta si ricava da qui |
| `order_by` | string | No | `codice` (default), `descrizione`, `utility_descrizione`, `tipologia_descrizione`, `attivo`, `data_insert`, `data_update`, `giorni_alla_scadenza` |
| `order_dir` | string | No | `asc` oppure `desc` |

`utility_id` e `tipologia_id`: stringa vuota equivale a parametro assente;
non numerici → `400 E_VALIDATION_INPUT`, ≤ 0 → `400 E_VENDITE_VALIDATION`.
Permesso modello `("vendite", "listino")` su tutte le rotte di questa pagina.
⚠️ La paginazione è `limit`/`offset`: `page`/`page_size` sono un 400 `E_VALIDATION_INPUT` (dal 2026-10-20; prima erano ignorati).

#### Risposta (200)

```json
{
  "data": {
    "count": 1,
    "page": 1,
    "page_size": 25,
    "total_pages": 1,
    "results": [
      {
        "id": 10,
        "codice": "LIST-GAS-2026",
        "descrizione": "Tariffe consumo gas 2026",
        "utility_id": 1,
        "utility_codice": "GAS",
        "utility_descrizione": "Gas",
        "tipologia_id": 1,
        "tipologia_codice": "CONSUMO",
        "tipologia_descrizione": "Consumi",
        "attivo": true,
        "versioni_count": 2,
        "giorni_alla_scadenza": null
      }
    ]
  }
}
```

### 1.2 Crea listino

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/vendite/listini/` |

#### Body JSON

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `codice` | string | Si | Codice univoco listino (immutabile dopo create) |
| `descrizione` | string | Si | Descrizione listino |
| `utility_id` | int | Si | FK `config.utilities` — intero positivo (per il commercio usare la utility `Base`, id=5 nel seed standard) |
| `tipologia_id` | int | Si | FK `config.listini_tipologie` — intero positivo; la coppia `(utility_id, tipologia_id)` deve esistere attiva in `config.listini_tipologie_utilities` (guard DB) |
| `emittente_soggetto_ruolo_id` | int | Si | L'emittente fiscale (soggetto-ruolo) a cui il listino appartiene — intero positivo |
| `meta` | object | No | Metadati liberi |
| `attivo` | bool | No | Default DB `true` |

#### Risposta (200)

Restituisce il dettaglio completo del listino creato, con l'array `versioni`.
Una chiave fuori dall'elenco del body → `400 E_VENDITE_VALIDATION`.

#### Errori tipici

- `400` `E_VENDITE_VALIDATION`:
  - `utility_id`, `tipologia_id` o `emittente_soggetto_ruolo_id` mancanti, nulli, non numerici, non positivi
  - chiave fuori elenco
  - Combinazione `(utility_id, tipologia_id)` non ammessa dalla matrice `config.listini_tipologie_utilities`
  - payload JSON non coerente
- `400` `E_VENDITE_FK`: `utility_id` / `tipologia_id` non esistenti (FK violation)
- `409` `E_VENDITE_DUPLICATO`: codice listino duplicato (`uq_listini_codice`)

---

## 2. Dettaglio e update listino

### 2.1 Dettaglio listino

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/` |

#### Risposta (200)

```json
{
  "data": {
    "id": 10,
    "codice": "LIST-GAS-2026",
    "descrizione": "Tariffe consumo gas 2026",
    "utility_id": 1,
    "utility_codice": "GAS",
    "utility_descrizione": "Gas",
    "tipologia_id": 1,
    "tipologia_codice": "CONSUMO",
    "tipologia_descrizione": "Consumi",
    "attivo": true,
    "versioni_count": 2,
    "versioni": []
  }
}
```

### 2.2 Aggiorna listino

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/` |

#### Body JSON

Campi ammessi (tutti opzionali; almeno uno deve essere presente):

| Campo | Tipo | Nullable | Descrizione |
| --- | --- | --- | --- |
| `descrizione` | string | No | Nuova descrizione |
| `utility_id` | int | No | Nuova utility (se inviato, NOT NULL; guard matrice DB) |
| `tipologia_id` | int | No | Nuova tipologia (se inviato, NOT NULL; guard matrice DB) |
| `emittente_soggetto_ruolo_id` | int | No | Nuovo emittente (se inviato, intero positivo, non `null`) |
| `meta` | object | Si | Metadati liberi |
| `attivo` | bool | No | Attivazione / disattivazione |

#### Regole specifiche

- `codice` è immutabile a livello API (trigger DB `trg_listini_a10_protect_codice_upd` lo conferma).
- `utility_id` e `tipologia_id` non possono essere inviati a `null`: se presenti nel payload devono essere interi positivi. Il cambio coppia è validato dal trigger DB `trg_listini_a10_guard_tipologia_utility_ins_upd` contro la matrice `config.listini_tipologie_utilities`.
- La `PATCH` legge il corpo con `corpo_oggetto` (corpo non oggetto → `400 E_VALIDATION_INPUT`); una chiave fuori elenco → `400 E_VENDITE_VALIDATION`.
- Se nessun campo supportato è presente nel payload, restituisce `400` `E_VENDITE_VALIDATION`.

#### Errori tipici

- `404` `E_VENDITE_LISTINO_NOT_FOUND`
- `400` `E_VENDITE_VALIDATION`:
  - `tipologia_id` inviato come `null`
  - Combinazione `(utility_id, tipologia_id)` non ammessa dalla matrice
  - Payload vuoto

### 1.5 Elimina listino mai usato

| | |
|---|---|
| **Metodo** | `DELETE` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/` |

Elimina un listino **solo se non ha versioni**: `versioni_count == 0`. Caso
d'uso tipico: listini di test creati per errore. Per disattivare un listino con
figli, usare `PATCH attivo=false`.

⚠️ Il secondo controllo storico — `associazioni_count == 0` — **non esiste piu'**
da F2-BE-13 (`listini_service.fn_delete_listino`).

Risposta (200):

```json
{ "data": { "deleted": true, "id": 10 } }
```

Errori tipici:

- `400` `E_VENDITE_VALIDATION` se il listino ha versioni
- `404` `E_VENDITE_LISTINO_NOT_FOUND`

---

## 2bis. Tipologie ammesse per utility

Endpoint di supporto per il frontend: dato un `utility_id`, restituisce le
tipologie di listino ammesse dalla matrice
`config.listini_tipologie_utilities` (solo righe attive). Usato dal
`ListinoDrawer` per popolare il Select tipologia al cambio utility.

### 2bis.1 Lista tipologie per utility

| | |
| --- | --- |
| **Metodo** | `GET` |
| **URL** | `/api/v1/vendite/listini/tipologie-per-utility/` |

#### Query param

| Parametro | Tipo | Obbligatorio | Descrizione |
| --- | --- | --- | --- |
| `utility_id` | int | Si | FK `config.utilities`, intero positivo |

Se `utility_id` manca o è stringa vuota, la risposta è `400`
`E_VENDITE_VALIDATION` con detail che riporta esplicitamente
"utility_id è obbligatorio".

#### Risposta (200)

Envelope standard con chiave `results` (pattern lookup dedicati):

```json
{
  "data": {
    "results": [
      {
        "id": 1,
        "codice": "CONSUMO",
        "descrizione": "Consumi",
        "e_consumo": true,
        "e_quota_fissa": false,
        "e_imposta": false,
        "e_onere": false,
        "e_prodotto": false,
        "e_servizio": false,
        "ordinamento": 10
      },
      {
        "id": 2,
        "codice": "QUOTA_FISSA",
        "descrizione": "Quote fisse",
        "e_consumo": false,
        "e_quota_fissa": true,
        "e_imposta": false,
        "e_onere": false,
        "e_prodotto": false,
        "e_servizio": false,
        "ordinamento": 20
      }
    ]
  }
}
```

L'ordinamento segue `ordinamento ASC, descrizione ASC`. Sono restituite
solo le tipologie attive (`listini_tipologie.attivo = true`) e solo le
righe della matrice attive (`listini_tipologie_utilities.attivo = true`).

#### Errori tipici

- `400` `E_VENDITE_VALIDATION`: `utility_id` mancante, vuoto o non positivo.

#### Note

- L'utility deve esistere per ottenere righe. Per `utility_id` inesistente
  la risposta è `200` con `results: []` (no 404) — accettabile per un
  endpoint lookup.
- Non applica scope per emittente: `config.listini_tipologie` è tabella
  globale.

---

## 3. Versioni listino

### 3.1 Lista versioni

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/` |

La pagina della lista `vendite.listini_versioni` (il tab «Versioni» del drawer
listino): stessa busta paginata del §1.1. Per ogni versione i dati principali,
`righe_count` e `giorni_alla_scadenza` (§7). Il dettaglio (§3.3) ha gli stessi
campi tranne `giorni_alla_scadenza`. ⚠️ Fino al 2026-10-31 era la collezione
completa `{count, results}`, senza pagina.

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `search` | string | No | Ricerca libera sulle colonne che il catalogo accende (`codice_versione`); sotto 3 caratteri si ignora |
| `limit` · `offset` | int | No | Come §1.1 |
| `order_by` | string | No | `valido_dal` (default, DESC), `valido_al`, `codice_versione`, `righe_count`, `stato`, `giorni_alla_scadenza`. Le date senza direzione si ordinano DESC |
| `order_dir` | string | No | `asc` oppure `desc` |

Campi dal modello del documento (giro 12, brief-modello-documento-vendita §16,
2026-10-28):

| Campo | Cosa dice |
|---|---|
| `stato` | il codice dello stato (`BOZZA`, `ATTIVA`, `CHIUSA`) dal vocabolario `config.stati_doc_listino_versioni`: e' lo stato **del DB**, nessuna deduzione dalle date |
| `azioni_permesse` | le `action_key` dei passaggi che **l'operatore** puo' fare dallo stato della versione (`script.fn_doc_azioni_permesse`, che applica l'azione della riga del passaggio). Oggi solo `attiva`, da BOZZA, a chi ha `attiva_listino`. Permesso ⇒ nascondi |
| `attivazione_blocco_reason` · `attivazione_blocco_reason_key` | perche' «Attiva» e' spento (codice macchina e chiave i18n del primo motivo di `script.fn_check_versione_listino_attivabile`, la stessa con cui il verbo rifiuta), da `vendite.vw_listini_versioni_azioni`; `null` = niente lo vieta. Sono le colonne che il registro `config.azioni_riga` dichiara per `ATTIVA_VERSIONE_LISTINO` |
| `eliminazione_blocco_reason` · `eliminazione_blocco_reason_key` | perche' «Elimina» e' spento (`VERSIONE_NON_IN_BOZZA`, `VERSIONE_CITATA`: il primo motivo di `script.fn_check_versione_listino_eliminabile`), dalla stessa vista; registro `ELIMINA_VERSIONE_LISTINO` (§16.13, 2026-10-29) |
| `chiusura_blocco_reason` · `chiusura_blocco_reason_key` | perche' «Chiudi» e' spento (`VERSIONE_NON_ATTIVA`: il primo motivo di `script.fn_check_versione_listino_chiudibile`, senza data), dalla stessa vista; registro `CHIUDI_VERSIONE_LISTINO` (§16.16, 2026-10-29). «Clona» non ha colonne: si clona da qualunque stato |
| `chiusura_programmata` | la versione e' ATTIVA con `valido_al` scritto: il job la porta a CHIUSA quando la fine passa. Fra la fine e il job resta ATTIVA, e si mostra cosi' |

### 3.2 Crea versione

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/` |

#### Body JSON

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `codice_versione` | string | Si | Codice univoco per listino |
| `valido_dal` | date | Si | Data inizio validita` |
| `valido_al` | date | No | Data fine validita` |
| `meta` | object | No | Metadati liberi |
| `attivo` | bool | No | Default DB `true` |

### 3.3 Dettaglio versione

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/` |

### 3.4 Aggiorna versione

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/` |

#### Campi modificabili per stato

Li decide il DB (L-5, giro 12): il guard `vendite.trgfn_listini_versioni_guard_per_stato`.
Il backend non filtra per stato e trasporta il rifiuto.

| Stato versione | Campi modificabili |
|---|---|
| `BOZZA` | `codice_versione`, `valido_dal`, `valido_al`, `meta`, `attivo` |
| `ATTIVA` | nessun campo da qui: la fine (`valido_al`) solo da «Chiudi» (§3.6-bis) o dall'attivazione di una successiva |
| `CHIUSA` | nessun campo (stato terminale) |

**Razionale**: una versione `ATTIVA` ha gia` propagato i prezzi negli snapshot di
`commesse_attivita`/`attivita_fatturabili`. Modificare `codice_versione`, `valido_dal`
o `meta` su una versione operativa creerebbe drift tra documenti emessi e stato
listino. Solo la fine resta modificabile, e solo dai verbi che la scrivono
(C-4 = a, 2026-10-29): cosi' vale sempre la regola «la fine non sta nel passato». Per
cambiare prezzi su un periodo gia` attivo, si crea una nuova versione (clone +
edit + activate).

#### Errori tipici

- `409` `E_LISTINO_VERSIONE_CAMPO_NON_MODIFICABILE` (dal DB): il campo non si cambia
  nello stato della versione; la frase nomina il primo campo. Fino al 2026-10-28 era un
  `400 E_VENDITE_VALIDATION` del backend
- `500` `E_LISTINO_VERSIONE_FINE_SOLO_DAL_VERBO` (`TECNICO`, dal DB): `valido_al` di una
  ATTIVA dal PATCH. Nessuna interfaccia lo produce: si passa da §3.6-bis
- `404` `E_VENDITE_LISTINO_VERSIONE_NOT_FOUND`

### 3.5 Clona versione

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{src_ver_id}/clona/` |

Crea una **nuova versione BOZZA** dello stesso listino copiando tutte le righe
attive della versione sorgente, **da qualunque stato** (anche da una BOZZA: C-1 = a,
2026-10-29). La copia e' il verbo `vendite.fn_clona_versione_listino`, in una
transazione: versione, righe attive e componenti attivi dei compositi con la validita'
ricalcolata sul periodo comune alla distinta e alla versione nuova. Workflow operativo "cambio prezzi": clona V001
in V002 BOZZA, modifica i prezzi che cambiano, attiva V002. La sorgente non
viene toccata.

#### Body JSON

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `codice_versione` | string | Si | Codice univoco per il listino |
| `valido_dal` | date | Si | Data inizio validita` (vedi vincolo D2 sotto) |
| `valido_al` | date | No | Data fine validita`, NULL = aperta |

La nuova versione nasce in stato BOZZA (lo stato iniziale, dal guard della
nascita: il backend non lo scrive) con `attivo=true` e `meta` vuoto. Ogni altra
chiave, `meta` e `attivo` compresi, → `400 E_VENDITE_VALIDATION`: fino al
2026-10-29 `meta` e `attivo` si validavano e poi si ignoravano in silenzio. Le righe vengono copiate
con `attivo=true` (le righe non attive della sorgente sono escluse).

#### Risposta (200)

Il dettaglio della versione nuova (§3.1) piu' i conteggi della copia:
`righe_copiate`, `componenti_copiati`, `componenti_saltati` (i componenti senza
giorni in comune fra la distinta e la versione nuova: non si copiano).

#### Vincolo D2 — `valido_dal` e retroattivita`

`nuova.valido_dal` puo` essere retroattivo (precedente alla data odierna), ma
**non puo` essere inferiore a `sorgente.valido_dal`**. Cio` protegge da cloni
"prima dell'inizio" della versione che si vuole sostituire. Lo dice il verbo
(`script.fn_check_versione_listino_clonabile`), sul campo `valido_dal`.

Il clone retroattivo non modifica le fatturazioni gia` emesse nel periodo:
queste continuano a basarsi sullo snapshot in `commesse_attivita` /
`attivita_fatturabili`. Per correggerle e` necessaria una rettifica DB-L4
(dominio separato, vedi `dev/work-in-progress/sviluppo-rettifiche.md`).

#### Errori tipici

- `400` `E_LISTINO_VERSIONE_CLONE_PRIMA_DELLA_SORGENTE` (dal DB, campo `valido_dal`) se
  `nuova.valido_dal < sorgente.valido_dal`. Fino al 2026-10-29 era un
  `400 E_VENDITE_VALIDATION` del backend
- `400` `E_VENDITE_VALIDATION` se manca un campo obbligatorio
- `409` `E_VENDITE_DUPLICATO` se `codice_versione` duplicato per il listino
  (`uq_listini_versioni_listino_codice`)
- `404` `E_VENDITE_LISTINO_VERSIONE_NOT_FOUND` se la sorgente non esiste

### 3.6 Elimina versione

| | |
|---|---|
| **Metodo** | `DELETE` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/` |

Elimina una versione **solo se in stato `BOZZA`** e non usata da un documento, con
le sue righe e i componenti dei compositi. Decide il verbo
`vendite.fn_elimina_versione_listino` (§16.11, 2026-10-29): prima il primo motivo di
`script.fn_check_versione_listino_eliminabile` (lo stesso del pulsante), poi la
cascata. Il backend non la fa piu'.

Risposta (200):

```json
{ "data": { "deleted": true, "id": 101, "righe_eliminate": 3, "componenti_eliminati": 8 } }
```

Errori tipici:

- `409` `E_LISTINO_VERSIONE_NON_ELIMINABILE`: la versione non e' in bozza
- `409` `E_LISTINO_VERSIONE_CITATA`: una bozza che un contratto, un'offerta o
  un'attivita' di commessa usa (prima cadeva sulla FK con un errore tecnico)
- `404` `E_VENDITE_LISTINO_VERSIONE_NOT_FOUND`

### 3.6-bis Chiudi versione

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/chiusura/` |

«Chiudi» e «Rimuovi chiusura» di una versione ATTIVA: fissa la fine della validita'
(la chiusura programmata) o la toglie. Decide il verbo
`vendite.fn_programma_chiusura_versione_listino` (§16.14, C-2 = a, 2026-10-29). Lo
stato non cambia: CHIUSA la scrive il job quando la fine passa. Nessun permesso di
passaggio (non e' un passaggio di stato): il permesso d'area `change`, come il PATCH
che sostituisce (`post_accesso = "change"`: senza, la POST chiederebbe `add`).

#### Body JSON

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `valido_al` | date \| null | Si | la nuova fine; `null` toglie la chiusura. ⚠️ La chiave e' obbligatoria anche quando e' `null`: un corpo vuoto e' un `400` |

Altre chiavi → `400 E_VENDITE_VALIDATION`. Risposta: il dettaglio della versione (§3.1).

#### Errori tipici

- `409` `E_LISTINO_VERSIONE_NON_CHIUDIBILE`: la versione non e' ATTIVA
- `400` `E_LISTINO_VERSIONE_FINE_NEL_PASSATO` (campo `valido_al`): la fine precede
  oggi (la data operativa). Prima il limite stava solo nel frontend
- `400` `E_DATA_AL_MINORE_DAL`: la fine precede l'inizio (guard comune delle date)
- `409` `E_VENDITE_LISTINO_VERSIONE_OVERLAP`: togliere la chiusura sovrapporrebbe la
  versione ATTIVA successiva
- `404` `E_VENDITE_LISTINO_VERSIONE_NOT_FOUND`

### 3.7 Cambia stato versione

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/stato/` |

È l'**attivazione** (BOZZA → ATTIVA), l'unico passaggio manuale della matrice
`config.transizioni_stati_listino_versioni`. Decide il verbo
`vendite.fn_attiva_versione_listino` (giro 12, L-3 e L-4, 2026-10-28).

#### Body JSON

```json
{
  "stato": "ATTIVA",
  "dry_run": false
}
```

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `stato` | string | Si | solo `ATTIVA`. ATTIVA → CHIUSA e' di processo: si programma con «Chiudi» (§3.6-bis) e la scrive il job a fine scaduta |
| `dry_run` | bool | No | Se `true`, non scrive nulla e restituisce l'anteprima delle versioni che verrebbero chiuse. Default `false`. ⚠️ Solo il booleano JSON: un altro valore (anche `"true"`) e' un `400` sul campo |

Altre chiavi → `400 E_VENDITE_VALIDATION`.

#### Il permesso

La view dichiara `post_passaggio = PassaggioDocumento(vendite.listini_versioni,
"ver_id", campo_stato="stato")`: l'azione la legge dalla riga del passaggio
(`attiva_listino`), prima della transazione, anche per il `dry_run`. Senza
l'azione: `403`.

#### Che cosa fa il verbo, in una transazione

1. la versione nel perimetro dell'utente, presa `FOR UPDATE`;
2. la riga comune del passaggio: gia' attiva → `E_DOC_GIA_NELLO_STATO`; l'azione;
3. il primo motivo che vieta (`script.fn_check_versione_listino_attivabile`):
   versione spenta, nessun prezzo;
4. la chiusura delle precedenti (decisione D3): le versioni ATTIVE e accese dello
   stesso listino, con decorrenza precedente e periodo che tocca la nuova, prendono
   `valido_al = nuova.valido_dal - 1`;
5. lo stato ATTIVA attraverso la porta.

Prima (fino al 2026-10-28) tutto questo era nel backend.

#### Modalita` `dry_run` (preview UI)

Con `dry_run: true` il verbo gira in un **savepoint annullato**: la chiamata
rifiuta con gli stessi codici dell'attivazione vera (vedi «Errori tipici»), non
lascia scritto niente e restituisce l'elenco che il verbo chiuderebbe, dallo
**stesso lettore** del verbo (`vendite.fn_versioni_listino_da_chiudere`): quello
che si mostra e' quello che si fa.

```json
{
  "data": {
    "dry_run": true,
    "versione_id": 202,
    "nuovo_stato": "ATTIVA",
    "auto_close": [
      {
        "id": 101,
        "codice_versione": "V001",
        "valido_dal": "2026-01-01",
        "valido_al_prima": null,
        "valido_al_dopo": "2026-03-31"
      }
    ]
  }
}
```

⚠️ Fino al 2026-10-28 l'anteprima leggeva il solo lettore e non verificava i
motivi: a un client senza il pulsante spento proponeva la chiusura delle
precedenti per un'attivazione che il verbo avrebbe poi rifiutato.

Senza `dry_run` la risposta è il dettaglio della versione riletto (§3.3).

#### Errori tipici

- `400` `E_VENDITE_VALIDATION`: `stato` diverso da `ATTIVA`, chiave fuori elenco, `dry_run` non booleano
- `403`: l'operatore non ha l'azione `attiva_listino`
- `404` `E_VENDITE_LISTINO_VERSIONE_NOT_FOUND`: la versione non è di quel listino, o è fuori perimetro
- `409` `E_DOC_GIA_NELLO_STATO`: la versione è già attiva
- `422` `E_LISTINO_VERSIONE_SPENTA`, `E_LISTINO_VERSIONE_SENZA_RIGHE`: i motivi del verbo
- `409` `E_VENDITE_LISTINO_VERSIONE_OVERLAP` se il vincolo `ex_listini_versioni_no_overlap` viene urtato

---

## 4. Righe prezzo versione

### 4.1 Lista righe

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/righe/` |

Le righe sono arricchite con campi display:
- `articolo_codice`, `articolo_descrizione`
- `uom_codice`, `uom_descrizione`

Query param: `attivo` (bool), `limit` / `offset` (default `25`, max `200`),
`order_by` (`articolo_descrizione` default, `articolo_codice`, `uom_codice`,
`prezzo`, `iva_aliquota`, `attivo`), `order_dir`. Envelope paginato standard.

Query param `search`: ricerca libera, le colonne le decide il catalogo della
lista `vendite.listini_righe` (`ricerca_full` nella configurazione). Sotto 3
caratteri il termine si **ignora** (nessun `400`). Cade sulle righe standalone
**e** sui compositi bundle, perché si applica ai campi che la lista mostra, dopo
l'unione delle due gambe.

### 4.2 Crea riga

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/righe/` |

#### Body JSON

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `articolo_id` | uuid | Si | Articolo prezzo |
| `uom_id` | int | Si | UoM prezzo |
| `prezzo` | decimal | Si | Prezzo unitario, `>= 0` |
| `meta` | object | No | Metadati liberi |
| `attivo` | bool | No | Default DB `true` |

Qualunque altra chiave → `400 E_VENDITE_VALIDATION`. ⚠️ 2026-10-20: tolti
`billing_account_id`, `utility_id` ed `emittente_soggetto_ruolo_id` (la riga non
ha un perimetro proprio: utility ed emittente sono del listino).

### 4.3 Aggiorna riga

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/righe/{riga_id}/` |

Campi ammessi: `prezzo`, `meta`, `attivo`. Ogni altra chiave (anche
`articolo_id`/`uom_id`, immutabili) → `400 E_VENDITE_VALIDATION`.

### 4.4 Elimina riga

| | |
|---|---|
| **Metodo** | `DELETE` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/righe/{riga_id}/` |

#### Regole specifiche

- **Immutabilita` per stato versione (guard fail-fast)**: `POST`, `PATCH` e `DELETE`
  riga sono ammessi **solo** se la versione padre e` in stato `BOZZA`. Su versioni
  `ATTIVA` o `CHIUSA` il backend rifiuta con `400 E_VENDITE_VALIDATION` prima di
  toccare il DB. Razionale: i prezzi delle versioni operative sono gia` snapshot
  in `commesse_attivita`/`attivita_fatturabili` e ogni modifica creerebbe drift
  con i documenti gia` emessi. Per cambiare prezzi su un periodo gia` attivo, si
  crea una nuova versione (clone + edit + activate).
- Il backend valida pre-flight:
  - articolo attivo
  - UoM attiva
  - compatibilita` articolo/UoM: UoM base articolo oppure UoM operativa attiva
- L'unicita` della combinazione attiva (`versione + articolo + uom`) e` demandata al DB (`uq_listini_righe_key_attiva` → `409 E_VENDITE_DUPLICATO`).

---

## 4bis. Bundle compositi (modello unificato BoM 2026-05-13)

Le righe `listini_righe` su articoli compositi sono **vietate** (trigger DB
`E_LISTINO_RIGA_COMPOSITO_VIETATO`, file 20260513-04). I prezzi dei
componenti di un articolo composito vivono nella tabella dedicata
`vendite.listini_righe_componenti`: una riga per ogni `(versione listino,
componente BoM)`. Il resolver bundle-aware (`fn_resolve_prezzo_listino_v2`
con `p_articolo_padre_contesto`) li legge prioritariamente, con fallback su
standalone.

⛔ **Non esiste una lista dei compositi** (`GET versioni/{ver_id}/bundle/`): la
rotta è solo `versioni/{ver_id}/bundle/{padre_id}/`, con `GET` (preview),
`POST` (salva) e `DELETE` (svuota). I compositi della versione arrivano dalla
lista righe, che unisce righe standalone e bundle (§4.1).

Vedi `docs/it/dev/manual/modello-componenti-bom.md` §8 per il modello.

### 4bis.2 Preview BoM padre + prezzi bundle definiti

|     |     |
| --- | --- |
| **Metodo** | `GET` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/bundle/{padre_id}/` |

Mostra la BoM corrente del padre composito + i prezzi bundle gia' definiti (LEFT JOIN). Usato dal `ComponentiDialog` FE per popolare il form di editing. Read-only.

#### Path param

- `padre_id` (uuid string, obbligatorio) — UUID articolo composito padre.

#### Risposta preview bundle (200)

```json
{
  "data": [
    {
      "articolo_componente_id": "019d6...",
      "componente_id": "019d5...",
      "componente_codice": "componente",
      "componente_descrizione": "Componente A",
      "coeff_qta": "1.0",
      "obbligatorio": true,
      "esposizione_in_fattura": "NASCOSTO",
      "iva_id": 1,
      "iva_codice": "22",
      "iva_aliquota": "22.00",
      "uom_id": 1,
      "uom_codice": "PZ",
      "listini_righe_componenti_id": 60,
      "prezzo_suggerito": "2.00"
    }
  ]
}
```

#### Regole preview bundle

- 1 riga per ogni `articoli_componenti` valida alla `data_riferimento` (BoM corrente).
- `prezzo_suggerito`: NULL se nessun prezzo bundle ancora definito (operatore deve valorizzare); altrimenti il prezzo salvato in `listini_righe_componenti.prezzo`.
- `data_riferimento` di default = oggi. Override esplicito ammesso lato service per audit di versioni ATTIVE/CHIUSE (simulare il momento dell'attivazione).
- Filtro `attivo=TRUE` su `articoli_componenti` e sulla riga bundle.
- Validazione: `articolo_padre_id` UUID non vuoto. `E_VENDITE_VALIDATION` se mancante.
- Validita' bundle (`lrc.validita`) NON proiettata: psycopg fallisce su `'infinity'` daterange. Se servira' al FE, castare a testo con `to_char(...)` o estrarre lower/upper.

---

### 4bis.3 Salva prezzi bundle (upsert batch)

|     |     |
| --- | --- |
| **Metodo** | `POST` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/bundle/{padre_id}/` |
| **Idempotency-Key** | obbligatoria (dal 2026-10-20 ogni POST che scrive la porta: `_ApiViewBase`, api.md §Idempotency-Key) |

#### Body JSON salva bundle

```json
{
  "rows": [
    {
      "articolo_componente_id": "019d6...",
      "articolo_figlio_id": "019d5...",
      "prezzo": "2.00",
      "iva_id": 1
    }
  ]
}
```

#### Risposta salva bundle (200)

```json
{
  "data": {
    "disattivati": 3,
    "inseriti": 3,
    "skipped_no_overlap": 0
  }
}
```

`skipped_no_overlap` (PG18, additivo): conta le righe non inserite perche'
l'intersezione fra `valido_dal/valido_al` della versione e quelli della
riga BoM e' vuota (es. richiesta una validita' antecedente alla BoM
corrente del componente). Le righe skippate sono loggate come warning
applicativo. Se > 0 il FE puo' mostrare un avviso all'operatore.

#### Regole salva bundle

- **Solo versione BOZZA**: il guard `_assert_versione_bozza_for_riga_op` rifiuta UPDATE su versioni ATTIVA/CHIUSA. Defense-in-depth col trigger DB `_immutabilita_v5` (codice `E_RIGA_LISTINO_VERSIONE_CHIUSA`, 409).
- **Strategia tabula rasa idempotente**: il repo prima soft-disattiva (`attivo=FALSE`) tutte le righe attive correnti per la coppia (versione, padre), poi inserisce le nuove. Garantisce stato esatto senza diff complesso. Transazione atomica.
- **Validita' = intersezione `versione ∩ BoM`** (PG18, calcolata su `valido_dal`/`valido_al` con `GREATEST`/`LEAST`): la colonna `validita` daterange e' STORED generated. Se l'intersezione e' vuota, la riga e' ignorata con warning + conteggio in `skipped_no_overlap` (evita errore SQL `range lower > upper`). La temporal FK `fk_listrighe_comp_articoli_comp_temporal` garantisce a livello DB il contenimento riga ⊆ BoM.
- **Skip prezzo null**: righe con `prezzo == NULL` vengono ignorate (= "non gestito a bundle"; il resolver fa fallback STADIO 1 standalone). Confermare con tutti i prezzi NULL = svuotare il composito (= "elimina composito" lato UI).
- **`iva_id` opzionale**: default lato DB.
- **Guard coerenza BoM PG18**: validita riga ⊆ validita BoM ora enforced da
  **temporal FK** `fk_listrighe_comp_articoli_comp_temporal` (migration 20260514-12,
  sostituisce guard 6 trigger rimosso con migration 20260514-13). Validita riga ⊆
  validita versione resta enforced dal trigger `trgfn_listini_righe_comp_guard_coerenza_bom`
  (guard residuo). Altri check (articolo_componente_id attivo, padre `is_composito=TRUE`,
  IVA padre = IVA figlio) restano nel trigger. Tutti producono `E_LISTINO_RIGA_COMP_BOM_INCOERENTE` (400).

### 4bis.4 Elimina prezzi bundle di un composito

|     |     |
| --- | --- |
| **Metodo** | `DELETE` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/bundle/{padre_id}/` |

Equivale al salvataggio con `rows: []`: soft-disattiva tutti i prezzi bundle del
composito nella versione. Solo versione BOZZA (stesso guard), idempotente (`0`
disattivati su un composito senza prezzi). Risposta `{ "disattivati": <n>,
"inseriti": 0 }`.

#### Errori

| Codice | HTTP | Sorgente |
| --- | --- | --- |
| `E_VENDITE_VALIDATION` | 400 | service (BOZZA-only guard, rows non lista, articolo_padre_id vuoto, versione senza valido_dal) |
| `E_VENDITE_DUPLICATO` | 409 | UNIQUE `uq_listini_righe_key_attiva` (riga prezzo gia' esistente) |
| `E_VENDITE_LISTINO_RIGA_COMP_OVERLAP` | 409 | EXCLUDE gist parziale `ex_listini_righe_comp_no_overlap` (ripristino enforcement 2026-06-02, migration `20260602-01`): due righe bundle **attive** sovrapposte sullo stesso `(versione, padre, componente)`. Pattern simmetrico a `E_VENDITE_PROMO_OVERLAP` / `E_VENDITE_LISTINO_VERSIONE_OVERLAP` |
| `E_RIGA_LISTINO_VERSIONE_CHIUSA` | 409 | trigger DB immutabilita' v5 (rev 2026-05-13) |
| `E_LISTINO_RIGA_COMP_BOM_INCOERENTE` | 400 | temporal FK PG18 `fk_listrighe_comp_articoli_comp_temporal` + guard residuo coerenza BoM |

Il service cattura `IntegrityError` e `DatabaseError`:

- `IntegrityError` → `_translate_integrity_error` via `map_integrity_error` (mappa UNIQUE/FK/CHECK + temporal FK BoM con codice parlante).
- `DatabaseError` P0001 → `_raise_bundle_db_error` (helper interno) preserva codici trigger (`E_RIGA_LISTINO_VERSIONE_CHIUSA`, `E_LISTINO_RIGA_COMP_BOM_INCOERENTE`).

---

## 5. Associazioni listino — RIMOSSA

⛔ **Le quattro rotte `/api/v1/vendite/listini/{listino_id}/associazioni/`
(GET/POST/PATCH/DELETE) non esistono piu'**: tolte da F2-BE-13 insieme alla
tabella `vendite.listini_associazioni`. Verificato il 2026-08-19: nel backend
vivo la parola «associazioni» compare **solo in commenti**, e
`urls_listini.py` lo dichiara in testa al file.

**Cosa si usa al suo posto.** Il legame listino → contesto non e' piu' una
tabella di associazione: il listino si sceglie dalla matrice
`anagrafiche.categorie_clienti_listini` (categoria cliente + utility + data)
oppure dal contratto del billing account. E' lo STADIO 1/2 di
`vendite.fn_resolve_prezzo_listino_v2`, descritto in `api_pricing.md`.

## 6. Test resolver prezzo — RIMOSSO

⛔ **`POST /api/v1/vendite/listini/test-prezzo/` non esiste piu'** (F2-BE-13).

**Cosa si usa al suo posto**, e sono due cose diverse:

* per **risolvere un prezzo**: `PricingService.resolve_prezzo` su
  `vendite.fn_resolve_prezzo_listino_v2` — vedi `api_pricing.md`;
* per **capire perche' un prezzo non si risolve**:
  `POST /api/v1/vendite/pricing/diagnose/`, che ispeziona la configurazione
  (contratto, matrice categoria → listino, versioni, righe) e risponde senza
  sollevare. E' quello che usa `TestResolverDialog.vue`.

## 7. Scadenze delle versioni (N2)

⭐ **Dal 2026-10-31 la regola «in scadenza senza successore» è del DB**:
`vendite.fn_listini_in_scadenza_senza_successore()` (20261031-27,
brief-db-liste-datatable-grezze-secondo-giro §7.2), una riga per versione in
vigore che scade entro N giorni senza un successore, coi giorni rimanenti. N è
il parametro `LISTINI_SCADENZA_PREAVVISO_GIORNI` (15 dal seed, con override):
**non si passa più dal client**.

La leggono, con una `LEFT JOIN` per query:

- la lista listini (§1.1): campo `giorni_alla_scadenza` (`null` = non in
  scadenza) e filtro `in_scadenza`;
- la lista versioni (§3.1): lo stesso campo, sulla versione.

Il badge del frontend (`AlertScadenzeWidget.vue`) conta i listini con
`in_scadenza=true` (§1.1, `limit=1`, il totale della busta) e al clic filtra
la lista.

⛔ **Ritirato il 2026-10-31** l'endpoint `GET /api/v1/vendite/listini/alert-scadenze/`
(parametro `giorni`, default 15, range 1-365), insieme alla query del
repository che scriveva la regola in Python (`listini_in_scadenza`,
`_filter_versioni_in_scadenza`). La regola è passata al DB riga per riga; il
caso del successore contiguo (`valido_dal = valido_al + 1`), che fino al
2026-10-21 la query sbagliava, resta presidiato sul DB vero da
`vendite/tests/db/test_listini_in_scadenza_db.py` attraverso le due liste.

---

## 8. Variazione percentuale massa (N8a)

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/applica-variazione/` |

Applica una variazione percentuale ai prezzi di tutte le righe attive di una versione
BOZZA. Supporta `dry_run` per preview e filtro opzionale per articoli.

### Body JSON

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `variazione_percentuale` | decimal | Si | Positivo = aumento, negativo = riduzione. Range: -99 a +1000 |
| `arrotondamento_decimali` | int | No | Decimali da mantenere. Default `4`, range 0-10 |
| `filtro_articoli` | array uuid | No | Se valorizzato, applica solo a questi articoli |
| `dry_run` | bool | No | Se `true`, calcola preview senza modificare. Default `false` |

### Risposta dry_run (200)

```json
{
  "data": {
    "dry_run": true,
    "righe_coinvolte": 500,
    "preview": [
      {
        "riga_id": 1001,
        "articolo_codice": "ART001",
        "articolo_descrizione": "Articolo esempio",
        "prezzo_attuale": "12.5000",
        "prezzo_calcolato": "12.8750"
      }
    ],
    "variazione_percentuale": "3.0",
    "arrotondamento_decimali": 4
  }
}
```

### Risposta applicazione (200)

```json
{
  "data": {
    "righe_aggiornate": 500,
    "variazione_percentuale": "3.0",
    "arrotondamento_decimali": 4
  }
}
```

### Regole specifiche

- Guard BOZZA: rifiuta con 400 su versioni ATTIVA o CHIUSA.
- Guard range: `-99 <= variazione <= 1000`. Fuori range → 400.
- **Arrotondamento composto**: ogni applicazione e` atomica con arrotondamento immediato.
  Due variazioni successive (+3% poi +2%) producono risultati diversi da una singola +5.06%.
- **Audit**: la variazione viene registrata in `versione.meta.variazioni_percentuali[]`
  con data, percentuale, arrotondamento, righe aggiornate e filtro.
- Frontend: `ApplicaVariazioneDialog.vue` (2 step: input → preview dry_run → conferma).

### Errori tipici

- `400` `E_VENDITE_VALIDATION`: versione non BOZZA, percentuale fuori range, arrotondamento fuori range

---

## 9. Rettifica controllata riga ATTIVA (N6)

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/righe/{riga_id}/rettifica-controllata/` |

Consente la modifica del prezzo di una riga di una versione **non BOZZA** e
**operativa oggi** (`valido_dal ≤ oggi ≤ valido_al`, o `valido_al` aperto) solo se
la riga **non e` mai stata propagata** in `commesse_attivita` o `attivita_fatturabili`.
Caso d'uso: errore di battitura su riga non ancora usata da nessuna commessa.

### Body JSON

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `prezzo` | decimal | Si | Nuovo prezzo, `> 0` |
| `motivo` | string | Si | Motivazione obbligatoria, max 500 caratteri |

### Risposta (200)

```json
{
  "data": {
    "riga_id": 1001,
    "prezzo_precedente": "12.5000000000",
    "prezzo_nuovo": "12.2500000000",
    "motivo": "errore di battitura al caricamento"
  }
}
```

### Regole specifiche

- **Endpoint dedicato** separato dal PATCH ordinario della riga. L'operazione
  eccezionale deve essere esplicita, non mascherata dal PATCH standard.
- **Una sede sola per la regola «propagata»**: il trigger DB
  `vendite.trgfn_listini_righe_guard_stato`. Il service prende il lock
  `FOR UPDATE` sulla riga, rilegge prezzo e `meta` sotto il lock e scrive; se il
  guard rifiuta, porta al chiamante il codice del DB. ⛔ Nessun controllo di
  propagazione in Python (ritirato il 2026-10-09 con `E_VENDITE_RIGA_GIA_PROPAGATA`:
  ripeteva la regola del guard con un codice suo).
- **Audit obbligatorio** in `riga.meta.rettifiche_controllate[]`.
- Che cosa vuol dire «propagata» lo dice il guard (doc auto-generata di
  `vendite.trgfn_listini_righe_guard_stato`), non questa pagina.
- Se la riga e` stata propagata → errore `409 E_RIGA_LISTINO_PROPAGATA`.
  Soluzione: clonare la versione (O1).

### Errori tipici

- `400` `E_VENDITE_VALIDATION`: versione in BOZZA (si usa il PATCH ordinario), versione non operativa oggi, prezzo non valido, motivo mancante o troppo lungo
- `409` `E_RIGA_LISTINO_PROPAGATA` (dal guard DB): riga usata in almeno una commessa/fatturabile
- `409` `E_RIGA_LISTINO_VERSIONE_CHIUSA` (dal guard DB): la versione e' CHIUSA

---

## Regole trasversali

- Tutti gli endpoint richiedono JWT.
- Le `POST` usano il pattern core `handle_post_json(...)`, le `PATCH` `corpo_oggetto` + `success_response`.
- Gli endpoint `PATCH` accettano solo payload JSON.
- Dal 2026-10-20 ogni POST che scrive porta l'`Idempotency-Key` (400 `E_IDEMPOTENCY_KEY_REQUIRED` senza), bundle compreso; PATCH, PUT e DELETE non la chiedono (api.md §Idempotency-Key). Prima nessuna rotta di listini la chiedeva.
- I booleani del corpo (`attivo`, `dry_run`…) sono booleani JSON.
- I codici errore applicativi sono centralizzati in `error_policies.py`:
  - `E_VENDITE_LISTINO_NOT_FOUND` (404)
  - `E_VENDITE_LISTINO_VERSIONE_NOT_FOUND` (404)
  - `E_VENDITE_LISTINO_RIGA_NOT_FOUND` (404)
  - `E_RIGA_LISTINO_PROPAGATA` (409, dal guard DB) — rettifica controllata N6
  - `E_VENDITE_VALIDATION` (400) — validazione generica

## Dipendenze DB

- Tabelle:
  - `vendite.listini`
  - `vendite.listini_versioni`
  - `vendite.listini_righe`
  - `vendite.listini_righe_componenti`
- Lookup/decodifiche:
  - `catalogo.vw_articoli_dettaglio`
  - `catalogo.unita_misura`
  - `catalogo.articoli`
  - `catalogo.articoli_uom_operativa`
  - `config.utilities`
  - `config.listini_tipologie`
  - `config.listini_tipologie_utilities` (matrice ammissibilita` utility x tipologia)
- Funzioni SQL:
  - `vendite.fn_resolve_prezzo_listino_v2(...)` (consumata dal pricing, non da queste rotte)
- Trigger DB di guard rilevanti per le API:
  - `trg_listini_a10_guard_tipologia_utility_ins_upd` → `vendite.trgfn_listini_guard_tipologia_utility()`
    valida la coppia `(utility_id, tipologia_id)` contro `config.listini_tipologie_utilities`

## Note di migrazione

- Il backend non replica la logica pricing del DB: la consuma.
- Overlap temporali, univocita` e buona parte delle guard di integrita` restano nel database.
- **Post-refactor 2026-04-09**: il campo `priorita` e` stato droppato da `listini_versioni` e
  `listini_associazioni` (migration `20260409-04/-05`). Nessun endpoint lo accetta piu`.
- **Sprint B-v3 (2026-04-12)**: aggiunti endpoint alert scadenze (N2), variazione % massa (N8a),
  rettifica controllata (N6). La rettifica N6 attende trigger DB defense-in-depth (`dev/db-tid`).
- **Sprint v4 (2026-04-13/14)**: rimosso il campo legacy `dominio` (enum UTILITY/COMMERCIO).
  Ogni listino ha ora due colonne NOT NULL: `utility_id` (FK `config.utilities`; id=5
  utility Base per il commercio) e `tipologia_id` (FK `config.listini_tipologie`).
  Gli endpoint create/update richiedono entrambi i campi; la matrice di ammissibilita` e`
  verificata da trigger DB. Nuovo endpoint di supporto per il drawer frontend:
  GET /api/v1/vendite/listini/tipologie-per-utility/. Nuovo filtro `tipologia_id` sulla lista
  listini e nuovi campi di ordinamento `utility_descrizione` e `tipologia_descrizione`.
