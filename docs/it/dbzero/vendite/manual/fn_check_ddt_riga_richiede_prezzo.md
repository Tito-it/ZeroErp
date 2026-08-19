## 📘 Documentazione Concettuale – Funzione `vendite.fn_check_ddt_riga_richiede_prezzo`

> 👀 **Vedi anche**
>
**Chi la consuma:**
>
• [vendite.ddt_righe_componenti](/dbzero/vendite/tabelle/ddt_righe_componenti) — clausola `WHEN` del trigger sul prezzo zero
> • [vendite.fn_ddt_riga_componenti_init](/dbzero/vendite/funzioni/fn_ddt_riga_componenti_init)
>
**Dove vive la dichiarazione d'intento:**
>
• [config.causali_trasporto](/dbzero/config/tabelle/causali_trasporto)

### 🎯 Scopo Principale

(creata 2026-08-19 — brief-ddt-righe-senza-prezzo §9 slice C)

**Risponde a una domanda sola: «la riga di DDT che sto per toccare appartiene a
un documento che vende?»** Cioè: il suo DDT ha una causale di trasporto
fatturabile.

Serve a decidere se pretendere un prezzo. Un componente obbligatorio a prezzo
zero è un difetto su una vendita, e non significa niente su un conto visione:
questa funzione è ciò che distingue i due casi senza doverlo spiegare a ogni
punto del codice che se lo chiede.

### Le risposte, comprese le due non ovvie

| situazione | risposta | perché |
|---|---|---|
| causale **fatturabile** | `TRUE` | il documento vende: il prezzo serve |
| causale **non fatturabile** | `FALSE` | il documento non vende: il prezzo non ha oggetto |
| causale **assente** (bozza) | `FALSE` | in bozza il NULL è legittimo, e non si inventa un intento che l'operatore non ha ancora dichiarato. Presidia il gate all'emissione |
| riga **non leggibile** | `TRUE` | ⚠️ fail-closed, vedi sotto |

### ⚠️ Il fail-closed, e perché non è prudenza generica

La funzione gira dentro un trigger, quindi **sotto RLS**: una lettura che non
trova la riga non distingue «non esiste» da «non la vedo». Nel dubbio risponde
`TRUE`, cioè tiene il comportamento severo.

Dei due errori possibili, uno costa una richiesta di prezzo dove non serviva;
l'altro lascia passare uno zero su un documento che vende, e **quello arriva in
fattura**. Non sono equivalenti.

> ⛔ **Si guarda `FOUND`, non una variabile-sentinella.** La prima stesura usava
> `SELECT ct.fatturabile, TRUE INTO v_fatturabile, v_trovata` con `v_trovata`
> inizializzata a `FALSE`, e **non funzionava**: `SELECT INTO` senza righe non
> lascia le variabili come stanno, le **azzera**. `v_trovata` diventava `NULL`,
> `NOT NULL` non è vero, il ramo non scattava e la funzione rispondeva `FALSE` —
> l'esatto contrario del fail-closed. Trovato dal test sull'id inesistente.

### Regole

- **Pura** (convenzione `fn_check_*`): non solleva, non scrive, `STABLE`.
  Un parametro nullo o non positivo non è un errore: è una risposta `TRUE`.
- **Non è `SECURITY DEFINER`**, e non deve diventarlo: il fail-closed rende
  inutile scavalcare la RLS, che porterebbe con sé owner e GRANT da governare.

### ⭐ Perché esiste come funzione a sé

Il divieto del prezzo zero sui componenti obbligatori vive in
`script.trgfn_componenti_check_prezzo_obbligatorio`, **condivisa da quattro
tabelle** (preventivi, ordini, contratti, DDT). Parametrizzarla avrebbe voluto
dire portarle dentro la nozione di «causale di trasporto», che esiste solo per i
DDT: insegnare a un oggetto generico un fatto di un dominio solo, e rischiare su
tre tabelle per servirne una.

Con questa funzione in una clausola `WHEN`, il codice condiviso **non si tocca**:
cambia solo *quando* il trigger viene invocato — che è esattamente il mestiere
della `WHEN`.
