# Brief DB — Cambio di natura del soggetto: conferma della perdita e pulizia dei dati non congrui

## ⏭️ Chi riparte — aggiornato al 2026-11-14

⚠️ **Il modello è cambiato il 2026-11-14 (§0, D-5 e D-6 di Tid):** il cambio di natura **non pulisce
niente**. Rifiuta ed elenca i motivi, e il giro lo fa l'operatore a mano. Il titolo del file («conferma
della perdita e pulizia») è quello d'origine e non si rinomina, per non rompere i rimandi.

**Riparte: il team DB**, quando Tid dà il via: prima il censimento dei documenti per D-6, poi il
progetto del §0.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | Tid | ✅ Decisioni prese (D-5, D-6, D-7). Dà il via allo sviluppo | §0 | — |
| 2 | DB | Progetto del nuovo §0: regola dei motivi, regola dei cambi ammessi a DB, guard al cambio, verbo manuale di eliminazione dei dati societari (D-7), codici d'errore, pgTAP. Prima: censimento delle tabelle «documento intestato al soggetto» per D-6 | §0 | 1 |
| 3 | Tid | Applica i changeSet e lancia i pgTAP | — | 2 |
| 4 | BE/FE | Le nature in modifica dalla regola DB, il pulsante o la natura spenti con i motivi, via il «flag nascosto a `N`» | §0 | 3 |
| 5 | DB | Archiviazione in `work-done/` | — | 4 |

Decisioni aperte di Tid: nessuna. Lavoro fatto da committare: nessuno (solo questo brief).

**Brief vicini verificati (2026-11-14):** nessuno sugli stessi oggetti.
[brief-db-fornitore-privato-indirizzi](brief-db-fornitore-privato-indirizzi.md) tocca gli indirizzi
obbligatori del **ruolo** `FO`, non il cambio di natura; i residui del brief dati fiscali (registro dei
residui aperti) sono complementari e non si sovrappongono.

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-11.
> **A chi:** team DB (`dev/db-tid`); richieste a BE/FE in §6.
> **Origine:** revisione del lato BE/FE di
> [brief-db-dati-fiscali-e-societari-del-soggetto](../work-done/brief-db-dati-fiscali-e-societari-del-soggetto.md)
> (§9), e la decisione di Tid del 2026-10-11: «andrebbe richiesta la conferma di perdita dati e
> poi si puliscono quelli non congrui».
> **Stato:** 🔵 da fare. ⚠️ Modello rivisto da Tid il 2026-11-14 (§0): le decisioni di pulizia del
> §3 (D-0, D-1, D-3, D-4) e i §4.2-4.3, §5, §6 sono **superati**. Nessuna domanda aperta.

## 0. Il modello rivisto (Tid, 2026-11-14) — ⭐ si parte da qui

Origine: la discussione sulla riverifica. Tid: «non dobbiamo abilitare nessuna cancellazione delle
informazioni con trigger collegati o funzioni, il giro deve essere fatto manualmente»; «poter correggere
la P.IVA non significa che l'amministratore possa cambiare la natura se ci sono informazioni collegate».
⚠️ **Revoca** D-0 e D-1 del 2026-10-11 e D-3 e D-4 di oggi (la pulizia confermata).

| # | Decisione |
| --- | --- |
| **D-5** | Il cambio di natura **non pulisce mai niente**: nessun trigger e nessuna funzione cancella, chiude o azzera dati per farlo passare. Il DB **rifiuta** il cambio ed **elenca tutti i motivi**; l'operatore li toglie **a mano**, con gli strumenti che già esistono, e poi il cambio passa. Vale **anche per il SUPER_ADMIN**: il suo diritto di correggere CF e P.IVA non si estende al cambio di natura. |
| **D-6** | Alcuni motivi **non si tolgono** e bloccano il cambio per tutti: i **documenti intestati al soggetto** (preventivi, ordini, DDT, contratti, fatture…), ma **solo** se il cambio tocca l'**identità fiscale**, cioè fa nascere o sparire la P.IVA (DI ↔ PR). Fra nature che tengono P.IVA e CF (SC ↔ SP, una trasformazione di società: l'ente resta lo stesso) i documenti non bloccano. |
| **D-7** | *(Q-5)* I dati societari si tolgono con un'azione **manuale** «Elimina i dati societari», nella loro sezione, **separata** dal cambio di natura: la usa l'operatore, con un gesto suo. Il cambio di natura non la chiama. La riga eliminata resta nello storico (`trg_dati_societari_z90_storico_upd_dlt`). |

