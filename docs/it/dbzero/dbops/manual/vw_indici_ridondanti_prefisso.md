## 📘 Documentazione Concettuale – Vista `dbops.vw_indici_ridondanti_prefisso`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy) — dove si decide `SENZA_INDICE` per un indice governato dall'automazione
>
> Approfondimento viste:
>
> * [dbops.vw_duplicate_indexes](/dbzero/dbops/views/vw_duplicate_indexes) — la sorella: i duplicati esatti
> * [dbops.vw_fk_senza_indice](/dbzero/dbops/views/vw_fk_senza_indice) — la stessa idea di copertura per prefisso, dal lato delle chiavi esterne
>
> Approfondimento funzioni:
>
> * [dbops.fn_indici_schema_nell_ambito](/dbzero/dbops/funzioni/fn_indici_schema_nell_ambito) — gli schemi in cui la vista cerca
> * [dbops.apply_fk_index_policy](/dbzero/dbops/funzioni/apply_fk_index_policy) — la procedura che rifarebbe un indice tolto senza cambiare la decisione
>
> Guide:
>
> * [Linee guida SQL — indici ridondanti](/linee-guida-sql#86-gestione-indici-ridondanti) — come si decide e come si rimuove

---

### 🎯 Scopo Principale

I btree degli schemi governati dalla politica degli indici resi inutili da un altro btree della stessa
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
| `AUTOMAZIONE_FK` | la riga di `dbops.fk_index_policy` che nomina proprio quell'indice si porta a `SENZA_INDICE` nel CSV della politica, e il giro successivo di `dbops.apply_fk_index_policy` lo toglie. Un `DROP` secco verrebbe annullato al primo `migrate` se la riga è `CON_INDICE` |
| `MANUALE` | rimozione dell'indice in un changeSet dedicato |

`policy_constraint_name` e `policy_decisione` mostrano la riga di politica corrispondente, quando c'è.

⭐ La riga si aggancia per **nome esatto**: `indice_nome` della politica uguale al nome
dell'indice, la stessa colonna che la procedura usa per togliere. Un nome che termina come quello di
un altro indice, o che contiene il trattino basso, aggancia solo la riga sua.

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

### Test

* `db/pgtap/dbops/test-fk-index-policy-decisione-v1.sql` — la riga di politica si aggancia per nome
  esatto anche quando un altro nome ne è il suffisso o contiene il trattino basso.

---

### Note di migrazione

* 2026-07-27 — nasce con la bonifica degli indici ridondanti. Dei candidati con molte letture, quasi
  tutti avevano un coprente di dimensione identica, e gli altri un rapporto di poco superiore: sono
  stati rimossi tutti.
* 2026-11-09 — la riga di politica si aggancia per nome esatto (`indice_nome`), e
  `policy_consentito` diventa `policy_decisione`; il perimetro viene da `fn_indici_schema_nell_ambito`
  (`20261110-45`, brief-db-revisione-dbops, giro 10d). Prima il nome dell'indice si cercava dentro il
  comando con un confronto per somiglianza: un nome suffisso di un altro, o col trattino basso che
  nel confronto vale come carattere qualsiasi, agganciava la riga sbagliata e la vista diceva
  `AUTOMAZIONE_FK` su un indice che la politica non governa.

---

{% include-markdown "signature-core.md" %}
