# Brief DB — L'azienda che emette è quella del cliente: una regola, sette copie

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-10. **A chi:** Tid; poi BE (§6).
> **Origine:** §10.3 e §5.5 di [brief-db-esecutivi-ba-coppia](brief-db-esecutivi-ba-coppia.md), il
> debito fuori perimetro: «i guard emittente ↔ BA sono sette copie quasi uguali; il giro che li
> toccherà li estrae in un BB parametrico (regola del 2)».
> **Stato:** 📝 **aperto, decisioni chiuse da Tid il 2026-10-10 (§4), nessun codice scritto.** Il
> prossimo passo è il giro DB: BB `script.trgfn_doc_guard_emittente_ba`, codice nuovo, sette
> funzioni ritirate (§3, §5).
> **Nel registro dei difetti DB:** voce **D22** di `migliorie-generali-da-test-valutazione.md`, che
> rimanda qui.

## 1. La regola

Un documento di vendita è emesso dall'**azienda del suo cliente**: l'emittente del documento è quello
che il billing account risolve (`anagrafiche.fn_get_emittente_fiscale_pk`). È una regola sola, e vale
per sette tabelle: preventivi, offerte, contratti, ordini, DDT, resi, commesse.

Oggi è scritta **sette volte**, una funzione trigger per tabella. La regola del 2 chiede una sede.

## 2. Che cosa dice oggi il DB (doc auto-generata, 2026-10-10)

| Tabella | Funzione | Fascia | Colonna dell'emittente | Risolutore | Codice | Classe | Esce se BA NULL |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `preventivi` | `trgfn_preventivi_guard_emittente_ba` | `_a10_` | `emittente_fiscale_id` | `fn_get_emittente_fiscale_pk` | `E_PREV_EMITTENTE_BA_INCOERENTE` | DATO_ERRATO | sì |
| `offerte_commerciali` | `trgfn_offerte_commerciali_guard_emittente_ba` | `_a10_` | idem | idem | `E_OFFERTA_…` | DATO_ERRATO | sì |
| `contratti` | `trgfn_contratti_guard_emittente_ba` | `_a10_` | idem | idem | `E_CONTRATTO_…` | DATO_ERRATO | **no** |
| `ordini` | `trgfn_ordini_guard_emittente_ba` | `_a10_` | idem | idem | `E_ORDINE_…` | DATO_ERRATO | sì |
| `ddt` | `trgfn_ddt_guard_emittente_ba` | `_z10_` | idem | idem | `E_DDT_…` | DATO_ERRATO | sì |
| `resi` | `trgfn_resi_guard_emittente_ba` | `_z10_` | idem | idem | `E_RESO_…` | DATO_ERRATO | sì |
| `commesse` | `trgfn_commesse_guard_emittente_ba` | `_a10_` | **`emittente_soggetto_ruolo_id`** | **`fn_get_emittente_fiscale_id`** | `E_COMMESSA_…` | **TECNICO** | no |

Tutti montati `BEFORE INSERT OR UPDATE OF billing_account_id, <colonna dell'emittente>`. Nessun altro
trigger `BEFORE` scrive quelle colonne su UPDATE, quindi `UPDATE OF` è la forma giusta
(linee-guida-trigger, «Scelta tra UPDATE e UPDATE OF»).

**Le sei copie dei documenti sono identiche nel testo**, tranne il nome della tabella e il codice. La
commessa è la stessa regola con un'altra colonna (il ruolo dell'emittente invece della PK) e un'altra
classe: lì nessuna persona sceglie l'emittente, lo deriva il push, e un valore diverso è un chiamante
rotto (TECNICO, scelta dichiarata nel suo COMMENT).

### 2.1 Difetti che le copie portano con sé

