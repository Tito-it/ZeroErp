## 📘 Documentazione Concettuale – Tabella `dbops.processi`

> **Ultimo aggiornamento**: 12 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi_bersagli](/dbzero/dbops/tabelle/processi_bersagli) — le tabelle che un processo di dominio scrive, col percorso all'emittente
> * [dbops.processi_identita](/dbzero/dbops/tabelle/processi_identita) — con quale utente tecnico gira un processo senza operatore
> * [dbops.processi_accensione](/dbzero/dbops/tabelle/processi_accensione) — la scelta a mano che scavalca il default di accensione
> * [dbops.installazione](/dbzero/dbops/tabelle/installazione) — l'ambiente da cui dipende il default
> * [dbops.cause_fallimento](/dbzero/dbops/tabelle/cause_fallimento) — il vocabolario di `causa_fallimento`
> * [dbops.coda_lavori_tipi](/dbzero/dbops/tabelle/coda_lavori_tipi) — i tipi di lavoro di coda, legati al processo per codice
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale delle corse, legato al processo per codice
>
> Approfondimento viste:
>
> * [dbops.vw_processi_programmazione](/dbzero/dbops/views/vw_processi_programmazione) — il panorama: sveglia, ultima corsa, stato
> * [dbops.vw_processi_dominio_senza_emittente](/dbzero/dbops/views/vw_processi_dominio_senza_emittente) — il dominio senza percorso verso l'emittente
> * [dbops.vw_processi_dominio_senza_difesa](/dbzero/dbops/views/vw_processi_dominio_senza_difesa) — il dominio col percorso ma senza policy o guard
> * [dbops.vw_processi_dominio_senza_identita](/dbzero/dbops/views/vw_processi_dominio_senza_identita) — il dominio che non sa dire chi agisce
> * [dbops.vw_processi_dominio_su_pgagent](/dbzero/dbops/views/vw_processi_dominio_su_pgagent) — il dominio che esegue dentro pgAgent
> * [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare) — legge `causa_fallimento` e `corsa_verdetto_completo`
>
> Approfondimento funzioni:
>
> * [dbops.fn_processo_acceso_su_valori](/dbzero/dbops/funzioni/fn_processo_acceso_su_valori) — la regola dell'accensione, sulle quattro colonne di questa tabella
> * [maintenance.fn_sveglia_accesa](/dbzero/maintenance/funzioni/fn_sveglia_accesa) — il cancello che le sveglie chiedono prima di partire
> * [script.fn_e_obsoleto](/dbzero/script/funzioni/fn_e_obsoleto) — la regola del ritiro: data raggiunta nel fuso aziendale
> * [script.fn_crea_utente_tecnico](/dbzero/script/funzioni/fn_crea_utente_tecnico) — crea l'utente tecnico di un processo di dominio
> * [dbops.fn_accoda_lavoro](/dbzero/dbops/funzioni/fn_accoda_lavoro) — la porta dei lavori di coda
>
> Guide:
>
> * [I lavori automatici: che natura hanno e per conto di chi girano](/guide/processi-automatici-classe-e-identita) — il racconto completo del registro
> * [Framework di Automazione DB](/guide/automazione-db) — quando girano le automazioni e i processi visti dall'interfaccia

---

### 🎯 Scopo Principale

Il catalogo di **tutto ciò che il sistema fa da solo**: i lavori notturni, i comandi delle
sveglie, i servizi sempre accesi, i lavori messi in coda. Una riga per processo, con la sua
classe, il suo canale e il contratto con cui il database lo sorveglia.

Risponde a una domanda che prima non aveva risposta scritta: **questo lavoro automatico sta
manutenendo il database, o sta lavorando i documenti di un'azienda?** Sono due mestieri con
regole diverse: un lavoro che ricostruisce gli indici non appartiene a nessuno; uno che emette
fatture appartiene **sempre** a un emittente, e chi lo fa girare deve avere il permesso di
toccare i documenti di quell'emittente.

