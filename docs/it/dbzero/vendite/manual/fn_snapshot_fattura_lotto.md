## 📘 Documentazione Concettuale – Funzione `vendite.fn_snapshot_fattura_lotto`

> 👀 **Vedi anche**
>
> **Tabelle:**
>
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti) · [vendite.fatture_log](/dbzero/vendite/tabelle/fatture_log)
> • [vendite.fatture_indirizzi](/dbzero/vendite/tabelle/fatture_indirizzi)
>
> **Funzioni:**
>
> • [vendite.fn_snapshot_indirizzi_fattura](/dbzero/vendite/funzioni/fn_snapshot_indirizzi_fattura) · [vendite.fn_snapshot_intestazione_fattura](/dbzero/vendite/funzioni/fn_snapshot_intestazione_fattura) — le due sorelle invocate
> • [vendite.fn_genera_scadenze_lotto](/dbzero/vendite/funzioni/fn_genera_scadenze_lotto) — costruito su questo **modello**

---
### 🎯 Scopo Principale
(latest review 02-08-2026)

`vendite.fn_snapshot_fattura_lotto` applica a **tutte le fatture di un lotto** il
congelamento dei satelliti: indirizzi **e** intestazione fiscale. È il task
`snapshot_indirizzi_lotto` dello step **DRAFT**.

---

### 📛 Il nome è cambiato, il `task_code` no

Si chiamava `fn_snapshot_indirizzi_lotto`. Quando ha iniziato a scrivere anche
l'intestazione, quel nome ne diceva **metà** ed è stato corretto.

⚠️ Il **`task_code` resta `snapshot_indirizzi_lotto`**: è il nome del *passo*,
vive nei CSV di seed, nelle policy e nel registry. Nome della funzione e identità
del task sono due cose diverse, e confonderle costa una migration di dati.

---

### 🔴 Filtrare su `meta->>'task'`, mai su `source`

Il ritiro delle segnalazioni critiche filtra sul **`task_code`**, non sul nome
della funzione.

Il motivo è appena successo: il `source` è il nome della funzione, e le funzioni
si rinominano. Con il filtro sul nome, dopo ogni rinomina il task non
riconoscerebbe più le proprie bandiere e **smetterebbe di abbassarle** — senza
errori, senza segnali, solo fatture che restano marcate per sempre.

Il `task_code` è l'identità **stabile** del passo.

---

### Filtra prima di scrivere

Per le fatture oltre EMESSA il wrapper **non chiama nemmeno** la per-fattura: il
loro snapshot è stato preso in DRAFT ed è quello definitivo.

⚠️ «Salta» non è «lascia indietro». Una fattura definitiva **non ha lavoro da
fare**: il giro non si ferma e non è fallito, le altre ricevono il loro lavoro
completo, lo step si chiude normalmente e la traccia è un log **non critico**. Un
`critical` bloccherebbe l'avanzamento del runner — cioè proprio il blocco che si
vuole evitare.

> Il modello `fn_ricalcola_riepiloghi_iva_lotto` **non** filtra. Qui si devia, e
> la deviazione è voluta.

---

### Il fallimento di una non uccide il giro

Sotto-blocco `BEGIN/EXCEPTION` per fattura, marcatura `'C'` su `fatture_log`, le
altre proseguono: i clienti incompleti si vedono **tutti in una volta** invece di
uno per esecuzione.

Si cattura `raise_exception` (P0001), **non** `others`: un guasto di sistema deve
continuare a salire.

---

### Sei contatori

Il sesto, `intestazioni_scritte`, è nato con la funzione sorella. I contatori si
selezionano **per nome**: aggiungerne uno non rompe i consumatori esistenti, che
semplicemente non lo leggono finché non vogliono.

---
{% include-markdown "signature-core.md" %}