**I motivi, rivisti sul §2:**

| Motivo | Chi lo toglie, e come |
| --- | --- |
| `cliente_pa` / `split_payment` a `S` non ammessi | L'operatore, nel form: il flag a `N`. ⛔ Sparisce il «flag nascosto a `N`» del FE (`SoggettoDrawer.vue`), che è una pulizia silenziosa |
| titolo IVA vigente non ammesso, del proprio emittente | L'operatore, chiudendolo nel drawer dei titoli |
| titolo IVA vigente non ammesso, di **un altro emittente** | Non l'operatore, che non lo vede: il motivo dice che esiste (senza dettagli) e che deve intervenire chi lo vede (SUPER_ADMIN o l'altro emittente). Lettura `SECURITY DEFINER`, come `fn_titolo_iva_non_ammesso_del_soggetto` |
| indirizzo di un tipo che la natura nuova non ammette (Q-3) | L'operatore, eliminandolo dagli indirizzi del soggetto |
| riga di dati societari, natura nuova `NONE` | L'operatore, con l'azione manuale «Elimina i dati societari» (D-7): un verbo DB **suo**, `SECURITY DEFINER` come `fn_scrivi_dati_societari`, così B-5 resta vero. ⚠️ Il verbo rifiuta quando la natura **attuale** ha `dati_societari_policy = REQUIRED` (una SC non resta senza la riga): il guard differito `trgfn_soggetti_guard_dati_societari_required` scatta solo sugli UPDATE di `soggetti`, non sulla cancellazione della riga |
| P.IVA scritta, natura nuova `NON_APPLICABILE` (DI → PR, Q-4) | Solo il SUPER_ADMIN, svuotandola a mano (`trgfn_soggetti_guard_id_fiscale_immutabile`). E se il soggetto ha documenti, il cambio è comunque bloccato (D-6) |
| documenti intestati al soggetto, cambio DI ↔ PR | Nessuno (D-6): definitivo |
| forma giuridica non ammessa, sesso o P.IVA mancanti, indirizzi obbligatori della natura nuova | Non sono dati da togliere ma da **dare** (SCEGLI / COMPLETA del §2, D-2): l'operatore li dà nello stesso salvataggio, i guard che esistono giudicano lo stato finale |

**Conseguenze per il progetto DB** (le scelte tecniche restano del team DB):

1. **Una regola sola dei motivi**, che alimenta sia la natura o il pulsante spenti con il motivo sia
   il rifiuto (lo schema di `script.fn_check_annullo_movimento_titolo_iva`). Elenca **tutti** i
   motivi, non il primo; per i titoli parte da `fn_titolo_iva_non_ammesso_del_soggetto`,
   generalizzata (§4.1).
2. **Il guard al cambio** su `anagrafiche.soggetti` legge quella regola: un `UPDATE` di
   `tipo_soggetto_dettaglio_id` con motivi aperti si rifiuta, da qualunque strada arrivi. Nessun
   verbo con `conferma_pulizia`, nessun verbo che cancelli (i vecchi §4.2-4.3 cadono).
3. **I cambi ammessi diventano una regola del DB.** Oggi le nature proposte in modifica le calcola
   il BE (`soggetti_repository.get_soggetto`: «stessa macro-tipologia»). Con D-6 la regola dipende
   dai dati collegati: la scrive il DB, e il BE la legge.
4. **Da censire prima di scrivere**: quali tabelle contano come «documento intestato al soggetto»
   per D-6. È un elenco chiuso che va scritto nel brief prima del changeSet.

## 1. Il caso

