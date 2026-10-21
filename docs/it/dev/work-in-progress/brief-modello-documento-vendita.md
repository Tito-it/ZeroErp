# Brief — Il modello del documento di vendita, scritto una volta

## ⏭️ Chi riparte — aggiornato al 2026-10-21

**Riparte: Tid**, con la lettura del §2 (il modello com'è oggi) e le decisioni M-1 … M-6 del §4.
Nessun codice scritto: questo brief per ora **descrive**, non cambia niente.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ team DB | Bozza: il modello com'è oggi, le divergenze, le decisioni già prese | §2, §3 | — |
| 2 | **Tid** | Le contraddizioni aperte, decise una volta per tutti i documenti | §4 | 1 |
| 3 | team DB | Il §2, corretto con le decisioni, diventa la guida `docs/it/guide/modello-documento-di-vendita.md`; le guide `gestione-*.md` rimandano lì | §2 | 2 |
| 4 | team DB + BE | Il piano: ogni documento portato al modello **tutto in una volta**, un documento per giro | §5 | 3 |
| 5 | Tid | Fine del fermo dei temi trasversali (PROJECT_CONTEXT) | — | 3 |

Decisioni aperte di Tid: §4. Lavoro da committare: questo documento, la regola «un tema, un brief»
in `.codex/AGENTS.md` e il fermo in `.codex/PROJECT_CONTEXT.md`.

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-21. **A chi:** Tid; poi team DB e BE.
> **Origine:** D2 e D3 di [brief-be-verifica-documentazione-api](brief-be-verifica-documentazione-api.md)
> (azioni di processo mancanti fra gemelli; permesso del cambio stato del DDT). Analizzandole sono
> uscite due proposte che, senza saperlo, contraddicevano una decisione viva e ne revocavano
> un'altra (§3.2). Tid: «non mi sto più fidando… una volta in un modo, poi in un altro, poi si torna
> al precedente». Da qui la ricostruzione della storia (§1) e questo brief.
> **Brief vicini verificati:**
> [brief-db-documento-nasce-nello-stato-iniziale](brief-db-documento-nasce-nello-stato-iniziale.md)
> (stato iniziale e verbo: candidato a confluire qui, M-6);
> [brief-db-grammatica-unica-documenti](brief-db-grammatica-unica-documenti.md) (solo i nomi dei
> tipi: resta suo); [brief-db-magazzino-tutte-le-scritture-dal-verbo](brief-db-magazzino-tutte-le-scritture-dal-verbo.md)
> (magazzino; rimanda «`vendite`, brief suo»: è **questo**).

---

## 1. Perché questo brief — i fatti, con la data

Ricostruzione del 2026-10-21 su git, brief chiusi e guide (finestra 2026-09-01 → 2026-10-21).
Sono fatti datati: servono a capire, non decidono la forma (Regola zero).

* **I ritorni indietro veri sono pochissimi** (1-3: partite merce per riga, ritirata lo stesso
  giorno per prestazioni; icona e severity nelle capability, aggiunte ad aprile e tolte il 27-28/09;
  la firma con `%TYPE` persa e rimessa). Nessun brief della finestra ha disfatto il lavoro di un
  altro.
* **La sensazione di girare in tondo ha un'altra causa: ogni concetto del documento esiste in una
  copia per documento.** 11 funzioni di capability (`script.fn_available_actions_*`), 11 guard di
  transizione, 8 verbi d'annullo (`fn_annulla_*`). Ogni regola nuova che vale per tutti i documenti
  va ricopiata in 6-9 posti.
* Nella finestra sono arrivati **27 temi trasversali** (perimetro emittente, congelamento prezzi,
  icone, fuso aziendale, cache dei piani, indirizzi, annullo con legami, testata dopo l'emissione,
  articoli ammessi, grammatica unica, modelli standard…), ciascuno applicato **un documento alla
  volta**: il 61% dei changeSet sui documenti. `fn_available_actions_offerta` è stata riscritta 12
  volte, ogni volta per una ragione diversa.
* **Non esiste un documento che fissi il modello comune.** Ci sono sei guide per documento
  (`gestione-preventivi.md`, `-ordini`, `-ddt`, `-contratti`, `-offerte-commerciali`, `-commesse`)
  che si dichiarano «gemelle», ma la gemellanza non è scritta da nessuna parte.

Rimedio deciso da Tid il 2026-10-21: il fermo dei temi trasversali (PROJECT_CONTEXT), la regola
«un tema, un brief» (AGENTS.md) e questo modello, scritto **una volta**.

---

## 2. Il modello com'è oggi (bozza della guida)

> Descrive lo stato attuale. Dove i documenti fanno in modo diverso, la differenza è nel §3.

### 2.1 Stati e transizioni

* Ogni documento ha un vocabolario di stati (`config.stati_doc_*`) e una **matrice delle
  transizioni** in tabella (`config.transizioni_stati_*`): una riga = un passaggio ammesso.
* Un trigger `trgfn_*_guard_transizione` rifiuta ogni passaggio che non è nella matrice.
* La stessa matrice, con il suo `meta` (`action_key`, `label_key`, `requires_confirm`, `manuale`),
  alimenta i bottoni: la funzione di capability del documento la legge e dice quali azioni sono
  disponibili e perché le altre sono spente.

### 2.2 Chi scrive lo stato: il verbo

* Direzione decisa il 2026-09-24 (D-1/D-2 di
  [brief-db-permesso-nel-verbo-di-scrittura](../work-done/brief-db-permesso-nel-verbo-di-scrittura.md),
  guida `architettura-permessi-e-autorizzazioni.md` §7.4): **una scrittura = un verbo**. I domini
  nuovi nascono così; quelli esistenti ci passano «quando un cantiere tocca le loro scritture».
* Per `vendite` il passaggio era rimandato a «un brief suo», mai scritto: è questo.

### 2.3 Chi può: il permesso

* Le operazioni CRUD chiedono il livello sull'area; le operazioni di **processo** (emetti, cambia
  stato, annulla, genera…) chiedono un'**azione di processo** (`config.azioni_processo`).
