## 📘 Documentazione Concettuale – Funzione `documenti.fn_risolvi_template_applicabile()`

> 👀 **Vedi anche**
>
> [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti) (§ «Il modello standard»)
> [documenti.vw_template_personalizzati_scarto](/dbzero/documenti/views/vw_template_personalizzati_scarto)
> [documenti.vw_template_versioni_stampabili](/dbzero/documenti/views/vw_template_versioni_stampabili)
> [documenti.fn_template_esito_risoluzione](/dbzero/documenti/funzioni/fn_template_esito_risoluzione)
> [documenti.fn_template_motivo_non_coerente](/dbzero/documenti/funzioni/fn_template_motivo_non_coerente)

### 🎯 Scopo

(20-10-2026 — brief `brief-db-modelli-documento-standard`, §4.1 Q-2)

Dice **con quale modello si stampa un documento**. Un emittente nuovo non ha modelli suoi: per lui
vale il **modello standard**, che il sistema fornisce per ogni tipo di documento. Chi vuole un
modello diverso lo personalizza, e da quel momento vale il suo.

La regola sta nel database perché è una regola del modello: il backend la chiama e non la riscrive.
Dal 21-10-2026 (§10.3 K-2) è **la porta unica** della stampa: vale anche quando chi stampa indica
il modello (§ «Il modello indicato»).

### Conta solo un modello che può stampare

Un modello entra nella scelta solo se **può stampare**: è attivo e ha una versione **pubblicata**,
attiva e valida alla data operativa dell'azienda. La condizione sta in un punto solo, la vista
`vw_template_versioni_stampabili`, che questa funzione legge.

Il motivo: un modello si prepara da attivo (una versione non può nascere sotto un modello spento).
Quindi «attivo» non vuol dire «pronto». La copia appena creata con «personalizza» ha solo una
bozza, e finché non la si pubblica l'emittente continua a stampare con lo standard. Lo stesso vale
per una versione spenta e per una versione pubblicata che vale da una data futura.

La condizione vale per tutti e tre i passi: la scelta del tipo, il livello dell'emittente e il
livello standard.

### Dice anche con quale versione si stampa

(20-10-2026 — §8.4 P-2)

Insieme al modello la funzione restituisce **la versione** che lo rende stampabile: quella
pubblicata, attiva e valida alla data operativa. Per ogni modello e per ogni data ce n'è al
massimo una, perché le versioni pubblicate e attive di uno stesso modello non possono avere date di
validità che si sovrappongono.

Il motivo: chi stampa usa questa versione e non la va a cercare di nuovo. Se la cercasse con filtri
suoi, la regola «può stampare» sarebbe scritta in due posti, e il giorno che i due posti dicessero
cose diverse la funzione sceglierebbe un modello che poi non si riesce a stampare.

### La regola, a due livelli

La regola è di `fn_template_esito_risoluzione`, che la lista Modelli documento legge attraverso
`vw_template_risoluzione_emittente`: stampa e lista rispondono allo stesso modo.

1. **L'emittente ha almeno un modello suo che può stampare** per quel tipo di documento e quella
   sorgente → si usa il **suo predefinito**, se anche lui può stampare. Altrimenti la stampa si
   ferma con `E_DOCUMENTI_TEMPLATE_SENZA_PREDEFINITO`, e lo standard **non** entra. Un modello
   pubblicato dell'emittente vuol dire «per questo documento uso i miei». Un predefinito
   dimenticato, o ancora in preparazione, non deve far uscire il documento con la grafica
   sbagliata senza che nessuno se ne accorga.
2. **L'emittente non ha nessun modello suo che può stampare** → si usa il **predefinito
   standard**. Se manca, è spento o non ha una versione valida oggi:
   `E_DOCUMENTI_TEMPLATE_NON_RISOLTO`.

Spegnere tutti i propri modelli di un tipo riporta allo standard: è voluto.

