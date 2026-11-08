## 📘 Documentazione Concettuale – Funzione `pratiche.fn_prendi_in_carico_flusso`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — il flusso che si prende in carico
> * [pratiche.competenze_flussi](/dbzero/pratiche/tabelle/competenze_flussi) — la matrice delle competenze per template
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane) — il reparto anagrafico dell'operatore
>
> Approfondimento funzioni:
>
> * [pratiche.fn_coda_lavoro_operatore](/dbzero/pratiche/funzioni/fn_coda_lavoro_operatore) — la coda che propone gli stessi flussi con la stessa policy
> * [pratiche.trgfn_flussi_giornale_assegnazione](/dbzero/pratiche/funzioni/trgfn_flussi_giornale_assegnazione) — registra la presa in carico nel giornale

---

### 🎯 Scopo Principale

`pratiche.fn_prendi_in_carico_flusso` assegna un flusso `DA_ESEGUIRE` a un operatore, applicando la
policy di eleggibilità «reparto prima, competenza opzionale». Restituisce `true` se ha assegnato il
flusso, `false` se il flusso era già di quell'operatore.

L'operazione è atomica: la riga del flusso si blocca in lettura, e di due operatori che provano insieme
il secondo attende e poi riceve `E_FLUSSI_GIA_ASSEGNATO`.

---

### I controlli, nell'ordine

1. Flusso e operatore sono obbligatori e positivi.
2. Il flusso esiste.
3. Il flusso è in stato `DA_ESEGUIRE`.
4. Se è già assegnato allo stesso operatore, non fa niente e restituisce `false`.
5. Se è già assegnato a un altro operatore, rifiuta.
6. L'operatore è eleggibile secondo la policy qui sotto.

Superati i controlli, assegna il flusso all'operatore e verifica di aver aggiornato esattamente una riga.

---

### La policy di eleggibilità

Per un flusso e un operatore:

* il template è **sotto competenza** quando esiste almeno una competenza **attiva** per il template del
  flusso;
* l'operatore è **competente** quando ha una competenza attiva per quel template;
* l'operatore è **nel reparto** quando il flusso ha un reparto e coincide col reparto anagrafico
  dell'operatore.

| Caso | Flusso | Eleggibile se | Rifiuto |
| --- | --- | --- | --- |
| A — reparto e competenza | reparto valorizzato, template sotto competenza | competente | `E_FLUSSI_COMPETENZA_MANCANTE` |
| B — solo reparto | reparto valorizzato, template non sotto competenza | nel reparto | `E_FLUSSI_PRESA_NON_ELIGIBILE` |
| C — niente configurato | nessun reparto, template non sotto competenza | chiunque | — |
| D — solo competenza | nessun reparto, template sotto competenza | competente | `E_FLUSSI_COMPETENZA_MANCANTE` |

La competenza è un lucchetto opzionale: governa solo dove la matrice è configurata per quel template;
altrove decide il reparto, o la presa è libera.

⚠️ **Sotto competenza vuol dire competenza attiva**, non «una riga qualsiasi»: se tutte le competenze di
un template sono spente, lo step non è più sotto competenza, e non resta un flusso che nessuno può
prendere.

`pratiche.fn_coda_lavoro_operatore` legge le competenze allo stesso modo: i casi A e D vi compaiono al
livello competenza, il B al livello reparto. ⚠️ Il caso C nella coda è più stretto: il lavoro libero lo
propone solo all'operatore della pratica, mentre la presa in carico lo ammette per chiunque.

Il reparto scritto sulla riga di competenza non entra nella decisione: conta la coppia template e
operatore.

---

### ⭐ Il rifiuto dice quale flusso

I rifiuti per stato errato e per flusso già assegnato portano nel contesto dell'errore il **bersaglio**,
il flusso: chi prende in carico arriva da una lista, e la frase gli dice quale flusso ha rifiutato senza
che debba ritrovarselo.

---

### Effetti

La presa in carico cambia l'operatore del flusso, e il giornale registra `FLUSSO_ASSEGNAZIONE_CAMBIATA`:
anche l'auto-presa è tracciata. La funzione si chiama dal servizio del backend, che rende l'errore per
l'interfaccia.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — flusso o operatore assenti o non positivi.
* `E_VALORE_MANCANTE` — il flusso non esiste.
* `E_FLUSSI_PRESA_CARICO_STATO_ERRATO` — il flusso non è `DA_ESEGUIRE`.
* `E_FLUSSI_GIA_ASSEGNATO` — il flusso è già di un altro operatore.
* `E_FLUSSI_COMPETENZA_MANCANTE` — casi A e D, operatore senza competenza attiva.
* `E_FLUSSI_PRESA_NON_ELIGIBILE` — caso B, operatore fuori dal reparto del flusso.
* `E_QUERY_FAILED` — l'assegnazione non ha aggiornato esattamente una riga.

---

### Note di migrazione

* 2026-06-18 — la competenza passa da obbligatoria a condizionale: prima ogni flusso con template la
  richiedeva (brief-db-assegnazione-flusso).
* 2026-08-24 — i rifiuti portano il bersaglio sul flusso (brief-db-bersaglio-errore).

---

{% include-markdown "signature-core.md" %}
