## 📘 Documentazione Concettuale – Funzione `ui.fn_preset_aggiornato`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente) — lo snapshot di una preferenza di lista
> * [ui.dashboard_preferenza_utente](/dbzero/ui/tabelle/dashboard_preferenza_utente) — lo snapshot di una preferenza di dashboard
> * [ui.lista_preset](/dbzero/ui/tabelle/lista_preset) — la data del contenuto del preset, per chiave
>
> Approfondimento funzioni:
>
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — la legge per il banner delle liste
> * [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) — la legge per il banner delle dashboard
> * [ui.fn_preset_di_base](/dbzero/ui/funzioni/fn_preset_di_base) — sceglie la base di oggi
> * [ui.trgfn_preferenza_preset_base_snapshot](/dbzero/ui/funzioni/trgfn_preferenza_preset_base_snapshot) — scrive lo snapshot
> * [ui.trgfn_preset_contenuto_aggiornato](/dbzero/ui/funzioni/trgfn_preset_contenuto_aggiornato) — sposta la data del contenuto
>
> Guide:
>
> * [Configurazione liste](/guide/configurazione-liste) — il banner visto dall'operatore

---

### 🎯 Scopo Principale

`ui.fn_preset_aggiornato` dice per quali chiavi è acceso il banner «preset aggiornato» di una
preferenza, per le liste e per le dashboard: le chiavi che la preferenza imposta, e il cui
contenuto nel preset di base è cambiato dopo lo snapshot salvato con la preferenza.

---

### Due mappe e le chiavi da guardare

Il preset di base porta la data del suo contenuto **per chiave**: una mappa `{chiave: data}`, con
le stesse chiavi della configurazione della preferenza (`colonne` e `pagina_dimensione` per le
liste; `widget` e `dimensione_max` per le dashboard). Lo **snapshot**
della preferenza è la copia di quella mappa, presa quando l'utente ha salvato.

Il chiamante passa le due mappe e le chiavi da guardare: quelle che la preferenza imposta
(origine `preferenza`). La funzione restituisce, in ordine, le chiavi per cui il contenuto è più
recente dello snapshot. L'elenco è vuoto, mai `NULL`, quando manca lo snapshot, quando manca il
contenuto, o quando la chiave non c'è in una delle due mappe.

---

### ⭐ Una chiave che segue il preset non accende niente

Una preferenza che imposta solo la misura riceve le colonne dal preset: se le colonne del preset
cambiano, le vede già, e non c'è niente da proporle. Per questo il chiamante passa solo le
chiavi di origine `preferenza`, e la funzione non guarda le altre.

---

### Chiudere il banner è riallineare

Non c'è una data «ignorato». L'utente chiude il banner con una scrittura che nomina
`preset_base_id`, anche con lo stesso valore: il DB riscrive lo snapshot con la mappa del preset di
oggi, e il banner si spegne. Al cambio successivo del preset la chiave torna più recente dello
snapshot, e il banner si riaccende.

---

### ⭐ Si chiede solo sulla base di oggi

Il banner ha senso solo se il preset salvato con la preferenza è ancora la base dell'utente. I due
resolver lo chiedono solo in quel caso; quando la base salvata non è più quella di oggi (spenta,
cancellata, o scavalcata da un'altra) rispondono un esito diverso, `preset_base_cambiato`, e
l'elenco resta vuoto.

---

### Codici errore

Nessuno.

---

### Test

* `db/pgtap/ui/test-fn-preset-di-base-v1.sql` — senza snapshot nessuna chiave; contenuto più
  recente la chiave; una chiave che la preferenza non imposta non entra; contenuto uguale allo
  snapshot nessuna; attraverso il resolver: il banner sulla base di oggi, muto quando la base
  salvata è un'altra, chiuso dalla riscrittura di `preset_base_id` e riacceso dal cambio dopo.
* `db/pgtap/ui/test-fn-resolve-lista-config-preset-aggiornato-v1.sql` — il banner attraverso il
  resolver delle liste, con «Ignora».
* `db/pgtap/ui/test-fn-resolve-lista-config-cascata-per-chiave-v1.sql` e
  `db/pgtap/ui/test-fn-resolve-dashboard-config-cascata-per-chiave-v1.sql` — una preferenza che
  segue il preset su una chiave non vede il banner quando quella chiave cambia.

---

### Note di migrazione

* 2026-11-20 — nasce, e prende il posto dell'espressione che i due resolver scrivevano ciascuno per
  conto suo.
* 2026-11-20 — diventa per chiave: due mappe e le chiavi da guardare, risponde l'elenco delle chiavi
  in banner. L'ignorato non c'è più. STABLE, perché legge le date da testo.

---

{% include-markdown "signature-core.md" %}
