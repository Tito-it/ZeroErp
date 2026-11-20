## 📘 Documentazione Concettuale – Funzione `ui.fn_preset_aggiornato`

> **Ultimo aggiornamento**: 20 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente) — lo snapshot e l'«ignora» di una preferenza di lista
> * [ui.dashboard_preferenza_utente](/dbzero/ui/tabelle/dashboard_preferenza_utente) — lo snapshot e l'«ignora» di una preferenza di dashboard
> * [ui.lista_preset](/dbzero/ui/tabelle/lista_preset) — la data del contenuto del preset
>
> Approfondimento funzioni:
>
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — la legge per il banner delle liste
> * [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) — la legge per il banner delle dashboard
> * [ui.fn_preset_di_base](/dbzero/ui/funzioni/fn_preset_di_base) — sceglie la base di oggi
> * [ui.trgfn_preferenza_preset_base_snapshot](/dbzero/ui/funzioni/trgfn_preferenza_preset_base_snapshot) — scrive lo snapshot
>
> Guide:
>
> * [Configurazione liste](/guide/configurazione-liste) — il banner visto dall'operatore

---

### 🎯 Scopo Principale

`ui.fn_preset_aggiornato` dice se il banner «preset aggiornato» di una preferenza è acceso, per le
liste e per le dashboard: vero quando il contenuto del preset di base è cambiato dopo lo snapshot salvato
con la preferenza, e l'utente non ha chiuso il banner dopo quel cambio.

---

### Tre date, un esito

La funzione confronta tre date: lo **snapshot** (la data del contenuto salvata con la preferenza),
il **contenuto** del preset di base oggi, e l'**ignorato** (quando l'utente ha chiuso il banner).
Il banner si accende se il contenuto è più recente dello snapshot e l'ignorato manca o viene prima
del cambio. Senza snapshot o senza contenuto il banner è spento: la risposta non è mai vuota.

Non legge tabelle: le tre date gliele passa il chiamante, che le ha già lette. Per questo è
immutabile, e la stessa domanda dà sempre la stessa risposta.

---

### ⭐ Si chiede solo sulla base di oggi

Il flag ha senso solo se il preset salvato con la preferenza è ancora la base dell'utente. I due
resolver lo chiedono solo in quel caso; quando la base salvata non è più quella di oggi (spenta,
cancellata, o scavalcata da un'altra) rispondono un esito diverso, `preset_base_cambiato`, e il
flag resta spento.

---

### ⚠️ Che cosa oggi non copre

* **Il flag è per preset intero.** La data del contenuto è una per tutto il preset: una preferenza
  di sola misura vede il banner quando il preset cambia l'ordinamento, che le arriva già.

---

### Codici errore

Nessuno.

---

### Test

* `db/pgtap/ui/test-fn-preset-di-base-v1.sql` — senza snapshot spento; contenuto più recente acceso;
  chiuso dopo il cambio spento; contenuto uguale allo snapshot spento; nei resolver, il flag acceso
  sulla base di oggi e muto quando la base salvata è un'altra.
* `db/pgtap/ui/test-fn-resolve-lista-config-preset-aggiornato-v1.sql` — il flag attraverso il
  resolver delle liste, con l'«ignora».

---

### Note di migrazione

* 2026-11-20 — nasce, e prende il posto dell'espressione che i due resolver scrivevano ciascuno per
  conto suo.

---

{% include-markdown "signature-core.md" %}
