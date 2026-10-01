# Guida – Presidi e registri del debito

> **Cos'è.** Come ZeroErp si accorge da solo che qualcosa si è rotto in silenzio,
> e come tiene il conto di ciò che è rotto e non è ancora stato sistemato.
>
> Riguarda i controlli che oggi esistono — i **riferimenti morti** nelle funzioni
> del database, la **baseline dei test rossi** e il **codice errore che arriva al
> backend** — e la forma che hanno in comune.
>
> ⭐ **Ce n'è una famiglia in più, nata a settembre 2026 e descritta altrove**:
> gli otto controlli sui **lavori automatici** (chi non dice di chi sono i dati
> che tocca, chi non ha un'identità, chi si è fermato senza che nessuno se ne
> accorgesse). Sono fatti con la stessa forma raccontata nel §2 e portano un
> pezzo in più — il **debito dichiarato** —, quindi vale la pena leggerli
> insieme: [I lavori automatici — capitolo 6](/guide/processi-automatici-classe-e-identita).
>
> ⚠️ Il pezzo in più è questo: in quei controlli una riga può restare **di
> proposito**, se qualcuno ha scritto perché. Cambia la domanda a cui il
> controllo risponde — non più «è vuoto?» ma «c'è qualcosa che *nessuno si
> aspettava*?» — e cambia il prezzo: dichiarare un debito **zittisce** il
> controllo su quel caso.
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

## 2-bis. Il terzo pezzo: il catalogo, cioè **chi la legge**

> ⭐ Nato il 2026-09-10, e chiude il §1 di questa guida in un punto che era
> rimasto aperto. Sede: [`dbops.presidi`](/dbzero/dbops/manual/presidi).

La misura e il registro rispondono a *«com'è messa adesso»* e *«che cosa sappiamo
già»*. Nessuno dei due risponde alla domanda che viene dopo:

> **Chi va a leggerli, e quando?**

Per i tre presidi del §3 la risposta c'è ed è un cancello: girano in CI, bloccano
l'integrazione, nessuno deve ricordarsene. Ma il database ha anche una trentina
di **viste di controllo** che nessun cancello legge — e lì la risposta era
*«qualcuno, prima o poi»*, che è la stessa risposta del promemoria del §1.

⛔ **Ed è costata quanto quel promemoria.** Il 2026-09-09 un lavoro notturno era
fallito **quattro notti di fila**. Le righe che lo dicevano stavano in
`dbops.vw_coda_lavori_da_guardare` — una vista che porta nel nome ciò che
serviva — e sono rimaste lì. Il presidio aveva funzionato perfettamente:
*guardare non è di nessuno*.

### Perché serve una tabella e non un elenco nel programma

Un programma può leggere le viste e mandarne il contenuto a una persona. Non può
decidere da solo **quali righe siano un allarme**, e le tre nature non si
deducono dal nome:

* una riga di `vw_coda_lavori_da_guardare` è un guasto **di adesso**;
* le righe di `vw_riferimenti_morti_da_sanare` sono un **debito noto**, e
  l'allarme è la voce che il registro **non conosce**;
* le duemila righe di `vw_trigger_functions` sono l'**inventario dei trigger**, e
  la loro presenza è la condizione normale.

Un elenco scritto nel programma sarebbe una seconda sorgente di verità, e
divergerebbe alla prima vista nuova: il presidio nuovo nascerebbe **fuori** dal
giro, in silenzio, cioè lo stesso guasto che il catalogo chiude.

⭐ E non è un'ipotesi: la **trentaduesima** vista è nata il 2026-09-09, lo stesso
giorno in cui il brief ne contava trentuno e argomentava proprio così.

### Le due regole che lo tengono onesto, e sono le stesse del §2

| Regola | Dove vive |
|---|---|
| Senza un motivo scritto la riga non si aggiunge | **vincolo del database** (`nota` non vuota) |
| Una vista nuova non può nascere fuori dal catalogo | **test** (`test-catalogo-presidi-v1.sql`, verso 1) |
| Una riga che non trova più la sua vista va tolta | **test** (stesso file, verso 2) |

⚠️ **E il debito si tiene con un registro, non con una soglia.** La tentazione è
una colonna «oggi sono 508, l'allarme scatta a 509». Un numero vede solo il
totale ed è cieco sullo **scambio**: un debito saldato e un difetto nuovo
comparsi lo stesso giorno lasciano il conteggio fermo. È il §C5 di
`analisi-presidi-percorso-storto.md` — *«un numero scritto a mano che
invecchia»* — applicato a un presidio invece che a un commento.

