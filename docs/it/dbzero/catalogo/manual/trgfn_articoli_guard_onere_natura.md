## 📘 Documentazione Concettuale – Funzione `catalogo.trgfn_articoli_guard_onere_natura`

> **Ultimo aggiornamento**: 3 novembre 2026

> 👀 **Vedi anche**
>
> [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — la tabella su cui il trigger opera (§ Articolo-onere)
> [config.nature_vendita](/dbzero/config/tabelle/nature_vendita) — il vocabolario da cui si legge la destinazione
> [vendite.fn_aggiungi_onere_commessa](/dbzero/vendite/funzioni/fn_aggiungi_onere_commessa) — la porta che scrive gli oneri in commessa

### 🎯 Scopo Principale

Un **articolo-onere** (`causale_onere_id` valorizzato) rappresenta un addebito — trasferta,
urgenza, spese amministrative, penale. Dal 2026-11-03 entra anche nelle righe di ordine e bolla,
come un articolo, ma resta un addebito: **non è merce** (la sua natura non va in ordine) e **non
è un bene** (non sta a magazzino, non ha distinta, lotti né matricole).

Senza questo guard un onere creato senza dire la natura prendeva il default di
`natura_vendita_id`, che è la merce: sarebbe stato un bene da evadere in ordine e in bolla, e
per il fisco una cessione di beni (`e_cessione_beni`).

---

### Logica applicata

* Trigger `trg_articoli_a10_guard_onere_natura_ins_upd`, **BEFORE INSERT OR UPDATE OF
  natura_vendita_id, causale_onere_id, gestito_a_magazzino, is_composito, requires_lotto,
  requires_serial** su `catalogo.articoli`.
* Un articolo senza `causale_onere_id` passa. Un UPDATE che non cambia nessuna delle sei
  colonne non si rigiudica (per esempio il loader del seed che riscrive gli stessi valori).
* **Regola 1 — la natura.** Se la natura è merce
  ([script.fn_natura_e_merce](/dbzero/script/funzioni/fn_natura_e_merce), destinazione
  `ORDINE_VENDITA`) → `E_ARTICOLO_ONERE_NATURA_MERCE` (1295), campo `natura_vendita_id`, con il
  codice dell'articolo e la descrizione della natura.
* **Regola 2 — la struttura** (rev 2026-11-03). Se l'onere è gestito a magazzino, composito, a
  lotti o a matricola → `E_ARTICOLO_ONERE_STRUTTURA`, campo = la prima colonna in quest'ordine,
  con il codice dell'articolo e il nome leggibile della caratteristica. Nessuna porta
  amministratore: nemmeno la correzione di struttura fa di un onere un bene.
* La regola 1 parla prima della 2: un articolo merce che riceve una causale si sente dire della
  natura.

**Perché la struttura.** Con gli oneri sulle righe di ordine e bolla, magazzino, prelievi,
scarico e distinta leggono i flag dell'articolo: se l'onere non li ha mai, quei lettori restano a
posto per costruzione, senza un filtro ciascuno (brief-db-addebito-trasporto-ordine §8.1,
decisione 10).

**Perché la destinazione e non il codice della natura**: è la stessa lettura del building
block «la natura è merce», che usano anche l'ammissione delle righe d'ordine e bolla e lo
smistamento del preventivo. Se una natura cambia destinazione
nel vocabolario, la regola la segue senza toccare codice.

⚠️ Il guard giudica l'articolo. Un cambio di `destinazione_tipo` in `config.nature_vendita` è una
modifica del vocabolario, e qui non si giudica.

---

### Comportamento atteso

* **Consentito**: un onere con natura di servizio (gli oneri del seed hanno il servizio una
  tantum, destinazione commessa); un articolo non-onere con qualunque natura.
* **Bloccato**: un onere con una natura che va in ordine, sia quando nasce, sia quando cambia la
  natura, sia quando un articolo merce riceve una causale onere; un onere gestito a magazzino,
  composito, a lotti o a matricola, quando nasce o quando cambia uno solo di quei flag.

---
{% include-markdown "signature-core.md" %}
