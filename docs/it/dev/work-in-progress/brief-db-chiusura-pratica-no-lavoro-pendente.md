# Brief DB — Chiusura pratica generale: "nessun lavoro pendente" (motore configurabile)

> **Tipo**: brief DB (cosa serve + design) · **Destinatario**: team DB (`dev/db-tid`)
> **Priorità**: 🔴 alta (blocca il percorso PREVENTIVI merce; regola generale del motore)
> **Data**: 2026-06-30
> **Origine**: PRA-0000225 — la pratica si **auto-chiude a SMISTAMENTO**, prima che
> nascano i flussi ordine condizionali (CONFERMA_ORDINE/INVIO_COMMESSA). Vedi
> [analisi-uniformita-pratica-preventivi.md](analisi-uniformita-pratica-preventivi.md),
> [piano-be-fe-uniformita-pratica-preventivi.md](piano-be-fe-uniformita-pratica-preventivi.md).

---

## 0. Perché è un tema di motore (non un caso vendite)

Le pratiche sono il motore generico per tracciare la maggior parte delle casistiche →
devono avere **rami condizionali** (step che nascono solo se servono). Con rami
condizionali *terminali*, l'auto-chiusura attuale sbaglia. Serve una **regola di
chiusura generale e data-driven**, valida per ogni tipo prestazione presente e futuro,
senza logica per-caso.

## 1. Problema attuale

`fn_check_pratica_chiudibile` chiude quando **non resta alcun template OBBLIGATORIO
bloccante** (`fn_check_chiusura_pratica`: obbligatorio + non completato + percorribile).
Il trigger `trg_flussi_z90_autochiusura_pratica_upd` (AFTER UPDATE OF stato_id) la applica
a ogni completamento flusso.

Due difetti con i rami condizionali:
1. **Ignora i flussi ISTANZIATI aperti non obbligatori.** Gli step condizionali (es.
   `CONFERMA_ORDINE`, `obbligatorio=false`) non bloccano → la pratica chiude anche se sono
   aperti / stanno per nascere.
2. **Timing**: il trigger scatta *durante* l'UPDATE di completamento di SMISTAMENTO,
   **prima** che l'handler di dominio (dispatch handler-eventi) crei i flussi a valle
   on-demand → al momento del check quei flussi non esistono ancora → chiude.

Non è risolvibile con `obbligatorio=true` sui condizionali: il check è **template-based**,
quindi bloccherebbe **anche** le pratiche del ramo alternativo (es. tutto-servizi, dove
quei flussi non nascono mai) → non chiuderebbero più.

## 2. Principio (regola unica, generale)

Una pratica è **chiudibile** quando **non ha più lavoro da fare**:

- ogni **template obbligatorio** ha un'istanza **COMPLETATA** (percorso minimo fatto), **e**
- **nessun flusso ISTANZIATO è in stato non terminale** (nessun lavoro avviato pendente:
  DA_ESEGUIRE / IN_CORSO / SOSPESO).

I rami condizionali si gestiscono **da soli**: sono `obbligatorio=false` e vengono
**istanziati on-demand** dal dominio solo quando servono. Finché un'istanza condizionale è
aperta, la pratica non chiude; se il ramo non serve, l'istanza non nasce e non blocca.
Il flag `chiude_pratica` resta come **override esplicito** (chiusura su flusso designato)
per i casi che lo vogliono.

## 3. Cosa serve (DB motore)

**D1 — `fn_check_pratica_chiudibile`**: aggiungere alla condizione di chiudibilità
"**nessun flusso istanziato in stato non terminale**" (oltre all'attuale "nessun template
obbligatorio bloccante"). Gli stati terminali dei flussi: COMPLETATO (+ eventuali
ANNULLATO/annullati). Quelli non terminali (DA_ESEGUIRE/IN_CORSO/SOSPESO) bloccano.

**D2 — Timing dell'auto-chiusura**: la valutazione deve avvenire **dopo** che gli handler
di completamento hanno creato i flussi a valle. Proposta: rendere l'auto-chiusura un
trigger **DEFERRABLE INITIALLY DEFERRED** (valuta a fine transazione, quando i flussi
on-demand esistono già), oppure equivalente che garantisca l'ordine "prima gli handler,
poi la chiusura". Va verificata la coerenza con il guard `trg_flussi_a10_guard_chiusura_prematura`
e con il guard pratica-terminale (l'handler crea i flussi a valle **prima** che la pratica
possa chiudere).

**D3 — Binding on-demand del ramo ordine** (seed, per PREVENTIVI): l'handler
`vendita.post_smistamento` è già bindato su SMISTAMENTO COMPLETATO/POSITIVO e crea
CONFERMA_ORDINE. Per creare **INVIO_COMMESSA** quando CONFERMA_ORDINE si chiude, bindare lo
**stesso** handler anche su **CONFERMA_ORDINE (9013) · COMPLETATO · POSITIVO** (l'handler è
già generico: crea i post-ordine percorribili). *(Se preferite, si può valutare in
alternativa un secondo handler; ma il riuso è sufficiente.)*

## 4. Criteri di accettazione (scenari PREVENTIVI 9004)

- **Merce**: dopo SMISTAMENTO (con ordine generato) la pratica **resta APERTA**; nasce
  CONFERMA_ORDINE; alla sua chiusura nasce INVIO_COMMESSA; alla chiusura di INVIO_COMMESSA
  (nessun flusso aperto, tutti gli obbligatori fatti) la pratica **si chiude**.
- **Tutto-servizi**: dopo SMISTAMENTO (nessun ordine, nessun flusso condizionale creato) la
  pratica **si chiude** subito.
- Nessuna regressione sugli altri tipi prestazione (chiudono come prima quando non hanno
  flussi istanziati aperti).
- pgTAP sui due scenari (merce / servizi) + regressione tipi esistenti.

## 5. Lato BE (fuori scope DB — lo facciamo noi)

- `post_smistamento` già crea i flussi a valle percorribili (guard prereq BEFORE INSERT →
  crea solo i percorribili); con D3 crea INVIO_COMMESSA alla chiusura di CONFERMA_ORDINE.
- Nessun'altra logica di chiusura lato BE: la chiusura è del motore (data-driven).

## 6. Nota di design (configurabilità)

La regola è **interamente guidata dai dati del grafo** (`template_flussi`: obbligatorio +
prerequisiti esito-aware + binding handler che istanziano i condizionali). Un nuovo caso
futuro con rami condizionali **non richiede codice motore**: si configura il grafo. È la
parametrizzazione ampia richiesta per usare le pratiche come tracker generale.
