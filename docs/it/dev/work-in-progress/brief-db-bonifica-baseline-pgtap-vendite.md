# Bonifica baseline pgTAP — perimetro `vendite`

> Cantiere aperto il 2026-08-18 · perimetro DB (`dev/db-tid`)
> Registro: [`db/pgtap/baseline-rossi.tsv`](../../../db/pgtap/baseline-rossi.tsv)
> Precedenti chiusi: `work-done/brief-db-pgtap-runner-rls-baseline.md`,
> `work-done/brief-db-bonifica-pgtap-sorgente-polimorfa.md`

## Stato

| | inizio 2026-08-18 | ora |
|---|---|---|
| rossi `vendite` | 12 su 189 | **5** |
| registro complessivo | 45 | **38** |
| `dbops`, `pagamenti`, `catalogo` | zero | zero |

## Il principio che ha retto tutto il lavoro

Un rosso di baseline ha tre esiti possibili, non due, e vanno tenuti distinti
perche' solo il primo e' «sistemare un test»:

1. **Riparare** — il soggetto del test e' vivo, e' morta la *scorciatoia* con
   cui la fixture ci arrivava. E' il caso della maggioranza.
2. **Rivoltare** — il test descrive un ramo che nessun percorso attraversa piu'.
   Non si ripara e non si cancella: si riscrive su cio' che accade davvero, e si
   segnala il ramo morto. (Memoria: *un ramo si verifica dal percorso che lo
   attraversa, non dal codice che lo dichiara*.)
3. **Ritirare** — l'oggetto collaudato non esiste piu'. Se al suo posto e'
   subentrato un altro presidio, l'asserzione **si sposta** invece di sparire:
   toglierla e basta lascerebbe scoperto cio' che oggi conta.

## Fatto

### Famiglia C — guard tipo doc su `commesse_attivita` (2 file, RIPARATI)

`test-fn-list-commessa-attivita-v1` (14/14) e
`test-fn-list-commesse-emittibili-fatturazione-immediata-v1` (6/6).

Le fixture creavano righe `APPROVATA + NON_EMESSA` senza
`p_tipo_doc_fiscale_id`. Da `trg_commesse_attivita_a10_guard_tipo_doc_emittibile`
quello stato non e' piu' ammesso: la riga sarebbe invisibile a
`fn_list_emittibili_lane`, cioe' fatturato perso in silenzio. Zero contenuto di
design: si passa il parametro.

### Famiglia B — guard commessa su `attivita_fatturabili` (4 file)

`test-attivita-prezzo-bloccato-v1` (5/5), `test-fatturazione-draft` (6/6),
`test-fatturazione-reset-lotto-draft` (12/12), `test-attivita-fatturabili` (36/36).

⭐ **Il flag `attivita_fatturabili_require_commessa` non c'entrava.**
`commessa_id` e `commessa_attivita_id` sono **NOT NULL** sulla tabella: spegnere
il flag non riaprirebbe il percorso, darebbe `23502` invece di `P0001`. Il guard
arriva prima solo perche' e' un BEFORE ROW. L'attivita' senza commessa non e'
una policy accendibile, e' una colonna.

**La ricetta** (verificata prima di applicarla, sonda in `BEGIN…ROLLBACK`): il
modello NON e' `test-attivita-guardrail-commessa-v1` — che passa da
`fn_get_or_create_commessa` + `fn_link_commessa_sorgente` +
`fn_upsert_commessa_attivita` a 40 parametri e trascina il guard della sorgente
polimorfa — ma **`test-vw-dash-competenza-v1`**: `INSERT` diretti in
`vendite.commesse` e `vendite.commesse_attivita`, `sorgente_tipo_id` a `NULL`.
Non serve il setup di scope emittente per scrivere in `vendite.commesse` come
applicazione.

**Gli strati incontrati**, in ordine, perche' il conteggio dei rossi cala piu'
lentamente del lavoro fatto:

1. la coppia commessa — che **disarma anche**
   `trgfn_attivita_fatturabili_guard_ba_coerenza`, commessa-aware, che fa
   `RETURN NEW` quando `commessa_attivita_id IS NOT NULL`;
2. `competenza_dal` / `competenza_al` sono diventate **NOT NULL** e nessuna
   fixture le passava;
