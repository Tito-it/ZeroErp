# API Dashboard Competenza — Lente 1 (Django)

## Scopo

Espone la Lente 1 Competenza dei cruscotti fatturazione a due lenti: aggregata
annuale del funnel commessa → fattura per mese di competenza (4 stadi + breakdown
per stato documento fiscale), drill-down paginato a grana attività e lista degli
errori vivi di fatturazione (blocco 4).

## Contesto

Fase 1 BE del brief
[brief-design-fatturazione-due-lenti](../../../dev/work-done/brief-design-fatturazione-due-lenti.md)
(substrato DB in
[brief-db-fatturazione-due-lenti](../../../dev/work-done/brief-db-fatturazione-due-lenti.md),
migrations `20260706-01..15`): tre endpoint GET **sottili** sopra le proiezioni
read-only `vendite.vw_dash_competenza_mensile` (aggregata formato lungo),
`vendite.vw_dash_competenza_attivita` (grana attività) e
`vendite.vw_dash_competenza_errori` (union task in errore + fatture critical).
Nessuna logica di dominio in Python: stadi, ritardo e competenza vivono nelle
viste (DB-first); il service fa solo il **pivot** del formato lungo. Livello area
`LETTURA` sufficiente; nessuna azione di processo.

```text
GET /api/v1/vendite/dashboard-competenza/                   (ApiDashboardCompetenza)
GET /api/v1/vendite/dashboard-competenza/attivita/          (ApiDashboardCompetenzaAttivita)
GET /api/v1/vendite/dashboard-competenza/commesse/          (ApiDashboardCompetenzaCommesse)
GET /api/v1/vendite/dashboard-competenza/commesse/export/   (ApiDashboardCompetenzaCommesseExport)
GET /api/v1/vendite/dashboard-competenza/gruppi/            (ApiDashboardCompetenzaGruppi)
GET /api/v1/vendite/dashboard-competenza/gruppi/export/     (ApiDashboardCompetenzaGruppiExport)
GET /api/v1/vendite/dashboard-competenza/residui/           (ApiDashboardCompetenzaResidui)
GET /api/v1/vendite/dashboard-competenza/residui/export/    (ApiDashboardCompetenzaResiduiExport)
GET /api/v1/vendite/dashboard-competenza/errori/            (ApiDashboardCompetenzaErrori)
GET /api/v1/vendite/dashboard-competenza/errori/export/     (ApiDashboardCompetenzaErroriExport)
```

Gli export (`?formato=csv|xlsx`, default csv; mai `format`) prendono gli stessi
filtri e lo stesso ordinamento della lista gemella, colonne dal catalogo della
lista. Le liste `commesse/`, `gruppi/`, `residui/`, `errori/` e i loro export
dichiarano `lista_codice` (`vendite.dash_competenza_*`): il cancello di
perimetro emittente può rispondere `422 E_UI_LISTA_EMITTENTE_DA_SCEGLIERE`.

**Ordinamento comune** a tutte le liste: con `order_by` e senza `order_dir` le
colonne data (per nome: `data_*`, `*_dal/_al`, `*_at`, `competenza_mese`)
partono DESC, le altre ASC; il vuoto vale come minimo (`ASC NULLS FIRST` /
`DESC NULLS LAST`, `sql_order_direction`). Paginazione `limit`/`offset`
(`pagina_da_query`): `limit` default 25, max 200, `offset` default 0; non
interi, `limit` fuori da 1..200 o `offset` negativo → 400 `E_VALIDATION_INPUT`
(il fuori limite dal 2026-10-21: prima si riportava nei limiti in silenzio). ⛔
`page`/`page_size` in query sono un 400 `E_VALIDATION_INPUT` dal 2026-10-21
(prima erano il contratto di queste liste); la risposta porta ancora `page` e
`page_size`, ricavati dall'offset.

Catena: view (`views_dashboard_competenza.py`) →
`vendite_service.fn_dash_competenza_{mensile,attivita,commesse,errori}` →
`VenditeRepository.list_dash_competenza_{mensile,attivita,commesse,errori}` +
`count_dash_competenza_errori_mensile`.

Il drill-down esiste in **due grane** sullo stesso perimetro (mese + stadio +
`solo_ritardo`): `attivita/` a grana attività (una riga per `commessa_attivita`)
e `commesse/` **aggregato per commessa** (una riga per commessa — DEC-4, brief
processi-fatturazione §FASE E). Il FE della Lente 1 usa `commesse/` per la lista
(la commessa non è più ripetuta); il dettaglio a grana attività vive nel drawer
di gestione commessa. Entrambi leggono `vw_dash_competenza_attivita` (lo scope
emittente è DB-side via GUC nella vista): `commesse/` fa `GROUP BY commessa_id`.

## Input

### `GET /dashboard-competenza/`

- `anno` (opzionale, int): anno di competenza. Default: anno corrente.
  Range ammesso 2000–2100 (`E_VENDITE_VALIDATION` fuori range,
  `E_VALIDATION_INPUT` se non numerico).

### `GET /dashboard-competenza/attivita/`

- `competenza_mese` (obbligatorio, date ISO): mese di competenza; qualsiasi
  giorno viene normalizzato al 1° del mese.
- `stadio` (opzionale): `DA_APPROVARE | DA_EMETTERE | EMESSA_NON_FATTURATA |
  FATTURATA` (case-insensitive; fuori whitelist → `E_VENDITE_VALIDATION`;
  assente = tutti gli stadi).
- `solo_ritardo` (opzionale, bool): se `true` solo le attività emesse in ritardo
  (`emessa_in_ritardo IS TRUE` — recuperi tardivi, §7 del design).
