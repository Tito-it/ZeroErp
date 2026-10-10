# Brief DB — Un testo non si riempie di spazi: `character(n)` dove la lunghezza varia

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-10, su segnalazione della sessione BE.
> **A chi:** team DB; team BE/FE per il §6 (nessuna modifica obbligatoria, solo verifiche).
> **Origine:** nella ricerca del comune il drawer mostra `Potenza (PZ        )`. La sessione BE ha
> trovato la causa nel tipo di `config.province.sigla` e proposto un brief
> `brief-db-province-sigla-varchar`. Nell'analisi DB il perimetro risulta più largo della sola
> sigla (§2), quindi il brief ha un nome più generale.
> **Stato:** 📝 **bozza, non iniziato**. Prima di scrivere i changeSet servono le decisioni di Tid
> del §3.
> **Da leggere per primo:** §1 e §3.

## 1. Il difetto, sul modello

In PostgreSQL `character(n)` è un testo **a lunghezza fissa**: un valore più corto viene riempito
di spazi fino a `n`. `PZ` in un `character(10)` viene salvato e letto come `'PZ        '`.

Questo tipo va bene solo quando **ogni** valore ammesso ha esattamente `n` caratteri: in quel caso
non c'è niente da riempire. Se il valore può essere più corto, ogni lettore riceve gli spazi e deve
toglierli. Chi se ne dimentica li mostra all'utente o li scrive in un documento.

La sigla di provincia è dichiarata `character(10)` e nella realtà ha due caratteri. La descrizione
della provincia è `character(80)`, e «Potenza» ne ha sette. Nessuna delle due colonne ha un dominio
a lunghezza fissa.

⛔ **I tamponi a valle non chiudono il difetto.** Il problema è già stato aggirato in tre punti
(§2.3) e nessuno ha corretto il tipo. Ogni lettore nuovo della colonna si ritrova con gli spazi:
il drawer di oggi è il quarto caso. Anche un `.strip()` nel backend sarebbe solo il quinto tampone.

⚠️ **Il tipo dà anche un secondo problema, nelle firme delle funzioni.** `character` senza
lunghezza vale `character(1)`. Inoltre `RETURN QUERY` pretende che il tipo sia identico e rifiuta
`varchar` dove la firma dichiara `bpchar`. Questo ha già rotto per quattro mesi l'autocomplete vie
(`script.fn_search_stradario`, aprile–agosto 2026): il changeSet `20260402-01` aveva convertito il
`codice` di sette tabelle `config` ma non la firma che lo esponeva.
Nota: quel cantiere convertì **solo** le colonne `codice`. `sigla` e `descrizione` della stessa
famiglia rimasero `character(n)`, ed è da lì che arriva la segnalazione di oggi.

## 2. Che cosa dice oggi il DB (contratto, letto il 2026-10-10 su dbdev)

### 2.1 Le colonne `character(n)` il cui dominio non ha lunghezza fissa

| Colonna | Tipo | Dominio reale | Effetto |
| --- | --- | --- | --- |
| `config.province.sigla` | `character(10)` | sigla della provincia (in Italia 2 lettere) | **la segnalazione** |
| `config.province.descrizione` | `character(80)` | nome della provincia | stesso difetto, fino a 73 spazi |
| `anagrafiche.dati_societari.destinatario_fe` | `character(10)` | codice destinatario SDI: 7 caratteri (6 per la PA) | arriva con gli spazi al BE (`soggetti_repository.py:1083`) e in `fn_get_soggetto_dati_by_ruolo`; per la fattura lo toglie un `btrim` (§2.3) |
| `anagrafiche.gestori.descrizione` | `character(50)` | testo libero | idem |
| `anagrafiche.gestori.cd_prod_software` | `character(20)` | codice libero | idem |
| `config.ambiti.descrizione` | `character(100)` | testo libero | idem |
| `config.stati_cliente.descrizione_breve` | `character(20)` | testo libero | idem |
| `anagrafiche.catasto_unita_immobiliari.foglio_catastale`, `particella`, `sezione_catastale`, `subalterno` | `character(5)` | numeri e sigle catastali di lunghezza variabile | idem |
| `magazzino.note*.lingua` (dieci tabelle, la madre partizionata `magazzino.note` compresa) | `character(5)` | codice lingua (`it`, `it-IT`) | esce con gli spazi da `fn_get_note` e dalle tre `fn_get_*_note` |

### 2.2 Le colonne `character(n)` a lunghezza **esatta**

