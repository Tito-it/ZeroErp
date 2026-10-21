# API fatture_list (Django)

## Scopo

Esporre via HTTP l'**elenco paginato dei documenti fiscali** — fatture, note di
credito e note di debito — con filtri, ordinamento configurabile, scope
emittente ed export CSV/XLSX.

## Contesto

⭐ **È la settima lista del ciclo attivo, e la più tarda.** Fino al **2026-08-24**
la fattura era **l'unico documento senza il suo elenco**: `preventivi`,
`offerte`, `ordini`, `contratti`, `ddt` e `resi` avevano la loro
`ui.lista_definizione`, `fatture` no. Un documento fiscale si raggiungeva
**solo** passando da un lotto, da un cruscotto o da un collegamento.

Il caso che l'ha resa urgente — rilievo di Tid, nato sul campo — è una commessa
di **competenza giugno** fatturata **ad agosto**: il documento porta la data di
**agosto** dentro un lotto di **giugno**, e chi lo cerca lo cerca per *quella*
data. Il racconto completo è nel **§11-bis** di
[brief-db-event-log-scope-e-riga-parlante.md](../../../dev/work-done/brief-db-event-log-scope-e-riga-parlante.md).

Sorgente: la vista canonica **`vendite.vw_fatture_lista`**, `security_invoker`.

⛔ **Mai una query nostra al posto della vista.** È la regola di tutte e sei le
sorelle: una seconda verità sullo stesso elenco divergerebbe al primo ritocco.

⚠️ **Sola lettura, per costruzione.** La fattura si produce dalla pipeline di
fatturazione e oltre `EMESSA` le righe sono congelate a DB. Non esiste `POST`, e
non è una dimenticanza.

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/vendite/fatture/`
- Export: `/api/v1/vendite/fatture/export/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Query param (tutti opzionali; assente o vuoto = nessun filtro):
  - `search` (string) — attivo da **3 caratteri**; cerca su `numero` (cast a
    testo), `ragione_sociale_completa`, `ba_codice` e
    `id_fiscale_univoco_cf_piva`
  - `stato_codice_interno` (string) — stato del documento fiscale, un
    `codice_interno` di `config.stati_doc_fiscale`
  - `natura_doc_codice` (string) — `codice_interno` di
    `config.nature_doc_fiscale` (`FATTURA` | `NOTA_CREDITO` | `NOTA_DEBITO`)
  - ⚠️ Per entrambi, un valore che il catalogo non conosce → `400
    E_VENDITE_VALIDATION` col campo (`context.field`). Dal 2026-10-20: prima
    rispondeva lista vuota. Codici dismessi ammessi
  - `billing_account_id` (int) — il cliente
  - `id_fiscale` (string) — codice fiscale / partita IVA, **confronto esatto**
  - `utility_id` (int)
  - `data_da` / `data_a` (date ISO) — **data del DOCUMENTO**
  - `limit` (int, default `25`, max `200`) · `offset` (int, default `0`): fuori
    limiti (`limit` fuori da 1..200, `offset` negativo) o non interi → 400
    `E_VALIDATION_INPUT` (il fuori limite dal 2026-10-21; prima si riportava nei
    limiti)
  - `order_by` (string) — `campo_sorgente` del catalogo `vendite.fatture`,
    whitelist `_ORDER_COLS_FATTURE`; default `data`
  - `order_dir` (string) — `asc` | `desc` (default `desc`)
  - `formato` (solo export) — `csv` (default) | `xlsx`

⚠️ **`data_da`/`data_a` filtrano la data del DOCUMENTO, non la competenza della
commessa che l'ha generato.** È la ragione per cui questa lista esiste: filtrare
per competenza avrebbe riprodotto esattamente il buco che la lista chiude.

⚠️ **`formato` e non `format`**: quest'ultimo è un *magic parameter* di DRF e
verrebbe intercettato prima della view.

## Output

Envelope standard `success_response(paginated_envelope(...))`: `results`,
`count`, `page`, `page_size`, `total_pages`.

