# API giornale — il giornale trasversale degli eventi (Django)

## Scopo

«**Cosa è andato storto, su tutto, nell'ultimo periodo**»: la Storia di tutte
le entità insieme, filtrata per gravità, con il salto al lotto e al documento.
È la «vista errori trasversale (non legata al mese di competenza)» del Passo B
di [analisi-osservabilita-log](../../../dev/work-done/analisi-osservabilita-log.md),
scritta come pezzo **G** del
[piano BE/FE dell'osservabilità](../../../dev/work-done/piano-be-fe-osservabilita-pallino-e-superfici.md) §3.

## Contesto

**Terzo lettore** di `script.vw_giornale_entita` — la vista che cuce i quattro
registri di evento (`EVENT_LOG`, `LOTTO_LOG`, `TASK_RUN`, `FATTURA_LOG`) in una
forma normalizzata — sullo **stesso corpo** dei due lettori per entità
(`VenditeRepository._list_giornale`): non un aggregato nuovo. Il perimetro qui
non è un'entità ma un insieme di filtri, ed è la ragione per cui quel corpo
riceve il perimetro come SQL + parametri.

Tre layer: `ApiGiornale` / `ApiGiornaleExport` (`apps/vendite/api/views.py`),
`get_giornale_trasversale` (`vendite_service.py`),
`VenditeRepository.list_giornale_trasversale` + `_aggiungi_entita_display`.

📌 Il lettore vive ancora in `vendite` (tre lettori, un dominio): «al secondo
dominio va in `core`» — il prossimo (pratiche) lo sposta.

## Input

### `GET /api/v1/vendite/giornale/` (`DomainAPIView`, area `vendite`, `lista_codice = "vendite.giornale"`)

| Query param | Tipo | Note |
| --- | --- | --- |
| `gravita` | csv di `ERROR` \| `WARN` \| `INFO` | default `ERROR`. ⚠️ Con `ERROR` si **include** la gravità `NULL` — la riga che dichiara un difetto («un vincolo si è allargato e la mappa è rimasta indietro»), come nel pannello lotto. Fuori vocabolario → `400 E_VENDITE_VALIDATION` (`context.field = "gravita"`) |
| `registro` | csv di `codice_interno` di **`config.registri_giornale`** (al 2026-09-19: `EVENT_LOG`, `LOTTO_LOG`, `TASK_RUN`, `FATTURA_LOG`) | default tutti; fuori **catalogo** → `400 E_VENDITE_VALIDATION` (`context.field = "registro"`). ⭐ Il vocabolario si **legge dal catalogo** a ogni richiesta che porta il filtro (`VenditeRepository.registri_giornale_ammessi()`, tutte le righe, ritirate comprese): non c'è una costante nel backend — il quinto registro entra con un `UNION ALL` nella vista e una riga di CSV, e qui non cambia niente. La tendina del frontend legge lo stesso catalogo dal lookup generico (`rel=config.registri_giornale`, specializzato con `etichetta_key`). Brief: `work-done/brief-db-registri-giornale-catalogo.md` |
| `entity_type` | codice di `config.tipi_entita` | esatto (portato in maiuscolo). Fuori vocabolario → `400 E_VENDITE_VALIDATION` (`context.field = "entity_type"`); i tipi ritirati (`obsoleto_dal`) sono ammessi, il diario li porta. ⚠️ 2026-10-20: prima un codice ignoto rispondeva zero righe |
| `data_da` / `data_a` | date ISO | su `quando`, giorni **dell'azienda** (fuso `SYSTEM_FUSO_ORARIO`, confini calcolati dal DB col BB `predicato_giorno_operativo`, dal 2026-10-09), `data_a` incluso; malformate → `400`. Il floor standard lo mette il frontend |
| `filo` | uuid | `tx_id` **oppure** `correlation_id` (R-2: filtrare per filo tiene `EVENT_LOG` + `TASK_RUN` e butta le righe scritte per una persona — il default non filtra per filo). Non uuid → `400` |
| `solo_vive` | bool, default `true` | esclude le segnalazioni **ritirate**; `ritirate_count` dice quante. Strict (`qp_bool_optional`): un token non riconosciuto è un 400 |
| `order_by` | `quando` (default, DESC) \| `gravita` | `gravita` ordina il rango e, dentro, il tempo dal più recente (`_giornale_order_clause`, come sulla Storia). Fuori whitelist → **400** `E_VENDITE_VALIDATION` (un ripiego muto sulla gravità ordinerebbe la lista diversamente da come è stata chiesta) |
| `order_dir` | `asc` \| `desc` | assente ⇒ `desc` |
| `limit` / `offset` | int | paginazione offset-based, default `25` / `0`. Fuori limiti è un `400 E_VALIDATION_INPUT` (`limit` fuori da 1..200, `offset` negativo; `parse_list_params` → `pagina_da_query`, dal 2026-10-21: prima si riportava nei limiti) |

### `GET /api/v1/vendite/giornale/export/?formato=csv|xlsx`

Stessi filtri e ordinamento; `lista_codice = ApiGiornale.lista_codice`.

## Output

Envelope paginato standard + **`ritirate_count`**:

```json
{
  "riga_key": "LOTTO_LOG:10299", "registro": "LOTTO_LOG",
  "quando": "2026-09-12T13:52:15.031304+00:00", "gravita": "ERROR",
  "cosa": "Errore emissione commessa 36984", "etichetta_key": null,
  "tx_id": "01a095e3-…", "correlation_id": null,
  "auth_user_id": null, "user_insert": "tid", "ritirata": false,
  "entity_type": "LOTTO", "entity_id": 13568, "entita_display": "LTF-0011071"
}
```

- Le colonne sono **quelle della Storia** di un'entità, più **`entita_display`**
  — il codice del lotto o il **numero parlante** del documento da
  `vendite.fn_numero_documento_fattura` (la sede unica, «numero - serie»; l'id fra parentesi
  finché la bozza non ha un numero), risolto **nel backend** con una query
  sulla pagina (`_aggiungi_entita_display`). ⭐ Non un JOIN dentro la query di
  `_list_giornale`: là starebbe prima di `LIMIT`, su tutto il perimetro.
  Dal 2026-09-27 lo chiama il corpo comune, cioè anche le due Storie per
  entità — che sono la stessa lista a catalogo (`vendite.giornale`) e mostrano
  la stessa colonna «Riferimento». `TASK_RUN` e gli altri tipi restano
  `null`: il display è un'offerta.
- `cosa` è il **codice** dell'evento solo su `EVENT_LOG` (con `etichetta_key`
  da `config.eventi_dominio`, che il frontend rende con `labelOrCode`);
  altrove è già una frase. ⚠️ Il catalogo non ha una `descrizione`: il
  «`cosa_descrizione` dal catalogo» del piano è la chiave i18n che già
  viaggiava (scostamento dichiarato).
