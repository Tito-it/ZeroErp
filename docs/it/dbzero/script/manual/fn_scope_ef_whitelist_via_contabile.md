## 📘 Documentazione Concettuale – Funzione `script.fn_scope_ef_whitelist_via_contabile`

### 🎯 Scopo Principale

(rev 2026-08-22)

Dice se l'operatore ha scope su una **distinta contabile**: risolve
`distinta → canale → conto → soggetto → emittente` e delega alla canonica.

Serve alla policy della **riga** contabile, che il canale non ce l'ha in colonna:
ce l'ha la sua testata. Gemella di
[fn_scope_ef_whitelist_via_ente_incasso](/dbzero/script/funzioni/fn_scope_ef_whitelist_via_ente_incasso),
che parte invece dal canale.

---

### ⚠️ Su una distinta INTERNA risponde `false`, ed è voluto

Le distinte **interne** — fondo fattura, compensazione — nascono **senza canale**
per disegno: non arrivano da nessun flusso, le fabbrica il sistema. La catena si
interrompe, l'emittente resta `NULL`, la canonica risponde `false`.

⭐ Ed è esattamente ciò che serve: **le righe di una distinta interna non devono
vedersi in giro**, e a dire di chi è quel denaro è la **fattura che la riga
porta**.

> ⚠️ Che la **testata** di quella distinta sia invece visibile a tutti è una
> decisione **diversa**, e sta scritta **nella policy** — `ente_incasso_id IS
> NULL`, in chiaro — non qui dentro. Chi legge la policy deve vedere l'eccezione,
> non scoprirla dentro una funzione.

---

### 🔴 Perché è `SECURITY INVOKER` e non `DEFINER` — e perché funziona lo stesso

Legge `pagamenti.vendite_contabili`, **la cui policy chiama questa funzione**. Da
sola sarebbe una **ricorsione infinita**: policy → funzione → lettura → policy.

Non lo è perché **non legge da sé**: delega a
[fn_resolve_emittente_fiscale_id](/dbzero/script/funzioni/fn_resolve_emittente_fiscale_id),
che è `SECURITY DEFINER` e gira come proprietario — e il proprietario salta la
row security finché non c'è il `FORCE`.

⚠️ Ne segue la dipendenza da conoscere: **con un `FORCE ROW LEVEL SECURITY` la
ricorsione tornerebbe**. È il motivo per cui il pgTAP del perimetro incassi non
usa il `FORCE` locale alla transazione — la tecnica dei test RLS più vecchi — e
gira invece come utente applicativo, che è anche più fedele.

---

### Regole principali

* Un `p_contabile_id` nullo → `false` (fail-closed).
* È `STABLE`.

### Chi la usa

La policy `rls_vendite_contabili_righe_perimetro_incasso` su
[vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe),
come **prima** delle sue tre strade.

{% include-markdown "signature-core.md" %}
