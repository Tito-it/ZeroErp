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
| [brief-db-posting-e-abbinamento-rata.md](../../../dev/work-in-progress/brief-db-posting-e-abbinamento-rata.md) | il lato **database**: sette lotti, 15 guard, 2 matrici di transizione, la RLS |
| [brief-be-fe-posting-e-abbinamento-rata.md](../../../dev/work-in-progress/brief-be-fe-posting-e-abbinamento-rata.md) | il piano **BE/FE**, le nove domande chiuse, lo stato di sviluppo |

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
| `GET`/`PATCH` | `distinte/{contabile_id}/` | dettaglio con righe e cataloghi · i campi compilabili | — | area |
| `POST` | `distinte/{contabile_id}/stato/` | il percorso della distinta: `VALIDATA` · `BOZZA` · `ANNULLATA` | ✅ | area |
| `GET`/`POST` | `distinte/{contabile_id}/righe/` | le righe · un importo arrivato | ✅ su POST | area |
| `GET` | `distinte/{contabile_id}/anteprima-registrazione/` | la fotografia di ciò che succede se si registra adesso | — | area |
| `POST` | `distinte/{contabile_id}/registra/` | ⭐ **la madre**: registra, una sola `SELECT` | ✅ | `registra_distinta` |
| `POST` | `distinte/{contabile_id}/correggi/` | la **correzione guidata**: una distinta nuova a segno opposto | ✅ | `registra_distinta` |
| `PATCH` | `righe/{riga_id}/` | i **fatti** della riga (come è arrivato il denaro) | — | area |
| `POST` | `righe/{riga_id}/stato/` | il percorso della riga | ✅ | area |
| `POST` | `righe/{riga_id}/abbina/` | fattura + cliente + rata, e la **forzatura a due tempi** | ✅ | area |
| `GET` | `righe/` | la coda del riconciliatore, cross-distinta (`?coda=`) | — | area |
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
`rate/fuori-capienza/` prima di `rate/{id}/saldo/`. Non è un dettaglio del
file: è la ragione per cui `fuori-capienza` non viene letto come un id.

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
| Paginazione | **page-based**: `page` (default 1), `page_size` (default 50, max 200). Risposta `{count, page, page_size, total_pages, results}`. ⛔ `count` viene da `COUNT(*) OVER ()` nella stessa valutazione, mai da `len(results)` |
| Ordinamento | `order_by` su una **whitelist per lista** (tabella sotto) — il nome è quello **fisico** della colonna, come la lista lo espone; `order_dir` `asc\|desc`. Fuori whitelist → `400 E_PAGAMENTI_VALIDATION` |
| Query param opzionali | contratto degli helper `qp_*_optional`: vuoto = assente, malformato = `400` |
| Vocabolari a `CHECK` | `stato`, `origine`, `coda`, `motivo`, `chi_e_in_credito`, `tipo`, `destinazione`: un valore fuori vocabolario è un **400**, mai una lista vuota — su due valori possibili una lista vuota è indistinguibile da «non c'è niente», cioè dalla risposta più rassicurante |
| `Idempotency-Key` | obbligatoria su **ogni** `POST` (creazioni, verbi, cambi di stato). ⚠️ Sui `PATCH` no: passano da `request.data`, non da `handle_post_json` |
| 404 | «non esiste» e «non lo vedi» (RLS) danno la **stessa** risposta, di proposito: dire «esiste ma non è tuo» racconterebbe a chi è fuori perimetro che quel documento c'è |
| Cancello di perimetro emittente | le liste con `lista_codice` (`pagamenti.distinte`, `.righe`, `.rate_fuori_capienza`, `.eccedenze`, `.sistemazioni_fattura`, `.canali_incasso`) passano dal cancello di [`perimetro_emittente`](../../ui/manual/api_export_liste.md): un operatore **multi-emittente** senza emittente scelto riceve `422 E_UI_LISTA_EMITTENTE_DA_SCEGLIERE`. Non è un permesso: è «scegli prima da dove guardi» |
| `?format=` | ⛔ mai: è un parametro magico di DRF e la richiesta muore con **404** prima di arrivare alla view. Il parametro dell'export si chiama **`formato`** |

