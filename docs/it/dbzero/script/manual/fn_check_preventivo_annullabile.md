## 📘 Documentazione Concettuale – Funzione `script.fn_check_preventivo_annullabile()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> • [vendite.ordini](/dbzero/vendite/tabelle/ordini)
> • [vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti)
>
Approfondimento funzioni:
> • [vendite.trgfn_preventivi_guard_annullamento](/dbzero/vendite/funzioni/trgfn_preventivi_guard_annullamento)
> • [script.fn_check_ordine_annullabile](/dbzero/script/funzioni/fn_check_ordine_annullabile)

---
### 🎯 Scopo Principale

(rev 2026-08-21 — funzione rev 2026-08-10)

Elenca i motivi che impediscono di **annullare** un preventivo: un ordine già nato da esso
(MOTIVO 1), oppure righe già **emesse** in commessa (MOTIVO 2).

Dal 2026-08-04 il MOTIVO 2 è stato **assorbito dalla porta** `fn_cambia_stato_preventivo`, che
prima lo teneva per sé: da allora la porta non ha più una regola propria, chiama questa.

---

### 🔴 Il MOTIVO 1 non è mai scattato per tre changeSet — e la ragione insegna

Cercava l'ordine figlio su `ordini.sorgente_uid`. Quella colonna **non è il legame al
documento a monte**: è l'origine **import**, e risultava valorizzata su **0 righe su 90**. Il
legame vero è la coppia `(documento_origine_tipo, documento_origine_id)` — 66 su 90.

⚠️ **Perché l'errore era invisibile**: era stato scritto per simmetria col gemello sui DDT,
dove la colonna *omonima* `sorgente_uid` **è** davvero il legame al padre **ed è** popolata. La
stessa parola per due cose diverse.

È la trappola §4a di `docs/it/guide/sorgente-polimorfa.md`: colonne che **sembrano** polimorfe
e non lo sono. `vendite.ordini` non ha il guard di sorgente polimorfa, quindi non è
consumatrice di quel meccanismo — e nulla lo segnalava.

⭐ Un guard che non scatta mai è **indistinguibile da un guard che funziona**, finché non si
misura la popolazione delle colonne su cui poggia. Nessun test era rosso.

---

### ⚠️ I figli annullati non bloccano

Il conteggio esclude gli ordini figli con `is_abortito` — altrimenti **un documento morto
bloccherebbe il padre per sempre**, senza via d'uscita.

Decisione di Tid del 2026-08-10: **qualunque altro stato blocca, bozza compresa**. La via
d'uscita per un ordine in bozza è abbandonare prima quello.

Il predicato usa `is_abortito` e non `codice_interno = 'ANNULLATO'`: è l'asse uniforme
cross-catalogo, e non si rompe se un dominio chiama diversamente il proprio stato terminale.

---

### Codici errore

| Codice | Motivo |
|--------|--------|
| `E_PREV_ORDINE_GIA_GENERATO` | Esiste un ordine figlio vivo |
| *(codice del MOTIVO 2)* | Righe già emesse in commessa |
| `E_PARAMETRO_INVALIDO` | `preventivo_id` nullo o non positivo |

---

### Il pattern `fn_check_*`

**Funzione pura**: `STABLE`, nessuna scrittura, nessun raise di dominio. Ritorna `[]` se
l'azione è permessa, altrimenti un array JSONB ordinato di
`{codice, reason, reason_key, dettaglio}` — l'ordine è quello di gravità, chi solleva prende
il **primo**.

⭐ **Sorgente unica** per il guard di transizione (che solleva) e per
`fn_available_actions_*` (che espone `disabled` + `reasons`): il bottone della UI e il rifiuto
del database non possono divergere, perché leggono lo stesso verdetto.

⚠️ Unica eccezione alla purezza: `id` nullo o `<= 0` solleva `E_PARAMETRO_INVALIDO` — errore
di programmazione, non condizione di dominio.

⚠️ **Documento inesistente ⇒ `[]`, cioè «nessun ostacolo».** La funzione non distingue
«annullabile» da «non esiste»: la decisione è lasciata al chiamante. Nel percorso reale il
guard gira su un `UPDATE` di una riga che esiste per definizione, quindi il caso non si
presenta — ma chi la chiamasse da fuori quel percorso deve saperlo.

---

{% include-markdown "signature-core.md" %}
