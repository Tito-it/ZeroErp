# Brief BE ↔ DB — dare al catalogo degli errori la cosa che gli manca: **cosa sono**

**Chi scrive:** proposta BE (`dev/backend-tid`, 2026-08-07), **rivista e integrata dal DB** (`dev/db-tid`, 2026-08-07).
**Origine:** domanda di Tid alla chiusura di
[brief-db-be-terzo-lato-presidio-codici](../work-done/brief-db-be-terzo-lato-presidio-codici.md):
*«come evitare che si ripeta? La messaggistica si era trasformata in un bugiardino.»*
**Stato:** 🟢 **disegno chiuso** — 19 decisioni (§14), nessuna aperta. **L'esecuzione è in due piani separati** (§13): si comincia dal [piano DB](piano-db-classe-codici-errore.md).
**Perimetro:** tabelle + vocabolario + seed lato DB · generatore di `error_policies.py` e mappa classe→HTTP lato BE.
**Ruolo di questo file:** **guida generale** — le ragioni, le misure, le decisioni. L'esecuzione sta nei due piani operativi (§13).

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
> **Aggiunto nel pomeriggio, rispondendo all'ultima domanda aperta (§7.2):** i
> tre codici «solo Python» non erano codici — un morto, un disallineamento di
> nome e un **avviso**. Il terzo ha aperto un buco nel vocabolario, chiuso con
> l'ottavo valore `AVVISO` (§4.2).
>
> **E sei annotazioni del BE (A1-A6), tutte accolte**, di cui due hanno corretto
> il DB su cose **già scritte come verificate**:
>
> * ⚠️ **la decisione del §6 è ribaltata**: non lettura a runtime, ma
>   `error_policies.py` **generato** — la (a) era la (b) con tre pezzi in più, e
>   il registro DB-dipendente violava «i test girano senza DB» (§6.1);
> * ⚠️ **la tabella `ui_action` del §8 era sbagliata e ribaltava la conclusione**:
>   su `DATO_ERRATO` non è «quasi a metà», è **117 contro 117** (§8);
> * ⚠️ **`AVVISO` non «fallisce rumorosamente»**: `resolve()` non fallisce mai, e
>   per un `W_` ripiega su **500** (§4.2);
> * gli **accumulatori** salgono nel piano: `E_VALIDAZIONE` si spezza **prima**
>   del seed (§9.1);
> * il discriminante *superato / non-agganciato* diventa **misurabile** (§7.1);
> * e resta scritto che **nessuno presidia che la classe resti vera** (§9.2).
>
> **Sera dello stesso giorno — il BE chiude l'ultima decisione, e ne corregge una
> terza:** `user_message` **non duplica** il catalogo, è la variante senza
> segnaposto (**0 su 656** contengono `%s`, contro 371 a catalogo). Il §11 diceva
> il contrario. La forma scelta è a **quattro moduli**, separati per *quando
> cambiano* (§14.2), e il contratto del generatore è nel §14.4.

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
voci da mappare. Con la classe l'unità diventa la **classe**: otto valori.
`script.fn_log_and_raise_error` legge già la riga di catalogo per comporre il
messaggio — leggerne anche `classe` e sollevare con `ERRCODE = 'U0001'..'U0008'`
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
spezzare (`E_STATO_SCONOSCIUTO` sì, `E_SOGGETTI_RUOLI` no). Il punto 3 del §9 di questo
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

Otto valori stabili, referenziati da una colonna `NOT NULL`. Il progetto per
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
config.classi_errore                        ← il vocabolario, 8 righe
  classe        text PK                     ← DATO_ERRATO, CONFLITTO_STATO, …
  descrizione   text NOT NULL               ← la definizione che decide i casi dubbi
  obsoleto_dal  date                        ← una classe si ritira, non si disattiva
  + audit (data_insert, user_insert, data_update, user_update, tx_id)

config.codici_errore                        ← una riga per CODICE — l'identità
  codice        text PK                     ← ~689 righe (vedi 3.5)
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

config.vw_codici_errore                     ← la superficie di REVISIONE (§5)
  codice · classe · obsoleto_dal · lingua · messaggio · causa · soluzione
  ⚠️ una riga per (codice, lingua) — LEFT JOIN: un codice senza messaggio c'e'

config.vw_codici_errore_identita            ← la sorgente del GENERATORE (§14.4)
  codice · classe · obsoleto_dal · note
  una riga per codice, nessun join, ORDER BY codice stabile