⛔ **Attenzione al verso.** Dove la vista porta una colonna di stato, il catalogo
dichiara l'unico stato **atteso** e l'allarme è tutto il resto — non l'elenco
degli stati di allarme. Con la seconda forma uno stato *nuovo*, aggiunto domani,
non sarebbe nell'elenco e cadrebbe nel **silenzio**: è l'unico verso in cui un
presidio marcisce senza che nessuno se ne accorga.

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

  ⚠️ **Questa seconda ragione si è ristretta il 2026-08-07, e va detta com'è
  adesso.** Da quando l'elenco delle policy è **generato dal catalogo**, un
  codice a catalogo — anche fuori convenzione — la sua risposta ce l'ha. Il
  rischio non è più permanente: è la **finestra** fra il migrate che crea il
  codice e il commit con cui il backend rigenera, e in quell'intervallo a
  decidere fra 400 e 500 resta il prefisso. La regola vale ancora, ma per un
  motivo più stretto — e una regola che si spiega con un fatto scaduto insegna
  una cosa falsa a chi si fida.

* **il nome del campo sbagliato finisce nel canale di qualcun altro.** Dal
  2026-08-08 l'eccezione porta anche **quale campo** l'operatore deve correggere,
  e il frontend ci accende un bordo rosso. È un secondo canale con lo stesso
  difetto possibile del primo — con un aggravante: un mittente abusivo non
  farebbe fallire niente, farebbe **evidenziare il campo sbagliato**, mandando
  l'operatore a correggere un dato che è giusto. È peggio di non evidenziarne
  nessuno, ed è il motivo per cui il controllo (F) è nato **insieme al canale**,
  quando i mittenti abusivi erano zero: il controllo (A) invece dovette
  rincorrere, perché il suo canale era già in uso.

| Pezzo | Dove |
|---|---|
| La sede unica che scrive i campi | `script.fn_log_and_raise_error` |
| Il codice viaggia in | `CONSTRAINT` (dal 2026-08-05) |
| Il **nome del campo** viaggia in | `COLUMN` (dal 2026-08-08) — contratto gemello |
| Il registro dei nomi ereditati | `dbops.messaggi_errore_codici_legacy` — **a zero, e non si droppa** |
| Il ritiro di un nome vecchio | `config.codici_errore.obsoleto_dal` |
| Cancello automatico | `scripts/sql/guardrail_codice_errore_strutturato.sql` (passo CI) — controlli (A)…(F) |
| Test della suite | `db/pgtap/script/test-fn-log-and-raise-error-constraint-codice.sql` · `db/pgtap/config/test-codici-errore-obsoleto-dal.sql` · `db/pgtap/vendite/test-ordini-guard-transizione-v1.sql` (test 8) |

> ⚠️ **Due righe di questa tabella erano vecchie fino al 2026-08-09**, e vale la
> pena dire come: `obsoleto_dal` **ha cambiato casa** — stava su
> `config.messaggi_errore`, che è chiavata *(codice, lingua)*, quindi si poteva
> ritirare un codice in italiano e lasciarlo vivo in inglese senza che nulla
> protestasse. Dal changeSet `20260807-13` vive su `config.codici_errore`, che ha
> **una riga per codice**: il ritiro appartiene al codice, non alla frase.
> E il file di test citato non esisteva più: era stato spostato in `config/` col
> nome nuovo. Un riferimento morto in una guida sui presidi è il difetto che la
> guida stessa descrive.

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
accanto alla voce (`config.codici_errore.obsoleto_dal`). La voce resta, il
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

### 3.5 Il significato di un codice, che si allarga da solo

**Cosa sorveglia.** Un codice errore nasce per dire *una* cosa. Poi qualcuno lo
usa «anche per questo caso qui», una volta, e sembra ragionevole. La
sessantottesima volta è `E_GENERICO`: un'etichetta che copre problemi diversi,
che chiedono reazioni diverse, e che a video diventano tutti lo stesso messaggio.

⭐ **Nessuno crea un codice generico di proposito.** È il motivo per cui questo
presidio non guarda lo stato, ma il **cambiamento**.

#### Perché non è un cancello sullo stato

La domanda «questo codice è generico?» ha bisogno di leggere, per ogni punto che
lo solleva, la condizione che lo precede — e di capirla. La misura che lo fa
(`dbops.vw_codici_errore_forme_condizione`) ci riesce per **75 codici su 344**:
per gli altri **dichiara di non sapere**, ed è la cosa più onesta che fa.

