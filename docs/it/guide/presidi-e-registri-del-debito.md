# Guida — Presidi e registri del debito

> **Ultimo aggiornamento**: 4 novembre 2026
>
> **Destinatari**: sviluppatori database e backend, e chi costruisce o mantiene un
> controllo automatico (un guardrail, un pgTAP di presidio, una vista di controllo)
>
> **Vedi anche** — schemi DB:
>
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo delle viste di controllo: che cosa significa una riga, con che cadenza si guarda, a chi tocca
> * [dbops.presidi_testi](/dbzero/dbops/tabelle/presidi_testi) — cosa vuol dire una riga e cosa fare, per chi deve agire
> * [dbops.presidi_cause](/dbzero/dbops/tabelle/presidi_cause) — a chi tocca, causa per causa, sui presidi che elencano guasti diversi
> * [dbops.riferimenti_morti_esenzioni](/dbzero/dbops/tabelle/riferimenti_morti_esenzioni) — il registro dei riferimenti morti
> * [dbops.messaggi_errore_codici_legacy](/dbzero/dbops/tabelle/messaggi_errore_codici_legacy) — il registro dei nomi di codice fuori convenzione
> * [dbops.codici_errore_senza_policy](/dbzero/dbops/tabelle/codici_errore_senza_policy) — il registro dei codici senza tipo di risposta
> * [dbops.stati_check_dichiarazioni](/dbzero/dbops/tabelle/stati_check_dichiarazioni) — il registro degli stati ammessi che nessuna funzione scrive
>
> **Vedi anche** — funzioni e viste DB:
>
> * [dbops.fn_check_funzioni_riferimenti_morti](/dbzero/dbops/funzioni/fn_check_funzioni_riferimenti_morti) — la misura dei riferimenti morti
> * [dbops.vw_codici_errore_da_dichiarare](/dbzero/dbops/views/vw_codici_errore_da_dichiarare) — la misura del tipo di risposta
> * [dbops.vw_codici_errore_forme_condizione](/dbzero/dbops/views/vw_codici_errore_forme_condizione) — la misura delle famiglie di condizione
> * [dbops.vw_stati_check_scrittori](/dbzero/dbops/views/vw_stati_check_scrittori) — chi scrive ogni stato ammesso
> * [dbops.fn_conta_presidio](/dbzero/dbops/funzioni/fn_conta_presidio) — il conteggio onesto di un presidio letto senza utente
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — la sede unica che solleva un errore
>
> **Vedi anche** — guide correlate:
>
> * [I lavori automatici](/guide/processi-automatici-classe-e-identita) — i controlli sui lavori automatici (capitolo 6), il digest e chi lo sorveglia
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — l'uso quotidiano della baseline, in sviluppo e in CI
> * [Messaggi di errore e generazione log](/guide/Messaggi-di-Errore-e-Generazione-Log) — il catalogo dei codici, la classe e i canali, dal lato del dominio
> * [Automazione DB](/guide/automazione-db) — il framework che applica le regole strutturali
> * [Linee guida API](/dev/api) §Tassonomia errori — il contratto dell'errore visto dal backend

---

## In una frase

Un **presidio** è un controllo che si accorge da solo che qualcosa si è rotto in
silenzio. È fatto di una **misura**, di un **registro del debito** e di qualcuno
che **legge** il risultato al momento giusto: senza uno dei tre pezzi non presidia
niente.

Questa guida descrive la forma comune (§1–§2), i presidi del database e del
trasporto degli errori (§3), dove gira ognuno e perché (§4), e come se ne
costruisce uno nuovo (§6). I controlli sui **lavori automatici** hanno la stessa
forma e un pezzo in più — il debito dichiarato, che zittisce di proposito un caso
noto —: stanno nella guida [I lavori automatici](/guide/processi-automatici-classe-e-identita),
capitolo 6.

---

## 1. Un promemoria non è un presidio

Una segnalazione lasciata in un commento — *«da verificare se la funzione va
rimossa»* — non presidia niente. È un promemoria, e i promemoria non si rileggono:
la verifica non viene fatta, e il difetto si ripresenta quando qualcuno esegue
quel codice, cioè nel momento peggiore.

Perché una cosa sia davvero presidiata serve qualcosa che **protesti da solo**,
al momento giusto, senza che nessuno debba ricordarsene. I controlli descritti
sotto non sono strumenti presi a caso: hanno tutti la stessa forma, e conviene
conoscerla prima dei dettagli.

---

## 2. La forma comune

### 2.1 La misura e il registro

**La misura** dice qual è la situazione adesso. Deve essere ripetibile e non
opinabile: lanciata oggi e domani, se nulla è cambiato, dà la stessa risposta.

**Il registro del debito** dice quali problemi sappiamo già di avere e perché
sono ancora lì. Serve perché la realtà non è mai a zero: c'è sempre qualcosa di
rotto che si è deciso consapevolmente di non sistemare subito.

⚠️ **Il registro è un debito, non un elenco di eccezioni.** È la differenza che
tiene questi controlli utili invece di farli diventare rumore di fondo:

* un **elenco di eccezioni** può solo allungarsi: ogni volta che qualcosa dà
  fastidio lo si aggiunge, e dopo un po' nessuno lo legge più e i problemi veri
  ci si nascondono dentro;
* un **registro del debito** deve **calare**: ogni voce ha una data, e dice perché
  è ancora aperta e cosa la chiuderebbe.

Per tenerlo onesto servono due regole, e stanno in due posti diversi apposta:

