## 📘 Documentazione Concettuale – Funzione `pagamenti.fn_posta_contabile`

> 👀 **Vedi anche**
>
> **Tabelle:**
>
> • [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili) · [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe) · [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti)
>
> **Funzioni:**
>
> • [pagamenti.fn_get_saldo_fattura](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura) — quella che, da adesso, smette di dire sempre la stessa cosa
> • [pagamenti.fn_get_or_create_vendite_contabile](/dbzero/pagamenti/funzioni/fn_get_or_create_vendite_contabile) — da dove la distinta viene
>
> **Piano:** [brief-db-posting-e-abbinamento-rata](/dev/work-in-progress/brief-db-posting-e-abbinamento-rata) §2.1 S1-10

---

### 🎯 Scopo Principale

(rev 2026-08-22)

Trasforma in **movimenti contabili** le righe di una distinta che sono pronte a
diventarlo, e chiude la distinta.

⭐ **È il punto in cui nasce il primo movimento del progetto.** Fino a qui
nessuna funzione del database scriveva `pagamenti.vendite_movimenti`, quindi
`fn_get_saldo_fattura` rispondeva *«residuo = totale»* **per costruzione**: non
perché nessuno avesse pagato, ma perché non c'era modo di registrarlo. Da qui
comincia a dire la verità.

In parole semplici: fin qui il denaro arrivato era **dichiarato** — scritto su
un documento di lavoro. Adesso viene **registrato**, e da quel momento conta nei
saldi.

---

### Chi chiama, e che cosa passa

```sql
SELECT * FROM pagamenti.fn_posta_contabile(
    p_contabile_id  => 42,
    p_righe_attese  => 3,        -- facoltativo, ma insieme al prossimo
    p_totale_atteso => 1250.00
);
```

| Parametro | Che cos'è |
| --- | --- |
| `p_contabile_id` | la distinta da registrare |
| `p_righe_attese` · `p_totale_atteso` | ⭐ **la dichiarazione di chi conferma**: quante righe pronte aveva davanti, e per che totale |

> ⭐ **Perché la dichiarazione sta nella firma.** Chi preme «registra» ha
> davanti un elenco; fra quel momento e la registrazione la distinta può
> cambiare — un collega abbina una riga, un import ne aggiunge un'altra.
> Registrare qualcosa di diverso da ciò che è stato approvato sarebbe
> **irreversibile**, quindi la funzione confronta e, se non corrisponde,
> **rifiuta prima di scrivere qualsiasi cosa**.
>
> ⚠️ I due parametri sono **facoltativi ma legati**: o tutti e due o nessuno.
> Mezza dichiarazione non si può verificare, e accettarla in silenzio
> significherebbe registrare senza controllo *credendo* di averlo fatto.
> Assenti, si registra ciò che c'è — è la strada dei processi automatici, che
> non hanno un operatore che guarda.

### Che cosa risponde

| Colonna | Che cos'è |
| --- | --- |
| `movimenti_creati` | quanti movimenti sono nati |
| `righe_postate` | quante righe sono passate a «registrata» |
| `righe_saltate` | quante righe restano indietro, cioè quelle di cui nessuno ha ancora detto che cosa ne è stato |
| `totale_postato` | quanto denaro è stato registrato |
| `esito` | `POSTATA` oppure `NULLA_DA_POSTARE` |

> ⭐ **«Niente da registrare» non è un errore.** La funzione non solleva: dice
> l'esito e basta. Un errore dovrebbe voler dire che qualcosa non funziona, e
> *«non c'era niente da fare»* è una risposta vera.
>
> ⚠️ E c'era un costo concreto nell'altra strada: il database **scrive nel
> registro degli errori prima di sollevare**, quindi ogni pulsante premuto due
> volte avrebbe lasciato un errore che errore non è — rumore in mezzo alle cose
> vere. Il messaggio *«l'hai già fatto»* lo mette il frontend leggendo l'esito:
> *il database dice il fatto, chi parla con la persona decide come
> raccontarlo.*

---

### L'ordine delle cose, e perché è quello

1. **si blocca la distinta** (`FOR UPDATE`), per non registrare due volte in parallelo;
2. **si controlla lo stato**: si registra **solo** da uno stato **registrabile** — `is_registrabile` sul catalogo, oggi la sola `VALIDATA`, che è il gesto «ho finito di inserire». Da bozza la distinta potrebbe cambiare mentre la si registra; da chiusa o annullata il lavoro è finito. ⭐ Dal 18-09-2026 (D20-d) la domanda si fa al **catalogo** e non al letterale `'VALIDATA'`: stesso codice, stessa frase, e il dettaglio espone la stessa bandiera per spegnere «Registra» col motivo;
3. **si quadra la distinta**, se dichiara un totale: tutte le righe attive contro `importo_dichiarato`;
4. **si verifica la dichiarazione** di chi conferma;
5. **si rifiuta parlando** se una riga pronta non dice a quale fattura e a quale cliente appartiene;
6. **si scrivono i movimenti**;
7. **si portano le righe a «registrata»**;
8. **si scrive la conferma e si chiude**.

