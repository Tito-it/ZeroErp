## 📘 Documentazione Concettuale – View `dbops.vw_punti_canale_campo`

> 👀 **Vedi anche**
>
Approfondimenti viste:
>
[dbops.vw_funzioni_check_codici](/dbzero/dbops/manual/vw_funzioni_check_codici)
>
[dbops.vw_codici_errore_da_dichiarare](/dbzero/dbops/manual/vw_codici_errore_da_dichiarare)

---
### 🎯 Scopo Principale
(latest review 03-11-2026)

Risponde a una domanda sola:

> **Quando il database rifiuta un dato, dice anche *quale campo* correggere?**

Ogni riga è un **codice d'errore** dentro una **funzione** del database, con
accanto **come** quella funzione lo solleva e **se** gli allega il nome del
campo. È la metà «database» di un controllo che ha anche una metà «programma»
(il test del backend), ed è la parte che serve a far accendere in rosso
l'input giusto sullo schermo.

---

### ⭐ Perché serviva, e non bastava guardare

Ogni codice d'errore porta a catalogo una **promessa all'interfaccia**: per
molti dice *«evidenzia il campo del form»*. Ma quella promessa non accende
niente da sola. Il campo si accende solo se, nel punto in cui l'errore nasce,
qualcuno ha scritto **il nome del campo** nel posto in cui il meccanismo va a
leggerlo. Se manca, sullo schermo esce un avviso generico e nessun campo
rosso — e non fallisce nulla: nessun test, nessuna pagina bianca, nessun
allarme. Il 21 settembre 2026 erano **37 codici** in questa condizione, e in
molti il nome del campo *c'era*, scritto nel posto sbagliato.

⭐ E la sera stessa, acceso il controllo del programma sopra questa vista, ne
sono usciti **altri 9** che la lista compilata a mano non aveva: erano finiti
nel bucket «forse» della prima misura, perché il nome del campo compariva in
*un'altra* chiamata della stessa funzione e nessuno sapeva attribuirla. La
vista attribuisce, e li ha visti il primo giorno. Sono stati sanati il 22
settembre.

---

### Come un codice viene sollevato (`via`)

| `via` | Che cosa vuol dire | È un «sito»? |
| --- | --- | --- |
| `DIRETTO` | la funzione solleva il codice chiamando il meccanismo centrale, col codice scritto in chiaro (o scelto poco prima in una variabile) | sì |
| `PRIMO_MOTIVO` | la funzione solleva il primo dei **motivi** che una funzione di controllo (`fn_check_*`) le ha restituito: il codice viene da lì | sì |
| `MOTIVO` | è la funzione di controllo stessa, quella che **produce** il motivo: non solleva, ma è il posto dove il campo può essere scritto per tutti i chiamanti | no — è la sede del campo |
| `NOMINATO` | il codice compare nel testo della funzione ma non viene sollevato da lì (un confronto, un esito, una capability) | no |

Distinguere `NOMINATO` da «nessuna riga» conta: un codice che *nessuno* nomina
è morto; uno *nominato e mai sollevato* è un caso da guardare.

---

### Il canale del campo (`canale`)

| `canale` | Che cosa vuol dire | Che cosa fare |
| --- | --- | --- |
| `IN_CHIAMATA` | il nome del campo è scritto nel punto giusto, dentro la chiamata (o nel motivo della funzione di controllo) | niente |
| `IN_VARIABILE` | il nome c'è, ma in una variabile preparata prima, oppure il codice stesso è in una variabile: **probabilmente** va bene, ma la lettura non può esserne certa | leggere quel punto una volta |
| `CHIAVE_NON_LETTA` | il nome della colonna c'è, ma come **etichetta** di un altro dato (`'quantita', NEW.quantita`), dove il meccanismo non lo legge | aggiungere la coppia `'campo', '<nome>'`: `nome_in_chiave` dice quale |
| `NESSUNO` | niente | o si aggiunge il campo, o si smette di promettere che verrà evidenziato (la promessa era sbagliata) |

`chiave` dice *quale* delle due etichette ammesse è stata trovata (`campo`, o
`parametro` — la seconda porta il nome del parametro e il meccanismo lo
converte da sé).

---

### ⭐ Una funzione, più chiamate: come si legge

