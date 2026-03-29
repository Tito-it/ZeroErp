# fn_resolve_email_template

### Scopo

Risolve il template email da utilizzare per un dato codice, reparto, tipo prestazione e lingua. Implementa una catena di fallback a 5 livelli che permette di specializzare i testi per reparto e tipo pratica mantenendo sempre un default di sistema.

## Schema

`config`

## Firma

```sql
config.fn_resolve_email_template(
    p_codice                  config.email_template.codice%TYPE,
    p_unita_organizzativa_id  config.email_template.unita_organizzativa_id%TYPE
                              DEFAULT NULL,
    p_tipo_prestazione_id     config.email_template.tipo_prestazione_id%TYPE
                              DEFAULT NULL,
    p_lingua                  config.email_template.lingua%TYPE
                              DEFAULT 'it'
) RETURNS jsonb
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:------------:|-------------|
| `p_codice` | `email_template.codice%TYPE` | Si | Codice tipo template (es. `INVITO_OPERATORE`, `COMUNICAZIONE_PRATICA`) |
| `p_unita_organizzativa_id` | `email_template.unita_organizzativa_id%TYPE` | No | ID reparto per override. NULL = solo sistema |
| `p_tipo_prestazione_id` | `email_template.tipo_prestazione_id%TYPE` | No | ID tipo prestazione per specializzazione. NULL = generico |
| `p_lingua` | `email_template.lingua%TYPE` | No | Codice lingua ISO (default `it`) |

## Catena di fallback (5 livelli)

Cerca il primo template **attivo** in quest'ordine:

1. **Reparto + tipo prestazione + lingua** — massima specializzazione
2. **Reparto + lingua** (tipo prestazione NULL) — generico per il reparto
3. **Sistema + tipo prestazione + lingua** — specializzato per tipo, senza reparto
4. **Sistema + lingua** (reparto e tipo NULL) — generico di sistema
5. **Sistema + lingua `it`** — fallback finale (solo se `p_lingua <> 'it'`)

Se `p_codice` e' NULL, ritorna immediatamente NULL.

## Caratteristiche

- **STABLE**: non modifica dati, solo lettura
- Ogni livello cerca esattamente un record con `attivo = true`

## Risultato

JSONB con le chiavi:

| Chiave | Tipo | Descrizione |
|--------|------|-------------|
| `id` | integer | ID del template trovato |
| `codice` | text | Codice tipo template |
| `oggetto` | text | Oggetto email con variabili `{{...}}` |
| `corpo_html` | text | Corpo HTML con variabili `{{...}}` |
| `corpo_testo` | text | Corpo plaintext (puo' essere null) |
| `variabili_disponibili` | jsonb | Array variabili accettate |
| `lingua` | text | Lingua del template trovato |

## Dipendenze

- `config.email_template` — tabella template

## Esempio

```sql
-- Template COMUNICAZIONE_PRATICA per reparto Acquisti, tipo Reclamo, lingua it
SELECT config.fn_resolve_email_template('COMUNICAZIONE_PRATICA', 3, 7, 'it');

-- Template INVITO_OPERATORE generico di sistema
SELECT config.fn_resolve_email_template('INVITO_OPERATORE');

-- Template con fallback lingua (cerca 'en', poi fallback 'it')
SELECT config.fn_resolve_email_template('RESET_PASSWORD', NULL, NULL, 'en');
```
