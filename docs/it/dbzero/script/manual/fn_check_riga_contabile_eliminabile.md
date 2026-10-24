## 📘 Documentazione Concettuale – Funzione `script.fn_check_riga_contabile_eliminabile()`

> 👀 **Vedi anche**
>
> **Chi la chiama:**
>
> • [pagamenti.trgfn_vendite_contabili_righe_guard_contenuto](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_contenuto) — il guard che solleva il primo motivo
> • il backend, sul dettaglio di una riga
>
> **Dove stanno i motivi:** [script.fn_check_riga_contabile_eliminabile_su_distinta](/dbzero/script/manual/fn_check_riga_contabile_eliminabile_su_distinta) — le liste chiamano quella, con la testata già letta *(dal 21-10-2026)*
>
> **Approfondimento tabelle:**
>
> • [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe)
> • [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili)
> • [pagamenti.vendite_contabili_stati](/dbzero/pagamenti/tabelle/vendite_contabili_stati)
>
> **Il modello:** [script.fn_check_ordine_annullabile](/dbzero/script/funzioni/fn_check_ordine_annullabile) · la regola: [linee-guida-sql §12.5](/linee-guida-sql)
>
> **Piano:** [brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga](/dev/work-done/brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga) §2.2 (D17), §4 P-1

---

### 🎯 Scopo Principale
(scritta il 14-09-2026, rev 30-09-2026)

Elenca i motivi, **ordinati**, che impediscono di **eliminare** una riga
contabile — cioè portarla ad `attivo = false`, oppure cancellarla. Risponde `[]`
quando si può: la riga sta in una distinta **`MANUALE` in `BOZZA`**.

È la risposta alla domanda del primo collaudo in-app (Tid, 14-09-2026): *una riga
digitata male su una bozza manuale non è un fatto — non è denaro arrivato, è un
errore di battitura — e deve potersi togliere*. «Scarta» racconta il contrario
(*denaro arrivato, non nostro*) e **conta nella quadratura**: senza
l'eliminazione, un errore di digitazione su una manuale con totale dichiarato non
aveva via d'uscita.

---

### ⭐ Una sede sola per il predicato

Il guard **non riscrive** il predicato: la **chiama** e solleva il codice del
primo motivo con `script.fn_raise_primo_motivo_se_presente`. Il backend legge lo
stesso elenco per spegnere il cestino col perché. Tooltip e rifiuto non
«coincidono oggi»: **non possono divergere**, perché la regola sta scritta in un
posto solo.

### ⭐ Lettura e giudizio in due metà *(dal 21-10-2026)*

Questa funzione **legge**: la riga e la sua testata sotto la row security, con i
due guard di chiamata. Poi **delega** i motivi a
[`fn_check_riga_contabile_eliminabile_su_distinta`](/dbzero/script/manual/fn_check_riga_contabile_eliminabile_su_distinta),
che li giudica sulla testata. Per chi la chiama non cambia niente.

⛔ **Una lista non la chiama per riga.** Ogni chiamata è un'istruzione a sé, e
ricalcolerebbe il perimetro dell'utente per ogni riga della lista
([linee-guida-sql §13.2](/linee-guida-sql)). La lista ha già letto la testata e
chiama la metà su distinta. Il guard e il dettaglio restano qui, perché hanno
bisogno della lettura e del 404.

---

### I motivi, nell'ordine in cui li nomina

L'ordine è il **contratto**: il guard solleva il primo, e lo specifico batte il
generico.

| # | `reason` | Quando | `codice` | `valori` |
| --- | --- | --- | --- | --- |
| 1a | `DISTINTA_ANNULLATA` | la testata è in uno stato con [`righe_lavorabili = false`](/dbzero/pagamenti/tabelle/vendite_contabili_stati) — oggi `ANNULLATA` — per **ogni** origine *(dal 30-09-2026)* | `E_RIGA_CONTABILE_DISTINTA_ANNULLATA` | `(codice distinta)` |
| 1b | `DISTINTA_FINALE` | **in alternativa** alla 1a: le altre finali — oggi `CHIUSA` — per **ogni** origine | **riuso** `E_RIGA_CONTABILE_DISTINTA_FINALE` | `(codice distinta, chiusa \| annullata)` |
| 2 | `DISTINTA_NON_MANUALE` | `origine <> 'MANUALE'` | `E_RIGA_CONTABILE_DISTINTA_NON_MANUALE` | `(codice distinta, arrivata da un file \| prodotta dal sistema)` |
| 3 | `DISTINTA_VALIDATA` | `MANUALE`, non finale, **non in `BOZZA`** | `E_RIGA_CONTABILE_DISTINTA_VALIDATA` | `(codice distinta)` |

