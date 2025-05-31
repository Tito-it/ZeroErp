# Tabella `messaggi_errore`

## Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| codice | text | NO |  |
| lingua | text | NO | 'it'::text |
| messaggio | text | NO |  |

## Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | 16601_18606_1_not_null |  |
| CHECK | 16601_18606_2_not_null |  |
| CHECK | 16601_18606_3_not_null |  |
| PRIMARY KEY | pk_messaggi_errore | codice, lingua |

## Indici
| Nome | Definizione |
|------|-------------|
| pk_messaggi_errore | `CREATE UNIQUE INDEX pk_messaggi_errore ON config.messaggi_errore USING btree (codice, lingua)` |