## 📘 Documentazione Concettuale – Vista `documenti.vw_template_risoluzione_emittente`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — le aziende, una riga ciascuna per documento
> * [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti) — da qui vengono le coppie (tipo, sorgente)
>
> Approfondimento funzioni:
>
> * [documenti.fn_template_esito_risoluzione](/dbzero/documenti/funzioni/fn_template_esito_risoluzione) — la regola, la stessa della stampa
> * [documenti.fn_risolvi_template_applicabile](/dbzero/documenti/funzioni/fn_risolvi_template_applicabile) — la porta della stampa
>
> Guide:
>
> * [Documenti e Stampe](/guide/documenti-e-stampe) — §3.5, che cosa vede la lista Modelli documento

---

### 🎯 Scopo Principale

Dice, per ogni azienda e ogni documento, con che cosa si stampa: l'esito della risoluzione, il modello
e la versione. La legge la lista Modelli documento, che così mostra «si usa lo standard» o «nessun
predefinito» senza ricalcolare la regola.

---

### Le righe

Una riga per ogni azienda e ogni coppia (tipo di documento, sorgente) per cui esiste almeno un modello
standard o un modello di quell'azienda, in qualunque stato. La riga porta l'esito (`EMITTENTE`,
`SENZA_PREDEFINITO`, `STANDARD`, `NON_RISOLTO`), il modello e la versione quando ci sono, e quanti
modelli suoi l'azienda ha che possono stampare.

Una coppia i cui modelli non stampano esce `STANDARD` o `NON_RISOLTO`: è proprio quello che la lista
deve far vedere, prima che la stampa si fermi.

---

### ⭐ La regola non è qui

La regola è `fn_template_esito_risoluzione`, la stessa che usa la stampa: la vista aggiunge solo le
righe, cioè le aziende e le coppie. Un pgTAP verifica che vista e stampa diano lo stesso modello e la
stessa versione.

---

### Il perimetro delle aziende lo applica chi legge

La vista legge con i permessi di chi la interroga, ma né le aziende né i modelli hanno sicurezza di
riga: la vista porta **tutte** le aziende, anche quelle spente. Il backend della lista restringe alle
aziende del perimetro dell'operatore e alle sole aziende attive.

---

### Test

* `db/pgtap/documenti/test-documenti-template-porta-unica-v1.sql` — la vista è `security_invoker`; gli
  esiti `EMITTENTE`, `STANDARD` e `SENZA_PREDEFINITO`; la parità con la stampa.

---

### Note di migrazione

* 2026-10-21 — nasce, per la lista Modelli documento.

---

{% include-markdown "signature-core.md" %}
