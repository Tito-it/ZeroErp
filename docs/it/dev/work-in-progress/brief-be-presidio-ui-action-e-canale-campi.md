# Brief BE — Presidio C2: la `ui_action` promessa e il canale che la realizza

> **Destinatari:** backend (`dev/backend-tid`); il team DB per la metà
> PL/pgSQL del canale (**§4**).
>
> **Tipo:** brief di cantiere. Nasce dal candidato **C2** di
> [analisi-presidi-percorso-storto.md](../work-done/analisi-presidi-percorso-storto.md)
> (chiusa il 2026-09-19) e dalla **decisione di Tid del 2026-09-09** in
> [api.md §«Cosa cambia davvero lo status»](../api.md), che quel candidato
> aveva perso per dieci giorni.
>
> **Da leggere per primo: §2 — che cosa è il presidio, e che cosa NON è.**
>
> **Stato:** 🔵 aperto — misurato col criterio pieno (§3-bis) e **sanato lato
> Python il 2026-09-21** (§3-ter: 13 codici mandano il campo, 16 override
> tolti, `PayloadValidator` allineato); sette decisioni prese da Tid (§5).
> Al team DB: la vista del §4, i 37 codici PL/pgSQL da sanare, due ritiri.
> Il test nasce dopo (decisione 5). La prima
> misura (§3, 2026-09-19, criterio grezzo) resta come storia. ✅ La richiesta
> BE §6 di C1, accodata qui dal team DB, è **chiusa il 21-09**:
> `apps/core/tests/test_stati_check_scrittori_python.py` (§7).
>
> **Da leggere per primo, dopo il §2: §3-bis — la misura vera, e i due difetti
> di meccanismo che ha trovato senza cercarli.**
>
> **Origine:** Tid, 2026-09-19 — *«fai sia C1 che C2, così chiudiamo l'analisi e
> abbiamo i brief su cui lavorare»*.

---

## 1. Il difetto, sul modello

Ogni codice errore porta a catalogo una **promessa all'interfaccia**:
`ui_action`. Dal 2026-08-07 si deriva dalla classe, e **182** codici la
sovrascrivono con una decisione scritta in `error_ui_overrides.py`, ciascuna
con la sua ragione. **129** di quelle decisioni dicono `highlight_form_fields`:
*«evidenzia il campo del form»*.

Ma il campo non lo evidenzia `ui_action`. Lo evidenzia un **altro canale**:
`error.fields` → `campiErrati` → `:invalid` sull'input, alimentato da
`context={"field": …}` in Python e da `RAISE … USING COLUMN` in PL/pgSQL. La
decisione di Tid del 09-09 lo dice in chiaro: `highlight_form_fields` **è
servita da `campiErrati`**, come `redirect_login` è servita dallo status 401 e
le altre quattro dal toast.

⇒ **La promessa e il comportamento viaggiano su due binari**, e possono
divergere in silenzio:

| Il catalogo promette | Il punto che solleva manda | A video |
| --- | --- | --- |
| `highlight_form_fields` | nessun `field` | un toast, nessun campo rosso: la promessa è vuota |
| `show_error_banner` | `field` | il campo si accende comunque: la promessa non decide niente |

Nessuno dei due casi fallisce. Nessun test li vede. È esattamente la classe del
percorso storto: un contratto **emesso** — con 182 decisioni motivate — di cui
nessuno verifica che sia **mantenuto**.

⚠️ **E la condizione che Tid ha messo per accendere un secondo consumatore di
`ui_action` è proprio questa**: *«le 176 righe di override vanno riguardate
prima, non dopo — sono state decise quando nessuno poteva verificarle a
video»*. Un giro a mano le riguarda una volta; questo presidio le riguarda **a
ogni PR**.

---

## 2. Che cos'è il presidio — e che cosa non è

### 2.1 La regola

> Per ogni codice con `ui_action = highlight_form_fields` (override o default
> di classe) esiste **almeno un** punto di sollevamento che valorizza il
> canale `fields`; e un codice il cui **ogni** punto di sollevamento valorizza
> `fields` non promette un'altra `ui_action` — salvo esenzione motivata.

Due versi, e servono entrambi: il primo è la promessa vuota, il secondo è la
promessa che non decide.

### 2.2 Che cosa NON è

* ⛔ **Non è un presidio sul consumo** («quanti componenti leggono
  `azioneUi`»). L'analisi l'ha misurato tre volte e ha sempre detto zero — e
  sarebbe zero anche a presidio scritto, perché il consumatore giusto di sei
  valori su sette è il **default** del client, e il default non si conta. Il
  settimo (`confirm_and_retry`) ha i suoi due lettori (`useForzaturaConfermata`,
  `useRigheDaRate`) e non serve un cancello per contarli.
* ⛔ **Non è una rilettura delle 182 ragioni.** La ragione scritta accanto a
  ogni override resta una decisione di interfaccia; il presidio verifica che il
  **meccanismo** la possa onorare, non che la scelta sia giusta.
* ⛔ **Non ricalcola la resa a video.** Che `campiErrati` accenda l'input lo
  presidiano già `useApiHandler.spec.js` e i binding nei componenti (67 `.vue`
  al 19-09).

### 2.3 Le sorgenti, tutte in git

