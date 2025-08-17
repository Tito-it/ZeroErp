{% include-markdown "it/dbzero/config/manual/iva.md" %}
# 📚 Tabella `iva`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.iva_id_seq'::regclass) |
| codice | character | NO |  |
| descrizione | character varying | NO |  |
| descrizione_breve | character varying | NO |  |
| aliquota_iva | numeric | NO | 0 |
| assoggettamento_iva | character | NO | ''::bpchar |
| natura_iva_id | integer | YES |  |
| conto_iva_acquisti_id | integer | YES |  |
| conto_iva_vendita_id | integer | YES |  |
| id_iva_split | integer | YES |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_iva_assoggettamento |  |
| CHECK | chk_iva_assoggettamento_aliquota |  |
| FOREIGN KEY | fk_iva_conto_acq | conto_iva_acquisti_id |
| FOREIGN KEY | fk_iva_conto_ven | conto_iva_vendita_id |
| FOREIGN KEY | fk_iva_natura | natura_iva_id |
| FOREIGN KEY | fk_iva_split | id_iva_split |
| PRIMARY KEY | pk_iva | id |
| UNIQUE | uq_iva_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_iva_desc | `CREATE INDEX ix_iva_desc ON config.iva USING btree (descrizione)` |
| pk_iva | `CREATE UNIQUE INDEX pk_iva ON config.iva USING btree (id)` |
| uq_iva_codice | `CREATE UNIQUE INDEX uq_iva_codice ON config.iva USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_iva_ins_upd_check_conti_iva | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_iva_ins_upd_check_conti_iva()` |
| trg_iva_ins_upd_check_conti_iva | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_iva_ins_upd_check_conti_iva()` |
| trg_upd_iva_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
---
{% include-markdown "signature-core.md" %}