È catalogo: si scrive dal seed, uguale su ogni installazione. Le metà che dipendono dalla
macchina (l'utente tecnico, la scelta a mano sulla sveglia) stanno in tabelle a parte.

---

### ⭐ La classe è una dichiarazione, non una deduzione

Si sarebbe potuto **dedurre** la natura di un processo guardando che cosa tocca («scrive su una
tabella protetta, quindi è di dominio»). ⛔ È la strada sbagliata: una tabella nuova nasce
**senza** protezioni, quindi il processo che la tocca risulterebbe innocuo proprio quando è più
pericoloso.

⇒ La classe la scrive chi registra il processo, e il database la **verifica in un verso solo**:
ciò che è dichiarato di dominio deve avere un perimetro, una difesa e un'identità (le viste di
presidio del «Vedi anche»). Una dichiarazione sbagliata in quel verso si vede; il verso opposto
(un processo di dominio dichiarato manutenzione) resta un errore umano che nessuna vista prende.

| Classe | Che cosa fa | Ha un emittente? |
| --- | --- | --- |
| `MANUTENZIONE` | tiene in ordine il database: indici, storicizzazione, pulizie, automazioni, presidi | no |
| `AMMINISTRAZIONE` | governa la macchina: utenze, permessi, sincronizzazioni | no |
| `DOMINIO` | lavora i documenti di un'azienda: fatture, stampe, email, scadenze | ⛔ sì, sempre |

⚠️ Il confine non è «tocca dati / non tocca dati»: la manutenzione tocca eccome i dati, li
storicizza e li archivia. La differenza è **di chi sono**: se una riga ha un padrone, il processo
è di dominio.

---

### I quattro canali: chi fa partire il lavoro

| Canale | Chi lo fa partire | Ha una sveglia? |
| --- | --- | --- |
| `PGAGENT` | lo scheduler del database | sì |
| `COMMAND` | un timer o un servizio dell'host che lancia un comando del backend | sì |
| `CODA_AUTOMATICA` | una **macchina** (un job pgAgent che accoda e non lavora); il lavoro lo esegue il drenatore della coda | sì |
| `CODA` | una **persona** che accoda un lavoro dall'applicazione | no |

⭐ **`CODA` cambia le regole dell'identità.** Un lavoro accodato da una persona porta con sé
l'identità di chi l'ha chiesto: non gli serve un utente tecnico, e dargliene uno cancellerebbe il
nome di chi ha premuto il pulsante. Per questo i presidi sull'identità escludono i `CODA`.

⚠️ **`CODA_AUTOMATICA` è la correzione di quell'assunzione.** Un lavoro che passa dalla coda ma
lo accoda una sveglia non ha un nome da prestare: vuole l'identità tecnica come i `PGAGENT` e i
`COMMAND`, e i presidi lo contano fra quelli.

⭐ Un `CODA` può essere anche di `MANUTENZIONE`: `avvio_manuale` è il gesto «Esegui ora» su una
sveglia, lo accoda una persona e non tocca i dati di nessuna azienda. Sotto di lui non si scrive
nessuna corsa: l'audit del gesto è la riga di [dbops.coda_lavori](/dbzero/dbops/tabelle/coda_lavori),
l'audit dell'esecuzione è la corsa che il comando lanciato scrive sotto il **proprio** processo.

⚠️ Per questo il suo lavoro è `SISTEMA`, non `OPERATORE`: il comando serve da sé tutte le aziende
del suo processo, e un lavoro `OPERATORE` apparterrebbe a una sola. Chi preme non è l'identità del
lavoro ma il suo **attore**, e viaggia nei dati del lavoro. La regola «un `CODA` ha l'identità di
chi accoda» vale per i `CODA` di `DOMINIO`, che toccano i dati di un'azienda.

---

### Il codice, il job e il ritiro

* `codice` è il nome stabile del processo, ed è l'attore di ogni corsa del giornale
  (`maintenance.job_run_log.processo_codice`) e di ogni tipo di lavoro di coda: due chiavi
  esterne lo referenziano **per codice**, quindi rinominare un processo è una migrazione, non una
  modifica di catalogo. Le procedure dei job registrano sotto il nome che passano alla porta del
  giornale, e quel nome deve essere un codice a catalogo.
