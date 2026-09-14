## 📘 Documentazione Concettuale – Funzione `vendite.fn_cancella_fondo_fattura`

> 👀 **Vedi anche**
>
> **Il criterio, che sta altrove:**
>
> • [vendite.fn_check_fondo_cancellabile](/dbzero/vendite/funzioni/fn_check_fondo_cancellabile)
>
> **I due consumatori:**
>
> • [pagamenti.fn_annulla_sistemazione](/dbzero/pagamenti/funzioni/fn_annulla_sistemazione) — il riporto sbagliato
> • `DELETE /api/v1/vendite/fondi-fattura/{id}/` — il fondo `AUTOMATICA` non più capiente della lista «da decidere» *(backend, passo BE-4)*
>
> **Chi smette di farlo inline:**
>
> • [vendite.fn_reset_fondi_fattura](/dbzero/vendite/funzioni/fn_reset_fondi_fattura)
>
> **Piano:** [brief-db-fondo-fattura-ricalcolo-e-governo](/dev/work-done/brief-db-fondo-fattura-ricalcolo-e-governo) §9.5, §9.6-b, §9.7 — passo D-21

---

### 🎯 Scopo Principale
(latest review 14-09-2026)

Cancella un atto di fondo fattura **che non è ancora diventato un fatto** —
oppure **rifiuta, dicendo perché**.

---

### ⭐ Si CANCELLA, non si annulla

Il piano originale (D-12) proponeva il passaggio ad `ANNULLATO` con motivo
obbligatorio. È **superato**: il 2026-08-21 il cantiere posting aveva già
riscritto `fn_reset_fondi_fattura` perché **cancelli** l'atto non eseguito
invece di riportarlo a `DISPONIBILE`, e la ragione era che `ANNULLATO` portava
tre significati diversi.

> *Un atto che non è mai diventato un fatto non lascia una riga di registro:
> lascia il posto vuoto che aveva prima.*

---

### Il criterio non è qui

Sta in `fn_check_fondo_cancellabile`, che questa funzione legge **una volta
sola** e mappa su quattro codici:

| Motivo del predicato | Codice sollevato | Che cosa dice all'operatore |
| --- | --- | --- |
| `ATTO_NON_TROVATO` | `E_FONDO_NON_TROVATO` | non esiste, o non è tuo — indistinguibili di proposito |
| `ATTO_ESEGUITO` · `RIGA_REGISTRATA` · `CONTABILE_CHIUSA` | `E_FONDO_NON_CANCELLABILE` | il denaro si è già mosso; la `cause` viaggia nel contesto |
| `FIGLIA_CONGELATA` | `E_FONDO_FIGLIA_CONGELATA` | la fattura che lo ha ricevuto non è più modificabile |
| `SISTEMAZIONE_ATTIVA` | `E_FONDO_TRATTENUTO_DA_SISTEMAZIONE` | **si disfa annullando la sistemazione**, non da qui |

⚠️ **Il predicato si legge una volta sola.** È il difetto già pagato in Fase C di
questo cantiere: il guard chiamava `fn_saldo_sorgente_fondo` due volte sulla
stessa riga, accettando metà condizione e rifiutando l'altra.

---

### ⭐ `E_FONDO_FIGLIA_CONGELATA` non riusa `E_FATTURA_SATELLITE_CONGELATO`

È la **stessa regola sulla stessa soglia**, e il criterio di casa è «chi può
rimediare» — che qui dà la stessa persona. L'unico argomento per coniarne uno
nuovo è che il messaggio esistente riceve `TG_TABLE_NAME` nel `VARIADIC`, cioè
**infilerebbe il nome di una tabella nella frase che l'operatore legge**.

---

### I tre `DELETE`, nell'ordine che la FK impone

```text
1. pagamenti.vendite_contabili_righe   ← fk_..._fondo_source è NO ACTION
2. vendite.fatture_fondi_fattura       ← il fondo applicato alla figlia
3. vendite.fatture_fondi_fattura_source← l'atto
```

