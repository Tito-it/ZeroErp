# fn_cleanup_token_scaduti

### 🎯 Scopo Principale

Pulizia periodica dei token monouso scaduti o gia' utilizzati. Pensata per esecuzione automatica come job pgAgent notturno, elimina i record che non hanno piu' utilita' operativa.

## Schema

`config`

## Firma

```sql
config.fn_cleanup_token_scaduti(
    p_giorni_retention  integer DEFAULT 30
) RETURNS integer
```

## Parametri

| Parametro            | Tipo      | Obbligatorio | Descrizione                                                                    |
| -------------------- | --------- | :----------: | ------------------------------------------------------------------------------ |
| `p_giorni_retention` | `integer` |      No      | Giorni di retention dopo scadenza/utilizzo (default 30). Se NULL o < 0, usa 30 |

## Logica di eliminazione

Elimina i token che soddisfano **almeno una** di queste condizioni:

1. **Scaduti**: `scadenza < now() - N giorni`
2. **Utilizzati**: `utilizzato = true AND utilizzato_at < now() - N giorni`

I token ancora validi e non utilizzati non vengono mai eliminati, indipendentemente dall'eta'.

## Caratteristiche

- **VOLATILE**: modifica dati (DELETE)
- Guard: `p_giorni_retention` NULL o negativo normalizzato a 30
- Ritorna il numero di record effettivamente eliminati

## Risultato

| Tipo      | Descrizione               |
| --------- | ------------------------- |
| `integer` | Numero di token eliminati |

## Dipendenze

- `config.token_monouso` — tabella token

## Uso previsto

```sql
-- Pulizia con retention default (30 giorni)
SELECT config.fn_cleanup_token_scaduti();

-- Pulizia con retention 7 giorni (ambiente di test)
SELECT config.fn_cleanup_token_scaduti(7);
```

### Schedulazione pgAgent

Esecuzione consigliata: una volta al giorno (es. 03:00). Il job non ha impatto sulle operazioni correnti perche' elimina solo token gia' inutilizzabili.
