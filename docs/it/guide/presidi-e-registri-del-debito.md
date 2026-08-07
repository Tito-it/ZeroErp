# Guida – Presidi e registri del debito

> **Cos'è.** Come ZeroErp si accorge da solo che qualcosa si è rotto in silenzio,
> e come tiene il conto di ciò che è rotto e non è ancora stato sistemato.
>
> Riguarda i controlli che oggi esistono — i **riferimenti morti** nelle funzioni
> del database, la **baseline dei test rossi** e il **codice errore che arriva al
> backend** — e la forma che hanno in comune.
> Il §4 spiega perché alcuni girano da soli e uno va lanciato a mano, che è la
> domanda che si fanno tutti.

---

## 1. Il problema: un promemoria non è un presidio

Il 2026-03-31, durante una campagna di pulizia, due funzioni del database furono
riconosciute **morte** — nominavano una tabella cancellata mesi prima — e lasciate
dov'erano. Non per distrazione: fu scritto nero su bianco, in un changeSet che
esiste solo per dirlo.

> «Dipende da `vendite.attivita_fatturabili_lotti` (tabella rimossa).
> **Da verificare se la funzione va rimossa dal DB.**»

Quella verifica non è mai stata fatta. Cinque mesi dopo, una delle due ha fatto
fallire un aggiornamento del database, ed è così che ci siamo tornati sopra.

**La lezione, che vale ben oltre il caso**: una segnalazione lasciata in un
commento non presidia niente. È un promemoria, e i promemoria non si rileggono.
Perché una cosa sia davvero presidiata serve qualcosa che **protesti da solo**,
al momento giusto, senza che nessuno debba ricordarsene.

Da qui i controlli descritti sotto. Non sono strumenti presi a caso: hanno la
stessa forma, e conviene conoscerla prima dei dettagli.

---

## 2. La forma comune: la misura e il registro

Ogni presidio è fatto di **due pezzi**, e nessuno dei due funziona senza l'altro.

**La misura** dice qual è la situazione adesso. Deve essere ripetibile e non
opinabile: la si lancia oggi e domani e, se nulla è cambiato, dà la stessa
risposta.

**Il registro del debito** dice quali problemi sappiamo già di avere e perché
sono ancora lì. Serve perché la realtà non è mai a zero: c'è sempre qualcosa di
rotto che si è deciso consapevolmente di non sistemare oggi.

⚠️ **Il registro è un debito, non un elenco di eccezioni.** La differenza è tutta
qui, ed è la ragione per cui questi controlli restano utili invece di diventare
rumore di fondo:

* un **elenco di eccezioni** può solo allungarsi. Ogni volta che qualcosa dà
  fastidio, lo si aggiunge. Dopo un anno nessuno lo legge più, e i problemi veri
  ci si nascondono dentro;
* un **registro del debito** deve **calare**. Ha una data, e ogni voce spiega
  perché è ancora aperta e cosa la chiuderebbe.

Per tenerlo onesto servono due regole, e stanno in due posti diversi apposta:

| Regola | Dove vive | Perché lì |
|---|---|---|
| Senza un motivo scritto, la voce non si aggiunge | vincolo del database | non è un controllo che si può dimenticare di lanciare: è il database che rifiuta la riga |
| Una voce che non serve più va tolta | test | per saperlo bisogna ri-misurare, e una misura non può essere un vincolo |

Senza la seconda regola il registro può solo crescere, e torna a essere un elenco
di eccezioni — cioè il changeSet del 2026-03-31 con cui è cominciata questa
storia.

---

## 3. I presidi che esistono oggi

### 3.1 Riferimenti morti nelle funzioni del database

**Cosa sorveglia.** PostgreSQL non tiene traccia di cosa c'è scritto dentro una
funzione. Se si cancella una tabella o si rinomina una colonna, le funzioni che le
nominavano restano lì, apparentemente sane, e **non vengono più ricontrollate**.
Si scoprono rotte solo quando qualcuno le esegue — che può essere mesi dopo, o
nel momento peggiore.

