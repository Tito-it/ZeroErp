## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_preferenza_guard_forma`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente) — una delle due tabelle su cui è montato
> * [ui.dashboard_preferenza_utente](/dbzero/ui/tabelle/dashboard_preferenza_utente) — l'altra
> * [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina) — il catalogo della misura di pagina
>
> Approfondimento funzioni:
>
> * [ui.fn_check_forma_configurazione](/dbzero/ui/funzioni/fn_check_forma_configurazione) — la regola di forma
> * [ui.fn_guard_misura_pagina](/dbzero/ui/funzioni/fn_guard_misura_pagina) — la misura di pagina delle liste
> * [ui.trgfn_preferenza_preset_base_snapshot](/dbzero/ui/funzioni/trgfn_preferenza_preset_base_snapshot) — l'altro trigger delle preferenze, che scrive lo snapshot
>
> Guide:
>
> * [Configurazione liste](/guide/configurazione-liste) — che cosa si salva nella preferenza

---

### 🎯 Scopo Principale

`ui.trgfn_preferenza_guard_forma` fa sì che la configurazione di una preferenza, di una lista o di una
dashboard, abbia la forma ammessa, e sulle liste che la misura «righe per pagina» sia del catalogo.
Rifiuta la scrittura che non la rispetta.

---

### Un guard per le due preferenze

La stessa funzione è montata sulle due tabelle delle preferenze, e la famiglia la dice la tabella. La
regola non sta qui: la chiede a
[fn_check_forma_configurazione](/dbzero/ui/funzioni/fn_check_forma_configurazione), che risponde il
primo motivo, e qui il motivo diventa il rifiuto, con la chiave e la frase nel messaggio. Sulle liste,
se la forma è buona, la misura di pagina la giudica poi
[fn_guard_misura_pagina](/dbzero/ui/funzioni/fn_guard_misura_pagina), col suo codice.

Sulle liste prende il posto del guard della sola misura: la misura è una delle regole della forma.

---

### ⭐ Un salvataggio che non cambia la configurazione passa

Il guard giudica la nascita della preferenza e ogni modifica che cambia la configurazione, o la lista
(la dashboard) della riga. Una scrittura che riscrive la configurazione uguale passa senza giudizio:
chiudere il banner «preset aggiornato», o riallineare la preferenza al preset di base, riscrive la riga
nominando la base, e una configurazione salvata prima del guard non deve bloccare l'utente proprio
mentre chiude il banner.

Le righe che esistevano quando il guard è nato sono state portate in forma nello stesso momento: il
guard non ne trova di sbagliate al primo salvataggio.

---

### ⚠️ Che cosa oggi non copre

* **Una misura uscita dal catalogo blocca la modifica.** Il catalogo delle misure non sa delle
  preferenze: una misura citata solo da preferenze si toglie senza rifiuto. Da quel momento ogni
  modifica della configurazione che conservi quella misura è rifiutata, anche se tocca soltanto le
  colonne; la lettura, invece, scarta la misura e risponde lo standard. Il client evita il caso
  rimandando la misura solo quando la lettura la dice scelta dall'utente.

---

### Codici errore

* `E_UI_CONFIGURAZIONE_FORMA` — la configurazione non ha la forma ammessa; nel messaggio la chiave e il
  motivo.
* `E_UI_MISURA_PAGINA_NON_AMMESSA` — sulle liste, la misura di pagina non è del catalogo (da
  `fn_guard_misura_pagina`).
* `E_TRIGGER_ARGOMENTI_INVALIDI` — montata su un'altra tabella, o non prima della scrittura di ogni riga.

---

### Test

* `db/pgtap/ui/test-ui-forma-configurazione-v1.sql` — un rifiuto per ogni forma sbagliata, sulle due
  famiglie; la misura fuori catalogo rifiutata col codice della misura; un UPDATE che non cambia la
  configurazione su una riga malformata che passa, e uno che la cambia che è giudicato; il guard montato
  sulle due preferenze e quello della sola misura non più montato.

---

### Note di migrazione

* 2026-11-21 — nasce, e prende il posto di `ui.trgfn_ui_lista_preferenza_utente_guard_pagina_dimensione`,
  che giudicava solo la misura di pagina delle liste. Sulle dashboard prima non c'era nessun guard: la
  forma la controllava solo il backend.

---

{% include-markdown "signature-core.md" %}
