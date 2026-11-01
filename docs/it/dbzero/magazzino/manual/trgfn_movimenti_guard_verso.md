## 📘 Documentazione Concettuale – Trigger function `magazzino.trgfn_movimenti_guard_verso`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — dove è montato
> * [magazzino.movimenti_attesi](/dbzero/magazzino/tabelle/movimenti_attesi) — dove è montato
> * [magazzino.causali](/dbzero/magazzino/tabelle/causali) — il verso
>
> Approfondimento funzioni:
>
> * [magazzino.fn_scrivi_movimento](/dbzero/magazzino/funzioni/fn_scrivi_movimento) — la primitiva, che dà la frase prima di arrivare qui
>
> Guide:
>
> * [Messaggi di errore e generazione log](/guide/Messaggi-di-Errore-e-Generazione-Log) — classi e campi dei codici

---

### 🎯 Scopo Principale

**La rete del verso**: rifiuta un movimento — o un atteso — la cui quantità non ha il segno
della causale (il verso, più uno o meno uno). È montato prima dell'inserimento e
dell'aggiornamento su `movimenti` e su `movimenti_attesi`: una funzione, due trigger.

---

### È tecnico, di proposito

Il verso non lo digita mai una persona: lo compone l'**operazione** dalla causale. Un
disallineamento è quindi un chiamante rotto, non un dato sbagliato — classe `TECNICO`, nessun
campo da accendere nel form. La primitiva di scrittura dà il messaggio comprensibile *prima* di
arrivare qui (è il suo passo 3); questo guard è la rete, e chi lo legge è `dbops.error_log`. Il
messaggio nomina la causale, il segno e la quantità.

---

### Due cose da sapere

* **La quantità zero cade qui**, non nel vincolo di tabella che la vieta: un trigger che scatta
  prima della scrittura della riga arriva prima dei vincoli di tabella, e zero non ha mai il
  segno di una causale. Il vincolo resta come seconda rete.
* **Una causale inesistente non è affar suo**: la funzione lascia parlare la chiave esterna,
  invece di dire «verso incoerente» su una causa che è un'altra.

---

### Codici errore

* `E_MAG_MOVIMENTO_VERSO_INCOERENTE` — il segno della quantità non è quello della causale.

---

### Test

`db/pgtap/magazzino/test-movimenti-vincoli-v2.sql` (test 7 e 9) e
`db/pgtap/magazzino/test-movimenti-attesi-forma-v1.sql` (test 3 e 4).

---

### Note di migrazione

* 2026-09-15 — nasce con `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.9, M-1).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
