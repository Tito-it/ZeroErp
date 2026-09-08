## 📘 Documentazione Concettuale – Funzione `script.fn_check_documento_escludibile_da_giro`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti_esiti](/dbzero/vendite/tabelle/fatturazione_lotti_esiti)
> • [config.stati_doc_fiscale](/dbzero/config/tabelle/stati_doc_fiscale)
>
**Approfondimento funzioni:**
>
• [vendite.fn_escludi_documento_da_giro](/dbzero/vendite/funzioni/fn_escludi_documento_da_giro)
> • [script.fn_check_fattura_eliminabile_da_lotto](/dbzero/script/funzioni/fn_check_fattura_eliminabile_da_lotto)

---

### 🎯 Scopo Principale
(latest review 2026-09-08)

Risponde a una domanda sola: **«questo documento si può togliere da questo giro
di fatturazione?»** — e quando la risposta è no, dice **perché**.

È una funzione **pura**: non scrive niente e non solleva errori di dominio.
Ritorna `[]` se il documento si può togliere, altrimenti l'elenco **ordinato**
dei motivi.

---

### Perché esiste una funzione a parte

⭐ **La regola sta in un posto solo.** La stessa risposta serve a due
interlocutori diversi:

| Chi chiede | Che cosa se ne fa |
| --- | --- |
| [`vendite.fn_escludi_documento_da_giro`](/dbzero/vendite/funzioni/fn_escludi_documento_da_giro) | rifiuta l'operazione, sollevando il **primo** motivo |
| il **frontend** | spegne il pulsante e ci scrive accanto il perché |

Così il messaggio sul pulsante spento e il rifiuto non «coincidono oggi»: **non
possono divergere**, perché sono la stessa funzione.

---

### I motivi, e il loro ordine

⚠️ **L'ordine è il contratto**, non un dettaglio estetico: chi rifiuta solleva il
primo.

| # | Motivo | Quando |
| --- | --- | --- |
| 1 | `STATO_LOTTO_NON_PRE_FISCALE` | il giro è andato oltre la fase pre-fiscale: lì non si tocca più niente, su nessun documento |
| 2 | `SENZA_ESITO` | il documento non risulta lavorato da questo lotto — di solito un elenco a video invecchiato |
| 3 | `GIA_USCITO` | è già stato tolto: doppio clic, o due operatori sulla stessa lista |
| 4 | `DOCUMENTO_NON_IN_ERRORE` | il documento è sano, e dal giro escono solo quelli che hanno fallito |

> ⚠️ **Il terzo precede il quarto, e la precedenza è portante.** Un documento già
> uscito è **anche** «non in errore»: senza quest'ordine scatterebbero due motivi
> e chi rifiuta solleverebbe quello sbagliato.

---

### Due cose che non si trovano leggendo il codice in fretta

#### Il confine «pre-fiscale» non è un elenco di stati

Si legge dal flag `congela_fiscale` del catalogo degli stati, e si legge
**fail-closed**: se lo stato del lotto non è risolvibile, il documento **non** si
tocca. Non sapere in che stato è il giro non è un buon motivo per lasciarci
mettere le mani.

⭐ Un elenco di stati scritto a mano sarebbe una seconda sede della stessa regola,
e invecchierebbe al primo stato nuovo.

#### La bozza condivisa **non è** fra i motivi

Che togliere un documento ne trascini altri è una **conseguenza**, non un
divieto. Quanti siano lo dice
[`script.fn_gruppi_trascinati_da_uscita`](/dbzero/script/funzioni/fn_gruppi_trascinati_da_uscita),
e lo dichiara la conferma a video: le conseguenze stanno nella conferma, non in
un rifiuto.

---

### Forma della risposta

Ogni motivo è un oggetto con quattro chiavi:

| Chiave | A chi parla |
| --- | --- |
| `codice` | il **backend** — è un codice registrato a catalogo, che diventa uno status HTTP |
| `reason` | codice **macchina**, per chi programma il comportamento |
| `reason_key` | l'**indirizzo** del testo tradotto che l'operatore legge |
| `dettaglio` | il dato che rende la frase concreta (lo stato, il documento) |

> ⛔ Un `reason` non porta mai il prefisso `E_`: quello è riservato ai codici a
> catalogo, e un `reason` che comincia così arriverebbe ai controlli automatici
> come un codice senza classificazione.

---

### Esempio d'uso

```sql
-- [] = si può togliere
SELECT script.fn_check_documento_escludibile_da_giro(
    11221, 'ORDINE_VENDITA:01a06ce4-b46a-7a49-a72f-c07c29de47bb'
);

-- il primo motivo, che è quello che verrebbe sollevato
SELECT script.fn_check_documento_escludibile_da_giro(11221, 'ORDINE_VENDITA:...')
       -> 0 ->> 'reason';
```

> Piano e decisioni: `docs/it/dev/work-in-progress/brief-db-uscita-documento-dal-giro.md`.

---

{% include-markdown "signature-core.md" %}