> ⭐ **1a e 1b si escludono** (`ELSIF`, dal 30-09-2026). Sotto un'annullata le
> righe si leggono soltanto (D-3), e il rimedio non è quello di una chiusa (D-2).
> Un `DISTINTA_FINALE` messo dietro aggiungerebbe al `motivi` del contesto un
> secondo rimedio, e sbagliato. La domanda si fa alla bandiera di catalogo e non
> a `is_final`, perché `CHIUSA` e `ANNULLATA` sono entrambe finali e opposte per
> le righe. Brief: `brief-db-righe-distinta-annullata-fuori-dalle-code`.

Le `reason_key` sono `pagamenti.righe.elimina_reason.{distinta_annullata,
distinta_finale, distinta_non_manuale, distinta_validata}` — un **debito verso il frontend**
(§12.3): senza la voce nei locales il cestino spento ha il tooltip vuoto.

> ⚠️ **Nessun motivo «riga registrata»**, ed è voluto. Una riga `POSTATA` sta
> per costruzione sotto una distinta `CHIUSA` (la chiusura è la conseguenza del
> posting), quindi la ferma il motivo 1. Un motivo irraggiungibile insegnerebbe
> un caso che non esiste — la lezione di `STORNATA`.
>
> ⚠️ **Il motivo 3 è scritto solo per la manuale.** Su una `GENERATA` «torna in
> bozza» non è un rimedio (la riapertura è della sola manuale), e un tooltip che
> lo suggerisse manderebbe a fare un gesto destinato a fallire: lì parla il
> motivo 2, e basta. Su una `GENERATA` chiusa l'array porta **1 e 2**: il guard
> solleva il primo, il backend può mostrarli tutti.
>
> ⭐ **Un riuso, due conii.** `E_RIGA_CONTABILE_DISTINTA_FINALE` esiste già per il
> guard d'ingresso con lo stesso messaggio — *«…e quelle che ha non si lavorano
> più»* — e gli stessi due valori: è la stessa condizione da una porta in più,
> non un accumulo.

---

### ⚠️ `SECURITY INVOKER`, e legge sotto la row security

Legge la riga **e** la sua testata, che hanno entrambe la RLS del perimetro
incassi. Chi vede la riga vede la testata per la stessa catena di scope
(`fn_scope_ef_whitelist_via_contabile`), come già fa `guard_distinta_finale`.

Una riga che **non si legge** — inesistente, o di un altro — solleva
`E_RIGA_CONTABILE_NON_TROVATA` (404), con la **stessa** risposta per i due casi:
la convenzione no-leak di casa. ⛔ Rispondere `[]` sarebbe *«si può eliminare»*
detto di una cosa che non si vede — un fail-open silenzioso.

---

### Codici errore

| Codice | Classe | Quando |
| --- | --- | --- |
| `E_RIGA_CONTABILE_DISTINTA_ANNULLATA` | `CONFLITTO_STATO` | motivo 1a — lo stesso codice della quinta mossa del guard sulla distinta finale |
| `E_RIGA_CONTABILE_DISTINTA_FINALE` | `CONFLITTO_STATO` | motivo 1b — riusato |
| `E_RIGA_CONTABILE_DISTINTA_NON_MANUALE` | `CONFLITTO_STATO` | motivo 2 |
| `E_RIGA_CONTABILE_DISTINTA_VALIDATA` | `CONFLITTO_STATO` | motivo 3 — lo stesso codice della terza mossa del guard (D18) |
| `E_RIGA_CONTABILE_NON_TROVATA` | `NON_TROVATO` | la riga non si legge |
| `E_PAGAMENTI_CHIAMATA_NON_VALIDA` | `TECNICO` | `p_riga_id` nullo o `<= 0`: un chiamante rotto, non un dato dell'operatore |

---

### Il pattern `fn_check_*`

**Funzione pura**: `STABLE`, nessuna scrittura, nessun raise di dominio (salvo i
due guard di chiamata). Ritorna `[]` se l'azione è permessa, altrimenti un array
JSONB **ordinato** di `{codice, reason, reason_key, dettaglio, valori}` — chi
solleva prende il **primo**. ⛔ Il `reason` non porta il prefisso `E_`, riservato
ai codici a catalogo.

Presidio: `db/pgtap/pagamenti/test-righe-contabili-eliminazione-v1.sql`.

{% include-markdown "signature-core.md" %}
