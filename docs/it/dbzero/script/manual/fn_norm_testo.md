## 📘 Documentazione Concettuale – Funzione `script.fn_norm_testo`

> 👀 **Vedi anche**
>
> • [script.fn_norm_via](/dbzero/script/funzioni/fn_norm_via)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Normalizza una stringa per il **confronto**: minuscole, spazi collassati, caratteri di
servizio rimossi, bordi ripuliti.

⭐ È `IMMUTABLE`, e non è un dettaglio: solo una funzione immutabile può essere usata dentro un
**indice di espressione**. È ciò che permette di indicizzare la forma normalizzata di una via
e di cercarci sopra senza scansione completa.

⚠️ Serve a confrontare, **non a visualizzare**: il testo normalizzato non va mostrato
all'utente né salvato al posto dell'originale. Si tiene il testo vero e si indicizza la sua
normalizzazione.

---

{% include-markdown "signature-core.md" %}
