## 📘 Documentazione Concettuale – Funzione `pratiche.fn_log_evento_dominio`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — il giornale su cui scrive
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la pratica a cui l'evento appartiene
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_sospensioni_giornale_ins](/dbzero/pratiche/funzioni/trgfn_sospensioni_giornale_ins) — un trigger di giornale che distingue esplicitamente il livello pratica e flusso

---

### 🎯 Scopo Principale

`pratiche.fn_log_evento_dominio` è il canale controllato con cui gli handler applicativi scrivono un
evento di dominio (`DOMINIO_*`) sul giornale della pratica, per esempio `DOMINIO_COMMESSA_CREATA` o
`DOMINIO_PREVENTIVO_EVASO` scritti dal push del preventivo. Restituisce l'id della riga inserita.

Esiste perché gli handler non scrivano direttamente su `pratiche.giornale`: qui i parametri sono
validati, l'origine è fissata a `HANDLER` e la riga porta il `tx_id` della sessione, così l'evento resta
correlabile alla transazione che l'ha prodotto. Il tipo di evento diventa l'azione del giornale, i
metadati il suo dettaglio (un oggetto vuoto se mancano).

---

### ⭐ La forma del nome la garantisce la tabella, non la funzione

La funzione **non verifica** che il tipo di evento abbia la forma `DOMINIO_*`. Lo fa il vincolo
sull'azione del giornale, che ammette gli eventi del motore oppure un codice `DOMINIO_` seguito da
maiuscole, cifre e trattini bassi.

È una scelta: la regola vive sul dato, e vale anche per chi scrivesse sul giornale per un'altra strada.

⚠️ La conseguenza per il chiamante: un nome non conforme non produce un errore di dominio ma una
violazione di `CHECK` (SQLSTATE `23514`), senza codice `E_*` e senza riga nel registro degli errori. Il
messaggio parla di un vincolo, non di un evento sbagliato.

---

### Il flusso è opzionale, e il vuoto significa qualcosa

Un evento può essere della pratica (flusso vuoto) o di una fase (flusso valorizzato): il vuoto è ammesso,
un valore non positivo no.

È lo stesso asse che i trigger delle sospensioni rendono esplicito nel dettaglio col campo `livello`
(`PRATICA` / `FLUSSO`). ⚠️ Qui quel campo non si aggiunge: chi legge il giornale distingue i due livelli
solo dalla presenza di `flusso_id`.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — pratica assente o non positiva; flusso valorizzato ma non positivo; tipo di
  evento assente o vuoto. I tre casi hanno lo stesso codice: quale parametro fosse sbagliato lo dice il
  contesto dell'errore.

---

### Test

* `pratiche/test-fn-log-evento-dominio` — la riga scritta (azione, origine, dettaglio, `tx_id`), l'evento
  a livello di pratica, i nomi non conformi rifiutati dal vincolo, il controllo sui parametri.

---

### Note di migrazione

* 2026-06-08 — nasce insieme agli eventi `DOMINIO_*` del giornale.

---

{% include-markdown "signature-core.md" %}