- ⛔ **Niente `context`/`payload`**: la lista è una vetrina; gli appunti
  forensi restano nella Storia dell'entità (vincolo del Passo A).
- `count` = le righe **viste** (vive, più le ritirate se `solo_vive=0`),
  dalla CTE dei conteggi sul perimetro — indipendente dalla pagina.

## Regole

- 🔒 **Il perimetro si prova, non si deduce (R-4).** La vista è
  `security_invoker`: il perimetro emittente lo applica la connessione di chi
  legge, riga per riga **e nei conteggi**. Non c'è un cancello di testata
  (non c'è *una* entità da autorizzare); la lista sta dietro il cancello di
  perimetro emittente della view (`lista_codice`). Presidio sul DB vero:
  `apps/vendite/tests/db/test_giornale_trasversale_perimetro.py` **costruisce**
  due aziende con i builder pgTAP (`dbops.fn_pgtap_crea_emittente_operatore`),
  un lotto e una riga `ERROR` ciascuna, e legge col contesto del solo primo
  operatore: la seconda non compare e `count` dice il numero visto.
- ⚠️ La lista a catalogo è `perimetro_emittente = true`, `multi_emittente =
  false`: la vista **non proietta l'emittente** della riga, quindi la lista
  non sa dire da quale azienda arriva ogni riga — su «Tutti» il cancello
  chiede di scegliere un emittente (`422`), come `vendite.fatture` e la coda
  lavori. Per certificarla `multi_emittente` serve una colonna in più nella
  vista (`emittente_soggetto_ruolo_id` nei quattro rami): richiesta al team
  DB, dichiarata nel registro del piano.
- 📐 **EXPLAIN** (fatto datato, 19-09, DB di sviluppo): i quattro registri
  hanno poche centinaia di righe vive (`event_log` 359, `lotti_log` 1.225,
  `task_runs` 616, `fatture_log` 19) e il planner sceglie **seq scan** su
  tutti i rami anche con `data_da` — la risposta giusta su tabelle così. Con
  `enable_seqscan = off` il piano è il `Merge Append` atteso da P-3 sul ramo
  `event_log` (`ix_event_log_event_time` backward); sugli altri tre rami il
  planner entra dalla **testata** (`fatturazione_lotti`/`fatture` via PK) e
  dagli indici FK dei log, non dagli indici per tempo: è la forma del JOIN di
  ancoraggio della vista, non un indice mancante. Il test 3 del presidio
  verifica che i quattro indici **esistano** e che ogni filtro si attraversi;
  **non** asserisce sul piano, che è del planner e della popolazione.
- Sola lettura; JWT + livello area `vendite` ≥ LETTURA.

## Dipendenze DB

- `script.vw_giornale_entita` (R-6: `quando` del `TASK_RUN` è `started_at`, `20260919-04`)
- `config.eventi_dominio` (etichetta i18n), `vendite.fatturazione_lotti`, `vendite.fatture` (display)
- indici per tempo `20260919-05`
- `ui.lista_*` — lista `vendite.giornale` (id 79, colonne 885-894, seed CSV)

## Frontend

`GiornaleListView` (`/vendite/giornale`, voce «Giornale eventi» accanto ai
lotti): `<ListaConfigurabile codice="vendite.giornale">`, store
`vendite/stores/giornale.js` (`useListaStoreCore` + `ritirateCount` da
`onPayload`), toolbar con `FiltroToggle` «Solo errori» (`bindToggle` con
`on = "ERROR"`, `off = "ERROR,WARN"`), select registro ed entità, campo
«Filo», filtro data standard; export. Kebab di riga: **«Apri …»** dal resolver
dei bersagli (`azioniDaBersagli`): `LOTTO` → lista lotti con `?open=`,
`FATTURA`/`COMMESSA`/… → il drawer; `TASK_RUN` senza destinazione ⇒ nessun
pulsante. ⚠️ Non c'è un'azione «Storia» separata: nessun drawer sa aprirsi su
una scheda, e «Apri» porta dove la Storia è una scheda (scostamento dal piano
§3.2, dichiarato). Il deep-link `?tx_id=` (dal registro degli errori tecnici)
si legge in `onActivated`, scrive `filo`, azzera il floor temporale e allarga
la gravità: un filo attraversa qualunque data.

## Test

- `apps/vendite/tests/api/test_giornale_trasversale_api.py` (8): porta,
  rotte, normalizzazione dei filtri, vocabolari (400), uuid/date (400),
  envelope con `ritirate_count`, niente `context`/`payload`.
- `apps/vendite/tests/db/test_giornale_trasversale_perimetro.py` (3, DB vero
  come `zeroerp_app`): il perimetro con due emittenti costruiti, il filo, ogni
  filtro attraversato + i quattro indici.
- `apps/vendite/tests/db/test_giornale_ordinamento.py` (la clausola, invariata).
- Presidi trasversali: `test_liste_configurabili_seed`,
  `test_lista_proiezione_campo_sorgente` (`entita_display` dichiarata
  `campi_da_python`), `test_perimetro_emittente_copertura`,
  `test_export_lista_codice_pari`.

## Note di migrazione

- 2026-09-19: nasce con il pezzo G. La lista è **dato** nei CSV di
  `80_data/sql/ui/`: sul DB di sviluppo compare al prossimo `db-migrate`;
  fino ad allora la rotta risponde `E_UI_LISTA_NON_TROVATA` dal cancello di
  perimetro (la lista dichiarata non esiste ancora a catalogo).
