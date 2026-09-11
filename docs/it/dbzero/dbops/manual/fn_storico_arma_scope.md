## 📘 Documentazione Funzione – `dbops.fn_storico_arma_scope` / `fn_storico_arma_scope_tutte`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [dbops.storico_scope_policy](/dbzero/dbops/manual/storico_scope_policy) — la mappa che decide se armare
>
**Approfondimento funzioni:**
>
• [dbops.fn_ensure_storico_table](/dbzero/dbops/manual/fn_ensure_storico_table) — la chiama sulla shadow appena creata
• [dbops.fn_storico_backfill_scope](/dbzero/dbops/manual/fn_storico_backfill_scope) — il pregresso
• [dbops.fn_grant_storico_shadows](/dbzero/dbops/manual/fn_grant_storico_shadows) — stessa forma, per i privilegi dei ruoli batch
>

### 🎯 Scopo Principale
(latest review 11-09-2026)

Porta la tabella di storico di una madre alla **forma decisa** per lo scope
congelato, aggiungendo solo ciò che manca:

1. le colonne **`origine_schema`** e **`scope_emittente_fiscale_id`** (con
   indice). Su una shadow appena nata, `origine_schema` è subito `NOT NULL`;
   su una con versioni già scritte resta nullable finché il backfill non le
   attribuisce tutte;
2. la revoca del **`DELETE`** all'applicazione: uno snapshot non si cancella,
   la retention è del proprietario;
3. se la mappa dice che la madre è **protetta** (`modo` diverso da `NESSUNO`):
   RLS accesa e tre policy —
   `rls_sto_<tab>_ef_whitelist` (lettura, veste operatore, sull'emittente
   congelato), `rls_sto_<tab>_trg_ins` e `rls_sto_<tab>_trg_upd` (scrittura del
   trigger, senza filtro).

`fn_storico_arma_scope_tutte()` la applica a **ogni madre con il trigger di
storico** — il marcatore è il trigger, non un elenco — e scrive un riepilogo
nell'audit.

Brief: `brief-db-rls-storico-scope-congelato`, §4b.

---

### ⭐ Perché le policy di scrittura sono «true»

La tabella di storico la scrive il **trigger**, che gira come chi sta scrivendo
la madre — cioè l'applicazione. Con la RLS accesa e la sola policy di lettura,
PostgreSQL rifiuterebbe l'inserimento della versione e l'aggiornamento che
chiude la precedente toccherebbe zero righe *in silenzio*: la storicizzazione si
romperebbe, o peggio tacerebbe. Filtrare la scrittura non difenderebbe niente —
la madre ha già la sua RLS — e bloccherebbe le scritture di sistema. La RLS
della shadow protegge la **lettura**; la scrittura la governano i privilegi
(`INSERT` e `UPDATE` sì, `DELETE` no).

---

### ⚠️ Chi può eseguirla, e cosa succede altrimenti

`ALTER TABLE`, `CREATE POLICY` e `REVOKE` li fa **il proprietario** della
tabella. Dove il migratore non lo è — su dev il job pgAgent ha creato 68 shadow
su 121 come `postgres` — la funzione registra `WARN` nell'audit e prosegue: non
ferma il migrate. Le allinea `scripts/sql/provision_storico_scope.sql`, da
superuser, che ne riassegna anche la proprietà al migratore. In CI il problema
non esiste: tutto è di `zeroerp`.

---

### Idempotenza

Rete che converge, non migrazione: aggiunge solo ciò che manca, non registra
nulla su una shadow già allineata, e **non disarma mai** — una shadow condivisa
fra una madre protetta e una `NESSUNO` resta armata. La chiamano il generatore
alla nascita della shadow, il changeSet `90_end/20260911-29` (`runAlways`) a
ogni migrate e il provisioning.

Torna un `jsonb` con esito (`ALLINEATA`, `GIA_ALLINEATA`, `SKIP_OWNER`,
`NO_SHADOW`) e l'elenco delle azioni fatte, o che farebbe in `dry_run`.

Presidio: `db/pgtap/storico/test-storico-scope-congelato-v1.sql`.