| Regola | Dove vive | Perché lì |
|---|---|---|
| Senza un motivo scritto la voce non si aggiunge | vincolo del database | non è un controllo che si può dimenticare di lanciare: è il database che rifiuta la riga |
| Una voce che non serve più va tolta | test o cancello | per saperlo bisogna ri-misurare, e una misura non può essere un vincolo |

Senza la seconda regola il registro può solo crescere, e torna a essere un elenco
di eccezioni.

⭐ **Un registro a zero non si toglie.** Due dei registri di questa guida sono
oggi vuoti (§3.3, §3.4) e restano: un registro vuoto è un registro **in pari**, ed
è l'unico modo per distinguere «nessun debito» da «nessuno lo sta più misurando».
Toglierlo costringerebbe a toccare il cancello che lo legge mentre è verde, e
toglierebbe il posto pronto per la prossima eredità.

⚠️ **Il debito si tiene con un registro, non con una soglia.** La tentazione è
una colonna «oggi sono 508, l'allarme scatta a 509». Un numero vede solo il
totale ed è cieco sullo **scambio**: un debito saldato e un difetto nuovo comparsi
lo stesso giorno lasciano il conteggio fermo, e il controllo tace.

### 2.2 Il terzo pezzo: chi legge

La misura e il registro rispondono a *«com'è messa adesso»* e *«che cosa sappiamo
già»*. Resta la domanda che viene dopo: **chi va a leggerli, e quando?**

Per i presidi del §3 la risposta è un **cancello**: girano in CI e bloccano
l'integrazione. Per le **viste di controllo** del database — qualche decina, e
crescono — la risposta è il catalogo [`dbops.presidi`](/dbzero/dbops/tabelle/presidi),
letto da due consumatori:

* il **digest** dei presidi, un comando del backend lanciato da due timer systemd
  (giornaliero e settimanale), che manda per posta le viste da guardare a quella
  cadenza;
* il **pannello Processi automatici** dell'area Amministrazione, che mostra lo
  stesso quadro a chi è collegato.

⭐ Il programma non contiene nessun elenco di viste né di soglie: che cosa si
guarda, con che cadenza e che cosa significa una riga lo dice il catalogo. Un
elenco scritto nel programma sarebbe una seconda sorgente di verità, e una vista
nuova nascerebbe **fuori** dal giro, in silenzio.

#### Che cosa dice il catalogo, per ogni vista

| Colonna | Che cosa dice |
| --- | --- |
| `natura` | che cosa significa una riga: un guasto adesso (`ZERO`), un debito noto (`REGISTRO`), una coda o una tendenza (`LAVORAZIONE`), un controllo già fatto da un cancello (`CANCELLO`), un panorama che elenca anche i sani (`INVENTARIO`) |
| `colonna_stato`, `stato_atteso` | per le viste con una colonna di stato, l'**unico** stato atteso: l'allarme è tutto il resto |
| `registro` | la tabella che tiene le voci note, sui presidi di natura `REGISTRO` |
| `cadenza` | ogni quanto si guarda; `MAI` per inventari e cancelli, che non vanno nel digest |
| `perimetro` | se il conteggio è onesto letto da un programma senza utente, o se va fatto con [`fn_conta_presidio`](/dbzero/dbops/funzioni/fn_conta_presidio) |
| `chi_agisce` | a chi tocca spegnerlo: `AMMINISTRATORE`, `SISTEMISTA` o `SVILUPPO` |
| `colonna_variante` | sui presidi che elencano guasti **diversi**, la colonna da cui si legge la causa di ogni riga; testo e destinatario si scelgono causa per causa ([`presidi_cause`](/dbzero/dbops/tabelle/presidi_cause)) |

Il dettaglio di ogni colonna è nella scheda della tabella. Qui conta la ragione
di tre scelte:

* ⛔ **Le nature non si deducono dal nome.** Su una vista una riga è un guasto di
  adesso, su un'altra è un debito noto e l'allarme è la voce che il registro non
  conosce, su una terza ci sono duemila righe ed è la condizione normale. Un
  avviso che non distingue i tre casi si apre con l'inventario, e un avviso
  rumoroso viene ignorato al secondo invio.
* ⛔ **Si dichiara lo stato atteso, non quelli di allarme.** Con un elenco degli
  stati di allarme, uno stato *nuovo* aggiunto domani non sarebbe nell'elenco e
  cadrebbe nel **silenzio**: è l'unico verso in cui un presidio marcisce senza che
  nessuno se ne accorga.
* ⭐ **Il catalogo parla a due lettori.** La `nota` e il commento della vista sono
  scritti per chi **mantiene** il presidio; chi lo legge nel pannello o nel digest
  deve **agire**, e ha due domande sole — cosa vuol dire, cosa devo fare — a cui
  rispondono `significato` e `azione` di
  [`presidi_testi`](/dbzero/dbops/tabelle/presidi_testi). I due testi non si
  sostituiscono.

#### Le regole che tengono onesto il catalogo

| Regola | Dove vive |
|---|---|
| Senza un motivo scritto la riga non si aggiunge | **vincolo del database** (`nota` non vuota) |
| Un presidio che può accendersi dice a chi tocca spegnerlo | **vincolo del database** (`chi_agisce`, obbligatoria tranne su `INVENTARIO`) |
| Inventari e cancelli non vanno nel digest | **vincolo del database** (cadenza `MAI`) |
| Una vista di controllo nuova non può nascere fuori dal catalogo | **test** `db/pgtap/dbops/test-catalogo-presidi-v1.sql`, primo verso |
| Una riga che non trova più la sua vista va tolta | **test**, stesso file, verso opposto |
| Ogni presidio che può accendersi ha le sue parole, e ogni causa le sue | **test** `db/pgtap/dbops/test-presidi-testi-v1.sql` |