| Lato | Dove sta il codice | Dove sta il campo |
| --- | --- | --- |
| Python | `ServiceError(code=…)` / `ErrorManager.require(…, code="E_X", …)` / `raise_error(…)` | `context={"field": <nome>}` o `fields=(…)` sulla stessa chiamata, **oppure** la chiamata passa da un BB che lo mette da sé: `PayloadValidator(validation_code=…)` (⚠️ **non sempre**, vedi sotto), `map_integrity_error` (terzo elemento della tupla), `create_with_constraint_mapping` |
| PL/pgSQL | `script.fn_log_and_raise_error(area, fn, 'E_X', context, …)` | `context ->> 'campo'`, **con ripiego su `context ->> 'parametro'`** (tolto il prefisso `p_`) — è l'helper a farlo, riga 182-185 del corpo, e `api.md` lo dice dall'08/08: *«il ripiego su `parametro` copre quasi tutti i punti»*. Una misura che guarda la sola chiave `campo` (com'era la §3) conta la metà del canale. L'helper consegna il nome come `COLUMN` e `diagnostica_db` lo legge; i corpi si leggono dalla doc auto-generata `dbzero` o da `pg_proc` sul DB provvisto |
| DB, per riflesso | i codici sollevati da `fn_raise_primo_motivo_se_presente` | il `campo` sta nel motivo che la `fn_check_*` emette |

⚠️ **Due cose che questa tabella diceva sbagliate fino al 21-09, corrette
leggendo il codice e non il ricordo:**

1. **`PayloadValidator` NON mette `field` «sempre».** Su 33 punti che sollevano
   `self._code`, **8 metodi** lo omettono: `validate_allowed_keys`,
   `validate_order_by`, `reject_keys`, `guard_positive_int`,
   `guard_non_empty_string`, `optional_smallint`, `optional_bool`,
   `optional_meta`. Ma non sono tutti un difetto, e la scrittura l'ha
   distinto: **tre** estraggono dal *payload* con una `key` — `optional_smallint`,
   `optional_bool`, `optional_meta` — e scrivevano `context={key: value}`, la
   chiave col **nome** del campo invece della stringa `"field"`: sanati il 21-09
   (§3-bis.4). Gli altri cinque **non devono** mandarlo: `guard_positive_int` e
   `guard_non_empty_string` sono guard su parametri *non da payload* (un id
   dall'URL: accendere un input che sul form non c'è è il difetto opposto,
   `api.md` §Envelope), `validate_order_by` è un parametro di lista,
   `validate_allowed_keys`/`reject_keys` parlano di chiavi che il form non ha.
2. **Il canale DB ha due chiavi**, `campo` e `parametro`: la seconda è quella
   usata in 225 punti su 111 funzioni (misura dell'08/08 nel corpo dell'helper),
   la prima in 8. Contare la sola `campo` — la §3 lo faceva — dava 21 corpi;
   con entrambe i punti che mandano il nome sono la maggioranza (§3-bis).

⭐ **La forma è quella di `test_naming_codice_interno_python`**: ricerca
testuale sulle sorgenti Python (AST dove serve: la chiamata e i suoi kwargs),
lettura dei corpi PL/pgSQL, registro chiavato su `(codice, lato) → esito`, e
**mai** sul numero di riga. Le sorgenti che i test esistenti già leggono:
`test_error_codes_declared_guardrail` (i punti di chiamata Python per codice),
`dbops.vw_codici_errore_da_dichiarare` (i letterali nei corpi vivi).

### 2.4 Il registro delle esenzioni, con la ragione

Ci sono casi in cui la promessa e il canale divergono **di proposito**, e il
precedente è già scritto in `error_ui_overrides.py` il 15-09:
`E_EMITTENTE_NON_RISOLTO` non ha override — banner — «perché il rimedio è la
combo dell'emittente in alto, non un campo del form; e `fields`, quando il DB
lo manda, accende comunque l'input». È il verso 2 esente con la ragione.

Il registro vive **nel test**, come `test_naming_codice_interno_python` e
`test_perimetro_emittente_copertura`: `(codice, verso) → ragione`. ⛔ Non nel
file degli override — quello porta la ragione della **scelta**, non
dell'eccezione al presidio, e mescolarle farebbe di ogni riga una sede doppia.
Verso di ritiro obbligatorio: una riga di registro il cui codice ora soddisfa
la regola è rossa.

---

## 3. La prima misura — 2026-09-19, criterio grezzo

*Fatto datato, e il criterio è dichiaratamente più rozzo di quello del §2.3:
per il lato Python «il file che nomina il codice contiene anche `"field":`»,
per il lato DB «il corpo che nomina il codice contiene anche `'campo'`».
Non vede i BB che mettono il campo da sé (`PayloadValidator`), quindi
sovrastima i rossi. Serve a dire l'ordine di grandezza, non l'elenco.*

Dei **129** codici con `highlight_form_fields` in override:

| Esito grezzo | Codici |
| --- | --- |
| un sito Python nello stesso file di un `"field":` | 24 |
| un corpo PL/pgSQL con `'campo'` | 21 |
| nominati in Python o in una funzione, **senza** traccia del canale | **75** |
| **nessun sito** che li nomini (né Python né funzione viva) | **9** — sotto |

I nove senza sito, letti uno per uno — ed è la parte che vale:

| Codici | Che cosa sono | Esito |
| --- | --- | --- |
| `CF_NON_VALIDO`, `PIVA_NON_VALIDA`, `E_PREV_EMITTENTE_NON_RISOLTO`, i quattro `TEMPLATE_FLUSSO_*` | **ritirati** a catalogo (`CODICI_RITIRATI`) | non è un difetto: l'override resta perché un codice ritirato deve continuare a risolvere per il diario (api.md). Il presidio li **esclude per costruzione**, non li registra |
| `E_CONTATTO_INCOMPLETO` | sollevato in due punti via la **costante** `anagrafiche/error_codes.py` | falso positivo del criterio testuale: un codice passato per nome di costante non si vede con un grep sul letterale. ⚠️ `test_error_codes_declared_guardrail` li risolve già con l'AST — il presidio riusa **quella** risoluzione, non ne scrive una seconda |
| `E_ATTIVITA_VALIDATION` | vivo a catalogo, **nessun** sito Python né PL/pgSQL lo nomina | **l'unica promessa vuota per costruzione** trovata dal criterio grezzo: un override per un codice che nessuno solleva. Candidato al ritiro (`obsoleto_dal`), non al registro |

⭐ **Che cosa dice davvero questo numero.** Non che 75 promesse siano vuote — la
maggior parte passerà da `PayloadValidator`, che il criterio non vede. Dice tre
cose più utili:

1. il criterio **vero** deve conoscere i BB e risolvere le costanti (§2.3), o
   il registro nascerebbe con settanta righe e nessuno lo leggerebbe (guida
   presidi §6.4);
2. i **ritirati** escono dal perimetro prima di misurare — sette su nove
   «senza sito» erano quello;
3. resta **un** codice con una promessa e nessun mittente: è piccolo, ed è
   esattamente la grana che il presidio deve vedere da solo il giorno che ne
   nasce un altro.

⚠️ Il verso 2 (codici con un'altra `ui_action` che mandano sempre `fields`) non
è ancora misurato: richiede il criterio pieno, perché «sempre» si dice solo
guardando ogni sito.

---

## 3-bis. La seconda misura — 2026-09-21, criterio pieno

*Fatto datato, sul DB di sviluppo (`pg_proc`, funzioni `plpgsql`) e sui `.py`
non di test di `backend/apps` a HEAD `950952a05`. È la misura con il criterio
del §2.3 corretto — BB compresi, costanti risolte anche se **importate**
(`from apps.anagrafiche.error_codes import E_CONTATTO_INCOMPLETO`), le due
chiavi a DB. Serve a dimensionare il registro e a decidere il §5; il presidio la
rifarà nella sua sede (§4), non ricopiando questi numeri.*

### 3-bis.1 Il perimetro

**121** codici vivi con `ui_action = highlight_form_fields` — tutti da override
(nessuna classe ha quel default). I **129** del §3 contavano anche i ritirati,
che escono per costruzione (`CODICI_RITIRATI`). Sull'altro verso: **681**
codici vivi con un'altra `ui_action`.

### 3-bis.2 Verso 1 — la promessa vuota

| Esito | Codici | Che cosa vuol dire |
| --- | ---: | --- |
| **canale valorizzato** in almeno un sito | **35** | la promessa è mantenuta |
| canale **forse**: `context` in una variabile del corpo (`l_error_ctx := jsonb_build_object('campo', …)`) | **17** | il criterio testuale a livello di chiamata non lo vede; la vista del §4 lo può seguire. Tutti a DB |
| **promessa vuota**: siti trovati, **nessuno** manda il nome | **66** | ▶ sotto |
| **nessun sito** che li nomini | **3** | ▶ sotto |

I **66**, per lato: **28** con soli siti Python, **37** con soli siti PL/pgSQL,
**1** con entrambi (`E_PREV_UTILITY_ISTANZA_INCOERENTE`). Non sono tutti la
stessa cosa, e la lista va letta codice per codice — ma **tre famiglie** si
vedono a occhio:

* **i `*_VALIDATION`/`*_VALIDAZIONE` generici** (`E_AMM_VALIDAZIONE`,
  `E_DDT_VALIDAZIONE`, `E_CORE_VALIDATION`, `E_PIPELINE_VALIDATION`,
  `E_RESET_LOTTO_VALIDATION`, `E_FLUSSO_VALIDATION`, `E_PRATICA_VALIDATION`,
  `E_SEARCH_VALIDATION`, …): sollevati con `detail` parlante e **nessun campo**.
  Alcuni siti un campo ce l'hanno davvero (`E_CORE_VALIDATION` su `tabella`
  della query string) — ma un parametro di query string non è un input del
  form: lì la promessa è **sbagliata**, non il canale;
* **le mappe di `map_integrity_error` a due elementi** (`E_ANAG_FK`,
  `E_CONFIG_MATRICE_FK`, `E_NOTA_FK`, `E_NOTA_CHECK_VIOLATION`,
  `E_TEMPLATE_CODICE_DUPLICATO`): il BB porta il campo **solo se la tupla ha il
  terzo elemento**, e queste non ce l'hanno. È il caso più economico da
  chiudere, ed è il caso per cui la regola «si dichiara solo quando è vero»
  del catalogo BB va riletta voce per voce;
* **i guard PL/pgSQL col nome della colonna come CHIAVE del context**:
  `jsonb_build_object('quantita', NEW.quantita)` (`E_QTA_NON_POSITIVA`,
  tre trigger dei resi), e la stessa forma su `E_CONTO_BANCARIO`,
  `E_FORMA_GIURIDICA_PAESE`, `E_TIPO_INDIRIZZO_NON_PERMESSO`… — il nome c'è,
  ma sta nel posto che l'helper **non legge**. È il gemello DB del
  `{field: value}` di `PayloadValidator` (§3-bis.4).

I **3 senza sito**:

| Codice | Che cos'è | Esito |
| --- | --- | --- |
| `E_ATTIVITA_VALIDATION` | già in §3 | conferma: nessuno lo solleva |
| `E_ONERE_CAUSALE_NON_VALIDA` | vivo a catalogo; **nessuna funzione in `pg_proc` lo nomina**; il solo Python è il *marker* di traduzione in `commesse_service._ONERE_DB_ERROR_MARKERS` | **secondo caso «promessa e nessun mittente»**: un marker che aspetta un codice che il DB non solleva più. Stessa domanda della decisione 2 |
| `E_DOCUMENTO_DATA_ANTERIORE_ULTIMO_NUMERO` | `fn_get_next_progressivo` lo sceglie con un `CASE` in una **variabile** (`v_codice_seq`) e la passa all'helper | **falso positivo del criterio**: il codice non è un letterale nella chiamata. La vista del §4 deve leggere i codici come `vw_codici_errore_da_dichiarare` — *ogni letterale nel corpo*, volutamente larga — e non solo dentro la chiamata |

### 3-bis.3 Verso 2 — la promessa che non decide

**52** codici con un'altra `ui_action` (tutti `show_error_banner`, uno
`show_empty_state`) i cui siti mandano **tutti** il nome del campo. Fra questi
`E_EMITTENTE_NON_RISOLTO`, il precedente del §2.4 — quindi la misura lo trova, e
il registro delle esenzioni a verso 2 nasce con quella riga. Gli altri 51 sono
da guardare uno per uno, ma la domanda è la stessa: *a video il campo si
accende comunque*, quindi è una decisione di interfaccia da confermare, non un
difetto da sanare (decisione 1).

