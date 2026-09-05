# Brief DB — processi automatici: registro, identità e perimetro

> **Destinatario:** team DB (`dev/db-tid`).
>
> **Origine.** Le decisioni sono già prese e motivate in
> [analisi-db-be-processi-automatici-identita-e-perimetro.md](analisi-db-be-processi-automatici-identita-e-perimetro.md)
> (D-1, D-2, D-4, D-5, D-6, D-8, D-9, D-10, tutte del 2026-09-04).
> ⛔ **Questo brief non le rispiega e non le riapre**: le traduce in DDL, funzioni,
> seed, viste di presidio e test, nell'ordine in cui vanno scritte.
>
> **Stato:** ✅ **LAVORO DB COMPLETO — 2026-09-04.** Tutte e sette le fasi
> applicate su dbdev (0, 1, 2, 3a, 3b, 4, 5, 6).
>
> * gli **utenti tecnici** esistono col loro emittente — `vw_emittenti_non_serviti`
>   e `vw_processi_dominio_senza_identita` sono vuote;
> * la **coda** rifiuta un lavoro di dominio senza operatore, e ogni bersaglio
>   della chiusura scadenze dichiara la propria classe;
> * la **porta è chiusa**: il ramo «nessun utente in sessione → passa» non c'è
>   più, e il criterio è `row_security_active()`. ⛔ Non era bloccata dal ritiro
>   di `BYPASSRLS`, come si era creduto — §12.5;
> * baseline pgTAP su **491 file: nessuna regressione**;
> * ✅ **documentazione allineata** — §12.10.
> * 📨 **il BE ha risposto** con cinque richieste — §12.9.
>
> 🔴 **Correzione 2026-09-05 — il migrate della CI si fermava sulla fase 4.**
> Il mirror di `dbops.coda_lavori_tipi` è ancorato a **luglio** e la colonna
> `processo_codice` gli era stata aggiunta lì: su un database ricostruito da zero
> scriveva la FK **prima** che `20260904-13` seminasse `dbops.processi`. Corretto
> con un mirror ri-ancorato — §11.1, ultima trappola. Il lavoro sul DB resta
> completo: era un difetto di **posizione nella timeline**, non di modello.
>
> ⭐ **Tutto ciò che resta aperto — nostro e altrui — sta nel §12.**
> Avanzamento fase per fase nel §10.
>
> ⚠️ **Perimetro:** solo `db/`. ⛔ Il backend (worker, dispatch, command che accodano)
> ha il suo brief: qui si dichiara **cosa il DB gli offre** e **cosa smette di offrirgli**.

---

## 0. Che cosa si costruisce, in due parole

Sei pezzi, e i primi due non toccano niente di vivo:

1. **Un registro dei processi** — l'elenco dei programmi automatici che esistono, con
   scritto di che tipo sono e quali tabelle toccano. Oggi non c'è: il nome del
   programma è testo libero;
2. **il nome di chi ha girato** sul giornale dei run — oggi si sa *quale* programma, non
   *per conto di chi*;
3. **gli utenti tecnici**, uno per programma, per i programmi che fanno il lavoro delle
   aziende;
4. **la coda** impara a rifiutare un lavoro di dominio senza operatore;
5. **la chiusura scadenze** dichiara la classe di ogni bersaglio;
6. **il controllo in scrittura** smette di spegnersi quando non c'è un utente — ed è
   l'ultimo, perché prima fermerebbe tutto.

Più le **viste di presidio**, che devono restare vuote, e i **test**.

---

## 1. Che cosa NON è di questo brief

* il **worker** e il dispatch della coda, i command che accodano N lavori, la
  riscrittura di `_guard_canale_sistema`: sono backend;
* il **ritiro del ruolo `zeroerp_batch_fatturazione`**: vive nel **provisioning**
  (`scripts/sql/provision_db_role_batch_fatturazione.sql`), non in un changeSet — i
  privilegi dei ruoli batch non stanno mai in Liquibase;
* la **colonna emittente su `config.email_outbox`** e le **policy mancanti su
  `vendite.listini*`**: sono debiti che questo brief **fa emergere** (§8, livello 2) e
  non progetta — ⇒ registrati in **§12.3** con la vista che li verifica;
* **magazzino e acquisti**, in ristrutturazione.

---

## 2. Fase 1 — Il registro dei processi (D-0)

⭐ È il passo 0: senza, nessuna vista del §8 è costruibile e la classe resta prosa.

### 2.1 Tre tabelle, e la separazione catalogo/macchina è obbligatoria

Il registro descrive **due cose di natura diversa**, e mescolarle rende il seed non
ricaricabile su un database ricostruito da zero:

| Tabella | Che cosa dichiara | Natura |
| --- | --- | --- |
| `dbops.processi` | quali processi esistono, di che classe, su quale canale | 📚 **catalogo** |
| `dbops.processi_bersagli` | quali tabelle ogni processo **scrive**, e come raggiungono l'emittente | 📚 **catalogo** |
| `dbops.processi_identita` | quale utente tecnico serve un processo | 🔧 **macchina** (FK verso `django.auth_user`) |

⇒ Il seed di `processi_identita` va marcato `context: dati_macchina`.
⚠️ E il filtro va reso esplicito dove si applica: `--contexts="!provision and !dati_macchina"`
— `"!provision"` da solo **non** lo esclude.

### 2.2 `dbops.processi`

| Colonna | Tipo | Note |
| --- | --- | --- |
| `id` | `int GENERATED … AS IDENTITY` | tabella tecnica |
| `codice` | `text NOT NULL` | ⭐ **è l'attore** (D-8). `UNIQUE` — ci si aggancia la FK del §3 |
| `descrizione` | `text NOT NULL` | |
| `classe` | `text NOT NULL` | `CHECK IN ('MANUTENZIONE','AMMINISTRAZIONE','DOMINIO')` |
| `canale` | `text NOT NULL` | `CHECK IN ('PGAGENT','COMMAND','CODA')` |
| `attivo` | `boolean NOT NULL DEFAULT true` | |
| `obsoleto_dal` | `date NULL` | deprecabilità di catalogo: si ritira per data, non si cancella |
| `meta` | `jsonb NOT NULL DEFAULT '{}'` | |
| audit + `tx_id` | | `data_insert`/`user_insert`/`data_update`/`user_update` |

Vincoli: `pk_processi`, `uq_processi_codice`, `chk_processi_classe`, `chk_processi_canale`.

⚠️ **La classe di un processo guidato da configurazione è la più STRETTA fra quelle dei
suoi bersagli** (D-10). `chiusura_scadenze` ha oggi due bersagli entrambi di dominio ⇒
è `DOMINIO`. La classe **per bersaglio** vive sulla riga di configurazione (§6), non
qui: qui c'è ciò che il processo può toccare **al massimo**.

### 2.3 `dbops.processi_bersagli`

Senza questa tabella il presidio *«dominio senza emittente»* non esiste: le scritture di
un processo non stanno in nessun catalogo di PostgreSQL.

| Colonna | Tipo | Note |
| --- | --- | --- |
| `processo_id` | `int NOT NULL` | FK → `dbops.processi(id)` |
| `schema_tabella`, `nome_tabella` | `text NOT NULL` | il bersaglio scritto |
| `emittente_via` | `text NULL` | ⭐ **come la riga raggiunge l'emittente** — stesso vocabolario del guard esistente: `fiscale` \| `soggetto_ruolo` \| `fattura` \| `contabile`, più `padre` |
| `emittente_colonna` | `text NULL` | la colonna che porta il riferimento (per `padre`: la FK verso il padre) |
| `note` | `text NULL` | |

Vincoli: `uq_processi_bersagli_target (processo_id, schema_tabella, nome_tabella)`,
`chk_processi_bersagli_via`.

⚠️ **Limite dichiarato, e va scritto nel commento della tabella:** è un elenco
**dichiarato**. Prova che qualcuno ha detto dove il processo scrive, non che il processo
scriva solo lì. Un processo che comincia a scrivere altrove e non aggiorna la riga
sfugge. È lo stesso limite di `dbops.vw_liste_multi_emittente_non_certificate`, ed è il
prezzo di un presidio che esiste invece di uno perfetto che non esiste.

### 2.4 `dbops.processi_identita` (dati di macchina)

