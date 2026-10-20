# API giornale fattura — la storia del documento (Django)

## Scopo

Rispondere a una domanda sola: **«cosa è successo a questo documento, in ordine
di tempo»**. Elenco paginato e di sola lettura, che alimenta la scheda
**«Storia»** del `FatturaDrawer`.

⛔ **Non è il pannello «Collegamenti»** (`/passaggi/`). Quello dice **con quali
altri documenti** la fattura è legata; questo dice **cosa le è successo**. Due
domande diverse, due sorgenti diverse — e vivono in due schede accanto.

⛔ **Non è il Passo B.** Nessun aggregato, nessuna finestra temporale, nessun
conteggio per periodo: quelli hanno prerequisiti loro.

## Contesto

È il **Passo A** del filone osservabilità
([analisi-osservabilita-log.md](../../../dev/work-done/analisi-osservabilita-log.md)),
e il **primo consumatore** di `script.vw_giornale_entita` — la vista che cuce i
registri di evento del progetto in una forma normalizzata (lotto L3 del
[brief event_log](../../../dev/work-done/brief-db-event-log-scope-e-riga-parlante.md)).

⭐ **Fino al 2026-08-24 quella vista non l'aveva interrogata nessuno**: il suo
perimetro era verificato dal pgTAP e non dall'uso. Scriverne il primo lettore
era anche il suo collaudo, ed è stato messo in conto come lavoro.

**Perché la fattura e non il lotto.** Perché la storia di un lotto **non
contiene** quella delle sue fatture — sono due entità diverse e la vista le
tiene separate. Sul caso sporco misurato, le 213 righe del lotto dicevano otto
volte «Esito fatture lotto · WARN», e la frase che serviva stava solo sulla
fattura. Il lotto arriva dopo, quando si deciderà cos'è un «caso».

View: `ApiFatturaGiornale` (`apps.vendite.api.fatture_views`) →
service `get_fattura_giornale` (`apps.vendite.services.vendite_service`) →
`VenditeRepository.list_giornale_entita`.

## Input

- Metodo: `GET`
- Path: `/api/v1/vendite/fatture/<fattura_id>/giornale/`
- Header: `Authorization: Bearer <access_token>`

⭐ **Dal 2026-09-27 è la lista a catalogo `vendite.giornale`** (lista 79, la
stessa del giornale trasversale e della Storia del lotto —
[brief-db-liste-datatable-grezze §3.1](../../../dev/work-done/brief-db-liste-datatable-grezze.md),
decisione di Tid): contratto di lista standard, dichiarato una volta per le due
Storie in `apps/vendite/api/_giornale_params.py`. ⛔ Il vecchio contratto
(`page`/`page_size`/`sort_by`/`sort_dir`) non è più letto.

| Query param | Default | Cosa fa |
| --- | --- | --- |
| `limit` | `25` | Righe per pagina, riportato in `[1, 200]`: fuori limiti non è un `400` (`parse_list_params`) |
| `offset` | `0` | Scostamento, riportato a `≥ 0`; la `page` della risposta si ricava da qui |
| `order_by` | `quando` | Colonna di ordinamento (`campo_sorgente` del catalogo): `quando` o `gravita`. ⛔ Fuori whitelist → **400** `E_VENDITE_VALIDATION`: una lista ordinata diversamente da come è stata chiesta non solleva niente |
| `order_dir` | *(assente = `desc`)* | Verso: `desc` o `asc` |
| `emittente_soggetto_ruolo_id` | — | L'emittente (soggetto-ruolo) del documento. È il `lista_emittente_param` della view: la lista è `perimetro_emittente` e **non** `multi_emittente`, e senza chi ha più emittenti nello scope riceverebbe `E_UI_LISTA_EMITTENTE_DA_SCEGLIERE` dentro il drawer. ⚠️ **Non filtra** le righe: il perimetro è la fattura del path, e a dire se la si vede è il cancello di testata |
| `ritirate` | `false` | Include anche le segnalazioni **ritirate**, di default nascoste. Strict: un valore non booleano è un 400 |

## Output

- `200`: envelope paginato standard

```json
{
  "data": {
    "fattura_id": 19563,
    "count": 2,
    "page": 1,
    "page_size": 25,
    "total_pages": 1,
    "ritirate_count": 1,
    "results": [
      {
        "riga_key": "FATTURA_LOG:4006",
        "registro": "FATTURA_LOG",
        "quando": "2026-08-24T11:57:09+02:00",
        "gravita": "ERROR",
        "cosa": "Non si può numerare il documento: rettifica righe di altri documenti che non risultano ancora numerati. Documenti da numerare prima: 1.",
        "tx_id": null,
        "correlation_id": null,
        "auth_user_id": null,
        "user_insert": "tid",
        "ritirata": false,
        "entity_type": "FATTURA",
        "entity_id": 19563,
        "etichetta_key": null,
        "entita_display": "19563 - A"
      }
    ]
  },
  "meta": { "request_id": "…" }
}
```

