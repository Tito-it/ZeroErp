{% include-markdown "it/dbzero/anagrafiche/manual/gestori.md" %}
# 📚 Tabella `gestori`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| soggetto_ruolo_id | bigint | NO |  |
| descrizione | character | NO |  |
| cd_prod_software | character | NO |  |
| valuta_id | integer | NO |  |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_soggetti_ruoli_anagrafiche | soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id |
| FOREIGN KEY | fk_valute_config | valuta_id |
| PRIMARY KEY | pk_gestori | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_anagrafiche_gestori_soggetto_ruolo_id | `CREATE INDEX ix_anagrafiche_gestori_soggetto_ruolo_id ON anagrafiche.gestori USING btree (soggetto_ruolo_id)` |
| ix_anagrafiche_gestori_valuta_id | `CREATE INDEX ix_anagrafiche_gestori_valuta_id ON anagrafiche.gestori USING btree (valuta_id)` |
| pk_gestori | `CREATE UNIQUE INDEX pk_gestori ON anagrafiche.gestori USING btree (id)` |
| uq_gestori_singleton | `CREATE INDEX uq_gestori_singleton ON anagrafiche.gestori USING gist (id) WHERE (id IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_gestori_a10_guard_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_gestori_guard()` |
| trg_gestori_a10_guard_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_gestori_guard()` |
| trg_gestori_audit_data_user_generic_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_gestori_check_ruolo_gestore_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_gestori_check_ruolo_gestore()` |
| trg_gestori_check_ruolo_gestore_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_gestori_check_ruolo_gestore()` |

---
{% include-markdown "signature-core.md" %}