### 3-bis.4 ⭐ I due difetti di MECCANISMO, trovati senza cercarli

Il presidio verifica che il meccanismo **possa** onorare la promessa (§2.2). La
misura ha trovato due punti in cui il meccanismo la tradisce **avendo il nome in
mano**, uno per lato, con la stessa forma:

| Lato | Forma | Dove | Effetto |
| --- | --- | --- | --- |
| Python | `context={key: value}` — il nome del campo come **chiave** | 3 metodi di `PayloadValidator` che estraggono dal payload: `optional_smallint`, `optional_bool`, `optional_meta` (6 rifiuti) | `_campi_da_correggere` legge la sola chiave `"field"`: l'envelope usciva **senza `fields`** su un errore che sa esattamente quale input ha sbagliato. ✅ **Sanato il 21-09** (`"field": key`, come le sorelle `require_string`/`optional_string`), con un test per metodo in `test_payload_helpers` (76-78), rossi senza la correzione |
| PL/pgSQL | `jsonb_build_object('quantita', NEW.quantita)` — la colonna come **chiave** | i guard dei resi (`E_QTA_NON_POSITIVA`), conti bancari, forma giuridica, tipo indirizzo, … | l'helper legge `campo` e `parametro`: la `COLUMN` esce **vuota** |

⛔ Non sono decisioni di interfaccia da riguardare: sono il canale che non parla
pur avendo il dato. Sono il caso più vicino allo *«scrivere uno scrittore»*
di C1, e si sanano **prima**, non si registrano — un registro che porta un
difetto risolvibile in una riga di codice non è un debito, è un rinvio
(decisione 6: ✅ lato Python fatto; lato DB resta nella vista del §4).
⚠️ E la prima stesura di questa tabella contava **8** metodi Python come
difetto: letti i corpi, cinque **non devono** mandare il campo (§2.3, punto 1) —
un guard su un id dell'URL che nominasse `field` accenderebbe un input che il
form non ha. *Avere un nome in mano non basta: dev'essere il nome di un input.*

