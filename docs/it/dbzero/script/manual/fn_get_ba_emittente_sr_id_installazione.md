## 📘 Documentazione Concettuale – Funzione `script.fn_get_ba_emittente_sr_id_installazione`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[script.fn_get_ba_emittente_sr_id](/dbzero/script/manual/fn_get_ba_emittente_sr_id) — la stessa domanda, ma per chi agisce
>
[anagrafiche.fn_guard_istanza_ba_gestore_globale](/dbzero/anagrafiche/manual/fn_guard_istanza_ba_gestore_globale) e [anagrafiche.fn_guard_albero_ba_gestore_globale](/dbzero/anagrafiche/manual/fn_guard_albero_ba_gestore_globale) — chi la usa
>
Approfondimenti tabelle:
>
[anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account)

---
### 🎯 Scopo Principale
(latest review 10-10-26)

Risponde a: **di quale azienda è questo billing account, per l'installazione?**

* se il billing account ha un collegamento proprio a un'azienda, è quella;
* altrimenti è l'**azienda predefinita** del sistema.

Non guarda chi sta lavorando. È la risposta che vale anche quando nessuno è
collegato: un job notturno, un altro utente, un'altra azienda.

---

### Perché esiste accanto a `fn_get_ba_emittente_sr_id`

[`script.fn_get_ba_emittente_sr_id`](/dbzero/script/manual/fn_get_ba_emittente_sr_id)
risponde a tre livelli: il collegamento, poi **l'azienda di chi sta agendo**, poi
la predefinita. Il livello di mezzo serve nell'istante in cui un billing account
nasce: il trigger che lo collega non ha ancora scritto, e il billing account
«è» di chi lo sta creando.

Per lo **spostamento dell'azienda predefinita** quella risposta è sbagliata. Se
a spostarla è un utente con la sua azienda, un billing account senza
collegamento sembra restare a quell'azienda, e il controllo non vede che
un'istanza o un albero finiranno su due aziende appena l'utente esce. Per quel
controllo serve la domanda senza chi agisce: è questa funzione.

Non è una copia del risolutore: le due funzioni rispondono a due domande
diverse («per chi agisce» e «per l'installazione»), e condividono solo le due
letture di riga.

---

### Risposte

| Billing account | Risposta |
| --- | --- |
| con un collegamento | l'azienda del collegamento |
| senza collegamento | l'azienda predefinita |
| senza collegamento, e nessuna predefinita | `NULL` (chi confronta lo tratta come «diverso») |
| `NULL` | `NULL`: «nessun billing account» non è «non collegato» |

---

### Come si prova

`db/pgtap/anagrafiche/test-istanza-ba-gestore-globale-v1.sql` (test 2, e i test
3 e 6 per i guard che la usano).

Brief: `brief-db-istanza-nasce-col-ba-residui` (D-5).
