# API — Le anagrafiche di magazzino: magazzini, ubicazioni, lotti

> **Ultimo aggiornamento**: 22 novembre 2026

## Scopo

Le tre **anagrafiche** dello schema `magazzino` con endpoint propri, fuori dal
pannello di configurazione generico (decisione **B** di Tid, 2026-09-20 —
[piano](../../../dev/work-done/2026/piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config.md)):
un magazzino ha un emittente e un indirizzo, un'ubicazione ha un magazzino, un
tipo e un padre, un lotto ha un articolo, un'azienda e due date. Non sono vocabolari, e il
drawer generico non sa renderli.

Il documento interno (inventari, rettifiche), i lookup di riga e la
consultazione dello stesso dominio sono in [api_magazzino.md](api_magazzino.md).

Lista **offset-based** (`limit`/`offset`, `{count, results}`, la lingua di
`<ListaConfigurabile>`), export CSV/XLSX sorella della lista, creazione,
dettaglio e `PATCH` **per delta**. Nessuna azione di dominio: disattivare e' un
`PATCH {"attivo": false}` e il DB decide (`block_deact`).

## Contesto

Area funzionale `magazzino` (`DomainAPIView`, livello `TUTTO` per scrivere).
⚠️ **Conseguenza dichiarata** del piano §2: creare un magazzino passa da qui e
non piu' dall'area `config`.

