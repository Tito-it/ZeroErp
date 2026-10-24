# API lotto_giornale (Django)

## Scopo

Rispondere a una domanda sola: **«cosa è successo a questo lotto, in che
ordine»** — il lotto **più le sue fatture**; di default le sole righe non-INFO
(«solo problemi», filtro `info`).
Elenco paginato e di sola lettura che alimenta la scheda **«Storia»** del
`LottoDrawer`.

## Contesto

Secondo (e ultimo) consumatore di **`script.vw_giornale_entita`**, la vista che
cuce i registri di evento del progetto in una forma normalizzata a sette
colonne. Sul lotto rispondono **tre** registri — `EVENT_LOG`, `LOTTO_LOG`,
`TASK_RUN` — più `FATTURA_LOG` per i documenti che contiene.

⭐ **«Il lotto più le sue fatture» è una DECISIONE** (Tid, 2026-08-24), non una
scelta di schermata: cambia il filtro, il contratto e su cosa si pagina.

Il numero che l'ha decisa, misurato sul lotto **6260**: filtrando la sola entità
`LOTTO` tornano righe che ripetono *«Esito fatture lotto · WARN»* e **non
contengono il motivo** — che sta sulla **fattura**, perché la sua entità è la
fattura (rilievo **R-3**). Un pannello onesto ma limitato al lotto sarebbe un
pannello che **nel giorno in cui serve non contiene la risposta**.

⛔ **Non era scrivibile prima del 2026-08-24, 19:33.** Qui i registri sono tre, e
con l'orario di **transazione** (`now()`) tutte le righe scritte nella stessa
transazione uscivano con lo **stesso istante**: una timeline che mostra una
sequenza **mai avvenuta** — e che guardandola non sembra rotta. È il rilievo
**R-1**, chiesto dal BE e risolto dal team DB con `clock_timestamp()`
(changeSet `20260824-16`, `-17`, `-18`).

⛔ **Da non confondere con `/segnalazioni/`**, che elenca i problemi **aperti** da
risolvere: qui c'è anche ciò che è andato bene e i tentativi poi superati.

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/vendite/lotti/{lotto_id}/giornale/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- ⭐ **Dal 2026-09-27 è la lista a catalogo `vendite.giornale`** (la stessa
  della Storia della fattura e del giornale trasversale, decisione di Tid,
  [brief-db-liste-datatable-grezze §3.1](../../../dev/work-done/brief-db-liste-datatable-grezze.md)):
  contratto di lista standard, dichiarato una volta per le due Storie in
  `apps/vendite/api/_giornale_params.py`. Il vecchio contratto
  (`page`/`page_size`/`sort_by`/`sort_dir`) non è più letto.
- Query param (tutti opzionali):
  - `limit` (int, default `25`, max `200`) · `offset` (int, default `0`).
    Fuori limiti è un `400 E_VALIDATION_INPUT` (`limit` fuori da 1..200,
    `offset` negativo; `parse_list_params` → `pagina_da_query`, dal 2026-10-21:
    prima si riportava nei limiti)
  - `order_by` — `quando` (default, il preset) | `gravita`. Fuori whitelist → **400**
  - `order_dir` — assente = `desc` | `asc`
  - `emittente_soggetto_ruolo_id` — l'emittente del lotto, `lista_emittente_param`
    della view: scioglie il cancello di perimetro della lista per chi ha più
    emittenti nello scope. Non filtra le righe (il perimetro è il lotto del path)
  - `info` (bool strict, default `false`) — include le righe di routine: è il
    filtro «solo problemi», proprio della Storia del lotto
  - `ritirate` (bool strict, default `false`) — include le segnalazioni ritirate

## Output

```json
{"data": {"lotto_id": 6260, "count": 113, "page": 1, "page_size": 25,
          "total_pages": 5, "ritirate_count": 2, "info_count": 173,
          "results": [...]}}
```

Ogni riga porta `riga_key`, `registro`, `quando`, `gravita`, `cosa`,
`etichetta_key`, `tx_id`, `correlation_id`, `auth_user_id`, `user_insert`,
`ritirata`, **`entity_type` / `entity_id`** e — dal 2026-09-27, per tutti e
tre i lettori — **`entita_display`** (il codice del lotto o il numero del
documento: la colonna «Riferimento» della lista a catalogo).

