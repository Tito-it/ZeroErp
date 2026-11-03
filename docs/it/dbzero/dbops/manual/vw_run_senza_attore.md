## 📘 Documentazione Concettuale – View `dbops.vw_run_senza_attore`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[maintenance.job_run_log](/dbzero/maintenance/manual/job_run_log)
>
[dbops.processi](/dbzero/dbops/manual/processi)

---
### 🎯 Scopo Principale

Elenca i lavori automatici che, nell'**ultima corsa**, non hanno detto **quale
processo** fossero.

Il giornale dei run registra da sempre *che* qualcosa è girato. Da questo
cantiere registra anche *chi*: il codice del processo e, quando c'è, l'utente
tecnico con cui ha girato. Questa vista conta chi non lo dice ancora.

> ⚠️ **Deve restare vuota.**

---

### ⭐⭐ È scritta sull'ULTIMA corsa, e la prima versione era sbagliata

Vale la pena raccontarlo, perché è un errore che si rifà facilmente.

La prima versione contava **tutte** le righe storiche senza attore. Sembrava
più prudente, ed era inutile: quelle righe sono state scritte prima che la
colonna esistesse, **hanno l'attore vuoto per sempre**, e non c'è niente che si
possa fare per sanarle.

⇒ Una vista che non può arrivare a zero è **rumore**: si impara a ignorarla, e
allora smette di funzionare anche il giorno in cui avrebbe qualcosa da dire.

⭐ Sull'ultima corsa, invece, un job **sparisce dalla vista appena si
dichiara**. La regola generale, valida per qualunque presidio nuovo:

> Prima di scrivere una vista di controllo: *«che cosa la fa arrivare a zero?»*
> Se non c'è risposta, la vista è sbagliata.

---

### ⭐ I dodici job notturni si sono dichiarati SENZA toccare lo scheduler

La configurazione di pgAgent è una fase che in CI **non gira mai**: modificarla
significa cambiare qualcosa che nessun test esercita, e scoprire un errore di
notte.

⇒ Il codice del processo non viene passato come parametro: si **deriva dal nome
del job**, perché il codice del processo e il nome del job sono la stessa
stringa. Chi vuole essere esplicito passa comunque il parametro, che vince.

⚠️ Un nome di job che non corrisponde a nessun processo non può più restare
senza attore: il CHECK `chk_job_run_log_processo_dichiarato` su
`maintenance.job_run_log` respinge la riga nuova, e la corsa fallisce prima di
partire. Il vincolo è `NOT VALID` e non rivaluta il passato: la vista mostra
quindi il solo residuo storico, le righe scritte prima che il vincolo
esistesse.

---

### Esempio d'uso

```sql
-- Chi non si è ancora dichiarato, all'ultima corsa
SELECT * FROM dbops.vw_run_senza_attore;
```

---

### Note operative

* I **command** (i comandi lanciati a mano o da cron) non hanno un jobname da
  cui derivare: devono passare il codice del processo esplicitamente. È lavoro
  di backend, ed è la ragione principale per cui questa vista oggi non è
  ancora vuota.

Origine: `docs/it/dev/work-done/brief-db-processi-automatici-identita-e-perimetro.md` §3.

---

{% include-markdown "signature-core.md" %}
