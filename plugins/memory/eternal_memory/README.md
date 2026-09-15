# Eternal Memory

Model-agnostik (arkadaki LLM değişse bile hafızayı ve kimliği koruyan), tamamen
yerel Memory Provider. Ağ yok, üçüncü parti bağımlılık yok — yalnızca Python
standart kütüphanesi (`sqlite3`, `json`, `re`, `hashlib`, `pathlib`, `threading`).

## Depolama (profile-scoped)

Tüm durum `$HERMES_HOME/memories/eternal/` altında tutulur:

| Dosya | Katman | İçerik |
|---|---|---|
| `eternal_memory.db` | SQLite | `memories`, `entities`, `skills_ledger` tabloları (WAL modunda) |
| `state.json` | JSON | Sağlayıcı durumu, `identity_sha256` bütünlük damgası, sayaçlar |
| `identity.md` | Markdown | Çekirdek kimlik belgesi — system-prompt zırhının kaynağı (ilk çalıştırmada yazılır, asla üzerine yazılmaz) |

## Neden model-agnostik?

Karakter ve kurallar modele değil, profile bağlıdır:

- `system_prompt_block()` her turda sabit bir **"Çekirdek Kimlik ve Değişmez Prensipler"**
  zırhı döndürür: `identity.md` içeriği + model değişimlerine karşı "asla bozulamaz"
  prensipleri. Backend modeli değişse bile aynı zırh enjekte edilir.
- Hatıralar/terçihler/teknik kararlar SQLite'ta durur; `prefetch()` her turda son
  kullanıcı mesajındaki anahtar kelimelere göre en alakalı hatıraları ve kullanıcı
  tercihlerini geri getirir.
- `on_turn_end(messages, session_id)` (çerçevenin `sync_turn` kanalıyla her tur
  sonunda çağrılır) konuşmadan yeni öğrenilen kritik bilgileri, tercihleri ve teknik
  kararları regex tabanlı (LLM gerektirmez → model değişiminden bağımsız) ayıklayıp
  içerik-hash'iyle (SHA-256) duplike edilmeden kalıcı tabloya yazar; `tool_calls`
  gözlemleri `skills_ledger`'a işlenir.

## Yapılandırma

`config.yaml` → `memory.eternal_memory` (tümü opsiyonel):

```yaml
memory:
  provider: eternal_memory
  eternal_memory:
    auto_extract: true      # tur sonu otomatik ayıklama (varsayılan: true)
    max_results: 6          # prefetch'te en fazla kaç hatıra (varsayılan: 6)
    half_life_days: 90      # tazelik yarım ömrü, gün (varsayılan: 90)
```

## Araç

`eternal_memory` — `remember`, `search`, `list`, `forget` (yumuşak silme),
`entities`, `skills` işlemleri.

## Test

```bash
python -m pytest tests/plugins/memory/test_eternal_memory.py -q
```