In modifica il drawer del soggetto offre le nature di dettaglio della **stessa macro-tipologia**
(`tipi_modificabili_ids`: PR ↔ DI, SC ↔ SP, …). Dal 2026-10-10 il cambio arriva al DB, e i guard
del brief dati fiscali giudicano la natura nuova contro i dati che il soggetto ha già. I guard
fanno il loro mestiere — **rifiutano** — ma per una parte dei casi l'operatore non ha una via
d'uscita:

* **Ditta individuale con dati societari → privato.** `PR` ha `dati_societari_policy = NONE`, la
  riga c'è. Al COMMIT `trgfn_soggetti_guard_forma_giuridica_natura` rifiuta
  (`E_TIPO_SOGGETTO_FORMA_GIURIDICA_NON_AMMESSA`, campo `forma_giuridica_id`), su una sezione che
  il form per un privato **non mostra**. E l'applicazione non può togliere la riga: dal
  `20261011-04` non ha `DELETE` su `anagrafiche.dati_societari` (B-5: scrive solo il verbo), e un
  verbo che cancelli non esiste. **Vicolo cieco.**
* **Titoli IVA vigenti non ammessi dalla natura nuova.** Rifiuto
  `E_TIPO_SOGGETTO_CON_TITOLI_IVA_NON_AMMESSI`: l'operatore deve andare a chiudere i titoli uno
  per uno in un altro drawer, e solo dopo cambiare la natura.
* **Flag PA / split payment a `S` non ammessi.** Oggi il FE li manda a `N` **senza dirlo** (§9.1
  del brief dati fiscali): una perdita silenziosa, proprio quella che la decisione di Tid esclude.

## 2. Cosa diventa non congruo (dal contratto, non dai dati)

> ⚠️ *2026-11-14:* l'esito **PULISCI** di questa tabella è superato da D-5 (§0): quei dati restano
> motivi di rifiuto, che l'operatore toglie a mano. SCEGLI e COMPLETA restano validi.

| Dato | Regola (sede) | Al cambio di natura |
| --- | --- | --- |
| `cliente_pa`, `split_payment` a `S` | `cliente_pa_ammesso` / `split_payment_ammesso` (`trgfn_soggetti_guard_regime_pa`) | **PULISCI**: a `N` |
| riga `dati_societari`, natura nuova `NONE` | `dati_societari_policy` | **PULISCI**: la riga si toglie (lo storico la conserva: `trg_dati_societari_z90_storico_upd_dlt`) |
| forma giuridica non ammessa, natura nuova `OPTIONAL`/`REQUIRED` | `fn_forma_giuridica_ammessa` | **SCEGLI**: forma nuova nello stesso salvataggio (§3, D-2) |
| titoli IVA vigenti non ammessi | `fn_titolo_iva_ammesso` (`trgfn_soggetti_guard_titoli_iva_ammessi`) | **PULISCI**: si chiudono (§3, D-1) |
| sesso mancante, natura nuova `REQUIRED` (DI → PR) | `sesso_policy` | **COMPLETA**: il form lo chiede |
| indirizzi obbligatori della natura nuova | `tipi_soggetto_dettaglio_tipi_indirizzo` | **COMPLETA**: l'operatore li aggiunge |
| indirizzi di un tipo che la natura nuova **non ammette** (es. `SEDELEG` di una DI → PR) | `tipi_soggetto_dettaglio_tipi_indirizzo` | ⚠️ **buco confermato il 2026-11-14**, esito da decidere (§7, Q-3) |
| partita IVA scritta, natura nuova con `formato_piva = NON_APPLICABILE` (DI → PR) | `config.tipi_soggetto_dettaglio.formato_piva` | ⚠️ **da decidere** (§7, Q-4) — riga aggiunta il 2026-11-14 |
| partita IVA mancante, natura nuova con `piva_obbligatoria` (PR → DI) | `trgfn_soggetti_guard_cf_piva_obbligatori` | **COMPLETA**: il form la chiede (un campo vuoto si può riempire anche col guard di immutabilità) |
| ruoli | `tipi_ruoli_nature_ammesse`, per **macro-tipologia** | invariato: il cambio resta nella stessa macro-tipologia |

