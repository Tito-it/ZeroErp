## 📘 Documentazione Concettuale – Funzione `pratiche.fn_genera_pratica_da_flusso`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.regole_generazione](/dbzero/pratiche/tabelle/regole_generazione) — la regola che si applica
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la pratica madre e la figlia
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — il flusso completato e il flusso iniziale della figlia
> * [config.stati_pratiche](/dbzero/config/tabelle/stati_pratiche) — lo stato iniziale della figlia
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_flussi_generazione](/dbzero/pratiche/funzioni/trgfn_flussi_generazione) — la chiama per le regole automatiche
> * [pratiche.trgfn_flussi_guard_definizione](/dbzero/pratiche/funzioni/trgfn_flussi_guard_definizione) — il guard che il flusso iniziale deve passare

---

### 🎯 Scopo Principale

`pratiche.fn_genera_pratica_da_flusso` crea una pratica figlia da un flusso completato, secondo una
regola di `pratiche.regole_generazione`, e ne ritorna l'id.

È il motore della generazione da pratica a pratica: la chiamano il trigger per le regole automatiche e
il backend per quelle manuali.

---

### ⭐ Una figlia sola per (flusso, tipo di destinazione)

Se esiste già una pratica generata da quel flusso con quel tipo, la funzione ritorna il suo id senza
crearne un'altra: vale per il trigger, per la richiesta manuale e per un evento doppio. Un indice unico
su `pratiche.pratiche` rende il doppione impossibile anche fuori dal motore. Resta legittimo che un
flusso generi pratiche di tipi diversi, con regole diverse.

---

### Che cosa eredita la figlia

* Dalla madre: emittente, soggetto, contesto (ruolo del soggetto e istanza della utility), billing
  account e priorità. Senza il contesto, la figlia cadrebbe fuori dalle viste che filtrano per esso.
* Dalla regola: il tipo di pratica.
* La genealogia: `pratica_padre_id` (la madre) e `flusso_origine_id` (il flusso che l'ha generata), per
  risalire in entrambi i versi.
* Lo stato `APERTA`: la figlia è un lavoro già avviato e nasce operativa. La data di apertura la mette
  il trigger della pratica.
* La definizione del workflow non si passa: la risolve il trigger di nascita della pratica per
  l'emittente della figlia.

---

### Il flusso iniziale, nella definizione della figlia

Se la regola dichiara il passo iniziale, la funzione crea il primo flusso della figlia in
`DA_ESEGUIRE`. La regola indica il passo del preset, ma la figlia può essere legata a un'edizione
diversa della definizione: il passo si ritrova per **codice** nella definizione della figlia, e la
sequenza viene da lì. Così il flusso passa `pratiche.trgfn_flussi_guard_definizione`.

Il passo iniziale deve essere senza prerequisiti, perché la figlia nasce senza flussi: altrimenti il
guard dei prerequisiti fa fallire la generazione, ed è un errore di configurazione della regola.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — flusso o regola assenti o non positivi.
* `E_VALORE_MANCANTE` — il flusso non esiste.
* `E_CODICE` — la regola non esiste o non è attiva, oppure manca a catalogo lo stato `APERTA` delle
  pratiche o `DA_ESEGUIRE` dei flussi.
* `E_GENERAZIONE_TEMPLATE_NON_IN_DEFINIZIONE` — la definizione della figlia non contiene il passo
  iniziale della regola (per esempio un'edizione che l'ha tolto).

---

### Test

* `pratiche/test-generazione-cross-pratica` — generazione automatica e manuale, unicità della figlia,
  genealogia, contesto ereditato e flusso iniziale.

---

### Note di migrazione

* 2026-06-11 — la funzione diventa idempotente per (flusso, tipo di destinazione), e la figlia porta
  genealogia e contesto della madre.
* 2026-10-08 — la figlia copia dalla madre anche il billing account (brief-db-istanza-nasce-col-ba).

---

{% include-markdown "signature-core.md" %}
