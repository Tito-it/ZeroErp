## 📘 Documentazione Concettuale – Funzione `dbops.fn_populate_fk_index_policy`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy) — la policy in cui registra
>
> Approfondimento viste:
>
> * [dbops.vw_fk_senza_indice](/dbzero/dbops/views/vw_fk_senza_indice) — da dove legge le chiavi esterne scoperte e il comando suggerito
>
> Approfondimento funzioni:
>
> * [dbops.fn_seed_fk_index_policy](/dbzero/dbops/funzioni/fn_seed_fk_index_policy) — la gemella per le chiavi esterne che un indice ce l'hanno già
> * [dbops.apply_fk_index_policy](/dbzero/dbops/funzioni/apply_fk_index_policy) — la procedura che esegue la policy
> * [maintenance.proc_apply_fk_index_policy_job](/dbzero/maintenance/funzioni/proc_apply_fk_index_policy_job) — il job settimanale che la chiama
>
> Guide:
>
> * [Linee guida SQL — automazione indici FK](/linee-guida-sql#87-automazione-indici-fk) — la policy è opt-in

---

### 🎯 Scopo Principale

Registra in `dbops.fk_index_policy` ogni chiave esterna scoperta che non ha ancora una riga, con
il flag `consentito` **spento** e il comando suggerito dalla vista delle scoperte. Rieseguirla non
duplica righe né tocca le decisioni già prese.

---

### ⚠️ Registra, non indicizza

È il fraintendimento più costoso. La riga nasce a `consentito = false`, e finché resta così
`dbops.apply_fk_index_policy` non crea nessun indice: anzi, a ogni giro tenta di togliere l'indice
che il comando nomina (che non esiste, quindi non succede niente).

Perché l'indice nasca serve un **seed esplicito** che porti il flag a `true`, in `80_data`, come
CSV caricato sulla chiave del vincolo. Su una tabella nuova l'automazione da sola non produce gli
indici delle chiavi esterne: chi crea la tabella prevede il seed.

⭐ Il default spento è voluto: nessun indice nasce senza che qualcuno l'abbia deciso, e ogni chiave
esterna scoperta diventa comunque una riga, cioè una decisione da prendere.

---

### «Scoperta» lo decide la vista

La funzione non giudica la copertura: legge `dbops.vw_fk_senza_indice`, che è dove vive la regola
(copertura per prefisso, solo btree validi, predicato assente o di soli «non nullo» sulle colonne
della chiave esterna). Una chiave esterna già servita da una UNIQUE più larga non viene quindi
registrata.

⚠️ Una volta registrata a `false`, la chiave esterna **esce** dalla vista delle scoperte, che
rispetta la policy: da quel momento resta visibile solo come riga di policy a flag spento.

---

### Chi la chiama

Solo il job settimanale `maintenance.proc_apply_fk_index_policy_job`, chiamato con il
popolamento acceso, subito prima della procedura che applica la policy. Il giro che parte a ogni
migrazione applica la policy e basta: non registra le chiavi esterne nuove.

---

{% include-markdown "signature-core.md" %}
