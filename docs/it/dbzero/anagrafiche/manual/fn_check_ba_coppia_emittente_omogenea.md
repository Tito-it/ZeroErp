## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_check_ba_coppia_emittente_omogenea`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
>
Approfondimenti funzioni:
>
[anagrafiche.fn_get_emittente_fiscale_id](/dbzero/anagrafiche/manual/fn_get_emittente_fiscale_id)

---
### 🎯 Scopo Principale
(latest review 18-08-26)

Domanda pura, risposta si'/no: **questo billing account e il suo genitore
appartengono allo stesso emittente fiscale?**

Non solleva errori: e' il mattone su cui poggiano i due guard veri.

---

### La regola, e quella sbagliata che le assomiglia

| | |
| --- | --- |
| ❌ *«un soggetto sta sotto un solo emittente»* | **Falso.** Un cliente puo' essere cliente di piu' emittenti: sono alberi separati, ed e' legittimo |
| ✅ *«un singolo albero non attraversa due emittenti»* | **Questa e' la regola.** Cio' che non deve esistere e' **un** albero con un piede di qua e uno di la' |

---

### Due scelte di costruzione, entrambe importanti

**1. L'emittente si RISOLVE, non si legge.** Un billing account senza
assegnazione esplicita non e' «senza emittente»: appartiene al **gestore
globale**. Confrontare le righe di assegnazione invece dei valori risolti
significherebbe giudicare su un dato assente — lo stesso difetto del codice
fiscale mancante, spostato su un'altra colonna.

**2. Si usa lo STESSO risolutore della fatturazione.** Non e' pigrizia: e'
l'unico modo perche' *«albero omogeneo»* e *«la fattura esce da un solo
emittente»* siano la **stessa** affermazione. Un secondo risolutore
dichiarerebbe sano un albero che la fattura spacca comunque — peggio di nessun
controllo, perche' rassicura.

---

### Impatto e Vantaggi

* un solo posto dove sta scritto cosa vuol dire «stesso emittente»;
* se l'emittente non si risolve, la risposta e' **no**: nel dubbio si chiude.
