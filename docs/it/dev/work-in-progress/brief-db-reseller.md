# Brief DB — Il reseller: il codice, il legame col billing account nel tempo, il reseller della fattura

## ⏭️ Chi riparte — aggiornato al 2026-11-27

**Riparte: Tid**, con le decisioni D-R-0 … D-R-5 (§4). Il brief è **aperto, non iniziato**: nessuno sviluppo, nessun
range di changeSet. Nasce dal T8c di [brief-db-revisione-anagrafiche](brief-db-revisione-anagrafiche.md) (§25.4), da
cui Tid ha tolto le voci del reseller il 2026-11-27.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | Tid | D-R-0: a che cosa serve oggi il reseller, e chi scrive il legame | §4 | — |
| 2 | Tid | D-R-1 … D-R-5 | §4 | 1 |
| 3 | sessione DB | Il giro: pgTAP rosso, changeSet, prova sullo scratch, doc e guida | §5 | 2, via di Tid e range |
| 4 | Tid | Apply e pgTAP, commit | — | 3 |
| 5 | team BE/FE | La richiesta al BE, se D-R-0 porta un verbo o un'interfaccia | §5 | 4 |
| 6 | sessione DB | Archiviazione in `work-done/` | — | 4, 5 |

**Decisioni aperte di Tid:** D-R-0 … D-R-5.
**Da committare:** questo brief, nato il 2026-11-27.

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-27. **A chi:** Tid e team DB.
> **Origine:** le segnalazioni S12 e S57d/S57e del censimento di `anagrafiche` (giro 0d, 2026-11-22), le voci S12a-S12d
> e S57e di T8c, e il COMMENT stantio della tabella `resellers` (M6 di §8.1 di quel brief).
> **Brief vicini verificati:**
> [brief-db-revisione-anagrafiche](brief-db-revisione-anagrafiche.md) §25.4: da lì vengono le voci; lì restano PSP,
> vettori, fornitori, gestore e il guard di ruolo doppio (compreso quello di `resellers`, §25.1).
> [sviluppo-multi-face-da-completare](sviluppo-multi-face-da-completare.md) riga 164: se `resellers_billing_account`
> debba avere un perimetro per emittente è una domanda di modello aperta, «decisione di Tid, fuori da questo
> cantiere»; non è nel perimetro di questo brief, ma un legame che diventa scrivibile da un'interfaccia (D-R-0) la
> rende concreta. Nessun altro brief aperto nomina il reseller.
> **Guide verificate** (`scripts/guide_coinvolte.py --oggetti`, 6 oggetti, 2026-11-27):
>
> | Guida | Esito |
> | --- | --- |
> | [soggetti-e-ruoli-anagrafici](../../guide/soggetti-e-ruoli-anagrafici.md) | **indietro**: il reseller è una riga della tabella dei ruoli; il legame col billing account, il periodo e il reseller della fattura non sono descritti. Si scrive nel giro |
> | [fatturazione](../../guide/fatturazione.md) | **indietro per assenza**: non dice che il reseller è un elemento della chiave con cui le attività si accorpano in fattura (§2); `vendite.fn_build_fattura_key` va nel suo «Vedi anche» |
> | `architettura-multi-face-auth`, `architettura-permessi-e-autorizzazioni`, `gestione-dei-pagamenti`, `integrazione-ai` | trovate per `vendite.fatture`; nessuna frase sul reseller: **coerenti** per assenza |
>
> **Orfani** dello script: `resellers_billing_account`, `trgfn_resellers_guard_attivo`, `trgfn_resellers_normalize`,
> `fn_build_fattura_key`. Il primo è un concetto di dominio (va nella guida dei ruoli); gli altri due trigger sono
> dettagli interni, che con D-R-1 e D-R-3 si ritirano.

## 1. La decisione di modello che esiste

[fatturazione-attivita-progetto](../work-done/2026/fatturazione-attivita-progetto.md) §3.2 (archiviato): il reseller è
un **ruolo commerciale, non un cliente**. Il destinatario della fattura resta sempre il billing account; il reseller è
facoltativo e serve «come filtro e metadato commerciale (report, provvigioni, selezioni batch)»; la **distribuzione**
(il reseller destinatario della fattura) è esclusa dallo standard, da trattare come processo dedicato. Il legame
`resellers_billing_account` nasce il 2026-01-26 (`2d786a90a`).

## 2. Che cosa dice il catalogo (scratch `zeroerp_ruoli`, 2026-11-26 e 2026-11-27)

* `anagrafiche.resellers`: una riga per ruolo `RE`; `codice` NOT NULL, unico, maiuscolo, bloccato dopo la nascita;
  nessuna riga in `config.sistema_codici`, nessun generatore. `trgfn_resellers_normalize` è `RETURN NEW`, e il suo
  COMMENT promette un generatore che non esiste. Il COMMENT della tabella dice «Ruolo RES»: il codice è `RE`.
* Lo spegnimento: `trgfn_resellers_guard_attivo` (scritto a mano perché la FK del legame punta a `soggetti_ruoli`)
  rifiuta lo spegnimento finché esiste **un** legame, anche chiuso: un reseller che ha avuto clienti non si spegne.
