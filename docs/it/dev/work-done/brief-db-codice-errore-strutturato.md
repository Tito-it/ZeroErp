# Brief DB — far arrivare il codice errore di dominio al backend

**Chi scrive:** backend (`dev/backend-tid`), 2026-08-05.
**Cosa chiede:** una riga in `script.fn_log_and_raise_error` — il codice errore
viaggia in un campo strutturato dell'eccezione invece di essere ripescato dal
testo.
**Origine:** [brief-be-bonifica-riferimenti-morti](../work-done/brief-be-bonifica-riferimenti-morti.md) §5,
che nasce da [brief-db-bonifica-riferimenti-morti](../work-done/brief-db-bonifica-riferimenti-morti.md).
**Perimetro:** **una** funzione DB + **un** metodo Python. Ma cambia il
comportamento di ogni errore dell'applicazione: va fatta come slice a sé.

> **Correzione al brief BE §5.** Quel paragrafo concludeva che il codice non
> arriva **mai** e che `error_policies.py` non scatta mai. Misurato sul percorso
> reale: **arriva nel 91% dei casi**, ma per un motivo che non è una difesa. Il
> difetto è più piccolo di come era scritto e più insidioso di come suonava:
> non è un guasto, è una dipendenza da qualcosa che nessuno ha progettato.

---

> ## ⚠️ Rilettura DB — 2026-08-05
>
> Le misure del brief sono state **ricontrollate sul DB vivo** e tornano tutte
> (dettagli nei paragrafi, dove le cifre differiscono di poco è il seed che è
> cresciuto). La proposta del §3 si accoglie **così com'è**. Cambiano tre cose:
>
> 1. **Il §8 è già stato fatto**, la notte prima che il brief arrivasse:
>    commit `b7d594244` (famiglia **F8**), mergiato con la PR #1164. Oggi nel DB
>    **non esiste più nessun call site a meno di 6 argomenti**. Gli item 4 e 5
>    del riepilogo sono chiusi — vedere il §8 riscritto, che spiega anche perché
>    i conteggi non coincidono (20-in-15 contro 16-in-12).
> 2. **Il §7 non è neutro come lo racconta**: per i 77 call site senza prefisso
>    `E_` l'adozione del campo lato BE porta un **400 di oggi a diventare un 500**.
>    Non blocca la slice DB, ma vincola l'ordine dei passi. §7 riscritto.
> 3. **Il §4.3 non è una valutazione da fare dopo**: i numeri la chiudono già.
>    Il fallback a regex resta. §4 aggiornato.
>
> Aggiunte alla slice, decise con Tid il 2026-08-05:
> **il presidio del contratto** (§10) e **la chiusura del rubinetto sui codici
> fuori convenzione** (§7).

---

