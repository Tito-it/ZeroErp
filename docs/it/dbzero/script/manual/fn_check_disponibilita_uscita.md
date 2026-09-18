## 📘 Documentazione Concettuale – Funzione `script.fn_check_disponibilita_uscita`

> 👀 **Vedi anche**
>
Approfondimento tabelle e viste:
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti), [magazzino.vw_giacenza](/dbzero/magazzino/views/vw_giacenza) — il fisico
> • [magazzino.movimenti_attesi](/dbzero/magazzino/tabelle/movimenti_attesi) — i blocchi
> • [magazzino.vw_disponibilita](/dbzero/magazzino/views/vw_disponibilita) — la stessa formula, in colonne
>
Approfondimento funzioni:
> • [magazzino.fn_scrivi_movimento](/dbzero/magazzino/funzioni/fn_scrivi_movimento) — chi la chiama per rifiutare
>
Guide: [Linee guida SQL — 12.5 le azioni per riga](/linee-guida-sql) · brief `brief-db-magazzino-lotto-2-motore` (§4.3)

---
### 🎯 Scopo Principale

(rev 2026-09-18 — Lotto 2 del magazzino)

**Quanto può uscire.** Dati magazzino, articolo, una quantità positiva e — se ci sono — lotto,
seriale e la sorgente di chi chiede, risponde un elenco **ordinato** di motivi per cui
l'uscita non è ammessa: vuoto se è ammessa. Non scrive e non solleva (salvo la guardia sui
parametri): è una funzione *pura*, come tutte le `fn_check_*`.

⭐ **La chiamano in due, e il numero è uno.** La primitiva
[fn_scrivi_movimento](/dbzero/magazzino/funzioni/fn_scrivi_movimento) la chiama dentro il lock
per rifiutare col primo motivo; l'interfaccia la chiama come operatore per spegnere un pulsante
e dire perché. Non possono divergere, perché la regola è scritta in un posto solo: la scheda
non promette mai ciò che il sistema rifiuterà.

---

### I due motivi, nell'ordine

| # | Codice | `reason` | Quando |
| --- | --- | --- | --- |
| 1 | `E_MAG_GIACENZA_INSUFFICIENTE` | `GIACENZA_INSUFFICIENTE` | il **fisico** alla grana più fine dichiarata è minore della richiesta: se c'è un seriale, la sua posizione in questo magazzino; se c'è un lotto, la somma di quel lotto; altrimenti la giacenza dell'articolo. Un'uscita di 5 pezzi dal lotto L non passa perché l'articolo ne ha 20 se il lotto L ne ha 3 |
| 2 | `E_MAG_MERCE_BLOCCATA` | `MERCE_BLOCCATA_PER_ALTRI` | i **blocchi** stanno alla grana dell'articolo: giacenza + somma (firmata, quindi negativa) dei blocchi aperti **altrui** è minore della richiesta. «Altrui» = con una sorgente diversa da quella di chi chiede; un blocco senza sorgente è sempre altrui |

Nella frase per l'operatore entrano i codici di articolo e magazzino e i numeri interi
(«disponibili 11, richiesti 12»); le chiavi i18n del tooltip sono
`magazzino.disponibilita.blocco.giacenza_insufficiente` e `…merce_bloccata`.

⚠️ **Un blocco è un'uscita attesa.** Un atteso in *entrata* (merce in arrivo) non entra nel
conto: farebbe uscire merce promessa da un arrivo non ancora avvenuto. La colonna «in arrivo»
è di un lotto successivo, e questa funzione non la anticipa.

---

### Chi è esonerato lo dice il chiamante

La funzione **non legge la causale** — così l'interfaccia può chiederle la disponibilità senza
averne una in mano. È la primitiva a passarle `p_ignora_blocchi = causali.is_rettifica`: una
rettifica registra un **fatto** sulla merce, un blocco è una **promessa**, e il fatto vince
(il fisico resta). Con `consente_stock_negativo` la primitiva non la chiama affatto.

---

### Il perimetro

È `SECURITY INVOKER`: chiamata dall'operatore legge il magazzino *se lo vede* (altrimenti
zero — e un magazzino che non vede è un magazzino su cui non scriverà); chiamata dalla
primitiva legge tutto il magazzino, che è di un emittente solo.

Presidio: `db/pgtap/magazzino/test-fn-scrivi-movimento-disponibilita-v1.sql` (compreso il
test che la chiama da sola e confronta i suoi valori con la frase della madre).

---

### Storia

* 2026-09-18 — nasce con il Lotto 2 (`20260918-11`).

---

{% include-markdown "signature-core.md" %}