Qui il padding non può nascere: ogni valore ha già `n` caratteri. Restano però esposte al problema
delle firme del §1.

| Colonna | Tipo |
| --- | --- |
| `config.stati.codice_iso2`, `anagrafiche.conti_bancari.paese` | `character(2)` (ISO 3166 alpha-2) |
| `config.stati.codice_iso3`, `config.valute.iso_code` | `character(3)` |
| `anagrafiche.catasto_unita_immobiliari.destinazione_immobile` | `character(2)` |
| flag a un carattere: `soggetti.sesso`, `cliente_pa`, `split_payment`, `clienti.garanzia_tipo`, `istanze_utilities.proprietario_inquilino`, `conti_contabili.tipo_conto`, `stati_cliente.*` (3), `tipi_utenze.tipo_pdr_std`, `catasto.tipo_accatastamento`, `esigibilita` (3 tabelle vendite), `status` di `fatture_log` e `fatturazione_lotti_log` | `character(1)` |
| `storico.*.change_type`, `storico.*.tipo_evento`, `storico.pdp.tipo_operazione` (le tabelle dello storico) | `character(1)` |

### 2.3 I tamponi già presenti (tutti a valle del tipo)

| Dove | Che cosa toglie |
| --- | --- |
| `config.vw_province_lista`, `config.vw_comuni_lista`, `config.vw_codici_postali_lista` | `TRIM` su sigla e descrizione della provincia |
| `script.fn_snapshot_indirizzo`, `script.fn_snapshot_indirizzo_soggetto` | `btrim` su `provincia_sigla` e `stato_iso2` (la Provincia della FatturaPA deve avere due caratteri) |
| `vendite.fn_snapshot_intestazione_fattura` | `btrim` su `pr.sigla` e su `destinatario_fe` |
| `script.fn_get_stradario`, `script.fn_search_stradario` | `p.sigla::text` (la conversione a `text` toglie gli spazi in coda) |
| pgTAP `test-snapshot-intestazione-fattura-v1` (test 7) | presidio: nessun valore dello snapshot ha spazi di riempimento. **Resta valido** anche dopo la correzione |

### 2.4 Chi legge la colonna così com'è (i punti che oggi mostrano gli spazi)

- **Viste**: `script.vw_indirizzo_completo` (`p.sigla AS provincia`), `anagrafiche.vw_dati_societari`,
  `script.vw_ita_province_regioni` e la catena `vw_indirizzi_resolved_*`.
- **Funzioni** con `character` nel `RETURNS TABLE`: `script.fn_get_indirizzo`,
  `script.fn_get_indirizzi_by_ruolo` (`provincia_sigla`, `provincia_descrizione`, `stato_iso2`),
  `script.fn_get_soggetto_dati_by_ruolo` (`provincia_iscri_rea_sigla`, `destinatario_fe`, `sesso`),
  `fn_get_note` e le sue tre sorelle di dominio (`lingua`).
- **Backend** (query SQL scritte nel repository): `core/db/lookup_repository.py:419`
  (autocomplete comuni, la segnalazione), `anagrafiche/db/soggetti_repository.py:293` (comune di
  nascita) e `:1083` (`destinatario_fe`), `anagrafiche/db/geo_repository.py:347` (`list_province`,
  tendina).

### 2.5 Che cosa trascina una `ALTER COLUMN … TYPE` su `config.province`

Verificato da catalogo il 2026-10-10:

- **viste** che leggono `sigla` o `descrizione`, comprese quelle che le leggono indirettamente (14):
  `anagrafiche.vw_dati_societari`, `config.vw_codici_postali_lista`, `config.vw_comuni_lista`,
  `config.vw_province_lista`, `script.vw_indirizzo_completo`, `script.vw_ita_province_regioni` →
  `anagrafiche.vw_indirizzi_dettaglio` → `vw_indirizzi_resolved_base`,
  `vw_istanze_utilities_dettaglio`, `vw_pdp` → `vw_indirizzi_resolved_all`, `_ruolo`, `_soggetto`,
  `vw_istanze_dati_precontrattuali_dettaglio`;
- **funzioni sul tipo riga di quelle viste** (`RETURNS SETOF <vista>`):
  `script.fn_get_indirizzi_by_soggetto(uuid)`,
  `script.fn_get_indirizzo_by_soggetto(uuid, varchar)`,
  `anagrafiche.fn_search_indirizzi_dettaglio(…)`;
