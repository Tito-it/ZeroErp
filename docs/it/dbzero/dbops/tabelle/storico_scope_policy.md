{% include-markdown "it/dbzero/dbops/manual/storico_scope_policy.md" %}
# 📚 Tabella `storico_scope_policy`

> 📝 **Descrizione**
>
> La mappa «dove sta l'emittente di questa tabella», una riga per madre storicizzata (chiave schema + tabella). La legge dbops.fn_storico_risolvi_scope quando il trigger di storico scrive una versione: il valore risolto si congela nella shadow (scope_emittente_fiscale_id) e non si ricalcola più — un archivio che cambia col presente non è un archivio. Cinque modi: EF (colonna emittente_fiscale_id in riga), SR (colonna emittente_soggetto_ruolo_id, convertita in EF 1:1), PADRE (si risale via FK e si continua sulla riga del padre, ricorsivamente), BA (un billing account ha esattamente un emittente), NESSUNO (la madre non è protetta: la shadow non si arma e la ragione dice perché). ⭐ È anche il registro del debito: una madre col trigger di storico senza riga, o in RLS con modo NESSUNO, è un rosso di db/pgtap/dbops/test-storico-scope-policy-v1.sql. Brief: brief-db-rls-storico-scope-congelato §4b (D3).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| schema_tabella | text | NO |  |
| nome_tabella | text | NO |  |
| modo | text | NO |  |
| colonna | text | YES |  |
| padre_schema | text | YES |  |
| padre_tabella | text | YES |  |
| ragione | text | YES |  |
| data_registrazione | date | NO | script.fn_data_operativa() |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_storico_scope_policy_forma |  |
| CHECK | chk_storico_scope_policy_modo |  |
| CHECK | chk_storico_scope_policy_ragione |  |
| FOREIGN KEY | fk_storico_scope_policy_padre | padre_schema, padre_tabella |
| PRIMARY KEY | pk_storico_scope_policy | id |
| UNIQUE | uq_storico_scope_policy_madre | schema_tabella, nome_tabella |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_storico_scope_policy | `CREATE UNIQUE INDEX pk_storico_scope_policy ON dbops.storico_scope_policy USING btree (id)` |
| uq_storico_scope_policy_madre | `CREATE UNIQUE INDEX uq_storico_scope_policy_madre ON dbops.storico_scope_policy USING btree (schema_tabella, nome_tabella)` |

---
{% include-markdown "signature-core.md" %}
