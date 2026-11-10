## 📘 Documentazione Concettuale – Vista `dbops.vw_fk_da_decidere`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy) — la politica, dove si scrive la decisione che svuota il presidio
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo dei presidi, in cui la vista è iscritta
>
> Approfondimento viste:
>
> * [dbops.vw_fk_senza_indice](/dbzero/dbops/views/vw_fk_senza_indice) — il fatto da cui la vista parte: le chiavi esterne scoperte
>
> Approfondimento funzioni:
>
> * [dbops.fn_populate_fk_index_policy](/dbzero/dbops/funzioni/fn_populate_fk_index_policy) — la scoperta, che registra le chiavi esterne nuove come da decidere
> * [dbops.apply_fk_index_policy](/dbzero/dbops/funzioni/apply_fk_index_policy) — la procedura che esegue le decisioni
> * [dbops.fn_indici_schema_nell_ambito](/dbzero/dbops/funzioni/fn_indici_schema_nell_ambito) — il perimetro della politica
>
> Guide:
>
> * [Automazione DB — policy indici FK](/guide/automazione-db#6-policy-indici-fk) — il flusso completo

---

### 🎯 Scopo Principale

Il presidio della politica degli indici delle chiavi esterne: le chiavi esterne scoperte su cui
nessuno ha deciso, quelle decise `CON_INDICE` e ancora scoperte, e le righe di politica che stanno
fuori dagli schemi governati. La colonna `caso` dice quale delle tre.

È una coda di lavoro, non un allarme: si svuota decidendo.

---

### I tre casi

| `caso` | Che cosa vuol dire | Che cosa si fa |
| --- | --- | --- |
| `DA_DECIDERE` | una chiave esterna scoperta senza riga, o con la riga `DA_DECIDERE`: nessuno ha deciso se le serve un indice | si scrive una riga `CON_INDICE` o `SENZA_INDICE` nel CSV della politica |
| `CON_INDICE_NON_APPLICATA` | una chiave esterna decisa `CON_INDICE` e ancora scoperta: una promessa non mantenuta | si guarda perché: l'apply non è ancora girato, o il comando crea un indice che non la copre |
| `FUORI_AMBITO` | una riga di politica su uno schema che la politica non governa: l'apply non la applica | si toglie la riga, o lo schema entra nell'ambito |

Per ogni riga la vista dà la decisione (vuota se la chiave esterna non ha riga) e il comando: quello
suggerito dalla vista delle scoperte, oppure, per una riga fuori ambito, quello scritto in
politica.

⭐ **Una chiave esterna `SENZA_INDICE` non compare.** È scoperta per decisione, ed è giusto che lo
sia: il fatto la mostra ancora, in `dbops.vw_fk_senza_indice`, ma qui non c'è niente da fare.

---

### Da dove vengono le righe da decidere

La scoperta, `dbops.fn_populate_fk_index_policy`, gira a ogni migrazione e nel job settimanale, e
registra come `DA_DECIDERE` ogni chiave esterna scoperta senza riga. Una tabella nuova con chiavi
esterne scoperte compare quindi qui al primo `migrate`, anche su un database da zero. La riga esce
quando la chiave esterna riceve una decisione nel seed, oppure quando smette di essere scoperta (un
indice del suo changeSet la copre, o la chiave esterna sparisce).

Nel catalogo dei presidi la vista è una lavorazione a cadenza settimanale.

---

### Test

* `db/pgtap/dbops/test-fk-index-policy-decisione-v1.sql` — una chiave esterna nuova compare come
  `DA_DECIDERE`; una decisa `SENZA_INDICE` non compare; una `CON_INDICE` ancora scoperta compare come
  `CON_INDICE_NON_APPLICATA` ed esce quando l'apply crea l'indice; una riga fuori ambito compare come
  `FUORI_AMBITO`; nessuna riga vera della politica è fuori ambito.

---

### Note di migrazione

* 2026-11-09 — nasce, quando la vista delle chiavi esterne scoperte smette di fare anche da presidio
  (`20261110-49`, brief-db-revisione-dbops, giro 10d). Prima il presidio era
  `vw_fk_senza_indice` stessa, filtrata sul flag `consentito`: la scoperta scriveva falso su ogni
  chiave esterna nuova, e così le chiavi esterne nuove uscivano tutte dal controllo. Prende anche il
  posto di `vw_fk_con_indice_missing_policy`, ritirata lo stesso giorno: mostrava le chiavi esterne
  già coperte da un indice dedicato e senza riga, perché una funzione, che nessuno chiamava, le
  registrasse con una decisione scritta dall'automazione. Una chiave esterna coperta dall'indice del
  suo changeSet non ha bisogno di una riga.

---

{% include-markdown "signature-core.md" %}