- **trigger `UPDATE OF`**: nessuno su `config.province` (`tgattr` vuoto);
- **FK**: `comuni.provincia_id` e `dati_societari.id_prov_iscri_rea` puntano a `province.id`, non
  alla sigla: non sono coinvolte;
- **indice unico** `uq_province_sigla`: PostgreSQL lo ricostruisce da solo durante l'`ALTER`.

È la **stessa catena** che `20260402-01` ha già abbattuto e ricostruito (ordine dei `DROP` e
changeSet di ricostruzione `20260402-03…-10`): si riparte da quel modello, ma i corpi si prendono
dalla doc auto-gen di oggi e non da quegli YAML.

### 2.6 Un controesempio (fatto datato, 2026-10-10, dbdev)

`config.province` contiene una riga con sigla `TEST` (4 caratteri), creata dall'endpoint di
creazione provincia (`geo_repository.create_provincia`, che accetta qualunque sigla). Un `CHECK`
`^[A-Z]{2}$` la rifiuterebbe. Il punto vale sul modello e non sulla riga: **oggi nessuna regola
dice come è fatta una sigla**.

⚠️ Sul modello una provincia può essere estera: `regioni.stato_id` lega la regione a uno stato
qualunque, e `province.regione_id` è nullable. Per questo la regola delle **due lettere** non
dipende dalla sola riga della provincia (vedi D-2).

## 3. Decisioni attese da Tid

| # | Domanda | Proposta della sessione DB |
| --- | --- | --- |
| **D-1** | **Perimetro.** Solo `province` (sigla e descrizione)? Tutto il §2.1? Anche il §2.2? | **Tutto il §2.1 in questo brief**: è lo stesso difetto, e correggerlo a metà ripete `20260402-01`, che sistemò `codice` e lasciò `sigla`. Il **§2.2 resta fuori**: lì il padding non può nascere. Per quelle colonne valgono la regola nuova (D-4) e il registro del presidio (D-5). |
| **D-2** | **Forma della sigla.** Quale `CHECK`? | `varchar(10)` con `CHECK (sigla ~ '^[A-Z0-9]{1,10}$')`: niente spazi, maiuscole, nessun valore vuoto. Le **due lettere** sono una regola della provincia **italiana**, e lo stato si legge da un'altra tabella, quindi non può essere un `CHECK`. La sede proposta è il guard di scrittura di `config.province`, che legge lo stato dalla regione e per l'Italia pretende `^[A-Z]{2}$`. In alternativa si lascia la regola dov'è oggi, nello snapshot della FatturaPA. Decide Tid. |
| **D-3** | **I tamponi del §2.3**: si tolgono? | **Sì, nello stesso giro**, nelle viste e nelle funzioni che i changeSet riscrivono comunque. Un `TRIM` rimasto non fa danni, ma lascia credere al prossimo lettore che il tipo produca ancora spazi. I `btrim` degli snapshot fiscali restano solo se D-2 lascia lì la regola delle due lettere. Il presidio pgTAP test 7 resta comunque. |
| **D-4** | **Regola nuova** in `linee-guida-sql.md`? | Sì: «**`character(n)` non si usa.** Un testo a lunghezza variabile è `varchar(n)` o `text`. Un codice a lunghezza fissa è `varchar(n)` con un `CHECK` sulla forma. Nelle firme delle funzioni non compare mai `character`». La regola si scrive sul modello, non su questi casi. |
| **D-5** | **Presidio** strutturale? | Un pgTAP che rifiuta ogni colonna `bpchar` nuova, con un **registro dichiarato** delle colonne del §2.2 tollerate, e ogni funzione con `character` in firma o nel `RETURNS`. Così il prossimo `character(n)` diventa rosso in CI, invece di arrivare come segnalazione dal drawer. |

## 4. Piano dei changeSet (dopo le decisioni)

Sullo stesso modello di `20260402-01`:

1. **`00_schema`**, un changeSet per tabella (o uno per la catena di `province`):
   - `DROP FUNCTION` delle tre funzioni sul tipo riga delle viste (§2.5), poi `DROP VIEW` dalle
     viste che non hanno dipendenti verso quelle a monte;
   - `ALTER COLUMN … TYPE varchar(n) USING btrim(col)`. È DDL: nessun trigger di riga scatta, e non
     serve nessun `UPDATE` di bonifica. La conversione da `character` a `varchar` toglie già gli
     spazi in coda; `btrim` toglie anche quelli in testa;
   - `ADD CONSTRAINT … CHECK` sulla forma (D-2), e `CHECK (col = btrim(col) AND col <> '')` dove la
     colonna è testo libero.
   ⚠️ Prima dell'`ALTER`, contare le righe che violerebbero il `CHECK`. È un uso legittimo della
   misura: cerca un controesempio (§2.6) e non decide nulla.
