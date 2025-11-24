{% include-markdown "it/dbzero/anagrafiche/manual/conti_bancari.md" %}
# 📚 Tabella `conti_bancari`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| iban | character varying | NO |  |
| bic_swift | character varying | YES |  |
| intestatario_predefinito | character varying | YES |  |
| paese | character | YES |  |
| attivo | boolean | NO | true |
| verificato | boolean | NO | false |
| meta | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |
| bank_branch_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_conti_bancari_bic_fmt |  |
| CHECK | chk_conti_bancari_iban_fmt |  |
| CHECK | chk_conti_bancari_paese_fmt |  |
| FOREIGN KEY | fk_conti_bancari_bank_branches | bank_branch_id |
| PRIMARY KEY | pk_conti_bancari | id |
| UNIQUE | uq_conti_bancari_iban | iban |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_conti_bancari_attivo | `CREATE INDEX ix_conti_bancari_attivo ON anagrafiche.conti_bancari USING btree (attivo)` |
| pk_conti_bancari | `CREATE UNIQUE INDEX pk_conti_bancari ON anagrafiche.conti_bancari USING btree (id)` |
| uq_conti_bancari_iban | `CREATE UNIQUE INDEX uq_conti_bancari_iban ON anagrafiche.conti_bancari USING btree (iban)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_conti_bancari_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_conti_bancari_normalize()` |
| trg_conti_bancari_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_conti_bancari_normalize()` |

---
{% include-markdown "signature-core.md" %}