- `order_by` / `order_dir` (opzionali): **ordinamento colonne server-side**
  (convenzione delle liste standard). `order_by` in whitelist —
  `commessa_codice` | `cliente_display` | `articolo_codice` (ordina per la
  descrizione **mostrata**, `COALESCE(art.descrizione, art.codice)`) |
  `data_attivita` (ordina per la **colonna data**, non per la stringa
  gg/mm/aaaa del FE) | `valore`; `order_dir` = `asc` | `desc`. Senza `order_by`:
  `valore DESC`. Server-side
  perché la lista è paginata: ordine corretto su **tutte** le pagine. Colonna
  fuori whitelist o direzione ≠ asc/desc → 400 (`E_VENDITE_VALIDATION`). Tiebreak
  stabile `(commessa_codice, commessa_attivita_id)`.
- `limit` / `offset` (opzionali): paginazione standard (default 25/0, max 200).
- ⚠️ `registro_id` / `registro_non_risolvibile` **non** esistono qui: il filtro
  sezionale è solo di `gruppi/`.

### `GET /dashboard-competenza/commesse/`

Stesso perimetro e stessi filtri di `attivita/` (`competenza_mese` obbligatorio,
`stadio`, `solo_ritardo`, `limit`/`offset`), ma **aggregato per commessa**.

- `order_by` / `order_dir` (opzionali): whitelist **aggregata** —
  `commessa_codice` | `cliente_display` | `n_attivita` | `valore_tot` (default,
  DESC) | `data_attivita_max` | `emittente_ragione_sociale`; `order_dir` = `asc` | `desc`. Le colonne di riga
  (es. `data_attivita`) **non** sono ammesse qui → 400 (`E_VENDITE_VALIDATION`).
  Tiebreak stabile `(commessa_codice, commessa_id)`.
- Il `count` dell'envelope è il **numero di commesse distinte** nel perimetro
  (non di attività).

### `GET /dashboard-competenza/gruppi/`

Elenco dei **gruppi fatturabili** (emissione mirata, 2026-07-27).

- `competenza_mese` (obbligatorio, date ISO, normalizzato al 1°).
- `stadio` (opzionale, whitelist come sopra). Il cockpit usa `DA_EMETTERE`.
- `tipo_gruppo` (opzionale, **assente = tutti**): filtro «tipo
  documento/sorgente». Valori = `config.sorgenti.codice_interno`
  (`PREVENTIVO`, `ORDINE_VENDITA`, `CONTRATTO`, `DDT_VENDITA`, …) oppure
  `ONERI_COMMESSA` per le righe manuali senza documento. **Nessuna whitelist
  Python**: il vocabolario è estensibile lato DB e una lista parallela si
  disallineerebbe al primo tipo aggiunto; il valore è un bind param e le voci
  valide del perimetro le dichiara il blocco `tipi` della risposta.
- `ba_fatturazione_id` (int, opzionale) / `ba_non_determinabile` (bool,
  opzionale): filtro **cliente** sul BA di fatturazione (lo stesso che entra
  nella chiave fattura). Alternativi: `ba_non_determinabile=true` vince e
  seleziona i gruppi senza BA determinabile.
- `registro_id` (int, opzionale) / `registro_non_risolvibile` (bool,
  opzionale): filtro **sezionale**, vedi §«Il filtro per sezionale».
- `search` (opzionale): ricerca libera, le colonne le decide il catalogo della
  lista `vendite.dash_competenza_gruppi` (`ricerca_full` nella configurazione).
  Sotto 3 caratteri il termine si **ignora** (nessun `400`, nessuna lista
  svuotata). Vale per lista, `riepilogo` ed export — la soglia sta nel
  repository; le tre facet non la seguono (perimetro base).
- `order_by` / `order_dir` (opzionali): whitelist `riferimento` | `tipo_gruppo` |
  `cliente_display` | `commessa_codice` | `n_attivita` | `valore` (default,
  DESC) | `data_attivita_max` | `ba_codice_fatturazione` | `id_fiscale` |
  `emittente_ragione_sociale` | `registro_codice` | `data_documento_prevista` |
  `ultimo_esito` | `ultimo_errore_codice` | `ultimo_errore_quando` |
  `ultimo_lotto_codice`; fuori whitelist → 400 `E_VENDITE_VALIDATION`;
  tiebreak stabile `gruppo_key ASC, stadio`.
- `limit` / `offset` (opzionali): paginazione standard.

### `GET /dashboard-competenza/residui/`

Elenco dei **residui** del mese (2026-08-27): le attività fatturabili che una
fattura non ce l'hanno più e che nessun giro riprenderà da solo. È l'elenco su
cui agisce il verbo «Riporta da emettere».

- `competenza_mese` (**obbligatorio**, date ISO, normalizzato al 1°).
- `order_by` / `order_dir` (opzionali): whitelist di **dieci** colonne, chiavate
  sul `campo_sorgente` del catalogo e non sul `codice` — due divergono
  (`articolo` → `articolo_codice`, `lotto_provenienza` →
  `lotto_provenienza_codice`). Senza `order_by`: `competenza_mese`, che ora
  segue la regola delle date (DESC senza `order_dir`); la colonna è comunque
  costante sul mese, e l'ordine visibile lo decide il tiebreak.
- `limit` / `offset` (opzionali): paginazione standard.

⛔ **Non esiste un parametro per scegliere il motivo**, ed è deliberato. Lo
stadio `EMESSA_NON_FATTURATA` contiene **quattro** situazioni e solo `RESIDUO`
chiede un'azione: esporre un filtro darebbe a chi chiama l'illusione di poter
allargare il perimetro del verbo, che invece lo decide il modello. Il `WHERE
motivo_non_fatturata = 'RESIDUO'` sta nel repository e il discriminante lo
calcola la **vista**. Il valore `RESIDUO` vive in una costante sola
(`MOTIVO_NON_FATTURATA_RESIDUO`, in `db/vendite_repository.py`) e si passa
come **parametro SQL**, non come letterale dentro la query.

⭐ **Perché `competenza_mese ASC` e non `valore DESC` come le liste sorelle**:
il default è quello che il preset `dash_competenza_residui_default` dichiara a
catalogo, e il repository e il frontend lo ripetono uguale — se divergessero,
l'export (che non passa dai filtri a video) darebbe un ordine diverso dalla
schermata e chi apre il foglio non avrebbe modo di accorgersene.