1. **La frase mostra nomi di colonna all'utente.** Le sei frasi a catalogo dicono «Ordine:
   emittente_fiscale_id non corrisponde all'emittente derivabile dal billing_account_id.» — nessun
   segnaposto, nessun dato leggibile. I guard passano comunque un VARIADIC tecnico
   (`'ba=…, ef=…, ef_atteso=…'`), che la frase non usa. La commessa invece ha una frase leggibile
   («Commessa %s: l'emittente indicato (%s) non è quello del billing account %s (%s)»).
2. **Il log perde la transazione**: tutte e sette passano `NULL::uuid` al posto di `NEW.tx_id`.
3. **Sei codici per lo stesso significato.** Il progetto ha già scelto «un codice per la regola»
   altrove (`E_DOC_CLIENTE_DIVERSO_DA_SORGENTE`, `E_DOC_EMITTENTE_FUORI_BOZZA`, entrambi del 2026-10-09).
4. **L'uscita sul BA NULL** è diversa da tabella a tabella senza una ragione scritta: i contratti e le
   commesse non ce l'hanno. Su preventivo, offerta e ordine il BA è NOT NULL, ma il NOT NULL si
   controlla dopo i trigger `BEFORE` (§6.3 di brief-db-istanza-nasce-col-ba): l'uscita serve a far
   parlare il vincolo invece del risolutore. Su DDT e reso il BA NULL è un caso del modello.

## 3. Forma proposta

Un **building block trigger**, montato sulle sette tabelle:

```sql
CREATE TRIGGER trg_ordini_a10_guard_emittente_ba_ins_upd
  BEFORE INSERT OR UPDATE OF billing_account_id, emittente_fiscale_id ON vendite.ordini
  FOR EACH ROW
  EXECUTE FUNCTION script.trgfn_doc_guard_emittente_ba(
    'Ordine',                      -- [0] come chiamare il documento nella frase
    'emittente_fiscale_id',        -- [1] la colonna dell'emittente
    'E_DOC_EMITTENTE_BA_INCOERENTE'); -- [2] il codice (vedi D-1)
```

* legge le colonne con `to_jsonb(NEW)`, come il BB di testata `trgfn_doc_testata_lock_fuori_bozza`;
* il risolutore lo sceglie la colonna: `emittente_fiscale_id` → `fn_get_emittente_fiscale_pk`,
  `emittente_soggetto_ruolo_id` → `fn_get_emittente_fiscale_id`;
* BA NULL → esce (su tutte e sette: §2.1 punto 4);
* passa `NEW.tx_id`;
* montaggio sbagliato (colonna inesistente, argomenti mancanti) → errore di configurazione, come i
  due BB fuori bozza;
* i trigger mantengono **nome e fascia** di oggi (`_a10_`, e `_z10_` su DDT e reso, dopo il
  normalize che eredita il BA): cambia solo la funzione.

Le sette funzioni si ritirano nello stesso giro.

## 4. Decisioni per Tid

| # | Domanda | Proposta | Decisione di Tid |
| --- | --- | --- | --- |
| **D-1** | Un codice per i sei documenti, o uno per documento? | **Uno**, `E_DOC_EMITTENTE_BA_INCOERENTE` (DATO_ERRATO, `campo` = la colonna), come `E_DOC_EMITTENTE_FUORI_BOZZA`. I sei vecchi si ritirano. La **commessa tiene il suo** `E_COMMESSA_EMITTENTE_BA_INCOERENTE`: la classe diversa (TECNICO) è un significato diverso per chi riceve l'errore, non uno stile | ✅ **Uno solo** (Tid, 2026-10-10); la commessa tiene il suo |
| **D-2** | La frase | Leggibile, coi valori: «%s: l'azienda che emette (%s) non è quella del cliente (%s, billing account %s).» — documento, emittente indicato, emittente atteso, codice del BA. Niente nomi di colonna | ✅ **Sì, con i dati** (Tid, 2026-10-10). ⚠️ Nella frase vanno i **nomi** delle due aziende (come le chiama l'utente), non gli id: da dove leggerli si sceglie scrivendo il BB, e gli id restano nel contesto del log |
| **D-3** | La commessa entra nel BB? | **Sì**: è la stessa regola, e colonna, risolutore e codice sono argomenti. Restarne fuori la lascerebbe come seconda sede della stessa regola | ✅ **Dentro** (Tid, 2026-10-10). ⚠️ Conseguenza: il BB passa gli stessi valori per tutti e due i codici, quindi la frase di `E_COMMESSA_EMITTENTE_BA_INCOERENTE` va riscritta con i segnaposto nello stesso ordine di quella nuova (documento, emittente indicato, emittente atteso, BA) |
| **D-4** | Dove sta il BB | `script` (la sede comune dei BB lato DB, come `fn_cliente_dal_billing_account`), non `vendite`: la regola è di anagrafica (il BA risolve l'emittente) e vale su più tabelle | ✅ **`script`** (Tid, 2026-10-10) |

## 5. Da censire nel giro (non qui)

* i pgTAP che citano i sei codici (uno, al 2026-10-10) e quelli che provano i sette guard;
* i COMMENT dei trigger, e le pagine `manual/` delle sette funzioni (da cancellare: oggetti ritirati);
* `anagrafiche.fn_check_ba_coppia_emittente_omogenea`, che la commessa nomina come «stessa scelta»:
  da guardare se è un'ottava copia della stessa regola;
* i presidi trasversali per una funzione plpgsql nuova (riferimenti morti, catalogo messaggi).

## 6. Ricaduta BE (dopo la consegna DB)

* `backend/apps/core/services/error_ui_overrides.py`: oggi ha una voce per ciascuno dei sei codici;
  con D-1 diventa una;
* policy generate e frase di ripiego del codice nuovo;
* nessun cambio di contratto per i form: l'errore resta sul campo dell'emittente.

## 7. Fuori da questo brief

* **Le altre colonne di testata in fase chiusa** (§8 di brief-db-esecutivi-ba-coppia): quali colonne
  di una testata si possono ancora cambiare dopo l'emissione. È una domanda di dominio, colonna per
  colonna: brief suo.
