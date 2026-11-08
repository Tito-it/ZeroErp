# Gestione Pratiche — Come procedere (stato attuale + roadmap)

> **Tipo documento**: operativo "come procedere" — **autorevole per i prossimi
> passi del dominio pratiche**. · **Data**: 2026-06-20 (revisione 2026-11-08: §3, la bozza abbandonata dal flusso) · **Stato**: 🟢 vivo.
>
> **Origine**: consolidamento dello stato pratiche dopo che il **primo consumatore
> (PREVENTIVI)** è stato validato end-to-end (anello3 §8.5, Fase E) e dopo
> l'aggiunta di coda lavoro + assegnazione flusso + pannello "Le mie attività".
> Raccoglie e mette in ordine i punti dispersi nei 6 handoff pratiche
> point-in-time (ora consolidati in un unico handoff + storia git).
>
> **Documenti collegati**: [analisi-pratiche-domini-anello3.md](analisi-pratiche-domini-anello3.md)
> (visione integrazione domini), [analisi-pratiche-workflow-v2.md](../work-done/analisi-pratiche-workflow-v2.md)
> (motore workflow), [gestione-pratiche-v2.md](../work-done/gestione-pratiche-v2.md) (piano v1→v2,
> ormai storico), brief PREVENTIVI in `work-done/` (db/be/fe).

---

## 0. In una frase

Il motore pratiche è **validato col primo consumatore (PREVENTIVI)**. Prima di
estenderlo a **offerta / contratto / ordine**, conviene **chiudere lo smoke E2E
della base**; poi si replica lo stesso pattern (DB seed → handler BE → registry
FE), perché la dashboard e il container pratica sono già **generici per
`tipo_prestazione`**.

---

## 1. Stato attuale — cosa è fatto e collaudato

| Capacità | Stato | Dove |
|---|---|---|
| Motore pratiche v2: nascita **APERTA**, auto-chiusura, percorso da `template_flussi`, sola-lettura terminale | ✅ | workflow-v2, handoff 0614 |
| Esito flussi **configurabile** (MANUALE/AUTOMATICO/CONTESTUALE) + guard `COMPLETATO⇒esito` | ✅ committato `d16710a68` | handoff 0618 |
| Giornale di bordo `DOMINIO_*` + decode stati + giornale "parlante" | ✅ committato `98c3d3e19` | handoff 0618 |
| Aggancio **documento↔flusso** (ROOT per-flusso, non per-pratica) | ✅ committato `b027e3020` | handoff 0617 |
| **Attività-UI da flusso** (apri documento) + **completamento event-driven** (handler su evento) | ✅ committato `aa3b02c2d` | handoff 0615 |
| **Assegnazione flusso** a operatore/reparto (policy reparto-first, 4 casi) | ✅ committato `a97798d40` | handoff 0619 |
| **Coda lavoro** + pannello **"Le mie attività"** | ✅ committato `acec053c2` | (questa sessione) |
| **PREVENTIVI end-to-end**: richiesta → preventivo → accetta → CONFERMA → commessa emittibile → fattura | ✅ validato runtime (Fase E) | anello3 §8.5 |

**Catena PREVENTIVI nel dettaglio** (il pattern di riferimento per gli altri domini):

1. **Accettazione** = completamento del flusso `APPROVAZIONE_CLIENTE` con esito
   `POSITIVO` → dispatch dell'handler event-driven **`vendita.accetta_preventivo`**
   (binding in `pratiche.template_flussi_handler_eventi`), che porta il preventivo
   ROOT ad `ACCETTATO` nella stessa transazione. *(Ha sostituito il vecchio endpoint
   M2 `/approvazione-flusso/`.)*
2. **Conferma** = il flusso `CONFERMA` entra in `IN_CORSO` → dispatch dell'handler
   **`vendita.push_preventivo`** (orchestratore `CONFERMA_VENDITA`): **split per
   natura** delle righe — MERCE→ordine (`fn_push_preventivo_a_ordine`), SERVIZIO
   una-tantum→commessa (`pr_run_commesse_push_one`, politica IMMEDIATA/DIFFERITA dai
   `handler_params`), RICORRENTE bloccata a DB. Commessa→`PRONTA_FATTURAZIONE`,
   preventivo→`EVASO` (gate EVASO: solo se nessun residuo merce).