Ogni riga è **la riga della vista** (`SELECT v.*`), e basta: dal changeSet
`20260829-01/02` la vista porta gia' `frontiera_tipo_codice_interno` e
`frontiera_natura_doc_codice_interno`, quindi il repository non decodifica piu'
niente. ⛔ *(Testo superato: «più `frontiera_tipo_codice` (LEFT JOIN su
`config.sorgenti`)» — quel join era la stessa riga ricopiata in sette
repository, e dimenticarla spegneva la cella «Transito» in silenzio.)*
⚠️ E `natura_doc_codice` della riga si chiama ora `natura_doc_codice_interno`:
il **filtro** in query string resta `natura_doc_codice`, perche' e' un nome di
parametro d'ingresso e non di colonna.
⭐ Alla riga della vista si aggiungono le **colonne di sintesi lineage**
(`unisci_sintesi_lineage`, da `vendite.fn_documento_lineage_sintesi`, una
chiamata per blocco di righe della pagina): una riga senza sintesi le ha
comunque tutte, a `null`.

Errori:
- `400 E_VENDITE_VALIDATION` — stato o natura fuori vocabolario
- `400 E_VALIDATION_INPUT` — filtro malformato (`billing_account_id`/`utility_id`
  non interi, `data_da`/`data_a` non ISO)
- `403` — permesso modello `("vendite", "fattura")` mancante
- `422 E_UI_LISTA_EMITTENTE_DA_SCEGLIERE` — la lista è `multi_emittente = f`:
  chi ha più emittenti nello scope e non ne ha scelto uno riceve il rifiuto del
  cancello di perimetro

L'export risponde `text/csv` o XLSX, con **colonne, ordine e visibilità presi
dalla configurazione lista dell'operatore** (`UiService.get_lista_config` +
`ListaExportService`) e i filtri applicati riportati in testata.

⚠️ L'export fetcha `EXPORT_MAX_ROWS + 1` righe per **rilevare** il superamento
del tetto invece di consegnare un file troncato in silenzio.

## Regole

| Regola | Perché |
|---|---|
| **Whitelist ORDER BY chiusa** | Un nome fuori elenco ripiega sul default invece di entrare nella query |
| `valuta_codice` e `azioni` **fuori** dalla whitelist | Il seed li dichiara **non ordinabili**: offrire qui una capacità che il catalogo non espone sarebbe irraggiungibile, e il presidio dei seed la segnala |
| **NULL = valore minimo** (`sql_order_direction`) | `numero` è NULL su tutte le fatture non ancora numerate: i default PostgreSQL le manderebbero **in cima** proprio ordinando dal più recente |
| **Tiebreak su `v.id`**, non su `numero` | Paginazione deterministica; `numero` è NULL sulle non numerate |
| **Filtri identici fra lista ed export** | *Il file È la lista*: un filtro che non arriva all'export consegna a qualcuno un elenco più largo di quello che stava guardando |
| `model_permission = ("vendite", "fattura")` | Stesso livello oggetto del dettaglio: chi non può vedere una fattura non ne vede nemmeno l'elenco |

### Scope emittente — la RLS c'è, e il filtro si somma

`vendite.fatture` ha **RLS attiva** con due policy (`rls_fatture_ef_whitelist`
`FOR ALL`, `rls_fatture_ba_ownership` `FOR SELECT`), e la vista è
`security_invoker`: **il perimetro morde a livello DB**, prima che il backend
dica qualcosa. Verificato: `0` righe senza contesto operatore (fail-closed).

`add_emittente_scope_condition(column="v.emittente_fiscale_id", convention="pk")`
resta come **difesa in profondità**, come prescrive
[api.md](../../../dev/api.md) §Scope emittente e come fanno tutte e sei le
sorelle.

⭐ E ha una ragione concreta: **la RLS gira sulle tabelle, il filtro applicativo
sulla colonna della vista**. Un `LEFT JOIN` futuro verso una tabella senza policy
sfuggirebbe alla prima e non al secondo.

