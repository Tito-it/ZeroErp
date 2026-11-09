## 📘 Documentazione Concettuale – Procedura `dbops.apply_fk_index_policy`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy) — le decisioni che la procedura esegue
>
> Approfondimento viste:
>
> * [dbops.vw_fk_senza_indice](/dbzero/dbops/views/vw_fk_senza_indice) — la fotografia delle chiavi esterne scoperte, su cui poggia la prima guardia
> * [dbops.vw_fk_da_decidere](/dbzero/dbops/views/vw_fk_da_decidere) — dove compaiono le righe che la procedura lascia stare, e le decisioni che non ha potuto mantenere
> * [dbops.vw_indici_ridondanti_prefisso](/dbzero/dbops/views/vw_indici_ridondanti_prefisso) — gli indici ridondanti, e quali si tolgono passando da qui
>
> Approfondimento funzioni:
>
> * [dbops.fn_indici_schema_nell_ambito](/dbzero/dbops/funzioni/fn_indici_schema_nell_ambito) — il perimetro: gli schemi le cui righe si applicano
> * [dbops.fn_populate_fk_index_policy](/dbzero/dbops/funzioni/fn_populate_fk_index_policy) — la scoperta, che registra le chiavi esterne nuove come da decidere
> * [maintenance.proc_apply_fk_index_policy_job](/dbzero/maintenance/funzioni/proc_apply_fk_index_policy_job) — il job settimanale, con giornale e lock
>
> Guide:
>
> * [Linee guida SQL — automazione indici FK](/linee-guida-sql#87-automazione-indici-fk) — le due guardie e la regola «mai a mano»

---

### 🎯 Scopo Principale

Esegue le decisioni della politica degli indici sulle chiavi esterne: per ogni riga di
`dbops.fk_index_policy` decisa `CON_INDICE` crea l'indice se la chiave esterna è ancora scoperta,
per ogni riga decisa `SENZA_INDICE` lo toglie se toglierlo è innocuo. Le righe `DA_DECIDERE` e
quelle fuori dagli schemi governati non le tocca.

Gira a ogni migrazione (un changeSet `runAlways` in `90_end`) e nel job settimanale
`maintenance.proc_apply_fk_index_policy_job`.

---

### Che cosa fa per ogni riga

| La riga | Che cosa succede |
| --- | --- |
| su uno schema che la politica non governa | niente; la riga compare nel presidio come `FUORI_AMBITO` |
| `DA_DECIDERE` | niente: né creazione né rimozione |
| `CON_INDICE` | esegue il comando, se la chiave esterna è ancora scoperta (prima guardia) |
| `SENZA_INDICE` | toglie l'indice `indice_nome`, se non regge un vincolo (seconda guardia) |

⭐ **Nessuno ha deciso, quindi non si fa niente.** Una riga `DA_DECIDERE` la scrive la scoperta,
non una persona: se togliesse l'indice per nome, un indice nato nel changeSet della tabella col nome
canonico sparirebbe senza che nessuno l'abbia voluto. Agisce solo una decisione del seed.

Il perimetro lo dà `dbops.fn_indici_schema_nell_ambito`, per schema: una riga fuori non crea e non
toglie, e la si vede nel presidio invece che dal suo effetto.

---

### ⭐ Due guardie, perché una decisione può essere sbagliata

Una riga si può rimettere al valore sbagliato per errore — una modifica distratta, un merge. Senza
guardie la procedura eseguirebbe alla lettera qualunque cosa trovi in tabella.

**Prima guardia — non si crea ciò che è già coperto.** Con `CON_INDICE` l'indice nasce solo se la
chiave esterna figura ancora fra le scoperte di `dbops.vw_fk_senza_indice`. Una chiave esterna già
servita da una UNIQUE più larga, o da un indice parziale sulle sole condizioni «non nullo» delle sue
colonne, non riceve un indice dedicato: un `CON_INDICE` scritto per errore non può rigenerare le
ridondanze già bonificate.

⚠️ L'auto-riparazione resta: se un indice governato viene cancellato a mano, la chiave esterna
torna scoperta e al giro successivo l'indice rinasce. La guardia non congela lo stato, verifica il
bisogno ogni volta.

**Seconda guardia — non si toglie ciò che non è solo un acceleratore.** Con `SENZA_INDICE` la
procedura prende il nome da `indice_nome` e, prima di togliere l'indice, controlla che non sia un
indice UNIQUE, una chiave primaria, un indice che sostiene un vincolo o la `REPLICA IDENTITY`. Se lo
è, rifiuta. Una decisione non deve poter togliere un vincolo di integrità.

La fotografia delle chiavi esterne scoperte si prende **una volta sola**, prima di scorrere la
politica: la vista è costosa e le righe sono centinaia.

---

### ⚠️ Avvisi, non errori

Un rifiuto della seconda guardia è un **avviso**, non un'eccezione, e il giro prosegue. La
procedura gira a ogni migrazione: un errore fermerebbe ogni deploy finché qualcuno non interviene,
e un indice di troppo costa incomparabilmente meno di una pipeline ferma.

A fine giro un avviso informativo riepiloga quanti indici ha creato, quanti ha saltato perché già
coperti, quanti ne ha tolti, quanti rifiuti ha opposto, e quante righe ha lasciato stare perché da
decidere o fuori ambito.

⚠️ Gli avvisi arrivano al client e al log del server, non al giornale dei job: per il job
settimanale la corsa risulta riuscita anche quando la guardia ha rifiutato qualcosa. Chi vuole
sapere se una riga chiede di togliere un vincolo legge il log del server.

---

### ⛔ Che cosa non fa

* non crea chiavi esterne né decide quali indicizzare: esegue la decisione scritta nel seed;
* non registra le chiavi esterne nuove: lo fa `dbops.fn_populate_fk_index_policy`, che gira anch'essa
  a ogni migrazione e nel job settimanale. L'ordine fra le due non conta, perché le righe che la
  scoperta scrive sono `DA_DECIDERE`, e qui non producono niente;
* non agisce fuori dagli schemi governati, nemmeno per togliere.

---

### Test

* `db/pgtap/dbops/test-fk-index-policy-decisione-v1.sql` — l'apply non tocca l'indice di una
  `DA_DECIDERE`, toglie quello di una `SENZA_INDICE`, crea quello di una `CON_INDICE` (che esce dal
  presidio), e non toglie l'indice di una riga fuori ambito.
* `db/pgtap/dbops/test-indici-letture-trasversali-v1.sql` — l'indice che la procedura crea in
  `90_end` per una riga `CON_INDICE` esiste davvero.
* `db/pgtap/dbops/test-processi-jobname-wrapper.sql` — il nome che il job settimanale passa al
  giornale, `apply_fk_index_policy`, è a catalogo in `dbops.processi`.

---

### Note di migrazione

* 2026-07-27 — nascono le due guardie. Prima la procedura eseguiva alla lettera ogni riga di
  policy: un flag sbagliato bastava a produrre un indice ridondante o, nel caso peggiore, a togliere
  un vincolo.
* 2026-11-09 — legge `decisione` al posto del flag `consentito`; il nome dell'indice da togliere è
  `indice_nome`, non più la sesta parola del comando; le righe `DA_DECIDERE` e quelle fuori ambito
  non producono niente (`20261110-47`, brief-db-revisione-dbops, giro 10d). Prima una riga a falso
  scritta dalla scoperta toglieva per nome l'indice, e una riga fuori ambito a falso faceva il
  `DROP`, mentre a vero non creava mai.

---

{% include-markdown "signature-core.md" %}