* `anagrafiche.resellers_billing_account`: `reseller_soggetto_ruolo_id` → `soggetti_ruoli(id)`, non la riga del
  reseller: nessun controllo del tipo di ruolo, e un legame nuovo verso un reseller spento nasce. `valido_dal`,
  `valido_al` e la colonna generata `validita` non entrano in nessun vincolo: due reseller sullo stesso billing
  account negli stessi giorni sono ammessi. RLS accesa. Nessuno storico.
* **I lettori.** `vendite.fn_build_fattura_key` prende il reseller del billing account con `ORDER BY rb.id LIMIT 1`,
  senza periodo: vale il legame più vecchio, anche chiuso. Il valore entra nella chiave: `fn_get_or_create_fattura_header`
  cerca la testata con `reseller_soggetto_ruolo_id IS NOT DISTINCT FROM` e lo scrive su `vendite.fatture`;
  `fn_applica_fondi_fattura` lo confronta allo stesso modo. Il reseller quindi **separa** le fatture dello stesso
  billing account, oltre a esserne il metadato.
* **Il filtro del lotto non c'è più.** La §3.2 lo prevedeva (`p_reseller_soggetto_ruolo_id`); la firma di oggi di
  `vendite.fn_create_fatturazione_lotto` non ha un parametro reseller.
* **Chi scrive.** Nessun verbo DB; dal backend nessuno scrive né il reseller né il legame (lettura dei chiamanti, T8
  §25.4, 2026-11-26).
* **Il precedente per la FK verso la specializzazione** c'è ed è montato: `emittenti_fiscali_billing_account` →
  `emittenti_fiscali(soggetto_ruolo_id)` ha il require differito e il block sul padre generati dall'automazione
  ATTIVO (guida `automazione-db` §4.2).

## 3. Le voci (da T8c, 2026-11-26)

| # | Il catalogo oggi | Natura | Proposta |
| --- | --- | --- | --- |
| S12a il codice | NOT NULL, nessun generatore | difetto | riga in `sistema_codici` + `trgfn_resellers_gen_codice`, come vettori e fornitori; `trgfn_resellers_normalize` si ritira (D-R-1) |
| S12b il periodo del legame | in nessun vincolo | difetto | `EXCLUDE USING gist (billing_account_id WITH =, validita WITH &&)` |
| S12c il reseller della fattura | il legame più vecchio, senza periodo | difetto | il legame valido alla data (D-R-2) |
| S12d / S57d il ruolo del legame e il reseller spento | FK su `soggetti_ruoli` | difetto | FK verso `resellers(soggetto_ruolo_id)`; `trgfn_resellers_guard_attivo` si ritira (D-R-3) |
| S57e lo spegnimento | conta anche i legami chiusi | difetto | D-R-4 |
| M6 il COMMENT «RES» | stantio | metadato | COMMENT al presente nel giro |

## 4. Le decisioni per Tid

* **D-R-0 — a che cosa serve oggi il reseller.** Il modello del 2026-01 lo voleva filtro del lotto e metadato; oggi
  il filtro non c'è e il reseller divide le fatture di uno stesso billing account. (a) Resta nella chiave della
  fattura, e il legame va scritto da qualcuno: un verbo DB e la sua interfaccia (richiesta al BE); (b) resta nella
  chiave, il legame si scrive solo da migrazione o a mano, e lo si dichiara; (c) esce dalla chiave e resta un
  metadato della fattura (cambio di modello sulla fattura: lo si scrive nella guida). Proposta: da decidere da Tid,
  è la domanda che dice se le altre valgono la spesa.
* **D-R-1 — il prefisso del codice.** Le righe di `anagrafiche` in `sistema_codici` non hanno una forma comune
  (`SGT-`, `VET-`, `IFO-`, `BAC/`, `FORN`, tutte a 7 cifre). Proposta: `RES-` + 7 cifre.
* **D-R-2 — a quale data il legame vale per la fattura.** Proposta: la competenza dell'attività fatturata. ⚠️ Con il
  reseller nella chiave, un lotto che prende attività di due periodi con due reseller produce due fatture dello
  stesso billing account: è la conseguenza da accettare o da evitare con D-R-0 (c).
* **D-R-3 — la FK verso `resellers(soggetto_ruolo_id)`.** Proposta: sì; tipo, esistenza e «attivo» dall'automazione.
  `vendite.fatture.reseller_soggetto_ruolo_id` punta anch'essa a `soggetti_ruoli`: va con lo stesso disegno di T12
  del brief di revisione, che lo decide per tutte le colonne di documento.
* **D-R-4 — un legame chiuso ferma lo spegnimento?** Proposta: no, contano i legami validi oggi o dopo. Con la FK di
  D-R-3 il block dell'automazione conta **tutti** i figli: o si accetta, o resta un guard a mano che guarda il periodo.
* **D-R-5 — il perimetro del legame per emittente** (la domanda aperta di `sviluppo-multi-face-da-completare`):
  entra qui solo se D-R-0 è (a).

## 5. Il piano (dopo le decisioni)

* [x] Le voci tolte da T8c e raccolte qui (Tid, 2026-11-27)
* [ ] D-R-0 … D-R-5 (Tid)
* [ ] pgTAP rosso, changeSet (range da Tid), prova sullo scratch con `scripts/prova_changeset.py`
* [ ] Pagine `manual/` di `resellers` e `resellers_billing_account`; guida dei ruoli e «Vedi anche» della fatturazione
* [ ] Apply e pgTAP (Tid), doc auto-generata rigenerata, commit
* [ ] La richiesta al BE, se D-R-0 è (a)
