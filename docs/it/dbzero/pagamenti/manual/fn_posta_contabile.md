## 📘 Documentazione Concettuale – Funzione `pagamenti.fn_posta_contabile`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili) — la distinta che registra e chiude
> * [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe) — le righe pronte che diventano movimenti
> * [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti) — dove nascono i movimenti
> * [pagamenti.vendite_contabili_stati](/dbzero/pagamenti/tabelle/vendite_contabili_stati) — la bandiera `is_registrabile`
>
> Approfondimento funzioni:
>
> * [pagamenti.fn_get_saldo_fattura](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura) — il saldo che i movimenti fanno cambiare
> * [pagamenti.fn_get_or_create_vendite_contabile](/dbzero/pagamenti/funzioni/fn_get_or_create_vendite_contabile) — da dove la distinta viene
> * [pagamenti.fn_posta_riga_tardiva](/dbzero/pagamenti/funzioni/fn_posta_riga_tardiva) — la gemella per una riga sola, dopo la chiusura
> * [pagamenti.trgfn_vendite_contabili_guard_chiusura](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_chiusura) — perché la chiusura è una conseguenza
> * [pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_distinta_finale) — la quarta mossa, il prezzo della chiusura
> * [pagamenti.trgfn_vendite_contabili_righe_marca_fondo_eseguito](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_marca_fondo_eseguito) — come il fondo si accorge della registrazione

---

### 🎯 Scopo Principale

Registra una distinta contabile: trasforma in movimenti le righe pronte, le porta a
«registrata», scrive la conferma sulla distinta e la chiude. Una sola chiamata, tutto o
niente; risponde quanti movimenti sono nati, quante righe sono state registrate e quante
sono rimaste indietro, il totale registrato e l'esito.

In parole semplici: fin qui il denaro arrivato era **dichiarato**, scritto su un documento di
lavoro. Da qui viene **registrato**, e da quel momento conta nei saldi.

---

### ⭐ La dichiarazione di chi conferma

Chi preme «registra» ha davanti un elenco; fra quel momento e la registrazione la distinta
può cambiare — un collega abbina una riga, un import ne aggiunge un'altra. Registrare
qualcosa di diverso da ciò che è stato approvato sarebbe **irreversibile**, quindi chi
conferma può dichiarare **quante righe pronte aveva davanti e per che totale**: la funzione
confronta e, se non corrisponde, **rifiuta prima di scrivere qualsiasi cosa**.

⚠️ I due valori sono **facoltativi ma legati**: o tutti e due o nessuno. Mezza dichiarazione
non si può verificare, e accettarla in silenzio vorrebbe dire registrare senza controllo
*credendo* di averlo fatto. Assenti, si registra ciò che c'è: è la strada dei processi
automatici, che non hanno un operatore che guarda.

---

### ⭐ «Niente da registrare» non è un errore

La funzione non solleva: dice l'esito (`POSTATA` oppure `NULLA_DA_POSTARE`) e basta. Un
errore dovrebbe voler dire che qualcosa non funziona, e *«non c'era niente da fare»* è una
risposta vera.

⚠️ E l'altra strada aveva un costo concreto: il database **scrive nel registro degli errori
prima di sollevare**, quindi ogni pulsante premuto due volte avrebbe lasciato un errore che
errore non è. Il messaggio *«l'hai già fatto»* lo mette il frontend leggendo l'esito: *il
database dice il fatto, chi parla con la persona decide come raccontarlo.*

---

### L'ordine delle cose, e perché è quello

1. **si blocca la distinta**, per non registrare due volte in parallelo;
2. **si controlla lo stato**: si registra **solo** da uno stato **registrabile**
   (`is_registrabile` sul catalogo, oggi la sola `VALIDATA`, il gesto «ho finito di
   inserire»). Da bozza la distinta potrebbe cambiare mentre la si registra; da chiusa o
   annullata il lavoro è finito. La domanda si fa al catalogo, che il dettaglio della
   distinta espone per spegnere «Registra» col motivo;
3. **si quadra la distinta**, se dichiara un totale: tutte le righe attive contro
   `importo_dichiarato`;
4. **si verifica la dichiarazione** di chi conferma;
5. **si rifiuta parlando** se una riga pronta non dice a quale fattura e a quale cliente
   appartiene;
6. **si scrivono i movimenti**;
7. **si portano le righe a «registrata»**;
8. **si scrive la conferma e si chiude**.

