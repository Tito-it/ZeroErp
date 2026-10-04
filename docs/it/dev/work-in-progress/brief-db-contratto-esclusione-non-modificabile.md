# Brief DB — Un'esclusione del contratto non si modifica

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-04. **A chi:** team DB
> (`dev/db-tid`); poi BE/FE (§5), che **attende** la consegna DB.
> **Origine:** verifica critica del codice non committato del
> `brief-db-liste-righe-documento` (§9.15-9.16), 2026-10-04.
> **Decisione:** di Tid, 2026-10-04: «una esclusione non si modifica».
> **Stato:** ⏳ da scrivere (team DB).

## 1. La regola

Una riga `ESCLUSIONE` di `vendite.contratti_righe` dice una cosa sola: «questo articolo del listino
non è disponibile per questo contratto». Non ha prezzo (CHECK
`chk_contrighe_prezzo_per_tipo_eccezione`), e quantità, UdM, erogazione e fonte non hanno senso su un
articolo che il contratto non vende. **Si crea (Escludi) e si cancella (Ripristina articolo), e
basta.** Cambiare idea è cancellarla e, se serve, creare un'altra eccezione.

## 2. Il difetto di oggi

La regola non è scritta da nessuna parte, e il modello dice il contrario:

* `vendite.fn_contratto_righe_preview` dà alla riga `ESCLUSIONE` i verbi
  `ARRAY['MODIFICA', 'RIPRISTINA_ARTICOLO']` (D-8.4 del brief liste-righe);
* nessun guard rifiuta un `UPDATE` su una riga `ESCLUSIONE`: il solo vincolo è il CHECK sul prezzo;
* il drawer, che **rende** i verbi del DB, apre quindi il form di modifica sull'esclusione. Il form
  ripiega su `tipo_erogazione = CANONE` e sulla fonte di default (`FISSA`, quantità 1) perché la
  riga, creata con `tipo_erogazione` NULL, non li ha: il primo «Salva» scrive sull'esclusione valori
  che nessuno ha scelto. È la stessa classe di difetto del §9.11 del brief liste-righe (il form che
  riscrive in silenzio).

⛔ Il frontend **non** deve togliere da sé il click sulle esclusioni: i verbi della riga li decide il
DB (capability di riga, linee-guida-sql §12.5), e una seconda sede della regola è la divergenza che
D-8.4 ha ritirato.

## 3. Richiesta

| # | Cosa |
| --- | --- |
| R1 | `vendite.fn_contratto_righe_preview`: sulla riga `ESCLUSIONE` i verbi diventano `ARRAY['RIPRISTINA_ARTICOLO']`. Aggiornare il `COMMENT` (oggi elenca `ESCLUSIONE -> MODIFICA, RIPRISTINA_ARTICOLO`). |
| R2 | Un guard `BEFORE UPDATE` su `vendite.contratti_righe` che rifiuta l'`UPDATE` di una riga con `OLD.tipo_eccezione = 'ESCLUSIONE'`, con codice ed errore propri (forma §12.5: un `script.fn_check_*` che rende i motivi, letto anche dal guard, come `fn_check_esclusione_articolo_contratto`). ⚠️ Da decidere sul modello quali colonne restano ammesse: le tecniche (`data_update`, `user_update`, `tx_id`) le scrivono i trigger della stessa riga; resta da vedere `attivo` (la cancellazione è un `DELETE` fisico nel repository, ma i trigger `prevent_deactivate_if_children` dicono che una disattivazione esiste nel modello). |
| R3 | ⭐ **Simmetria, da valutare insieme**: `tipo_eccezione` è immutabile per il modello (il service lo dice nei messaggi: «per cambiare tipo, eliminare la riga e crearne una nuova»), ma a DB nessun guard lo impedisce. Senza, un `UPDATE` che porta `OVERRIDE → ESCLUSIONE` crea un'esclusione per un'altra via. Se il team DB conferma, lo stesso guard rifiuta `NEW.tipo_eccezione IS DISTINCT FROM OLD.tipo_eccezione`. |
| R4 | Elencare **tutti** gli scrittori di `contratti_righe` (funzioni, trigger, job) e verificare che nessuno aggiorni per percorso legittimo una riga `ESCLUSIONE` (per esempio una propagazione al cambio di versione del listino): un guard nuovo non deve rompere in silenzio un flusso esistente. |
| R5 | pgTAP **costruiti**: un'esclusione fabbricata nel test, l'`UPDATE` rifiutato col codice atteso, i verbi della riga senza `MODIFICA`; per R3 il cambio di tipo rifiutato. Non su righe esistenti. |

Codice di errore nuovo: va registrato con la sua policy **e** il ripiego senza `%s` (regola del
progetto, Messaggi-di-Errore-e-Generazione-Log).

## 4. Fuori perimetro

* Le righe `OVERRIDE` e `AGGIUNTA` restano modificabili come oggi.
* «Escludi» (creazione) e «Ripristina articolo» (`DELETE`) non cambiano.

## 5. Lato BE/FE, a consegna DB fatta

* **BE** (`contratti_service.update_riga`): il ramo che pre-valida il prezzo di una `ESCLUSIONE` diventa
  irraggiungibile e va tolto; il codice nuovo del guard va tradotto (policy). Test: un PATCH su
  un'esclusione risponde l'errore del guard.
* **FE** (`ContrattoRigheDrawer`): nessun cambio di comportamento (il click segue i verbi). Diventano
  morti i rami del form di **modifica** che trattano l'`ESCLUSIONE` (Tag «prezzo n/a», prezzo
  disabilitato, ripieghi `tipo_erogazione`/fonte per le righe senza): da togliere nello stesso giro.
* **Doc:** `api_contratti.md` (PATCH riga), `analisi-contratti-v1.md` se ne parla.