3. A valle: commessa emittibile → pipeline lotto → fattura (già collaudata).

---

## 2. Urgenze — chiudere la base PRIMA di estendere

Replicare il pattern su offerta/contratto/ordine **sopra una base non
smoke-verificata** moltiplica il rischio. Da chiudere per primi:

| Pri | Item | Dettaglio | Fonte |
|---|---|---|---|
| 🔴 | **Smoke UI E2E pratiche MAI eseguito** | esiste solo smoke BE/unit; il giro UI reale (crea pratica → avanza flussi → accetta → conferma → commessa/fattura, su app+DB seedato+auth) non è mai stato fatto | handoff 0609, 0615, 0618 (ricorrente) |
| ✅ | **Push→commessa→fatturazione (prev/ord/contratto)** | **CHIUSO 2026-06-29** → doc in `work-done`. Smoke verdi: §1 preventivo, §2 ordine (super admin + operatore reale), §3b contratto addebito standard. §3a contratto ricorrente rinviato (utilities). 4 bug reali risolti (DB gate EVASO commessa; BE `priorita_operativa`, `codice_interno` PDF contratto, `emittente_fiscale_id` in `create_contratto`). Resta fuori: ultimo miglio lotto→fattura (blocco DB `1→8`, handoff 0619), UX FE | [a-test-push-commesse-fatturazione.md](../work-done/a-test-push-commesse-fatturazione.md) |
| 🟡 | **Part B audit giornale** (append-only) | audit utente reale su `pratiche.*` — la parte giornale/append-only resta aperta lato **team DB** | handoff 0618 |

---

## 3. Aperto — item residui dagli handoff pratiche (consolidato)

Oltre alle urgenze §2, item minori tracciati negli handoff (tutti su funzionalità
**già costruite**, non bloccanti):

- **Workflow flussi** (handoff 0614): codici guard `FLUSSI_TRANSIZIONE_NON_AMMESSA`
  / `FLUSSI_ESITO_OBBLIGATORIO` non mappati nel registry FE + prefisso `E_`
  disallineato; esporre `template_flussi.chiude_pratica` nella UI di config;
  pulizia flussi generici legacy.
- **Aggancio documento↔flusso** (handoff 0617): backfill dei 13 ROOT storici non
  fatto (testare con pratiche **nuove**); handler accetta/push ancora **per-pratica**
  (da generalizzare quando nascono offerta/contratto).
- **La bozza abbandonata dal flusso resta agganciata** (aggiunto il 2026-11-08, dal
  giro P.1 di [brief-db-sorgente-documento-e-riga](brief-db-sorgente-documento-e-riga.md),
  §8.16 BE-P.1-e). Dal passo PREVENTIVAZIONE il drawer crea la bozza del preventivo e al
  primo salvataggio automatico la aggancia al flusso come ROOT (`collegaPratica`). Se
  l'operatore la abbandona vuota, la cancellazione e' rifiutata: un documento collegato a
  una pratica non si cancella (`E_SORG_ORIGINE_REFERENZIATA`, il guard unico di
  `pratiche.pratiche_sorgenti` e' BLOCCA). La bozza vuota resta nell'elenco dei preventivi
  e riaprendo il passo si ritrova lei (un solo ROOT per flusso,
  `uq_pratiche_sorgenti_flusso_root`). Lo stesso varra' per offerta e contratto, quando
  nasceranno i loro flussi.
  - **Proposta (scelta C, Tid 2026-11-08: «va messa da qualche parte»):** la bozza vuota
    che si cancella si porta via il suo aggancio alla pratica; la pratica resta, il passo
    torna senza documento. ⚠️ E' un cambio di modello: l'azione del guard di
    `pratiche_sorgenti` (BLOCCA → CANCELLA) vale per **ogni** documento collegabile a una
    pratica, non per il solo preventivo. Si decide con la storia della decisione del giro
    P.1 davanti.
  - **Precondizione:** ogni documento collegabile a una pratica deve avere a DB la regola
    «si cancella solo la bozza vuota». Oggi ce l'hanno ordini, bolle, resi e contratti
    (giro T.4); **non** preventivi, offerte e commesse: li copre il lotto Z di
    brief-db-sorgente-documento-e-riga. Senza, CANCELLA farebbe sparire in silenzio
    l'aggancio di una commessa cancellata.
  - Fino ad allora il comportamento e' il blocco, con la sola frase del DB (il pre-check BE
    «pratiche collegate» si ritira: BE-P.1-e, scelta A).
