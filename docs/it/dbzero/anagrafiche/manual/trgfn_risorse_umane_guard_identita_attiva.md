## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_risorse_umane_guard_identita_attiva`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
>
**Approfondimento funzioni:**
>
[dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children) — la stessa regola, generata dall'automazione, per le coppie legate da una FK
>
Guida: [Risorse umane e accessi](/guide/risorse-umane-e-accessi) · [Disattivazione record — ordine UPDATE e trigger](/dev/api#disattivazione-record-ordine-update-e-trigger)

---
### 🎯 Scopo Principale
(nata il 12-09-2026, `20_code/anagrafiche/20260912-18`; decisione Tid, analisi
`analisi-software-per-dati-morti` §6.2)

**Una risorsa umana con un'identità operatore ancora attiva non si disattiva.**
È «figli prima, padre poi», la regola di tutto il progetto — qui scritta a mano
perché il legame fra `risorse_umane` e `identita_digitali` **non è una chiave
esterna** (passa da `soggetto_ruolo_id`), e l'automazione ATTIVO, che genera i
guard dalle FK, non lo vede.

Trigger: `trg_risorse_umane_a10_guard_identita_attiva_upd`, `BEFORE UPDATE OF
attivo` su `anagrafiche.risorse_umane`, fase `_a10_`. Interviene **solo** sulla
transizione `attivo` `true → false`; INSERT e UPDATE di altre colonne non sono
affar suo.

---

### ⚠️ Perché è nata: una regola che viveva per caso

Fino al 12-09-2026 la stessa regola la faceva rispettare il guard di automazione
`trg_risorse_umane_a10_risorse_umane_auth_user_block_deact_upd`, generato quando
`risorse_umane_auth_user` era una **tabella** figlia. Dopo il cutover multi-face
quel nome risolveva una **vista** su `identita_digitali`, e il guard continuava
a funzionare per caso (la vista aveva `risorsa_umana_id` e `attivo`). Con il
ritiro della vista (`90_end/20260912-26`) sarebbe caduto — o peggio, avrebbe
sollevato `E_ATTIVO_BLOCK_FKCOL_NOT_FOUND` a ogni disattivazione, come il
guard gemello sulla legacy la mattina dello stesso giorno. Il guard di
automazione è stato ritirato (`00_schema/20260912-19`) **dopo** che questo era
in servizio nella timeline: nessuna finestra senza regola.

L'alternativa scartata — nessun guard, la risorsa si disattiva e il sync spegne
l'utente — avrebbe fatto trascinare il figlio dal padre: un modello diverso da
tutte le altre coppie padre/figlio.

---

### Come rifiuta

Codice **suo**, [`E_RISORSA_UMANA_IDENTITA_ATTIVA`](/guide/Messaggi-di-Errore-e-Generazione-Log)
(classe `CONFLITTO_STATO`: lo stato del figlio può cambiare, quindi l'azione
resta proposta e disabilitata col motivo — non `E_ATTIVO_BLOCK_CHILDREN_ACTIVE`,
che è dell'automazione e nomina una FK). Nel contesto: `campo = attivo`
(l'interruttore che il frontend accende), `risorsa_umana_id`,
`soggetto_ruolo_id`. Nel `VARIADIC` lo **username** dell'utente ancora attivo:
è ciò che una persona riconosce, e la frase a catalogo lo nomina.

Il rimedio è nella `soluzione` a catalogo: disattivare prima l'identità
operatore (o chiuderne la validità), poi ripetere.

---

### Presidio

`db/pgtap/anagrafiche/test-risorse-umane-guard-identita-attiva-v1.sql` — otto
test su un operatore **costruito** dalla madre `fn_crea_operatore_v2` (non
cercato: in CI `anagrafiche` è vuoto): rifiuto con codice nel canale
`CONSTRAINT` e username nella frase; passaggio a identità spenta; il sync
`z90` che spegne l'utente; il guard vecchio non più montato.

---

{% include-markdown "signature-core.md" %}