Non è teoria: al primo giro, il 2026-08-04, ne sono uscite **34**. La più vecchia
era rotta da undici mesi, e una era la ricerca degli indirizzi usata dagli
operatori.

**Come funziona.** L'estensione `plpgsql_check` **compila davvero** il corpo di
ogni funzione, come farebbe la prima esecuzione: vede tabelle e colonne, e vede
anche i pezzi di codice che nessuno ha mai eseguito.

| Pezzo | Dove |
|---|---|
| La misura | `dbops.fn_check_funzioni_riferimenti_morti()` |
| Il registro | `dbops.riferimenti_morti_esenzioni` |
| Le due viste | `dbops.vw_riferimenti_morti_da_sanare` · `..._rientrati` |
| Strumento a mano | `scripts/sql/check_funzioni_riferimenti_morti.sql` |
| Cancello automatico | `scripts/sql/guardrail_riferimenti_morti.sql` (passo CI) |
| Test della suite | `db/pgtap/dbops/test-riferimenti-morti-v1.sql` |

**Quando diventa rosso** si hanno due strade, e nessuna delle due è ignorarlo:
ripararlo — quasi sempre è una riga — oppure registrarlo nel debito **con un
motivo scritto**.

Storia completa del primo giro — le 34 righe una per una, le cause radice e le
trappole pagate — nel brief di lavoro `docs/it/dev/work-done/brief-db-bonifica-riferimenti-morti.md`
(nel repository: i documenti di cantiere non fanno parte del sito pubblicato).

### 3.2 Baseline dei test rossi

**Cosa sorveglia.** Una parte della suite di test del database è rossa da tempo,
quasi sempre perché le fixture sono rimaste indietro rispetto a controlli entrati
dopo. In quella situazione un test rosso non dice più niente: è normale che ce ne
siano, quindi nessuno guarda.

La baseline separa i **rossi già noti** dai **rossi nuovi**. Solo i secondi sono
una notizia.

```bash
scripts/pgtap-baseline.sh vendite            # solo gli schemi toccati
scripts/pgtap-baseline.sh                    # tutta la suite (~7 min)
scripts/pgtap-baseline.sh --update vendite   # dopo aver sanato qualcosa
```

Il registro è `db/pgtap/baseline-rossi.tsv`, con la causa classificata. Lo script
segnala tre cose: le **regressioni** (rosso nuovo, esce con errore), i **rientrati**
(ora verdi, la riga va tolta) e il silenzio sui rossi già noti.

⚠️ **Una classificazione sbagliata nasconde un problema vero.** È successo: un test
era registrato come «errore di fixture» mentre in realtà la funzione che
collaudava non partiva proprio. È rimasto lì mesi, coperto da un'etichetta
rassicurante. Quando si aggiunge una riga alla baseline vale la pena spendere
cinque minuti a capire *perché* è rossa, invece di catalogarla per somiglianza.

⚠️ **Un file che fallisce nella fixture non esegue nessuna verifica.** La sua
copertura vale **zero**, non «parziale» — ed è peggio di un'area scoperta, perché
sembra coperta.

### 3.3 Il codice errore che arriva al backend

**Cosa sorveglia.** Quando il database rifiuta un'operazione, manda al backend un
**codice** — ed è da quel codice che dipendono la risposta HTTP (409 sul
duplicato, 404 sul non trovato, 403 sul vietato) e il messaggio che l'operatore
legge a video. Il codice viaggia in un campo dedicato dell'eccezione, riempito da
`script.fn_log_and_raise_error`.

Due modi di romperlo, e nessuno dei due fa rumore da solo:

* **qualcun altro scrive nello stesso campo.** Sollevare un errore a mano è
  possibile ovunque, e nel database ci sono 135 punti che lo fanno. Se uno di
  quelli mettesse nel campo qualcosa che non è un codice, il backend non
  fallirebbe: **risponderebbe la cosa sbagliata**, che è peggio, perché nessuno
  se ne accorge;