⚠️ La FK è `NO ACTION` **di proposito**, e il `COMMENT` della colonna lo
dichiara: *cancellare un atto pretende di aver prima cancellato le sue righe;
una FK differita nasconderebbe l'ordine invece di dirlo.*

⭐ **Ed è la sede unica di quest'ordine**: da qui `fn_reset_fondi_fattura` smette
di scriverlo inline e chiama questa.

> ℹ️ Il legame verso `vendite.fatture_fondi_fattura` **non è una FK** — quella
> tabella non ha `fondo_source_id` — ma la terna *(figlia, sorgente, tipo)*, che
> è esattamente come lo scrive `fn_applica_fondi_fattura`.

> ⭐ **Rev 14-09-2026 — il primo `DELETE` apre una porta.** Dal guard del
> contenuto della distinta
> ([trgfn_vendite_contabili_righe_guard_contenuto](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_contenuto),
> D17) cancellare una riga contabile passa da
> `script.fn_check_riga_contabile_eliminabile`, che sotto una `GENERATA` risponde
> *«non è compilata a mano»*: quel predicato è il cestino dell'**operatore**, e
> qui non c'è un operatore — c'è il giro che ha prodotto quelle righe, e che ha
> già letto il **suo** criterio (punto 2). La funzione lo dichiara con
> `SET LOCAL zeroerp.allow_contabile_riga_delete_override = 'on'` prima del
> `DELETE` delle righe, e lo **richiude** subito dopo. Stesso contratto di
> `script.fn_change_user_emittenti_scope` sulla sua porta. Nessun predicato e
> nessun conteggio è cambiato.

---

### ⚠️ Due conseguenze da conoscere prima di chiamarla

1. **La tabella non è storicizzata**: il `DELETE` è definitivo. Per il riporto la
   traccia resta su `pagamenti.sistemazioni`, che diventa `ANNULLATA` **con il
   motivo** — ed è la ragione per cui il motivo lì è obbligatorio. *È il registro
   a ricordare, non la conseguenza.* ⛔ Per il fondo `AUTOMATICA` della lista
   «da decidere» non c'è registro, e non se ne inventa uno: quell'atto non ha mai
   mosso denaro.
2. **Cancellare RIAPRE la rigenerazione automatica.** Non è una scoperta:
   `fn_reset_fondi_fattura` lo dichiara già nel proprio `COMMENT` — l'«atto
   unico» di `fn_fondo_fattura_proponibile` guarda se un atto esiste in
   *qualunque* stato, quindi il giro successivo ne rifà uno leggendo il residuo
   **di adesso**. Sul riporto è il comportamento giusto (l'eccedenza è tornata al
   suo posto), ma va detto e non scoperto al primo giro notturno.

---

### Regole principali

* `SECURITY INVOKER`: la row security su `fatture_fondi_fattura_source` resta
  applicata, ed è ciò che rende vera la frase «non esiste **o** non è tuo».
* `FOR UPDATE` sull'atto: due gesti in parallelo sullo stesso atto arriverebbero
  entrambi ai `DELETE`, e il secondo ne cancellerebbe zero dicendo di aver fatto
  qualcosa.
* Guard di parametro con `E_VENDITE_CHIAMATA_NON_VALIDA` (`TECNICO`).
* Il bersaglio dell'errore è la **fattura** (sorgente o figlia, secondo il
  motivo), mai un nome di tabella. ⛔ Su `SISTEMAZIONE_ATTIVA` non c'è bersaglio:
  `config.tipi_entita` non ha un codice per le sistemazioni, e un tipo non
  dichiarato farebbe fallire la CI.

---

### Esempio d'uso

```sql
-- Il gesto della persona, con il suo esito
SELECT * FROM vendite.fn_cancella_fondo_fattura(987);
--  deleted_righe | deleted_fondi | deleted_source
--  --------------+---------------+---------------
--              1 |             1 |              1
```

---

{% include-markdown "signature-core.md" %}