> ## ✅ Stato: slice DB **CHIUSA, applicata e verde** — 2026-08-05
>
> Tutto ciò che in questo brief è marcato «DB» è fatto, applicato sul DB di
> sviluppo e verificato. Dettaglio nel §9; le prove nel §11.
>
> | Verifica | Esito |
> | --- | --- |
> | ChangeSet | `20260805-05` · `-06` · `-07` · `-08` — tutti `EXECUTED` |
> | pgTAP | **13/13 verdi** (5 nuovi sull'helper + 8 sulla guard ordini, di cui 1 nuovo) |
> | Guardrail nuovo | **verde**, exit 0 |
> | Baseline `script vendite` | **nessuna regressione** (48 rossi, tutti già noti) |
> | Guardrail riferimenti morti | **verde** dopo la modifica alla funzione |
>
> ✅ **Lato BE chiuso il 2026-08-05** nell'ordine indicato — prima i codici, poi
> la lettura. Dettaglio e scoperte nel **§12**: i codici da registrare erano
> **30 e non 57** (23 c'erano già, 4 sono usciti dal seed con `20260805-11`
> mentre il BE lavorava; trascriverli tutti creava chiavi duplicate che in Python
> vincono in silenzio), e i punti di innesto erano **4 e non 3** — il quarto è
> `pratiche_service`, dove il match avveniva su **frammenti di messaggio in
> italiano**. Test: 11 verdi, di cui 3 end-to-end su DB reale; suite intera 3574
> verdi.
>
> ✅ **I 5 status divergenti sono decisi** (Tid, 2026-08-05): quattro applicati
> (403/403/400/409), il quinto tenuto a 409. Il test non è stato aggiustato ma
> **riscritto**: asserisce lo status atteso per ogni codice — 14 codici, non 7
> con lo stesso numero (§12.1).
>
> 🔴 **Restano aperti, tutti fuori slice:**
>
> * ~~registro **53 → 51**: due voci sono doppioni senza prefisso di codici
>   vivi~~ — ✅ **fatto**, `20260805-16`. La motivazione per tenerle era un falso
>   positivo da ricerca per sottostringa (§7);
> * ~~il ritiro dei codici con log è bloccato dalla FK~~ — ✅ **risolto**:
>   `obsoleto_dal` (`20260805-17`) permette di ritirare un codice senza
>   cancellarlo, e il controllo **(D)** del guardrail impedisce che un codice
>   ritirato torni a girare. §15;
> * ⏳ **cantiere rinomina, aperto e in corso**: dei 57 codici fuori convenzione
>   iniziali ne restano **46**, in circa 35 funzioni. Non sono ritirabili così
>   come sono — **nessuno dei 46 è morto**, vanno prima rinominati a `E_*`, e il
>   ritiro è la coda di ogni rinomina. Il costo si conta **per funzione**: una
>   `CREATE OR REPLACE` ne libera fino a quattro (§15.8);
> * **133 codici `E_*`** sollevati dal DB non sono dichiarati in
>   `error_policies.py` (83 da trigger agganciate). Non è una regressione: manca
>   il **terzo lato** del presidio — codici sollevati dal DB vs
>   `error_policies.py`, l'unica direzione che nessuno guarda (§12.5).

---

## 1. Cosa serve al backend, e cosa riceve

Il backend deve sapere **quale** errore è, non cosa dice: da `error_policies.py`
(`codice → HTTP status → azione UI`, centinaia di voci) dipendono il 409 sul
duplicato, il 404 sul non trovato, il 403 sul vietato, e il messaggio che
l'operatore legge.

`script.fn_log_and_raise_error` chiude così:

```sql
RAISE EXCEPTION '%', v_msg
    USING DETAIL = coalesce(v_detail, ''),
          HINT   = coalesce(v_hint, '');
```

Partono tre cose: il messaggio localizzato, `causa` (in `DETAIL`), `soluzione`
(in `HINT`). **Il codice non è in nessuna delle tre.** Misurato:

| Misura | Valore |
|---|---|
| Messaggi `it` che contengono il proprio codice | **0 su 635** |
| `causa` / `soluzione` che lo contengono | **0** |
| SQLSTATE | sempre `P0001` (default di `RAISE EXCEPTION`) |

Lato Python, `ErrorTranslator._extract_app_error_code` lo cerca con una regex
(`\bE_[A-Z][A-Z0-9_]+\b`) nel **testo intero** dell'eccezione, e il commento
dice: *«`fn_log_and_raise_error` include il codice nel RAISE EXCEPTION via
`fn_get_messaggio`»*. Non è vero: `fn_get_messaggio` mette il codice nel testo
**solo nel fallback**, cioè quando la riga manca dal seed.

---

## 2. Perché oggi funziona lo stesso, e perché non basta

Il driver, nel testo dell'eccezione, allega anche **lo statement chiamante**. E
lì il codice c'è, scritto a mano:

```
QUERY: SELECT script.fn_log_and_raise_error(
         'documenti', 'trgfn_template_asset_block_delete',
         'E_DOCUMENTI_ASSET_DELETE_BLOCKED',      <-- la regex trova QUESTO
         jsonb_build_object(...), NULL::uuid)
CONTEXT: funzione PL/pgSQL documenti.trgfn_template_asset_block_delete() riga 14 a PERFORM
```

Il backend sta leggendo il codice dal **sorgente della chiamata**, non dal dato.
Censimento dei **971** call site nei corpi vivi:

| | Call site | Cosa succede |
|---|---:|---|
| **A** | **886** | codice letterale `E_*` → la regex lo trova (per fortuna, non per progetto) |
| **B** | **76** | codice letterale **senza prefisso `E_`** → la regex non lo riconosce |
| **C** | **9** | codice da espressione → nel testo c'è il **nome della variabile** |

> **Ricensimento DB del 2026-08-05:** **978** call site — A **886** (identico),
> B **77**, C **9** (identico). Le differenze sono di conteggio, non di
> sostanza: il quadro regge intero. ⚠️ Attenzione se lo si rifà: contare gli
> argomenti significa spezzare sulle virgole di primo livello, e un apostrofo
> dentro un commento SQL (`-- la funzione e' VARIADIC`) apre una stringa che non
> si chiude più. Vanno tolti i commenti **prima** di contare — vedi §8.

**Il gruppo C è il danno vivo.** Sono le guard di cambio stato, cioè gli errori
che l'operatore incontra ogni giorno:

```sql
PERFORM script.fn_log_and_raise_error(..., v_motivi -> 0 ->> 'codice', ...)
```

`vendite.trgfn_ordini_guard_transizione` · `trgfn_commesse_guard_transizione` ·
`trgfn_preventivi_guard_annullamento` · `fn_cambia_stato_preventivo` ·
`fn_riporta_lotto_a_draft` · `fn_annulla_lotto_da_draft` ·
`fn_elimina_fattura_da_lotto` · `fn_riapri_riconsegna_reso` ·
`script.trgfn_lock_columns` (`msgcode`).

Per tutte e nove il translator ripiega su `E_DATABASE`, che è classificato
**tecnico**: il messaggio localizzato viene **scartato** e sostituito da un testo
generico, e il dettaglio è soppresso (*«Dettaglio tecnico non esposto»*). Chi
tenta una transizione non ammessa non legge perché non è ammessa.

> **Verifica DB (2026-08-05) — il gruppo C guadagna davvero.** Non era scontato:
> quei codici non si vedono nel sorgente, quindi andava controllato *da dove
> vengono*. Escono tutti dai `script.fn_check_*_annullabile`, la stessa funzione
> pura che accende il bottone in `fn_available_actions_*`, e sono **tutti `E_*`**:
> `E_ORD_ANNULLA_CON_DDT`, `E_ORD_ANNULLA_IN_COMMESSA`,
> `E_PREV_GIA_IN_COMMESSA`, `E_PREV_ANNULLA_COMMESSA_EMESSA`,
> `E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE`, `E_LOTTO_FATTURE_NUMERATE`,
> `E_FATTURA_GIA_NUMERATA`, `E_RESO_NOT_FOUND`…
> Quindi il gruppo C **non** ricade nel secondo muro del §7: il campo strutturato
> lo porta fino in fondo, dal DB al banner che l'operatore legge. È questa la
> giustificazione economica della slice.

⚠️ **Il gruppo A è la parte che preoccupa di più**, proprio perché funziona: se
domani una di quelle 886 chiamate passa il codice per variabile — che è
esattamente ciò che è successo alle nove del gruppo C, una alla volta — smette di
funzionare **in silenzio**, senza che nulla fallisca a DB né in CI.

**E la stessa pesca nel testo è scritta in tre posti diversi**, ognuno col suo
modo: `ErrorTranslator._extract_app_error_code`, `payload_helpers.DB_ERROR_CODE_RE`
(dentro `translate_db_errors`), `ErrorManager.raise_from_database_error`
(substring match sui `known_markers` del chiamante). Il campo strutturato le
riduce a una lettura sola.

---

## 3. La forma proposta

Il codice viaggia in un campo dedicato dell'eccezione. `RAISE ... USING` ne
espone cinque oltre a `DETAIL`/`HINT`; **`CONSTRAINT` è il meno improprio**: il
codice errore *è* il nome della regola violata.

```sql
    -- 5) Sollevamento eccezione con DETAIL/HINT localizzati.
    --    CONSTRAINT porta il CODICE di dominio: e' l'unico campo strutturato
    --    che il backend puo' leggere senza fare parsing del testo. Il codice
    --    NON compare nel messaggio (per scelta: il messaggio e' per l'utente).
    RAISE EXCEPTION '%', v_msg
        USING ERRCODE    = 'P0001',
              DETAIL     = coalesce(v_detail, ''),
              HINT       = coalesce(v_hint, ''),
              CONSTRAINT = p_error_code;
```

`ERRCODE = 'P0001'` è già il default: renderlo esplicito serve a dire che il
contratto è *«P0001 + `CONSTRAINT` valorizzato = errore di dominio»*, che è la
condizione che il backend userà per fidarsi del campo (§5).

### Verificato davvero, non dedotto

Round-trip DB → libpq → psycopg3 → `django.db.DatabaseError` provato su questo
DB (PostgreSQL 18.4). Arrivano **tutti** i campi: `schema_name`, `table_name`,
`column_name`, `datatype_name`, `constraint_name`. E `constraint_name`
sopravvive anche:

* **annidato** in più livelli PL/pgSQL (è il caso normale: trigger → guard → helper);
* attraverso un blocco `EXCEPTION ... RAISE;` che **ri-solleva**.

### Le alternative, e perché no

| Strada | Perché no |
|---|---|
| SQLSTATE custom (classe `U0`) | pulita, ma SQLSTATE è di 5 caratteri: servirebbe una mappa `codice → sqlstate` da mantenere allineata al seed. Un secondo posto da tenere in bolla, cioè il difetto da cui nasce tutto |
| Prefisso convenzionale nel messaggio | sporca il testo che l'operatore legge, e resta parsing |
| `COLUMN` | funziona identico, ma dice una cosa falsa: non è una colonna |
| `DETAIL` in JSON | `DETAIL` è già occupato da `causa`, che è per l'utente |

---

## 4. Compatibilità: nessuna regressione, e migrazione in due tempi

**Il campo non cambia `str(exc)`.** Verificato: con `CONSTRAINT` valorizzato il
testo dell'eccezione resta

```
Username gia' in uso.
DETAIL:  causa
HINT:    soluzione
CONTEXT: funzione PL/pgSQL ...
```

e il codice **non** vi compare. Conseguenza pratica: i tre parser di testo che
esistono oggi continuano a comportarsi **esattamente** come prima. Quindi:

1. **Il DB può andare per primo, da solo.** Applicare il changeSet senza toccare
   il backend non cambia niente per nessuno: nuovo campo ignorato, comportamento
   invariato. Nessuna finestra di rottura, nessuna fase di compatibilità.
2. Il backend adotta il campo subito dopo, con la lettura difensiva del §5.
3. ~~Solo quando i pgTAP e i test Django del §6 sono verdi si valuta se togliere
   il fallback a regex.~~ **Il fallback a regex resta, e non è una valutazione da
   rimandare: la misura la chiude già.** Nel DB vivo ci sono **135
   `RAISE EXCEPTION` diretti in 46 funzioni PL/pgSQL** che non passano da
   `fn_log_and_raise_error`. Per quelle il campo esce vuoto e la regex è l'unica
   strada. Il numero va scritto qui perché una porta lasciata socchiusa, fra un
   anno, diventa un ticket «rimuovere il fallback legacy» aperto da chi la misura
   non ce l'ha.
   La regex si potrà togliere il giorno in cui quei 135 saranno zero — che è un
   cantiere a sé, non la coda di questo.

---

## 5. Cosa fa il backend (per completezza — lo scriviamo noi)

In `ErrorTranslator._from_database_error`, prima della regex:

```python
        # Codice di dominio dal campo strutturato: e' valido SOLO su P0001.
        # Su una violazione di vincolo vera (classe 23xxx) `constraint_name`
        # contiene il nome del vincolo DB (`uq_...`, `fk_...`): prenderlo per
        # un codice applicativo produrrebbe un codice inesistente, quindi la
        # policy di fallback e un 500 al posto di un 409 parlante.
        app_code = None
        if sqlstate == "P0001":
            app_code = getattr(diag, "constraint_name", None) or None
        if app_code is None:
            app_code = ErrorTranslator._extract_app_error_code(raw_message)
```

⚠️ **Il guard su `sqlstate == 'P0001'` non è prudenza, è necessario.** Senza,
ogni `IntegrityError` porterebbe il nome del vincolo dentro `code`, e
`map_integrity_error` — che oggi traduce quei vincoli in codici di dominio
leggendo `str(exc)` — si troverebbe scavalcato a monte.

Stesso innesto, con la stessa condizione, in `translate_db_errors` e
`ErrorManager.raise_from_database_error`.

---

## 6. Test richiesti

Il giro va asserito **intero**, altrimenti resta un altro presidio che si può
dimenticare di lanciare:

* **pgTAP** su `script.fn_log_and_raise_error`: che il campo `CONSTRAINT` esca
  valorizzato col codice passato, e che `DETAIL`/`HINT` restino `causa`/`soluzione`.
  Da fare su un codice **presente a seed** — un codice mancante fa scattare il
  placeholder di `fn_get_messaggio` e il test passerebbe per il motivo sbagliato
  (è lo stesso inganno di `test-fn-crea-auth-user`, brief BE §4).
* **pgTAP** su almeno **una** delle nove guard del gruppo C — dove il codice
  arriva da `v_motivi` — perché è lì che il vecchio meccanismo non arrivava.
* **test Django** end-to-end: eccezione DB reale → `ApiError.code` giusto →
  HTTP status giusto dalla policy. Non un mock: il mock non vede né i campi diag
  né il testo del driver, che è precisamente ciò che stiamo cambiando.

> **Stato.** I due pgTAP sono **fatti e verdi** (§11): 5 asserzioni sull'helper e
> il test 8 su `vendite.trgfn_ordini_guard_transizione`, che è la guard del
> gruppo C scelta perché la sua fixture esisteva già.
> Ne è stato aggiunto uno che il brief non chiedeva e che vale la pena tenere: il
> **contratto negativo**, cioè che il codice **non** compaia nel messaggio. Senza,
> fra sei mesi qualcuno lo rimette nel testo «per farlo trovare più facilmente» e
> la scelta si perde senza che nulla diventi rosso — che è il modo in cui le
> decisioni di progetto muoiono.
>
> 🔴 Il **test Django** resta al BE, ed è l'unico dei tre che qui non si poteva
> scrivere.

---

## 7. I codici senza prefisso (gruppo B) — ⚠️ non è neutro, e la decisione è presa

**Non è in questa slice**, ma va deciso *prima* che il BE adotti il campo: il
campo strutturato risolve A e C, **non risolve B**. Lì il problema non è il
trasporto, è il **nome**.

Nel DB ci sono **57 codici distinti** (su 636) che non seguono la convenzione
`E_{MODULO}_{TIPO}` di `docs/it/dev/api.md`: `PRATICHE_TRANSIZIONE_NON_AMMESSA`,
`PREV_TRANSIZIONE_NON_AMMESSA`, `DEFINIZIONE_*`, `FLUSSI_*`, `TEMPLATE_FLUSSO_*`,
`ERRORE_PARAMETRI` (13 call site), `SEQUENZA_NON_CONFIGURATA`,
`CODICE_NON_MODIFICABILE`, `CF_NON_VALIDO`, `PIVA_NON_VALIDA`… — **76 call site**.
Sono tutti regolarmente a seed in `config.messaggi_errore`.

Col campo strutturato quei codici **arriveranno** al backend. Ma lì incontrano un
secondo muro, tutto lato BE: non sono registrati in `error_policies.py`, e
`ErrorPolicyRegistry.resolve` ha una scorciatoia esplicita solo per i codici che
cominciano per `E_` (→ 400 «errore di validazione»). Tutti gli altri cadono su
`E_GENERICO` → **HTTP 500**. Cioè: un operatore che tenta una transizione di
pratica non ammessa fa apparire al frontend un errore di server.

### ⚠️ Correzione: non è «rotti uguale», è un 400 che diventa un 500

Il brief concludeva *«dopo il campo strutturato sono rotti uguale — nessun
peggioramento»*. Letto [`error_policies.py`](../../../../backend/apps/core/services/error_policies.py),
non è così:

Oggi la regex non trova quei codici e il translator ripiega su `E_DATABASE`, che
è registrato → **400** con messaggio generico. Domani il codice **arriva**, e da
lì in poi dipende da una cosa sola: se è registrato o no.

> ⚠️ **Correzione alla correzione.** Il brief BE dice che quei codici «non sono
> registrati in `error_policies.py`». **Non è vero per tutti: 23 su 57 lo sono
> già.** Le chiavi vere di `_POLICIES` sono 430, e fra queste ci sono
> `PRATICHE_TRANSIZIONE_NON_AMMESSA`, `FLUSSI_TRANSIZIONE_NON_AMMESSA`, tutta la
> famiglia `DEFINIZIONE_*`. Qualcuno le ha registrate col nome storto, e ha fatto
> la cosa giusta.

Il gruppo B si spacca in due metà con destini **opposti**:

| | Codici | Call site | Oggi | Dopo l'adozione BE |
|---|---:|---:|---|---|
| **Già registrati** | **23** | **29** | `E_DATABASE` → 400 generico | ✅ la **loro** policy: status e messaggio giusti. **Migliorano il giorno stesso** |
| **Non registrati** | **30** | **48** (in 26 funzioni) | `E_DATABASE` → 400 generico | 🔴 `resolve()` ha la scorciatoia solo per `E_` → `E_GENERICO` → **500** |

Da 400 a 500 non è una sfumatura: cambia gli allarmi, cambia cosa finisce nei
log di errore server, e cambia cosa fa il frontend. **Quindi la registrazione non
è un «poi si decide»: è un prerequisito di sequenza del passo 3.** La slice DB
resta invece sicura da sola, perché finché il BE non legge il campo non cambia
niente (§4).

### Decisione (Tid, 2026-08-05): registrare **e** chiudere il rubinetto

Nessuna delle due strade presa da sola. Rinominare i 57 costa il seed + 77 call
site + i pgTAP che li asseriscono, e non compra nulla che la registrazione non
compri; ma registrare e basta lascia in piedi l'obiezione giusta del brief — *il
prossimo codice nascerà di nuovo storto*. Quindi tutte e due le metà:

| | Cosa | Chi |
|---|---|---|
| **Registrare** i 57 così come sono | 57 voci in `error_policies.py`, **prima o insieme** all'adozione del campo | BE |
| **Chiudere il rubinetto** | presidio CI: un codice **nuovo** fuori convenzione fa fallire la CI. I 57 esistenti vivono in un registro del debito che deve calare | DB — §10 |

Così i 57 diventano un debito **numerato e visibile** invece di una convenzione
disattesa in silenzio, e il 58° non nasce.

> ✅ **Trovato mentre si costruiva il presidio, e già tolto** (`20260805-08`).
> In `config.messaggi_errore` c'era una riga con un **apostrofo in coda al
> codice**: `E_NOTE_RIGA_MISMATCH'` (id 76), che nessun call site può nominare —
> il codice vero (id 792) esiste accanto, aggiunto da un seed successivo. Riga
> morta, e veniva dal CSV (`80_data/sql/config/messaggi_errore.csv` riga 88),
> quindi il DELETE da solo non sarebbe bastato: il loader è `runOnChange` e la
> rimetterebbe. Tolta **in due mosse**, riga dal CSV *e* changeSet di DELETE.
> Verificato: 0 residui.
>
> Piccolo dividendo del presidio: il controllo (B) è diventato rosso la prima
> volta che ha girato, e su una cosa vera.

> ✅ **Il registro è sceso a 53** (`20260805-11`). Incrociando i 57 codici coi
> call site veri, **otto** non sono sollevati da nessuna funzione: due sono
> **solo loggati** e non arriveranno mai a un client (`MESSAGGIO_NON_DEFINITO`,
> `W_TXID_NOT_REGISTERED`), due sono i doppioni senza prefisso di codici vivi
> (vedi il rilievo BE qui sotto), **quattro non hanno consumatori da nessuna
> parte** — né DB, né Python, né FE — e sono usciti dal seed.
>
> ⚠️ Prima di cancellarli è servita la distinzione che conta: **superati** o
> **non ancora agganciati**? Un codice a seed senza chiamanti può essere un
> residuo o un pezzo della slice di qualcun altro che il call site non ha ancora
> raggiunto. Per tutti e quattro l'ha detto il DB stesso:
>
> | Codice | id | Prova |
> |---|---:|---|
> | `PREV_TOTALE_NON_POSITIVO` | 353 | il corpo vivo di `fn_cambia_stato_preventivo`: *«rev 2026-07-16: rimossi il guard PREV_TOTALE_NON_POSITIVO e il filtro quantita > 0»* |
> | `PREV_ANNULLAMENTO_COMMESSA_ATTIVA` | 356 | stesso corpo, nota di `20260804-74`: *«con l'assorbimento esce di scena anche il codice …, privo del prefisso `E_`»*. Rimpiazzato da `E_PREV_ANNULLA_COMMESSA_EMESSA` |
> | `PRATICHE_ISTANZA_SENZA_RUOLO` | 304 | `trgfn_pratiche_guard_contesto` oggi solleva `..._ISTANZA_SENZA_SOGGETTO` e `..._RUOLO_SENZA_SOGGETTO`: la variante «senza ruolo» non c'è più |
> | `CATASTO_SOURCE_NOT_FOUND` | 115 | `fn_clone_catasto_from_parent_by_istanza` oggi solleva `ERRORE_PARAMETRI` |
>
> ⚠️ **Controllo che avrebbe fatto fallire il migrate se saltato:**
> `dbops.error_log` ha una FK verso `config.messaggi_errore(id)`. Verificato
> **0 riferimenti** per tutte e quattro; con anche uno solo il `DELETE` sarebbe
> morto sulla FK.
>
> Due mosse per il catalogo (righe dal CSV **+** `DELETE`, perché il loader è un
> upsert), **una sola per il registro**: il suo seed è `DELETE` + `loadData`,
> cioè un mirror — bastano le righe tolte dal CSV. È esattamente il motivo per
> cui era stato scritto come mirror invece che come upsert.
>
> Simulazione dello stato post-migrate in transazione annullata: guardrail verde,
> *«nessuna voce di troppo nel registro (53 registrate)»*.

> 🔴 **Rilievo BE (2026-08-05): il registro può scendere ancora, a 51.** La
> motivazione per tenere `EMITTENTE_NON_MODIFICABILE` e
> `PREV_STATO_NON_MODIFICABILE` — *«due li usa il backend»* — non regge: il
> backend usa `E_EMITTENTE_NON_MODIFICABILE` e `E_PREV_STATO_NON_MODIFICABILE`,
> che sono **altri due codici**, entrambi a catalogo accanto ai loro gemelli
> senza prefisso. La ricerca per sottostringa trova il codice lungo quando cerchi
> quello corto — ed è la stessa forma di errore di cui parla tutto questo brief.
>
> Ri-misurato con i confini di parola (`(?<![A-Z_])CODICE\b`): per le due varianti
> **senza** prefisso, **zero consumatori** in funzioni DB, in `backend/apps` e in
> `frontend/src`. Sono doppioni superati esattamente come i quattro sopra, e la
> prova è che il gemello con prefisso è vivo e usato.
>
> Azione **al team DB** (non fatta qui: è seed): togliere i due dai due CSV +
> `DELETE`, registro **53 → 51**. Lato BE non cambia nulla — le policy dei due
> codici con prefisso sono già registrate e sono quelle che scattano.

---

## 8. ✅ Allegato `FP_VARIADIC` — **CHIUSO prima di arrivare** (commit `b7d594244`)

> **Non rifare niente di questo paragrafo.** La segnalazione è arrivata al DB per
> altra via ed è stata sanata la notte fra il 4 e il 5 agosto, poche ore prima
> che il brief fosse scritto: commit **`b7d594244` — «Bonifica riferimenti morti
> — F8: chiamate senza valori variadici»**, mergiato con la PR #1164.
> Ricensito il 2026-08-05 sui corpi vivi: **978 call site, arità minima 6**.
> Nessun residuo.
>
> ⚠️ Eseguirlo oggi significherebbe rifare ~16 `CREATE OR REPLACE` su corpi che
> nel frattempo sono cambiati: è il modo esatto di regredire in silenzio contro
> cui mette in guardia la regola *«il DDL dalla doc auto-gen, mai dagli YAML»*.
>
> **Perché i conteggi non coincidono** (brief: 20 call site in 15 funzioni; F8:
> 16 in 12). Nessuno dei due ha sbagliato a guardare: sono falsi positivi di
> *parsing*. Contare gli argomenti di una chiamata vuol dire spezzare sulle
> virgole di primo livello, e un apostrofo dentro un commento SQL — `-- la
> funzione e' VARIADIC` — apre una stringa che non si chiude mai, inghiottendo
> le virgole successive. Ci è cascata anche la ri-verifica di oggi: al primo giro
> dava 2 residui, spariti togliendo i commenti *prima* di contare.
> Piccola morale coerente col resto del brief: **anche la misura di un difetto è
> un programma, e può avere il suo difetto.**
>
> **Cosa è stato fatto**, oltre ai call site:
>
> * i codici mancanti aggiunti (`E_ATTIVO_BLOCK_REF_NULL`, id 840) e il valore
>   del segnaposto corretto dove parlava d'altro;
> * la regola del presidio corretta da `20260805-01`, ma **più stretta** di come
>   la chiedeva il §9 item 5: non «esenzione solo con ≥1 valore variadico», bensì
>   `provariadic = '"any"'::regtype`, cioè la condizione a monte. Nessuna nostra
>   funzione è `VARIADIC "any"`, quindi la classe resta **strutturalmente vuota**
>   invece di svuotarsi caso per caso;
> * il punto che questo paragrafo dà per scontato — *«il rimedio è il 6°
>   argomento oppure `VARIADIC ARRAY[]::text[]`»* — era già stato affrontato: il
>   rimedio **non è uniforme**, dipende dai `%s` del template a seed (11 codici su
>   12 non ne avevano, per il dodicesimo serviva un valore). Con un segnaposto e
>   l'array vuoto il `format` viene saltato e all'operatore arriva un `%s`
>   letterale: un difetto silenzioso al posto di uno rumoroso.
>
> ✏️ *Nota lessicale, perché non si ripeta:* il 6° argomento **non è «il
> messaggio»**. È un **valore** che riempie un `%s` del template in
> `config.messaggi_errore`. Detto come lo dice il paragrafo qui sotto, invita a
> passarci dentro il testo del messaggio.

Quello che segue resta come **storia della diagnosi** — è ancora la spiegazione
più chiara del perché il difetto esisteva.

La regola v3 del classificatore (`brief-db-bonifica-riferimenti-morti` §3.1)
esenta i 42883 su `fn_log_and_raise_error` se la funzione chiamata *ha* un
parametro `VARIADIC`. Manca un pezzo: in PostgreSQL una funzione
`VARIADIC <tipo>[]` **non può essere chiamata con zero argomenti variadici**.
Solo `VARIADIC "any"` lo permette — per questo `format('x')` funziona:

```
=> select script.fn_log_and_raise_error('t'::text,'p'::text,'E_X'::text,NULL::jsonb,NULL::uuid);
ERRORE: la funzione script.fn_log_and_raise_error(text, text, text, jsonb, uuid) non esiste
=> select script.fn_log_and_raise_error('t'::text,'p'::text,'E_X'::text,NULL::jsonb,NULL::uuid,
                                        VARIADIC ARRAY[]::text[]);
ERRORE: Username gia' in uso.      <- questa risolve
```

Vale identico in PL/pgSQL. Quindi le righe etichettate `FP_VARIADIC` **non sono
rumore**: sono difetti veri, della stessa natura della famiglia F3 già corretta.
Censimento sui corpi vivi: **20 call site a 5 argomenti in 15 funzioni**.

| Funzione | Siti | Trigger |
|---|---:|---|
| `documenti.trgfn_documenti_generati_check_coerenza` | 4 | `documenti_generati` |
| `documenti.trgfn_template_documenti_versioni_block_delete` | 2 | `template_documenti_versioni` |
| `documenti.trgfn_documenti_generati_block_delete` · `_protect_snapshot` · `_eventi_block_delete` · `_eventi_block_update` · `_file_protect_file` · `trgfn_template_asset_block_delete` · `_protect_file` · `trgfn_template_documenti_versioni_protect_pubblicata` | 1 cad. | agganciate |
| `anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo` | 1 | `indirizzi` |
| `dbops.trgfn_prevent_deactivate_if_children` → `fn_log_error_only` | 1 | **343 tabelle** |
| `pratiche.fn_guard_prerequisiti_flusso` · `fn_guard_ripetibilita_flusso` · `script.fn_change_user_emittenti_scope` | 4 | non-trigger |

Prova live (transazione annullata, riga intatta):

```
BEGIN; DELETE FROM documenti.template_asset WHERE id = (SELECT min(id) ...);
ERRORE: la funzione script.fn_log_and_raise_error(unknown,unknown,unknown,jsonb,uuid) non esiste
CONTESTO: funzione PL/pgSQL documenti.trgfn_template_asset_block_delete() riga 14 a PERFORM
ROLLBACK;
```

Cosa costa davvero:

* il codice di dominio non arriva mai (SQLSTATE `42883`, non `P0001`): il backend
  traduce in `E_DATABASE` → 400 generico, dettaglio soppresso. **Il campo
  strutturato di questo brief non li salva**: la funzione non viene nemmeno
  raggiunta;
* `fn_log_error_only` non gira → **nessuna riga di log** per errori che dovevano
  essere tracciati;
* il caso `dbops.trgfn_prevent_deactivate_if_children` è il peggiore per natura:
  lì il contratto è *«logga senza sollevare»*. Un call site a 5 argomenti
  **solleva**, e fa fallire una disattivazione legittima. Ramo stretto (si prende
  quando la `ref_col` esplicita è NULL sul record OLD), ma è armato su 343 tabelle.

**Rimedio ai call site**: il 6° argomento (il messaggio, come fanno gli altri
962) oppure `VARIADIC ARRAY[]::text[]`.
**Rimedio al presidio**, che è il punto se non si vuole tornare qui: nella regola
`FP_VARIADIC` l'esenzione deve valere solo se il call site passa **almeno un**
valore variadico. `provariadic <> 0` da solo non basta.

Nota di metodo: è lo stesso modo di fallire del §3.3 del vostro brief — *«il
check è un setaccio, non una lista»*. Qui però il difetto non era nascosto sotto
un altro difetto: era nascosto **sotto un'etichetta**, come
`test-fn-search-stradario` sotto `ERRORE_FIXTURE`.

---

## 9. Riepilogo

| # | Cosa | Chi | Stato |
|---|---|---|---|
| 1 | `CONSTRAINT = p_error_code` in `fn_log_and_raise_error` (`runOnChange: false` — nel progetto `true` è solo crutch locale) | DB | ✅ **fatto** — `20260805-05` |
| 2 | pgTAP §6: campo valorizzato su codice a seed + una guard del gruppo C + il **contratto negativo** | DB | ✅ **fatto** — 13/13 verdi (§11) |
| 3 | Lettura del campo con guard `sqlstate = 'P0001'` nei 3 punti + test Django | BE | ✅ **fatto** — 4 punti, non 3 (§12) |
| 4 | ~~20 call site variadici a 5 argomenti~~ | DB | ✅ **fatto** — `b7d594244` (§8) |
| 5 | ~~Regola `FP_VARIADIC`~~ | DB | ✅ **fatto** — `20260805-01`, più stretta del richiesto (§8) |
| 6 | Registrare i codici senza prefisso **e senza policy** in `error_policies.py` | BE | ✅ **fatto** — **30** (dei 53 rimasti, 23 c'erano già) (§12.1) |
| 7 | Presidio del contratto + rubinetto sui codici nuovi + registro del debito | DB | ✅ **fatto** — `20260805-06/-07` + guardrail (§10) |
| 8 | Riga morta `E_NOTE_RIGA_MISMATCH'` (CSV riga 88 + DELETE) | DB | ✅ **fatto** — `20260805-08` (§7) |
| 9 | 4 codici superati fuori dal seed: registro **57 → 53** | DB | ✅ **fatto** — `20260805-11` (§7) |
| 10 | 5 status storici incoerenti con la semantica: decidere e allineare | Tid + BE | ✅ **fatto** — 4 applicati, 1 tenuto; test riscritto (§12.1) |
| 11 | 2 doppioni senza prefisso di codici vivi: registro **53 → 51** | DB | ✅ **fatto** — `20260805-16` (§7) |
| 12 | Terzo lato del presidio: codici sollevati dal DB vs `error_policies.py` | da decidere | 🔴 **aperto** — 133 non dichiarati, misura pronta (§12.5) |
| 13 | `obsoleto_dal`: ritirare un codice **con log** senza cancellarlo — sblocca 46 casi su 53 | DB | ✅ **fatto** — `20260805-17` + guardrail (D) + pgTAP 4/4 (§15) |
| 14 | Cantiere rinomina — **1° lotto**: `trgfn_template_flussi_guard_modalita_esito`, 4 codici | DB | ✅ **fatto** — `20260805-19`, registro **50 → 46**, baseline `pratiche` invariata (§15.8) |
| 15 | Cantiere rinomina — **2° lotto**: `trgfn_pratiche_guard_contesto`, 4 codici | DB | ✅ **fatto** — `20260805-20`, registro **46 → 42**, baseline `pratiche` verde (§15.9) |
| 16 | Cantiere rinomina — **3° lotto**: `fn_crea_revisione_preventivo` (+1 letterale in `fn_cambia_stato_preventivo`), 3 codici | DB | ✅ **fatto** — `20260805-25`, registro **42 → 39**, baseline `vendite` verde (§15.12) |
| 17 | Cantiere rinomina — **lotti 4..n**: dei **39** rimasti, **27 accoppiati al BE** (23 in un solo file) e 12 DB-only | DB | ⏳ **aperto, ma DB-only**: il coordinamento col BE non serve più — entrambi i nomi sono dichiarati per tutti e 51 (39 vivi + 12 già ritirati), quindi i lotti si aprono senza avvisare e senza sincronia. Brief chiuso in [work-done](../work-done/brief-be-rinomina-codici-known-markers.md) §7 |
| 18 | Cantiere rinomina — **pulizia finale BE**: togliere le voci vecchie da `known_markers` e `error_policies.py` | BE | ⏳ **aperto, senza fretta** — a registro vuoto. Una voce di troppo non fa danno; va tolta anche l'asserzione «almeno un legacy» del test (work-done §7.4) |
| 19 | Cantiere rinomina — **tutti i DB-only in un lotto**: 11 codici, 14 funzioni | DB | ✅ **fatto** — `20260805-26`, registro **39 → 28**, baseline verde (§15.14) |
| 20 | `W_` = warning: convenzione allargata a `^[EW]_` + controllo **(E)** «un warning non si solleva mai» | DB | ✅ **fatto** — `20260805-28`, registro **28 → 27** (§15.15) |
| 21 | Cantiere rinomina — **ultimo lotto**: 26 codici, 28 funzioni. Registro **27 → 1** | DB | ⏳ **da applicare** — `20260805-29` (§15.17) |
| 22 | `E_TEMPLATE_CODICE_DUPLICATO` seedato (rilievo BE) | DB | ⏳ **da applicare** — id 864 (§15.18) |
| 23 | `MESSAGGIO_NON_DEFINITO`: unica voce residua — rinominare `W_*` via provision, o lasciarla | decisione Tid | 🔴 **aperto** (§15.17) |

**Ordine obbligato:** ~~1 → 2 → 7~~ (DB, applicato da solo, nessuna finestra di
rottura) · ~~6 → 3~~ (BE, in quest'ordine e non nell'altro: invertirli portava
77 call site da 400 a 500). **Entrambe le catene sono chiuse.** Restano 11 e 12,
che non hanno vincoli di sequenza fra loro né con il resto.

### Cosa trova il BE già pronto

| | |
| --- | --- |
| Il campo | `diag.constraint_name` su `SQLSTATE = 'P0001'`, applicato e asserito |
| ⚠️ Campo vuoto ≠ NULL | quando il codice viene da un'espressione che vale NULL, arriva **stringa vuota**: `... or None` non è cosmetico |
| ⚠️ Il ripiego resta | 135 `RAISE EXCEPTION` diretti in 46 funzioni non passano dall'helper: per quelle il campo è vuoto e la regex è ancora l'unica strada |
| I codici da registrare | elenco vivo: `SELECT codice FROM dbops.messaggi_errore_codici_legacy ORDER BY 1` — **53 righe, e 23 hanno già la policy**: da fare sono le **30** che non compaiono fra le chiavi di `_POLICIES` |
| ⚠️ Chiave duplicata = sovrascrittura muta | in un dict literal Python l'ultima vince **senza errore né warning**, e nel progetto non ci sono `ruff`/`flake8` che lo intercettino. Registrare un codice già presente **sostituisce** la policy esistente: le 23 vecchie voci vanno **rimosse esplicitamente**, non coperte |

---

## 10. Il presidio del contratto (aggiunta DB, 2026-08-05)

Il §3 dichiara un contratto — *«`P0001` + `CONSTRAINT` valorizzato = errore di
dominio»* — ma finché resta un commento, è una convenzione. Nulla impedisce a un
futuro `RAISE EXCEPTION ... USING CONSTRAINT = 'qualcosa'` scritto a mano di
usare lo stesso canale per altro, e il BE si fiderebbe. Con **135 `RAISE`
diretti** già in circolazione (§4) la probabilità non è teorica.

Nuovo `scripts/sql/guardrail_codice_errore_strutturato.sql`, stessa forma dei due
guardrail già in CI (`check_naming_stato_codice`, `guardrail_riferimenti_morti`):
un `DO` che solleva, e con `ON_ERROR_STOP=1` il passo diventa rosso.

| | Controllo | Perché |
|---|---|---|
| **A** | `RAISE ... USING ... CONSTRAINT =` fuori da `script.fn_log_and_raise_error` | il canale ha **un solo** mittente autorizzato, altrimenti il guard `P0001` del §5 si fida di un campo che qualcun altro ha scritto |
| **B** | un codice di `config.messaggi_errore` fuori da `^E_[A-Z0-9_]+$` e non nel registro | il rubinetto del §7: i 57 sono debito noto, il 58° no |
| **C** | una voce del registro che non corrisponde più a nessun codice a seed | **il debito deve calare**: un registro che si può solo allungare è il posto dove i problemi vanno a sparire |

Dry-run prima di scriverlo, sul DB vivo: **(A) zero violazioni** — e il regex non
inciampa sulle 36 funzioni che nominano `CONSTRAINT` per altri motivi (`ADD
CONSTRAINT` in SQL dinamico), perché àncora la ricerca a `RAISE ... USING` dentro
lo stesso statement. **(B) 58 codici** fuori convenzione: i 57 del §7 più la riga
morta con l'apostrofo, che infatti si è tolta.

✅ **Costruito e verde.** Dopo l'apply il guardrail esce con `exit 0` e il
messaggio *«un solo mittente sul canale CONSTRAINT, nessun codice fuori
convenzione non registrato, nessuna voce di troppo nel registro (57
registrate)»*. È in CI come passo `Guardrail codice errore strutturato`, messo
**prima** del migrate di Django — al contrario di quello dei riferimenti morti,
che invece lo pretende dopo perché compila i corpi e ha bisogno dello schema
`django`; questo legge solo `pg_proc`, `config.messaggi_errore` e il registro,
che Liquibase ha già messo.

### Perché il registro non chiede un `motivo` per riga

`dbops.riferimenti_morti_esenzioni` impone un motivo di almeno 40 caratteri per
riga, e lì è giusto: ogni voce è una **decisione indipendente**. Qui no: le 57
voci sono **una sola decisione** (quella del §7) applicata 57 volte. Un campo
`motivo` obbligatorio produrrebbe 57 copie della stessa frase, cioè rumore che
somiglia a rigore. La motivazione sta nel `COMMENT ON TABLE`, dove è scritta una
volta e si legge una volta.

### Cosa **non** si è fatto, e perché

* **Non** si controlla la forma piena `E_{MODULO}_{TIPO}` dichiarata in
  `api.md`, ma solo il prefisso `E_` e l'alfabeto. Motivo: 13 codici conformi e
  in uso hanno un solo underscore (`E_DATABASE`, `E_GENERICO`, `E_TOKEN`,
  `E_PIPELINE`…), e diversi sono registrati in `error_policies.py`. Stringere
  fino alla forma piena vorrebbe dire un secondo registro da 13 voci per
  comprare, in cambio, niente: quello che serve al BE è **il prefisso**, perché
  è su quello che `ErrorPolicyRegistry.resolve` decide 400 anziché 500.
* **Non** si è messo un trigger su `config.messaggi_errore`. Sarebbe più
  DB-first, ma i codici nuovi entrano solo dal CSV via Liquibase — che la CI
  esegue — e un trigger su una tabella caricata in `runOnChange` da un
  `loadUpdateData` è un modo eccellente per rompere un seed a metà giro.
* **Non** si sono usati `SCHEMA`/`TABLE`/`COLUMN`/`DATATYPE`, pure liberi, per
  far viaggiare `p_area` e `p_function_name`. Sarebbe comodo, ma psycopg e
  Django leggono quei campi per comporre i messaggi di `IntegrityError`:
  riempirli con «area» direbbe una cosa falsa. È la stessa obiezione con cui il
  §3 scarta `COLUMN` — vale anche per i suoi fratelli.

---

## 11. Cosa è stato consegnato, e cosa lo dimostra

### I file

| File | |
|---|---|
| `20_code/script/20260805-05-update-fn-log-and-raise-error-constraint-codice` | il campo strutturato. Corpo dalla doc auto-gen, `runOnChange: false`, rollback al comportamento pre-slice |
| `00_schema/dbops/20260805-06-create-messaggi-errore-codici-legacy` | il registro del debito |
| `80_data/changelog/20260805-07-seed-messaggi-errore-codici-legacy` + `80_data/sql/dbops/messaggi_errore_codici_legacy.csv` | le 57 voci. `DELETE` + `loadData`, non upsert: il registro deve poter **calare** togliendo una riga dal CSV |
| `80_data/changelog/20260805-08-delete-messaggio-errore-codice-con-apostrofo` + riga 88 del CSV messaggi | la riga morta (§7) |
| `80_data/changelog/20260805-11-delete-messaggi-errore-codici-superati` + 4 righe dai **due** CSV | i 4 codici superati: registro **57 → 53** (§7) |
| `scripts/sql/guardrail_codice_errore_strutturato.sql` | i tre controlli (§10) |
| `.github/workflows/ci-validate.yaml` | il passo di CI |
| `db/pgtap/script/test-fn-log-and-raise-error-constraint-codice.sql` | 5 asserzioni, nuovo |
| `db/pgtap/vendite/test-ordini-guard-transizione-v1.sql` | `plan(7)` → `plan(8)`: il gruppo C sul percorso vero |

Documentazione: `api.md` §Tassonomia errori (il contratto visto dal BE + i 57
codici), il manuale di `fn_log_and_raise_error`, e il **§3.3 nuovo** della guida
*Presidi e registri del debito*.

### Le prove

| | |
|---|---|
| pgTAP helper | **5/5** — campo + `P0001`, DETAIL/HINT invariati, contratto negativo, annidamento, codice non a seed |
| pgTAP guard ordini | **8/8** — l'8 asserisce `E_ORD_ANNULLA_IN_COMMESSA` sul campo, con il codice che arriva da `v_motivi` |
| Guardrail nuovo | **exit 0** |
| Guardrail riferimenti morti | **verde** dopo la modifica alla funzione |
| `pgtap-baseline.sh script vendite` | **nessuna regressione** — 48 rossi, tutti già noti |
| ChangeSet | `20260805-05..08` tutti `EXECUTED`; riga morta: **0 residui** |

⚠️ **Una nota sui test, perché non tragga in inganno chi li legge dopo.** Il
pgTAP sull'helper passa il codice **come parametro**, non come letterale nella
chiamata. È voluto: è la forma del gruppo C. Un test scritto col letterale
sarebbe passato **anche senza la modifica**, pescando il codice dal testo dello
statement — cioè avrebbe misurato il vecchio meccanismo credendo di misurare il
nuovo. Lo stesso vale per il test 8 sulla guard ordini, che è lì proprio perché
sull'helper il codice si sa già quando lo si chiama.

---

## 12. ✅ Lato BE — chiuso il 2026-08-05

Eseguito nell'ordine obbligato del §9: prima i codici, poi la lettura.

### 12.1 I codici (#6): erano 30, non 57

Due sottrazioni, e nessuna delle due si vedeva dal brief iniziale:

* **23 dei 57 erano già registrati** — la correzione del §7, confermata sul
  file;
* **4 sono usciti dal seed** con `20260805-11` mentre il BE lavorava: erano fra
  i miei, e li ho tolti. 57 − 4 − 23 = **30**, che è il numero del §7.

Registrarli tutti e 57 alla lettera produce **chiavi duplicate** nel dizionario
di `error_policies.py` — che in Python non è un errore: l'ultima vince, in
silenzio. In cinque casi la copia nuova aveva uno status **diverso** dalla voce
storica, e uno di quei cinque (`FLUSSI_ESITO_OBBLIGATORIO`, da 409 a 400) ha
fatto diventare rosso `test_workflow_guard_codes_hanno_policy_409` — un test che
quegli status li aveva già fissati e che ha fatto esattamente il suo lavoro.
Senza quel test la sovrascrittura sarebbe passata muta: è il caso da tenere a
mente ogni volta che si tocca questo file.

Conservate **sempre** le voci preesistenti: sono il contratto in uso, e cambiare
lo status di endpoint già in esercizio non era in perimetro. I 34 nuovi seguono
la tassonomia di `api.md` letta **sul messaggio a seed, non sul nome** — un
codice che si chiama `..._NON_AMMESSO` può essere un 409 (stato) o un 400
(valore fuori dominio), e la differenza sta nel messaggio.

| Status | Voci | Criterio |
|---|---:|---|
| 409 | 28 | conflitto con lo stato corrente: transizioni, immutabilità, «già esistente», precondizioni di emissione |
| 400 | 19 | input non valido o incoerente, validazioni di campo, progettazione degli step template |
| 404 | 2 | non trovato |
| 500 | 3 | configurazione di sistema: non è l'utente a sbagliare |
| 422 | 1 | voce storica preesistente, non toccata |

Verifica: i **53** di `dbops.messaggi_errore_codici_legacy` risolvono tutti a una
policy registrata, **nessuno** cade più su `E_GENERICO`; e nel registro non c'è
**nessuna chiave duplicata** (**460** voci, 460 distinte — cioè le 430 di prima
più le 30 nuove, il conto del §7).

#### ✅ I 5 status divergenti — decisi e applicati (Tid, 2026-08-05)

Cinque voci storiche avevano uno status che non corrispondeva alla loro
semantica. Non erano codici nuovi: rispondevano già così, quindi cambiarli è un
**cambio di contratto** verso il FE e andava deciso, non fatto di slancio. La
rilettura DB le ha esaminate una per una; **quattro applicate, una tenuta com'è**:

| Codice | Prima | Ora | Perché |
|---|---:|---:|---|
| `FLUSSI_COMPETENZA_MANCANTE` | 409 | **403** | è autorizzazione — l'operatore non ha la competenza — non conflitto con lo stato |
| `FLUSSI_PRESA_NON_ELIGIBILE` | 409 | **403** | idem: il flusso è instradato a un altro reparto |
| `FLUSSI_ESITO_OBBLIGATORIO` | 409 | **400** | è un campo obbligatorio non compilato, non uno stato che impedisce l'azione |
| `DEFINIZIONE_NON_PUBBLICABILE` | 422 | **409** | era l'unico 422 in una famiglia `DEFINIZIONE_*` tutta 409, a parità di semantica |
| `FLUSSI_TEMPLATE_FUORI_DEFINIZIONE` | 409 | **409** | tenuto: «il template non appartiene alla definizione pinnata dalla pratica» descrive uno stato del percorso, non un campo compilato male |

Erano tutti a 409 **per inerzia**, non per scelta: quando l'unica cosa che si
sapeva era «non è un errore tecnico», 409 era la casella comoda.

**Il test è stato riscritto, non aggiustato.** `test_workflow_guard_codes_hanno_policy_409`
asseriva `409` per tutti; ora è
`test_workflow_guard_codes_hanno_lo_status_atteso` e asserisce **lo status
atteso per ogni codice**, su 14 codici invece di 7. La differenza non è
cosmetica: un `assertEqual(..., 409)` uguale per tutti non si accorge se un
codice finisce sulla policy di un altro — ed è esattamente quello che era
successo con la chiave duplicata.

Il pgTAP `test-assegnazione-flusso-eligibilita.sql` asserisce il **codice**, non
lo status: non si rompe. Suite: 3574 verdi.

⚠️ **Nota per chi tocca `error_policies.py`:** un dizionario con 464 chiavi non
protesta se ne aggiungi una che c'è già. Prima di inserire, verificare — il
sintomo non è un errore ma un comportamento che cambia altrove.

### 12.2 La lettura (#3): i punti erano **quattro**

Il brief ne indicava tre. Il quarto è `pratiche_service._raise_known_db_error`,
ed è quello dove il vecchio meccanismo era messo peggio: i codici di quel dominio
non hanno prefisso `E_`, quindi la regex non li ha **mai** visti e l'unico
appiglio erano **14 frammenti di messaggio in italiano**
(`"flussi ancora aperti"`, `"non e' ripetibile in questa pratica"`…). Bastava
riformulare una frase nel seed — o tradurla, come il commento stesso avvertiva —
e il match cadeva in silenzio sul generico.

Estratta **una** lettura condivisa in
[`apps/core/services/db_error_fields.py`](../../../../backend/apps/core/services/db_error_fields.py)
(regola del 2, alla quarta copia): `structured_db_error_code` (solo campo) e
`db_error_code` (campo + ripiego a regex). Modulo senza dipendenze interne: lo
importano `error_translator`, `error_manager` e `payload_helpers`, e un import
verso quei moduli sarebbe un ciclo.

Nei due `raise_from_*` il codice dal campo è accettato **solo se il chiamante lo
ha dichiarato** nei propri marker. Non è timidezza: in quelle firme `message` e
`fallback_message` sono due messaggi diversi, scelti in base a «riconosciuto o
no». Accettare un codice fuori lista farebbe usare il messaggio del caso
riconosciuto per un errore che il chiamante non aspettava. L'insieme degli esiti
resta identico a prima — cambia solo che il match non dipende più dal testo.

Entrambe le indicazioni del §9 «cosa trova il BE già pronto» erano esatte e sono
implementate: guard su `P0001` e `... or None` sulla stringa vuota. Il secondo ha
un test dedicato, perché è il caso che si rompe **senza** rompersi.

### 12.3 I test

`apps/core/tests/services/test_db_error_fields.py` — **11 verdi**:

* **8 unitari** sulla precedenza campo/testo, senza DB: il campo vince sul testo
  anche quando il testo contiene un codice *diverso*; stringa vuota → ripiego;
  campo assente → ripiego; **SQLSTATE `23xxx` → il campo si ignora**; un codice
  legacy senza prefisso arriva e risolve a **409, non a 500**; e i due casi di
  `raise_from_database_error` (codice dichiarato / non dichiarato);
* **3 end-to-end su DB reale**, che sono l'unica cosa che un sostituto non può
  dimostrare — che i campi diag sopravvivano al giro libpq/psycopg. Fra questi il
  **caso del gruppo C**: codice passato da variabile, dove il test asserisce che
  la regex **non trova nulla** e il campo sì. È il contrario del test che passa
  per il motivo sbagliato: qui il vecchio meccanismo deve fallire.

Gli end-to-end sono **opt-in** (`ZEROERP_TEST_DB_E2E=1`), spenti di default per
il vincolo CI di `AGENTS.md`. Suite intera: **3574 verdi**, 1 classe skipped.

> ⚠️ **Aggiornamento del pomeriggio — vedi §14.** Il flag è stato **acceso in
> CI**, quindi i tre e2e non sono più «da lanciare quando uno se ne ricorda»:
> girano a ogni PR. Ed è emerso *perché* funzionano, che non è il motivo che
> sembra e che va saputo prima di toccarli.

> ⚠️ **Un test che rompeva i test degli altri.** La prima versione decideva se
> saltare con `@skipUnless(_db_raggiungibile(), ...)`. L'argomento di un
> decoratore si valuta **all'import**: quel probe apriva una connessione al DB di
> sviluppo durante la *discovery*, prima che il runner predisponesse i database,
> e faceva diventare rossi **469 test di altre app** (middleware che rispondeva
> 500 invece di 404/400) — mentre la suite mirata delle stesse app, senza questo
> file, era verde.
>
> Peggio: per un po' ho creduto che quei rossi fossero preesistenti, perché li
> avevo confrontati con `HEAD` via `git stash`. **`git stash` non tocca i file
> non tracciati**: il file incriminato restava al suo posto anche nella misura di
> «baseline», che quindi mostrava lo stesso difetto (604 contro 601) e sembrava
> assolverlo. Una baseline che contiene la causa non è una baseline. Tolto il
> contatto col DB dall'import, la suite intera è verde: di rossi preesistenti non
> ce n'era **nessuno**.

### 12.4 I file consegnati, e cosa li dimostra

| File | |
|---|---|
| `apps/core/services/db_error_fields.py` | **nuovo** — la lettura unica: `structured_db_error_code` (solo campo, guard `P0001`, stringa vuota → `None`), `db_error_code` (campo + ripiego regex), `db_diag`. Nessuna dipendenza interna: lo importano i tre moduli core e un import verso di loro sarebbe un ciclo |
| `apps/core/services/error_translator.py` | usa `db_error_code`; `_extract_app_error_code` resta come delegatore del solo ripiego (lo chiamano i test); via la regex locale |
| `apps/core/services/payload_helpers.py` | `translate_db_errors` usa `db_error_code`; `DB_ERROR_CODE_RE` resta come alias per chi lo importava |
| `apps/core/services/error_manager.py` | `raise_from_database_error` accetta il campo **solo se dichiarato** nei `known_markers` del chiamante |
| `apps/pratiche/services/pratiche_service.py` | il quarto punto: campo per primo, i 14 marker testuali restano come ripiego |
| `apps/core/services/error_policies.py` | **30** voci nuove (i codici legacy) + **4** status rivisti (§12.1) |
| `apps/core/tests/services/test_db_error_fields.py` | **nuovo** — 8 unitari + 3 end-to-end opt-in |
| `apps/pratiche/tests/services/test_pratiche_service_flussi.py` | `..._policy_409` → `..._hanno_lo_status_atteso`: mappa codice → status su 14 codici |

Documentazione: `api.md` §Tassonomia errori (dove vive la lettura unica e la
tabella dei 4 punti), il [catalogo BB backend](../backend/catalogo-building-block-backend.md)
(`db_error_fields` come building block), e questo §12.

| Prova | Esito |
|---|---|
| `test_db_error_fields` | **11/11** — default: 8 run + 3 skipped; con `ZEROERP_TEST_DB_E2E=1`: 11 run |
| `test_error_codes_declared_guardrail` | **verde** (2 test) |
| `apps.pratiche.tests` | **234 verdi** dopo il cambio di status |
| Suite intera | **3574 verdi**, 1 classe skipped |
| Chiavi `_POLICIES` | **460**, 460 distinte, **nessuna duplicata** |
| Registro legacy | **53/53** coperti, nessuno su `E_GENERICO` |
| Modalità CI (senza DB) | verde: gli end-to-end si saltano, non falliscono |

---

### 12.5 Cosa resta aperto, e non è di questa slice

**133 codici `E_*` sollevati da funzioni DB vive non sono dichiarati in
`error_policies.py`** — 83 da trigger function agganciate, quindi sul percorso
richiesta. Non è una regressione né un effetto di questa slice: sono così da
sempre, e l'effetto è che lo status HTTP resta appiattito a 400 dove servirebbe
409/404/403 (il messaggio localizzato arriva comunque all'operatore).

Il motivo per cui nessuno se n'era accorto è strutturale, ed è la coda naturale
del §10: esiste un presidio sui codici usati nel **codice Python**
(`test_error_codes_declared_guardrail`) ed esiste quello DB sui codici sollevati
vs `messaggi_errore.csv`. **Manca il terzo lato — codici sollevati dal DB vs
`error_policies.py`** — ed è l'unica direzione che nessuno guarda: è da lì che
sono passati questi 133, ed è la stessa direzione da cui erano passati i 9 codici
del §8 diventati raggiungibili con F8.

Misura già scritta e funzionante (≈40 righe, legge `pg_proc` + il testo di
`error_policies.py`, non serve Django). Manca la decisione su come chiuderlo:
83 status da assegnare uno per uno, e il presidio in `ci-validate.yaml`.

---

## 13. I due controlli, per non rifarli a mano

**Chiavi duplicate in `error_policies.py`** (deve stampare due numeri uguali e
lista vuota). È il controllo che manca a monte: nel progetto non ci sono
`ruff`/`flake8` che intercettino una chiave ripetuta in un dict literal, e
l'ultima vince senza dire niente.

```bash
python - <<'PY'
import re, collections
src = open('backend/apps/core/services/error_policies.py').read()
k = re.findall(r'^\s*"([A-Z][A-Z0-9_]*)":\s*ErrorPolicy\(', src, re.M)
print("voci:", len(k), "| distinte:", len(set(k)),
      "| duplicate:", [x for x, c in collections.Counter(k).items() if c > 1])
PY
```

**Copertura del registro legacy** (ogni codice del registro deve avere una
policy; nessuno deve cadere su `E_GENERICO`):

```sql
SELECT codice FROM dbops.messaggi_errore_codici_legacy ORDER BY 1;
```

confrontato con le chiavi estratte sopra. Al 2026-08-05: **53 su 53 coperti**,
460 voci totali, nessuna duplicata.

> ⚠️ **Se si rifà il censimento dei call site**, togliere i commenti **prima** di
> contare gli argomenti: un apostrofo dentro un commento SQL (`-- la funzione e'
> VARIADIC`) apre una stringa che non si chiude più e inghiotte le virgole
> successive. Ci sono cascate entrambe le sponde — il BE contando 20 call site
> dove erano 16, il DB trovando 2 residui inesistenti alla ri-verifica. **Anche
> la misura di un difetto è un programma, e può avere il suo difetto.**

---

## 14. Coda — perché i 3 e2e funzionano, e cosa li romperà (2026-08-05, pomeriggio)

Lanciati sul server backend: **11 verdi**, i tre end-to-end compresi. Non era
scontato — la previsione era che fallissero, perché `settings.py` non ha nessun
blocco `TEST` sull'alias `default` e `manage-test.sh` non usa `--keepdb`: il
runner avrebbe dovuto creare un database usa-e-getta con le sole migration
Django, dove `script.fn_log_and_raise_error` non esiste.

**La risposta era nella terza riga dell'output**, che è facile scorrere:

```
Skipping setup of unused database(s): default, system_fatturazione.
```

### 14.1 Il meccanismo

Django prepara il database di test **solo se almeno un test dichiara di averne
bisogno**: `django.test.TestCase`, `TransactionTestCase`, o un attributo
`databases = [...]`. Censito su `backend/apps`:

| Base class | Occorrenze |
|---|---:|
| `unittest.TestCase` | 114 |
| `django.test.SimpleTestCase` | 86 |
| `django.test.TestCase` / `TransactionTestCase` | **0** |

Zero, ed è la conseguenza diretta della regola di `AGENTS.md` — *«i test devono
funzionare in CI senza dipendere da un DB reale accessibile»*. Buona regola, e
regge anche qui.

Effetto: **nessun database di test viene creato**, quindi `django.db.connection`
resta puntata a quella **configurata** — il database di sviluppo, con lo schema
Liquibase completo. Ecco perché i tre e2e trovano la funzione e passano.

### 14.2 ⚠️ Ma è una coincidenza, non un progetto

Funzionano perché **nessuno**, in tutto il backend, ha ancora scritto un test che
dichiari un database. Non è vietato — `AGENTS.md` dice «non usarlo *a meno che*
il test non necessiti realmente del database», che è un'autorizzazione
condizionata, non un divieto.

Il primo che lo farà, in una app qualunque, farà creare al runner un database
vuoto **per tutta la suite**. Lì le nostre funzioni PL/pgSQL non ci sono, e i tre
e2e cominceranno a fallire con «la funzione `script.fn_log_and_raise_error` non
esiste» — **dentro una PR che non c'entra niente**, addosso a chi non ha idea di
cosa siano.

È la stessa forma di difetto che questo brief racconta dall'inizio: **qualcosa
che funziona per una ragione che nessuno ha progettato.** Il codice errore
arrivava al backend nel 91% dei casi perché il driver allega al testo lo
statement chiamante; questi tre test girano perché nessuno ha ancora scritto un
`TestCase` con database. Due coincidenze diverse, la stessa fragilità.

### 14.3 Cosa si è fatto (DB)

| | |
|---|---|
| **CI** | `ZEROERP_TEST_DB_E2E: "1"` nello step «Django tests» di `ci-validate.yaml`. Funziona proprio grazie a §14.1: il job ha il servizio `postgres`, lo step gira **dopo** Liquibase e `manage.py migrate`, e con il setup dei database saltato la connessione è quella provvista. I tre e2e passano da «da lanciare a mano» a **eseguiti a ogni PR**: la giuntura DB → psycopg diventa presidiata da un cancello automatico invece che verificata a memoria |
| **`.codex/AGENTS.md`** | la dipendenza implicita è scritta **subito sotto** la regola che la regge, nel §Regole test Django. Chi sta per scrivere un `django.test.TestCase` la legge *mentre decide*, non dopo che la CI è rossa |

### 14.4 Cosa si chiede al BE

Brief dedicato: [brief-be-e2e-db-error-fields-skip-schema](../work-done/brief-be-e2e-db-error-fields-skip-schema.md).
In sintesi:

1. un **`SkipTest`** nel `setUpClass`, dopo `ensure_connection()`, che verifichi
   `to_regprocedure('script.fn_log_and_raise_error(text,text,text,jsonb,uuid,text[])')`.
   Non serve a farli girare — girano: serve a far dire **cos'è successo** il
   giorno in cui non gireranno più. Uno skip che si spiega invece di un errore
   criptico su una PR altrui. Lo snippet è scritto pronto nel brief;
2. la condizione implicita del §14.1 nel **docstring** della classe, accanto alla
   nota — ottima, da tenere — sul probe a import-time che faceva 469 rossi;
3. ⚠️ **niente test che scrivono, in quel file.** Poiché la connessione è quella
   vera, un test che scrive scriverebbe sul database di sviluppo. I tre attuali
   no: provocano solo un errore dentro un `transaction.atomic()` che viene
   annullato — ma il prossimo che aggiunge un caso lì dentro non ha modo di
   saperlo, se non glielo si scrive accanto.

---

## 15. ⭐ `obsoleto_dal` — ritirare un codice senza cancellarlo (deciso 2026-08-05)

### 15.1 Il muro

Il ritiro di un codice legacy finora è stato un `DELETE` (`20260805-11`, `-16`).
Provando a togliere `PREV_TRANSIZIONE_NON_AMMESSA` — rinominato in
`E_PREV_TRANSIZIONE_NON_AMMESSA` da `20260805-15`, quindi il **primo debito
davvero pagato** e non un codice morto — il `DELETE` è stato **rifiutato dalla
foreign key**: `dbops.error_log.messaggio_errore_id` punta a
`config.messaggi_errore(id)` ed è **`NOT NULL`**. Quel codice ha 109 righe di log.

Non è un caso isolato. Misurato il 2026-08-05:

| | |
|---:|---|
| **46 su 53** | codici del registro **con** righe di log → `DELETE` impossibile |
| 7 | senza log → cancellabili (sono i casi già chiusi) |
| **46.040** | righe di `error_log` complessive sui 46 |

Quindi la strada del `DELETE` è chiusa per **quasi tutto il cantiere che resta**.

### 15.2 ⚠️ E c'è un secondo problema, più insidioso della FK

**Un `DELETE` su `messaggi_errore` passa in CI e può fallire su un DB longevo.**
In CI `error_log` nasce vuota, quindi la FK non protesta mai; su `dev` — e domani
in produzione — protesta se quel codice ha girato **almeno una volta**.

Un changeSet il cui esito dipende da **quanto è vissuto il database** non è
riproducibile: verde in CI, rosso da chi lo applica davvero. È la stessa
avvertenza del registro delle migrazioni — *verificare solo su dev misura una
macchina, non la riproducibilità*, qui nella forma opposta e più subdola, perché
è la CI a dare la risposta rassicurante.

⚠️ Anche i changeSet `-11` e `-16` già applicati hanno questa forma: hanno
funzionato perché quei sei codici avevano **0 righe di log**, verificato prima di
scriverli. Non è una fortuna, è il controllo che è stato fatto — ma non è una
strada che scala.

### 15.3 Le tre strade, e perché B

| | Cosa | Perché no / sì |
|---|---|---|
| **A** | il changeSet cancella prima i log, poi il messaggio | funziona ovunque, ma **distrugge 46.040 righe di storia** per riordinare un catalogo. E il changeSet vive per sempre: il giorno della produzione farebbe la stessa cosa su dati veri. Si scambia evidenza per pulizia |
| **C** | il guardrail smette di segnalare un codice fuori convenzione quando **nessuno lo solleva più** (obsolescenza *derivata*) | elegante e quasi gratis, ma **sotto-rileva**: non vede i codici sollevati dal **Python**, e il guardrail è uno script SQL — `backend/` non lo può leggere |
| **B** ⭐ | **`obsoleto_dal`** sul catalogo: la riga resta, i log restano agganciati, il presidio ignora gli obsoleti | scelta |

**Perché B, in tre punti:**

1. **È il pattern che il progetto ha già deciso** per questa classe esatta —
   deprecare una voce di catalogo referenziata da istanze storiche, senza usare
   `attivo = false` che romperebbe i riferimenti. Colonna **data**, asse
   «selezionabile per il nuovo» separato da «esiste» (`brief-db-deprecabilita-catalogo-vs-istanze` §0).
2. **Funziona identico su dev, CI e produzione**: nessuna dipendenza dai dati,
   nessun changeSet il cui esito cambia col vissuto del database.
3. **È l'unica che fa funzionare davvero la storia del registro.** Il piano è
   «il registro cala fino a zero, poi la tabella si droppa»: ma se le righe di
   catalogo non si possono cancellare, un codice ritirato deve pur stare da
   qualche parte. Con `obsoleto_dal` sta **nel catalogo**, che è il posto giusto,
   e il registro può davvero svuotarsi.

### 15.4 La forma

**Colonna.** `config.messaggi_errore.obsoleto_dal DATE NULL`. NULL = in servizio;
valorizzata = ritirata, non più nominabile da codice nuovo.

⚠️ **`obsoleto_dal` NON deve nascondere il messaggio.** `fn_get_messaggio` e
`fn_log_and_raise_error` continuano a risolverlo: se un percorso non ancora
bonificato lo solleva, l'operatore deve leggere una frase, non
`[MESSAGGIO NON DEFINITO]`. La colonna è un asse per il **presidio**, non un
interruttore di runtime — è esattamente la differenza fra `obsoleto_dal` e
`attivo` che la guida sulla deprecabilità mette in guardia di non confondere.

**Seed.** La colonna va aggiunta **al CSV e alla lista `columns:` del loader**
`20260614-08`: è un `loadUpdateData` `runOnChange` + `validCheckSums: ANY`, cioè
un mirror vivo del CSV, e una colonna non elencata non verrebbe mai toccata.
Estenderlo in place è lecito proprio perché è progettato per ri-girare. Nessun
backfill: tutte le righe nascono `NULL`.

**Guardrail** (`scripts/sql/guardrail_codice_errore_strutturato.sql`):

| Controllo | Come cambia |
|---|---|
| **(B)** codici fuori convenzione non registrati | **ignora** i codici con `obsoleto_dal` valorizzata: sono ritirati, non debito |
| **(C)** voci di troppo nel registro | oggi «il codice non è più a catalogo» → diventa «non è più a catalogo **oppure è obsoleto**»: in entrambi i casi la riga del registro va tolta |
| **(D)** *nuovo* | ⚠️ **nessuna funzione viva solleva un codice obsoleto.** È il controllo che rende `obsoleto_dal` una promessa mantenuta invece di un'etichetta: si marca obsoleto **dopo** aver tolto i call site, e il presidio impedisce che qualcuno lo rimetta. Senza (D), `obsoleto_dal` sarebbe esattamente il tipo di etichetta rassicurante che il §4-bis della guida sui presidi indica come il punto cieco peggiore |

**Procedura di ritiro, dopo questa slice** — tre righe, sempre le stesse:

1. rinominare il codice ai call site (changeSet `20_code`) e aggiungere il nuovo
   codice `E_*` al CSV del catalogo;
2. valorizzare `obsoleto_dal` sulla riga vecchia (CSV del catalogo);
3. togliere la riga dal CSV del registro (è un mirror: basta quello).

Nessun `DELETE`, nessuna FK da schivare, nessuna riga di log persa, e il conto
del registro cala di uno.

### 15.5 Cosa serve, in ordine

| # | Cosa | Dove |
|---|---|---|
| 1 | `ALTER TABLE config.messaggi_errore ADD COLUMN obsoleto_dal DATE` + `COMMENT` che dica **cosa non è** (non è `attivo`, non nasconde il messaggio) | `00_schema/config/` |
| 2 | colonna nel CSV + nella lista `columns:` del loader `20260614-08` | `80_data` |
| 3 | guardrail: (B) e (C) adeguati, **(D) nuovo** | `scripts/sql/` |
| 4 | pgTAP: un codice obsoleto risolve ancora il messaggio; e il presidio lo ignora | `db/pgtap/script/` |
| 5 | primo uso reale: ritirare `PREV_TRANSIZIONE_NON_AMMESSA`, registro **51 → 50** | `80_data` |
| 6 | doc: la guida sui presidi (§3.3) e questa sezione | `docs/` |

Il punto 5 è quello che chiude il giro iniziato con `20260805-15`: la rinomina
c'è già, mancava solo un modo di ritirare il vecchio nome senza cancellare la
storia.

### 15.6 ✅ Fatto — 2026-08-05

| # | Cosa | Dove |
|---|---|---|
| 1 | colonna `obsoleto_dal DATE` + `COMMENT` che dice **cosa non è** | `20260805-17` |
| 2 | colonna nel CSV (token letterale `NULL`) e nel loader, con `nullValue` da `""` a `"NULL"` | `20260614-08` esteso in place |
| 3 | guardrail: (B) e (C) adeguati, **(D) nuovo** | `guardrail_codice_errore_strutturato.sql` |
| 4 | pgTAP `test-messaggi-errore-obsoleto-dal.sql` — **4/4 verdi** | `db/pgtap/script/` |
| 5 | ritirato `PREV_TRANSIZIONE_NON_AMMESSA`: registro **51 → 50** | solo CSV, nessun changeSet |
| 6 | guida presidi §3.3 e questa sezione | `docs/` |

**Le prove, tutte in transazione annullata:**

* guardrail verde a fine giro: *«50 attive, 1 ritirato»*;
* **(D) sa diventare rosso**: marcando obsoleto un codice ancora vivo
  (`ERRORE_PARAMETRI`) elenca le cinque funzioni che lo sollevano, col nome;
* **(D) tace su un ritiro programmato**: con `obsoleto_dal` a data futura non
  protesta, perché il codice è ancora in servizio;
* un codice ritirato **risolve ancora il suo messaggio** — asserito sia in
  simulazione sia dal pgTAP, ed è il contratto che regge tutto il resto.

Il punto 5 non ha richiesto nessun changeSet: **due celle di CSV**. È la
procedura del §15.4 alla sua prima applicazione, e vale identica per gli altri 45.

### 15.7 ⚠️ Due trappole pagate mentre si costruiva

**Il `DELETE` non tiene se il CSV torna indietro.** `20260805-16` era applicato e
`EXECUTED`, eppure `EMITTENTE_NON_MODIFICABILE` e `PREV_STATO_NON_MODIFICABILE`
sono **ricomparsi nel database**: un commit successivo ha riportato il CSV del
catalogo alla versione con quelle righe, e il loader `runOnChange` le ha
reinserite al migrate seguente. Il changeSet `-16` non poteva rimediare — è
`runOnChange: false`, gira una volta sola.
È la regola delle «due mosse» vista dal lato che non si prevede: non basta fare
entrambe, devono anche **restare** entrambe. Un altro argomento a favore di
`obsoleto_dal`, che essendo un *valore* nel CSV non ha questa asimmetria.

**Il CSV del catalogo ha un campo che contiene un a capo** — 636 righe fisiche
per 634 record. Aggiungere una colonna riga per riga spezza quel record e fa
slittare tutto: al primo tentativo ha alterato **1.579 campi** senza che il
confronto testuale se ne accorgesse, perché toglieva la colonna aggiunta e
ritrovava il file «identico». L'unica verifica che vale è il confronto
**record per record col parser CSV** — e con quella il round-trip risulta pulito:
634 record, zero campi modificati.

### 15.8 Primo lotto di rinomina — `trgfn_template_flussi_guard_modalita_esito`

Con `obsoleto_dal` in servizio, il cantiere dei 50 codici fuori convenzione si
apre. Prima misura utile: **nessuno dei 50 è pronto al ritiro** — sono tutti
ancora sollevati da qualcuno. Il lavoro quindi non è ritirare, è **rinominare**;
il ritiro è la coda di ogni rinomina.

**Il costo si legge per funzione, non per codice.** Contati per codice sono 129
punti di intervento; ma una sola `CREATE OR REPLACE` ne libera più d'uno:

| Codici liberati | Funzione | pgTAP da toccare |
|---:|---|---:|
| **4** | `pratiche.trgfn_template_flussi_guard_modalita_esito` | **0** ⭐ |
| 4 | `pratiche.fn_prendi_in_carico_flusso` | 2 |
| 4 | `pratiche.trgfn_pratiche_guard_contesto` | 1 |
| 3 | `vendite.fn_crea_revisione_preventivo` | 1 |

Il primo lotto è quello con quattro codici e **zero test da aggiornare**:
`20260805-19`, registro **50 → 46**.

La rinomina è meccanica — si antepone `E_` — ed è la stessa forma usata dal BE in
`20260805-15`. Non è l'occasione per riprogettare i nomi: modulo e tipo sono già
leggibili, mancava solo il prefisso su cui `resolve()` decide 400 invece di 500.

**Le tre mosse, e perché in quest'ordine:**

1. i 4 codici nuovi entrano a catalogo (CSV, id 842-845);
2. la funzione smette di sollevare i vecchi (`20260805-19`);
3. i vecchi vengono ritirati con `obsoleto_dal` e tolti dal registro (CSV).

Il 3 non può precedere il 2 — il controllo (D) fallirebbe, ed è il suo mestiere.
Il 1 non può seguire il 2 — l'operatore leggerebbe `[MESSAGGIO NON DEFINITO]`.

⚠️ **Nota onesta sull'ordine dentro il migrate:** il CSV del catalogo è `80_data`
e la funzione è `20_code`, quindi fra il passo 2 e il passo 1 esiste una finestra
**dentro** il migrate in cui la funzione solleva codici non ancora a catalogo. È
accettabile — nessuno usa il database durante un migrate, e a fine giro lo stato
è coerente — ma va saputo, non scoperto.

**✅ APPLICATO E VERIFICATO (2026-08-05).** `20260805-19` è `EXECUTED`, e con lui
`-16`, `-17`, `-18`. Sul DB:

| | |
|---|---|
| Guardrail | **verde** — *«46 attive, 5 ritirati»* |
| Registro | **50 → 46** |
| Codici ritirati | 5 (`PREV_TRANSIZIONE_NON_AMMESSA` + i 4 del lotto) |
| Nuovi `E_TEMPLATE_FLUSSO_*` a catalogo | 4 |
| Doppioni risorti | **0** — `-18` ha chiuso la partita |
| `pgtap-baseline.sh pratiche` | **nessuna regressione** |

Il controllo (D) tace, cioè la funzione non nomina più i vecchi codici: è la
prova che la rinomina è completa e non parziale.

> ⚠️ **Un difetto trovato dalla simulazione, che la sola lettura non avrebbe
> visto.** Il corpo copiato dalla doc auto-gen finisce con `$function$` **senza
> punto e virgola** — nell'auto-gen il `COMMENT` che segue è un blocco separato,
> nel changeSet è lo stesso statement. Senza il `;` l'apply muore con
> *«errore di sintassi a o presso "COMMENT"»*. Vale per **ogni** changeSet che
> ricopia un corpo dall'auto-gen: è una riga che il copia-incolla non porta con
> sé.

**Richiesta al BE:** i 4 vecchi codici hanno una voce in `error_policies.py`
(dal blocco del 2026-08-05). Le voci vanno **rinominate**, non duplicate — una
chiave ripetuta in un dict literal vince l'ultima senza dire niente. Gli status
non cambiano.

### 15.9 Secondo lotto — `trgfn_pratiche_guard_contesto`

`20260805-20`. Altri **4 codici** in una funzione sola: la guard di coerenza fra
soggetto, ruolo e istanza utility della pratica.

| Vecchio | id | Nuovo | id |
|---|---:|---|---:|
| `PRATICHE_RUOLO_SENZA_SOGGETTO` | 305 | `E_PRATICHE_RUOLO_SENZA_SOGGETTO` | 846 |
| `PRATICHE_RUOLO_NON_COERENTE` | 306 | `E_PRATICHE_RUOLO_NON_COERENTE` | 847 |
| `PRATICHE_ISTANZA_NON_COERENTE` | 307 | `E_PRATICHE_ISTANZA_NON_COERENTE` | 848 |
| `PRATICHE_ISTANZA_SENZA_SOGGETTO` | 308 | `E_PRATICHE_ISTANZA_SENZA_SOGGETTO` | 849 |

Registro **46 → 42**. Simulazione verde: *«42 attive, 9 ritirati»*.

> ⚠️ **Il pgTAP di quella guard non se ne accorge, ed è bene saperlo.**
> `test-guard-contesto-pratica.sql` la copre con cinque
> `throws_ok(sql, NULL, NULL, descrizione)`: i due `NULL` sono SQLSTATE e
> messaggio attesi, quindi il test asserisce soltanto **che qualcosa fallisca**,
> non *cosa*. La rinomina perciò non lo rompe — ma non è un merito suo: non se ne
> accorgerebbe nemmeno se il codice fosse sbagliato. Il suo verde **non è** una
> conferma della rinomina; la conferma è il controllo (D) del guardrail.
> Non è materia di questo lotto, ma è un candidato per quando si passerà a
> rinforzare le asserzioni deboli.

### 15.10 Avanzamento del cantiere

| Lotto | Funzione | Codici | Registro | Stato |
|---|---|---:|---|---|
| — | ritiro `PREV_TRANSIZIONE_NON_AMMESSA` (già rinominato da `20260805-15`) | 1 | 51 → 50 | ✅ |
| 1° | `pratiche.trgfn_template_flussi_guard_modalita_esito` | 4 | 50 → 46 | ✅ applicato |
| 2° | `pratiche.trgfn_pratiche_guard_contesto` | 4 | 46 → 42 | ⏳ da applicare |
| 3° | `pratiche.fn_prendi_in_carico_flusso` | 4 | 42 → 38 | prossimo (2 pgTAP) |
| 4° | `vendite.fn_crea_revisione_preventivo` | 3 | 38 → 35 | (1 pgTAP) |

Da 57 di partenza a **42**: −15 in una giornata, di cui 6 cancellati (codici
morti) e 9 ritirati con `obsoleto_dal` dopo rinomina. I 42 che restano vivono in
circa 31 funzioni, e la coda è fatta soprattutto di funzioni che portano **un
codice solo**: da lì in poi il rapporto fra fatica e resa peggiora, e conviene
procedere per dominio invece che per conteggio.

### 15.11 Terzo lotto — e la scoperta che riordina il cantiere

**Il lotto previsto non si poteva fare da soli.** Il piano diceva
`pratiche.fn_prendi_in_carico_flusso` (4 codici). Misurando prima di scrivere:
quei quattro sono nominati **anche dal backend**, in
`apps/pratiche/services/pratiche_service.py`, dentro una lista `known_markers`
che riconosce l'errore da una **substring del messaggio** e ne restituisce il
codice.

⚠️ **Rinominarli a DB senza toccare il Python non romperebbe niente in modo
rumoroso — ed è questo il problema.** Il messaggio non cambia, quindi il marker
continua a corrispondere e l'API restituirebbe il **vecchio nome ormai ritirato**
mentre il DB solleva il nuovo. Due verità diverse sullo stesso errore, e nessun
test che protesti.

Da qui il censimento che riordina tutto il cantiere:

| | Codici | Funzioni | |
|---|---:|---:|---|
| ✅ **DB-only** | 20 | 15 | rinominabili da soli |
| 🔴 **Accoppiati al backend** | 37 | 29 | vanno rilasciati **insieme** al Python |

I lotti 1 e 2 erano DB-only per fortuna, non per scelta: la distinzione non era
stata fatta. Da qui in poi è il primo criterio di composizione dei lotti.

### 15.12 `20260805-25` — il lotto DB-only più grosso

`vendite.fn_crea_revisione_preventivo`, 3 codici:

| Vecchio | id | Nuovo | id |
|---|---:|---|---:|
| `PREV_REVISIONE_STATO_NON_AMMESSO` | 354 | `E_PREV_REVISIONE_STATO_NON_AMMESSO` | 850 |
| `PREV_REVISIONE_BOZZA_ESISTENTE` | 355 | `E_PREV_REVISIONE_BOZZA_ESISTENTE` | 851 |
| `PREV_STATO_CORRENTE_NON_TROVATO` | 357 | `E_PREV_STATO_CORRENTE_NON_TROVATO` | 852 |

Registro **42 → 39**.

**✅ APPLICATO E VERIFICATO (2026-08-05).** `20260805-25` è `EXECUTED`; guardrail
verde — *«39 attive, 12 ritirati»* — e `pgtap-baseline.sh vendite` senza
regressioni.

> ⚠️ **La prima simulazione è fallita, e ha insegnato la regola che mancava.**
> Il controllo (D) ha protestato: `PREV_STATO_CORRENTE_NON_TROVATO` **non è
> esclusivo** di `fn_crea_revisione_preventivo` — lo solleva anche
> `fn_cambia_stato_preventivo`. Rinominarlo in una sola delle due lasciava
> l'altra a sollevare un codice ritirato.
>
> **L'unità del ritiro è il CODICE, non la funzione.** Il raggruppamento per
> funzione serve solo a comporre i lotti e a stimarne il costo; prima di ritirare
> un codice va verificato **ovunque** sia sollevato. Il changeSet contiene perciò
> **due** `CREATE OR REPLACE`: la seconda cambia un solo letterale e lascia
> intatto `PREV_NESSUNA_RIGA_ATTIVA`, che uscirà col suo lotto.
>
> È il primo caso in cui un presidio scritto in questa slice ha fermato un errore
> di questa slice. Senza (D) il lotto sarebbe passato, e il difetto — una
> funzione che solleva un codice dichiarato ritirato — non aveva nessun altro
> modo di farsi notare.

Nel pgTAP `test-fn-crea-revisione-preventivo.sql` il codice era citato in una
descrizione di test e in un commento, mai in un'asserzione: aggiornati nello
stesso commit, perché una descrizione che nomina un codice inesistente confonde
chi legge fra sei mesi.

### 15.13 Il fronte accoppiato al backend — brief di coordinamento

Dei **39** codici ancora fuori convenzione, **27 sono nominati dal backend** e
**23 stanno in un file solo**: la lista `known_markers` di
`apps/pratiche/services/pratiche_service.py`. Gli altri 12 sono DB-only e il DB
li rinomina da solo.

Brief: [brief-be-rinomina-codici-known-markers](../work-done/brief-be-rinomina-codici-known-markers.md).

**La proposta, in una riga:** invece di un rilascio simultaneo per ogni lotto —
sincronia fra due repository e due server, che prima o poi va storta — il BE
**dichiara entrambi i nomi** in `known_markers` per un periodo. Poiché il campo
strutturato vince su qualunque marker *purché il codice sia fra quelli
dichiarati*, con entrambe le voci presenti:

| Momento | Cosa arriva dal DB | Esito |
|---|---|---|
| prima della rinomina | vecchio codice | matcha la voce vecchia ✅ |
| dopo la rinomina | nuovo codice | matcha la voce nuova ✅ |

**L'ordine di rilascio diventa indifferente e la finestra di disallineamento
sparisce.** È il campo strutturato che ripaga il debito che ha creato: senza di
esso servirebbe la sincronia.

Sequenza: il DB prosegue sui 12 DB-only mentre il BE prepara il §4 del suo brief;
i lotti accoppiati si aprono appena quelle voci sono in `Tito-dev`.

### 15.14 `20260805-26` — tutti i DB-only in un colpo solo

11 codici, **14 funzioni**, registro **39 → 28**.

I primi tre lotti sono stati piccoli apposta, perché la procedura era nuova. Ha
ripagato: hanno trovato il `;` mancante dopo `$function$` e il codice sollevato
da due funzioni invece che una. Ora la procedura è meccanica e le trappole sono
note — spezzare i restanti in altri otto changeSet aggiungerebbe cerimonia, non
sicurezza.

⚠️ **L'unità del ritiro è il codice, non la funzione**, e qui vale per quattro
codici su undici: `CODICE_NON_MODIFICABILE` è sollevato da **3** funzioni,
`PREV_NESSUNA_RIGA_ATTIVA`, `SEQUENZA_NON_CONFIGURATA` e
`TEMPLATE_FLUSSO_PROIEZIONE_CONFLITTO_HANDLER` da **2** ciascuno. Le 14 funzioni
sono l'elenco completo ricavato da `pg_proc`, non a memoria.

> ⚠️ **Un gemello `E_` esisteva già, e aveva il messaggio peggiore.**
> `E_SOSPENSIONI_FLUSSO_NON_COERENTE` era a catalogo (id 735), creato da qualcuno
> e **mai agganciato**. Il suo testo però era più povero dell'originale — senza
> segnaposti e senza causa/soluzione — mentre il 303 aveva
> «Il flusso %s non appartiene alla pratica %s» con entrambe.
>
> Puntarci la funzione così com'era avrebbe **peggiorato ciò che l'operatore
> legge**, dentro un changeSet che si presenta come una rinomina. Quindi il 735
> eredita il contenuto del 303, la funzione punta al 735, il 303 viene ritirato:
> 10 righe nuove, non 11.
>
> È l'unico caso su tutto il registro, ma resta come regola per i lotti futuri:
> **prima di creare il codice nuovo, verificare che non esista già** — e se
> esiste, confrontare i due messaggi invece di dare per scontato che il nuovo sia
> migliore.

### 15.15 ⭐ `W_` non era un codice storto: era un'altra famiglia

`W_TXID_NOT_REGISTERED` stava nel registro come «da rinominare». **Non lo era.**
La `W` sta per **warning**, è una scelta deliberata: il messaggio comincia con
«Warning - », e `dbops.trgfn_tx_id_managed` lo passa a `fn_log_error_only` — lo
**logga soltanto**, non lo solleva mai.

Rinominarlo `E_TXID_NOT_REGISTERED` avrebbe fatto dire al codice una cosa falsa
— che è un errore — **per far tornare un conteggio**. La convenzione di `api.md`
parla di codici di *errore*: i warning sono una famiglia che il presidio non
aveva considerato. Quindi si allarga la regola (`^[EW]_`), non si forza il dato.

⚠️ **Ma allargare apre un buco, e va chiuso nello stesso giro.** La scorciatoia
di `ErrorPolicyRegistry.resolve` vale **solo per `E_`**: un `W_` *sollevato*
arriverebbe al backend, non troverebbe policy e cadrebbe su `E_GENERICO` →
**HTTP 500**. Cioè il difetto da cui nasce tutta questa slice, reintrodotto da
una regola allentata.

Da qui il **controllo (E)**: *un codice `W_` non può comparire in una chiamata a
`fn_log_and_raise_error`*. La regola sta in una riga — **`E_` si solleva, `W_` si
scrive nel log** — e non è un commento, è un cancello della CI. Provato nei due
versi: verde oggi, rosso col nome della funzione se qualcuno ne solleva uno.

`20260805-28` allinea il `CHECK` del registro alla stessa regex.

> ⚠️ **E l'ordine dentro il changeSet non è pignoleria.** Allargare la
> convenzione rende `W_TXID_NOT_REGISTERED` *conforme*, e un codice conforme non
> può stare nel registro: il `CHECK` lo rifiuta. La riga esce anche dal CSV, ma
> quel seed vive in `80_data` e gira **dopo** `00_schema` — lasciare la pulizia
> solo al CSV avrebbe fatto fallire la `ALTER` al primo migrate, su ogni database
> che ha già la riga. Il changeSet se la toglie da solo, prima.

Registro **28 → 27**.

**✅ APPLICATO E VERIFICATO (2026-08-05).** `20260805-26` e `-28` sono `EXECUTED`,
guardrail verde — *«27 attive, 23 ritirati, nessun warning sollevato come
errore»* — e nessuna regressione nelle baseline degli schemi toccati.

### 15.16 Dove siamo, e cosa resta

| | 5 agosto, mattina | 5 agosto, sera |
|---|---:|---:|
| Codici fuori convenzione | **57** | **27** |
| di cui cancellati (morti) | — | 6 |
| di cui ritirati dopo rinomina | — | 23 |
| di cui riclassificati (`W_`) | — | 1 |

**−30 in una giornata**, e il registro può solo calare: il rubinetto è chiuso dal
controllo (B), il ritorno di un codice ritirato dal (D), e un warning sollevato
come errore dal (E).

I **27 che restano** erano classificati «accoppiati al backend» perché il Python
li riconosce dal testo. Se il BE ha davvero dichiarato **entrambi i nomi** per
tutti — come risulta dalla riga 17 del §9 — quell'accoppiamento **non c'è più**:
i lotti si aprono senza sincronia e senza preavviso, e il cantiere può arrivare a
**zero** invece di fermarsi a 27. Da verificare prima di aprire il lotto, con la
stessa misura del §15.11.

> **La cosa che vale oltre questo cantiere.** Tre presidi sono stati scritti in
> questa slice, e **tutti e tre sono diventati rossi almeno una volta su un
> difetto vero**, non su un caso di prova:
>
> * **(B)** ha trovato la riga con l'apostrofo nel codice, la prima volta che è girato;
> * **(D)** ha fermato un ritiro parziale — un codice sollevato da due funzioni, rinominato in una sola;
> * **(E)** ha dimostrato di reggere il buco che l'allargamento a `W_` apriva.
>
> Un presidio che non è mai stato rosso non si sa se funziona. Questi si sa.

### 15.17 `20260805-29` — l'ultimo lotto: il registro va da 57 a 1

26 codici, 28 funzioni. Sbloccato dalla chiusura del brief BE: l'accoppiamento
non è stato tolto allungando la lista ma **cambiando la condizione che la usa**
(`structured.removeprefix("E_") in _CODICI_DICHIARATI`). La lista è un
*perimetro*, non un elenco di stringhe esatte — ed è la ragione per cui l'ordine
di rilascio è diventato indifferente.

⚠️ **Corollario da tenere presente per sempre: la rinomina deve restare il solo
prefisso.** `ERRORE_PARAMETRI` diventa `E_ERRORE_PARAMETRI`, che è brutto —
«errore errore», senza modulo. Ribattezzarlo `E_PARAMETRI_NON_VALIDI` sarebbe uno
sbaglio **tecnico**, non di gusto: `removeprefix("E_")` darebbe un nome che il BE
non ha dichiarato, il campo strutturato verrebbe scartato e vincerebbe il marker,
restituendo il vecchio codice. La bruttezza si corregge dopo, come slice a sé e
con coordinamento.

> ⚠️ **Due esclusioni, per motivi diversi e convergenti.**
>
> `MESSAGGIO_NON_DEFINITO` **non è un errore di dominio**: è il segnaposto che
> `fn_log_error_only` scrive in `dbops.error_log` quando un codice non è a
> catalogo. Non arriva mai a un client — con un codice sconosciuto il campo
> `CONSTRAINT` porta comunque il codice *originale*, non questo. È un marcatore
> di log, stessa famiglia di `W_TXID_NOT_REGISTERED`.
>
> E c'è un secondo motivo, **indipendente e dirimente**: l'unica funzione che lo
> nomina è `script.fn_log_error_only`, di proprietà di **`postgres`** — mentre le
> altre 28 sono di `titodb`, l'utente con cui gira Liquibase. Il
> `CREATE OR REPLACE` falliva con *«bisogna essere proprietari»*, ed è così che è
> saltato fuori: **la simulazione ha trovato un vincolo di permessi che nessuna
> lettura del codice avrebbe mostrato.**
>
> Resta l'unica voce del registro. Proposta: rinominarlo
> `W_MESSAGGIO_NON_DEFINITO` — la famiglia dei warning ora esiste ed è presidiata
> dal controllo (E) — passando dal changelog di provision che gira come
> `postgres`; oppure lasciarlo, accettando che il registro si fermi a uno.

**Stato finale simulato:** *«1 attiva, 49 ritirati, nessun warning sollevato come
errore»*.

| | 5 agosto, mattina | 5 agosto, sera |
|---:|---:|---:|
| Codici fuori convenzione | **57** | **1** |
| cancellati (morti) | — | 6 |
| ritirati dopo rinomina | — | 49 |
| riclassificati (`W_`) | — | 1 |

### 15.18 Il seed che ci ha chiesto il BE

`E_TEMPLATE_CODICE_DUPLICATO` è dichiarato nei loro marker (mappa la violazione
di `uq_template_flussi_definizione_codice`) ma non era a catalogo. Seedato,
id 864.

Due precisazioni emerse verificandolo, entrambe utili a chi rileggerà:

* **non è un constraint, è un indice unico** — per questo `pg_constraint` non lo
  trova. Il marker del BE funziona lo stesso, perché il nome dell'indice compare
  nel testo del 23505;
* **oggi non degradava a `MESSAGGIO_NON_DEFINITO`**: nessuna funzione DB lo
  nomina e il backend non scrive in `dbops.error_log`. Lo scenario era teorico —
  il seed serve per completezza del catalogo, non a riparare un difetto in atto.

---

## 16. ✅ CHIUSO — 2026-08-05

Tutto ciò che questo brief chiedeva è fatto, applicato e verificato. Il campo
strutturato è in servizio, il registro del debito è passato da **57 a 1**, e il
contratto è presidiato da tre cancelli che girano a ogni PR.

| | Mattina | Sera |
|---|---:|---:|
| Codici fuori convenzione | **57** | **1** |
| cancellati perché morti | — | 6 |
| ritirati dopo rinomina | — | 49 |
| riclassificati (`W_` = warning) | — | 1 |
| Codici raggiungibili dal backend col loro nome | ~91% per caso | **100% per progetto** |

**ChangeSet:** `20260805-05..08`, `-11`, `-16..20`, `-25`, `-26`, `-28`, `-29`.
**pgTAP:** 13 asserzioni nuove sul campo strutturato + 4 su `obsoleto_dal`.
**Guardrail:** `scripts/sql/guardrail_codice_errore_strutturato.sql`, 5 controlli.

### Quello che vale oltre il cantiere

Tre presidi sono nati qui, e **tutti e tre sono diventati rossi almeno una volta
su un difetto vero**, non su un caso di prova:

| | Cosa ha preso |
|---|---|
| **(B)** rubinetto sui codici nuovi | la riga con l'apostrofo dentro il codice, al primo giro |
| **(D)** un codice ritirato non si solleva | un ritiro parziale: codice sollevato da due funzioni, rinominato in una sola |
| **(E)** un warning non si solleva | il buco che l'allargamento a `W_` avrebbe aperto |

Un presidio che non è mai stato rosso non si sa se funziona. Questi si sa.

E la simulazione in transazione annullata, prima di ogni apply, ha fermato tre
cose che nessuna rilettura del codice avrebbe mostrato: il `;` mancante dopo
`$function$`, il gemello `E_` già esistente col messaggio peggiore, e il vincolo
di **proprietà** su `fn_log_error_only` (di `postgres`, non dell'utente Liquibase).

### ⚠️ Se arrivi qui da un percorso che non esiste più

Quattordici changeSet applicati — `20260805-05, -06, -07, -08, -11, -16, -17,
-18, -19, -20, -25, -26, -28, -29` — citano questo brief al vecchio percorso
`docs/it/dev/work-in-progress/…`. Sono `runOnChange: false` e già `EXECUTED`:
correggerli romperebbe i checksum, quindi restano così. **Il file è qui, in
`work-done/`.** Non è un caso comune: succede quando un cantiere nasce e finisce
nello stesso giorno, e i changeSet vengono scritti mentre il brief è ancora
aperto.

### Cosa resta, e dove è finito

| | Dove |
|---|---|
| **Terzo lato del presidio** — ~141 codici `E_*` sollevati dal DB senza una voce in `error_policies.py`, 90 da trigger sul percorso richiesta | 🔴 **brief proprio**: [brief-db-be-terzo-lato-presidio-codici](brief-db-be-terzo-lato-presidio-codici.md) |
| `MESSAGGIO_NON_DEFINITO`: unica voce del registro. Rinominarlo `W_*` via changelog di provision (è di `postgres`), o lasciarlo | decisione, §15.17 |
| Pulizia BE: togliere le voci vecchie da `_KNOWN_DB_ERROR_MARKERS` e `error_policies.py`. **La condizione non va toccata** | BE, senza fretta |

⚠️ **Non droppare `dbops.messaggi_errore_codici_legacy`** anche se è quasi vuota:
finché esiste, il controllo (B) la legge e impedisce che un codice nuovo fuori
convenzione entri senza registrazione. È il rubinetto che ha reso possibile tutto
il resto.
