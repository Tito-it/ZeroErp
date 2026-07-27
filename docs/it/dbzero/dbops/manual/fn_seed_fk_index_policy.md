## 📘 Documentazione Concettuale – Funzione `dbops.fn_seed_fk_index_policy()`

> 👀 **Vedi anche**
>
Approfondimento Tabelle:  
>
[dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy)  
>
Approfondimento funzioni:  
>
[dbops.vw_fk_con_indice_missing_policy](/dbzero/dbops/views/vw_fk_con_indice_missing_policy)  
> [dbops.fn_populate_fk_index_policy](/dbzero/dbops/funzioni/fn_populate_fk_index_policy)  
> [dbops.apply_fk_index_policy](/dbzero/dbops/funzioni/apply_fk_index_policy)  

La funzione **`dbops.fn_seed_fk_index_policy()`** popola `dbops.fk_index_policy` con le foreign key **già indicizzate** ma **non ancora presenti** in policy, **limitandosi agli schemi presenti in `dbops.automation_scope`**, marcandole come `consentito = true` e `generated_by_script = true`.

È l'operazione simmetrica di [fn_populate_fk_index_policy](/dbzero/dbops/funzioni/fn_populate_fk_index_policy): quella registra le FK **scoperte** (a `false`), questa quelle **già coperte da un indice dedicato** (a `true`), per portarle sotto il governo dell'automazione.

---
### 🎯 Scopo Principale
(latest review 27-07-26)

* **Sincronizzazione iniziale**
  Aggiunge in `fk_index_policy` le FK con indice dedicato rilevate in `vw_fk_con_indice_missing_policy`.
* **Automazione**
  Evita inserimenti manuali per policy già coperte da indice.
* **Flag di origine**
  Imposta `generated_by_script = true` per distinguere le righe create automaticamente.

---

### ⚠️ Questa funzione ha rigenerato indici già rimossi

Non per un difetto suo — il codice non è cambiato — ma per un difetto della view che legge. Fino al 27-07-2026 `vw_fk_con_indice_missing_policy` costruiva il `create_index_suggestion` **sintetizzando un nome** invece di usare quello dell'indice trovato. La riga registrata da questa funzione conteneva quindi un comando che creava un **secondo** indice, gemello del primo ma con un altro nome, e `apply_fk_index_policy()` lo eseguiva.

> Un indice droppato a gennaio è ricomparso a luglio senza alcun changeSet, per questa catena: view → `fn_seed` → `apply`. Non era stato scritto a mano.

Con la view corretta il comando nomina l'indice reale, quindi registrare una FK non ne crea più un secondo: con `IF NOT EXISTS`, l'esecuzione è un no-op.

---

### 🔒 Solo indici dedicati

La view propone ora **soltanto** indici che la policy può legittimamente possedere: colonne chiave uguali a quelle della FK, non `UNIQUE`, non PK, non `REPLICA IDENTITY`, non a supporto di un constraint, totali, btree.

Il motivo è che registrare una riga significa dare ad `apply_fk_index_policy()` il potere di **droppare** quell'indice, se un domani il flag passasse a `false`. **Un flag booleano deve poter togliere solo un acceleratore, mai un vincolo di integrità.**

Le FK coperte da un indice più largo o da una UNIQUE non vengono più proposte: non c'è nulla da governare.

---

### Parametri di Input

Questa funzione **non** richiede parametri: agisce su tutti i record presenti nella view `dbops.vw_fk_con_indice_missing_policy`.

---

### Flusso Logico

1. **Selezione FK da view**
   Recupera `schema_name`, `table_name`, `constraint_name` e `create_index_suggestion` dalla view.
2. **Inserimento con ON CONFLICT**
   Usa `INSERT ... ON CONFLICT (schema_name, table_name, constraint_name) DO NOTHING` per:

   * `consentito = true`
   * `generated_by_script = true`
   * non toccare le righe già presenti, quindi **nessuna decisione già presa viene sovrascritta**.

> `DO NOTHING` è la ragione per cui una riga portata a `consentito = false` durante una bonifica non torna a `true` da sola. La rimozione resta stabile.

---

### Utilizzo

```sql
-- Esegui il popolamento iniziale:
SELECT dbops.fn_seed_fk_index_policy();
```

Può essere integrata in un changeSet Liquibase con `runAlways: false` (solo esecuzione iniziale) per assicurare che tutte le FK con indice dedicato siano registrate in policy.

> ⚠️ **Non è chiamata dal job settimanale**, che esegue invece `fn_populate_fk_index_policy()` più `apply`. Va lanciata consapevolmente: prima di farlo, conviene guardare cosa propone con `SELECT * FROM dbops.vw_fk_con_indice_missing_policy;`.

---

### Vantaggi Operativi

* **Completezza**: nessuna FK con indice dedicato resta fuori dal governo della policy.
* **Tracciabilità**: `generated_by_script` segnala le policy create automaticamente.
* **Nessun gemello**: il comando registrato nomina l'indice che esiste già.
* **Sicurezza**: nessuna riga registrata può portare `apply` a rimuovere un vincolo.
* **Semplicità**: un'unica chiamata per inizializzare la policy.

---

> **“Con `fn_seed_fk_index_policy()` automatizziamo la scoperta e l'inclusione delle FK già indicizzate, mantenendo la policy sempre completa e allineata.”**
