## 📘 Documentazione Concettuale – Funzione `vendite.fn_genera_pratica_da_preventivo`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.preventivi](/dbzero/vendite/tabelle/preventivi) — il preventivo da cui nasce la pratica
> * [pratiche.pratiche_sorgenti](/dbzero/pratiche/tabelle/pratiche_sorgenti) — il link `ROOT` preventivo → pratica
>
> Approfondimento funzioni:
>
> * [pratiche.fn_crea_pratica](/dbzero/pratiche/funzioni/fn_crea_pratica) — la figlia condivisa che crea la pratica
> * [anagrafiche.fn_get_emittente_fiscale_pk](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_pk) — l'emittente dal billing account
> * [script.fn_sorgente_provenienza](/dbzero/script/funzioni/fn_sorgente_provenienza) — la provenienza del link, dal tipo e dalla chiave del preventivo
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

La funzione **`vendite.fn_genera_pratica_da_preventivo`** è la **funzione madre
atomica** che genera una pratica a partire da un preventivo e la collega come
`ROOT` in `pratiche.pratiche_sorgenti`.

Risoluzione del contesto, creazione della pratica e link sono un'unica statement: con creazione
e link in transazioni separate, un link fallito lascerebbe una **pratica orfana**, mai collegata
al preventivo.

**Composizione:** la creazione pratica è delegata alla figlia condivisa
[`pratiche.fn_crea_pratica`](/dbzero/pratiche/funzioni/fn_crea_pratica); questa
madre fa solo la parte specifica del dominio preventivo (risolve
emittente e soggetto dal preventivo e inserisce il link).

---

### Flusso

1. Legge il contesto dal preventivo (billing account, istanza). Preventivo inesistente ⇒
   **`E_PREV_NOT_FOUND`**.
2. Risolve emittente (`fn_get_emittente_fiscale_pk`), soggetto e ruolo dal BA.
3. Calcola la provenienza del link con `script.fn_sorgente_provenienza`: il tipo `PREVENTIVO` e
   la chiave del preventivo nella colonna del suo `key_selector` (`sorgente_uid`). Lo fa **prima**
   di creare la pratica: un tipo assente o spento ferma tutto subito (`E_SORG_CONF`, da
   `script.fn_sorgente_chiave`).
4. Crea la pratica via `pratiche.fn_crea_pratica`, col billing account del preventivo.
5. Inserisce il link `ROOT` preventivo → pratica in `pratiche_sorgenti`, che il guard unico
   `script.trgfn_guard_sorgente` verifica.

---

### Note tecniche

* **`SECURITY INVOKER`**: RLS/scope valutati come dal Python.
* Il link `ROOT` ha `flusso_id` NULL (la decisione D-B sul `flusso_id` riguarda i
  link `COLLEGATO`, non il `ROOT`).
* Il check di dominio «preventivo in stato ACCETTATO» resta un pre-check
  (read-only) del service: non attiene all'atomicità (la causa del finding).


---

### Note di migrazione

* 2026-07-08 — nasce la madre atomica: il service Python creava la pratica e il link in
  transazioni separate, e un link fallito lasciava la pratica orfana (analisi fix transazioni
  backend, Classe A, finding #3).
* 2026-10-08 — la pratica nasce col **billing account del preventivo**: la sorgente dice di quale
  cliente parla la pratica. Tolto il ramo «preventivo senza BA» (`E_PREV_VALIDAZIONE`), non più
  raggiungibile (brief-db-istanza-nasce-col-ba, R-8, D-9).
* 2026-11-08 — il link nasce con la provenienza tipizzata del modello, calcolata da
  `script.fn_sorgente_provenienza`, al posto dell'uid del preventivo in testo e del tipo letto da
  `config.sorgenti` (che sollevava `E_CONFIG_MANCANTE`) (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