* **nasce un codice con un nome fuori convenzione.** I codici si chiamano
  `E_MODULO_TIPO`. Il backend, davanti a un codice che non conosce, se comincia
  per `E_` risponde comunque in modo sensato; se non comincia per `E_` risponde
  **errore di server**. Un operatore che tenta una transizione non ammessa si
  vedrebbe un 500 al posto di una spiegazione.

| Pezzo | Dove |
|---|---|
| La sede unica che scrive il campo | `script.fn_log_and_raise_error` |
| Il registro | `dbops.messaggi_errore_codici_legacy` |
| Il ritiro di un nome vecchio | `config.messaggi_errore.obsoleto_dal` |
| Cancello automatico | `scripts/sql/guardrail_codice_errore_strutturato.sql` (passo CI) |
| Test della suite | `db/pgtap/script/test-fn-log-and-raise-error-constraint-codice.sql` · `db/pgtap/script/test-messaggi-errore-obsoleto-dal.sql` · `db/pgtap/vendite/test-ordini-guard-transizione-v1.sql` (test 8) |

**Il registro contiene i nomi fuori convenzione ereditati** dal periodo in cui la
regola non era presidiata. Rinominarli costerebbe più di quanto renda, quindi si
tengono; ma dal 2026-08-05 **non se ne aggiungono altri**. Il registro deve
calare, e quando arriva a zero la tabella si toglie.

È già calato il primo giorno, da **57 a 53**, e non rinominando: incrociando i
codici con i punti che li sollevano davvero, quattro sono risultati **residui di
controlli ritirati** — nessuno li usava più, né il database né il resto
dell'applicazione. Sono usciti dal catalogo dei messaggi e dal registro insieme.

⚠️ Prima di togliere un codice del genere va distinto se è **superato** o **non
ancora agganciato**: un codice a catalogo che nessuno solleva può essere un
residuo, oppure un pezzo di lavoro in corso a cui manca ancora il collegamento.
Cancellare il secondo tipo rompe il lavoro di qualcun altro. Nei quattro casi la
risposta era scritta nel database stesso, nei commenti delle funzioni che li
avevano ritirati.

### Perché quasi nessuno di questi nomi si può cancellare

Quando un codice viene rinominato correttamente, verrebbe voglia di cancellare la
riga vecchia. **Quasi mai si può**: ogni errore che il sistema registra lascia una
riga di diario che *punta* alla voce del catalogo, e finché quel diario esiste la
voce non si tocca. Al 2026-08-05 erano **46 nomi su 53**, per oltre 46.000 righe
di diario.

Cancellare il diario per riordinare il catalogo sarebbe distruggere una prova per
sistemare un'etichetta. E c'è di peggio: una cancellazione del genere **riesce
sulle installazioni nuove e fallisce su quelle che hanno una storia** — la prova
automatica direbbe che va tutto bene proprio dove non c'è niente da rompere.

Perciò un nome non si cancella: si **ritira**, scrivendo la data del ritiro
accanto alla voce (`config.messaggi_errore.obsoleto_dal`). La voce resta, il
diario resta agganciato, e — punto essenziale — **chi dovesse ancora incontrare
quell'errore continua a leggere la spiegazione di sempre**, non un messaggio
vuoto. È una dichiarazione di intenti («non usatelo più»), non un interruttore.

⚠️ E una dichiarazione di intenti, da sola, è aria: qualcuno può sempre tornare a
usarlo. Per questo il controllo automatico ne verifica una in più — **nessun
punto del sistema deve poter sollevare un errore dichiarato ritirato**. Se
succede, una delle due cose è falsa e la verifica lo dice. Senza quel controllo,
la data di ritiro sarebbe l'etichetta rassicurante di cui parla il §4-bis: la
cosa più pericolosa che si possa mettere in un registro.

