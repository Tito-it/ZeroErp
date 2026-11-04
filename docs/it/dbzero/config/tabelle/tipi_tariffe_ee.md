{% include-markdown "it/dbzero/config/manual/tipi_tariffe_ee.md" %}
# 📚 Tabella `tipi_tariffe_ee`

> 📝 **Descrizione**
>
> Tipologia Tariffa mercato elettrico

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(20) | NO |  |
| gruppo_tariffa_ee | character varying(2) | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_tipi_tariffe_ee | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_tariffe_ee | `CREATE UNIQUE INDEX pk_tipi_tariffe_ee ON config.tipi_tariffe_ee USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_tariffe_ee_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_tipi_tariffe_ee_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |

---
{% include-markdown "signature-core.md" %}