| Colonna | Tipo | Note |
| --- | --- | --- |
| `processo_id` | `int NOT NULL` | FK → `dbops.processi(id)`, **UNIQUE**: un processo, un utente |
| `auth_user_id` | `integer NOT NULL` | l'utente tecnico (§4) |
| `attivo` | `boolean NOT NULL DEFAULT true` | |

⛔ Nessuna FK verso `django.auth_user` in `%TYPE`: le funzioni che citano `django.*`
restano `plpgsql` e senza `%TYPE` (il tipo si scrive esteso).

### 2.5 Il seed di catalogo

`80_data`, in CSV con mirror `loadUpdateData` — mai `INSERT` sparsi.

| Canale | Quanti | Classe |
| --- | --- | --- |
| `PGAGENT` | 10 `automations_*` / `apply_storicizza` / `sync_storico_set_storicizza` | `MANUTENZIONE` |
| `PGAGENT` | `sync_auth_user_expired_daily` | `AMMINISTRAZIONE` |
| `PGAGENT` | `chiusura_scadenze_daily` | `DOMINIO` |
| `COMMAND` | `run_fatturazione_batch`, `draina_coda_stampa`, `send_pending_emails` | `DOMINIO` |
| `COMMAND` | `sync_auth_user_active`, `listen_cambio_reparto` | `AMMINISTRAZIONE` |
| `COMMAND` | `draina_coda_lavori` | `MANUTENZIONE` (è il worker, non il lavoro) |
| `CODA` | `FATTURAZIONE_GIRO`, `FATTURAZIONE_NUMERA` | `DOMINIO` |

⚠️ `chiusura_scadenze_daily` entra come `DOMINIO` **prima** di essere sistemato: il
registro descrive ciò che il processo **è**, non ciò che è già stato messo a posto. La
vista del §8 lo segnalerà, ed è corretto che lo faccia.

⚠️ **`loadUpdateData` non cancella.** Togliere una riga dal CSV — un processo ritirato,
un bersaglio che non si scrive più — **non** la toglie dal database. Per questo
`dbops.processi` ha `obsoleto_dal`: un processo si ritira **per data**. Per un
**bersaglio** che sparisce davvero serve un `DELETE` SQL forward-only, ed è l'unica
eccezione legittima alla regola «si cambia dal CSV».

⚠️ **E i privilegi non arrivano da soli.** Le `ALTER DEFAULT PRIVILEGES` del
provisioning valgono per il ruolo che le ha impostate: fuori dalla CI il ruolo
applicativo **non riceve** privilegi sulle tabelle nuove. Serve un `GRANT` mirato in
`90_end`, o `zeroerp_app` non vede nemmeno il registro — e le viste di presidio
sarebbero inutilizzabili proprio da chi deve leggerle. ⭐ Il difetto è **invisibile da
`information_schema`**, che è filtrata per privilegi: le tabelle risultano
*inesistenti*, non *inaccessibili*.

---

## 3. Fase 2 — L'attore sul giornale dei run (D-3)

Indipendente da tutto il resto, e utile da subito anche ai dieci job che resteranno di
manutenzione.

### 3.1 `maintenance.job_run_log`: due colonne

| Colonna | Tipo | Note |
| --- | --- | --- |
| `processo_codice` | `text NULL` | ⭐ l'attore (D-8). **FK → `dbops.processi(codice)`** |
| `auth_user_id` | `integer NULL` | ✅ **risposta al residuo di D-3**: l'utente tecnico quando c'è. ⛔ Non è l'operatore per-item della coda, che sta già in `coda_lavori.scope` |

⭐ **La FK fa da cancello dove una vista farebbe da referto**: un codice non registrato
**non si scrive**, invece di comparire in un elenco il giorno dopo. Con la colonna
nullable, la transizione non si ferma.

⚠️ **`NULL` all'inizio, non `NOT NULL`.** Il dato va reso obbligatorio **dove si può
fornire**: finché il backend e i job pgAgent non passano il parametro, un `NOT NULL`
fermerebbe tutti e dodici i job al primo giro. Il `NOT NULL` arriva quando la vista
*run senza attore* è vuota, e sarà un changeSet suo.

### 3.2 Le funzioni sono DUE

⛔ L'errore facile è toccarne una sola. Ogni job pgAgent passa da `fn_run_and_log`.

| Funzione | Cosa cambia |
| --- | --- |
| `script.fn_job_run_start` | `+ p_processo_codice`, `+ p_auth_user_id`, entrambi `DEFAULT NULL` |
| `maintenance.fn_run_and_log` | idem, e li scrive nella propria `INSERT` |

⛔ **`%TYPE` è obbligatorio, e nei TRE punti** — firma, `DECLARE` e `RETURNS TABLE`:

```sql
CREATE OR REPLACE FUNCTION script.fn_job_run_start(
    …,
    p_processo_codice maintenance.job_run_log.processo_codice%TYPE DEFAULT NULL,
    p_auth_user_id    maintenance.job_run_log.auth_user_id%TYPE    DEFAULT NULL)
 RETURNS TABLE(id       maintenance.job_run_log.id%TYPE,
               run_uuid maintenance.job_run_log.run_uuid%TYPE,
               acquired boolean)
```

⚠️ Tre trappole, tutte su questa funzione:

* **`CREATE OR REPLACE` non cambia il `RETURNS TABLE`** ⇒ se si tocca il ritorno serve
  un `DROP` prima, nello stesso changeSet;
* **aggiungere parametri crea un OVERLOAD**, non una sostituzione: la vecchia firma va
  `DROP`ata esplicitamente, o restano due funzioni e il backend chiama a caso;
* ⚠️ il `%TYPE` in firma **è una fotografia**: si scioglie al momento della creazione, e
  la doc auto-gen mostrerà i tipi risolti. È corretto — ma non ci si può fare
  affidamento per «seguire» un cambio di tipo della colonna.

⚠️ **`fn_job_run_start` ritorna `TABLE(...)`**: un `CREATE OR REPLACE` non cambia il tipo
di ritorno. Qui il ritorno non cambia, ma **aggiungere parametri crea un overload**: il
vecchio va `DROP`ato esplicitamente nello stesso changeSet, o restano due firme e il
backend chiama a caso.

### 3.3 ⭐ La derivazione dal jobname — i 12 job pgAgent senza toccare `85_pgagent`

I job pgAgent non chiamano `fn_run_and_log` direttamente: passano da wrapper
`maintenance.proc_*_job` che invocano `p_jobname := 'automations_tx_id'` — **esattamente
il codice seedato** in `dbops.processi`.

⇒ Se il chiamante non passa il codice e il jobname **corrisponde** a un processo
registrato, `fn_run_and_log` usa quello. I dodici job diventano conformi **senza una
riga** in `85_pgagent`, che è la fase mai eseguita in CI (`MARK_RAN`) e quindi la più
scomoda da collaudare.

⚠️ **È lecito perché qui la derivazione è COMPLETA.** Nel dominio di quella funzione —
i job pgAgent — il jobname *è* l'identità del processo. Dove non lo è, non si deriva:
`fn_job_run_start` riceve nomi come `run_fatturazione_batch:immediata`, con la corsia
attaccata, e lì il codice lo passa il chiamante. ⛔ *Una derivazione incompleta è peggio
di nessuna derivazione*: copre una parte dei casi e tace sull'altra.

⇒ Un jobname che non corrisponde a nessun processo **resta `NULL`** e compare in
`vw_run_senza_attore`. Niente è mascherato — ed è coperto da un test suo.

### 3.4 ⛔ L'advisory lock NON si allinea — correzione

