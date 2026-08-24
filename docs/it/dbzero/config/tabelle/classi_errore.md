{% include-markdown "it/dbzero/config/manual/classi_errore.md" %}
# 📚 Tabella `classi_errore`

> 📝 **Descrizione**
>
> Vocabolario di CHE COSA e' un errore, in lingua di dominio: il tipo di rifiuto, non il suo trasporto. La mappa classe -&gt; HTTP status vive nel backend. Popolata dal seed 80_data.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| classe | text | NO |  |
| descrizione | text | NO |  |
| obsoleto_dal | date | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_classi_errore_classe_non_vuota |  |
| PRIMARY KEY | pk_classi_errore | classe |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_classi_errore | `CREATE UNIQUE INDEX pk_classi_errore ON config.classi_errore USING btree (classe)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_classi_errore_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_classi_errore_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