Chi sorveglia il digest stesso — se muore lui nessuno manda il messaggio che lo
dice — è nella guida [I lavori automatici](/guide/processi-automatici-classe-e-identita).

---

## 3. I presidi del database e degli errori

### 3.1 Riferimenti morti nelle funzioni del database

**Cosa sorveglia.** PostgreSQL non tiene traccia di cosa c'è scritto dentro una
funzione. Se si cancella una tabella o si rinomina una colonna, le funzioni che le
nominavano restano lì, apparentemente sane, e **non vengono più ricontrollate**.
Si scoprono rotte solo quando qualcuno le esegue.

**Come funziona.** L'estensione `plpgsql_check` **compila davvero** il corpo di
ogni funzione, come farebbe la prima esecuzione: vede tabelle e colonne, e vede
anche i rami di codice che nessuno ha mai eseguito. Una seconda misura guarda i
nomi di oggetti scritti come **dato** nelle tabelle di configurazione, che il
compilatore non vede.

| Pezzo | Dove |
|---|---|
| La misura | [`dbops.fn_check_funzioni_riferimenti_morti`](/dbzero/dbops/funzioni/fn_check_funzioni_riferimenti_morti) |
| Il registro | [`dbops.riferimenti_morti_esenzioni`](/dbzero/dbops/tabelle/riferimenti_morti_esenzioni) |
| Le due viste | [`vw_riferimenti_morti_da_sanare`](/dbzero/dbops/views/vw_riferimenti_morti_da_sanare) · [`vw_riferimenti_morti_rientrati`](/dbzero/dbops/views/vw_riferimenti_morti_rientrati) |
| Strumento a mano | `scripts/sql/check_funzioni_riferimenti_morti.sql` |
| Cancello automatico | `scripts/sql/guardrail_riferimenti_morti.sql` (passo CI) |
| Test della suite | `db/pgtap/dbops/test-riferimenti-morti-v1.sql` |

**Quando diventa rosso** le strade sono due, e nessuna è ignorarlo: ripararlo —
quasi sempre è una riga — oppure registrarlo nel debito **con un motivo scritto**.

⚠️ La misura ricompila centinaia di funzioni a ogni lettura: non è una vista da
interrogare per abitudine, e infatti il catalogo dei presidi le dà una cadenza
lunga.

### 3.2 Baseline dei test rossi

**Cosa sorveglia.** Una parte della suite pgTAP è rossa da tempo, quasi sempre
perché le fixture sono rimaste indietro rispetto a controlli entrati dopo. In
quella situazione un test rosso non dice più niente: è normale che ce ne siano,
quindi nessuno guarda.

La baseline separa i **rossi già noti** dai **rossi nuovi**, e solo i secondi sono
una notizia. Lo script `scripts/pgtap-baseline.sh` riesegue la suite (tutta, per
schema o solo i file modificati) e segnala tre cose: le **regressioni** (rosso
nuovo, esce con errore), i **rientrati** (ora verdi: la riga va tolta) e il
silenzio sui rossi già noti. I comandi sono nell'[area tecnica](#area-tecnica-esempi).

Le baseline sono **due**, perché le popolazioni sono due:

| Baseline | Dove si misura | Chi la aggiorna |
| --- | --- | --- |
| `db/pgtap/baseline-rossi.tsv` | il database di sviluppo, con dati veri | chi lavora, con `--update` dopo aver sanato |
| `db/pgtap/baseline-rossi-ci.tsv` | il database della CI, ricostruito da zero | **solo la CI**: in locale `--update` su questo file è rifiutato |

Confrontare una corsa con la baseline dell'altra popolazione produce decine di
finte regressioni. Per lo stesso motivo una baseline vale solo se è stata presa
**con lo stesso ruolo di connessione** (owner o utente applicativo): la prima
riga del file lo dichiara, e lo script rifiuta il confronto fra corse
disomogenee. Il dettaglio d'uso è nella guida
[Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test).

⚠️ **Una classificazione sbagliata nasconde un problema vero.** Un test
registrato come «errore di fixture» può coprire una funzione che non parte
proprio. Quando si aggiunge una riga alla baseline vale la pena capire *perché* è
rossa, invece di catalogarla per somiglianza.

⚠️ **Un file che fallisce nella fixture non esegue nessuna verifica.** La sua
copertura vale **zero**, non «parziale» — ed è peggio di un'area scoperta, perché
sembra coperta.

### 3.3 Il codice errore che arriva al backend

**Cosa sorveglia.** Quando il database rifiuta un'operazione manda al backend un
**codice**, ed è da quel codice che dipendono la risposta HTTP (409 sul duplicato,
404 sul non trovato, 403 sul vietato) e il messaggio che l'operatore legge a
video. L'errore lo solleva una sede unica,
[`script.fn_log_and_raise_error`](/dbzero/script/funzioni/fn_log_and_raise_error),
che riempie tre campi dell'eccezione:

| Campo | Che cosa porta | Che cosa ne fa il frontend |
| --- | --- | --- |
| `CONSTRAINT` | il **codice** | sceglie il tipo di risposta e la frase |
| `COLUMN` | il **campo** che l'operatore deve correggere | accende un bordo rosso sul campo |
| `DATATYPE` | il **bersaglio**: su quali entità si riferisce l'errore | propone un pulsante «vai al documento» |

**Come si rompe**, senza fare rumore:

