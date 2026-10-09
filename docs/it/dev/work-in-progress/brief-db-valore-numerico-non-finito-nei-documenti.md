# Brief DB — Un documento con un numero che non è un numero non si genera

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-09. **A chi:** team DB
> (`dev/db-tid`); poi BE (§4), che **attende** la consegna DB.
> **Origine:** L3 di [piano-be-type-checker.md](piano-be-type-checker.md) §5.3 — mypy
> ha segnalato in `apps/documenti/services/context_builders/_number_formatting.py`
> (righe 96 e 101) un'operazione che su NaN/Infinity va in `TypeError`.
> **Decisione:** di Tid, 2026-10-09 — **opzione C**: se un valore numerico di un
> documento è NaN o infinito, la generazione si **ferma** con un errore chiaro; non si
> stampa «NaN» e non lo si nasconde con un trattino.
> **Stato:** 🟡 aperto, in attesa del team DB.

## 1. Il difetto

PostgreSQL ammette nel tipo `numeric` i valori speciali `'NaN'` e (dalla 14)
`'Infinity'`/`'-Infinity'`. Se uno di questi arriva a un documento (importo, prezzo,
quantità), `format_misura` calcola `-d.as_tuple().exponent`, che per questi valori è
una **stringa** (`'n'`, `'N'`, `'F'`): il segno meno su una stringa è un `TypeError`,
cioè la generazione del PDF esce con un 500 anonimo. `format_importo` fa lo stesso per
gli infiniti (`quantize` solleva `InvalidOperation`).

⚠️ Un CHECK come `prezzo >= 0` **non** ferma `'NaN'`: in PostgreSQL `NaN` è maggiore
di ogni altro numero, quindi il CHECK lo lascia passare.

## 2. Richiesta

| # | Cosa |
| --- | --- |
| **R-1** | **Un codice d'errore** per «il documento porta un valore numerico non finito», per esempio `E_DOCUMENTI_VALORE_NUMERICO_NON_VALIDO`, con la frase (un segnaposto per il campo, uno per il valore) e la classe. Proposta del BE sulla classe: **non** `DATO_ERRATO`, perché la richiesta dell'operatore è corretta e il difetto sta nel dato già scritto. La domanda «chi può rimediare» la decide il team DB. |
| **R-2** | **Da valutare (decisione di Tid):** il modo giusto di non arrivarci mai è che il valore non si **scriva**. Un controllo `<> 'NaN'` (e sugli infiniti) sulle colonne `numeric` di importi, prezzi e quantità dei documenti, con un guard o un CHECK, sul modello del guard comune delle date. Il BE non sa se un percorso oggi possa scriverli: la domanda è sul modello, non sui dati. |

## 3. Fuori da questo brief

- La formattazione delle date e dei valori non numerici (stringhe descrittive): restano
  come sono.

## 4. Ricaduta BE (dopo la consegna DB)

1. Policy generata e frase di ripiego (`error_messages_fallback.py`) per il codice nuovo,
   rigenerate **dopo** il pull della consegna DB, mai col DB avanti rispetto a git.
2. `_number_formatting.py`: `format_misura` e `format_importo` riconoscono un `Decimal`
   non finito (`not d.is_finite()`) e sollevano il codice nuovo col nome del campo. I 2
   rilievi mypy residui (righe 96 e 101) si sanano qui, e il registro scende a **zero**.
3. Test: NaN, `Infinity` e `-Infinity` (anche da stringa e da `float`) su una misura e su
   un importo → l'errore col codice; un numero normale → invariato.
