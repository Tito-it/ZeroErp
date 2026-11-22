# Sviluppo Listini v2 — Documento di sintesi e analisi (WIP)

> Stato: **WIP — IN ANALISI** (raccolta concetti per decisioni operative)
>
> Ultima revisione: aprile 2026
>
> Scopo: documento di lavoro che consolida in un unico posto:
>
> 1. tutti i concetti gia` documentati altrove sul dominio listini (guide ufficiali, WIP padre, manuali DB)
> 2. la sintesi del modello dati e del resolver attuale
> 3. l'analisi del ciclo di vita versione (BOZZA / ATTIVA / CHIUSA) con i gap implementativi rilevati
> 4. le proposte operative discusse in chat per chiudere i gap senza violare gli invarianti documentati
> 5. il rimando al perimetro DB-L4 rettifiche, da analizzare in parallelo
>
> Riferimenti incrociati:
>
> * [guide/gestione-listini.md](/guide/gestione-listini) — guida funzionale ufficiale
> * [dev/work-in-progress/sviluppo-listini.md](/dev/work-in-progress/sviluppo-listini) — analisi/decisioni operative (documento padre)
> * [dev/work-in-progress/sviluppo-rettifiche.md](/dev/work-in-progress/sviluppo-rettifiche) — DB-L4 rettifiche prezzi
> * [dbzero/vendite/manual/listini.md](/dbzero/vendite/manual/listini)
> * [dbzero/vendite/manual/listini_versioni.md](/dbzero/vendite/manual/listini_versioni)
> * [dbzero/vendite/manual/listini_righe.md](/dbzero/vendite/manual/listini_righe)
> * [dbzero/vendite/manual/listini_associazioni.md](/dbzero/vendite/manual/listini_associazioni)
> * [dbzero/vendite/funzioni/fn_resolve_prezzo_listino.md](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino)
> * [backend/vendite/manual/api_listini.md](/backend/vendite/manual/api_listini)

---

## 1) Inquadramento generale

In Zero ERP il **listino** non e` una semplice tabella di prezzi: e` un sistema multi-livello che risponde alla domanda *"quanto costa questo articolo, per questo contesto, in questa data?"* tenendo conto del cliente (BA), del servizio (utility) e dell'emittente fiscale.

Il modello e` **generico**:

* dominio `UTILITY` (gas, energia, idrico) con prezzi ad alta precisione per consumi minimi
* dominio `COMMERCIO` (servizi, manifatturiero) con pricing standard

L'architettura sottostante e` identica per entrambi.

### Filosofia DB-first

Le regole di coerenza (transizioni stato, no overlap temporale, almeno una riga per attivare, ecc.) vivono **nei vincoli e trigger del database**. Il backend Python orchestra ma non duplica la logica. Il frontend Vue espone solo presentazione.

---

## 2) Modello dati (sintesi DDL effettivo)

### 2.1 `vendite.listini` — testata

| Campo | Note |
|---|---|
| `id` | bigint PK |
| `codice` | univoco, immutabile dopo create (lock_columns) |
| `descrizione` | testo libero |
| `dominio` | enum `UTILITY` o `COMMERCIO` |
| `attivo` | boolean, disattivabile solo se non ha versioni o associazioni attive |
| `meta` | jsonb |

Il listino e` un **contenitore stabile**. Non contiene date ne` prezzi: sono delegati alle entita` figlie.

### 2.2 `vendite.listini_versioni` — finestra temporale + ciclo di vita

| Campo | Note |
|---|---|
| `id` | bigint PK |
| `listino_id` | FK al listino |
| `codice_versione` | varchar, univoco per `(listino_id, codice_versione)` |
| `valido_dal` | date, NOT NULL |
| `valido_al` | date, NULL = aperta indefinitamente |
| `priorita` | smallint, default 100, > 0 (tie-break tra versioni del listino) |
| `stato` | enum `BOZZA` / `ATTIVA` / `CHIUSA` (CHECK constraint) |
| `attivo` | boolean (default true) |
| `meta` | jsonb |

**Vincoli chiave**:

* `chk_listini_versioni_date`: `valido_al > valido_dal` (se valorizzato)
* `chk_listini_versioni_priorita`: `priorita > 0`
* `chk_listini_versioni_stato`: `stato IN ('BOZZA', 'ATTIVA', 'CHIUSA')`
* **`ex_listini_versioni_no_overlap`**: indice GIST exclusion sul `daterange(valido_dal, COALESCE(valido_al, 'infinity'))` per `listino_id` quando `attivo IS TRUE`. **Nessuna sovrapposizione temporale tra versioni attive dello stesso listino.**

### 2.3 `vendite.listini_righe` — prezzi elementari

| Campo | Note |
|---|---|
| `id` | bigint PK |
| `listino_versione_id` | FK alla versione |
| `articolo_id` | uuid, obbligatorio |
| `uom_id` | bigint, obbligatorio |
| `billing_account_id` | opzionale (dimensione contesto) |
| `utility_id` | opzionale (dimensione contesto) |
| `emittente_soggetto_ruolo_id` | opzionale (dimensione contesto) |
| `prezzo` | numeric(22,10) — alta precisione per micro-importi utility |
| `attivo` | boolean |
| `meta` | jsonb |

**Vincoli chiave**:

* `chk_listini_righe_prezzo`: `prezzo >= 0`
* `uq_listini_righe_key_attiva`: unique parziale su `(listino_versione_id, articolo_id, uom_id, COALESCE(BA, -1), COALESCE(utility, -1), COALESCE(emittente, -1))` WHERE `attivo IS TRUE`. Garantisce che dentro una versione non esistano due righe attive con stessa combinazione dimensionale.

**NB importante**: la riga **non ha date proprie**. La finestra temporale e` esclusivamente sulla versione padre.

