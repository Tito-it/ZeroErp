{% include-markdown "it/dbzero/acquisti/manual/ddt_righe.md" %}
# 📚 Tabella `ddt_righe`

> 📝 **Descrizione**
>
> Righe DDT di acquisto (merce ricevuta).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| ddt_id | bigint | NO |  |
| riga_nr | integer | NO |  |
| articolo_id | uuid | NO |  |
| descrizione | character varying(150) | NO |  |
| uom_id | bigint | YES |  |
| qta | numeric(18,6) | NO |  |
| lotto | character varying(50) | YES |  |
| seriale | character varying(50) | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| hash_contenuto | character varying(64) | YES |  |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |
| sorgente_riga | bigint | YES |  |
| sorgente_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_ddt_acquisto_r_qta_pos |  |
| CHECK | chk_ddt_righe_qta_finito |  |
| FOREIGN KEY | fk_a_ddt_righe_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_ddt_acquisto_r_articolo | articolo_id |
| FOREIGN KEY | fk_ddt_acquisto_r_testata | ddt_id |
| FOREIGN KEY | fk_ddt_acquisto_r_uom | uom_id |
| PRIMARY KEY | pk_ddtar | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_acquisti_ddt_righe_articolo_id | `CREATE INDEX ix_acquisti_ddt_righe_articolo_id ON acquisti.ddt_righe USING btree (articolo_id)` |
| pk_ddtar | `CREATE UNIQUE INDEX pk_ddtar ON acquisti.ddt_righe USING btree (id)` |
| uq_ddt_acquisto_r_riga_nr | `CREATE UNIQUE INDEX uq_ddt_acquisto_r_riga_nr ON acquisti.ddt_righe USING btree (ddt_id, riga_nr)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ddt_righe_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_ddt_righe_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_ddt_righe_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_ddt_righe_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_ddt_righe_a10_unita_misura_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id', 'id')` |
| trg_ddt_righe_a10_unita_misura_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id', 'id')` |
| trg_ddt_righe_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ddt_righe_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ddt_righe_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ddt_righe_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ddt_righe_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('ddt_righe_id')` |
| trg_ddt_righe_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('ddt_righe_id')` |

---
{% include-markdown "signature-core.md" %}