⚠️ **La discriminazione non è mai stata esercitata sui dati**: tutte le fatture
in essere appartengono a un solo emittente, quindi un operatore con whitelist
ristretta vede lo stesso numero di righe di un SUPER_ADMIN. Il *fail-closed* è
verificato; la *discriminazione* no.

⚠️ `lista_codice` è scritto **letterale** su entrambe le view, non come costante:
`test_perimetro_emittente_copertura` legge quell'attributo con
`ast.literal_eval`, e una variabile la salta in silenzio — la lista risulterebbe
senza cancello.

## Dipendenze DB

- `vendite.vw_fatture_lista` (changeSet `20260824-15`, pgTAP
  `db/pgtap/vendite/test-vw-fatture-lista.sql`)
- ~~`config.sorgenti` (LEFT JOIN per `frontiera_tipo_codice`)~~ — non piu': la vista porta il codice (`20260829-02`)
- `ui.lista_definizione` **48** `vendite.fatture` — 22 colonne, preset
  `fatture_default` (ordinamento `data desc`, pagina 25), `multi_emittente = f`

## Note per il frontend

⚠️ **I nomi degli slot `#cell-…` sono i `codice` di QUESTA lista**, e **non**
coincidono con quelli delle sorelle: qui il DB ha chiamato le colonne
`natura_doc_descrizione`, `stato_descrizione`, `pratica_numero`; sui contratti si
chiamano `natura`, `stato`, `pratica`.

⛔ Uno slot col nome sbagliato **non dà nessun errore**: la cella ripiega sul
valore grezzo e i Tag colorati spariscono in silenzio. **Il nome si legge dal
seed, mai dalla lista sorella.**

## I due collegamenti in entrata *(2026-08-24)*

Le liste **soggetti** e **clienti** mandano qui con una voce del kebab («Vedi le
fatture»), e **con due criteri diversi**:

| Da | Criterio | Perché |
| --- | --- | --- |
| `anagrafiche.soggetti` | `id_fiscale` | Un soggetto è una **persona giuridica** e può avere **più billing account**: «le sue fatture» è un insieme più largo di «le fatture di un conto» |
| `anagrafiche.clienti` | `ba` → `billing_account_id` | Lì la riga **è** un conto |

⚠️ **`id_fiscale` non è un doppione di `search`**, che sullo stesso campo fa
`ILIKE %…%`. Un `ILIKE` sul collegamento sarebbe sbagliato **in modo
silenzioso**: una partita IVA è contenuta in altre partite IVA più lunghe, e il
collegamento consegnerebbe le fatture di qualcun altro senza dare nessun segno.

⛔ **Il collegamento TOGLIE il pavimento temporale.** La lista nasce con `data_da`
= oggi−60gg (regola delle liste documento), ma chi arriva da un cliente chiede
*«le SUE fatture»*, non «le sue fatture recenti»: con il pavimento attivo un
soggetto con documenti di sei mesi fa riceverebbe **«Nessuna fattura»** — una
risposta falsa che non sembra un errore.

⛔ **E la pagina lo DICHIARA a video**, con un banner e un pulsante per togliere
il filtro. Una lista che mostra 8 righe su 18 senza dire perché si legge come
l'elenco intero: *«questo cliente ha 8 fatture»* invece di *«ne sto mostrando 8
delle 18 che ci sono»*.

⚠️ **Nota per chi tocca la lista clienti**: la vista `vw_clienti_lista` ha **sia
`id` sia `billing_account_id`**, e non coincidono mai (misurato: 0 righe su 21).
Passare `id` darebbe un filtro valido e **sempre vuoto** — «questo cliente non ha
fatture» su ogni cliente, senza nessun errore.

## Correlati

- [api_fattura_dettaglio.md](api_fattura_dettaglio.md) — il documento singolo
- [api_fattura_giornale.md](api_fattura_giornale.md) — la sua storia
- [api_lotto_fatture_list.md](api_lotto_fatture_list.md) — i documenti *di un
  lotto*, che è un'altra domanda
