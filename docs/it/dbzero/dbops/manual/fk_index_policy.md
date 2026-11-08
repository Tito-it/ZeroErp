## 📘 Documentazione Concettuale – Tabella `dbops.fk_index_policy`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — gli schemi in cui le viste della policy cercano le chiavi esterne
>
> Approfondimento viste:
>
> * [dbops.vw_fk_senza_indice](/dbzero/dbops/views/vw_fk_senza_indice) — le chiavi esterne davvero scoperte, e la guardia della creazione
> * [dbops.vw_fk_con_indice_missing_policy](/dbzero/dbops/views/vw_fk_con_indice_missing_policy) — le chiavi esterne con un indice dedicato e senza riga qui
> * [dbops.vw_indici_ridondanti_prefisso](/dbzero/dbops/views/vw_indici_ridondanti_prefisso) — dice quali righe tengono in vita un indice ridondante
>
> Approfondimento funzioni:
>
> * [dbops.apply_fk_index_policy](/dbzero/dbops/funzioni/apply_fk_index_policy) — la procedura che esegue la policy
> * [dbops.fn_populate_fk_index_policy](/dbzero/dbops/funzioni/fn_populate_fk_index_policy) — registra le chiavi esterne scoperte, a flag spento
> * [dbops.fn_seed_fk_index_policy](/dbzero/dbops/funzioni/fn_seed_fk_index_policy) — porta sotto governo gli indici dedicati che esistono già
>
> Guide:
>
> * [Automazione DB — policy indici FK](/guide/automazione-db#6-policy-indici-fk) — il flusso completo
> * [Linee guida SQL — automazione indici FK](/linee-guida-sql#87-automazione-indici-fk) — le regole per chi scrive un changeSet

---

### 🎯 Scopo Principale

La policy degli indici sulle chiavi esterne: una riga per vincolo, con un flag che dice se
l'indice deve esistere e il comando che lo crea. È l'unico posto da cui gli indici delle
chiavi esterne nascono e muoiono.

Chi crea o toglie a mano un indice governato da qui se lo ritrova disfatto al `migrate`
successivo: `dbops.apply_fk_index_policy` gira a ogni migrazione e nel job settimanale, e
riporta il database a ciò che la tabella dice.

---

### Una riga per vincolo, due decisioni possibili

La chiave è il vincolo di chiave esterna (schema, tabella, nome del vincolo). `consentito`
dice che cosa deve essere vero:

| `consentito` | Che cosa ottiene la riga |
| --- | --- |
| `true` | l'indice nasce, **se la chiave esterna è ancora scoperta**: una chiave esterna già servita da un indice più largo non ne riceve uno dedicato |
| `false` | l'indice viene tolto, **se togliere quell'indice è innocuo**: un indice che sostiene un vincolo non si tocca |

Le due condizioni sono le guardie della procedura, descritte nella sua scheda.

⭐ **Portare a `false` una riga è una decisione reversibile.** Il comando resta scritto: se un
giorno l'indice più largo che rendeva superfluo quello dedicato sparisse, basta rimettere `true`
e l'indice torna, con lo stesso nome di prima. Con `false` la policy fa anche da guardia
permanente: un indice ricreato a mano fuori dalle migrazioni viene ritolto.

---

### ⛔ `dll_command` è un comando, non una nota

La procedura esegue `dll_command` alla lettera quando deve creare l'indice, e ne ricava il
**nome** dell'indice — la sesta parola separata da spazi — quando deve toglierlo. Un testo
libero al suo posto romperebbe il deploy (creazione) oppure, peggio, renderebbe muto il ramo
che toglie: il nome estratto sarebbe una parola a caso e la riga sembrerebbe funzionare senza
fare nulla.

Per questo la colonna è obbligatoria e il vincolo `chk_fk_index_policy_dll_command_forma`
pretende la forma esatta: creazione dell'indice «se non esiste», con il nome come sesta parola,
scritto senza virgolette, seguito dalla clausola sulla tabella. La riga sbagliata non entra
nemmeno. I comandi generati dalle viste della policy rispettano la forma per costruzione.

⚠️ Il comando deve nominare l'indice **che esiste**, non uno inventato: se il nome registrato
non è quello reale, la procedura crea un secondo indice gemello sotto il nome registrato.

---

### ⚖️ La policy è opt-in

`dbops.fn_populate_fk_index_policy` registra le chiavi esterne scoperte con `consentito = false`.
Perché l'indice nasca serve un **seed esplicito** che porti il flag a `true`; senza, l'automazione
non crea nulla. Su una tabella nuova, quindi, chi crea la tabella prevede anche il seed dei flag.

`generated_by_script` distingue le righe nate dalle funzioni di popolamento da quelle scritte a
mano in un seed.

---

### Come si modifica

Con un seed in `80_data`, CSV più caricamento con aggiornamento sulla chiave del vincolo: la
stessa riga aggiorna o inserisce. Ogni riga porta un `dll_command` valorizzato anche quando il
flag è `false`, ed è quello che rende la decisione reversibile; il perché della decisione si
scrive nel changeSet che carica il seed.

⛔ Non si ricostruisce la logica della procedura con uno script scritto a mano: la procedura ha
le due guardie, una copia artigianale no.

---

### Test

* `db/pgtap/dbops/test-indici-letture-trasversali-v1.sql` — una riga di policy a `true` col
  comando che nomina l'indice canonico, e l'indice che ne è uscito.
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

---

{% include-markdown "signature-core.md" %}
