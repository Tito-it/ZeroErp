## 📘 Documentazione Concettuale – Vista `documenti.vw_template_versioni_stampabili`

> 👀 **Vedi anche**
>
> [documenti.fn_risolvi_template_applicabile](/dbzero/documenti/funzioni/fn_risolvi_template_applicabile)
> [documenti.fn_template_esito_risoluzione](/dbzero/documenti/funzioni/fn_template_esito_risoluzione)
> [documenti.vw_template_personalizzati_scarto](/dbzero/documenti/views/vw_template_personalizzati_scarto)
> [Guida — Documenti e Stampe](/guide/documenti-e-stampe) (§3.1)

### 🎯 Scopo

(latest review 14-11-2026 — la validità decide, `20261114-02`; nata il 21-10-2026, brief
`brief-db-modelli-documento-standard`, §10.3 K-1)

Dice **quali modelli possono stampare oggi**, e con quale versione. È la sede unica di «può
stampare»: chi deve sapere se un modello stampa la legge, invece di ripetere le condizioni.

### Una riga per modello che può stampare

Un modello può stampare se:

* è attivo;
* ha una versione **fuori bozza** (`PUBBLICATA` o `OBSOLETA`), attiva e valida alla data
  operativa dell'azienda.

**Decide la validità, non lo stato.** Lo stato separa le versioni operative dalla `BOZZA`; il
giorno in cui una versione stampa lo dicono le sue date. Una versione `OBSOLETA` è superata da una
pubblicazione successiva, e stampa fino all'ultimo giorno della sua validità: se la nuova parte da
una data futura, fino a quel giorno stampa ancora la vecchia, e dal giorno di partenza la nuova.

Per ogni modello c'è al più una riga: le versioni attive fuori bozza di uno stesso modello non si
sovrappongono nel tempo (vincolo di esclusione `ex_template_documenti_versioni_no_overlap_pubblicata`
sulla tabella delle versioni, che copre anche le `OBSOLETA`).

### Chi la legge

| Lettore | Per che cosa |
|---|---|
| `fn_template_esito_risoluzione` | la regola dei due livelli |
| `fn_risolvi_template_applicabile` | la deduzione del tipo e il modello indicato |
| `fn_personalizza_template_standard` | attraverso la porta: la versione da cui parte una copia |
| `vw_template_personalizzati_scarto` | le due versioni confrontate |

### Note

* La data operativa si calcola una volta per la query.
* `security_invoker`: legge come chi la interroga. Le tabelle dei modelli non hanno RLS.

### Note di migrazione

Prima il predicato era scritto due volte dentro `fn_risolvi_template_applicabile` e una nel
backend (`get_versione_pubblicata_attiva`), che non guardava se il modello è attivo.

Fino al 14-11-2026 la vista chiedeva `stato = 'PUBBLICATA'`. La pubblicazione rende `OBSOLETA` la
versione in corso nel momento in cui pubblica la nuova, anche quando la nuova parte da una data
futura: fra la pubblicazione e la partenza non stampava nessuna delle due, e il modello cadeva su
`E_DOCUMENTI_TEMPLATE_NON_RISOLTO`. La decisione del 29-04-2026 (`work-done/sviluppo-documenti.md`,
punto 51) voleva invece la vecchia in uso fino alla partenza della nuova. Il caso è emerso in CI: il
fuso aziendale spostato al giorno prima della pubblicazione dello standard. Prova:
`db/pgtap/documenti/test-fn-pubblica-template-documento-versione-v1.sql`, test 12-17.
