{% include-markdown "it/dbzero/storico/manual/_legacy_risorse_umane_auth_user.md" %}
# 📚 Tabella `_legacy_risorse_umane_auth_user`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico._legacy_risorse_umane_auth_user_id_seq'::regclass) |
| _legacy_risorse_umane_auth_user_id | bigint | NO |  |
| change_type | character | YES | 'A'::bpchar |
| tipo_operazione | smallint | YES |  |
| snapshot | jsonb | YES |  |
| user_insert | text | YES | CURRENT_USER |
| data_insert | timestamp with time zone | YES | now() |
| tx_id | uuid | YES |  |
| valid_from | timestamp with time zone | YES | now() |
| valid_to | timestamp with time zone | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_storico__legacy_risorse_umane_auth_user | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix__legacy_risorse_umane_auth_user__legacy_risorse_umane_auth_u | `CREATE INDEX ix__legacy_risorse_umane_auth_user__legacy_risorse_umane_auth_u ON storico._legacy_risorse_umane_auth_user USING btree (_legacy_risorse_umane_auth_user_id)` |
| pk_storico__legacy_risorse_umane_auth_user | `CREATE UNIQUE INDEX pk_storico__legacy_risorse_umane_auth_user ON storico._legacy_risorse_umane_auth_user USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_legacy_risorse_umane_auth_user_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_legacy_risorse_umane_auth_user_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
