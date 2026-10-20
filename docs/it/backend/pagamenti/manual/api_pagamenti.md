# API pagamenti (Django)

## Scopo

Esporre via HTTP il **giro degli incassi**: la **distinta contabile** che
raccoglie il denaro arrivato, le sue **righe** (l'unità di allocazione),
l'**abbinamento** di ogni riga a una fattura e a una rata, la **registrazione**
(il gesto irreversibile che muove il denaro), la **base dei saldi** che dice
quanto resta da regolare a ogni livello, le **sistemazioni** di ciò che è
entrato di troppo, e i **canali di incasso** da cui il denaro arriva.

## Contesto

Famiglia di endpoint di area `pagamenti` (schema `pagamenti`, area funzionale
id 7). È il lato HTTP del cantiere «contabili di pagamento», descritto in tre
documenti che non si sovrappongono e a cui questa pagina **non si sostituisce**:

| Documento | Che cosa contiene |
| --- | --- |
| [brief-incassi-riconciliazione-rate-promemoria.md](../../../dev/work-in-progress/brief-incassi-riconciliazione-rate-promemoria.md) | le **decisioni di dominio** (D1…D15) col loro perché |
| [brief-db-posting-e-abbinamento-rata.md](../../../dev/work-done/brief-db-posting-e-abbinamento-rata.md) | il lato **database**: sette lotti, 15 guard, 2 matrici di transizione, la RLS |
| [brief-be-fe-posting-e-abbinamento-rata.md](../../../dev/work-done/brief-be-fe-posting-e-abbinamento-rata.md) | il piano **BE/FE**, le nove domande chiuse, lo stato di sviluppo |

Qui c'è **il contratto**: che cosa si chiama, che cosa si manda, che cosa
torna, e quale codice esce quando non si può.

```text
pagamenti.vendite_contabili           la DISTINTA: N importi arrivati insieme (nessun importo in testata)
  └─ vendite_contabili_righe          la RIGA: l'unità di allocazione (importo, fattura, rata, forzatura)
       └─ vendite_movimenti           il MOVIMENTO: scritto dalla registrazione, mai a mano
pagamenti.sistemazioni                l'ATTO su un'eccedenza (riporto · rimborso · compensazione)
pagamenti.enti_incasso                il CANALE: da quale conto arriva il denaro
```

🔴 **Il backend è sottile per obbligo, non per stile.** Le regole di questo
dominio — se una transizione è ammessa, se una distinta quadra, se una rata ha
capienza, che cosa si fa di un'eccedenza — vivono in **15 guard, 2 matrici di
transizione e 3 funzioni madri** dentro PostgreSQL. Il service **non le
replica**: valida la forma del payload, chiama, traduce. ⛔ Nessuna delle
condizioni descritte sotto come «rifiuta con `E_…`» è scritta in Python: è il
database che risponde, e questa pagina la riporta perché chi chiama deve
sapere che cosa aspettarsi.

⚠️ **`pagamenti.*` pretende l'operatore.** Le quattro tabelle transazionali
(`vendite_contabili`, `vendite_contabili_righe`, `vendite_movimenti`,
`sistemazioni`) e `enti_incasso` hanno la row level security accesa: senza il
contesto operatore (`app.ruolo_applicativo = 'OPERATORE'`) una lista torna
**zero righe** senza errore, e uno zero senza contesto sembra un dato. Gli
endpoint girano sempre sotto JWT, quindi il contesto c'è; la trappola vale per
chi legge queste tabelle da un canale di sistema.

⭐ **La risorsa si chiama `distinte`, non `contabili`.** Sul filo si usa la
parola che l'operatore legge sulla schermata; `vendite_contabili` è il nome
della tabella e compare solo nei codici errore, che sono del database.

## Le rotte

Tutte sotto `/api/v1/pagamenti/`. ✅ = `Idempotency-Key` obbligatoria.

| Metodo | Path | Cosa | Idem-Key | Gate |
| --- | --- | --- | :---: | --- |
| `GET`/`POST` | `distinte/` | elenco paginato · apre (o ritrova) la distinta manuale | ✅ su POST | area |
| `GET`/`PATCH` | `distinte/{contabile_id}/` | dettaglio con cataloghi e transizioni (⚠️ **senza righe** dal 18/09) · i campi compilabili | — | area |
| `POST` | `distinte/{contabile_id}/stato/` | il percorso della distinta: `VALIDATA` · `BOZZA` · `ANNULLATA` | ✅ | area |
| `GET`/`POST` | `distinte/{contabile_id}/righe/` | le righe, **paginate** (lista `pagamenti.distinta_righe`, dal 18/09), **scartate fuori di default** (`?scartate=1`, dal 19/09) · un importo arrivato, **e di chi è** (D16) | ✅ su POST | area |
| `GET` | `distinte/{contabile_id}/righe/export/` | ⭐ **la contabile in CSV/Excel** (dal 18/09): le colonne sono quelle che l'operatore vede | — | area |
| `GET` | `distinte/{contabile_id}/anteprima-registrazione/` | la fotografia di ciò che succede se si registra adesso | — | area |
| `POST` | `distinte/{contabile_id}/registra/` | ⭐ **la madre**: registra, una sola `SELECT` | ✅ | `registra_distinta` |
| `POST` | `distinte/{contabile_id}/correggi/` | la **correzione guidata**: una distinta nuova a segno opposto | ✅ | `registra_distinta` |
| `PATCH`/`DELETE` | `righe/{riga_id}/` | i **fatti** della riga (come è arrivato il denaro) · **elimina** la riga (D17, `attivo = false`) | ✅ su DELETE | area |
| `POST` | `righe/{riga_id}/stato/` | il percorso della riga | ✅ | area |
| `POST` | `righe/{riga_id}/abbina/` | fattura + cliente + rata, e la **forzatura a due tempi** | ✅ | area |
| `POST` | `righe/{riga_id}/registra/` | ⭐ **la registrazione TARDIVA** (D20-b, dal 19/09): una `SOSPESA` sotto una distinta registrata si abbina **e** si registra, stesso payload di `abbina/` | ✅ | `registra_distinta` |
| `POST` | `distinte/{contabile_id}/righe/da-rate/` | ⭐ **N rate scelte → N righe** in un Salva (D19-d), esito **per riga** | ✅ | area |
| `GET` | `righe/` | la coda del riconciliatore, cross-distinta (`?coda=`) | — | area |
| `GET` | `rate/` | ⭐ **l'elenco delle rate col saldo** (lista `pagamenti.rate`, D19-c): la sorgente del picker e dello scadenzario | — | area |
| `GET` | `rate/fuori-capienza/` | le rate uscite dalla banda: l'elenco che rende onesta la forzatura | — | area |
| `GET` | `rate/{scadenza_id}/saldo/` | la base dei saldi, livello **rata** | — | area |
| `GET` | `fatture/{fattura_id}/saldo/` | la base dei saldi, livello **documento** | — | ⚠️ `skip_area_check` |
| `GET` | `fatture/{fattura_id}/rate/` | le rate di una fattura, ciascuna col suo saldo, un giro solo | — | ⚠️ `skip_area_check` |
| `GET` | `eccedenze/` | i documenti su cui è entrato più del dovuto | — | area |
| `POST` | `sistemazioni/` | registra la **decisione** su un'eccedenza (nasce in bozza) | ✅ | area |
| `GET` | `sistemazioni/{sistemazione_id}/` | l'atto, col suo esito quando c'è | — | area |
| `POST` | `sistemazioni/{sistemazione_id}/conferma/` | l'atto diventa un fatto: il denaro si muove | ✅ | area |
| `POST` | `sistemazioni/{sistemazione_id}/annulla/` | l'atto si scarta, e resta a registro con la ragione | ✅ | area |
| `GET` | `fatture/{fattura_id}/sistemazioni/` | gli atti di un documento (paginata) | — | ⚠️ `skip_area_check` |
| `GET` | `fatture/{fattura_id}/sistemazioni/export/` | lo stesso elenco come file (`?formato=csv\|xlsx`) | — | ⚠️ `skip_area_check` |
| `GET`/`POST` | `enti-incasso/` | i canali di incasso · creazione | ✅ su POST | area |
| `GET`/`PATCH` | `enti-incasso/{ente_incasso_id}/` | il canale, col suo conto in chiaro · i campi compilabili | — | area |
| `GET` | `conti-incasso/?soggetto_ruolo_id=` | i soli conti con `uso = 'INCASSO'` di un soggetto | — | area + perimetro |

⚠️ **L'ordine in `urlpatterns` conta**: le azioni (`righe/`, `stato/`,
`registra/`, `correggi/`, …) stanno **prima** del dettaglio `distinte/{id}/`,
`righe/da-rate/` prima di `righe/` (che è `GET`/`POST` sulla collezione),
`rate/` e `rate/fuori-capienza/` prima di `rate/{id}/saldo/`. Non è un
dettaglio del file: è la ragione per cui `fuori-capienza` non viene letto come
un id.

⭐ **Perché quattro rotte su `fatture/…` stanno qui e hanno `skip_area_check`.**
Le consuma il drawer **fattura**, che vive in `vendite`: senza, per vedere se
una fattura è pagata servirebbe la LETTURA su `pagamenti`, cioè allargare un
permesso per comodità. Rispondono il **minimo su un documento già scelto** —
lo stesso pattern del lookup cross-dominio. ⚠️ E stanno qui e non in `vendite`
per un vincolo, non per gusto: le chiamate laterali fra moduli di pari livello
non sono ammesse ([api.md §Comunicazione cross-modulo](../../../dev/api.md)),
quindi `vendite` non può chiedere un saldo a `pagamenti`.

### Regole che valgono su tutte le rotte

| Regola | Dettaglio |
| --- | --- |
| Envelope | `{"data": …, "meta": {"request_id"}}`; errori nell'envelope standard di [api.md](../../../dev/api.md) |
| Paginazione | **page-based**: `page` (default 1), `page_size` (default 25, max 200). Risposta `{count, page, page_size, total_pages, results}`. ⛔ `count` viene da `COUNT(*) OVER ()` nella stessa valutazione, mai da `len(results)`. ⚠️ Le tre liste nate su `<ListaConfigurabile>` con `createListaStore` — `fatture/{id}/sistemazioni/` (02/09), `rate/` (17/09) e `distinte/{id}/righe/` (18/09) — sono **offset-based** (`limit`/`offset`, la lingua di `useSearchTable`) e rispondono `{count, results}`: la conversione per le altre la fa lo store, in un posto solo (`paramsPagina`) |
| Ordinamento | `order_by` su una **whitelist per lista** (tabella sotto) — il nome è quello **fisico** della colonna, come la lista lo espone; `order_dir` `asc\|desc`. Fuori whitelist → `400 E_PAGAMENTI_VALIDATION` |
| Query param opzionali | contratto degli helper `qp_*_optional`: vuoto = assente, malformato = `400` |
| Vocabolari a `CHECK` | `stato`, `origine`, `coda`, `motivo`, `chi_e_in_credito`, `tipo`, `destinazione`: un valore fuori vocabolario è un **400**, mai una lista vuota — su due valori possibili una lista vuota è indistinguibile da «non c'è niente», cioè dalla risposta più rassicurante |
| `Idempotency-Key` | obbligatoria su **ogni** `POST` (creazioni, verbi, cambi di stato). ⚠️ Sui `PATCH` no: passano da `request.data`, non da `handle_post_json` |
| 404 | «non esiste» e «non lo vedi» (RLS) danno la **stessa** risposta, di proposito: dire «esiste ma non è tuo» racconterebbe a chi è fuori perimetro che quel documento c'è |
| Cancello di perimetro emittente | le liste con `lista_codice` (`pagamenti.distinte`, `.righe`, `.distinta_righe` — lista **ed** export —, `.rate`, `.rate_fuori_capienza`, `.eccedenze`, `.sistemazioni_fattura`, `.canali_incasso`) passano dal cancello di [`perimetro_emittente`](../../ui/manual/api_export_liste.md): un operatore **multi-emittente** senza emittente scelto riceve `422 E_UI_LISTA_EMITTENTE_DA_SCEGLIERE`. Non è un permesso: è «scegli prima da dove guardi» |
| `search` | ricerca libera sulle colonne che il catalogo della lista accende (`ricerca_full`), su `distinte/`, `righe/`, `distinte/{id}/righe/` (+ `export/`), `rate/`, `rate/fuori-capienza/`, `eccedenze/`. Sotto la soglia della lista (`ricerca_min_caratteri`) il termine non filtra: mai un 400 |
| `?format=` | ⛔ mai: è un parametro magico di DRF e la richiesta muore con **404** prima di arrivare alla view. Il parametro dell'export si chiama **`formato`** |

**Le whitelist di ordinamento**, con il default e il suo verso:

