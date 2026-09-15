## 📘 Documentazione Concettuale – Tabella `pagamenti.vendite_contabili_stati`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili)  
> • [pagamenti.vendite_contabili_righe_stati](/dbzero/pagamenti/tabelle/vendite_contabili_righe_stati)  
>
### 🎯 Scopo Principale
(latest review 13-02-2026)  
La tabella **`pagamenti.vendite_contabili_stati`** definisce il lookup
degli stati della **testata contabile vendite**.

---

### Campi chiave (semantica)

* `codice`: codice stato funzionale (BOZZA, IMPORTATA, VALIDATA, CHIUSA, ANNULLATA).
* `descrizione`: testo descrittivo dello stato.
* `is_final`: indica se lo stato e` terminale.
* `ordine`: priorita`/sequenza di avanzamento stato.
* `attivo`: abilita/disabilita stato per nuovi processi.
* `meta`: estensioni configurative. Dal 2026-09-15 porta su **tutte e cinque**
  le righe la chiave i18n `nessuna_azione_key` (`pagamenti.distinte.stato_info.<stato>`):
  e` il testo che il drawer della distinta mostra per dire *dove si e`* (bozza: si
  digita · validata: pronta da registrare, il denaro non e` ancora registrato ·
  registrata …). Il backend la trasporta come `stato_info_key`, il frontend la passa
  a `DrawerActionsBar :info-key`: e` lo stesso meccanismo degli altri cataloghi di
  stato, descritto in
  [frontend-standards §«L'informazione di stato — prop `infoKey`»](/dev/frontend/frontend-standards).
  ⚠️ Il testo **non** sta qui: qui c'e` solo l'indirizzo i18n, e cambiarlo e` un
  edit del CSV (`80_data/sql/pagamenti/vendite_contabili_stati.csv`), mai un `UPDATE`.

---

### Regole principali

* `codice` univoco.
* Stati finali marcati con `is_final = true`.
* `ordine` usato come supporto per ordinamento operativo.

---

### Esempio d’uso

```sql
SELECT id, codice, descrizione, is_final
FROM pagamenti.vendite_contabili_stati
WHERE attivo IS TRUE
ORDER BY ordine, id;
```

---

{% include-markdown "signature-core.md" %}
