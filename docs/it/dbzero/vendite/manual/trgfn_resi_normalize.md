## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_resi_normalize`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.resi](/dbzero/vendite/tabelle/resi) — la testata che normalizza
> * [vendite.ddt](/dbzero/vendite/tabelle/ddt) — la bolla da cui eredita
>
> Approfondimento funzioni:
>
> * [vendite.trgfn_ddt_normalize](/dbzero/vendite/funzioni/trgfn_ddt_normalize) — la gemella della bolla

---

### 🎯 Scopo Principale

Normalizza la testata del reso, `BEFORE INSERT` e `BEFORE UPDATE` su `vendite.resi`: completa anno e data, eredita dalla bolla d'origine i dati del cliente e dell'emittente, e come ultimo ripiego risolve l'emittente dal cliente.

---

### Le regole, in ordine

1. **Anno e data**: all'inserimento, se il numero c'è e anno o data mancano, prende quelli del
   giorno operativo.
2. **Eredità dalla bolla**: all'inserimento, se il reso dichiara come provenienza una bolla di
   vendita (tipo `DDT_VENDITA`, riconosciuto per `codice_interno`), prende dalla bolla i campi che
   mancano — `billing_account_id`, `destinatario_soggetto_ruolo_id`, `utility_id`, `valuta_id`,
   `emittente_fiscale_id`. La bolla è a chiave `id`: il reso la dichiara in `sorgente_id`, e la
   funzione la ritrova lì.
3. **Emittente dal cliente**: se l'emittente manca ancora e c'è un cliente, lo risolve con
   `anagrafiche.fn_get_emittente_fiscale_pk`. Oggi un reso nasce sempre da una bolla, quindi è un
   ripiego che non scatta.

Non sovrascrive mai un valore già scritto. Parla prima del guard emittente–cliente (fascia `z10`),
che così vede i valori finali.

---

### Note di migrazione

* 2026-07-13 — nasce col reso di vendita (brief-db-resi-vendita).
* 2026-11-06 — la bolla si legge dalla chiave del modello, `sorgente_id`; prima dal suo uid in
  `sorgente_uid` (brief-db-sorgente-documento-e-riga).
* 2026-11-08 — la bolla si cerca per `sorgente_id` soltanto: il ramo su `sorgente_uid` non
  trovava più niente (brief-db-sorgente-documento-e-riga, G-3).

---

{% include-markdown "signature-core.md" %}
