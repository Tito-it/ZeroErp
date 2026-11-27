## 📘 Documentazione Concettuale – Funzione `script.fn_get_ba_emittente_sr_id_installazione`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[script.fn_get_ba_emittente_sr_id](/dbzero/script/manual/fn_get_ba_emittente_sr_id) — la stessa domanda, ma per chi agisce
>
[anagrafiche.fn_clienti_stessa_chiave](/dbzero/anagrafiche/funzioni/fn_clienti_stessa_chiave), [anagrafiche.fn_guard_cliente_chiave_unica](/dbzero/anagrafiche/funzioni/fn_guard_cliente_chiave_unica), [anagrafiche.trgfn_clienti_set_parent_istanza](/dbzero/anagrafiche/funzioni/trgfn_clienti_set_parent_istanza) — chi la usa: l'azienda nella chiave del cliente manuale
>
[anagrafiche.fn_check_ba_padre](/dbzero/anagrafiche/funzioni/fn_check_ba_padre) — chi la usa: un solo padre per cliente e per azienda
>
Approfondimenti tabelle:
>
[anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account)

---
### 🎯 Scopo Principale

Risponde a: **di quale azienda è questo billing account, per l'installazione?**

* se il billing account ha un collegamento proprio a un'azienda, è quella;
* altrimenti è l'**azienda predefinita** del sistema.

Non guarda chi sta lavorando. È la risposta che vale anche quando nessuno è
collegato: un job notturno, un altro utente, un'altra azienda. Ogni billing
account ha sempre il suo collegamento, e la risposta è quello; il ripiego sulla
predefinita riguarda solo l'istante della nascita, prima che il collegamento
sia scritto.

---

### Perché esiste accanto a `fn_get_ba_emittente_sr_id`

[`script.fn_get_ba_emittente_sr_id`](/dbzero/script/manual/fn_get_ba_emittente_sr_id)
risponde a tre livelli: il collegamento, poi **l'azienda di chi sta agendo**, poi
la predefinita. Il livello di mezzo serve nell'istante in cui un billing account
nasce: il trigger che lo collega non ha ancora scritto, e il billing account
«è» di chi lo sta creando.

Per le regole che devono valere uguali per tutti quella domanda è sbagliata:
la chiave del cliente manuale (due operatori di aziende diverse devono vedere la
stessa chiave) e il padre unico di un cliente per azienda non possono dipendere
da chi sta lavorando. Per loro serve la domanda senza chi agisce: è questa
funzione. Con ogni billing account collegato le due risposte coincidono; la
differenza resta nel principio, e nell'istante della nascita.

Non è una copia del risolutore: le due funzioni rispondono a due domande
diverse («per chi agisce» e «per l'installazione»), e condividono solo le due
letture di riga.

---

### Risposte

| Billing account | Risposta |
| --- | --- |
| con un collegamento | l'azienda del collegamento |
| senza collegamento (solo nell'istante della nascita) | l'azienda predefinita |
| senza collegamento, e nessuna predefinita | `NULL` (chi confronta lo tratta come «diverso»); senza nessuna azienda, del resto, il billing account non nasce |
| `NULL` | `NULL`: «nessun billing account» non è «non collegato» |

---

### Come si prova

* `db/pgtap/anagrafiche/test-billing-account-sempre-collegato-v1.sql` — spostata
  l'azienda predefinita, il billing account resta all'azienda del suo
  collegamento (test 7 e 8).
* `db/pgtap/anagrafiche/test-guard-albero-ba-omogeneo-v1.sql` — spostata la
  predefinita, padre e figlio restano sulla stessa azienda (test 10 e 11).

---

### Note di migrazione

* 2026-10-10 — nasce per i guard dello spostamento della predefinita, ritirati
  il 2026-11-26 quando ogni billing account ha avuto sempre il suo
  collegamento.
