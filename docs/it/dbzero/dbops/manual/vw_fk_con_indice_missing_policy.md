## 📘 Documentazione Concettuale – Vista `dbops.vw_fk_con_indice_missing_policy`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy) — la policy in cui mancano le righe che la vista elenca
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — gli schemi in cui la vista cerca
>
> Approfondimento viste:
>
> * [dbops.vw_fk_senza_indice](/dbzero/dbops/views/vw_fk_senza_indice) — la sorella: le chiavi esterne che nessun indice serve
> * [dbops.vw_duplicate_indexes](/dbzero/dbops/views/vw_duplicate_indexes) — i duplicati esatti, che qui non contano
>
> Approfondimento funzioni:
>
> * [dbops.fn_seed_fk_index_policy](/dbzero/dbops/funzioni/fn_seed_fk_index_policy) — la consuma, registrando le righe a flag acceso
> * [dbops.apply_fk_index_policy](/dbzero/dbops/funzioni/apply_fk_index_policy) — la procedura il cui ramo di rimozione detta le esclusioni
>
> Guide:
>
> * [Linee guida SQL — automazione indici FK](/linee-guida-sql#87-automazione-indici-fk) — il comando deve nominare l'indice che esiste

---

### 🎯 Scopo Principale

Le chiavi esterne degli schemi di `dbops.automation_scope` che hanno già un **indice dedicato** ma
nessuna riga in `dbops.fk_index_policy`: le candidate a passare sotto il governo dell'automazione.
Per ognuna dà il nome reale dell'indice e il comando che lo descrive.

È la coda che `dbops.fn_seed_fk_index_policy` consuma: la funzione registra queste righe con
`consentito = true`, e lanciarla svuota la vista. Nel catalogo dei presidi è una lavorazione, non
un registro di debito.

---

### ⭐ Il comando descrive l'indice che c'è

`create_index_suggestion` usa il **nome reale** dell'indice e le sue colonne **nell'ordine reale**.
Registrarlo in policy non crea niente: il comando è «crea se non esiste», e l'indice esiste.

È la regola che chiude il difetto per cui la vista è stata riscritta: un comando che nominasse un
indice diverso da quello esistente farebbe nascere, al primo giro della procedura, un secondo
indice gemello sotto il nome registrato.

---

### 🔒 Solo indici dedicati

Non basta che un indice copra la chiave esterna: deve essere un indice che la policy possa
**legittimamente possedere**, perché con il flag spento la procedura lo toglie. Sono esclusi gli
indici:

| Esclusione | Perché |
| --- | --- |
| con colonne in più rispetto alla chiave esterna | serve anche ad altro: la policy non può rivendicarlo |
| UNIQUE o chiave primaria | impongono integrità, non sono solo acceleratori |
| a supporto di un vincolo | toglierlo fallirebbe o porterebbe via il vincolo |
| `REPLICA IDENTITY` | toglierlo romperebbe la replica |
| parziali, con colonne `INCLUDE` o su espressioni | la policy sa ricreare solo indici totali su colonne |
| non btree, non validi o non pronti | non servono il controllo referenziale |

Le chiavi esterne coperte da un indice più largo o da una UNIQUE **non si propongono**: non c'è
niente da governare, e un indice dedicato sarebbe ridondante. È la stessa nozione di copertura di
`dbops.vw_fk_senza_indice`.

Se più indici dedicati servono la stessa chiave esterna, la vista ne propone uno solo, il primo per
nome; gli altri sono duplicati, e li mostra `dbops.vw_duplicate_indexes`.

---

### Note di migrazione

* 2026-07-27 — il comando suggerito passa al nome reale dell'indice. Prima la vista esponeva il nome
  reale ma costruiva il comando con un nome sintetizzato secondo una convenzione abbandonata, e la
  catena vista → seed → procedura aveva fatto ricomparire a luglio un indice tolto a gennaio, senza
  che nessun changeSet lo creasse. Lo stesso giorno la vista smette di proporre indici non dedicati:
  un primo tentativo di correzione, che puntava al nome reale qualunque indice fosse, registrava
  anche UNIQUE, innocue in creazione e letali con il flag spento.

---

{% include-markdown "signature-core.md" %}
