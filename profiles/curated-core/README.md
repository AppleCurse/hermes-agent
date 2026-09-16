# Curated Core Profile

Bu profil bilinçli olarak küçüktür: **Eternal Memory**, **Ponytail**, **Browser Use**, **Firecrawl** ve izinli kullanıcı-adı keşfi için **Sherlock**.

## Kurulum

Repo kökünden:

```bash
hermes profile install ./profiles/curated-core --name core -y
hermes -p core plugins doctor ponytail --ci
hermes -p core tools post-setup browser_use_cli
```

Firecrawl'ın doğrudan SDK'sını önceden kurmak istersen, Hermes'in çalıştığı Python ortamında:

```bash
python -m pip install -e '.[firecrawl]'
```

`~/.hermes/profiles/core/.env.EXAMPLE` dosyasını aynı dizindeki `.env` olarak kopyalayıp yalnız kendi anahtarlarını ekleyebilirsin. Anahtar şart değildir; profile Firecrawl'ın açıkça seçilmiş keyless yolunu da destekler.

Sherlock için, profile'ın çalıştığı makinede bir kez şunu çalıştır:

```bash
pipx install sherlock-project==0.16.2
```

## Bilinçli sınırlar

- **CodeGraph** dahil değildir: ancak repo gerçekten büyükse ve semantic çağrı/etki grafiği gerektiğinde eklenir. Telemetri kapalı olmalıdır.
- **instagrapi** kabul edilmedi: güncel paket/repo metadatasında tanınmış bir lisans yok. Instagram hesabı için ihtiyaç doğarsa yalnız resmî Meta Graph API ile, ayrı ve kullanıcı-yetkili bir köprü değerlendirilir.
- Superpowers, RTK, ikinci memory sağlayıcısı ve rastgele OSINT/MCP paketleri yoktur.

Yerel Browser Use için desteklenen bir Chromium gerekir. Cloud kullanmak istersen `BROWSER_USE_API_KEY` ekledikten sonra `browser.cloud_provider: browser-use` ayarını bilinçli olarak aç.
