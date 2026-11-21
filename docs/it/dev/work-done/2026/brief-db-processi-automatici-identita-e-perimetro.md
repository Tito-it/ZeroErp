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
> * ✅ **documentazione allineata** — §12.12;
> * ⭐ **pgAgent sveglia, non lavora** — §12.12;
> * 🔴 **R-12**: `apply_storicizza_weekly` è fermo dal 21-02 — §12.11;
> * ✅ **decisioni del 2026-09-05** — §12.10.
> * 📨 **il BE ha risposto** con cinque richieste — §12.9.
>
> 🔴 **Correzione 2026-09-05 (b) — il migrate della CI si fermava su
> `20260905-23`**: `dbops.vw_processi_roster` faceva `JOIN django.auth_user`, e
> una **vista** si risolve alla `CREATE` mentre le tabelle di Django le crea
> `manage.py migrate`, dopo. Il riferimento passa ora da un accessore plpgsql
> (`script.fn_get_auth_user_stato`), le cinque condizioni restano cinque —
> §11.1, penultima trappola. Definizione viva: `20260905-30`.
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
* ⛔⛔ **Un test che asserisce la PRESENZA di una riga in un presidio si rompe quando il
  debito viene pagato — ed è successo TRE volte.** `test-processi-registro` due volte
  (`listini_versioni` chiudendo R-8, `send_pending_emails` chiudendo DB-3),
  `test-identita-tecnica` una. Ogni volta il test è diventato rosso **perché il lavoro
  era riuscito**.
  ⭐ **La regola, ormai pagata tre volte:** un test SU un presidio asserisce che è
  **vuoto**, e **costruisce** il caso che lo deve accendere. Non si appoggia mai a un
  debito reale — quelli si pagano, ed è il loro mestiere.
* ⚠️ **E il verso opposto, trovato il 2026-09-05: anche «il presidio è VUOTO» può
  diventare falso senza che niente si rompa.** `test-rls-fatture-stampa-coda-write-guard`
  chiedeva che `vw_processi_dominio_senza_difesa` fosse vuota — ed era vero quando è
  stato scritto. Poche ore dopo, il `20260905-18` ha dato a `config.email_outbox` la
  colonna emittente **ma non la policy**, e la riga è ricomparsa **giusta**: un debito
  con un nome, dichiarato.
  ⛔ Insistere su «vuota» avrebbe reso il rosso una bugia — non un difetto, ma una
  decisione presa apposta. ⇒ Da quando un presidio sa **dichiarare** i suoi debiti,
  l'invariante non è più «vuoto» ma «**nessuna riga non dichiarata**».
  ⚠️ E il rischio va dichiarato dove sta: **dichiarare un debito zittisce quel test**.
  Per questo il censimento dei debiti vive in un file suo, che prova che un bersaglio
  **nuovo** e rotto esce `NON_DICHIARATO` — cioè che il flag è un gesto, non
  l'impostazione di fabbrica.
* ⚠️ **Un numero scritto a mano in un'asserzione di copertura è una fotografia.**
  `test-processi-registro` chiedeva «il seed copre tutti e **tre** i canali» con un `3`
  costante: il giorno in cui il `CHECK` ne ha ammesso un quarto (`CODA_AUTOMATICA`) è
  andato rosso pur essendo tutto a posto. ⭐ L'elenco lecito si **legge dal vincolo**, e
  l'asserzione diventa la regola vera: *ogni canale dichiarato è usato da almeno un
  processo*. Aggiungerne uno senza seminarlo accende il test; aggiungerlo seminandolo no.
* ⛔ **Un vincolo nuovo rompe i test che collaudavano la vecchia tolleranza, e il
  principio va riscritto, non il test.** `chk_job_run_log_processo_dichiarato` ha rotto
  due asserzioni: «un jobname sconosciuto resta senza attore» (ora **non entra
  affatto**) e «la vista vede un run senza attore» (ora **non può più nascerne uno**).
  ⭐ Nel secondo caso il presidio ha **cambiato natura**: da «chi non si è ancora
  dichiarato» — domanda sul presente — a «il residuo storico che non si dichiarerà
  mai». Scriverlo dentro il test è ciò che impedisce di leggerlo ancora come prima.
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
  🔴 **Seguito del 2026-09-05, e chiude la storia: due mirror sullo stesso CSV sono una
  trappola armata.** Il ri-ancoraggio ha lasciato **due** loader su
  `coda_lavori_tipi.csv` — quello di luglio con `processo_codice` in `type: SKIP`, quello
  di settembre completo. Una riga **nuova** viene però inserita dal più **vecchio**, che
  per disegno non sa scrivere quella colonna: e nel frattempo la colonna è diventata
  `NOT NULL`. ⇒ *«il valore nullo nella colonna "processo_codice" viola il vincolo non
  nullo»*, sul changeSet di luglio.
  ⚠️ **Stessa divergenza CI-vs-DEV, presa dal verso opposto**: in CI il mirror gira a
  luglio quando la colonna è ancora nullable e settembre la completa; su dev il
  `NOT NULL` c'è già. ⛔ Aggiungere la colonna al mirror di luglio avrebbe **riaperto il
  problema di timeline** per cui era in `SKIP`.
  ⇒ **Il mirror vecchio smette di caricare** (`loadUpdateData` → `SELECT 1;` più la
  diagnosi a commento) e **non si cancella**: è già applicato, e la sua riga in
  `databasechangelog` racconta che a luglio quei due tipi sono stati seminati.
  ⭐ **La regola:** finché un CSV ha due mirror, ogni riga nuova va a chi arriva prima —
  cioè a chi ne sa di meno. **Una sorgente, un'ancora.**

* 🔴 **Una VISTA non può nominare `django.*` — una funzione sì** (2026-09-05,
  secondo migrate CI fermo). `dbops.vw_processi_roster` faceva
  `JOIN django.auth_user` e la CI si è fermata con *«la relazione
  "django.auth_user" non esiste»*.
  ⛔ **Non è un ordine da sistemare**: quelle tabelle **non esistono in nessun
  momento** del migrate. Lo schema `django` lo crea Liquibase (`90_end`,
  `20250924-01`), le TABELLE dentro le crea `manage.py migrate` — un passo che in
  `ci.yaml` non c'è affatto e in `ci-validate.yaml` viene dopo (sta scritto nella
  CI stessa, `ci-validate.yaml:509`).
  ⭐ **La differenza è il momento in cui il riferimento si risolve**: il corpo di
  una funzione **plpgsql** non viene risolto alla `CREATE`, una **vista** sì. È
  per questo che le ~40 funzioni del progetto che leggono `django.*` non hanno
  mai dato problemi — ed è la stessa ragione della regola già scritta *«funzioni
  che citano `django.*`: plpgsql, mai `%TYPE`»*, di cui questa è la seconda metà
  mancante.
  ⇒ **La regola: il DB può CHIAMARE dentro `django.*`, non può DIPENDERNE
  strutturalmente** — vista, FK, colonna generata. Il precedente c'era già e non
  era stato letto: `anagrafiche.risorse_umane_auth_user`, una vista che si chiama
  così, passa da `identita_digitali` e non da Django.
  ⇒ Rimedio: un **accessore plpgsql** (`script.fn_get_auth_user_stato`) e un
  `JOIN LATERAL` sopra di esso. Il join resta INNER, quindi il comportamento non
  cambia di una riga — provato sul DB in transazione annullata: stesse 8 righe,
  stesso ordine, e spegnendo `is_active` la coppia sparisce come pretende il
  test 6 del pgTAP.
  ⛔ **Non si sacrifica la condizione**, e sarebbe stata la scorciatoia ovvia
  («tanto `idg.attivo` la rispecchia»): la sincronia è a senso unico
  (identità → Django), quindi un utente disattivato **dentro Django** resterebbe
  attivo per il DB.
  ⚠️ **E il changeSet era già applicato su dbdev**: correggerlo e basta avrebbe
  lasciato due definizioni dello stesso oggetto su due macchine — e la doc
  auto-gen, che si genera da dbdev, avrebbe raccontato quella sbagliata. Serve
  `validCheckSums: ANY` sul vecchio (perché da zero deve creare la forma giusta,
  anche per la preCondition del `-24`) **più** un changeSet nuovo che allinei
  dbdev: `20260905-30`.

