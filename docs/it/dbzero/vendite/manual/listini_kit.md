## 📘 Documentazione Concettuale – Tabella `vendite.listini_kit`

> **Ultimo aggiornamento**: 6 novembre 2026

> 👀 **Vedi anche**
>
> [vendite.listini_righe](/dbzero/vendite/manual/listini_righe) — i prezzi degli articoli semplici
> [vendite.listini_righe_componenti](/dbzero/vendite/manual/listini_righe_componenti) — i prezzi dei componenti di un kit
> [vendite.fn_listino_periodicita_articolo](/dbzero/vendite/manual/fn_listino_periodicita_articolo) — la sede che la legge
> [Guida dei listini §2.1](/guide/gestione-listini#21-listino)

---

### 🎯 Scopo Principale
(31-10-2026 — brief `brief-db-contratto-righe-periodiche-in-commessa` §7.2, D-2-bis, decisione B di Tid)

**Il kit su una versione di listino, per ciò che non è un prezzo.** Una riga per versione e kit:
oggi la **periodicità** con cui il kit si addebita a canone. Su un kit di quota fissa è il ritmo
con cui ogni contratto del listino lo paga; altrove è la periodicità proposta all'adesione.

Il kit sul listino **non ha una riga** in `listini_righe`, per la decisione del modello unificato
dei componenti (`work-done/brief-db-componenti-modello-unificato.md`, 2026-05): il suo prezzo è
la somma dei componenti, e qui non c'è. Senza questa tabella un kit non avrebbe avuto dove
tenere la periodicità: la quota fissa di un kit non si sarebbe mai addebitata, e un kit aderito
non l'avrebbe ereditata.

Scartate, nella stessa decisione: la riga del padre in `listini_righe` senza prezzo (revocava il
modello unificato e toglieva il `NOT NULL` a `prezzo`); la periodicità sull'articolo (è una
condizione del listino, non del catalogo).

---

### Regole

* Una riga per kit e versione (`uq_listini_kit_versione_articolo`); `periodicita` è `NOT NULL`:
  togliere la periodicità di un kit è togliere la riga.
* Si scrive **solo in bozza**, INSERT, UPDATE e DELETE (`E_RIGA_LISTINO_VERSIONE_CHIUSA`, come i
  componenti), e **solo per un composito** (`E_LISTINO_KIT_NON_COMPOSITO`): la periodicità di un
  articolo semplice sta sulla sua riga di listino. Lo tiene
  [vendite.trgfn_listini_kit_guard](/dbzero/vendite/funzioni/trgfn_listini_kit_guard).
* Kit e versione sono l'identità della riga: dopo l'inserimento non cambiano
  (`E_LISTINO_RIGA_IDENTITA_IMMUTABILE`, il lucchetto generato, come sulla riga di listino).
* **Il kit non nasce su un articolo ritirato** (6-11-2026, `20261106-02`): il guard generico
  [dbops.trgfn_child_requires_non_obsolete_parent](/dbzero/dbops/funzioni/trgfn_child_requires_non_obsolete_parent)
  su `articolo_padre_id`, senza esenzione, perché una versione di listino è sempre una scelta
  (`E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`). Il kit esistente, il cui articolo è poi ritirato, si
  modifica. Vedi la [guida dell'obsoleto](/guide/uso-di-obsoleto).
* Il clone della versione la copia (non il kit di un articolo ritirato), l'eliminazione la porta via
  ([vendite.fn_clona_versione_listino](/dbzero/vendite/manual/fn_clona_versione_listino),
  [vendite.fn_elimina_versione_listino](/dbzero/vendite/manual/fn_elimina_versione_listino)).
* RLS della famiglia dei listini.

### Chi la legge

Una sola sede, [vendite.fn_listino_periodicita_articolo](/dbzero/vendite/manual/fn_listino_periodicita_articolo):
il default della periodicità sulla riga a canone, l'addebito dei contratti, l'anteprima delle
righe e il controllo all'attivazione della versione.

### 🧪 Il presidio

`db/pgtap/vendite/test-listino-kit-e-periodicita-v1.sql`.

---

{% include-markdown "signature-core.md" %}