⚠️ **Due controlli che sembrano uno solo, e non lo sono.** La **quadratura** chiede *«ho
letto tutto quello che è arrivato?»* (tutte le righe contro il totale dichiarato all'arrivo).
La **dichiarazione** chiede *«sto registrando quello che mi hanno approvato?»* (le righe
pronte adesso contro quelle che l'operatore ha contato un istante fa).

---

### 🔴 Due istruzioni separate, legate da un elenco di id

Per il chiamante l'operazione è atomica per costruzione: è una *funzione madre*, una sola
chiamata. Dentro però la scrittura dei movimenti e l'aggiornamento delle righe restano **due
istruzioni separate**: con la RLS attiva padre e figlio nella stessa istantanea **non si
vedono**, e il controllo di scrittura nega fail-closed. Un'istruzione unica sarebbe elegante
e sbagliata.

⚠️ **E le due sono legate dall'elenco degli id scritti, non dal ripetere la stessa
condizione**: fra l'una e l'altra un'altra sessione può aggiungere una riga alla distinta, e
ripetere la condizione la porterebbe a «registrata» **senza il suo movimento**. Un secondo
movimento per la stessa riga è impossibile per costruzione: lo vieta l'unicità del movimento
sulla riga.

---

### Le date del movimento

La data effettiva è la data di pagamento della riga, o, se manca, la data contabile della
distinta; data contabile e data di registrazione vengono dalla distinta; la data di
contabilizzazione è il giorno operativo. Il `meta` del movimento porta l'origine `POSTING`,
che nel giornale lo distingue da una registrazione tardiva.

---

### ⭐ La chiusura è una conseguenza, non una scelta

Registrata, la distinta va a **`CHIUSA`**. Non è un gesto separato: dopo la registrazione
righe pronte non ne restano, e il
[guard di chiusura](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_chiusura) lascia
passare la chiusura proprio perché è vera.

⚠️ **Ha un prezzo.** Una riga rimasta «da abbinare» sotto una distinta chiusa **non deve
poter diventare pronta**, o sarebbe denaro dichiarato che non verrà registrato mai. Lo
impedisce la **quarta mossa** di
[trgfn_vendite_contabili_righe_guard_distinta_finale](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_distinta_finale).

`data_conferma` e `user_conferma` le scrive qui, tenendo **la prima volta**: la conferma è
l'atto di *registrare*, e quando è successo non si riscrive.

---

### ⭐ Il «resto»: la registrazione tardiva

Le righe che restano indietro possono essere solo **sospese** e **scartate**: non si valida
con righe ancora da lavorare. Una sospesa sotto la distinta chiusa **non è senza strada**: si
registra in ritardo, una riga alla volta, con
[pagamenti.fn_posta_riga_tardiva](/dbzero/pagamenti/funzioni/fn_posta_riga_tardiva) —
movimento suo, riga a «registrata», distinta che resta chiusa con la conferma di questa
funzione. Una scartata resta «non nostra», dentro la quadratura e fuori dal lavoro; se poi
risulta nostra, «Riprendi» e tardiva.

---

### ⛔ Ciò che non fa, ed è una scelta

* **Non crea, non modifica e non annulla fondi fattura**: *i fatti si aggiungono, i saldi si
  leggono, le decisioni le prende una persona*. ⭐ Il fondo però se ne accorge lo stesso:
  portando la riga a «registrata» fa scattare il trigger che porta l'atto del fondo a
  `ESEGUITO`.
* **Non tocca le rate**: l'abbinamento a una rata sta sulla riga, e il movimento nasce dalla
  riga così com'è.
* **Non scrive nel registro degli errori di suo**: lo fa l'helper quando solleva.

---

### Codici errore

* `E_PAGAMENTI_CHIAMATA_NON_VALIDA` — distinta nulla o non positiva, righe attese negative,
  o mezza dichiarazione: nessuna interfaccia li produce (tecnico).
* `E_CONTABILE_NON_TROVATA` — la distinta non esiste o non si vede.
* `E_CONTABILE_NON_REGISTRABILE` — la distinta non è in uno stato registrabile.
* `E_CONTABILE_TOTALE_DICHIARATO_NON_QUADRA` — le righe non sommano al totale dichiarato.
* `E_CONTABILE_DICHIARAZIONE_NON_CORRISPONDE` — la distinta è cambiata da quando chi
  conferma l'ha vista.
* `E_RIGA_CONTABILE_ABBINAMENTO_INCOMPLETO` — una riga pronta non dice a quale fattura e
  cliente appartiene.
* `E_CONTABILE_STATO_NON_CONFIGURATO` — manca a catalogo lo stato `POSTATA` della riga o
  `CHIUSA` della distinta (tecnico).

---

### Test

* `db/pgtap/pagamenti/test-fn-posta-contabile.sql` — da bozza non si registra; una
  dichiarazione che non corrisponde è rifiutata e non registra niente; un movimento per ogni
  riga pronta, le non pronte restano indietro; la quadratura fra movimenti e righe
  registrate; il saldo della fattura **cambia**; la distinta chiusa con la conferma scritta;
  la seconda registrazione rifiutata; la quarta mossa; «niente da registrare» come esito.
* `db/pgtap/pagamenti/test-posta-riga-tardiva-v1.sql` — la tardiva su una distinta
  registrata da questa funzione.

---

### Note di migrazione

* 2026-08-22 — nasce: è il punto in cui nasce il primo movimento
  del progetto. Fino ad allora nessuna funzione scriveva `pagamenti.vendite_movimenti`, e
  `fn_get_saldo_fattura` rispondeva *«residuo = totale»* per costruzione. La chiusura dopo la
  registrazione è una decisione di Tid dello stesso giorno; `data_conferma` e
  `user_conferma`, che esistevano vuote, le scrive da qui.
* 2026-09-18 — il controllo di stato
  legge `is_registrabile` al posto del letterale `'VALIDATA'`, con lo stesso codice e la
  stessa frase. Lo stesso giorno nasce la registrazione tardiva per le sospese rimaste sotto
  una distinta chiusa.

---

{% include-markdown "signature-core.md" %}