⚠️ **Qui il registro non chiede un motivo per riga**, al contrario di quello dei
riferimenti morti. Non è una dimenticanza: là ogni voce è una decisione a sé,
qui le 57 voci sono **una sola decisione** presa una volta. Un motivo
obbligatorio avrebbe prodotto 57 copie della stessa frase — rumore che somiglia
al rigore. La ragione sta scritta una volta, sulla tabella.

### 3.4 Il *tipo* di risposta — il terzo lato

**Cosa sorveglia.** Il §3.3 garantisce che il codice **arrivi** al backend e che
l'operatore legga la frase giusta. Ma sul codice deve andare d'accordo un terzo
elenco: la tabella che dice, per ogni codice, **che tipo di risposta** dare —
«non esiste», «non ti è permesso», «è in conflitto con lo stato attuale», «hai
sbagliato a compilare» (`backend/apps/core/services/error_policies.py`).

Su quelle parole gli elenchi sono tre, e fino al 2026-08-05 due direzioni erano
presidiate e una no:

| Direzione | Presidiata da |
|---|---|
| le parole usate dal codice applicativo sono dichiarate | `apps/core/tests/test_error_codes_declared_guardrail.py` |
| le parole che dice il database sono a catalogo | guardrail SQL del §3.3 |
| **le parole che dice il database hanno un tipo di risposta** | `apps/core/tests/test_error_codes_db_policy_guardrail.py` |

**Cosa succedeva senza.** L'operatore leggeva comunque la frase giusta — quella
viene dal catalogo — ma il *tipo* di risposta restava appiattito su «hai
sbagliato a compilare» anche quando la verità era «non esiste» o «non ti è
permesso». Chi ascolta capisce lo stesso; chi deve **reagire** — la pagina che
decide se mostrare un avviso o riportarti indietro, un allarme, un tentativo
automatico — no. Al primo giro erano **141 codici**, 90 dei quali sollevati da
funzioni agganciate a un trigger, cioè sul percorso di una richiesta vera.

Il debito ha cominciato a calare il giorno dopo, e in quattro lotti i codici **sul
percorso di una richiesta** sono passati da **90 a zero**: il registro da 141 a
51, e quel che resta sta in funzioni che potrebbero non essere mai raggiunte dal
web. Le decisioni sono state prese leggendo il punto che solleva, non il nome del
codice: tre volte su novantuno il nome diceva un'altra cosa. Uno dei codici non ha preso una risposta — è stato
**spezzato in due**, perché ne conteneva due: la stessa parola diceva «lo stato
di workflow non esiste» (404) e «la nazione dell'indirizzo non si risolve» (400,
con un campo da correggere). Un registro fatto bene non serve solo a ricordare
il debito: **fa emergere i difetti di modellazione** che il debito nascondeva.

| Pezzo | Dove |
|---|---|
| La misura | `dbops.vw_codici_errore_da_dichiarare` |
| Il registro | `dbops.codici_errore_senza_policy` (+ CSV mirror `DELETE`/`loadData`) |
| Cancello automatico | `apps/core/tests/test_error_codes_db_policy_guardrail.py` (suite Django, accesa in CI) |

⚠️ **Il cancello sta lato backend, e non è un dettaglio organizzativo.** Il
confronto è contro un dizionario Python: da SQL si potrebbe fare solo leggendo il
*testo* di quel sorgente, legando un guardrail SQL alla forma di un file che non
è suo. Il prezzo è che questo cancello, unico fra quelli qui elencati, ha bisogno
di un **database provvisto** per girare — in CI ce l'ha; in locale si accende con
`ZEROERP_TEST_DB_E2E=1`.

⚠️ **La misura è volutamente larga**, e va saputo perché. Raccoglie ogni
letterale `E_*` che compare in un corpo PL/pgSQL vivo, non solo quelli dentro la
chiamata che solleva: restringere perderebbe i codici che arrivano da
un'espressione, e la versione «raffinata» della misura aveva fatto esattamente
questo — dichiarava conformi quattro codici che non lo erano. Fra i due errori
possibili si sceglie quello che si corregge guardando i falsi positivi (una
policy di troppo costa una riga), non quello che non si vede. È la stessa scelta
del §3.1: **un setaccio, non una lista**.

