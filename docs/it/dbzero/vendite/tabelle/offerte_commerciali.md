{% include-markdown "it/dbzero/vendite/manual/offerte_commerciali.md" %}
# 📚 Tabella `offerte_commerciali`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| codice | text | NO |  |
| emittente_fiscale_id | bigint | NO |  |
| billing_account_id | bigint | NO |  |
| istanza_utility_id | bigint | NO |  |
| utility_id | integer | NO |  |
| listino_id | bigint | NO |  |
| listino_versione_id | bigint | YES |  |
| valore_variazione_globale | numeric | YES | 0 |
| tipo_variazione_globale | character varying | YES |  |
| validita_dal | date | NO |  |
| validita_al | date | YES |  |
| stato_doc_offerta_id | bigint | NO |  |
| revisione_numero | integer | NO | 1 |
| revisione_padre_id | bigint | YES |  |
| data_emissione | timestamp with time zone | YES |  |
| data_accettazione | timestamp with time zone | YES |  |
| data_rifiuto | timestamp with time zone | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |
| motivazione_rifiuto | text | YES |  |
| data_annullamento | timestamp with time zone | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_offerte_revisione_numero |  |
| CHECK | chk_offerte_tipo_variazione_globale |  |
| CHECK | chk_offerte_validita_date |  |
| CHECK | chk_offerte_variazione_globale_coerenza |  |
| FOREIGN KEY | fk_offerte_commerciali_billing_account | billing_account_id |
| FOREIGN KEY | fk_offerte_commerciali_emittente_fiscale | emittente_fiscale_id |
| FOREIGN KEY | fk_offerte_commerciali_istanza_utility | istanza_utility_id |
| FOREIGN KEY | fk_offerte_commerciali_listino | listino_id |
| FOREIGN KEY | fk_offerte_commerciali_listino_versione | listino_versione_id |
| FOREIGN KEY | fk_offerte_commerciali_revisione_padre | revisione_padre_id |
| FOREIGN KEY | fk_offerte_commerciali_stato_doc | stato_doc_offerta_id |
| FOREIGN KEY | fk_offerte_commerciali_utility | utility_id |
| PRIMARY KEY | pk_offerte_commerciali | id |
| UNIQUE | uq_offerte_commerciali_codice | codice |
| UNIQUE | uq_offerte_commerciali_uid | uid |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_offerte_commerciali_billing_account | `CREATE INDEX ix_offerte_commerciali_billing_account ON vendite.offerte_commerciali USING btree (billing_account_id)` |
| ix_offerte_commerciali_istanza_utility | `CREATE INDEX ix_offerte_commerciali_istanza_utility ON vendite.offerte_commerciali USING btree (istanza_utility_id)` |
| ix_offerte_commerciali_listino_versione | `CREATE INDEX ix_offerte_commerciali_listino_versione ON vendite.offerte_commerciali USING btree (listino_versione_id) WHERE (listino_versione_id IS NOT NULL)` |
| ix_offerte_commerciali_revisione_padre | `CREATE INDEX ix_offerte_commerciali_revisione_padre ON vendite.offerte_commerciali USING btree (revisione_padre_id) WHERE (revisione_padre_id IS NOT NULL)` |
| ix_offerte_commerciali_stato_doc | `CREATE INDEX ix_offerte_commerciali_stato_doc ON vendite.offerte_commerciali USING btree (stato_doc_offerta_id)` |
| pk_offerte_commerciali | `CREATE UNIQUE INDEX pk_offerte_commerciali ON vendite.offerte_commerciali USING btree (id)` |
| uq_offerte_commerciali_codice | `CREATE UNIQUE INDEX uq_offerte_commerciali_codice ON vendite.offerte_commerciali USING btree (codice)` |
| uq_offerte_commerciali_uid | `CREATE UNIQUE INDEX uq_offerte_commerciali_uid ON vendite.offerte_commerciali USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_offerte_commerciali_a10_guard_transizione_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_offerte_commerciali_guard_transizione()` |

---
{% include-markdown "signature-core.md" %}
