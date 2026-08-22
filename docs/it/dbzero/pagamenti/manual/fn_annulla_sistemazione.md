## 📘 Documentazione Concettuale – Funzione `pagamenti.fn_annulla_sistemazione`

### 🎯 Scopo Principale

(rev 2026-08-22)

Scarta un atto di sistemazione **lasciandolo a registro** con la ragione per cui
è stato scartato.

> ⚠️ **Annullare non è cancellare**, ed è il senso stesso di avere un registro:
> l'eccedenza continuerà a comparire nell'elenco — è vera, non se n'è andata — e
> chi guarderà troverà scritto perché la volta scorsa si è deciso di lasciarla lì.

---

### ⭐ È piccola, e deve restarlo

**Non è una madre**: scrive una riga sola. Esiste per **due** ragioni, non per
tre:

1. dare un messaggio giusto a *«quell'atto non c'è»* — che sotto la row security
   vuol dire anche *«non è tuo»*, e le due cose devono restare indistinguibili;
2. far arrivare il **motivo** nello stesso gesto in cui si annulla, invece di
   chiedere a chi chiama di scriverlo prima con un `UPDATE` a parte.

⛔ **Non ricontrolla lo stato**: se l'atto è già terminale a parlare è
`trgfn_sistemazioni_guard_transizione` con `E_SISTEMAZIONE_IMMUTABILE`, che dice
*anche in che stato si trova*. Ripetere qui quel controllo vorrebbe dire due sedi
per la stessa regola, e il giorno in cui una cambia l'altra mente.

### ⭐ Il motivo si fonde, non si sovrascrive

`COALESCE(NULLIF(btrim(p_motivo), ''), motivo)`: se l'atto ne aveva già uno e la
chiamata arriva vuota, **si tiene quello che c'era**.

⚠️ E se restano entrambi vuoti non passa: il guard dei dati pretende il motivo su
un annullamento, perché *una decisione scartata senza una ragione non si
ricostruisce* — fra sei mesi nessuno saprebbe se è stata una scelta o una
dimenticanza.

---

{% include-markdown "signature-core.md" %}
