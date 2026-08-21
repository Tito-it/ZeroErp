## 📘 Documentazione Concettuale – Tabella `storico.risorse_umane_auth_user`

> 📄 **La tabella di origine è stata archiviata**: il ponte risorsa umana ↔ utente è passato
> da `anagrafiche.identita_digitali` con il cutover multi-face-auth del 2026-04-19.
> Per la struttura si veda [anagrafiche._legacy_risorse_umane_auth_user](/dbzero/anagrafiche/tabelle/_legacy_risorse_umane_auth_user).

{% include-markdown "it/dbzero/storico/_tabelle-storico.md" %}

---

### ⚠️ Storico di una tabella archiviata

Contiene **12 righe** (2026-08-21) prodotte prima del cutover. La tabella viva non esiste più con
questo nome: al suo posto ci sono la tabella archiviata `_legacy_risorse_umane_auth_user` e la
vista omonima `anagrafiche.risorse_umane_auth_user`, che legge dalle identità digitali.

⭐ È il caso che mostra perché lo storico **non segue** la sorte della fonte: quelle righe
raccontano associazioni che sono esistite davvero, e restano l'unica traccia di come erano
prima del cutover.

---

{% include-markdown "signature-core.md" %}
