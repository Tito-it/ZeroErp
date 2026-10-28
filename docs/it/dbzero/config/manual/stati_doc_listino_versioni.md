## 📘 Documentazione Concettuale – Tabella `config.stati_doc_listino_versioni`

> 👀 **Vedi anche**
>
> [config.transizioni_stati_listino_versioni](/dbzero/config/tabelle/transizioni_stati_listino_versioni) ·
> [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni) ·
> [Il modello del documento di vendita](/guide/modello-documento-di-vendita)

### 🎯 Scopo
(28-10-2026 — brief `brief-modello-documento-vendita` §16, L-1)

**Gli stati di una versione di listino.** La colonna
`vendite.listini_versioni.stato_doc_listino_versione_id` ne porta l'id (FK).

| Codice | Che cosa vuol dire |
| --- | --- |
| BOZZA | in preparazione: righe e date si cambiano, la versione si elimina. Lo stato in cui nasce (`iniziale`) |
| ATTIVA | i prezzi sono in uso; si cambia solo la fine validità |
| CHIUSA | la finestra è passata: è la storia dei prezzi di un periodo. Niente esce da qui (`terminale`) |

### Regole

* `codice_interno` è la chiave stabile: la leggono `script.fn_doc_stato_id` e i lettori che
  confrontano un codice.
* ⚠️ Gli id del seed (1 BOZZA, 2 ATTIVA, 3 CHIUSA) sono scritti anche nel predicato di
  `ex_listini_versioni_no_overlap` e in `chk_listini_versioni_chiusa_con_fine`, perché un
  vincolo non legge un'altra tabella. Non si rinumerano; il pgTAP
  `vendite/test-listino-versione-al-modello-v1` li confronta coi codici.
* Seed dal CSV `80_data/sql/config/stati_doc_listino_versioni.csv`.

---

{% include-markdown "signature-core.md" %}
