## 📘 Documentazione Concettuale – Tabella `dbops.fk_index_policy`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — gli schemi che la politica governa
>
> Approfondimento viste:
>
> * [dbops.vw_fk_senza_indice](/dbzero/dbops/views/vw_fk_senza_indice) — il fatto: le chiavi esterne scoperte, con la loro decisione
> * [dbops.vw_fk_da_decidere](/dbzero/dbops/views/vw_fk_da_decidere) — il presidio: le chiavi esterne da decidere, le decisioni non applicate, le righe fuori ambito
> * [dbops.vw_indici_ridondanti_prefisso](/dbzero/dbops/views/vw_indici_ridondanti_prefisso) — dice quali righe tengono in vita un indice ridondante
>
> Approfondimento funzioni:
>
> * [dbops.apply_fk_index_policy](/dbzero/dbops/funzioni/apply_fk_index_policy) — la procedura che esegue le decisioni
> * [dbops.fn_populate_fk_index_policy](/dbzero/dbops/funzioni/fn_populate_fk_index_policy) — la scoperta: registra le chiavi esterne scoperte come da decidere
> * [dbops.fn_indici_schema_nell_ambito](/dbzero/dbops/funzioni/fn_indici_schema_nell_ambito) — il perimetro della politica, per schema
>
> Guide:
>
> * [Automazione DB — policy indici FK](/guide/automazione-db#6-policy-indici-fk) — il flusso completo
> * [Linee guida SQL — automazione indici FK](/linee-guida-sql#87-automazione-indici-fk) — le regole per chi scrive un changeSet

---

### 🎯 Scopo Principale

La politica degli indici sulle chiavi esterne: una riga per vincolo, con la **decisione** su un
indice dedicato e il comando che lo crea. È l'unico posto da cui gli indici governati delle chiavi
esterne nascono e muoiono.

Chi crea o toglie a mano un indice governato da qui se lo ritrova disfatto al `migrate`
successivo: `dbops.apply_fk_index_policy` gira a ogni migrazione e nel job settimanale, e
riporta il database a ciò che le decisioni dicono.

---

### Tre valori: chi ha deciso, e che cosa

La chiave è il vincolo di chiave esterna (schema, tabella, nome del vincolo). `decisione` dice a
che punto è la riga:

| `decisione` | Chi la scrive | Che cosa fa l'apply |
| --- | --- | --- |
| `DA_DECIDERE` | la scoperta, ed è il default | niente: non crea e non toglie |
| `CON_INDICE` | solo il seed | crea l'indice, **se la chiave esterna è ancora scoperta**: una chiave esterna già servita da un indice più largo non ne riceve uno dedicato |
| `SENZA_INDICE` | solo il seed | toglie l'indice, **se togliere quell'indice è innocuo**: un indice che regge un vincolo non si tocca |

Le due condizioni sono le guardie della procedura, descritte nella sua scheda.

⭐ **Un flag non sapeva dire «nessuno ha deciso».** Con tre valori la differenza fra una chiave
esterna nuova e una decisa sta nella riga: la scoperta scrive solo `DA_DECIDERE`, le decisioni le
scrive solo il seed, e il presidio `dbops.vw_fk_da_decidere` mostra ciò che resta da decidere. Una
chiave esterna `SENZA_INDICE` resta scoperta per scelta, e il fatto continua a mostrarla in
`dbops.vw_fk_senza_indice`.

`motivo` è il perché della decisione. È facoltativo, ma mai una stringa vuota: il vincolo
`chk_fk_index_policy_motivo_non_vuoto` la rifiuta.

---

### ⭐ Una decisione è reversibile

Il comando resta scritto su ogni riga, anche `SENZA_INDICE` e `DA_DECIDERE`. Se un giorno l'indice
più largo che rendeva superfluo quello dedicato sparisse, basta portare la riga a `CON_INDICE` e
l'indice torna, con lo stesso nome di prima. Con `SENZA_INDICE` la politica fa anche da guardia
permanente: un indice ricreato a mano fuori dalle migrazioni viene ritolto.

---

### ⛔ `dll_command` è un comando, non una nota

La procedura esegue `dll_command` alla lettera quando deve creare l'indice. Il **nome**
dell'indice, che serve per toglierlo, sta in `indice_nome`: una colonna generata dal comando, con la
stessa grammatica del vincolo `chk_fk_index_policy_dll_command_forma`. Il vincolo pretende la forma
esatta: creazione dell'indice «se non esiste», col nome scritto senza virgolette e seguito dalla
clausola sulla tabella. Una riga sbagliata non entra nemmeno, e il nome c'è sempre.

Il nome si legge in un posto solo: la procedura e `dbops.vw_indici_ridondanti_prefisso` confrontano
`indice_nome` per uguaglianza, e non lo ricavano ciascuna a modo suo dal testo del comando.

⚠️ Il comando deve nominare l'indice **che esiste**, non uno inventato. Una riga `SENZA_INDICE` col
nome sbagliato non toglie niente, perché cerca un indice che non c'è.

⚠️ Il corollario: una riga `SENZA_INDICE` il cui comando ha il nome canonico toglie anche l'indice
con quel nome nato nel changeSet della tabella. La guardia lo impedisce solo se l'indice regge un
vincolo.

---

### Una chiave esterna già coperta non ha bisogno di una riga

La politica governa gli indici che crea lei. Una chiave esterna coperta dall'indice nato nel
changeSet della sua tabella, o da un indice più largo, non entra fra le scoperte e non riceve una
riga dalla scoperta: non c'è niente da decidere.

Una riga può invece nominare una chiave esterna che sul database non c'è ancora. Su un database
da zero le chiavi esterne verso `django.auth_user` nascono dopo Liquibase, e le loro righe sono
decisioni del seed, non righe morte: per questo la scoperta non cancella mai una riga decisa.

---

### Il perimetro è lo schema

La politica governa le chiavi esterne degli schemi che compaiono in `dbops.automation_scope`,
qualunque sia il filtro per tabella: lo decide `dbops.fn_indici_schema_nell_ambito`, che leggono le
viste e la procedura. Una riga su uno schema fuori dal perimetro non fa niente, e il presidio la
mostra come `FUORI_AMBITO`.

---

### Come si modifica

Le decisioni stanno in **un** CSV, `80_data/sql/dbops/fk_index_policy.csv`, caricato da un solo
mirror con aggiornamento sulla chiave del vincolo, a ogni migrate. Una decisione nuova o cambiata si
scrive lì: la riga aggiorna o inserisce. Nel CSV un `motivo` assente si scrive col segnaposto
`NULL`, perché una cella vuota entrerebbe come stringa vuota.

⚠️ Il caricamento aggiorna e aggiunge, non cancella: togliere una riga dal CSV non toglie la
decisione dai database in cui è già stata caricata. Una riga che c'è solo sul database di una
macchina resta com'è.

⛔ Non si scrive una decisione con un `INSERT` o un `UPDATE` in un changeSet, né con un secondo CSV:
sarebbe una seconda sorgente, che diverge dal file in silenzio. E non si ricostruisce la logica
della procedura con uno script scritto a mano: la procedura ha le due guardie, una copia
artigianale no.

---

### Test

* `db/pgtap/dbops/test-fk-index-policy-decisione-v1.sql` — il vocabolario della decisione, il
  motivo mai vuoto, il nome generato dal comando; la scoperta, il fatto e il presidio sui tre valori;
  l'apply che non tocca una `DA_DECIDERE`, toglie una `SENZA_INDICE`, crea una `CON_INDICE`; la
  scoperta che non tocca una riga decisa senza chiave esterna; le righe fuori ambito.
* `db/pgtap/dbops/test-indici-letture-trasversali-v1.sql` — una riga decisa `CON_INDICE` col comando
  che nomina l'indice canonico, e l'indice che ne è uscito.
* `db/pgtap/dbops/test-marcatori-automazione-senza-esecutore-v1.sql` (test 14) — la tabella non
  ha `tx_id`, `data_update` né `user_update`: un catalogo che scrive solo la migrazione non li porta.

---

### Note di migrazione

* 2026-01-16 — nascono il popolamento, il seed e il job settimanale della policy; una prima
  bonifica toglie gli indici FK già coperti da una UNIQUE.
* 2026-07-27 — `dll_command` diventa obbligatoria e prende il vincolo di forma: la pagina di
  documentazione di allora mostrava un esempio con una descrizione in italiano nel comando, e chi
  l'avesse seguito avrebbe rotto il deploy. Lo stesso giorno la procedura prende le due guardie e
  la copertura delle viste passa al prefisso.
* 2026-11-08 — perde `data_update` e `user_update`, che nessuno scriveva: la scrivono la
  migrazione e il popolamento a runtime, che però inserisce soltanto e non aggiorna mai (regola
  dello scrittore, `automazione-db.md` §1.1; `brief-db-revisione-dbops`, giro 7-bis). Esce dal
  registro del debito di `test-user-update-not-null-v1`.
* 2026-11-09 — il flag `consentito` lascia il posto a `decisione`, con `motivo` e il nome generato
  `indice_nome`; escono `consentito` e `generated_by_script` (`20261110-42`, `-53`;
  brief-db-revisione-dbops, giro 10d). Il flag aveva default vero, la scoperta scriveva falso, e una
  chiave esterna a falso usciva da ogni presidio: le chiavi esterne nuove sparivano tutte. Alla
  conversione ogni riga diventa `DA_DECIDERE`, e il mirror del CSV unico riscrive le decisioni
  (`20261110-51`): i 34 CSV laterali, uno per cantiere, e il CSV che nessuno caricava confluiscono in
  quel file; le righe che erano solo l'uscita delle automazioni non vi entrano e restano da decidere.
  Lo stesso giorno si ritirano `fn_seed_fk_index_policy` e la sua vista
  `vw_fk_con_indice_missing_policy`, che scrivevano una decisione da un'automazione e che nessuno
  eseguiva.

---

{% include-markdown "signature-core.md" %}
