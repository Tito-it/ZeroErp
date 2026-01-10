{% include-markdown "it/dbzero/anagrafiche/manual/catasto_unita_immobiliari.md" %}
# 📚 Tabella `catasto_unita_immobiliari`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| sezione_catastale | character | YES |  |
| foglio_catastale | character | YES |  |
| particella | character | YES |  |
| subalterno | character | YES |  |
| categoria_catastale | character varying | YES |  |
| classe_catastale | character varying | YES |  |
| rendita_catastale | numeric | YES |  |
| consistenza | integer | YES |  |
| tipo_accatastamento | character | YES |  |
| immobile_rurale | boolean | NO | false |
| destinazione_immobile | character | YES |  |
| anno_protocollo | integer | YES |  |
| superficie | integer | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_catasto_unita_immobiliari | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_catasto_unita_immobiliari | `CREATE UNIQUE INDEX pk_catasto_unita_immobiliari ON anagrafiche.catasto_unita_immobiliari USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_catasto_unita_immobiliari_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_catasto_unita_immobiliari_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_catasto_unita_immobiliari_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_catasto_unita_immobiliari_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('catasto_unita_immobiliari_id')` |
| trg_catasto_unita_immobiliari_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('catasto_unita_immobiliari_id')` |

---
{% include-markdown "signature-core.md" %}