### 2.4 `vendite.listini_associazioni` — visibilita` per contesto

| Campo | Note |
|---|---|
| `id` | bigint PK |
| `listino_id` | FK al listino |
| `billing_account_id` | opzionale |
| `utility_id` | opzionale |
| `emittente_soggetto_ruolo_id` | opzionale |
| `priorita` | smallint, default 100, > 0 |
| `valido_dal` / `valido_al` | finestra temporale dell'associazione |
| `attivo` | boolean |

L'associazione risponde a *"questo listino e` valido per il contesto X?"*. Non e` solo configurazione UI: e` il **primo filtro** del resolver per determinare quali listini sono candidati.

### 2.5 ER

```text
listini ──┬── listini_versioni ── listini_righe
          └── listini_associazioni
```

---

## 3) Resolver prezzo (`vendite.fn_resolve_prezzo_listino`)

### 3.1 Input

| Parametro | Obbligatorio |
|---|---|
| `p_articolo_id` (uuid) | si |
| `p_uom_id` (bigint) | si |
| `p_data_riferimento` (date) | si |
| `p_billing_account_id` | no |
| `p_utility_id` | no |
| `p_emittente_soggetto_ruolo_id` | no |

### 3.2 Flusso a 4 fasi

1. **Associazioni**: filtra listini candidati per contesto + finestra temporale
2. **Versioni**: per ogni candidato seleziona versioni con `stato = 'ATTIVA'` AND `attivo IS TRUE` AND `p_data_riferimento ∈ [valido_dal, valido_al]`
3. **Righe**: cerca righe con stesso `articolo_id + uom_id`, assegnando `match_level` da 1 (BA+utility+emittente) a 7 (solo articolo+UoM, fallback)
4. **Tie-break**: cascata `match_level → associazione.priorita → versione.priorita → data validita`

### 3.3 Output

`(listino_id, listino_versione_id, listino_riga_id, listino_associazione_id, prezzo, match_level)`

### 3.4 Errori

| Codice | Significato |
|---|---|
| `E_PREZZO_LISTINO_NON_TROVATO` | Nessun match per il contesto e la data |
| `E_PREZZO_LISTINO_AMBIGUO` (`AMBIGUOUS_PRICE_MATCH`) | Match equivalenti dopo tutti i tie-break |
| `E_PARAMETRO_INVALIDO` | Input mancante o non valido |

**Nessun fallback silenzioso**: il resolver o trova un prezzo univoco o solleva errore esplicito.

### 3.5 Cosa il resolver NON vede

* Versioni in stato `BOZZA` → invisibili (sandbox)
* Versioni in stato `CHIUSA` → invisibili (storiche)
* Versioni con `attivo = false` → invisibili
* Righe con `attivo = false` → invisibili
* Date al di fuori del `[valido_dal, valido_al]` della versione e dell'associazione → escluse

**Conseguenza**: il pricing reale e` interessato solo da versioni `ATTIVA + attivo + data ∈ finestra`. Tutto il resto e` audit storico o sandbox.

---

## 4) Ciclo di vita versione (analisi approfondita)

### 4.1 Stati ammessi

```text
BOZZA ────────→ ATTIVA ────────→ CHIUSA
 (sandbox)       (operativa)      (storica)
```

