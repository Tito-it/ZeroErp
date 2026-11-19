{% include-markdown "it/dbzero/dbops/manual/porte_manutenzione_passaggi.md" %}
# 📚 Tabella `porte_manutenzione_passaggi`

> 📝 **Descrizione**
>
> Il diario delle porte di manutenzione: una riga per ogni riga passata da una porta che solo il migratore apre a mano (bonifica, refuso, DELETE forward-only). La scrive solo script.fn_porta_manutenzione_aperta quando la porta si apre (GUC accesa e sessione del migratore); l'app la legge soltanto. Le porte di verbo, che una funzione apre per se', non passano di qui.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| chiave | text | NO |  |
| schema_name | text | NO |  |
| table_name | text | NO |  |
| riga_id | text | YES |  |
| operazione | text | NO |  |
| utente_sessione | text | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_porte_manutenzione_passaggi_chiave |  |
| CHECK | chk_porte_manutenzione_passaggi_nome_tabella |  |
| CHECK | chk_porte_manutenzione_passaggi_operazione |  |
| PRIMARY KEY | pk_porte_manutenzione_passaggi | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_porte_manutenzione_passaggi_tabella | `CREATE INDEX ix_porte_manutenzione_passaggi_tabella ON dbops.porte_manutenzione_passaggi USING btree (schema_name, table_name, data_insert)` |
| pk_porte_manutenzione_passaggi | `CREATE UNIQUE INDEX pk_porte_manutenzione_passaggi ON dbops.porte_manutenzione_passaggi USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_porte_manutenzione_passaggi_gen_tx_id_ins | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
