# Brief DB — Indirizzi documento: simmetria, codici unificati, snapshot fn, cascata al push

> **Tipo**: brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-11 · **Owner**: Tid
> **Design-of-record**: [brief-design-indirizzi-documenti-vendita.md](brief-design-indirizzi-documenti-vendita.md)
> (decisioni D-1…D-5 chiuse). Non in produzione: breaking change ammessi, niente compatibilità.

---

## Contesto

Le tabelle `vendite.{preventivi,ordini,fatture,ddt}_indirizzi` esistono e sono identiche
(snapshot JSONB + `origine_indirizzo_id`/`origine_soggetto_ruolo_id` FK soft SET NULL,
UNIQUE uno-per-tipo, trigger `trgfn_tipi_indirizzi_only_allowed('<AMBITO>')`).
Mancano: simmetria su offerte/contratti, seed della whitelist per ambito (si usa il
fallback hardcoded del trigger), una funzione unica che componga lo snapshot, e la
copia degli indirizzi nelle funzioni di push della catena documentale.

## Richieste

### 1. Simmetria: due tabelle nuove (D-3)

- `vendite.offerte_commerciali_indirizzi` e `vendite.contratti_indirizzi`, struttura
  **identica** alle 4 esistenti (stesse colonne, FK CASCADE al documento, UNIQUE
  uno-per-tipo, trigger whitelist con ambito `OFFERTE` / `CONTRATTI`).
- Estendere il check `chk_tipi_indirizzi_ambito` di `config.tipi_indirizzi_allowed`
  ai nuovi ambiti.

### 2. Unificazione codici: `CON` unico "dove va la merce" (D-2)

- Ritirare **SPED** dalle whitelist documento. Whitelist target (seed di
  `config.tipi_indirizzi_allowed`, così si smette di usare il fallback hardcoded):

| Ambito | Tipi ammessi (proposta seed) | Obbligatorio |
|---|---|---|
| PREVENTIVI | FATT, CON, FORNITURA, RES | — |
| OFFERTE | FATT, CON, FORNITURA, RES | — |
| ORDINI | CON, FATT | — |
| DDT | CON | CON alla stampa/emissione (valutare) |
| CONTRATTI | FATT, CON, FORNITURA | — |
| FATTURE | FATT, CON, FORNITURA, RES | FATT (valutare) |

- SPED resta eventualmente in `config.tipi_indirizzi` per usi anagrafici, ma fuori
  dagli ambiti documento; se non usato altrove, valutarne il ritiro completo.
- Nota DDT: mittente = emittente fiscale (già memorizzato in testata), vettore = dati
  trasporto in testata; in `ddt_indirizzi` serve solo la destinazione (CON). Il manuale
  `dbzero/vendite/manual/ddt_indirizzi.md` che parla di "mittente/destinatario/vettore"
  va allineato di conseguenza — confermate voi la lettura.
- Aggiornare i **fallback hardcoded** in `trgfn_tipi_indirizzi_only_allowed` per
  coerenza (o rimuoverli una volta seedata la config: preferito, no-hardcode).

### 3. `fn_snapshot_indirizzo(p_indirizzo_id)` → jsonb (D-5)

- Funzione unica che, dato `anagrafiche.indirizzi.id`, produce lo snapshot JSONB
  canonico (shape del manuale `ddt_indirizzi`: via/civico/CAP/comune/provincia/stato +
  display, gestendo sia modalità normalizzata sia libera; base: le colonne già risolte
  da `vw_indirizzi_resolved_ruolo` / `fn_get_indirizzo`).
- È la **single source** dello shape: la usano sia le funzioni di push (§4) sia il BE
  (endpoint upsert). Documentarne lo shape nel manuale.

### 4. Derivazione a cascata nelle funzioni madre di push (D-1)

- Nei push della catena (preventivo→ordine, ordine→DDT/evasione, offerta→ordine,
  offerta/ordine→contratto dove applicabile): dopo la creazione del documento
  destinazione, **copiare le righe `*_indirizzi` del documento sorgente** filtrate sui
  tipi ammessi nell'ambito di destinazione (join su `config.tipi_indirizzi_allowed`),
  snapshot 1:1, `origine_*` propagati.
- Idempotenza: `ON CONFLICT` sul vincolo uno-per-tipo → non sovrascrivere se già
  presente (il documento a valle può essere stato ritoccato).
- ⚠️ **Coordinamento firme**: se toccate `fn_push_preventivo_a_ordine` & co., c'è già
  in coda la richiesta di aggiungere `flusso_id` alla firma
  ([brief-design-guida-rollout-multidominio.md](brief-design-guida-rollout-multidominio.md) R1,
  coordinata con analisi-fix-transazioni): fate un solo giro di `DROP FUNCTION`.

### 5. Fix minori

- `trgfn_tipi_indirizzi_only_allowed`: il log d'errore è **hardcoded** su
  `'table','vendite.fatture_indirizzi'` e `'fattura_id', NEW.fattura_id` anche negli
  altri ambiti → rendere dinamico (TG_TABLE_NAME + PK generica).
- `tipo_indirizzo_id` è `bigint` nelle tabelle documento vs `integer` in
  `config.tipi_indirizzi.id`: allineare (integer, come il resto del modello config).
- Simmetria acquisti: valutare se applicare le stesse decisioni a
  `acquisti.ddt_indirizzi` (stesso trigger, stessi codici) — per noi sì, a vostro
  giudizio il timing.

### 6. Test pgTAP attesi

- Whitelist per i 6 ambiti (tipo ammesso passa, tipo non ammesso → `E_TIPO_INDIRIZZO`
  con payload d'errore che cita la tabella giusta).
- `fn_snapshot_indirizzo`: shape completo su indirizzo normalizzato e su indirizzo
  libero; errore su id inesistente.
- Push preventivo→ordine e ordine→DDT: indirizzi copiati e filtrati (FORNITURA/RES non
  passano su DDT), `origine_*` propagati, idempotenza su ri-esecuzione.
- Uno-per-tipo: secondo insert stesso tipo → conflitto gestito.

## Non richiesto ora

- Nessuna migrazione dati (tabelle documento vuote o quasi: DB di sviluppo).
- Niente indirizzi su commesse/pipeline fatturazione (cantiere separato).