Questo brief diceva *«`fn_run_and_log` usa la forma a un argomento contro la convenzione
a due: si allinea qui, mentre la si tocca»* (difetto C dell'analisi). **Sbagliato, e il
ragionamento era superficiale — coerenza di forma senza guardare la semantica.**

Le due forme occupano **spazi di lock distinti** in PostgreSQL, e questo tiene
**indipendenti** i due canali: un job pgAgent e un comando headless non si bloccano a
vicenda, per costruzione. Allineare non sarebbe coerenza: **accoppierebbe** due canali
oggi indipendenti, e in più costringerebbe a stringere il `bigint` di `p_lock_key` in un
`int`. ⇒ Nessun vantaggio, due rischi. **Resta com'è**, e il difetto C si chiude come
*«non si fa, e questo è il motivo»*.

---

## 4. Fase 3 — Gli utenti tecnici (D-6)

> **3a ✅ applicata** — tipo ruolo `PROC_AUTO`, flag `tecnica`, le due viste di
> presidio, GRANT, pgTAP. **3b 🔵 prossima** — la fabbrica e i 4 utenti veri.

### 4.0 ⛔ Tre vincoli scoperti applicando la 3a, che cambiano il disegno

* ⛔ **Un solo soggetto «sistema» per N processi è IMPOSSIBILE.**
  `uq_soggetto_ruolo (soggetto_id, tipo_ruolo_id)` ammette una riga sola per coppia, e
  `uq_identita_digitali_sr_ruolo_attivo` una sola identità `OPERATORE` per
  `soggetto_ruolo`. ⇒ **un soggetto per processo**. D-6b regge — «non l'azienda
  emittente» — ma nella forma che la struttura impone.
* ⛔ **La matrice delle nature resta VUOTA, ed è una decisione.** Volevo dichiarare `PG`
  per impedire strutturalmente che il ruolo-processo finisse su una persona; ma le
  nature `PG` disponibili (`SC`, `SP`) impongono **partita IVA e codice fiscale**, che
  un processo non ha. Vincolarla costringerebbe a inventare una categoria anagrafica per
  una cosa che anagrafica non è. ⭐ L'assenza è **fissata da un test** (§9), altrimenti
  fra sei mesi sembra un buco da tappare.
* 🔴 **Un utente ha UN SOLO emittente**, e questo ha riscritto D-6.
  `config.user_emittenti_fiscali` è `UNIQUE(auth_user_id)` — non è una whitelist, è
  1-a-1 (changeSet 20260408-11), e *«solo il super admin è multi-emittente»*.
  ⇒ Un utente tecnico **per processo × emittente**: oggi con un emittente sono
  quattro, con tre ne sarebbero dodici. ⛔ Non è l'`automatico_<emittente>` scartato
  nell'analisi §6: quello moltiplicava le identità di una **persona**; questo è un
  badge per **posto di lavoro**, e nel modello il posto di lavoro è l'emittente.
* ⛔ **Il profilo non si punta al reparto, e non serve.** Un profilo `REPARTO`
  raggiunge una persona via `anagrafiche.risorse_umane` — il rapporto di lavoro. E i
  profili valgono per liste, dashboard e API: un processo headless non ci passa.
  **Zero capability è minimo privilegio.**
* ⭐ **Non tutti i processi DOMINIO vogliono un utente tecnico.** I tipi della **coda**
  sono accodati da un operatore e girano con lo scope catturato all'enqueue: hanno già
  un'identità, ed è quella della **persona**. Dargliene una tecnica ne cancellerebbe il
  nome. ⇒ Servono un utente i soli `DOMINIO` su canale `PGAGENT` o `COMMAND`: **quattro**,
  non sei. Entrambe le viste escludono `canale = 'CODA'`.


Dipende dalla fase 1. È il prerequisito per smettere di bypassare.

### 4.1 Il tipo ruolo — catalogo

Una riga in `config.tipi_ruoli` (`codice_interno` stabile, è la chiave su cui il codice
si aggancia). Seed CSV.

⚠️ **E la matrice delle nature va DICHIARATA.**
`anagrafiche.trgfn_soggetti_ruoli_guard_natura_ammessa` applica *«matrice assente =
nature libere»*: non scrivere righe in `config.tipi_ruoli_nature_ammesse` **è** una
decisione, e presa per omissione non si vede. O la riga, o qualcosa che dice perché
è libero.
✅ **Fatto, e non con un commento:** l'assenza è fissata da un'asserzione in
`db/pgtap/anagrafiche/test-identita-tecnica.sql` (il perché in §4.0). ⭐ Un commento si
cancella senza che nessuno se ne accorga; un test che pretende la matrice **vuota** si
rompe se qualcuno la riempie — cioè parla nel momento in cui la decisione cambia.

### 4.2 Il soggetto «sistema» e le identità — dati di macchina

Un soggetto in `anagrafiche.soggetti` (+ `tipo_soggetto_dettaglio`), un
`soggetti_ruoli` per processo, un `identita_digitali` per processo.

⛔ **Due vincoli che non si negoziano** (§6.3 dell'analisi):

1. `ruolo_applicativo = 'OPERATORE'` — ogni policy lo pretende in AND; con altro il
   processo vedrebbe **zero righe, in silenzio**;
2. ⛔⛔ **mai il profilo `SUPER_ADMIN`** — bypassa lo scope *prima* della whitelist e
   riaprirebbe la porta che tutto questo brief chiude.

⚠️ `anagrafiche.identita_digitali` ha `trg_..._z90_sync_auth_user_active_ins/upd`:
inserire un'identità **tocca `django.auth_user.is_active`**. È il comportamento voluto,
ma va saputo — non è una tabella inerte.

### 4.3 Il flag

`anagrafiche.identita_digitali.tecnica boolean NOT NULL DEFAULT false`.

⚠️ **Due effetti collaterali di una colonna nuova su una tabella automatizzata:**

* `dbops.automation_lock_columns` è *create-if-not-exists*: una colonna nuova **non**
  entra da sola. Va **DROP + rigenera** per quella tabella;
* i trigger di audit/`tx_id`/storico li genera `ci_apply`, cioè la **seconda**
  invocazione di Liquibase. ⛔ Nessun `ALTER TRIGGER` / `DROP TRIGGER` senza
  `IF EXISTS` su quei nomi: in CI, alla prima passata, non esistono ancora.

### 4.4 Il profilo si PUNTA, non si copia

`config.profili_accesso_bindings` accetta `identita_digitale_id`: l'identità tecnica si
lega **allo stesso `profilo_accesso_id` del reparto** di riferimento. ⇒ Quando il
profilo del reparto cambia, il processo segue. Nessuna copia da tenere allineata.

### 4.5 La whitelist emittenti

Una riga in `config.user_emittenti_fiscali` per **ogni** emittente che il processo deve
servire (D-1: tutti). ⛔ Non si può lasciare vuota: `fn_check_user_emittente_scope` con
zero righe risponde **false** (P-2a).

⚠️ **Ed è il punto dove nasce il buco silenzioso di D-9**: un emittente nuovo senza la
riga fa girare il lavoro a vuoto — «FATTO, 0 elaborate», nessun errore. Il presidio
*emittente non servito* (§8) è **parte di questa fase**, non un ripensamento.

---

## 5. Fase 4 — La coda impara a rifiutare (D-7, difetto A)

### 5.1 ⭐ Correzione al piano dell'analisi: il `CHECK` NON cambia

L'analisi (§10.2) diceva che la ridefinizione di `run_as` tocca **cinque** punti, fra cui
`chk_coda_lavori_run_as_scope`. **Verificato: quel `CHECK` resta valido così com'è.**

Dice *«`OPERATORE` ⇒ scope non nullo; `SISTEMA` ⇒ scope nullo»*. Dopo la ridefinizione un
job `SISTEMA` continua a non avere emittente ⇒ continua ad avere `scope` nullo. ⇒ **La
condizione è già quella giusta**: cambia il *significato* di `SISTEMA`, non la sua forma.

| Cosa | Prima | Dopo |
| --- | --- | --- |
| `SISTEMA` | il worker apre il canale `BYPASSRLS` | gira col **ruolo applicativo normale**, senza identità e senza emittente ⇒ **può toccare solo tabelle senza RLS** |
| `OPERATORE` | identità + emittente dallo scope | invariato |

⇒ I punti da toccare sono **quattro**, e uno solo è DB:

| Punto | Dove |
| --- | --- |
| il **commento** della colonna `run_as` (oggi cita il canale `BYPASSRLS`) | 🗄️ DB |
| il guard in `dbops.fn_accoda_lavoro` | 🗄️ DB |
| il legame tipo → processo (§5.2) | 🗄️ DB |
| il dispatch `_dispatch_item` | 🖥️ backend |

### 5.2 Il legame, senza duplicare la classe

⛔ **Non** una colonna `classe` su `dbops.coda_lavori_tipi`: sarebbe una **seconda
scrittura dello stesso fatto**, e due scritture dissentono.

✅ `dbops.coda_lavori_tipi.processo_codice text NOT NULL`, FK → `dbops.processi(codice)`.
La classe si **legge** da lì. Fonte unica.

⚠️ **Chi scrive la colonna non è il mirror di luglio.** La sede del dato resta il CSV
`80_data/sql/dbops/coda_lavori_tipi.csv`, ma il loader che lo porta a bordo è
`20260905-01-riancora-mirror-coda-lavori-tipi-processo`: l'ancora originale
(`20260720-10`) sta **prima** del seme di `dbops.processi` nella timeline e la colonna
lì è dichiarata `type: SKIP`. Il perché per esteso è la trappola in fondo al §11.1.

### 5.3 Il guard in `fn_accoda_lavoro`

Oggi `v_run_as := COALESCE(p_run_as, v_tipo.run_as_default)`: il default per-tipo è un
suggerimento e `p_run_as` lo sovrascrive. ⇒ un tipo di dominio può essere accodato come
`SISTEMA` e passare tutti i cancelli.

Si aggiunge: **se il processo del tipo è `DOMINIO`, `run_as` deve essere `OPERATORE`** —
altrimenti errore.

⚠️ **Il codice errore si conia, non si riusa.** La funzione oggi solleva
`E_PARAMETRO_INVALIDO`, che è dichiarato **debito, non sede**. Qui non c'è un parametro
invalido: c'è un'**invariante rotta**, quindi classe `TECNICO`. Il codice nuovo si
aggiunge **in append al CSV** dei codici e messaggi — mai un loader nuovo.
⛔ E nel `VARIADIC` non entra il nome di un parametro PL/pgSQL: la frase la legge una
persona.

---

## 6. Fase 5 — Chiusura scadenze: la classe sta sul bersaglio (D-10)

`dbops.automazione_chiusura_scadenze` prende **`classe`** (`CHECK` sugli stessi tre
valori). Il CSV si aggiorna con le due righe di oggi, **entrambe `DOMINIO`**:

| Bersaglio | Percorso all'emittente |
| --- | --- |
| `vendite.contratti` | colonna diretta |
| `vendite.listini_versioni` | `listino_id → vendite.listini.emittente_soggetto_ruolo_id` (`NOT NULL`) |

`dbops.fn_apply_chiusura_scadenze` prende **`p_classe`** e lavora **solo i bersagli di
quella classe**. ⇒ Una riga nuova nel CSV senza classe **non viene lavorata**: il
cancello sta dentro la funzione, non nell'elenco dei job.

⚠️ Il job `85_pgagent` passa la classe. ⛔ Ma **quel job non si tocca finché il bersaglio
di dominio non ha una casa**: la migrazione alla coda è backend. Finché è lì, gira come
oggi — e la vista del §8 lo dice.

⚠️ E `85_pgagent` è una fase **mai eseguita in CI** (`MARK_RAN`): un cambiamento lì si
prova solo sul database di sviluppo, e va detto nel changeSet.

---

## 7. Fase 6 — Il guard di scrittura (D-4) — ULTIMA

`script.trgfn_guard_emittente_scope`: il ramo *«utente NULL → `RETURN NEW`»* diventa
**«se questa sessione bypasserebbe comunque la RLS, salta; altrimenti, senza utente →
errore»**.

⇒ Il guard spara **esattamente dove spara la policy**: un criterio solo, quello che
PostgreSQL applica già.

| Chi | Esito |
| --- | --- |
| Liquibase (proprietario `titodb`) — **18 changeSet** fanno backfill sulle 15 tabelle col guard | ✅ passa, come passa già dalla RLS |
| pgAgent (superuser) | ✅ passa |
| `zeroerp_batch_fatturazione` (`BYPASSRLS`) | ✅ passa — ⚠️ **finché il ruolo esiste**: è il motivo per cui R-2 rende efficace questa fase, non il suo prerequisito |
| `zeroerp_app` **senza utente in sessione** | ⛔ **si ferma** — ⭐ è il bersaglio |

⚠️ **Deroga dichiarata** alle linee guida §10.4 (le funzioni di scope non guardano il
ruolo DB): qui non si identifica l'utente, si **rispecchia** la regola di bypass.
⛔ L'alternativa — una GUC che una migrazione imposta per dire «sono io» — è un cartello,
non un cancello: chiunque può impostarla. È la ragione per cui il progetto ha già
scartato il sentinel applicativo del canale di sistema.

⚠️ **Perché è ultima**: prima che i processi abbiano identità, chiuderla li ferma.
✅ **Ora l'identità c'è** (fase 3b). ⇒ Il blocco residuo **non è il ritiro del ruolo**:
sono i 12 file pgTAP e la decisione sui trigger gemelli — **§12.5 e §12.6**.

---

## 8. Le viste di presidio

`20_code`, schema `dbops`, tutte **devono restare vuote** — stampo di
`vw_riferimenti_morti_da_sanare` e `vw_liste_multi_emittente_non_certificate`.

| Vista | Elenca | Fase |
| --- | --- | --- |
| `vw_processi_che_bypassano` | ruoli **applicativi** con `BYPASSRLS` fuori dall'elenco dichiarato. Oggi uno (`zeroerp_batch_fatturazione`); a regime **zero** | ⭐ subito, indipendente |
| `vw_processi_dominio_senza_emittente` | bersagli di processi `DOMINIO` con `emittente_via` nullo, **oppure** con un percorso dichiarato la cui colonna **non esiste** (verifica su `information_schema`) | 1 |
| `vw_processi_dominio_senza_difesa` | bersagli `DOMINIO` col percorso ma **senza policy RLS né guard** — livello 2, è un **debito che deve calare**. Prime righe attese: `vendite.listini*`, `config.email_outbox` | 1 |
| `vw_run_senza_attore` | righe di `job_run_log` con `processo_codice` nullo | 2 |
| `vw_processi_dominio_senza_identita` | processi `DOMINIO` senza riga in `processi_identita`, e identità con `tecnica = true` senza processo | 3 |
| `vw_emittenti_non_serviti` | emittente attivo assente dalla whitelist di un processo `DOMINIO` (D-9) | 3 |

⚠️ **`vw_processi_che_bypassano` va scritta con cura:** `pg_roles.rolbypassrls` è
leggibile, ma l'elenco dei ruoli *applicativi* va dichiarato — non dedotto dal nome.
E `role_table_grants` **è cieco fuori dal ruolo connesso**: non si usa qui.

⚠️ **Le viste di `20_code` non precondizionano sul contenuto di `80_data`.** Il registro
è seed: una `preCondition` che pretende una riga di `dbops.processi` muore in CI, dove
`20_code` gira **prima**. Il legame si risolve a runtime.

---

## 9. I test pgTAP

Preambolo obbligatorio in ogni file (`BEGIN;`, riga di contesto,
`SET CONSTRAINTS ALL IMMEDIATE`), e i test **si fabbricano i soggetti**: un test che
itera su ciò che c'è passa a vuoto su un database ricostruito da zero.

| File | Che cosa costruisce e verifica |
| --- | --- |
| `db/pgtap/dbops/test-processi-registro.sql` | i tre `CHECK`, l'unicità del codice, la FK bersagli→processi, e che le **viste di presidio siano vuote** |
| `db/pgtap/maintenance/test-job-run-attore.sql` | `fn_job_run_start` e `fn_run_and_log` scrivono l'attore; ⛔ un `processo_codice` inesistente **è respinto dalla FK**; nessun overload residuo (arità in `pg_proc`) |
| `db/pgtap/dbops/test-coda-accoda-classe.sql` | un tipo `DOMINIO` accodato con `run_as => 'SISTEMA'` **solleva**, con lo **SQLSTATE atteso** — ⛔ `throws_ok` senza SQLSTATE accetta qualunque errore |
| `db/pgtap/dbops/test-chiusura-scadenze-classe.sql` | `fn_apply_chiusura_scadenze('AMMINISTRAZIONE')` **non tocca** un bersaglio `DOMINIO`, e viceversa |
| `db/pgtap/script/test-guard-emittente-senza-utente.sql` | ⭐ i **tre casi costruiti**: proprietario passa; operatore fuori perimetro si ferma; sessione applicativa **senza utente** si ferma |

⚠️ Il pgTAP gira **come l'applicazione** (`zeroerp_app` + contesto operatore), non da
owner: una fixture che scrive dove l'applicazione non scrive non passa.
⚠️ E la suite ha rossi preesistenti: usare `scripts/pgtap-baseline.sh` prima di
attribuire un rosso a questo lavoro.

---

## 10. L'ordine, e che cosa può partire subito

| Fase | Stato | Contenuto | changeSet | Blocca il backend? |
| --- | --- | --- | --- | --- |
| **0** | ✅ applicata | `vw_processi_che_bypassano` | `-10` | no |
| **1** | ✅ applicata | Il registro: 3 tabelle + 2 CSV di catalogo + 2 viste + GRANT | `-07`…`-15` | no — è tutto nuovo |
| **2** | ✅ applicata | L'attore sui run: 2 colonne + 2 funzioni + vista + GRANT, e la correttiva dei privilegi | `-16`…`-21` | no — parametri con default |
| **3a** | ✅ applicata | Il contratto degli utenti tecnici: tipo ruolo `PROC_AUTO`, flag `tecnica`, 2 viste, GRANT | `-22`…`-25` | no |
| **3b** | ✅ applicata | La fabbrica `fn_crea_utente_tecnico` + gli utenti tecnici **per processo × emittente**, con il loro perimetro. ⛔ Senza profilo (non serve) | `-26`…`-30`, `-36`…`-39` | no |
| **4** | ✅ applicata | Coda: `processo_codice` sui tipi (hard FK) + guard di classe in `fn_accoda_lavoro` + `NOT NULL` in `90_end` + commento `run_as` | `-40`…`-42` | ✅ **no — verificato**: `CodaLavoriRepository.accoda` è l'**unico** punto che accoda, e passa `run_as=OPERATORE`. Il guard vincola il futuro, non rompe il presente |
| **5** | ✅ applicata | Chiusura scadenze: `classe` sul BERSAGLIO + CHECK + `NOT NULL` in `90_end` + `fn_apply_chiusura_scadenze(p_classe)` con default | `-43`…`-45` | ⚠️ parziale |
| **6** | ✅ **applicata** | Il guard di scrittura: `row_security_active()` al posto del ramo «nessun utente», più `E_SCOPE_SENZA_UTENTE`. ⭐ `test-guard-emittente-senza-utente` **6/6**, ed era rosso su 4-5 prima della migrazione | `-51` + CSV | ✅ no: il batch bypassa, il drenatore imposta la GUC |

⚠️ **La 3b è separata dalla 3a per una ragione, non per comodità:** creare righe in
`anagrafiche.soggetti` attraversa dieci trigger e una FK su `stato_id`. Indovinare
lascia spazzatura in un'anagrafica vera, quindi quella parte vuole il suo giro di
verifica.

⭐ **Le fasi 0, 1 e 2 si possono scrivere e applicare senza che il backend cambi una
riga**: non tolgono niente a nessuno.

---

## 11. Trappole note, da tenere davanti mentre si scrive

### 11.1 ⛔ Trovate applicando (fasi 0–6, più DB-4) — valgono per tutto ciò che resta

Non sono cronaca: sono le cose che, ripetute, romperebbero di nuovo.

* 🔴 **`DROP FUNCTION` porta via anche i PRIVILEGI.** La `CREATE` successiva riparte dal
  default di PostgreSQL, che per le funzioni è **`EXECUTE` a `PUBLIC`**. Il
  `REVOKE ... FROM PUBLIC` di un changeSet vecchio è attaccato alla **firma vecchia** e
  sparisce con lei. Su una `SECURITY DEFINER` è un buco: è successo su
  `fn_job_run_start` (corretto da `-21`). ⇒ **Chi fa `DROP+CREATE` ricostruisce l'ACL
  nello stesso changeSet**, non nel successivo.
  ✅ Il `GRANT` ai ruoli batch invece si ricrea da solo: il provisioning imposta
  `ALTER DEFAULT PRIVILEGES FOR ROLE <migrator>`, che copre gli oggetti futuri.
* ⛔ **I privilegi sugli oggetti NUOVI non arrivano da soli** fuori dalla CI: ogni
  tabella o vista nuova vuole un `GRANT` mirato in `90_end`. ⚠️ E il difetto è
  **invisibile da `information_schema`**, che è filtrata per privilegi: gli oggetti
  risultano *inesistenti*, non *inaccessibili*.
* ⚠️ **La doc auto-gen non mostra la LUNGHEZZA dei `varchar`**: la riga dice
  `character varying` e basta. `config.tipi_ruoli.codice` è `varchar(10)`, e un codice
  di 13 caratteri ha fatto fallire il migrate. ⇒ Per una colonna `varchar` si guarda il
  DDL, oppure — più rapido — le lunghezze **già in uso nel seed**.
* ⛔ **Un `DROP` porta via i PRIVILEGI — di funzioni E di viste.** La `CREATE`
  successiva riparte dal default. ⚠️ E non basta contare su un `GRANT` in `90_end`
  marcato `runOnChange`: quello ri-esegue solo se **il suo file cambia**, e non cambia.
  ⇒ Il `GRANT`/`REVOKE` si rimette **nello stesso changeSet** del `DROP`.
* ⚠️ **`CREATE OR REPLACE VIEW` non sa TOGLIERE colonne** (aggiungerle in coda sì).
  Cambiare la forma di una vista è `DROP` + `CREATE` — con la riga sopra che ne segue.
* ⚠️ **Un presidio deve poter arrivare a ZERO, o è rumore.** La prima versione di
  `vw_run_senza_attore` contava *tutte* le righe storiche, che hanno l'attore `NULL` per
  sempre e non sono sanabili: non sarebbe mai stata vuota. Riscritta sull'**ultima
  corsa**, un job sparisce appena dichiara. ⇒ Prima di scrivere una vista di presidio:
  *«che cosa la fa arrivare a zero?»* — se non c'è risposta, la vista è sbagliata.
* ⚠️ **Un `NOT NULL` nuovo rompe le fixture pgTAP che seminano su quella tabella —
  ed è il presidio che funziona.** Le fasi 4 e 5 hanno fatto cadere 4 file pgTAP
  preesistenti: creavano tipi di coda senza processo e bersagli senza classe, cioè
  righe che il modello nuovo non ammette più. ⛔ **Non si rilassa il vincolo**: la
  fixture si adegua. ⭐ E si adegua **fabbricandosi il proprio processo** invece di
  appoggiarsi a uno del catalogo — dichiarato `MANUTENZIONE`, così il guard di classe
  non entra in gioco e quel file continua a collaudare *ciò che collaudava*, non altro.
  ⇒ Prima di scrivere un `NOT NULL`: `grep -rn "INSERT INTO <schema>.<tabella>" db/pgtap/`.
* ⛔ **Accendere la RLS su una famiglia PADRE-FIGLIO rompe chi li scrive INSIEME.**
  La policy della figlia risolve il perimetro leggendo il padre, e in un'unica
  istruzione lo legge con **lo snapshot di quell'istruzione** — che non contiene la
  riga appena scritta dalla CTE sorella. Padre invisibile ⇒ perimetro `NULL` ⇒ *«la
  nuova riga viola la regola di sicurezza»*. ⇒ **Due istruzioni.** Trovato applicando
  DB-4 ai listini; vale per qualunque famiglia protetta, backend compreso.
* ⛔ **I vincoli DIFFERITI si chiudono nei panni di chi c'è in quel momento, non di chi
  ha scritto.** `trgfn_child_requires_active_parent` legge il padre **sotto la RLS**, e
  scatta al `SET CONSTRAINTS` — non all'`INSERT`. Una fixture che crea come super admin
  e poi torna operatore si vede alzare *«Padre non attivo»* su una riga perfettamente
  attiva: sembra un difetto della fixture ed è la RLS che funziona. ⇒ I vincoli
  differiti si chiudono **prima** di cambiare attore.
* ⛔ **Un test che asserisce la PRESENZA di una riga in un presidio si rompe quando il
  debito viene pagato.** `test-processi-registro` pretendeva che
  `vw_processi_dominio_senza_difesa` nominasse `vendite.listini_versioni`: chiudendo
  R-8 è diventato rosso **per il motivo giusto**. ⭐ Un presidio ha il compito di
  arrivare a zero. ⇒ Un test sul presidio **costruisce il proprio caso**, così misura il
  meccanismo e resta verde qualunque debito reale ci sia — o non ci sia.
* ⚠️ **`has_function_privilege` con la firma scritta a mano si rompe quando la firma
  cambia.** Aggiungere un parametro a `fn_job_run_start` ha fatto fallire un test che
  citava la vecchia stringa di 5 tipi — *«la funzione non esiste»*, non *«manca il
  privilegio»*. ⇒ Il privilegio si chiede sull'**OID cercato per nome**, così il test
  misura il privilegio e non la firma.
* 🔴 **Una colonna con FK aggiunta a un mirror VECCHIO lo manda a scrivere prima del
  proprio bersaglio** (2026-09-05, migrate CI fermo). `processo_codice` è entrata nel
  CSV di `dbops.coda_lavori_tipi` e nel suo loader, che però è ancorato a **luglio**
  (`20260720-10`), mentre il catalogo `dbops.processi` lo semina `20260904-13`. In
  `80_data` l'ordine è quello dei nomi dei file: su un database ricostruito da zero il
  mirror gira prima, e il migrate muore con *«violates foreign key constraint
  "fk_coda_lavori_tipi_processi" — Key (processo_codice)=(FATTURAZIONE_GIRO) is not
  present in table "processi"»*.
  ⚠️ **Su dev non si vede, e il motivo è la solita divergenza CI-vs-DEV**: lì il seme
  dei processi e la colonna nel CSV sono atterrati in **due migrate diversi**, e al
  secondo `dbops.processi` era già pieno. Un solo giro, e il difetto salta fuori.
  ⇒ **Il numero di un changeSet è la sua posizione nella timeline**: un fatto nato a
  settembre non può essere scritto da un'ancora di luglio. Il rimedio è un **mirror
  ri-ancorato** dopo il seme (`20260905-01`), stessa forma dei ri-ancoraggi
  `20260806-13`/`-14` — si duplica un'ancora, non una sorgente.
  ⛔ **E togliere la riga `- column:` NON basta**: una colonna presente
  nell'intestazione del CSV e non dichiarata viene caricata lo stesso, perché Liquibase
  mappa dall'header e la lista `columns` sono solo *override*. L'unica forma che non la
  scrive è `type: SKIP` — verificato con `updateSQL` offline su Liquibase 5.0.4, non
  supposto.
  ⭐ **La domanda da farsi prima**, ogni volta che si aggiunge una colonna a un CSV già
  a bordo: *«il valore che ci metto ha una FK, e il suo bersaglio è seminato prima o
  dopo questo loader?»*

### 11.2 Le regole di sempre


* ⛔ **`runOnChange: true` è vietato** in `00_schema` e `20_code` — presidiato in CI. E
  se si spegne un `runOnChange` altrove, si corregge anche `validCheckSums` (**al
  plurale**: il singolare Liquibase lo ignora).
* ⛔ **Nessuna `preCondition` di `00_schema`/`20_code` sul contenuto di `80_data`** (§8).
  Leciti: `tableExists`, `columnExists`, `pg_proc`, `sqlCheck` con `expectedResult: 0`.
  ⚠️ Il verso opposto **si tiene**: un changeSet di `80_data` deve precondizionare su
  `tableExists`.
* ⛔ **Niente DDL su trigger che nascono da `ci_apply`** (audit, `tx_id`, storico): in CI
  non esistono ancora alla prima passata.
* ⛔ **I dati di `80_data` si cambiano dal CSV**, non con `UPDATE` diretti — vale per il
  registro, per i codici errore e per `automazione_chiusura_scadenze`.
* ⛔ **Le definizioni si prendono dalla doc auto-gen**, mai dagli YAML: una funzione è
  riscritta da changeSet successivi, e un singolo YAML è quasi sempre stantio.
* ⚠️ **`%TYPE` in firma è una fotografia**, e non si usa nelle funzioni che citano
  `django.*`.
* ⚠️ **Il numero `NN` di un changeSet è globale per data e scade nel minuto**: si assegna
  quando si scrive il file, non adesso.
* ⛔ **Non applicare migrazioni** senza richiesta esplicita, e non lanciare la build doc
  né rigenerare `changelog-autogen.yaml` a mano.

---

## 12. ⭐ Registro dei residui — che cosa resta quando questo brief chiude

> ⛔ **Questa sezione non progetta niente**: elenca ciò che il cantiere ha lasciato
> aperto o fatto emergere, con **chi lo chiude** e **come si vede che è chiuso**.
> Serve a non doverlo ricostruire leggendo il brief da capo.

⭐ **Dove c'è un presidio, la voce si verifica da sola**: non si va a memoria, si
interroga la vista. Dove non c'è, la colonna lo dice.

### 12.1 🗄️ DB — ✅ niente di aperto

| # | Residuo | Blocco | Come si vede che è chiuso |
| --- | --- | --- | --- |
| **R-1** | ✅ **CHIUSA — fase 6 applicata il 2026-09-04** (changeSet `-51`). I 12 pgTAP riscritti e verdi; i cinque trigger gemelli restano come sono, col perché nel changeSet | — | fatto: `test-guard-emittente-senza-utente` **6/6**, e la baseline su 491 file non registra **nessuna regressione** |

### 12.2 ⚙️ Provisioning e backend — il perimetro non è nostro

| # | Residuo | Dove | Come si vede che è chiuso |
| --- | --- | --- | --- |
| **R-2** | **Ritiro del ruolo `zeroerp_batch_fatturazione`** (`BYPASSRLS`). ⛔ Non è un changeSet: i privilegi dei ruoli batch stanno nel provisioning. ⚠️ **Indipendente da R-1**, non un suo prerequisito | `scripts/sql/provision_db_role_batch_fatturazione.sql` + `backend/apps/core/services/system_context.py`, `run_fatturazione_batch.py`, `draina_coda_stampa.py`, `zeroerp_backend/settings.py` | `dbops.vw_processi_che_bypassano` **vuota** — ⭐ è il presidio della fase 0, acceso apposta |
| **R-3** | **I command passano il processo** a `script.fn_job_run_start` / `maintenance.fn_run_and_log` (`p_processo_codice`, `p_auth_user_id`). ⚠️ **Non urgente**: i 12 job pgAgent si autodichiarano già per derivazione dal jobname (§3.3); questo serve ai **command**, che jobname non hanno | backend | `SELECT * FROM dbops.vw_run_senza_attore` → **vuota** |
| **R-4** | **Riscrittura di `_guard_canale_sistema`** — il canale di sistema applicativo, dopo il ritiro del bypass | backend | nessun presidio DB: lo copre il test BE |
| **R-5** | **UI utenti tecnici / identità digitali**: oggi si vedono solo da SQL. ⚠️ Concordata a voce, **non ancora briefata** | BE + FE | — |
| **R-6** | ✅ **Dispatch coda: NON serve.** *Verificato 2026-09-04*: `CodaLavoriRepository.accoda` è l'**unico** punto che accoda e passa già `run_as=OPERATORE`. Il guard di classe vincola il futuro senza rompere il presente | — | — |

### 12.3 🕳️ Debiti che questo brief **fa emergere** e non progetta

⚠️ Non sono regressioni introdotte qui: erano scoperti **prima**, ed erano invisibili
perché nessuno faceva la domanda. Ora una vista li elenca.

| # | Debito | Perché è un debito | Come si vede che è chiuso |
| --- | --- | --- | --- |
| **R-7** | **`config.email_outbox` non ha la colonna emittente** — quindi `send_pending_emails` è un processo di `DOMINIO` **senza percorso al perimetro** | una email fiscale è di un emittente; senza colonna non c'è niente su cui filtrare | `dbops.vw_processi_dominio_senza_emittente` **vuota** |
| **R-8** | ✅ **CHIUSA — 2026-09-05.** `vendite.listini` e `listini_versioni` hanno policy RLS + write-guard (changeSet `20260905-02`…`-06`) | era il **prerequisito** della chiusura scadenze per emittente, non un debito parallelo: `fn_apply_chiusura_scadenze` è `SECURITY INVOKER`, quindi il perimetro arriva dall'identità — ma solo dove c'è una policy che lo applichi | fatto: `dbops.vw_processi_dominio_senza_difesa` non nomina più la famiglia listino, e `db/pgtap/rls/test-rls-listini-ef-whitelist-write.sql` è 8/8 |
| **R-10** | ⭐ **NUOVO (2026-09-05, trovato rispondendo al BE):** `vendite.fatture_stampa_coda` ha il percorso all'emittente (`fattura`) ma **nessun write-guard** | `draina_coda_stampa` sta per ricevere un'identità tecnica: senza la difesa avrebbe **mezzo perimetro**, come i listini (R-8) | `dbops.vw_processi_dominio_senza_difesa` vuota — dal 2026-09-05 nomina **una riga sola**, questa |
| **R-9** | ✅ **CHIUSA — non è un debito, è una decisione dichiarata.** La matrice `config.tipi_ruoli_nature_ammesse` è **vuota** per `PROC_AUTO` (§4.0: le nature `PG` esigono partita IVA e codice fiscale, che un processo non ha) | sta qui solo perché **sembra** un buco da tappare, e fra sei mesi qualcuno proverà a tapparlo | è già presidiata: l'asserzione *«non vincola la natura»* in `db/pgtap/anagrafiche/test-identita-tecnica.sql` si rompe se qualcuno riempie la matrice |

### 12.4 ⛔ Fuori perimetro dichiarato — non sono residui

**Magazzino e acquisti** sono in ristrutturazione: le loro misure sono state **tolte**
dall'analisi apposta, e non rientrano da questa porta.

---

---

### 12.5 ⛔ Correzione — la fase 6 NON è bloccata dal ritiro del ruolo

> **Fatto datato 2026-09-04.** Era scritto — anche a voce — che chiudere la fase 6
> prima del ritiro di `zeroerp_batch_fatturazione` avrebbe fermato la fatturazione.
> ⛔ **È falso, e il verso è esattamente opposto.**

La regola nuova è *«se questa sessione bypasserebbe comunque la RLS, salta»*. E
`zeroerp_batch_fatturazione` **ha `BYPASSRLS`**: è quindi la sessione che **continua a
passare**, non quella che si ferma. Il ritiro del ruolo (R-2) non è un prerequisito
di R-1: è ciò che **rende R-1 efficace** su quel processo, ed è indipendente.

⚠️ **Perché mi era sfuggito:** avevo letto la tabella del §7 senza guardare la
condizione della sua terza riga — *«processo applicativo senza utente **(dopo il
ritiro del bypass)**»*. La riga diceva già la cosa giusta.

**Chi passa oggi, misurato** (`pg_roles`, `pg_class`, `pgagent.pga_jobstep`, e la
`.service` del demone):

| Sessione | Passa? | Perché |
| --- | --- | --- |
| Liquibase — `titodb` | ✅ | è **proprietario** di tutte e 15 le tabelle, e nessuna ha `FORCE ROW LEVEL SECURITY` |
| pgAgent | ✅ | il demone si connette `user=postgres`, superuser |
| `zeroerp_batch_fatturazione` | ✅ | `rolbypassrls = true` |
| **`zeroerp_app` senza utente in sessione** | ⛔ **si ferma** | ⭐ è il bersaglio della fase |

**Il backend a runtime regge** — verificato, non supposto: i due command che scrivono
sotto guard (`run_fatturazione_batch`, `draina_coda_stampa`) usano la connessione di
sistema col ruolo di bypass; il drenatore della coda **imposta `app.current_user_id`**
dallo `scope` (`coda_lavori/context.py`); `send_pending_emails` scrive su
`config.email_outbox`, che il guard non copre.

### 12.6 ⚠️ Il costo vero della fase 6, misurato

**a) Dodici file pgTAP svuotano `app.current_user_id` e poi scrivono** su una delle 15
tabelle — ~51 scritture. Non è un difetto delle fixture: quei test **si appoggiano al
ramo che la fase 6 chiude**, e uno lo dichiara nell'intestazione
(*«…quando la GUC `app.current_user_id` è vuota»*).

⭐ Quindi non si riparano con una fixture: vanno **riscritti perché dichiarino un
operatore**. È lavoro che ha valore anche se la fase 6 slittasse — oggi quei file
collaudano il comportamento di una porta aperta.

⚠️ Altri **6** file toccano le stesse tabelle svuotando la GUC ma girano `owner`
(`titodb`, proprietario) e **non sono toccati**.

**b) ⛔ Il ramo «nessun utente» non è solo nel guard: sono OTTO funzioni trigger.**
`trgfn_contratti_default_emittente`, `…ddt…`, `…ordini…`, `…preventivi…`,
`trgfn_event_log_deriva_scope`, più due su `billing_account`.