### 3-bis.5 I limiti della misura, dichiarati

* legge le sole funzioni **`plpgsql`**: una funzione `sql` che sollevasse non
  la vede (oggi nessuna lo fa, per costruzione: `fn_log_and_raise_error` è
  `PERFORM`);
* il codice **in variabile** (`E_DOCUMENTO_DATA_ANTERIORE_ULTIMO_NUMERO`) non
  lo vede: la vista del §4 sì, leggendo i letterali del corpo;
* il `context` **in variabile** lo vede solo a livello di corpo (i 17 «forse»);
* sul lato Python un `PayloadValidator` conta come sito **con** campo, benché 8
  metodi non lo mandino (§3-bis.4): a difetto sanato la semplificazione
  diventa vera, ed è un'altra ragione per sanarlo prima.

---

## 3-ter. Sanare prima — la proposta per codice (lato Python, 29 codici)

*Scritto il 2026-09-21 dopo la decisione 5 di Tid («sanare prima»). Letti
tutti i siti (messaggio e chiavi del `context`, dump in appendice al §3-bis).
Per ogni codice UNA delle due strade: **A** = il sito ha un input del form,
si manda il campo; **B** = non c'è un input da accendere, la promessa era
sbagliata e l'override si toglie (torna al banner di classe). ⛔ Nessun codice
resta com'è: «promessa vuota» non è uno stato ammesso.*

⚠️ La regola per scegliere, ed è quella di `api.md` §Envelope e §409-vs-400:
`highlight_form_fields` promette un input **nella pagina in cui l'operatore si
trova**. Un id dall'URL, un parametro di query string, un header, un payload di
comando della coda, uno stato non configurato **non** lo sono: lì il nome che
si ha in mano non è il nome di un input. ⚠️ Dove un codice copre siti dei due
tipi la strada è A (il verso 1 chiede *almeno un* sito), e i siti senza input
restano senza campo — è la forma dichiarata in `api.md`: *«un codice usato per
due cose si spezza a monte»*, ma spezzarlo non è di questo brief.

