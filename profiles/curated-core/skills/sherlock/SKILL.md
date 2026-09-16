---
name: sherlock
description: İzinli bir kullanıcı adı için platformlar arası pasif hesap eşlemesi.
version: 1.0.0
author: AppleCurse/hermes-agent curated profile
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [username, social-media, research]
    category: research
prerequisites:
  commands: [sherlock]
---

# Sherlock: Pasif Kullanıcı Adı Keşfi

Yalnız kullanıcı açıkça belirttiğinde ve hedef kendi hesabı ya da araştırmaya izin verdiği bir kullanıcı adı olduğunda çalıştır.

1. Önce `sherlock --version` ile CLI'ı doğrula. Yoksa tek öneri: `pipx install sherlock-project==0.16.2`. Bu sürüm, CVE-2026-44590 için düzeltilmiş seridedir.
2. Tek kullanıcı adı için çalıştır: `sherlock --print-found --no-color "<username>" --timeout 60`.
3. Bulunan URL'leri olası eşleşme olarak ver; aynı kullanıcı adı kişi kimliği kanıtı değildir.

Yapma: toplu tarama, NSFW/Tor varsayılanı, parola/oturum isteme, hedefli taciz veya gizli izleme.