⭐ **`etichetta_key` — dal 2026-08-31.** L'indirizzo i18n del fatto, da
`config.eventi_dominio.etichetta_key`, per le sole righe del registro
**`EVENT_LOG`**: là `cosa` è il **codice** dell'evento, mentre sugli altri tre
registri è già una frase e il campo è `null`. Si rende con
`labelOrCode(t, te, etichetta_key, cosa)` — ⚠️ il ripiego è il **codice grezzo**,
mai il path della chiave, ed è la ragione per cui il campo può restare `null`
senza che nessuno veda un buco: `event_log` **non ha** una FK verso quel
catalogo (deliberato: il diario non deve smettere di scrivere per un problema di
configurazione), quindi un codice non dichiarato è un caso previsto.

🔴 **Perché è arrivato solo ora**: il catalogo dichiarava quell'indirizzo dal
primo giorno e **non lo leggeva nessuno** — le sei chiavi `config.eventi_dominio.*`
non esistevano nei `locales` e la vista non le esponeva. Era un contratto
*emesso, trasportato e non consumato*: la stessa forma di `ui_action`, e la
ragione per cui [api.md](../../../dev/api.md) prescrive di **verificare che il
client la legga** prima di dichiarare fatta una capability. Se ne è accorto
l'arrivo di `LOTTO_RIAPERTO` (2026-08-31), che a video sarebbe comparso come
codice macchina.

⭐ **`entita_display` — dal 2026-09-27** anche qui (prima solo nel giornale
trasversale): è la colonna «Riferimento» della lista a catalogo, risolta sulla
pagina da `_aggiungi_entita_display`, che ora chiama il corpo comune
`_list_giornale` per tutti e tre i lettori.

- `400`: `E_VENDITE_VALIDATION` — `fattura_id` non positivo, `order_by`/`order_dir` fuori whitelist (la paginazione fuori limiti viene riportata nei limiti, non rifiutata); `E_VALIDATION_INPUT` — `ritirate` non booleano
- `403`: area `vendite` BLOCCATA, oppure oggetto `vendite.fattura` bloccato
- `404`: `E_FATTURA_NON_TROVATA` — inesistente **oppure fuori scope emittente**

## Regole

### 🔴 Il cancello è la testata, e qui non è ridondante

`script.vw_giornale_entita` è `security_invoker`: su una fattura fuori scope la
RLS la fa rispondere **zero righe**. Zero righe è una frase, e dice *«a questo
documento non è successo niente»* — che è **diversa** da *«questo documento non
lo vedi»*.

Il service carica **prima** la testata (`get_fattura_testata`) e si ferma con
404 se è `None`; solo dopo legge il giornale.

Verificato sul database, fattura 19563:

| Contesto | La vista da sola | L'endpoint |
| --- | --- | --- |
| con contesto operatore | 3 righe | 3 righe |
| **senza contesto** (fail-closed) | **0 righe** | **`E_FATTURA_NON_TROVATA`** |

⚠️ Presidiato da `test_giornale_non_letto_se_testata_none`: senza quel test la
regressione sarebbe **silenziosa**, perché la risposta sbagliata è un `200` con
un elenco vuoto — che non somiglia a un difetto.

### ⭐ L'ordine di default è il TEMPO, dal più recente *(dal 2026-09-27)*

È il preset della lista a catalogo (`giornale_default`, `quando desc`), e la sede
è una per i tre lettori: `GIORNALE_ORDINE_DEFAULT` in `vendite_repository.py`.
La gravità resta a un clic, sulla sua colonna.

📌 **Dal 2026-08-24 al 2026-09-27 il default era la GRAVITÀ** (Tid, dopo la
validazione in-app: davanti a un documento la prima domanda è «c'è qualcosa che
non va?»). Quella domanda ha ora una risposta sua: il banner in testa al drawer
legge `errore_vivo` dal **dettaglio** della fattura
(`VenditeRepository.get_giornale_errore_vivo`, la riga ERROR più recente e non
ritirata) e non dipende più dall'ordine della pagina — che il preset o
l'operatore possono cambiare.

```sql
ORDER BY t.quando DESC, t.riga_id DESC                          -- default
ORDER BY t.rango_gravita DESC, t.quando DESC, t.riga_id DESC   -- order_by=gravita
```

⛔ **L'ordinamento è del server, e non è pignoleria**: la lista è **paginata**,
quindi riordinare nel client riordinerebbe la sola pagina caricata — «il più
grave» diventerebbe «il più grave fra i primi 50 in ordine di tempo», senza
dirlo. È un difetto silenzioso: a video un elenco ordinato male somiglia in
tutto a uno ordinato bene. *(Lato frontend la lista è `<ListaConfigurabile>`
paginata dal server, nel tab condiviso `GiornaleEntitaTab`.)*

⚠️ **Il rango non è la colonna**: il vocabolario normalizzato della vista è
testuale — `INFO | WARN | ERROR` — e ordinarlo per testo darebbe **ERROR < INFO
< WARN**, cioè un ordine alfabetico spacciato per una scala. Il rango si calcola
nella CTE.

