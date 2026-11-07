## 📘 Documentazione Concettuale – Vista `dbops.vw_codici_errore_forme_condizione`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.codici_errore](/dbzero/config/tabelle/codici_errore) — la classe dichiarata di ogni codice, da incrociare con la forma
> * [config.classi_errore](/dbzero/config/tabelle/classi_errore) — le classi
>
> Approfondimento viste:
>
> * [dbops.vw_codici_errore_da_dichiarare](/dbzero/dbops/views/vw_codici_errore_da_dichiarare) — la misura dei codici nominati, che condivide i punti ciechi
>
> Approfondimento funzioni:
>
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — la chiamata che segna un punto che solleva
> * [dbops.fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione) — il corpo senza commenti che la vista taglia a righe
> * [dbops.fn_regexp_occorrenze](/dbzero/dbops/funzioni/fn_regexp_occorrenze) — l'estrazione dei codici di una riga

---

### 🎯 Scopo Principale

La misura degli accumulatori: per ogni codice errore, sotto quali forme di condizione viene
sollevato, letta dal testo delle funzioni PL/pgSQL. Un codice che serve a situazioni troppo diverse
smette di dire qualcosa, e chi lo riceve non sa che fare.

⭐ **L'asse è la forma della condizione al punto che solleva**, cioè che cosa verifica l'`IF` sopra
la chiamata, non il dominio della funzione. Misurando per dominio l'asse segnalava `E_VALIDAZIONE`,
che è proprio il caso su cui la risposta è «va bene così»: un codice di validazione compare ovunque
per definizione, ed è la forma del controllo a dire se sta accumulando significati diversi.

La vista **non filtra di proposito**: chi filtra decide che cosa non vedere.

---

### Come funziona: isole fra due guardie

Il corpo di ogni funzione, letto senza commenti da
[fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione), si spezza riga per riga, e ogni riga
si marca:

* **guardia** — comincia con `IF`, `ELSIF`, `ELSE`, `EXCEPTION WHEN`, `WHEN OTHERS`, `WHEN SQLSTATE`;
* **chiamata** — nomina `fn_log_and_raise_error`;
* **motivo** — dichiara un motivo con la sua chiave `codice` e un letterale `E_*`;
* **codici** — i letterali `E_*` distinti che la riga porta, tutti.

Le guardie delimitano le **isole**: ogni codice appartiene alla guardia che apre la sua isola. Una
riga con un codice è un **punto** se c'è una chiamata entro le sei righe precedenti, oppure se è la
riga che dichiara un motivo, e se sta entro venticinque righe dalla sua guardia. Dalla guardia si
ricava la famiglia.

⭐ **Ogni codice distinto di una riga è un punto suo.** Isole, chiamata vicina e guardia si calcolano
sulle righe; solo dopo la riga si espande nei suoi codici, che prendono tutti la stessa guardia. Una
guardia o un motivo che nomina due codici dà due punti, e il secondo codice ha la sua famiglia come
il primo.

Le distanze si contano sul corpo senza commenti: un commento a blocco su più righe non le allunga, e
una chiamata rimasta in un commento non accende la «chiamata vicina».

⭐ **Il codice nominato in un motivo.** Quando la madre chiama una funzione di controllo, il letterale
sta dentro la funzione di controllo, dove nessuna chiamata all'helper gli sta vicino. Per questo la
riga che dichiara un motivo è un punto da sé, e la guardia si prende dall'`IF` che la precede
**dentro** la funzione di controllo, dove sta la condizione vera. ⛔ Non si risale dalla chiamata
alla funzione di controllo: sopra il punto che solleva, nella madre, la guardia è sempre «ci sono
motivi», identica ovunque e muta sul perché, e attribuirle i codici li archivierebbe tutti come
illeggibili. Il marcatore è per forma, non per nome di funzione: un perimetro scritto a elenco
invecchia da solo.

---

### Le famiglie, e il loro ordine

L'ordine è portante: una guardia che somiglia a due famiglie finisce nella **prima** che la
riconosce.

| # | Famiglia | Che cosa verifica la guardia |
| --- | --- | --- |
| 1 | `ECCEZIONE` | è un gestore d'eccezione |
| 2 | `NOT_FOUND` | una riga che doveva esserci non c'è |
| 3 | `PARAMETRO` | un parametro della funzione è nullo o non positivo |
| 4 | `ENUM` | il valore è fuori da un insieme ammesso (`NOT IN`) |
| 5 | `VALORE_ATTESO` | il valore letto non è quello ammesso (confronto con un letterale) |
| — | `IGNOTO` | nessuna regola sa leggere quella guardia |

⭐ **`VALORE_ATTESO` è la forma di ogni guardia di stato o di perimetro** del progetto: «questo
documento non è in bozza», «questa non è una email di sistema». Era una famiglia intera che l'asse
non nominava e finiva tutta in `IGNOTO`. ⛔ È una famiglia nuova e non un `ENUM` allargato perché le
letture di questa vista sono datate e si confrontano nel tempo: cambiare che cosa significa `ENUM`
renderebbe incomparabili, in silenzio, le letture vecchie con le nuove. L'ordine la mette dopo `ENUM`
e `PARAMETRO`: un `NOT IN` resta `ENUM`, una guardia su un parametro nullo resta `PARAMETRO` anche se
confronta un letterale.

⛔ **`PARAMETRO` non si legge su un campo di un record.** Una guardia che controlla un campo del
documento passato come parametro non dice «chi ha chiamato è rotto», dice «manca un dato che una
persona corregge»: è la differenza fra un guasto tecnico e un dato errato, cioè proprio l'asse per
cui la vista esiste. Il nome di parametro seguito da un punto non conta; se sulla riga c'è anche un
parametro vero, resta `PARAMETRO`. Chi non si legge più cade in `IGNOTO`, che è la risposta onesta.

