# API UI — Personalizzazioni liste (Django)

## Scopo

Esporre via HTTP la configurazione effettiva di una lista per l'utente
autenticato (cascata preset + permessi) e gestire la sua preferenza
personale (UPSERT/DELETE). Endpoint trasversali consumati da tutte le
viste del frontend che usano il componente `<ListaConfigurabile>`.

## Contesto

Strato di presentazione del refactor `sviluppo-personalizzazioni-liste.md`
(Blocchi A+B+C atterrati 2026-05-06/07). Lo schema DB `ui` ospita 6
tabelle (`lista_definizione`, `lista_colonna`, `lista_preset`,
`lista_preset_colonna`, `lista_preferenza_utente`, `lista_colonna_permesso`)
e la funzione `ui.fn_resolve_lista_config(VARCHAR, INTEGER, BIGINT)` che
applica:

1. cascata **per chiave** (dal 2026-11-01): `colonne` e `pagina_dimensione`
   vengono ognuna dal primo livello che la
   contiene — preferenza utente -> preset di ruolo (priorita ASC) ->
   preset di emittente -> preset di sistema -> catalogo grezzo. Una chiave
   assente dalla preferenza vale «come lo standard». ⛔ `ordinamento` e
   `filtri` sono usciti dalla cascata col giro 2 di brief-db-revisione-ui
   (Q38/Q39 §6, 2026-11-21): i filtri di partenza sono dello store,
   l'ordinamento di partenza è del preset (`ui.fn_ordinamento_lista`);
2. merge automatico delle nuove colonne aggiunte al catalogo dopo
   l'ultimo salvataggio della preferenza (con `visibile=false`);
3. normalizzazione colonne obbligatorie (`identificatore`/`azione`
   forzate a `visibile=true`);
4. filtro autorizzativo (deny-list per non sensibili, allow-list per
   sensibili) via `script.fn_get_profili_accesso_applicabili` filtrata
   per la veste corrente (GUC `app.ruolo_applicativo`). Oggi passa da due
   building block del DB: la veste la legge `ui.fn_veste_corrente()`, il
   livello di ogni colonna lo da' `ui.fn_lista_colonne_livello` (`BLOCCATO`
   esce, `LETTURA` resta a video con `esportabile = false`).