* ⛔ Per questo il codice **non si cambia nel CSV**: la modifica della chiave è rifiutata su ogni
  database dove esistono righe figlie, mentre passa su uno ricostruito da zero, che non ne ha. Si
  aggiunge la riga col codice nuovo e si ritira la vecchia; la storia resta col codice con cui è
  stata scritta. Vale per ogni codice referenziato **per codice**: prima di toccarne uno in un CSV
  si cercano le chiavi esterne che entrano su quella colonna.
* ⚠️ Il legame col job di pgAgent **non è il nome**: lo dichiara `jobname_pgagent`, perché un job
  può chiamarsi diversamente dal processo che registra (`apply_fk_index_policy` è svegliato da
  `automations_apply_fk_indexes_policy`). Due processi non possono dichiarare lo stesso job, e un
  nome vuoto non vale come «nessun job».
* Un processo ritirato **non si cancella**: la sua storia nel giornale resta leggibile.
* ⭐ **Il ritiro ha una sede sola: `obsoleto_dal`.** Un processo è **vivo** finché la data è
  vuota o non è ancora arrivata, ed è **ritirato** dal giorno indicato (nel fuso aziendale). La
  regola è il building block [script.fn_e_obsoleto](/dbzero/script/funzioni/fn_e_obsoleto), e la
  leggono tutti: la sveglia, l'accensione e il suo guard, il panorama, i presidi, il roster,
  l'utente tecnico.
  * Un ritiro **programmato** (data futura) lascia il processo vivo fino a quel giorno: ha la
    sveglia, ammette la scelta a mano, compare nel panorama, nel roster e nei presidi.
  * Un processo ritirato non ha sveglia (`E_PROCESSO_SENZA_SVEGLIA`) ed esce dal panorama e dai
    presidi.
  * ⚠️ `attivo` dice solo se la riga è un riferimento valido, non se il processo è vivo: nessun
    lettore la guarda per questo. `attivo` falso pretende la data del ritiro
    (`chk_processi_ritiro_con_data`).
* `meta` raccoglie le estensioni in JSONB.

---

### ⭐ Il contratto di liveness dei `COMMAND`

Per i `PGAGENT` la programmazione si legge da pgAgent; per i `CODA` una cadenza non esiste. I
`COMMAND` li sveglia l'host, e il database non li vedeva: per loro il catalogo dichiara che cosa
aspettarsi.