Una stessa funzione può sollevare lo stesso codice in tre punti, e allegare il
campo solo in due (perché nel terzo non c'è nessun input da indicare, ma un
identificativo che arriva dall'indirizzo della pagina). La riga riporta il
**miglior** esito fra i punti — perché la regola del controllo è «*almeno un*
punto lo indica» — e i due contatori `n_chiamate` / `n_con_canale` dicono che
sono **3 su 2**. Chi vuole la regola più severa («*ogni* punto») guarda
`n_con_canale = n_chiamate`.

Dove invece la lettura **non sa** attribuire il campo a un codice (il codice è
in una variabile), non concede il beneficio del dubbio: risponde
`IN_VARIABILE`, mai `IN_CHIAMATA`. Un falso «va bene» qui costerebbe una
promessa vuota che nessuno vedrebbe più.

---

### ⚠️ Che cosa questa vista NON dice

Che il nome scritto sia **quello giusto**. Dice che un nome c'è, nel posto
giusto. Che sia il nome dell'input che l'operatore ha davanti — e non un
identificativo interno — è un giudizio che si prende codice per codice
(è la tabella A/B del brief).

E legge il **testo** delle funzioni: una chiave scritta dentro un blocco JSON
letterale non la vede, una chiamata con un `;` dentro un testo la tronca, i
rifiuti sollevati senza passare dal meccanismo centrale non passano di qui.
I limiti sono scritti nel commento della vista e provati dal test.

---

### Chi la legge (a catalogo: `CANCELLO`)

Questa vista **non è un allarme da sola**: elenca anche i punti sani, di
proposito, come `vw_codici_errore_da_dichiarare`. Il cancello è il test del
backend (`apps/core/tests/test_ui_action_e_canale_campi.py`), che incrocia il
catalogo dei codici con questa vista per i siti del database e con il sorgente
Python per gli altri, in due versi:

| Verso | Che cosa chiede | Esito |
| --- | --- | --- |
| 1 — la promessa vuota | ogni codice che promette «evidenzia il campo» ha **almeno un** punto che manda il nome | **rosso**, blocca |
| 2 — la promessa che non decide | un codice che manda *sempre* il nome ma promette altro | solo **misurato** e riportato, non blocca |

Le eccezioni volute stanno nel test, con la ragione, e hanno il verso di
ritiro: una riga di eccezione per un codice che ora rispetta la regola è rossa.
Il pgTAP `db/pgtap/dbops/test-punti-canale-campo-v1.sql` presidia invece la
**forma** (che la vista classifichi come dichiara) e che le sanature fatte non
vengano disfatte da un corpo riemesso da un file più vecchio.

---

### Esempio d'uso

I codici con la promessa e senza il campo, con il nome che *ci sarebbe*:

```sql
SELECT codice, funzione, canale, nome_in_chiave, n_chiamate, n_con_canale
  FROM dbops.vw_punti_canale_campo
 WHERE via IN ('DIRETTO', 'PRIMO_MOTIVO')
   AND canale IN ('CHIAVE_NON_LETTA', 'NESSUNO')
 ORDER BY codice, funzione;
```

### 🔄 rev 2026-11-03 — il codice che arriva dal **trigger**

Certe regole sono scritte una volta, in una funzione generica, e montate su
molte tabelle: il codice d'errore lo sceglie il trigger e lo passa alla
funzione come argomento. Nel testo della funzione il codice non c'è, e questa
vista non vedeva il punto: la coerenza fra emittente e cliente, che evidenzia
il campo davvero, risultava «senza sito», e il backend aveva un'eccezione
scritta apposta.

Da questo giorno i codici di una funzione sono quelli del suo testo **più**
quelli che i trigger le passano, letti da
[`vw_codici_errore_argomenti_trigger`](/dbzero/dbops/manual/vw_codici_errore_argomenti_trigger).
La funzione generica solleva il codice da una variabile, quindi la lettura non
concede il beneficio del dubbio: il canale è al massimo `IN_VARIABILE`, come
per ogni codice in variabile. Il lucchetto di colonna, che non indica il campo,
risulta `NESSUNO`, ed è la verità. Test: casi 17 e 18.

Origine: `docs/it/dev/work-done/brief-be-presidio-ui-action-e-canale-campi.md`
(§4, §4-bis e §4-ter); la revisione: voce D24 di
`migliorie-generali-da-test-valutazione`. Test: `db/pgtap/dbops/test-punti-canale-campo-v1.sql`.

---

{% include-markdown "signature-core.md" %}