Tre esiti diversi, e vanno tenuti distinti: **PULISCI** (il dato si perde, ci vuole la conferma),
**SCEGLI** / **COMPLETA** (manca qualcosa che solo l'operatore può dare: non c'è niente da pulire,
il guard rifiuta col campo finché non lo dà).

## 3. Decisioni di Tid (2026-10-11)

> ⚠️ *Superate il 2026-11-14 da D-5 e D-6 (§0):* D-0, D-1, D-3, D-4, e la seconda frase di D-2
> («la riga si toglie se la natura nuova ha `NONE`»). Resta valida la prima parte di D-2: la forma
> non ammessa non si pulisce, l'operatore ne sceglie una ammessa nello stesso salvataggio.

| # | Decisione |
| --- | --- |
| **D-0** | Il cambio di natura che **perde dati** chiede una **conferma esplicita**, che elenca cosa si perde. Confermato, i dati non congrui **si puliscono** nella stessa transazione del cambio. |
| **D-1** | I **titoli IVA** vigenti non ammessi **si chiudono** (non si cancellano): `valido_al` = il giorno prima del cambio. La storia resta. |
| **D-2** | **Forma giuridica** non ammessa ma natura nuova con i dati societari: **non si pulisce**, l'operatore sceglie una forma ammessa nello stesso salvataggio (la forma è NOT NULL, C-2, e REA e capitale ne dipendono). La riga si toglie **solo** se la natura nuova ha `dati_societari_policy = NONE`. |
| **D-3** | *(2026-11-14, Q-1)* Un titolo IVA non ammesso che **non è ancora cominciato** (`valido_dal` dal giorno del cambio in poi) **si cancella**: non ha mai valso, e chiuderlo alla sua data d'inizio registrerebbe un giorno di validità falso. Eccezione a D-1, che resta per i titoli già cominciati. |
| **D-4** | *(2026-11-14, Q-2)* Se fra i titoli da chiudere o cancellare ce n'è anche uno solo di un **altro emittente**, il cambio di natura **si rifiuta** a chi non è SUPER_ADMIN, e il messaggio dice che l'intervento lo deve fare un SUPER_ADMIN. Nessun dettaglio dei titoli altrui (solo che esistono). Per il SUPER_ADMIN valgono D-0, D-1 e D-3 su tutti i titoli. |

## 4. Proposta per il team DB

> ⚠️ *Superata il 2026-11-14 (§0):* cadono i punti 2 e 3 (il verbo con `conferma_pulizia` e
> `fn_elimina_dati_societari`). Il punto 1 resta, con i motivi del §0 al posto degli esiti `PULISCI`;
> il punto 4 è deciso dal §0.2 (il guard al cambio, da qualunque strada); il punto 5 resta.

Le scelte tecniche sono del team DB; quello che conta è che **anteprima e pulizia leggano una
regola sola** (lo stesso principio di `script.fn_check_annullo_movimento_titolo_iva`, che
alimenta sia il pulsante spento sia il rifiuto).

1. **La regola: `anagrafiche.fn_check_cambio_natura_soggetto(p_soggetto_id uuid,
   p_tipo_soggetto_dettaglio_id bigint)`**, `RETURNS TABLE(voce, esito, campo, dettaglio jsonb)`,
   con `esito` in `PULISCI` / `SCEGLI` / `COMPLETA`. Una riga per dato del §2. Legge i predicati
   che esistono già (`fn_forma_giuridica_ammessa`, `fn_titolo_iva_ammesso`, le colonne della
   natura), non ne riscrive.
   ⚠️ *Nota del 2026-11-14:* per i titoli IVA esiste già
   `anagrafiche.fn_titolo_iva_non_ammesso_del_soggetto(p_soggetto_id, p_tipo_soggetto_dettaglio_id)`,
   `SECURITY DEFINER` (la RLS per emittente nasconderebbe i titoli degli altri), letta da
   `trgfn_soggetti_guard_titoli_iva_ammessi`. Restituisce **solo il primo** tipo non ammesso;
   l'anteprima vuole l'elenco (o almeno il conteggio, Q-2). Perché guard e anteprima leggano una
   regola sola, la voce dei titoli parte da lì (generalizzata, con il guard che la segue), non da
   una seconda query su `fn_titolo_iva_ammesso`.