| Lista | `order_by` ammessi | Default |
| --- | --- | --- |
| `distinte/` | `data_contabile` · `codice` · `stato_descrizione` · `origine` · `centro_descrizione` · `totale_righe` | `data_contabile` DESC |
| `righe/` | `data_pagamento` · `importo` · `stato_descrizione` · `contabile_codice` | `data_pagamento` DESC |
| `distinte/{id}/righe/` (+ `export/`) | `id` · `data_pagamento` · `data_valuta` · `data_operazione` · `riferimento_ente` · `importo` · `billing_account_descrizione` · `billing_account_codice` · `fattura_numero_documento` (coppia `(fattura_numero, fattura_serie)`, non il testo) · `scadenza_numero_rata` · `scadenza_data` · `stato_descrizione` | `id` **DESC** — ⭐ **l'ultima riga digitata in cima** (decisione di Tid del 02/09 sugli atti di sistemazione, stessa ragione: da quando la lista impagina, una riga appena scritta in ordine crescente finirebbe nell'ultima pagina); le quattro date partono DESC al primo click |
| `rate/fuori-capienza/` | `data_scadenza` · `motivo` · `residuo` · `importo_rata` · `fattura_numero` · `numero_documento` (dal 17/09: ordina per la coppia `(fattura_numero, serie)`, non per il testo) | `data_scadenza` DESC |
| `rate/` | `numero_documento` (coppia `(numero, serie)`) · `data` · `ragione_sociale_completa` · `ba_codice` · `numero_rata` · `data_scadenza` · `importo` · `totale_doc` · `stato_descrizione` — ⛔ **non** i tre saldi: non stanno nella vista, arrivano dopo la pagina | `data_scadenza` **ASC** — è una **coda**, la rata più vecchia prima; le due date hanno verso naturale DESC quando le si chiede senza `order_dir` |
| `eccedenze/` | `eccedenza_cliente` · `cliente_ragione_sociale` · `eccedenza` · `fattura_data` · `fattura_numero` | `eccedenza_cliente` DESC — ⭐ **per cliente, non per documento**: la decisione si prende guardando il cliente |
| `fatture/{id}/sistemazioni/` | `destinazione` · `importo` · `stato` · `motivo` · `data_esecuzione` | quello del repository (`data_esecuzione` DESC) |
| `enti-incasso/` | `codice` · `descrizione` · `tipo` · `centro_descrizione` | `codice` ASC |

---

## 1. La distinta

### `GET /api/v1/pagamenti/distinte/`

Elenco paginato. Filtri: `stato` (codice interno: `BOZZA` · `IMPORTATA` ·
`VALIDATA` · `CHIUSA` · `ANNULLATA`), `origine` (`MANUALE` · `GENERATA` ·
`AUTOMATICA`), `centro_riscossione_id`, `ente_incasso_id`, `data_da`/`data_a`
sulla **data contabile** (ISO; nessun floor lato backend — il default delle
liste lo applica il frontend), `search`. `stato` o `origine` fuori vocabolario:
`400 E_PAGAMENTI_VALIDATION` col campo (fino al 2026-10-20 davano una lista
vuota).

⭐ **`origine` non è un dettaglio tecnico**: dice a chi guarda se sta vedendo
il lavoro di una persona (`MANUALE`), la contabilità interna scritta dal giro
dei fondi fattura (`GENERATA`) o un import (`AUTOMATICA`).

Ogni riga è una `DistintaRow`:

```json
{
  "id": 12, "codice": "DIS-ACME-2026-0000012",
  "centro_riscossione_id": 3, "centro_codice": "BNK", "centro_descrizione": "Banca",
  "ente_incasso_id": 7, "ente_codice": "BNK-01", "ente_descrizione": "Conto incassi",
  "data_contabile": "2026-09-01", "data_registrazione": "2026-09-01",
  "stato_id": 41, "stato_codice": "BOZZA", "stato_descrizione": "Bozza", "stato_is_final": false,
  "origine": "MANUALE",
  "emittente_soggetto_ruolo_id": 72, "emittente_fiscale_id": 32,
  "emittente_fiscale_codice": "ACME", "emittente_ragione_sociale": "ACME S.r.l.",
  "registro_id": 91, "anno": 2026,
  "importo_dichiarato": "1500.00",
  "data_conferma": null, "user_conferma": null,
  "lotti_ids": null, "meta": {},
  "righe_totali": 3, "righe_registrabili": 2,
  "totale_righe": "1500.00", "totale_registrabile": "1200.00", "scarto_dichiarato": "0.00"
}
```

⚠️ **I totali sono derivati, non colonne**: si contano sulle righe **attive**
in una `LATERAL`. `totale_righe` conta tutte, `SCARTATA` compresa — quel
denaro **è arrivato**, e la quadratura chiede «ho letto tutto ciò che c'era»,
non «tutto è nostro»: è la stessa somma che il guard di validazione confronta
con `importo_dichiarato`. `scarto_dichiarato` è la differenza (`null` senza
dichiarato).

⚠️ **`lotti_ids` è al plurale, ed è una correzione**: l'unico su
`vendite_contabili_lotti` è `(lotto_id, contabile_id)`, quindi una distinta può
appartenere a più lotti; letta come valore singolo, la riga compariva **due
volte** nell'elenco e il conteggio con lei — senza nessun errore.

⭐ **Il codice viene dal registro, e la distinta sa di chi è (dal 2026-09-17,
[brief distinta-numerata-sul-registro](../../../dev/work-done/brief-db-distinta-numerata-sul-registro.md)).**
`codice` è `DIS-<SIGLA>-<ANNO>-<7 cifre>`: lo assegna il trigger sul registro
`DISTINTA` dell'emittente alla **creazione**, con l'anno dalla `data_contabile`
e il reset a Capodanno — la sesta famiglia di `vendite.famiglie_documento`, la
prima fuori da `vendite` e la prima senza billing account. La testata porta
l'emittente in **tre forme** — `emittente_soggetto_ruolo_id` (la chiave del
database), `emittente_fiscale_id` + `emittente_fiscale_codice` +
`emittente_ragione_sociale` (i nomi che `EmittenteFiscaleField` legge in
edit, gli stessi dei documenti di vendite) — più i due assi del contatore,
`registro_id` e `anno`. ⚠️ Sul **pregresso** (`VC_…`, numerato prima del
trasloco) `registro_id` e `anno` sono `null`: non è un buco, è un documento
che non ha mai avuto un registro; la forma diversa lo tiene separato dai
nuovi. ⛔ **Il codice non si parsa**: sigla e anno stanno anche nelle colonne.
🔒 **E la RLS passa dalla colonna**: una distinta senza canale non è più «di
tutti» — è del suo emittente, come il lotto da cui nasce. `list_distinte` non
aggiunge filtri applicativi.

### `POST /api/v1/pagamenti/distinte/`

Apre — o **ritrova** — la distinta manuale dell'operatore.

```json
{ "centro_riscossione_id": 3, "data_contabile": "2026-09-01",
  "ente_incasso_id": 7, "emittente_fiscale_id": 32,
  "importo_dichiarato": "1500.00", "meta": {} }
```

`centro_riscossione_id` e `data_contabile` obbligatori; `ente_incasso_id`,
`emittente_fiscale_id`, `importo_dichiarato`, `meta` facoltativi. Nasce
`origine = MANUALE`, stato `BOZZA`.

⭐ **`emittente_fiscale_id` (PK) è facoltativo qui e obbligatorio a database**
(D4 del brief). Il backend lo **trasporta e non lo deduce**: se manca, lo
risolve `pagamenti.fn_get_emittente_distinta` in un ordine solo — dato dal
chiamante → dal **canale** (il conto su cui atterra il denaro ha un solo
padrone) → dall'**operatore in sessione** (`fn_resolve_emittente_for_user`,
che legge l'emittente attivo scelto in topbar) → altrimenti **rifiuto**
`E_CONTABILE_EMITTENTE_OBBLIGATORIO` (400, `fields: ["emittente_fiscale_id"]`):
è il super admin in «tutti gli emittenti» che apre una manuale su CASSA e
deve scegliere. Se emittente **e** canale sono entrambi indicati e
dissentono: `E_CONTABILE_CANALE_DI_ALTRO_EMITTENTE` (400, `fields:
["ente_incasso_id"]`, la frase nomina il canale e le due sigle). ⛔ Nessun
ripiego sul «default dell'installazione», né a database né qui: dichiarare di
un emittente il denaro di un altro è l'attribuzione che la numerazione per
emittente esiste per impedire. ⚠️ La **chiave di riuso** del *get or create*
comprende l'emittente: la manuale è il lotto di lavoro di un operatore **per
un emittente**.

⭐ **È un *get or create*** (`fn_get_or_create_vendite_contabile`): se
l'operatore riapre con gli stessi dati — stessa giornata, stesso centro,
stesso canale, **stessa persona** — il database non ne crea una seconda, gli
ridà la sua. La distinta manuale è **proprietà** di chi la lavora (D12-a), ed è
ciò che rende inutile qualunque lock. Da cui la risposta:

```json
{ "data": { "distinta": {…}, "stati_distinta": […], "stati_riga": […],
            "transizioni": {…}, "gia_popolata": true } }
```

È il dettaglio (sotto, quindi **senza righe**: si leggono da
`distinte/{id}/righe/`) più **`gia_popolata`**: `true` se la distinta
restituita ha già delle righe. La schermata **deve dirlo** — entrarci in
silenzio è il modo in cui si registra due volte credendo di cominciare.
⛔ `gia_popolata` NON significa «riaperta»: una distinta esistente e vuota è
indistinguibile da una appena creata, e il caso è innocuo.

🔴 **Due scritture, una transazione.** Il totale dichiarato non è un parametro
della madre e si scrive subito dopo, dentro un `transaction.atomic()`
esplicito: `ATOMIC_REQUESTS` non è attivo nel progetto, e una distinta nata
senza il suo dichiarato è una distinta la cui quadratura **non scatta mai** —
il controllo esisterebbe e non direbbe niente.

### `GET /api/v1/pagamenti/distinte/{contabile_id}/`

Testata, **i due cataloghi di stato** e **le transizioni ammesse** in un
round-trip:

```json
{ "data": {
    "distinta": { …DistintaRow…, "stato_info_key": "pagamenti.distinte.stato_info.bozza",
                  "stato_is_registrabile": false,
                  "contenuto_modificabile": true,
                  "can_validare": false,
                  "validazione_blocco_reason": "RIGHE_NON_LAVORATE",
                  "validazione_blocco_reason_key": "pagamenti.distinte.validazione_reason.righe_non_lavorate",
                  "validazione_blocco_dettaglio": { "quante": 2, "contabile_righe_ids": [11, 12] },
                  "righe_per_stato": [ { "stato_codice_interno": "ABBINATA", "stato_descrizione": "…",
                                         "righe": 3, "importo": 300.00 }, … ],
                  "righe_scartate": 1, "totale_scartate": "5.00" },
    "stati_distinta": [ {"id", "codice", "codice_interno", "descrizione", "is_final", "ordine", "is_registrabile"} ],
    "stati_riga":     [ {…, "is_postabile", "richiede_abbinamento"} ],
    "transizioni": { "distinta": { "BOZZA": ["VALIDATA", "ANNULLATA"], "VALIDATA": ["BOZZA", "ANNULLATA"] },
                     "riga":     { "DA_ABBINARE": ["ABBINATA", "SOSPESA", "SCARTATA"],
                                   "ABBINATA": ["SOSPESA"], … } }
} }
```

⭐ **`transizioni` (dal 2026-09-14, BE-5)** sostituisce `stati_richiedibili`:
per ogni stato di partenza, gli stati di arrivo che una **persona** può
chiedere — letti dalle due **matrici** del database
(`pagamenti.transizioni_stati_contabile`, `…_riga`) e ristretti al vocabolario
dei richiedibili sull'arrivo (`POSTATA` e `CHIUSA` non compaiono mai). Il
vocabolario nudo diceva *che cosa* si può chiedere, non *da dove*: il frontend
toglieva lo stato corrente e proponeva `SCARTATA` su una riga `ABBINATA`, che
la matrice non ammette — il difetto del primo collaudo in-app. Uno stato senza
uscite ha la lista vuota, non la chiave assente; gli stati ritirati
(`obsoleto_dal`) escono da entrambi i lati.

⭐ **Il verbo «valida» col suo motivo** (BE-1, D20-a — dal 2026-09-19): la
terna `validazione_blocco_reason` / `_reason_key` / `_dettaglio` + il flag
`can_validare`, dal **primo motivo** di `script.fn_check_contabile_validabile(c.id,
c.importo_dichiarato)` — la **stessa** check che
`trgfn_vendite_contabili_guard_validazione` chiama per rifiutare l'ingresso in
`VALIDATA`. Il drawer spegne «Porta a VALIDATA» col motivo, e tooltip e 409
non possono divergere (api.md §«Capability di riga»). ⚠️ La check vuole
**due** argomenti: il dichiarato è un parametro, non si rilegge per id (brief
§4-bis). ⚠️ La terna viaggia **solo se lo stato corrente ammette `VALIDATA`
fra le uscite** (la matrice, letta qui): su una `CHIUSA` o una `ANNULLATA` è
`null` — un motivo su un verbo che non si propone è rumore. Il `dettaglio`
porta i **nomi** dei parametri della frase i18n (`quante`; `importo_dichiarato`,
`somma_righe`).

