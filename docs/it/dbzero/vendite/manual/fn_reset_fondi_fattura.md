## 📘 Documentazione Concettuale – Funzione `vendite.fn_reset_fondi_fattura`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatture](/dbzero/vendite/tabelle/fatture) — la fattura figlia di cui si disfano i fondi
> * [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source) — l'atto
> * [vendite.fatture_fondi_fattura](/dbzero/vendite/tabelle/fatture_fondi_fattura) — il fondo applicato
>
> Approfondimento funzioni:
>
> * [vendite.fn_check_fondo_cancellabile](/dbzero/vendite/funzioni/fn_check_fondo_cancellabile) — il criterio
> * [vendite.fn_applica_cancellazione_fondo_fattura](/dbzero/vendite/funzioni/fn_applica_cancellazione_fondo_fattura) — la primitiva che cancella
> * [vendite.fn_cleanup_fatture_by_ids](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids) — l'unico chiamante: la pulizia del lotto
> * [vendite.fn_applica_fondi_fattura](/dbzero/vendite/funzioni/fn_applica_fondi_fattura) — chi applica i fondi che qui si disfano
>
> Guide:
>
> * [Fatturazione](/guide/fatturazione) — il reset del lotto e i fondi che non tocca
> * [Gestione dei pagamenti](/guide/gestione-dei-pagamenti) — i fondi fattura

---

### 🎯 Scopo Principale

La funzione **`vendite.fn_reset_fondi_fattura()`** disfa i fondi fattura
applicati ad una **fattura figlia**:

* **cancella** l'atto che non è stato eseguito, insieme alle sue righe
* elimina le righe in `fatture_fondi_fattura`
* **non tocca** un atto già `ESEGUITO`: lo segnala e va avanti
* gestisce i casi bloccati da contabile in stato `CHIUSA`

> ⭐ **La regola sta in una riga: si cancella solo ciò che non è stato eseguito.**
> Fino al 21-08-2026 il reset *riapriva* l'atto (`stato = 'DISPONIBILE'`), e su un
> atto già eseguito scriveva `ANNULLATO` **lasciando la fattura figlia
> agganciata** — un record che si contraddiceva.
>
> Adesso: un atto mai eseguito è una **proposta**, non un fatto, e una proposta
> si cancella. Il giro successivo ne fa una nuova, letta sul residuo **di
> adesso** invece che sull'importo vecchio congelato.
>
> ⚠️ **Due conseguenze da conoscere.** La tabella non è storicizzata, quindi il
> `DELETE` è definitivo. E cancellare **riapre la rigenerazione**: è la regola
> dell'«atto unico» a impedire al giro notturno di rifare un fondo, e quella
> guarda se un atto esiste *in qualunque stato*. È il comportamento cercato, ma
> è un cambio reale rispetto a prima.
>
> ⭐ **È un'operazione TECNICA sul ciclo di vita della figlia** — il ritorno di
> un lotto in bozza — **e non una reazione ai pagamenti**: nessun incasso la
> chiama e nessun incasso deve chiamarla.
>
> La precisazione risponde a una domanda che il piano si era posto: *«che cosa
> succede a un fondo `ASSEGNATO` se la sorgente riceve poi un incasso?»*.
> Risposta: **niente**. Un fondo assegnato non si tocca; l'eventuale doppio
> pagamento diventa un credito sulla sorgente e si governa nel **processo
> rimborsi**, in `pagamenti`. Senza questa riga è il tipo di funzione che al giro
> dopo qualcuno chiama credendo di aver trovato il pezzo mancante.

---

### Il criterio e la cancellazione stanno altrove

I controlli «l'atto non è ancora un fatto» e i tre `DELETE` nell'ordine imposto
dalle chiavi esterne non sono scritti qui:

```text
il CRITERIO  →  vendite.fn_check_fondo_cancellabile
l'AZIONE     →  vendite.fn_applica_cancellazione_fondo_fattura (la primitiva)
la REAZIONE  →  resta qui, ed è l'opposto di quella del gesto manuale
```

| Chi | Quando l'atto è bloccato |
| --- | --- |
| **questa funzione** | **segnala e prosegue** — è un giro tecnico su N atti, e un'eccezione fermerebbe il reset di un lotto intero |
| il gesto «cancella il fondo» (`fn_cancella_fondo_fattura`, con la primitiva) | **rifiuta e lo dice** — è il gesto di una persona su un atto |