```

⚠️ **Due viste e non una, e la ragione è nel numero di righe.** Quella di
revisione affianca la frase, quindi moltiplica per lingua; il generatore vuole
**una riga per codice** e non deve vedere le traduzioni. Usare la prima per
entrambi significa filtrare per lingua — e il filtro perderebbe proprio i codici
**senza** messaggio, che sono quelli che più servono vedere.

### 3.4 ⚠️ Cosa **non** si tocca

`dbops.error_log` ha una FK verso `config.messaggi_errore(id)`. **Non va
toccata**, e la PK surrogata `id` resta dov'è: il diario continua a puntare alla
**riga tradotta** che l'operatore ha effettivamente letto, che è l'informazione
giusta da conservare. La classe si raggiunge con un join, non serve denormalizzarla.

Non si tocca nemmeno `script.fn_get_messaggio`: la risoluzione lingua con
fallback su `it` resta identica.

### 3.5 ✅ La chiave è **lo stesso codice**, e la stringa regge il vincolo

Domanda di Tid (2026-08-07): *il `codice` di `messaggi_errore` è lo stesso che
useremo nella tabella nuova?* **Sì** — stessa identica stringa, nessuna
traduzione, nessuna chiave nuova, nessun id in mezzo.

Verificato prima di prometterlo, perché una FK su testo non perdona:

| Controllo sul CSV vivo | Esito |
|---|---|
| spazi in testa/coda | **nessuno** |
| codici che differiscono solo per maiuscole | **nessuno** |
| caratteri fuori da `[A-Z0-9_]` | **nessuno** |
| codici distinti su 690 righe | **689** — l'unico doppio è la coppia `it`/`en` |

**La FK atterra pulita: nessuna bonifica preliminare.**

⭐ **E il controllo ha tirato fuori un numero che serviva.** Nel catalogo ci sono
**50 codici senza prefisso `E_`/`W_`**, che a prima vista sembrano un problema.
Incrociati con `obsoleto_dal`, i 50 senza prefisso **sono esattamente i 50
ritirati**: sono i vecchi nomi che la campagna di rinomina ha sostituito e che
non si sono potuti cancellare per via della FK di `dbops.error_log`.

L'unico codice **vivo** fuori convenzione è `MESSAGGIO_NON_DEFINITO` — cioè
esattamente l'unica riga rimasta in `dbops.messaggi_errore_codici_legacy`
(57 → 1). Conferma indipendente della storia del §7.2.

**Conseguenza sul dimensionamento:** `config.codici_errore` nasce con **~689
righe, di cui 50 sono nomi ritirati** che convivono coi loro gemelli `E_*` vivi.
È corretto e voluto — ma vuol dire che anche quei 50 vogliono la loro `classe`,
che è quella che avevano da vivi (§7).

### 3.6 ⚠️ L'indice di FK va deciso, e la risposta è **no**

`messaggi_errore.codice` è già la **colonna di testa** dell'unico
`uq_messaggi_errore_codice_lingua`: un indice dedicato alla FK sarebbe
**ridondante**.

Gli indici FK in questo progetto sono **opt-in** — `dbops.apply_fk_index_policy()`
crea solo i `consentito = true` e DROPpa i `false` — quindi non nascerebbe
comunque. Ma senza seed esplicito resta una riga **non decisa**, e la prossima
persona che guarda la policy non sa se è stata valutata o dimenticata.

→ Seed in `dbops.fk_index_policy` con **`consentito = false`** e la ragione
scritta: *«coperto dal prefisso di `uq_messaggi_errore_codice_lingua`»*.

---

## 4. Il vocabolario — otto valori, e non sono inventati

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

> ✅ **Conteggi confermati in modo indipendente lato DB (2026-08-07, pomeriggio):
> 659 voci su 659**, e i sette numeri tornano esatti. La prima verifica DB ne
> leggeva 627 e li dichiarava tali; ne mancavano **32 scritte su una riga sola**
> (`ErrorPolicy(code=..., http_status=..., ...)` senza a capo), che il parser
> cercava a inizio riga. La correzione ha sistemato anche il §8, dove il numero
> sbagliato **ribaltava una conclusione** (A3).
>
> È la quinta volta in questo filone: *anche la misura è un programma, e può
> avere il suo difetto*. E stavolta il difetto era **dichiarato** («627 su 659»)
> ma la conclusione è stata scritta lo stesso — dichiarare l'incertezza non è
> come toglierla.

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

`AVVISO` **non ha uno status HTTP**, e non è una lacuna della mappa del §6: un
avviso non raggiunge mai il client, e questo non è una speranza — è il controllo
(E) che lo garantisce.

> ⚠️ **Correzione (A3/A4, BE 2026-08-07): «fallisce in modo rumoroso» oggi è
> falso**, e la frase originale di questo paragrafo lo dava per acquisito.
> Verificato leggendo `ErrorPolicyRegistry.resolve`: **non fallisce mai**. Ha due
> ripieghi, e per un `W_` scatta il peggiore dei due —
>
> | Codice non registrato | Cosa restituisce `resolve` |
> |---|---|
> | comincia per `E_` | ripiego **400** «Errore di validazione» |
> | **tutto il resto**, quindi ogni `W_` | `E_GENERICO` → **500** |
>
> Cioè un avviso che sfuggisse al controllo (E) non farebbe rumore: diventerebbe
> un **500 tecnico** con il messaggio soppresso — esattamente il difetto
> `E_DATABASE` da cui è nato tutto il filone.
>
> **Requisito, non proprietà attesa** (entra nel piano al punto 12): lato BE,
> *classe senza status ⇒ eccezione, non ripiego*. La garanzia va scritta in una
> riga di codice, altrimenti non c'è.

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

## 6. ⭐ Da dove il backend prende la classe — **decisione ribaltata: file generato**

La prima stesura affermava: *«non c'è più un secondo elenco da cui divergere,
perché non c'è più un secondo elenco»*. ⚠️ **Vero solo per lo `http_status`.**
Resta la mappa **codice → classe**, 689 voci, e il BE deve poterla leggere quando
traduce un'eccezione. Se quella mappa resta in Python, il secondo elenco non è
sparito: ha cambiato contenuto.

Le tre strade, con le loro conseguenze:

| | Dove sta la mappa codice→classe | Il secondo elenco… |
|---|---|---|
| ~~**a**~~ | il BE la legge da `config.codici_errore` a runtime | ~~sparisce davvero~~ → ⚠️ **falso, e la riga è lasciata com'era scritta**: col suo snapshot di ripiego la (a) *è* la (b), più una dipendenza DB sul percorso d'errore (§6.1) |
| ✅ **b** | modulo Python **generato** dal DB, allineamento presidiato in CI | resta, ma **meccanico** — ed è il massimo ottenibile senza toccare gli SQLSTATE |
| **c** | la classe viaggia **nell'eccezione** (SQLSTATE per classe, §2.2) | sparisce **davvero**, e non serve né cache né file — ma 311 pgTAP da toccare |

⭐ **La (c) è l'unica in cui il secondo elenco sparisce per davvero**, e questa
revisione lo rende più chiaro di prima: fra (a) e (b) la scelta è *dove tenere lo
stesso elenco*, non *se averlo*.

### 6.1 ⚠️ **Decisione ribaltata il 2026-08-07 (pomeriggio): è la (b), non la (a)**

La prima decisione era la **(a)**, su raccomandazione DB. Il BE l'ha contestata
(annotazione **A2**) e **ha ragione**. L'argomento, in una riga:

> lo snapshot di ripiego dev'essere **generato dal DB, committato e presidiato in
> CI perché non diverga**. Quello è, parola per parola, il modulo generato della
> strada (b).

Il conto vero: **(a) = (b) + una query all'avvio + una cache + un ramo di
fallback + un log rumoroso da presidiare.** E il vantaggio che avrebbe giustificato
la complessità — *«cambio una classe e ha effetto senza deploy»* — **non esiste**:
la cache si invalida al reload del processo, quindi cambiare una classe richiede
comunque un riavvio, esattamente come il deploy di un file generato.

⭐ **E c'è un secondo argomento, che nessuno dei due aveva pesato e che da solo
chiuderebbe la questione: la suite di test.** `.codex/AGENTS.md` §Regole test
Django impone che i test funzionino **senza dipendere da un DB reale**, e oggi
**9 file di test** usano `ErrorPolicyRegistry` — fra cui
`test_drf_exception_handler.py`, che è `unittest.TestCase` puro, senza database.
Caricare il registro dal DB renderebbe DB-dipendente il registro, e con lui una
fetta larga della suite: è **contro una regola esplicita del progetto**, e si
sarebbe scoperto scrivendo il codice.

**Decisione (2026-08-07): strada (b).** Il disegno:

1. **`error_policies.py` diventa generato** — non si aggiunge un artefatto, se ne
   toglie la manutenzione a mano a uno che esiste già. Oggi contiene 659 voci
   scritte a mano; domani le stesse voci escono dal DB;
2. **la generazione legge `config.vw_codici_errore`** e produce `codice → classe`;
   lo `http_status` non compare più nel file: si deriva;
3. **un controllo in CI** fallisce se il file generato diverge dal DB — è il
   cancello `test_error_codes_db_policy_guardrail` che cambia mestiere ancora una
   volta, e non un presidio nuovo;
4. **la mappa classe → HTTP resta lato BE**, otto righe scritte a mano (sette
   status + `AVVISO`, che non ne ha uno). È
   trasporto, non dominio: il DB non deve sapere cosa sia un 409;
5. `ui_action` e `user_message` restano scritti a mano nel file generato — e
   **questo è il pezzo scomodo**: un file in parte generato e in parte a mano è
   una forma fragile. Va deciso lato BE se separarli in due moduli (generato +
   override) o se generare anche gli override da una seconda sorgente. **Non è
   una domanda per il DB**, ma va risolta prima di scrivere il generatore.

> ⚠️ **Va detto senza girarci intorno: il secondo elenco NON sparisce, in
> nessuna delle due strade.** Quello che sparisce è la sua **scrittura a mano** —
> che è il punto da cui nascono le divergenze, e quindi è già il guadagno vero.
> La frase del §8 *«non c'è più un secondo elenco»* era sbagliata due volte: la
> prima stesura la diceva dello status, questa revisione la diceva della classe.
> È corretta nel §8.

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
decisioni residue**, non scoperti a lavoro iniziato.

⚠️ **E «per la maggior parte sarà ritiro» era una scorciatoia** (rilievo BE, A5).
La [guida dei presidi §3.3](../../guide/presidi-e-registri-del-debito.md) chiede
il contrario: *«prima di togliere un codice del genere va distinto se è
**superato** o **non ancora agganciato**: cancellare il secondo tipo rompe il
lavoro di qualcun altro»*. È la stessa domanda rimasta aperta sulle due funzioni
orfane del cantiere precedente.

### 7.1 ⭐ Il discriminante è misurabile — il metodo, che vale oltre questi 33

La guida chiede di distinguere ma non dice **come**. Il BE ha proposto un
criterio e il DB l'ha verificato: **contare le tracce**, su due assi invece che
su uno.

| Asse | Cosa misura |
|---|---|
| **funzioni vive che lo sollevano** | è agganciato *adesso*? (per questi 33 è **0** per costruzione) |
| **file del repo che lo nominano**, escluso il CSV del catalogo | qualcuno l'ha **progettato**? (doc, brief, YAML, test) |

Incrociati, separano i 33 da soli:

| Tracce | Quanti | Cosa sono | Cosa farne |
|---|---|---|---|
| **0** | 3 — `E_INVALID_SNAPSHOT` · `E_DRYRUN_CREATE_TRIGGER` · `E_DATA_FINE_INFERIORE_DI_INIZIO` | esistono **solo** come riga di catalogo: mai sollevati, mai documentati, mai nominati da nessuno | ✅ **ritiro**, sono i candidati veri |
| **1-3** | 6 — `E_STORICO_UPD` · `E_STORICO_DLT` · `E_TXID_DBLINK_ERROR` · `E_TXID_DBLINK_NULL` · `E_ATTIVO_CASCADE` · `E_DBLINK_LOG_CONN_MISSING` | traccia sottile | plausibilmente **superati** — verificare il singolo |
| **3-10** | ~10 — famiglie `E_BOM_*` (4) · `E_CONTRATTO_MODALITA_C_*` (3) · `E_COMPETENZA*` + `E_VENDITA_COMPETENZA_RICHIESTA` (3) | ⚠️ **famiglie coerenti, progettate**: `E_VENDITA_COMPETENZA_RICHIESTA` ha 10 tracce e zero funzioni che lo sollevano | **non ancora agganciate** — si classificano, non si ritirano |

✅ **Verificato lato DB sui casi limite** (2026-08-07): i tre a zero tracce hanno
davvero `0` ovunque — nessuna funzione viva, nessun file nel repo. E
`E_BOM_VERSIONE_OVERLAP` (5 tracce) / `E_VENDITA_COMPETENZA_RICHIESTA` (10) hanno
tracce **e zero funzioni che li sollevano**: è la firma esatta di *«progettato,
non ancora cablato»*.

> ⭐ **Il metodo è la parte riusabile, più dei 33.** «Zero tracce» e «zero
> sollevamenti» sembrano la stessa cosa e non lo sono: il secondo da solo dice
> «nessuno lo usa **ora**», ed è ciò che ha lasciato aperte per un cantiere
> intero le due funzioni orfane. Il primo dice «nessuno l'ha mai **pensato**», ed
> è quello che autorizza a cancellare.

⚠️ **Uno si è mosso da ieri:** `E_AI_CONFIRMATION_REQUIRED` è nei 33, ma il BE
l'ha **ritirato** nell'audit degli status (nessuno lo sollevava: il flusso di
conferma AI risponde 200 con `requires_confirmation` nel payload). A catalogo è
ancora vivo → **va ritirato anche lì, non classificato**.

**In tutti i casi**: la classe di un codice ritirato è **quella che aveva quando
era vivo**. Il diario deve continuare a risolvere.

### 7.2 ✅ I «3 solo-Python» — la domanda di perimetro si scioglie da sola

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
  **sette**. ⚠️ **Non** «non c'è più un secondo elenco»: la mappa codice → classe
  resta, e con la strada (b) del §6 resta in un file. Quello che sparisce è la
  sua **scrittura a mano**, che è da dove nascono le divergenze;
* **`ui_action` resta per codice** — non è derivabile. ⚠️ La tabella qui sotto è
  la **seconda versione**: la prima veniva da una lettura parziale (627 su 659) e
  **ribaltava la conclusione**. Ricontato 659/659, confermato dal BE (A3):

  | classe (status) | totale | valore dominante | override che restano |
  |---|---|---|---|
  | `DATO_ERRATO` (400) | 234 | `show_error_banner` — **117** | **117** |
  | `CONFLITTO_STATO` (409) | 224 | `show_error_banner` — 205 | 19 |
  | `NON_TROVATO` (404) | 84 | `show_empty_state` — 50 | **34** |
  | `TECNICO` (500) | 63 | `show_error_banner` — 62 | 1 |
  | `NON_PERMESSO` (403) | 23 | `show_error_banner` — 23 | 0 |
  | `NON_ESEGUIBILE` (422) | 22 | `show_error_banner` — 20 | 2 |
  | `NON_DISPONIBILE` (501) | 4 | `show_error_banner` — 3 | 1 |
  | | | **totale** | **174** |

  ⚠️ **Sulla classe più numerosa il default non esiste: è un lancio di moneta.**
  Non «quasi a metà» — **esattamente** a metà, 117 contro 117, e con la dominanza
  **invertita** rispetto alla prima tabella (banner, non campo evidenziato). Su
  `DATO_ERRATO` un default per classe indovina il 50% delle volte, che è come non
  averlo.

  Il discriminante non è la classe ma **dove manca il dato**: sul form che
  l'operatore sta compilando (campo evidenziato) o sull'entità collegata
  (banner). È un'informazione che la classe non porta e non può portare — da
  sapere **prima** di progettare «default per classe con override», non dopo.

  Restano comunque **174 override su 659**: il guadagno c'è, ma è «da 659 voci a
  174 + 7 regole», non «a sette»;
* il cancello `test_error_codes_db_policy_guardrail` **resta**, e cambia mestiere
  per la seconda volta: da unico presidio, a rete di sicurezza, a **controllo di
  divergenza fra il file generato e il DB** (§6.1 punto 3).

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
4. ⚠️ **I due accumulatori non si curano con una classe** — e il `NOT NULL` li
   **peggiora**. Vedi §9.1: non è più una nota in coda, è un passo del piano.
5. **La classe è una proprietà del codice, non del punto che solleva.** È il
   limite strutturale del disegno, ed è accettato: la garanzia che compra è
   *«ogni codice ha una semantica dichiarata»*, non *«ogni sollevamento ha la
   semantica giusta»*. La seconda non è ottenibile da una tabella — si ottiene
   leggendo la funzione, che è quello che il cantiere ha fatto 150 volte.
6. ⚠️ **Nessuno presidia che la classe resti vera** — §9.2.

### 9.1 ⚠️ Gli accumulatori: il `NOT NULL` non è neutro, li **certifica**

Rilievo BE (**A1**), accolto. Il punto non è che la classe non li cura — è che
assegna una classe **ufficiale** a un codice che ne vorrebbe cinque, e da quel
momento la bugia ha un dato che la certifica.

**`E_VALIDAZIONE` — 10 funzioni, cinque domini.** Verificato sulla doc auto-gen,
la lista del BE è esatta:

> `fn_resolve_indirizzo_documento` · `fn_snapshot_indirizzo` ·
> `fn_snapshot_indirizzo_soggetto` · `fn_annulla_reso` · `fn_conferma_reso` ·
> `fn_genera_ddt_da_ordine` · `fn_genera_ddt_riconsegna` ·
> `fn_ordine_ha_residuo_evasione` · `fn_ordine_riga_qta_riconsegna` ·
> `fn_push_preventivo_a_ordine`

Risoluzione indirizzi, annullamento resi, generazione DDT, residui d'ordine,
push preventivo — tutti sotto «Validazione fallita: %s». `DATO_ERRATO` è
plausibile per alcuni e **falso** per altri: `fn_annulla_reso` che rifiuta un
annullamento è `CONFLITTO_STATO`, non un dato sbagliato.

→ **Si spezza prima del seed.** Dieci funzioni sono un lotto piccolo, e la
distinzione è già chiara.

**`E_PARAMETRO_INVALIDO` — 112 secondo il BE, 114 file nella doc auto-gen.** La
differenza non è stata inseguita: l'ordine di grandezza è quello, e la conclusione
non cambia. ⚠️ **Qui bloccare il piano non è praticabile**: centoquattordici
funzioni sono un cantiere a sé, non il passo 3 di questo. E sappiamo già che
almeno un uso non è `DATO_ERRATO` — nel resolver di prezzo il parametro sbagliato
lo riceve la funzione dal chiamante, non l'operatore.

→ **Denominatore sicuro + il perché nella colonna `note`.** La colonna del §3.3
esiste per questo: un accumulatore va riconoscibile *come tale*, non solo
classificato.

> ⚠️ **Una correzione al costo, però.** Il BE scrive che se il seed parte prima
> dello split «poi si riscrive il seed». **Non è così**: spezzare un codice crea
> codici **nuovi** (righe nuove); la riga dell'accumulatore non si riscrive — o
> resta per gli usi che sopravvivono, o si **ritira**. Il costo di «seed prima,
> split poi» è che per un po' una riga porta una classe di compromesso, con la
> ragione scritta accanto. È un costo di **verità**, non di rilavorazione — che
> resta un buon motivo per fare `E_VALIDAZIONE` prima, ma non per bloccare
> `E_PARAMETRO_INVALIDO`.

**E la regola che chiude il rubinetto** — vietare **nuovi** codici generici,
come si è fatto per i codici fuori convenzione — resta in coda al lavoro (piano,
punto 15): rincorrere gli esistenti senza chiudere il rubinetto è la forma in cui
questi registri non calano mai.

### 9.2 ⚠️ Chi controlla che la classe resti **vera**? Oggi nessuno

Rilievo BE (**A6**), accolto e — a differenza degli altri — con una proposta.

Il disegno ha un `NOT NULL` che impedisce a un codice di **nascere** senza
classe. Non ha niente che impedisca a una classe di **diventare falsa dopo**,
quando la funzione che solleva cambia ramo o quando qualcuno riusa il codice
altrove.

**È successo davvero:** `E_STATO_SCONOSCIUTO` è diventato ambiguo il giorno in
cui è stato riusato in `trgfn_toponomastica_normalize`, molto dopo la sua
creazione. ⚠️ **E con la classe a catalogo sarebbe andata peggio**: quel riuso
avrebbe trovato `NON_TROVATO` già scritto, e non avrebbe protestato — la classe
avrebbe dato al riuso una patente di legittimità.

**Proposta DB — una misura, non un cancello.** Il segnale c'è ed è calcolabile
dalla stessa sorgente della vista esistente:

> **un codice sollevato da funzioni di più di un dominio è un candidato
> accumulatore.**

Avrebbe intercettato tutti e tre i casi noti: `E_STATO_SCONOSCIUTO` (vendite +
toponomastica), `E_VALIDAZIONE` (cinque domini), `E_PARAMETRO_INVALIDO` (114
funzioni sparse). Ed è **set-based**: una vista accanto a
`dbops.vw_codici_errore_da_dichiarare`, che l'estrazione dei punti di
sollevamento ce l'ha già.

⚠️ **Misura, non cancello**, e per una ragione precisa: un codice legittimamente
trasversale esiste (`E_PERMESSO_NEGATO` sarà multidominio per costruzione), e un
cancello che lo bocci verrebbe disattivato. Va guardata **all'apertura di un
lotto**, come la lente — con la differenza che questa non ha il 23% di
precisione: dice un fatto, non un'ipotesi.

**Resta comunque fuori dalla garanzia**, e va detto: il disegno presidia la
*nascita* di un codice, non la sua *vita*. Chi legge questo brief fra un anno
deve trovarlo scritto, non doverlo dedurre dal punto 5 del §9.

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

## 11. ⚠️ ~~L'altro elenco duplicato~~ — **NON è un duplicato**, ed era un errore del DB

> ⚠️ **Questa sezione diceva il contrario, e sbagliava.** Va letta come
> correzione, non come aggiornamento: è il terzo errore del DB in questo brief, e
> come gli altri due stava in una frase scritta con la sicurezza di un fatto.

**Come era scritta:** *«`user_message` — 659 stringhe italiane dentro
`error_policies.py`. **Duplicano** `config.messaggi_errore.messaggio`»*, con la
malattia rovesciata di `obsoleto_dal` (monolingui contro un catalogo
multilingua), e un cantiere futuro per spostarle.

**Cosa sono davvero** (rilievo BE, verificato lato DB): sono la **variante senza
segnaposto**. Il messaggio a catalogo ha i buchi che
`script.fn_log_and_raise_error` riempie a runtime; il `user_message` è quello che
si mostra **quando quegli argomenti non ci sono** — cioè quando il messaggio del
DB non è arrivato. Non è un duplicato: è il ripiego per il caso in cui il
catalogo non ha parlato.

### 11.1 La prova non è la somiglianza dei testi, è il segnaposto

Il BE l'ha misurata per **somiglianza** (338 «uguale o contenuto» contro 318
diversi); il DB rifacendola ne ha ottenuti altri (226 contro 430). ⚠️ **La
differenza non conta, e la ragione è più utile del numero**: un confronto per
somiglianza dipende da come si normalizza il testo, quindi due misure oneste
danno due risposte. Il segnale vero è un altro, ed è **binario**:

| Misurato su 656 codici confrontabili | |
|---|---|
| messaggi **a catalogo** che contengono `%s` | **371** (56%) |
| `user_message` che contengono `%s` | **0** |
| fra i 430 divergenti, quanti hanno `%s` a catalogo | **368** (86% della divergenza) |

**Zero contro 371.** Non è un'euristica, è un fatto: la divergenza non è
disordine, è **il segnaposto**. La tesi del BE regge, e regge più solidamente di
come l'aveva argomentata.

> ⭐ **La lezione di metodo, che vale oltre `user_message`:** quando due elenchi
> sembrano duplicati, la somiglianza dei testi è una misura fragile — il
> **contratto** di ciascuno (qui: «accetta argomenti / non li accetta») è una
> misura netta. Cercare la seconda prima della prima.

### 11.2 Conseguenza: spostarli è più caro di come sembrava

Il vincolo che il DB aveva scritto — *«la separazione scelta ora non deve rendere
più difficile spostarle un domani»* — resta valido ma va **riprezzato**: non è
muovere 659 stringhe. Richiederebbe che il catalogo porti una **seconda variante
argument-free** di ogni messaggio, per **371 codici** (tutti quelli con `%s`).
Cioè una colonna in più su `messaggi_errore`, o una riga in più per codice: un
cantiere suo, e più grosso di quanto il paragrafo originale lasciasse credere.

✅ **La forma scelta dal BE lo tiene aperto senza pagarlo adesso**: i
`user_message` vanno in un modulo **loro**, che si chiama `fallback` (§14.2).
Spostarli un domani sarà cancellare un file, non estrarli da un file che contiene
anche decisioni di UI.

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

## 13. Il piano — ⚠️ **spostato in due documenti separati**

> **Decisione (Tid, 2026-08-07 sera): il BE è fermo, si sviluppa tutto il DB per
> primo.** Da qui in avanti **questo brief è la guida generale** — le ragioni, le
> misure, le 19 decisioni — e l'esecuzione vive in due piani operativi:
>
> * ▶️ [**piano-db-classe-codici-errore**](piano-db-classe-codici-errore.md) — D-1..D-10, si comincia da qui;
> * ⏸️ [**piano-be-classe-codici-errore**](piano-be-classe-codici-errore.md) — B-1..B-7, coi prerequisiti marcati.
>
> La tabella qui sotto **resta come vista d'insieme**, ma i piani sono la
> versione viva: se divergono, valgono loro.

### 13.0 ⭐ Il BE non era un prerequisito del DB — misurato

Il piano unico aveva al punto 3 *«il BE genera il CSV `codice,classe` da
`error_policies.py`»*, e sembrava il punto in cui il DB avrebbe dovuto aspettare.

**Non è così.** La mappa status → classe è deterministica e il file è nel repo:
il DB se lo estrae da solo. Misurato il 2026-08-07:

| | |
|---:|---|
| **654** su 659 | convertiti automaticamente dallo status |
| **5** | restano — `E_JWT_SENZA_IDENTITA`, `E_IDENTITA_NON_ATTIVA`, `E_AUTHENTICATION_FAILED`, `E_NOT_AUTHENTICATED` (401) e `E_AI_PROVIDER_ERROR` (502) |
| | e sono **esattamente** i codici già esclusi dal vocabolario di dominio (§4) |

⭐ **E vale anche al contrario**: dei sette passi del BE, **quattro non hanno
nessun prerequisito DB** (togliere la policy morta, l'eccezione su classe senza
status, i quattro moduli, la mappa classe → HTTP). L'unico vero cancello è
**D-9** — le due viste — che è il passo di consegna del piano DB.

Quindi *«prima il DB, poi il BE»* è una **scelta di comodo, non un vincolo
tecnico**. Va scritto perché fra sei mesi sembrerà una dipendenza, e non lo era.

⚠️ **Una conseguenza da mettere in conto:** finché il BE non ha il generatore, i
codici **nuovi** creati dal DB (lo split di `E_VALIDAZIONE`) cadono sul ripiego
400 di `resolve()`. Non è una regressione — è il comportamento di oggi per ogni
codice nuovo — ma **lo split non cambia niente di visibile finché il BE non
riparte**.

### 13.1 Vista d'insieme (superata dai due piani)

L'ordine è per **dipendenza**, non per dimensione.

| # | Cosa | Chi | Note |
|---|---|---|---|
| 1 | ~~Decidere il perimetro dei 3 codici solo-Python~~ | ~~Tid~~ | ✅ **chiuso** (§7.2): il catalogo è di **tutti** i codici, e i tre non erano codici |
| **1-bis** | ⏱ **Spezzare `E_VALIDAZIONE`** — 10 funzioni, 5 domini | **DB + BE** | 🔴 **la prima a scadere**: se il seed parte prima, `fn_annulla_reso` prende `DATO_ERRATO` dove la verità è `CONFLITTO_STATO` (§9.1) |
| **1-ter** | 🔵 Decidere la forma di `error_policies.py` generato/a-mano | **BE** | §14.1 — non blocca il DB, blocca il generatore |
| 2 | `config.classi_errore` (**8 valori**, `AVVISO` incluso) + `config.codici_errore` (`00_schema`) — `classe NOT NULL` **senza DEFAULT**, FK, audit, `note` | DB | |
| 3 | Il BE genera il CSV `codice,classe` da `error_policies.py` | BE | 659 righe su 692; **escludendo `PREV_STATO_NON_MODIFICABILE`**, che è morto (§7.2); `E_PARAMETRO_INVALIDO` col denominatore sicuro e il perché in `note` |
| 4 | **Le ~32 decisioni residue** — classificare o ritirare, **col discriminante del §7.1** | Tid + DB | i **3 a zero tracce** si ritirano subito; le famiglie `E_BOM_*` / `E_CONTRATTO_MODALITA_C_*` / `E_COMPETENZA*` si **classificano** (non agganciate ≠ superate). ⚠️ `E_AI_CONFIRMATION_REQUIRED` → ritiro anche a catalogo |
| 5 | Seed: `classi_errore` + `codici_errore.csv`, **dentro `20260614-08` prima del catalogo** (§10.1) | DB | ⚠️ è il passo che rompe la CI se fatto nel modo ovvio |
| 6 | Migrazione `obsoleto_dal`: colonna nuova popolata, poi `DROP` sulla vecchia | DB | forward-only, breaking secco: non siamo in produzione |
| 7 | FK `messaggi_errore.codice → codici_errore.codice` + seed `fk_index_policy` a **`consentito = false`** | DB | dopo che il seed regge; l'indice è ridondante (§3.6) |
| 8 | Riscrivere i **5 lettori** di `obsoleto_dal` (§10.2) | DB | stesso giro del punto 6 |
| 9 | Adeguare i **4 pgTAP** (§10.3) + nuovo test sul `NOT NULL` e sulla FK | DB | |
| 10 | Vista `config.vw_codici_errore` (`20_code`) | DB | ⚠️ numerazione **più alta** di chi la dipende |
| 10-bis | **Vista di sola identità** (`codice, classe, obsoleto_dal, note`) per il generatore | DB | §14.4 — `vw_codici_errore` ha una riga per (codice, lingua): non serve al generatore |
| 11 | **Generatore** dei 4 moduli (§14.2) + controllo di divergenza in CI | BE | §6.1 — non più «lettura a runtime + snapshot»; sorgente e `ORDER BY` nel §14.4 |
| 12 | `http_status` derivato dalla classe; `ui_action` a default+override; **`classe` senza status ⇒ eccezione** | BE | **174** override restano, di cui 117 sul solo `DATO_ERRATO` (§8) |
| 13 | Vista dei **codici multidominio** — la misura del §9.2 | DB | misura, non cancello |
| 14 | Regola «niente nuovi codici generici» | BE + DB | coda del lavoro |

**Punto di non ritorno:** il 6. Fino al 5 tutto è additivo e reversibile; dal 6 il
catalogo cambia forma e i lettori vanno con lui.

⏱ **L'ordine del piano non è l'ordine di urgenza, ed è un rilievo del BE.**
Le due cose che pesano di più scadono in punti lontani: il **1-bis** (accumulatori)
è il primo a mordere, la **D6-bis** (generato invece che a runtime) è la più
importante ma scade all'11. Chi legge il piano dall'alto le incontra nell'ordine
sbagliato — per questo stanno entrambe qui in testa, fuori numerazione.

### 13.1 Fuori piano, ma nate qui — due code da non perdere

Non bloccano niente e non entrano nel piano, ma sono l'unico posto in cui
risultano scritte:

* **`PREV_STATO_NON_MODIFICABILE` da togliere** da `error_policies.py`: è una
  policy orfana di un codice che il DB ha cancellato il 2026-08-05 (§7.2).
  ⚠️ *Perimetro BE* — richiesta al team BE, una riga;
* **`MESSAGGIO_NON_DEFINITO` → `E_MESSAGGIO_NON_DEFINITO`**: chiude il registro
  `dbops.messaggi_errore_codici_legacy` (**1 → 0**, e a zero la tabella si
  droppa). Slice sua, perché `script.fn_log_error_only` cerca quel codice per
  nome scritto a mano: le funzioni vanno nello stesso changeSet (§7.2).

---

## 14. Decisioni prese, con data

| # | Decisione | Chi, quando |
|---|---|---|
| D1 | **Tabella separata** `config.codici_errore`, non una colonna su `messaggi_errore` | Tid, 2026-08-07 |
| D2 | `classe` con **FK a un vocabolario** `config.classi_errore`, non un `CHECK` | DB, 2026-08-07 |
| D3 | Il **vocabolario del §4** si adotta così com'è | Tid, 2026-08-07 |
| D4 | La mappa **classe → HTTP resta lato BE**: è trasporto, non dominio | Tid, 2026-08-07 |
| D5 | Il meccanismo anti-ricaduta è il **`NOT NULL` senza `DEFAULT`**, con la **vista** come superficie di revisione — **non** l'adiacenza | Tid, 2026-08-07 (§5) |
| ~~D6~~ | ~~Il BE legge la classe dal DB a runtime (strada *a*)~~ | **superata dalla D6-bis** |
| **D6-bis** | **Strada (b)**: `error_policies.py` diventa **generato** dal DB, con controllo di divergenza in CI. La (a) era la (b) con una query, una cache e un fallback in più — e il registro DB-dipendente violava la regola «i test girano senza DB» (§6.1) | BE + DB, 2026-08-07 pomeriggio |
| D7 | `obsoleto_dal` **migra** su `codici_errore`: il ritiro appartiene al codice, non alla frase | Tid, 2026-08-07 |
| D8 | Lo **SQLSTATE per classe** (§2.2) non si fa ora — 311 pgTAP — ma resta scritto | DB, 2026-08-07 |
| D9 | `config.codici_errore` è il catalogo di **tutti** i codici — non serviva scegliere: **656 su 659** ci sono già (§7.2) | Tid, 2026-08-07 |
| D10 | **Ottavo valore `AVVISO`** per la famiglia `W_`: un avviso non è un rifiuto, e senza di lui la FK non ha padre (§4.2) | DB, 2026-08-07 |
| D11 | **`E_VALIDAZIONE` si spezza prima del seed** (10 funzioni, 5 domini); `E_PARAMETRO_INVALIDO` no — denominatore sicuro + `note`, e cantiere suo (§9.1) | BE + DB, 2026-08-07 pomeriggio |
| D12 | **`classe` senza status ⇒ eccezione, non ripiego** — requisito lato BE, perché `resolve()` oggi non fallisce mai (§4.2) | BE, 2026-08-07 pomeriggio |
| D13 | Il **discriminante superato/non-agganciato è il conteggio delle tracce**, su due assi (§7.1) | BE + DB, 2026-08-07 pomeriggio |
| D14 | **Vista dei codici multidominio** come misura all'apertura di ogni lotto — non un cancello (§9.2) | DB, 2026-08-07 pomeriggio |
| D15 | **Quattro moduli** lato BE, separati per *quando cambiano*; override in codice e non in CSV (§14.2) | BE, 2026-08-07 sera |
| D16 | ⚠️ **`user_message` NON è un duplicato del catalogo**: è la variante senza segnaposto — **0 su 656** contengono `%s`, contro 371 a catalogo (§11) | BE + DB, 2026-08-07 sera |
| D17 | **Due viste, non una**: `vw_codici_errore` per la revisione (per lingua), `vw_codici_errore_identita` per il generatore (per codice), con `ORDER BY codice` dentro la vista (§14.4) | DB, 2026-08-07 sera |
| D18 | **`note` su una riga sola**, senza a capo: le celle CSV multi-riga sono strada battuta poco (3 in tutto il repo) (§14.3) | DB, 2026-08-07 sera |
| D19 | **Due piani separati, DB per primo**: il BE è fermo e — misurato — non era un prerequisito (654/659 estraibili dal DB). L'unico cancello è D-9 (§13.0) | Tid, 2026-08-07 sera |

### 14.1 ✅ ~~Cosa resta da decidere~~ — chiusa dal BE, 2026-08-07

L'ultima decisione aperta (la forma di `error_policies.py` generato/a-mano) è
**chiusa**: strada 1, ma con **quattro moduli** invece di due. Dettaglio nel
§14.2. **Nessuna decisione aperta.**

### 14.2 ⭐ La forma scelta: quattro moduli, separati per **destino**

Non per contenuto — per **quando cambiano**. È il criterio che rende facile la
mossa futura sui `user_message` (§11.2):

| Modulo | Cosa | Chi lo scrive | Quando cambia |
|---|---|---|---|
| `error_policies_generated.py` | `codice → classe`, 659 voci | **generato dal DB** | a ogni seed |
| `error_policies.py` (registry) | `classe → (status, ui_action di default)` — 8 righe + la logica | a mano | quasi mai |
| `error_ui_overrides.py` | i **174** `ui_action` fuori default, coi loro commenti | a mano | quando cambia una scelta di UI |
| `error_messages_fallback.py` | i `user_message` | a mano, **per ora** | quando si spostano al catalogo |

⭐ **Il quarto modulo è la risposta al vincolo del §11.2, e il valore sta nel
nome.** Dentro il modulo degli override, spostare i `user_message` domani sarebbe
un refactor di un file che contiene anche decisioni di UI; da soli in un file che
si chiama `fallback`, spostarli è **cancellare un file** — e nel frattempo il
nome dice la verità su cosa sono.

**Perché non la strada 2 (override in un CSV).** Perché gli override non sono
dati: sono **decisioni con una motivazione**, e un CSV non porta un paragrafo.
**194 blocchi di commento** in `error_policies.py` sono il ragionamento delle 150
decisioni del cantiere precedente — per esempio, su `E_CONTO_BANCARIO`:

> *«la guard è `attivo IS NOT TRUE`, che copre DUE casi: conto disattivato e
> conto inesistente. Il 400 col campo evidenziato è corretto in entrambi; un 404
> sarebbe giusto solo nel secondo e svuoterebbe la pagina nel primo.»*

Metterlo in un CSV lo cancella, ed è **esattamente la cosa che questo cantiere è
servito a non perdere**.

### 14.3 La regola su dove finisce ciascun commento

| Il perché di… | Va in |
|---|---|
| **la classe** | `config.codici_errore.note` — lato DB |
| **la `ui_action`** | il modulo `error_ui_overrides.py` — lato BE |
| **un ritiro, una storia** | il brief che l'ha deciso |

⚠️ **Una trappola DB su `note`**, da verificare prima del seed: quei paragrafi
finiscono in una **cella di CSV**. Precedenti nel repo ce ne sono — `messaggi_errore.csv`
ha già celle da **872 caratteri**, e due CSV hanno celle con **a capo dentro**
(`stradario_generale`, `sec_functions_owner`) — quindi Liquibase regge. Ma sono
tre celle in tutto il repo: se le `note` diventano paragrafi multi-riga, quella
è una strada battuta **poco**. Prudenza: `note` su **una riga sola**, senza a
capo, finché non serve davvero il contrario.

### 14.4 Il contratto del generatore — quello che il BE chiede al DB

Il BE ha chiesto due cose, entrambe dovute: **la query di sorgente** e
**l'ordinamento stabile**. Sulla prima il DB corregge la richiesta.

⚠️ **`config.vw_codici_errore` NON è la sorgente giusta**, ed è una svista
nostra: è la vista di *revisione* (§5.2), affianca la frase al codice, quindi ha
**una riga per (codice, lingua)**; e siccome è un `LEFT JOIN`, un codice **senza**
messaggio ci compare con `lingua IS NULL`. Filtrarla per `lingua = 'it'`
perderebbe proprio quei codici — che sono fra quelli che più servono vedere.

→ **Sorgente = la seconda vista, di sola identità** (§3.3, piano punto 10-bis):

```sql
-- Sorgente del generatore di error_policies_generated.py.
-- Una riga per codice, nessun join, nessun filtro lingua da sbagliare.
-- ORDER BY codice: l'ordine NON e' un dettaglio estetico (vedi sotto).
SELECT codice, classe, obsoleto_dal, note
  FROM config.vw_codici_errore_identita
 ORDER BY codice;
