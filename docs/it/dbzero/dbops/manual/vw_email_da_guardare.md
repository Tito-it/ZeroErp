## 📘 Documentazione Concettuale – Vista `dbops.vw_email_da_guardare`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.email_log](/dbzero/config/tabelle/email_log) — la coda delle email
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo che la iscrive
>
> Approfondimento viste:
>
> * [config.vw_email_in_coda](/dbzero/config/views/vw_email_in_coda) — la definizione di «in coda», scritta una volta sola
>
> Approfondimento funzioni:
>
> * [dbops.fn_conta_presidio](/dbzero/dbops/funzioni/fn_conta_presidio) — il conteggio del digest
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — come si legge un presidio che deve restare vuoto

---

### 🎯 Scopo Principale

Le email che la coda deve a qualcuno da oltre un'ora e che nessuno ha preso in mano. Deve
restare vuota: se si riempie, il processo `send_pending_emails` non gira, o gira e non svuota.

---

### ⛔ Perché serve: nessuno aspetta una mail a un'ora precisa

Senza questa vista le email si accumulerebbero in coda **per sempre, in silenzio**: nessuno nota
la mancanza di un messaggio che non sapeva di dover ricevere. Non è un'ipotesi: il timer del
processo non era installato su `backend-dev`, e l'unico motivo per cui non ci sono state
conseguenze è che la coda era vuota.

---

### ⭐ Si presidia l'effetto, non lo schedulatore

Nessuno chiede al sistema operativo se il timer è acceso: si guarda **la coda che si accumula**.
È più robusto, perché prende anche il processo che gira e sbaglia, e non ha bisogno di sapere
niente della macchina. Un timer mai installato non ha un effetto: le email restano ferme, e
questa vista le vede.

---

### ⭐ La definizione di «in coda» non è qui

Sta in `config.vw_email_in_coda`, scritta **una volta sola** per il processo che invia e per
questo presidio. Qui c'è **solo la soglia**: la riga era dovuta da più di un'ora.

⛔ In coda non ci sono solo le email in attesa e quelle da ritentare: ci sono anche le **fallite
con tentativi residui**, che il processo ripesca apposta. Copiare qui il filtro del processo
sarebbe stata la seconda sede dello stesso predicato, che diverge alla prima modifica.

---

### Due motivi, perché sono due gesti diversi

| Motivo | Che cos'è successo | Che cosa si fa |
| --- | --- | --- |
| **mai presa in mano** | un'email in attesa e vecchia: il processo non è passato | si riaccende `send_pending_emails` |
| **ritentativo dovuto e mai eseguito** | un'email da ritentare, o fallita con tentativi residui, il cui tentativo era dovuto e nessuno l'ha ripreso | si guarda perché il processo non ritenta, o non gira |

---

### ⚠️ La soglia è una scelta, non una misura

Un'ora. Non deriva dalla cadenza del processo: una soglia dedotta dai tempi di oggi si
taglierebbe addosso al carico di oggi. Un'ora dice «qualcosa è chiaramente sbagliato», e basta.

⭐ L'attesa fra un tentativo e l'altro è rispettata per costruzione: l'ora si misura da quando la
riga era **dovuta** (il prossimo tentativo), non da quando è nata. Una riga col prossimo
tentativo fra dieci minuti non è in ritardo e non compare.

---

### ⛔ Perimetro `DEFINER`, e non è una scelta

`config.email_log` ha la row level security e questa vista è `security_invoker`: una persona la
legge **col suo perimetro**; il digest, un comando senza identità, la **conta** da proprietario
con `dbops.fn_conta_presidio` e riporta **il numero**, mai le righe. Senza, «zero righe» e «non ho
potuto vedere» si scriverebbero uguale.

⚠️ Sta in `dbops` e non in `config` perché il catalogo dei presidi pretende a catalogo ogni vista
degli schemi che vi compaiono: una riga `config.vw_…` porterebbe dentro tutte le viste di `config`.

---

### Test

* `db/pgtap/dbops/test-vw-email-da-guardare.sql` — costruisce i casi dalla porta di sistema (quindi
  anche su un database vuoto) e li interroga per nome: i due motivi che devono comparire, quelli
  che non devono (il ritentativo non ancora dovuto, la fallita senza tentativi, l'attesa recente),
  il momento da cui si misura e il conteggio da proprietario.

---

### Note di migrazione

* 2026-09-11 — nasce con il presidio dei processi che non ne avevano uno
  (`brief-db-quattro-processi-senza-presidio` §5).

---

{% include-markdown "signature-core.md" %}