| Colonna | Che cosa dice |
| --- | --- |
| `tolleranza_minuti` | «se sto bene, lascio un segno di vita almeno ogni N minuti». Vuota = la liveness non si presidia da qui |
| `segno_di_vita` | **dove** il database cerca quel segno: `GIORNALE` (l'ultima corsa nel giornale) o `SESSIONE` (una connessione viva il cui `application_name` è il codice del processo) |

* Il contratto vale solo per i `COMMAND`: per gli altri canali la tolleranza è vuota e il segno è
  `GIORNALE` (`chk_processi_contratto_solo_command`); la tolleranza, se c'è, è positiva.
* ⭐ `SESSIONE` è un fatto, non una dichiarazione: un listener tiene una connessione aperta, e se
  muore la connessione sparisce. Non ha tolleranza (`chk_processi_sessione_senza_tolleranza`):
  la domanda è «c'è **adesso**?».
* **Perché a catalogo e non nel deploy**: il lettore che serve vive nel database (il guardiano del
  digest è un job pgAgent e legge solo qui), e una sede sola resta una sede sola.
* ⚠️ Cadenza e tolleranza non sono indipendenti: la tolleranza è il **contratto** del processo,
  uguale ovunque; la cadenza del timer è **come l'host lo onora**, e sta nel deploy. Un timer più
  lento della tolleranza viola il contratto: quella verifica è del backend.

Lo legge [vw_processi_programmazione](/dbzero/dbops/views/vw_processi_programmazione), che per un
`COMMAND` con contratto dice `OK`, `MUTO` o `MAI_PARTITO`, e per uno senza dice `FUORI_PORTATA`.

---

### ⭐ La convergenza in CI: i job pgAgent girano anche dove pgAgent non c'è

In CI i job pgAgent non esistono, e quello che **solo** un job fa non si vedrebbe mai. Per questo
ogni processo con un job (`jobname_pgagent` valorizzato) dichiara **una** di due cose, e chi non
ha un job non ne dichiara nessuna (`chk_processi_convergenza_ci`):

| Dichiarazione | Colonne | Che cosa succede |
| --- | --- | --- |
| è **strutturale** | `ci_ordine` e `ci_procedura` | la convergenza del rilascio chiama la procedura in ordine di `ci_ordine` e pretende nel giornale una corsa riuscita, non saltata |
| resta **fuori** | `ci_esclusione` | il perché, in chiaro: un job operativo su dati e orologio, o con un giro suo altrove |

* `ci_procedura` è scritta per esteso con la firma, non dedotta dal codice: un job può chiamare
  una procedura con un altro nome.
* L'ordine conta: la tabella di storico prima del suo trigger, l'insieme della storicizzazione
  prima del default che lo consuma, l'attivo prima del lock. `ci_ordine` è unico.
* ⚠️ La procedura deve registrare nel giornale **sotto il codice del processo**: è da lì che la
  convergenza riconosce che è andata.

---

### ⭐ Acceso o spento: il default per ambiente

Ogni processo **con una sveglia** (canali `PGAGENT`, `COMMAND`, `CODA_AUTOMATICA`) dichiara
quattro cose, **anche da ritirato**; i `CODA` le lasciano tutte vuote (`chk_processi_accensione`).
⚠️ Il CHECK guarda solo il canale: non sa se la data del ritiro è arrivata, e un processo a ritiro
programmato gira fino a quel giorno. Che un ritirato non abbia sveglia lo dice la regola
dell'accensione, non il CHECK.

| Colonna | Che cosa dice |
| --- | --- |
| `acceso_in_sviluppo` | se la sveglia è accesa di default in un'installazione di sviluppo |
| `acceso_in_produzione` | se è accesa di default in un'installazione di produzione |
| `spegnibile` | se la sveglia si può spegnere a mano |
| `accendibile_in_produzione` | se in produzione la sveglia si può accendere a mano |

⭐ **Non spegnibile** è un processo che, spento, romperebbe la sicurezza o la correttezza dei dati
senza che nessuno se ne accorga: permessi tolti che restano validi (`listen_permessi`), utenti
scaduti che restano attivi (`sync_auth_user_expired_daily`), stati per scadenza che restano aperti
(`chiusura_scadenze_daily`), la coda che si ferma (`draina_coda_lavori`), i guasti che nessuno
guarda più (`digest_presidi`, `guardiano_digest`), le email che non partono (`send_pending_emails`).
Il CHECK lo vuole acceso di default in tutti e due gli ambienti; la scelta a mano non lo spegne, e
il suo stato non dipende dall'ambiente.

⭐ **Non accendibile in produzione** è il gemello: un processo che su una base vera non deve
girare mai, perché scrive dati di prova (per esempio `smoke_notturno`). Il CHECK lo vuole spento
di default in produzione; la scelta a mano non lo accende lì, e una riga accesa già presente si
ignora. In sviluppo non conta.

Chi risponde, una regola scritta una volta sola:

| Domanda | Chi risponde |
| --- | --- |
| la regola | [dbops.fn_processo_acceso_su_valori](/dbzero/dbops/funzioni/fn_processo_acceso_su_valori), pura sui valori |
| la scelta a mano è ammessa dal divieto di produzione? | [dbops.fn_accensione_a_mano_ammessa_su_valori](/dbzero/dbops/funzioni/fn_accensione_a_mano_ammessa_su_valori) |
| lo stato su questa installazione, per chi descrive | [dbops.fn_processo_acceso_dichiarato](/dbzero/dbops/funzioni/fn_processo_acceso_dichiarato), che non solleva |
| la sveglia deve partire? | [maintenance.fn_sveglia_accesa](/dbzero/maintenance/funzioni/fn_sveglia_accesa), che risponde o solleva |

⚠️ **Spegnere ferma la sveglia, non l'aggiornamento**: la convergenza del rilascio chiama le
procedure strutturali sempre, anche su un processo spento.

---

### ⭐ A chi tocca un fallimento: `causa_fallimento`

Dice a chi tocca un fallimento del processo **quando l'ambiente è sano**: `PROGRAMMA` (lo
sviluppo), `AMBIENTE` (chi gestisce il server) o `CONFIGURAZIONE` (l'amministratore). È
obbligatoria su **ogni** processo, anche `CODA` e ritirati: ogni processo può lasciare un
fallimento nel giornale.

È l'**ultima** parola, non la prima: [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare)
guarda prima i segni dell'ambiente (una corsa morta senza chiudersi, un codice di guasto del
database) e il codice d'errore, se dichiara la sua causa. Un disco pieno resta un guasto del
server anche per un processo che dichiara `PROGRAMMA`.