* La regola ha **una sede sola**, nel DB (`script.fn_check_azione_processo`), e **due punti in cui
  si applica**, voluti (guida §7.4, «il backend chiede, non decide due volte»): l'endpoint
  (`post_permission`, risponde 403 subito) e il verbo (`script.fn_guard_azione`).

### 2.4 L'emissione

* L'emissione è il passaggio che dà il numero e, dove il documento si stampa, genera il PDF
  (rotta `/emetti/`, fabbrica `build_documenti_sorgente_views`).

### 2.5 L'annullo

* Ogni documento ha un verbo d'annullo; un documento con **legami** a valle si annulla solo se chi
  conferma dichiara quanti legami ha visto (guard comune `trgfn_doc_guard_annullo_con_legami`,
  [brief-db-annullo-documento-con-legami](../work-done/brief-db-annullo-documento-con-legami.md)).

---

## 3. Dove i documenti divergono oggi

### 3.1 Tabella per documento (censimento del 2026-10-21)

| Documento | Cambio stato | Matrice | Azione di processo | Emissione | Annullo |
| --- | --- | --- | --- | --- | --- |
| Preventivo | verbo `fn_cambia_stato_preventivo` (senza guard d'azione) | tabella | `cambia_stato_preventivi`, solo backend | solo da `/emetti/` | `fn_annulla_preventivo` → verbo generale |
| Contratto | UPDATE dal backend | **nel codice del trigger**; la tabella la legge solo la capability | nessuna | solo da `/emetti/` | `fn_annulla_contratto`, UPDATE dentro di sé |
| Offerta | UPDATE dal backend; gli stati di partenza ripetuti in Python | tabella (nome fuori serie `stati_doc_offerte_transizioni`) | nessuna | `/emetti/` | da ACCETTATA via guard (`fn_check_offerta_annullabile`), forma diversa dall'annullo con legami |
| Ordine | UPDATE dal backend | tabella | nessuna | `/emetti/`, ma `/conferma/` e `cambia-stato` accettano CONFERMATO (scelta del 2026-06-05) | `fn_annulla_ordine`, UPDATE dentro di sé |
| DDT | verbo `fn_cambia_stato_ddt` per ogni transizione (dal 2026-10-13) | tabella | `emetti_ddt` (emissione, annullo dell'emesso) e `registra_magazzino` (consegna di un trasferimento): **nel corpo del verbo**; emissione controllata anche dal backend | `/emetti/`, ma `cambia-stato` accetta EMESSO (copiato dall'ordine) | `fn_annulla_ddt` → verbo generale |
| Reso | verbi `fn_conferma_reso` / `fn_annulla_reso` | tabella | `conferma_reso`, backend + verbo | conferma | verbo |
| Commessa | verbo `fn_cambia_stato_commessa` (senza guard d'azione) | tabella | `cambia_stato_commessa`, solo backend | push | `fn_annulla_commessa` → verbo generale |
| Versione di listino | UPDATE dal backend | **nel codice del trigger** e ricopiata in Python (`_validate_versione_state_transition`); stato testo con CHECK, senza vocabolario | nessuna | — | — |
| Fattura | funzioni della pipeline; stato del lotto con UPDATE | tabella | azioni della pipeline, solo backend | pipeline | reset del lotto |

Fuori vendita, stessa domanda: pagamenti (stato di distinte e righe, abbinamenti, sistemazioni:
nessuna azione; i verbi di registrazione senza guard) e magazzino (conferma/annullo dei documenti
interni: nessuna azione; la registrazione col guard nel verbo).

### 3.2 Due proposte del 2026-10-21 ritirate, e perché

* **«Il backend toglie `post_permission`, niente controllo doppio»**: contraddiceva §7.4 della
  guida dei permessi, decisione viva. Ritirata.
* **«EMESSO solo da `/emetti/` anche per il DDT»**: non è una regola nuova, **revoca** l'opzione (i)
  di [brief-ordini-stampa](../work-done/brief-ordini-stampa.md) §6.2 (2026-06-05), che il DDT ha
  copiato il 2026-07-11. Torna come decisione M-2.

### 3.3 Altro emerso dal censimento

* Azioni a catalogo che nessuno usa: `genera_fattura`, `approva_fattura`, `emetti_fattura`;
  `approva_rimessa` già spenta.
* Pratica: il cambio stato generico (`cambia_stato_pratica`) accetta ogni passaggio della matrice,
  compreso APERTA ↔ SOSPESA: si potrebbe sospendere senza `sospendi_pratica` e senza la riga di
  sospensione. **Da verificare**: non è ancora provato.
* Il commento di `listini_service._validate_versione_state_transition` cita un brief che non esiste
  (`brief-db-listini-stato-chiusa-sync.md`).

---

## 4. Decisioni per Tid — una volta, per tutti i documenti

| # | Domanda | Oggi | Note |
| --- | --- | --- | --- |
| M-1 | Ogni cambio di stato passa da un verbo DB con il guard d'azione (completare D-1/D-2 su vendite)? | 4 modelli diversi (§3.1) | Già decisa la direzione il 2026-09-24: qui si decide **se e quando** completarla |
| M-2 | L'emissione si fa **solo** da `/emetti/` (con PDF) per tutti i documenti che si stampano? | sì per preventivo e contratto (2026-05-28); no per ordine (2026-06-05) e DDT (copiato) | Un sì **revoca** l'opzione (i) del 2026-06-05. Dal 2026-10-13 un DDT si emette senza PDF anche se muove merce (prima la porta del registro lo respingeva): da provare |
| M-3 | L'azione richiesta da un passaggio si dichiara **sulla riga della matrice**, letta dal verbo, dall'endpoint e dalla capability? | nel DDT è scritta nel corpo del verbo; altrove solo sulla view | **Nuova**, mai valutata. Supera due scelte prese prima del modello del verbo: «gate per `action_key` nel service» (2026-07-27) e «permesso fuori dalle capability» (2026-08-04). Risponde a D3 |
| M-4 | Quante azioni per documento: una «cambia stato X» (come preventivo e commessa) o separate (emetti / annulla come DDT e reso)? | miste | Da decidere una volta, vale per tutti |
| M-5 | Le matrici scritte nel codice (contratto, versione di listino) passano in tabella, e le copie Python si ritirano? | contratto e listino fuori dal modello | Per il contratto la tabella c'è già; per il listino serve il vocabolario |
| M-6 | [brief-db-documento-nasce-nello-stato-iniziale](brief-db-documento-nasce-nello-stato-iniziale.md) confluisce qui? | aperto, non iniziato, stesso tema (stato e verbo) | Regola «un tema, un brief» |

---

## 5. Come si procede dopo le decisioni

* Il §2, corretto con le decisioni, diventa la guida. Da lì una proposta che non è nella guida, o
  la contraddice, si dichiara come revoca.
* Si porta **un documento per giro, tutto intero** al modello (verbo, matrice, azioni, emissione,
  annullo), invece di un tema per giro su nove documenti. L'ordine dei documenti si decide col piano.
* Prima di ricopiare una regola nelle 11 capability o negli 11 guard, si valuta se quella parte può
  vivere in un building block comune che legge la matrice: è la causa strutturale del §1.
