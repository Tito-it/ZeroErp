## 📘 Documentazione Concettuale – Funzione `documenti.fn_template_esito_risoluzione()`

> 👀 **Vedi anche**
>
> [documenti.fn_risolvi_template_applicabile](/dbzero/documenti/funzioni/fn_risolvi_template_applicabile)
> [documenti.vw_template_risoluzione_emittente](/dbzero/documenti/views/vw_template_risoluzione_emittente)
> [documenti.vw_template_versioni_stampabili](/dbzero/documenti/views/vw_template_versioni_stampabili)

### 🎯 Scopo

(21-10-2026 — brief `brief-db-modelli-documento-standard`, §10.3 K-5; strada B di §4.1 Q-2)

La regola dei **due livelli**, scritta una volta: per un'azienda e un documento (tipo, sorgente),
con che cosa si stampa. Conta solo un modello che può stampare
(`vw_template_versioni_stampabili`).

### L'esito

| Esito | Quando | Modello e versione |
|---|---|---|
| `EMITTENTE` | l'azienda ha modelli suoi che possono stampare, e uno è predefinito | il suo predefinito |
| `SENZA_PREDEFINITO` | ha modelli suoi che possono stampare, nessuno predefinito: lo standard non entra | nessuno |
| `STANDARD` | non ne ha nessuno, e lo standard predefinito può stampare | lo standard |
| `NON_RISOLTO` | non ne ha nessuno, e nemmeno lo standard può stampare | nessuno |

Restituisce anche quanti modelli suoi possono stampare. Una riga sempre.

### Chi la legge

* `fn_risolvi_template_applicabile`, che sugli esiti negativi solleva il codice del caso;
* `vw_template_risoluzione_emittente`, la lettura della lista Modelli documento.

Non legge gli emittenti: chi la chiama ha già l'azienda, e la stampa non dipende da cosa la RLS
lascia vedere delle aziende.
