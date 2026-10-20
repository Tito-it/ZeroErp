## 📘 Documentazione Concettuale – Vista `documenti.vw_template_risoluzione_emittente`

> 👀 **Vedi anche**
>
> [documenti.fn_template_esito_risoluzione](/dbzero/documenti/funzioni/fn_template_esito_risoluzione)
> [documenti.fn_risolvi_template_applicabile](/dbzero/documenti/funzioni/fn_risolvi_template_applicabile)
> [Guida — Documenti e Stampe](/guide/documenti-e-stampe) (§3.5)

### 🎯 Scopo

(21-10-2026 — brief `brief-db-modelli-documento-standard`, §10.3 K-5, D-5 di Tid)

Per la lista **Modelli documento**: per ogni azienda e ogni documento, con che cosa si stampa. Così
la lista dice «si usa lo standard» o «nessun predefinito» senza ricalcolare la regola.

### Le righe

Una riga per azienda × (tipo di documento, sorgente) per cui esiste almeno un modello standard o un
modello di quell'azienda, in qualunque stato. La riga porta l'esito (`EMITTENTE`,
`SENZA_PREDEFINITO`, `STANDARD`, `NON_RISOLTO`), il modello, la versione e quanti modelli suoi
possono stampare.

### La regola non è qui

La regola è `fn_template_esito_risoluzione`, la stessa della stampa: la vista aggiunge solo le
righe, cioè le aziende e le coppie. Una coppia con modelli che non stampano esce `STANDARD` o
`NON_RISOLTO`: è proprio quello che la lista deve far vedere.

### Note

`security_invoker`: la legge l'operatore. Le aziende e i modelli non hanno RLS; il perimetro delle
aziende lo applica il backend, come per la lista dei modelli.