---

### ⭐ Ogni corsa è un verdetto completo? `corsa_verdetto_completo`

Dice se ogni corsa del processo **ricontrolla tutto il suo perimetro**, così che un verde chiude
i rossi che lo precedono. Nasce falsa: chi non dichiara resta com'era.

**Il criterio**: dopo un verde, resta qualcosa che il rosso aveva lasciato e il verde non ha
ricontrollato? Se sì, è falsa.

| Vera | Falsa |
| --- | --- |
| lo smoke notturno, le automazioni e la policy degli indici, il digest e il suo guardiano, le statistiche, il riallineamento degli utenti scaduti, l'accodamento delle chiusure per scadenza | le code (un lavoro fallito resta fallito, la corsa dopo ne prende altri), l'invio delle email, la fatturazione batch; i `CODA` e il listener, che non scrivono corse giudicate |

Per un verdetto completo il presidio dei job accende «intermittente» solo se il lavoro è
**ricaduto** dopo essere tornato verde. ⚠️ Vale per ogni corsia del processo (ogni `jobname`
sotto lo stesso codice): una corsia nuova che lavora una parte vuole un processo suo, o la colonna
falsa.

---

### Come si registra un processo nuovo

1. Una riga nel seed dei processi: è catalogo, si cambia dal CSV, mai con un aggiornamento
   diretto (il ruolo applicativo ha sola lettura). La riga dichiara:
   * la convergenza in CI, se ha un job pgAgent;
   * `corsa_verdetto_completo`, col criterio sopra;
   * le quattro colonne dell'accensione, se ha una sveglia; e se il job è pgAgent, il suo passo
     nasce già avvolto nel cancello della sveglia.
2. Se è di **dominio**, una riga in [processi_bersagli](/dbzero/dbops/tabelle/processi_bersagli)
   per ogni tabella che scrive, con il percorso che porta all'emittente.
3. Se è di dominio **e non lo lancia una persona** (canali `PGAGENT`, `COMMAND`,
   `CODA_AUTOMATICA`), un utente tecnico per ogni emittente da servire, con
   [fn_crea_utente_tecnico](/dbzero/script/funzioni/fn_crea_utente_tecnico).

⇒ Se un passo manca lo dicono i presidi, che devono restare vuoti:
`vw_processi_dominio_senza_emittente`, `vw_processi_dominio_senza_difesa`,
`vw_processi_dominio_senza_identita`, `vw_processi_dominio_su_pgagent` e
[vw_emittenti_non_serviti](/dbzero/dbops/views/vw_emittenti_non_serviti).

---

### Test

* `db/pgtap/dbops/test-processi-registro.sql` — i CHECK di classe e canale, il codice unico, ogni
  canale del CHECK usato, i presidi di livello 1 e 2 su casi costruiti, un solo processo vivo per
  lo stesso lavoro.