⚠️ **Su questa lista quella colonna è però COSTANTE**: il perimetro è un mese
solo (`competenza_mese` è obbligatorio), quindi l'ordine che si vede lo decide
per intero il tiebreak — commessa, poi chiave. La clausola si scrive lo stesso
perché è ciò che il catalogo dichiara e perché sarebbe già quella giusta se il
filtro si allargasse a un intervallo. ⛔ Quel che **non** si può dire è «i più
vecchi in cima»: dentro un mese solo non c'è nessuna anzianità da leggere qui.

⚠️ Con la primaria ASC anche il **tiebreak** è ASC (`attivita_fatturabile_id`):
allineare il verso è la regola di `sql_tiebreak_direction` — altrimenti dentro
lo stesso mese l'elenco andrebbe al contrario di come è stato chiesto.

### `GET /dashboard-competenza/residui/export/`

Esporta la **stessa** lista con lo stesso ordinamento; colonne e ordine dal
catalogo `vendite.dash_competenza_residui`. Hard cap 10.000 righe.
⚠️ `formato` (csv | xlsx), **non** `format`: quest'ultimo è magic per DRF.

### `GET /dashboard-competenza/errori/`

- `competenza_mese` (opzionale, date ISO, normalizzato al 1°): assente = errori
  vivi di tutti i mesi.
- `order_by` / `order_dir` (opzionali, **dal 2026-08-03**): ordinamento
  server-side. `order_by` in whitelist — `tipo_evento` | `lotto_codice` |
  `fattura_numero` | `error_code` | `data_evento` (default) |
  `emittente_ragione_sociale`; `order_dir` = `asc` | `desc` (senza: DESC su
  `data_evento`, ASC sulle altre). Colonna fuori whitelist o direzione
  ≠ asc/desc → 400 (`E_VENDITE_VALIDATION`, validato nel service).
  ⚠️ NULL come minimo (`ASC NULLS FIRST` / `DESC NULLS LAST`): metà della
  union non ha i campi di documento (un errore di task non ha fattura, una
  fattura critical non ha task), e in DESC finiscono in coda.
- `limit` / `offset` (opzionali): paginazione standard.

## Output

### Aggregata annuale

```json
{
  "data": {
    "anno": 2026,
    "mesi": [
      { "competenza_mese": "2026-01-01",
        "stadi": [
          { "stadio": "FATTURATA", "n_attivita": 7, "valore": "3000.00",
            "valore_fatturato": "3000.50", "valore_display": "3000.50",
            "n_in_ritardo": 1, "valore_in_ritardo": "100.00",
            "n_residui": 0, "valore_residui": "0",
            "n_trattenute": 0, "valore_trattenuto": "0",
            "n_fatture": 2, "n_fatture_stato": "OK",
            "stati_fattura": [
              { "stato_fattura_codice_interno": "DRAFT",
                "stato_fattura_codice": "DRAFT", "n_attivita": 3,
                "valore": "1000.00", "valore_fatturato": "990.00",
                "n_in_ritardo": 1, "valore_in_ritardo": "100.00" }
            ] }
        ],
        "totali": { "valore_teorico": "3300.00", "valore_fatturato": "3000.50",
                    "valore_da_fatturare": "300.00", "n_in_ritardo": 1,
                    "copertura_fatturato": "3000.50",
                    "copertura_da_fatturare": "300.00",
                    "copertura_da_addebitare": "300.00",
                    "copertura_da_accreditare": "0",
                    "rettifiche_valore": "0", "rettifiche_n": 0 },
        "n_errori": 1 }
    ]
  }
}
```

- **12 mesi sempre presenti**, ognuno con i **4 stadi in ordine funnel** fisso:
  `DA_APPROVARE, DA_EMETTERE, EMESSA_NON_FATTURATA, FATTURATA` (completamento a
  griglia nel service, stesso contratto D-5 della dashboard 5-card). Eventuali
  stadi **fuori whitelist** emessi in futuro dalla vista vengono **accodati dopo
  i 4 noti**, mai persi in silenzio (fail-visible, stesso principio anti-drift
  di `config.motivi_fermo`): aggregata e drill-down non possono divergere senza
  segnale.
- **Contratto simmetrico** (concentrico DL-8): ogni cella-stadio ha sempre tutti i
  campi; `valore_fatturato` è significativo solo su FATTURATA, `n_in_ritardo`
  solo sugli stadi emessi, `stati_fattura` è popolata solo su FATTURATA (breakdown
  3a, righe nell'ordine `config.stati_doc_fiscale.ordine`).
- **Misura "fatturato" = `imponibile_riga`** (decisione DB-6, Tid 2026-07-06):
  la regola vive **una volta sola nel BE** come `valore_display` per cella
  (= `valore_fatturato` su FATTURATA, teorico `valore` altrove) e nel blocco
  `totali` del mese (`valore_teorico` / `valore_fatturato` /
  `valore_da_fatturare` = teorico dei non fatturati / `n_in_ritardo`). Il FE
  rende `valore_display` e `totali` senza scegliere la misura. Importi
  serializzati come stringhe.
- `n_trattenute` / `valore_trattenuto`: la quota della cella trattenuta da un
  giro ancora in corso (simmetrico: `0` dove non si applica).
- `n_fatture`: quante **fatture** (non attività) nella cella; `n_fatture_stato`
  dice perché il numero c'è o no — `OK` (valorizzato, anche `0`),
  `NON_APPLICABILE` (`n_fatture: null`: stadio senza documento, cioè
  `DA_APPROVARE`/`DA_EMETTERE`, o cella vuota), `ERRORE` (`null`: il conteggio
  doveva riuscire e non è riuscito). Si calcola su `FATTURATA` ed
  `EMESSA_NON_FATTURATA`.
- `totali.copertura_*`: la copertura in **valore assoluto** (niente si
  compensa): `copertura_fatturato`, `copertura_da_fatturare` e le sue due voci
  `copertura_da_addebitare` + `copertura_da_accreditare` (=
  `copertura_da_fatturare`). I tre totali netti restano invariati.
  `rettifiche_valore` / `rettifiche_n`: le rettifiche (note di credito) del mese.
- `n_errori` = errori vivi del mese (blocco 4), per semaforo/badge senza seconda
  chiamata.

#### `n_residui` / `valore_residui` — la quota che chiede un'azione (2026-08-27)

⭐ **La card dice DUE cose, e sono due perché hanno rimedi opposti.** Dentro
`EMESSA_NON_FATTURATA` convivono **tre** situazioni (dimensione
`motivo_non_fatturata`, changeSet `20260826-54`; tre valori dal `20260912-36`
— il perché sta nel manuale della vista,
[vw_dash_competenza_attivita](../../../dbzero/vendite/manual/vw_dash_competenza_attivita.md)):
il **RESIDUO** — rimasto senza fattura, e nessun giro lo riprende da solo —
chiede un'azione («Riporta da emettere»); le altre due (`GIRO_IN_CORSO`,
`SENZA_ATTIVITA_FATTURABILE`) sono transito o anomalia, e non chiedono niente.
⭐ Il patto con le etichette del frontend (`motivo_<codice>`, chiave costruita
e quindi invisibile a `check_i18n_keys`) è presidiato nei due versi da
`apps/vendite/tests/db/test_motivo_non_fatturata_locale.py`, su DB provvisto.
Un numero solo per rimedi opposti **era il difetto**.