```

L'`ORDER BY` sta **anche dentro la vista**, non solo nella query del generatore:
un requisito che vive in due posti si dimentica in uno dei due.

> ⚠️ **Perché l'ordinamento è un requisito e non una cortesia.** Senza `ORDER BY`
> PostgreSQL non promette niente, e l'ordine può cambiare fra due esecuzioni
> identiche (piano diverso, righe riscritte da un `UPDATE`). Un generatore che
> produce **diff spurii per riordino** diventa un file che nessuno rilegge — e da
> lì a non accorgersi di una **classe cambiata** è un passo solo. È la stessa
> famiglia del difetto che questo cantiere cura: non un guasto, una cosa che
> smette di essere guardata.
>
> ⭐ **E la ragione per cui le viste sono due merita di restare scritta**: la
> stessa tabella serve due mestieri con **cardinalità diverse**. La revisione
> vuole vedere la frase, quindi moltiplica per lingua; il generatore vuole
> l'identità, quindi una riga per codice. Riusare una vista per entrambi
> costringe a un filtro — e il filtro sbagliato qui non dà errore: **toglie
> righe in silenzio**, che è la forma di guasto contro cui è costruito tutto
> questo brief.

> ⚠️ **Le altre annotazioni del BE (A1, A3, A4, A5, A6) sono tutte accolte e
> incorporate**, e due di esse hanno corretto un errore del DB: la tabella
> `ui_action` del §8 veniva da una lettura parziale che **ribaltava una
> conclusione** (A3), e la garanzia «`AVVISO` fallisce rumorosamente» era falsa
> (A4). Il valore del giro non è che il BE avesse ragione: è che entrambi gli
> errori erano in cose **già scritte come verificate**.

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
