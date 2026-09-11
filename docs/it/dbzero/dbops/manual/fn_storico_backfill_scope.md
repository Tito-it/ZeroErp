## 📘 Documentazione Funzione – `dbops.fn_storico_backfill_scope` / `fn_storico_backfill_scope_tutte`

> 👀 **Vedi anche**
>
**Approfondimento funzioni:**
>
• [dbops.fn_storico_risolvi_scope](/dbzero/dbops/manual/fn_storico_risolvi_scope) — chi risolve l'emittente
• [dbops.fn_storico_arma_scope](/dbzero/dbops/manual/fn_storico_arma_scope) — chi mette le colonne
>

### 🎯 Scopo Principale
(latest review 11-09-2026)

Le versioni di storico scritte **prima** dell'11-09-2026 non hanno né
`origine_schema` né `scope_emittente_fiscale_id`. Questa funzione li attribuisce
alle righe che ne sono prive, madre per madre:

* `origine_schema` = lo schema della madre;
* `scope_emittente_fiscale_id` = l'emittente risolto **dallo snapshot** della
  versione, seguendo la mappa — è l'unica riga che il passato ci ha lasciato.

Quando nessuna riga resta senza origine, porta `origine_schema` a `NOT NULL`.
`fn_storico_backfill_scope_tutte()` la applica a ogni madre con il trigger.

Brief: `brief-db-rls-storico-scope-congelato`, §4b e §5.

---

### ⭐ Le tabelle condivise: di chi è questa versione?

`storico.ddt` contiene versioni di `acquisti.ddt` e di `vendite.ddt`, senza nulla
che dica quale. Lo snapshot però è la riga intera: le sue **chiavi** sono le
colonne della madre al momento della scrittura, e le due madri hanno colonne che
l'altra non ha. Una versione si attribuisce alla madre di cui porta almeno una
**chiave esclusiva**. Le versioni che non ne portano nessuna restano senza
origine, e il controllo automatico le conta.

---

### ⚠️ Il limite dichiarato

Per i modi `PADRE` il resolver risale al padre **com'è oggi** — o, se il padre
non è più vivo, alla sua ultima versione nello storico. Il passato viene letto
in parte con il presente: è il limite del backfill, non della regola. Da qui in
avanti le versioni le congela il trigger nel momento in cui sono certe. Dove né
il padre né il suo archivio rispondono, la versione resta senza scope e, sulla
tabella armata, non si vede.

Letto sul database di sviluppo dopo l'apply dell'11-09-2026 (fatto datato):
**65.751 versioni attribuite, zero senza origine** — tutte le 116 tabelle di
storico con madre sono passate a `origine_schema NOT NULL`, anche le sei
condivise. Nel dry-run precedente, `fatture_scadenze` aveva 56 versioni su 60
con l'emittente ritrovato, 46 di queste solo grazie all'archivio della fattura.

---

### Chi la lancia

Il changeSet `90_end/20260911-31`, una volta; e `scripts/sql/provision_storico_scope.sql`
da superuser per le tabelle che il migratore non possiede. Idempotente: tocca
solo le righe ancora senza origine. Dove la tabella non ha le colonne (il
provisioning non è passato) registra `WARN` e prosegue.
