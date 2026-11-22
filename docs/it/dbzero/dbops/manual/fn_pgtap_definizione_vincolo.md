## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_definizione_vincolo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento viste:
>
> * [dbops.vw_stati_check_scrittori](/dbzero/dbops/views/vw_stati_check_scrittori) — legge i valori di un `CHECK` e regge le stesse due forme
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — un vincolo si asserisce per nome e definizione insieme

---

### 🎯 Scopo Principale

Restituisce la **definizione di un vincolo** di una tabella, come `pg_get_constraintdef`, ma in
**una forma sola**: quella che il vincolo ha quando nasce sul database. Serve ai test che
asseriscono un vincolo per nome e definizione.

---

### ⭐ Stesso vincolo, due testi

Su PostgreSQL 19 lo stesso `CHECK (col IN ('A', 'B'))` su una colonna `varchar` si legge in due
modi, secondo la strada da cui il vincolo è arrivato:

| Il vincolo… | Si legge |
| --- | --- |
| è nato sul database (database costruito dal changelog, cioè la CI e ogni installazione nuova) | `ANY ((ARRAY['A'::character varying, 'B'::character varying])::text[])` |
| è stato riletto da un dump della 18 (`pg_upgrade`, un restore) | `ANY (ARRAY[('A'::character varying)::text, ('B'::character varying)::text])` |

La regola è la stessa. Un test che ne asserisce una sola dice su quale macchina gira, non com'è
fatto il vincolo: è verde su un database aggiornato e rosso in CI, o il contrario.

La funzione riporta la seconda forma alla prima. Lo fa un array alla volta, con `ANY` e `ALL`,
e solo se **ogni** elemento è un letterale `varchar` col suo cast. Un array di `text`
(`ARRAY['A'::text]`) è nato così e resta com'è. Ogni altra parte del testo è quella di
`pg_get_constraintdef`.

---

### ⚠️ Una differenza nota, non una normalizzazione generale

La funzione copre solo la differenza osservata sulla 19 per gli `IN` su `varchar`. Se un'altra
forma cambiasse testo fra un vincolo nato e uno riletto, il test che la asserisce tornerebbe
rosso su una delle due strade: la cura è aggiungere quella forma qui, non riscrivere il testo
atteso del test.

---

### Codici errore

Nessuno. Un vincolo che non esiste restituisce `NULL`, e l'asserzione che lo confronta con il
testo atteso è rossa.

---

### Test

* `db/pgtap/dbops/test-fn-pgtap-definizione-vincolo-v1.sql` — costruisce le due forme in una
  tabella temporanea: il vincolo scritto con `IN`, e lo stesso vincolo scritto col testo del
  dump della 18, che la 19 rilegge nell'altra forma.

---

### Note di migrazione

* 2026-11-22 — nasce perché tre pgTAP asserivano la forma di dbdev, aggiornato dalla 18, ed
  erano rossi in CI (`20261122-40`).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
