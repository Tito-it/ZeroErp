{% include-markdown "it/dbzero/config/manual/codici_errore.md" %}
# 📚 Tabella `codici_errore`

> 📝 **Descrizione**
>
> Identita' di un codice errore: che COSA e' (classe) e se e' ancora in servizio (obsoleto_dal). La FRASE che l'operatore legge sta in config.messaggi_errore, chiavata (codice, lingua). Popolata dal seed 80_data.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| codice | text | NO |  |
| classe | text | NO |  |
| obsoleto_dal | date | YES |  |
| note | text | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| causa_fallimento | text | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_codici_errore_codice_non_vuoto |  |
| CHECK | chk_codici_errore_note_una_riga |  |
| FOREIGN KEY | fk_codici_errore_cause_fallimento | causa_fallimento |
| FOREIGN KEY | fk_codici_errore_classi_errore | classe |
| PRIMARY KEY | pk_codici_errore | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_codici_errore | `CREATE UNIQUE INDEX pk_codici_errore ON config.codici_errore USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_codici_errore_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_codici_errore_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_codici_errore_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_codici_errore_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