⚠️ **Tre numeri per lo stesso fatto** — 133, 141, 137 — sono costati una
giornata di riconciliazione, perché ognuna delle due sponde si era scritta la
propria query. Per questo la misura è **una vista sola**, e il cancello la
interroga invece di riscrivere il regex. *Anche la misura di un difetto è un
programma, e può avere il suo difetto.*

---

## 4. Perché alcuni girano da soli e uno no

Sì: i cancelli automatici non vanno lanciati a mano. Ma non sono la stessa cosa
messa in posti diversi — sono **controlli di natura diversa**, e questo paragrafo
spiega perché ognuno sta dove sta.

Il confronto qui sotto mette a fuoco i due estremi, il §3.1 (cancello in CI) e il
§3.2 (baseline da lanciare): il §3.3 e il §3.4 appartengono alla stessa famiglia
del §3.1 e vale per loro tutto ciò che si dice del cancello automatico. Il §3.4 è
l'unico a vivere nella suite Django invece che in uno script SQL — perché
confronta contro un dizionario Python — ma resta un passo della stessa CI, che
blocca l'integrazione allo stesso modo.

### Cosa dà davvero il controllo automatico

Il vantaggio del cancello in CI non è tanto che «gira da solo»: è che **non si può
dimenticare**. Blocca l'integrazione. Nessuno deve ricordarsi di lanciarlo, e
soprattutto nessuno può decidere di saltarlo perché ha fretta.

Va però saputo **quando** scatta: sui `push` verso il branch di integrazione e
sulle richieste di merge, e solo se sono stati toccati certi percorsi. Sul proprio
branch di lavoro **non parte**. Quindi non è un riscontro immediato: è una rete
che si trova al momento del merge. Il giro lanciato a mano resta il ciclo veloce,
quello che si usa mentre si lavora.

### Cosa può misurare la baseline, e dove

Qui sta la differenza di natura, ed è il punto meno ovvio di questa guida.

Il database della CI è **costruito da zero** a ogni giro: ha la struttura e i dati
di configurazione, ma **nessun dato di lavoro** — nessuna fattura, nessun ordine,
nessuna commessa. Molti test del database, invece, scelgono un caso reale fra i
dati esistenti e ci lavorano sopra: **69 file su 437** contengono un salto
condizionato proprio per questo.

Su un database vuoto quei test **non falliscono: si saltano**. E un test saltato
conta come verde.

⚠️ Un ipotetico giro in CI così com'è darebbe quindi una pipeline verde che ha
misurato molto meno di quanto sembra — cioè il difetto peggiore di tutti, perché
non fa rumore. La baseline vive a mano, sul server di sviluppo, **perché è lì che
può misurare quello che deve**: il comportamento su dati veri.

Il che non vuol dire che i due controlli debbano restare per sempre come sono, ma
che spostare l'uno dove sta l'altro non è una semplificazione: cambia cosa si
misura.

### Il corollario, che vale per tutto il progetto

Il database di sviluppo e un database ricostruito dai changelog **non sono lo
stesso oggetto**, pur partendo dagli stessi file. Verificare solo sul primo
significa verificare lo stato di **una macchina**; verificare sul secondo significa
verificare che le migrazioni sappiano ricostruirla. Sono due proprietà diverse, e
la seconda è quella che conta il giorno in cui si prepara un ambiente nuovo.

Non è un discorso astratto: la prima volta che il controllo sui riferimenti morti
ha girato in CI ha trovato due funzioni che sul server di sviluppo **non
esistevano**, perché i comandi che le cancellavano funzionavano solo su un
database cresciuto nel tempo.

**Servono entrambi**, e per motivi opposti.

---

## 4-bis. ⚠️ Il punto cieco peggiore: una regola che mente

C'è un modo di sbagliare che nessuno dei due presidi può intercettare da solo, ed
è successo davvero — vale la pena raccontarlo perché è il più difficile da vedere.