- **Split natura** (handoff 0609): manca il **dialog FE di smistamento
  riga-per-riga** (l'endpoint/fn accettano già `righe_ids`); coordinamento
  multi-sorgente alla consegna.
- **Attività-UI** (handoff 0615): per offerta/contratto servirà **1 voce di
  registry + seed** quando nasceranno i relativi flussi.

---

## 4. Stato dei documenti pratiche (da allineare)

- **`analisi-pratiche-domini-anello3.md`** — quasi aggiornato (Fase E chiusa
  2026-06-12). **Punti stale**: §8 cita ancora l'**M2** (`completa_approvazione_da_flusso`
  + endpoint `approvazione-flusso`), **rimosso** e sostituito da
  `vendita.accetta_preventivo`; la nota §8 dice "split natura **non consegnato**"
  mentre §8.5 lo dà fatto (contraddizione interna). → corretti con marker 2026-06-20.
- **`gestione-pratiche-v2.md`** — in gran parte **storico/superato** (piano v1→v2 di
  marzo, Fasi 1-7 ✅). **Stale**: §6.2/§6.5 citano `config.modalita_fatturazione`
  come "nuova tabella" che **non esiste** (la politica vive in `handler_params`
  JSONB); §6.5 descrive il ramo fatturazione single-branch (ora è natura-split). →
  marcato come superato in testa, rimanda a questo doc + anello3 + workflow-v2.

---

## 5. Prossimi sviluppi — pratiche per OFFERTA / CONTRATTO / ORDINE

È il next step **già documentato** (anello3 §8.2–8.4 "visione ampia"; handoff
0615/0617 lo flaggano due volte). La pratica è il **container di processo
trasversale**: la dashboard è generica per `tipo_prestazione`, quindi i nuovi tipi
"compaiono da soli" una volta seedati.

### 5.1 Il pattern da replicare (da PREVENTIVI) — per layer

Per **ogni** nuovo dominio-pratica servono tre cose, nessuna delle quali è logica
nuova: è cablaggio del doc-type sul motore esistente (regola del 2).

**DB (brief → team DB)**:
- `pratiche.tipi_prestazione`: il nuovo tipo (es. `CONTRATTO_STANDARD`).
- `pratiche.template_flussi` + `template_flussi_prerequisiti` (esito-aware): gli step
  del percorso, con `azione_ui_id` (apri documento) e `handler_id`/eventi dove serve.
- `pratiche.handler_flussi`: la `handler_key` del nuovo handler (es.
  `vendita.accetta_offerta`).
- `template_flussi_handler_eventi`: binding evento→handler per le azioni di
  completamento (come `accetta_preventivo` su COMPLETATO+POSITIVO).

**BE (apps/vendite/handlers/)**:
- nuovo/i handler che implementano `BaseFlussoHandler.execute(...)`, **delegando** ai
  service/fn esistenti (mai reimplementare il dominio):
  - **accettazione** → handler event-driven su COMPLETATO (specchio di
    `accetta_preventivo_handler.py`);
  - **conferma/push** → orchestratore su IN_CORSO (specchio di
    `push_preventivo_handler.py`), che riusa le conversioni già pronte.
- registrazione in `HANDLER_MAP` via `apps/vendite/apps.py:ready()` (lazy import,
  pattern già stabilito).