* `db/pgtap/dbops/test-processi-coda-automatica.sql` — il canale `CODA_AUTOMATICA`: ammesso dal
  CHECK, visto dai presidi d'identità, servito dalla fabbrica degli utenti tecnici.
* `db/pgtap/dbops/test-processi-convergenza-ci.sql` — la dichiarazione di convergenza per ogni
  processo con un job.
* `db/pgtap/dbops/test-processi-jobname-wrapper.sql` — ogni nome con cui una procedura di job
  registra nel giornale è un codice a catalogo.
* `db/pgtap/dbops/test-processi-accensione-v1.sql` — le quattro colonne dell'accensione, il CHECK
  convalidato, i non spegnibili e i non accendibili a catalogo.
* `db/pgtap/dbops/test-vw-processi-programmazione.sql` — il contratto di liveness letto dal
  panorama.
* `db/pgtap/dbops/test-processo-vivo-v1.sql` — il ritiro con la data: `attivo` falso senza data
  rifiutato, un ritiro programmato vivo per la sveglia, la scelta a mano, il panorama e i presidi,
  un ritiro raggiunto senza sveglia e fuori; i lettori chiamano `script.fn_e_obsoleto`.

---

### Note di migrazione

* 2026-09-04 — nasce col registro dei processi automatici (`brief-db-processi-automatici-identita-e-perimetro`):
  classe dichiarata, bersagli, identità.
* 2026-09-05 — nasce il canale `CODA_AUTOMATICA`; `chiusura_scadenze_daily` lascia `PGAGENT`
  (`brief-db-processi-automatici-residui-be`).
* 2026-09-06 — nasce `jobname_pgagent`: prima il legame col job si deduceva dal nome.
* 2026-09-11 — nasce il contratto di liveness dei `COMMAND` (`brief-db-quattro-processi-senza-presidio`):
  la tolleranza esce dal file delle sveglie del deploy. Prima ogni `COMMAND` era `FUORI_PORTATA`.
* 2026-09-14 — nasce `avvio_manuale` (`brief-db-avvio-manuale-di-un-processo`).
* 2026-09-26 — nasce la convergenza in CI (`brief-db-job-notturni-in-ci`).
* 2026-10-04 — `listen_cambio_reparto` è ritirato; lo sostituisce `listen_permessi`, che ascolta
  anche il catalogo dei permessi. Le corse storiche restano nel giornale col codice vecchio.
* 2026-10-16 — nascono il default di accensione per ambiente e `spegnibile`
  (`brief-db-processi-accensione-per-ambiente`), e `causa_fallimento`. Prima il catalogo non sapeva
  quali sveglie fossero accese su un'installazione: lo sapeva solo il deploy.
* 2026-10-18 — nascono `accendibile_in_produzione`, che porta nel database un consenso che stava
  solo nel `.env` di una macchina, e `corsa_verdetto_completo`.
* 2026-11-07 — la regola fra canale `CODA` e identità si restringe ai processi di `DOMINIO`: il
  lavoro di `avvio_manuale` è `SISTEMA`, con chi preme come attore (`brief-db-revisione-dbops`,
  giro 5). Revoca in parte la decisione del 2026-09-14 (`brief-db-avvio-manuale-di-un-processo`).
* 2026-11-08 — perde `tx_id`, `data_update`, `user_update` e i due trigger montati a mano che li
  scrivevano: la tabella la scrive solo la migrazione, dal CSV, e le colonne direbbero sempre «il
  migratore» (regola dello scrittore, `automazione-db.md` §1.1; `brief-db-revisione-dbops`, giro 7-bis).
* 2026-11-08 — il ritiro passa alla sola `obsoleto_dal`, letta con `script.fn_e_obsoleto`. Prima panorama, presidi e roster leggevano `attivo` e la
  data scritta, l'accensione solo la data scritta: un ritiro programmato spariva dai presidi il
  giorno in cui si scriveva. Nasce `chk_processi_ritiro_con_data`; `chk_processi_accensione` smette
  di esentare i ritirati.

---

{% include-markdown "signature-core.md" %}
