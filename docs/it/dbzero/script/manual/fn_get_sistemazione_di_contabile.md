## 📘 Documentazione Concettuale – Funzione `script.fn_get_sistemazione_di_contabile`

### 🎯 Scopo Principale

(rev 2026-08-22)

Dice se una **distinta contabile è nata da un atto di sistemazione**, e quale: un
id, letto **fuori dalla row security**.

---

### ⭐ Perché esiste: girando il verso, la domanda si è capovolta

Prima la contabile **portava** il riferimento all'atto
(`vendite_contabili.compensazione_id`), e chiedersi *«è nata da una
compensazione?»* voleva dire guardare una colonna della riga.

Girato il verso (D15-e) quella colonna non c'è più: **lo sa l'atto**. La domanda
è diventata una lettura su **un'altra tabella** — e quell'altra tabella ha la row
security.

### 🔴 E lì c'era un varco, chiuso prima di aprirlo

Il guard che ne ha bisogno gira su `pagamenti.vendite_contabili_lotti` ed è
`SECURITY INVOKER`. Leggendo `sistemazioni` sotto RLS, per un utente fuori
perimetro l'atto **non c'è** → il guard **lascia passare**.

⚠️ E non è teorico, per una ragione che viene dal lotto 6: la contabile di una
**compensazione** è una distinta **interna** — centro dedicato, nessun canale — e
le distinte interne sono **visibili a tutti**.

> 🔴 Quindi un operatore dell'azienda B **vede** la distinta di compensazione
> dell'azienda A, e senza questa funzione potrebbe agganciarla a un proprio lotto
> di fatturazione: il guard non vedrebbe l'atto che c'è dietro, e tacerebbe.

### ⚠️ Non allarga niente

Un id su una distinta che il chiamante ha **già nominato**. Nessun importo,
nessun documento, nessun cliente: chi chiede scopre solo che quella distinta *è
impegnata* — che è esattamente ciò che gli serve sapere per non impegnarla due
volte.

### Regole principali

* `uq_sistemazioni_contabile` garantisce che la riga sia **una sola**: niente
  `ORDER BY` da scegliere, niente scommesse.
* È `STABLE`, con `search_path` bloccato.
* ⚠️ Dipende dalla RLS abilitata e **non forzata**, come le sorelle.

---

{% include-markdown "signature-core.md" %}