**FE (`src/<dominio>/iscrizioni.js`)**:
- 1 voce iscritta con `iscriviAttivitaUi` nel registro di
  `src/pratiche/uiActivityRegistry.js` (apri il drawer di dominio dal flusso) —
  lo specchio di `HANDLER_MAP`: il motore non nomina il dominio (dal 2026-09-26) —
  + eventuali chiavi i18n; la **dashboard/percorso/coda non cambiano** (generici).

### 5.2 Specificità per dominio (cosa riusa cosa)

I "motori" di conversione documentale **esistono già** — il lavoro pratica è
avvolgerli in un percorso:

- **OFFERTA** → la conversione **offerta→ordine** è già fatta
  (`crea_ordine_da_offerta`, `fn_offerta_righe_espanse`, prezzi negoziati
  preservati, **1:1** con UNIQUE parziale). Pratica `OFFERTA_*`: richiesta →
  offerta → accettazione (handler `accetta_offerta`) → genera ordine. Nota XOR:
  da un'offerta nascono **o** ordine **o** contratto, mai entrambi.
- **CONTRATTO** → è la destinazione del **SERVIZIO_RICORRENTE** (modello: il
  ricorrente non sta nel preventivo, passa per offerta→contratto). Pratica
  `CONTRATTO_*`: percorso di sottoscrizione/attivazione; l'handler attiva il
  contratto e aggancia ROOT/COLLEGATO.
- **ORDINE** → la conversione **preventivo→ordine** è già nel push natura (ramo
  MERCE). Una pratica `ORDINE_*` standalone (ordine non originato da preventivo)
  avrebbe un percorso più corto: inserimento → conferma → push a commessa/DDT.
  Valutare se serve davvero un container pratica o se l'OdV si gestisce dal suo
  dominio (decisione di prodotto).

### 5.3 Generalizzazione necessaria (debito noto)

Gli handler accetta/push oggi sono **per-pratica PREVENTIVI** (handoff 0617). Prima
del secondo dominio conviene **estrarre il frammento condiviso** (risoluzione
ROOT/sorgenti, aggancio `pratiche_sorgenti`, scrittura giornale `DOMINIO_*`) per
non duplicarlo — è la "regola del 2" applicata agli handler.

### 5.4 Direzione alternativa documentata

Anello3 **Fase F** = **secondo consumatore non-vendite** (assistenza/ticketing —
`crm-ticketing-pratiche.md` — acquisti o CRM). Promuove il motore a "contratto
stabile" provandolo su un dominio diverso da vendite. Da scegliere in base alle
priorità di business: estensione **in profondità** (vendite: offerta/contratto) vs
**in ampiezza** (nuovo dominio).

---

## 6. Ordine consigliato

1. **Chiudere lo smoke E2E** della base (UI pratiche + ordini conferma/push) — §2.
2. **Aggiornare i 2 doc** allo stato attuale (fatto i marker stale; eventuale
   potatura ulteriore di `gestione-pratiche-v2.md`).
3. **Generalizzare gli handler** accetta/push (§5.3) — prerequisito pulito al 2° dominio.
4. **Predisporre la prima pratica nuova** (raccomandata: **OFFERTA**, perché la
   conversione a valle è già pronta) replicando il pattern §5.1.
5. Valutare CONTRATTO e l'opportunità di una pratica ORDINE standalone (§5.2).

---

## 7. Riferimenti

- [analisi-pratiche-domini-anello3.md](analisi-pratiche-domini-anello3.md) — §2 (pattern aggancio), §5 (caso vendite), §8 (roadmap).
- [analisi-pratiche-workflow-v2.md](../work-done/analisi-pratiche-workflow-v2.md) — motore workflow (ripetibilità, bivi, lenti contesto, guard chiusura).
- Brief PREVENTIVI (work-done): db / be / fe — il template implementativo.
- [brief-preventivi-ordini.md](../work-done/brief-preventivi-ordini.md) — split per natura.
- [a-test-push-commesse-fatturazione.md](../work-done/a-test-push-commesse-fatturazione.md) — smoke OdV residuo.

---

*Gestione Pratiche — come procedere — ZeroERP (2026-06-20). Documento vivo:
aggiornare quando si chiude un'urgenza §2 o si avvia un nuovo dominio-pratica §5.*
