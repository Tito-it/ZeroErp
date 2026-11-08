## 📘 Documentazione Concettuale – Vista `dbops.vw_storico_scope_da_dichiarare`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.storico_scope_policy](/dbzero/dbops/tabelle/storico_scope_policy) — la mappa di cui la vista mostra il debito
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo che porta la vista nel digest
>
> Approfondimento viste:
>
> * [dbops.vw_rls_perimetro_scoperto](/dbzero/dbops/views/vw_rls_perimetro_scoperto) — lo stesso disegno per il perimetro della row level security
>
> Approfondimento funzioni:
>
> * [dbops.fn_storico_risolvi_scope](/dbzero/dbops/funzioni/fn_storico_risolvi_scope) — chi segue la mappa, e risponde vuoto dove la mappa tace
> * [dbops.fn_storico_arma_scope](/dbzero/dbops/funzioni/fn_storico_arma_scope) — chi arma la shadow quando la riga di mappa è giusta
>
> Guide:
>
> * [Storicizzazione delle tabelle](/guide/storicizzazione-tabelle) — la sezione «Di chi è una versione»

---

### 🎯 Scopo Principale

Il debito della mappa dello scope di storico: le madri storicizzate per cui nessuno ha ancora detto,
o non dice più il vero, da dove si prende l'emittente che protegge le loro versioni. Deve restare
**vuota**.

È la stessa domanda che il pgTAP della mappa fa in CI, portata nel digest settimanale perché si veda
anche su un database dove la CI non gira.

---

### ⭐ Perché serve, se c'è già il pgTAP

Il pgTAP ferma una consegna sbagliata. Ma la mappa può invecchiare **senza nessuna consegna**: una
tabella entra in RLS con un cantiere di un altro dominio, una tabella viene cancellata, la
storicizzazione viene tolta. Il pgTAP se ne accorge al primo build; la vista se ne accorge la prima
settimana, su ogni database.

---

### I tre motivi

| `motivo` | Che cosa dice | Come si chiude |
| --- | --- | --- |
| `SENZA_RIGA` | una madre **col trigger di storico** non ha una riga nella mappa: nessuno l'ha ancora guardata | si aggiunge la riga al CSV della mappa, col modo giusto, o `NESSUNO` con la ragione |
| `PROTETTA_NESSUNO` | la madre ha la **row level security accesa** ma la mappa dice `NESSUNO`: la sua storia è aperta. La ragione dichiarata è nel `dettaglio` | si passa la riga al modo giusto; la convergenza arma la shadow al migrate successivo |
| `RIGA_SENZA_MADRE` | una riga di mappa non ha più una madre col trigger: tabella cancellata o storicizzazione tolta | si toglie la riga dal CSV **e** con un changeSet di cancellazione, perché il mirror non cancella |

Il marcatore delle madri è il **trigger** su `script.trgfn_storico_generic`, non il nome di una
tabella in `storico`. Il confronto con la mappa passa per la risoluzione del nome qualificato: una
riga scritta con maiuscole o spazi diversi non vale come «trovata», ed esce due volte, come
`SENZA_RIGA` per la madre e come `RIGA_SENZA_MADRE` per la riga.

La colonna `shadow` è il nome che la shadow avrebbe: la vista non verifica che esista.

---

### Che cosa non compare

* le tabelle di `storico` che **non sono shadow**, come i registri delle fusioni di comuni e vie:
  non hanno una madre col trigger e non hanno una riga di mappa;
* una riga `NESSUNO` su una madre **senza** RLS: è la dichiarazione corretta, non un debito;
* una riga con un modo sbagliato ma non `NESSUNO` (una colonna che non c'è, una catena rotta): quella
  la vede solo il pgTAP.

---

### Legge con gli occhi di chi interroga

La vista è `security_invoker`: la mappa si legge con i privilegi di chi interroga, e l'applicazione ha
la lettura apposta.

---

### Test

* `db/pgtap/dbops/test-storico-scope-policy-v1.sql` — i test 2, 4 e 5 asseriscono gli stessi tre motivi
  in CI; i test 29-32 provano che la vista dica il vero su casi costruiti (una madre temporanea col
  trigger, prima senza riga e poi in RLS con riga `NESSUNO`; una riga di mappa senza madre) e che sia a
  catalogo in `dbops.presidi`, natura `ZERO`, cadenza settimanale.

---

### Note di migrazione

* 2026-09-12 — nasce per portare nel digest il debito della mappa (`brief-db-rls-storico-scope-congelato`,
  §4.2 e §4c).

---

{% include-markdown "signature-core.md" %}