⚠️ **Imprecisione dichiarata**: la forma prende anche del normale controllo di flusso che capita
entro venticinque righe da un punto (un ramo sul tipo di operazione, un ramo sul tipo di
identificativo). Sta dentro la natura di una misura, ma va saputo leggendo i candidati.

---

### ⚠️ Tre letture, da usare insieme

Il `COMMENT` della vista le scrive per esteso. La ragione per cui sono tre:

1. **Candidati** — i codici con più di una famiglia nota, ordinati per numero di punti.
2. **Copertura** — quanti codici sono classificati e quanti restano solo `IGNOTO`. Senza la seconda,
   la prima si legge come una verità: l'assenza di un codice dai candidati può voler dire «non si sa».
3. **La classe è ancora vera?** — incrocia le due letture indipendenti dello stesso codice, la
   guardia (che cosa fa il punto) e la classe a catalogo (che cosa dice). Le righe `IGNOTO` lì non
   sono una famiglia: sono la misura che dichiara di non saper leggere. E «fuori dalla famiglia
   dominante» non vuol dire sbagliato: è una lista da guardare, non di difetti.

Il numero delle righe di questa vista, da solo, non ha significato.

---

### ⚠️ È una misura: il cancello sta altrove

Non c'è soglia e non c'è verdetto: un codice con più famiglie può essere un accumulatore da spezzare
oppure un codice legittimamente trasversale. Il cancello che la usa giudica il **cambiamento**, non lo
stato: lo scatto della CI (`scripts/codici-errore-baseline.sh`) confronta le famiglie note di ogni
codice con una baseline committata, ed è rosso quando un codice acquista una famiglia che non aveva o
nasce con più di una. `IGNOTO` non entra nel confronto.

Per questo nel catalogo dei presidi ([dbops.presidi](/dbzero/dbops/tabelle/presidi)) la sua natura
è `CANCELLO`, presidiata dal passo B-7 di `ci-validate`, e sta fuori dal digest: la vista è la
materia del cancello, e il verdetto lo dà la build.

Condivide i punti ciechi di
[vw_codici_errore_da_dichiarare](/dbzero/dbops/views/vw_codici_errore_da_dichiarare): legge
letterali in corpi PL/pgSQL, e non vede i codici costruiti per concatenazione né i `RAISE EXCEPTION`
diretti. I commenti, di riga e a blocco, non entrano: un codice citato in un commento non è un
punto.

La vista è `security_invoker` e legge i cataloghi di sistema.

---

### Test

* `db/pgtap/dbops/test-vw-codici-errore-valore-atteso.sql` — quattro forme costruite e la loro
  famiglia, compresa una guardia illeggibile che resta `IGNOTO`; l'ordine fra `ENUM`, `PARAMETRO` e
  `VALORE_ATTESO`; il caso segnalato dal backend ha un codice suo.
* `db/pgtap/dbops/test-vw-codici-errore-motivo-nominato.sql` — un codice nominato solo come motivo
  compare e prende la guardia dentro la funzione di controllo; il marcatore non è troppo largo ed è
  per forma; un parametro nullo resta `PARAMETRO`, un campo di un record no; due codici sulla stessa
  riga sono due punti con la stessa guardia (test 9); un codice in un commento a blocco non è un
  punto (test 10).

---

### Note di migrazione

* 2026-08-08 — nasce a window function (la prima versione a sottoquery correlate impiegava oltre
  due minuti). Lettura del giorno: 344 codici, 75 classificati.
* 2026-09-07 — nasce `VALORE_ATTESO`, segnalato dal backend (`brief-db-sveglia-dei-processi` §3.2):
  `E_VALIDAZIONE` non compariva fra i candidati perché la sua seconda forma, la guardia più
  pericolosa di `config.fn_chiudi_email_sistema`, era illeggibile. Sugli stessi 453 codici i
  classificati passano da 96 a 148 e i candidati da 6 a 10.
* 2026-09-08 — il codice nominato in un motivo diventa un punto: 35 codici-motivo su 50 erano
  invisibili.
* 2026-09-09 — `PARAMETRO` non si legge più su un campo di un record.
* 2026-11-04 — ogni codice distinto di una riga è un punto (D56 di `brief-db-revisione-dbops`): prima
  si prendeva solo il primo, e il secondo codice di una riga si perdeva.
* 2026-11-04 — le righe si tagliano dal corpo senza commenti di `fn_corpo_funzione` (D14 di
  `brief-db-revisione-dbops`): prima si scartavano solo le righe che cominciano con un commento di
  riga, quindi un codice in un commento a blocco o in coda a una riga contava come punto. Le distanze
  di sei e venticinque righe cambiano solo dove c'era un commento a blocco su più righe, che non le
  allunga più; una riga di solo commento resta, vuota, e conta come prima. Fatto datato: quel giorno, sul
  codice vivo, la misura non cambiava una riga, e la baseline del cancello non si è mossa.
* 2026-11-04 — i codici di una riga si estraggono con `fn_regexp_occorrenze`, che dichiara una riga
  per chiamata, e non più da un elenco espanso, che ne dichiarava dieci: la stima del piano era salita
  oltre la soglia in cui il JIT ottimizza, e ogni lettura pagava circa 300 ms di compilazione. Output
  invariato. I due test che la leggono la fotografano una volta sola.

* 2026-11-07 — nel catalogo dei presidi passa da `LAVORAZIONE` a `CANCELLO`, presidiata dal
  passo B-7 (`brief-db-revisione-dbops`, giro 6).

---

{% include-markdown "signature-core.md" %}