* 🔴 **«La vista è vuota» è lo STESSO errore che fissa un debito, girato al
  contrario** (2026-09-05, unica regressione pgTAP dopo il migrate).
  `test-processi-registro` t.10 fissava `send_pending_emails` come riga attesa;
  corretto in `is_empty` sull'intera vista, è tornato rosso al primo migrate.
  ⛔ Fissare l'**assenza** di un debito è fragile quanto fissarne la presenza.
  ⚠️ E il debito non era stato pagato: si era **spostato**. Il `-18` ha dato
  l'emittente a `config.email_outbox`, ma quella tabella la scrive l'interfaccia
  — il processo legge `config.email_log`, che la colonna non ce l'ha. *Un debito
  pagato e uno spostato, da fuori, si assomigliano.*
  ⭐ L'invariante stabile è **«nessuna riga `NON_DICHIARATO`»**, ed era già
  scritta due volte nello stesso perimetro: t.13 dello stesso file (bypass RLS) e
  t.4 di `test-presidi-debito-dichiarato`. È la ragione per cui la colonna
  `stato` esiste (`20260905-19`).
  ⚠️ Il prezzo si dichiara: dichiarare un debito **zittisce** quel test. Lo
  tengono onesto i casi COSTRUITI (t.11, t.12, e t.6 dell'altro file).

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

### 12.1 🗄️ DB — ✅ niente di aperto *fra ciò che il brief pianificava* (lo stato finale: §12.17)

| # | Residuo | Blocco | Come si vede che è chiuso |
| --- | --- | --- | --- |
| **R-1** | ✅ **CHIUSA — fase 6 applicata il 2026-09-04** (changeSet `-51`). I 12 pgTAP riscritti e verdi; i cinque trigger gemelli restano come sono, col perché nel changeSet | — | fatto: `test-guard-emittente-senza-utente` **6/6**, e la baseline su 491 file non registra **nessuna regressione** |

### 12.2 ⚙️ Provisioning e backend — il perimetro non è nostro

| # | Residuo | Dove | Come si vede che è chiuso |
| --- | --- | --- | --- |
| **R-2** | **Ritiro del ruolo `zeroerp_batch_fatturazione`** (`BYPASSRLS`). ⛔ Non è un changeSet: i privilegi dei ruoli batch stanno nel provisioning. ⚠️ **Indipendente da R-1**, non un suo prerequisito. ✅ **La metà DB è pronta (2026-09-05)**: `scripts/sql/retire_db_role_batch_fatturazione.sql`, con tre cancelli (sessioni aperte, oggetti posseduti, ruolo già assente) e la verifica sul presidio. ⛔ Si lancia **dopo** il backend: prima, ferma la fatturazione | `scripts/sql/provision_db_role_batch_fatturazione.sql` + `backend/apps/core/services/system_context.py`, `run_fatturazione_batch.py`, `draina_coda_stampa.py`, `zeroerp_backend/settings.py` | `dbops.vw_processi_che_bypassano` **vuota** — ⭐ è il presidio della fase 0, acceso apposta |
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
| **R-12** | 🔴 **NUOVO (2026-09-05) — `apply_storicizza_weekly` FALLISCE DA FEBBRAIO.** `config.storico_set_storicizza` ha **tre** righe che puntano a tabelle sparite | il job pgAgent gira ogni settimana (ultima corsa verificata: 2026-09-05) e muore sempre su `ALTER TABLE vendite.attivita_fatturabili_lotti`, che non esiste piu'. ⛔ Muore **prima di scrivere**, quindi non lascia traccia nel giornale: l'ultima riga di `job_run_log` per quel job e' del **21 febbraio** | `dbops.vw_run_senza_attore` non nomina piu' `apply_storicizza_weekly` — cioe' quando quel job riesce a girare |
| **R-11** | ⚠️ **NUOVO (2026-09-05):** i due job pgAgent per `automations_lock_columns` e `automations_delete_block` vivono in `85_pgagent`, che in CI è **`MARK_RAN`** | segnata come eseguita **senza essere eseguita**: su un ambiente ricostruito da zero i due job non esisterebbero, e nessun test lo direbbe | ⛔ non c'è un presidio DB possibile: la fase non gira. Si verifica **a mano** su un ambiente nuovo |
| **R-10** | ✅ **CHIUSA — 2026-09-05.** `vendite.fatture_stampa_coda` ha il write-guard (changeSet `20260905-07`) | la policy c'era già, ma sull'`INSERT` il `WITH CHECK` arriva **dopo** i `BEFORE ROW`: la riga si fermava con un errore vero e inservibile invece di nominare utente ed emittente | fatto: ⭐ `dbops.vw_processi_dominio_senza_difesa` è **VUOTA**, primo presidio del cantiere ad arrivarci |
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

### 12.10 ✅ Decisioni del 2026-09-05 — le tre domande aperte sono chiuse

⭐ La risposta di merito sta nel **§1-quater** di
[brief-db-processi-automatici-residui-be.md](brief-db-processi-automatici-residui-be.md):
si risponde dove è stato chiesto. Qui c'è cosa ricade su questo registro.

| Decisione | Effetto su questo brief |
| --- | --- |
| **R-E → strada B** | ⛔ **cambia un presidio nostro.** «Coda ⇒ c'è una persona» è un'assunzione scritta da noi, ed è lei a sbagliare: un processo di coda accodato da una **macchina** vuole comunque l'identità. Si corregge la regola, non si spacca il processo in due |
| **`lock_columns` / `delete_block` → dimenticanza** | due job notturni nuovi + due righe nel registro. ⚠️ Ritirarli *non* avrebbe svuotato `vw_run_senza_attore`: un job ritirato non gira più, quindi non si dichiara mai — sarebbe stato di nuovo un presidio incapace di arrivare a zero |
| **DB-7 → allineare i nomi, non il codice esplicito** | 2 rinomine + 2 righe nel CSV, **più il presidio che manca** |

#### ⛔ Il difetto di fondo, e va scritto senza attenuarlo

Il §3.3 di questo brief prometteva che *«i dodici job pgAgent si dichiarano da
soli, senza toccare `85_pgagent`»*. **La precondizione era vera per otto su
dodici**, e non è stata verificata: il registro è stato seminato coi nomi dei
**job pgAgent**, mentre `fn_run_and_log` riceve il nome che gli passano i
**wrapper `maintenance.proc_*_job`**.

⚠️ E non era un caso isolato: `chiusura_scadenze_daily` e
`sync_auth_user_expired_daily` chiamano SQL **diretto**, quindi nel giornale non
scrivono affatto — il loro nome pgAgent è irrilevante.

⇒ La regola vera, che ora è presidiata: **il codice del processo è la stringa che
arriva a `fn_run_and_log`**, non il nome del job.

⭐ **La correttiva non è rinominare: è il presidio.** Senza, il prossimo wrapper
romperebbe la stessa cosa in silenzio — ed è esattamente com'è arrivata fin qui.

#### ⚠️ Un debito NUOVO, creato da una decisione presa oggi

I due job pgAgent nuovi vivono in `85_pgagent`, fase che in CI è **`MARK_RAN`**:
segnata come eseguita **senza essere eseguita**. ⇒ Nasceranno su dbdev, ma su un
ambiente ricostruito da zero **non esisterebbero**, e nessun test lo direbbe.
Registrato come **R-11**.

> 🔴 **R-11, 2026-09-26: il primo danno misurato.** Il job `automations_lock_columns`
> chiamava anche `dbops.fn_run_automations_drop_lock_trg`, che cancellava per
> funzione i lock di colonna scritti a mano. Su dbdev, dove il job gira, sono
> spariti i lock di `config.iva_stati` e di `vendite.fatture.natura_doc_id`; su
> `zeroerp_ci`, dove non esiste, c'erano ancora. Per due giorni la differenza è
> stata letta al contrario («dev fuori modello»), perché la CI era considerata il
> metro. ⇒ **Finché `85_pgagent` è `MARK_RAN`, ogni automazione notturna ha su CI
> un pezzo di comportamento in meno che su dev**, e una divergenza dev/CI va letta
> prima di tutto come «che cosa gira solo di notte?». Proposta (decisa da Tid,
> D4 del brief sotto): lanciare almeno i **corpi** dei job una volta in CI dopo
> `ci_apply`, anche senza pgAgent. ✅ Aperto il 26-09:
> [brief-db-job-notturni-in-ci.md](brief-db-job-notturni-in-ci.md).
> Brief: [brief-db-lock-di-colonna-fuori-registro.md](brief-db-lock-di-colonna-fuori-registro.md).

---

### 12.11 🔴 R-12 — un job fermo da sei mesi, trovato guardando un presidio

⛔ **`apply_storicizza_weekly` fallisce ogni settimana dal 21 febbraio 2026.**

Il job pgAgent è **acceso e gira** — verificato su `pgagent.pga_joblog`, ultima
corsa 2026-09-05 — e muore sempre allo stesso punto:

```
ERRORE: la relazione "vendite.attivita_fatturabili_lotti" non esiste
```

⚠️ **Muore prima di scrivere**, quindi non lascia traccia: l'ultima riga in
`maintenance.job_run_log` per quel job è del **21 febbraio**. Un guasto che dura
da sei mesi e che nessun log racconta.

**La causa**: `config.storico_set_storicizza` elenca le tabelle a cui
`maintenance.proc_apply_storicizza_defaults` deve mettere il default su
`storicizza`. **Tre** di quelle righe puntano a tabelle che non esistono più:

| riga | come è arrivata |
| --- | --- |
| `vendite.attivita_fatturabili_lotti` | ⚠️ è anche nel **seed CSV** (riga 50) |
| `config.profili_reparto_aree` | inserita dal sync (`insert_manuale = f`) |
| `config.profili_reparto_azioni` | idem |

⛔ Il job muore **sulla prima**, quindi le altre due non si vedono nemmeno: si
scoprono solo cercandole.

#### ⭐ Come è saltato fuori, che è la parte che vale

Non da un allarme: **chiedendosi perché una riga di
`dbops.vw_run_senza_attore` non se ne andava.** La vista dice *«questo job non
si è ancora dichiarato»*; la risposta vera era *«questo job non gira da sei
mesi»*.

> È esattamente ciò per cui una vista di presidio esiste — non segnalare, ma
> **reggere una domanda**.

#### Le due facce del rimedio (non progettate qui)

1. **Il dato**: le tre righe morte vanno ritirate — una dal CSV di seed, due
   dalla tabella, e va guardato perché il sync inserisce senza mai pulire.
2. ⭐ **La forma**: `proc_apply_storicizza_defaults` dovrebbe **saltare** una
   tabella che non esiste più invece di morirci sopra. Un giro di manutenzione
   che si ferma alla prima riga stantia lascia indietro tutto il resto — ed è il
   motivo per cui un difetto da una riga è diventato un job fermo.

⚠️ **Conseguenza su DB-5**: finché quel job non riesce a girare,
`dbops.vw_run_senza_attore` **non può svuotarsi**, quindi il criterio del
backend («vi scrivo io quando la vista è vuota») resta insoddisfatto per una
ragione che non c'entra col cantiere. ⇒ Il vincolo di DB-5 è stato scritto in
modo da **non dipenderne**.

---

### 12.12 ⭐ Decisione 2026-09-05 — pgAgent sveglia, non lavora

> **La regola:** ⛔ **nessun processo di classe `DOMINIO` su pgAgent.**

⚠️ Non «gli applicativi via da pgAgent», che è vago. È il **perimetro emittente**
a fare la differenza, e la classe già lo dice: `sync_auth_user_expired_daily` è
applicativo in senso lato ma non ha un emittente, quindi non ha un perimetro da
rispettare e può restare.

⭐ E così formulata la regola è **presidiabile**: la classificazione smette di
essere una dichiarazione verificata a mano e diventa struttura.

#### Quanto costa oggi: un processo

| classe / canale | quanti |
| --- | --- |
| `DOMINIO` / `PGAGENT` | ⛔ **1** — `chiusura_scadenze_daily` |
| `MANUTENZIONE` / `PGAGENT` | 12 |
| `AMMINISTRAZIONE` / `PGAGENT` | 1 |

⇒ La decisione sposta **una cosa sola**. Il suo valore non è la migrazione: è la
regola che lascia dietro.

#### ⭐⭐ L'argomento è sperimentale, non teorico

**R-12 è la prova.** `apply_storicizza_weekly` è fallito per **sei mesi** senza
che nessuno lo sapesse: un job pgAgent che muore lascia traccia solo in
`pgagent.pga_joblog`, che nessuno guarda e che l'applicazione non vede. Un
lavoro di coda che fallisce lascia una riga con `ultimo_errore` e `tentativi`.

Più due ragioni strutturali:

* ⛔ **`85_pgagent` in CI è `MARK_RAN`**: ogni processo che vive lì è
  **invisibile ai test**. Accettabile per la manutenzione — idempotente, a basso
  rischio; non per qualcosa che tocca fatture.
* ⭐ **La coda porta l'identità nello scope.** Su pgAgent andrebbe
  re-implementato a mano il ciclo per emittente con `set_config`, cioè riscritto
  ciò che la coda fa già.

#### ⚠️ Ma sposta anche un rischio, e per questo l'ordine è cambiato

**Il silenzio si trasferisce, non sparisce.** Se il worker è giù i lavori si
accumulano **in silenzio** — la stessa forma di R-12, in un altro posto. E
misurato il 2026-09-05: la coda aveva **4 lavori in `ERRORE`** e **nessuna
vista** che li nominasse.

⇒ **Il presidio sulla coda viene PRIMA della migrazione**, non dopo. Senza,
staremmo comprando una visibilità che non abbiamo ancora costruito.

#### ⭐ E pgAgent resta lo scheduler

La domanda «chi sveglia il produttore» ha una risposta che va detta, o la regola
suona più assoluta di quello che è: **pgAgent resta**, ma su un processo di
dominio **sveglia e non lavora**. Un job che chiama `fn_accoda_lavoro` non tocca
nessun documento: se muore non ha fatto danni, e il lavoro vero resta tracciato
nella coda.

⚠️ L'alternativa — cron/systemd — avrebbe **lo stesso problema di visibilità**
di `85_pgagent`, solo spostato fuori dal repo.

#### L'ordine

| # | | |
| --- | --- | --- |
| 1 | `dbops.vw_coda_lavori_da_guardare` | ⭐ viene prima: è ciò che rende sicuro il resto |
| 2 | tipo di coda `CHIUSURA_SCADENZE` + processo su `CODA_AUTOMATICA` | |
| 3 | il job pgAgent smette di eseguire e **accoda** un lavoro per azienda | |
| 4 | la vista «nessun `DOMINIO` su pgAgent» | rende la regola verificabile |

---

### 12.13 ✅ Documentazione — che cosa è stato scritto

⛔ **Solo `manual/`**: le pagine sotto `tabelle/`, `funzioni/` e `views/` sono
auto-generate e non si toccano a mano.

**Dieci pagine nuove**

| Dove | Pagine |
| --- | --- |
| `dbops/manual/` | `processi` · `processi_bersagli` · `processi_identita` |
| `dbops/manual/` | le sei viste di presidio |
| `script/manual/` | `fn_crea_utente_tecnico` |

**Quattro pagine in piu' con DB-1** (2026-09-05, §12.14): `vw_processi_roster`,
`vw_coda_lavori_da_guardare`, `vw_processi_dominio_su_pgagent`,
`fn_accoda_chiusura_scadenze`.

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
`include-markdown` nella pagina auto-gen **solo se il file manuale esisteva
quando ha girato**. ⇒ Dopo aver scritto un `manual/` nuovo va rilanciato
`scripts/gen_db_docs.py`, o la pagina resta scritta e **non agganciata**.

---

### 12.14 ✅ DB-1 — fatto, applicato e collaudato (2026-09-05)

> Il piano di §12.12, eseguito nell'ordine che vi era scritto. **Sviluppo DB
> chiuso** per questo cantiere.

#### Che cosa è stato applicato

| changeSet | |
| --- | --- |
| `20260905-21` | `dbops.vw_coda_lavori_da_guardare` — ⭐ **prima di tutto il resto** |
| `20260905-22` | `dbops.vw_processi_dominio_su_pgagent` — la regola diventa verificabile |
| `20260905-23` | `dbops.vw_processi_roster` — il fatto che viveva in una stringa Python |
| `20260905-24` | `dbops.fn_accoda_chiusura_scadenze` — il produttore |
| `20260905-25` | `85_pgagent`: il job **accoda** invece di eseguire |
| CSV | `processi.csv` (canale `CODA_AUTOMATICA`) · `coda_lavori_tipi.csv` (tipo `CHIUSURA_SCADENZE`) |

**Misurato dopo l'apply:** `vw_processi_dominio_su_pgagent` = **0**, roster su due
aziende, il job pgAgent chiama `fn_accoda_chiusura_scadenze`, il tipo di coda
dichiara il suo processo.

#### ⛔ La trappola presa applicando: **due mirror sullo stesso CSV**

L'apply è fallito su un changeSet di **luglio**:

```
il valore nullo nella colonna "processo_codice" ... viola il vincolo non nullo
Migration failed for changeset 20260720-10-seed-dbops-coda-lavori-tipi-...
```

`coda_lavori_tipi.csv` aveva **due** mirror: quello di luglio, che dichiara
`processo_codice` come `type: SKIP` — e lo dichiara **a ragione**, perché la FK di
quella colonna punta a `dbops.processi`, seminato a settembre — e quello
ri-ancorato di settembre, che scrive tutte le colonne.

⛔ Una riga **nuova** viene però inserita dal mirror **più vecchio**, che per
disegno non sa scrivere quella colonna. E dal `20260904-42` la colonna è
`NOT NULL`.

> ⚠️ **E si vedeva solo su dev.** In CI il database nasce vuoto: il mirror gira a
> luglio, quando la colonna è ancora nullable, e settembre la completa. Su dev il
> `NOT NULL` c'è già quando il mirror ri-esegue. ⇒ È la **stessa divergenza
> CI-vs-DEV** descritta nel commento di quel file, presa dal verso opposto.

**Rimedio:** `20260720-10` **smette di caricare** (il suo `loadUpdateData` diventa
un `SELECT 1;` con la diagnosi a commento). Il file **non si cancella**: è già
applicato, e la sua riga in `databasechangelog` racconta che a luglio quei due
tipi sono stati seminati.

⛔ Aggiungere la colonna lì avrebbe **riaperto il problema di timeline** per cui
era in `SKIP`. ⭐ Così il dato ha **una sorgente sola e un'ancora sola**.

#### I test — quattro file nuovi, 23 asserzioni

| File | Che cosa fissa |
| --- | --- |
| `dbops/test-vw-processi-roster.sql` (7) | ⛔ i **quattro** livelli costruibili: ognuno basta da solo a far sparire la coppia |
| `dbops/test-vw-coda-lavori-da-guardare.sql` (7) | i tre guasti che compaiono e i quattro casi che **non** devono comparire |
| `dbops/test-vw-processi-dominio-su-pgagent.sql` (5) | vuota **e** si accende su un caso costruito |
| `dbops/test-fn-accoda-chiusura-scadenze.sql` (6) | ⭐ l'**isolamento per azienda**, con un guasto iniettato su una sola |

⚠️ **La quinta condizione del roster (`ef.attivo`) non è collaudata, ed è
dichiarato nel file.** Misurato: spegnere un emittente è vietato dal guard delle
figlie (EMITEST e PGTAPEF202 hanno contratti e documenti), e costruirne uno
usa-e-getta chiede soggetto, ruolo EF e un utente tecnico proprio — una fixture
più grande della cosa da provare. ⛔ Si dichiara invece di fingere: un
`CASE WHEN … skip()` avrebbe occupato un numero di test senza provare niente,
che **sembra copertura**.

#### ⚠️ Due asserzioni RIVOLTATE, non riparate

Nessuna delle due era un difetto del codice: erano **fotografie scritte come
regole**.

| Dove | Diceva | Dice |
| --- | --- | --- |
| `rls/test-rls-fatture-stampa-coda-write-guard.sql` t.6 | «il livello 2 è **vuoto**» | «non ha righe **NON_DICHIARATO**» |
| `dbops/test-processi-registro.sql` t.8 | «il seed copre tutti e **tre** i canali» | «ogni canale **dichiarato dal CHECK** è usato» |

* Il primo era **vero quando è stato scritto** — poi il `20260905-18` ha dato a
  `config.email_outbox` la colonna emittente ma non la policy, e la riga è
  ricomparsa **giusta**: un debito con un nome. ⛔ Insistere su «vuota» avrebbe
  reso il rosso una bugia. ⚠️ E si dichiara il rischio: dichiarare un debito
  **zittisce** quel test — per questo il censimento sta in
  `test-presidi-debito-dichiarato.sql`, dove il test 6 prova che un bersaglio
  nuovo e rotto esce `NON_DICHIARATO`.
* Il secondo aveva un **3 scritto a mano**: il giorno in cui il `CHECK` ha
  ammesso `CODA_AUTOMATICA` è andato rosso pur essendo tutto a posto. ⭐ Adesso
  l'elenco lecito si **legge dal vincolo**: aggiungere un canale senza seminarlo
  accende il test, aggiungerlo seminandolo no.

#### Baseline

`scripts/pgtap-baseline.sh` — 581 file: **19 rossi, tutti già noti**.
✅ Nessuna regressione. Tutti i guardrail verdi.

#### ⚠️ Che cosa resta aperto dopo DB-1

| | |
| --- | --- |
| 🟡 **La policy su `config.email_outbox`** | ✅ **decisa** il 2026-09-05 (solo super admin), ⛔ **non scrivibile ancora**: abilitare la RLS oggi fermerebbe l'invio. §12.15 |
| 🔴 **R-12** | `apply_storicizza_weekly` e le tre righe morte in `config.storico_set_storicizza` (§12.11) |
| ⚙️ BE | `processi_repository.roster_processo` può diventare un `SELECT` su `dbops.vw_processi_roster`. Finché restano due copie, sono due copie |
| ⚠️ R-11 | `85_pgagent` è `MARK_RAN` in CI: su un ambiente ricostruito da zero il job resterebbe alla forma vecchia — **eseguirebbe invece di accodare** — e nessun test lo direbbe |

⚠️ **Un'osservazione dal collaudo, non un residuo**:
`vw_coda_lavori_da_guardare` espone `scope` (chi ha chiesto il lavoro) ma non
`payload` (di che cosa si trattava). Per la chiusura scadenze non manca niente
— lo scope nomina già l'azienda — ma per un tipo di lavoro futuro potrebbe.
Da valutare quando servirà, non prima.

---

---

### 12.15 ⛔ `config.email_outbox` — decisa, e volutamente NON scritta (2026-09-05)

#### ✅ La decisione (Tid)

> **Le email di ambito `SISTEMA` le legge solo il super admin.**

Sono le email che **non appartengono a nessuna azienda** — reset password, alert
— e il loro contenuto vale quanto una credenziale. ⇒ Non c'è un operatore che
abbia titolo per leggerle: o si è super admin, o no.

Le altre seguono la regola di sempre: l'emittente della riga dev'essere nella
whitelist di chi guarda (`script.fn_scope_ef_whitelist`, la stessa della
famiglia).

#### 🔴 Ma la policy non si scrive oggi, e il motivo è **misurato**

`send_pending_emails` è un **management command**, non una richiesta HTTP. Le
GUC `app.current_user_id` e `app.ruolo_applicativo` le imposta l'autenticazione
JWT (`jwt_audit_authentication`): in un command **non ci sono**. E il ruolo di
connessione `zeroerp_app` **non ha `BYPASSRLS`** — verificato: ce l'hanno solo
`postgres` e `zeroerp_batch_fatturazione`, che è in ritiro (R-2).

⇒ Abilitando la row level security oggi, chi spedisce vedrebbe **zero righe**.

> ⛔ **E non se ne accorgerebbe nessuno.** Una coda vuota è indistinguibile da
> «niente da fare»: il command girerebbe verde, il giornale direbbe «0
> processate», e le email di reset password semplicemente **non partirebbero**.
> ⭐ È la forma esatta di R-12 — un guasto che si manifesta come **assenza** — e
> sarebbe stato introdotto **da noi**, dentro il cantiere che esiste per
> toglierla.

⚠️ Il commento nel codice del command lo dice già, da prima di questa analisi:
*«questo processo è di DOMINIO e non ha un perimetro … gli si dà l'ATTORE e
basta»*. Con DB-3 la colonna adesso c'è; **chi la usa, no**.

#### La forma, già decisa e pronta

```sql
USING (
    current_setting('app.ruolo_applicativo', true) = 'OPERATORE'
    AND CASE
          WHEN ambito = 'SISTEMA'
            THEN script.fn_is_super_admin(<utente corrente>)
          ELSE script.fn_scope_ef_whitelist(<utente corrente>, emittente_fiscale_id)
        END
)
```

⇒ Scritta il 2026-09-05 (`20260905-32`), con la **row level security ancora
spenta** — e il presidio lo dice invece di tacere, perché dal `-26` conta una
policy solo se è **in vigore**.

⇒ Scritta il 2026-09-05 (`20260905-32`), con la **row level security ancora
spenta** — e il presidio lo dice invece di tacere, perché dal `-26` conta una
policy solo se è **in vigore**.

#### ⛔ Il ramo della macchina è uscito da questa policy (`20260905-33`)

La prima stesura dava lettura, sul ramo `SISTEMA`, anche all'identità tecnica di
`send_pending_emails`. Il ragionamento era giusto — *portare è leggere* — ma
applicato alla **tabella sbagliata**.

⭐ Misurato sui due soli percorsi che potevano smentirlo:

* **inviare una bozza** (`EmailOutboxSendView` → `confirm_and_send`) gira **dentro
  la richiesta HTTP**, con una persona vera: crea l'`email_log`, spedisce,
  aggiorna la bozza. Nessuna coda, nessuna identità tecnica;
* **il ritentativo** del command (`retry_log_entry`) tocca **solo**
  `config.email_log` — non scrive mai la riga di outbox.

⛔ E il problema non è che il permesso sia «inutile»: è che **non si può
collaudare**. Non «non ancora testato» — *non esercitabile*, perché nessun codice
ci arriva. Un ramo così si scopre sbagliato il giorno in cui serve.

⚠️ E in più afferma una cosa **falsa dentro una regola di sicurezza** — «chi
spedisce legge le bozze» — cioè lo stesso errore del bersaglio dichiarato che
puntava alla tabella sbagliata, ma in un posto che si legge quando si indaga un
incidente.

⇒ Il ramo va sulla policy di `config.email_log`, dove quel processo legge
davvero e dove un collaudo funzionale lo esercita.

⭐ **`script.fn_scope_identita_processo` (`20260905-31`) resta**, ed è la
distinzione che conta: ciò che non si poteva collaudare era il **ramo** dentro
una policy che nessun codice raggiunge — non la funzione, che un test esercita
per davvero, livello per livello. Nasce per togliere due copie dello stesso
`EXISTS` da `USING` e `WITH CHECK`, e la regola è **più stretta** di quella che
sostituisce: guarda tutti e cinque i livelli dell'identità invece del solo
legame. Un'identità **revocata** avrebbe continuato a leggere i reset password —
`db/pgtap/script/test-fn-scope-identita-processo.sql` test 6 costruisce quel caso.

⚠️ La simmetria fra le due tabelle è tentante (stesso tipo di contenuto), ma due
tabelle con **lettori diversi** si somigliano per caso: `email_log` la apre una
macchina, `email_outbox` solo delle persone.

#### 🔴 E c'è un fatto in più, trovato dal backend: **sono due tabelle**

`send_pending_emails` seleziona da **`config.email_log`**. `config.email_outbox`
non compare nel giro di invio: è l'area delle **bozze**, che scrive e legge
l'interfaccia.

| | `config.email_outbox` | `config.email_log` |
| --- | --- | --- |
| a che serve | bozze, scritte dall'UI | il registro degli invii |
| chi la legge in automatico | ⛔ nessuno | ✅ `send_pending_emails` |
| `emittente_fiscale_id` | ✅ c'è (DB-3, `20260905-18`) | ⛔ **non c'è** |

⛔ **Quindi il bersaglio dichiarato in `dbops.processi_bersagli` è sbagliato.**
Dice che `send_pending_emails` tocca `email_outbox`, e quel processo non la apre
mai. ⇒ Il presidio di livello 2 sorveglia la tabella **sbagliata** per quel
processo, e la tabella che il processo tocca davvero **non è sorvegliata da
nessuno** — non compare nemmeno nel livello 1, perché non è dichiarata.

⭐ **Nessuno dei due lati poteva vederlo da solo**: noi guardavamo il registro,
loro il codice. È il caso che dà ragione al censimento — e insieme il caso che
mostra il suo limite: un bersaglio dichiarato è un'**affermazione**, e il
presidio verifica che quella tabella sia difesa, non che sia **la tabella
giusta**.

⚠️ Il lavoro di DB-3 non è sprecato: `email_outbox` ha comunque bisogno del
perimetro, perché le bozze sono di un'azienda. È il **censimento** ad aver
sbagliato bersaglio, non la colonna.

#### ✅ La decisione che mancava (2026-09-05, Tid)

> **Sì: un utente tecnico può leggere le email di ambito `SISTEMA`.**

⇒ Il quadro è completo: le legge **il super admin** fra le persone, e
**l'identità tecnica del processo che le spedisce** fra le macchine. Nel
database *portare è leggere* — non esiste un modo di spedire una riga senza
vederla — quindi senza questa autorizzazione la posta di sistema non partirebbe.

⚙️ Da qui discende, e non è una scelta: **la policy nomina il processo**. L'altra
strada è chiusa dal database stesso — `fn_crea_utente_tecnico` rifiuta qualunque
profilo non `AD_HOC` (`E_UTENTE_TECNICO_PROFILO_VIETATO`), e le due identità di
`send_pending_emails` hanno `fn_is_super_admin = false` e **nessun profilo di
accesso legato**. Verificato misurando.

---

#### 🔴 E il blocco si è SPOSTATO, non è sparito

⚠️ Con la scoperta delle due tabelle sembrava che `config.email_outbox` fosse
sbloccata: chi spedisce legge `email_log`, quindi accendere la RLS sull'outbox
non lo tocca. ⛔ **Non è così**, e il motivo è nel codice che ci **scrive**:

```python
# apps/core/api/email_views.py:84
ambito=(payload.get("ambito") or "SISTEMA").strip(),
```

L'API mette `SISTEMA` **per default** quando il client non manda l'ambito — e il
frontend non lo manda. In più l'`INSERT` di `create_outbox` **non valorizza
`emittente_fiscale_id`**.

⇒ Con la policy accesa oggi:

| | |
| --- | --- |
| bozza senza ambito esplicito → `SISTEMA` | ⛔ un operatore non la può più creare né vedere: è roba da super admin |
| bozza con un ambito vero | ⛔ viola `chk_email_outbox_ambito_emittente`: la colonna emittente non viene popolata |

**La funzione bozze si romperebbe in tutte e due le direzioni.**

> ⛔ **Il difetto vero, e vale oltre questo caso:** `SISTEMA` in questa tabella
> oggi significa *«nessuno ha detto quale ambito»*, non *«email di sistema»*.
> ⭐ Un valore di **default** non può fare da cancello di sicurezza: la policy
> classificherebbe come segreto di sistema ogni bozza a cui un client ha
> dimenticato un campo.
>
> ⇒ Prima della policy, `ambito` deve diventare un'**affermazione**.

---

#### ✅ Intanto il censimento smette di mentire

`config.email_log` è ora dichiarata come bersaglio di `send_pending_emails`
(riga 51 del CSV, `debito_dichiarato = true`).

⛔ Prima il registro diceva che quel processo tocca `email_outbox` — che non apre
mai. Il presidio sorvegliava **con sicurezza la tabella sbagliata**, e quella
vera non compariva da nessuna parte.

⭐ Adesso il livello 1 la nomina — *«percorso verso l'emittente non
dichiarato»*, `DEBITO_DICHIARATO` — e gli allarmi restano **zero**. Il debito è
visibile, ha un nome, e aspetta il pezzo del backend.

⚠️ Ne segue che anche `test-presidi-debito-dichiarato` test 4 passa da «il
livello 1 è **vuoto**» a «nessuna riga **NON_DICHIARATO**»: la terza volta che
questa correzione si paga, e stavolta perché un presidio ha cominciato a dire il
vero.

🔵 **Resta una sotto-domanda**: `config.email_outbox` deve **restare** un
bersaglio dichiarato? Un bersaglio afferma *«un processo automatico tocca questa
tabella»*, e per le bozze non è vero — le scrive l'interfaccia. La riga 30 non è
stata tolta: è una decisione, non una pulizia.

#### ✅ La policy è SCRITTA — changeSet `20260905-31` (2026-09-05)

`rls_email_outbox_ambito` su `config.email_outbox`, `FOR ALL`, con il ramo scelto
sull'**etichetta**: `SISTEMA` → super admin **oppure** un'identità tecnica attiva
di `send_pending_emails` (letta da `dbops.processi_identita`, così una revoca ha
effetto lo stesso giorno); tutto il resto → `script.fn_scope_ef_whitelist` sulla
colonna emittente, che fuori da `SISTEMA` il `CHECK` garantisce non nulla.

🔴 **La `ROW LEVEL SECURITY` resta SPENTA, e non è una dimenticanza.** Restano due
gesti, che sono lo stesso gesto:

| | |
| --- | --- |
| `ALTER TABLE config.email_outbox ENABLE ROW LEVEL SECURITY;` | una riga |
| il **write-guard** di famiglia | ⛔ è un **trigger**: morde anche con la RLS spenta, quindi montarlo oggi fermerebbe la creazione delle bozze subito |

⛔ **E non è la scorciatoia che era stata rifiutata.** Quella era scartata perché
lasciava la tabella aperta *con il presidio che diceva di no*; dal `20260905-26`
la vista chiede `relrowsecurity`, quindi il presidio **non va a zero** e dirà
*«la policy c'è ma la ROW LEVEL SECURITY non è attiva sulla tabella, e manca il
write-guard»*. Lo stato in cui siamo, detto ad alta voce.

⚠️ **Fatto datato 2026-09-05**: le righe di `config.email_outbox` sono **6, tutte
`SISTEMA`** — cioè la fotografia del difetto che blocca l'accensione, non un
argomento per accenderla.

Verifica: `db/pgtap/rls/test-rls-email-outbox-ambito.sql` (5 test — forma della
decisione, non collaudo funzionale: con la RLS spenta la policy non filtra).

#### Il prerequisito, ed è del backend

| | |
| --- | --- |
| **Chi** | backend |
| **Che cosa** | `send_pending_emails` deve **dire chi è** anche al database, non solo al giornale: impostare `app.current_user_id` / `app.ruolo_applicativo` con l'identità tecnica del processo — che **esiste già** (`send_pending_emails@<azienda>`, vedi `dbops.vw_processi_roster`) |
| **E per le `SISTEMA`** | serve un lettore dichiarato: o l'identità tecnica ha il profilo super admin, o la policy nomina esplicitamente il processo. ⚠️ **È una decisione di sicurezza**, non un dettaglio implementativo: chi spedisce un reset password lo può leggere |
| **Come si vede che è chiuso** | `dbops.vw_processi_dominio_senza_difesa` → **vuota**, con la RLS **attiva** su `config.email_outbox` |

---

### 12.16 ❓ Il job pgAgent `chiusura_scadenze_daily` va ritirato?

> ⛔ **No. È diventato la sveglia, e senza sveglia non si chiude più niente.**

Prima quel job **eseguiva** la chiusura. Adesso chiama
`dbops.fn_accoda_chiusura_scadenze()` e basta: mette in coda un lavoro per
azienda e non tocca nessun documento.

⇒ Ritirarlo vorrebbe dire che **nessuno accoda**: la coda resterebbe vuota, il
worker non avrebbe niente da drenare, e le scadenze non si chiuderebbero mai
più — in silenzio, perché una coda vuota non è un errore.

⭐ **La regola presa in §12.12 dice «nessun processo di DOMINIO ESEGUE dentro
pgAgent», non «pgAgent va via».** Un job che accoda, se muore, non ha fatto
danni; e il lavoro vero resta tracciato nella coda, che sa dire se è fallito —
cosa che pgAgent non sa fare.

⚠️ Ed è il motivo per cui il registro ha un canale nuovo: `CODA_AUTOMATICA`
descrive **il processo** — che passa dalla coda — non chi suona la sveglia.
`dbops.vw_processi_dominio_su_pgagent` è a **zero** proprio perché guarda il
processo, non il job.

**Che cosa andrebbe ritirato, invece:** niente, oggi. ⚠️ L'unico residuo è R-11 —
`85_pgagent` è `MARK_RAN` in CI, quindi su un ambiente ricostruito da zero il
job resterebbe alla **forma vecchia** (eseguirebbe invece di accodare) e nessun
test lo direbbe.

---

---

### 12.17 🏁 Stato finale — il brief è chiuso per il DB? (2026-09-05)

> ✅ **Sì per tutto ciò che il brief PIANIFICAVA.** ⚠️ **No per tutto**: restano
> due cose, ed entrambe sono cose che il brief ha fatto **emergere**, non
> progettato.

#### ✅ Fatto e applicato — il piano, per intero

Fasi 0–6 · DB-1 … DB-8 · R-8 · R-10 · R-E · R-F, più l'irrigidimento del
presidio (`20260905-26`), il commento restituito (`-27`), R-12 (`-28`/`-29`), il
ri-ancoraggio del roster (`-30`) e la policy sulle email (`-31` … `-33`).
**Baseline pgTAP: nessuna regressione.**

#### I sei presidi, misurati dopo l'ultimo apply

| Presidio | | |
| --- | --- | --- |
| `vw_processi_dominio_senza_emittente` | **1** | 🟡 `email_log`, `DEBITO_DICHIARATO` — righe `NON_DICHIARATO`: **0** (rimisurato 2026-09-05 sera, dopo la riga 51 del censimento) |
| `vw_processi_dominio_su_pgagent` | **0** | ✅ |
| `vw_processi_dominio_senza_identita` | **0** | ✅ |
| `vw_emittenti_non_serviti` | **0** | ✅ |
| `vw_processi_dominio_senza_difesa` | **1** | 🟡 `email_outbox`, `DEBITO_DICHIARATO` |
| `vw_processi_che_bypassano` | **1** | ⚙️ R-2, provisioning — non è DB |
| `vw_run_senza_attore` | **4** | ⚠️ residuo **storico congelato**: dal `20260905-16` un run senza attore non può più nascere |
| `vw_coda_lavori_da_guardare` | **0** | ✅ i quattro lavori falliti da 32–45 giorni sono stati **archiviati** (rimisurato 2026-09-05 sera) |

#### ⚠️ Che cosa resta sul DB, e non è poco

| | Che cos'è | Chi |
| --- | --- | --- |
| 🟢 **R-12** | ✅ **ripreso e risolto** il 2026-09-05 nel suo brief — [brief-db-storicizzazione-bersagli-spariti.md](brief-db-storicizzazione-bersagli-spariti.md) §4: la sincronizzazione impara a **potare** (`20260905-28`) e il consumatore a **sopravvivere a una riga stantia** (`-29`). 🔵 Resta aperta la domanda larga: `fn_run_and_log` scrive il fallimento e il `RAISE` lo butta via — **nessun job può lasciare una riga rossa** | DB |
| 🟡 **Policy sulle email** | decisa, **scritta e applicata** (`20260905-32`, ripulita dal `-33`) — ⛔ ma con la **RLS spenta**: accenderla oggi romperebbe le bozze, perché l'API scrive `ambito = 'SISTEMA'` per default e non valorizza l'emittente. ✅ Il censimento nel frattempo è stato corretto: il bersaglio è `config.email_log`, che aspetta la sua colonna | DB, **dopo** il BE |

⭐ **E non è un caso che restino queste due.** Sono entrambe la stessa forma di
guasto — quella che il cantiere esisteva per rendere visibile: **un lavoro che
non viene fatto e non lo dice a nessuno.** R-12 è il caso già successo; la
policy di `email_outbox` è il caso che stavamo per introdurre.

⇒ Il cantiere non le chiude. Le ha rese **visibili e nominate**, che era il suo
scopo: le prime quattro righe della tabella qui sopra sono zero, e le altre
quattro hanno un nome, un motivo e un padrone.

#### ✅ I quattro lavori falliti nella coda — archiviati

`FATTURAZIONE_GIRO` ×2 e `FATTURAZIONE_NUMERA` ×2, fermi da **32 e 45 giorni**,
tentativi esauriti. Non erano un residuo di questo cantiere — erano lì prima,
**invisibili**. Guardati e archiviati: `vw_coda_lavori_da_guardare` è tornata
vuota (rimisurato il 2026-09-05 in serata), quindi da domani la vista distingue
il nuovo dal vecchio invece di mostrare sempre gli stessi quattro.

---

---

### 12.18 ✅ Decisioni del 2026-09-05, sera — le email e il ramo della macchina

> Registro compatto: **che cosa si è deciso**, e che cosa ne è seguito. Le
> conseguenze non sono decisioni, e tenerle separate serve a non doverle
> ridiscutere.

| | Decisione | Chi |
| --- | --- | --- |
| **D1** | ✅ **Un utente tecnico può leggere le email di ambito `SISTEMA`.** Nel database **portare è leggere**: non esiste un modo di spedire una riga senza vederla, e senza questa autorizzazione la posta di sistema non partirebbe — in silenzio, perché una coda vuota è identica a «niente da fare» | Tid |
| **D2** | ⛔ **Il ramo della macchina NON sta sulla policy di `config.email_outbox`.** Misurato: quel processo legge `config.email_log`, e l'outbox non la apre mai — né inviando una bozza (gira dentro la richiesta HTTP) né ritentando | DB, condivisa |
| **D3** | ⛔ **La `ROW LEVEL SECURITY` resta spenta** finché il backend non rende `ambito` un'**affermazione** e non valorizza l'emittente | Tid |
| **D4** | ⚙️ **Forma forward-only anche qui**: `-32` è già applicato, quindi non si corregge sul posto — si scrive `-33`. Il `-32` diventa copia storica | standard di progetto |
| **D6** | ✅ **La RLS su `config.email_outbox` si accende** (`20260905-37`), write-guard compreso — accettando che le bozze restino inutilizzabili finché il backend non toglie il default di `ambito` | Tid |
| **D5** | ⛔ **`config.email_outbox` NON è più un bersaglio dichiarato** (`20260905-34`): le bozze le scrive **l'interfaccia**, non un processo automatico. Una riga di `processi_bersagli` afferma *«questo processo tocca questa tabella»*, e quella era **falsa** | Tid |

#### Le conseguenze, che non sono scelte

| | |
| --- | --- |
| **da D1** | la policy **nomina un processo** — l'altra strada è chiusa dal DB stesso: `fn_crea_utente_tecnico` rifiuta qualunque profilo non `AD_HOC` |
| **da D1** | la domanda diventa una **funzione** (`script.fn_scope_identita_processo`, `-31`) invece di un `EXISTS` copiato in `USING` e `WITH CHECK`. ⭐ E più **stretta**: cinque livelli invece del solo legame — un'identità **revocata** avrebbe continuato a leggere i reset password |
| **da D2** | la funzione **resta** e aspetta il suo consumatore: la policy di `config.email_log`. ⚠️ Non è codice morto — ciò che non si poteva collaudare era il **ramo dentro una policy irraggiungibile**, non la funzione, che un test esercita livello per livello |
| **da D2** | i test 4 e 5 di `test-rls-email-outbox-ambito` si **spostano**, non spariscono: presidiavano il ramo, e il ramo è altrove. ⭐ Il rischio della rinomina resta coperto da `test-fn-scope-identita-processo` |

#### ⭐ Il criterio che ha deciso D2, e vale oltre questo caso

> ⛔ **Un permesso che nessun codice esercita non è «inutile»: è
> *incollaudabile*.** Non «non ancora testato» — non raggiungibile. Un ramo così
> si scopre sbagliato **il giorno in cui serve**, che è troppo tardi.

⚠️ E c'è un secondo motivo che pesa quanto il primo: quel ramo **affermava una
cosa falsa dentro una regola di sicurezza** — *«chi spedisce legge le bozze»*. È
lo stesso errore del bersaglio dichiarato che puntava alla tabella sbagliata, ma
in un posto che si legge **quando si indaga un incidente**.

⚠️ La simmetria fra le due tabelle era tentante — stesso tipo di contenuto — ma
due tabelle con **lettori diversi** si somigliano per caso.

#### ⚠️ Che cosa comporta D5, e va detto invece che scoperto

Con la riga 30 fuori, `dbops.vw_processi_dominio_senza_difesa` va a **ZERO** — e
la row level security su `config.email_outbox` è ancora **spenta**.

⛔ Non è un debito messo sotto il tappeto: è un debito che **non apparteneva a
quel presidio**. La domanda che fa è *«i processi automatici rispettano il
perimetro emittente?»*, non *«ogni tabella del database è difesa?»*. Rispondere
alla seconda con lo strumento della prima significa tenere una riga **falsa** per
non perdere una spia — e una riga falsa in un censimento è esattamente il difetto
che ci è costato due giorni.

⭐ Il debito resta scritto dove è vero: qui in §12.15, e soprattutto nella **riga
51** — `config.email_log`, il bersaglio vero, che il livello 1 nomina come
`DEBITO_DICHIARATO` finché non ha la colonna emittente. *Quello* sì è un debito
di processo.

⚠️ E ne segue una correzione al test: `test-presidi-debito-dichiarato` test 5
chiedeva che `email_outbox` comparisse nel livello 2 — cioè **si appoggiava a un
debito reale**. È la quarta volta che questa lezione si paga. Ora il caso lo
**costruisce**, simmetrico al test 6 che costruisce quello opposto.

#### ✅ D6 — la RLS si accende (`20260905-37`)

**Decisione di Tid, 2026-09-05 sera.** Verificato sui dati: le 6 righe a bordo
sono tutte `SISTEMA` senza emittente — nate quando `SISTEMA` voleva dire
*«nessuno ha detto»* — e sono tutte **`CANCELLED`, di prova** («Test», «Test
smoke»), dell'utente 1. ⇒ Accendere non nasconde niente che qualcuno stia usando.

Il changeSet accende la row level security **e** monta il write-guard: sono lo
stesso gesto, perché un guard è un trigger e morde anche con la RLS spenta.

> 🔴 **Ma il blocco del write path non è stato tolto, e va detto.** Misurato
> stasera sul codice: `email_views.py:84` scrive ancora
> `ambito=(payload.get("ambito") or "SISTEMA")` — il default c'è — e
> `create_outbox` **non valorizza** `emittente_fiscale_id`.
>
> ⇒ Da quando `-37` è applicato, **un operatore non può più creare una bozza**:
> quella `SISTEMA` la respinge il `WITH CHECK` della policy, quella con un ambito
> vero violerebbe `chk_email_outbox_ambito_emittente` — e quest'ultimo caso
> fallisce **già oggi**, senza RLS (verificato eseguendolo).

⚠️ **Il costo è delimitato, ed è la ragione per cui si accende lo stesso**: la
funzione bozze oggi non la usa nessuno, e non siamo in produzione. ⭐ Si sblocca
con **una riga** di Python — punti 1 e 2 della lista al backend.

⛔ Chi incontrerà quell'errore ha trovato questo, non un difetto nuovo: sta
scritto nell'intestazione del changeSet, che è dove lo si cerca.

⭐ **E il livello 2 va a zero per il motivo giusto**: non perché la riga di
censimento sia stata tolta (quella è D5), ma perché da qui la tabella è
**davvero difesa** — misurato in transazione, il presidio esce vuoto.

#### 🔵 Che cosa resta da decidere

| | |
| --- | --- |
| 🔵 | `fn_run_and_log` scrive il fallimento e il `RAISE` lo butta via ⇒ **nessuno dei dodici job può lasciare una riga rossa**. Tre strade, tutte con conseguenze sui dodici insieme (brief storicizzazione §4) |

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