Il backend Django (`apps.ui`) e' un wrapper sottile: tutta la logica
di dominio vive nel DB. La meta-API e' trasversale ai domini funzionali
(non legata a un'`area_funzionale` di business): tutte le view usano
`DomainAPIView` con `skip_area_check = True`. JWT obbligatorio su tutti
gli endpoint; lo scope dati per-utente e' implicito (la fn DB filtra
sull'`auth_user_id` e i profili applicabili).

`emittente_fiscale_id` non e' un parametro di input HTTP: e' derivato
1:1 lato service via `PermissionResolver.get_emittente_for_user`
(refactor operatore-emittenti, una sola riga in `config.user_emittenti_fiscali`).
Per admin globale (0 righe) -> `None` -> la fn DB ricade sul preset di
sistema o sul catalogo grezzo.

---

## Endpoint

### 1. Risolvi configurazione lista

#### Input

- Metodo: `GET`
- Path canonico: `/api/v1/ui/liste/{codice}/config/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Path parameter:
  - `codice` (string) — codice della lista come definito in
    `ui.lista_definizione.codice`. Convenzione `<schema>.<entita>` o
    `<schema>.<entita>:<contesto>` (es. `anagrafiche.clienti`,
    `anagrafiche.clienti:picker`).
- Query param:
  - `emittente_esplicito` (int, opzionale) — l'emittente già fissato dal contesto
    che apre la lista (per esempio un tab dentro il drawer di un emittente). Se c'è,
    la lista non è ambigua e `richiede_scelta_emittente` è `false`. Un valore non
    intero o ripetuto è trattato come assente.

#### Output

- `200`:

```json
{
  "data": {
    "colonne": [
      {
        "codice": "ragione_sociale",
        "ordine": 1,
        "larghezza": 240,
        "visibile": true,
        "fissata": true,
        "esportabile": true,
        "tipo_colonna": "identificatore",
        "etichetta_i18n_key": "liste.clienti.ragione_sociale",
        "priorita": 1
      },
      {
        "codice": "partita_iva",
        "ordine": 2,
        "larghezza": 130,
        "visibile": true,
        "fissata": false,
        "esportabile": true,
        "tipo_colonna": "informazione",
        "etichetta_i18n_key": null,
        "priorita": 3
      }
    ],
    "pagina_dimensione": 25,
    "pagina_dimensione_standard": 25,
    "origine": {
      "colonne": "preferenza",
      "pagina_dimensione": "sistema"
    },
    "ricerca_min_caratteri": 3,
    "colonne_nuove": 0,
    "preset_base": {
      "id": 5,
      "ambito": "sistema",
      "contenuto_aggiornato_il": {
        "colonne": "2026-11-20T09:12:00+00:00",
        "pagina_dimensione": "2026-11-18T16:40:00+00:00"
      }
    },
    "preset_base_cambiato": false,
    "preset_aggiornato": false,
    "preset_aggiornato_chiavi": [],
    "multi_emittente": false,
    "perimetro_emittente": true,
    "ricerca_full": true,
    "richiede_scelta_emittente": false
  },
  "meta": {"request_id": "..."}
}
```

Campi dell'oggetto colonna:

- `codice` — riferimento stabile a `ui.lista_colonna.codice`
- `ordine` — posizione nella tabella renderizzata (intero crescente)
- `larghezza` — pixel suggeriti (override del preset/preferenza, fallback
  a `ui.lista_colonna.larghezza_default`)
- `visibile` — se `false`, la colonna e' nel pool ma non mostrata di
  default; appare nella modale di personalizzazione
- `fissata` — frozen column (non scrolla orizzontalmente). Sempre `true`
  per `tipo_colonna='identificatore'`
- `esportabile` — se `false`, la colonna e' visibile a video ma esclusa
  dall'export (deriva da livello permesso `LETTURA` o da
  `lista_colonna.esportabile=false` per `tipo_colonna='azione'`)
- `tipo_colonna` — uno tra `identificatore`, `informazione`, `azione`.
  Il FE disabilita il toggle visibilita' nella modale per
  `identificatore` e `azione`.
- `etichetta_i18n_key` — la chiave di traduzione dell'etichetta, fresca dal
  catalogo (`null` se la colonna non ne ha una)
- `priorita` — la priorita' della colonna, fresca da `ui.lista_colonna`
  (non dal preset o dalla preferenza)

Campi top-level:

- `colonne_nuove` — quante colonne del catalogo non erano presenti nella
  preferenza salvata (per il badge UX "N nuove colonne disponibili")
- `pagina_dimensione` — stato derivato dalla
  cascata (preferenza > preset di ruolo > preset di emittente > preset
  di sistema > la misura di default **dell'uso della lista** nel catalogo
  `ui.misure_pagina`: `COMPATTA` o `PAGINA`, da
  `ui.lista_definizione.uso_misura`). La regola e' `ui.fn_misura_pagina_risolta`,
  la stessa di `ui.fn_misura_lista`. ⭐ Dal 2026-09-30 `pagina_dimensione` e'
  **sempre una misura del catalogo**: quella scelta se ammessa, altrimenti il
  default — mai `NULL`, mai un numero che il paginatore non offre
- `ricerca_min_caratteri` — la soglia della ricerca libera della lista: il
  frontend non manda un termine piu' corto. E' la stessa colonna che legge il
  BB di ricerca (`soglia_ricerca`)
- `multi_emittente` — la lista sa dire l'emittente di ogni riga (non e' un
  permesso)
- `perimetro_emittente` — `false` per un catalogo globale: la domanda
  dell'emittente non si applica. Con `multi_emittente` e' l'ingresso di
  `richiede_scelta_emittente`
- `origine` — per ognuna delle due chiavi (`colonne`, `pagina_dimensione`),
  il livello da cui viene:
  `preferenza`, `ruolo`, `emittente_fiscale`, `sistema` o `catalogo` (dal
  2026-11-01). ⭐ Il FE rimanda al salvataggio **solo** le chiavi
  `preferenza`, piu' quella toccata: rimandare la configurazione intera
  congelerebbe nella preferenza le chiavi del preset (era il difetto fino
  al 2026-10-31)
- `preset_base` — il preset di base di **oggi** per l'utente (`{id, ambito,
  contenuto_aggiornato_il}`; la data del contenuto è **per chiave**,
  `{chiave: data}`, dal giro 1b di brief-db-revisione-ui), oppure `null` se nessun preset vale e ogni
  chiave viene dal catalogo. Lo sceglie il DB in una sede sola
  (`ui.fn_preset_di_base`): un preset vale se è acceso e ha almeno una
  colonna attiva; il ruolo concorre solo con la veste valorizzata, l'azienda
  solo se accesa, poi il sistema. ⭐ È la base che il salvataggio della
  preferenza registra (endpoint 3): il backend non ha una copia della cascata
- `preset_base_cambiato` — `true` se la preferenza ha salvato un preset di
  base che non è quello di oggi (spento, o sostituito da un altro livello).
  Il frontend mostra il banner «base cambiata» con l'azione «Riallinea», che
  risalva la preferenza (dal 2026-11-20, BE7 di brief-db-revisione-ui)
- `preset_aggiornato` — `true` se la base salvata è quella di oggi e il suo
  contenuto è cambiato, in almeno una chiave scelta dall'utente (origine
  `preferenza`), dopo lo snapshot della preferenza: il banner DEF-2.
  «Ignora» (endpoint 5) riallinea lo snapshot. Con `preset_base_cambiato`
  vero è sempre `false`, e i due banner non si sovrappongono
- `preset_aggiornato_chiavi` — le chiavi di quel cambiamento (elenco, vuoto
  se nessuna; dal giro 1b): il banner dice quali parti sono cambiate
- `pagina_dimensione_standard` — la misura che la cascata darebbe **senza**
  la preferenza; il drawer di personalizzazione la mostra come «Come lo
  standard (N)»
- `ricerca_full` — `true` se la lista ha, **per l'utente corrente**, almeno
  una colonna in cui la ricerca libera cerca (`ricercabile_full = t`,
  attiva, non `BLOCCATO` per i permessi di colonna). Il frontend mostra la
  casella di ricerca **solo** se e' vera: una casella senza colonne accese non
  troverebbe niente. Letta da `ui.fn_lista_colonne_ricerca_full`, la stessa
  sede del BB `add_ricerca_full_condition` (dal 2026-09-23,
  brief-be-ricerca-full-liste-residue §7-bis). ⚠️ Solo in questo endpoint
  (`UiService.get_lista_config_per_video`): la configurazione che leggono
  l'export e la modale di personalizzazione non la porta, e non paga la query

- `richiede_scelta_emittente` — `true` se l'operatore deve scegliere un
  emittente prima di vedere la lista: la lista ha un perimetro emittente, non è
  certificata multi-emittente, non c'è un `emittente_esplicito` e il perimetro
  effettivo dell'utente ha più di un emittente. Lo calcola il backend
  (`perimetro_emittente.richiede_scelta_emittente`, lo stesso BB del cancello
  `422 E_UI_LISTA_EMITTENTE_DA_SCEGLIERE` sulle rotte dati): il frontend non lo
  ricalcola

Errori:

- `401` — JWT mancante o non valido
- `404` `E_UI_LISTA_NON_TROVATA` — `codice` non esiste in
  `ui.lista_definizione` oppure `attivo=false`
- `400` `E_UI_GENERIC_FAILED` — DatabaseError generico durante la
  risoluzione (caso eccezionale, log a DB)
- `500` `E_UI_CHIAMATA_NON_VALIDA` (classe `TECNICO`, dal 2026-09-24) — il
  contesto di sessione della richiesta (GUC `app.current_user_id`) è vuoto o
  nomina un utente diverso da quello autenticato. La configurazione risponde
  per l'utente della chiamata, `ricerca_full` e la ricerca vera per quello
  della GUC: se divergessero, la casella direbbe una cosa e la ricerca ne
  farebbe un'altra, senza errore. In una richiesta HTTP le due fonti
  coincidono per costruzione (`JwtAuditAuthentication`), quindi a video non
  compare mai: segnala un chiamante rotto. Contesto a diario: `lista_codice`,
  `auth_user_id`, `utente_di_sessione`. Brief-be-ricerca-full-liste-residue §12

#### Note

- Idempotente, no side effect. Cache lato FE con ETag e' un'evoluzione
  pianificata (vedi WIP §10.3).
- Non accetta `emittente_fiscale_id` come query param: e' derivato
  internamente dall'utente. L'unico parametro di perimetro è
  `emittente_esplicito`, che non cambia la configurazione ma solo
  `richiede_scelta_emittente`.

---

### 2. Catalogo colonne (per modale di personalizzazione)

#### Input

- Metodo: `GET`
- Path canonico: `/api/v1/ui/liste/{codice}/catalogo/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Path parameter: `codice` (vedi §1)

#### Output

- `200`:

```json
{
  "data": {
    "colonne": [
      {
        "id": 1,
        "codice": "ragione_sociale",
        "etichetta": "Ragione sociale",
        "etichetta_estesa": "Ragione sociale del cliente",
        "etichetta_i18n_key": "liste.clienti.ragione_sociale",
        "campo_sorgente": "ragione_sociale",
        "tipo_colonna": "identificatore",
        "tipo_dato": "string",
        "formato": null,
        "larghezza_default": 240,
        "ordine_default": 10,
        "allineamento": "left",
        "gruppo": "Anagrafica",
        "gruppo_ordine": 10,
        "filtrabile": true,
        "ordinabile": true,
        "esportabile": true,
        "ricercabile_full": true,
        "sensibile": false,
        "attivo": true
      }
    ]
  },
  "meta": {"request_id": "..."}
}
```

I metadati ricchi (etichetta, etichetta_estesa, etichetta_i18n_key, gruppo,
gruppo_ordine, formato, ordine_default, ecc.) servono al frontend per
renderizzare la modale (`etichetta_i18n_key` la traduce nella lingua
dell'utente): raggruppamento collassabile per `gruppo`/`gruppo_ordine`,
tooltip da `etichetta_estesa`, ordinamento di default per
`ordine_default`.

L'output **filtra le colonne BLOCCATE** per il profilo dell'utente:
quelle escluse da `ui.fn_resolve_lista_config` (deny-list non sensibili
+ allow-list sensibili) non compaiono nemmeno nella modale, perche' la
modale non puo' offrire l'attivazione di una colonna proibita.

Errori:

- `401`, `404`, `400` — stessi codici di §1 (la view delega a
  `UiService.get_lista_config` per la risoluzione 404+permessi prima di
  arricchire i metadati).

---

### 3. UPSERT preferenza utente

#### Input

- Metodo: `PUT`
- Path canonico: `/api/v1/ui/liste/{codice}/preferenza/`
- Header sicurezza:
  - `Authorization: Bearer <access_token>`
  - `Idempotency-Key: <uuid-stringa>` — **obbligatorio** (cfr. policy
    api.md su modifiche di stato)
- Path parameter: `codice` (vedi §1)
- Body JSON (tutti i campi opzionali; la forma la giudica il DB — chiavi
  extra rifiutate):

```json
{
  "colonne": [
    {
      "codice": "ragione_sociale",
      "ordine": 1,
      "larghezza": 240,
      "visibile": true,
      "fissata": true
    },
    {"codice": "partita_iva", "ordine": 2, "visibile": true}
  ],
  "pagina_dimensione": 50
}
```

⭐ **La forma la giudica il DB, in una sede sola**: il guard
`ui.trgfn_preferenza_guard_forma` (`ui.fn_check_forma_configurazione`) risponde
`400 E_UI_CONFIGURAZIONE_FORMA`, col messaggio che nomina la chiave e il motivo
(«`colonne`: la voce `x` ha `larghezza` null»). Dal giro 2 di
brief-db-revisione-ui (BE8, 2026-11-22) il service non ha più una sua copia: del
BE resta la sola regola dell'API, il corpo è un oggetto con almeno una chiave
(`400 E_UI_PREFERENZA_VALIDAZIONE`). Chiavi ammesse: `colonne`,
`pagina_dimensione`. ⛔ `ordinamento` e `filtri` sono usciti dalla preferenza
(Q38/Q39 §6, giro 2 del 2026-11-21): nel payload sono un `400
E_UI_CONFIGURAZIONE_FORMA`. ⭐ **Ogni chiave e' facoltativa** (dal 2026-11-01):
quella **assente** vale «come lo standard», e la preferenza contiene solo le
chiavi scelte. ⛔ Una chiave a `null` non è «assente»: è un rifiuto di forma, in
radice e nella voce («svuota la larghezza» è la chiave tolta, e la toglie il FE:
decisione di Tid del 2026-11-22). ⛔ Una preferenza **senza chiavi** si toglie col
`DELETE` (endpoint 4): il `PUT` vuoto risponde `400
E_UI_PREFERENZA_VALIDAZIONE`. Chiavi della voce colonna: `codice`, `ordine`,
`larghezza`, `visibile`, `fissata`. Vincoli:

- `codice` (string non vuota) — obbligatorio; una colonna della lista, una
  volta sola
- `ordine`, `larghezza` (intero positivo, numero JSON: `"120"` è rifiutato) —
  opzionali
- `visibile`, `fissata` (bool stretto) — opzionali; non accetta `"true"`
  o `1`
- `pagina_dimensione` (int) — una delle misure del catalogo
  `ui.misure_pagina` (endpoint 6). ⭐ Il backend ne controlla solo la
  **forma**; l'ammissibilita' la decide il guard a DB, e una misura fuori
  catalogo risponde `400 E_UI_MISURA_PAGINA_NON_AMMESSA`. ⛔ Fino al
  2026-09-30 il service applicava un suo tetto (`MAX_LIMIT`, 200): una
  seconda regola, diversa dal catalogo, che ammetteva 37

#### Output

- `200`:

```json
{
  "data": {
    "id": 99,
    "preset_base_id": 5
  },
  "meta": {"request_id": "..."}
}
```

- `id` — PK della riga in `ui.lista_preferenza_utente`
- `preset_base_id` — id del preset di base di oggi, letto dalla
  risoluzione (`preset_base` dell'endpoint 1; `null` se l'utente parte dal
  catalogo). ⭐ Lo snapshot per il banner «preset aggiornato» (DEF-2),
  `lista_preferenza_utente.preset_base_contenuto_aggiornato_il` (per chiave,
  `{chiave: data}`), lo scrive il
  DB: `ui.trgfn_preferenza_preset_base_snapshot` lo copia dalla data del
  **contenuto** del preset a ogni scrittura che nomina `preset_base_id`
  (dal 2026-11-20, BE5 e BE6 di brief-db-revisione-ui). Ogni salvataggio è
  quindi un riallineamento.

Errori:

- `400` `E_IDEMPOTENCY_KEY_REQUIRED` — header `Idempotency-Key` mancante
- `400` `E_UI_PREFERENZA_VALIDAZIONE` — il corpo non è un oggetto, o non ha
  nessuna chiave
- `400` `E_UI_CONFIGURAZIONE_FORMA` — la forma non è ammessa (chiave fuori
  posto, voce senza codice o con una chiave a `null`, tipo errato, codice
  ripetuto o non della lista); il messaggio nomina la chiave e il motivo
  (dal guard a DB)
- `400` `E_UI_MISURA_PAGINA_NON_AMMESSA` — `pagina_dimensione` non e' una
  misura del catalogo (dal guard a DB; il messaggio elenca le ammesse)
- `401` — JWT mancante o non valido
- `404` `E_UI_LISTA_NON_TROVATA` — codice lista non esistente o non attivo

#### Note

- L'UPSERT usa `ON CONFLICT (auth_user_id, lista_id) DO UPDATE`: stessa
  chiamata aggiorna la preferenza esistente.
- `preset_base_contenuto_aggiornato_il` lo riscrive il DB a ogni
  salvataggio: l'utente che salva risolve implicitamente l'eventuale
  notifica "preset aggiornato", e con la base di oggi anche quella della
  base cambiata.
- L'`Idempotency-Key` strong mode (`DJANGO_API_STRONG_IDEMPOTENCY_ENABLED=1`)
  fa replay della risposta sulla stessa key entro la TTL di
  `dbops.idempotency_keys`.

---

### 4. DELETE preferenza utente

#### Input

- Metodo: `DELETE`
- Path canonico: `/api/v1/ui/liste/{codice}/preferenza/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Path parameter: `codice` (vedi §1)
- Body: nessuno

#### Output

- `200`:

```json
{
  "data": {"deleted": true},
  "meta": {"request_id": "..."}
}
```

`deleted=true` se la preferenza esisteva ed e' stata eliminata,
`false` se non esisteva (idempotenza). Al prossimo `GET .../config`
l'utente parte dal preset di ruolo / emittente / sistema / catalogo
grezzo (cascata standard).

Errori:

- `401` — JWT mancante o non valido
- `404` `E_UI_LISTA_NON_TROVATA` — codice lista non esistente
  (caso patologico: protezione contro path errati; non e' un errore
  business reale per l'utente)

---

### 5. POST preferenza/ignore-preset-update (DEF-2)

#### Scopo

«Ignora» del banner preset aggiornato: riscrive `preset_base_id` della
preferenza di `(request.user, codice)` col valore che ha già, e il trigger
`ui.trgfn_preferenza_preset_base_snapshot` riallinea lo snapshot
(`preset_base_contenuto_aggiornato_il`) al contenuto di oggi, chiave per
chiave. Il flag `preset_aggiornato` ritornato da `ui.fn_resolve_lista_config`
torna `false` finche' il contenuto del preset non cambia di nuovo. ⛔ Dal
giro 1b di brief-db-revisione-ui (2026-11-20) l'ignorato
`preset_aggiornato_ignored_at` non esiste più: «ignorare» e «riallineare»
sono lo stesso gesto, e il banner si confronta solo con lo snapshot.

L'endpoint chiude la conversazione "l'amministratore ha aggiornato il
preset del tuo ruolo, vedi novita' / ignora": "Vedi novita'" si chiude
naturalmente al successivo save preferenza (il DB riscrive lo snapshot
`preset_base_contenuto_aggiornato_il`); "Ignora" usa questo endpoint
per nascondere il banner senza modificare la configurazione utente.

#### Input

- Metodo: `POST`
- Path canonico: `/api/v1/ui/liste/{codice}/preferenza/ignore-preset-update/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Header obbligatorio: `Idempotency-Key: <uuid>` (allineamento al pattern POST `handle_post_json`, strong mode replay su `dbops.idempotency_keys`)
- Path parameter: `codice` (vedi §1)
- Body: nessuno

#### Output

- `200`:

```json
{
  "data": {"ignored": true},
  "meta": {"request_id": "..."}
}
```

Errori:

- `400` `E_IDEMPOTENCY_KEY_REQUIRED` — header `Idempotency-Key` mancante
- `401` — JWT mancante o non valido
- `404` `E_UI_LISTA_NON_TROVATA` — codice lista non esistente
- `404` `E_UI_PREFERENZA_NON_TROVATA` — l'utente non ha ancora una
  preferenza salvata sulla lista (caso patologico: il banner non
  sarebbe visibile, ma chiamata diretta da retry/script viene
  rifiutata)

#### Note DEF-2

- **Idempotency-Key**: obbligatoria per coerenza con il pattern POST
  (api.md). Ripetere il riallineamento è innocuo: lo snapshot torna uguale.
- **La base resta quella salvata**: «Ignora» non cambia `preset_base_id`.
  Con la base cambiata il banner è l'altro («Riallinea»), che salva la base
  di oggi con la preferenza (endpoint 3).
- **Riapparizione banner**: il banner torna visibile alla prossima
  modifica del contenuto del preset, in una chiave scelta dall'utente.
  Pattern by design: l'utente che "ignora una volta" non perde visibilita'
  sulle future modifiche.
- **Lo snapshot non lo scrive l'app**: chi scrive la data del contenuto di
  un preset riceve `500 E_UI_PRESET_CONTENUTO_DERIVATO` (la scrive solo il
  DB, `ui.trgfn_preset_contenuto_aggiornato`).

---

### 6. GET misure-pagina

#### Scopo

Le misure «righe per pagina» che **ogni** paginatore dell'applicazione
offre, e i due default, lette da `ui.fn_get_misure_pagina()` (catalogo
`ui.misure_pagina`, sede unica per DB, backend e frontend — decisioni di
Tid del 2026-09-29). Non sono dentro la configurazione di una lista perche'
le usano anche tabelle grezze, dialog e cruscotti. Il frontend le legge
**una volta per sessione**, dal guard del router, prima di aprire
qualunque pagina dell'operatore (BB `core/misurePagina.js`).

#### Input

`GET /api/v1/ui/misure-pagina/` — nessun parametro. JWT obbligatorio.

#### Output

- `200`:

```json
{
  "data": {
    "misure": [10, 25, 50, 100],
    "default_compatta": 10,
    "default_pagina": 25
  },
  "meta": {"request_id": "..."}
}
```

- `misure` — in ordine crescente (l'ordine del selettore)
- `default_compatta` — la misura di partenza delle liste in drawer e dialog
- `default_pagina` — quella delle liste a pagina intera, e il ripiego del
  resolver quando nessuno ha scelto

Errori:

- `401` — JWT mancante o non valido
- `500` `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE` (`TECNICO`) — il catalogo non
  ha la riga di uno dei due default: anomalia di seed, non un valore vuoto

---

## Regole

- **Permessi**: `skip_area_check = True` su tutte le view. JWT
  obbligatorio. Lo scope dati per-utente e' applicato dalla fn DB
  (filtri sui profili applicabili dell'utente).
- **Multi-veste**: la veste corrente e' letta dalla GUC
  `app.ruolo_applicativo` (propagata da `JwtAuditAuthentication`).
  Utente con identita' multi-veste (es. OPERATORE+CLIENTE_PORTALE su
  stessa email) vede preset/permessi della sola veste del JWT corrente
  (DB-4 landed 2026-05-07).
- **Cascata preset di ruolo**: ordinata per `priorita ASC` (AD_HOC=1
  prevale su REPARTO/PORTALE=2). DB-3 landed 2026-05-07.
- **Eliminazione preset di base**: la FK `preset_base_id` e'
  `ON DELETE SET NULL` (DB-2 landed), e
  `ui.trgfn_preferenza_preset_base_snapshot` lo vede come un cambio di base:
  snapshot e «ignora» azzerati. I due flag (`preset_base_cambiato`,
  `preset_aggiornato`) li calcola il DB: il FE li legge e basta.
- **Ordinamento di partenza delle liste** (dal 2026-11-22, BE25 (2) di
  brief-db-revisione-ui): l'endpoint di una lista configurabile (la view
  dichiara `lista_codice`), chiamato **senza `order_by`**, ordina con
  l'ordinamento del preset di base dell'utente (`ui.fn_ordinamento_lista`, la
  prima voce, per campo sorgente) e lo dice nella risposta:
  `meta.ordinamento = {order_by, order_dir, col}`. Vale anche per l'export.
  Con `order_by` nella richiesta vince la richiesta, e `meta.ordinamento`
  non c'e'; senza un ordinamento a preset vale il default del repository.
  Il frontend accende l'intestazione da `meta.ordinamento`
  (`ordinamentoApplicato`), non da un ordinamento scritto nello store.
  ⭐ `meta.ordinamento` dice l'ordinamento **applicato**, non quello
  proposto: c'e' solo se il repository ha risolto la chiave nella sua
  whitelist. Una lista che ordina nel browser non lo porta. Se la colonna del
  preset e' `ordinabile` a catalogo ma il repository non la sa ordinare, la
  lista si apre col suo default (la view la rilegge senza ordinamento, e il
  difetto va nel log), non con un 400. Un `order_by` **chiesto dal client**
  fuori whitelist resta il 400 `E_VALIDATION_INPUT`.
- **Misura di partenza delle liste** (dal 2026-11-22, BE10 di
  brief-db-revisione-ui): la stessa porta, chiamata **senza `limit`**, pagina
  con la misura della configurazione della lista (`ui.fn_misura_lista`, la
  stessa regola di `pagina_dimensione` qui sopra), non con il `default_limit`
  della view, che per una lista configurabile non vale piu'. La legge
  `pagina_da_query` solo se l'endpoint pagina davvero. Il tetto (`max_limit`)
  resta della view: un `limit` del client oltre il tetto e' un 400, una misura
  di catalogo oltre il tetto si riporta al tetto con un warning nel log (e' un
  difetto del catalogo, non della richiesta). BB:
  `apps.core.services.ordinamento_di_partenza`.
- **Su quali porte vale la partenza**: ordinamento e misura di partenza li
  accende `_ApiViewBase`, quindi **ogni** view che dichiara `lista_codice`,
  comprese le liste dell'amministrazione su `AdminAPIView` (dal 2026-11-22,
  giro 6). Il cancello del perimetro emittente invece resta solo su
  `DomainAPIView`.
- **Veste GUC corrotta**: `ui.fn_veste_corrente()` risponde `NULL` («tutte
  le vesti dell'utente») per una GUC assente, vuota o fuori dominio, mai
  un'eccezione (`EXCEPTION WHEN invalid_text_representation`). E' semantica
  di presentazione: le funzioni di `script` che decidono un accesso restano
  fail-closed sulla veste.

## Dipendenze DB

- Tabelle: `ui.lista_definizione`, `ui.lista_colonna`, `ui.lista_preset`,
  `ui.lista_preset_colonna`, `ui.lista_preferenza_utente`,
  `ui.lista_colonna_permesso`, `ui.misure_pagina`
- Funzioni: `ui.fn_resolve_lista_config` (con `ui.fn_lista_da_codice`,
  `ui.fn_veste_corrente`, `ui.fn_preset_di_base`, `ui.fn_preset_aggiornato`,
  `ui.fn_lista_colonne_livello` e `ui.fn_misura_pagina_risolta`),
  `ui.fn_lista_da_codice` (anche da solo: `lista_codice -> id` per la
  preferenza), `ui.fn_lista_colonne_ricerca_full` (`ricerca_full`),
  `ui.fn_ordinamento_lista` e `ui.fn_misura_lista` (la partenza),
  `ui.fn_get_misure_pagina`,
  `script.fn_get_profili_accesso_applicabili` (dentro
  `ui.fn_lista_colonne_livello`),
  `script.fn_resolve_emittente_for_user` (via Python
  `PermissionResolver.get_emittente_for_user`)
- Trigger: `trgfn_ui_lista_definizione_a10_valida_vista_sql`,
  `trgfn_ui_lista_colonna_a10_valida_campo_sorgente`,
  `ui.trgfn_preferenza_preset_base_snapshot` (lo snapshot del preset di base)

## Building block backend usati

- [`apps.core.api.base_views.DomainAPIView`](../../core/manual/api-domain-conventions.md)
  con `skip_area_check=True`
- [`apps.core.api.endpoint_helpers.handle_post_json`](../../core/manual/api_endpoint_helpers.md)
  con `require_idempotency_key=True` (PUT preferenza)
- [`apps.core.services.permissions_resolver.PermissionResolver.get_emittente_for_user`](../../core/manual/permissions_resolver.md)
  per la derivazione 1:1 user->emittente
- [`apps.core.services.error_manager.ErrorManager`](../../core/manual/error-handling-api.md)
  per gli errori strutturati

## Codici errore registrati

Ogni codice ha una **classe** nel catalogo
`db/changelog/migrations_v2/80_data/sql/config/codici_errore.csv`, rigenerata in
`apps/core/services/error_policies_generated.py` (`manage.py
genera_error_policies`, non si modifica a mano). Status HTTP e `ui_action` si
derivano dalla classe in `apps/core/services/error_policies.py`.

| Codice | HTTP | UI action | Origine |
| ------ | ---- | --------- | ------- |
| `E_UI_LISTA_NON_TROVATA` | 404 | `show_empty_state` | BB DB `ui.fn_lista_da_codice` (lista inesistente o `attivo=false`), via resolver e repository |
| `E_UI_PREFERENZA_NON_TROVATA` | 404 | `show_empty_state` | Service (`ignore-preset-update` senza preferenza salvata) |
| `E_UI_PRESET_CONTENUTO_DERIVATO` | 500 | `show_error_banner` | Trigger DB `ui.trgfn_preset_contenuto_aggiornato` (la data del contenuto la scrive solo il DB) |
| `E_UI_LISTA_EMITTENTE_DA_SCEGLIERE` | 422 | `show_error_banner` | Cancello di perimetro di `DomainAPIView` sulle rotte dati (non su questi endpoint: qui c'e' solo il flag `richiede_scelta_emittente`) |
| `E_UI_VISTA_SQL_NON_TROVATA` | 400 | `show_error_banner` | Trigger B1 (admin only — seed/import) |
| `E_UI_CAMPO_SORGENTE_NON_TROVATO` | 400 | `show_error_banner` | Trigger B2 (admin only) |
| `E_UI_PREFERENZA_VALIDAZIONE` | 400 | default `DATO_ERRATO` (banner: nessun input da accendere) | Service write (corpo non oggetto o senza chiavi) |
| `E_UI_CONFIGURAZIONE_FORMA` | 400 | default `DATO_ERRATO` | Guard DB sulla preferenza (forma della configurazione) |
| `E_UI_GENERIC_FAILED` | 400 | `show_error_banner` | Service (DatabaseError non riconosciuto) |
| `E_UI_CHIAMATA_NON_VALIDA` | 500 | `show_error_banner` | Service (`get_lista_config_per_video`: contesto di sessione ≠ utente della chiamata) |
| `E_UI_MISURA_PAGINA_NON_AMMESSA` | 400 | default `DATO_ERRATO` | Guard DB su preset e preferenza (misura fuori catalogo) |
| `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE` | 500 | default `TECNICO` | fn DB (`ui.fn_misura_pagina_default`: il catalogo non ha il default) |

## Note di migrazione

- App `apps.ui` registrata in `INSTALLED_APPS` di
  [zeroerp_backend/settings.py](../../../../backend/zeroerp_backend/settings.py).
- Routing: `path("api/v1/ui/", include("apps.ui.api.urls"))` in
  [zeroerp_backend/urls.py](../../../../backend/zeroerp_backend/urls.py).
- Test in `apps/ui/tests/`: `services/` e `api/` con repository mockato
  (`SimpleTestCase`/`JwtMockedApiTest`), `db/` sul database vero (forma della
  preferenza, `fn_lista_da_codice`, misure, ordinamento di partenza, audit,
  seed). Il conteggio non si ricopia qui: invecchia.
- Brief team DB DB-1..DB-4 atterrato 2026-05-07
  (vedi [`brief-db-ui-personalizzazioni-liste.md`](../../../dev/work-done/2026/brief-db-ui-personalizzazioni-liste.md)).
