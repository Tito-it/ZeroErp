{% include-markdown "it/dbzero/dbops/manual/processi_bersagli.md" %}
# 📚 Tabella `processi_bersagli`

> 📝 **Descrizione**
>
> Le tabelle che ogni processo SCRIVE, con il percorso che porta all'emittente. Serve al presidio «dichiarato DOMINIO ma senza percorso» (dbops.vw_processi_dominio_senza_emittente), che prende l'omissione di progetto PRIMA che il processo giri — a runtime non e' recuperabile. ⚠️ E' un elenco DICHIARATO: prova che qualcuno ha detto dove il processo scrive, non che scriva solo li'. Brief: brief-db-processi-automatici-identita-e-perimetro §2.3.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| processo_id | integer | NO |  |
| schema_tabella | text | NO |  |
| nome_tabella | text | NO |  |
| emittente_via | text | YES |  |
| emittente_colonna | text | YES |  |
| note | text | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| debito_dichiarato | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_processi_bersagli_via |  |
| CHECK | chk_processi_bersagli_via_colonna |  |
| FOREIGN KEY | fk_processi_bersagli_processi | processo_id |
| PRIMARY KEY | pk_processi_bersagli | id |
| UNIQUE | uq_processi_bersagli_target | processo_id, schema_tabella, nome_tabella |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_processi_bersagli_processo_id | `CREATE INDEX ix_processi_bersagli_processo_id ON dbops.processi_bersagli USING btree (processo_id)` |
| pk_processi_bersagli | `CREATE UNIQUE INDEX pk_processi_bersagli ON dbops.processi_bersagli USING btree (id)` |
| uq_processi_bersagli_target | `CREATE UNIQUE INDEX uq_processi_bersagli_target ON dbops.processi_bersagli USING btree (processo_id, schema_tabella, nome_tabella)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_processi_bersagli_audit_data_user_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_processi_bersagli_audit_data_user_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_processi_bersagli_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_processi_bersagli_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
