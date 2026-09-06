# Brief — chi sveglia i processi, e perché di otto non lo sappiamo

> **Destinatari:** backend e team DB (`dev/db-tid`).
>
> **Che cos'è.** Le due code rimaste dal filo delle email, che con le email non
> c'entravano niente. Erano il §6-bis e l'ultimo punto del §10 di
> [brief-db-email-perimetro-e-invio-di-sistema.md](../work-done/brief-db-email-perimetro-e-invio-di-sistema.md)
> (ora in `work-done/`): un cantiere a sé, dentro un documento chiuso.
>
> **Stato:** 🔵 aperto, non urgente. ⛔ **Non blocca niente**, e proprio per
> questo va scritto: è il genere di cosa che resta scoperta finché qualcuno non
> la nomina.
>
> ⚠️ **Nessuno dei due punti è un guasto.** Sono due posti in cui un presidio
> **non guarda** — e un presidio cieco non si nota, per definizione.

---

## 1. Il panorama, misurato il 2026-09-06

`dbops.vw_processi_programmazione` confronta due fonti — chi dovrebbe svegliare
un processo e quando ha girato davvero:

| stato | n | |
| --- | --- | --- |
| `OK` | **12** | pgAgent lo sveglia e il giornale lo registra |
| `FUORI_PORTATA` | **8** | ⛔ la sveglia vive **fuori** dal database |
| `GIRA_E_NON_REGISTRA` | **2** | `apply_storicizza_weekly`, `chiusura_scadenze_daily` — i wrapper ci sono, si tolgono alla prossima corsa |

⭐ Il DB si ferma dove deve: chiama `FUORI_PORTATA` ciò che non può vedere,
invece di darlo per buono. **È tutto quello che può onestamente fare.**

---

## 2. 🔴 Gli otto scoperti, e sono quasi tutti nostri

| processo | classe | canale | chi lo sveglia |
| --- | --- | --- | --- |
| `run_fatturazione_batch` | DOMINIO | COMMAND | cron/systemd |
| `send_pending_emails` | DOMINIO | COMMAND | cron/systemd |
| `draina_coda_stampa` | DOMINIO | COMMAND | worker systemd |
| `draina_coda_lavori` | MANUTENZIONE | COMMAND | worker systemd |
| `sync_auth_user_active` | AMMINISTRAZIONE | COMMAND | cron/systemd |
| `listen_cambio_reparto` | AMMINISTRAZIONE | COMMAND | servizio in ascolto |
| `FATTURAZIONE_GIRO` | DOMINIO | CODA | lo accoda un operatore |
| `FATTURAZIONE_NUMERA` | DOMINIO | CODA | lo accoda un operatore |

⛔ **Sei su otto sono comandi del backend**, e la loro cadenza vive in unit
systemd e crontab — cioè **fuori dal repository**, invisibili ai test. È lo
stesso difetto che il cantiere dei processi automatici ha già nominato una volta
per `85_pgagent`, solo spostato di lato.

### Che cosa vuol dire davvero

> Se stanotte `send_pending_emails` non parte — unit disattivata, timer
> sbagliato, macchina spenta — **nessuna vista se ne accorge**. Il processo non
> ha fallito: non è mai partito. E l'unico segno sarebbe una coda che si allunga,
> che è di nuovo un guasto che si manifesta come **assenza**.

⚠️ I due `CODA` sono un caso diverso e sano: li sveglia una persona, quindi non
esiste una cadenza da dichiarare. Restano `FUORI_PORTATA` a ragione — ma varrebbe
la pena che il panorama li distinguesse dagli altri sei, o «otto scoperti» conta
insieme cose diverse.

---

## 3. Che cosa serve, e da chi

### 3.1 🔵 Backend — dire quando siamo programmati

Il database non ha modo di sapere la cadenza di un comando su systemd. ⇒ Deve
dirgliela chi ce l'ha: **noi**.

⚠️ **Non è "una colonna con un cron string"**, ed è il punto da decidere insieme:
una cadenza *dichiarata* che nessuno verifica è una promessa, e una promessa in
una tabella invecchia come tutte. Il valore sta nel **confronto** fra due fonti —
esattamente ciò che la vista già fa per pgAgent. ⇒ La domanda giusta non è «dove
scriviamo la cadenza» ma **«quale seconda fonte possiamo confrontare?»**.

🔵 Una strada possibile, da valutare: il comando stesso, al primo giro, dichiara
la propria cadenza attesa — e da lì in poi il confronto è fra *quando ha detto
che sarebbe tornato* e *quando è tornato davvero*. Non serve conoscere systemd:
serve che il processo prometta e che qualcuno controlli la promessa.

### 3.2 🔵 DB — la terza guardia che la misura non sa leggere

Il rubinetto degli accumulatori (`scripts/codici-errore-baseline.sh`) classifica
un punto d'errore leggendo la **riga di guardia**. In
`config.fn_chiudi_email_sistema` la terza è:

```sql
IF v_ambito <> 'SISTEMA' THEN
```

⇒ Nessuna regola la riconosce: risulta `IGNOTO`.

⛔ Ed è **il caso pericoloso** — quello che il vostro stesso commento dice avere
«parole sue» perché è l'unico momento in cui si nota che qualcuno sta usando la
porta di sistema per l'email di un'azienda. Il presidio che dovrebbe accorgersi
se quel codice si allarga, lì **non sta guardando**.

⚠️ Non è urgente e non è un guasto: è un presidio con un punto cieco, e i punti
ciechi si nominano quando si vedono.

---

## 4. Come si vede che è chiuso

* `dbops.vw_processi_programmazione` non ha più righe `FUORI_PORTATA` per i
  processi che il backend sveglia — o le ha, ma perché è stato **deciso** che
  quelli non si presidiano, e la vista lo dice;
* nessun punto d'errore di `fn_chiudi_email_sistema` resta `IGNOTO`.
