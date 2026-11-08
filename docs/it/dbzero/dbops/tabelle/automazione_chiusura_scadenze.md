{% include-markdown "it/dbzero/dbops/manual/automazione_chiusura_scadenze.md" %}
# 📚 Tabella `automazione_chiusura_scadenze`

> 📝 **Descrizione**
>
> Configurazione del framework di chiusura automatica per scadenza. Ogni riga descrive una tabella target con ciclo stato + valido_al. Letta da dbops.fn_apply_chiusura_scadenze() chiamata dal job notturno chiusura_scadenze_daily (85_pgagent).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | smallint | NO |  |
| schema_tabella | text | NO |  |
| nome_tabella | text | NO |  |
| col_stato | text | NO |  |
| tipo_stato | text | NO |  |
| col_valido_al | text | NO | 'valido_al'::text |
| stato_attivo_codice | text | NO |  |
| stato_chiuso_codice | text | NO |  |
| fk_lookup_schema | text | YES |  |
| fk_lookup_table | text | YES |  |
| fk_lookup_codice_col | text | YES |  |
| fk_lookup_id_col | text | YES |  |
| attivo | boolean | NO | true |
| descrizione | text | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| classe | text | NO |  |
| verbo_chiusura | text | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_automazione_chiusura_scadenze_classe |  |
| CHECK | chk_automazione_chiusura_scadenze_fk_coerente |  |
| CHECK | chk_automazione_chiusura_scadenze_tipo_stato |  |
| CHECK | chk_automazione_chiusura_scadenze_verbo_qualificato |  |
| PRIMARY KEY | pk_automazione_chiusura_scadenze | id |
| UNIQUE | uq_automazione_chiusura_scadenze_target | schema_tabella, nome_tabella |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_automazione_chiusura_scadenze_attivo | `CREATE INDEX ix_automazione_chiusura_scadenze_attivo ON dbops.automazione_chiusura_scadenze USING btree (id) WHERE (attivo IS TRUE)` |
| pk_automazione_chiusura_scadenze | `CREATE UNIQUE INDEX pk_automazione_chiusura_scadenze ON dbops.automazione_chiusura_scadenze USING btree (id)` |
| uq_automazione_chiusura_scadenze_target | `CREATE UNIQUE INDEX uq_automazione_chiusura_scadenze_target ON dbops.automazione_chiusura_scadenze USING btree (schema_tabella, nome_tabella)` |

---
{% include-markdown "signature-core.md" %}
