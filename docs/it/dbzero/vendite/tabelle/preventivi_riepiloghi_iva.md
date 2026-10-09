{% include-markdown "it/dbzero/vendite/manual/preventivi_riepiloghi_iva.md" %}
# 📚 Tabella `preventivi_riepiloghi_iva`

> 📝 **Descrizione**
>
> Riepilogo IVA aggregato per preventivo, pattern coerente con fatture_riepiloghi_iva. Popolato da vendite.fn_ricalcola_riepilogo_iva_preventivo. Group by (iva_id, natura_id, esigibilita, split_payment), calcolo fiscalmente corretto (ROUND aggregato, non per riga).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| preventivo_id | bigint | NO |  |
| iva_id | integer | YES |  |
| natura_id | integer | YES |  |
| esigibilita | character(1) | YES |  |
| split_payment | boolean | YES |  |
| imponibile | numeric | NO | 0 |
| imposta | numeric | NO | 0 |
| arrotondamento | numeric | NO | 0 |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_preventivi_riepiloghi_iva_arrotondamento_finito |  |
| CHECK | chk_preventivi_riepiloghi_iva_imponibile_finito |  |
| CHECK | chk_preventivi_riepiloghi_iva_imposta_finito |  |
| FOREIGN KEY | fk_preventivi_r_iva_iva | iva_id |
| FOREIGN KEY | fk_preventivi_r_iva_natura | natura_id |
| FOREIGN KEY | fk_preventivi_r_iva_preventivo | preventivo_id |
| PRIMARY KEY | pk_preventivi_r_iva | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_preventivi_r_iva | `CREATE UNIQUE INDEX pk_preventivi_r_iva ON vendite.preventivi_riepiloghi_iva USING btree (id)` |
| uq_preventivi_r_iva_key | `CREATE UNIQUE INDEX uq_preventivi_r_iva_key ON vendite.preventivi_riepiloghi_iva USING btree (preventivo_id, COALESCE(natura_id, 0), COALESCE(esigibilita, 'I'::bpchar), COALESCE(split_payment, false), COALESCE(iva_id, 0))` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_preventivi_riepiloghi_iva_a10_iva_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_preventivi_riepiloghi_iva_a10_iva_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_preventivi_riepiloghi_iva_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_preventivi_riepiloghi_iva_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
