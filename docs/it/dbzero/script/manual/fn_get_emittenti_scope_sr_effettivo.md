## 📘 Documentazione Concettuale – Funzione `script.fn_get_emittenti_scope_sr_effettivo`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[script.fn_get_emittenti_scope_sr_ids](/dbzero/script/manual/fn_get_emittenti_scope_sr_ids)
>
[script.fn_get_emittenti_scope_pk_ids](/dbzero/script/manual/fn_get_emittenti_scope_pk_ids)

---
### 🎯 Scopo Principale
(latest review 18-08-26)

Risponde a una domanda sola: **quali emittenti fiscali puo' vedere chi sta
leggendo, tenuto conto anche di una restrizione che il chiamante ha chiesto?**

Il risultato e' l'**intersezione** fra lo scope *di diritto* (quello che
l'utente ha) e la restrizione *richiesta*. La regola che la governa e' una:

> **Il chiamante puo' solo restringere. Mai allargare.**

---

### Il problema che risolve

Lo scope esce dal database con **tre** significati distinti:

| Valore | Significa |
| --- | --- |
| `NULL` | nessuna restrizione: li vede tutti |
| `'{}'` | nessun accesso: non ne vede nessuno |
| array | vede solo quelli elencati |

Due funzioni di ricerca ricevevano pero' quell'informazione **di ritorno dal
backend**, dopo un viaggio attraverso Python. E in Python la lista vuota e il
"non specificato" sono **entrambi falsi**: ogni modo naturale di scrivere quel
codice li fonde. I due estremi opposti — *tutto* e *niente* — arrivavano
appiattiti sullo stesso valore, e si appiattivano dalla parte che **apre**.

Non era una svista di chi aveva scritto quella riga: era un canale che perde per
costruzione, tanto che la stessa fusione era gia' avvenuta in due punti
indipendenti.

Questa funzione non corregge il viaggio: **toglie il viaggio**. Una risposta che
non esce dal database non puo' degradarsi per strada.

---

### Logica Operativa

1. **Attore nullo** (processo automatico senza utente): non c'e' uno scope di
   diritto da opporre, quindi vale la sola restrizione del chiamante. E' la
   convenzione di tutta la famiglia, non un'eccezione locale.
2. **Scope di diritto uguale a tutto** (super admin): decide il chiamante, che
   comunque puo' solo restringere.
3. **Scope di diritto vuoto**: si risponde vuoto, **mai** `NULL`. E' il punto
   per cui la funzione esiste: rispondere `NULL` qui vorrebbe dire *«vede
   tutto»*, cioe' ricreare in SQL lo stesso appiattimento che si voleva togliere.
4. **Nessuna restrizione richiesta**: vale lo scope di diritto.
5. **Altrimenti**: intersezione dei due insiemi.

---

### Impatto e Vantaggi

* nessun valore passato da fuori puo' **allargare** cio' che una lettura mostra;
* la regola *«solo restringente, mai allargante»* non e' nuova: e' la stessa con
  cui l'emittente attivo si combina con lo scope. Qui e' applicata a un
  parametro invece che a un'impostazione di sessione;
* l'errore Python a valle diventa **innocuo**: continua a scrivere una cosa
  falsa, ma non decide piu' niente.