* **qualcun altro scrive nello stesso campo.** Sollevare un errore a mano è
  possibile ovunque. Un mittente abusivo non fa fallire niente: fa **rispondere la
  cosa sbagliata**, che è peggio, perché nessuno se ne accorge. E il danno cresce
  col canale: un codice sbagliato fa decidere male una risposta, un campo
  sbagliato manda l'operatore a correggere un dato giusto, un bersaglio sbagliato
  gli apre un documento che non c'entra;
* **nasce un codice con un nome fuori convenzione.** I codici si chiamano
  `E_MODULO_TIPO` (i warning `W_…`). Le risposte del backend sono **generate dal
  catalogo**, quindi un codice a catalogo la sua risposta ce l'ha; ma nella
  finestra fra il migrate che crea un codice e il commit con cui il backend
  rigenera, a decidere fra un errore dell'utente e un errore di server resta il
  prefisso;
* **si usa un codice ritirato**, che l'operatore leggerebbe come un messaggio vuoto
  o superato.

Il cancello è `scripts/sql/guardrail_codice_errore_strutturato.sql` (passo CI).
Fallisce se trova:

| Controllo | Che cosa vieta |
| --- | --- |
| (A) | un mittente diverso dalla sede unica sul canale `CONSTRAINT` |
| (B) | un codice nuovo fuori convenzione e non registrato nel debito |
| (C) | una voce del registro che non serve più (il debito è pagato: la riga va tolta) |
| (D) | una funzione viva che solleva un codice ritirato |
| (E) | un codice di warning sollevato invece che scritto nel diario |
| (F) | un mittente diverso dalla sede unica sul canale `COLUMN` |
| (G) | un mittente diverso dalla sede unica sul canale `DATATYPE` |
| (H) | una regola di blocco delle colonne che nomina un codice non vivo |

⭐ **I controlli (F) e (G) sono nati insieme ai loro canali**, a zero mittenti
abusivi: un presidio che parte da zero non chiede mai a nessuno di sanare un
arretrato. È la forma da preferire ogni volta che si apre un canale nuovo.

⭐ **Il controllo (H) guarda un punto che solleverà in futuro.** Una riga di
[`dbops.automation_lock_columns`](/dbzero/dbops/tabelle/automation_lock_columns)
non solleva niente finché l'automazione non genera il trigger, e da quel momento
lo solleva per sempre: un codice sbagliato lì nasce in silenzio e si manifesta
alla prima rigenerazione, quando nessuno lo sta più guardando.

| Pezzo | Dove |
|---|---|
| La sede unica che scrive i campi | `script.fn_log_and_raise_error` |
| Il registro dei nomi ereditati | [`dbops.messaggi_errore_codici_legacy`](/dbzero/dbops/tabelle/messaggi_errore_codici_legacy) — **a zero, e non si toglie** (§2.1) |
| Il ritiro di un codice | `config.codici_errore.obsoleto_dal` |
| Cancello automatico | `scripts/sql/guardrail_codice_errore_strutturato.sql` (passo CI) — controlli (A)…(H) |
| Test della suite | `db/pgtap/script/test-fn-log-and-raise-error-constraint-codice.sql` · `db/pgtap/config/test-codici-errore-obsoleto-dal.sql` · `db/pgtap/vendite/test-ordini-guard-transizione-v1.sql` |

⚠️ **Il registro dei nomi non chiede un motivo per riga**, al contrario di quello
dei riferimenti morti. Là ogni voce è una decisione a sé; qui tutte le voci
sarebbero **una sola decisione** — l'eredità di un periodo in cui la convenzione
non era presidiata — e un motivo obbligatorio produrrebbe tante copie della stessa
frase. La ragione sta scritta una volta, sulla tabella. E una famiglia nuova con
una semantica sua (come i warning `W_`) non si registra: si allarga la
convenzione.

#### Perché un codice non si cancella, si ritira

Quando un codice viene sostituito, verrebbe voglia di cancellare la voce vecchia.
**Quasi mai si può**: ogni errore registrato lascia una riga di diario che *punta*
alla voce del catalogo, e finché quel diario esiste la voce non si tocca.
Cancellare il diario per riordinare il catalogo sarebbe distruggere una prova per
sistemare un'etichetta — e una cancellazione del genere **riesce sulle
installazioni nuove e fallisce su quelle che hanno una storia**: la prova
automatica direbbe che va tutto bene proprio dove non c'è niente da rompere.

Perciò un codice si **ritira**, scrivendo la data accanto alla voce
(`config.codici_errore.obsoleto_dal`, una riga per codice: il ritiro appartiene al
codice, non alla frase in una lingua). La voce resta, il diario resta agganciato,
e chi dovesse ancora incontrare quell'errore continua a leggere la spiegazione di
sempre.

⚠️ Una data di ritiro, da sola, è una dichiarazione di intenti: qualcuno può
sempre tornare a usare il codice. Per questo il controllo (D) verifica che
**nessuna funzione viva sollevi un codice ritirato**: senza, la data sarebbe
l'etichetta rassicurante di cui parla il §5.

⚠️ Prima di togliere dal catalogo un codice che nessuno solleva, va distinto se è
**superato** o **non ancora agganciato**: può essere un residuo, oppure un pezzo
di lavoro in corso a cui manca il collegamento. Cancellare il secondo tipo rompe
il lavoro di qualcun altro.

### 3.4 Il tipo di risposta — il terzo lato

