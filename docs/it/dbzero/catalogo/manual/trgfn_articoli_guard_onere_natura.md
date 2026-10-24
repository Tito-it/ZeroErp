## 📘 Documentazione Concettuale – Funzione `catalogo.trgfn_articoli_guard_onere_natura`

> 👀 **Vedi anche**
>
> [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — la tabella su cui il trigger opera (§ Articolo-onere)
> [config.nature_vendita](/dbzero/config/tabelle/nature_vendita) — il vocabolario da cui si legge la destinazione
> [vendite.fn_aggiungi_onere_commessa](/dbzero/vendite/funzioni/fn_aggiungi_onere_commessa) — la porta che scrive gli oneri in commessa

### 🎯 Scopo Principale

(latest review 2026-10-13)

Un **articolo-onere** (`causale_onere_id` valorizzato) rappresenta un addebito — trasferta,
urgenza, spese amministrative, penale — e si scrive in commessa. Non è merce: la sua natura non
può avere destinazione `ORDINE`.

Senza questo guard un onere creato senza dire la natura prendeva il default di
`natura_vendita_id`, che è la merce: sarebbe stato un bene da evadere in ordine e in bolla, e
per il fisco una cessione di beni (`e_cessione_beni`).

---

### Logica applicata

* Trigger `trg_articoli_a10_guard_onere_natura_ins_upd`, **BEFORE INSERT OR UPDATE OF
  natura_vendita_id, causale_onere_id** su `catalogo.articoli`.
* Un articolo senza `causale_onere_id` passa. Un UPDATE che non cambia nessuna delle due
  colonne non si rigiudica (per esempio il loader del seed che riscrive gli stessi valori).
* Se la natura ha `destinazione_tipo = 'ORDINE'` → `E_ARTICOLO_ONERE_NATURA_MERCE` (1295),
  campo `natura_vendita_id`, con il codice dell'articolo e la descrizione della natura.

**Perché la destinazione e non il codice della natura**: è la stessa lettura delle viste di
smistamento del preventivo e dei guard sulle righe d'ordine. Se una natura cambia destinazione
nel vocabolario, la regola la segue senza toccare codice.

⚠️ Il guard giudica l'articolo. Un cambio di `destinazione_tipo` in `config.nature_vendita` è una
modifica del vocabolario, e qui non si giudica.

---

### Comportamento atteso

* **Consentito**: un onere con natura di servizio (gli oneri del seed hanno il servizio una
  tantum, destinazione commessa); un articolo non-onere con qualunque natura.
* **Bloccato**: un onere con una natura che va in ordine, sia quando nasce, sia quando cambia la
  natura, sia quando un articolo merce riceve una causale onere.

---
{% include-markdown "signature-core.md" %}
