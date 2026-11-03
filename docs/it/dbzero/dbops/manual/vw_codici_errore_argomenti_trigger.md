## 📘 Documentazione Concettuale – View `dbops.vw_codici_errore_argomenti_trigger`

> 👀 **Vedi anche**
>
Approfondimenti viste:
>
[dbops.vw_punti_canale_campo](/dbzero/dbops/manual/vw_punti_canale_campo)
>
[dbops.vw_codici_errore_da_dichiarare](/dbzero/dbops/manual/vw_codici_errore_da_dichiarare)
>
Approfondimenti funzioni:
>
[dbops.fn_trigger_argomenti](/dbzero/dbops/funzioni/fn_trigger_argomenti)

---
### 🎯 Scopo Principale
(latest review 03-11-2026)

Un elenco, non un allarme: per ogni **trigger** del database, quali **codici
d'errore** passa alla sua funzione come argomento.

Serve perché certe regole sono scritte una volta sola, in una funzione
generica, e montate su molte tabelle: il lucchetto di colonna, il blocco dei
documenti fuori bozza, la coerenza fra emittente e cliente. La funzione non sa
da sola quale codice usare: glielo dice il trigger, al momento del montaggio.
Il codice quindi **non è scritto nel testo della funzione**, ma negli argomenti
del trigger.

---

### ⭐ Perché esiste da sola

Due controlli cercavano i codici d'errore solo nel testo delle funzioni, e per
loro questi codici non esistevano:

* il controllo sul **canale del campo** (`vw_punti_canale_campo`) non vedeva
  che la coerenza fra emittente e cliente evidenzia il campo giusto, e il
  backend aveva dovuto scrivere un'eccezione per non dare un falso rosso;
* la **misura dei codici** (`vw_codici_errore_da_dichiarare`) non vedeva trenta
  codici: tutti avevano la loro regola di risposta, ma un codice nuovo montato
  così, senza regola, non avrebbe fatto scattare nessun allarme.

Tutti e due hanno bisogno della stessa lettura. Scritta dentro ciascuno, il
giorno in cui una cambia le due misure direbbero cose diverse sullo stesso
fatto. Perciò la lettura sta **qui**, una volta, e le due viste la interrogano.

---

### Come si legge

| Colonna | Che cosa porta |
| --- | --- |
| `funzione` | la funzione generica che riceve il codice (`schema.nome`) |
| `trigger_nome` | il trigger che la monta |
| `tabella` | la tabella del trigger (`schema.nome`) |
| `posizione` | quale argomento del trigger è il codice, contando da 1 |
| `codice` | il codice d'errore |
| `funzione_oid`, `trigger_oid` | gli identificativi interni, per chi incrocia con altre viste di sistema |

---

### ⚠️ Che cosa è un codice, qui

Un argomento che è **per intero** un codice (`E_` seguito da maiuscole, cifre e
trattini bassi). Un pezzo di parola no: lo stato `ORDINE_VENDITA` contiene la
sequenza `E_VENDITA`, ma non è un codice, e una ricerca libera lo contava. Il
27 ottobre due codici fantasma erano nati proprio così.

Oggi i codici stanno sempre in un argomento a sé. Se una funzione generica
cominciasse a riceverne più di uno in una lista, la lista andrebbe letta con le
regole di quella funzione, non con questa vista.

---

### Esempio d'uso

Le funzioni generiche e quanti codici ricevono:

```sql
SELECT funzione, count(DISTINCT codice) AS codici, count(DISTINCT trigger_oid) AS trigger
  FROM dbops.vw_codici_errore_argomenti_trigger
 GROUP BY funzione
 ORDER BY codici DESC;
```

Origine: voce D24 di `docs/it/dev/work-in-progress/migliorie-generali-da-test-valutazione.md`.
Test: `db/pgtap/dbops/test-punti-canale-campo-v1.sql` (casi 17 e 18).

---

{% include-markdown "signature-core.md" %}