| Codice | Siti | Strada | Il campo (A) o la ragione (B) |
| --- | ---: | :---: | --- |
| `E_AI_QUERY_EMPTY`, `E_AI_QUERY_TOO_LONG` | 1+1 | **A** | il campo del messaggio: `message`, la chiave del payload di `POST /ai/chat/` |
| `E_AMM_VALIDAZIONE` | 13 | **A** | `username`, `email`, `password`, `qualifica_id`, `cognome`, `nome`, `codice_fiscale`, `soggetto_id` (UUID). Senza campo: `ruolo_sistema non ammesso` ×2, i due del catalogo override, e «Reparto inesistente» — ⚠️ la prima stesura lo dava A con `unita_organizzativa_id`, ma `uo_id` arriva dall'**URL** (`reparti/<uo_id>/profilo/`): non e' un input |
| `E_ANAG_FK` | 5 tuple | **A** | terzo elemento: `categoria_cliente_id`, `utility_id`, `emittente_soggetto_ruolo_id`, `classe_utenza_id`, `listino_id` — da verificare che siano chiavi del **payload** (regola del catalogo BB) |
| `E_CONFIG_MATRICE_FK` | 4 tuple | **A** | `fallback_tipo_indirizzo_id`, `utility_id`, `tipo_ruolo_id`; la voce composta «tipo ruolo **o** tipo indirizzo» resta a due |
| `E_CONTATTO_INCOMPLETO` | 2 | **A** | il `context` porta già `missing` (la lista dei campi mancanti): diventa `fields=tuple(missing)` — è il caso per cui `ServiceError.fields` esiste |
| `E_DDT_VALIDAZIONE` | 20 | **A** | `billing_account_id` ×2, `destinatario_soggetto_ruolo_id`, `stato_codice`, `articolo_id`, `uom_operativa_id`. Senza campo: stati non configurati, «nessun campo aggiornabile», testata anomala |
| `E_FLUSSO_VALIDATION` | 9 | **A** | `esito` ×3, `template_flusso_id`, `nuovo_stato`, `motivo`; senza campo le due sospensioni (stato) |
| `E_PRATICA_VALIDATION` | 21 | **A** | `emittente_fiscale_id`, `tipo_prestazione_id`, `nuovo_stato`, `tipo_nota_codice`, `contenuto`, `tipo_allegato_codice`, `nome_file`, `motivo`, `priorita_id`, `soggetto_id`; senza campo «operatore non associato», sospensioni |
| `E_NOTA_CHECK_VIOLATION` | 9 tuple | **A** | `anchor_tipo`, `posizione`, `seq`, `testo` ×3; le tre di coerenza restano a due |
| `E_NOTA_FK` | 4 tuple | **A** | `id_stile`, `id_lingua` (le chiavi del payload nota, `_PAYLOAD_KEYS`); le due «riga non trovata» restano a due (`target_riga_id` non è un input) |
| `E_TEMPLATE_CODICE_DUPLICATO` | 1 | **A** | `codice` — il marker DB si traduce in `_raise_known_db_error`: lì il campo si aggiunge come per `map_integrity_error` |
| `E_PREV_UTILITY_ISTANZA_INCOERENTE` | 1 (+1 DB) | **A** | `utility_id`; e il sito DB è del team DB (§4) |
| `E_FLUSSO_ID_OBBLIGATORIO`, `E_FLUSSO_ID_INVALIDO`, `E_PRATICA_ID_OBBLIGATORIO`, `E_PRATICA_ID_INVALIDO` | 1+1+2+2 | **B** | ⚠️ la prima stesura li dava A («chiavi del body di un picker»): letti i siti sono **query string di GET** (`?flusso_id=` per risolvere il preventivo/ordine radice) e parametri di firma. Nessun input |
| `E_CORE_VALIDATION` | 19 | **B** | query string (`page`, `order_col`, `tabella`), lookup di relazione, «utente non trovato»: nessun form |
| `E_SEARCH_VALIDATION` | 11 | **B** | parametri di ricerca e paginazione |
| `E_IDEMPOTENCY_KEY_REQUIRED` | 1 | **B** | è un **header** |
| `E_INVALID_ID` | 47 | **B** | tutti `<x>_id deve essere > 0` su parametri di firma: chiamante rotto, non un input (`AGENTS.md` §riuso o conio: candidato `TECNICO`, ma la classe non è di questo brief) |
| `E_PIPELINE_VALIDATION` | 24 | **B** | stati non configurati, parametri di paginazione del cockpit, ordine dei task, contesto fiscale: ⚠️ tre siti hanno un input (`tipo_doc_fiscale_id`, `utility_id`, `fino_a_stato` del cockpit) — se si vuole A lì, va spezzato prima |
| `E_FATTURAZIONE_GIRO_PAYLOAD`, `E_FATTURAZIONE_NUMERA_PAYLOAD` | 3+3 | **B** | payload di un lavoro in coda, letto dal drenatore |
| `E_GENERATE_FATTURE_RIGHE_VALIDATION`, `E_GROUP_ATTIVITA_VALIDATION` | 1+1 | **B** | `lotto_id`/`attivita_id` di firma |
| `E_RESET_LOTTO_VALIDATION`, `E_RESET_LOTTO_FATTURA_VALIDATION` | 3+1 | **B** | `lotto_id`/`fattura_id`/`gruppo_key` di comando |
| `E_NOTA_RIGA_INCOERENTE` | 1 | **B** | `target_id`/`target_riga_id`: legami, non input |

**Conto**: **13 codici A** e **16 codici B**.