⇒ Chiudere **una sola** delle otto lascia sette che rispondono ancora *«nessun utente,
va bene lo stesso»*. È la trappola già registrata: **un `CHECK` allargato e un guard
che dissentono**. La fase 6 deve decidere se i cinque «default emittente» restano come
sono (⭐ tesi difendibile: **non concedono niente**, riempiono un default e poi il
guard decide) o se seguono. **Da decidere prima di scrivere il changeSet, non dopo.**

**c) 🕳️ Non misurato: la suite Django.** 59 file di test toccano i modelli guardati,
**5** impostano il contesto utente. Dipende da chi è proprietario delle tabelle nel
database di test: se è `zeroerp_app`, passa da proprietario e non se ne accorge
nessuno. ⇒ Si misura lanciando la suite BE **dopo** il changeSet, non prima.

---

### 12.7 ✅ Fase 6 — che cosa è stato fatto, nell'ordine

**1. I dodici pgTAP, prima del changeSet.** Rimosso lo svuotamento di
`app.current_user_id`; il contesto operatore del preambolo resta valido per tutto il
file. ⭐ **Dieci sono passati senza altro**, perché le loro fixture già ordinavano la
scelta dell'emittente e pescavano quello dell'operatore.

Due hanno chiesto una decisione, e sono i due che insegnano qualcosa:

* **`test-ordini-riepilogo-iva-totali.sql`** — il passo 15 sposta un ordine su un
  **altro** emittente per far scattare `trg_ordini_z90_ricalcola_totali_upd`, che
  scatta **solo** su `AFTER UPDATE OF emittente_fiscale_id` (verificato su
  `pg_get_triggerdef`): non c'è un'altra scrittura che lo accenda. ⚠️ Ma spostare un
  documento fra emittenti è precisamente ciò che il guard nega a un operatore — la
  relazione utente/emittente è 1-a-1, quindi **nessun** operatore ha entrambi.
  ⇒ Il passo si mette nei panni del **super admin**, l'unico attore che può farlo, e
  poi torna operatore. ⭐ E l'asserzione resta nel contesto del super admin: appena il
  documento è passato all'altro emittente, **l'operatore di partenza non lo vede più**,
  e il confronto tornava `NULL` — un rosso che sembra un trigger rotto ed è invece la
  policy che funziona.
* **`test-trgfn-preventivi-default-emittente-e-guard-coerenza.sql`** — qui svuotare la
  GUC **resta giusto**: la GUC vuota *è il caso in prova*, non una scorciatoia. ⚠️ E
  regge dopo la fase 6 per una ragione fragile, ora scritta nel file: i trigger
  `BEFORE ROW` scattano in **ordine alfabetico**, e `…_default_emittente_ins` viene
  prima di `…_guard_emittente_scope_ins_upd`. ⛔ Una rinomina invertirebbe l'ordine e il
  test diventerebbe **verde sull'altro errore** — entrambi passano da
  `fn_log_and_raise_error`, quindi entrambi sono `P0001`.

