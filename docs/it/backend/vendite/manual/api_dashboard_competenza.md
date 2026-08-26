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
GET /api/v1/vendite/dashboard-competenza/            (ApiDashboardCompetenza)
GET /api/v1/vendite/dashboard-competenza/attivita/   (ApiDashboardCompetenzaAttivita)
GET /api/v1/vendite/dashboard-competenza/commesse/   (ApiDashboardCompetenzaCommesse)
GET /api/v1/vendite/dashboard-competenza/errori/     (ApiDashboardCompetenzaErrori)
```

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
- `registro_id` (int, opzionale) / `registro_non_risolvibile` (bool,
  opzionale) — filtro sezionale, vedi sotto. Alternativi.
- `stadio` (opzionale): `DA_APPROVARE | DA_EMETTERE | EMESSA_NON_FATTURATA |
  FATTURATA` (case-insensitive; fuori whitelist → `E_VENDITE_VALIDATION`;
  assente = tutti gli stadi).
- `solo_ritardo` (opzionale, bool): se `true` solo le attività emesse in ritardo
  (`emessa_in_ritardo IS TRUE` — recuperi tardivi, §7 del design).
- `order_by` / `order_dir` (opzionali): **ordinamento colonne server-side**
  (convenzione delle liste standard). `order_by` in whitelist —
  `commessa_codice` | `cliente_display` | `articolo_codice` (ordina per la
  descrizione **mostrata**, `COALESCE(art.descrizione, art.codice)`) |
  `data_attivita` (default; ordina per la **colonna data**, non per la stringa
  gg/mm/aaaa del FE) | `valore`; `order_dir` = `asc` | `desc`. Server-side
  perché la lista è paginata: ordine corretto su **tutte** le pagine. Colonna
  fuori whitelist o direzione ≠ asc/desc → 400 (`E_VENDITE_VALIDATION`). Tiebreak
  stabile `(commessa_codice, commessa_attivita_id)`.
- `page` / `page_size` (opzionali): paginazione standard (default 1/50, max 200).

### `GET /dashboard-competenza/commesse/`

Stesso perimetro e stessi filtri di `attivita/` (`competenza_mese` obbligatorio,
`stadio`, `solo_ritardo`, `page`/`page_size`), ma **aggregato per commessa**.

- `order_by` / `order_dir` (opzionali): whitelist **aggregata** —
  `commessa_codice` | `cliente_display` | `n_attivita` | `valore_tot` (default,
  DESC) | `data_attivita_max`; `order_dir` = `asc` | `desc`. Le colonne di riga
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
- `order_by` / `order_dir` (opzionali): whitelist `riferimento` | `tipo_gruppo` |
  `cliente_display` | `commessa_codice` | `n_attivita` | `valore` (default,
  DESC) | `data_attivita_max`; tiebreak stabile su `gruppo_key`.
- `page` / `page_size` (opzionali): paginazione standard.

### `GET /dashboard-competenza/errori/`

- `competenza_mese` (opzionale, date ISO, normalizzato al 1°): assente = errori
  vivi di tutti i mesi.
- `order_by` / `order_dir` (opzionali, **dal 2026-08-03**): ordinamento
  server-side. `order_by` in whitelist — `tipo_evento` | `lotto_codice` |
  `fattura_numero` | `error_code` | `data_evento` (default); `order_dir` =
  `asc` | `desc` (default `desc`: eventi recenti prima). Era l'unica lista
  delle tre dashboard senza ordinamento. Colonna fuori whitelist o direzione
  ≠ asc/desc → 400 (`E_VENDITE_VALIDATION`, validato nel service).
  ⚠️ `NULLS LAST` esplicito su ogni colonna: metà della union non ha i campi
  di documento (un errore di task non ha fattura, una fattura critical non ha
  task), e in DESC quei NULL finirebbero in testa.
- `page` / `page_size` (opzionali): paginazione standard.

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
            "stati_fattura": [
              { "stato_fattura_codice_interno": "DRAFT",
                "stato_fattura_codice": "DRAFT", "n_attivita": 3,
                "valore": "1000.00", "valore_fatturato": "990.00",
                "n_in_ritardo": 1, "valore_in_ritardo": "100.00" }
            ] }
        ],
        "totali": { "valore_teorico": "3300.00", "valore_fatturato": "3000.50",
                    "valore_da_fatturare": "300.00", "n_in_ritardo": 1 },
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
- `n_errori` = errori vivi del mese (blocco 4), per semaforo/badge senza seconda
  chiamata.

### Drill-down attività

Envelope paginato standard (`count/page/page_size/total_pages/results`); ogni riga:
chiavi (`commessa_attivita_id`, `commessa_id`, `commessa_codice`),
`cliente_display`, articolo decodificato via JOIN (`articolo_id`,
`articolo_codice`, `articolo_descrizione`), `data_attivita`, `quantita`, `stadio`,
assi grezzi (`stato_approvazione`, `stato_emissione`), `valore`,
`data_emissione` (= `attivita_fatturabili.data_insert`, DL-5), `emessa_in_ritardo`
(NULL se non emessa), flag AF (`sospesa`, `posticipa_al`), aggancio fattura
(`fattura_id/anno/serie/numero`, `stato_fattura_codice_interno/codice`,
`valore_fatturato`, `fattura_critical`).
Ordinamento: default `valore DESC NULLS LAST, commessa_codice,
commessa_attivita_id`; con `order_by`/`order_dir` (vedi Input) l'ORDER BY diventa
`<colonna whitelist> <asc|desc> NULLS LAST` + tiebreak `commessa_codice,
commessa_attivita_id` — colonna e direzione **whitelistate** (mai input grezzo).

### Drill-down per commessa (aggregato)

Envelope paginato standard; `count` = numero di **commesse** distinte. Ogni riga:
`commessa_id`, `commessa_codice`, `cliente_display`, `n_attivita` (COUNT),
`n_in_ritardo` (COUNT FILTER `emessa_in_ritardo`), `valore_tot` (SUM `valore`),
`valore_fatturato_tot` (SUM `valore_fatturato`), `data_attivita_min` /
`data_attivita_max` (MIN/MAX). Importi/date serializzati come stringhe (NULL
preservato). Ordinamento: default `valore_tot DESC NULLS LAST, commessa_codice,
commessa_id`; con `order_by`/`order_dir` colonna **aggregata** whitelistata +
stesso tiebreak.

### Gruppi fatturabili

Envelope paginato standard **più** la chiave `riepilogo` — i totali di TUTTO il
perimetro, non della pagina: `n_gruppi`, `n_attivita`, `valore`,
`n_gruppi_oneri`. Vengono dal DB
(`vw_dash_competenza_gruppi_riepilogo` **aggrega** la vista di dettaglio, quindi
i due numeri non possono divergere); sommare le righe della pagina corrente lato
client produrrebbe un parziale con l'aria di un totale.

Ogni riga: `gruppo_key`, `tipo_gruppo` (`codice_interno` della sorgente, oppure
`ONERI_COMMESSA`), `area_documento`, `riferimento` (numero leggibile del
documento, o la commessa per gli oneri), `commessa_id/commessa_codice`,
`cliente_display`, `stadio`, `n_attivita`, `valore`, `ha_oneri`,
`data_attivita_min` / `data_attivita_max`, `registri_n`, `registro_codice`,
`data_documento_prevista`.

Il blocco **`tipi`** è la *facet* del filtro: le voci realmente presenti nel
perimetro con il conteggio (`tipo_gruppo`, `area_documento`, `n_gruppi`,
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
`dev/work-in-progress/brief-db-registro-e-data-prevista-in-competenza.md`.

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

### Errori vivi

Envelope paginato standard; ogni riga: `tipo_evento`
(`TASK_ERRORE | FATTURA_CRITICA`), `competenza_mese`, `lotto_id/lotto_codice/
stato_lotto`, `fattura_id/anno/serie/numero`, `task_code`, `error_code`,
`messaggio`, `data_evento`. Ordinamento: `data_evento DESC NULLS LAST` di
default, oppure la colonna scelta via `order_by` (vedi Input), sempre seguita
dal tiebreaker deterministico su **chiavi naturali** — `tipo_evento, lotto_id,
fattura_id, task_code` — perché la union **non ha una PK**.

⚠️ Per lo stesso motivo quel tiebreak **non segue la direzione** della colonna,
a differenza delle altre liste (regola 2026-08-03): non è uno spareggio
tecnico su una chiave univoca ma una catena di chiavi naturali. Lato FE la
riga non ha un `id` su cui riconciliare, e `DashboardCompetenzaView` compone
un `data-key` sintetico dalle stesse quattro colonne.

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
