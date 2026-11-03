## 📘 Documentazione Concettuale – Funzione `dbops.fn_guardiano_digest`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
Approfondimenti viste:
>
[dbops.vw_processi_programmazione](/dbzero/dbops/manual/vw_processi_programmazione) — *dove si decide che il digest è `MUTO`*
>
Approfondimenti tabelle:
>
[dbops.processi](/dbzero/dbops/manual/processi) — *il contratto di liveness*
> [dbops.coda_lavori](/dbzero/dbops/manual/coda_lavori)
> [dbops.coda_lavori_tipi](/dbzero/dbops/manual/coda_lavori_tipi)
>
Approfondimenti funzioni:
>
[dbops.fn_accoda_lavoro](/dbzero/dbops/manual/fn_accoda_lavoro)
> [maintenance.fn_run_and_log](/dbzero/maintenance/manual/fn_run_and_log)

---
### 🎯 Scopo Principale

**Chi guarda il guardiano.** Il digest dei presidi segnala tutti gli altri; se
muore lui, l'unica cosa che lo direbbe è il battito — che sta *dentro* il
digest. Un digest morto non manda il messaggio che dice che è morto, e
l'assenza di una mail non si nota.

Questa funzione è il corpo del job pgAgent `guardiano_digest`: ogni ora legge lo
stato di `digest_presidi` dal panorama e, se è **`MUTO`**, accoda **un lavoro al
giorno** su `dbops.coda_lavori` che lo dica a una persona.

---

### ⭐ La guardia reciproca

pgAgent vive **dentro il database**, in un mondo che non muore insieme a systemd
del backend. È l'unico posto da cui la morte del digest si vede senza dipendere
dal digest.

E il guardiano è a catalogo come processo `PGAGENT`, e passa dal giornale
(`maintenance.proc_guardiano_digest_job` → `fn_run_and_log`): quindi il panorama
guarda **anche lui**. Il digest riporta il guardiano; il guardiano accoda per il
digest. Ognuno dei due vede la morte dell'altro.

---

### ⛔ Non manda una mail — ed è la forma giusta

pgAgent non spedisce, e **non conosce il destinatario**: è un fatto di deploy
(`.env.systemd`) e resta nel backend. Il guardiano **accoda un lavoro**
(`NOTIFICA_DIGEST_MUTO`); lo esegue `draina_coda_lavori` — il processo più vivo
del backend, ogni minuto, con badge in topbar — che spedisce col destinatario
**suo**. Nessun indirizzo entra nel database.

---

### Che cosa fa, in ordine

1. Legge `stato`, `tolleranza_minuti` e `ultimo_segno_di_vita` di
   `digest_presidi` da `vw_processi_programmazione`. ⭐ **Il criterio di `MUTO`
   non è qui**: sta accanto al `CASE` che lo produce, e se cambia lì questa
   funzione lo segue.
2. Se il digest **non è a catalogo** (spento o ritirato) → solleva
   `E_CONFIG_MANCANTE`. Un guardiano che non ha niente da guardare lo **dice**,
   non dorme.
3. Se lo stato **non è `MUTO`** → torna `DIGEST_<stato>` e non fa altro.
   ⚠️ Solo `MUTO`, non `MAI_PARTITO`: un digest mai installato lo dice già il
   panorama nel pannello, e un nagging orario su un'installazione nuova
   insegnerebbe a ignorare il guardiano.
4. Se **oggi** esiste già un lavoro con chiave `guardiano_digest:<giorno>`, in
   qualunque stato → `GIA_NOTIFICATO_OGGI`. ⭐ `fn_accoda_lavoro` dedupe solo
   fra `PENDING`/`IN_CORSO`: un lavoro già `FATTO` non fermerebbe il successivo
   un'ora dopo. Una mail al giorno è il ritmo del digest stesso.
5. Altrimenti accoda: `SISTEMA` senza scope, origine `CRON`, e nel payload
   `processo_codice`, `tolleranza_minuti`, `ultimo_segno_di_vita`, `muto_da` —
   ciò che serve all'handler per comporre la mail senza rileggere niente →
   `ACCODATO:<id>`.

---

### ⭐ Se il tipo di lavoro fosse spento, la corsa diventerebbe rossa

Il tipo `NOTIFICA_DIGEST_MUTO` è acceso e il backend ha il suo handler, quindi
l'avviso parte davvero. Questa funzione **non aggira** il binding: se il tipo
venisse spento, il giorno in cui il digest tace `fn_accoda_lavoro` solleverebbe
`E_JOB_TYPE_NON_ATTIVO` e la corsa sarebbe **rossa** in
`maintenance.vw_job_run_da_guardare`, cioè nel pannello. Un ritorno silenzioso
sarebbe un presidio che tace proprio quando serve.

---

### Verifica

`db/pgtap/dbops/test-fn-guardiano-digest.sql` — nove asserzioni: il guardiano è
a catalogo; digest vivo → `DIGEST_OK`; digest `MUTO` col tipo spento → solleva;
col tipo acceso → accoda, con la forma giusta; un'ora dopo →
`GIA_NOTIFICATO_OGGI` anche se il lavoro è già `FATTO`; digest tornato vivo →
`DIGEST_OK`; digest tolto dal catalogo → solleva.

Origine: `docs/it/dev/work-done/brief-db-quattro-processi-senza-presidio.md` §6 · §10.2 — decisione di Tid, 2026-09-11.
