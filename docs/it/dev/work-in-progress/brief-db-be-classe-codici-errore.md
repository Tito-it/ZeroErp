# Brief BE ↔ DB — dare al catalogo degli errori la cosa che gli manca: **cosa sono**

**Chi scrive:** proposta BE (`dev/backend-tid`, 2026-08-07), **rivista e integrata dal DB** (`dev/db-tid`, 2026-08-07).
**Origine:** domanda di Tid alla chiusura di
[brief-db-be-terzo-lato-presidio-codici](../work-done/brief-db-be-terzo-lato-presidio-codici.md):
*«come evitare che si ripeta? La messaggistica si era trasformata in un bugiardino.»*
**Stato:** 🟢 **disegno completo, nessuna decisione aperta** (10 decisioni, §14) — da costruire, si parte dal punto 2 del piano (§13).
**Perimetro:** tabelle + vocabolario + seed lato DB · lettura a runtime e mappa classe→HTTP lato BE.

> **Cosa è cambiato rispetto alla prima stesura (BE, mattina del 2026-08-07).**
> Il disegno regge, ma tre cose sono state riscritte dopo la revisione DB:
>
> 1. il **meccanismo anti-ricaduta dichiarato era sbagliato** — il brief prometteva
>    l'adiacenza fra classe e messaggio e poi le separava in due tabelle (§5);
> 2. mancava la domanda che decide se il secondo elenco sparisce davvero o cambia
>    solo indirizzo: **dove legge la classe il backend, a runtime** (§6);
> 3. il backfill **non è completo**: 659 classi su **692 codici**. Misurato (§7).
>
> Ed è emerso che l'idea **c'era già, due volte** — con esiti documentati che
> vanno letti prima di ricominciare (§2).
>
> **Aggiunto nel pomeriggio, rispondendo all'ultima domanda aperta (§7.1):** i
> tre codici «solo Python» non erano codici — un morto, un disallineamento di
> nome e un **avviso**. Il terzo ha aperto un buco nel vocabolario, chiuso con
> l'ottavo valore `AVVISO` (§4.2).

---

## 1. Il problema, in una riga

`config.messaggi_errore` dice **cosa scrivere** all'operatore (`messaggio`,
`causa`, `soluzione`). Non dice **che cosa è** l'errore.

Quel significato — «non esiste», «è in conflitto con lo stato», «non ti è
permesso», «hai sbagliato a compilare», «è un guasto» — oggi vive **soltanto** in
un dizionario Python
([`backend/apps/core/services/error_policies.py`](../../../../backend/apps/core/services/error_policies.py),
659 voci). Due elenchi separati che parlano della stessa cosa, tenuti allineati
da un presidio. Il presidio funziona; la domanda è perché ci siano due elenchi.

**Cosa è costato non averlo.** Tre giorni, 150 decisioni, e un difetto per ogni
famiglia: codici che dicevano «parametro non valido» su un `IF NOT FOUND`, un
`E_SNAPSHOT_ID_NOT_FOUND` che è un 500, un `E_STATO_SCONOSCIUTO` che conteneva
due errori diversi. Nessuno di questi era visibile guardando il catalogo, perché
**il catalogo non ha il campo dove la contraddizione si sarebbe vista**.

---

## 2. ⭐ Cosa c'era già — tre precedenti, e perché questo non è un doppione

Prima di costruire: la stessa intuizione è già stata tentata **due volte**, in
forme diverse, e in entrambi i casi c'è una ragione documentata per cui non ha
retto. Questa è la terza incarnazione, ed è quella giusta — ma solo se si sa
perché le prime due non lo erano.

### 2.1 La classe **dentro il nome del codice** — [api.md §Tassonomia errori](../api.md)

Era già lì, ed è viva ancora oggi:

| Suffisso | HTTP tipico |
|---|---|
| `_VALIDATION` / `_VALIDAZIONE` | 400 |
| `_NOT_FOUND` | 404 |
| `_DUPLICATO` / `_IN_ESECUZIONE` | 409 |
| `_NEGATO` / `_DENIED` | 403 |

Cioè esattamente *«il codice dichiara che cosa è»*, affidato alla convenzione di
naming. ⚠️ **Ed è già stato misurato come fallito**, dentro il cantiere che ha
generato questo brief: *«Il suffisso NON decide lo status: decide il punto che
solleva»*. Su 91 decisioni **il nome ha mentito tre volte**, in tre direzioni
diverse:

| Codice | Cosa suggerisce il nome | Cosa fa davvero | Status |
|---|---|---|---|
| `E_SNAPSHOT_ID_NOT_FOUND` | 404 | `EXCEPTION WHEN OTHERS` nella storicizzazione | **500** |
| `E_DELETE_NOT_ALLOWED` | 409 | blocca sempre, sbloccabile solo da GUC di sistema | **403** |
| `E_FULFILL_NOT_FOUND` | «manca un legame» | la riga indicata non esiste | **404** |

> **È l'argomento più forte di questo brief, ed è bene che sia il primo.** Non
> stiamo inventando una classificazione: stiamo togliendo quella che **esiste
> già** da dove non regge (una convenzione di naming, che mente il 3% delle
> volte e in silenzio) e mettendola dove regge (un dato, con un vincolo).

### 2.2 Lo **SQLSTATE custom** (classe `U0`) — scartato per un motivo che qui cade

[brief-db-codice-errore-strutturato §3 «Le alternative, e perché no»](../work-done/brief-db-codice-errore-strutturato.md)
lo aveva valutato e respinto:

> *«pulita, ma SQLSTATE è di 5 caratteri: servirebbe una mappa `codice →
> sqlstate` da mantenere allineata al seed. Un secondo posto da tenere in bolla,
> cioè il difetto da cui nasce tutto»*

