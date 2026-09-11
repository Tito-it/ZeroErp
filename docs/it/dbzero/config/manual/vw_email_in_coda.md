## 📘 Documentazione Concettuale – View `config.vw_email_in_coda`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[config.email_log](/dbzero/config/manual/email_log)
>
Approfondimenti viste:
>
[dbops.vw_email_da_guardare](/dbzero/dbops/manual/vw_email_da_guardare) — *il presidio che mette la soglia*

---
### 🎯 Scopo Principale
(latest review 11-09-2026)

Risponde a una domanda sola: **«questa email è ancora in coda?»** — cioè
`send_pending_emails` la deve ancora prendere in mano.

Sono in coda:

* le `PENDING`, sempre;
* le `RETRY` e le `FAILED` **con tentativi residui** (`tentativi < max_tentativi`)
  il cui prossimo tentativo è già dovuto, o non è mai stato fissato.

⚠️ I `FAILED` sono in coda **di proposito**: il cron li ripesca finché hanno
tentativi, ed è il recupero — se l'SMTP viene configurato entro quei tentativi,
la mail parte da sola. Il backend l'ha scoperto il 2026-09-11 fidandosi di un
commento che nominava «PENDING o RETRY» e ometteva i `FAILED`.

---

### ⭐ Perché esiste: la definizione va scritta una volta

La stessa regola serviva a **due** lettori: il cron (nella sua `SELECT`) e il
presidio [dbops.vw_email_da_guardare](/dbzero/dbops/manual/vw_email_da_guardare).
Scriverla in Python e in SQL vuol dire che divergono alla prima modifica — e il
presidio guarda una coda che il cron non svuota più, o viceversa.

⇒ La definizione vive qui, nel database, e la leggono in due. Il presidio la
proietta con la soglia; il cron la legge al posto della propria `SELECT` dal
giorno in cui la adotta (lavoro del backend, brief §10.7).

---

### `dovuta_dal` — da quando la coda la deve a qualcuno

| Stato | `dovuta_dal` |
| --- | --- |
| `PENDING` | `data_insert`: nessuno l'ha mai presa in mano |
| `RETRY` / `FAILED` | `COALESCE(prossimo_tentativo, data_insert)`: il backoff è legittimo, si misura da quando era **dovuta** |

⚠️ `config.email_log` non ha `data_update`: non c'è una colonna migliore.

---

### ⚠️ Non è un presidio

Nessuna soglia, nessuna riga in `dbops.presidi`. È una vista di dominio, e sta
in `config` proprio per questo: il catalogo dei presidi legge il proprio
perimetro dagli schemi che vi compaiono, e un presidio in `config` porterebbe
dentro tutte le viste di `config`.

`security_invoker`: chi la legge la legge **col proprio perimetro** — il cron
con l'identità tecnica del processo, una persona con la sua veste.

`SENT`, `SIMULATA` e i `FAILED` terminali **non** sono in coda.

---

### Verifica

`db/pgtap/dbops/test-vw-email-da-guardare.sql` — i test 3..7 provano questa
vista: il `RETRY` con backoff non è in coda, il `FAILED` terminale non è in coda,
la `PENDING` fresca sì, `SENT`/`SIMULATA` no, e `dovuta_dal` è il prossimo
tentativo dove c'è.

Origine: `docs/it/dev/work-in-progress/brief-db-quattro-processi-senza-presidio.md` §10.1 (D3).
