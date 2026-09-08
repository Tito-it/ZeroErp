## 📘 Documentazione Concettuale – Vista `vendite.vw_segnalazioni_con_documento_ignoto`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti_log](/dbzero/vendite/tabelle/fatturazione_lotti_log)
> • [vendite.fatturazione_lotti_esiti](/dbzero/vendite/tabelle/fatturazione_lotti_esiti)
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_lotto_segnalazioni_summary](/dbzero/vendite/funzioni/fn_get_lotto_segnalazioni_summary)
> • [vendite.fn_escludi_documento_da_giro](/dbzero/vendite/funzioni/fn_escludi_documento_da_giro)

---

### 🎯 Scopo Principale
(latest review 2026-09-08)

**È un presidio.** Elenca le segnalazioni **vive** di un lotto che nominano un
documento che quel lotto **non ha** fra i suoi esiti.

> ⛔ **Invariante: deve restare vuota.**

---

### Perché una riga qui è un difetto vero

Una segnalazione che dichiara un proprietario inesistente ha **due conseguenze
concrete**, e nessuna delle due si nota da sola:

1. **Non si potrà mai zittire.** Il modo per togliere di mezzo la segnalazione di
   un documento è **togliere il documento dal giro** — ma qui non c'è niente da
   togliere. La segnalazione resta a bloccare il lotto **per sempre**, e nessuna
   azione a video la risolve.
2. **L'operatore legge un nome che non esiste.** Nella colonna «Documento» della
   scheda segnalazioni comparirebbe qualcosa che nell'elenco dei documenti del
   lotto non c'è.

⇒ E dice una terza cosa, a chi ci mette le mani: **chi scrive la segnalazione ha
dichiarato il proprietario sbagliato**.

---

### Che cosa **non** entra, e perché

* **Le segnalazioni senza proprietario.** Una segnalazione che non nomina nessun
  documento è *del giro* — un emittente non risolto, una configurazione mancante
  — ed è legittimo che sia così: non ha un documento e non deve averlo.
  Metterla qui farebbe accusare come difetto la metà sana del vocabolario.
* **Le segnalazioni ritirate.** Non bloccano niente e non si leggono più:
  presidiarle non cambierebbe nessuna decisione.

---

### ⚠️ Oggi è vuota, ma non per teorema

La vista è vuota **perché nessuno valorizza ancora il proprietario** delle
segnalazioni, non perché la condizione sia impossibile. La differenza conta:
diventa raggiungibile esattamente il giorno in cui chi scrive le segnalazioni
comincerà a dichiarare a quale documento appartengono.

> 🔴 **Sostituisce un presidio promesso e mai scritto**, che era *vacuo*: «lotti
> fermi con tutte le criticità di documenti usciti». Se tutte le criticità sono
> di documenti usciti il conteggio risponde zero e il lotto **non è fermo** —
> sarebbe stata una vista vuota per costruzione.
> *Un presidio che non può accendersi non è prudenza: è rumore, e chi lo apre due
> volte a vuoto la terza non lo apre più.*

---

### Esempio d'uso

```sql
-- Deve rispondere zero righe.
SELECT * FROM vendite.vw_segnalazioni_con_documento_ignoto;
```

⚠️ La vista rispetta i permessi di chi legge: il collegamento al lotto **è** il
perimetro emittente. Letta da un canale senza contesto operatore risponde zero
righe per fail-closed, che **non** è la stessa cosa di «tutto a posto».

> Piano e decisioni: `docs/it/dev/work-in-progress/brief-db-uscita-documento-dal-giro.md`.

---

{% include-markdown "signature-core.md" %}
