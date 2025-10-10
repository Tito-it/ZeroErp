{% include-markdown "it/dbzero/config/manual/termini_pagamento.md" %}
# 📚 Tabella `termini_pagamento`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying | NO |  |
| codice_interno | character varying | NO |  |
| descrizione | character varying | NO |  |
| numero_rate | smallint | NO |  |
| unita_intervallo | character | NO |  |
| intervallo | smallint | YES |  |
| primo_offset_giorni | smallint | YES |  |
| tipo_offset | character | NO | 'N'::bpchar |
| ripartizione | character varying | NO | 'UGUALI'::character varying |
| arrotondamento_metodo | character varying | NO | 'HALF_UP'::character varying |
| arrotondamento_decimali | smallint | NO | 2 |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_termini_pag_arrotond_dec |  |
| CHECK | chk_termini_pag_numero_rate_pos |  |
| CHECK | chk_termini_pagamento_arrotondamento_metodo |  |
| CHECK | chk_termini_pagamento_intervallo_range |  |
| CHECK | chk_termini_pagamento_intervallo_uso |  |
| CHECK | chk_termini_pagamento_ripartizione |  |
| CHECK | chk_termini_pagamento_tipo_offset |  |
| PRIMARY KEY | pk_termini_pagamento | id |
| UNIQUE | uq_cfg_termini_pagamento_codice_interno | codice_interno |
| UNIQUE | uq_termini_pagamento_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_cfg_termini_pagamento_attivo | `CREATE INDEX ix_cfg_termini_pagamento_attivo ON config.termini_pagamento USING btree (attivo)` |
| ix_termini_pagamento_codice_interno_upper | `CREATE INDEX ix_termini_pagamento_codice_interno_upper ON config.termini_pagamento USING btree (upper((codice_interno)::text))` |
| ix_termini_pagamento_codice_upper | `CREATE INDEX ix_termini_pagamento_codice_upper ON config.termini_pagamento USING btree (upper((codice)::text))` |
| ix_termini_pagamento_descrizione_upper | `CREATE INDEX ix_termini_pagamento_descrizione_upper ON config.termini_pagamento USING btree (upper((descrizione)::text))` |
| pk_termini_pagamento | `CREATE UNIQUE INDEX pk_termini_pagamento ON config.termini_pagamento USING btree (id)` |
| uq_cfg_termini_pagamento_codice_interno | `CREATE UNIQUE INDEX uq_cfg_termini_pagamento_codice_interno ON config.termini_pagamento USING btree (codice_interno)` |
| uq_termini_pagamento_codice | `CREATE UNIQUE INDEX uq_termini_pagamento_codice ON config.termini_pagamento USING btree (codice)` |

---
{% include-markdown "signature-core.md" %}