⚠️ **`NULL` pesa come un `ERROR`, non come un `INFO`.** La vista dichiara che una
gravità nulla significa *«un vincolo si è allargato e la mappa è rimasta
indietro»*: mandarla in fondo la renderebbe invisibile dalla seconda pagina in
giù, che è il modo più efficace di nascondere un difetto. A video resta
distinguibile — trattino e colore neutro — quindi nessuno la scambia per un
errore vero. *(Stesso criterio già scritto in `ErroreRigaInfo`: una segnalazione
che non sa dire quanto pesa si mostra forte, non sottovoce.)*

### ⛔ E il tempo, da solo, non ordina

`event_time` e `data_ora` hanno default `now()`, che in PostgreSQL è il
timestamp di **transazione**, non `clock_timestamp()`. Misurato: 38 righe di un
lotto su **3 istanti distinti**, uno per corsa.

Per questo il tempo porta sempre con sé il tiebreak `riga_id`, che è l'ordine di
**scrittura** — ed è la sequenza vera finché il registro è **uno solo** (oggi,
per la fattura, `fatture_log`).

⚠️ Il giorno in cui una fattura avrà righe da **due** registri, dentro lo stesso
istante l'ordine tornerà arbitrario: lì servirà una sequenza vera, non questo
ripiego.

⭐ **Dentro la stessa gravità il tempo resta DISCENDENTE anche con
`order_dir=asc`**, ed è una scelta: *«i meno gravi prima»* non vuol dire *«i più
vecchi prima»*. Presidiato da un test apposta.

### Le segnalazioni ritirate si nascondono, e il numero le dichiara

`disabilitato` è la segnalazione **ritirata**: quella di un tentativo poi
rifatto. Sul caso misurato è *letteralmente la stessa frase* di quella viva —
mostrarle entrambe fa credere che sia successo due volte.

⛔ **Il filtro è sul server**, non nel client: la lista è paginata lato server e
filtrare a valle filtrerebbe solo la pagina visibile.

⚠️ **`ritirate_count` non è un accessorio**: senza, *«nessun evento»* e *«tre
eventi, tutti superati»* si leggono uguali. Il frontend rende tre vuoti distinti,
e il terzo — *«non sono riuscito a chiederlo»* — non è nessuno dei due.

📌 `?ritirate=1` le rimette dentro; lì `ritirate_count` vale `0`, perché non c'è
più niente di nascosto da dichiarare.

### I due `NULL` di `disabilitato` non sono lo stesso NULL

| Registro | `disabilitato` | Perché |
| --- | --- | --- |
| `FATTURA_LOG` · `LOTTO_LOG` | valorizzato | la colonna esiste nella sorgente |
| `EVENT_LOG` | `NULL` | il concetto **non esiste**: append-only, un evento è un fatto accaduto |
| `TASK_RUN` | `NULL` | il ritiro esiste ma su un **altro asse** — `attivo` spegne il *tentativo*, `disabilitato` ritira un *segnale* |

Il repository applica `COALESCE(disabilitato, false)`: dove il concetto non si
applica la riga è **viva**, che è l'unica lettura che non inventa niente.

### Scope e permessi

- `model_permission = ("vendite", "fattura")`, come il dettaglio: chi non può
  vedere la fattura non ne vede nemmeno la storia.
- `get_scope_user_id(request)` somma il filtro applicativo alla RLS — `None` per
  il superuser, che vede tutto.

## Dipendenze DB

| Oggetto | Ruolo |
| --- | --- |
| `script.vw_giornale_entita` | la sorgente: cuce `event_log`, `fatturazione_lotti_log`, `fatturazione_lotti_task_runs`, `fatture_log`. `security_invoker` |
| `vendite.fatture` | il **cancello**: ha la RLS, e il 404 nasce da lì |
| `vendite.fatture_log` | l'unico ramo che oggi risponde per una fattura — `event_log` non ha righe di entità `FATTURA` |

⚠️ **Il diario di una fattura muore con la fattura.**
`vendite.fn_cleanup_fatture_by_ids` cancella anche `fatture_log`, quindi ogni
riporta-a-bozza azzera la storia del documento. **È voluto** (decisione di Tid,
2026-08-24): di una fattura rigenerata contano gli ultimi eventi, non quelli dei
tentativi precedenti. Il **lotto** invece accumula.

## Note di migrazione

- `20260824-14` — `disabilitato` esposto sulla vista. ⚠️ La colonna è **in
  coda**, dopo `user_insert`: un `CREATE OR REPLACE VIEW` non può inserirla in
  mezzo. Qui non morde (le colonne si nominano nella `SELECT`), ma chi legge per
  posizione da un `SELECT *` deve saperlo.
- ⭐ `list_giornale_entita` vive in `VenditeRepository` perché il primo
  consumatore è la fattura. **Al secondo dominio va spostato in `core`** — non
  prima (regola del 2). La vista è già cross-dominio per costruzione: quando
  arriverà «cosa è successo a questa pratica», il ramo entra con un `UNION ALL`
  e il lettore non cambia.
