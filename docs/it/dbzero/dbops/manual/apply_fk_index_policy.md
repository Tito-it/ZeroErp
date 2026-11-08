## 📘 Documentazione Concettuale – Procedura `dbops.apply_fk_index_policy`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy) — la policy che la procedura esegue
>
> Approfondimento viste:
>
> * [dbops.vw_fk_senza_indice](/dbzero/dbops/views/vw_fk_senza_indice) — la fotografia delle chiavi esterne scoperte, su cui poggia la prima guardia
> * [dbops.vw_fk_con_indice_missing_policy](/dbzero/dbops/views/vw_fk_con_indice_missing_policy) — propone solo indici che il ramo di rimozione può togliere
> * [dbops.vw_indici_ridondanti_prefisso](/dbzero/dbops/views/vw_indici_ridondanti_prefisso) — gli indici ridondanti, e quali si tolgono passando da qui
>
> Approfondimento funzioni:
>
> * [dbops.fn_populate_fk_index_policy](/dbzero/dbops/funzioni/fn_populate_fk_index_policy) — registra le chiavi esterne nuove, prima del giro settimanale
> * [dbops.fn_seed_fk_index_policy](/dbzero/dbops/funzioni/fn_seed_fk_index_policy) — porta sotto governo gli indici dedicati che esistono già
> * [maintenance.proc_apply_fk_index_policy_job](/dbzero/maintenance/funzioni/proc_apply_fk_index_policy_job) — il job settimanale, con giornale e lock
>
> Guide:
>
> * [Linee guida SQL — automazione indici FK](/linee-guida-sql#87-automazione-indici-fk) — le due guardie e la regola «mai a mano»

---

### 🎯 Scopo Principale

Esegue la policy degli indici sulle chiavi esterne: per ogni riga di `dbops.fk_index_policy` crea
l'indice se il flag è acceso e la chiave esterna è ancora scoperta, lo toglie se il flag è spento e
toglierlo è innocuo.

Gira a ogni migrazione (un changeSet `runAlways` in `90_end`) e nel job settimanale
`maintenance.proc_apply_fk_index_policy_job`, che prima registra le chiavi esterne nuove.

---

### ⭐ Due guardie, perché un flag può essere sbagliato

La policy poggia su un booleano, e un booleano si può rimettere al valore sbagliato per errore —
una modifica distratta, un CSV rigenerato, un merge. Senza guardie la procedura eseguirebbe alla
lettera qualunque cosa trovi in tabella.

**Prima guardia — non si crea ciò che è già coperto.** Con `consentito = true` l'indice nasce solo
se la chiave esterna figura ancora fra le scoperte di `dbops.vw_fk_senza_indice`. Una chiave
esterna già servita da una UNIQUE più larga, o da un indice parziale sulle sole condizioni «non
nullo» delle sue colonne, non riceve un indice dedicato nemmeno a flag acceso: un `true` rimesso
per errore non può rigenerare le ridondanze già bonificate.

⚠️ L'auto-riparazione resta: se un indice governato viene cancellato a mano, la chiave esterna
torna scoperta e al giro successivo l'indice rinasce. La guardia non congela lo stato, verifica il
bisogno ogni volta.

**Seconda guardia — non si toglie ciò che non è solo un acceleratore.** Con `consentito = false`
la procedura ricava il nome dell'indice dal comando registrato (la sesta parola) e, prima di
toglierlo, controlla che non sia un indice UNIQUE, una chiave primaria, un indice che sostiene un
vincolo o la `REPLICA IDENTITY`. Se lo è, rifiuta. Un flag booleano non deve poter togliere un
vincolo di integrità.

La fotografia delle chiavi esterne scoperte si prende **una volta sola**, prima di scorrere la
policy: la vista è costosa e le righe di policy sono centinaia.

---

### ⚠️ Avvisi, non errori

Un rifiuto della seconda guardia è un **avviso**, non un'eccezione, e il giro prosegue. La
procedura gira a ogni migrazione: un errore fermerebbe ogni deploy finché qualcuno non interviene,
e un indice di troppo costa incomparabilmente meno di una pipeline ferma.

A fine giro un avviso informativo riepiloga quanti indici ha creato, quanti ha saltato perché già
coperti, quanti ne ha tolti e quanti rifiuti ha opposto.

⚠️ Gli avvisi arrivano al client e al log del server, non al giornale dei job: per il job
settimanale la corsa risulta riuscita anche quando la guardia ha rifiutato qualcosa. Chi vuole
sapere se una riga di policy chiede di togliere un vincolo legge il log del server.

---

### ⛔ Che cosa non fa

* non crea chiavi esterne né decide quali indicizzare: esegue la decisione scritta in policy;
* non registra le chiavi esterne nuove: lo fa `dbops.fn_populate_fk_index_policy`, e solo nel job
  settimanale, non nel giro di ogni migrazione;
* non guarda oltre gli schemi di `dbops.automation_scope`: una chiave esterna fuori da quegli
  schemi non compare fra le scoperte, e una riga a `true` che la riguarda viene sempre saltata.

---

### Test

* `db/pgtap/dbops/test-indici-letture-trasversali-v1.sql` — l'indice che la procedura crea in
  `90_end` per una riga di policy a `true` esiste davvero.
* `db/pgtap/dbops/test-processi-jobname-wrapper.sql` — il nome che il job settimanale passa al
  giornale, `apply_fk_index_policy`, è a catalogo in `dbops.processi`.

---

### Note di migrazione

* 2026-07-27 — nascono le due guardie. Prima la procedura eseguiva alla lettera ogni riga di
  policy: un flag sbagliato bastava a produrre un indice ridondante o, nel caso peggiore, a togliere
  un vincolo.

---

{% include-markdown "signature-core.md" %}