⚠️ Un cancello che capisce un caso su cinque **boccia a caso e passa a caso**. E
boccerebbe anche i codici legittimamente trasversali — `E_PERMESSO_NEGATO` è
ovunque per costruzione, e non è un difetto. Dopo due blocchi sbagliati qualcuno
lo spegne, e **un presidio spento è peggio di uno assente**: nel frattempo ha
convinto tutti di esserci.

#### La forma che funziona

> Non «questo codice è generico?» — che richiede copertura totale — ma **«questo
> codice ha acquistato una condizione che non aveva?»**, che la misura sa dire
> con certezza sui 75 che legge.

È lo stesso schema della baseline dei test rossi (§3.2): un file committato con
lo stato noto, e la CI che fallisce sul **delta**.

| Situazione | Esito |
|---|---|
| un codice **acquista** una famiglia di condizione | 🔴 rosso, la CI si ferma |
| un codice **nuovo** nasce già con due famiglie | 🔴 rosso — nasce storto |
| un codice **perde** una famiglia (si restringe) | 🔵 non è un difetto, **ma la baseline va stretta subito** |
| un codice sparisce dalla misura | 🔵 si allinea |

| Pezzo | Dove |
|---|---|
| Lo scatto | `scripts/sql/codici_errore_famiglie_snapshot.sql` |
| Il confronto e il `--update` | `scripts/codici-errore-baseline.sh` |
| La baseline committata | `db/baseline-codici-errore-famiglie.tsv` |
| Cancello automatico | passo CI, subito dopo il guardrail |

⛔ **La regola che vale più dello script:** se diventa rosso, **non si rigenera
la baseline per far passare la CI**. La riga rossa è la richiesta di una
decisione — o serve un codice nuovo, o l'uso è legittimo e la baseline si
aggiorna **con la ragione nel messaggio di commit**.

#### ⚠️ Il buco che aveva alla nascita, trovato dal primo uso vero

Guardava solo le famiglie **aggiunte**. Quando un codice si è ristretto per la
prima volta — uno scorporo fatto un'ora dopo — il presidio **ha taciuto**.

Un restringimento non è un difetto. Ma finché la baseline non viene stretta,
**continua a dichiarare ammessa** la famiglia che il codice non ha più: il giorno
in cui qualcuno ce la rimette, il confronto la trova già in baseline e tace.

> ⭐ La baseline marciva **nel verso permissivo** — l'unico verso in cui un
> presidio si degrada senza che nessuno se ne accorga.

È il caso da tenere a mente ogni volta che si scrive un confronto con una
baseline: **un presidio va guardato anche nel verso in cui le cose migliorano**,
perché è lì che smette di sorvegliare senza diventare rosso.

#### Il limite, detto qui e non scoperto dopo

Presidia i **75 codici che la misura sa leggere**, non i 344. Non è copertura
totale ed è inutile fingere il contrario: è il rubinetto sui codici vivi e
*leggibili*, ed è molto più di quello che c'era prima, che era niente.

### 3.6 Uno stato previsto dal modello e mai scritto

**Cosa sorveglia.** Il `CHECK` di una colonna di stato — `stato IN ('DRAFT',
'CONFIRM', 'POSTED', 'CANCEL')` — è una promessa: ogni valore ammesso è uno
stato che il sistema sa raggiungere. Se un valore è ammesso e **nessuno lo
scrive mai**, la promessa è vuota, e il sistema è muto proprio sul caso che quel
valore doveva raccontare. Di regola è il fallimento: `ERRORE` è stato per mesi
nel `CHECK` degli esiti di un lotto, con un contatore dedicato nella summary, e
nessuno lo scriveva — le corse chiudevano in `COMPLETATO` con un documento
rifiutato.

**Come misura.** Il perimetro non è un elenco: è ogni `CHECK` di appartenenza su
una colonna il cui nome dice «stato», letto dal catalogo di PostgreSQL. Per ogni
valore la misura (`dbops.vw_stati_check_scrittori`) cerca **chi lo scrive**: il
default della colonna, una funzione che scrive la tabella col valore nel corpo,
o una funzione che chiama uno scrittore passandogli il valore. Non conta le
righe: guarda la struttura, non il contenuto.

**Il registro** (`dbops.stati_check_dichiarazioni`) porta un **canale**, perché
il database non vede tutti gli scrittori: una parte dei valori li scrive
l'applicazione, e quelli il database non può che dichiararli. Il canale dice chi
verifica la riga:

