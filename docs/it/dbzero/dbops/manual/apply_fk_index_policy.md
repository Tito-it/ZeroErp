## 📘 Documentazione Concettuale – Procedura `dbops.apply_fk_index_policy()`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
Approfondimento Tabelle:  
>
[dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy)  
>
Approfondimento funzioni :  
>
[dbops.fn_populate_fk_index_policy](/dbzero/dbops/funzioni/fn_populate_fk_index_policy)  
> [dbops.fn_seed_fk_index_policy](/dbzero/dbops/funzioni/fn_seed_fk_index_policy)  
> [dbops.vw_fk_senza_indice](/dbzero/dbops/views/vw_fk_senza_indice)  
> [dbops.vw_indici_ridondanti_prefisso](/dbzero/dbops/views/vw_indici_ridondanti_prefisso)  

---
### 🎯 Scopo Principale
Applicare in modo automatico le regole di indicizzazione definite nella tabella `dbops.fk_index_policy`:  

*  **Creare** gli indici sulle foreign key contrassegnate come `consentito = true`, **se ancora servono**.
*  **Rimuovere** gli indici non più approvati (`consentito = false`), **se togliere quell'indice è un'operazione innocua**.

Le due condizioni in grassetto sono le **guardie** introdotte il 27-07-2026: senza di esse la procedura eseguiva alla lettera qualunque cosa trovasse in tabella, e un flag sbagliato bastava a produrre un indice ridondante o, nel caso peggiore, a rimuovere un vincolo.

---

### Descrizione del Flusso

1. **Fotografia delle FK scoperte**
   Prima del ciclo, legge **una sola volta** `dbops.vw_fk_senza_indice` e ne conserva le chiavi in un array. La view è costosa e le righe di policy sono centinaia: valutarla dentro il ciclo significherebbe rieseguirla per ognuna.
2. **Scansione**
   Itera su ogni riga di `dbops.fk_index_policy` (schema, tabella, constraint, comando).
3. **Creazione — con guardia**
   Se `rec.consentito = true`, esegue `rec.dll_command` **solo se** la FK figura ancora nella fotografia, cioè è davvero priva di copertura. Altrimenti salta e incrementa il contatore dei saltati.
4. **Rimozione — con guardia**
   Se `rec.consentito = false`, estrae il nome dell'indice dal sesto token di `dll_command` e, **prima** di rimuoverlo, verifica che non sia un `UNIQUE`, una `PRIMARY KEY`, un indice a supporto di un constraint o la `REPLICA IDENTITY` della tabella. Se lo è, **rifiuta** con `RAISE WARNING` e prosegue. Altrimenti:

   ```sql
   DROP INDEX IF EXISTS <schema>.<index_name>;
   ```
5. **Riepilogo**
   A fine ciclo emette un `RAISE NOTICE`:

   ```text
   apply_fk_index_policy: creati=2, saltati_perche_gia_coperti=145, droppati=577, drop_rifiutati=0
   ```

---

### Le due guardie in dettaglio

#### Guardia 1 — non creare ciò che è già coperto

Una FK già servita da una `UNIQUE` più larga, o da un indice parziale `WHERE colonna IS NOT NULL`, **non riceve un indice dedicato nemmeno con `consentito = true`**.

Il motivo è che la policy poggia su un flag booleano, e un flag può essere rimesso a `true` per errore — una modifica sbagliata, un CSV rigenerato, un merge. Senza guardia, quell'errore rigenerava silenziosamente le ridondanze appena bonificate, al primo passaggio del job settimanale. Con la guardia, girare l'interruttore per sbaglio non produce più nulla.

> ⚠️ **L'auto-riparazione resta intatta.** Se un indice governato dalla policy viene cancellato a mano, la FK ricompare in `vw_fk_senza_indice` e al giro successivo viene ricreata. La guardia non congela lo stato: verifica il bisogno reale, ogni volta.

#### Guardia 2 — non rimuovere ciò che non è solo un acceleratore

Il ramo `consentito = false` esegue `DROP INDEX` sul nome estratto dal comando. Se quel nome appartenesse a un `UNIQUE`, a una `PRIMARY KEY`, a un indice a supporto di un constraint o alla `REPLICA IDENTITY`, un semplice flag avrebbe tolto un **vincolo di integrità** o rotto la replica.

**Warning e non eccezione.** La procedura gira `runAlways` in `90_end` a ogni `migrate` e nel job settimanale: sollevare un errore bloccherebbe ogni deploy finché qualcuno non interviene, e il costo di un indice di troppo è incomparabilmente minore di quello di una pipeline ferma. Il warning arriva al client e al log del server, non al giornale: `maintenance.fn_run_and_log` registra la corsa come riuscita, e un indice risparmiato dalla guardia non rende rossa la corsa.

> La difesa è ridondante per scelta: anche [vw_fk_con_indice_missing_policy](/dbzero/dbops/views/vw_fk_con_indice_missing_policy) impedisce che righe pericolose entrino in policy. Ma questa guardia sta nel punto in cui il `DROP` viene davvero eseguito, ed è l'unica che regge anche a un `INSERT` fatto a mano nella tabella.

---

### Invocazione

```sql
CALL dbops.apply_fk_index_policy();
```

Chiamata automaticamente da:

* il changeSet `90_end/20250626-31` (`runAlways: true`) — a ogni `migrate`;
* `maintenance.proc_apply_fk_index_policy_job()` — job pgAgent settimanale, con logging e lock.

---

### Vantaggi Operativi

* **Centralizzazione**: tutte le regole di indicizzazione FK risiedono in un'unica tabella.
* **Automazione**: evita script manuali di `CREATE/DROP INDEX`, riducendo errori e incongruenze.
* **Flessibilità**: modificando la colonna `consentito` si abilita o disabilita subito l'indice, senza alterare codice.
* **Idempotenza rispetto al bisogno**: non crea ciò che sarebbe superfluo, quindi eseguirla più volte non accumula ridondanze.
* **Sicurezza**: nessun flag può togliere un vincolo di integrità.
* **Osservabilità**: il riepilogo finale dice cosa è stato fatto in quel giro.
* **Integrazione CI/CD**: è chiamata in un changeSet `90-end` per assicurarsi che, a ogni deploy, la policy sia applicata.