⚠️ Il tredicesimo file, `test-seed-stati-doc-ordini-evaso-v1.sql`, resta col rosso che
aveva: **gli stessi due test 4 e 6**, verificato rieseguendo la versione precedente.
Sta in `baseline-rossi.tsv` e non c'entra con questa fase.

**2. Due difetti trovati in un test della fase 3a** (`test-identita-tecnica.sql`), che
nessuno aveva più eseguito dopo la 3b:

* il test 7 costruiva il caso mettendo `tecnica = true` su una **persona**. Dal
  changeSet `-28` quell'UPDATE non passa più: un'identità tecnica pretende un
  `soggetto_ruolo` `PROC_AUTO`. ⭐ **È il DB che ha imparato a impedire proprio l'abuso
  che il test temeva.** La fixture ora costruisce il caso che *resta possibile* — un
  utente tecnico vero il cui legame col processo viene disattivato: il residuo di un
  processo ritirato male;
* il test 8 **diceva il falso** dopo la riscrittura `-38`: pretendeva che
  `vw_emittenti_non_serviti` non nominasse un processo senza utente tecnico. Con la
  domanda nuova — *«per la coppia (processo, emittente) esiste un utente?»* — la
  risposta è «no» su **ogni** emittente. ⇒ Ora asserisce ciò che serve sapere: la vista
  nomina **ogni emittente attivo rimasto scoperto**.

