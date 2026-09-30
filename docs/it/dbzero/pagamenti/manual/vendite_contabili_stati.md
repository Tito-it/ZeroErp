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
* `is_registrabile` *(18-09-2026, D20-d)*: «da questo stato si puo` registrare?».
  `true` **solo** su `VALIDATA`. La legge `pagamenti.fn_posta_contabile` (guard 3)
  al posto del letterale `'VALIDATA'` — stesso codice `E_CONTABILE_NON_REGISTRABILE`,
  stessa frase, cambia **chi lo dice** — e il dettaglio della distinta la espone
  come `stato_is_registrabile`: «Registra» si spegne col motivo invece di finire in
  409 (rilievo §1 del terzo collaudo). Una bandiera e non una `fn_check`: il
  motivo e` uno e statico, lo stato. Default `false`, fail-closed su uno stato
  nuovo. ⚠️ Il valore sta nel CSV (mirror `20260821-30`), mai in un `UPDATE`.
* `righe_lavorabili` *(30-09-2026, D-1)*: «sotto questo stato le righe della
  distinta si lavorano ancora?». `false` **solo** su `ANNULLATA`. ⭐ `is_final` non
  basta: `CHIUSA` e `ANNULLATA` sono entrambe finali ma opposte per le righe.
  Sotto una chiusa una sospesa ha ancora la registrazione tardiva e una scartata
  si riprende; sotto un'annullata non c'e` niente da dire, perche` quel denaro per
  il registro non e` mai arrivato. La leggono il guard delle righe (quinta mossa:
  sotto `false` ogni `UPDATE` e` rifiutato), la check di eliminabilita`, la coda del
  riconciliatore (le righe escono dalla lista di lavoro) e il frontend (azioni di
  riga spente). Default `false`, fail-closed. ⚠️ Il valore sta nel CSV, mai in un
  `UPDATE`. Brief: `brief-db-righe-distinta-annullata-fuori-dalle-code`.
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
* Si registra **solo** dagli stati con `is_registrabile = true` — oggi `VALIDATA`.
* Sotto gli stati con `righe_lavorabili = false` — oggi `ANNULLATA` — le righe si
  **leggono soltanto**; e in quegli stati entra solo una distinta `MANUALE`.
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
