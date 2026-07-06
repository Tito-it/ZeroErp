## 📘 Documentazione Funzione – `pratiche.trgfn_documento_reconcile_proiezione`

> 👀 **Vedi anche**
>
Funzioni / oggetti collegati:
>
> [pratiche.fn_reconcile_sorgente](/dbzero/pratiche/funzioni/fn_reconcile_sorgente)
> [pratiche.reconcile_errori](/dbzero/pratiche/tabelle/reconcile_errori)
> [config.sorgenti](/dbzero/config/tabelle/sorgenti)

---
### 🎯 Scopo Principale
(review 06-07-2026 — GUIDA D4, brief-db-guida-avanza-esito-proiettato)

**Trigger-function generica di innesco** (`G3b`) dell'avanzamento su esito proiettato. Da
agganciare in `AFTER UPDATE OF <colonna_stato>` a **ogni tabella-documento** del roll-out
(pilota: `vendite.preventivi`). Dopo un cambio-stato del documento — su **qualsiasi** percorso
di scrittura, **standalone incluso** — invoca `pratiche.fn_reconcile_sorgente(tipo, uid)`.

Generica e parametrica nello stile dei `dbops.trgfn_*`: un solo corpo, N agganci per-dominio.

---

### Parametrizzazione (argomenti del trigger)

Gli argomenti li fornisce il **seed per-dominio** nella `CREATE TRIGGER … EXECUTE FUNCTION …`,
in modo **esplicito** (D-B9): **niente** reverse-lookup da `config.sorgenti.target_table` (una
stessa `target_table` può avere più righe per `scope`/`tipo_doc_fiscale` → ambiguo).

| Argomento | Descrizione |
|-----------|-------------|
| `TG_ARGV[0]` | `sorgente_tipo_id` (`config.sorgenti.id`) del documento. |
| `TG_ARGV[1]` | Nome della colonna chiave nativa: `'id'` oppure `'uid'` (da `config.sorgenti.key_selector`). L'UID si estrae con `to_jsonb(NEW) ->> TG_ARGV[1]`, senza SQL dinamico. |

---

### Best-effort — documento sovrano (D-B7)

La chiamata a `fn_reconcile_sorgente` è racchiusa in un blocco `BEGIN … EXCEPTION WHEN OTHERS`
così che **un errore lato pratiche non propaghi mai** e **non faccia rollback** del cambio-stato
del documento. L'errore è **loggato** su `pratiche.reconcile_errori` (l'`INSERT` del handler
`EXCEPTION` gira nella transazione esterna, fuori dal savepoint rollbackato). Il trigger è
`AFTER` e ritorna `NULL`.

---

### Aggancio per-dominio (esempio pilota PREVENTIVI)

```sql
CREATE TRIGGER trg_preventivi_z90_reconcile_proiezione_upd
  AFTER UPDATE OF stato_doc_preventivo_id
  ON vendite.preventivi
  FOR EACH ROW
  WHEN (OLD.stato_doc_preventivo_id IS DISTINCT FROM NEW.stato_doc_preventivo_id)
  EXECUTE FUNCTION pratiche.trgfn_documento_reconcile_proiezione('2', 'uid');
```

**Dormiente e sicuro** finché non esiste un binding `template_flussi_avanzamento_proiezione`
sullo step: `fn_reconcile_sorgente` non trova candidati e ritorna 0 (no-op).

---

{% include-markdown "signature-core.md" %}