Il controllo sui riferimenti morti classifica ogni segnalazione, e alcune le
etichetta come **rumore**. Una di quelle etichette poggiava su un'affermazione
tecnica **sbagliata**: si era scritto che una certa forma di chiamata era lecita e
che era lo strumento a non capirla. Non era vero: lo strumento aveva ragione, e
sedici chiamate rotte sono state zittite per due giri di lavoro.

⚠️ **La regola sbagliata è stata perfino affinata due volte.** Ogni giro la
restringeva un po', trovava difetti veri, e con ciò **confermava** l'assunto di
partenza. Nessuno dei due ha chiesto se l'assunto fosse vero.

Da qui tre cose che valgono per qualunque presidio:

* **Un'etichetta rassicurante è più pericolosa di un errore.** Un errore lo si
  guarda; un'etichetta la si legge una volta e poi ci si fida. È lo stesso
  meccanismo per cui un test rosso registrato in baseline con la causa sbagliata è
  rimasto mesi a coprire una funzione che non partiva.
* **Chi scrive la regola non è la persona giusta per verificarla.** Quel difetto
  l'ha trovato un altro team, che aveva un motivo indipendente per guardare — non
  il presidio, e nemmeno chi l'aveva costruito.
* **Le esenzioni vanno scritte con la loro giustificazione tecnica**, non solo con
  il nome della categoria. Se accanto all'etichetta c'è la frase che la motiva,
  quella frase può essere letta e contestata. Se c'è solo l'etichetta, no.

Il presidio ha comunque fatto il suo mestiere: ha tenuto il conto, e quando la
regola è stata corretta i sedici difetti sono comparsi tutti insieme, con nome e
posizione. Quello che un presidio **non** può fare è accorgersi da solo che una
sua regola mente.

---

## 5. Se un cancello della CI diventa rosso

Prima di considerarlo un problema della CI, vale la pena tenere presente l'ordine
delle ipotesi:

1. **il difetto è reale** e la CI l'ha appena trovato — è il caso più frequente;
2. **il controllo misura un database incompleto**, perché è messo nel punto
   sbagliato della sequenza;
3. **il difetto esiste solo su un database costruito da zero** — vedi §4.

⚠️ La prima ipotesi che *non* va fatta è «la CI è rotta». Quando un controllo passa
in locale e fallisce in CI, di solito è il locale che sta nascondendo qualcosa.

Nota di sequenza, che è costata un giro rosso: in ZeroErp lo schema del database
**non ha un solo proprietario**. Liquibase costruisce quasi tutto, ma lo schema
`django` lo crea Django. Un controllo sulle definizioni del database deve girare
**dopo che entrambi hanno finito**, altrimenti misura un database a metà e segnala
problemi che non esistono.

---

## 6. Aggiungere un presidio nuovo

La ricetta, nell'ordine:

1. **Scrivi la misura prima del rimedio.** Serve a sapere quanto è grande il
   problema. Spesso la misura sposta le priorità: al primo giro sui riferimenti
   morti, il difetto più grave non era nemmeno nella lista iniziale.
2. **Classifica il rumore, non filtrarlo.** Un controllo che nasconde le righe che
   crede innocue non è più verificabile. Meglio farle uscire tutte con
   un'etichetta: se una è etichettata male, si vede. È successo — una regola
   troppo larga aveva catalogato come innocuo un difetto vero.
3. **Metti la misura in un posto solo.** Se la usano in due (il cancello e il
   test), devono leggere la stessa. Due copie prima o poi divergono, e da quel
   momento danno risposte diverse sullo stesso problema.
4. **Il registro nasce piccolo.** Se parte con trenta righe, nessuno lo leggerà.
   Meglio sanare prima e registrare solo ciò che è davvero una decisione presa.
5. **Fai fallire il controllo quando non può misurare.** Se manca un prerequisito,
   deve dirlo ad alta voce, non saltare in silenzio. Un cancello che passa perché
   non ha misurato niente è peggio di un cancello assente: dà la sensazione della
   copertura senza averla.
