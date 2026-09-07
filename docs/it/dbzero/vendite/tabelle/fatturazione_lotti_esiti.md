# 📚 Tabella `fatturazione_lotti_esiti`

> 📝 **Descrizione**
>
> Com'e' andato un DOCUMENTO dentro un lotto: una riga per (lotto, documento), creata quando c'e' qualcosa da dire. ⭐ Nasce separando due domande che vivevano nella stessa tabella: vendite.fatturazione_lotti_gruppi dice QUALI documenti lavorare (il perimetro, dove «nessuna riga» significa «nessuna restrizione») e diceva anche COM'E' ANDATO ciascuno. Le due coincidono sui giri mirati e divergono su quelli di massa, che non scrivono nessun perimetro: li' un documento fallito restava muto. ⛔ Scrivere il perimetro anche sui giri di massa non era una via — trasformerebbe ogni giro schedulato in un giro mirato. ⭐ Il backend non cambia: chiamava gia' vendite.fn_segna_esito_gruppo_lotto per ogni commessa, e sui giri di massa quella chiamata tornava 0 perche' non trovava la riga; qui la riga viene creata. ⚠️ Un tentativo successivo sullo stesso lotto SOVRASCRIVE: la domanda e' «com'e' finita», non «quante volte ci abbiamo provato» — lo storico sta nel giornale del lotto. Brief: brief-db-esito-gruppo-lotto §15.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| lotto_id | bigint | NO |  |
| gruppo_key | text | NO |  |
| stato_esecuzione | text | NO |  |
| errore_codice | text | YES |  |
| errore_messaggio | text | YES |  |
| errore_quando | timestamp with time zone | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatturazione_lotti_esiti_errore_parlante |  |
| CHECK | chk_fatturazione_lotti_esiti_stato |  |
| FOREIGN KEY | fk_fatturazione_lotti_esiti_lotto | lotto_id |
| PRIMARY KEY | pk_fatturazione_lotti_esiti | id |
| UNIQUE | uq_fatturazione_lotti_esiti_documento | lotto_id, gruppo_key |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_fatturazione_lotti_esiti | `CREATE UNIQUE INDEX pk_fatturazione_lotti_esiti ON vendite.fatturazione_lotti_esiti USING btree (id)` |
| uq_fatturazione_lotti_esiti_documento | `CREATE UNIQUE INDEX uq_fatturazione_lotti_esiti_documento ON vendite.fatturazione_lotti_esiti USING btree (lotto_id, gruppo_key)` |

---
{% include-markdown "signature-core.md" %}