**Cosa sorveglia.** Il §3.3 garantisce che il codice **arrivi** al backend e che
l'operatore legga la frase giusta. Ma sullo stesso codice deve andare d'accordo un
terzo elenco: le policy del backend che dicono, per ogni codice, **che tipo di
risposta** dare — «non esiste», «non ti è permesso», «è in conflitto con lo stato
attuale», «hai sbagliato a compilare» (`backend/apps/core/services/error_policies.py`).

| Direzione | Presidiata da |
|---|---|
| le parole usate dal codice applicativo sono dichiarate | `backend/apps/core/tests/test_error_codes_declared_guardrail.py` |
| le parole che dice il database sono a catalogo | guardrail SQL del §3.3 |
| le parole che dice il database hanno un tipo di risposta | `backend/apps/core/tests/test_error_codes_db_policy_guardrail.py` |

**Cosa succede senza.** L'operatore legge comunque la frase giusta — viene dal
catalogo — ma il tipo di risposta resta appiattito su «hai sbagliato a compilare»
anche quando la verità è «non esiste» o «non ti è permesso». Chi legge capisce lo
stesso; chi deve **reagire** — la pagina che decide se mostrare un avviso o
riportarti indietro, un allarme, un tentativo automatico — no.

| Pezzo | Dove |
|---|---|
| La misura | [`dbops.vw_codici_errore_da_dichiarare`](/dbzero/dbops/views/vw_codici_errore_da_dichiarare) |
| Il registro | [`dbops.codici_errore_senza_policy`](/dbzero/dbops/tabelle/codici_errore_senza_policy) — **a zero, e non si toglie** (§2.1) |
| Cancello automatico | `backend/apps/core/tests/test_error_codes_db_policy_guardrail.py` (suite Django, in CI) |

⭐ **Un registro fatto bene fa emergere i difetti di modellazione.** Assegnare il
tipo di risposta si fa leggendo il punto che solleva, non il nome del codice — e
così si scopre il codice che dice **due cose** (un «non esiste» e un «correggi
questo campo» sotto la stessa parola): non va classificato, va **spezzato**.

⚠️ **Il cancello sta lato backend, e non è un dettaglio organizzativo.** Il
confronto è contro un dizionario Python: da SQL si potrebbe fare solo leggendo il
*testo* di quel sorgente, legando un guardrail SQL alla forma di un file che non è
suo. Il prezzo è che ha bisogno di un **database provvisto** per girare: in CI ce
l'ha, in locale si accende con `ZEROERP_TEST_DB_E2E=1`.

⚠️ **La misura è volutamente larga.** Raccoglie ogni letterale `E_*` che compare
in un corpo PL/pgSQL vivo, non solo quelli dentro la chiamata che solleva:
restringerla perderebbe i codici che arrivano da un'espressione. Fra i due errori
possibili si sceglie quello che si corregge guardando i falsi positivi (una policy
di troppo costa una riga), non quello che non si vede: **un setaccio, non una
lista**.

⚠️ **La misura è una vista sola**, e il cancello la interroga invece di riscrivere
la regola. Due sponde che si scrivono ognuna la propria query danno numeri diversi
per lo stesso fatto: *anche la misura di un difetto è un programma, e può avere il
suo difetto.*

### 3.5 Il significato di un codice, che si allarga da solo

**Cosa sorveglia.** Un codice errore nasce per dire *una* cosa. Poi qualcuno lo
usa «anche per questo caso qui», una volta, e sembra ragionevole; alla lunga
diventa un'etichetta che copre problemi diversi, che chiedono reazioni diverse, e
che a video diventano tutti lo stesso messaggio.

⭐ **Nessuno crea un codice generico di proposito.** Per questo il presidio non
guarda lo stato, ma il **cambiamento**.

**Perché non è un cancello sullo stato.** Dire «questo codice è generico?»
richiede di leggere, per ogni punto che lo solleva, la condizione che lo precede —
e di capirla. La misura che lo fa
([`dbops.vw_codici_errore_forme_condizione`](/dbzero/dbops/views/vw_codici_errore_forme_condizione))
ci riesce per una parte dei codici, e per gli altri **dichiara di non sapere**.
Un cancello che capisce solo una parte dei casi boccia a caso e passa a caso, e
boccerebbe anche i codici trasversali per costruzione (`E_PERMESSO_NEGATO` è
ovunque, e non è un difetto). Dopo due blocchi sbagliati qualcuno lo spegne — e
**un presidio spento è peggio di uno assente**, perché ha convinto tutti di
esserci.

