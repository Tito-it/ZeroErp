## 📘 Documentazione Concettuale – Funzione `pagamenti.fn_annulla_sistemazione`

### ⭐ rev 31-08-2026 — SU UN RIPORTO, IL FONDO CADE CON L'ATTO (D-25)

Se l'atto era `CONFERMATA` e la destinazione è `RIPORTO`, l'annullamento chiama
`vendite.fn_cancella_fondo_fattura` e il fondo creato dalla conferma **sparisce
insieme alla decisione**.

> ⭐ *L'atto e il suo effetto cadono insieme, o il registro racconta un fatto che
> non è avvenuto.*

**Perché guida `pagamenti` e non `vendite`:** chi alza la bandiera la abbassa (il
fondo l'ha creato `fn_conferma_sistemazione`); `api.md` vieta le chiamate
laterali fra moduli di pari livello, quindi la sola sede in cui i due schemi si
toccano è **il database**; e l'atto sta qui, mentre il fondo è la sua
**conseguenza**.

⚠️ **L'ordine è invertito rispetto al piano, e non poteva essere altrimenti.** Il
brief chiedeva *«prima si cancella il fondo, e solo se riesce si porta l'atto ad
ANNULLATA»*: alla lettera non è eseguibile, perché `fk_sistemazioni_fondo_source`
è `NO ACTION` e trattiene il `DELETE` finché l'atto punta il fondo — e per
staccare il puntatore serve proprio quell'`UPDATE`. **La garanzia regge lo stesso
per costruzione**: è tutto dentro una funzione, cioè una transazione, quindi se
la cancellazione solleva l'`UPDATE` non sopravvive. Il record che il piano temeva
— *sistemazione annullata con il suo fondo ancora vivo* — non è raggiungibile.

⚠️ **Il composito dell'esito cade intero** (`data_esecuzione`, `user_esecuzione`,
`fondo_source_id`), perché `chk_sistemazioni_eseguita` lo pretende. ⭐ Ma la
memoria non si butta: ciò che il registro perderebbe finisce sotto
`meta -> 'annullata_dopo_esecuzione'`, che nessun `CHECK` vincola — e si scrive
**solo** quando l'atto era davvero stato eseguito, perché su una `BOZZA` una
chiave con dentro tre `null` direbbe il falso.

⚠️ **Cancellare il fondo RIAPRE la rigenerazione automatica**: l'«atto unico»
guarda se un atto esiste in qualunque stato, quindi il giro successivo ne rifà
uno leggendo il residuo di adesso. Sul riporto è il comportamento giusto —
l'eccedenza è tornata al suo posto — ma è un cambio reale.

⛔ **Continua a NON ricontrollare lo stato**: a quello risponde
`trgfn_sistemazioni_guard_transizione`. La riga si legge per sapere se c'è un
**esito** da disfare, non per rideliberare.

---

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
