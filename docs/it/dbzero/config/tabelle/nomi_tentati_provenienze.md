{% include-markdown "it/dbzero/config/manual/nomi_tentati_provenienze.md" %}
# 📚 Tabella `nomi_tentati_provenienze`

> 📝 **Descrizione**
>
> Freno sulla coppia NOME TENTATO + PROVENIENZA per un nome che non e' una credenziale (R-7, 2026-09-25): stessa soglia, stessa durata e stesso codice della coppia credenziale + provenienza (config.credenziali_provenienze), cosi' la risposta del login non dice se il nome esiste. La riga nasce al primo fallimento e scade (cleanup_at). Scrivono solo le funzioni del login; all'app solo SELECT. Brief: brief-db-blocco-login-per-credenziale §13.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| nome_tentato_id | bigint | NO |  |
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
| CHECK | chk_nomi_tentati_provenienze_tentativi |  |
| FOREIGN KEY | fk_nomi_tentati_provenienze_nomi_tentati | nome_tentato_id |
| PRIMARY KEY | pk_nomi_tentati_provenienze | id |
| UNIQUE | uq_nomi_tentati_provenienze_nome_provenienza | nome_tentato_id, provenienza |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_nomi_tentati_provenienze | `CREATE UNIQUE INDEX pk_nomi_tentati_provenienze ON config.nomi_tentati_provenienze USING btree (id)` |
| uq_nomi_tentati_provenienze_nome_provenienza | `CREATE UNIQUE INDEX uq_nomi_tentati_provenienze_nome_provenienza ON config.nomi_tentati_provenienze USING btree (nome_tentato_id, provenienza)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_nomi_tentati_provenienze_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_nomi_tentati_provenienze_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_nomi_tentati_provenienze_m50_cleanup_at_ins | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_cleanup_at_alla_nascita()` |

---
{% include-markdown "signature-core.md" %}
