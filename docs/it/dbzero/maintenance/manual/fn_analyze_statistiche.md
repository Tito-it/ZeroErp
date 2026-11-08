## 📘 Documentazione Concettuale – Funzione `maintenance.fn_analyze_statistiche`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il processo `analyze_statistiche`, col suo posto nella convergenza di CI
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale dove resta la riga rossa di un'autoverifica fallita
>
> Approfondimento viste:
>
> * [maintenance.vw_statistiche_mancanti](/dbzero/maintenance/views/vw_statistiche_mancanti) — la prova che la funzione legge subito dopo `ANALYZE`
>
> Approfondimento funzioni:
>
> * [maintenance.proc_analyze_statistiche_job](/dbzero/maintenance/funzioni/proc_analyze_statistiche_job) — il wrapper del job, l'unico chiamante a regime
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — il giornale da cui passa il wrapper
>
> Guide:
>
> * [Liquibase, setup e workflow](/liquibase-setup-workflow) — §1, «Due diritti che si notano solo quando mancano»: chi possiede le tabelle che il job analizza

---

### 🎯 Scopo Principale

Aggiorna le statistiche del pianificatore delle query (`ANALYZE` del database, o delle sole
tabelle indicate) e poi verifica di esserci riuscito: se resta anche una tabella senza
statistiche, solleva invece di dire «fatto».

Prima di eseguire una query, PostgreSQL sceglie come farla (quale indice, in che ordine unire
le tabelle) **stimando** quante righe escono da ogni passaggio. Le stime vengono dalle
statistiche che scrive `ANALYZE`: quante righe ha una tabella, quali valori sono frequenti,
come sono distribuite le date. Sono una **fotografia dei dati**, e invecchiano con loro. Senza,
il pianificatore stima con valori fissi, e un piano può cambiare da solo a metà giornata.

L'autovacuum non basta: rianalizza una tabella solo quando ne cambiano 50 righe più il 10%,
quindi una tabella piccola o ferma non ci arriva mai, e le tabelle partizionate non le analizza
affatto. Questa funzione è il posto che lo fa.

---

### Tutto il database, oppure un elenco

Senza argomento la funzione analizza **tutto il database**: è il caso del job notturno e della
convergenza in CI. Con un elenco di tabelle analizza solo quelle, e l'autoverifica guarda solo
quelle: serve dopo un import, o a un pgTAP che deve provare la regola senza analizzare l'intero
database.

Il valore di ritorno è il numero di tabelle rimaste senza statistiche, ed è sempre zero: se non
lo fosse, la funzione avrebbe già sollevato.

---

### ⭐ L'autoverifica: perché la funzione può fallire

`ANALYZE` **non fallisce** su una tabella che non può analizzare: la salta con un avviso
(`WARNING`). Un job che saltasse metà delle tabelle scriverebbe «fatto» nel giornale.

Per questo, subito dopo `ANALYZE` e **nella stessa transazione** (così vede le statistiche
appena scritte), la funzione legge `maintenance.vw_statistiche_mancanti`. Se resta anche una
tabella, solleva `E_STATISTICHE_MANCANTI` nominando le prime dieci; nel contesto dell'errore ci
sono tutte, ciascuna col suo motivo, e il ruolo con cui l'analisi è girata.

| Motivo | Che cosa vuol dire | Che cosa fare |
| --- | --- | --- |
| `NON_ANALIZZABILE` | il ruolo che esegue non ha il diritto di analizzare la tabella | dare la **proprietà** della tabella al migratore `zeroerp_owner`, il ruolo con cui gira il job (è il lavoro della fase `pre` di `scripts/sql/provision_zeroerp.sql`), e rilanciare |
| `MAI_ANALIZZATA` | la tabella è ancora senza statistiche anche dopo `ANALYZE` | guardare la tabella: con il diritto, non dovrebbe succedere |

Il caso tipico di `NON_ANALIZZABILE` è una tabella creata da superuser e rimasta sua: quelle di
Liquibase (`databasechangelog`, `databasechangeloglock`) e `internal.project_metadata`, che il
primo passo dell'installazione crea come `postgres`. Il rimedio non è un diritto in più al
ruolo del job, ma il passaggio di proprietà: da proprietario `zeroerp_owner` non ha bisogno
d'altro. È provisioning, mai un changeSet.

⚠️ **La verifica sta qui e non in una vista guardata dal digest.** Subito dopo `ANALYZE`, una
tabella senza statistiche è un errore. In un'ora qualunque potrebbe essere solo una tabella
nata da una migrazione di poco prima: un controllo che dipenderebbe dal calendario.

---

### ⚠️ Una transazione sola

La funzione non fa `COMMIT` fra una tabella e l'altra: in CI la chiamano dentro la transazione
di un changeSet. `ANALYZE` tiene un lock `SHARE UPDATE EXCLUSIVE` su ogni tabella fino alla
fine: non blocca letture e scritture, blocca DDL, un altro `ANALYZE` e l'autovacuum. Una DDL
lanciata mentre il job gira aspetta che finisca.

---

### Il catalogo di sistema resta fuori

`ANALYZE` senza argomenti analizza anche `pg_catalog` se il ruolo è superuser o proprietario del
database, altrimenti lo salta. Il catalogo è **fuori** dall'autoverifica: i diritti sui cataloghi
di sistema non sono nostri da dare, e un errore che nessuno può correggere non serve.

---

### Chi la chiama

* Il job pgAgent `analyze_statistiche`, ogni notte alle 02:30, attraverso
  `maintenance.proc_analyze_statistiche_job`.
* In CI, la convergenza dei job strutturali (passata `ci_apply`), che chiama la stessa procedura
  per **ultima** (`ci_ordine` 900 in `dbops.processi`): si analizza dopo che le automazioni hanno
  creato le tabelle di storico, prima dei pgTAP.

---

### Codici errore

* `E_STATISTICHE_MANCANTI` — dopo `ANALYZE` restano tabelle senza statistiche; classe `TECNICO`,
  perché il rimedio è nel provisioning o in una tabella da guardare, non in un gesto
  dell'operatore.

---

### Test

`db/pgtap/maintenance/test-fn-analyze-statistiche-v1.sql` — costruisce tabelle temporanee mai
analizzate (piena, vuota, partizionata con una partizione) e prova che la funzione le porta a
statistiche presenti e ritorna zero; che una tabella che il ruolo non può analizzare fa
**sollevare** `E_STATISTICHE_MANCANTI` (caso saltato in modo dichiarato quando il test gira da
proprietario o superuser, dove non si costruisce); che gli oggetti delle estensioni sono fuori
dal perimetro; che il processo è a catalogo ed è l'ultimo della convergenza in CI.

---

### Note di migrazione

* 2026-10-14 — nasce, insieme alla vista e al job notturno
  (`brief-db-statistiche-tabelle-job-notturno`, D15). Il catalogo di sistema resta fuori
  dall'autoverifica per decisione di Tid (D-1).
* 2026-10-15 — la CI smette di dare `pg_maintain` al ruolo della migrazione: le tabelle create
  da superuser passano in proprietà a `zeroerp_owner` (`brief-db-ruoli-di-sistema`, fase 2).

---

{% include-markdown "signature-core.md" %}
