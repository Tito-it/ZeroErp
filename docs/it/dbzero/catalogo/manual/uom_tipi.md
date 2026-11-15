## 📘 Documentazione Concettuale – Tabella `catalogo.uom_tipi`

> **Ultimo aggiornamento**: 11 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura) — le unità, ognuna in una sola famiglia
> * [catalogo.unita_misura_conversioni](/dbzero/catalogo/tabelle/unita_misura_conversioni) — le conversioni globali, ammesse solo dentro una famiglia
> * [catalogo.articoli_uom_operativa](/dbzero/catalogo/tabelle/articoli_uom_operativa) — i fattori di un solo articolo, che la famiglia non limita
>
> Approfondimento funzioni:
>
> * [catalogo.trgfn_uom_conversioni_guard_tipo](/dbzero/catalogo/funzioni/trgfn_uom_conversioni_guard_tipo) — rifiuta una conversione fra due famiglie
> * [catalogo.trgfn_unita_misura_guard_tipo](/dbzero/catalogo/funzioni/trgfn_unita_misura_guard_tipo) — rifiuta il cambio di famiglia di un'unità che ha conversioni, e lega il calendario al tempo
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns) — il blocco di `codice_interno`

---

### 🎯 Scopo Principale

È l'elenco delle famiglie di unità di misura (massa, lunghezza, energia, tempo…). Ogni
unità di `catalogo.unita_misura` appartiene a una sola famiglia, e una conversione globale
si scrive solo fra due unità della stessa famiglia.

Senza famiglie il database accetterebbe conversioni senza senso, come metri in grammi o
litri in pezzi. La famiglia non riguarda i fattori di un singolo articolo (la scatola da 50
pezzi, il cartone da 6 bottiglie): quelli stanno in `articoli_uom_operativa` e collegano
anche unità di famiglie diverse.

---

### Le famiglie del seed

Il seed porta `LUNGHEZZA`, `MASSA`, `VOLUME`, `AREA`, `ENERGIA`, `POTENZA`, `TEMPO`,
`QUANTITA`, `IMBALLAGGIO` e `GENERICO`. Non c'è una famiglia per le valute.

* `IMBALLAGGIO` classifica pallet, colli, scatole. Non vuol dire che esista un fattore
  universale fra loro: quanti pezzi stanno in una scatola dipende dall'articolo.
* `GENERICO` è un ripiego controllato, da non usare come contenitore di unità eterogenee.
* `TEMPO` ha una regola sua: solo un'unità di questa famiglia si può contare dal calendario
  (`unita_misura.conta_dal_calendario`). Il guard delle unità la riconosce dal codice interno.
* `SMC` (standard metro cubo di gas) sta in `ENERGIA` con `KWH` e `MJ`, non in `VOLUME`:
  così una sua conversione verso le unità di energia è ammessa. Il seed delle conversioni
  però è vuoto: nessuna conversione è scritta.

---

### L'identificativo stabile è `codice_interno`

La tabella ha due codici, `codice` e `codice_interno`, tutti e due unici, e nel seed hanno
lo stesso valore. Quello bloccato è `codice_interno`: dopo la creazione non si modifica.
`codice` invece si può cambiare, e si salva normalizzato (senza spazi ai lati, in
maiuscolo). È `codice` quello che si mostra e si cerca: il backend lo usa come etichetta della
famiglia, per l'ordinamento e per la ricerca. Per questo le due colonne restano tutte e due:
dicono la stessa cosa oggi, ma servono a due lettori diversi.

---

### Una famiglia usata non si spegne

`attivo = false` ritira una famiglia senza cancellarla, ma solo se nessuna unità attiva vi
appartiene. Un'unità attiva non può puntare a una famiglia spenta: il controllo scatta alla
fine della transazione.

---

### Codici errore

* `E_CODICE_NON_MODIFICABILE` — modifica di `codice_interno`.
* `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` — spegnimento di una famiglia che ha ancora unità attive.

---

### Test

* `db/pgtap/catalogo/test-uom-tipi-global-conversioni-v1.sql` — le famiglie del seed ci
  sono, una conversione dentro la stessa famiglia passa, una fra due famiglie è rifiutata.
* `db/pgtap/script/test-fn-codice-normalizzato-v1.sql` — la normalizzazione del codice.

---

### Note di migrazione

* 2026-04-28 — nasce la tabella, con il seed delle famiglie e il riempimento di
  `unita_misura.tipo_uom_id` per le unità che esistevano già.
* 2026-11-11 — ritirato l'indice su `upper(codice_interno)`, che nessuna lettura usava; i
  COMMENT di `codice` e `codice_interno` dicono le due cose diverse
  (brief-db-revisione-catalogo, giro 5).

---

{% include-markdown "signature-core.md" %}
