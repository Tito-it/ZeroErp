# fn_resolve_codice_postale
### 🎯 Scopo Principale
Risolve il `codice_postale_id` con logica di fallback a due livelli.
Unica source of truth per la logica CAP (prima nel watcher Vue).

## Schema

`script` (funzione di lettura cross-dominio)

## Firma

```sql
script.fn_resolve_codice_postale(
    p_stradario_id   config.stradario.id%TYPE   DEFAULT NULL,
    p_comune_id      config.comuni.id%TYPE      DEFAULT NULL
) RETURNS config.codici_postali.id%TYPE
```

## Parametri

| Parametro | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| `p_stradario_id` | integer | NULL | Stradario di riferimento (priorita' 1) |
| `p_comune_id` | integer | NULL | Comune di riferimento (fallback) |

## Caratteristiche

- **STABLE**: solo lettura
- **PARALLEL SAFE**: nessun side-effect
- Guard implicito: parametri NULL o <= 0 saltano il relativo blocco
- Ritorna NULL se nessun fallback applicabile

## Logica di fallback

```
Priorita' 1: stradario_id fornito e > 0
  └─ SELECT codice_postale_id FROM config.stradario WHERE id = p_stradario_id
  └─ Se trovato → RETURN

Priorita' 2: comune_id fornito e > 0
  └─ SELECT id, COUNT(*) OVER() FROM config.codici_postali WHERE comune_id = p_comune_id
  └─ Se count = 1 (il comune ha un solo CAP) → RETURN
  └─ Se count > 1 (multipli CAP) → NULL (l'utente sceglie)

Fallback finale: RETURN NULL
```

## Casi d'uso

| Scenario | p_stradario_id | p_comune_id | Risultato |
|----------|---------------|-------------|-----------|
| Via con CAP specifico | 123 | - | CAP dello stradario |
| Comune con CAP unico | NULL | 456 | L'unico CAP del comune |
| Comune con piu' CAP | NULL | 789 | NULL (scelta manuale) |
| Stradario senza CAP + comune unico | 100 | 456 | CAP del comune (fallback) |
| Nessun parametro | NULL | NULL | NULL |

## Dipendenze

- `config.stradario` — lookup CAP per via
- `config.codici_postali` — lookup CAP per comune

## Esempi

```sql
-- CAP dalla via specifica
SELECT script.fn_resolve_codice_postale(p_stradario_id := 123);

-- Fallback: CAP unico del comune
SELECT script.fn_resolve_codice_postale(p_comune_id := 456);

-- Entrambi: tenta stradario, poi comune
SELECT script.fn_resolve_codice_postale(
    p_stradario_id := 123,
    p_comune_id := 456
);

-- Uso nel frontend (auto-set CAP)
-- Chiamato via API quando l'utente seleziona una via o un comune
```
