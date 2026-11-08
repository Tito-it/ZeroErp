## 📘 Documentazione Concettuale – Vista `dbops.vw_punti_canale_campo`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.codici_errore](/dbzero/config/tabelle/codici_errore) — il catalogo dei codici e la promessa all'interfaccia
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo che la iscrive come cancello
>
> Approfondimento viste:
>
> * [dbops.vw_funzioni_check_codici](/dbzero/dbops/views/vw_funzioni_check_codici) — la risalita dal punto alla check e ai suoi codici, condivisa
> * [dbops.vw_codici_errore_argomenti_trigger](/dbzero/dbops/views/vw_codici_errore_argomenti_trigger) — i codici che un trigger passa alla sua funzione
> * [dbops.vw_punti_primo_motivo](/dbzero/dbops/views/vw_punti_primo_motivo) — l'altra lettrice della stessa risalita
> * [dbops.vw_codici_errore_da_dichiarare](/dbzero/dbops/views/vw_codici_errore_da_dichiarare) — la misura sorella, volutamente larga come questa
>
> Approfondimento funzioni:
>
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — il meccanismo che legge il nome del campo
> * [script.fn_raise_primo_motivo_se_presente](/dbzero/script/funzioni/fn_raise_primo_motivo_se_presente) — l'helper che solleva il primo motivo di una check
> * [dbops.fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione) — il corpo senza commenti da cui la vista legge le funzioni

---

### 🎯 Scopo Principale

