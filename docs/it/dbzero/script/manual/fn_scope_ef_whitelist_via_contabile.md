## 📘 Documentazione Concettuale – Funzione `script.fn_scope_ef_whitelist_via_contabile`

### 🎯 Scopo Principale

(rev 2026-08-22, corretta il 2026-09-15)

Dice se l'operatore ha scope su una **distinta contabile**: risolve
`distinta → emittente` (dal 2026-09-15 leggendo la colonna
`emittente_soggetto_ruolo_id` della testata; fino ad allora
`distinta → canale → conto → soggetto → emittente`) e delega alla canonica.

Serve alle policy dei **satelliti** della distinta — le righe e il manifesto dei
lotti — che l'emittente non ce l'hanno in colonna: ce l'ha la loro testata.
La gemella che partiva dal canale, `fn_scope_ef_whitelist_via_ente_incasso`,
è stata ritirata il 2026-10-10 (`20261010-78`): dal 2026-09-15 nessuna policy
la chiamava più.

---

### ⭐ Su una distinta INTERNA risponde per il **suo** emittente (2026-09-15)

Le distinte **interne** — fondo fattura, sistemazione — nascono **senza canale**
per disegno: non arrivano da nessun flusso, le fabbrica il sistema. Fino al
2026-09-15 la catena per canale si interrompeva, l'emittente restava `NULL` e
la canonica rispondeva `false` a tutti — *«le righe di una distinta interna non
devono vedersi in giro, e a dire di chi è quel denaro è la fattura che la riga
porta»*. Nel frattempo la **testata** era visibile a tutti per una scelta scritta
nella policy (`ente_incasso_id IS NULL`).

Dal brief
[distinta-numerata-sul-registro](/dev/work-done/brief-db-distinta-numerata-sul-registro)
**la distinta sa di chi è**: porta l'emittente in colonna (risolto alla nascita
in una sede sola — dato, canale, operatore in sessione, o rifiuto — e per una
distinta di fondi è l'emittente del **lotto**, per una sistemazione quello
dell'**atto**). Quindi qui una distinta interna risponde `true` per il suo
emittente e `false` per gli altri, e le sue righe si vedono dalla **sola
testata**, senza passare dalla fattura. Il ramo «senza canale = di tutti» è
sparito dalla testata (`20260915-31`) e dai satelliti (`20260915-32`).

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
