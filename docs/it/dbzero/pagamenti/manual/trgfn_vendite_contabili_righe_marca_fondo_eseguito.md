## 📘 Documentazione Concettuale – Trigger function `pagamenti.trgfn_vendite_contabili_righe_marca_fondo_eseguito`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe) — la riga, col suo legame `fondo_source_id`
> * [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source) — l'atto che il trigger porta a `ESEGUITO`
>
> Approfondimento viste:
>
> * [vendite.vw_fondi_fattura_da_decidere](/dbzero/vendite/views/vw_fondi_fattura_da_decidere) — uno dei tre lettori che filtrano sullo stato dell'atto
>
> Approfondimento funzioni:
>
> * [vendite.fn_sync_contabili_fondo_fattura](/dbzero/vendite/funzioni/fn_sync_contabili_fondo_fattura) — il giro che non vede più l'atto eseguito
> * [vendite.fn_applica_fondi_fattura](/dbzero/vendite/funzioni/fn_applica_fondi_fattura) — non lo applica una seconda volta
> * [vendite.trgfn_fondi_source_guard_transizione](/dbzero/vendite/funzioni/trgfn_fondi_source_guard_transizione) — la matrice dell'atto, che l'aggiornamento attraversa
> * [vendite.fn_saldo_sorgente_fondo](/dbzero/vendite/funzioni/fn_saldo_sorgente_fondo) — regge sull'invariante che questo trigger mantiene

---

### 🎯 Scopo Principale

Quando la riga contabile nata da un **fondo fattura** entra in `POSTATA`, porta l'atto che l'ha
generata a **`ESEGUITO`**.

In parole semplici: *appena il trasferimento è registrato in contabilità, il fondo smette di
essere una cosa da lavorare e diventa una cosa fatta.*

---

### ⭐ Perché un trigger e non una riga dentro la madre del posting

Perché **scatta sul fatto**, non su chi se lo ricorda. La madre del posting non è l'unica strada
per cui una riga contabile può finire registrata: c'è la registrazione tardiva, c'è la
correzione a mano, arriveranno l'import da flusso bancario e il ri-posting. Una riga di codice
dentro *una* di quelle strade protegge quella strada; un trigger sulla tabella protegge **il
dato**.

È un effetto che segue, non un guard che rifiuta: per questo è un trigger `AFTER` in fase
`z90`, dopo i guard, che devono poter rifiutare la riga prima che l'atto venga marcato.

---

### ⭐ Il guadagno è strutturale

Tutti e tre i lettori dei fondi filtrano sullo **stato dell'atto**:

| Chi | Filtra | Effetto dello stato `ESEGUITO` |
| --- | --- | --- |
| [vendite.fn_sync_contabili_fondo_fattura](/dbzero/vendite/funzioni/fn_sync_contabili_fondo_fattura) | `ASSEGNATO` | il ciclo non vede più il fondo registrato |
| [vendite.fn_applica_fondi_fattura](/dbzero/vendite/funzioni/fn_applica_fondi_fattura) | `DISPONIBILE` | non lo applica una seconda volta |
| [vendite.vw_fondi_fattura_da_decidere](/dbzero/vendite/views/vw_fondi_fattura_da_decidere) | `DISPONIBILE` | non lo propone come «non più capiente» |

Un fondo che esce da `ASSEGNATO` **esce da tutti e tre gratis**, senza che nessuno dei tre
cambi. È così che i due difetti storici, il giro che riscriveva una riga già registrata e il
fondo interamente registrato che si auto-annullava, smettono di essere *raggiungibili* invece di
essere tamponati uno per uno.

---

### Tre condizioni, e nessuna è decorativa

| Condizione | Perché |
| --- | --- |
| la riga viene da un fondo | altrimenti non c'è niente da marcare, ed è il caso della stragrande maggioranza delle righe |
| la riga è attiva | una riga disattivata non è in nessun conto: dire che il denaro si è mosso sarebbe falso |
| l'atto è ancora `ASSEGNATO` | idempotenza: un ri-posting non cambia nulla, e un atto `ANNULLATO` o `DISPONIBILE` non viene resuscitato |

Su un aggiornamento che non cambia lo stato della riga il trigger non fa niente.

⚠️ **«Stato registrato» oggi è `POSTATA` e basta**, confrontato per `codice_interno` (la chiave
immutabile, mai `codice`). Non c'è una bandiera di catalogo per dirlo, accanto a `is_postabile`,
`is_final`, `richiede_abbinamento` e `lavorata`: sarebbe una colonna per un insieme di **uno**.
Il giorno in cui gli stati registrati diventassero due, la bandiera diventa la mossa giusta.

---

### ⚠️ Scrive da `pagamenti` verso `vendite`

1. ⚠️ `vendite.fatture_fondi_fattura_source` ha la **row security**, e il trigger non è
   `SECURITY DEFINER`: l'aggiornamento vede solo gli atti che chi registra vede. Un atto fuori
   dal perimetro di chi scrive resterebbe `ASSEGNATO` senza errore, perché un aggiornamento che
   non trova righe non solleva.
2. Il blocco colonne su quella tabella ferma importo, fattura sorgente, tipo di fondo e
   origine: **lo stato non è fra quelle**.
3. Scrivendo lo stato fa scattare
   [vendite.trgfn_fondi_source_guard_transizione](/dbzero/vendite/funzioni/trgfn_fondi_source_guard_transizione),
   la matrice dell'atto, che ammette `ASSEGNATO → ESEGUITO`. È la ragione dell'**ordine
   obbligato** con cui è stato applicato: prima il vocabolario degli stati, poi la matrice, poi
   questo trigger.

---

### Codici errore

Nessun codice proprio. Se il passaggio di stato non fosse ammesso parlerebbe la matrice
dell'atto (`E_FONDO_STATO_NON_AMMESSO`), ma la condizione sull'atto ancora `ASSEGNATO` fa sì che
non accada.

---

### Test

* `db/pgtap/vendite/test-fondo-fattura-eseguito.sql` — la riga passa a `POSTATA` e l'atto
  diventa `ESEGUITO`; `ESEGUITO` è terminale; l'**invariante** su cui regge
  `vendite.fn_saldo_sorgente_fondo`, *nessun fondo `ASSEGNATO` ha una riga già registrata*; il
  sync non riscrive più quella riga e non annulla più quel fondo; il reset non tocca un atto
  eseguito.
* `db/pgtap/config/test-costanti-catalogo-citate-dal-codice-v1.sql` — lo stato `POSTATA` che il
  trigger cita esiste a catalogo.

---

### Note di migrazione

* 2026-08-21 — nasce insieme allo stato
  `ESEGUITO` dell'atto.
* 2026-08-31 — `vendite.fatture_fondi_fattura_source` prende la row security: cade la premessa «quella tabella non ha
  RLS, quindi il trigger non incontra il problema del padre che non vede», scritta quando il
  trigger è nato.

---

{% include-markdown "signature-core.md" %}
