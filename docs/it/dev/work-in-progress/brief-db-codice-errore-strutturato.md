# Brief DB — far arrivare il codice errore di dominio al backend

**Chi scrive:** backend (`dev/backend-tid`), 2026-08-05.
**Cosa chiede:** una riga in `script.fn_log_and_raise_error` — il codice errore
viaggia in un campo strutturato dell'eccezione invece di essere ripescato dal
testo.
**Origine:** [brief-be-bonifica-riferimenti-morti](brief-be-bonifica-riferimenti-morti.md) §5,
che nasce da [brief-db-bonifica-riferimenti-morti](brief-db-bonifica-riferimenti-morti.md).
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
> **34 e non 57** (23 c'erano già, e trascriverli tutti creava chiavi duplicate
> che in Python vincono in silenzio), e i punti di innesto erano **4 e non 3** —
> il quarto è `pratiche_service`, dove il match avveniva su **frammenti di
> messaggio in italiano**. Test: 11 verdi, di cui 3 end-to-end su DB reale.
>
> 🔴 **Resta aperto, fuori slice:** 133 codici `E_*` sollevati dal DB non sono
> dichiarati in `error_policies.py` (83 da trigger agganciate). Non è una
> regressione: manca il **terzo lato** del presidio — codici sollevati dal DB vs
> `error_policies.py`, l'unica direzione che nessuno guarda (§12.4).

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

| | Cosa arriva al translator | Policy | HTTP |
|---|---|---|---|
| **Oggi** | la regex non trova il codice → ripiego `E_DATABASE` | **registrata** | **400** |
| **Dopo l'adozione BE** | arriva `PRATICHE_TRANSIZIONE_NON_AMMESSA` | non registrata, e la scorciatoia di `resolve()` è solo per `E_` → `E_GENERICO` | **500** |

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
| 6 | Registrare i 57 codici senza prefisso in `error_policies.py` | BE | ✅ **fatto** — 34 nuovi, 23 c'erano già (§12) |
| 7 | Presidio del contratto + rubinetto sui codici nuovi + registro del debito | DB | ✅ **fatto** — `20260805-06/-07` + guardrail (§10) |
| 8 | Riga morta `E_NOTE_RIGA_MISMATCH'` (CSV riga 88 + DELETE) | DB | ✅ **fatto** — `20260805-08` (§7) |

**Ordine obbligato:** ~~1 → 2 → 7~~ (fatto: tutto DB, applicato da solo, nessuna
finestra di rottura) · **resta 6 → 3** (BE, in quest'ordine e non nell'altro,
altrimenti 77 call site passano da 400 a 500).

### Cosa trova il BE già pronto

| | |
| --- | --- |
| Il campo | `diag.constraint_name` su `SQLSTATE = 'P0001'`, applicato e asserito |
| ⚠️ Campo vuoto ≠ NULL | quando il codice viene da un'espressione che vale NULL, arriva **stringa vuota**: `... or None` non è cosmetico |
| ⚠️ Il ripiego resta | 135 `RAISE EXCEPTION` diretti in 46 funzioni non passano dall'helper: per quelle il campo è vuoto e la regex è ancora l'unica strada |
| I 57 codici da registrare | elenco vivo: `SELECT codice FROM dbops.messaggi_errore_codici_legacy ORDER BY 1` |

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

### 12.1 I codici (#6): erano 34, non 57

**23 dei 57 erano già registrati.** Il brief li dava tutti da fare, e presi alla
lettera producono **chiavi duplicate** nel dizionario di `error_policies.py` —
che in Python non è un errore: l'ultima vince, in silenzio. In cinque casi la
copia nuova aveva uno status **diverso** dalla voce storica, e uno di quei
cinque (`FLUSSI_ESITO_OBBLIGATORIO`, da 409 a 400) ha fatto diventare rosso
`test_workflow_guard_codes_hanno_policy_409` — un test che quegli status li
aveva già fissati e che ha fatto esattamente il suo lavoro.

Conservate **sempre** le voci preesistenti: sono il contratto in uso, e cambiare
lo status di endpoint già in esercizio non era in perimetro. I 34 nuovi seguono
la tassonomia di `api.md` letta **sul messaggio a seed, non sul nome** — un
codice che si chiama `..._NON_AMMESSO` può essere un 409 (stato) o un 400
(valore fuori dominio), e la differenza sta nel messaggio.

| Status | Voci | Criterio |
|---|---:|---|
| 409 | 30 | conflitto con lo stato corrente: transizioni, immutabilità, «già esistente», precondizioni di emissione |
| 400 | 20 | input non valido o incoerente, validazioni di campo, progettazione degli step template |
| 404 | 3 | non trovato |
| 403 | 2 | operatore non abilitato |
| 500 | 3 | configurazione di sistema: non è l'utente a sbagliare |
| 422 | 1 | voce storica preesistente, non toccata |

Verifica: i 57 di `dbops.messaggi_errore_codici_legacy` risolvono tutti a una
policy registrata, **nessuno** cade più su `E_GENERICO`; e nel registro non c'è
**nessuna chiave duplicata** (464 voci, 464 distinte).

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

### 12.4 Cosa resta aperto, e non è di questa slice

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