⚠️ **Quell'obiezione si dissolve con questo brief**, e va detto perché altrimenti
qualcuno la riproporrà. Uccideva l'idea perché l'unità era il **codice**: 689
voci da mappare. Con la classe l'unità diventa la **classe**: sette valori.
`script.fn_log_and_raise_error` legge già la riga di catalogo per comporre il
messaggio — leggerne anche `classe` e sollevare con `ERRCODE = 'U0001'..'U0007'`
costerebbe zero, e il backend riceverebbe la semantica **dentro l'eccezione**,
senza nessun elenco da tenere allineato.

**Non si fa adesso**, e il raggio è misurato:

| Cosa attende `P0001` | Quanti |
|---|---|
| asserzioni pgTAP | **311**, in **108 file** |
| punti nel backend che citano `P0001` | ~20 |
| contratto in essere | *«`P0001` + `CONSTRAINT` valorizzato = errore di dominio»* — è la condizione su cui il BE decide se fidarsi del campo strutturato |

È un cantiere a sé, e forse non si farà mai. Resta scritto qui perché è la
risposta naturale alla domanda del §6, e perché il costo di riscoprirla da capo
è una settimana.

### 2.3 La regola del **denominatore sicuro** — già scritta, da citare e non riscrivere

[api.md](../api.md) contiene già la regola operativa per i codici a più
significati: *«lo status giusto è il denominatore sicuro, e il codice va
segnalato al team DB come candidato allo split»*, con il criterio di quando
spezzare (`E_STATO_SCONOSCIUTO` sì, `E_SOGGETTI_RUOLI` no). Il §9.3 di questo
brief **non la riformula**: la richiama.

---

## 3. La forma: due tabelle e un vocabolario

⚠️ **Non è «aggiungere una colonna a `messaggi_errore`»**, ed è il punto che va
capito per primo.

### 3.1 Perché non una colonna sul catalogo dei messaggi

`config.messaggi_errore` è chiavata **`(codice, lingua)`**. Misurato sul CSV vivo
il 2026-08-07: **690 righe per 689 codici**, e già oggi un codice ha due righe
(`E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA`, `it` + `en`). Mettere la classe
lì significherebbe **duplicarla per lingua**: la traduzione inglese potrebbe
dichiarare una classe diversa da quella italiana. Sarebbe la stessa voragine
appena chiusa, riaperta in un posto nuovo.

> ⚠️ **E non è un rischio teorico: c'è già una colonna che soffre di questo, ed è
> `obsoleto_dal`.** Sta su `messaggi_errore`, quindi è **per lingua**: oggi è
> possibile ritirare un codice in italiano e lasciarlo vivo in inglese.
> Misurato: **50 righe ritirate, tutte `it`**, e il codice bilingue non è fra
> loro. Non è ancora successo — ma la tabella lo consente, e il giorno in cui
> l'interfaccia inglese sarà davvero popolata succederà senza che nessuno se ne
> accorga.

**Il codice deve avere una sola identità. Le traduzioni sono quello che sono:
traduzioni.** La classe e il ritiro appartengono al codice, non alla frase.

### 3.2 `config.classi_errore` — un vocabolario, non un `CHECK`

Sette valori stabili, referenziati da una colonna `NOT NULL`. Il progetto per
questa forma usa **tabelle-vocabolario** (`config.iva_natura`,
`config.esiti_flussi_pratiche`, `config.nature_vendita`), non `CHECK` con lista
di letterali. Le ragioni, qui, sono tre:

1. la **descrizione della classe diventa un dato leggibile**, non un commento
   dentro un vincolo — ed è la definizione che decide le prossime classificazioni;
2. quando il BE leggerà le classi a runtime (§6) trova già dove leggerle;
3. aggiungere o ritirare una classe è un `INSERT` in un CSV, non un
   `ALTER TABLE ... DROP CONSTRAINT` + ricreazione.

⚠️ Non è un `attivo`: una classe non si disattiva. Se una classe va in disuso si
usa lo stesso asse del catalogo — `obsoleto_dal` — perché i codici che l'hanno
avuta devono continuare a risolvere.

### 3.3 Lo schema, per intero

```
config.classi_errore                        ← il vocabolario, 7 righe
  classe        text PK                     ← DATO_ERRATO, CONFLITTO_STATO, …
  descrizione   text NOT NULL               ← la definizione che decide i casi dubbi
  obsoleto_dal  date                        ← una classe si ritira, non si disattiva
  + audit (data_insert, user_insert, data_update, user_update, tx_id)

config.codici_errore                        ← una riga per CODICE — l'identità
  codice        text PK
  classe        text NOT NULL               ← FK → config.classi_errore(classe)
                                              ⛔ NESSUN DEFAULT (§5)
  obsoleto_dal  date                        ← SPOSTATO qui da messaggi_errore
  note          text                        ← perché questa classe, sui casi non ovvi
  + audit

config.messaggi_errore                      ← una riga per (codice, lingua) — la frase
  codice        text  → FK verso config.codici_errore(codice)
  lingua, messaggio, causa, soluzione
  id            bigint PK   (invariata — vedi 3.4)
  ⛔ obsoleto_dal RIMOSSA (migra su codici_errore)

config.vw_codici_errore                     ← la superficie di lettura (§5)
  codice · classe · obsoleto_dal · lingua · messaggio · causa · soluzione
```

### 3.4 ⚠️ Cosa **non** si tocca