**3. Il changeSet `-51`** e il codice errore `E_SCOPE_SENZA_UTENTE` (classe `TECNICO`:
non c'è una persona a cui negare qualcosa, c'è un processo senza identità).
⭐ `CREATE OR REPLACE`, non `DROP`+`CREATE`: la firma non cambia, quindi l'ACL resta
attaccata — la lezione di `-21` applicata prima che costasse.

**4. Il test della fase, `db/pgtap/script/test-guard-emittente-senza-utente.sql`** —
⭐ **era ROSSO sui test 4 e 5 prima della migrazione, e doveva esserlo**:
*«caught: no exception»* era la porta aperta, misurata. ✅ **6/6 dopo.**
Il test 2 è il presidio del test stesso: asserisce che la sessione **subisce** la RLS —
girando da owner, i test 4-5 sarebbero verdi *perché non succede niente*.

---

### 12.8 ⚠️ Due regressioni arrivate da FUORI questo cantiere, mentre lo si chiudeva

Nessuna delle due è della fase 6, e distinguerle è costato meno di ripararle.

* **`test-fatturazione-draft.sql`** — cadeva sui test 3-4-5 (*selezione*), non su 1-2
  (*inserimento*): il changeSet **`-50`** di un altro cantiere fa filtrare
  `fn_select_attivita_fatturabili` su `emit_batch_id = p_lock_batch_id`. La fixture
  creava l'attività **senza marchio** e poi chiedeva il lock col proprio giro: zero
  righe, che è l'effetto voluto da quel cantiere. ⇒ Ora la fixture si marchia col
  proprio giro, come farà il backend.
