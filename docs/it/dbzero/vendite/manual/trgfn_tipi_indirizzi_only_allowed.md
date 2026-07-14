## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_tipi_indirizzi_only_allowed()`

> 👀 **Vedi anche**
>
> Tabelle:
> [config.tipi_indirizzi_allowed](/dbzero/config/tabelle/tipi_indirizzi_allowed)
> [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi)
> [vendite.ddt_indirizzi](/dbzero/vendite/tabelle/ddt_indirizzi)
>
> Errori:
> [config.messaggi_errore E_TIPO_INDIRIZZO (id=71)](/dbzero/config/tabelle/messaggi_errore)

---

### 🎯 Scopo Principale

(rev 2026-07-11)

Funzione trigger **parametrica condivisa** che valida il `tipo_indirizzo_id`
inserito/aggiornato su una tabella `*_indirizzi` documento contro la **whitelist
per ambito** in `config.tipi_indirizzi_allowed`. L'ambito è passato come
argomento del trigger (`TG_ARGV[0]`).

Usata da tutte le tabelle indirizzi documento:

| Tabella | Ambito (`TG_ARGV[0]`) |
|---|---|
| `vendite.preventivi_indirizzi` | `PREVENTIVI` |
| `vendite.ordini_indirizzi` | `ORDINI` |
| `vendite.fatture_indirizzi` | `FATTURE` |
| `vendite.ddt_indirizzi` | `DDT` |
| `vendite.offerte_commerciali_indirizzi` | `OFFERTE` |
| `vendite.contratti_indirizzi` | `CONTRATTI` |
| `acquisti.ddt_indirizzi` | `ACQUISTI_DDT` |

---

### Riscrittura 2026-07-11 (brief indirizzi simmetria/cascata)

Rispetto alla versione precedente:

1. **Payload d'errore dinamico**: usa `TG_TABLE_SCHEMA`/`TG_TABLE_NAME` e la riga
   `NEW` generica (`to_jsonb(NEW)` meno lo `snapshot`). Prima era hardcoded su
   `vendite.fatture_indirizzi` + `NEW.fattura_id`, con due bug: (a) log sempre
   etichettato "Fatture"; (b) sugli altri ambiti il ramo d'errore riferiva
   `NEW.fattura_id` (colonna inesistente) → errore "record new has no field
   fattura_id" invece di `E_TIPO_INDIRIZZO`.
2. **Nessun fallback hardcoded**: la whitelist è letta **solo** da
   `config.tipi_indirizzi_allowed` (ora sempre seedata). Comportamento
   **fail-closed**: se un ambito non ha righe attive, nessun tipo è ammesso.
3. **Rimosso `TG_ARGV[1]`** (custom CSV): non più necessario senza fallback.

---

### Logica

1. Legge il `codice_interno` del tipo richiesto (per il log).
2. Costruisce `v_allowed_ids`/`v_allowed_codes` da `config.tipi_indirizzi_allowed`
   (join `config.tipi_indirizzi`) per `ambito = TG_ARGV[0]` e `attivo = true`.
3. Se il tipo è NULL o **non** è nella whitelist →
   `script.fn_log_and_raise_error` con `E_TIPO_INDIRIZZO` e contesto JSONB
   (`table`, `ambito`, `new_row`, `tipo_indirizzo_id`, `codice_interno`,
   `allowed_codes`).

---

### Errori sollevati

| Codice | id | Quando | Contesto JSONB |
|---|---|---|---|
| `E_TIPO_INDIRIZZO` | 71 | `tipo_indirizzo_id` non ammesso per l'ambito (o config ambito assente → fail-closed) | `table`, `ambito`, `new_row`, `tipo_indirizzo_id`, `codice_interno`, `allowed_codes` |

---

### Note operative

- Whitelist e obblighi (`obbligatorio`) sono dati di configurazione in
  `config.tipi_indirizzi_allowed`: cambiare gli ammessi = cambiare il seed, non
  il codice.
- La cascata al push (preventivo→ordine, ordine→DDT, offerta→contratto) copia
  gli indirizzi filtrando sugli stessi ambiti, quindi le righe generate
  soddisfano questo guard per costruzione.

---

{% include-markdown "signature-core.md" %}
