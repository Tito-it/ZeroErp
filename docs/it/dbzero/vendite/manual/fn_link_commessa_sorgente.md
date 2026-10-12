## 📘 Documentazione Concettuale – Funzione `vendite.fn_link_commessa_sorgente`
### 🎯 Scopo Principale
(latest review 24-02-2026)
Collega la ROOT source a una commessa in modo idempotente e coerente.

---

### Regole applicate

* Una commessa puo` avere una sola ROOT (`ruolo_link='ROOT'`); le sorgenti
  successive diventano COLLEGATO (multi-sorgente, la fn decide il ruolo).
* ⭐ **Un documento sta in una sola commessa APERTA alla volta** (dal 2026-10-12,
  brief-db-annullo-a-valle-riapre-a-monte D-12). Se il documento sta gia' in
  un'altra commessa aperta — chiesto a
  [vendite.fn_commessa_viva_di_sorgente](/dbzero/vendite/funzioni/fn_commessa_viva_di_sorgente)
  — `E_COMMESSA_SORGENTE_ALTRA_COMMESSA`, con l'id della commessa aperta. Una
  commessa **chiusa o annullata** non trattiene il documento: il suo link resta
  come **storia** (lineage, passaggi), e il documento si rimanda in una commessa
  nuova. Fino a quel giorno la regola era «una commessa per sempre»
  (`uq_commesse_sorgenti_src_uid`, globale), e dopo l'annullo della commessa il
  secondo invio moriva qui.
* **Idempotente sulla stessa commessa**: un secondo link dello stesso documento
  alla stessa commessa restituisce il link che c'e'. Il `meta` si riscrive solo
  se il chiamante porta qualcosa di nuovo (la porta si chiama per ogni riga
  mandata: un `UPDATE` a vuoto scriverebbe una riga di storico per riga).
* **Due lock.** Quello sulla commessa serializza la scelta del ruolo; un lock
  advisory sulla **sorgente** serializza due invii dello stesso documento verso
  commesse diverse (che il lock sulla commessa non vede). Vale in `READ
  COMMITTED`, come lavora l'applicazione.
* `sorgente_uid` obbligatoria e non vuota.
* **Normalizzazione della chiave** (2026-07-18, brief-db-guard-sorgente-polimorfa
  §2a): prima di idempotenza e insert, la chiave viene portata alla forma
  canonica dettata da `config.sorgenti.key_selector`:
  * tipo a chiave `id` + valore numerico → stoccato com'e' (`id::text`);
  * tipo a chiave `id` + valore uuid → **tradotto** in `id::text` via
    `target_table.uid` (i chiamanti storici BE restano intatti); se il target
    non ha colonna `uid` o l'uuid non risolve → `E_SORG_NORM_NON_RISOLTA` (547);
  * formato non conforme al selector → `E_SORG_FORMATO` (546). Dal 2026-10-05 vale la
    **forma canonica** (`id::text`, `uid::text` minuscolo), con la stessa regola del guard
    ([script.fn_sorgente_chiave_id](/dbzero/script/funzioni/fn_sorgente_chiave_id) /
    [_uuid](/dbzero/script/funzioni/fn_sorgente_chiave_uuid)). Gli spazi attorno alla chiave
    il rubinetto li toglie da sé, prima del controllo;
  * tipo non censito/non attivo → `E_SORG_CONF`.
* A valle, il guard `trgfn_guard_sorgente_polimorfa_testuale` sulla tabella
  ri-valida formato ed esistenza (difesa in profondita' per i writer che
  saltano la fn).

---

### Chi la chiama

* `vendite.fn_upsert_commessa_attivita`, per ogni riga che viene da un documento
  spinto in commessa (`config.sorgenti.scope = 'PUSH_COMMESSA'`): **il link nasce
  con la riga**, nel DB (D-13, 2026-10-12).
* Il backend la chiamava a parte, prima della riga (`BaseSourceHandler`): con la
  madre che la chiama, quella chiamata trova il link gia' scritto e passa dal
  ramo idempotente; il ritiro e' una richiesta del brief.

---

### Output

Ritorna `id` del record in `vendite.commesse_sorgenti`.

---

{% include-markdown "signature-core.md" %}