- `n_residui` — le attività della cella con `motivo_non_fatturata = 'RESIDUO'`.
- `valore_residui` — il loro valore, **NETTO** (con segno).
- La differenza `n_attivita − n_residui` è il transito legittimo: **non si
  tocca**.

⛔ **`valore_residui` è netto e NON assoluto**, e non è un dettaglio: viene reso
**sotto** `valore_display` della stessa cella — che è netto — e **sopra** una
lista che mostra il valore di riga col segno. Con l'assoluto un residuo di
**RETTIFICA** — e il verbo li tocca eccome, nessuna whitelist su
`tipo_movimento` — direbbe «di cui 1 · 500,00 €» sotto un totale di
**−500,00 €**: due metà che non si sommano al tutto, e chi guarda non ha modo di
capire quale delle due mente. L'assoluto ha **una sede sola** in questa
risposta ed è il blocco `copertura_*` dei `totali`, dove non compensare è
proprio il punto.

⭐ **Contratto simmetrico** come il resto della cella (DL-8): i due campi ci sono
su **ogni** stadio e valgono `0` dove non si applicano — il frontend rende, non
deduce quali stadi ce l'abbiano. Il discriminante lo calcola la **vista**, con lo
stesso `IS DISTINCT FROM` di `script.fn_check_attivita_riportabile_da_emettere`:
ricalcolarlo in Python sarebbe una seconda implementazione, e la divergenza
sarebbe silenziosa — la card conterebbe un perimetro e la lista ne mostrerebbe
un altro.

⚠️ Il conteggio **non si deduce sommando la lista dei residui**: quella è
paginata, e sommare la pagina darebbe un parziale con l'aspetto di un totale.

### Drill-down attività

Envelope paginato standard (`count/page/page_size/total_pages/results`); ogni riga:
chiavi (`commessa_attivita_id`, `commessa_id`, `commessa_codice`),
`cliente_display`, articolo decodificato via JOIN (`articolo_id`,
`articolo_codice`, `articolo_descrizione`), `data_attivita`, `quantita`, `stadio`,
assi grezzi (`stato_approvazione`, `stato_emissione`), `valore`,
`data_emissione` (= `attivita_fatturabili.data_insert`, DL-5), `emessa_in_ritardo`
(NULL se non emessa), flag AF (`sospesa`, `posticipa_al`), aggancio fattura
(`fattura_id/anno/serie/numero`, `stato_fattura_codice_interno/codice`,
`valore_fatturato`, `fattura_critical`), `lotto_id`. Nessun `registro_id` /
`registro_non_risolvibile` (campi e filtro esistono solo su `gruppi/`).
Ordinamento: default `valore DESC NULLS LAST, commessa_codice,
commessa_attivita_id`; con `order_by`/`order_dir` (vedi Input) l'ORDER BY diventa
`<colonna whitelist> ASC NULLS FIRST | DESC NULLS LAST` + tiebreak
`commessa_codice ASC, commessa_attivita_id <stessa direzione>` — colonna e
direzione **whitelistate** (mai input grezzo).

### Drill-down per commessa (aggregato)

Envelope paginato standard; `count` = numero di **commesse** distinte. Ogni riga:
`commessa_id`, `commessa_codice`, `cliente_display`, `n_attivita` (COUNT),
`n_in_ritardo` (COUNT FILTER `emessa_in_ritardo`), `valore_tot` (SUM `valore`),
`valore_fatturato_tot` (SUM `valore_fatturato`), `data_attivita_min` /
`data_attivita_max` (MIN/MAX), `emittente_ragione_sociale`. Importi/date serializzati come stringhe (NULL
preservato). Ordinamento: default `valore_tot DESC NULLS LAST, commessa_codice,
commessa_id`; con `order_by`/`order_dir` colonna **aggregata** whitelistata +
stesso tiebreak.

### Gruppi fatturabili

Envelope paginato standard **più** la chiave `riepilogo` — i totali di TUTTO il
perimetro, non della pagina: `n_gruppi`, `n_attivita`, `valore`,
`n_gruppi_oneri`, `n_gruppi_trattenuti` (i primi quattro **escludono** i gruppi
trattenuti da un lotto ancora in gioco, che restano visibili in lista). Vengono dal DB
(`vw_dash_competenza_gruppi_riepilogo` **aggrega** la vista di dettaglio, quindi
i due numeri non possono divergere); sommare le righe della pagina corrente lato
client produrrebbe un parziale con l'aria di un totale.

