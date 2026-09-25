{% include-markdown "it/dbzero/config/manual/nomi_tentati.md" %}
# 📚 Tabella `nomi_tentati`

> 📝 **Descrizione**
>
> I fallimenti di login su un NOME che non e' una credenziale (R-7, 2026-09-25): il freno e l'attesa valgono per il nome tentato, esista o no, cosi' la risposta del login non dice se l'utente esiste. La gemella di config.credenziali per cio' che non esiste: la credenziale resta la chiave quando il nome la trova. Il nome non si salva: solo il suo digest. Scade (cleanup_at). Scrivono solo le funzioni del login; all'app solo SELECT. Brief: brief-db-blocco-login-per-credenziale §13.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| nome_digest | bytea | NO |  |
| fallimenti_consecutivi | integer | NO | 0 |
| ultimo_fallimento_at | timestamp with time zone | NO |  |
| cleanup_at | timestamp with time zone | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_nomi_tentati_fallimenti |  |
| CHECK | chk_nomi_tentati_nome_digest |  |
| PRIMARY KEY | pk_nomi_tentati | id |
| UNIQUE | uq_nomi_tentati_nome_digest | nome_digest |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_nomi_tentati | `CREATE UNIQUE INDEX pk_nomi_tentati ON config.nomi_tentati USING btree (id)` |
| uq_nomi_tentati_nome_digest | `CREATE UNIQUE INDEX uq_nomi_tentati_nome_digest ON config.nomi_tentati USING btree (nome_digest)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_nomi_tentati_m50_cleanup_at_ins | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_cleanup_at_alla_nascita()` |

---
{% include-markdown "signature-core.md" %}