3. `trgfn_attivita_fatturabili_normalize` e' commessa-aware (vedi 🔴 sotto);
4. la UNIQUE sulla sorgente non esiste piu' (vedi 🔴 sotto);
5. `vendite.attivita_fatturabili_lotti` e' stata dismessa (vedi 🔴 sotto).

**Trappola evitata su `test-attivita-fatturabili`**:
`uq_attivita_fatturabili_commessa_attivita` e' una UNIQUE piena, 1:1. Le 13
righe hanno **13 attivita' di commessa distinte**, comprese quelle degli INSERT
che devono fallire: condividerne una avrebbe fatto scattare *quella* unique al
posto del `23503`/`23514` atteso — un verde preso dall'indice sbagliato.

**Bonus**: in tre file i riferimenti sceglievano articolo, istanza utility e
billing account da `LIMIT 1` **indipendenti**, senza garanzia che l'istanza
appartenesse a quel BA. Ora il soggetto si sceglie una volta sola.

## 🔴 Tre segnalazioni fuori perimetro test

### 1. Il ramo standard di `trgfn_attivita_fatturabili_normalize` e' codice morto

La funzione e' commessa-aware: quando `commessa_attivita_id IS NOT NULL` fa
`RETURN NEW` in testa e salta **tutto** il blocco delle competenze — «lo
snapshot CA e' gia' completo», dice il suo commento. Essendo quella colonna
NOT NULL, **il ramo standard non e' raggiungibile da nessun percorso**:
normalizzazione di `competenza_mese` al primo del mese, derivazione da
`posticipa_al`, default di `competenza_dal`/`competenza_al`. Due asserzioni di
`test-attivita-fatturabili` lo collaudavano; ora verificano il comportamento
reale (la riga viene **respinta** dal CHECK / dal NOT NULL, perche' il
normalizzatore non copre piu' per chi scrive). Il codice morto resta: e' una
funzione condivisa, va potata in un passaggio suo.

### 2. `lotto_attivita_id` e' una colonna orfana, in due tabelle

`vendite.attivita_fatturabili_lotti` e' stata **dismessa il 2026-08-04** con la
potatura delle attivita' di pipeline morte. Sono rimaste
`attivita_fatturabili.lotto_attivita_id` e `attivita_consumi.lotto_attivita_id`:
**nessuna tabella padre, nessuna FK**. Oggi accettano qualunque numero. O
tornano ad avere un padre o vanno via.

### 3. La UNIQUE su `(sorgente_tipo_id, sorgente_uid)` non esiste piu'

Sulla tabella ci sono solo `pk`, `uq_..._uid` e
`uq_attivita_fatturabili_commessa_attivita`. La chiave si e' spostata sulla
coppia commessa/attivita' — stessa storia gia' registrata da
`test-drop-uq-commesse-attivita-src-uid-partial-v1`. L'asserzione e' stata
**spostata** sulla chiave viva, non tolta.

## Restano 5

| file | tipo | nota |
|---|---|---|
| `test-fn-resolve-prezzo-composito-v1` | ERRORE_FIXTURE | ⚠️ **decisione**: il suo CASO B1 (composito con riga di listino propria) e' vietato da `trgfn_listini_righe_guard_no_composito`, quindi il ramo B1 di `fn_resolve_prezzo_composito` e' irraggiungibile. O e' codice morto o il guard e' troppo largo |
| `test-fn-list-preventivi-da-pushare-v1` | ASSERZIONE | 3 asserzioni rosse; probabile causa unica condivisa col -v2 |
| `test-fn-list-preventivi-da-pushare-v2` | ASSERZIONE | 3 asserzioni rosse |
| `test-fn-preventivo-ha-residuo-commessa-v1` | ASSERZIONE | ⭐ si e' sbloccato da solo: era `ERRORE_FIXTURE`, ora gira tutte e 13 e ne fallisce 2 (`PREVENTIVO_NESSUNA_RIGA_COMMESSA`, `PREVENTIVO_SENZA_BILLING_ACCOUNT`) |
| `test-contratti-utilities-snapshot` | ASSERZIONE | serve un billing account la cui istanza/utility non abbia precontrattuali: non ce ne sono piu' (42/42 coperti, UNIQUE su istanza+utility). La fixture deve **crearsi** un'istanza vergine |

## Rientrati per migrazione, non per bonifica

`test-fatture-arrotondamenti-scope` — verde con `20260818-70` (guard sui
parametri di `fn_get_arrotondamento_scope`).