Per ogni coppia (funzione PL/pgSQL, codice d'errore): **come** la funzione solleva il codice e
**se** gli allega il nome del campo da correggere. È la metà «database» del controllo che fa
accendere in rosso l'input giusto sullo schermo.

---

### ⭐ Perché serviva, e non bastava guardare

Ogni codice d'errore porta a catalogo una **promessa all'interfaccia**: per molti dice «evidenzia
il campo del form». Ma la promessa non accende niente da sola. Il campo si accende solo se, nel
punto in cui l'errore nasce, qualcuno ha scritto **il nome del campo** nel posto in cui
`script.fn_log_and_raise_error` va a leggerlo: la chiave `campo` del contesto, o in ripiego
`parametro`.

Se manca, sullo schermo esce un avviso generico e nessun campo rosso, e non fallisce nulla:
nessun test, nessuna pagina bianca, nessun allarme. E spesso il nome del campo *c'è*, scritto nel
posto sbagliato.

---

### Come un codice viene sollevato (`via`)

| `via` | Che cosa vuol dire | È un «sito»? |
| --- | --- | --- |
| `DIRETTO` | la funzione solleva il codice chiamando il meccanismo centrale, col codice scritto in chiaro o in una variabile | sì |
| `PRIMO_MOTIVO` | la funzione solleva il primo dei **motivi** che una funzione di controllo (`fn_check_*`) le ha restituito, con l'helper o a mano: il codice viene da lì | sì |
| `MOTIVO` | è la funzione di controllo stessa, quella che **produce** il motivo: non solleva, ma è il posto dove il campo può essere scritto per tutti i chiamanti | no: è la sede del campo |
| `NOMINATO` | il codice compare nel testo della funzione ma non viene sollevato da lì (un confronto, un esito, una capability) | no |

Distinguere `NOMINATO` da «nessuna riga» conta: un codice che *nessuno* nomina è morto; uno
*nominato e mai sollevato* è un caso da guardare.

I codici di un sito `PRIMO_MOTIVO` sono **tutti** quelli delle check citate nel corpo: la lettura
non sa quale ramo verrà preso. La risalita dal punto alla check non è scritta qui ma in
`dbops.vw_funzioni_check_codici`, condivisa con `dbops.vw_punti_primo_motivo`.

---

### ⭐ Il codice che arriva dal trigger

Certe regole sono scritte una volta, in una funzione generica montata su molte tabelle: il codice
d'errore lo sceglie il trigger e lo passa alla funzione come argomento. Nel testo della funzione il
codice non c'è.

⇒ I codici di una funzione sono quelli del suo testo **più** quelli che i trigger le passano, letti
da `dbops.vw_codici_errore_argomenti_trigger`. La funzione generica solleva il codice da una
variabile, quindi il canale è al massimo `IN_VARIABILE`, come per ogni codice in variabile. Un
lucchetto di colonna, che non indica un campo, risulta `NESSUNO`, ed è la verità.

---

### Il canale del campo (`canale`)

| `canale` | Che cosa vuol dire | Che cosa fare |
| --- | --- | --- |
| `IN_CHIAMATA` | il nome del campo è scritto nel punto giusto: dentro la chiamata, come campo letterale dell'helper, o nel motivo della funzione di controllo | niente |
| `IN_VARIABILE` | il nome c'è ma in una variabile preparata prima, oppure il codice stesso è in una variabile: **probabilmente** va bene, ma la lettura non può esserne certa | leggere quel punto una volta |
| `CHIAVE_NON_LETTA` | il nome della colonna c'è, ma come **etichetta** di un altro dato, dove il meccanismo non lo legge | aggiungere la chiave `campo` col nome: `nome_in_chiave` dice quale |
| `NESSUNO` | niente | o si aggiunge il campo, o si smette di promettere che verrà evidenziato |

`chiave` dice *quale* delle due etichette ammesse è stata trovata: `campo`, o `parametro`, che porta
il nome del parametro e il meccanismo converte da sé.

---

### ⭐ Una funzione, più chiamate: si riporta il migliore

Una stessa funzione può sollevare lo stesso codice in tre punti e allegare il campo solo in due,
perché nel terzo non c'è un input da indicare ma un identificativo che arriva dall'indirizzo della
pagina. La riga riporta il **miglior** esito fra i punti, perché la regola del controllo è «*almeno
un* punto lo indica», e i contatori `n_chiamate` e `n_con_canale` dicono quanti. Chi vuole la regola
più severa («*ogni* punto») guarda se i due contatori coincidono.

⛔ Dove la lettura **non sa** attribuire il campo a un codice (il codice è in una variabile), non
concede il beneficio del dubbio: risponde `IN_VARIABILE`, mai `IN_CHIAMATA`. Un falso «va bene» qui
costerebbe una promessa vuota che nessuno vedrebbe più.

---

### ⚠️ Che cosa questa vista non dice

Che il nome scritto sia **quello giusto**. Dice che un nome c'è, nel posto giusto. Che sia il nome
dell'input che l'operatore ha davanti, e non un identificativo interno, è un giudizio che si prende
codice per codice.

E legge il **testo** delle funzioni PL/pgSQL, dal corpo senza commenti di
[fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione), che rispetta i letterali: una chiamata è il testo fino al primo
punto e virgola, quindi un punto e virgola dentro una stringa la tronca; una chiave scritta dentro un
blocco JSON letterale non la vede; i rifiuti sollevati senza passare dal meccanismo centrale non
passano di qui; le funzioni scritte in SQL non sono lette. I due helper del meccanismo sono esclusi.

---

### Chi la legge: un cancello, ma non da sola

Questa vista **non è un allarme**: elenca anche i punti sani, di proposito, come
`dbops.vw_codici_errore_da_dichiarare`, e il suo numero non è il debito. Il cancello è il test del
backend `apps/core/tests/test_ui_action_e_canale_campi.py`, che incrocia il catalogo dei codici con
questa vista per i siti del database e con il sorgente Python per gli altri, in due versi:

| Verso | Che cosa chiede | Esito |
| --- | --- | --- |
| 1, la promessa vuota | ogni codice che promette «evidenzia il campo» ha **almeno un** sito che manda il nome | **rosso**, blocca |
| 2, la promessa che non decide | un codice che manda *sempre* il nome ma promette altro | solo **misurato**, non blocca |

Le eccezioni volute stanno nel test, con la ragione, e hanno il verso di ritiro: una riga di
eccezione per un codice che ora rispetta la regola è rossa. Per questo a catalogo la vista è un
`CANCELLO`, perimetro `LIBERO`: legge solo il catalogo di PostgreSQL.

---

### Test

* `db/pgtap/dbops/test-punti-canale-campo-v1.sql` — la **forma**: ogni via e ogni canale costruiti
  uno per uno, la delega fra check, il codice negli argomenti del trigger (test 17 e 18), e le
  sanature già fatte che non si disfano quando un corpo viene riemesso da un file più vecchio.
* `db/pgtap/dbops/test-vw-funzioni-check-codici-sotto-jit-v1.sql` — il costo stimato della vista
  resta sotto la soglia del JIT.

---

### Note di migrazione

* 2026-09-21 — nasce come `INVENTARIO`, la misura del presidio C2
  (`brief-be-presidio-ui-action-e-canale-campi` §4): quel giorno 37 codici promettevano il campo
  senza mandarlo, e in molti il nome c'era, nel posto sbagliato.
* 2026-09-22 — diventa `CANCELLO` col test del backend. Acceso il test, la vista trova altri 9 codici
  che la lista compilata a mano non aveva, perché il nome del campo compariva in un'altra chiamata
  della stessa funzione; sanati lo stesso giorno (§4-bis, §4-ter).
* 2026-11-03 — entrano i codici passati dal trigger come argomento. Prima per la vista quel sito non
  esisteva, e il backend aveva un'eccezione scritta apposta (voce D24 di
  `migliorie-generali-da-test-valutazione`).
* 2026-11-04 — il corpo si legge da `fn_corpo_funzione` (D14 di `brief-db-revisione-dbops`): la copia
  di prima toglieva un commento, di riga o a blocco, anche dentro un letterale.

---

{% include-markdown "signature-core.md" %}
