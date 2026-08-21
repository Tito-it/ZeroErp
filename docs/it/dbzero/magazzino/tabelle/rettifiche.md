{% include-markdown "it/dbzero/magazzino/manual/rettifiche.md" %}
# 📚 Tabella `rettifiche`

> 📝 **Descrizione**
>
> Documento interno di rettifica inventariale

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| data | date | NO | CURRENT_DATE |
| stato_mag_rettifiche | character varying | NO | 'DRAFT'::character varying |
| magazzino_id | bigint | NO |  |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |
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
| CHECK | chk_mag_rettifiche_stato |  |
| FOREIGN KEY | fk_mag_rettifiche_magazzino | magazzino_id |
| PRIMARY KEY | pk_mag_rettifiche | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_mag_rettifiche_data | `CREATE INDEX ix_mag_rettifiche_data ON magazzino.rettifiche USING btree (data)` |
| ix_mag_rettifiche_stato | `CREATE INDEX ix_mag_rettifiche_stato ON magazzino.rettifiche USING btree (stato_mag_rettifiche)` |
| pk_mag_rettifiche | `CREATE UNIQUE INDEX pk_mag_rettifiche ON magazzino.rettifiche USING btree (id)` |
| uq_mag_rettifiche_source_fk | `CREATE UNIQUE INDEX uq_mag_rettifiche_source_fk ON magazzino.rettifiche USING btree (sorgente_tipo_id, sorgente_uid) WHERE ((sorgente_tipo_id IS NOT NULL) AND (sorgente_uid IS NOT NULL))` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_rettifiche_a10_magazzini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id', 'id')` |
| trg_rettifiche_a10_magazzini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id', 'id')` |
| trg_rettifiche_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_rettifiche_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_rettifiche_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_rettifiche_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_rettifiche_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('rettifiche_id')` |
| trg_rettifiche_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('rettifiche_id')` |

---
{% include-markdown "signature-core.md" %}