### Il modello indicato

Con `p_template_documento_id` il modello non si sceglie, **si verifica**:

1. è adatto al documento? `fn_template_motivo_non_coerente`: stessa sorgente, stesso tipo (se
   indicato), stessa azienda oppure standard. Se no: `E_DOCUMENTI_TEMPLATE_NON_COERENTE`, col
   motivo (`SORGENTE`, `TIPO`, `EMITTENTE`);
2. può stampare oggi? Se no: `E_DOCUMENTI_TEMPLATE_NON_STAMPABILE`, col motivo (`MODELLO_SPENTO`,
   `NESSUNA_VERSIONE_VALIDA`);
3. livello `INDICATO`, con la versione.

È la stessa regola che il trigger di coerenza applica alla scrittura del documento generato, detta
prima del render. La usa anche `fn_personalizza_template_standard`, per sapere da quale versione
dello standard parte una copia.

### Firma

| Parametro | Tipo | Significato |
|---|---|---|
| `p_sorgente_tipo_id` | `template_documenti.sorgente_tipo_id%TYPE` | la sorgente del documento (obbligatoria) |
| `p_emittente_fiscale_id` | `template_documenti.emittente_fiscale_id%TYPE` | l'emittente **del documento** (obbligatorio) |
| `p_tipo_documento_output_id` | `template_documenti.tipo_documento_output_id%TYPE` | il tipo di documento; facoltativo |
| `p_template_documento_id` | `template_documenti.id%TYPE` | il modello indicato; facoltativo (dal 21-10-2026) |
| **Ritorno** | `TABLE(template_documento_id, livello, template_versione_id)` | una riga; `livello` = `EMITTENTE`, `STANDARD` o `INDICATO`; `template_versione_id` = la versione con cui il modello stampa oggi |

Il tipo di documento si può omettere solo se, fra i modelli della sorgente che l'emittente può
usare (i suoi e gli standard) e che possono stampare, ce n'è **uno** solo: una bozza di un altro
tipo non conta. Con più tipi la funzione non sceglie a caso:
`E_DOCUMENTI_TEMPLATE_AMBIGUO`.

`STABLE`, `SECURITY INVOKER`. Non rifà il perimetro: l'emittente è quello del documento, che il
chiamante ha già letto con i suoi permessi, e lo standard si legge da tutti.

### Errori

| Codice | Classe | Quando |
|---|---|---|
| `E_DOCUMENTI_TEMPLATE_SENZA_PREDEFINITO` | `CONFLITTO_STATO` | l'emittente ha modelli suoi che possono stampare, ma nessuno di loro è predefinito. Rimedia l'operatore |
| `E_DOCUMENTI_TEMPLATE_NON_RISOLTO` | `NON_TROVATO` | nessun modello dell'emittente che può stampare, e nessuno standard predefinito che può stampare |
| `E_DOCUMENTI_TEMPLATE_AMBIGUO` | `TECNICO` | tipo omesso su una sorgente con più tipi di documento |
| `E_DOCUMENTI_TEMPLATE_NON_STAMPABILE` | `CONFLITTO_STATO` | il modello indicato oggi non può stampare. Rimedia l'operatore |
| `E_DOCUMENTI_TEMPLATE_NON_COERENTE` | `DATO_ERRATO` | il modello indicato non è adatto al documento |
| `E_DOCUMENTI_RISOLVI_TEMPLATE_INPUT_INVALIDO` | `TECNICO` | sorgente o emittente NULL o ≤ 0, tipo o modello ≤ 0, un id che non è un modello |

### Test

`db/pgtap/documenti/test-documenti-template-standard-v1.sql` (test 11-23; la versione restituita
nei test 11, 13 e 36),
`test-documenti-template-standard-app-v1.sql` (test 6, la lettura come applicazione),
`test-documenti-template-porta-unica-v1.sql` (il modello indicato, la vista e la parità con la
lista).
