# Vista `dbops.vw_parameter_fk_surrogate_dangling`

## 📘 Documentazione Concettuale

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [config.parameter_fk_surrogate](/dbzero/config/tabelle/parameter_fk_surrogate)
> [config.parameters](/dbzero/config/tabelle/parameters)
> [config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides)
>
Approfondimento funzioni:
> [script.fn_check_parameter_fk_surrogate](/dbzero/script/funzioni/fn_check_parameter_fk_surrogate)

### 🎯 Scopo Principale

(latest review 02-05-2026)

Vista diagnostica del framework FK-surrogata sui parametri. Enumera tutte le
righe in stato **dangling**: parametri (`default_value`) e override
(`overridden_value`) il cui valore corrente **non esiste piu'** nella tabella
di catalogo target indicata dal registry `config.parameter_fk_surrogate`.

### Perche' una vista diagnostica

Il dispatcher (`config.trgfn_parameters_fk_surrogate_dispatch` e speculare su
`parameter_overrides`) blocca INSERT/UPDATE quando il valore non esiste, ma
**non scatta su DELETE delle tabelle target**. Se viene cancellata una riga
in `config.utilities` o `config.tipi_soggetto_dettaglio` referenziata da un
parametro, il parametro resta "appeso" finche' non viene aggiornato.

Output non vuoto della vista = situazione da risolvere manualmente:

* UPDATE del parametro/override verso un valore valido, **oppure**
* ricreazione della riga di catalogo cancellata.

### Schema output

| Colonna | Tipo | Descrizione |
|---|---|---|
| `source` | text | `parameter` (riga di `config.parameters`) o `parameter_override` (riga di `config.parameter_overrides`). |
| `source_id` | bigint | PK della riga. |
| `code` | varchar | `parameters.code` (per gli override e' il code del parametro padre risolto via `parameter_id`). |
| `value` | text | `default_value` o `overridden_value` non valido. |
| `target` | text | Label `schema.table.column` del target del registry. |
| `matched_pattern` | varchar | Pattern matchato in `parameter_fk_surrogate.code_pattern`. |
| `matched_mode` | varchar | `EXACT` o `LIKE`. |

### Uso tipico

**Check post-deploy** (CI / smoke test):

```sql
SELECT count(*) FROM dbops.vw_parameter_fk_surrogate_dangling;
-- 0 atteso. Se > 0, fallire il deploy o emettere alert.
```

**Lista dettagliata** per intervento manuale:

```sql
SELECT source, code, value, target, matched_pattern
  FROM dbops.vw_parameter_fk_surrogate_dangling
 ORDER BY source, code;
```

**Filtro per pattern specifico**:

```sql
SELECT *
  FROM dbops.vw_parameter_fk_surrogate_dangling
 WHERE matched_pattern = 'DEFAULT_UTILITY';
```

### Note operative

* **Costo**: la vista esegue `script.fn_check_parameter_fk_surrogate` su ogni
  riga. Su volumi tipici (parametri + override = qualche decina di righe) il
  costo e' irrilevante. Non e' una vista materializzata: ogni interrogazione
  fa lookup live.
* **Non blocca**: e' diagnostica pura. Per bloccare cancellazioni che
  lascerebbero dangling, servirebbe un guard speculare BEFORE DELETE sulle
  tabelle target (rinviato finche' non si manifesta come problema reale).
* **Job pgAgent**: in futuro si puo' wrappare in un job di alert (es. mail
  oncall se count > 0). Non implementato in questo PR.
* **Idempotente**: se non ci sono righe dangling, la vista e' vuota.

---

{% include-markdown "signature-core.md" %}

---
