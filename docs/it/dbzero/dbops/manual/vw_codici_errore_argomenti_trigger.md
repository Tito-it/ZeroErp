## 📘 Documentazione Concettuale – Vista `dbops.vw_codici_errore_argomenti_trigger`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento viste:
>
> * [dbops.vw_punti_canale_campo](/dbzero/dbops/views/vw_punti_canale_campo) — il presidio del canale del campo, che la legge
> * [dbops.vw_codici_errore_da_dichiarare](/dbzero/dbops/views/vw_codici_errore_da_dichiarare) — la misura del terzo lato, che la legge
>
> Approfondimento funzioni:
>
> * [dbops.fn_trigger_argomenti](/dbzero/dbops/funzioni/fn_trigger_argomenti) — taglia gli argomenti del trigger

---

### 🎯 Scopo Principale

L'elenco dei codici d'errore che ogni trigger passa alla sua funzione come argomento: una riga per
trigger e argomento, quando l'argomento è per intero un codice. È una derivazione letta da due
presidi, non un allarme.

Certe regole sono scritte una volta sola, in una funzione generica, e montate su molte tabelle: il
lucchetto di colonna, il blocco dei documenti fuori bozza, la coerenza fra emittente e cliente. La
funzione non sa da sola quale codice usare: glielo dice il trigger, al montaggio. Il codice quindi
non è scritto nel testo della funzione, ma negli argomenti del trigger.

---

### ⭐ Perché esiste da sola

Due controlli cercavano i codici solo nel testo delle funzioni, e per loro questi non esistevano:

* il presidio del **canale del campo**
  ([vw_punti_canale_campo](/dbzero/dbops/views/vw_punti_canale_campo)) non vedeva che la coerenza
  fra emittente e cliente evidenzia il campo giusto, e il backend aveva dovuto scrivere
  un'eccezione per non dare un falso rosso;
* la **misura dei codici**
  ([vw_codici_errore_da_dichiarare](/dbzero/dbops/views/vw_codici_errore_da_dichiarare)) non
  vedeva i codici dei building block trigger: un codice nuovo montato così, senza la sua regola di
  risposta, non avrebbe fatto scattare il cancello.

Tutti e due hanno bisogno della stessa lettura. Scritta dentro ciascuno, il giorno in cui una cambia
le due misure direbbero cose diverse sullo stesso fatto: la lettura sta qui, una volta.

---

### Come si legge

| Colonna | Che cosa porta |
| --- | --- |
| `funzione` | la funzione generica che riceve il codice, come testo `schema.nome` |
| `trigger_nome` | il trigger che la monta |
| `tabella` | la tabella del trigger, come testo `schema.nome` |
| `posizione` | quale argomento del trigger è il codice, contando da 1 |
| `codice` | il codice d'errore |
| `funzione_oid`, `trigger_oid` | gli identificativi interni, per chi incrocia con altre viste di sistema |

Tabella e funzione sono testo e non riferimenti di catalogo: un riferimento di catalogo in colonna si
stampa con il `search_path` di chi legge, e due lettori vedrebbero nomi diversi. Entrano solo i
trigger scritti dal progetto, non quelli interni di PostgreSQL.

---

### ⚠️ Che cosa è un codice, qui

Un argomento che è **per intero** un codice: `E_` seguito da maiuscole, cifre e trattini bassi. Un
pezzo di parola no: lo stato `ORDINE_VENDITA` contiene la sequenza `E_VENDITA`, ma non è un codice,
e una ricerca libera lo contava.

La vista riconosce la forma di un codice di progetto, non la grammatica di una funzione generica: se
un building block cominciasse a ricevere più codici in una lista dentro un solo argomento, la lista
andrebbe letta con le regole di quella funzione, non con questa vista.

---

### Test

* `db/pgtap/dbops/test-punti-canale-campo-v1.sql` — un building block che riceve il codice negli
  argomenti del trigger compare nel presidio del canale del campo e nella misura del terzo lato
  (casi costruiti).

---

### Note di migrazione

* 2026-10-27 — due codici fantasma erano nati da una ricerca libera nelle stringhe, che contava
  `E_VENDITA` dentro `ORDINE_VENDITA`.
* 2026-11-03 — nasce con D24 di `migliorie-generali-da-test-valutazione`, e le due viste lettrici
  passano a leggerla.

---

{% include-markdown "signature-core.md" %}
