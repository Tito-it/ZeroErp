## 📘 Documentazione Concettuale – View `dbops.vw_email_da_guardare`

> 👀 **Vedi anche**
>
Approfondimenti viste:
>
[config.vw_email_in_coda](/dbzero/config/manual/vw_email_in_coda) — *la definizione di «in coda», scritta una volta sola*
>
Approfondimenti tabelle:
>
[config.email_log](/dbzero/config/manual/email_log)
> [dbops.presidi](/dbzero/dbops/manual/presidi)
>
Approfondimenti funzioni:
>
[dbops.fn_conta_presidio](/dbzero/dbops/manual/fn_conta_presidio)

---
### 🎯 Scopo Principale
(latest review 11-09-2026)

Elenca le email che **la coda deve a qualcuno da oltre un'ora e che nessuno ha
preso in mano**. Deve restare vuota.

Se resta piena, il processo `send_pending_emails` non gira — o gira e non
svuota. È il presidio che `config.email_log` non aveva: senza, le email si
accumulavano in coda **per sempre, in silenzio**, perché nessuno aspetta una mail
entro un tempo preciso.

⛔ Non è un'ipotesi: quel timer non era installato su `backend-dev`, e l'unico
motivo per cui non ci sono state conseguenze è che la coda era vuota.

---

### ⭐ Si presidia l'effetto, non lo schedulatore

Nessuno chiede a systemd se il timer è acceso: si guarda **la coda che si
accumula**. È più robusto — prende anche il processo che gira e sbaglia — e non
ha bisogno di sapere niente dell'host. Un timer mai installato non ha un
effetto: le email restano ferme, e questa vista le vede.

---

### ⭐ La definizione di «in coda» non è qui

Sta in [config.vw_email_in_coda](/dbzero/config/manual/vw_email_in_coda), scritta
**una volta sola** per il cron e per questo presidio. Qui c'è **solo la soglia**:
`dovuta_dal < now() - 1 ora`.

⛔ Il brief chiedeva «`PENDING` e `RETRY`». Mancavano i **`FAILED` con tentativi
residui**, che il cron ripesca apposta (è il recupero). Copiare la `WHERE` del
cron in questa vista sarebbe stata la seconda sede dello stesso predicato — che
diverge alla prima modifica, come è già successo fra un commento e una `SELECT`.

---

### Due motivi, perché sono due gesti diversi

| Motivo | Che cos'è successo | Che cosa si fa |
| --- | --- | --- |
| **mai presa in mano** | una `PENDING` vecchia: il cron non è passato | si riaccende `send_pending_emails` |
| **ritentativo dovuto e mai eseguito** | un `RETRY`/`FAILED` il cui prossimo tentativo era dovuto e nessuno l'ha ripreso | si guarda perché il cron non ritenta — o non gira |

---

### ⚠️ La soglia è una scelta, non una misura

Un'ora. Il cron gira ogni 5 minuti e un'ora sono «12 giri», ma non è quello
l'argomento: una soglia dedotta dai tempi di oggi si taglierebbe addosso al
carico di oggi. Un'ora dice «qualcosa è chiaramente sbagliato», e basta.

⭐ Il **backoff** dei `RETRY` è rispettato per costruzione: `dovuta_dal` misura da
quando la riga era **dovuta** (`prossimo_tentativo`), non da quando è nata. Una
riga col prossimo tentativo fra dieci minuti non è in ritardo e non compare.

---

### ⛔ Perimetro `DEFINER`, e non è una scelta

`config.email_log` ha la row level security e questa vista è `security_invoker`:
una persona la legge **col suo perimetro**; il digest — un comando senza veste —
la **conta** con [fn_conta_presidio](/dbzero/dbops/manual/fn_conta_presidio) da
proprietario e riporta **il numero**, mai le righe. Senza, «zero righe» e «non ho
potuto vedere» si scriverebbero uguale.

⚠️ Sta in `dbops` e non in `config` per una ragione precisa: il catalogo dei
presidi legge il proprio perimetro **dagli schemi che vi compaiono**, e una riga
`config.vw_…` porterebbe dentro tutte le viste di `config`.

---

### Verifica

`db/pgtap/dbops/test-vw-email-da-guardare.sql` — costruisce i sette casi dalla
porta di sistema (quindi anche su un database vuoto) e li interroga per nome: i
due che devono comparire, i tre che non devono, `dovuta_dal`, e il conteggio da
proprietario.

Origine: `docs/it/dev/work-in-progress/brief-db-quattro-processi-senza-presidio.md` §5 · §10.1.
