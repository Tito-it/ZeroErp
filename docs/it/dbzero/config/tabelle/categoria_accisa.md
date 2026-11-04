{% include-markdown "it/dbzero/config/manual/categoria_accisa.md" %}
# 📚 Tabella `categoria_accisa`

> 📝 **Descrizione**
>
> Categoria accisa per utility

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| utility_id | integer | NO |  |
| codice | character varying(20) | NO |  |
| descrizione | character varying(200) | NO | ''::character varying |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_categoria_accisa_utility | utility_id |
| PRIMARY KEY | pk_categoria_accisa | id |
| UNIQUE | uq_categoria_accisa_codice_utility | codice, utility_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_categoria_accisa_descrizione | `CREATE INDEX ix_categoria_accisa_descrizione ON config.categoria_accisa USING btree (descrizione)` |
| ix_config_categoria_accisa_utility_id | `CREATE INDEX ix_config_categoria_accisa_utility_id ON config.categoria_accisa USING btree (utility_id)` |
| pk_categoria_accisa | `CREATE UNIQUE INDEX pk_categoria_accisa ON config.categoria_accisa USING btree (id)` |
| uq_categoria_accisa_codice_utility | `CREATE UNIQUE INDEX uq_categoria_accisa_codice_utility ON config.categoria_accisa USING btree (codice, utility_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_categoria_accisa_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_categoria_accisa_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |

---
{% include-markdown "signature-core.md" %}