2. **`20_code`**, con numero successivo, nella stessa corsa:
   - si ricreano le 14 viste e le 3 funzioni dal **corpo vivo** (doc auto-gen), senza i `TRIM` (D-3);
   - `DROP` + `CREATE` delle funzioni con `character` nel `RETURNS TABLE` (§2.4): cambiare il tipo
     di una colonna del risultato richiede il `DROP`. Firma, `RETURNS TABLE`, `DECLARE` e
     `COMMENT`/`GRANT` vanno **ancorati con `%TYPE`** alla colonna convertita: un `%TYPE` si risolve
     al `CREATE`, quindi va scritto dopo l'`ALTER`. Il controllo si fa riga per riga sul file nuovo;
   - `GRANT` delle funzioni ricreate, come nell'originale.
3. **Censimento dei chiamanti**, prima di consegnare (tre popolazioni):
   - dentro il DB: chi chiama le funzioni ricreate (`pg_proc.prosrc`);
   - fuori dal DB: `grep` nel backend dei nomi delle funzioni e delle colonne del §2.4;
   - chi le verifica: i 13 pgTAP che le nominano (`grep -rlE 'province|provincia_sigla|destinatario_fe|vw_indirizzi_resolved|fn_get_indirizz|fn_get_soggetto_dati_by_ruolo|vw_comuni_lista|vw_province_lista' db/pgtap`).
     Oggi nessuno asserisce il tipo `bpchar`, ma vanno riletti.
4. **Prova** sull'SQL estratto, in transazione annullata. Dopo la ricreazione deve esserci una sola
   funzione per nome, e ogni colonna della catena deve avere il tipo atteso (`pg_attribute`).
   Inoltre `SELECT provincia_sigla FROM script.fn_get_indirizzo(…)` non deve avere spazi.
5. **Manual** di `province` e delle tabelle toccate: si aggiornano il tipo e la regola del `CHECK`.

## 5. Trappole note da non ripetere

- **`%TYPE` in firma è una fotografia.** Le funzioni che ancorano una colonna convertita non si
  aggiornano da sole e vanno ricreate. È il guasto di `fn_search_stradario` del §1.
- **`RETURN QUERY` vuole il tipo identico**: una vista diventata `varchar` sotto una firma ancora
  `bpchar` rompe la chiamata a runtime, non al migrate.
- **Le viste si ricreano dal corpo vivo** e non dagli YAML del 2026-04-02: da allora la catena
  `vw_indirizzi_resolved_*` è stata riscritta più volte (`20260628-09`, `20260927-42`, …).
- **La doc auto-gen non mostra le colonne di un trigger `UPDATE OF`**. Per `province` il catalogo
  dice che non ce ne sono; per le altre tabelle del §2.1 va verificato su `pg_trigger.tgattr`
  prima dell'`ALTER`.
- **Lo storico jsonb** mantiene i valori vecchi con gli spazi nelle righe passate. È storia e non si
  bonifica.

## 6. Richieste a BE/FE

Il lato DB corregge il tipo, quindi **il backend non deve togliere spazi da nessuna parte**: le
query del §2.4 riceveranno valori puliti senza modifiche.

- **R-1 (BE)** — ⛔ **nessun `.strip()`** in uscita su sigla, descrizione o `destinatario_fe`:
  sarebbe il quinto tampone (§1). Se nel frattempo ne è stato aggiunto uno, va tolto dopo l'apply.
- **R-2 (BE/FE)** — dopo l'apply, verifica a video: autocomplete comuni (`Potenza (PZ)`), comune di
  nascita nel dettaglio soggetto, tendina province, dati societari (codice destinatario).
- **R-3 (BE)** — il `.strip().upper()` in **ingresso** di `geo_repository.create_provincia` /
  `update_provincia` può restare: normalizza l'input dell'utente. La regola sulla forma diventa del
  DB (D-2), e un valore fuori forma torna come errore del `CHECK`. Se il codice è nuovo, va
  registrato nella tassonomia errori di `api.md`.

## 7. Registro

| Data | Cosa |
| --- | --- |
| 2026-10-10 | Brief aperto su segnalazione BE (drawer comuni: `Potenza (PZ        )`). Perimetro allargato dall'analisi DB (§2). In attesa di D-1…D-5. |