`dbops.error_log` ha una FK verso `config.messaggi_errore(id)`. **Non va
toccata**, e la PK surrogata `id` resta dov'è: il diario continua a puntare alla
**riga tradotta** che l'operatore ha effettivamente letto, che è l'informazione
giusta da conservare. La classe si raggiunge con un join, non serve denormalizzarla.

Non si tocca nemmeno `script.fn_get_messaggio`: la risoluzione lingua con
fallback su `it` resta identica.

---

## 4. Il vocabolario — sette valori, e non sono inventati

Vengono dalle **659 decisioni già prese** nel cantiere del terzo/quarto lato, non
da un disegno a priori:

| `classe` | HTTP | Quando | Quanti oggi |
|---|---|---|---|
| `DATO_ERRATO` | 400 | la richiesta è malformata o il valore è sbagliato | 234 |
| `CONFLITTO_STATO` | 409 | in conflitto con lo stato attuale della risorsa | 224 |
| `NON_TROVATO` | 404 | la cosa indicata non esiste | 84 |
| `TECNICO` | 500 | guasto o pezzo non configurato: l'operatore non può farci niente | 63 |
| `NON_PERMESSO` | 403 | il diritto manca, e non dipende dallo stato | 23 |
| `NON_ESEGUIBILE` | 422 | si capisce ma non si può eseguire (configurazione che non regge a quella data) | 22 |
| `NON_DISPONIBILE` | 501 | funzione presente ma non servita (disattivata) | 4 |
| `AVVISO` | — | **non è un rifiuto**: è una nota nel diario, non raggiunge mai chi ha fatto la richiesta (§4.2) | 1 |

⚠️ **`AVVISO` è l'ottavo valore, ed è arrivato dopo** — non stava nella prima
stesura, è emerso rispondendo alla domanda aperta del §7. La sua ragione sta nel
§4.2 e va letta prima di considerarlo un riempitivo.

> Ricontato in modo indipendente lato DB: stessa graduatoria e stessi ordini di
> grandezza (400 ≥ 409 ≫ 404 > 500 > 403 > 422 > 501). Il riconteggio DB legge
> 627 dei 659 blocchi — perde quelli con commenti multi-riga fra le chiavi — e
> **non va usato per fissare i totali**: fa fede il conteggio BE. È la stessa
> trappola del §24.3 punto 5 del cantiere precedente: *anche la misura è un
> programma, e può avere il suo difetto*.

**Restano fuori due casi**, che non vanno nel vocabolario di dominio:

* **401** (autenticazione, 4 codici) — costruiti da `JwtAuditMiddleware`, non
  passano dall'exception handler;
* **502** (un provider esterno ha risposto male, 1 codice).

Vanno mappati a mano nel backend, e va bene: non sono errori che una funzione
PL/pgSQL solleva.

### 4.1 Le classi si distinguono **anche fra due `IF` adiacenti**