**Le whitelist di ordinamento**, con il default e il suo verso:

| Lista | `order_by` ammessi | Default |
| --- | --- | --- |
| `distinte/` | `data_contabile` · `codice` · `stato_descrizione` · `origine` · `centro_descrizione` · `totale_righe` | `data_contabile` DESC |
| `righe/` | `data_pagamento` · `importo` · `stato_descrizione` · `contabile_codice` | `data_pagamento` DESC |
| `rate/fuori-capienza/` | `data_scadenza` · `motivo` · `residuo` · `importo_rata` · `fattura_numero` | `data_scadenza` DESC |
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
liste lo applica il frontend).

⭐ **`origine` non è un dettaglio tecnico**: dice a chi guarda se sta vedendo
il lavoro di una persona (`MANUALE`), la contabilità interna scritta dal giro
dei fondi fattura (`GENERATA`) o un import (`AUTOMATICA`).

Ogni riga è una `DistintaRow`:

```json
{
  "id": 12, "codice": "DST-0000012",
  "centro_riscossione_id": 3, "centro_codice": "BNK", "centro_descrizione": "Banca",
  "ente_incasso_id": 7, "ente_codice": "BNK-01", "ente_descrizione": "Conto incassi",
  "data_contabile": "2026-09-01", "data_registrazione": "2026-09-01",
  "stato_id": 41, "stato_codice": "BOZZA", "stato_descrizione": "Bozza", "stato_is_final": false,
  "origine": "MANUALE", "importo_dichiarato": "1500.00",
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

### `POST /api/v1/pagamenti/distinte/`

Apre — o **ritrova** — la distinta manuale dell'operatore.

```json
{ "centro_riscossione_id": 3, "data_contabile": "2026-09-01",
  "ente_incasso_id": 7, "importo_dichiarato": "1500.00", "meta": {} }
```

`centro_riscossione_id` e `data_contabile` obbligatori; `ente_incasso_id`,
`importo_dichiarato`, `meta` facoltativi. Nasce `origine = MANUALE`, stato
`BOZZA`.

⭐ **È un *get or create*** (`fn_get_or_create_vendite_contabile`): se
l'operatore riapre con gli stessi dati — stessa giornata, stesso centro,
stesso canale, **stessa persona** — il database non ne crea una seconda, gli
ridà la sua. La distinta manuale è **proprietà** di chi la lavora (D12-a), ed è
ciò che rende inutile qualunque lock. Da cui la risposta:

```json
{ "data": { "distinta": {…}, "righe": […], "stati_distinta": […], "stati_riga": […],
            "stati_richiedibili": {…}, "gia_popolata": true } }
```

È il dettaglio (sotto) più **`gia_popolata`**: `true` se la distinta
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

Testata, righe e **i due cataloghi di stato** in un round-trip:

```json
{ "data": {
    "distinta": { …DistintaRow… },
    "righe": [ …RigaContabileRow… ],
    "stati_distinta": [ {"id", "codice", "codice_interno", "descrizione", "is_final", "ordine"} ],
    "stati_riga":     [ {…, "is_postabile", "richiede_abbinamento"} ],
    "stati_richiedibili": { "distinta": ["VALIDATA", "BOZZA", "ANNULLATA"],
                            "riga": ["DA_ABBINARE", "ABBINATA", "SOSPESA", "SCARTATA"] }
} }
```

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

### `GET /api/v1/pagamenti/distinte/{contabile_id}/righe/`

Le righe attive della distinta: `{ "count": N, "results": [ …RigaContabileRow… ] }`.
Non paginata: le righe di una distinta sono limitate per costruzione.

```json
{ "id": 91, "contabile_id": 12, "importo": "500.00",
  "riferimento_ente": "TRN 2026…", "data_pagamento": "2026-08-30",
  "data_valuta": null, "data_operazione": null,
  "fattura_id": 820, "fattura_numero": 815, "fattura_anno": 2026, "fattura_serie": "A",
  "billing_account_id": 44, "billing_account_codice": "BA-000044", "billing_account_descrizione": "…",
  "scadenza_id": 1301, "scadenza_numero_rata": 2, "scadenza_data": "2026-09-30",
  "forzata": false, "motivo_forzatura": null,
  "stato_id": 52, "stato_codice": "ABBINATA", "stato_descrizione": "Abbinata",
  "stato_is_postabile": true, "stato_richiede_abbinamento": true,
  "motivo_sospeso": null, "fondo_source_id": null, "attivo": true, "meta": {} }