6. **Scrivi i limiti accanto al controllo.** Ogni misura ha punti ciechi. Se non
   sono scritti, il primo che legge un risultato verde crede che copra tutto.
7. **Motiva ogni esenzione con la sua ragione tecnica, non con la categoria.**
   Un'etichetta si legge e ci si fida; una frase che spiega *perché* quella riga è
   rumore può essere contestata da chi passa. Vedi §4-bis: è così che una regola
   fondata su un'affermazione falsa è sopravvissuta a due revisioni.

---

## 7. Limiti noti

Nessuno di questi controlli vede tutto, e conviene saperlo prima di fidarsi di un
risultato verde.

**Il controllo sui riferimenti morti non vede:**

* i riferimenti scritti in un **dato** invece che nel codice — una tabella nominata
  come testo dentro una tabella di configurazione. Per questo esiste una seconda
  misura sui dati di configurazione, ed è nata da un caso reale;
* i riferimenti che si risolvono verso la **cosa sbagliata**: una funzione che
  scrive il dato giusto nella colonna sbagliata compila benissimo. Il significato
  non si compila;
* i rami di codice che dipendono dai **parametri** con cui un controllo viene
  agganciato a una tabella, invece che dalla tabella stessa;
* più di un difetto per volta nello stesso punto: si ferma al primo. Per questo la
  bonifica va **ri-misurata dopo ogni passo**, non eseguita come una lista scritta
  una volta sola.

**La baseline non vede** ciò che i test non collaudano, e i test collaudano solo
ciò che i dati presenti permettono di collaudare.

**Entrambi non distinguono** un residuo da qualcosa lasciato lì di proposito.
Quella differenza sta nell'intenzione di chi l'ha scritto, e nessuna misura la
trova: è esattamente ciò per cui esiste il registro, con il suo motivo scritto.

### ⚠️ E c'è un difetto che non si presidia affatto

I tre lati del §3.3 e §3.4 hanno tutti una regola **meccanica**: il codice è a
catalogo? è dichiarato nel codice applicativo? ha un tipo di risposta? Sono
domande a cui si risponde confrontando due elenchi.

Ce n'è una quarta che non funziona così: **il messaggio descrive davvero la
condizione che solleva l'errore?** Un `IF NOT FOUND` che solleva un codice
chiamato «parametro non valido» è un difetto vero — l'operatore legge una frase
che non c'entra, e il tipo di risposta ne discende sbagliato — ma riconoscerlo
richiede di capire *cosa significa* quel ramo di codice.

Misurato il 2026-08-06 su 998 punti di sollevamento: l'euristica migliore ha dato
**~31 candidati per 7 difetti reali, il 23% di precisione**. Un cancello con quel
rapporto verrebbe disattivato entro una settimana — sarebbe il §4-bis in azione,
un presidio che grida al lupo finché nessuno lo ascolta più.

Perciò resta una **lente da rilanciare a mano** quando si apre un lotto di
lavoro, non un passo della CI. La convenzione dei nomi lo dice già da sola:
`scripts/sql/check_*` è uno strumento, `scripts/sql/guardrail_*` è un cancello.
**Sapere che una classe di difetti non è automatizzabile vale quanto
automatizzarne un'altra**: evita di costruire un presidio che mente.

---

## Riferimenti

* `docs/it/dev/work-done/brief-db-bonifica-riferimenti-morti.md` — la storia del primo giro (solo nel repository)
* `docs/it/dev/work-done/brief-db-codice-errore-strutturato.md` — perché il codice errore ha dovuto cambiare strada, e le due misure che lo presidiano (solo nel repository)
* [Linee guida API](../dev/api.md) §Tassonomia errori — il contratto visto dal lato backend
* [Automazione DB](automazione-db.md) — il framework che applica le regole strutturali
* `.codex/AGENTS.md` §Test — l'uso quotidiano della baseline
