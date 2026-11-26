## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_check_ba_padre`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il conto, il suo padre (`parent_account_id`) e i suoi figli
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) e [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — da dove si legge chi è il cliente di un conto
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_billing_account_guard_normalize](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_normalize) — il chiamante: solleva il primo motivo quando il padre nasce o cambia
> * [script.fn_get_ba_emittente_sr_id_installazione](/dbzero/script/funzioni/fn_get_ba_emittente_sr_id_installazione) — l'azienda di ciascun conto, per l'installazione
> * [script.fn_raise_primo_motivo_se_presente](/dbzero/script/funzioni/fn_raise_primo_motivo_se_presente) — chi trasforma il primo motivo in rifiuto
>
> Guide:
>
> * [Generazione cliente](/guide/generazione-cliente) — il billing account e il suo albero

---

### 🎯 Scopo Principale

`anagrafiche.fn_check_ba_padre` dice perché un billing account non può prendere il padre proposto. Restituisce
l'elenco dei motivi, vuoto quando il padre va bene o non c'è; non rifiuta da sola: il rifiuto lo dà
`anagrafiche.trgfn_billing_account_guard_normalize`, che solleva il primo motivo.

---

### ⭐ L'albero dei billing account ha un livello solo

Un conto padre raccoglie la fatturazione dei suoi figli: la fattura va al **padre diretto**, e il motore di
fatturazione legge un livello solo. Un padre che avesse a sua volta un padre renderebbe ambiguo chi riceve la
fattura. Le regole sono due, e insieme rendono impossibili anche i cicli, perché in un ciclo ogni conto
sarebbe padre e figlio insieme:

* chi ha un padre non fa da padre: il padre proposto ha già un padre (`E_PARENT_CON_PADRE`);
* chi fa da padre non prende un padre: il conto ha già dei figli (`E_PARENT_HA_FIGLI`).

Nessun flag dice «questo conto è un padre»: lo dice `parent_account_id` dei figli. Un flag sarebbe una seconda
verità, che prima o poi direbbe una cosa diversa dalla prima.

---

### Un cliente ha un solo padre per azienda

Un cliente, cioè la stessa identità fiscale o, senza, lo stesso soggetto, ha un solo conto padre per ogni
azienda: è quello che raccoglie la fatturazione di tutti i suoi conti presso quell'azienda. Se il cliente ha
già un altro conto che fa da padre sulla stessa azienda del padre proposto, la risposta è
`E_PARENT_SECONDO_PADRE`, e la frase nomina il padre che c'è già. Su un'altra azienda il cliente può avere un
altro padre: sono due fatturazioni diverse.

«Stesso cliente» è la stessa regola del guard del padre (identità fiscale, o soggetto). L'azienda si chiede
**per l'installazione** (`script.fn_get_ba_emittente_sr_id_installazione`): «un padre per azienda» non
dipende da chi sta lavorando. Ogni billing account ha sempre il suo collegamento a un'azienda, e la risposta è
quella del collegamento.

---

### Il conto che cambia entra per parametri

La check gira dentro un trigger che scatta **prima** della scrittura: la tabella ha ancora la riga di prima.
Per questo il conto che cambia entra come parametri (il suo id, il suo codice per la frase, il padre
proposto), e fra i figli dell'altro padre si esclude il conto stesso, che può esserne il figlio di oggi e
stare solo cambiando padre.

Si chiama solo quando il padre nasce o cambia: un aggiornamento di altre colonne non rilegge l'albero.

---

### ⭐ Perché è privilegiata

Legge il padre del padre, i figli del conto e gli altri padri del cliente: righe che il perimetro di chi
scrive può nascondere. Con i permessi di chi scrive, un padre di un'altra azienda sarebbe invisibile e la
risposta direbbe «a posto» proprio nel caso da rifiutare. Gira quindi coi privilegi del proprietario, e
risponde solo i codici dei billing account, niente di più.

---

### Che cosa non fa

* Non giudica che il padre sia lo stesso conto, che esista, che sia raggiungibile e dello stesso cliente:
  sono le altre regole di `anagrafiche.trgfn_billing_account_guard_normalize`.
* Non giudica il cambio o lo stacco del padre con attività non fatturate
  (`E_DISSOCIAZIONE_PARENT_CON_ATTIVITA`): lo fa il guard, perché riguarda le fatture del figlio, non la
  forma dell'albero.
* Non giudica che padre e figlio siano sulla stessa azienda: lo fa `anagrafiche.fn_guard_albero_ba_emittente`.

---

### Codici errore

| Codice | Quando |
| --- | --- |
| `E_PARENT_CON_PADRE` | il padre proposto ha già un padre |
| `E_PARENT_HA_FIGLI` | il conto fa già da padre e prende un padre (anche il ciclo) |
| `E_PARENT_SECONDO_PADRE` | il cliente ha già un altro conto padre sulla stessa azienda |

Sono motivi restituiti, non sollevati: li solleva il chiamante.

---

### Test

* `db/pgtap/anagrafiche/test-billing-account-albero-un-livello-v1.sql` — il padre di un padre, il padre che
  prende un padre, il ciclo, il secondo padre dello stesso cliente sulla stessa azienda, il cambio di padre
  con attività non fatturate rifiutato come lo stacco.

---

### Note di migrazione

* 2026-11-26 — nasce: l'albero dei billing account passa da «senza limite di livelli» a un livello solo, con
  un padre per cliente e per azienda.

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

---

{% include-markdown "signature-core.md" %}
