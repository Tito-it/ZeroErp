## 📘 Documentazione Concettuale – Tabella `pratiche.giornale`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la pratica a cui ogni evento appartiene
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — il flusso, per gli eventi di flusso
>
> Approfondimento funzioni:
>
> * [pratiche.fn_log_evento_dominio](/dbzero/pratiche/funzioni/fn_log_evento_dominio) — l'unico canale degli eventi di dominio

---

### 🎯 Scopo Principale

La tabella `pratiche.giornale` è il giornale di bordo del modulo pratiche: registra ogni evento
significativo nel ciclo di vita di pratiche e flussi, una riga per evento.

---

### Chi scrive, e che cosa

Le righe le scrivono i trigger di giornale delle tabelle del modulo, ognuno per i propri eventi, e
`pratiche.fn_log_evento_dominio` per gli eventi di dominio. Il giornale si legge come append-only: si
aggiunge, non si corregge. ⚠️ È una convenzione degli scrittori, non un vincolo: nessun trigger impedisce
l'aggiornamento o la cancellazione di una riga.

| Azione | Chi la scrive | Evento |
| --- | --- | --- |
| `PRATICA_CREATA` | inserimento di una pratica | creazione della pratica |
| `STATO_CAMBIATO` | cambio di stato della pratica | cambio di stato |
| `ASSEGNAZIONE_CAMBIATA` | cambio di operatore o reparto della pratica | cambio di assegnazione |
| `PRIORITA_CAMBIATA` | cambio di priorità della pratica | cambio di priorità |
| `FLUSSO_CREATO` | inserimento di un flusso | creazione del flusso |
| `FLUSSO_STATO_CAMBIATO` | cambio di stato del flusso | cambio di stato del flusso |
| `FLUSSO_ASSEGNAZIONE_CAMBIATA` | cambio di operatore o reparto del flusso | cambio di assegnazione del flusso, anche la presa in carico |
| `NOTA_AGGIUNTA` | inserimento di una nota di pratica o di flusso | nota aggiunta |
| `ALLEGATO_AGGIUNTO` | inserimento di un allegato di pratica o di flusso | allegato aggiunto |
| `SOSPENSIONE_REGISTRATA` | inserimento di una sospensione | sospensione registrata |
| `SOSPENSIONE_CHIUSA` | riattivazione di una sospensione | sospensione chiusa |
| `PRATICA_GENERATA` | ammessa dal vocabolario; oggi nessuna funzione la scrive | pratica generata da un flusso |
| `DOMINIO_*` | `pratiche.fn_log_evento_dominio` | evento di dominio applicativo |

---

### Gli eventi di dominio

Oltre agli eventi del motore, a vocabolario chiuso, il giornale accetta eventi di dominio applicativi
col prefisso `DOMINIO_` seguito da maiuscole, cifre e trattini bassi: un evento nuovo non chiede un
vincolo nuovo. Il vincolo sull'azione ammette l'elenco del motore oppure quella forma, e rifiuta tutto
il resto.

L'unico canale per scriverli è `pratiche.fn_log_evento_dominio`, che gli handler applicativi chiamano:
forza l'origine `HANDLER` e correla la riga alla transazione. Il catalogo degli eventi di dominio in uso
sta nel catalogo dei building block del backend.

---

### Le colonne che non si capiscono dal nome

* `flusso_id` — presente solo per un evento di flusso; vuoto per un evento della pratica.
* `origine` — chi ha originato l'evento: `SISTEMA` (predefinito), `UTENTE`, `HANDLER`, `SCHEDULER`.
* `dettaglio` — i dati strutturati dell'evento, per esempio lo stato precedente e quello nuovo.
* `tx_id` — la transazione in cui l'evento è stato scritto: collega l'evento alle modifiche fatte nella
  stessa transazione su altre tabelle. Lo valorizza l'automazione `tx_id` della tabella.

---

### Accesso e indici

La tabella ha la RLS: ogni operatore vede gli eventi del perimetro del proprio emittente. Due indici
servono le letture tipiche: per data (gli ultimi eventi, un intervallo) e per azione.

---

### Note di migrazione

* 2026-06-08 — il giornale accetta gli eventi di dominio `DOMINIO_*`, con `pratiche.fn_log_evento_dominio`
  come unico canale.

---

{% include-markdown "signature-core.md" %}