2. **Il verbo: `anagrafiche.fn_cambia_natura_soggetto(p_soggetto_id, p_tipo_soggetto_dettaglio_id,
   p_conferma_pulizia boolean)`**:
   * con voci `PULISCI` e `p_conferma_pulizia = false` → rifiuto con un **codice nuovo**
     (proposta `E_CAMBIO_NATURA_RICHIEDE_CONFERMA`, `CONFLITTO_STATO`, campo
     `tipo_soggetto_dettaglio_id`, l'elenco delle voci nel contesto). È il presidio di D-0 **a DB**:
     nessun chiamante cambia natura perdendo dati senza averlo detto;
   * confermato → applica le pulizie, **poi** aggiorna la natura;
   * le voci `SCEGLI` / `COMPLETA` le lascia ai guard che già esistono (forma al COMMIT, sesso,
     indirizzi): il verbo non le anticipa.
3. **Togliere la riga dei dati societari**: un verbo `fn_elimina_dati_societari(p_soggetto_id)`,
   chiamato da `fn_cambia_natura_soggetto`, così B-5 resta vero («una porta per operazione», e
   nessun `DELETE` all'app).
4. **L'UPDATE diretto di `tipo_soggetto_dettaglio_id`**: se il cambio deve passare solo dal verbo
   (come i dati societari con B-5) lo decide il team DB. Senza un presidio, un `UPDATE` diretto
   salta la conferma; i guard restano comunque.
5. **L'ordine con i dati societari** non cambia (§8.3 del brief dati fiscali): nella stessa
   transazione prima la natura (ora: il verbo), poi `fn_scrivi_dati_societari`, e il guard
   differito giudica lo stato finale.

## 5. Prove attese

> ⚠️ *Superate il 2026-11-14 (§0):* le prove «riga tolta con conferma» e «titolo chiuso al giorno
> prima» non esistono più. Le prove nuove: per ogni motivo del §0, il cambio rifiutato col motivo, e
> che passa dopo che il motivo è stato tolto a mano; DI → PR con un documento intestato, rifiutato
> anche al SUPER_ADMIN; SC → SP con documenti, che passa; il titolo di un altro emittente, che compare
> come motivo senza dettagli. Casi **costruiti** nel pgTAP; la nota sul flag qui sotto resta.

pgTAP che **costruiscono** i casi (non che li cercano nel seed): DI con dati societari → PR
(rifiuto senza conferma, riga tolta con conferma, storico scritto); DI con titolo `INTENTO`
vigente → PR (titolo chiuso al giorno prima); SC con `split_payment = 'S'` → natura senza split
(flag a `N`); SC (SRL) → SP senza forma nuova (rifiuto al COMMIT sul campo) e con la SNC (passa).

⚠️ *Nota del 2026-11-14, dal contratto (seed `80_data` di `config.tipi_soggetto_dettaglio` e i suoi
CHECK):* nel catalogo di oggi nessun cambio **dentro la stessa macro-tipologia** porta un flag da
ammesso a non ammesso: `cliente_pa_ammesso` è vero solo per `ENC`, unica natura della sua
macro-tipologia; `SC` e `SP` ammettono entrambe lo split; `chk_tipi_soggetto_dettaglio_regime_pa_natura`
li vieta alle persone fisiche. La voce resta (il catalogo è un CSV, il modello ammette il caso), ma il
pgTAP del flag deve **fabbricarsi** in transazione una natura di dettaglio `PG` senza split: «SC →
natura senza split» non si costruisce con le nature del seed.

## 6. Richieste a BE/FE (dopo il DB)

> ⚠️ *Superate il 2026-11-14 (§0):* niente `conferma_pulizia` e niente dialog di conferma. Al loro
> posto: le nature in modifica dalla regola DB dei cambi ammessi, i motivi mostrati all'operatore, e il
> «flag nascosto a `N`» che sparisce. Il dettaglio si riscrive quando il DB è fatto.

* **BE**: `GET soggetti/{id}/cambio-natura/anteprima/?tipo_soggetto_dettaglio_id=` → le voci di
  `fn_check_cambio_natura_soggetto`; nella PATCH, un cambio di natura passa dal verbo, con
  `conferma_pulizia` dal payload.
* **FE**: al salvataggio con la natura cambiata, l'anteprima; con voci `PULISCI` un dialog di
  conferma che **elenca** le perdite, e `conferma_pulizia: true` solo dopo l'ok. Le voci
  `SCEGLI`/`COMPLETA` accendono i campi. ⛔ Sparisce il «flag nascosto parte `N`» di
  `SoggettoDrawer.handleSave`: diventa una pulizia confermata.

## 7. Domande aperte

> ⚠️ *2026-11-14:* Q-1 e Q-2 sono **superate** da D-5 (nessun titolo si chiude o si cancella da
> solo); le loro risposte restano scritte qui sotto come storia. Q-3 è chiusa: l'indirizzo non ammesso
> è un motivo, e l'operatore lo elimina a mano. Q-4 è chiusa: la P.IVA la svuota solo il SUPER_ADMIN, e
> con documenti intestati il cambio DI → PR è bloccato comunque (D-6). Aperta Q-5.

* **Q-5** *(2026-11-14)* — Una DI con dati societari che diventa PR: per D-5 la riga va tolta a mano
  prima del cambio, ma oggi **non c'è modo**. L'app non ha `DELETE` su `anagrafiche.dati_societari`
  (B-5) e un verbo che cancelli non esiste: il vicolo cieco del §1 resta. Decide Tid se esiste un'azione
  manuale «elimina i dati societari», separata dal cambio, oppure se la riga presente è un motivo
  definitivo.
  ✅ *Decisa da Tid il 2026-11-14 (D-7, §0):* l'azione manuale, separata dal cambio.

* **Q-1** — Un titolo non ammesso con `valido_dal` **dopo** il giorno prima del cambio non si può
  chiudere a quella data (`valido_al < valido_dal`). Si cancella (non ha mai valso) o si chiude a
  `valido_dal`? Da decidere con Tid. Verificare anche i consumi di plafond già registrati dopo la
  data di chiusura.
  ✅ *Decisa da Tid il 2026-11-14 (D-3, §3):* si **cancella**. Resta da confermare il caso con
  consumi di plafond già registrati dopo la data di chiusura (proposta: rifiuto del cambio).
* **Q-2** — I titoli sono per **emittente**, e l'operatore vede solo i suoi (RLS); la natura è
  del **soggetto**. Proposta: si chiudono tutti (la natura non è dell'emittente), e il dialog
  dice «N titoli di altri emittenti» senza dettagli. Decide Tid.
  ✅ *Decisa da Tid il 2026-11-14 (D-4, §3):* **rifiuto**, l'intervento è del SUPER_ADMIN (la
  proposta «si chiudono tutti» è scartata). Ricadute per il progetto: l'anteprima deve saper dire
  «titoli di altri emittenti» senza vederli (lettura `SECURITY DEFINER`, come
  `fn_titolo_iva_non_ammesso_del_soggetto`), con un esito che non è né `PULISCI` né
  `SCEGLI`/`COMPLETA`; serve un codice d'errore suo; da verificare in sviluppo che il SUPER_ADMIN
  veda e possa chiudere i titoli di tutti gli emittenti (RLS di `soggetti_titoli_iva`).
* **Q-3** — Un indirizzo di tipo che la natura nuova non ammette (la sede legale di una DI che
  diventa PR): c'è un guard? Se no, è un buco del modello da chiudere, e l'esito (pulizia
  confermata o rifiuto) lo decide Tid.
  ✅ *Verificato il 2026-11-14:* il guard c'è **solo dal lato dell'indirizzo**
  (`trgfn_indirizzi_soggetti_guard_tipo_indirizzo`, all'INSERT/UPDATE della riga di indirizzo, con
  `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO`). Nessun trigger di `anagrafiche.soggetti` rilegge gli
  indirizzi esistenti quando cambia la natura: il buco è confermato. Resta da decidere l'esito
  (pulizia confermata, cioè una voce `PULISCI`, o rifiuto). Attenzione al «fallback permissivo» del
  guard: una natura **senza** righe di matrice ammette qualunque tipo.
* **Q-4** *(nuova, 2026-11-14)* — Una partita IVA scritta su una natura nuova con
  `formato_piva = NON_APPLICABILE` (DI → PR). Oggi nessun guard la rifiuta: `fn_validate_cf_piva_it`
  con `NON_APPLICABILE` salta la validazione e basta, quindi il privato si tiene la P.IVA della ditta.
  Se è un dato non congruo da pulire (D-0), la pulizia urta
  `trgfn_soggetti_guard_id_fiscale_immutabile` (dal `20261110-96`): una P.IVA scritta si svuota solo
  da SUPER_ADMIN, perché CF e P.IVA sono la chiave d'unicità del soggetto
  (`uq_soggetto_idstato_id_fiscale_univoco`). Le strade: (a) la P.IVA resta, e `NON_APPLICABILE` vuol
  dire solo «non si valida»; (b) voce `PULISCI` e il verbo la svuota anche contro il guard (eccezione
  dentro il verbo); (c) il cambio DI → PR con P.IVA scritta è rifiutato a chi non è SUPER_ADMIN, come
  il cambio della P.IVA stessa. Decide Tid.
  *Fatti aggiunti il 2026-11-14, dalla discussione con Tid («è giusto che una DI diventi PR?»):*
  la DI ha la P.IVA **obbligatoria** nel modello (`piva_obbligatoria = true`, `NUM_11`); la chiave
  d'unicità di una persona fisica è il **codice fiscale** (`id_fiscale_univoco_cf_piva` =
  `UPPER(TRIM(codice_fiscale))` in `fn_crea_soggetto_pf`), quindi la strada «si chiude la ditta e si
  crea un privato nuovo» non esiste: un secondo soggetto con lo stesso CF è rifiutato. E le nature
  ammesse in modifica (`tipi_modificabili_ids`) le calcola il **BE**
  (`soggetti_repository.get_soggetto`: stessa macro-tipologia), non una regola del DB.

## 8. Diario

| Data | Evento |
| --- | --- |
| 2026-10-11 | Brief aperto dalla revisione BE/FE del brief dati fiscali; decisioni di Tid D-0, D-1, D-2. |
| 2026-11-14 | Riverifica sullo stato di sviluppo (sessione DB). Reggono: tutti gli oggetti citati esistono con il contratto descritto; B-5 vale ancora (`anagrafiche.dati_societari` fra le tabelle in sola lettura per l'app, `90_end/20261011-04` e loop dei grant); le riscritture di `fn_scrivi_dati_societari` (`20261012-02`, `20261025-87`) non toccano D-2; nessuna delle funzioni proposte e nessun codice nuovo esiste; il «flag nascosto a `N`» è ancora in `SoggettoDrawer.vue`. Aggiunti: blocco «Chi riparte», la nota sul BB `fn_titolo_iva_non_ammesso_del_soggetto` (§4.1), la nota sul pgTAP dei flag (§5), l'esito di Q-3 (buco confermato), Q-4 e le due righe della partita IVA nel §2. Decise D-3 (Q-1) e D-4 (Q-2). |
| 2026-11-14 | Tid rivede il modello: D-5 (il cambio non pulisce niente, rifiuta coi motivi, giro manuale; vale anche per il SUPER_ADMIN) e D-6 (i documenti intestati bloccano solo i cambi DI ↔ PR). Revocate D-0, D-1, D-3, D-4; superati §4.2-4.3, §5, §6; Q-1 … Q-4 chiuse o superate. Nuovo §0; aperta Q-5. |
| 2026-11-14 | Q-5 decisa da Tid (D-7): l'eliminazione manuale dei dati societari, separata dal cambio. Nessuna decisione aperta; riparte il team DB, al via di Tid. |
