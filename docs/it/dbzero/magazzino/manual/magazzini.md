## 📘 Documentazione Concettuale – Tabella `magazzino.magazzini`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — di chi è il magazzino
> • [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — dove sta
> • [magazzino.ubicazioni](/dbzero/magazzino/tabelle/ubicazioni) — le posizioni al suo interno
>
Approfondimento funzioni:
> • [script.fn_scope_ef_whitelist_via_magazzino](/dbzero/script/funzioni/fn_scope_ef_whitelist_via_magazzino) — la risalita che tutto il dominio usa
> • [script.trgfn_guard_emittente_scope](/dbzero/script/funzioni/trgfn_guard_emittente_scope)
>
Guide: brief `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.7, §4.10) · analisi carico e scarico (§7-sexies, M-6)

---
### 🎯 Scopo Principale

(rev 2026-09-15 — Lotto 1 del magazzino)

**Anagrafica dei magazzini e depositi.** Un magazzino è un *luogo*, non un soggetto: il suo
indirizzo è legato ad `anagrafiche.indirizzi_dettaglio` e non passa da un ruolo anagrafico —
è la differenza rispetto a clienti, fornitori e vettori. ⚠️ `indirizzo_dettaglio_id` è
obbligatorio: serve un indirizzo prima del magazzino.

Il codice viene normalizzato da `trgfn_magazzini_normalize` (maiuscolo, senza spazi ai
bordi): `mag1`, `MAG1 ` e ` Mag1` sono lo stesso codice.

---

### L'ancora del perimetro: `emittente_fiscale_id`

Dal 15-09 ogni magazzino dice **di chi è**: `emittente_fiscale_id` è obbligatorio, senza
default, con la FK verso `anagrafiche.emittenti_fiscali`. È l'**ancora** da cui discende il
perimetro di tutto il dominio — movimenti, attese, valore, inventari, rettifiche,
trasferimenti, ubicazioni e le loro note leggono l'emittente dal magazzino
(`fn_scope_ef_whitelist_via_magazzino`). Un magazzino senza emittente non appartiene a
nessuno e nessuno lo vedrebbe.

Un operatore vede e scrive i magazzini del **proprio emittente** (policy
`rls_magazzini_ef_whitelist`); chi scrive deve avere l'emittente che dichiara nel proprio
perimetro (`trgfn_guard_emittente_scope`, la difesa in profondità). Il meccanismo è quello
comune: [Linee guida SQL — sezione 10](/linee-guida-sql#10-row-level-security-rls).

⚠️ **Punto aperto**: non c'è un trigger che assegni l'emittente da solo dalla sessione (nelle
vendite ce n'è uno per documento). Chi crea un magazzino lo dice; il pannello di
amministrazione generico oggi non lo passa, ed è un punto da chiudere quando servirà.

---

### Le regole che il magazzino porta con sé

* nessuna operazione di magazzino attraversa due emittenti: un trasferimento fra un
  magazzino di A e uno di B è rifiutato (`trgfn_trasferimenti_guard_stesso_emittente`);
* un magazzino con movimenti, attese, inventari, rettifiche o ubicazioni non si spegne
  (guard generati dal framework delle automazioni);
* è storicizzato e la sua storia porta il perimetro dell'emittente (mappa
  `dbops.storico_scope_policy`, modo `EF`).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