```

⚠️ `fattura_numero` è un **bigint**, non una stringa: è il progressivo, e la
forma leggibile (serie/anno/numero) la compone chi la mostra.

### `POST /api/v1/pagamenti/distinte/{contabile_id}/righe/`

```json
{ "importo": "500.00", "riferimento_ente": "TRN …", "data_pagamento": "2026-08-30",
  "data_valuta": null, "data_operazione": null, "motivo_sospeso": null, "meta": {} }
```

Solo `importo` obbligatorio. Risponde `{ "riga": {…} }`.

⭐ **Nasce `DA_ABBINARE`**: quando il denaro arriva non si sa ancora di chi sia,
e quello stato dice esattamente questo. Chi sa già la fattura la abbina subito
dopo, col verbo dell'abbinamento (§4). Su una distinta in stato finale il
database rifiuta (`E_RIGA_CONTABILE_DISTINTA_FINALE`, 409).

⚠️ **Un importo è un `Decimal` esatto letto dalla forma testuale** — `NaN` e
`Infinity` sono rifiutati, e un booleano non è un importo: ogni somma che
incontra un `NaN` diventa `NaN`, e un totale `NaN` **non si vede**, si legge
come un campo vuoto.

### `PATCH /api/v1/pagamenti/righe/{riga_id}/`

I **fatti** della riga — come è arrivato il denaro: `importo`,
`riferimento_ente`, `data_pagamento`, `data_valuta`, `data_operazione`,
`motivo_sospeso`, `meta`. ⛔ **Non l'abbinamento**: `fattura_id`,
`billing_account_id`, `scadenza_id` non sono accettati qui — abbinare è un
verbo, perché porta con sé la rata e la forzatura, ed è una decisione, non la
correzione di un dato digitato male. Risponde `{ "riga": {…} }`.

⭐ Le righe sono indirizzate **per id proprio**, non sotto la distinta: una
riga si lavora anche dalla coda del riconciliatore, dove la distinta di
appartenenza non è il contesto.

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

`fattura_id` e `billing_account_id` obbligatori. ⚠️ **La rata resta
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
`incassato`, `in_lavorazione`, `righe_forzate`, `motivi_forzatura`. Le ultime
due sono ciò che la forzatura ha lasciato scritto: **è così che resta onesta**.

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

⚠️ Residuo e «in lavorazione» escono da **una** lettura (`CROSS JOIN` fra le
due funzioni): letti separati sarebbero due istanti diversi, e un residuo di
prima accanto a un «in lavorazione» di dopo sono due numeri veri che insieme
raccontano una cosa falsa. `404 E_FATTURA_NON_TROVATA` — lo solleva il
database.

### `GET /api/v1/pagamenti/fatture/{fattura_id}/rate/`

Le rate della fattura, **ciascuna col suo saldo**, in un giro solo:

```json
{ "data": { "count": 3, "results": [
    { "scadenza_id": 1301, "numero_rata": 1, "data_scadenza": "2026-08-31", "importo": "500.00",
      "residuo": "0.00", "in_lavorazione": "0.00", "incassato": "500.00", "has_movimenti": true },
    … ] } }