✅ **Applicato il 2026-09-21 (ok di Tid).** A: 44 siti — `context={…,
"field": "<chiave>"}` su `ai_assistant` (2), `amm_software` (8), `ddt_service`
(6), `pratiche` (flusso 6, pratica 13), `preventivi_service` (1); `fields=
tuple(missing)` sui due siti di `E_CONTATTO_INCOMPLETO`; il terzo elemento su
14 tuple (`E_ANAG_FK` 5, `E_CONFIG_MATRICE_FK` 3, `E_NOTA_CHECK_VIOLATION` 6,
`E_NOTA_FK` 2) — e per questo le firme di `translate_db_errors` /
`make_db_errors_translator` passano a `dict[str, tuple]`, come
`map_integrity_error` già dichiarava; per `E_TEMPLATE_CODICE_DUPLICATO`, che
arriva da una UNIQUE violata senza `COLUMN`, nasce `_CAMPO_PER_CODICE_DB` in
`pratiche_service` (il campo per codice quando `diag.fields` è vuoto — stessa
forma del terzo elemento, ⚠️ una forma che il criterio del test deve
conoscere; letta con `_campo_per_codice_db`, che normalizza il prefisso `E_`
come il resto della funzione, e provata da `test_pratiche_service_flussi`
30-31 — anche il verso «la `COLUMN` del DB vince sulla mappa»). B: 16 righe
tolte da `error_ui_overrides.py` con la ragione in testa al dizionario.
⚠️ Lato FE una sola cosa, trovata rileggendo il canale fino all'input:
`ContattoForm.vue` riceveva già `campiErrati` dai tre drawer ma i due
obbligatori (`nominativo`, `tipo_contatto_id`) leggevano solo gli `errors`
della validazione locale — il `fields` di `E_CONTATTO_INCOMPLETO` arrivava
e restava muto. Ora accendono anche su `campiErrati`. Suite verde (4227 test delle sette app toccate). Rimisurato:
**47 canale ok, 17 forse (DB), 38 promesse vuote = i 37 del DB + 1 falso
positivo del criterio** (`E_TEMPLATE_CODICE_DUPLICATO`, che ora passa da
`_CAMPO_PER_CODICE_DB`): lato Python **zero** promesse vuote.

⚠️ I **B** cambiano il contratto: da `highlight_form_fields` a
`show_error_banner`. A video oggi **non cambia niente** (nessun consumatore
ramifica su quei sei valori, `api.md` §Cosa cambia davvero lo status), ed è
esattamente la finestra in cui riguardare le righe costa zero.

✅ Le 29 righe erano decisioni di interfaccia: applicate **dopo** l'ok di
Tid, non prima.

---

## 4. Richiesta al team DB — la metà PL/pgSQL

Il presidio legge i corpi delle funzioni per sapere se il `context` porta
`campo`. Due strade, e il BE sceglie quale:

* **leggere `dbzero`** (la doc auto-generata, in git): zero database, ma il
  parsing è testuale e il criterio resta approssimato;
* **una vista `dbops`** che per ogni `(funzione, codice)` dica se il `context`
  della chiamata a `fn_log_and_raise_error` porta la chiave `campo` — la
  gemella di `dbops.vw_punti_primo_motivo`, letta dal test sul DB provvisto
  (`richiedi_db_provvisto`). ⭐ È la strada che tiene la misura in un posto
  solo (guida presidi §6.3) e che il team DB può presidiare a sua volta col
  rubinetto già esistente.

⭐ **Il BE sceglie la vista** (proposta, decisione 4 del §5): la misura del
§3-bis mostra due cose che un parsing di `dbzero` non regge — il `context` in
variabile (17 codici) e il codice in variabile (1) — e che una vista risolve
leggendo il corpo intero, come fanno già `vw_codici_errore_da_dichiarare` e
`vw_punti_primo_motivo`.

**Il contratto chiesto** — nome proposto `dbops.vw_punti_canale_campo`, una
riga per **(funzione, codice)**:

| Colonna | Che cosa porta |
| --- | --- |
| `funzione` | `schema.nome`, funzione `plpgsql` viva |
| `codice` | ogni letterale `'E_*'` del corpo (senza commenti) — **volutamente largo** come `vw_codici_errore_da_dichiarare`, così il codice scelto in una variabile (`v_codice_seq`) entra |
| `via` | `DIRETTO` (il corpo chiama `fn_log_and_raise_error`) oppure `PRIMO_MOTIVO` (il corpo passa da `fn_raise_primo_motivo_se_presente`: il codice e il campo stanno nella `fn_check_*` — si legge da `vw_punti_primo_motivo`, non si rifà) |
| `canale` | `IN_CHIAMATA` (`'campo'` o `'parametro'` dentro la chiamata all'helper, o nel motivo della check), `IN_VARIABILE` (la chiave è in un `jsonb_build_object` assegnato a una variabile del corpo), `NESSUNO` |
| `chiave` | `campo` / `parametro` / `NULL` — quale delle due: serve a leggere un rosso, e a misurare quante volte il nome del form è quello del parametro |

⚠️ Le due chiavi, non una: `campo` con ripiego su `parametro` è il contratto
dell'helper (§2.3). E il `NESSUNO` con la **colonna come chiave**
(`jsonb_build_object('quantita', …)`, §3-bis.4) merita un'etichetta sua —
`CHIAVE_NON_LETTA` — perché è il caso sanabile, e la vista è il posto dove
si conta.

⚠️ **Pessimista, come `vw_punti_primo_motivo`**: una funzione con più chiamate
all'helper e lo stesso codice in due rami dà la riga migliore fra i rami — un
falso «ok» qui costa una promessa vuota non vista, quindi se il criterio non
sa attribuire la chiamata al codice, dichiara `IN_VARIABILE`, non `IN_CHIAMATA`.

⭐ **E la lista da sanare lato DB, dalla misura del §3-bis** (37 codici a soli
siti PL/pgSQL, criterio pieno, 2026-09-21 — la vista la rifarà, questa è per
partire): `E_ARTICOLO_NON_COMPOSITO`, `E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE`,
`E_BA_SOGGETTO_INCOERENTE_ISTANZA`, `E_BOM_VALIDO_AL_INVALIDO`, `E_COERENZA_ID`,
`E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO`, `E_CONTO_BANCARIO` (2 trigger),
`E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO`, `E_CONTRATTO_CLASSE_TIPO_INCOERENTE`,
`E_CONTRATTO_UTILITY_SENZA_DIMENSIONE_TIPO_CLASSE_VIETATI`,
`E_CONTRATTO_UTILITY_TIPO_CLASSE_OBBLIGATORI`, `E_DATA_ERRATA`,
`E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO` (3 punti), `E_FLUSSI_ESITO_NON_AMMESSO`,
`E_FORMA_GIURIDICA_PAESE`, `E_FORNITORE_ID_INVALIDO`, `E_IVA_CONTO_ACQ_ERR`,
`E_IVA_CONTO_VEN_ERR`, `E_LISTINO_TIPOLOGIA_UTILITY`, `E_NAZIONE_NON_TROVATA`,
`E_NOTE_TARGET_ID`, `E_PROFILO_ACCESSO_BINDING_INCOERENTE` (3 punti),
`E_QTA_MISSING`, `E_QTA_NON_POSITIVA` (3 trigger dei resi),
`E_QTA_OPERATIVA_NON_INTERA`, `E_QTA_OPER_STEP_INVALIDO`,
`E_RISORSA_UMANA_SOGGETTO_MISMATCH`, `E_SOGGETTO_NULL`, `E_SORG_KEY_MISSING`
(3), `E_STATO_DOC_ESITO_NON_VERDETTO`, `E_STATO_SORGENTE_PARAM_INVALIDO`, i
quattro `E_TEMPLATE_FLUSSO_*` di `trgfn_template_flussi_guard_modalita_esito`,
`E_TIPO_INDIRIZZO_NON_PERMESSO`, `E_UOM_MISSING`; più
`E_PREV_UTILITY_ISTANZA_INCOERENTE` (il sito DB, quello Python è del §3-ter).
Stessa domanda A/B del §3-ter, codice per codice: dove il guard ha la colonna
in mano (`'quantita'`, `'conto'`, `'forma_giuridica_id'`, `'tipo_indirizzo_id'`)
è `'campo'` da aggiungere al `jsonb_build_object`; dove è un parametro di
firma o un'invariante (`E_SOGGETTO_NULL`, `E_SORG_KEY_MISSING`, `E_COERENZA_ID`)
la promessa è sbagliata e l'override esce dal lato BE — basta dirlo.

Stessa famiglia di viste di C1
([brief-db-presidio-stati-mai-scritti.md](../work-done/brief-db-presidio-stati-mai-scritti.md),
**chiuso lato DB il 21-09**), stesso pgTAP trasversale con i casi **costruiti**
(context in variabile, colonna come chiave, codice in variabile, primo
motivo). ⚠️ La riga di `presidi.csv` (natura `CANCELLO`, `presidiato_da` = il
test §6 di questo brief) si scrive quando il test esiste, non prima.

✅ **La richiesta BE §6 di C1**, che il team DB aveva accodato qui, è chiusa
(§7): stessa forma, stessi strumenti — ma un giro prima, perché lì i
prerequisiti c'erano tutti.

---

## 5. Decisioni per Tid

1. **Il verso 2 si presidia o si dichiara?** Un codice `show_error_banner` che
   manda `fields` non fa danno a video (il campo si accende, il banner c'è):
   è una promessa che non decide, non una che mente. Proposta: si **misura** e
   si riporta, ma il cancello blocca solo sul verso 1. ✅ **Deciso da Tid il
   21-09: solo misurato.**
2. **`E_ATTIVITA_VALIDATION`** (§3): l'unico codice vivo con la promessa e
   nessun mittente. Si ritira a catalogo (`obsoleto_dal`, team DB) o si cerca
   il mittente che manca? Proposta: si ritira — un registro che nasce con un
   codice morto dentro è già un elenco di eccezioni. ✅ **Deciso da Tid il
   21-09: si ritira** — insieme a `E_ONERE_CAUSALE_NON_VALIDA` (decisione 7).
   ▶ **Richiesta al team DB**: `obsoleto_dal` sui due codici in
   `codici_errore.csv`; lato BE il marker di ONERE è già uscito, gli override
   restano (un codice ritirato deve continuare a risolvere per il diario).
3. **Dove vive**: `apps/core/tests/` accanto ai fratelli (decisione 2
   dell'analisi, mai presa). Proposta: lì, con `# Scopo:` che nomina questo
   brief — la «cartella dei presidi del percorso storto» non serve finché
   sono due. ✅ **Deciso da Tid il 21-09: `apps/core/tests/`.**
4. **La metà PL/pgSQL (§4): vista `dbops` o parsing di `dbzero`?** Proposta:
   la **vista**, per le ragioni del §4 — e allora il test attende il team DB,
   e nel frattempo nasce con la sola metà Python **dichiarata parziale** (un
   `skip` parlante sui codici a soli siti DB, non un verde). ✅ **Deciso da
   Tid il 21-09: la vista** — la richiesta al team DB è il §4.
5. **Come nasce il registro del verso 1, con 66 promesse vuote misurate.**
   Due strade: (a) *sanare prima* — il test arriva quando le 66 sono decise
   una per una, cioè fra settimane, e intanto il rubinetto resta aperto;
   (b) *nasce col debito* — come `test_naming_codice_interno_python`: un
   `_DEBITO` chiavato sul **codice**, che può solo calare, distinto dal
   registro delle **esenzioni** `(codice, verso) → ragione`, che nasce con la
   sola riga di `E_EMITTENTE_NON_RISOLTO`. Proposta: **(b)** — il rubinetto si
   chiude oggi sul 67º, e il debito è visibile nel posto dove cala. ✅ **Deciso
   da Tid il 21-09: (a), sanare prima** — il test nasce quando le 66 sono
   decise una per una. ⇒ Le 29 con siti Python sono la lista del **§3-ter**,
   con una proposta per codice; le 37 a soli siti DB sono del team DB (§4).
6. **I due difetti di meccanismo (§3-bis.4).** ✅ **Deciso da Tid il 21-09:
   si sana ora.** Lato Python **fatto**: i tre metodi di `PayloadValidator`
   che estraggono dal payload nominano `field`; i cinque che non lo fanno
   restano così per ragione, non per dimenticanza (§2.3). Lato DB: i guard con
   la colonna come chiave — non un changeSet ora, ma l'etichetta
   `CHIAVE_NON_LETTA` nella vista del §4, così la lista è del DB e cala dal
   suo lato.
7. **`E_ONERE_CAUSALE_NON_VALIDA`** (§3-bis.2): secondo codice vivo con la
   promessa e nessun mittente. Stessa domanda della decisione 2, e se la
   risposta è «ritiro», il marker in `_ONERE_DB_ERROR_MARKERS` esce con lui.
   ✅ **Deciso da Tid il 21-09: ritiro** — marker tolto (e il test che lo
   attendeva), `obsoleto_dal` chiesto al team DB con la decisione 2.

---

## 6. Cosa resta

* ✅ il criterio pieno (§2.3, corretto il 21-09), BB compresi, e la misura
  rifatta con quello (§3-bis) — fuori dal presidio, come misura datata;
* 🔵 le **sette decisioni** del §5 (le prime tre dal 19-09, le altre nate
  dalla misura);
* 🔵 **richiesta al team DB**: `obsoleto_dal` su `E_ATTIVITA_VALIDATION` e
  `E_ONERE_CAUSALE_NON_VALIDA` (decisioni 2 e 7, prese il 21-09); poi
  `genera_error_policies`;
* ✅ sanare `PayloadValidator` (decisione 6): tre metodi, tre test;
* ✅ **la tabella A/B del §3-ter** applicata (13 A, 16 B): lato Python zero
  promesse vuote; 🔵 i 37 lato DB nel §4;
* 🔵 la richiesta della vista al team DB (§4) — dopo la decisione 4;
* 🔵 il test in `apps/core/tests/test_ui_action_e_canale_campi.py` (sede
  decisa), **senza** `_DEBITO` (decisione 5: sanare prima) e col solo registro
  delle esenzioni `(codice, verso) → ragione`, nei due versi di ritiro — nasce
  quando la vista del §4 c'è e i 37 del DB sono sanati; il criterio Python
  deve conoscere anche `_CAMPO_PER_CODICE_DB` (§3-ter);
* 🔵 una riga in `api.md` §Envelope che nomini il presidio, e una in
  `dbops.presidi` (`CANCELLO`, quando la vista e il test esistono entrambi).

---

## 7. ✅ La richiesta BE §6 di C1 — chiusa il 2026-09-21

`apps/core/tests/test_stati_check_scrittori_python.py`, tre test, opt-in
`ZEROERP_TEST_DB_E2E=1` come il cancello del terzo lato: legge
`dbops.vw_stati_check_scrittori` sul DB provvisto (salta senza schema,
**fallisce** se lo schema c'è e la vista no), e sui `.py` non di test — senza
commenti né docstring — verifica le **26** righe `DICHIARATO_APPLICAZIONE`
(verso 1, il ritiro che il DB non può fare) e che nessuna `NON_DICHIARATO` sia
scritta da Python (verso 2, il verso permissivo). Verde: 26/26, 0 falsi
positivi sulle 14 `ESENTE`; fatto fallire togliendo il secondo salto (8 rosse)
prima di dichiararlo finito.

⭐ **Una cosa che la scrittura ha smentito del §6 di C1**: il criterio «letterale
e tabella **nello stesso file**» dava rosso su **8 righe su 26**, tutte della
stessa forma — il letterale nel *service* (`update_outbox_stato(id, "READY")`,
`severity="ERROR"`, `STATI_DOCUMENTO_INTERNO`), la tabella nel *repository*
(o in `famiglie.py`, o in un mixin). Non è un'eccezione: è l'architettura a tre
layer di `api.md`. Il test ammette quindi il **secondo salto** — file col
letterale che nomina un simbolo (`def`/`class`) definito **solo** in file che
nominano la tabella o uno scrittore DB — che è la forma di `scrittori_indiretti`
nella vista. Il vincolo «solo» non è pedanteria: senza, `get`/`post` legavano
tutto e accendevano 4 righe `ESENTE`; e le **docstring** vanno tolte come i
commenti, perché `commesse_source_handlers` nomina `attivita_consumi` in una
docstring e diventava «scrittore» di una tabella che non tocca. I limiti sono in
testa al file. 🔵 Al team DB resta una riga: `presidi.csv`, `presidiato_da` di
`vw_stati_check_da_sanare` → il nome del file, al posto di «richiesta §6 del
brief».
