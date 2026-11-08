{% include-markdown "it/dbzero/anagrafiche/manual/gestori.md" %}
# 📚 Tabella `gestori`

> 📝 **Descrizione**
>
> Società gestore del Sistema Informativo. Referenziata esclusivamente tramite soggetto_ruolo_id (legame soggetto↔ruolo gestito in anagrafiche.soggetti_ruoli).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| soggetto_ruolo_id | bigint | NO |  |
| descrizione | character varying(50) | NO |  |
| cd_prod_software | character varying(20) | NO |  |
| valuta_id | integer | NO |  |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_gestori_cd_prod_software_non_vuoto |  |
| CHECK | chk_gestori_descrizione_non_vuota |  |
| FOREIGN KEY | fk_soggetti_ruoli_anagrafiche | soggetto_ruolo_id |
| FOREIGN KEY | fk_valute_config | valuta_id |
| PRIMARY KEY | pk_gestori | id |
| UNIQUE | uq_gestori_soggetto_ruolo | soggetto_ruolo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_anagrafiche_gestori_valuta_id | `CREATE INDEX ix_anagrafiche_gestori_valuta_id ON anagrafiche.gestori USING btree (valuta_id)` |
| pk_gestori | `CREATE UNIQUE INDEX pk_gestori ON anagrafiche.gestori USING btree (id)` |
| uq_gestori_soggetto_ruolo | `CREATE UNIQUE INDEX uq_gestori_soggetto_ruolo ON anagrafiche.gestori USING btree (soggetto_ruolo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_gestori_a10_delete_block_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_delete_block_by_guc('zeroerp.maintenance_ruoli_delete')` |
| trg_gestori_a10_guard_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_gestori_guard()` |
| trg_gestori_a10_guard_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_gestori_guard()` |
| trg_gestori_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_gestori_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_gestori_guard_ruolo_gestore_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_gestori_guard_ruolo_gestore()` |
| trg_gestori_guard_ruolo_gestore_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_gestori_guard_ruolo_gestore()` |

---
{% include-markdown "signature-core.md" %}