⭐ **Le scritture passano dai verbi del DB** (dal 2026-11-22,
[brief](../../../dev/work-in-progress/brief-db-magazzino-tutte-le-scritture-dal-verbo.md) §7 R-1):
`magazzino.fn_aggiungi_{magazzino,ubicazione,lotto}` per la nascita (gli
obbligatori come argomenti, i facoltativi in `jsonb`) e
`magazzino.fn_modifica_{magazzino,ubicazione,lotto}` per il delta (una chiave a
`null` svuota, una assente resta). Il verbo controlla nella prima riga il livello
`TUTTO` sull'oggetto (`script.fn_guard_livello(…, 'magazzino', '<tabella>',
'TUTTO')`); finche' gli oggetti di magazzino non sono a catalogo nessun override
sull'oggetto si puo' scrivere, quindi risponde come l'area, cioe' come
l'endpoint. L'applicazione
non ha `INSERT`/`UPDATE` su queste tabelle. Le chiavi **ammesse** le dice il DB
(`magazzino.fn_<tabella>_colonne_ammesse('crea' | 'modifica')`), lette a ogni
scrittura; il backend valida il trasporto (tipo, obbligo, lunghezza) e una
chiave che il DB non ammette e' **400** col suo nome.

Le **lunghezze** dei testi sono quelle delle colonne: un testo piu' lungo e'
**400** col campo, mai il `22001` del DB. Codice del magazzino 32, codice
dell'ubicazione e del lotto 64, descrizione (magazzino e ubicazione) 120,
area, corsia, scaffale, piano e posizione dell'ubicazione 32. Il presidio
`tests/db/test_anagrafiche_magazzino_db.py` (11) le confronta col catalogo.
⚠️ Fino al 2026-11-23 il backend aveva un tetto unico (codice 50, descrizione
500, posizione 50), sbagliato nei due versi: oltre la colonna dava un 500, e
rifiutava i codici di ubicazione e lotto fra 51 e 64 caratteri, che il modello
ammette.

🔴 Le tre tabelle hanno la **row security** accesa: il perimetro e'
l'emittente del magazzino (per le ubicazioni, via il magazzino) e del lotto, e
lo scope applicativo si somma (`add_emittente_scope_condition`). Un dettaglio
fuori perimetro e' **404**, indistinguibile dall'inesistente (no-leak), anche
nel verbo di modifica. ⭐ Il lotto e' **dell'azienda** dal 2026-11-22
([brief](../../../dev/work-done/2026/brief-db-magazzino-lotto-dell-azienda.md)):
due aziende possono avere ciascuna il proprio lotto con lo stesso codice dello
stesso articolo; prima era dell'articolo, comune a tutte.

Le regole del modello vivono nel database e qui **non si riscrivono**: il
codice del magazzino e' lockato (`E_CODICE_NON_MODIFICABILE`), `usa_ubicazioni`
si cambia solo a registro vuoto (`E_MAG_MAGAZZINO_CON_GIACENZA`), la
disattivazione con figli attivi e' rifiutata (`E_ATTIVO_BLOCK_CHILDREN_EXIST`),
il padre dell'ubicazione e' dello stesso magazzino e senza cicli
(`E_MAG_UBICAZIONE_PADRE_DI_ALTRO_MAGAZZINO`, `E_MAG_UBICAZIONE_PADRE_CICLICO`),
il magazzino dell'ubicazione e' immutabile (`E_MAG_UBICAZIONE_MAGAZZINO_IMMUTABILE`),
la scadenza del lotto non precede l'arrivo (`chk_mag_lotti_scadenza_dopo_arrivo`),
l'articolo del lotto e' attivo (`E_ATTIVO_PADRE_NON_ATTIVO`, 409 col campo). Il service esegue e traduce
(`translate_db_errors`: i vincoli con nome col **campo**, i codici del DB intatti).

Codice: `apps/magazzino/api/views_anagrafiche.py`,
`services/anagrafiche_magazzino_service.py`,
`db/anagrafiche_magazzino_repository.py`.

## Endpoint

### Magazzini

#### 1. `GET /api/v1/magazzino/magazzini/`

Lista `magazzino.magazzini` (catalogo 80). Filtri: `search` (su codice e
descrizione; sotto la soglia del catalogo è ignorata, mai 400), `attivo` (assente = tutti, spenti compresi). Ordinamento
`order_by` in `MAGAZZINI_SORT_COLUMNS` (`codice`, `descrizione`,
`emittente_codice`, `emittente_ragione_sociale`, `indirizzo_normalizzato`, `usa_ubicazioni`, `predefinito`,
`attivo`, `ubicazioni_count`, `data_insert`, `id`); senza: `codice`.

Riga: `id`, `uid`, `codice`, `descrizione`, `emittente_fiscale_id`,
`emittente_codice`, `emittente_ragione_sociale`, `emittente_soggetto_id` (il
soggetto dell'azienda: il FE sceglie l'indirizzo fra i suoi), `indirizzo_dettaglio_id`,
`indirizzo_normalizzato`, `usa_ubicazioni`, `predefinito`, `attivo`,
`ubicazioni_count` (le attive), `meta`, audit. ⚠️ I display field arrivano con
**LEFT JOIN**: se la RLS nasconde la decodifica la colonna e' `null`, la riga
resta.

#### 2. `GET /api/v1/magazzino/magazzini/export/?formato=csv|xlsx`

Il file, con gli stessi filtri e ordinamento; colonne dalla preferenza della
lista (`lista_codice = magazzino.magazzini`, letto dalla stessa costante della
lista).

#### 3. `POST /api/v1/magazzino/magazzini/`

Crea. Payload: `codice`, `descrizione`, `indirizzo_dettaglio_id` (obbligatori);
`usa_ubicazioni`, `predefinito`, `meta` (facoltativi). ⛔ **`emittente_fiscale_id`
non viaggia**: lo mette `trgfn_default_emittente_fiscale('SOLLEVA')` dalla GUC
della sessione — l'admin globale su «tutti gli emittenti» riceve
`E_EMITTENTE_NON_RISOLTO` (400 col campo). ⛔ `attivo` non si sceglie alla
nascita. `Idempotency-Key` obbligatoria. Risposta: il dettaglio.

#### 4. `GET /api/v1/magazzino/magazzini/{id}/`

Il dettaglio (stessa riga della lista). 404 `E_MAG_MAGAZZINO_NON_TROVATO`
(NON_TROVATO) se non esiste **o** e' fuori perimetro.

#### 5. `PATCH /api/v1/magazzino/magazzini/{id}/`

Per **delta**: solo le chiavi presenti viaggiano (`codice`, `descrizione`,
`indirizzo_dettaglio_id`, `usa_ubicazioni`, `predefinito`, `attivo`, `meta`).
Cosi' il lock su `codice` scatta solo se il codice cambia davvero e il guard su
`usa_ubicazioni` solo se lo si tocca. Risposta: il dettaglio aggiornato.

### Ubicazioni (figlie del magazzino)

Il **padre e' nel path**: il perimetro e' la testata, e un magazzino fuori
scope e' 404 **prima** di leggere le figlie. La coppia (magazzino, ubicazione)
e' la risorsa: un'ubicazione di un altro magazzino «non c'e'»
(`E_MAG_UBICAZIONE_NON_TROVATA`).

#### 6. `GET /api/v1/magazzino/magazzini/{id}/ubicazioni/`

Lista `magazzino.ubicazioni` (catalogo 81). Filtri: `search`, `attivo`,
`parent_id` (le figlie dirette di un'ubicazione). Ordinamento in
`UBICAZIONI_SORT_COLUMNS`; senza: `codice`. Riga: `id`, `magazzino_id`,
`codice`, `descrizione`, `tipo_id`, `tipo_codice`, `tipo_descrizione`,
`parent_id`, `parent_codice`, `area`, `corsia`, `scaffale`, `piano`,
`posizione`, `attivo`, `meta`, audit.

#### 7. `GET /api/v1/magazzino/magazzini/{id}/ubicazioni/export/?formato=`

Il file (`lista_codice = magazzino.ubicazioni`).

#### 8. `POST /api/v1/magazzino/magazzini/{id}/ubicazioni/`

Crea nel magazzino del path. Payload: `codice`, `tipo_id` (obbligatori);
`parent_id`, `descrizione`, `area`, `corsia`, `scaffale`, `piano`, `posizione`,
`meta`. Il padre dello stesso magazzino e senza cicli lo decide
`trgfn_ubicazioni_guard_parent` (campo `parent_id` nel rifiuto).

#### 9. `GET /api/v1/magazzino/magazzini/{id}/ubicazioni/{ubicazione_id}/`

Il dettaglio (`ubicazione_id` è l'id intero dell'ubicazione); 404 sulla coppia.

#### 10. `PATCH /api/v1/magazzino/magazzini/{id}/ubicazioni/{ubicazione_id}/`

Per delta (`codice`, `descrizione`, `tipo_id`, `parent_id` — `null` la rende
radice —, la posizione, `attivo`, `meta`). ⛔ `magazzino_id` non e' fra le
chiavi: un'ubicazione nasce nel suo magazzino (lock a DB).

Il lookup `GET .../ubicazioni/lookup/` (le attive, per il form di riga) resta
com'era: sta con gli altri due lookup di riga in [api_magazzino.md](api_magazzino.md).

### Lotti (dell'articolo e dell'azienda)

#### 11. `GET /api/v1/magazzino/lotti/?articolo_id=<uuid>`

Lista `magazzino.lotti` (catalogo 82). **`articolo_id` obbligatorio** (400 col
campo se manca o non e' un uuid): un elenco di tutti i lotti di tutti gli
articoli non e' una domanda di nessuno. Filtri: `search` (sul codice),
`attivo`. Ordinamento in `LOTTI_SORT_COLUMNS`; senza: `data_arrivo DESC` (le
date partono DESC). Riga: `id`, `articolo_id`, `emittente_fiscale_id`,
`codice`, `data_arrivo`, `data_scadenza`, `attivo`, `meta`, audit.

La lista e' a catalogo con `perimetro_emittente = true` (dal 2026-11-22): le
view dichiarano `lista_codice`, come magazzini e ubicazioni, e la lista legge i
lotti delle aziende del perimetro filtrate dallo scope.

#### 12. `GET /api/v1/magazzino/lotti/export/?formato=&articolo_id=`

Il file.

#### 13. `POST /api/v1/magazzino/lotti/`

Crea. Payload: `articolo_id`, `codice`, `data_arrivo` (obbligatori);
`data_scadenza` (>= arrivo: lo dice il CHECK, il BE traduce col campo e non
ricontrolla), `meta`. ⛔ **`emittente_fiscale_id` non viaggia**: l'azienda del
lotto la mette il DB dalla sessione, come per il magazzino. Su un articolo disattivo il DB rifiuta
(`E_ATTIVO_PADRE_NON_ATTIVO`, 409, campo `articolo_id`): il FE non apre il drawer su
un articolo spento. ⚠️ Fino al 2026-11-07 il require rispondeva `E_ATTIVO_REQUIRE`
(TECNICO, 500): oggi quel codice lo solleva solo il generatore dei trigger.

#### 14. `GET /api/v1/magazzino/lotti/{id}/`

Il dettaglio; 404 `E_MAG_LOTTO_NON_TROVATO` se non esiste **o** e' di un'altra azienda.

#### 15. `PATCH /api/v1/magazzino/lotti/{id}/`

Per delta (`codice`, `data_arrivo`, `data_scadenza` — `null` la toglie —,
`attivo`, `meta`). ⛔ `articolo_id` non e' fra le chiavi.

## Codici errore

| codice | quando |
|---|---|
| `E_MAGAZZINO_VALIDATION` (fino al 2026-09-23 il generico `E_VALIDATION_INPUT`, R-6) | payload o query rifiutati dal BE (campo nel contesto); FK/CHECK del DB tradotti col campo |
| `E_ANAG_DUPLICATO` | `uq_magazzini_codice`, `uq_mag_ubicazioni_mag_codice`, `uq_mag_lotti_emittente_articolo_codice` (il codice del lotto e' unico nell'azienda; fino al 2026-11-22 `uq_mag_lotti_articolo_codice`) — campo `codice` |
| `E_MAG_MAGAZZINO_NON_TROVATO` · `E_MAG_UBICAZIONE_NON_TROVATA` · `E_MAG_LOTTO_NON_TROVATO` | i tre 404 (R-2 del brief DB): dalla lettura del service o dal verbo di modifica, con la stessa risposta |
| `E_PERMESSO_NEGATO` | 403 dal verbo, se il livello sull'oggetto e' sotto `TUTTO` (l'endpoint lo nega prima con lo stesso criterio) |
| `E_CAMPO_NON_AMMESSO` | la chiave che il verbo non ammette, col nome; il BE la rifiuta prima (`E_MAGAZZINO_VALIDATION`), quindi arriva solo da un chiamante che salta il service |
| i codici del DB | `E_CODICE_NON_MODIFICABILE`, `E_MAG_MAGAZZINO_CON_GIACENZA`, `E_ATTIVO_BLOCK_CHILDREN_EXIST`, `E_MAG_UBICAZIONE_PADRE_*`, `E_MAG_UBICAZIONE_MAGAZZINO_IMMUTABILE`, `E_EMITTENTE_NON_RISOLTO`, `E_ATTIVO_PADRE_NON_ATTIVO`: passano **com'e'**, con la frase e il campo del catalogo |

## Presidi

`apps/magazzino/tests/services/test_anagrafiche_magazzino_service.py` (unit,
mock del repository), `tests/api/test_anagrafiche_magazzino_api.py` (rotte,
parametri, coppie lista/export), `tests/db/test_anagrafiche_magazzino_db.py`
(DB provvisto: lista e dettaglio sul database vero, 404 no-leak, `articolo_id`
obbligatorio, le chiavi lette dal backend uguali a quelle ammesse dal DB, il
rifiuto del verbo senza livello, il lotto dell'azienda). Trasversali: `test_liste_configurabili_seed` (whitelist ↔ seed),
`test_perimetro_emittente_copertura`, `test_export_lista_codice_pari`.