* **BOZZA**: editing libero righe/contesto. Default all'INSERT. Nessun impatto sul pricing (resolver non vede).
* **ATTIVA**: versione operativa. Partecipa al pricing. Le righe sono **immutabili** (per coerenza con gli snapshot gia` propagati in commesse_attivita / attivita_fatturabili).
* **CHIUSA**: storica. Stato terminale. Solo audit, nessuna interazione possibile. Resolver non vede.

### 4.2 Transizioni e guard documentati

| Da | A | Ammessa? | Guard |
|---|---|---|---|
| BOZZA | ATTIVA | si | almeno 1 riga attiva nella versione + listino attivo |
| BOZZA | CHIUSA | no | vietato (transizione non logica) |
| ATTIVA | BOZZA | no | vietato (no rollback) |
| ATTIVA | CHIUSA | si | sempre ammesso |
| CHIUSA | * | no | stato terminale |

Le transizioni sono validate sia dal service Python (`fn_change_versione_state`) sia dal vincolo CHECK lato DB.

**Guard "almeno una riga"**: documentato in [gestione-listini.md §Vincoli](#) e implementato in service. Risponde alla domanda *"se non ci sono righe non portare mai ad attivo"* — gia` garantito.

### 4.3 Vincolo no-overlap tra versioni attive

Il vincolo `ex_listini_versioni_no_overlap` (GIST exclusion) impedisce a due versioni dello stesso listino di avere intervalli temporali sovrapposti quando entrambe sono `attivo = true`.

**Conseguenza operativa importante**: se V001 e` valida `2026-01-01..NULL` (aperta) e l'utente vuole attivare V002 con `valido_dal = 2026-04-01`, l'operazione **fallisce** finche` V001 non viene esplicitamente programmata in chiusura tramite PATCH `valido_al = 2026-03-31`.

Non esiste auto-close automatico (e non deve esistere — vedi §6.2).

### 4.4 Disaccoppiamento dalla fatturazione

Questo e` il punto piu` importante per capire perche` la versione ATTIVA e` immutabile:

```text
Resolver listino
   |
   v
commesse_attivita (snapshot prezzo: prezzo_snapshot, listino_versione_id, prezzo_bloccato)
   |
   v
attivita_fatturabili (prezzo propagato + flag prezzo_bloccato)
   |
   v
fatture_righe (arrotondamento a 6 decimali per esposizione fiscale)
```

Quando il resolver risolve un prezzo per un'attivita` di commessa, il valore viene **congelato** in `commesse_attivita.prezzo_snapshot` insieme al riferimento `listino_versione_id`. Da li` viene propagato in `attivita_fatturabili.prezzo_snapshot`. La pipeline di fatturazione legge **direttamente da `attivita_fatturabili`**, NON ricalcola il prezzo dal listino.

**Conseguenza**: se modifichi una riga prezzo di una versione gia` ATTIVA, le fatture **gia` emesse non cambiano** (perche` non rileggono il listino). Cambiano solo le **future** risoluzioni, creando un **drift** silenzioso tra documenti storici e prezzo "ufficiale". Audit incoerente.

**Per questo motivo le righe in versione ATTIVA sono immutabili.** Per cambiare un prezzo si deve creare una nuova versione (V002) con `valido_dal` futuro, e nessun documento gia` emesso viene toccato.

Per correggere errori su fatture **gia` emesse** esiste il dominio rettifiche (DB-L4, da implementare) — vedi §8.

---

## 5) Stato implementativo attuale (cosa funziona, cosa manca)

### 5.1 Cosa funziona ✅

**Database**:

* Tabelle `listini`, `listini_versioni`, `listini_righe`, `listini_associazioni` complete
* Vincoli CHECK + GIST exclusion + unique parziali
* Funzione `fn_resolve_prezzo_listino` con 7 livelli di specificita` + tie-break + errore esplicito
* Trigger guard di coerenza referenziale e attivazione

**Backend Python**:

* Repository `apps/vendite/db/listini_repository.py` con CRUD completo
* Service `apps/vendite/services/listini_service.py` con validazioni payload, traduzione IntegrityError, transizioni stato
* API view `apps/vendite/api/views_listini.py` con `DomainAPIView`, `handle_post_json`, `@extend_schema`
* Test unitari + smoke test bash
* Guard transizione stato (`_validate_versione_state_transition`) che permette solo BOZZA→ATTIVA, ATTIVA→CHIUSA
* Guard "almeno una riga" per attivazione (`fn_change_versione_state`)

**Frontend**:

* Lista listini con row-expansion default-aperta che mostra le versioni inline
* Mini-tabella versioni con transizioni stato inline (BOZZA→ATTIVA via check icon, ATTIVA→CHIUSA via lock icon)
* Pulsante "Gestisci righe" che apre `VersioneDrawer` con righe prezzo
* Drawer `ListinoDrawer` per testata listino, `ListinoAssociazioniDrawer` per associazioni
* Componente `BillingAccountLookup` riusabile cross-dominio integrato in `ListinoAssociazioniDrawer`
* `ArticoloLookup` con `@select` che pre-carica le UoM operative dell'articolo nel form riga prezzo
* Badge di stato versione con colori (BOZZA giallo / ATTIVA verde / CHIUSA grigio)
* Cache versioni nel store con prune automatico in `fetchList` (preload parallelo)

### 5.2 Cosa manca / e` incompleto ❌

#### 5.2.1 GAP CRITICO (bug-fix prioritario)

* **Backend non controlla lo stato della versione** quando si chiamano `fn_create_riga`, `fn_update_riga`, `fn_delete_riga`. Il frontend nasconde i pulsanti se `stato != BOZZA` (`isBozza` flag), ma il backend non ha guard. Chi chiama l'API direttamente (curl, Postman, futuro client) puo` modificare righe in versione ATTIVA → drift garantito tra listino e snapshot in commessa.
* Stesso problema per `fn_update_versione`: oggi accetta PATCH su qualsiasi campo indipendentemente dallo stato. Andrebbe limitato in base allo stato (es. in ATTIVA solo `valido_al` e `priorita`, in CHIUSA niente).

#### 5.2.2 Mancanza di operazioni di convenienza

* **Clone versione**: non esiste API per "clonare V001 in V002 BOZZA copiando tutte le righe". L'utente deve ricaricare a mano potenzialmente centinaia di righe ad ogni nuovo listino quadrimestrale → non sostenibile.
* **DELETE versione in BOZZA**: oggi non esiste DELETE su versione. L'utente che ha creato una versione sbagliata (es. ha caricato 100 righe e si accorge dell'errore) non puo` buttarla via.
* **DELETE listino mai usato**: oggi non esiste DELETE su listino. Se un utente crea un listino di test e poi lo vuole eliminare (zero versioni, zero associazioni), non puo`.

#### 5.2.3 Mancanza dominio rettifiche (DB-L4)

* Non c'e` ancora il motore rettifiche delta per gestire correzioni retroattive su fatture emesse. Trattato in [sviluppo-rettifiche.md](/dev/work-in-progress/sviluppo-rettifiche). Vedi §8 di questo documento per sintesi.

---

## 6) Analisi del modello operativo per le variazioni di prezzo

Questa sezione raccoglie i ragionamenti emersi in chat sulla gestione operativa "una versione e` ATTIVA, devo cambiare un prezzo, come faccio?".

### 6.1 Tre modelli teorici considerati

#### Modello A — Versione = istantanea immutabile pura

> Una volta ATTIVA, la versione non si tocca mai. Per cambiare anche un solo prezzo si crea sempre una nuova versione completa.

**Pro**: audit perfetto, resolver semplice (gia` cosi`), coerenza assoluta con il principio di immutabilita`.

**Contro**: rumore (tante versioni), serve clone funzione, serve gestire l'overlap tra versioni vecchie e nuove (chiusura programmata della precedente).

#### Modello B — Versione = contenitore lungo, riga = istantanea con date proprie

> La versione resta ATTIVA per anni. La riga porta `valido_dal/valido_al`. Cambiare prezzo = chiudere la riga vecchia al -1 e crearne una nuova nella stessa versione.

**Pro**: una sola versione viva per molto tempo, operativamente semplice (1 click sull'articolo, modifica prezzo).

**Contro**: **richiede modifiche strutturali al DDL** (aggiungere `valido_dal/valido_al` su `listini_righe`, riscrivere unique key, riscrivere resolver). Il modello attuale e` esplicitamente progettato per **NON** avere date sulla riga (vedi `sviluppo-listini.md §5.2`). Cambio architetturale significativo.

#### Modello C — Ibrido pragmatico (variazioni → nuova versione, correzioni puntuali → rettifica controllata in ATTIVA)

> La versione resta ATTIVA. Le variazioni "importanti" si fanno con clone + nuova versione. Le piccole correzioni di errore si fanno in ATTIVA con audit nel meta JSONB.

**Pro**: comodo per gli errori di battitura, evita di creare versioni nuove per correggere "10€" → "10.50€".

**Contro**: **viola il disaccoppiamento dalla fatturazione**. Il prezzo della riga ATTIVA e` gia` snapshot-ato in commessa: modificarlo crea drift tra listino e snapshot. L'audit "perche` quel prezzo era X" diventa non rintracciabile. Inoltre il documento `sviluppo-rettifiche.md` definisce esplicitamente le rettifiche come **delta correttivi** (note credito/debito o attivita` fatturabili negative), **non** come UPDATE in-place del listino.

### 6.2 Modello C ridotto — la proposta operativa effettiva

Dopo l'analisi della doc, gli unici elementi di "modello C" che restano validi sono i **fix bug** e le **operazioni di convenienza**, NON la rettifica controllata in ATTIVA.

#### Operazioni ammesse per stato

| Stato | Righe | Testata versione | Cambio stato |
|---|---|---|---|
| **BOZZA** | Create / Update / Delete liberi | PATCH liberi (codice_versione, valido_dal, valido_al, priorita, meta) | → ATTIVA (se ≥1 riga) |
| **ATTIVA** | ❌ nulla | PATCH solo `valido_al` (programmazione chiusura) e `priorita` | → CHIUSA |
| **CHIUSA** | ❌ nulla | ❌ nulla | (terminale) |

#### Operazioni di convenienza nuove

1. **`POST .../versioni/{src_id}/clona/`** — clone di una versione

   - Crea V_target in BOZZA con `codice_versione`, `valido_dal`, `valido_al`, `priorita` dal payload
   - Copia tutte le righe attive di V_src in V_target
   - Restituisce dettaglio V_target
   - V_src non viene toccata
   - Il clone e` indipendente: editing libero su V_target prima dell'attivazione

2. **`DELETE .../versioni/{id}/`** — elimina versione BOZZA

   - Guard backend: `stato == 'BOZZA'`
   - Cascade DELETE delle righe della versione (mai state usate)
   - 400 se ATTIVA o CHIUSA
   - L'utente puo` ricostruire la storia perche` BOZZA non e` mai stata vista dal pricing

3. **`DELETE .../listini/{id}/`** — elimina listino mai usato

   - Guard backend: `versioni_count == 0 AND associazioni_count == 0`
   - 400 altrimenti (suggerendo `attivo=false` per disattivare)
   - Caso d'uso: listini di test creati per errore

#### Workflow operativo "cambio prezzi quadrimestrale"

1. V001 ATTIVA, valida `2026-01-01..NULL`, contiene 200 righe
2. L'utente vuole cambiare 5 prezzi a partire dal `2026-04-01`
3. Apre la riga V001 in lista, click "Clona versione"
4. Compila dialog clone: `codice_versione = "V002-2026Q2"`, `valido_dal = 2026-04-01`, `valido_al = NULL`, `priorita = 100`
5. Sistema crea V002 in BOZZA con tutte le 200 righe copiate
6. L'utente apre V002, modifica i 5 prezzi che cambiano
7. L'utente apre V001 e fa PATCH `valido_al = 2026-03-31` (programmazione chiusura)
8. L'utente attiva V002 → POST `/stato/` `{"stato": "ATTIVA"}`. Il GIST exclusion non blocca perche` V001 ora termina al 2026-03-31 < V002.valido_dal
9. Quando arriva il 2026-03-31, V001 transita a CHIUSA (manuale o via job futuro). Il filtro temporale del resolver gia` la escludeva dal 2026-04-01, lo stato CHIUSA chiude formalmente il ciclo

#### Cosa NON viene modificato dalle fix

* Vincoli DDL (no overlap, unique parziali, CHECK stato): tutti restano cosi`
* Resolver `fn_resolve_prezzo_listino`: nessuna modifica
* Modello dati `listini_righe`: nessuna data sulla riga, mai
* Pipeline fatturazione: nessuna modifica (gia` disaccoppiata)

### 6.3 Risposte sintetiche alle domande operative emerse in chat

| Domanda | Risposta |
|---|---|
| "BOZZA / ATTIVA / CHIUSA, qual e` la logica?" | BOZZA = sandbox editabile, ATTIVA = operativa immutabile sulle righe, CHIUSA = storica terminale |
| "Se non ci sono righe non portare mai ad ATTIVO" | Gia` garantito: guard service `righe_count > 0` |
| "Prevedere il delete su conferma?" | Si`, solo per BOZZA versione e per listino mai usato (zero figli) |
| "Una volta ATTIVA cosa si puo` fare?" | Sulla testata: PATCH `valido_al` e `priorita`. Sulle righe: nulla. Per cambiare prezzi: nuova versione |
| "Variazioni di prezzo: chiudere riga al -1 o nuova versione?" | Nuova versione, sempre. Le date sulle righe (modello B) sono escluse esplicitamente dal modello attuale |
| "Auto-close magico della versione precedente quando attivo la nuova?" | NO. La chiusura programmata della precedente deve essere esplicita (PATCH `valido_al`) prima di attivare la nuova. L'auto-close violerebbe il principio DB-first di rendere espliciti gli effetti |

---

## 7) Gap implementativi identificati e proposte di fix

### 7.1 Bug-fix critici

#### F1 — Guard stato versione su create/update/delete riga

**File**: `backend/apps/vendite/services/listini_service.py`

**Problema**: `fn_create_riga`, `fn_update_riga`, `fn_delete_riga` non controllano lo stato della versione padre. Permettono di modificare righe in versione ATTIVA o CHIUSA → drift con commessa.

**Fix proposto**: aggiungere a tutte e tre le funzioni un guard early-fail:

```python
versione = _get_versione_or_raise(listino_id, versione_id, function_name=function_name)
ErrorManager.require(
    versione["stato"] == "BOZZA",
    code="E_VENDITE_VALIDATION",
    message="Operazione non consentita.",
    detail=f"Le righe sono modificabili solo in versioni BOZZA. Stato corrente: {versione['stato']}.",
    context={"versione_id": versione_id, "stato": versione["stato"]},
    function_name=function_name,
    log_to_db=True,
)
```

#### F2 — Whitelist campi PATCH versione in base allo stato

**File**: `backend/apps/vendite/services/listini_service.py:fn_update_versione`

**Problema**: oggi PATCH versione accetta qualsiasi campo su qualsiasi stato. Andrebbe limitato.

**Fix proposto**:

* Stato `BOZZA`: tutti i campi (codice_versione, valido_dal, valido_al, priorita, attivo, meta)
* Stato `ATTIVA`: solo `valido_al` e `priorita` (programmazione chiusura + tie-break)
* Stato `CHIUSA`: rifiuta qualsiasi PATCH

Implementazione: dopo `_get_versione_or_raise`, verificare `versione["stato"]` e validare i campi presenti nel payload contro la whitelist consentita.

#### F3 — Test pgTAP / smoke per i guard nuovi

* pgTAP test: tentare INSERT/UPDATE/DELETE riga in versione ATTIVA → atteso errore (oggi se il guard e` solo nel service Python il pgTAP da solo non basta, ma vale come scudo defense-in-depth se in futuro si aggiungesse anche un trigger DB)
* Smoke test bash: aggiungere casi negativi a `smoke-test-listini.sh`

### 7.2 Operazioni di convenienza da implementare

#### O1 — Clone versione

**Backend**:

* Nuovo metodo repository: `clone_versione(src_versione_id, target_data) -> int`
  ```sql
  -- Pseudocodice transazione
  INSERT INTO listini_versioni (listino_id, codice_versione, valido_dal, valido_al, priorita, stato)
    SELECT listino_id, %(target_codice)s, %(target_valido_dal)s, %(target_valido_al)s, %(target_priorita)s, 'BOZZA'
      FROM listini_versioni WHERE id = %(src_id)s
    RETURNING id;
  -- poi
  INSERT INTO listini_righe (listino_versione_id, articolo_id, uom_id, billing_account_id, utility_id, emittente_soggetto_ruolo_id, prezzo, attivo, meta)
    SELECT %(target_versione_id)s, articolo_id, uom_id, billing_account_id, utility_id, emittente_soggetto_ruolo_id, prezzo, true, meta
      FROM listini_righe
      WHERE listino_versione_id = %(src_id)s AND attivo IS TRUE;
  ```
* Nuovo service `fn_clone_versione(listino_id, src_versione_id, payload)`:
  - valida `payload.codice_versione` non vuoto e univoco per listino
  - valida `payload.valido_dal` >= oggi (no retroattivo, vedi D2 in §9)
  - valida coerenza date `valido_al > valido_dal` se entrambe presenti
  - chiama repository in transazione
  - restituisce dettaglio target
* Nuova view `ApiListinoVersioneClona(DomainAPIView)` con `POST /api/v1/vendite/listini/{id}/versioni/{src_id}/clona/`

**Frontend**:

* Pulsante "Clona" sulla riga versione (sempre disponibile, qualsiasi stato della sorgente)
* Dialog `CloneVersioneDialog.vue`: campi `codice_versione`, `valido_dal`, `valido_al`, `priorita`. Pre-compilati con suggerimenti (codice = src + suffisso, valido_dal = oggi+1)
* Dopo conferma → POST API → invalida cache versioni → expansion mostra la nuova V_target

#### O2 — DELETE versione BOZZA

**Backend**:

* Repository: gia` esiste `delete_versione`? Verificare. Se no aggiungere `delete_versione(listino_id, versione_id) -> bool` con DELETE CASCADE sulle righe (o DELETE manuale prima delle righe)
* Service `fn_delete_versione`:
  - guard `stato == 'BOZZA'`
  - delete in transazione (righe + versione)
  - restituisce `{"deleted": true, "id": versione_id}`
* View `ApiListinoVersioneDetail` esistente: aggiungere metodo `delete()`

**Frontend**:

* Pulsante "Elimina" sulla riga versione, **visibile solo se `stato == BOZZA`**
* Conferma modale: "Eliminare definitivamente la versione X? Tutte le righe verranno eliminate."

#### O3 — DELETE listino mai usato

**Backend**:

* Service `fn_delete_listino`:
  - guard `versioni_count == 0 AND associazioni_count == 0`
  - DELETE in transazione
* View `ApiListinoDetail` esistente: aggiungere metodo `delete()` con messaggio chiaro su 400 ("Per disattivare un listino con figli usa PATCH con `attivo=false`")

**Frontend**:

* Pulsante "Elimina" sulla riga listino in lista, **visibile solo se entrambi i conteggi sono 0** (gia` ritornati nella SELECT lista)
* Conferma modale chiara

### 7.3 Modifiche frontend di completamento

* `ListinoDrawer.vue`: in stato ATTIVA disabilitare campi non modificabili (mostrare solo `valido_al` e `priorita` come editabili). In CHIUSA tutto readonly.
* `VersioneDrawer.vue`: gia` ha `isBozza` per nascondere le azioni su righe — verificare che funzioni anche dopo le fix backend (la UX e` coerente).
* Avviso UX su PATCH `valido_al` di versione ATTIVA: dialog che spiega "Stai programmando la chiusura della versione al X. Dal Y i contesti gestiti da questa versione non avranno prezzo, a meno che non esista una versione successiva. Confermi?"

---

## 8) DB-L4 Rettifiche prezzi (analisi parallela)

Questa sezione e` un riassunto di [sviluppo-rettifiche.md](/dev/work-in-progress/sviluppo-rettifiche), inserito qui per averla a portata di mano durante la riflessione.

### 8.1 Obiettivo

Gestire le **modifiche retroattive ai prezzi** senza riscrivere documenti gia` emessi. Quando un prezzo viene corretto dopo che una o piu` fatture hanno gia` applicato il valore precedente, il sistema deve produrre **documenti correttivi delta** (NDC/NDD o attivita` negative/positive) tracciati in modo deterministico e idempotente.

### 8.2 Principi non negoziabili

1. **Nessuna riscrittura distruttiva di fatture emesse**: le fatture storiche restano immutate in `fatture` e `fatture_righe`
2. **Rettifica sempre tramite delta tracciato** con audit completo
3. **Motore unico** per canale manuale e automatico (zero divergenze tra processi umani e batch)
4. **Idempotenza**: rilanciare la stessa analisi produce lo stesso set di delta (no doppi conteggi)
5. **Confinamento al layer pricing**: il motore delta non conosce dettagli di fatturazione fiscale, si appoggia su `attivita_fatturabili`

### 8.3 Flusso comune (entrambi i canali)

1. **Rilevazione mismatch prezzo**: confronto tra il nuovo prezzo risolto via `fn_resolve_prezzo_listino` e il prezzo gia` snapshot in `attivita_fatturabili.prezzo_snapshot` (solo se `prezzo_bloccato = FALSE`)
2. **Calcolo delta** per perimetro (riga / documento / periodo)
3. **Emissione documento correttivo**:
   - attivita` negativa/positiva se la riga non e` ancora fatturata
   - NDC/NDD se la riga e` gia` in fattura emessa
4. **Audit esito**: registrazione delta calcolato, riga sorgente, riga correttiva, motivo, canale, operatore/job

### 8.4 Canali

| Canale | Innesco | Conferma | Uso tipico |
|---|---|---|---|
| `MANUALE` | Operatore da UI | Esplicita (preview → confirm) | Volumi piccoli, correzioni puntuali |
| `AUTOMATICA` | Job schedulato su `UPDATE` retroattivo `listini_versioni`/`listini_righe` | Policy-driven (soglie, perimetro) | Volumi massivi utilities |

### 8.5 Bloccanti aperti (da `sviluppo-rettifiche.md §6`)

1. [ ] **Perimetro ricerca rettifiche retroattive**:
   - finestra temporale massima (es. "rettifiche ammesse solo entro N anni")
   - criterio di stop se intercetta righe con `prezzo_bloccato = TRUE` (skippare? errore? emettere?)
   - gestione righe con override manuale documento (escludere?)

2. [ ] **Formato audit rettifica minimo**:
   - tabelle dedicate `vendite.rettifiche` + `vendite.rettifiche_righe`?
   - oppure campi su `attivita_fatturabili`?
   - campi minimi: id originale, id correttiva, delta, motivo, canale, operatore/job, timestamp, hash idempotenza

3. [ ] **Perimetro v1**: solo `FIXED` attivo. Formula/scaglioni v2

4. [ ] **Regole operative di segmentazione listini** per minimizzare `AMBIGUOUS_PRICE_MATCH` in produzione

### 8.6 Interazione con il modello v1 corrente

Importante: la **mancanza** del motore rettifiche **non e` un problema oggi** perche`:

* Il modello v1 e` immutabile sulle versioni ATTIVE → non si verifica mai un UPDATE retroattivo silenzioso
* Per cambiare un prezzo si crea sempre una nuova versione → niente impatto su attivita` gia` snapshot
* Le fatture gia` emesse non vengono mai toccate dal flusso normale

Il motore rettifiche serve nei casi di:

* Errore "vero" su un prezzo gia` applicato in fattura → necessario emettere NDC/NDD
* Modifica retroattiva (rara) di una versione gia` ATTIVA in seguito a contenzioso commerciale → necessario ricalcolare i delta

In assenza del motore rettifiche, oggi questi casi vengono gestiti **manualmente** dall'operatore con NDC/NDD create a mano. Il motore automatizza il processo.

### 8.7 Stato implementazione

* DB-L4 = **DA IMPLEMENTARE** (nessuna delle tabelle/funzioni esiste ancora)
* Backend / frontend = nemmeno avviato
* Prerequisito: chiusura dei bloccanti §8.5

---

## 9) Decisioni chiuse (2026-04-07)

Domande operative discusse in chat e chiuse il 2026-04-07. Le scelte effettive sono qui sotto e governano gli sprint A/B.

### D1 — Modello operativo "C ridotto" ✅ CONFERMATO

Procediamo con:

* Fix bug guard stato (F1, F2, F3)
* Operazioni di convenienza (O1 clone, O2 delete versione BOZZA, O3 delete listino mai usato)
* **Niente** rettifica controllata in versione ATTIVA
* Le rettifiche vere finiscono nel dominio DB-L4 separato (sospeso, vedi D4)

### D2 — Clone versione: `valido_dal` retroattivo AMMESSO con vincolo

**Decisione**: retroattivo ammesso, ma con vincolo:

* `nuova.valido_dal >= precedente.valido_dal` (non si puo` retro-datare prima dell'inizio della versione che si sta sostituendo)
* Dialog di conferma in UI che avvisa: *"Stai creando una versione con decorrenza retroattiva. Le fatturazioni gia` emesse nel periodo non verranno modificate automaticamente. Per correggerle e` necessaria una rettifica (dominio DB-L4)."*

**Conseguenza**: il dominio rettifiche resta separato (D4 sospeso), ma il clone retroattivo e` permesso per casi operativi reali. L'operatore consapevole accetta il drift sui documenti pregressi.

### D3 — Attivazione nuova versione: auto-close della precedente

**Decisione**: l'attivazione di una nuova versione chiude **automaticamente** la versione precedente dello stesso listino.

* Quando si esegue `POST .../versioni/{nuova_id}/stato/ {"stato": "ATTIVA"}`:
  1. il backend trova le versioni `ATTIVA + attivo` dello stesso listino con `valido_dal < nuova.valido_dal`
  2. per ognuna esegue `valido_al = nuova.valido_dal - 1` (nella stessa transazione)
  3. attiva la nuova versione
* Dialog di conferma in UI prima di attivare: mostra l'elenco delle versioni che verranno auto-chiuse e la nuova `valido_al` calcolata
* Se nessuna versione precedente attiva esiste → attivazione semplice senza prompt

**Nota architetturale**: questa decisione **ribalta** la posizione del §6.3 ("auto-close NO"). Il razionale e` che l'auto-close riduce gli errori operativi (no overlap accidentale, no buchi temporali) e centralizza la transizione in un solo step utente. Resta esplicito perche` mostrato in dialog prima dell'esecuzione.

### D4 — Rettifiche DB-L4: SOSPESO

Cantiere rinviato. Le rettifiche oggi si gestiscono manualmente con NDC/NDD ad-hoc. I bloccanti §8.5 restano da analizzare quando si riprendera`.

### D5 — Tre azioni separate (no wizard)

**Decisione**: 3 azioni indipendenti, nessun wizard:

1. **Clona** (genera nuova versione BOZZA copiando le righe della sorgente)
2. **Modifica** (editing libero in BOZZA)
3. **Attiva** (transizione BOZZA → ATTIVA che innesca l'auto-close della precedente — vedi D3)

L'operatore combina le 3 azioni nell'ordine che preferisce. Niente PATCH manuale di `valido_al` sulla precedente: e` l'attivazione della nuova che lo fa.

### D6 — Auto-close gestito dall'attivazione (no job notturno)

**Decisione**: la chiusura automatica della versione precedente avviene **al momento dell'attivazione della nuova** (vedi D3), nella stessa transazione DB. Niente job pgAgent notturno.

**Conseguenza operativa**: dopo l'attivazione, la versione precedente resta in stato `ATTIVA` ma con `valido_al` chiuso. Il filtro temporale del resolver la esclude automaticamente dalla data successiva. La transizione formale `ATTIVA → CHIUSA` resta manuale (caso d'uso ridotto: solo per pulizia visiva storica).

### D7 — Audit righe BOZZA: sandbox totale (no-op)

**Decisione**: nessun tracciamento di history sulle righe in BOZZA. In futuro, se servira`, l'utente aggiungera` la colonna `storico` (booleana) sulla versione che abilita la storicizzazione completa. Per ora **non implementare nulla**: il `data_update`/`user_update` standard basta.

---

## 10) Roadmap proposta (post-decisioni)

Dopo aver chiuso D1-D7, proporrei questo ordine di esecuzione:

### Sprint A — Fix bug e completamento ciclo di vita

1. F1 — Guard stato versione su CRUD righe
2. F2 — Whitelist PATCH versione per stato
3. F3 — Test smoke + unit per i guard nuovi
4. Aggiornamento doc concettuale `manual/listini_versioni.md` con regole esplicite per stato

### Sprint B — Operazioni di convenienza

5. O1 — Clone versione (backend + frontend + smoke + test)
6. O2 — DELETE versione BOZZA (backend + frontend)
7. O3 — DELETE listino mai usato (backend + frontend)
8. Avviso UX su PATCH `valido_al` ATTIVA

### Sprint C (opzionale) — Job automazione

9. Job pgAgent transizione ATTIVA → CHIUSA per versioni con `valido_al` passata
10. Test pgTAP del job

### Cantiere DB-L4 (separato, non in questo sprint)

* Vedi `sviluppo-rettifiche.md` per il dettaglio
* Prerequisito: chiusura bloccanti §8.5

---

## 11) Note finali

Questo documento e` un **WIP di analisi**, non una specifica chiusa. Contiene sintesi della doc esistente + ragionamenti operativi che hanno bisogno di essere validati prima di passare al codice.

Una volta chiuse le decisioni D1-D7, parti di questo documento possono essere:

1. Migrate in `sviluppo-listini.md` (documento padre) come §11 "Ciclo di vita versione e operazioni di gestione"
2. Migrate in `guide/gestione-listini.md` come "Workflow operativo" per l'utente finale
3. Lasciate qui come storico delle decisioni (questo documento puo` diventare l'archivio di razionali)

Il documento andra` aggiornato man mano che le decisioni vengono prese.

---

*Sviluppo Listini v2 — ZeroERP (aprile 2026, WIP analisi e sintesi)*
