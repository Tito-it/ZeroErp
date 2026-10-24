## 📘 Documentazione Concettuale – Funzione `maintenance.fn_analyze_statistiche`

> 👀 **Vedi anche**
>
Approfondimento viste:
>
[`maintenance.vw_statistiche_mancanti`](/dbzero/maintenance/manual/vw_statistiche_mancanti)
>
Approfondimento funzioni:
>
[`maintenance.proc_analyze_statistiche_job`](/dbzero/maintenance/manual/proc_analyze_statistiche_job)
> [`maintenance.fn_run_and_log`](/dbzero/maintenance/manual/fn_run_and_log)
>
Approfondimento tabelle:
>
[`dbops.processi`](/dbzero/dbops/manual/processi)

---
### 🎯 Scopo Principale
(latest review 14-10-2026)

Dare al pianificatore delle query **statistiche vere**, e dire quando non ci si
è riusciti.

Prima di eseguire una query, PostgreSQL sceglie come farla (quale indice, in
che ordine unire le tabelle) **stimando** quante righe escono da ogni passaggio.
Le stime le prende dalle statistiche che scrive `ANALYZE`: quante righe ha una
tabella, quali valori sono frequenti, come sono distribuite le date. Sono una
**fotografia dei dati**, e invecchiano con loro. Senza, il pianificatore stima
con valori fissi di default, e un piano può cambiare da solo a metà giornata.

L'autovacuum non basta: rianalizza una tabella solo quando ne cambiano 50 righe
più il 10%, quindi una tabella piccola o ferma non ci arriva mai, e le tabelle
partizionate non le analizza affatto. Questa funzione è il posto che lo fa.

---

### Firma

```sql
FUNCTION maintenance.fn_analyze_statistiche(p_tabelle regclass[] DEFAULT NULL)
RETURNS integer
```

* `p_tabelle` `NULL` — il caso del job: `ANALYZE` di tutto il database.
* `p_tabelle` valorizzato — solo quelle tabelle (dopo un import, o in un pgTAP,
  che non deve analizzare tutto il database per provare la regola).

Ritorna quante tabelle restano senza statistiche: sempre `0`, perché altrimenti
solleva.

---

### ⭐ L'autoverifica — perché la funzione può fallire

`ANALYZE` **non fallisce** su una tabella che non può analizzare: la salta con un
avviso (`WARNING`). Un job che saltasse metà delle tabelle scriverebbe «fatto»
nel giornale.

Per questo, subito dopo `ANALYZE` e nella stessa transazione, la funzione legge
[`vw_statistiche_mancanti`](/dbzero/maintenance/manual/vw_statistiche_mancanti).
Se resta anche una sola tabella, solleva **`E_STATISTICHE_MANCANTI`** (classe
`TECNICO`) nominando le prime dieci. Nel contesto dell'errore ci sono tutte, col
motivo, e il ruolo che ha eseguito.

| Motivo | Che cosa vuol dire | Che cosa fare |
| --- | --- | --- |
| `NON_ANALIZZABILE` | il ruolo che esegue il job non ha il diritto di analizzare la tabella | dargli `pg_maintain` nel provisioning ([liquibase-setup-workflow](/liquibase-setup-workflow) §2) e rilanciare |
| `MAI_ANALIZZATA` | la tabella è ancora senza statistiche anche dopo `ANALYZE` | guardare la tabella: con il diritto, non dovrebbe succedere |

⚠️ **La verifica sta qui e non in una vista guardata dal digest.** Subito dopo
`ANALYZE`, una tabella senza statistiche è un errore. In un'ora qualunque
potrebbe essere solo una tabella nata da una migrazione di oggi pomeriggio: un
controllo che dipende dal calendario.

---

### ⚠️ Una transazione sola

La funzione non fa `COMMIT` fra una tabella e l'altra: in CI la chiamano dentro
la transazione di un changeSet. `ANALYZE` tiene un lock `SHARE UPDATE
EXCLUSIVE` su ogni tabella fino alla fine. Non blocca letture e scritture;
blocca DDL, un altro `ANALYZE` e l'autovacuum. Per questo il job gira alle 02:30,
lontano dagli altri.

### Il catalogo di sistema

`ANALYZE` senza argomenti analizza anche `pg_catalog` se il ruolo è superuser o
proprietario del database, altrimenti lo salta. È **fuori** dall'autoverifica:
i diritti sui cataloghi non sono nostri da dare (D-1 di Tid, 2026-10-14).

---

### Chi la chiama

* il job pgAgent **`analyze_statistiche`**, ogni notte alle 02:30, attraverso
  [`proc_analyze_statistiche_job`](/dbzero/maintenance/manual/proc_analyze_statistiche_job);
* in CI, la convergenza dei job strutturali (`90_end/ci_apply/20260926-10`), che
  chiama la stessa procedura per **ultima** (`dbops.processi.ci_ordine`): dopo
  il caricamento, prima dei pgTAP.

Presidio: `db/pgtap/maintenance/test-fn-analyze-statistiche-v1.sql`.
Brief: `brief-db-statistiche-tabelle-job-notturno` (D15).
