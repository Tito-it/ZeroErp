## 📘 Documentazione Concettuale – View `dbops.vw_indici_ridondanti_prefisso`

> 👀 **Vedi anche**
>
Approfondimento Tabelle:  
>
[dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy)  
>
Approfondimento funzioni:  
>
[dbops.vw_duplicate_indexes](/dbzero/dbops/views/vw_duplicate_indexes)  
> [dbops.vw_fk_senza_indice](/dbzero/dbops/views/vw_fk_senza_indice)  
> [dbops.apply_fk_index_policy](/dbzero/dbops/funzioni/apply_fk_index_policy)  

La view **`dbops.vw_indici_ridondanti_prefisso`** individua i btree le cui **colonne chiave sono la testa di quelle di un altro btree** sulla stessa tabella. È **limitata agli schemi presenti in `dbops.automation_scope`**.

Per ciascun candidato riporta chi lo copre, quanto pesa, quanto è stato usato e — soprattutto — **come si rimuove**.

---
### 🎯 Scopo Principale
(latest review 27-07-26)

* **Vedere la ridondanza che `vw_duplicate_indexes` non può vedere.**
  Un indice su `(a)` è inutile se ne esiste uno su `(a, b)`: PostgreSQL usa già il secondo per ogni ricerca su `a`. Ma non è un *duplicato* — le colonne differiscono — quindi nessun affinamento della view sorella potrà mai catturarlo. Servono entrambe.
* **Dire come si rimuove**, non solo che c'è: la colonna `origine` distingue gli indici governati dall'automazione FK da quelli scritti a mano, perché l'azione corretta è diversa.
* **Quantificare**: peso e letture, per non droppare alla cieca.

---

### 🔑 Il criterio

Un btree **A** è ridondante se esiste un btree **B** sulla stessa tabella tale che:

1. le colonne chiave di **A** sono un prefisso di quelle di **B**, con identici **classe di operatori**, **collation** e **opzioni di ordinamento** (`ASC`/`DESC`, `NULLS FIRST`/`LAST`);
2. **A** e **B** hanno lo **stesso predicato** — entrambi totali, oppure predicato identico;
3. **B** è "almeno altrettanto forte": ha più colonne chiave, oppure è `UNIQUE`.

#### Solo btree

GIN e GiST non hanno semantica di prefisso: in un GIN multicolonna ogni colonna è una lista di posting indipendente, non c'è una testa che una ricerca parziale possa sfruttare. Includerli avrebbe prodotto consigli sbagliati.

#### Perché il predicato dev'essere identico, non "compatibile"

Un indice totale non è coperto da uno parziale, e stabilire se il predicato di **B** implichi quello di **A** è indecidibile in generale. La regola è quindi conservativa: meglio non segnalare una ridondanza vera che suggerire un `DROP` sbagliato.

---

### 🔒 Le esclusioni di sicurezza

Questa view suggerisce `DROP`, quindi il candidato **A** non può essere:

| Esclusione | Perché |
| --- | --- |
| `UNIQUE` (`indisunique`) | impone un vincolo, non è solo un acceleratore |
| `PRIMARY KEY` (`indisprimary`) | non si tocca |
| `REPLICA IDENTITY` (`indisreplident`) | droparlo rompe la replica logica |
| a supporto di un constraint (`pg_constraint.conindid`) | il `DROP` fallirebbe o porterebbe via il vincolo |
| con colonne `INCLUDE` | coprirle richiederebbe verificare che stiano anche in **B** |

**B** invece può essere qualsiasi cosa, PK comprese: se un indice non-unique su `(id)` è coperto dalla PK, è giusto saperlo.

Quando un indice è coperto da più indici, `DISTINCT ON` riporta il coprente più **stretto** (UNIQUE prima, poi meno colonne chiave): è quello la cui esistenza è più difficile da mettere in discussione.

---

### 🧭 La colonna che decide l'azione: `origine`

| `origine` | Come si rimuove |
| --- | --- |
| `AUTOMAZIONE_FK` | `consentito = false` in `dbops.fk_index_policy` **e** `DROP` esplicito in changeSet. Un `DROP` secco verrebbe annullato da `apply_fk_index_policy()` al primo `migrate` |
| `MANUALE` | `DROP INDEX` in un changeSet dedicato |

Senza questa distinzione la view suggerirebbe rimozioni che l'automazione rifarebbe al giro successivo. Le colonne `policy_constraint_name` e `policy_consentito` mostrano la riga di policy corrispondente, quando esiste.

---

### ⚖️ Un `idx_scan` alto non è una controindicazione

Il planner sceglie l'indice più stretto quando ci sono entrambi, perché costa meno pagine: è **proprio per questo** che le letture stanno lì. Tolto il più stretto, le stesse query passano sul più largo.

Prima di decidere, confrontare le dimensioni dei due:

```sql
SELECT v.indice_ridondante, v.idx_scan, v.peso AS peso_stretto,
       pg_size_pretty(pg_relation_size(
         (v.schema_name || '.' || quote_ident(v.coperto_da))::regclass)) AS peso_largo
FROM dbops.vw_indici_ridondanti_prefisso v
WHERE v.idx_scan > 50;
```

Se i due pesano uguale, il più stretto non porta alcun vantaggio di cache e si toglie senza pensarci. Se il coprente è molto più grande **e** la tabella è grande davvero, il caso va misurato: un indice stretto che sopravvive accanto a uno largo è legittimo, ma va motivato con numeri.

> Alla bonifica del 27-07-2026, degli 11 candidati con `idx_scan > 50` otto avevano coprente di dimensione **identica**, e i tre restanti un rapporto di 1,17x, 1,75x e 2,23x su indici da 96, 160 e 104 kB. Tutti rimossi.

---

### Colonne e Descrizione

| Colonna | Descrizione |
| --- | --- |
| `schema_name`, `table_name` | Dove si trova l'indice |
| `indice_ridondante` | Il candidato alla rimozione |
| `coperto_da` | L'indice che lo rende superfluo |
| `motivo` | `PREFISSO` oppure `DUPLICATO_ESATTO` (stesso numero di colonne chiave) |
| `peso_byte`, `peso` | Spazio occupato, grezzo e leggibile |
| `idx_scan` | Letture dell'indice da `pg_stat_user_indexes` |
| `origine` | `AUTOMAZIONE_FK` oppure `MANUALE` — vedi sopra |
| `policy_constraint_name` | Il vincolo FK della riga di policy, se governato |
| `policy_consentito` | Il flag corrente in `dbops.fk_index_policy` |

---

### Esempi di Utilizzo

```sql
-- panoramica per origine
SELECT origine, motivo, count(*), pg_size_pretty(sum(peso_byte)) AS peso
FROM dbops.vw_indici_ridondanti_prefisso
GROUP BY 1, 2 ORDER BY 1, 2;

-- gli indici da togliere agendo sulla policy
SELECT schema_name, table_name, indice_ridondante, coperto_da, policy_constraint_name
FROM dbops.vw_indici_ridondanti_prefisso
WHERE origine = 'AUTOMAZIONE_FK';
```

---

### Vantaggi Operativi

* **Copre l'angolo cieco**: intercetta la forma di ridondanza più comune e più invisibile.
* **Azionabile**: `origine` dice quale procedura seguire, non lascia dedurre.
* **Prudente**: esclude per costruzione tutto ciò che impone integrità o sostiene la replica.
* **Misurabile**: peso e letture accanto a ogni candidato, per decidere sui numeri.

---

> **“Un indice di troppo non costa solo spazio: costa una scrittura in più a ogni INSERT, UPDATE e DELETE, per sempre.”**
