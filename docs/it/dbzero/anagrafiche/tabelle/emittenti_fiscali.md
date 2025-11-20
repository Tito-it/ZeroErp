# 📚 Tabella `emittenti_fiscali`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| soggetto_ruolo_id | bigint | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| attivo | boolean | NO | true |
| regime_fiscale_rf | character varying | YES |  |
| esigibilita_iva_default | character | YES |  |
| split_payment_default | boolean | YES |  |
| bollo_auto | boolean | YES |  |
| bollo_soglia | numeric | YES |  |
| rounding_policy | character varying | YES |  |
| brand_meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_emittenti_fiscali_bollo_soglia |  |
| CHECK | chk_emittenti_fiscali_codice_non_vuoto |  |
| CHECK | chk_emittenti_fiscali_esigibilita |  |
| FOREIGN KEY | fk_emittenti_fiscali_ruolo | soggetto_ruolo_id |
| PRIMARY KEY | pk_emittf | id |
| UNIQUE | uq:codice | codice |
| UNIQUE | uq_emittenti_fiscali_ruolo | soggetto_ruolo_id |
| UNIQUE | uq_emittenti_fiscali_uid | uid |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_emittenti_fiscali_attivo | `CREATE INDEX ix_emittenti_fiscali_attivo ON anagrafiche.emittenti_fiscali USING btree (attivo)` |
| pk_emittf | `CREATE UNIQUE INDEX pk_emittf ON anagrafiche.emittenti_fiscali USING btree (id)` |
| uq:codice | `CREATE UNIQUE INDEX "uq:codice" ON anagrafiche.emittenti_fiscali USING btree (codice)` |
| uq_emittenti_fiscali_ruolo | `CREATE UNIQUE INDEX uq_emittenti_fiscali_ruolo ON anagrafiche.emittenti_fiscali USING btree (soggetto_ruolo_id)` |
| uq_emittenti_fiscali_uid | `CREATE UNIQUE INDEX uq_emittenti_fiscali_uid ON anagrafiche.emittenti_fiscali USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_emittenti_fiscali_a10_protect_codice_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_protect_codice()` |
| trg_emittenti_fiscali_check_ruolo_emi_fis_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_check_ruolo_emi_fis()` |
| trg_emittenti_fiscali_check_ruolo_emi_fis_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_check_ruolo_emi_fis()` |
| trg_emittenti_fiscali_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_normalize()` |
| trg_emittenti_fiscali_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_normalize()` |

---
{% include-markdown "signature-core.md" %}