Ogni riga: `gruppo_key`, `tipo_gruppo` (`codice_interno` della sorgente, oppure
`ONERI_COMMESSA`), `documento_apribile` (dal 2026-10-20 al posto di
`area_documento`, il plurale ritirato: vero quando il documento ha una sua pagina,
che si apre da `tipo_gruppo`; `null` sugli oneri), `riferimento` (numero leggibile del
documento, o la commessa per gli oneri), `documento_id`,
`commessa_id/commessa_codice`, `cliente_display`, `stadio`, `n_attivita`,
`valore`, `ha_oneri`, `data_attivita_min` / `data_attivita_max`, `registri_n`,
`registro_codice`, `data_documento_prevista`, `respinta_il`, `respinta_motivo`,
`commessa_emittibile`, `commessa_stato_codice_interno` /
`commessa_stato_descrizione`, `ba_codice_fatturazione`, `id_fiscale`,
`emittente_ragione_sociale` e l'esito dell'ultimo tentativo (`ultimo_esito`,
`ultimo_errore_*`, `ultimo_lotto_codice`).

Oltre a `riepilogo`, la risposta porta le facet `tipi`, `clienti`
(`ba_fatturazione_id`, `cliente_display`, `ba_codice_fatturazione`,
`id_fiscale`, `n_gruppi`, `n_attivita`; `ba_fatturazione_id: null` = cliente
non determinabile), `registri` e `n_gruppi_perimetro` — tutte sul perimetro
**base** (mese + stadio), non sui filtri. L'export restituisce le sole righe.

#### ⭐ `respinta_il` / `respinta_motivo` — la bandiera della commessa respinta

Dal **2026-09-04**. Un giro di fatturazione può aver **rifiutato** la commessa a
cui il gruppo appartiene: il pull la salta, il task chiude in `ERRORE` con
`E_PULL_COMMESSA`, e il lavoro resta lì. Fino a questa data la riga non lo
diceva — mostrava lavoro «da emettere» del tutto ordinario — e il motivo viveva
solo nel log del lotto, a due click da chi deve agire.

- `respinta_il` (ISO 8601, `null` = nessun rifiuto noto): **l'ultimo** rifiuto
  di quella commessa **in quel mese di competenza**;
- `respinta_motivo` (`null` se `respinta_il` è `null`): il **motivo di dominio**,
  per esempio *«ROOT source mancante per commessa 34137»*. Non è un dump
  tecnico: è ciò che il pull scrive in `meta->>'detail'` sul log di lotto, e la
  stessa stringa che serve `vendite.vw_dash_commesse_respinte`.

⛔ **Le due colonne NON sono in `vw_dash_competenza_gruppi`**, e non è un
dettaglio realizzativo che il client possa ignorare: non sono ordinabili né
filtrabili, e non esistono nell'export della lista. Arrivano da una **seconda
lettura** su `vendite.vw_dash_commesse_respinte`, ristretta alle commesse della
**pagina** servita.

ℹ️ Perché così e non con una `LATERAL` nella proiezione, che sarebbe stata la
forma ovvia: `query_paged_view` materializza la CTE per contare il totale,
quindi una LATERAL si sarebbe valutata su **tutto il perimetro del mese** e non
sulla pagina. Misurato il 2026-09-04 su `2026-06` (48 gruppi): **27 ms senza,
1073 ms con**, e in crescita con lo storico perché la chiave del join esce da un
`jsonb` che nessun indice copre. Con la seconda lettura la stessa risposta costa
**0,4 ms**.

⚠️ Il filtro sul **mese** non è ridondante: senza, un rifiuto di agosto
accenderebbe la bandiera su una riga di settembre — un allarme vero su un lavoro
che non c'entra.

#### ⭐ `riferimento` è NOT NULL, e `documento_id` esce dalla sua stessa riga

**`riferimento` non è mai `null`**, ed è un contratto della vista, non una
fortuna dei dati: è `COALESCE(numero del documento, codice commessa,
gruppo_key)` e l'ultimo ramo è la chiave del gruppo, che esiste sempre.

⛔ **Quindi il client non deve rimettere quella catena.** Un
`riferimento || commessa_codice || gruppo_key` lato client ripete i due rami di
coda del `COALESCE`: sono **irraggiungibili per costruzione**, non «rari». Fino
al 2026-09-01 il campo era dichiarato opzionale in `DashCompetenzaGruppoRow` e
una copia della catena viveva davvero nel frontend; entrambe sono state tolte
insieme, perché era la dichiarazione a legittimare la copia.

**`documento_id`** è `null` **solo** sui gruppi la cui sorgente non è un
documento sfogliabile (`config.sorgenti.area IS NULL`: oneri di commessa,
attività). È l'id con cui il client apre il drawer; quando c'è, `riferimento` è
il numero di **quel** documento — codice e id non possono descrivere oggetti
diversi, perché escono dalla stessa risoluzione.

⚠️ **Cambio di sorgente (2026-09-01, `20260901-04/-05`).** Le due colonne
arrivano ora da `vendite.fn_get_sorgente_documento_ref(sorgente_tipo_id,
sorgente_uid)` — una lettura sulla tabella dichiarata da
`config.sorgenti.target_table` — e non più da una `LEFT JOIN LATERAL` su
`vw_dash_fatturazione_documenti`. **Il contratto HTTP non cambia**: nome, tipo e
posizione dei campi sono identici, nessun adeguamento client richiesto.

⭐ **Cambia però cosa si vede su una classe di righe**, e va saputo per non
leggerlo come un difetto nuovo: sui gruppi la cui sorgente era **esclusa** dai
resolver della fatturazione — preventivo superato da una revisione, DDT con
causale non fatturabile — prima usciva il **codice commessa** al posto del numero
e `documento_id` era `null` (quindi niente azione «apri»). Ora esce il numero e
l'id c'è. ⭐ Per un preventivo l'id è quello della **revisione spinta**, non della
corrente: è quella da cui vengono quantità e prezzi che si stanno per fatturare.
A video il testo è identico nei due casi (il numero è condiviso fra le
revisioni): cambia solo il bersaglio dell'azione.