Il blocco degli atti `ESEGUITO` chiede al criterio invece di guardare lo stato:
`ATTO_ESEGUITO` è il primo motivo che il criterio prova. La quarta condizione
(`FIGLIA_CONGELATA`) **non si accende in questo percorso**: la figlia è la fattura
che la pulizia del lotto sta cancellando, e i controlli d'ingresso dei verbi del
reset la vogliono pre-fiscale. Il ramo resta scritto, perché un motivo senza
reazione sarebbe un atto saltato in silenzio.

⭐ **Un atto trattenuto da un riporto** viene **saltato** con una nota nel diario
(`W_FONDO_TRATTENUTO_DA_SISTEMAZIONE`), invece di far fallire il reset con un
errore nudo di chiave esterna. ⚠️ Il reset del lotto fallirà comunque più avanti
— l'atto continua a puntare la fattura che si sta cancellando — ma il diario dice
perché: *fallire ad alta voce resta, il silenzio no.*

---

### Chi la chiama

È riservata al proprietario: l'applicazione non la può eseguire. La chiama solo
[`vendite.fn_cleanup_fatture_by_ids`](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids),
dentro i verbi del reset del lotto, che chiedono il loro permesso e rimettono il
perimetro su lotto e fatture. Per questo cancella con la primitiva e non col
verbo pubblico, che chiede `governa_fondo_fattura`: il reset del lotto ha il suo
permesso, nei suoi verbi.

---

### Regole principali

* `p_fattura_id` obbligatorio.
* Opera solo su `source` con `stato = 'ASSEGNATO'`.
* Applica il reset solo ai tipi con `codice_interno = 'F_F_ADD_ACC'`.
* **Tre esiti, non più due:**

| Che cosa trova | Che cosa fa | Che cosa scrive nel diario |
| --- | --- | --- |
| un atto **`ESEGUITO`** (o, anomalia, `ASSEGNATO` con una riga già registrata) | **niente**: non si tocca | `W_FONDO_ESEGUITO_NON_RESETTABILE` |
| una riga contabile sotto una distinta **`CHIUSA`** | `stato = 'ANNULLATO'` + la ragione in `motivo` | `W_FONDO_MINIMO_NON_RIPRISTINABILE` |
| tutto il resto | **cancella** l'atto e le sue righe | — |

> ⚠️ **I due avvisi non dicono la stessa cosa, ed è il motivo per cui sono due.**
> Il primo significa *«il denaro è già stato registrato»*; il secondo *«la
> distinta è stata chiusa **senza** che quel denaro fosse registrato»*. Sono
> situazioni opposte. Fino al 21-08-2026 il messaggio del secondo diceva «già
> postato», cioè proprio la cosa che nel suo caso **non** era successa.
>
> ⚠️ Il blocco della distinta chiusa guarda **anche le righe non attive**: una
> riga archiviata in una distinta chiusa resta un fatto, e comunque impedirebbe
> di cancellare l'atto (la riga punta all'atto con una FK).
>
> ⚠️ **Perché la colonna e non solo il log.** La ragione c'era già, ma viveva in
> un **messaggio di diario**: leggibile da una persona, inutilizzabile da una
> query. Con `motivo` obbligatorio su ogni `ANNULLATO`
> (`chk_fondi_source_motivo_obbligatorio`), «perché questo fondo è sparito» si
> risponde guardando la riga.

---

### Output

Ritorna:

* `deleted_source` = numero di **atti cancellati**
* `deleted_fondi` = numero righe fondi eliminate

> ⚠️ **La prima colonna si chiamava `updated_source`** e ha cambiato nome col
> comportamento: dal 21-08-2026 non si aggiorna più niente, si cancella. Un
> nome che descrive un comportamento finito è peggio di un nome generico,
> perché si legge come se fosse stato verificato.
>
> ℹ️ Gli atti **bloccati** non entrano nel conto: `deleted_source = 0` con un
> avviso nel diario è la risposta normale su una fattura i cui fondi sono stati
> registrati o la cui distinta è chiusa.

---

### Note di migrazione

* 2026-08-21 — l'atto non eseguito si cancella invece di tornare `DISPONIBILE`, e un atto
  eseguito non si tocca mai; la prima colonna del risultato si chiamava `updated_source`.
* 2026-08-31 — il criterio passa a `fn_check_fondo_cancellabile` e i tre `DELETE` a una sede
  unica (brief-db-fondo-fattura-ricalcolo-e-governo, D-21).
* 2026-11-25 — cancella con la primitiva `fn_applica_cancellazione_fondo_fattura` invece che col
  verbo pubblico, e diventa riservata al proprietario (brief-db-porte-aperte-dalla-sola-guc,
  giro 8 + 1-7).

---

{% include-markdown "signature-core.md" %}
