## 📘 Documentazione Concettuale – Funzione `documenti.fn_risolvi_template_applicabile()`

> 👀 **Vedi anche**
>
> [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti) (§ «Il modello standard»)
> [documenti.vw_template_personalizzati_scarto](/dbzero/documenti/views/vw_template_personalizzati_scarto)

### 🎯 Scopo

(20-10-2026 — brief `brief-db-modelli-documento-standard`, §4.1 Q-2)

Dice **con quale modello si stampa un documento**. Un emittente nuovo non ha modelli suoi: per lui
vale il **modello standard**, che il sistema fornisce per ogni tipo di documento. Chi vuole un
modello diverso lo personalizza, e da quel momento vale il suo.

La regola sta nel database perché è una regola del modello: il backend la chiama e non la riscrive.

### La regola, a due livelli

1. **L'emittente ha almeno un modello suo attivo** per quel tipo di documento e quella sorgente →
   si usa il **suo predefinito**. Se nessuno dei suoi è predefinito, la stampa si ferma con
   `E_DOCUMENTI_TEMPLATE_SENZA_PREDEFINITO`: lo standard **non** entra. Un modello attivo
   dell'emittente vuol dire «per questo documento uso i miei», e un predefinito dimenticato non
   deve far uscire il documento con la grafica sbagliata senza che nessuno se ne accorga.
2. **L'emittente non ha nessun modello suo attivo** → si usa il **predefinito standard**. Se manca,
   `E_DOCUMENTI_TEMPLATE_NON_RISOLTO`.

Spegnere tutti i propri modelli di un tipo riporta allo standard: è voluto.

### Firma

| Parametro | Tipo | Significato |
|---|---|---|
| `p_sorgente_tipo_id` | `template_documenti.sorgente_tipo_id%TYPE` | la sorgente del documento (obbligatoria) |
| `p_emittente_fiscale_id` | `template_documenti.emittente_fiscale_id%TYPE` | l'emittente **del documento** (obbligatorio) |
| `p_tipo_documento_output_id` | `template_documenti.tipo_documento_output_id%TYPE` | il tipo di documento; facoltativo |
| **Ritorno** | `TABLE(template_documento_id, livello)` | una riga; `livello` = `EMITTENTE` o `STANDARD` |

Il tipo di documento si può omettere solo se, fra i modelli attivi della sorgente che l'emittente
può usare (i suoi e gli standard), ce n'è **uno** solo. Con più tipi la funzione non sceglie a caso:
`E_DOCUMENTI_TEMPLATE_AMBIGUO`.

`STABLE`, `SECURITY INVOKER`. Non rifà il perimetro: l'emittente è quello del documento, che il
chiamante ha già letto con i suoi permessi, e lo standard si legge da tutti.

### Errori

| Codice | Classe | Quando |
|---|---|---|
| `E_DOCUMENTI_TEMPLATE_SENZA_PREDEFINITO` | `CONFLITTO_STATO` | l'emittente ha modelli suoi attivi, nessuno predefinito. Rimedia l'operatore |
| `E_DOCUMENTI_TEMPLATE_NON_RISOLTO` | `NON_TROVATO` | nessun modello dell'emittente e nessuno standard predefinito attivo |
| `E_DOCUMENTI_TEMPLATE_AMBIGUO` | `TECNICO` | tipo omesso su una sorgente con più tipi di documento |
| `E_DOCUMENTI_RISOLVI_TEMPLATE_INPUT_INVALIDO` | `TECNICO` | sorgente o emittente NULL o ≤ 0, tipo ≤ 0 |

### Test

`db/pgtap/documenti/test-documenti-template-standard-v1.sql` (test 11-18),
`test-documenti-template-standard-app-v1.sql` (test 6, la lettura come applicazione).
