## 📘 Documentazione Concettuale – Funzione `dbops.fn_seed_fk_index_policy`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy) — la policy in cui scrive
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — gli schemi a cui si limita
>
> Approfondimento viste:
>
> * [dbops.vw_fk_con_indice_missing_policy](/dbzero/dbops/views/vw_fk_con_indice_missing_policy) — le FK con indice dedicato che la policy non ha ancora
> * [dbops.vw_fk_senza_indice](/dbzero/dbops/views/vw_fk_senza_indice) — le FK senza indice, la coda della funzione gemella
>
> Approfondimento funzioni:
>
> * [dbops.fn_populate_fk_index_policy](/dbzero/dbops/funzioni/fn_populate_fk_index_policy) — la gemella: registra le FK scoperte, con il flag spento
> * [dbops.apply_fk_index_policy](/dbzero/dbops/funzioni/apply_fk_index_policy) — esegue la policy: crea o toglie gli indici
>
> Guide:
>
> * [Linee guida SQL — 8.7 Automazione indici FK](/linee-guida-sql#87-automazione-indici-fk) — la policy degli indici sulle FK

---

### 🎯 Scopo Principale

Porta sotto la policy degli indici le FK **già coperte da un indice dedicato**: per ognuna che
`dbops.fk_index_policy` non ha ancora, scrive una riga con `consentito` vero, segnata come
generata (`generated_by_script`), e con il comando dell'indice che esiste già.

È la simmetrica di [fn_populate_fk_index_policy](/dbzero/dbops/funzioni/fn_populate_fk_index_policy),
che registra le FK **scoperte** con il flag spento.

---

### Non sovrascrive una decisione

Una FK che la policy ha già non si tocca: una riga portata a `consentito` falso durante una
bonifica non torna vera da sola, e la rimozione dell'indice resta stabile.

---

### 🔒 Solo indici dedicati

La vista da cui legge propone soltanto indici che la policy può possedere: colonne uguali a
quelle della FK, btree, totali, non `UNIQUE`, non chiave primaria, non a supporto di un vincolo.
Il motivo è che registrare una riga dà ad `apply_fk_index_policy` il potere di **togliere**
quell'indice se un giorno il flag si spegne: un flag deve poter togliere un acceleratore, mai un
vincolo di integrità. Le FK coperte da un indice più largo o da una `UNIQUE` non si propongono.

Il comando registrato nomina l'indice reale: eseguirlo non ne crea un secondo.

---

### ⚠️ L'ambito è letto per schema soltanto

La funzione considera una FK se il suo schema compare in `dbops.automation_scope`, e solo così:

* non guarda il filtro per tabella dell'ambito, che i runner applicano con
  `dbops.fn_table_in_scope`: in uno schema messo in ambito per poche tabelle registra le FK di
  tutte;
* con l'ambito vuoto non registra niente, mentre i runner, con l'ambito vuoto, lavorano su tutti
  gli schemi;
* il confronto del nome dello schema è esatto.

La gemella `fn_populate_fk_index_policy` non filtra affatto per ambito.

---

### Chi la chiama

Nessun job. L'ha chiamata una volta un changeSet di `20_code` (2026-01-16), per il popolamento
iniziale. Va lanciata consapevolmente: prima conviene guardare che cosa propone la vista
`dbops.vw_fk_con_indice_missing_policy`. ⚠️ Su un database costruito da zero quel changeSet gira
prima dei seed di `80_data`, quando l'ambito è ancora vuoto: lì non registra niente.

Il processo settimanale della policy esegue invece `fn_populate_fk_index_policy` e
`apply_fk_index_policy`.

---

### Note di migrazione

* 2026-01-16 — nasce, e un changeSet la chiama una volta per il popolamento iniziale.
* 2026-07-27 — la vista che legge nomina l'indice reale. Prima sintetizzava un nome: la riga
  registrata da questa funzione conteneva il comando di un **secondo** indice, gemello del primo,
  e `apply_fk_index_policy` lo creava. Un indice tolto a gennaio è ricomparso a luglio per questa
  catena, senza nessun changeSet. Il codice della funzione non è cambiato.

---

{% include-markdown "signature-core.md" %}
