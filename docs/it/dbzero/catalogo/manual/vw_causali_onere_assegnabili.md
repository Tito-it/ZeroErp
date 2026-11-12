## 📘 Documentazione Concettuale – Vista `catalogo.vw_causali_onere_assegnabili`

> **Ultimo aggiornamento**: 12 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.causali_onere](/dbzero/config/tabelle/causali_onere) — le causali onere
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — gli articoli, ognuno con al più una causale
> * [config.tabelle_gestibili](/dbzero/config/tabelle/tabelle_gestibili) — dove la vista è registrata per il lookup generico
>
> Approfondimento funzioni:
>
> * [dbops.fn_get_lookup_codici](/dbzero/dbops/funzioni/fn_get_lookup_codici) — il lookup generico che la legge
> * [catalogo.trgfn_articoli_guard_onere_natura](/dbzero/catalogo/funzioni/trgfn_articoli_guard_onere_natura) — il guard che rifiuta la causale già usata
>
> Approfondimento viste:
>
> * [catalogo.vw_articoli_dettaglio](/dbzero/catalogo/views/vw_articoli_dettaglio) — la causale dell'articolo aperto

---

### 🎯 Scopo Principale

Le causali onere che si possono dare a un articolo nuovo: quelle che nessun articolo porta ancora.
La tendina della causale, nel drawer articolo, legge questa vista.

---

### ⭐ Perché serve

Una causale onere va a un articolo solo. Ordini, bolle e commesse prendono prezzo e IVA
dell'addebito dall'articolo della causale, quindi due articoli con la stessa causale renderebbero
la scelta ambigua. La regola «quali causali sono libere» sta qui, e la tendina non la ricostruisce.

---

### Come si legge

* La vista ha la forma del lookup generico: `id`, `codice`, `codice_interno`, `descrizione`,
  `attivo`. È registrata in `config.tabelle_gestibili` per il lookup, non per il pannello di
  configurazione: la tendina la chiama come le altre, senza un servizio dedicato.
* La vista toglie solo le causali già legate. Le causali spente restano nella vista: le toglie il
  lookup, che di default mostra solo le attive.
* La causale dell'articolo aperto non c'è, perché è legata a lui. Il drawer la legge dalla riga
  dell'articolo (`causale_onere_descrizione` di `catalogo.vw_articoli_dettaglio`). Su un articolo
  già usato la causale non cambia più, e la tendina è spenta.
* La vista non decide da sola: se due operatori scelgono la stessa causale nello stesso momento,
  il secondo riceve `E_ARTICOLO_CAUSALE_ONERE_GIA_USATA` dal guard dell'articolo.

---

### Test

* `db/pgtap/catalogo/test-causale-onere-assegnabile-v1.sql` — la causale libera c'è, quella
  data a un articolo esce; il lookup generico dà le libere attive; la vista è registrata per il
  lookup e fuori dal pannello.

---

### Note di migrazione

* 2026-11-12 — nasce (brief-db-addebito-trasporto-ordine).

---

{% include-markdown "signature-core.md" %}
