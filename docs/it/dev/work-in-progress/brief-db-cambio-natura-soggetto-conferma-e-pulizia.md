# Brief DB — Cambio di natura del soggetto: conferma della perdita e pulizia dei dati non congrui

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-11.
> **A chi:** team DB (`dev/db-tid`); richieste a BE/FE in §6.
> **Origine:** revisione del lato BE/FE di
> [brief-db-dati-fiscali-e-societari-del-soggetto](../work-done/brief-db-dati-fiscali-e-societari-del-soggetto.md)
> (§9), e la decisione di Tid del 2026-10-11: «andrebbe richiesta la conferma di perdita dati e
> poi si puliscono quelli non congrui».
> **Stato:** 🔵 da fare. Decisioni di Tid prese (§3); tre domande aperte (§7).

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

| Dato | Regola (sede) | Al cambio di natura |
| --- | --- | --- |
| `cliente_pa`, `split_payment` a `S` | `cliente_pa_ammesso` / `split_payment_ammesso` (`trgfn_soggetti_guard_regime_pa`) | **PULISCI**: a `N` |
| riga `dati_societari`, natura nuova `NONE` | `dati_societari_policy` | **PULISCI**: la riga si toglie (lo storico la conserva: `trg_dati_societari_z90_storico_upd_dlt`) |
| forma giuridica non ammessa, natura nuova `OPTIONAL`/`REQUIRED` | `fn_forma_giuridica_ammessa` | **SCEGLI**: forma nuova nello stesso salvataggio (§3, D-2) |
| titoli IVA vigenti non ammessi | `fn_titolo_iva_ammesso` (`trgfn_soggetti_guard_titoli_iva_ammessi`) | **PULISCI**: si chiudono (§3, D-1) |
| sesso mancante, natura nuova `REQUIRED` (DI → PR) | `sesso_policy` | **COMPLETA**: il form lo chiede |
| indirizzi obbligatori della natura nuova | `tipi_soggetto_dettaglio_tipi_indirizzo` | **COMPLETA**: l'operatore li aggiunge |
| indirizzi di un tipo che la natura nuova **non ammette** (es. `SEDELEG` di una DI → PR) | `tipi_soggetto_dettaglio_tipi_indirizzo` | ⚠️ **da verificare** (§7, Q-3) |
| ruoli | `tipi_ruoli_nature_ammesse`, per **macro-tipologia** | invariato: il cambio resta nella stessa macro-tipologia |

Tre esiti diversi, e vanno tenuti distinti: **PULISCI** (il dato si perde, ci vuole la conferma),
**SCEGLI** / **COMPLETA** (manca qualcosa che solo l'operatore può dare: non c'è niente da pulire,
il guard rifiuta col campo finché non lo dà).

## 3. Decisioni di Tid (2026-10-11)

| # | Decisione |
| --- | --- |
| **D-0** | Il cambio di natura che **perde dati** chiede una **conferma esplicita**, che elenca cosa si perde. Confermato, i dati non congrui **si puliscono** nella stessa transazione del cambio. |
| **D-1** | I **titoli IVA** vigenti non ammessi **si chiudono** (non si cancellano): `valido_al` = il giorno prima del cambio. La storia resta. |
| **D-2** | **Forma giuridica** non ammessa ma natura nuova con i dati societari: **non si pulisce**, l'operatore sceglie una forma ammessa nello stesso salvataggio (la forma è NOT NULL, C-2, e REA e capitale ne dipendono). La riga si toglie **solo** se la natura nuova ha `dati_societari_policy = NONE`. |

## 4. Proposta per il team DB

Le scelte tecniche sono del team DB; quello che conta è che **anteprima e pulizia leggano una
regola sola** (lo stesso principio di `script.fn_check_annullo_movimento_titolo_iva`, che
alimenta sia il pulsante spento sia il rifiuto).

1. **La regola: `anagrafiche.fn_check_cambio_natura_soggetto(p_soggetto_id uuid,
   p_tipo_soggetto_dettaglio_id bigint)`**, `RETURNS TABLE(voce, esito, campo, dettaglio jsonb)`,
   con `esito` in `PULISCI` / `SCEGLI` / `COMPLETA`. Una riga per dato del §2. Legge i predicati
   che esistono già (`fn_forma_giuridica_ammessa`, `fn_titolo_iva_ammesso`, le colonne della
   natura), non ne riscrive.
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

pgTAP che **costruiscono** i casi (non che li cercano nel seed): DI con dati societari → PR
(rifiuto senza conferma, riga tolta con conferma, storico scritto); DI con titolo `INTENTO`
vigente → PR (titolo chiuso al giorno prima); SC con `split_payment = 'S'` → natura senza split
(flag a `N`); SC (SRL) → SP senza forma nuova (rifiuto al COMMIT sul campo) e con la SNC (passa).

## 6. Richieste a BE/FE (dopo il DB)

* **BE**: `GET soggetti/{id}/cambio-natura/anteprima/?tipo_soggetto_dettaglio_id=` → le voci di
  `fn_check_cambio_natura_soggetto`; nella PATCH, un cambio di natura passa dal verbo, con
  `conferma_pulizia` dal payload.
* **FE**: al salvataggio con la natura cambiata, l'anteprima; con voci `PULISCI` un dialog di
  conferma che **elenca** le perdite, e `conferma_pulizia: true` solo dopo l'ok. Le voci
  `SCEGLI`/`COMPLETA` accendono i campi. ⛔ Sparisce il «flag nascosto parte `N`» di
  `SoggettoDrawer.handleSave`: diventa una pulizia confermata.

## 7. Domande aperte

* **Q-1** — Un titolo non ammesso con `valido_dal` **dopo** il giorno prima del cambio non si può
  chiudere a quella data (`valido_al < valido_dal`). Si cancella (non ha mai valso) o si chiude a
  `valido_dal`? Da decidere con Tid. Verificare anche i consumi di plafond già registrati dopo la
  data di chiusura.
* **Q-2** — I titoli sono per **emittente**, e l'operatore vede solo i suoi (RLS); la natura è
  del **soggetto**. Proposta: si chiudono tutti (la natura non è dell'emittente), e il dialog
  dice «N titoli di altri emittenti» senza dettagli. Decide Tid.
* **Q-3** — Un indirizzo di tipo che la natura nuova non ammette (la sede legale di una DI che
  diventa PR): c'è un guard? Se no, è un buco del modello da chiudere, e l'esito (pulizia
  confermata o rifiuto) lo decide Tid.

## 8. Diario

| Data | Evento |
| --- | --- |
| 2026-10-11 | Brief aperto dalla revisione BE/FE del brief dati fiscali; decisioni di Tid D-0, D-1, D-2. |