⭐ **`etichetta_key` (dal 2026-08-31)** è l'indirizzo i18n del fatto
(`config.eventi_dominio`), valorizzato per le sole righe **`EVENT_LOG`** — là
`cosa` è il **codice** dell'evento; sugli altri tre registri è già una frase e il
campo è `null`. Si rende con `labelOrCode(t, te, etichetta_key, cosa)`, ripiego
sul codice grezzo. Contratto e storia nel gemello
[api_fattura_giornale.md](api_fattura_giornale.md): i due endpoint leggono lo
stesso `_list_giornale`, quindi il campo è comparso su entrambi in un colpo solo.

⭐ **`entity_type` non è un accessorio**: è l'informazione che rende utile il
pannello. Senza, *«il lotto dice che è andata male»* e *«la fattura 20024 dice
perché»* diventano due frasi indistinguibili nello stesso elenco.

## Regole

| Regola | Perché |
|---|---|
| **«Non-INFO» = tutto ciò che non è INFO, NULL compreso** | Il filtro gira sul **rango**, mai su `gravita IN ('WARN','ERROR')`: una gravità nulla significa «un vincolo si è allargato e la mappa è rimasta indietro», ed è esattamente la riga da non perdere. Un filtro per elencazione la butterebbe via **in silenzio** |
| **Le INFO si nascondono ma si CONTANO** (`info_count`: quelle che il filtro toglie davvero, cioè fra le righe che `ritirate` lascia passare) | Un elenco filtrato e uno completo si leggono uguali. «Tre problemi» e «tre problemi più 173 passi andati bene» sono due schermate diverse |
| **I conteggi si calcolano PRIMA dei filtri**, in una CTE | Una finestra sulla query filtrata non vedrebbe le righe nascoste — e dire quante se ne nascondono è metà del mestiere di nasconderle |
| Le INFO si contano **solo fra le vive** | Una riga INFO già ritirata sarebbe contata due volte, e i numeri a video non tornerebbero col totale |
| **Il rango di gravità si calcola in SQL** | Il vocabolario è testuale: ordinandolo per testo `ERROR` verrebbe prima di `INFO` e `WARN` — un ordine alfabetico spacciato per una scala |
| Il `NULL` pesa come un **ERROR** | Mandarlo in fondo lo renderebbe invisibile dalla seconda pagina in giù: il modo più efficace di nascondere un difetto |
| **Ordinamento e filtri sono del SERVER** | La lista è paginata: a valle si ordinerebbe la sola pagina, e «il più grave» diventerebbe «il più grave fra i primi 50» |
| Il perimetro delle fatture è una **sotto-query** | Un lotto può contenere migliaia di documenti: tradurli in un `IN (...)` da Python sarebbe un limite nascosto che si scopre il giorno del lotto grosso |

### Il cancello, e perché non è ridondante

Lotto inesistente **o fuori scope emittente** → **404 identico**
(`E_LOTTO_NON_TROVATO`), deciso da `repository.get_lotto` **prima** di leggere il
giornale.

⛔ **Non è ridondante con la RLS.** La vista non ha un perimetro emittente proprio
per le righe di entità `FATTURA`: senza il cancello un lotto altrui riceverebbe
**zero righe**, che si legge come *«lotto senza storia»* e non come *«non lo puoi
vedere»*. Misurato: la vista da sola risponde `0` righe su un id inesistente,
l'endpoint risponde 404.

## Dipendenze DB

- `script.vw_giornale_entita` (changeSet `20260822-70`)
- `vendite.fatturazione_lotti_fatture` — il perimetro dei documenti
- `vendite.fatturazione_lotti` — via `get_lotto`, il cancello
- ⛔ **R-1 è un prerequisito**, non un dettaglio: senza `clock_timestamp()` sulle
  quattro colonne di orario questo endpoint restituisce un ordine che non è
  quello dei fatti

## Correlati

- [api_fattura_giornale.md](api_fattura_giornale.md) — la stessa domanda su un
  documento. ⭐ I due condividono il corpo (`VenditeRepository._list_giornale`):
  cambia **solo** il perimetro, così gravità, conteggi e ordinamento non possono
  divergere fra le due schede
- [api_lotto_segnalazioni_summary.md](api_lotto_segnalazioni_summary.md) — i
  problemi **aperti**, che è un'altra domanda
- [api_lotto_fatture_list.md](api_lotto_fatture_list.md) — i documenti del lotto
