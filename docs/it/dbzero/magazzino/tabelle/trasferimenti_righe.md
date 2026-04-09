# 📚 Tabella `trasferimenti_righe`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| trasferimento_id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| qta | numeric | NO |  |
| lotto | character varying | YES |  |
| seriale | character varying | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_mag_trasferimenti_qta_pos |  |
| FOREIGN KEY | fk_mag_trasferimenti_righe_articolo | articolo_id |
| FOREIGN KEY | fk_mag_trasferimenti_righe_testata | trasferimento_id |
| PRIMARY KEY | pk_mag_trasferimenti_righe | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_magazzino_trasferimenti_righe_articolo_id | `CREATE INDEX ix_magazzino_trasferimenti_righe_articolo_id ON magazzino.trasferimenti_righe USING btree (articolo_id)` |
| pk_mag_trasferimenti_righe | `CREATE UNIQUE INDEX pk_mag_trasferimenti_righe ON magazzino.trasferimenti_righe USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_trasferimenti_righe_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_trasferimenti_righe_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_trasferimenti_righe_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_trasferimenti_righe_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_trasferimenti_righe_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_trasferimenti_righe_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_trasferimenti_righe_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('trasferimenti_righe_id')` |
| trg_trasferimenti_righe_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('trasferimenti_righe_id')` |

---
{% include-markdown "signature-core.md" %}
