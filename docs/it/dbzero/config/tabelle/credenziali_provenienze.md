{% include-markdown "it/dbzero/config/manual/credenziali_provenienze.md" %}
# 📚 Tabella `credenziali_provenienze`

> 📝 **Descrizione**
>
> Freno sulla PROVENIENZA (D-1 riletta, 2026-09-24): le password sbagliate frenano la coppia credenziale + provenienza, non il titolare, che continua a entrare dalla sua macchina. Una riga esiste solo dopo un fallimento da quella provenienza e si cancella a un accesso riuscito o a un reset; chi sbaglia e non riprova lo toglie la retention (cleanup_at). La provenienza non e' una veste: il conto resta della credenziale, per tutte le porte. Scrivono solo le funzioni del login; all'app solo SELECT. Brief: brief-db-blocco-login-per-credenziale.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| credenziale_id | bigint | NO |  |
| provenienza | inet | NO |  |
| tentativi_falliti | integer | NO | 0 |
| bloccato_fino_a | timestamp with time zone | YES |  |
| ultimo_fallimento_at | timestamp with time zone | NO |  |
| cleanup_at | timestamp with time zone | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_credenziali_provenienze_tentativi |  |
| FOREIGN KEY | fk_credenziali_provenienze_credenziali | credenziale_id |
| PRIMARY KEY | pk_credenziali_provenienze | id |
| UNIQUE | uq_credenziali_provenienze_credenziale_provenienza | credenziale_id, provenienza |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_credenziali_provenienze | `CREATE UNIQUE INDEX pk_credenziali_provenienze ON config.credenziali_provenienze USING btree (id)` |
| uq_credenziali_provenienze_credenziale_provenienza | `CREATE UNIQUE INDEX uq_credenziali_provenienze_credenziale_provenienza ON config.credenziali_provenienze USING btree (credenziale_id, provenienza)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_credenziali_provenienze_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_credenziali_provenienze_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_credenziali_provenienze_m50_cleanup_at_ins | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_cleanup_at_alla_nascita()` |

---
{% include-markdown "signature-core.md" %}
