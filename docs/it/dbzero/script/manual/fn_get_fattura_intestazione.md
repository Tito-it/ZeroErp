## 📘 Documentazione Concettuale – Funzione `script.fn_get_fattura_intestazione`

### 🎯 Scopo Principale

(rev 2026-08-22)

Risponde a **una** domanda di fatto — *«di chi è e a chi è questa fattura?»* —
**fuori dalla row security**, e risponde con **due soggetti**: l'emittente e il
cliente. Nient'altro.

---

### 🔴 La lezione che applica

`vendite.fatture` ha la RLS. Un guard è `SECURITY INVOKER`, e leggendola
direttamente:

> ⚠️ **non distingue *«è di un altro cliente»* da *«non lo vedo»***, e giudica su
> un `NULL`. A seconda di come è scritto il confronto, o rifiuta nominando la
> causa sbagliata, o **lascia passare**.

Un guard che confrontasse i clienti di due fatture leggendole da sé direbbe *«non
sono dello stesso cliente»* **anche quando lo sono** — perché una delle due non
si vede.

⭐ **Chi risolve non è chi applica.** Che poi l'utente possa scrivere su quei
documenti lo decide il guard di scope, che è un'altra cosa e ha un'altra risposta.

### ⚠️ Non allarga nessun perimetro

Risponde **due id** su una fattura che il chiamante ha **già nominato**: nessuna
riga esce, nessun elenco si popola, nessun dato del documento viene raccontato. E
due id da soli non dicono niente di usabile — non un numero, non un importo, non
un nome.

### Regole principali

* Nessuna riga se la fattura non esiste: chi chiama decide che farne, ed è
  l'unico che sa quale messaggio dare.
* È `STABLE`.
* `SET search_path TO 'pg_catalog', 'pg_temp'`: una `SECURITY DEFINER` senza
  search_path fisso è un'iniezione che aspetta.
* ⚠️ **Dipende dal fatto che la RLS sia abilitata e NON forzata** (il proprietario
  la salta). Con un `FORCE ROW LEVEL SECURITY` va rivista, come
  `fn_resolve_emittente_fiscale_id` e `fn_check_scadenza_di_fattura`.

### Chi la usa

`pagamenti.trgfn_sistemazioni_guard_dati`, per entrambe le fatture dell'atto.

---

{% include-markdown "signature-core.md" %}
