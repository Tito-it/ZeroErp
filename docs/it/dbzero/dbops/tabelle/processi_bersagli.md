{% include-markdown "it/dbzero/dbops/manual/processi_bersagli.md" %}
# 📚 Tabella `processi_bersagli`

> 📝 **Descrizione**
>
> Le tabelle che ogni processo scrive, con il percorso che porta all'emittente della riga. La leggono i presidi dbops.vw_processi_dominio_senza_emittente (processo di dominio senza bersagli, tabella o colonna inesistente, percorso non dichiarato) e dbops.vw_processi_dominio_senza_difesa (bersaglio senza policy o senza guard di scrittura), che trovano l'omissione prima che il processo giri. E' un elenco dichiarato: dice dove il processo scrive secondo chi l'ha registrato, non che scriva solo li'.

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
| debito_dichiarato | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_processi_bersagli_via_colonna |  |
| FOREIGN KEY | fk_processi_bersagli_emittente_via | emittente_via |
| FOREIGN KEY | fk_processi_bersagli_processi | processo_id |
| PRIMARY KEY | pk_processi_bersagli | id |
| UNIQUE | uq_processi_bersagli_target | processo_id, schema_tabella, nome_tabella |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_processi_bersagli_emittente_via | `CREATE INDEX ix_processi_bersagli_emittente_via ON dbops.processi_bersagli USING btree (emittente_via)` |
| ix_processi_bersagli_processo_id | `CREATE INDEX ix_processi_bersagli_processo_id ON dbops.processi_bersagli USING btree (processo_id)` |
| pk_processi_bersagli | `CREATE UNIQUE INDEX pk_processi_bersagli ON dbops.processi_bersagli USING btree (id)` |
| uq_processi_bersagli_target | `CREATE UNIQUE INDEX uq_processi_bersagli_target ON dbops.processi_bersagli USING btree (processo_id, schema_tabella, nome_tabella)` |

---
{% include-markdown "signature-core.md" %}