```

È la risposta a «su quale rata metto questi soldi?», e la consuma il form
dell'abbinamento: N chiamate per disegnare un menu sono N modi di essere
lenti. ⚠️ Nessun 404 sulla fattura: una fattura senza rate risponde
`count: 0`.

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

⛔ `order_by`/`order_dir` **non** vengono da `parse_list_params`, e non è una
svista: quel bundle ha un `order_by` di default (`descrizione`) che qui non è
colonna di niente, e normalizza l'assenza di `order_dir` ad `asc` — quindi il
default DESC del repository non verrebbe **mai** raggiunto. Nessun errore, solo
un elenco al contrario ([api.md](../../../dev/api.md) §`parse_list_params`).

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

Dettaglio (stessa forma della riga di lista) e aggiornamento dei campi
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
| `E_PAGAMENTI_VALIDATION` | 400 | backend | payload malformato, chiave fuori whitelist, vocabolario, importo non valido, dichiarazione a metà, motivo senza forzatura, FK violata (tradotta con la frase del campo) |
| `E_CONTABILE_NON_TROVATA` · `E_RIGA_CONTABILE_NON_TROVATA` · `E_SISTEMAZIONE_NON_TROVATA` · `E_ENTE_INCASSO_NON_TROVATO` · `E_RATA_NON_TROVATA` · `E_FATTURA_NON_TROVATA` | 404 | backend (fattura: anche il DB) | l'oggetto non c'è, **o il perimetro non lo lascia vedere** |
| `E_CONTABILE_STATO_NON_CONFIGURATO` | 500 | backend | il codice di stato chiesto non risolve a catalogo: `UPDATE` a zero righe su un oggetto che esiste |
| `E_PAGAMENTI_CHIAMATA_NON_VALIDA` | 500 | backend | la madre della conferma non ha risposto nessuna riga |
| `E_SCOPE_EMITTENTE` | 403 | repository | `conti-incasso/` su un soggetto fuori perimetro |
| `E_UI_LISTA_EMITTENTE_DA_SCEGLIERE` | 422 | cancello di perimetro | lista con `lista_codice` chiesta da un multi-emittente senza emittente scelto |
| `E_CONTABILE_TRANSIZIONE_NON_AMMESSA` · `E_RIGA_CONTABILE_TRANSIZIONE_NON_AMMESSA` · `E_SISTEMAZIONE_TRANSIZIONE_NON_AMMESSA` | 409 | matrici DB | il passaggio di stato non è ammesso da dove si è |
| `E_CONTABILE_TOTALE_DICHIARATO_NON_QUADRA` · `E_CONTABILE_DATI_OBBLIGATORI` · `E_CONTABILE_CENTRO_ENTE_INCOERENTE` | 400 | guard DB | la distinta non quadra, o i suoi dati non stanno insieme |
| `E_CONTABILE_RIAPERTURA_NON_MANUALE` · `E_CONTABILE_CHIUSURA_CON_RIGHE_PRONTE` · `E_CONTABILE_NON_REGISTRABILE` · `E_CONTABILE_DICHIARAZIONE_NON_CORRISPONDE` · `E_CONTABILE_CORREZIONE_NON_REGISTRATA` · `E_CONTABILE_GIA_CORRETTA` · `E_CONTABILE_SISTEMAZIONE_CON_LOTTO` | 409 | guard e madri DB | lo stato della distinta non ammette il gesto |
| `E_RIGA_CONTABILE_DISTINTA_FINALE` · `E_RIGA_CONTABILE_SENZA_ABBINAMENTO` | 409 | guard DB | la riga non si lavora più, o non ha di che postare |
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
| `pagamenti.fn_posta_contabile(p_contabile_id, p_righe_attese, p_totale_atteso)` | ⭐ **la madre della registrazione**: atomica, non solleva su `NULLA_DA_POSTARE`, porta la distinta a `CHIUSA` |
| `pagamenti.fn_crea_distinta_correzione` | la correzione guidata: la distinta a segno opposto |
| `pagamenti.fn_get_saldo_rata(p_scadenza_id, p_escludi_contabile_riga_id)` · `fn_get_saldo_fattura` · `fn_get_saldo_fattura_contabili` | i tre numeri, letti **solo** da `saldi_service` |
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
- **Frontend**: `frontend/src/pagamenti/` (6 pagine, 3 drawer, 4 dialoghi);
  i vocabolari copiati nel FE sono **solo** quelli senza catalogo
  (`vocabolari.js`); gli stati arrivano dal dettaglio.
