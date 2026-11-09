## 📘 Documentazione Concettuale – Vista `dbops.vw_punti_primo_motivo`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo che la iscrive come cancello
>
> Approfondimento viste:
>
> * [dbops.vw_funzioni_check_codici](/dbzero/dbops/views/vw_funzioni_check_codici) — la risalita dal punto alla check e ai suoi codici, che questa vista legge
> * [dbops.vw_punti_canale_campo](/dbzero/dbops/views/vw_punti_canale_campo) — l'altra lettrice della stessa risalita
> * [dbops.vw_codici_errore_forme_condizione](/dbzero/dbops/views/vw_codici_errore_forme_condizione) — quella a cui questa vista non serve
>
> Approfondimento funzioni:
>
> * [script.fn_raise_primo_motivo_se_presente](/dbzero/script/funzioni/fn_raise_primo_motivo_se_presente) — l'helper che solleva il primo motivo, la forma giusta
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — il meccanismo che i punti chiamano a mano
> * [dbops.fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione) — il corpo senza commenti su cui gira il marcatore dei punti
> * [dbops.fn_corpo_leggibile](/dbzero/dbops/funzioni/fn_corpo_leggibile) — quali funzioni hanno un corpo da leggere: il perimetro
>
> Guide:
>
> * [Linee guida SQL](/linee-guida-sql) — §12.5.2: la madre chiama la check

---

### 🎯 Scopo Principale

I punti che sollevano **a mano** il codice del primo motivo restituito da una funzione di controllo
(`script.fn_check_*`), legati alla check da cui il motivo viene e ai codici che quella nomina. È il
**rubinetto**: la sede da cui il presidio guarda se qualcuno riscrive la coda che dovrebbe stare
nell'helper.

---

### ⭐ Il rubinetto: chiudere la fonte, non rincorrere i casi

Una funzione che chiama una check e ne solleva il primo motivo può farlo in due modi: con l'helper
`script.fn_raise_primo_motivo_se_presente`, o riscrivendo la stessa coda a mano, leggendo il codice
dal motivo e passandolo al meccanismo centrale. Chi scrive una check nuova copia la coda dalla
funzione accanto: è così che le copie a mano si moltiplicano senza che nessuno l'abbia deciso.

Questa vista elenca le copie a mano. Chi chiama già l'helper non ci sta, per costruzione.

---

### Che cosa dice una riga

Una riga per (punto, check, codice):

* il **punto**: la funzione dal corpo leggibile, PL/pgSQL o SQL, che solleva a mano un codice letto da un motivo;
* la **check** citata nel suo corpo, e se quella check emette i **valori** della frase;
* il **codice** che quella check può produrre.

⭐ Il punto può stare nell'helper solo se la sua check emette i valori: dove non li emette, la frase
la compone il chiamante dai propri dati, e delegare la spezzerebbe. ⇒ Il perimetro dell'helper si
**deriva** da qui, non si elenca: una check che domani aggiunge i valori fa entrare il suo punto nel
perimetro da sola.

---

### ⭐ Pessimista di proposito

I codici di un punto sono l'**unione** di quelli nominati da tutte le check citate nel corpo, perché
la lettura legge il testo e non sa quale ramo verrà preso. Un presidio che scegliesse il ramo
ottimista assolverebbe il caso che deve segnalare.

⚠️ **Il ramo cieco.** Un punto senza check legata non è «a posto»: è un sito che la lettura non sa
legare alla sua check, e va visto.

---

### ⚠️ È un'euristica sul testo

Riconosce la forma scritta, non il significato: un punto è una funzione il cui testo contiene una
chiamata al meccanismo centrale che legge il codice da un motivo. Il perimetro sono i corpi
leggibili, PL/pgSQL e SQL (comprese le SQL `BEGIN ATOMIC`), come li decide
[fn_corpo_leggibile](/dbzero/dbops/funzioni/fn_corpo_leggibile): conta chi può sollevare un codice,
non il linguaggio in cui è scritto.

Il marcatore gira sul corpo senza commenti di
[fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione): una chiamata rimasta in un commento
non fa di una funzione un punto. Davanti resta la stessa forma cercata sul sorgente testuale, come
prefiltro: costa poco, è un sovrainsieme (un commento può solo aggiungere testo) e tiene bassa la
stima del costo della vista. Una funzione SQL `BEGIN ATOMIC` non ha un sorgente testuale (il suo è
vuoto): il prefiltro la lascia passare sempre, e la decide il marcatore sul corpo ricostruito.

⛔ Non serve a classificare la forma della guardia (`dbops.vw_codici_errore_forme_condizione`):
sopra questi punti la guardia è sempre «se ci sono motivi», che non dice niente. Lì si classifica
dove il codice è nominato.

---

### Chi la legge

A catalogo è un `CANCELLO`, perimetro `LIBERO`: legge solo il catalogo di PostgreSQL. Non è un
allarme da sola: il cancello è il pgTAP del rubinetto, che ne legge il perimetro e il ramo cieco.

---

### Test

* `db/pgtap/script/test-rubinetto-primo-motivo-v1.sql` — il cancello: nessun punto **in perimetro**
  solleva il primo motivo a mano, nessun punto resta senza check, il debito fuori perimetro non
  cresce, le funzioni bonificate chiamano davvero l'helper, e il marcatore non è né troppo largo né
  troppo stretto.
* `db/pgtap/script/test-catalogo-messaggi-errore-completo.sql` — la legge per sapere quali codici
  può sollevare un punto a codice non letterale, e controllare che il punto passi alla frase tanti
  valori quanti il messaggio ne chiede.
* `db/pgtap/dbops/test-vw-funzioni-check-codici-sotto-jit-v1.sql`, test 2 — il costo stimato della
  vista resta sotto la soglia del JIT.
* `db/pgtap/dbops/test-presidi-codici-corpo-leggibile-v1.sql` — vede il primo motivo sollevato a mano
  da una funzione SQL (caso costruito).

---

### Note di migrazione

* 2026-09-08 — nasce col rubinetto del primo motivo (`brief-db-i-motivi-si-fermano-dentro-la-check`
  V-0, `brief-db-coda-primo-motivo-in-un-posto-solo`). Prima viveva come vista temporanea dentro il
  pgTAP.
* 2026-09-21 — la risalita dal punto alla check e ai codici passa a `dbops.vw_funzioni_check_codici`,
  sede unica condivisa con il presidio del canale del campo
  (`brief-be-presidio-ui-action-e-canale-campi` §4): qui resta il solo marcatore dei punti.
* 2026-11-04 — il marcatore gira anche sul corpo senza commenti di `fn_corpo_funzione` (D14 di
  `brief-db-revisione-dbops`): prima leggeva il sorgente commenti compresi, e una chiamata rimasta in
  un commento faceva di una funzione un punto del rubinetto.
* 2026-11-09 — il perimetro passa dal solo PL/pgSQL ai corpi leggibili, PL/pgSQL e SQL, letti da
  `fn_corpo_leggibile`; il prefiltro lascia passare le SQL `BEGIN ATOMIC`, che non hanno un sorgente
  testuale (`20261110-81`, `brief-db-revisione-dbops`, giro 12).

---

{% include-markdown "signature-core.md" %}
