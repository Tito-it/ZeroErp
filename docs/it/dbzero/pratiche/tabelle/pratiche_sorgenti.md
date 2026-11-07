{% include-markdown "it/dbzero/pratiche/manual/pratiche_sorgenti.md" %}
# 📚 Tabella `pratiche_sorgenti`

> 📝 **Descrizione**
>
> Tabella ponte: collega pratiche a sorgenti esterne (preventivi, ordini, contratti).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| pratica_id | bigint | NO |  |
| sorgente_tipo_id | bigint | NO |  |
| sorgente_uid | text | NO |  |
| sorgente_riga | bigint | YES |  |
| ruolo_link | character varying(30) | NO | 'ROOT'::character varying |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| flusso_id | bigint | YES |  |
| sorgente_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_pratiche_sorgenti_ruolo |  |
| FOREIGN KEY | fk_pratiche_sorgenti_flusso | flusso_id |
| FOREIGN KEY | fk_pratiche_sorgenti_pratica | pratica_id |
| FOREIGN KEY | fk_pratiche_sorgenti_tipo | sorgente_tipo_id |
| PRIMARY KEY | pk_pratiche_sorgenti | id |
| UNIQUE | uq_pratiche_sorgenti_pratica_tipo_uid_ruolo | pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_pratiche_sorgenti_flusso_id | `CREATE INDEX ix_pratiche_sorgenti_flusso_id ON pratiche.pratiche_sorgenti USING btree (flusso_id)` |
| ix_pratiche_sorgenti_tipo_uid | `CREATE INDEX ix_pratiche_sorgenti_tipo_uid ON pratiche.pratiche_sorgenti USING btree (sorgente_tipo_id, sorgente_uid)` |
| pk_pratiche_sorgenti | `CREATE UNIQUE INDEX pk_pratiche_sorgenti ON pratiche.pratiche_sorgenti USING btree (id)` |
| uq_pratiche_sorgenti_flusso_root | `CREATE UNIQUE INDEX uq_pratiche_sorgenti_flusso_root ON pratiche.pratiche_sorgenti USING btree (flusso_id) WHERE (((ruolo_link)::text = 'ROOT'::text) AND (flusso_id IS NOT NULL))` |
| uq_pratiche_sorgenti_pratica_tipo_uid_ruolo | `CREATE UNIQUE INDEX uq_pratiche_sorgenti_pratica_tipo_uid_ruolo ON pratiche.pratiche_sorgenti USING btree (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_pratiche_sorgenti_a10_guard_coerenza_flusso_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_pratiche_sorgenti_guard_coerenza_flusso()` |
| trg_pratiche_sorgenti_a10_guard_coerenza_flusso_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_pratiche_sorgenti_guard_coerenza_flusso()` |
| trg_pratiche_sorgenti_a10_guard_sorgente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_sorgente_polimorfa_testuale()` |
| trg_pratiche_sorgenti_a10_guard_sorgente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_sorgente_polimorfa_testuale()` |
| trg_pratiche_sorgenti_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_pratiche_sorgenti_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_pratiche_sorgenti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_pratiche_sorgenti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_pratiche_sorgenti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_pratiche_sorgenti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_pratiche_sorgenti_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('pratiche_sorgenti_id')` |
| trg_pratiche_sorgenti_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('pratiche_sorgenti_id')` |

---
{% include-markdown "signature-core.md" %}