**La forma che funziona.** Non «questo codice è generico?», ma **«questo codice ha
acquistato una condizione che non aveva?»**, a cui la misura sa rispondere con
certezza sui codici che legge. È lo schema della baseline dei test rossi: un file
committato con lo stato noto, e la CI che fallisce sul **delta**.

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
| La baseline committata | `db/baseline-codici-errore-famiglie.tsv` (un'altra si sceglie con `CODICI_BASELINE`) |
| Cancello automatico | passo CI, subito dopo il guardrail del §3.3 |

⛔ **Se diventa rosso, non si rigenera la baseline per far passare la CI.** La riga
rossa è la richiesta di una decisione: o serve un codice nuovo, o l'uso è
legittimo e la baseline si aggiorna **con la ragione nel messaggio di commit**.

⚠️ **Un presidio va guardato anche nel verso in cui le cose migliorano.** Se un
codice si restringe e la baseline non viene stretta, la baseline continua a
dichiarare ammessa la famiglia che il codice non ha più: il giorno in cui qualcuno
ce la rimette, il confronto la trova già lì e tace. È il verso permissivo, l'unico
in cui un presidio smette di sorvegliare senza diventare rosso — ed è per questo
che anche il restringimento si segnala.

### 3.6 Uno stato previsto dal modello e mai scritto

**Cosa sorveglia.** Il `CHECK` di una colonna di stato è una promessa: ogni valore
ammesso è uno stato che il sistema sa raggiungere. Se un valore è ammesso e
**nessuno lo scrive mai**, la promessa è vuota, e il sistema è muto proprio sul
caso che quel valore doveva raccontare. Di regola è il fallimento: un esito
`ERRORE` ammesso, con il suo contatore, che nessuno scrive — e le corse chiudono
«completate» con un documento rifiutato.

**Come misura.** Il perimetro non è un elenco: è ogni `CHECK` di appartenenza su
una colonna il cui nome dice «stato», letto dal catalogo di PostgreSQL. Per ogni
valore la misura ([`dbops.vw_stati_check_scrittori`](/dbzero/dbops/views/vw_stati_check_scrittori))
cerca **chi lo scrive**: il default della colonna, una funzione che scrive la
tabella col valore nel corpo, o una funzione che chiama uno scrittore passandogli
il valore. Guarda la struttura, non il contenuto: non conta le righe.

**Il registro** ([`dbops.stati_check_dichiarazioni`](/dbzero/dbops/tabelle/stati_check_dichiarazioni))
porta un **canale**, perché il database non vede tutti gli scrittori: una parte
dei valori li scrive l'applicazione. Il canale dice chi verifica la riga:

| `canale` | Che cosa dice la riga | Chi la verifica |
| --- | --- | --- |
| `APPLICAZIONE` | «questo valore lo scrive un repository Python» | il test del backend `backend/apps/core/tests/test_stati_check_scrittori_python.py`: il valore deve comparire in un file che scrive quella tabella, o che la scrive **attraverso** il suo repository; se sparisce, rosso. E nel verso opposto: un valore non dichiarato che Python scrive va dichiarato `APPLICAZIONE`, non sanato a database |
| `ESENTE` | «non lo scrive nessuno, o il criterio non lo vede — e sappiamo perché» | il pgTAP, nel verso di ritiro: se uno scrittore compare a database, la riga va tolta |

⚠️ `ESENTE` non vuol dire «non scritto»: vuol dire che il **criterio** non lo
vede. Il caso tipico è un log che riceve lo stato **copiandolo** dal padre:
scritto a ogni riga, e nessun valore compare in nessuna funzione. Stringere il
`CHECK` romperebbe il log.

**La lista di lavoro** ([`dbops.vw_stati_check_da_sanare`](/dbzero/dbops/views/vw_stati_check_da_sanare))
è un cancello: `db/pgtap/dbops/test-stati-check-scrittori-v1.sql` la fa rossa su
un valore che nessuno scrive e nessuno ha dichiarato, e su una riga di registro
che non serve più. Lo stesso pgTAP tiene l'elenco delle colonne di stato misurate,
come prova che il perimetro non si restringe in silenzio.

**Il limite, detto qui.** Il criterio è **testuale**: nominare un valore in un
`WHERE` dentro una funzione che scrive la tabella conta come scriverlo; un valore
che passa per tre funzioni resta invisibile; una copia da un'altra colonna non si
vede. E PostgreSQL stampa lo stesso `CHECK` in due forme diverse (colonna `text` o
`varchar`): una misura che ne riconosce una sola si restringe senza dirlo. Ognuno
di questi limiti è scritto nel commento della vista e ha un caso costruito nel
pgTAP.

---

## 4. Dove gira ogni presidio, e perché

Tutti i presidi del §3 sono **passi della stessa CI** e bloccano l'integrazione.
Non sono però la stessa cosa messa in posti diversi: misurano su database diversi,
e per questo alcuni hanno anche un giro a mano.

| Presidio | In CI | A mano, in sviluppo |
| --- | --- | --- |
| Riferimenti morti (§3.1) | guardrail SQL | `check_funzioni_riferimenti_morti.sql` |
| Codice errore e canali (§3.3) | guardrail SQL | — |
| Tipo di risposta (§3.4) | suite Django, con database provvisto | `ZEROERP_TEST_DB_E2E=1` |
| Famiglie di condizione (§3.5) | `codici-errore-baseline.sh` | stesso script |
| Baseline pgTAP, con i pgTAP di presidio (§2.2, §3.2, §3.6) | suite pgTAP con `baseline-rossi-ci.tsv` | `pgtap-baseline.sh` con `baseline-rossi.tsv` |

### Cosa dà davvero il cancello in CI

Il vantaggio non è che «gira da solo»: è che **non si può dimenticare** e nessuno
può decidere di saltarlo perché ha fretta.

Va però saputo **quando** scatta. Il workflow di validazione parte sui `push` verso
il branch di integrazione e sulle richieste di merge, e solo se sono stati toccati
certi percorsi; la suite pgTAP, la più lunga, gira sulle richieste verso `main` e
sui `push` di integrazione che toccano il database. Sul proprio branch di lavoro
**non parte**: è una rete che si trova al momento del merge. Il giro a mano resta
il ciclo veloce, quello che si usa mentre si lavora.

⭐ **Un cancello non deve poter zittire un altro cancello.** La suite pgTAP parte
anche se un passo precedente indipendente (per esempio i test Django) è rosso:
sono due domande diverse e vogliono due risposte. Non parte, invece, se il
database non è stato costruito per intero — una suite su un database a metà
direbbe rosso per il motivo sbagliato.

### Due database, due popolazioni

Il database della CI è **costruito da zero** a ogni giro: ha la struttura e i dati
di configurazione, ma **nessun dato di lavoro**. Molti test, invece, scelgono un
caso reale fra i dati esistenti e ci lavorano sopra: su un database vuoto quei
test **non falliscono, si saltano**, e un test saltato conta come verde.

Per questo la baseline pgTAP è doppia (§3.2), e i due giri **servono entrambi, per
motivi opposti**:

* il giro in CI verifica che **le migrazioni sappiano ricostruire** il database —
  ed è la proprietà che conta il giorno in cui si prepara un ambiente nuovo;
* il giro in sviluppo verifica il comportamento **su dati veri**, che la CI non
  ha.

⚠️ Il database di sviluppo e un database ricostruito dai changelog **non sono lo
stesso oggetto**, pur partendo dagli stessi file. Un comando che funziona solo su
un database cresciuto nel tempo lascia sul database nuovo un oggetto che su quello
di sviluppo non esiste più: lo vede solo la CI. Verificare su una sola macchina
significa verificare lo stato di **quella macchina**.

⭐ **Un cancello costruito su una baseline sta in mezzo** (§3.5): ha il rosso che
ferma della CI e il file committato della baseline, e confronta il delta invece
dello stato assoluto. Quando un difetto non si sa misurare in assoluto ma si sa
riconoscere quando **cambia**, è questa la forma da copiare.

---

## 5. ⚠️ Il punto cieco peggiore: una regola che mente

C'è un modo di sbagliare che un presidio non può intercettare da solo.

Il controllo sui riferimenti morti classifica ogni segnalazione, e alcune le
etichetta come **rumore**. Se un'etichetta poggia su un'affermazione tecnica
**sbagliata** — «questa forma di chiamata è lecita, è lo strumento a non
capirla» — i difetti veri che cadono in quella categoria vengono zittiti. E ogni
giro di bonifica che restringe un po' la regola, trovando comunque qualche difetto
vero, **conferma** l'assunto di partenza invece di metterlo in dubbio.

Da qui tre cose che valgono per qualunque presidio:

* **Un'etichetta rassicurante è più pericolosa di un errore.** Un errore lo si
  guarda; un'etichetta la si legge una volta e poi ci si fida. È lo stesso
  meccanismo del test rosso registrato in baseline con la causa sbagliata.
* **Chi scrive la regola non è la persona giusta per verificarla.** Un difetto del
  genere lo trova chi ha un motivo indipendente per guardare.
* **Le esenzioni si scrivono con la loro giustificazione tecnica**, non solo con
  il nome della categoria. Una frase che motiva può essere letta e contestata;
  un'etichetta sola no.

Quando la regola viene corretta, il registro fa comunque il suo mestiere: i
difetti zittiti compaiono tutti insieme, con nome e posizione. Quello che un
presidio **non** può fare è accorgersi da solo che una sua regola mente.

---

## 6. Se un cancello della CI diventa rosso

Prima di considerarlo un problema della CI, l'ordine delle ipotesi:

1. **il difetto è reale** e la CI l'ha appena trovato — è il caso più frequente;
2. **il controllo misura un database incompleto**, perché è messo nel punto
   sbagliato della sequenza;
3. **il difetto esiste solo su un database costruito da zero** — vedi §4.

⚠️ La prima ipotesi che *non* va fatta è «la CI è rotta». Quando un controllo passa
in locale e fallisce in CI, di solito è il locale che sta nascondendo qualcosa.

⚠️ **Lo schema del database non ha un solo proprietario.** Liquibase costruisce
quasi tutto, ma lo schema `django` lo crea Django. Un controllo che legge le
definizioni dell'intero database deve girare **dopo che entrambi hanno finito**,
altrimenti misura un database a metà e segnala problemi che non esistono. Un
controllo che legge solo oggetti di Liquibase può girare prima, ed è meglio:
risponde prima.

---

## 7. Aggiungere un presidio nuovo

La ricetta, nell'ordine:

1. **Scrivi la misura prima del rimedio.** Serve a sapere quanto è grande il
   problema, e spesso il difetto più grave non è nella lista di partenza.
2. **Classifica il rumore, non filtrarlo.** Un controllo che nasconde le righe che
   crede innocue non è più verificabile. Meglio farle uscire tutte con
   un'etichetta: se una è etichettata male, si vede.
3. **Metti la misura in un posto solo.** Se la usano in due (il cancello e il
   test), devono leggere la stessa: due copie prima o poi divergono.
4. **Il registro nasce piccolo.** Meglio sanare prima e registrare solo ciò che è
   davvero una decisione presa; un registro che parte lungo non lo legge nessuno.
5. **Se apri un canale nuovo, presidialo subito**, a zero violazioni: dopo, il
   presidio dovrà rincorrere un arretrato.
6. **Fai fallire il controllo quando non può misurare.** Se manca un prerequisito
   — una baseline sparita, una vista che non si legge — deve dirlo ad alta voce,
   non saltare in silenzio. Un cancello che passa perché non ha misurato niente dà
   la sensazione della copertura senza averla.
7. **Scrivi i limiti accanto al controllo.** Ogni misura ha punti ciechi; se non
   sono scritti, chi legge un verde crede che copra tutto.
8. **Motiva ogni esenzione con la sua ragione tecnica**, non con la categoria
   (§5).
9. **Se è una vista di controllo, mettila nel catalogo** [`dbops.presidi`](/dbzero/dbops/tabelle/presidi)
   con le sue parole in [`presidi_testi`](/dbzero/dbops/tabelle/presidi_testi): è
   così che qualcuno la legge. Se ci si dimentica, il pgTAP del catalogo diventa
   rosso. I passi sono nella scheda della tabella.

---

## 8. Limiti noti

Nessuno di questi controlli vede tutto, e conviene saperlo prima di fidarsi di un
risultato verde.

**Il controllo sui riferimenti morti non vede:**

* i riferimenti che si risolvono verso la **cosa sbagliata**: una funzione che
  scrive il dato giusto nella colonna sbagliata compila benissimo. Il significato
  non si compila;
* i rami di codice che dipendono dai **parametri** con cui un controllo viene
  agganciato a una tabella, invece che dalla tabella stessa;
* più di un difetto per volta nello stesso punto: si ferma al primo. Una bonifica
  va **ri-misurata dopo ogni passo**, non eseguita come una lista scritta una volta.

**La baseline pgTAP non vede** ciò che i test non collaudano, e i test collaudano
solo ciò che i dati presenti permettono di collaudare — in CI meno che in
sviluppo (§4).

**Nessun registro distingue** un residuo da qualcosa lasciato lì di proposito.
Quella differenza sta nell'intenzione di chi l'ha scritto, e nessuna misura la
trova: è ciò per cui esiste il motivo scritto.

**Il presidio delle famiglie di condizione (§3.5) non vede:**

* i codici di cui la misura non sa leggere la guardia: su quelli tace, ed è giusto
  che taccia — un presidio che tira a indovinare si spegne da solo al secondo
  falso allarme;
* un codice che nasce generico con due famiglie entrambe illeggibili: non c'è
  delta da vedere;
* ⚠️ e la sua baseline è misurata **su un database**: confrontare una corsa in CI
  con una baseline presa in sviluppo produce finte regressioni, come per le
  baseline pgTAP. Si sceglie la baseline giusta con `CODICI_BASELINE`.

### ⚠️ Un difetto che non si presidia con un cancello

I lati del §3.3 e del §3.4 hanno una regola **meccanica**: il codice è a catalogo?
è dichiarato nel codice applicativo? ha un tipo di risposta? Si risponde
confrontando due elenchi.

C'è una domanda che non funziona così: **il messaggio descrive davvero la
condizione che solleva l'errore?** Un `IF NOT FOUND` che solleva un codice
chiamato «parametro non valido» è un difetto vero — l'operatore legge una frase
che non c'entra, e il tipo di risposta ne discende sbagliato — ma riconoscerlo
richiede di capire *che cosa significa* quel ramo di codice. Un'euristica sul
testo produce più falsi allarmi che difetti, e un cancello così verrebbe spento: il
§5 in azione.

Perciò resta una **lente da rilanciare a mano** quando si apre un lotto di
lavoro, non un passo della CI. La convenzione dei nomi lo dice da sola:
`scripts/sql/check_*` è uno strumento, `scripts/sql/guardrail_*` è un cancello.
**Sapere che una classe di difetti non è automatizzabile vale quanto
automatizzarne un'altra**: evita di costruire un presidio che mente.

---

## Area tecnica — esempi

Confrontare la suite pgTAP con la baseline di sviluppo, mentre si lavora:

```bash
scripts/pgtap-baseline.sh vendite            # solo gli schemi toccati
scripts/pgtap-baseline.sh --modificati       # solo i pgTAP modificati nell'albero
scripts/pgtap-baseline.sh                    # tutta la suite
```

Aggiornare la baseline di sviluppo dopo aver sanato qualcosa (togliere i rientrati):

```bash
scripts/pgtap-baseline.sh --update vendite
```

Togliere dalla baseline della CI i file rientrati, leggendoli dal log di una corsa:

```bash
scripts/pgtap-baseline-ci-rientrati.sh            # ultima corsa utile su Tito-dev
scripts/pgtap-baseline-ci-rientrati.sh <run-id>   # una corsa precisa
```

Accendere in locale il cancello del tipo di risposta (§3.4), che ha bisogno del
database:

```bash
cd backend && ZEROERP_TEST_DB_E2E=1 ./manage-env.sh test apps.core.tests.test_error_codes_db_policy_guardrail
```

---

## Riferimenti

Le storie dei singoli cantieri — i casi che hanno insegnato le regole di questa
guida, con date e numeri — stanno nei documenti di lavoro (solo nel repository,
non nel sito pubblicato):

* `docs/it/dev/work-done/brief-db-bonifica-riferimenti-morti.md` — il primo giro sui riferimenti morti
* `docs/it/dev/work-done/brief-db-codice-errore-strutturato.md` — il codice errore nel campo dedicato, e le misure che lo presidiano
* `docs/it/dev/work-done/brief-db-be-terzo-lato-presidio-codici.md` — il tipo di risposta e lo svuotamento del suo registro
* `docs/it/dev/work-done/brief-db-be-classe-codici-errore.md` — la classe dei codici e il presidio delle famiglie di condizione
* `docs/it/dev/work-done/brief-db-pgtap-runner-rls-baseline.md` — la baseline per ruolo di connessione
* `docs/it/dev/work-done/brief-db-presidio-stati-mai-scritti.md` — gli stati ammessi e mai scritti
* `docs/it/dev/work-done/brief-db-un-destinatario-per-i-presidi.md` — il catalogo dei presidi e il digest
* `docs/it/dev/work-done/brief-db-presidi-cosa-significa-cosa-fare.md` — `chi_agisce` e i testi per chi agisce
* `docs/it/dev/work-done/analisi-presidi-percorso-storto.md` — l'analisi trasversale sui presidi

---
{% include-markdown "signature-core.md" %}
