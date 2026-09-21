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
> **Stato:** 🔵 aperto, niente scritto. Prima misura in **§3** (datata
> 2026-09-19, criterio grezzo e dichiarato tale).
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
| Python | `ServiceError(code=…)` / `ErrorManager.require(…, "E_X", …)` / `raise_error(…)` | `context={"field": <nome>}` sulla stessa chiamata, **oppure** la chiamata passa da un BB che lo mette da sé: `PayloadValidator.*` (`field` sempre), `map_integrity_error` (terzo elemento della tupla), `create_with_constraint_mapping` |
| PL/pgSQL | `script.fn_log_and_raise_error(area, fn, 'E_X', context, …)` | `context ->> 'campo'` — che l'helper consegna come `COLUMN` e `diagnostica_db` legge; i corpi si leggono dalla doc auto-generata `dbzero` o da `pg_proc` sul DB provvisto |
| DB, per riflesso | i codici sollevati da `fn_raise_primo_motivo_se_presente` | il `campo` sta nel motivo che la `fn_check_*` emette |

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

Se il BE sceglie la seconda, il team DB la scrive nello stesso giro del
presidio C1 ([brief-db-presidio-stati-mai-scritti.md](../work-done/brief-db-presidio-stati-mai-scritti.md),
**chiuso lato DB il 21-09**): stessa famiglia di viste, stesso pgTAP trasversale.
⚠️ E in coda a questo brief sta la **richiesta BE §6 di C1**: il test gemello
sulle 26 righe `DICHIARATO_APPLICAZIONE` di `dbops.vw_stati_check_scrittori`
(il letterale in un `.py` non di test che nomina la tabella o uno scrittore),
nei due versi. Stessa forma, stessi strumenti, un solo giro.

---

## 5. Decisioni per Tid

1. **Il verso 2 si presidia o si dichiara?** Un codice `show_error_banner` che
   manda `fields` non fa danno a video (il campo si accende, il banner c'è):
   è una promessa che non decide, non una che mente. Proposta: si **misura** e
   si riporta, ma il cancello blocca solo sul verso 1.
2. **`E_ATTIVITA_VALIDATION`** (§3): l'unico codice vivo con la promessa e
   nessun mittente. Si ritira a catalogo (`obsoleto_dal`, team DB) o si cerca
   il mittente che manca? Proposta: si ritira — un registro che nasce con un
   codice morto dentro è già un elenco di eccezioni.
3. **Dove vive**: `apps/core/tests/` accanto ai fratelli (decisione 2
   dell'analisi, mai presa). Proposta: lì, con `# Scopo:` che nomina questo
   brief — la «cartella dei presidi del percorso storto» non serve finché
   sono due.

---

## 6. Cosa resta

* 🔵 il criterio pieno (§2.3), BB compresi, e la misura rifatta con quello;
* 🔵 ritirare (o dare un mittente a) `E_ATTIVITA_VALIDATION`;
* 🔵 il test in `apps/core/tests/test_ui_action_e_canale_campi.py`, col
  registro chiavato `(codice, verso)` e i due versi di ritiro;
* 🔵 la scelta del §4 e, se è la vista, la richiesta al team DB;
* 🔵 una riga in `api.md` §«Capability di riga» / §Envelope che nomini il
  presidio, e una in `dbops.presidi` (`CANCELLO`, se nasce la vista).
