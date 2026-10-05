## 📘 Documentazione Concettuale – Funzione `vendite.fn_link_commessa_sorgente`
### 🎯 Scopo Principale
(latest review 24-02-2026)
Collega la ROOT source a una commessa in modo idempotente e coerente.

---

### Regole applicate

* Una commessa puo` avere una sola ROOT (`ruolo_link='ROOT'`); le sorgenti
  successive diventano COLLEGATO (multi-sorgente, la fn decide il ruolo).
* Una sorgente (tipo + uid) appartiene a una sola commessa
  (`uq_commesse_sorgenti_src_uid`); se gia` su altra commessa:
  `E_COMMESSA_SORGENTE_ALTRA_COMMESSA`.
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

### Output

Ritorna `id` del record in `vendite.commesse_sorgenti`.

---

{% include-markdown "signature-core.md" %}
