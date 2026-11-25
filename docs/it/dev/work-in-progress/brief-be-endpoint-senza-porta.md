# Brief BE/FE — Gli endpoint senza porta: l'outbox delle mail e tre ritiri da decidere

## ⏭️ Chi riparte — aggiornato al 2026-11-25

**Riparte: Tid**, con le due decisioni di §1 e §2. Fino ad allora nessuno ha lavoro da fare.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | Tid | L'outbox serve a un operatore (si apre la porta) o è una funzione di configurazione (si chiude)? | §1.2 | — |
| 2 | sessione DB | Se la porta si apre: il brief DB per l'azione di processo `invia_email` | §1.3 | 1 |
| 3 | team BE/FE | Se la porta si apre: la schermata dell'outbox, poi l'apertura oltre `config` | §1.3 | 2 |
| 4 | Tid | I tre ritiri: `job-summary`, `manual-lookup`, `core/users/{id}/permessi-effettivi/` | §2 | — |
| 5 | team BE/FE | I ritiri decisi, con la verifica dei chiamanti | §2.2 | 4 |
| 6 | team BE/FE | Archiviazione in `work-done/` | §3 | 3 o 1, 5 |

**Decisioni aperte di Tid:** le due di §1.2 e §2.

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-11-25. **A chi:** Tid, poi il team BE/FE; la sessione DB solo
> se l'outbox si apre.
> **Origine:** il residuo del
> [piano BE/FE endpoint senza porta](../work-done/2026/piano-be-fe-endpoint-senza-porta.md), archiviato lo stesso
> giorno dopo la riverifica sul codice. La risposta «persona o servizio» per le tredici rotte (piano §1) è chiusa,
> come la lista del log (Strumenti › Email, 2026-09-26) e la rettifica controllata dei listini, che ha una porta dal
> 2026-11-15. Restano l'outbox (piano §2.3 passo 5) e i ritiri (piano §2.5), con un candidato nuovo. Il **perché**
> di ogni voce sta nel piano: qui solo cosa resta.
> **Brief vicini verificati:**
> [brief-db-email-visibilita-per-ambito](../work-done/2026/brief-db-email-visibilita-per-ambito.md) (chiuso): la RLS
> per ambito su log, bozze e allegati c'è. Nessun brief aperto chiede l'azione `invia_email`.

---

## 1. L'outbox delle mail

### 1.1 Lo stato, verificato sul codice il 2026-11-25

- Le 9 rotte di `/core/email/outbox/` (bozza, allegati, `prepare`, `send`, `cancel`) sono servite
  ([email_views.py](../../../../backend/apps/core/api/email_views.py)) e restano sotto l'area `config`.
- Nessun file di `frontend/src` le chiama.
- L'azione di processo `invia_email` non esiste: nessun changeSet la crea, nessun brief la chiede. Il commento in testa
  a `email_views.py` fissa l'ordine: prima l'azione a catalogo, poi la schermata, **poi** l'apertura oltre `config`.
  Mai il contrario.
- Il perimetro sui dati è già a posto: la policy `rls_email_outbox_ambito` applica SISTEMA, REPARTO e OPERATORE,
  in AND con l'emittente.

### 1.2 La decisione di Tid

È la domanda del piano §3.2, posta di nuovo per la sola parte che spedisce: *un operatore che non amministra deve
poter preparare e spedire una mail dall'applicazione?*

- **(a) Si apre.** Si procede come in §1.3.
- **(b) Si chiude.** L'outbox resta una funzione di chi ha `config`. Le 9 rotte passano da *persona* a *servizio*, e
  si decide se ritirarle o tenerle per i processi che spediscono da sé.

### 1.3 Il lavoro, se si apre

1. **Brief DB:** l'azione di processo `invia_email` a catalogo, col suo livello. Va scritto in una sessione DB.
2. **BE:** le view dell'outbox leggono l'azione al posto dell'area `config`.
3. **FE:** la schermata. È un flusso a stati (bozza → allegati → invio/annullo), quindi un drawer con `FormFooter`,
   non una lista. Accanto alla lista del log, nella voce Strumenti › Email, col BB `EmailLogLista`.
4. **Doc:** `api_email.md` e la riga «Email» di api.md §Endpoint attivi.

## 2. I ritiri da decidere

| Rotta | Chiamanti al 2026-11-25 | Perché è candidata |
| --- | --- | --- |
| `GET /core/tracciamento/job-summary/` | Nessuno nel FE né nei tool dell'assistente; test in `core/tests/api/test_tracciamento_api.py` e nei test del tracciamento | Già nel piano §1 #6: la stessa domanda ha due risposte migliori, il pannello code e il digest dei presidi |
| `GET /anagrafiche/utilities/manual-lookup/` | Nessuno nel FE né nei tool dell'assistente | Già nel piano §1 #12: superata dai lookup ricchi (`billing-account/lookup/`, `istanze-utility/lookup/`) |
| `GET /core/users/{id}/permessi-effettivi/` | Nessuno nel FE; test in `core/tests/api/test_permessi_effettivi_api.py` | **Nuova.** Nel piano §1 #7 restava «servizio» perché dava ciò che il pannello non dava: *cosa risulta davvero*. Dal 2026-10-04 (tetto d'area) il pannello ha un suo endpoint, `amm-software/operatori/<id>/permessi-effettivi/`, che lo mostra |

### 2.1 Cosa va pesato

Per `core/users/{id}/permessi-effettivi/` si ritirerebbe solo la rotta: la lettura che c'è dietro sta in
`permissions_resolver` ed è la stessa che usa `permessi-audit`. Va verificato che `permessi-audit` non perda niente.

### 2.2 Il lavoro, per ogni ritiro deciso

- Si cercano i chiamanti nel FE **e** nei tool dell'assistente AI, il giorno stesso del ritiro.
- Si tolgono rotta, view, test della rotta e documentazione `manual/`. Il presidio della documentazione delle rotte
  (`core/tests/test_copertura_doc_api.py`) deve restare verde.
- Una riga in api.md, se la rotta vi è nominata.

## 3. Alla chiusura

Il brief va in `work-done/` quando l'outbox è aperto o chiuso per decisione, e i ritiri sono fatti o rifiutati.

---
{% include-markdown "signature-core.md" %}
