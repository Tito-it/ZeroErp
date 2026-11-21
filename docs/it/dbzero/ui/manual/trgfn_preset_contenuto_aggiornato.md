## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_preset_contenuto_aggiornato`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_preset](/dbzero/ui/tabelle/lista_preset) — preset di lista: contenuto è la composizione e le righe per pagina
> * [ui.dashboard_preset](/dbzero/ui/tabelle/dashboard_preset) — preset di dashboard: contenuto è la composizione e il numero massimo di widget
> * [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente) — lo snapshot che la data confronta
> * [ui.dashboard_preferenza_utente](/dbzero/ui/tabelle/dashboard_preferenza_utente) — lo snapshot delle dashboard
>
> Approfondimento funzioni:
>
> * [ui.trgfn_preset_riga_tocca_preset](/dbzero/ui/funzioni/trgfn_preset_riga_tocca_preset) — la stessa data, mossa dalle righe del preset
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — il flag «preset aggiornato» delle liste
> * [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) — il flag delle dashboard
> * [script.trgfn_audit_data_user_generic](/dbzero/script/funzioni/trgfn_audit_data_user_generic) — l'audit, che è un'altra data

---

### 🎯 Scopo Principale

`ui.trgfn_preset_contenuto_aggiornato` tiene `contenuto_aggiornato_il` di un preset: la data
dell'ultimo cambio del suo **contenuto**, per chiave. È la mappa che i due resolver confrontano,
chiave per chiave, con lo snapshot salvato nella preferenza per accendere il banner «preset
aggiornato». La usano i preset di lista e quelli di dashboard.

---

### Una data per chiave

Le chiavi sono quelle che una preferenza può personalizzare, e ognuna ha la sua colonna:

| Famiglia | Chiave | Colonna |
| --- | --- | --- |
| [lista_preset](/dbzero/ui/tabelle/lista_preset) | `colonne` | `composizione_impronta` (la composizione) |
| | `pagina_dimensione` | `pagina_dimensione` |
| [dashboard_preset](/dbzero/ui/tabelle/dashboard_preset) | `widget` | `composizione_impronta` (la composizione) |
| | `dimensione_max` | `dimensione_max` |

L'ordinamento di partenza del preset (`ordinamento_default`) non è una chiave: la preferenza non lo
personalizza, e il suo cambio non accende il banner. Lo segue subito chiunque abbia il preset come base.

All'INSERT tutte le chiavi nascono all'ora dell'INSERT. All'UPDATE la funzione riparte dalla mappa
di prima e sposta solo la chiave la cui colonna è cambiata: una preferenza che segue il preset su
una chiave non vede il banner quando ne cambia un'altra. La mappa è una sola funzione per le due
famiglie: la famiglia la dice la tabella su cui il trigger è montato.

L'ora è quella del cambio (`clock_timestamp`), non quella della transazione: un cambio del preset
fatto nella stessa transazione dopo lo snapshot di una preferenza risulta più recente dello
snapshot.

---

### ⭐ La composizione passa dall'impronta

Le colonne e i widget stanno nelle righe del preset, non nella testata. Il trigger differito della
composizione, [trgfn_preset_riga_tocca_preset](/dbzero/ui/funzioni/trgfn_preset_riga_tocca_preset),
scrive a fine transazione l'impronta della composizione in `composizione_impronta`, e solo se è
cambiata. Per questa funzione l'impronta è una colonna come le altre: quando cambia, si sposta la
chiave `colonne` (o `widget`).

---

### ⛔ La data e l'impronta le scrive solo il database

Chi scrive `contenuto_aggiornato_il`, o un'impronta diversa da quella della composizione di oggi,
riceve `E_UI_PRESET_CONTENUTO_DERIVATO`. All'INSERT il rifiuto scatta se una delle due è indicata.
Una riscrittura con lo stesso valore passa: il rifiuto guarda i valori, non le colonne nominate.

Si rifiuta invece di ignorare per via del seed di primo impianto: il suo trigger, che parla prima,
giudica la personalizzazione di un preset sul valore che arriva. Una scrittura ignorata
personalizzerebbe per finta un preset di seed.

---

### Non è l'audit

`data_update` è l'audit del framework e si sposta a ogni UPDATE, anche se riscrive la riga uguale
(il seed lo fa a ogni giro) o tocca solo `attivo`. Se il banner guardasse l'audit si accenderebbe a
tutti a ogni rilascio. Qui una riscrittura uguale non sposta niente, e codice, descrizione, ambito
e `attivo` non sono contenuto.

---

### Codici errore

* `E_UI_PRESET_CONTENUTO_DERIVATO` — chi scrive la data del contenuto, o un'impronta che non è
  quella della composizione.
* `E_TRIGGER_ARGOMENTI_INVALIDI` — montata su una tabella che non è un preset, o non come
  `BEFORE INSERT OR UPDATE FOR EACH ROW`.

---

### Test

* `db/pgtap/ui/test-fn-resolve-lista-config-cascata-per-chiave-v1.sql` — testata del preset di lista
  riscritta uguale (nessuna chiave si sposta) e cambiata (solo la sua chiave), un cambio di
  `ordinamento_default` che non sposta nessuna chiave; la composizione
  cambiata sposta `colonne`; i due trigger sulle funzioni condivise.
* `db/pgtap/ui/test-fn-resolve-dashboard-config-cascata-per-chiave-v1.sql` — lo stesso sul preset di
  dashboard.
* `db/pgtap/ui/test-ui-nell-ambito-v1.sql` — col trigger d'audit montato, un UPDATE che non tocca il
  contenuto sposta `data_update` e non la data del contenuto; un UPDATE della misura sposta
  `data_update` e la sola chiave `pagina_dimensione`.
* `db/pgtap/ui/test-ui-forma-configurazione-v1.sql` — la data del contenuto di un preset di lista ha le
  sole chiavi `colonne` e `pagina_dimensione`.
* `db/pgtap/ui/test-fn-preset-di-base-v1.sql` — l'applicazione che scrive la data, o un'impronta
  finta, riceve `E_UI_PRESET_CONTENUTO_DERIVATO`.

---

### Note di migrazione

* 2026-11-01 — la data del contenuto nasce per la preferenza per chiave, scritta in `data_update`
  da `trgfn_preset_data_update_contenuto`.
* 2026-11-08 — prende il posto di `trgfn_preset_data_update_contenuto` e scrive la colonna nuova
  `contenuto_aggiornato_il`; `data_update` torna a essere l'audit del framework.
* 2026-11-20 — la data diventa per chiave, la scrive solo il database
  (`E_UI_PRESET_CONTENUTO_DERIVATO`), il trigger monta anche l'INSERT e non ha più il `WHEN`; la
  composizione passa dall'impronta.
* 2026-11-21 — le chiavi dei preset di lista sono `colonne` e `pagina_dimensione`: `filtri` esce con la
  colonna `filtri_default`, `ordinamento` perché la preferenza non personalizza più l'ordinamento. Le
  date già scritte hanno perso le due chiavi.

---

{% include-markdown "signature-core.md" %}