In `dbops.fn_accoda_lavoro`, `E_JOB_TYPE_NON_TROVATO` è `TECNICO` (nessuno può
rimediare finché qualcuno non configura) e `E_JOB_TYPE_NON_ATTIVO` è
`NON_DISPONIBILE` (il pezzo c'è, è spento). Il vocabolario deve reggere questa
distinzione, **e la regge**: è la prova che i valori non sono sinonimi mascherati.

### 4.2 ⭐ `AVVISO` — perché sette non bastavano, e non è un riempitivo

Le altre sette classi rispondono tutte alla **stessa domanda**: *«perché ti sto
rifiutando l'operazione?»*. Cambia solo il motivo del rifiuto.

Esiste però una famiglia che non rifiuta niente: i **warning**. Oggi ce n'è uno,
`W_TXID_NOT_REGISTERED`. La `W` è deliberata — il messaggio comincia con
«Warning - », `dbops.trgfn_tx_id_managed` lo passa a `fn_log_error_only`, cioè lo
**scrive nel diario e basta**, non lo solleva mai — e il **controllo (E)** del
guardrail è un cancello di CI che impedisce a chiunque di sollevarlo
(*«`E_` si solleva, `W_` si scrive nel log»*). La regola di naming è già
`^[EW]_`, allargata apposta nel cantiere precedente: *«la `W` non era un codice
storto, era un'altra famiglia»*.

⚠️ **E non lo si può lasciare fuori dalla tabella.** `W_TXID_NOT_REGISTERED` è
una riga di `config.messaggi_errore`; con la FK del §3.3 vuole per forza il suo
padre in `codici_errore`, e lì `classe NOT NULL` pretende un valore. Le strade
erano tre e due sono peggiori:

| Strada | Perché no |
|---|---|
| forzarlo su `TECNICO` | fa dire al dato una cosa falsa — che è un errore — **per far tornare un vincolo**. È esattamente ciò che il cantiere precedente si era rifiutato di fare rinominandolo `E_` |
| `classe` nullable per i warning | butta via il §5, che è tutto il brief |
| **una colonna `natura` (ERRORE/AVVISO) separata** | due assi dove ne basta uno: `AVVISO` non è un *tipo di rifiuto*, è l'assenza di rifiuto — sta bene sullo stesso asse |

`AVVISO` **non ha uno status HTTP**, e non è una lacuna della mappa del §6 (punto 4): un
avviso non raggiunge mai il client, e questo non è una speranza — è il controllo
(E) che lo garantisce. Se un giorno quel cancello cadesse, la classe `AVVISO`
senza status è ciò che fa fallire la traduzione in modo **rumoroso** invece di
mandare un 500 all'operatore.

---

## 5. ⭐ Il meccanismo anti-ricaduta: **non è l'adiacenza, è il `NOT NULL`**

⚠️ **Questa sezione corregge la prima stesura del brief**, che si contraddiceva —
e la contraddizione vale più della correzione, perché è lo stesso genere di
errore che il cantiere ha inseguito per tre giorni.

La prima stesura dichiarava come meccanismo l'**adiacenza**:

> *«la scrivi sulla stessa riga del messaggio: `classe = NON_TROVATO` accanto a
> "Parametro non valido" è una contraddizione che si vede a occhio nudo»*

Ma il §3 mette la classe in **un'altra tabella e in un altro CSV**. L'adiacenza
sparisce esattamente dove sarebbe servita: nel momento in cui si scrive. Chi
aggiunge un codice compila due file, e la contraddizione che «si vede a occhio
nudo» non è più in nessun campo visivo.

**Decisione (Tid, 2026-08-07): si tiene la separazione, e si cambia il
meccanismo dichiarato.** Sono due cose, e la seconda è quella che porta il peso.

### 5.1 Il meccanismo vero: un codice senza semantica **non può nascere**

`classe NOT NULL`, **senza `DEFAULT`**. È tutto qui, ed è più di quanto sembri.

⛔ **Niente `DEFAULT`, e la ragione va scritta nel changeSet.** Un default
significa *«se non ci pensi ne metto uno io»*, ed è **letteralmente il meccanismo
che ha prodotto il difetto**: `ErrorPolicyRegistry.resolve` ha un ripiego a 400
per i codici non registrati, ed è per quello che 659 codici avevano un 400 che
nessuno aveva deciso e nessuno vedeva. Un `DEFAULT 'DATO_ERRATO'` ricostruirebbe
la stessa trappola dentro il rimedio.

Con `NOT NULL` senza default, la sequenza cambia forma: oggi si può aggiungere un
codice al catalogo e **rimandare** la semantica (e rimandare significa che il
ripiego decide al posto tuo, in silenzio); domani l'`INSERT` non passa. La
decisione si sposta **nel momento in cui si ha in testa il ramo che solleva** —
che è l'unico momento in cui è facile.

### 5.2 La superficie di lettura: `config.vw_codici_errore`

L'adiacenza si perde in scrittura, **si recupera in revisione**. Una vista che
affianca classe, ritiro e testo:

```sql
SELECT c.codice, c.classe, c.obsoleto_dal, c.note,
       m.lingua, m.messaggio, m.causa, m.soluzione
  FROM config.codici_errore c
  LEFT JOIN config.messaggi_errore m ON m.codice = c.codice;
```

`LEFT JOIN` e non `JOIN`: un codice **può** esistere senza messaggio (§7), e la
vista deve mostrarlo, non nasconderlo — è anzi uno dei difetti che serve vedere.

⚠️ **La vista è per gli umani e per il BE, non è un cancello.** Serve a chi
rilegge un dominio, a chi apre un lotto di classificazione, e come sorgente della
lettura a runtime del §6. Chi cerca un cancello lo trova nel `NOT NULL`.

### 5.3 La lente resta una lente

[`scripts/sql/check_messaggio_vs_condizione.sql`](../../../../scripts/sql/check_messaggio_vs_condizione.sql)
può guadagnare un secondo verso — *la classe contraddice il testo del
messaggio?* — ora che ha una classe da confrontare. Ma resta quello che è:
**23% di precisione**, misurato. Utile all'apertura di un lotto, **mai** un
cancello. Chi la promuove a cancello la fa disattivare in una settimana, che è il
modo in cui i presidi muoiono.

---

## 6. ⭐ Dove il backend legge la classe, a runtime — **decisione: dal DB**

La prima stesura affermava: *«non c'è più un secondo elenco da cui divergere,
perché non c'è più un secondo elenco»*. ⚠️ **Vero solo per lo `http_status`.**
Resta la mappa **codice → classe**, 689 voci, e il BE deve poterla leggere quando
traduce un'eccezione. Se quella mappa resta in Python, il secondo elenco non è
sparito: ha cambiato contenuto.

Le tre strade, con le loro conseguenze:

| | Dove sta la mappa codice→classe | Il secondo elenco… |
|---|---|---|
| **a** | il BE la legge da `config.codici_errore` | **sparisce davvero** — il percorso d'errore acquista una dipendenza DB, da rendere fail-safe |
| **b** | modulo Python **generato** dal DB, allineamento presidiato in CI | resta, ma meccanico: è il cancello di oggi con un altro nome |
| **c** | la classe viaggia **nell'eccezione** (SQLSTATE per classe, §2.2) | sparisce, e non serve cache — ma 311 pgTAP da toccare |

**Decisione (Tid, 2026-08-07): strada (a).** È l'unica che rende il DB la
sorgente sola senza aprire il cantiere degli SQLSTATE. Il disegno:

1. **caricamento all'avvio** — `ErrorPolicyRegistry` popola la mappa
   `codice → classe` da `config.vw_codici_errore` (689 righe, una query);
2. **cache in processo**, invalidata al reload del processo. La tabella cambia
   solo per migrazione: non serve TTL né invalidazione attiva, e un TTL sarebbe
   una complicazione senza un problema;
3. ⚠️ **snapshot di ripiego committato** — un JSON/py generato, versionato nel
   repo, usato **solo** se il caricamento fallisce. Serve perché questa lettura
   sta sul **percorso d'errore**: un DB che non risponde mentre si traduce
   un'eccezione non deve produrre un secondo errore peggiore del primo. Il
   ripiego è vecchio ma coerente, e va **loggato in modo rumoroso** quando
   scatta, altrimenti diventa la nuova divergenza silenziosa;
4. **la mappa classe → HTTP resta lato BE**, sette righe scritte a mano. È
   trasporto, non dominio: il DB non deve sapere cosa sia un 409.

> ⚠️ **Lo snapshot di ripiego è un secondo elenco travestito, e va trattato come
> tale**: generato, mai scritto a mano, e con un controllo in CI che fallisce se
> diverge dal DB. Se lo si scrive a mano «tanto è solo un fallback», fra un anno
> è la sorgente vera e nessuno lo sa.

---

## 7. ⚠️ Il backfill **non** è completo — misurato, non dedotto

La prima stesura diceva: *«le 659 classi esistono già … nessuna decisione da
rifare»*. Confronto fra il CSV del catalogo e `error_policies.py`, 2026-08-07:

| | quanti |
|---:|---|
| codici a catalogo (`messaggi_errore.csv`) | **689** |
| policy dichiarate (`error_policies.py`) | **659** |
| **a catalogo ma SENZA policy** | **33** |
| di questi, già ritirati (`obsoleto_dal`) | **1** |
| **→ vivi, senza classe, che il `NOT NULL` bloccherà** | **32** |
| policy **senza** riga di catalogo (solo Python) | **3** |
| **universo reale dei codici** | **692** |

I 32 sono codici che **nessuna funzione viva solleva** — altrimenti sarebbero
nella vista `dbops.vw_codici_errore_da_dichiarare`, che il cantiere ha portato a
zero. Esempi: `E_STORICO_UPD`, `E_STORICO_DLT`, `E_TXID_DBLINK_ERROR`,
`E_TXID_DBLINK_NULL`, `E_BOM_VERSIONE_OVERLAP`, `E_COMPETENZA`,
`E_REFRESH_LOCK_TIMEOUT`, `E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI` (quest'ultimo
già ritirato lato policy nel cantiere satelliti fattura, ma vivo a catalogo).

⭐ **Questo è un argomento a favore, non contro.** Sono 32 codici che oggi non
guarda nessuno da nessun lato: non hanno una policy perché non li solleva
nessuno, e non risultano morti perché il catalogo non ha un campo che lo dica. Il
`NOT NULL` li fa emergere il primo giorno. Ma vanno messi in conto come **32
decisioni residue**, non scoperti a lavoro iniziato:

* per ognuno, la scelta vera è **classificare** oppure **ritirare**
  (`obsoleto_dal`) — e per la maggior parte sarà la seconda;
* la classe di un codice ritirato è **quella che aveva quando era vivo**: il
  diario deve continuare a risolvere.

### 7.1 ✅ I «3 solo-Python» — la domanda di perimetro si scioglie da sola

Era l'unica decisione rimasta aperta: *«`config.codici_errore` è il catalogo dei
codici che il DB può nominare, o di **tutti** i codici dell'applicazione?»*

**Risposta (verificata sui tre, 2026-08-07): è già il catalogo di tutti.** Dei
**659** codici che il backend dichiara, **656 hanno già la loro riga nel catalogo
DB**. Nessuno l'ha mai deciso: è successo, perché chi aggiungeva un codice lo
scriveva in tutti e due i posti. Non stiamo scegliendo fra due strade — stiamo
mettendo per iscritto quella che percorriamo già da sempre.

⭐ **E i tre «solo-Python» non sono tre codici: sono tre residui, uno per tipo.**
Aperti uno per uno, nessuno è un codice che vive soltanto in Python:

| Codice in `error_policies.py` | Cos'è davvero | Cosa serve |
|---|---|---|
| `PREV_STATO_NON_MODIFICABILE` | **un morto**. Il gemello vivo `E_PREV_STATO_NON_MODIFICABILE` è a catalogo (id 714); quello senza prefisso il DB l'ha **cancellato il 2026-08-05** (`20260805-16`, «doppione superato»). La riga Python è rimasta orfana | **BE**: togliere la voce. Una riga |
| `MESSAGGIO_NON_DEFINITO` | **un codice con due nomi**: a catalogo senza prefisso (id 14), in Python con la `E_`. È il segnaposto che il DB usa quando un messaggio manca. ⭐ È **l'ultima riga rimasta** del registro dei codici fuori convenzione (57 → 1, `dbops.messaggi_errore_codici_legacy`): debito **già noto e già tracciato** | **DB**: coda di quel registro, non di questo cantiere. ⚠️ non è gratis (sotto) |
| `W_TXID_NOT_REGISTERED` | **non è un errore, è un avviso** — la `W` è deliberata, il DB lo scrive nel diario e non lo solleva mai (§4.2) | **DB**: gli serve la classe `AVVISO`, l'ottavo valore |

⚠️ **`MESSAGGIO_NON_DEFINITO` non si rinomina con una riga di CSV.** Due funzioni
lo cercano **per nome scritto a mano** — `script.fn_log_error_only` fa
`WHERE codice = 'MESSAGGIO_NON_DEFINITO'` per recuperare l'`id` di ripiego
(`20260304-18`, `20260803-11`). Rinominarlo senza toccarle significa che il
ripiego del ripiego smette di risolvere, **e si vede solo quando serve** — cioè
il giorno in cui manca un messaggio a catalogo, che è il peggiore per scoprire un
guasto. Va fatto come slice sua, con le funzioni nello stesso changeSet.

**Conseguenza sul perimetro:** `config.codici_errore` accoglie **tutti** i codici,
e la domanda del §13 punto 1 è chiusa. Non serve nessuna eccezione per il
backend, perché non c'era nessun codice solo-suo: c'erano un morto, un
disallineamento di nome e un avviso.

---

## 8. Cosa cambia lato BE

* lo **`http_status` si deriva dalla classe**: da 659 righe scritte a mano a
  **sette**. Non c'è più un secondo elenco *di status*, e con la strada (a) del
  §6 non c'è più nemmeno un secondo elenco *di classi*;
* **`ui_action` resta per codice** — non è derivabile. Misurato sul dizionario
  (627 blocchi letti su 659, proporzioni stabili):

  | classe (status) | valore dominante | override che restano |
  |---|---|---|
  | `DATO_ERRATO` (400) | `highlight_form_fields` — 111 | **108** |
  | `CONFLITTO_STATO` (409) | `show_error_banner` — 200 | 19 |
  | `NON_TROVATO` (404) | `show_empty_state` — 47 | **34** |
  | `TECNICO` (500) | `show_error_banner` — 59 | 1 |
  | `NON_ESEGUIBILE` (422) | `show_error_banner` — 17 | 2 |
  | `NON_PERMESSO` (403) | `show_error_banner` — 22 | 0 |

  ⚠️ **«Default per classe con override» vale, ma gli override restano ~163, non
  una manciata**: sul 400 la spaccatura è quasi a metà (banner o campo
  evidenziato dipende da *dove* manca il dato — sul form o sull'entità
  collegata), e lì il default in pratica non esiste. Da 659 a ~163 è comunque un
  guadagno secco, ma il numero va scritto ora invece di scoprirlo a metà lavoro;
* il cancello `test_error_codes_db_policy_guardrail` **resta**, e cambia
  mestiere: da unico presidio a rete di sicurezza. Con `classe NOT NULL` un
  codice senza semantica non può proprio nascere;
* **si aggiunge un controllo**: lo snapshot di ripiego (§6.3) non deve divergere
  dal DB.

---

## 9. Cosa **NON** risolve — detto prima, non dopo

1. **Una classe sbagliata scelta alla creazione resta possibile.** Ma la scegli
   **una volta**, nel momento in cui hai in testa il ramo che solleva, e la
   sbagli in modo *visibile*: `classe = NON_TROVATO` su un codice il cui
   messaggio dice «Parametro non valido» è una contraddizione che la vista del
   §5.2 mostra a chiunque rilegga il dominio. Prima non era sbagliabile in modo
   visibile: era **non decidibile affatto**.
2. **Il legame messaggio ↔ condizione resta umano.** Misurato: la migliore
   euristica dà **23% di precisione**, inservibile come cancello. La classe lo
   *riduce* dando alla lente un secondo termine di confronto, non lo elimina.
3. **I codici a più significati vanno comunque decisi.** `classe NOT NULL` ti
   obbliga a scegliere il **denominatore sicuro** — che è ciò che si è fatto per
   `E_SOGGETTI_RUOLI` — e rende la scelta **visibile** invece che implicita. Il
   criterio è già scritto in [api.md](../api.md) (§2.3): non va riformulato.
4. ⚠️ **I due accumulatori non si curano con una classe.**
   `E_PARAMETRO_INVALIDO` è nominato da **113 funzioni**, `E_VALIDAZIONE` da 10.
   Con `classe NOT NULL` prenderebbero la classe del loro uso più comune e
   continuerebbero a mentire sugli altri. **La classe non cura i generici:
   quelli si spezzano.** In coda a questo lavoro vale una regola che vieta
   **nuovi** codici generici — come si è fatto per i codici fuori convenzione,
   chiudendo il rubinetto invece di rincorrere gli esistenti.
5. **La classe è una proprietà del codice, non del punto che solleva.** È il
   limite strutturale del disegno, ed è accettato: la garanzia che compra è
   *«ogni codice ha una semantica dichiarata»*, non *«ogni sollevamento ha la
   semantica giusta»*. La seconda non è ottenibile da una tabella — si ottiene
   leggendo la funzione, che è quello che il cantiere ha fatto 150 volte.

---

## 10. ⚠️ Trappole di applicazione — lato DB

### 10.1 🔴 L'ordine Liquibase fa fallire questo disegno **in CI e non su dev**

In [`changelog-master-v2.yaml`](../../../../db/changelog/changelog-master-v2.yaml)
**tutto `00_schema` gira prima di tutto `80_data`** (l'autogen è incluso per
primo, poi gli `includeAll` di `80_data`/`85_pgagent`/`90_end`).

Conseguenza, se si procede nel modo ovvio:

1. la FK `messaggi_errore.codice → codici_errore.codice` nasce in `00_schema`;
2. il mirror del catalogo è
   [`20260614-08`](../../../../db/changelog/migrations_v2/80_data/changelog/20260614-08-upsert-messaggi-errore-chiusura-flusso-prematuro-mctit.yaml),
   e un loader nuovo avrà data `2026-08-xx`, quindi gira **dopo**;
3. su un DB **ricostruito da zero** il catalogo si carica prima che
   `codici_errore` esista popolata → **violazione di FK**.

⚠️ **Su dev non si vede**: il catalogo è già popolato e la FK trova i padri. È
esattamente la trappola *«il DB di sviluppo NON è un DB ricostruito da zero»*: si
scopre in CI, in una PR che sembrava pronta.

**Rimedio pulito — estendere `20260614-08` in place**, aggiungendo un secondo
`loadUpdateData` su `codici_errore.csv` **prima** di quello del catalogo, nello
stesso changeSet:

* il changeSet è `runOnChange: true` + `validCheckSums: ANY`, cioè un **mirror
  vivo**: estenderlo in place è lecito e previsto, e il file stesso lo documenta
  («una colonna non elencata in `columns:` non verrebbe mai toccata dal loader,
  quindi va aggiunta qui, non gestita con changeSet SQL paralleli») — è già
  successo per `obsoleto_dal`;
* un solo changeSet = una sola transazione = ordine garantito, senza
  ri-ancoraggi;
* il DDL delle tabelle resta dove deve stare, in `00_schema`.

Il vocabolario `classi_errore` (7 righe) può stare nello stesso changeSet, prima
di tutto, oppure in un `insertData` dentro `00_schema` — è un enum, non un seed
che cambia.

> **Alternativa scartata:** creare la FK in un changeSet successivo ai due
> mirror. Funziona, ma sposta DDL fuori da `00_schema` per una ragione di
> ordinamento, e la prossima persona non capirà perché.

### 10.2 Lo spostamento di `obsoleto_dal` ha **cinque lettori**

Tutti da riscrivere nello stesso giro, altrimenti il presidio del ritiro smette
di funzionare in silenzio — che è il difetto che stiamo curando:

| Dove | Cosa |
|---|---|
| [`guardrail_codice_errore_strutturato.sql`](../../../../scripts/sql/guardrail_codice_errore_strutturato.sql) riga ~137 | controllo **C** |
| idem, righe ~165-185 | controllo **D** (codice ritirato ancora sollevato) |
| idem, righe ~219-232 | controllo **E** + testo del messaggio d'errore |
| idem, riga ~271 | esclusione dei ritirati |
| [`check_messaggio_vs_condizione.sql`](../../../../scripts/sql/check_messaggio_vs_condizione.sql) riga ~100 | la lente |

✅ **Lato BE nessun impatto su questo fronte**: `config.messaggi_errore` non è fra
le lookup generiche di `dbops_repository` (`_LOOKUP_SPECIALIZZATE`), quindi il
filtro `includi_obsoleti` dell'API di catalogo non la tocca. Verificato.

### 10.3 Quattro file pgTAP inseriscono direttamente nel catalogo

Con la FK vogliono un padre in `config.codici_errore`. È l'unico rosso **certo**
della slice, ed è meglio elencarlo che scoprirlo:

* [`test-messaggi-errore-obsoleto-dal.sql`](../../../../db/pgtap/script/test-messaggi-errore-obsoleto-dal.sql)
  — ⚠️ questo va **riscritto**, non adattato: verifica una colonna che cambia casa;
* [`test-fn-log-and-raise-error-fallback-lingua.sql`](../../../../db/pgtap/script/test-fn-log-and-raise-error-fallback-lingua.sql)
* [`test-fn-log-and-raise-error-constraint-codice.sql`](../../../../db/pgtap/script/test-fn-log-and-raise-error-constraint-codice.sql)
* [`test-fn-get-messaggio-fallback-lingua.sql`](../../../../db/pgtap/script/test-fn-get-messaggio-fallback-lingua.sql)

### 10.4 Le automazioni non arrivano subito

Tabelle nuove: audit/`tx_id`/storico li provvedono le automazioni, che girano
solo in contesto `ci_apply` (sul migrate manuale arrivano col pgagent di fine
giornata). Non è un problema, è da sapere quando si controlla il risultato la
sera stessa.

---

## 11. ⚠️ L'altro elenco duplicato, che questo brief **non** chiude

Se la domanda di partenza è *«perché ci sono due elenchi che parlano della stessa
cosa»*, allora va detto che ce n'è un secondo, ed è più grosso della classe:

**`user_message`** — 659 stringhe italiane dentro `error_policies.py`, lette da
`error_translator` (`policy.user_message` quando l'errore è tecnico) e da
`error_responses`. Duplicano `config.messaggi_errore.messaggio`.

E soffrono della malattia **rovesciata** rispetto a `obsoleto_dal`: sono
**monolingue** mentre il catalogo è multilingua. Un operatore con interfaccia
inglese, su un errore tecnico, legge italiano.

**Non si risolve qui** — è un cantiere suo, e va valutato se quelle 659 stringhe
siano davvero un duplicato o un ripiego deliberato per il caso in cui il catalogo
non risponde (che è la stessa domanda dello snapshot del §6.3, e forse la stessa
risposta). Sta scritto perché **senza questo paragrafo il brief sembrerebbe aver
chiuso una cosa che ha chiuso a metà**.

---

## 12. ⭐ Il consumatore in più: l'osservabilità

Argomento **lato DB** per una colonna **DB**, che la prima stesura non faceva.

Con `classe` a catalogo, `dbops.error_log` può finalmente distinguere il **guasto**
dal **rifiuto legittimo**. Oggi non può: un 500 tecnico e un «non puoi annullare
un ordine con DDT» sono la stessa riga con testo diverso.

Sono due buchi aperti di
[analisi-osservabilita-log](analisi-osservabilita-log.md):

* **B1** — *«il 67% di `error_log` non è attribuibile: qualunque strumento di
  consultazione mostra soprattutto rumore»*. Filtrare per `classe = 'TECNICO'`
  toglie il rumore alla radice, perché il rumore **sono** i rifiuti legittimi;
* **B7** — *«un lotto fermo in errore resta invisibile finché qualcuno non
  guarda»*. Un alert ha bisogno di un predicato: `classe = 'TECNICO'` è il primo
  predicato sensato che questo progetto possa scrivere.

Non è lavoro di questo brief. È la ragione per cui la classe **appartiene al DB**
e non è una gentilezza fatta al backend.

---

## 13. Il piano, in ordine

L'ordine è per **dipendenza**, non per dimensione.

| # | Cosa | Chi | Note |
|---|---|---|---|
| 1 | ~~Decidere il perimetro dei 3 codici solo-Python~~ | ~~Tid~~ | ✅ **chiuso** (§7.1): il catalogo è di **tutti** i codici, e i tre non erano codici |
| 2 | `config.classi_errore` (**8 valori**, `AVVISO` incluso) + `config.codici_errore` (`00_schema`) — `classe NOT NULL` **senza DEFAULT**, FK, audit | DB | |
| 3 | Il BE genera il CSV `codice,classe` da `error_policies.py` | BE | 659 righe su 692; **escludendo `PREV_STATO_NON_MODIFICABILE`**, che è morto (§7.1) |
| 4 | **Le 32 decisioni residue** (§7): classificare o ritirare | Tid + DB | leggendo il punto che solleva, o constatando che non c'è |
| 5 | Seed: `classi_errore` + `codici_errore.csv`, **dentro `20260614-08` prima del catalogo** (§10.1) | DB | ⚠️ è il passo che rompe la CI se fatto nel modo ovvio |
| 6 | Migrazione `obsoleto_dal`: colonna nuova popolata, poi `DROP` sulla vecchia | DB | forward-only, breaking secco: non siamo in produzione |
| 7 | FK `messaggi_errore.codice → codici_errore.codice` | DB | dopo che il seed regge |
| 8 | Riscrivere i **5 lettori** di `obsoleto_dal` (§10.2) | DB | stesso giro del punto 6 |
| 9 | Adeguare i **4 pgTAP** (§10.3) + nuovo test sul `NOT NULL` e sulla FK | DB | |
| 10 | Vista `config.vw_codici_errore` (`20_code`) | DB | ⚠️ numerazione **più alta** di chi la dipende |
| 11 | Lettura a runtime + snapshot di ripiego + controllo di divergenza | BE | §6 |
| 12 | `http_status` derivato dalla classe; `ui_action` a default+override | BE | ~163 override restano |
| 13 | Regola «niente nuovi codici generici» | BE + DB | §9.4, coda del lavoro |

**Punto di non ritorno:** il 6. Fino al 5 tutto è additivo e reversibile; dal 6 il
catalogo cambia forma e i lettori vanno con lui.

### 13.1 Fuori piano, ma nate qui — due code da non perdere

Non bloccano niente e non entrano nel piano, ma sono l'unico posto in cui
risultano scritte:

* **`PREV_STATO_NON_MODIFICABILE` da togliere** da `error_policies.py`: è una
  policy orfana di un codice che il DB ha cancellato il 2026-08-05 (§7.1).
  ⚠️ *Perimetro BE* — richiesta al team BE, una riga;
* **`MESSAGGIO_NON_DEFINITO` → `E_MESSAGGIO_NON_DEFINITO`**: chiude il registro
  `dbops.messaggi_errore_codici_legacy` (**1 → 0**, e a zero la tabella si
  droppa). Slice sua, perché `script.fn_log_error_only` cerca quel codice per
  nome scritto a mano: le funzioni vanno nello stesso changeSet (§7.1).

---

## 14. Decisioni prese, con data

| # | Decisione | Chi, quando |
|---|---|---|
| D1 | **Tabella separata** `config.codici_errore`, non una colonna su `messaggi_errore` | Tid, 2026-08-07 |
| D2 | `classe` con **FK a un vocabolario** `config.classi_errore`, non un `CHECK` | DB, 2026-08-07 |
| D3 | Il **vocabolario del §4** si adotta così com'è | Tid, 2026-08-07 |
| D4 | La mappa **classe → HTTP resta lato BE**: è trasporto, non dominio | Tid, 2026-08-07 |
| D5 | Il meccanismo anti-ricaduta è il **`NOT NULL` senza `DEFAULT`**, con la **vista** come superficie di revisione — **non** l'adiacenza | Tid, 2026-08-07 (§5) |
| D6 | Il BE legge la classe **dal DB a runtime** (strada *a*), con snapshot di ripiego committato e generato | Tid, 2026-08-07 (§6) |
| D7 | `obsoleto_dal` **migra** su `codici_errore`: il ritiro appartiene al codice, non alla frase | Tid, 2026-08-07 |
| D8 | Lo **SQLSTATE per classe** (§2.2) non si fa ora — 311 pgTAP — ma resta scritto | DB, 2026-08-07 |
| D9 | `config.codici_errore` è il catalogo di **tutti** i codici — non serviva scegliere: **656 su 659** ci sono già (§7.1) | Tid, 2026-08-07 |
| D10 | **Ottavo valore `AVVISO`** per la famiglia `W_`: un avviso non è un rifiuto, e senza di lui la FK non ha padre (§4.2) | DB, 2026-08-07 |

✅ **Nessuna decisione aperta.** Il disegno è completo: si può cominciare dal
punto 2 del piano.

---

## 15. Riferimenti

* [brief-db-be-terzo-lato-presidio-codici](../work-done/brief-db-be-terzo-lato-presidio-codici.md)
  — il cantiere da cui nasce la domanda; §24.3 e §28.3 per le lezioni residue
* [brief-db-codice-errore-strutturato](../work-done/brief-db-codice-errore-strutturato.md)
  §3 — le alternative già pesate, incluso lo SQLSTATE custom
* [api.md](../api.md) — §Tassonomia errori, gli status in uso, il denominatore sicuro
* [Presidi e registri del debito](../../guide/presidi-e-registri-del-debito.md) §3.3
* [analisi-osservabilita-log](analisi-osservabilita-log.md) — B1 e B7, §12
* [`scripts/sql/guardrail_codice_errore_strutturato.sql`](../../../../scripts/sql/guardrail_codice_errore_strutturato.sql)
  — i controlli in servizio
* [`scripts/sql/check_messaggio_vs_condizione.sql`](../../../../scripts/sql/check_messaggio_vs_condizione.sql)
  — la lente del quarto lato
