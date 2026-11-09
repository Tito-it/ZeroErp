## 📘 Documentazione Concettuale – Funzione `dbops.fn_populate_fk_index_policy`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy) — la politica in cui registra
>
> Approfondimento viste:
>
> * [dbops.vw_fk_senza_indice](/dbzero/dbops/views/vw_fk_senza_indice) — da dove legge le chiavi esterne scoperte e il comando suggerito
> * [dbops.vw_fk_da_decidere](/dbzero/dbops/views/vw_fk_da_decidere) — il presidio in cui le righe che scrive diventano lavoro da fare
>
> Approfondimento funzioni:
>
> * [dbops.apply_fk_index_policy](/dbzero/dbops/funzioni/apply_fk_index_policy) — la procedura che esegue le decisioni, e lascia stare le righe da decidere
> * [maintenance.proc_apply_fk_index_policy_job](/dbzero/maintenance/funzioni/proc_apply_fk_index_policy_job) — il job settimanale che la chiama
>
> Guide:
>
> * [Linee guida SQL — automazione indici FK](/linee-guida-sql#87-automazione-indici-fk) — la decisione sta nel seed

---

### 🎯 Scopo Principale

La scoperta della politica degli indici: registra in `dbops.fk_index_policy`, come `DA_DECIDERE`,
ogni chiave esterna scoperta che non ha ancora una riga, col comando suggerito dalla vista delle
scoperte; e toglie le righe `DA_DECIDERE` la cui chiave esterna non è più scoperta. Rieseguirla non
duplica righe e non tocca mai una decisione.

---

### ⚠️ Registra, non decide e non indicizza

La riga nasce `DA_DECIDERE`, e finché resta così `dbops.apply_fk_index_policy` non fa niente: né
crea né toglie. La riga è un lavoro da fare, e lo mostra il presidio `dbops.vw_fk_da_decidere`.

La decisione, `CON_INDICE` o `SENZA_INDICE`, la scrive solo il seed, nel CSV della politica. Su una
tabella nuova, quindi, la scoperta mette in evidenza le sue chiavi esterne scoperte, e chi crea la
tabella le decide.

---

### Toglie solo le sue righe

Una riga `DA_DECIDERE` la cui chiave esterna non compare più fra le scoperte esce: la chiave esterna
è stata tolta o rinominata, oppure ora la copre un indice nato nel suo changeSet. Sono righe
dell'automazione, e senza questa pulizia il registro aggiungerebbe e non toglierebbe mai.

⛔ Una riga **decisa** non si tocca, nemmeno se la sua chiave esterna sul database non c'è. Su un
database da zero le chiavi esterne verso `django.auth_user` nascono dopo Liquibase, e le loro righe
sono decisioni del seed che servono più tardi.

---

### «Scoperta» lo decide la vista

La funzione non giudica la copertura: legge `dbops.vw_fk_senza_indice`, che è dove vive la regola
(copertura per prefisso, solo btree validi, predicato assente o di soli «non nullo» sulle colonne
della chiave esterna) e il perimetro della politica. Una chiave esterna già servita da una UNIQUE più
larga non viene quindi registrata.

La vista mostra ogni chiave esterna scoperta qualunque decisione abbia, e dice quale: la funzione
registra quelle senza riga e lascia stare le altre.

---

### Chi la chiama

Due strade, con lo stesso effetto:

* il `90_end`, con un changeSet `runAlways`, a ogni migrazione: anche su un database da zero, quindi
  in CI, le chiavi esterne nuove hanno la loro riga `DA_DECIDERE` subito;
* il job settimanale `maintenance.proc_apply_fk_index_policy_job`, chiamato con il popolamento
  acceso, subito prima della procedura che applica la politica.

L'ordine rispetto all'apply non conta: le righe che la funzione scrive sono `DA_DECIDERE`, e l'apply
le lascia stare. Un avviso informativo dice quante righe ha aggiunto e quante ne ha tolte.

---

### Test

* `db/pgtap/dbops/test-fk-index-policy-decisione-v1.sql` — una chiave esterna scoperta senza riga
  viene registrata `DA_DECIDERE` e compare nel presidio; una `DA_DECIDERE` la cui chiave esterna non
  c'è più esce; una riga decisa la cui chiave esterna non c'è resta.

---

### Note di migrazione

* 2026-11-09 — scrive `DA_DECIDERE` al posto di `consentito = false`, che era una decisione scritta
  da un'automazione, e toglie le sue righe la cui chiave esterna non è più scoperta; gira anche a
  ogni migrazione, oltre che nel job settimanale (`20261110-48`, `-54`; brief-db-revisione-dbops,
  giro 10d). Prima la lanciava solo il job della domenica: su un database da zero le chiavi esterne
  nuove non avevano riga, e il registro aveva due forme diverse da zero e su sviluppo.

---

{% include-markdown "signature-core.md" %}