| `canale` | Che cosa dice la riga | Chi la verifica |
| --- | --- | --- |
| `APPLICAZIONE` | «questo valore lo scrive un repository Python» | il test del backend (`apps/core/tests/test_stati_check_scrittori_python.py`): il valore deve comparire in un file che scrive quella tabella — o in uno che la scrive **attraverso** il suo repository, il service che passa il valore; se sparisce, rosso. E nel verso opposto: un valore `NON_DICHIARATO` che Python scrive va dichiarato `APPLICAZIONE`, non sanato a database |
| `ESENTE` | «non lo scrive nessuno, o il criterio non lo vede — e sappiamo perché» | il pgTAP, nel verso di ritiro: se uno scrittore compare a database, la riga va tolta |

⚠️ `ESENTE` non vuol dire «non scritto»: vuol dire che il **criterio** non lo
vede. Il caso che l'ha insegnato è un log che riceve lo stato **copiandolo** dal
suo padre: scritto mille volte, e nessun valore compare in nessuna funzione.
Stringere il `CHECK` — la prima idea — avrebbe rotto il log.

**La lista di lavoro** (`dbops.vw_stati_check_da_sanare`) è un cancello:
`db/pgtap/dbops/test-stati-check-scrittori-v1.sql` la fa rossa in CI su un
valore che nessuno scrive e nessuno ha dichiarato, e su una riga di registro
che non serve più.

#### Il limite, detto qui e non scoperto dopo

Il criterio è **testuale**: nominare un valore in un `WHERE` dentro una funzione
che scrive la tabella conta come scriverlo; un valore che passa per tre funzioni
resta invisibile; una copia da un'altra colonna non si vede. Ognuno di questi
limiti è scritto nel commento della vista e ha un caso costruito nel pgTAP, così
che chi legge un verde sappia esattamente che cosa copre.

⭐ **E la misura stessa ha avuto un difetto, ed è il caso da ricordare.** Il
primo conteggio (19 settembre) trovava 18 colonne; il criterio definitivo ne
trova 32. Non era cambiato il database: la prima regex vedeva una sola delle
**due** scritture con cui PostgreSQL stampa lo stesso `CHECK` (colonna `text`
contro colonna `varchar`). *Anche la misura è un programma, e può avere il suo
difetto* — per questo il pgTAP tiene l'elenco delle 32 colonne come prova che il
perimetro non si è ristretto.

Origine: `docs/it/dev/work-done/brief-db-presidio-stati-mai-scritti.md`.

---

## 4. Perché alcuni girano da soli e uno no

Sì: i cancelli automatici non vanno lanciati a mano. Ma non sono la stessa cosa
messa in posti diversi — sono **controlli di natura diversa**, e questo paragrafo
spiega perché ognuno sta dove sta.

Il confronto qui sotto mette a fuoco i due estremi, il §3.1 (cancello in CI) e il
§3.2 (baseline da lanciare): il §3.3 e il §3.4 appartengono alla stessa famiglia
del §3.1 e vale per loro tutto ciò che si dice del cancello automatico.

⭐ **Il §3.5 è il primo che sta in mezzo, e non per caso**: è un cancello
automatico *costruito su una baseline*. Ha la CI del §3.1 e il file committato
del §3.2, e prende da entrambi la parte che serve — il rosso che ferma, e il
delta invece dello stato assoluto. Quando un difetto non si sa misurare in
assoluto ma si sa riconoscere quando **cambia**, è questa la forma da copiare.

Il §3.4 è
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

**Il rubinetto degli accumulatori (§3.5) non vede:**

* i **269 codici su 344** per cui la misura dichiara di non saper leggere la
  guardia. Su quelli tace, ed è giusto che taccia: un presidio che tira a
  indovinare si spegne da solo dopo il secondo falso allarme;
* un codice che nasce generico **e resta l'unico del suo genere**: se le sue due
  famiglie sono entrambe illeggibili, non c'è delta da vedere;
* ⚠️ e la sua baseline è **misurata su un database**. Quello di sviluppo non è
  ricostruito da zero: confrontare una corsa in CI con una baseline presa in
  sviluppo produce finte regressioni. È lo stesso difetto delle due baseline
  pgTAP, e la cura è la stessa (`CODICI_BASELINE`).

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
* [Come si scrive un test pgTAP](pgtap-come-si-scrive-un-test.md) — l'uso quotidiano della baseline
* [Gestione dei messaggi di errore e generazione log](Messaggi-di-Errore-e-Generazione-Log.md) — il catalogo, la classe di un codice e il canale del campo, visti dal lato del dominio

---
{% include-markdown "signature-core.md" %}