> ⚠️ **Due controlli che sembrano uno solo, e non lo sono.** La **quadratura**
> chiede *«ho letto tutto quello che è arrivato?»* (tutte le righe contro il
> totale dichiarato all'arrivo). La **dichiarazione** chiede *«sto registrando
> quello che mi hanno approvato?»* (le righe pronte adesso contro quelle che
> l'operatore ha contato un istante fa). Rispondono a domande diverse e
> scattano in momenti diversi.

### 🔴 Perché due statement e non una CTE sola

Il chiamante fa **una sola `SELECT`**, quindi l'operazione è atomica per
costruzione (è una *funzione madre*). Dentro però l'`INSERT` dei movimenti e
l'`UPDATE` delle righe restano **due statement separati**: con la RLS attiva
padre e figlio nella stessa snapshot **non si vedono**, e il controllo di
scrittura nega fail-closed. Una CTE unica sarebbe elegante e sbagliata.

⚠️ **E i due sono legati da un elenco di id, non dal ripetere la stessa
condizione**: fra l'uno e l'altro un'altra sessione può aggiungere una riga alla
distinta, e ripetere la condizione la porterebbe a «registrata» **senza il suo
movimento**.

---

### ⭐ La chiusura è una conseguenza, non una scelta

Registrato, la distinta va a **`CHIUSA`**. Non è un gesto separato: dopo il
posting righe pronte non ne restano, e il guard di chiusura dichiara che le
altre non devono bloccare.

⚠️ **Ha un prezzo, ed è pagato nello stesso lotto.** Una riga rimasta «da
abbinare» sotto una distinta chiusa **non deve poter diventare pronta**, o
sarebbe denaro dichiarato che non verrà registrato mai. Lo impedisce la
**quarta mossa** di
[trgfn_vendite_contabili_righe_guard_distinta_finale](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_distinta_finale).

### ⭐ `data_conferma` / `user_conferma`: due colonne che nessuno scriveva

Esistevano da sempre e restavano vuote. Le scrive qui, con un `COALESCE` che
**tiene la prima volta**: la conferma è l'atto di *registrare*, e quando è
successo non si riscrive.

---

### ⚠️ Error handling

| Codice | Quando |
| --- | --- |
| `E_PAGAMENTI_CHIAMATA_NON_VALIDA` (TECNICO) | id nullo o non positivo, o mezza dichiarazione: valori che nessuna interfaccia produce |
| `E_CONTABILE_NON_TROVATA` (NON_TROVATO) | la distinta non esiste |
| `E_CONTABILE_NON_REGISTRABILE` (CONFLITTO_STATO) | la distinta non è in uno stato registrabile (`is_registrabile`, oggi solo `VALIDATA`) |
| `E_CONTABILE_TOTALE_DICHIARATO_NON_QUADRA` (DATO_ERRATO) | le righe non sommano al totale dichiarato |
| `E_CONTABILE_DICHIARAZIONE_NON_CORRISPONDE` (CONFLITTO_STATO) | la distinta è cambiata da quando chi conferma l'ha vista |
| `E_RIGA_CONTABILE_ABBINAMENTO_INCOMPLETO` (DATO_ERRATO) | una riga pronta non dice a quale fattura e cliente appartiene |
| `E_CONTABILE_STATO_NON_CONFIGURATO` (TECNICO) | manca a catalogo lo stato `POSTATA` o `CHIUSA` |

---

### ⛔ Ciò che NON fa, e va detto perché è una scelta

* **non crea, non modifica e non annulla fondi fattura**: *i fatti si
  aggiungono, i saldi si leggono, le decisioni le prende una persona*.
  ⭐ Il fondo però se ne accorge lo stesso: portando la riga a «registrata» fa
  scattare il trigger che porta l'atto del fondo a `ESEGUITO`;
* **non tocca le rate**: nel modello dell'abbinamento non esistono ancora — è
  la slice 2 del cantiere;
* **non scrive nel registro degli errori di suo**: lo fa l'helper quando
  solleva.

### ⭐ E il «resto»? — la registrazione tardiva (dal 18-09-2026)

Le righe che restano indietro (`righe_saltate`) dopo il 18-09 possono essere solo
**sospese** e **scartate**: D20-a impedisce di validare con righe non lavorate
sotto. Una sospesa sotto la distinta chiusa **non è più senza strada**: si
registra in ritardo, per riga, con
[pagamenti.fn_posta_riga_tardiva](/dbzero/pagamenti/funzioni/fn_posta_riga_tardiva)
(D20-b) — movimento suo, riga a «registrata», distinta che resta chiusa con la
conferma di questa madre. Una scartata resta «non nostra», dentro la quadratura e
fuori dal lavoro (D20-c); se poi risulta nostra, «Riprendi» e tardiva.

### Presidio

`db/pgtap/pagamenti/test-fn-posta-contabile.sql` — 20 asserzioni, fra cui la
**quadratura** (somma dei movimenti = somma delle righe registrate) e la prova
che il saldo della fattura **cambia**, che è la ragione per cui questa slice
esiste.

{% include-markdown "signature-core.md" %}
