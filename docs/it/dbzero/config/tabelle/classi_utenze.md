{% include-markdown "it/dbzero/config/manual/classi_utenze.md" %}
# 📚 Tabella `classi_utenze`

> 📝 **Descrizione**
>
> Classi di utenza e parametri EE collegati a tipo_utenza/tariffa/categoria accisa

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(20) | NO |  |
| descrizione | character varying(100) | NO |  |
| descrizione_breve | character varying(40) | NO |  |
| tipo_utenza_id | integer | YES |  |
| categoria_accisa_id | integer | YES |  |
| pot_contratto_min_ee | numeric(9,3) | NO |  |
| pot_contratto_max_ee | numeric(9,3) | NO |  |
| tipi_tariffa_ee_id | integer | YES |  |
| tipo_pod | character varying(2) | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_classi_utenze_pot_contratto_max_ee_finito |  |
| CHECK | chk_classi_utenze_pot_contratto_min_ee_finito |  |
| CHECK | chk_classi_utenze_tipo_pod |  |
| FOREIGN KEY | fk_classi_utenze_categoria_accisa | categoria_accisa_id |
| FOREIGN KEY | fk_classi_utenze_tipi_tariffa_ee | tipi_tariffa_ee_id |
| FOREIGN KEY | fk_classi_utenze_tipi_utenze | tipo_utenza_id |
| PRIMARY KEY | pk_classi_utenze | id |
| UNIQUE | uq_classi_utenze_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_classi_utenze_descrizione | `CREATE INDEX ix_classi_utenze_descrizione ON config.classi_utenze USING btree (descrizione)` |
| ix_config_classi_utenze_categoria_accisa_id | `CREATE INDEX ix_config_classi_utenze_categoria_accisa_id ON config.classi_utenze USING btree (categoria_accisa_id)` |
| ix_config_classi_utenze_tipi_tariffa_ee_id | `CREATE INDEX ix_config_classi_utenze_tipi_tariffa_ee_id ON config.classi_utenze USING btree (tipi_tariffa_ee_id)` |
| ix_config_classi_utenze_tipo_utenza_id | `CREATE INDEX ix_config_classi_utenze_tipo_utenza_id ON config.classi_utenze USING btree (tipo_utenza_id)` |
| pk_classi_utenze | `CREATE UNIQUE INDEX pk_classi_utenze ON config.classi_utenze USING btree (id)` |
| uq_classi_utenze_codice | `CREATE UNIQUE INDEX uq_classi_utenze_codice ON config.classi_utenze USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_classi_utenze_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_classi_utenze_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |

---
{% include-markdown "signature-core.md" %}
