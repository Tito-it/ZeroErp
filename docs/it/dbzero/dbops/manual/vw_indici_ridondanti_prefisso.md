## 📘 Documentazione Concettuale – Vista `dbops.vw_indici_ridondanti_prefisso`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy) — dove si spegne il flag di un indice governato dall'automazione
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — gli schemi in cui la vista cerca
>
> Approfondimento viste:
>
> * [dbops.vw_duplicate_indexes](/dbzero/dbops/views/vw_duplicate_indexes) — la sorella: i duplicati esatti
> * [dbops.vw_fk_senza_indice](/dbzero/dbops/views/vw_fk_senza_indice) — la stessa idea di copertura per prefisso, dal lato delle chiavi esterne
>
> Approfondimento funzioni:
>
> * [dbops.apply_fk_index_policy](/dbzero/dbops/funzioni/apply_fk_index_policy) — la procedura che rifarebbe un indice tolto senza spegnere il flag
>
> Guide:
>
> * [Linee guida SQL — indici ridondanti](/linee-guida-sql#86-gestione-indici-ridondanti) — come si decide e come si rimuove

---

### 🎯 Scopo Principale

I btree degli schemi di `dbops.automation_scope` resi inutili da un altro btree della stessa
tabella, che ha le stesse colonne in testa. Per ogni candidato dice chi lo copre, quanto pesa,
quanto è stato letto e, soprattutto, **come si rimuove** (`origine`).

Vede la ridondanza che `dbops.vw_duplicate_indexes` non può vedere: un indice su una colonna è
inutile se ne esiste uno su quella colonna e un'altra, perché PostgreSQL usa già il secondo per ogni
ricerca sulla prima, controllo referenziale delle chiavi esterne compreso. Non è un duplicato, e
servono entrambe le viste.

---

### 🔑 Il criterio

Un btree **A** è ridondante se esiste un btree **B** sulla stessa tabella tale che:

1. le colonne chiave di A sono la testa di quelle di B, con identici classe di operatori, collation
   e ordinamento;
2. A e B hanno lo **stesso predicato**: entrambi totali, o predicato identico;
3. B è almeno altrettanto forte: ha più colonne chiave, oppure è UNIQUE.

Quando B ha lo stesso numero di colonne ed è UNIQUE, `motivo` dice `DUPLICATO_ESATTO`; altrimenti
`PREFISSO`.

**Solo btree.** GIN e GiST non hanno semantica di prefisso: in un GIN su più colonne ogni colonna è
una lista indipendente, non c'è una testa che una ricerca parziale possa sfruttare.

**Predicato identico, non «compatibile».** Un indice totale non è coperto da uno parziale, e
stabilire se un predicato ne implichi un altro non è decidibile in generale. La regola è prudente:
meglio non segnalare una ridondanza vera che suggerire una rimozione sbagliata.

---

### 🔒 Che cosa non si propone mai di togliere

La vista suggerisce rimozioni, quindi il candidato A **non** può essere:

| Esclusione | Perché |
| --- | --- |
| UNIQUE | impone un vincolo, non è solo un acceleratore |
| chiave primaria | non si tocca |
| `REPLICA IDENTITY` | toglierlo romperebbe la replica logica |
| a supporto di un vincolo | toglierlo fallirebbe o porterebbe via il vincolo |
| con colonne `INCLUDE` | coprirle richiederebbe verificare che stiano anche in B |

B invece può essere qualsiasi cosa, chiave primaria compresa: se un indice non unico su una colonna
è coperto dalla chiave primaria, è giusto saperlo. Quando A è coperto da più indici, la vista riporta
il coprente più stretto (prima una UNIQUE, poi meno colonne): è quello la cui esistenza è più
difficile da mettere in discussione.

---

### 🧭 La colonna che decide l'azione: `origine`

| `origine` | Come si rimuove |
| --- | --- |
| `AUTOMAZIONE_FK` | flag `consentito` spento in `dbops.fk_index_policy` **e** rimozione esplicita. La sola rimozione verrebbe annullata da `dbops.apply_fk_index_policy` al primo `migrate` |
| `MANUALE` | rimozione dell'indice in un changeSet dedicato |

`policy_constraint_name` e `policy_consentito` mostrano la riga di policy corrispondente, quando c'è.

⚠️ La vista riconosce la riga di policy cercando il nome dell'indice dentro il comando registrato,
con un confronto per somiglianza: non con la regola esatta della procedura, che legge il nome come
sesta parola del comando. Un nome che termina come quello di un altro indice, o che contiene il
trattino basso (che nel confronto vale come carattere qualsiasi), può agganciare una riga di policy
che non è la sua. Prima di agire su `AUTOMAZIONE_FK` si controlla che la riga indicata nomini davvero
quell'indice.

---

### ⚖️ Un `idx_scan` alto non è una controindicazione

Il planner sceglie l'indice più stretto quando ci sono entrambi, perché costa meno pagine: è
proprio per questo che le letture stanno lì. Tolto il più stretto, le stesse query passano sul più
largo.

Prima di decidere si confrontano le dimensioni dei due. Se pesano uguale, il più stretto non porta
nessun vantaggio di cache e si toglie. Se il coprente è molto più grande **e** la tabella è grande
davvero, il caso si misura: un indice stretto che sopravvive accanto a uno largo è legittimo, ma va
motivato con numeri, non con il sospetto.

---

### Note di migrazione

* 2026-07-27 — nasce con la bonifica degli indici ridondanti. Dei candidati con molte letture, quasi
  tutti avevano un coprente di dimensione identica, e gli altri un rapporto di poco superiore: sono
  stati rimossi tutti.

---

{% include-markdown "signature-core.md" %}
