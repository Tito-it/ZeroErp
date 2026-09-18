## 📘 Documentazione Concettuale – Tabella `magazzino.movimenti`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.causali](/dbzero/magazzino/tabelle/causali) — il verso
> • [magazzino.lotti](/dbzero/magazzino/tabelle/lotti) e [magazzino.assets](/dbzero/magazzino/tabelle/assets) — la tranche
> • [magazzino.valore_giacenza](/dbzero/magazzino/tabelle/valore_giacenza) — la copia del valore
> • [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo delle sorgenti
>
Approfondimento viste e funzioni:
> • [magazzino.vw_giacenza](/dbzero/magazzino/views/vw_giacenza), [magazzino.vw_giacenza_ubicazione](/dbzero/magazzino/views/vw_giacenza_ubicazione)
> • [magazzino.trgfn_movimenti_guard_verso](/dbzero/magazzino/funzioni/trgfn_movimenti_guard_verso)
> • [script.trgfn_guard_sorgente_polimorfa_tipizzata](/dbzero/script/funzioni/trgfn_guard_sorgente_polimorfa_tipizzata)
>
Guide: [Sorgente polimorfa](/guide/sorgente-polimorfa) · brief `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.4)

---
### 🎯 Scopo Principale

(rev 2026-09-15 — Lotto 1 del magazzino)

**Il registro dei movimenti**: una riga per ogni entrata o uscita di un articolo da un
magazzino. È l'unica scrittura che conta — la giacenza è la somma di queste righe, il valore
è la ri-somma dei loro costi — e non esiste un posto dove «correggere la giacenza» senza
passare da qui.

Dal 15 settembre 2026 la tabella ha la forma decisa dalle analisi di settembre (M-1 → M-8,
D-1 → D-9). Quattro regole la governano, e chi la legge deve saperle prima di scrivere.

---

### Le quattro regole

**1. La sorgente è obbligatoria e a catalogo.** Ogni movimento dice *quale operazione* lo
ha generato: `sorgente_tipo_id` (una riga di [config.sorgenti](/dbzero/config/tabelle/sorgenti):
riga di bolla, riga di inventario, riga di rettifica, riga di trasferimento, evento di un
asset…) più **esattamente una** chiave fra `sorgente_riga` (numerica) e `sorgente_uid`
(UUID), secondo quanto il catalogo dichiara per quel tipo. Un guard verifica che il record
esista davvero: una sorgente inesistente è rifiutata, non registrata.

⭐ Non esiste un movimento senza operazione a monte: **la correzione a mano è una
rettifica**, con la sua riga. Fino al 14-09 la tabella portava un riferimento libero
(`doc_schema`, `doc_table`, `doc_id`) che nessun vincolo controllava — poteva nominare una
tabella che non c'era.

**2. Il verso sta nella quantità.** `qta` è firmata: positiva in entrata, negativa in uscita,
mai zero. Il segno deve coincidere con `causali.segno`; se non coincide, il guard
[trgfn_movimenti_guard_verso](/dbzero/magazzino/funzioni/trgfn_movimenti_guard_verso) rifiuta
la riga (`E_MAG_MOVIMENTO_VERSO_INCOERENTE`). È la ragione per cui `vw_giacenza` può sommare
senza guardare le causali: la quantità arriva già nel verso giusto, e applicare il segno una
seconda volta lo raddoppierebbe.

**3. La quantità è in unità base dell'articolo.** Non c'è più una `uom_id` sul movimento:
come l'operatore ha digitato la quantità (10 scatole da 12) sta sulla riga di documento, che
il movimento raggiunge attraverso la sorgente. La conversione la fa l'operazione prima di
scrivere qui.

**4. L'identità è l'operazione-per-tranche.** L'indice unico `uq_mag_movimenti_identita` è
sulla terna *(sorgente, chiave del record, causale)* più la tranche *(asset, lotto,
ubicazione)*, con `NULLS NOT DISTINCT`: due righe uguali senza lotto, seriale e ubicazione
**collidono** (è la stessa operazione scritta due volte), mentre le due righe OUT/IN di un
trasferimento no (causali diverse) e N tranche dello stesso ricevimento no (lotti diversi).
⭐ La causale è il *verbo* dell'operazione: non serve una colonna che lo ripeta.

---

### Lotto, seriale, posizione

`lotto_id` e `asset_id` sono chiavi verso [magazzino.lotti](/dbzero/magazzino/tabelle/lotti)
e [magazzino.assets](/dbzero/magazzino/tabelle/assets), non più testo libero. Con un asset la
quantità è **uno** (`|qta| = 1`): un pezzo serializzato si muove uno alla volta. Se
l'articolo li pretende (`catalogo.articoli.requires_lotto`, `requires_serial`) è la primitiva
di scrittura (Lotto 2) a rifiutare un movimento senza.

`ubicazione_id` è **una sola** posizione per riga: uno spostamento dentro lo stesso magazzino
sono due righe, un'uscita dall'una e un'entrata nell'altra. Le vecchie coppie
(`magazzino_id_dest`, `ubicazione_id_from/_to`) non esistono più.

---

### Un ledger non si spegne: si storna

Non c'è più `attivo`. Un movimento sbagliato si annulla con un movimento contrario, che lo
nomina in `storno_di_movimento_id` e porta una causale di verso opposto (`STORNO_POS` per
annullare un'uscita, `STORNO_NEG` per un'entrata). Il legame è unico: un movimento si storna
una volta sola. L'utility che lo fa è un lotto successivo.

---

### Il costo

`costo_unitario` ha tre significati, e vanno tenuti distinti: in **entrata** da documento è
un dato in ingresso (il prezzo della riga d'acquisto, il costo di produzione); in **uscita** è
un dato calcolato — la media ponderata corrente dell'articolo in quel magazzino; nella riga
IN di un trasferimento è **ereditato** dalla riga OUT gemella.
[magazzino.valore_giacenza](/dbzero/magazzino/tabelle/valore_giacenza) è la somma di questi
valori, e si ricostruisce da qui.

---

### Chi può vedere e scrivere

La tabella è nel perimetro RLS del dominio: un operatore vede e scrive i movimenti dei
magazzini del **proprio emittente** (policy `rls_movimenti_ef_whitelist`, che risale dal
magazzino). Il meccanismo è quello comune a tutto il progetto: vedi
[Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

⭐ **Dal 18-09 (Lotto 2) la porta c'è.** L'applicazione ha **solo lettura** sul registro: scrive
soltanto [fn_scrivi_movimento](/dbzero/magazzino/funzioni/fn_scrivi_movimento), che gira con i
permessi del proprietario ed è l'unica strada — con i quattordici controlli nell'ordine del
contratto, il lock in uscita, il costo deciso dalla struttura, la copia del valore aggiornata.
Il perimetro che quella funzione scavalca lo rimette il guard di scope montato qui
(`trg_movimenti_a10_guard_emittente_scope_ins_upd`, modo `magazzino`), che dal 18-09 si ferma
anche senza identità in sessione. La postura sta in tre sedi (`90_end/20260918-15`, il loop
`ci_apply`, il provisioning) e `test-porta-ledger-v1` le tiene allineate.

---

### Storia

* 2026-08-21 — primo pgTAP della tabella; corretto il CHECK che rendeva inseribili solo i
  trasferimenti (`20260821-10`).
* 2026-09-15 — la forma decisa (`20260915-05`): via `doc_*`, `lotto`/`seriale` testo, le
  coppie, `attivo`, `uom_id`; entrano sorgente a catalogo, `lotto_id`, `asset_id`,
  `ubicazione_id`, `storno_di_movimento_id`, l'identità. Il guard del verso, che questa pagina
  segnalava mancante dal 21-08, è `20260915-13`. Presidio:
  `db/pgtap/magazzino/test-movimenti-vincoli-v2.sql`.
* 2026-09-18 — la porta (Lotto 2): l'app perde `INSERT/UPDATE/DELETE` (`20260918-15`), il guard
  di scope entra sul ledger (`20260918-14`), nasce la primitiva (`20260918-18`). `vincoli-v2`
  passa al runner owner (forma 3); il comportamento sta nei `test-fn-scrivi-movimento-*`.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
