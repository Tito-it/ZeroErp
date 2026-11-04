{% include-markdown "it/dbzero/config/manual/tipi_utenze.md" %}
# 📚 Tabella `tipi_utenze`

> 📝 **Descrizione**
>
> Tipo utenza. Utilizzata per definire il tipo d’uso (Domestico, Altri usi, Condominio, Pubblico).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(20) | NO |  |
| descrizione | character varying(100) | NO |  |
| descrizione_breve | character varying(40) | NO |  |
| iva_id | integer | YES |  |
| utility_id | integer | YES |  |
| tipo_pdr_std | character(1) | NO | '0'::bpchar |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_tipi_utenze_tipo_pdr_std |  |
| FOREIGN KEY | fk_tipi_utenze_iva | iva_id |
| FOREIGN KEY | fk_tipi_utenze_utility | utility_id |
| PRIMARY KEY | pk_tipi_utenze | id |
| UNIQUE | uq_tipi_utenze_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_config_tipi_utenze_iva_id | `CREATE INDEX ix_config_tipi_utenze_iva_id ON config.tipi_utenze USING btree (iva_id)` |
| ix_config_tipi_utenze_utility_id | `CREATE INDEX ix_config_tipi_utenze_utility_id ON config.tipi_utenze USING btree (utility_id)` |
| ix_tipi_utenze_descrizione | `CREATE INDEX ix_tipi_utenze_descrizione ON config.tipi_utenze USING btree (descrizione)` |
| pk_tipi_utenze | `CREATE UNIQUE INDEX pk_tipi_utenze ON config.tipi_utenze USING btree (id)` |
| uq_tipi_utenze_codice | `CREATE UNIQUE INDEX uq_tipi_utenze_codice ON config.tipi_utenze USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_utenze_a10_iva_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_tipi_utenze_a10_iva_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_tipi_utenze_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_tipi_utenze_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |

---
{% include-markdown "signature-core.md" %}