⭐ **`stato_is_registrabile`** (D20-d): la bandiera del catalogo
(`vendite_contabili_stati.is_registrabile`, `true` sulla sola `VALIDATA`) che
la madre del posting legge al posto del letterale. Il frontend spegne
«Registra» col motivo quando è falsa, e riconosce lo stato «in cui si entra
validando» dal flag nel catalogo (`stati_distinta[].is_registrabile`), non dal
nome.

⭐ **`righe_per_stato`** (BE-1): quante righe attive e per che importo, stato
per stato — l'array **ordinato dal catalogo**, `[]` su una distinta senza
righe. ⚠️ Qui `importo` è un **numero JSON**, non la stringa con cui viaggia
ogni `Decimal` (`totale_righe`, `totale_scartate`): l'array lo costruisce il
database con `jsonb_build_object`, la stessa forma dei `dettaglio` delle
check (`importo_dichiarato`, `somma_righe`) — chi lo legge passa da `Number()`
come per quelli. È la fotografia del dialog di validazione. Da lì il service deriva
**`righe_scartate` / `totale_scartate`** («di cui non nostre», D20-c) con lo
stesso codice con cui la lista le nasconde (`STATO_RIGA_SCARTATA`): una sede,
non due letterali.

⭐ **`contenuto_modificabile`** (D17/D18): `true` solo su una distinta
`MANUALE` in `BOZZA`. Governa il **contenuto** — righe nuove, fatti,
eliminazioni — non le decisioni (abbinare, sospendere, cambiare stato), che
sotto `VALIDATA` restano ammesse. È una **copia dichiarata** del motivo 3 di
`script.fn_check_riga_contabile_eliminabile` (il database stesso lo scrive due
volte, perché sull'`INSERT` non c'è una riga da passare alla check): serve a
**non proporre**, il rifiuto vero resta il 409 del guard.

⭐ **`stato_info_key`** (FE-9): la chiave i18n della riga «dove sono» del
drawer, letta dal `meta.nessuna_azione_key` dello stato — lo stesso campo
degli otto domini con `DrawerActionsBar :info-key`. `null` finché il seed non
è applicato; il backend la **trasporta**, non la deriva dal codice.

⭐ **I cataloghi viaggiano col dettaglio e non si cablano nel frontend.** Quali
stati pretendono fattura e cliente lo dice `richiede_abbinamento`; quali
occupano spazio su una rata lo dice `is_postabile`; quali sono terminali lo
dice `is_final` — e a catalogo **anche `STORNATA` è terminale**, non solo
`POSTATA`: il difetto trovato in revisione era proprio un `=== 'POSTATA'`
scritto a mano. Gli elenchi sono **due** perché il drawer disegna il percorso
della testata e quello della riga nella stessa schermata.

### `PATCH /api/v1/pagamenti/distinte/{contabile_id}/`

Solo i campi che una persona compila: `data_contabile`, `ente_incasso_id`,
`importo_dichiarato`, `meta`. Un `PATCH` che non nomina un campo non lo tocca;
una chiave fuori elenco è un `400`. ⛔ **Lo stato non passa di qui**: è
un'azione, e ha il suo endpoint. Risponde il dettaglio.

### `POST /api/v1/pagamenti/distinte/{contabile_id}/stato/`

```json
{ "nuovo_stato": "VALIDATA" }
```

**Tre** valori chiedibili: `VALIDATA` · `BOZZA` · `ANNULLATA`. Altro → `400`.

⛔ **`CHIUSA` non si chiede**: la chiusura è una **conseguenza del registrare**
(decisione di Tid, lotto 4) — la scrive `fn_posta_contabile` da sé. Un pulsante
«chiudi» rimetterebbe in mano a qualcuno una decisione che il database prende
da solo. ⛔ `IMPORTATA` nemmeno: la scrive l'import.

Il backend verifica **solo il vocabolario**. Se il passaggio sia ammesso da
dove la distinta si trova lo dice la matrice delle transizioni
(`E_CONTABILE_TRANSIZIONE_NON_AMMESSA`, 409); le altre condizioni le dicono i
guard: quadratura col dichiarato (`E_CONTABILE_TOTALE_DICHIARATO_NON_QUADRA`,
400), riapertura solo se manuale (`E_CONTABILE_RIAPERTURA_NON_MANUALE`, 409),
chiusura con righe ancora pronte (`E_CONTABILE_CHIUSURA_CON_RIGHE_PRONTE`, 409).