⚠️ **La ricerca libera su `riferimento` resta NON indicizzata.** Il costo per
riga è molto minore, ma la sua natura non è cambiata: resta un `COALESCE` il cui
primo ramo si risolve per riga, quindi valutato su tutto il perimetro prima di
poter filtrare. Il rimedio non è spegnere la colonna a catalogo — è ancorare
la ricerca alla sorgente del documento, ed è un cantiere aperto (DL-2).

Il blocco **`tipi`** è la *facet* del filtro: le voci realmente presenti nel
perimetro con il conteggio (`tipo_gruppo`, `documento_apribile`, `n_gruppi`,
`n_attivita`), ordinate per numerosità.

> ⚠️ **Tre blocchi, due perimetri diversi, ed è voluto.** `results` e
> `riepilogo` **seguono** `tipo_gruppo` (i totali riconciliano la lista che
> l'utente sta guardando); `tipi` **no** — deve mostrare tutte le voci anche
> quando una è selezionata, altrimenti scegliendo «Preventivi» le altre
> sparirebbero dalla tendina e non si potrebbe più cambiare idea.

> ⚠️ **Perché la facet e non un lookup su `config.sorgenti`.** Quella tabella
> ha 15 righe, di cui 5 `*_RIGA` con `scope = ROW_VALIDATOR` più
> `FATTURA`/`ATTIVITA`/`RESO_VENDITA`: sorgenti che non possono mai essere un
> gruppo fatturabile — offrire opzioni da zero risultati è peggio di nessun
> filtro. E soprattutto **non contiene `ONERI_COMMESSA`**, che è un valore
> sintetico della vista: proprio il caso che si vuole poter isolare.

#### Il sezionale previsto e la data prevista (2026-08-26)

Tre campi che rispondono alla domanda «su quale registro finirà, e con che
data», **prima** che il documento esista.

⭐ **Non sono una previsione parallela.** La vista li calcola con
`fn_resolve_registro_documento`, che dal 2026-08-26 è la **stessa** funzione con
cui `fn_build_fattura_key` scrive la chiave del documento vero: lista e
documento non coincidono perché due implementazioni si comportano uguale, ma
perché è un'implementazione sola. Brief:
`dev/work-done/brief-db-registro-e-data-prevista-in-competenza.md`.

| Campo | Cosa dice |
| --- | --- |
| `registri_n` | quanti sezionali tocca il gruppo |
| `registro_codice` | il codice, quando è **uno solo** |
| `data_documento_prevista` | la data che il documento porterebbe |

⚠️ **`registro_codice` è vuoto in DUE casi diversi**, e vanno distinti col
conteggio, non fra loro:

- `registri_n > 1` → il gruppo tocca **più** sezionali. Non è «non lo so», è
  «sono più di uno», ed è ammesso **per costruzione**: la chiave del gruppo non
  contiene tipo documento né natura, che sono colonne **di riga**;
- `registri_n <= 1` → il sezionale **non è risolvibile** (tipo documento non
  ancora scelto: il `CHECK` lo pretende solo da riga approvata e non emessa).

⛔ **La lista degli id NON esce nel payload.** Serve al `WHERE` del filtro e alla
facet, che vivono entrambi nel repository. Esporla obbligherebbe a decidere che
farne dei NULL che `array_agg(DISTINCT)` conserva: tenendoli è una lista
scomoda, togliendoli diverge da `registri_n` che invece li conta — e due numeri
che rispondono «quanti sezionali» in modo diverso sono peggio di uno solo.

⚠️ **La frase «Più sezionali (N)» la scrive il BACKEND** dentro
`registro_codice`, ed è una deroga consapevole (D-4): il progetto compone le
etichette nel frontend via i18n, ma l'export condivide questa proiezione e legge
i valori grezzi, senza passare da nessuno slot — un export che tace dove la
lista parla è peggio di un export in una lingua sola. Il **frontend non legge
quella stringa**: ricompone la propria da `registri_n`, quindi a video resta
bilingue, e le due non possono divergere perché dipendono dallo stesso numero.

⚠️ **`data_documento_prevista` è vuota dove il documento esiste già** (D-9), e
il discriminante è la **riga di fattura**, non lo stadio: un gruppo
`EMESSA_NON_FATTURATA` un documento non ce l'ha ancora.

ℹ️ Le due colonne di catalogo sono `ui.lista_colonna` **553** e **554** (lista
42) e sono **accese nel preset di sistema** (`ui.lista_preset_colonna`, 2026-08-26,
insieme alle tre che erano rimaste spente: codice BA, id fiscale, emittente).
La vista predefinita della lista è quindi di **13 colonne**.

⚠️ **Accendere una colonna è sicuro solo se qualcuno la serve.** Una colonna
accesa e non proiettata dal repository non dà nessun errore: si spunta e resta
**vuota su tutte le righe** — peggio di una spenta, perché sembra un dato
mancante invece di una configurazione. Per queste due la proiezione (BE-1) e la
whitelist di ordinamento (BE-2) sono arrivate **prima**.

ℹ️ Ciò che finisce nell'export sono le colonne **visibili ed esportabili della
preferenza dell'operatore**, non un elenco fisso: chi si è spento una colonna
non la trova nel file, ed è la preferenza che comanda.

#### Il filtro per sezionale

`registro_id` (int) e `registro_non_risolvibile` (bool), **alternativi** come la
coppia del cliente: il secondo vince e non si somma al primo.

⛔ **Il filtro lavora sull'INSIEME dei sezionali del gruppo, non sul codice.** È
la decisione portante: un gruppo multi-sezionale ha `registro_codice` NULL,
quindi un filtro sul codice lo farebbe sparire da **entrambe** le voci — cioè
proprio il gruppo che si sta cercando. Con l'insieme compare sotto ognuna.

⚠️ Il predicato di «non risolvibile» **non** è `cardinality(...) = 0`:
`array_agg(DISTINCT)` conserva i NULL, quindi un gruppo interamente non
risolvibile ha `{NULL}` — cardinalità **1** — e con quel predicato non lo
troverebbe nessuno. Misurato, non assunto.

Il blocco **`registri`** è la facet corrispondente (`registro_id`, `codice`,
`descrizione`, `n_gruppi`, `n_attivita`), stesso perimetro base delle altre due.

⚠️ **La somma degli `n_gruppi` può SUPERARE i gruppi del perimetro.** Non è un
errore di conteggio: è cosa significa «un gruppo sta su due sezionali» — ed è lo
stesso motivo per cui il filtro lo trova sotto entrambi.

⭐ Da qui la chiave **`n_gruppi_perimetro`**: quanti gruppi ha il perimetro
**base**, e serve solo alla voce «Tutti i sezionali» della tendina. Non si
ricava da nessuna delle due fonti già presenti — sommare la facet **sovrastima**
(appartenenza multipla), e `riepilogo` **segue i filtri**, quindi scelto un
sezionale la voce «Tutti» direbbe *32* di un'opzione che, premuta, ne mostra
*39*.

ℹ️ La facet dei **clienti** non ha questo problema e infatti somma le proprie
voci: lì ogni gruppo sta sotto una voce sola. La differenza non è fra le due
tendine, è fra **partizione** e **appartenenza multipla**.

> ⚠️ **La `gruppo_key` è un contratto, non un'etichetta**: è la stessa stringa
> che `POST /vendite/fatturazione/run/` accetta nel campo `gruppi`. Non va
> costruita, derivata o normalizzata dal client — la costruisce
> `vendite.fn_build_gruppo_fatturabile_key`, unica fonte di verità.

### Residui

```json
{
  "data": {
    "count": 5, "page": 1, "page_size": 25, "total_pages": 1,
    "results": [
      {
        "attivita_fatturabile_id": 1123,
        "commessa_attivita_id": 551, "commessa_id": 322,
        "commessa_codice": "CMM-20260710145604304-c6a64e",
        "cliente_display": "Azienda ConTutto",
        "articolo_codice": "ONERE_PENALE", "articolo_descrizione": "…",
        "competenza_mese": "2026-07-01", "data_attivita": "2026-07-10",
        "quantita": "1.000000", "valore": "5000.0000000000000000",
        "lotto_provenienza_id": 603, "lotto_provenienza_codice": "LTF-0000679",
        "motivo_non_fatturata": "RESIDUO",
        "emittente_ragione_sociale": "…"
      }
    ]
  }
}
```

⭐ **`attivita_fatturabile_id` è la chiave del verbo e NON è a catalogo**: si
proietta ma non si mostra. È ciò che si passa a
`vendite.fn_riporta_attivita_da_emettere`. ⚠️ Toglierlo dalla proiezione
lascerebbe una lista che si può guardare e non azionare.

⛔ **`lotto_provenienza_*` non è `lotto_id`.** Quello nasce dalla catena della
**fattura**, e su un residuo la fattura non c'è: sarebbe `NULL` proprio sulle
righe di questa lista. Il legame vero è `af.lock_batch_id`.

ℹ️ `motivo_non_fatturata` su questa lista vale sempre `RESIDUO` (è il filtro).
Esce nel payload perché la colonna è a catalogo e finisce nel file di export,
dove dichiara di che natura sono le righe che si stanno leggendo.

### Errori vivi

Envelope paginato standard; ogni riga: `tipo_evento`
(`TASK_ERRORE | FATTURA_CRITICA`), `competenza_mese`, `lotto_id/lotto_codice/
stato_lotto`, `fattura_id/anno/serie/numero`, `task_code`, `error_code`,
`messaggio`, `data_evento`, `commesse_fallite`, `n_commesse_fallite`,
`emittente_ragione_sociale`.
Ordinamento: `data_evento DESC NULLS LAST` di
default, oppure la colonna scelta via `order_by` (vedi Input), sempre seguita
dal tiebreaker deterministico su **chiavi naturali** — `tipo_evento, lotto_id,
fattura_id, task_code` — perché la union **non ha una PK**.

⚠️ Per lo stesso motivo quel tiebreak **non segue la direzione** della colonna,
a differenza delle altre liste (regola 2026-08-03): non è uno spareggio
tecnico su una chiave univoca ma una catena di chiavi naturali. Lato FE la
riga non ha un `id` su cui riconciliare, e `DashboardCompetenzaView` compone
un `data-key` sintetico dalle stesse quattro colonne.

#### ⭐ `commesse_fallite` / `n_commesse_fallite` — QUALI commesse, non quante volte

Dal **2026-09-04** (changeSet DB `20260904-47`). Il messaggio di un
`TASK_ERRORE` del pull dice *«1 commesse su 3 in errore»* e rimanda ai log di
lotto: chi guarda il cruscotto sapeva che qualcosa era stato rifiutato, non
**su cosa agire**.

```json
{
  "tipo_evento": "TASK_ERRORE",
  "task_code": "pull_attivita_da_commessa",
  "error_code": "E_PULL_COMMESSA",
  "n_commesse_fallite": 1,
  "commesse_fallite": [
    {
      "commessa_id": 34137,
      "commessa_codice": "CMM-PGTAPEF202-2026-000000004",
      "error_code": "E_PULL_COMMESSA",
      "messaggio": "Errore emissione commessa 34137",
      "dettaglio": "ROOT source mancante per commessa 34137"
    }
  ]
}
```

- `commesse_fallite`: array JSON, **`[]`** (mai `null`) sugli eventi
  `FATTURA_CRITICA`, che commesse non ne hanno;
- `n_commesse_fallite`: intero, `0` quando l'array è vuoto.

⛔ **`n_commesse_fallite` NON va sommato al conteggio del calendario.** Il badge
del mese conta gli **eventi** — «quante volte devo aprire un lotto» — e la lista
somma già due unità diverse (`TASK_ERRORE` per (lotto × task) e
`FATTURA_CRITICA` per fattura). Aggiungerne una terza farebbe di «4» la somma di
task, fatture e commesse: un numero che non risponde a nessuna domanda.

⭐ **La sorgente è il log di lotto, non `task_run.meta`.** Il backend scrive in
`meta.commesse_fallite` solo le **prime cinque** — è dichiaratamente una traccia
per il cockpit — mentre il log ha una riga per commessa. Con sei commesse
respinte, la sesta ci sarebbe comunque.

ℹ️ Il campo `dettaglio` di ogni voce è il **motivo di dominio** che il pull
scrive sul log, non il dump dell'eccezione. Chi diagnostica trova la stringa
tecnica in `meta.context.dettaglio_tecnico` della riga di log.

## Regole

- **Stadio** = CASE della vista attività: `DA_APPROVARE` (non emessa, non
  approvata) → `DA_EMETTERE` (approvata, non emessa) → `EMESSA_NON_FATTURATA`
  (AF senza `fattura_riga_id`) → `FATTURATA`.
- ⚠️ **`EMESSA_NON_FATTURATA` non è una tappa del percorso, è un RESIDUO.** Il
  pull e la generazione righe avvengono nello **stesso step DRAFT**: un'attività
  passa da `DA_EMETTERE` direttamente a `FATTURATA`, e in condizioni normali
  quello stadio è **vuoto**. Ci si accumula ciò che ha perso la propria riga di
  fattura — tipicamente una fattura **eliminata** dopo un errore: l'AF resta
  `fatturato = t` con `lock_in_fatturazione = t`, quindi **nessun giro
  successivo la ripesca**. Misurato il 2026-08-26: 5 AF di competenza luglio
  (5.019 €) orfane della fattura 834 del lotto 603, eliminata dopo
  `E_FATTURA_NON_NUMERABILE_INCOERENTE`.
  🔴 Non esiste oggi un verbo che le rimetta in circolo: la card è a sola
  lettura e il rimedio è manuale. Chi progetta quel verbo deve azzerare
  **entrambi** i flag (`fatturato`, `lock_in_fatturazione`), non solo il primo.
- ⭐ Il verbo **«Rendi definitive»** vive sulla card `FATTURATA`, non su
  `EMESSA_NON_FATTURATA`: numera i lotti in stato `EMESSA`, cioè fatture che nel
  funnel stanno in `FATTURATA` con `stato_fattura_codice_interno = 'EMESSA'`.
  Sulla card dei residui il pulsante spariva a mese tutto fatturato — cioè
  esattamente quando serviva.
- **Void esclusi** (parità predicato `20260703-61`): attività `ANNULLATA` /
  `RIFIUTATA` (salvo `EMESSA + RIFIUTATA`) e commesse `ANNULLATA` fuori da tutte
  le proiezioni.
- **Recupero tardivo** = `date_trunc('month', af.data_insert) > competenza_mese`
  (DL-5: `data_insert` validata come data-emissione affidabile; caveat C1
  documentato nel manuale della vista).
- **Errori vivi**: task run `ERRORE` attivo non superato da un run `COMPLETATO`
  sulla stessa chiave; fatture `critical = true`. Competenza per gli errori
  fattura: lotto → mesi AF → fallback mese data fattura (DB-7). Il bucket
  mensile (conteggio e filtro) è normalizzato con `date_trunc('month', …)`:
  `fatturazione_lotti.competenza_mese` non ha un CHECK primo-del-mese e una
  competenza a metà mese renderebbe l'errore invisibile alla griglia.
- **Scope emittente — interamente DB-side** (DB-8): le tre viste applicano il
  filtro `script.fn_get_emittenti_scope_sr_ids(app.current_user_id)` da GUC,
  fail-closed (senza GUC ⇒ 0 righe). Il BE **non** passa alcun `auth_user_id`.
- GET-only, nessun side-effect, nessuna Idempotency-Key.

## Dipendenze DB

- `vendite.vw_dash_competenza_attivita` — doc:
  `docs/it/dbzero/vendite/manual/vw_dash_competenza_attivita.md` (incluso caveat
  C1 e GUC fail-closed)
- `vendite.vw_dash_competenza_mensile` — doc:
  `docs/it/dbzero/vendite/manual/vw_dash_competenza_mensile.md`
- `vendite.vw_dash_competenza_errori` — doc:
  `docs/it/dbzero/vendite/manual/vw_dash_competenza_errori.md`
- `vendite.vw_dash_competenza_gruppi` + `vw_dash_competenza_gruppi_riepilogo`
  (emissione mirata) — doc:
  `docs/it/dbzero/vendite/manual/vw_dash_competenza_gruppi.md`
- `config.stati_doc_fiscale` (decode etichetta + ordine breakdown 3a)
- `catalogo.articoli` (decode articolo nel drill-down)
- Indice `ix_attivita_fatturabili_competenza_mese` (migration `20260706-14`)

## Note di migrazione

- Substrato DB applicato con migrations `20260706-01..15` (pgTAP
  `test-vw-dash-competenza-v1.sql` plan 15 verde). L'eventuale futura
  materializzazione dell'aggregata non cambia il contratto verso questi endpoint.
- Test: `apps/vendite/tests/api/test_dashboard_competenza_api.py` (14 casi) +
  `apps/vendite/tests/services/test_dashboard_competenza_service.py` (18 casi),
  tutti con mock (CI-safe).
- FE (Fase 1): rotta `/vendite/dashboard-competenza`
  (`DashboardCompetenzaView.vue`, store `dashboardCompetenza.js`).
- **Emissione mirata (2026-07-27)**: aggiunto `gruppi/` sopra le viste
  `20260727-18/19`. Additivo: i quattro endpoint preesistenti sono invariati.
  Brief: `dev/work-done/brief-be-fe-emissione-fattura-mirata.md`.
- 2026-10-21: le cinque liste (`attivita/`, `commesse/`, `gruppi/`, `residui/`,
  `errori/`) leggono la finestra come `limit`/`offset` (`pagina_da_query`);
  `page`/`page_size` in query diventano un 400. Envelope invariato.