* **CI rossa su `20260904-47`** (`GRANT … TO zeroerp_batch_fatturazione` in un
  changeSet). ⚠️ Il messaggio del guardrail dava una ragione **inesatta** per questa
  riga: *«il migrate muore»* — non sarebbe morto, il `GRANT` stava dentro un
  `IF EXISTS (… pg_roles …)` che il guardrail, testuale, non vede. Rossa era la
  **verifica**, non il migrate. ⭐ Ma la riga andava tolta per l'altra ragione: il
  provisioning fa già `GRANT SELECT ON ALL TABLES` + `ALTER DEFAULT PRIVILEGES`, quindi
  copriva già la vista. Duplicare un permesso è come duplicare un dato.
  ✅ Il checksum non è stato un problema: quel changeSet ha già
  `runOnChange: false` + `validCheckSums: [ANY]`, quindi accetta il nuovo checksum e
  **non ri-esegue**. ⚠️ Con `runOnChange: true`, `ANY` l'avrebbe fatto ri-eseguire.

---

### 12.9 📨 Il backend ha risposto — cinque richieste, e due decisioni congiunte

Il BE ha consumato il contratto e ha aperto
[brief-db-processi-automatici-residui-be.md](brief-db-processi-automatici-residui-be.md)
con cinque richieste. ⭐ **La risposta del team DB sta nel §1-bis di quel brief**, non
qui: si risponde dove è stato chiesto.

Quello che ricade su questo registro:

* ✅ **R-8 (listini) — CHIUSA il 2026-09-05**, ed è stata la prima cosa fatta proprio
  perché non era «un debito che deve calare»: era il **prerequisito** della migrazione
  della chiusura scadenze sulla coda. Misurato: `fn_apply_chiusura_scadenze` è
  `SECURITY INVOKER`, quindi il perimetro arriva **gratis** dall'identità con cui il
  lavoro gira — ma solo dove una policy lo applica, e `listini_versioni` non ne aveva
  nessuna. ⇒ Nessun parametro nuovo sulla funzione: due policy e due guard;
* **R-10 è nuovo** (sopra), stessa forma di R-8;
* **R-7 (email_outbox) ha una forma obbligata**: `ambito` è `NOT NULL` e oggi tutte le
  righe sono `SISTEMA`. ⇒ La colonna emittente dev'essere **nullable con un CHECK legato
  ad `ambito`** — un'email di sistema non ha emittente. ⚠️ E il presidio va insegnato a
  non contare le righe `SISTEMA`, o nasce già rosso.

⛔ **Due cose non le decide il DB da solo**, e vanno chiuse prima che uno dei due lati
scriva:

1. **La derivazione del processo dal jobname non copre quattro job vivi** — fra cui
   `run_fatturazione_batch:immediata`, il cui nome porta un **suffisso** che non
   combacerà mai. Rendere obbligatoria la colonna oggi **pianterebbe quei job**.
2. **Un processo di coda accodato da una MACCHINA** non esiste nel modello: i presidi
   escludono i processi `CODA` dal bisogno di identità perché assumono che chi accoda sia
   una persona. Ma `fn_accoda_lavoro` pretende uno scope con un `auth_user_id`, quindi
   l'utente tecnico servirebbe comunque — per riempire lo scope, non per eseguire.

---

### 12.10 ✅ Documentazione — che cosa è stato scritto

⛔ **Solo `manual/`**: le pagine sotto `tabelle/`, `funzioni/` e `views/` sono
auto-generate e non si toccano a mano.

**Dieci pagine nuove**

| Dove | Pagine |
| --- | --- |
| `dbops/manual/` | `processi` · `processi_bersagli` · `processi_identita` |
| `dbops/manual/` | le sei viste di presidio |
| `script/manual/` | `fn_crea_utente_tecnico` |

**Nove pagine esistenti allineate** — gli oggetti che il cantiere ha modificato:
`coda_lavori_tipi`, `fn_accoda_lavoro`, `automazione_chiusura_scadenze`,
`fn_apply_chiusura_scadenze`, `job_run_log`, `fn_run_and_log`,
`fn_job_run_start`, `identita_digitali`,
`trgfn_identita_digitali_guard_coerenza`.

⛔ **Una era diventata FALSA, non solo vecchia:**
`script/manual/trgfn_guard_emittente_scope` descriveva ancora il passo 1 come
*«nessun utente in sessione → skip»* — cioè la porta che la fase 6 aveva appena
chiuso. ⚠️ Una pagina incompleta si perdona; una che descrive un varco che non
esiste più manda qualcuno nella direzione sbagliata. Corretta (§12.7 il resto), insieme al conteggio
delle tabelle presidiate (erano dodici, sono **quindici**).

⚠️ **Un passo resta a chi genera la doc**: il generatore inserisce la riga
`{% include-markdown %}` nella pagina auto-gen **solo se il file manuale esisteva
quando ha girato**. ⇒ Dopo aver scritto un `manual/` nuovo va rilanciato
`scripts/gen_db_docs.py`, o la pagina resta scritta e **non agganciata**.

---

---

## 13. Riferimenti

* [analisi-db-be-processi-automatici-identita-e-perimetro.md](analisi-db-be-processi-automatici-identita-e-perimetro.md)
  — **le decisioni e il perché**: classi (§2), porta in scrittura (§4, §4.1), utenti
  tecnici (§6), limiti dei presidi (§13.1)
* `dbops.coda_lavori`, `dbops.coda_lavori_tipi`, `dbops.fn_accoda_lavoro`
* `maintenance.job_run_log`, `maintenance.fn_run_and_log`,
  `script.fn_job_run_start` / `fn_job_run_end`
* `script.trgfn_guard_emittente_scope`, `script.fn_check_user_emittente_scope`
* `anagrafiche.identita_digitali`, `anagrafiche.soggetti_ruoli`,
  `config.tipi_ruoli`, `config.tipi_ruoli_nature_ammesse`,
  `config.profili_accesso_bindings`, `config.user_emittenti_fiscali`
* `dbops.automazione_chiusura_scadenze`, `dbops.fn_apply_chiusura_scadenze`
* `dbops.vw_liste_multi_emittente_non_certificate` — lo stampo del presidio
  «dichiarato ma non verificato», col limite scritto nella descrizione
* `docs/it/linee-guida-sql.md` §10 (RLS), §11 (i divieti di changeSet)