🔴 **Zero righe toccate non è un successo silenzioso.** La distinta esiste
(l'abbiamo appena letta), quindi se l'`UPDATE` non tocca niente a non risolvere
è il **codice di stato** a catalogo: `500 E_CONTABILE_STATO_NON_CONFIGURATO`.
Prima l'operatore leggeva «fatto» su un gesto mai avvenuto.

## 2. Le righe

La riga è l'**unità di allocazione** (D1): un incasso che copre tre rate
diventa tre righe sotto la stessa distinta. ⛔ Non si «spezza» una riga per
gestire un importo sbagliato (D1-ter): quello si **registra** e poi si
**sistema** (§6).

⛔ **Le righe non viaggiano più nel dettaglio (dal 2026-09-18)**: fino a quel
giorno c'era `"righe": [ …RigaContabileRow… ]`, e il drawer le disegnava con una
`DataTable` grezza. Ora sono la lista `pagamenti.distinta_righe` (sotto), con la
sua pagina e il suo export — e portarle anche qui sarebbe leggere due volte la
`LATERAL` sulla check di eliminabilità, per riga, a ogni apertura del drawer,
per un campo che nessuno legge più.

### `GET /api/v1/pagamenti/distinte/{contabile_id}/righe/`

Le righe attive della distinta, **paginate** — la lista configurabile
`pagamenti.distinta_righe` (id 69, dal 2026-09-18): `{ "count": N, "results":
[ …RigaContabileRow… ], "scartate_count": K }`, offset-based (`limit`/`offset`,
default 25) con `order_by`/`order_dir` sulla whitelist della tabella sopra.

⭐ **Le `SCARTATA` sono FUORI di default** (BE-2, D20-c — dal 2026-09-19):
«non è nostra» resta nella distinta e nella quadratura ma esce dal lavoro.
`?scartate=1` le rimette dentro; spento, `scartate_count` dice **quante ne
nasconde** — contate sullo **stesso perimetro** della lista con il BB
`conta_con_perimetro` (la forma di `archiviate_count`), perché «elenco pulito»
e «tre righe messe via» non si leggano uguali. Acceso, il conteggio è 0 e non
si paga. L'export (`righe/export/`) legge lo stesso parametro: il file segue la
videata, interruttore compreso. Lo stato si nomina nel service per
`codice_interno` (`STATO_RIGA_SCARTATA`), come `STATO_RIGA_ABBINATA`.

⚠️ Fino al 18/09 questa riga diceva *«Non paginata: le righe di una distinta
sono limitate per costruzione»* — una **previsione sui dati**, e le previsioni
sui dati non decidono la forma di una lista (regola zero; è la stessa frase
caduta sugli atti di sistemazione il 02/09). E il `count` era `len(righe)`: un'eco,
non un conteggio (api.md §«Il `count` non si deriva MAI dalle righe»). Ora viene
da `COUNT(*) OVER ()` nella stessa valutazione della pagina.

### `GET /api/v1/pagamenti/distinte/{contabile_id}/righe/export/?formato=csv|xlsx`

⭐ **La contabile in un file.** Stesso `lista_codice` della lista a video: le
colonne sono quelle che l'operatore **vede** (preferenza + preset + permessi),
risolte da `build_export_response`; `order_by`/`order_dir` come la lista (il
file segue l'ordinamento a video). Chiede `EXPORT_MAX_ROWS + 1` righe, non la
pagina: il `+1` è ciò che fa scattare `422 E_UI_EXPORT_LIMIT_EXCEEDED` prima di
serializzare, invece di consegnare un file troncato in silenzio. Nessun filtro
dichiarato nell'intestazione: la distinta è nel path, non una scelta.

```json
{ "id": 91, "contabile_id": 12, "importo": "500.00",
  "riferimento_ente": "TRN 2026…", "data_pagamento": "2026-08-30",
  "data_valuta": null, "data_operazione": null,
  "fattura_id": 820, "fattura_numero": 815, "fattura_anno": 2026, "fattura_serie": "A",
  "fattura_numero_documento": "815 - A", "fattura_data": "2026-09-12", "fattura_totale_doc": "1220.00",
  "fattura_registro_codice": "REG-01",
  "natura_doc_codice_interno": "FATTURA", "natura_doc_descrizione": "Fattura",
  "billing_account_id": 44, "billing_account_codice": "BA-000044", "billing_account_descrizione": "…",
  "scadenza_id": 1301, "scadenza_numero_rata": 2, "scadenza_data": "2026-09-30", "scadenza_importo": "610.00",
  "forzata": false, "motivo_forzatura": null,
  "stato_id": 52, "stato_codice": "ABBINATA", "stato_descrizione": "Abbinata",
  "stato_is_postabile": true, "stato_richiede_abbinamento": true,
  "motivo_sospeso": null, "fondo_source_id": null, "attivo": true, "meta": {} }
```

⚠️ `fattura_numero` è un **bigint**, non una stringa: è il progressivo.
⭐ **Dal 2026-09-17 la forma leggibile NON la compone più chi la mostra**
(D19-b): `fattura_numero_documento` arriva dalla sede unica
`vendite.fn_numero_documento_fattura` («numero - serie», `NULL` sulla non
numerata — il ripiego lo sceglie chi rende), insieme a data, totale, registro,
natura del documento e importo della rata. ⚠️ La natura viaggia come
`natura_doc_codice_interno` / `natura_doc_descrizione` — **senza** il prefisso
`fattura_` dal 18/09: è il nome con cui ogni proiezione porta
`config.nature_doc_fiscale`, ed è la gemella che il `formato = natura_doc` del
catalogo liste legge dalla riga (con il prefisso la colonna «Natura» della lista
69 avrebbe reso `—` su ogni riga, senza errore). È ciò che serve a chi corregge un
importo per sapere **su che cosa** lo corregge, e alla natura per **segnalare**
una nota di credito su una riga di incasso (D19-e). Le sette colonne viaggiano
anche sulla coda (`GET /righe/`), che condivide il frammento. Il residuo **non**
sta sulla riga: si legge dalla base dei saldi (§5) col livello giusto — e in
modifica con `escludi_riga_id`, che dal 18/09 (P-6) sanno applicare **entrambi**
i livelli (fino a quel giorno solo la rata, e sul documento il pannello lo
dichiarava).

### `POST /api/v1/pagamenti/distinte/{contabile_id}/righe/`

```json
{ "importo": "500.00", "riferimento_ente": "TRN …", "data_pagamento": "2026-08-30",
  "data_valuta": null, "data_operazione": null, "motivo_sospeso": null, "meta": {},
  "fattura_id": 820, "billing_account_id": 44, "scadenza_id": 1301,
  "forzata": false, "motivo_forzatura": null }
```

Solo `importo` obbligatorio. Risponde `{ "riga": {…} }`.

⭐ **La riga MANUALE nasce con la destinazione (D16, 2026-09-14).** Con
`fattura_id` nasce **`ABBINATA`** — fattura, cliente, rata e forzatura entrano
nello **stesso `INSERT`** dei fatti, atomico per costruzione: i guard di riga
(dati richiesti dallo stato, coerenza rata/fattura, capienza, scope emittente)
sono `BEFORE INSERT OR UPDATE` e sull'`INSERT` parlano come sull'`UPDATE`.
Senza `fattura_id` nasce **`DA_ABBINARE`**: sulla manuale è l'**eccezione che
l'operatore dichiara** («non ho trovato il documento»), non il default — fino
al 14/09 lo era, e faceva passare chi ha il nome sotto gli occhi per il flusso
dell'importo arrivato senza nome. Si recupera dalla coda (§4).

- `billing_account_id` assente ⇒ è quello della **fattura**, letto dal
  documento (`E_FATTURA_NON_TROVATA` 404 se non c'è o non si vede);
- `scadenza_id`, `billing_account_id`, `forzata` **senza** `fattura_id` ⇒ 400
  (`E_PAGAMENTI_VALIDATION`, con `fields`): senza fattura non c'è destinazione;
- `motivo_forzatura` senza `forzata` ⇒ 400 (la stessa regola di `abbina`, ed è
  la **stessa lettura**: `_destinazione_da_payload`);
- il **doppio tempo della capienza** vale anche qui: primo tentativo senza
  `forzata`, 409 `E_RIGA_CONTABILE_CAPIENZA_SUPERATA` con `ui_action =
  confirm_and_retry` (chiavato sul codice, non sull'endpoint), secondo con
  `forzata = true` che resta scritto sulla riga.

Su una distinta in stato finale il database rifiuta
(`E_RIGA_CONTABILE_DISTINTA_FINALE`, 409); su una **manuale validata**
rifiuta con `E_RIGA_CONTABILE_DISTINTA_VALIDATA` (D18: il contenuto è fermo
finché non torna in bozza).

⚠️ **Un importo è un `Decimal` esatto letto dalla forma testuale** — `NaN` e
`Infinity` sono rifiutati, e un booleano non è un importo: ogni somma che
incontra un `NaN` diventa `NaN`, e un totale `NaN` **non si vede**, si legge
come un campo vuoto.

### `PATCH /api/v1/pagamenti/righe/{riga_id}/`

I **fatti** della riga — come è arrivato il denaro: `importo`,
`riferimento_ente`, `data_pagamento`, `data_valuta`, `data_operazione`,
`motivo_sospeso`, `meta` — e, dal **2026-09-15**, il **secondo tempo**:
`forzata`, `motivo_forzatura`. ⛔ **Non l'abbinamento**: `fattura_id`,
`billing_account_id`, `scadenza_id` non sono accettati qui — abbinare è un
verbo, perché porta con sé la rata, ed è una decisione, non la correzione di
un dato digitato male (R-6). Risponde `{ "riga": {…} }`.

⭐ Le righe sono indirizzate **per id proprio**, non sotto la distinta: una
riga si lavora anche dalla coda del riconciliatore, dove la distinta di
appartenenza non è il contesto.

⚠️ Sotto una manuale `VALIDATA` i **fatti** non si toccano (D18):
`E_RIGA_CONTABILE_DISTINTA_VALIDATA` (409). Le decisioni — stato, abbinamento
— sì.

⭐ **Il doppio tempo della capienza vale anche qui** (decisione di Tid,
2026-09-15 — brief D16/D17 §10.4 Q-H). Il guard della rata gira sull'`UPDATE`
di `importo` come sull'`INSERT`: un importo corretto oltre il residuo prende
il 409 `E_RIGA_CONTABILE_CAPIENZA_SUPERATA` con `confirm_and_retry`, e il
secondo tentativo con `forzata = true` (+ `motivo_forzatura`, facoltativo ma
**solo** con la forzatura — la stessa regola e la stessa funzione della
nascita e di `abbina`) passa e resta scritto sulla riga. ⚠️ Fino a quel
giorno il PATCH non accettava `forzata`: il codice prometteva una conferma
che il verbo non sapeva raccogliere, e il rimedio era eliminare la riga e
ricrearla. ⛔ R-6 resta intero: protegge la **destinazione**, non la
conferma di una scrittura. Provato per intero contro il guard vero:
`tests/db/test_riga_elimina_e_transizioni_db.py` (12-13).

### `DELETE /api/v1/pagamenti/righe/{riga_id}/`

Elimina la riga: **`attivo = false`** (D17, 2026-09-14). Risponde
`{ "riga_id": 91, "eliminata": true }`. `Idempotency-Key` obbligatoria; il
corpo è vuoto e viene ignorato.

⭐ **Il metodo dice il verbo** (§Grammatica URL): niente `/elimina/` nel path.
Ammesso **solo** su una distinta `MANUALE` in `BOZZA` — e a dirlo è il
database, con i tre motivi ordinati di
[`script.fn_check_riga_contabile_eliminabile`](/dbzero/script/manual/fn_check_riga_contabile_eliminabile):
`E_RIGA_CONTABILE_DISTINTA_FINALE` · `E_RIGA_CONTABILE_DISTINTA_NON_MANUALE` ·
`E_RIGA_CONTABILE_DISTINTA_VALIDATA` (tutti 409). ⛔ Nessuna copia del
predicato in Python: la **stessa** check alimenta le colonne
`elimina_blocco_reason` · `elimina_blocco_reason_key` ·
`elimina_blocco_dettaglio` · `can_eliminare` della riga in lista e nella coda
(`LATERAL`, primo motivo), così il cestino spento e il rifiuto non possono
dire due cose diverse.

⚠️ **Una riga eliminata non è più raggiungibile da nessun verbo**: `get_riga`
filtra `attivo`, quindi `PATCH`, `stato/`, `abbina/` e un secondo `DELETE`
rispondono `E_RIGA_CONTABILE_NON_TROVATA` (404) — la stessa risposta di «non
la vedi», e coerente con le liste, che le eliminate non le mostrano. Il doppio
invio lo copre l'`Idempotency-Key`, non un ramo «già eliminata». Non esiste un
verbo di riattivazione: D18 la classifica come contenuto, e nessuna schermata
la offre.

⚠️ «Scarta» **non** è un'eliminazione: `SCARTATA` vuol dire «denaro arrivato,
non nostro» e **conta nella quadratura** (D12-e). Una riga digitata male su
una bozza si **elimina**; scartare una riga sbagliata su una distinta col
totale dichiarato la lascia senza via d'uscita.

### `POST /api/v1/pagamenti/righe/{riga_id}/stato/`

```json
{ "nuovo_stato": "SOSPESA", "motivo_sospeso": "Bonifico senza causale" }
```

Chiedibili: `DA_ABBINARE` · `ABBINATA` · `SOSPESA` · `SCARTATA`. `POSTATA` non
si chiede: la scrive la registrazione. `IMPORTATA` la scrive l'import.

⚠️ **Il motivo viaggia nello stesso giro della sospensione**: sospendere senza
dire perché lascia la riga in una coda dove il prossimo che la guarda non sa
che cosa si era già capito. E `ABBINATA` su una riga senza fattura e cliente
la rifiuta il guard (`E_RIGA_CONTABILE_ABBINAMENTO_INCOMPLETO`, 400): il
backend guarda solo il vocabolario.

⭐ **Il ritorno a `DA_ABBINARE` è l'unico modo di sganciare un abbinamento
sbagliato**, ed è ammesso dal contratto: generare le transizioni dal catalogo
invece di scriverle a mano è ciò che lo ha fatto ricomparire nel frontend.

## 3. La registrazione

### `GET /api/v1/pagamenti/distinte/{contabile_id}/anteprima-registrazione/`

La **fotografia** di che cosa succede se si preme adesso:

```json
{ "data": {
    "contabile_id": 12, "stato_codice": "VALIDATA",
    "righe_registrabili": 2, "totale_registrabile": "1200.00",
    "righe_non_registrabili": [ { "id": 93, "importo": "300.00",
                                  "stato_codice": "SOSPESA", "stato_descrizione": "Sospesa" } ],
    "importo_dichiarato": "1500.00", "scarto_dichiarato": "0.00"
} }
```

⭐ **I due numeri `righe_registrabili` / `totale_registrabile` sono quelli da
rimandare indietro** come dichiarazione (sotto): è così che il database
verifica di registrare esattamente ciò che l'operatore ha approvato. Le righe
che restano indietro vengono elencate **con il loro stato**: «due righe non
registrabili» senza dire quali obbliga a cercarle a mano.

### `POST /api/v1/pagamenti/distinte/{contabile_id}/registra/`

⭐ **Il gesto irreversibile di questo dominio**, e l'unico con un cancello di
processo: `post_permission = "registra_distinta"`. ⚠️ L'azione va **assegnata
a un profilo**: finché non lo è, `fn_check_azione_processo` risponde `false`
per tutti tranne i super admin — **fail-closed**, che sul gesto che muove
denaro è il verso giusto in cui sbagliare.

```json
{ "righe_attese": 2, "totale_atteso": "1200.00" }
```

La dichiarazione è **facoltativa ma legata**: o tutti e due o nessuno
(`400` altrimenti). Mezza dichiarazione non si può verificare, e accettarla
significherebbe registrare senza controllo credendo di averlo fatto.
⚠️ **Zero è una dichiarazione legittima**: l'anteprima può mostrare zero righe
registrabili, e la coppia `(0, 0)` è esattamente ciò che l'operatore ha
davanti.

Una sola `SELECT pagamenti.fn_posta_contabile(...)`, atomica per costruzione:
⛔ nessun `transaction.atomic()` attorno a più statement, nessun ciclo che
posta le righe una a una. Risponde la **ricevuta**:

```json
{ "data": { "movimenti_creati": 2, "righe_postate": 2, "righe_saltate": 1,
            "totale_postato": "1200.00", "esito": "POSTATA" } }
```

⛔ **`esito` risale intatto: `POSTATA` | `NULLA_DA_POSTARE`, e il secondo NON
è un errore.** La funzione non solleva quando non c'è niente da registrare;
il backend non lo trasforma in un 409 e non lo inghiotte. La **frase** la
sceglie il frontend: replay tecnico → silenzio; seconda pressione voluta →
«questa distinta è già registrata» (D3-c). Se il backend lo facesse diventare
un errore, il database scriverebbe nel registro degli errori un errore che non
è un errore — la ragione esatta per cui la madre è scritta così.

Ciò che invece **rifiuta**, e viene dalla madre: distinta non in uno stato
registrabile (`E_CONTABILE_NON_REGISTRABILE`, 409), dichiarazione che non
corrisponde a ciò che c'è (`E_CONTABILE_DICHIARAZIONE_NON_CORRISPONDE`, 409).
A registrazione avvenuta la madre porta la distinta a `CHIUSA` da sé.

### `POST /api/v1/pagamenti/distinte/{contabile_id}/correggi/`

La **correzione guidata** (Q-7): da una distinta **registrata** nasce una
distinta **nuova** con le righe di segno opposto già compilate. Stesso cancello
della registrazione (`registra_distinta`), per la stessa ragione: un gesto che
rovescia del denaro non può avere una porta più larga di quello che lo ha
scritto.

```json
{ "data_contabile": "2026-09-05", "motivo": "Bonifico contabilizzato due volte" }
```

Entrambi facoltativi: senza data la madre usa `CURRENT_DATE` — il default sta
**là**, non qui. Risponde:

```json
{ "data": { "esito": { "contabile_id": 15, "righe_create": 2, "righe_saltate": 0,
                       "esito": "CREATA" },
            "distinta": { …dettaglio della distinta nuova… } } }
```

⭐ **Le righe nascono con fattura e rata già scritte ma in `DA_ABBINARE`**
(decisione C-1, misurata dal team DB il 28/08): nascerle già abbinate avrebbe
richiesto di scrivere `forzata = true` al posto dell'operatore, perché su una
rata saldata dal movimento che si sta correggendo non c'è capienza in nessuna
direzione. La correzione guida tutto tranne l'ultimo clic.

⛔ `NULLA_DA_CORREGGERE` risale intatto, con `"distinta": null` — è un esito,
non un errore, e non si legge nessun dettaglio. ⛔ Non si chiama «storno»:
`STORNATA` è fuori dal catalogo dal 21/08. Rifiuti dalla madre: si corregge
solo il registrato (`E_CONTABILE_CORREZIONE_NON_REGISTRATA`, 409), una
correzione per documento (`E_CONTABILE_GIA_CORRETTA`, 409).

## 4. L'abbinamento, le code, le rate fuori capienza

### `POST /api/v1/pagamenti/righe/{riga_id}/abbina/`

Il denaro trova il suo posto: la riga passa ad `ABBINATA` **nello stesso
gesto**.

```json
{ "fattura_id": 820, "billing_account_id": 44, "scadenza_id": 1301,
  "forzata": false, "motivo_forzatura": null }
```

`fattura_id` obbligatorio; `billing_account_id` **facoltativo** dal 2026-09-14:
se manca è quello della fattura, **letto** dal documento (`E_FATTURA_NON_TROVATA`
404 se non c'è o non si vede) — la stessa regola, e la stessa lettura
(`_destinazione_da_payload`), della nascita della riga (§2, `POST …/righe/`). ⚠️ **La rata resta
facoltativa** anche su una riga abbinata: la riga del fondo fattura ha fattura
sì e rata no, ed è un caso normale. `motivo_forzatura` senza `forzata = true`
è un `400`: sarebbe una nota che nessuno leggerà mai. Risponde `{ "riga": {…} }`.

🔴 **La coerenza si rifiuta, la capienza si segnala** (D14-b):

```text
«questa rata è di questa fattura?»       → 🔒 E_RIGA_CONTABILE_RATA_INCOERENTE   (400)
«c'è ancora spazio su questa rata?»      → ⚠️ E_RIGA_CONTABILE_CAPIENZA_SUPERATA (409)
```

**Il doppio tempo della capienza**, letto dal guard:

```text
1° tentativo, forzata = false → RIFIUTATO, col messaggio che porta già i numeri
2° tentativo, forzata = true  → ACCETTATO, e resta scritto sulla riga (colonne forzata + motivo_forzatura)
```

⛔ Nessun permesso, nessun pattern proponi/approva, un tempo solo, e la regola è
**simmetrica** nei due versi. Il backend **non decide che cosa sia forzabile**:
passa il flag alla madre, che sa. ⭐ Il frontend riconosce il rifiuto
confermabile dall'`ui_action` **`confirm_and_retry`** dichiarata su quel codice
in `error_ui_overrides.py` (Q-1) — ramifica sul **comportamento**, non su un
elenco di codici (`useForzaturaConfermata`). È il primo consumatore di
`ui_action` in tutto il prodotto.

⭐ E dal 24/08 questa è **la strada ordinaria del sovra-incasso**, non
l'eccezione: si registra il fatto, l'eccedenza si vede nell'elenco (§6) e la
decisione la prende una persona con un atto di sistemazione. Nessuno spezza
niente.

### `POST /api/v1/pagamenti/righe/{riga_id}/registra/`

⭐ **La registrazione TARDIVA** (D20-b, brief validata-e-tardiva §2.2 — dal
2026-09-19): una riga **`SOSPESA`** sotto una distinta **già registrata**
(`CHIUSA` con `data_conferma`) si abbina **e** si registra nello stesso gesto.
Una sola `SELECT` sulla madre `pagamenti.fn_posta_riga_tardiva`: la riga passa
da `ABBINATA` (girano **tutti** i guard dell'abbinamento — transizione, dati,
rata con capienza e coerenza, scope), alla quarta mossa si presenta con la GUC
transazionale, poi il movimento (`meta.origine = POSTING_TARDIVO`, registrato
**oggi**), poi `POSTATA`. La distinta **resta `CHIUSA`** e non tocca
`data_conferma`/`user_conferma`; la quadratura del giorno regge (la riga era
già contata).

Payload = quello di `abbina/` (`fattura_id` obbligatorio, `billing_account_id`
letto dalla fattura se manca, `scadenza_id` facoltativo, `forzata` +
`motivo_forzatura`), letto dalla **stessa** funzione (`_destinazione_da_payload`).
Risposta: `{ "movimento_id", "riga_id", "importo", "esito": "POSTATA", "riga": {…} }`.

🔴 **Il doppio tempo passa intatto**: primo tentativo senza `forzata`, 409
`E_RIGA_CONTABILE_CAPIENZA_SUPERATA` con `confirm_and_retry`, secondo con
`forzata = true`. Il backend non decide che cosa sia forzabile.

⛔ **Nessun esito «nulla da postare»**: una tardiva su una riga che non si può
registrare è un **rifiuto** della madre — `E_RIGA_CONTABILE_TARDIVA_STATO` (la
riga non è `SOSPESA`: da `SCARTATA` si passa prima da «Riprendi»),
`E_RIGA_CONTABILE_TARDIVA_DISTINTA_NON_REGISTRATA` (annullata, o ancora aperta:
«usa il giro normale») — 409 con la sua frase. Il backend **non** verifica né
lo stato della riga né quello della distinta: sono i guard della madre, e
riscriverli sarebbe la seconda sede (presidio statico in
`test_validata_e_tardiva`).

🔴 **Lo stesso cancello della registrazione** (`post_permission =
registra_distinta`): scrive un movimento. Chi la chiama: la coda «Sospese» e il
drawer di una distinta chiusa («Abbina e registra»). ⛔ Mai un job: la tardiva
è una decisione di chi ha identificato il denaro.

### `GET /api/v1/pagamenti/righe/`

La coda del riconciliatore: le righe **di tutte le distinte** in uno degli
stati chiesti. Filtri: `coda` (`DA_ABBINARE` · `SOSPESE` · `TUTTE`, default
`TUTTE`), `billing_account_id`, `data_da`/`data_a` sulla data contabile della
distinta. Paginata.

⭐ **Due voci di menu, un endpoint solo** (Q-4 → c). `DA_ABBINARE` è lavoro
non ancora fatto, `SOSPESE` è lavoro fatto che ha trovato un ostacolo: due
mestieri (D12-f), la stessa lista con il filtro già impostato — e una sola
definizione a catalogo (`pagamenti.righe`), quindi una configurazione di
colonne sola. `TUTTE` non è una coda: è il modo di guardarle insieme, e non
compare in nessun menu.

Ogni riga è una `RigaContabileRow` **più la sua distinta** —
`contabile_codice`, `contabile_data`, `contabile_origine`: una riga
cross-distinta senza il documento da cui viene non si lavora, chi la guarda
deve poterci tornare. ⚠️ Ed è la colonna su cui si ordina (`contabile_codice`):
la prima stesura la dichiarava ordinabile e non la proiettava, e ordinare per
distinta era un **500**.

⭐ **E i fatti della testata che decidono il verbo** (BE-4, D20-b — dal
2026-09-19): `contabile_stato_codice_interno`, `contabile_is_final`,
`contabile_registrata` (= `data_conferma IS NOT NULL`, scritta dal posting). Da
una «Sospesa» sotto una distinta **registrata** si «abbina e registra» (la
tardiva); sotto una aperta si abbina e basta. Il frontend sceglie da un fatto,
non ricalcola una regola.

⭐ **La risposta porta anche il catalogo e la matrice di riga** (FE-4):
`stati_riga` e `transizioni_riga` (`{ stato_da: [stato_a…] }`, ristretta ai
richiedibili come nel dettaglio), **accanto** a `results`/`count`. Dalla coda
si lavora — abbina, sospendi, scarta, riporta — e le voci del kebab si
costruiscono dalla matrice come nel drawer; vengono dalla stessa lettura delle
righe, quindi non possono raccontare due istanti diversi (la forma di `stati`
sul registro lotti).

### `GET /api/v1/pagamenti/rate/fuori-capienza/`

Le rate uscite dalla banda di capienza, da `vw_rate_fuori_capienza`. Filtri:
`motivo`, `billing_account_id`. Paginata.

🔴 **Senza questo elenco la forzatura sarebbe un modo per nascondere, non per
registrare**: è la ragione per cui la vista e il guard che permette di forzare
stanno nello stesso lotto.

⭐ **`motivo` è la prima colonna da guardare**, perché sono **due popolazioni
diverse in un elenco solo**: `SOVRA_INCASSATA` (è entrato più del dovuto) e
`MOVIMENTO_CONTRARIO` (un rimborso dove non era entrato niente). Un motivo
fuori vocabolario è un `400`, non una lista vuota.

Colonne: `motivo`, `scadenza_id`, `fattura_id`, `anno`, `serie`,
`fattura_numero`, `billing_account_id`, `emittente_soggetto_ruolo_id`,
`numero_rata`, `data_scadenza`, `importo_rata`, `registrato`, `residuo`,
`incassato`, `in_lavorazione`, `righe_forzate`, `motivi_forzatura`, — dal
17/09 (P-1-bis) — **`numero_documento`**, il numero parlante dalla sede unica
`fn_numero_documento_fattura` (la colonna 766 della lista 52: il contatore nudo
era ambiguo fra fattura e nota di credito) e — dal 18/09 (P-7) —
**`natura_doc_codice_interno`** e **`natura_doc_descrizione`** (la colonna 767,
«Natura», `formato = natura_doc`: la rende `CellaConfigurabile` con
`NaturaDocTag sempre`, e la gemella `codice_interno` è presidiata sulla
proiezione). `righe_forzate` e `motivi_forzatura`
sono ciò che la forzatura ha lasciato scritto: **è così che resta onesta**.

⭐ **La natura cambia cosa i due motivi SIGNIFICANO**, e il vocabolario resta a
due codici per decisione del DB: su una nota di credito `SOVRA_INCASSATA` è
«sovra-rimborsata» (rimborsato più del credito) e `MOVIMENTO_CONTRARIO` è
«entrato invece di uscire» (il cliente ha pagato una nota a suo favore). La
frase la sceglie il frontend ramificando su `natura_doc_codice_interno`
(`useEtichettePagamenti().motivoFuoriCapienza(codice, natura)`), e il residuo
negativo si dice per natura con la stessa sede di tendina, form e picker
(`residuoNegativo`): «di troppo» sulla fattura, «da rimborsare» sulla NC. Il
**filtro** `motivo` resta sui due codici letti come fattura: filtra per codice.

Ordinamento (`order_by`, whitelist `RATE_FUORI_CAPIENZA_SORT_COLUMNS`):
`data_scadenza` (default, DESC) · `motivo` · `residuo` · `importo_rata` ·
`fattura_numero` · `numero_documento` — quest'ultimo ordina per la **coppia**
`(fattura_numero, serie)`, non per il testo («10 - A» verrebbe prima di
«9 - A»). ⚠️ La natura **non** è ordinabile (non è nella whitelist, e la riga
767 del seed lo dichiara con `ordinabile = f`). Fino al 18/09 questa riga
diceva *«la vista non porta la natura»* — era vero, ed era il residuo P-7 del
brief DB, chiuso quel giorno.

## 4-bis. Le rate — il picker e lo scadenzario (D19, 2026-09-17)

> Il rilievo del secondo giro in-app (Tid, 15/09) in una frase: *chi digita un
> incasso non riconosce il documento da un contatore, e la domanda vera non è
> «quale fattura?» ma «quale rata?»*. Brief DB:
> [brief-db-distinta-ricerca-rate.md](../../../dev/work-done/brief-db-distinta-ricerca-rate.md);
> piano BE/FE: [piano-be-fe-distinta-ricerca-rate.md](../../../dev/work-in-progress/piano-be-fe-distinta-ricerca-rate.md).

### `GET /api/v1/pagamenti/rate/`

**L'elenco paginato delle rate col saldo** — la quarta lettura della base dei
saldi (`saldi_service.list_rate`), sorgente della lista `pagamenti.rate` (id 68)
e quindi del **picker** della distinta e, domani, dello **scadenzario**.

Una riga per rata di `vendite.vw_fatture_scadenze_lista` (rata · documento
com'è scritto · cliente · emittente) **più** `residuo · in_lavorazione ·
incassato · has_movimenti` dalla base unica. La chiave della riga è
**`scadenza_id`** (il vocabolario di `pagamenti`, `dataKey` della lista).

| Param | Forma | Note |
| --- | --- | --- |
| `billing_account_id` | int | il cliente — uno dei due criteri del picker |
| `fattura_numero` | int | il numero del documento, confronto **ESATTO**: 101 non porta 1010 (nel lookup sì, ed è giusto lì). `serie` e `anno` per disambiguare |
| `search` | str | ricerca libera sulle colonne che il **catalogo** della lista accende per l'operatore (`ricerca_full` nella configurazione; dichiarazione `_RICERCA_RATE`, BB `add_ricerca_full_condition`): le colonne non si elencano qui. Dal 24/09 cerca **anche il numero documento** (Tid), oltre al cliente. È un `ILIKE`: «101» porta anche la 1010 — il confronto esatto è `fattura_numero`, un filtro diverso. Sotto la soglia della lista il termine non filtra (nessun 400). Vale anche sul perimetro di `solo_aperte`: il BB sta nella funzione dell'alias |
| `solo_aperte` | bool | solo le rate con `residuo <> 0` (Q-B). ⚠️ Il filtro sta nel `WHERE`, quindi chiede il saldo di **tutto il perimetro** — è il costo onesto di quel filtro, non della lista |
| `solo_numerate` | bool | solo le rate di documenti **numerati** (`numero IS NOT NULL`; dal 18/09, rilievo in-app di Tid): una bozza non è un documento fiscale e la sua rata non è un credito su cui registrare un incasso. Il picker lo passa **sempre** (default dello store); vale anche sul perimetro di `solo_aperte`, perché sta nella stessa funzione dell'alias. ⏳ La regola di Tid è più stretta — «solo le definitive, inviate a SDI» — ed è un predicato di dominio che arriverà in **una** sede a DB, non come un secondo booleano (piano D19 §8) |
| `data_scadenza_da` / `_a` | date ISO | |
| `natura_doc_codice` | str | per lo scadenzario; il picker non lo passa. Il maiuscolo lo mette il **service** (una sede); il vocabolario è del catalogo ed è **aperto**, quindi un codice inesistente dà una lista vuota, non un 400 |
| `limit` / `offset` | int | offset-based (la lingua di `useSearchTable`): `limit` default **25**, max 200. ⚠️ Il picker chiede **10**: è la lista di un dialog alto dieci righe (`app-dialog-lista`), e lo store nasce a `PAGINATION.COMPACT_ROWS` |
| `order_by` / `order_dir` | str | whitelist `RATE_SORT_COLUMNS` (nomi **fisici** del seed 68): `numero_documento` (ordina per la coppia `(numero, serie)`, non per il testo) · `data` · `ragione_sociale_completa` · `ba_codice` · `numero_rata` · `data_scadenza` · `importo` · `totale_doc` · `stato_descrizione`. ⛔ I tre saldi **non** ordinano (arrivano dal nucleo *dopo* la pagina; il seed li dichiara `ordinabile = f`). Fuori whitelist = 400 col campo. `order_dir` **grezzo**: senza `order_by` la lista parte `data_scadenza ASC` (è una coda); con `order_by` su una data e senza verso il verso naturale è DESC (regola del 02/09) |

⚠️ **Nessun criterio è obbligatorio qui**: lo pretende il picker (cliente o
numero, D19-c), non la rotta — lo scadenzario la chiama senza. Lo scope
emittente applicativo (`v.emittente_fiscale_id`, convenzione `pk`) si somma alla
RLS di `fatture_scadenze` (via testata).

⭐ **Pagina prima, saldo dopo** (brief DB §8): la query pagina la **vista**
(`COUNT(*) OVER ()`), poi i saldi si chiedono al nucleo
`pagamenti.fn_get_saldi_rate(ARRAY[…ids della pagina])` in **una** chiamata —
non in `LATERAL` per riga (EXPLAIN del team DB: con `ARRAY[sc.id]` il filtro non
si piega e diventa una scansione dei movimenti per rata), e mai nella stessa
query del `COUNT(*) OVER ()`, che girerebbe sul perimetro. Con `solo_aperte`
l'eccezione è obbligata: «aperta» è un predicato sul saldo, sta nel `WHERE`, e
il nucleo si chiama sull'array del perimetro (`ARRAY(SELECT … stesse
condizioni)`), coi saldi che escono dalla stessa query. Le due `FROM`+`WHERE`
sono **una funzione** con l'alias come parametro: non possono divergere.

```json
{ "data": { "count": 2, "results": [
    { "scadenza_id": 1301, "fattura_id": 77, "numero_rata": 1, "data_scadenza": "2026-09-30",
      "importo": "610.00", "numero_documento": "101 - A", "registro_codice": "REG-01",
      "data": "2026-09-01", "natura_doc_codice_interno": "FATTURA", "totale_doc": "1220.00",
      "ragione_sociale_completa": "Rossi Mario SRL", "ba_codice": "BA-000123",
      "residuo": "400.00", "in_lavorazione": "0.00", "incassato": "210.00", "has_movimenti": true },
    … ] } }
```

⭐ **Selezionabile e importo proposto = `residuo − in_lavorazione`** (lo
*spazio*, Q-B di Tid), calcolato dal client (`spazioSaldo`, una sede): non è una
quarta colonna, e non lo sarà. Su una **nota di credito** (che dal 17/09 ha la
sua rata **negativa**, P-5) il residuo è negativo e la rata **si sceglie**: il
predicato è `≠ 0`, non `> 0` — il rimborso è un incasso a segno invertito.
🔴 **La sottrazione è in centesimi**, ed è una regola del contratto e non un
dettaglio del client: `importo` su `vendite_contabili_righe` è `numeric` **senza
scala** e il guard di capienza confronta `abs(importo) > abs(spazio)` sui numeri
com'è — un importo con i residui della virgola mobile (`0.29999999999999716`
per `100.30 − 100.00`) viene **rifiutato per capienza** pur essendo esattamente
lo spazio. Chi propone un importo da questa lista lo calcola in centesimi
(rilettura del 17/09; domanda al DB nel brief §4-bis.9-ter).

Presidi: `tests/services/test_rate_lista.py` (envelope, whitelist, ricerca
corta, criteri intatti) · `tests/db/test_rate_lista_db.py` sul DB provvisto, col
mondo **costruito** (101 e 1010 nella stessa serie): il numero è un `=`, i saldi
arrivano per ogni rata della pagina, `solo_aperte` toglie la saldata, ogni
colonna della whitelist ordina nei due versi e nei due rami, e `solo_numerate`
toglie la **bozza** — costruita nel test, non nella fixture — in entrambi i
rami (rosso alla controprova col filtro spento); la ricerca libera trova cliente
**e** documento nei due rami, e ogni colonna che il catalogo accende trova la
rata costruita (`RicercaListeDbTests`, `verifica_ricerca_colonna_per_colonna`). Seed:
`gen_seed_lista.py --verifica-ordinamento pagamenti.rate` verde.

### `POST /api/v1/pagamenti/distinte/{contabile_id}/righe/da-rate/`

⭐ **N rate scelte → N righe in un Salva** (D19-d): è D1 reso a video — *«un
incasso che copre tre rate resta tre righe, cambia solo quando si scrivono»*.
Verbo di **collezione** sulle righe (il nome dice **cosa**: le righe nate dalle
rate scelte), `Idempotency-Key` obbligatoria, gate `add` d'area come `POST
righe/`.

```json
{ "data_pagamento": "2026-09-17", "data_valuta": null, "riferimento_ente": "TRN 2026…",
  "righe": [ { "scadenza_id": 1301, "importo": "500.00" },
             { "scadenza_id": 1302, "importo": "620.00", "forzata": true, "motivo_forzatura": "…" } ] }
```

- i **fatti comuni** (`data_pagamento`, `data_valuta`, `data_operazione`,
  `riferimento_ente`, `meta`) valgono per tutte; per riga solo `scadenza_id`,
  `importo`, `forzata`, `motivo_forzatura` (il motivo solo con la forzatura, come
  ovunque). Tetto **200**; `scadenza_id` **duplicato = 400** con `fields`: da un
  picker è un difetto del client, e deduplicare in silenzio butterebbe via un
  importo;
- 🔴 **un fatto comune sbagliato è un 400 col campo, prima del giro** (rilettura
  del 17/09): si legge **una volta**, con gli stessi lettori di `crea_riga`, e
  viaggia già letto su ogni riga. Nella prima stesura una data malformata veniva
  rifiutata dentro il savepoint di **ogni** riga — un 200 `ERRORE` con N fallite
  identiche, la stessa frase su ogni rata dell'area e nessun campo acceso in
  testa;
- ⛔ **nessuna seconda strada di inserimento**: per ogni rata si risolve la
  fattura (sotto RLS: assente ⇒ `E_RATA_NON_TROVATA` per **quella** riga) e si
  chiama `crea_riga` così com'è — BA dalla fattura, stato `ABBINATA`, guard DB di
  coerenza e capienza sull'`INSERT`;
- `run_fan_out`, un savepoint per riga: le riuscite **entrano**, le rifiutate
  tornano col loro errore **intero**.

```json
{ "esito": "PARZIALE", "richieste": 3, "riuscite": 2,
  "creati": [ { "indice": 0, "scadenza_id": 1301, "riga": { …RigaContabileRow… } }, … ],
  "falliti": [ { "indice": 1, "scadenza_id": 1302,
                 "errore": { "code": "E_RIGA_CONTABILE_CAPIENZA_SUPERATA", "message": "…",
                             "hint": "…", "ui_action": "confirm_and_retry", "fields": [], "targets": [] } } ] }
```

⭐ `errore` è `ErrorTranslator.to_api_error(exc).to_dict()`, la sede unica delle
politiche dell'envelope (hint tolto sui tecnici, bersaglio solo dove c'è un
gesto): la capienza che non regge risale «confermabile» **per riga**, e il
frontend ramifica su `ui_action`, cieco ai codici. **Lo status è 200 anche su
`PARZIALE`/`ERRORE`**: chi legge guarda `esito`, `creati[]`, `falliti[]`.
⚠️ L'idempotenza copre il **giro**: il secondo tempo è un giro **nuovo** con le
sole righe rimaste (chiave nuova).

Presidi: `tests/services/test_righe_da_rate.py` (elenco, duplicati, tetto,
fatto comune malformato = 400, composizione per riga, tre esiti, indice giusto) ·
`tests/db/test_rate_lista_db.py::RigheDaRateDbTests` sul DB provvisto, per
intero: due rate, la seconda oltre la banda ⇒ `PARZIALE`, la prima scritta, la
seconda in `falliti` con `confirm_and_retry`; poi il secondo giro con `forzata`
che la fa entrare e resta scritta.

## 5. La base dei saldi

🔴 **I saldi hanno una sede sola** (decisione di Tid, 24/08): `saldi_service`
è l'**unico** modulo del backend che legge `fn_get_saldo_fattura`,
`fn_get_saldo_fattura_contabili` e `fn_get_saldo_rata`, ed espone **una forma
unica** a ogni livello. ⛔ Nessun altro service, repository o view le interroga
per conto suo: un saldo calcolato in due posti diverge alla prima regola nuova,
e sono numeri su cui qualcuno decide se sollecitare un cliente — la stessa
ragione per cui il pricing passa solo dal suo service.

```json
{ "data": { "livello": "RATA", "riferimento_id": 1301,
            "residuo": "300.00", "in_lavorazione": "500.00", "incassato": "700.00",
            "has_movimenti": true } }
```

| Numero | Che cosa dice |
| --- | --- |
| `residuo` | quanto manca ancora da regolare — la domanda che uno si fa. Tutti i movimenti contano: il trasferimento la salda davvero |
| `in_lavorazione` | denaro già digitato su una distinta e **non ancora registrato**: non abbassa il residuo, e vederlo spiega perché |
| `incassato` | di quanto è stato registrato, quanto è entrato **davvero in banca** — i centri interni (fondi, compensazioni) sono esclusi. ⚠️ «Incassato» non è «postato», e la differenza va detta fin dalla prima riga |
| `livello` | `DOCUMENTO` · `RATA` — e `CLIENTE`, dichiarato e non ancora acceso: la forma nasce capace di reggerlo |

⛔ Una schermata sceglie **quali** numeri accendere; nessuna li rinomina o li
ricalcola a modo suo.

### `GET /api/v1/pagamenti/rate/{scadenza_id}/saldo/`

Livello **rata**, tutti e tre i numeri. Query param `escludi_riga_id`: esclude
una riga contabile dal conto — serve a chiedere lo spazio **prima di sé**, cioè
a sapere se quella riga ci sta senza contarsi addosso. `404
E_RATA_NON_TROVATA` se la rata non c'è.

### `GET /api/v1/pagamenti/fatture/{fattura_id}/saldo/`

Livello **documento**. ⭐ Tutti e tre i numeri **dal 29/08** (DB-10, atterrata
il 25/08): fino a quel giorno `incassato` era `null`. ⛔ **Resta il divieto, e
vale per sempre**: l'`incassato` del documento **non si somma dalle rate** —
una riga contabile può avere fattura senza rata (il fondo fattura è
esattamente così), e quel denaro non comparirebbe in nessuna somma di rate. Un
numero incompleto che si presenta come completo è peggio di un numero assente.

⭐ **Dal 18/09 (P-6) anche qui `escludi_riga_id`**, con lo stesso nome e la
stessa domanda della rata — «quanto c'era **prima di me**» — per chi corregge
una riga **senza** rata (il fondo fattura): fino a quel giorno la funzione DB
non aveva il parametro e il pannello «Destinazione» lo *dichiarava*
(«comprende anche questa riga») invece di fingere. ⚠️ Semantica identica alla
rata, dichiarata dal DB nel changeSet: la riga esclusa esce dal **dichiarato**
e, se è già registrata, col suo **movimento** — come nel nucleo
`fn_get_saldi_rate`. Un valore non numerico è un `400` col campo, un id `≤ 0`
è un guasto del chiamante (`E_PAGAMENTI_CHIAMATA_NON_VALIDA`, TECNICO): il
backend passa e non normalizza a «nessuna esclusione».

⚠️ Residuo e «in lavorazione» escono da **una** lettura — `fn_get_saldo_fattura`
sola, che la sorella `_contabili` la chiama al suo interno (fino al 29/08 c'era
un `CROSS JOIN` fra le due, che faceva girare la seconda due volte): letti
separati sarebbero due istanti diversi, e un residuo di prima accanto a un «in
lavorazione» di dopo sono due numeri veri che insieme raccontano una cosa
falsa. `404 E_FATTURA_NON_TROVATA` — lo solleva il database.

### `GET /api/v1/pagamenti/fatture/{fattura_id}/rate/`

Le rate della fattura, **ciascuna col suo saldo**, in un giro solo:

```json
{ "data": { "count": 3, "results": [
    { "scadenza_id": 1301, "fattura_id": 77, "numero_rata": 1, "data_scadenza": "2026-08-31", "importo": "500.00",
      "residuo": "0.00", "in_lavorazione": "0.00", "incassato": "500.00", "has_movimenti": true },
    … ] } }
```

È la risposta a «su quale rata metto questi soldi?», e la consuma il form
dell'abbinamento: N chiamate per disegnare un menu sono N modi di essere
lenti. ⚠️ Nessun 404 sulla fattura: una fattura senza rate risponde
`count: 0`. ⭐ Dal 17/09 la rata porta **`fattura_id`**: il form della riga tiene
«una rata resta scelta solo se è del documento scelto» (il picker consegna
fattura e rata insieme), e per dirlo la rata deve sapere di chi è — la stessa
chiave della riga di `rate/`, così le due sorgenti hanno la stessa forma.

## 6. Le sistemazioni — che cosa si fa del denaro di troppo

Tre destinazioni a vocabolario chiuso, e **non sono tre modi di scrivere la
stessa cosa**: producono due specie diverse di oggetto (un fondo oppure una
distinta), ed è la ragione per cui l'esito ha due colonne e non una.

| `destinazione` | Il denaro | `fattura_destinazione_id` | `motivo` |
| --- | --- | --- | --- |
| `RIPORTO` | va su **un altro documento** del cliente: nasce un **fondo** | obbligatoria | obbligatorio |
| `COMPENSAZIONE` | chiude due documenti del cliente fra loro: nasce una **distinta** | obbligatoria | — |
| `RIMBORSO` | **esce** dal sistema: nasce una **distinta** di rimborso | ⛔ vietata | — |

⚠️ Le due regole sul destinatario le tiene anche il `CHECK` a database; sono
ripetute nel service **per farle arrivare come «campo mancante»** invece che
come violazione di vincolo. Non è una seconda sede della regola: se il `CHECK`
cambiasse, il rifiuto arriverebbe comunque, solo meno leggibile.

### `GET /api/v1/pagamenti/eccedenze/`

I documenti su cui è entrato più del dovuto, da `vw_eccedenze_da_sistemare`
(`security_invoker`: **va letta con la connessione dell'utente**). Filtri:
`chi_e_in_credito` (`CLIENTE` ha pagato più del dovuto · `AZIENDA` un documento
a credito su cui è entrato denaro), `billing_account_id`. Paginata, **ordinata
per cliente** di default.

⭐ **La vista porta già il raggruppamento per cliente in finestra**
(`eccedenza_cliente`, `documenti_cliente`): il backend non somma niente, e la
schermata nemmeno. Colonne: `fattura_id`, `fattura_numero`, `fattura_data`,
`emittente_soggetto_ruolo_id`, `cliente_soggetto_ruolo_id`,
`cliente_ragione_sociale`, `billing_account_id`, `totale_a_pagare`, `residuo`,
`eccedenza`, `chi_e_in_credito`, `eccedenza_cliente`, `documenti_cliente`,
`sistemazioni_in_bozza`, `sistemazioni_confermate`.

⭐ **L'elenco presenta, non sana**: nessuna riga ha un gemello automatico che la
corregge, perché sanarla vorrebbe dire muovere denaro senza che nessuno l'abbia
deciso.

### `POST /api/v1/pagamenti/sistemazioni/`

Registra la **decisione**.

```json
{ "fattura_origine_id": 820, "destinazione": "RIPORTO", "importo": "120.00",
  "fattura_destinazione_id": 831, "motivo": "Acconto sul documento successivo", "meta": {} }
```

Risponde `{ "sistemazione": {…} }`. ⚠️ **Registrare non è eseguire**: l'atto
nasce in `BOZZA` e il denaro si muove alla **conferma**. Fra i due momenti può
arrivare un altro incasso — ed è la ragione per cui il controllo dell'eccedenza
sta **là** e non qui: verificarla adesso darebbe una garanzia che scade.

🔴 **Cliente ed emittente non si passano**: li **deriva** il backend dalla
fattura di origine (`404 E_FATTURA_NON_TROVATA` se non c'è), perché non sono
una scelta di chi compila. Il guard del database li verifica con un codice
tecnico apposta.

⭐ Un `INSERT`, non una madre: una scrittura sola non ne ha bisogno.

### `GET /api/v1/pagamenti/sistemazioni/{sistemazione_id}/`

L'atto, col suo esito quando c'è:

```json
{ "data": { "sistemazione": {
    "id": 5, "destinazione": "RIPORTO", "stato": "CONFERMATA", "importo": "120.00",
    "motivo": "…",
    "fattura_origine_id": 820, "fattura_origine_numero": 815, "fattura_origine_anno": 2026, "fattura_origine_serie": "A",
    "fattura_destinazione_id": 831, "fattura_destinazione_numero": 826, "fattura_destinazione_anno": 2026, "fattura_destinazione_serie": "A",
    "cliente_soggetto_ruolo_id": 77, "cliente_ragione_sociale": "…", "emittente_soggetto_ruolo_id": 32,
    "contabile_id": null, "fondo_source_id": 402,
    "data_esecuzione": "2026-09-03T10:12:00+02:00", "user_esecuzione": "mario",
    "data_insert": "…", "user_insert": "mario", "meta": {} } } }
```

`stato ∈ {BOZZA, CONFERMATA, ANNULLATA}`. `contabile_id` e `fondo_source_id`
sono **l'esito**: uno dei due si valorizza alla conferma, a seconda della
strada che la madre ha scelto.

### `GET /api/v1/pagamenti/fatture/{fattura_id}/sistemazioni/` · `…/export/`

Gli atti registrati su un documento. ⭐ **Sono più di uno per natura**: si può
rimborsare una parte e riportare il resto. **Paginata dal 2026-09-02**, come
ogni lista configurabile: bundle standard `limit`/`offset` di
`parse_list_params`, envelope `{ "results": […], "count": N }`.

⛔ `order_by` **non** viene da `parse_list_params`, e non è una svista: quel
bundle ha un `order_by` di default (`descrizione`) che qui non è colonna di
niente. `order_dir` sì: assente è `None`, e decide il default DESC del
repository ([api.md](../../../dev/api.md) §`parse_list_params`).

L'**export** (`?formato=csv|xlsx`) è una rotta **sorella**, non una
sotto-risorsa dell'atto. Stesso `lista_codice` della lista a video
(`pagamenti.sistemazioni_fattura`): le colonne del file sono quelle che
l'operatore **vede**, non un elenco cablato. Esporta il **dataset**, non la
pagina, col guard di `build_export_response` che rifiuta **prima** di
serializzare invece di consegnare un file troncato. Contratto comune:
[api_export_liste.md](../../ui/manual/api_export_liste.md). ⛔ Nessun filtro
nell'intestazione del file: la fattura è nel path, non è una scelta.

### `POST /api/v1/pagamenti/sistemazioni/{sistemazione_id}/conferma/`

L'atto diventa un fatto. Una sola `SELECT pagamenti.fn_conferma_sistemazione(...)`,
che **sceglie la strada** (fondo, distinta negativa, compensazione) e ci mette
sopra il denaro — le tre strade sono un ramo **dentro** la funzione, e il
backend non le dispatcha.

```json
{ "ente_incasso_id": 7 }
```

⚠️ **Il canale del rimborso si chiede qui e non alla registrazione**: da quale
conto esce il bonifico è una decisione del momento in cui si paga. Sul
`RIMBORSO` è **obbligatorio** — senza, la madre rifiuta con
`E_CONTABILE_DATI_OBBLIGATORI` (400, campo `ente_incasso_id`); sulle altre due
destinazioni non serve. Risponde:

```json
{ "data": { "esito": { "contabile_id": null, "fondo_source_id": 402, "esito": "FONDO_CREATO" },
            "sistemazione": {…} } }
```

`esito ∈ {FONDO_CREATO, DISTINTA_RIMBORSO_CREATA, DISTINTA_COMPENSAZIONE_CREATA}`:
dice **quale specie di oggetto** è nata, e la colonna valorizzata fra
`fondo_source_id` e `contabile_id` è quella che lo identifica. La distinta del
rimborso e della compensazione **va poi registrata** come ogni altra (§3).

Rifiuti dalla madre: `E_SISTEMAZIONE_NON_CONFERMABILE` (409, non è in bozza),
`E_SISTEMAZIONE_ECCEDENZA_INSUFFICIENTE` (409, nel frattempo l'eccedenza è
calata), `E_SISTEMAZIONE_RIPORTO_NON_POSSIBILE` (409),
`E_ENTE_INCASSO_CONTO_NON_DI_INCASSO` (400), `E_CONFIG_MANCANTE` (500: un
centro interno o un pezzo di configurazione che manca — chi chiama non può
rimediare). Se la madre non rispondesse nessuna riga il backend solleva
`500 E_PAGAMENTI_CHIAMATA_NON_VALIDA`: tacere su un atto che ha mosso del
denaro è la cosa peggiore.

### `POST /api/v1/pagamenti/sistemazioni/{sistemazione_id}/annulla/`

L'atto si scarta e resta a registro con la sua ragione.

```json
{ "motivo": "Il cliente ha chiesto il rimborso" }
```

⚠️ **Il motivo è obbligatorio se l'atto non ne aveva già uno**: lo pretende il
guard sui dati (`E_SISTEMAZIONE_MOTIVO_OBBLIGATORIO`, 400), che sa se ce n'era
uno — il backend non replica la regola. Risponde `{ "sistemazione": {…} }`.

⭐ **E dal 2026-08-31 si annulla anche un atto CONFERMATO — sul solo
`RIPORTO`** (decisioni G-4/G-5 di Tid, rev. del trigger di transizione). Il
riporto lascia dietro un **fondo** in `vendite`, e per un fondo sbagliato non
c'era nessun rimedio: una sistemazione nuova non è la contropartita, perché
pretende un'eccedenza che quel riporto ha già consumato. L'annullo fa cadere
il fondo con l'atto, e la memoria di quando era stato eseguito resta nel
`meta` (`annullata_dopo_esecuzione`). È il verbo che
[api_fondi_fattura.md](../../vendite/manual/api_fondi_fattura.md) nomina come
strada per disfare un riporto sbagliato.

⛔ Su `RIMBORSO` e `COMPENSAZIONE` un atto confermato **non** si annulla
(`E_SISTEMAZIONE_ANNULLO_NON_AMMESSO`, 409), e il rifiuto **nomina
l'alternativa**: lì l'atto ha lasciato una **distinta**, e per una distinta
sbagliata il rimedio esiste già — la correzione guidata (§3). Aprire il varco
anche a loro darebbe due strade per disfare lo stesso fatto.

## 7. I canali di incasso — da dove arrivano i soldi

### `GET /api/v1/pagamenti/enti-incasso/`

Elenco paginato. Filtri: `tipo` (`BANCA` · `POSTE` · `PSP` · `ALTRO`, fuori
vocabolario → 400), `centro_riscossione_id`, `attivo`. Default `codice` ASC.
Cancello di perimetro emittente (`pagamenti.canali_incasso`,
`perimetro_emittente = t` a catalogo): vale l'emittente dell'operatore.

Ogni riga porta il **conto in chiaro**, ed è il punto:

```json
{ "id": 7, "codice": "BNK-01", "codice_interno": "BNK_01", "descrizione": "Conto incassi", "tipo": "BANCA", "attivo": true,
  "centro_riscossione_id": 3, "centro_codice": "BNK", "centro_descrizione": "Banca",
  "soggetto_ruolo_id": null, "soggetto_ragione_sociale": null,
  "bank_branch_id": 210, "bank_branch_nome": "…", "bank_branch_bank_code": "…",
  "soggetto_ruolo_conto_bancario_id": 55, "conto_iban": "IT00…", "conto_uso": "INCASSO",
  "conto_soggetto_ruolo_id": 32, "conto_istanza_utility_id": null, "conto_utility_descrizione": null,
  "formato_flusso": null, "regole_match": {}, "meta": {} }
```

⭐ Filiale e soggetto PSP **in chiaro**, e non è cosmesi: il drawer li mostra su
un canale già configurato, e senza il nome resterebbe un campo vuoto accanto a
un id valorizzato — cioè direbbe «non c'è filiale» di un canale `BANCA`, dove
la filiale è obbligatoria. `conto_utility_descrizione` `null` si legge
«nessuna utility», non come un campo vuoto (BE-11).

### `POST /api/v1/pagamenti/enti-incasso/`

```json
{ "codice": "BNK-01", "descrizione": "Conto incassi", "tipo": "BANCA",
  "soggetto_ruolo_conto_bancario_id": 55, "bank_branch_id": 210,
  "centro_riscossione_id": 3, "soggetto_ruolo_id": null,
  "formato_flusso": null, "regole_match": {}, "meta": {}, "attivo": true }
```

Obbligatori: `codice` (max 50), `descrizione`, `tipo`,
`soggetto_ruolo_conto_bancario_id`. Risponde `{ "ente_incasso": {…} }`.

🔴 **Il conto è obbligatorio su tutti i tipi, non solo su `BANCA`**: un canale
senza conto produrrebbe una coda di denaro che nessuno vede, e il conto è il
punto da cui il database ricava **di chi sono i soldi**. Un conto postale ha
un IBAN; il saldo di un PSP arriva sul conto di accredito dell'emittente.

⚠️ **La filiale è un fatto diverso dal conto e vale solo per la banca**: su
`BANCA` `bank_branch_id` è obbligatoria, su `POSTE`/`PSP`/`ALTRO` deve restare
`null` — ripetuto nel service per farlo arrivare come «campo di troppo» invece
che come violazione di `CHECK`. Su `PSP` il database pretende il soggetto
(`E_ENTE_INCASSO_PSP_SOGGETTO_RUOLO_OBBLIGATORIO`, `…_RUOLO_NON_PSP`,
`…_NON_CENSITO`), e rifiuta un conto che non sia di incasso
(`E_ENTE_INCASSO_CONTO_NON_DI_INCASSO`, 400). Codice duplicato → 400.

### `GET` / `PATCH /api/v1/pagamenti/enti-incasso/{ente_incasso_id}/`

Dettaglio e aggiornamento: entrambi rispondono `{ "ente_incasso": {…} }`
(il canale nella forma della riga di lista). Campi
compilabili: `codice`, `descrizione`, `tipo`, `attivo`,
`centro_riscossione_id`, `soggetto_ruolo_id`, `bank_branch_id`,
`soggetto_ruolo_conto_bancario_id`, `formato_flusso`, `regole_match`, `meta`.
⛔ **`codice_interno` non è aggiornabile**: è la chiave stabile con cui il
resto del sistema nomina il canale. `404 E_ENTE_INCASSO_NON_TROVATO`.

### `GET /api/v1/pagamenti/conti-incasso/?soggetto_ruolo_id=`

I **soli** conti con `uso = 'INCASSO'` del soggetto — quelli agganciabili a un
canale. `soggetto_ruolo_id` obbligatorio.

```json
{ "data": { "count": 1, "nessun_conto_di_incasso": false, "results": [
    { "soggetto_ruolo_conto_bancario_id": 55, "soggetto_ruolo_id": 32, "predefinito": true,
      "intestazione_dichiarata": "…", "conto_bancario_id": 9, "iban": "IT00…", "bic_swift": null,
      "intestatario_predefinito": "…", "conto_istanza_utility_id": null, "conto_utility_descrizione": null } ] } }
```

🔴 **Filtrato su `uso = 'INCASSO'` (BE-8), e non è comodità**: l'unicità «un
conto INCASSO → un solo soggetto» vive **solo** sulle righe con quell'uso — è
la garanzia da cui il database ricava di chi sono i soldi arrivati prima della
fattura. Il database rifiuterebbe gli altri con un errore parlante, ma un
elenco che li propone fa sbagliare, e chi sbaglia se ne accorge dopo aver
compilato tutto il resto.

⚠️ **Un elenco vuoto non è un guasto**: quel soggetto non ha ancora un conto di
incasso censito **a livello di ruolo** (D5: si fallisce alla configurazione,
non in esercizio). La risposta lo dice con `nessun_conto_di_incasso`, perché un
menu vuoto senza spiegazione sembra un errore dell'applicazione.

🔴 **Il perimetro lo tiene il repository, accanto all'SQL**:
`anagrafiche.soggetti_ruoli_conti_bancari` ha la row security **spenta di
proposito**, quindi su questa lettura il database non filtra niente. Un
`soggetto_ruolo_id` fuori dal perimetro emittente dell'operatore è un
**`403 E_SCOPE_EMITTENTE`** — trovato dalla riverifica E-4: l'operatore
dell'emittente 32 leggeva l'IBAN di incasso dell'emittente 44, nessun errore,
un elenco pieno. ⚠️ E il cancello rifiuta **prima** di chiedere a
`script.fn_check_user_emittente_scope`, che su un utente `NULL` risponde
`true` (regola «job batch»): «non so chi sei» vale **no**.

---

## Codici errore

Tutti a catalogo (`config.codici_errore`) con la loro classe; lo status si
deriva dalla classe. Quelli **sollevati dal backend** sono pochi: gli altri
arrivano dai guard e dalle madri, e il backend li fa passare intatti.

| Codice | HTTP | Chi lo solleva | Quando |
| --- | --- | --- | --- |
| `E_PAGAMENTI_VALIDATION` | 400 | backend | payload malformato, chiave fuori whitelist, vocabolario, importo non valido, dichiarazione a metà, motivo senza forzatura, rata/cliente/forzatura senza fattura alla nascita della riga, FK violata (tradotta con la frase del campo); su `da-rate/`: elenco vuoto, oltre 200, `scadenza_id` duplicato, **fatto comune** malformato — tutti **prima** del giro; su `distinte/`: `stato`/`origine` fuori vocabolario; su `rate/`: `order_by` fuori whitelist |
| `E_CONTABILE_NON_TROVATA` · `E_RIGA_CONTABILE_NON_TROVATA` · `E_SISTEMAZIONE_NON_TROVATA` · `E_ENTE_INCASSO_NON_TROVATO` · `E_RATA_NON_TROVATA` · `E_FATTURA_NON_TROVATA` | 404 | backend (fattura: anche il DB) | l'oggetto non c'è, **o il perimetro non lo lascia vedere**. ⚠️ Su `da-rate/` la rata assente non è un 404 della richiesta: è l'errore di **quella riga** dentro `falliti[]`, con status 200 |
| `E_CONTABILE_STATO_NON_CONFIGURATO` | 500 | backend | il codice di stato chiesto non risolve a catalogo: `UPDATE` a zero righe su un oggetto che esiste |
| `E_PAGAMENTI_CHIAMATA_NON_VALIDA` | 500 | backend | la madre della conferma non ha risposto nessuna riga |
| `E_SCOPE_EMITTENTE` | 403 | repository | `conti-incasso/` su un soggetto fuori perimetro |
| `E_UI_LISTA_EMITTENTE_DA_SCEGLIERE` | 422 | cancello di perimetro | lista con `lista_codice` chiesta da un multi-emittente senza emittente scelto |
| `E_CONTABILE_TRANSIZIONE_NON_AMMESSA` · `E_RIGA_CONTABILE_TRANSIZIONE_NON_AMMESSA` · `E_SISTEMAZIONE_TRANSIZIONE_NON_AMMESSA` | 409 | matrici DB | il passaggio di stato non è ammesso da dove si è |
| `E_CONTABILE_TOTALE_DICHIARATO_NON_QUADRA` · `E_CONTABILE_DATI_OBBLIGATORI` · `E_CONTABILE_CENTRO_ENTE_INCOERENTE` | 400 | guard DB | la distinta non quadra, o i suoi dati non stanno insieme |
| `E_CONTABILE_EMITTENTE_OBBLIGATORIO` · `E_CONTABILE_CANALE_DI_ALTRO_EMITTENTE` | 400 | `fn_get_emittente_distinta` (dal 2026-09-17) | nessun emittente risolvibile per una distinta senza canale (campo `emittente_fiscale_id`); il canale scelto è di un altro emittente (campo `ente_incasso_id`) |
| `E_CONTABILE_RIAPERTURA_NON_MANUALE` · `E_CONTABILE_CHIUSURA_CON_RIGHE_PRONTE` · `E_CONTABILE_NON_REGISTRABILE` · `E_CONTABILE_DICHIARAZIONE_NON_CORRISPONDE` · `E_CONTABILE_CORREZIONE_NON_REGISTRATA` · `E_CONTABILE_GIA_CORRETTA` · `E_CONTABILE_SISTEMAZIONE_CON_LOTTO` | 409 | guard e madri DB | lo stato della distinta non ammette il gesto |
| `E_RIGA_CONTABILE_DISTINTA_FINALE` · `E_RIGA_CONTABILE_SENZA_ABBINAMENTO` | 409 | guard DB | la riga non si lavora più, o non ha di che postare |
| `E_CONTABILE_VALIDAZIONE_RIGHE_NON_LAVORATE` | 409 | `fn_check_contabile_validabile` via guard di validazione (D20-a, dal 19/09) | si entra in `VALIDATA` con righe attive in uno stato `lavorata = false` (`DA_ABBINARE`, `IMPORTATA`). È il **primo motivo** della check, lo stesso che il dettaglio porta in `validazione_blocco_*` |
| `E_RIGA_CONTABILE_TARDIVA_STATO` · `E_RIGA_CONTABILE_TARDIVA_DISTINTA_NON_REGISTRATA` | 409 | `fn_posta_riga_tardiva` (D20-b, dal 19/09) | la riga non è `SOSPESA` · la distinta non è registrata (annullata, o ancora aperta: «usa il giro normale») |
| `E_RIGA_CONTABILE_DISTINTA_NON_MANUALE` · `E_RIGA_CONTABILE_DISTINTA_VALIDATA` | 409 | guard DB (`guard_contenuto`, dal 14/09) | non si elimina una riga di una generata/automatica · sotto una manuale validata il contenuto è fermo (righe nuove, fatti, eliminazioni). Sono i motivi 2 e 3 di `fn_check_riga_contabile_eliminabile`, gli stessi che spengono il cestino in lista |
| `E_RIGA_CONTABILE_ABBINAMENTO_INCOMPLETO` · `E_RIGA_CONTABILE_RATA_INCOERENTE` | 400 | guard DB | `ABBINATA` senza fattura/cliente · la rata non è di quella fattura |
| `E_RIGA_CONTABILE_CAPIENZA_SUPERATA` | 409 · `confirm_and_retry` | guard DB | non c'è spazio sulla rata: **confermabile** col secondo tempo |
| `E_SISTEMAZIONE_NON_CONFERMABILE` · `…_ECCEDENZA_INSUFFICIENTE` · `…_RIPORTO_NON_POSSIBILE` · `…_IMMUTABILE` · `…_ANNULLO_NON_AMMESSO` | 409 | guard e madre DB | l'atto non è nello stato per quel verbo, o il mondo è cambiato sotto. `ANNULLO_NON_AMMESSO` nomina l'alternativa (la correzione guidata) |
| `E_SISTEMAZIONE_DOCUMENTI_INCOERENTI` · `…_DOCUMENTI_NON_ABBINABILI` · `…_MOTIVO_OBBLIGATORIO` | 400 | guard DB | i due documenti non stanno insieme · manca la ragione |
| `E_ENTE_INCASSO_CONTO_NON_DI_INCASSO` · `…_SENZA_CENTRO` · `…_PSP_SOGGETTO_RUOLO_OBBLIGATORIO` · `…_PSP_RUOLO_NON_PSP` | 400 | guard DB | il canale è configurato male |
| `E_ENTE_INCASSO_PSP_NON_CENSITO` | 409 | guard DB | il PSP indicato non è censito |
| `E_CONFIG_MANCANTE` | 500 | madre DB | alla conferma manca un pezzo di configurazione (un centro interno): chi chiama non può rimediare |

⚠️ **Ogni codice vivo ha il suo ripiego senza segnaposto** in
`error_messages_fallback.py` (`test_ogni_codice_vivo_ha_un_messaggio_di_ripiego`).
I tre codici della compensazione ritirati il 22/08
(`E_CONTABILE_COMPENSAZIONE_*`) restano a catalogo come `obsoleto_dal` e non
li solleva più nessuno.

## Dipendenze DB

| Oggetto | Ruolo |
| --- | --- |
| `pagamenti.fn_get_or_create_vendite_contabile` | l'apertura della distinta manuale (*get or create*, l'operatore lo mette la funzione) |
| `pagamenti.fn_get_emittente_distinta` · `trgfn_vendite_contabili_emittente` · `trgfn_vendite_contabili_gen_codice` | la sede unica dei quattro livelli di risoluzione dell'emittente, il trigger che la applica a ogni scrittura e il numeratore sul registro `DISTINTA` (dal 2026-09-17) |
| `pagamenti.fn_posta_contabile(p_contabile_id, p_righe_attese, p_totale_atteso)` | ⭐ **la madre della registrazione**: atomica, non solleva su `NULLA_DA_POSTARE`, porta la distinta a `CHIUSA` |
| `pagamenti.fn_crea_distinta_correzione` | la correzione guidata: la distinta a segno opposto |
| `pagamenti.fn_get_saldo_rata(p_scadenza_id, p_escludi_contabile_riga_id)` · `fn_get_saldo_fattura(p_fattura_id, p_escludi_contabile_riga_id)` · `fn_get_saldo_fattura_contabili(idem)` | i tre numeri, letti **solo** da `saldi_service`. Il secondo parametro sul documento dal 18/09 (P-6, `20260918-01/-02`) |
| `pagamenti.fn_get_saldi_rate(p_scadenza_ids bigint[], p_escludi)` | ⭐ **il nucleo** dei saldi di rata (dal 17/09, P-3): la «porta 3» del backend — una chiamata con l'**array della pagina** (`get_saldi_rate`), mai `LATERAL` per riga e mai `NULL` per «tutte» (per quello c'è `vw_saldi_rate`). Una rata fuori perimetro è **zero righe**, non un errore |
| `vendite.vw_fatture_scadenze_lista` | la sorgente di `rate/` (una riga per rata col documento, `security_invoker`): la lista 68 la pagina, i saldi arrivano dopo dal nucleo |
| `vendite.fn_numero_documento_fattura(numero, serie)` | la **sede unica** del numero parlante: `_RIGA_COLONNE` lo legge da lì (`fattura_numero_documento`), la vista rate e `vw_rate_fuori_capienza` pure — nessuna composizione in Python o nel FE |
| `pagamenti.fn_conferma_sistemazione(p_sistemazione_id, p_ente_incasso_id)` · `fn_annulla_sistemazione(p_sistemazione_id, p_motivo)` | i due verbi dell'atto |
| `pagamenti.vw_rate_fuori_capienza` · `vw_eccedenze_da_sistemare` | le due liste che «rendono onesta» la forzatura e presentano il denaro di troppo — `security_invoker` |
| `pagamenti.vendite_contabili_stati` · `vendite_contabili_righe_stati` | i due cataloghi di stato coi flag `is_final`, `is_postabile`, `richiede_abbinamento` |
| `script.fn_check_azione_processo('registra_distinta')` | il cancello dei due gesti irreversibili |
| `anagrafiche.soggetti_ruoli_conti_bancari` (`uso = 'INCASSO'`) | i conti agganciabili a un canale — **senza RLS**, perimetro nel repository |

Firme lette dalla doc auto-generata in
[dbzero/pagamenti](../../../dbzero/pagamenti/index.md); il modello e le
decisioni nella guida [gestione-dei-pagamenti](../../../guide/gestione-dei-pagamenti.md).

## Note

- **Prove**: `apps/pagamenti/tests/{api,services,db}/` — unitari coi
  repository mockati, più i presidi sul DB provvisto (ogni colonna dichiarata
  ordinabile è provata con `EXPLAIN` su ogni lista; il perimetro di
  `conti-incasso/` è provato **rimettendo il difetto**, perché un doppio non ha
  un perimetro). ⛔ Le tre madri non sono mai state chiamate nei test, nemmeno
  sotto `EXPLAIN`: registrare è irreversibile — si verifica che i **nomi dei
  parametri** esistano nel catalogo di PostgreSQL.
- **Collaudo a video**: [collaudo-in-app-incassi-distinte-e-sistemazioni.md](../../../dev/work-in-progress/collaudo-in-app-incassi-distinte-e-sistemazioni.md)
  — non parte finché `registra_distinta` non è assegnata a un profilo.
- **Frontend**: `frontend/src/pagamenti/` (5 view, 3 drawer, 6 dialoghi — dal 17/09 il picker delle rate `RatePickerDialog`, singolo dal form e multiplo dalla toolbar delle righe);
  i vocabolari copiati nel FE sono **solo** quelli senza catalogo
  (`vocabolari.js`); gli stati arrivano dal dettaglio.
